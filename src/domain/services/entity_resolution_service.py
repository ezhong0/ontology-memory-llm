"""Entity resolution service.

Implements the 5-stage hybrid entity resolution algorithm from DESIGN.md v2.0.
"""

import structlog

from src.config import heuristics
from src.domain.entities import EntityAlias
from src.domain.exceptions import AmbiguousEntityError
from src.domain.ports import IEntityRepository, ILLMService
from src.domain.value_objects import (
    ConversationContext,
    EntityMention,
    ResolutionMethod,
    ResolutionResult,
)

logger = structlog.get_logger(__name__)


class EntityResolutionService:
    """Domain service for resolving entity mentions to canonical entities.

    Implements a 5-stage hybrid algorithm (DESIGN.md Section 5.1):
    1. Exact match on canonical name (70% of cases) - deterministic
    2. User alias lookup (15% of cases) - deterministic
    3. Fuzzy match using pg_trgm (10% of cases) - deterministic
    4. Coreference resolution via LLM (5% of cases) - LLM-based
    5. Domain database lookup (lazy entity creation) - deterministic

    Design Principle: Use deterministic methods where they excel (95%),
    LLMs only where they add clear value (5% - coreference).
    """

    def __init__(
        self,
        entity_repository: IEntityRepository,
        llm_service: ILLMService,
    ):
        """Initialize entity resolution service.

        Args:
            entity_repository: Repository for entity persistence
            llm_service: LLM service for coreference resolution
        """
        self.entity_repo = entity_repository
        self.llm_service = llm_service

        # Load thresholds from heuristics (calibrated in Phase 2)
        self.fuzzy_match_threshold = heuristics.FUZZY_MATCH_THRESHOLD
        self.high_confidence = heuristics.CONFIDENCE_EXACT_MATCH
        self.medium_confidence = heuristics.CONFIDENCE_FUZZY_LOW
        self.ambiguity_diff_threshold = heuristics.DISAMBIGUATION_MIN_CONFIDENCE_GAP

    async def resolve_entity(
        self,
        mention: EntityMention,
        context: ConversationContext,
    ) -> ResolutionResult:
        """Resolve an entity mention to a canonical entity.

        Applies stages 1-5 sequentially until resolution succeeds.

        Args:
            mention: Entity mention to resolve
            context: Conversation context for coreference

        Returns:
            ResolutionResult with entity_id, confidence, and method

        Raises:
            AmbiguousEntityError: If multiple entities match with equal confidence
            EntityResolutionError: If resolution fails unexpectedly
        """
        logger.info(
            "resolving_entity",
            mention=mention.text,
            is_pronoun=mention.is_pronoun,
            user_id=context.user_id,
        )

        # Stage 1: Exact match on canonical name (70% of cases)
        result = await self._stage1_exact_match(mention)
        if result:
            logger.info(
                "entity_resolved",
                method="exact",
                entity_id=result.entity_id,
                confidence=result.confidence,
            )
            return result

        # Stage 2: User alias lookup (15% of cases)
        result = await self._stage2_alias_match(mention, context.user_id)
        if result:
            logger.info(
                "entity_resolved",
                method="alias",
                entity_id=result.entity_id,
                confidence=result.confidence,
            )
            return result

        # For pronouns, skip fuzzy match and go straight to coreference
        if mention.requires_coreference:
            logger.debug("mention_requires_coreference", mention=mention.text)
            result = await self._stage4_coreference_resolution(mention, context)
            if result:
                logger.info(
                    "entity_resolved",
                    method="coreference",
                    entity_id=result.entity_id,
                    confidence=result.confidence,
                )
                return result
        else:
            # Stage 3: Fuzzy match using pg_trgm (10% of cases)
            result = await self._stage3_fuzzy_match(mention)
            if result:
                logger.info(
                    "entity_resolved",
                    method="fuzzy",
                    entity_id=result.entity_id,
                    confidence=result.confidence,
                )

                # Task 1.3.1: Auto-create alias from successful fuzzy match
                # This implements learning: next time this user types the same variant,
                # it will hit Stage 2 (alias) instead of Stage 3 (fuzzy match)
                try:
                    await self.learn_alias(
                        entity_id=result.entity_id,
                        alias_text=mention.text,
                        user_id=context.user_id,
                        source="fuzzy",
                    )
                    logger.info(
                        "fuzzy_match_alias_learned",
                        entity_id=result.entity_id,
                        alias=mention.text,
                        user_id=context.user_id,
                    )
                except Exception as e:
                    # Don't fail resolution if alias creation fails
                    logger.warning(
                        "fuzzy_match_alias_creation_failed",
                        entity_id=result.entity_id,
                        alias=mention.text,
                        error=str(e),
                    )

                return result

        # Stage 5: Domain database lookup (lazy creation)
        # Phase 1C: Domain DB connector pending - requires external DB integration
        # When implemented, will query domain.customers, domain.sales_orders, etc.
        # and create canonical entities on-the-fly for unresolved mentions
        logger.debug("domain_db_lookup_not_implemented", mention=mention.text)

        # Resolution failed
        logger.warning("entity_resolution_failed", mention=mention.text)
        return ResolutionResult.failed(
            mention_text=mention.text,
            reason="No matching entity found in any stage",
        )

    async def _stage1_exact_match(
        self, mention: EntityMention
    ) -> ResolutionResult | None:
        """Stage 1: Exact match on canonical name.

        Fast path for exact matches (70% of cases).

        Args:
            mention: Entity mention

        Returns:
            ResolutionResult if exact match found, None otherwise
        """
        try:
            entity = await self.entity_repo.find_by_canonical_name(mention.text)
            if entity:
                return ResolutionResult(
                    entity_id=entity.entity_id,
                    confidence=self.high_confidence,
                    method=ResolutionMethod.EXACT_MATCH,
                    mention_text=mention.text,
                    canonical_name=entity.canonical_name,
                    metadata={"entity_type": entity.entity_type},
                )
        except Exception as e:
            logger.error("stage1_exact_match_error", mention=mention.text, error=str(e))

        return None

    async def _stage2_alias_match(
        self, mention: EntityMention, user_id: str
    ) -> ResolutionResult | None:
        """Stage 2: User alias lookup.

        Check user-specific aliases first, then global aliases.

        Args:
            mention: Entity mention
            user_id: User ID for user-specific aliases

        Returns:
            ResolutionResult if alias found, None otherwise
        """
        try:
            # Searches user-specific first, then global
            entity = await self.entity_repo.find_by_alias(mention.text, user_id)
            if entity:
                return ResolutionResult(
                    entity_id=entity.entity_id,
                    confidence=self.medium_confidence,
                    method=ResolutionMethod.USER_ALIAS,
                    mention_text=mention.text,
                    canonical_name=entity.canonical_name,
                    metadata={"entity_type": entity.entity_type},
                )
        except Exception as e:
            logger.error("stage2_alias_match_error", mention=mention.text, error=str(e))

        return None

    async def _stage3_fuzzy_match(
        self, mention: EntityMention
    ) -> ResolutionResult | None:
        """Stage 3: Fuzzy match using pg_trgm.

        Handles typos, abbreviations, partial matches (10% of cases).

        Args:
            mention: Entity mention

        Returns:
            ResolutionResult if fuzzy match found, None otherwise

        Raises:
            AmbiguousEntityError: If multiple entities have similar confidence
        """
        try:
            matches = await self.entity_repo.fuzzy_search(
                search_text=mention.text,
                threshold=self.fuzzy_match_threshold,
                limit=5,
            )

            if not matches:
                return None

            # Get best match
            best_entity, best_score = matches[0]

            # Check for ambiguity: if top 2+ matches are within threshold, it's ambiguous
            if len(matches) > 1:
                second_entity, second_score = matches[1]
                score_diff = best_score - second_score

                if score_diff < self.ambiguity_diff_threshold:
                    # Ambiguous! Need clarification
                    candidates = [
                        (entity.entity_id, score) for entity, score in matches[:3]
                    ]
                    raise AmbiguousEntityError(
                        mention_text=mention.text,
                        candidates=candidates,
                    )

            # Confidence is the similarity score, capped at medium confidence threshold
            # (fuzzy matches are less confident than exact/alias)
            confidence = min(self.medium_confidence, best_score)

            return ResolutionResult(
                entity_id=best_entity.entity_id,
                confidence=confidence,
                method=ResolutionMethod.FUZZY_MATCH,
                mention_text=mention.text,
                canonical_name=best_entity.canonical_name,
                metadata={
                    "entity_type": best_entity.entity_type,
                    "similarity_score": best_score,
                    "alternatives": [
                        {
                            "entity_id": e.entity_id,
                            "name": e.canonical_name,
                            "score": s,
                        }
                        for e, s in matches[1:3]  # Include top alternatives
                    ],
                },
            )

        except AmbiguousEntityError:
            # Re-raise ambiguity errors
            raise
        except Exception as e:
            logger.error("stage3_fuzzy_match_error", mention=mention.text, error=str(e))

        return None

    async def _stage4_coreference_resolution(
        self, mention: EntityMention, context: ConversationContext
    ) -> ResolutionResult | None:
        """Stage 4: Coreference resolution via LLM.

        Use LLM to resolve pronouns and demonstratives (5% of cases).
        This is the ONLY stage that uses LLM.

        Args:
            mention: Entity mention (pronoun/demonstrative)
            context: Conversation context

        Returns:
            ResolutionResult if resolved, None if LLM can't resolve
        """
        if not context.has_recent_entities:
            logger.debug(
                "no_recent_entities_for_coreference",
                mention=mention.text,
            )
            return None

        try:
            # Delegate to LLM service
            result = await self.llm_service.resolve_coreference(mention, context)

            if result.is_successful:
                logger.info(
                    "coreference_resolved_by_llm",
                    mention=mention.text,
                    resolved_to=result.entity_id,
                    confidence=result.confidence,
                )
                return result
            else:
                logger.debug(
                    "llm_coreference_failed",
                    mention=mention.text,
                    reason=result.metadata.get("reason"),
                )
                return None

        except Exception as e:
            logger.error(
                "stage4_coreference_error",
                mention=mention.text,
                error=str(e),
            )
            return None

    async def learn_alias(
        self,
        entity_id: str,
        alias_text: str,
        user_id: str | None = None,
        source: str = "user_stated",
    ) -> EntityAlias:
        """Learn a new alias for an entity.

        Called when user explicitly states an equivalence:
        "Acme is short for Acme Corporation"

        Args:
            entity_id: Canonical entity ID
            alias_text: Alias text
            user_id: User ID for user-specific alias (None = global)
            source: Alias source (user_stated | learned | fuzzy)

        Returns:
            Created EntityAlias

        Raises:
            ValueError: If entity doesn't exist
        """
        # Verify entity exists
        entity = await self.entity_repo.find_by_entity_id(entity_id)
        if not entity:
            msg = f"Entity {entity_id} not found"
            raise ValueError(msg)

        # Check if alias already exists
        existing = await self.entity_repo.find_by_alias(alias_text, user_id)
        if existing and existing.entity_id == entity_id:
            logger.info(
                "alias_already_exists",
                entity_id=entity_id,
                alias=alias_text,
            )
            # Just increment use count
            aliases = await self.entity_repo.get_aliases(entity_id)
            for a in aliases:
                if a.alias_text == alias_text and a.user_id == user_id:
                    if a.alias_id is not None:
                        await self.entity_repo.increment_alias_use_count(a.alias_id)
                    return a

        # Create new alias
        # Use heuristics for alias confidence based on source
        alias_confidence = (
            heuristics.CONFIDENCE_USER_ALIAS if source == "user_stated"
            else heuristics.CONFIDENCE_FUZZY_LOW
        )

        alias = EntityAlias(
            canonical_entity_id=entity_id,
            alias_text=alias_text,
            alias_source=source,
            confidence=alias_confidence,
            user_id=user_id,
        )

        created_alias = await self.entity_repo.create_alias(alias)

        logger.info(
            "alias_learned",
            entity_id=entity_id,
            alias=alias_text,
            source=source,
            user_specific=user_id is not None,
        )

        return created_alias
