"""Resolve entities use case - Phase 1A extraction.

Extracts entity resolution logic from ProcessChatMessageUseCase god object.
Handles mention extraction and 5-stage entity resolution.
"""

from uuid import UUID

import structlog

from src.application.dtos.chat_dtos import (
    ResolvedEntityDTO,
)
from src.domain.exceptions import AmbiguousEntityError
from src.domain.ports import IChatEventRepository, IEntityRepository
from src.domain.services import EntityResolutionService
from src.domain.services.llm_mention_extractor import LLMMentionExtractor
from src.domain.value_objects import ConversationContext

logger = structlog.get_logger(__name__)


class ResolveEntitiesResult:
    """Result of entity resolution.

    Attributes:
        resolved_entities: List of successfully resolved entities
        mention_count: Total number of mentions extracted
        successful_resolutions: Number of successfully resolved mentions
        resolution_success_rate: Percentage of successful resolutions
        ambiguous_entities: List of AmbiguousEntityError exceptions (for user clarification)
    """

    def __init__(
        self,
        resolved_entities: list[ResolvedEntityDTO],
        mention_count: int,
        successful_resolutions: int,
        resolution_success_rate: float,
        ambiguous_entities: list[AmbiguousEntityError] | None = None,
    ):
        self.resolved_entities = resolved_entities
        self.mention_count = mention_count
        self.successful_resolutions = successful_resolutions
        self.resolution_success_rate = resolution_success_rate
        self.ambiguous_entities = ambiguous_entities or []


class ResolveEntitiesUseCase:
    """Use case for resolving entities from chat messages.

    Extracted from ProcessChatMessageUseCase to follow Single Responsibility Principle.
    Handles Phase 1A: Entity Resolution.

    Responsibilities:
    - Extract entity mentions from message
    - Build conversation context
    - Resolve each mention using 5-stage resolution
    - Track success rate and ambiguities
    """

    def __init__(
        self,
        entity_repository: IEntityRepository,
        chat_repository: IChatEventRepository,
        entity_resolution_service: EntityResolutionService,
        mention_extractor: LLMMentionExtractor,
    ):
        """Initialize use case.

        Args:
            entity_repository: Repository for entity persistence
            chat_repository: Repository for chat event history
            entity_resolution_service: Service for resolving entity mentions
            mention_extractor: Service for extracting mentions from text
        """
        self.entity_repo = entity_repository
        self.chat_repo = chat_repository
        self.resolution_service = entity_resolution_service
        self.mention_extractor = mention_extractor

    async def execute(
        self,
        message_content: str,
        user_id: str,
        session_id: UUID,
    ) -> ResolveEntitiesResult:
        """Resolve entities from message content.

        Args:
            message_content: The message text to extract entities from
            user_id: User identifier
            session_id: Session identifier for context

        Returns:
            ResolveEntitiesResult with resolved entities and metadata
        """
        logger.info(
            "resolving_entities",
            user_id=user_id,
            session_id=str(session_id),
            content_length=len(message_content),
        )

        # Step 1: Extract entity mentions from current message
        mentions = await self.mention_extractor.extract_mentions(message_content)

        logger.info(
            "entity_mentions_extracted",
            count=len(mentions),
        )

        # Step 2: Build conversation context (ALWAYS - per VISION.md "meaning is always contextual")
        context = await self._build_context(user_id, session_id, message_content)

        # Phase 2.2: ALWAYS extract implicit entities from recent session context
        # This enables: confirmations ("Yes, still correct"), pronouns ("they prefer Friday"),
        # and follow-ups without re-stating entities.
        # Per user directive: "recent messages should always be fed into context"
        implicit_entities = await self._extract_implicit_entities_from_context(
            context, user_id, session_id
        )

        if implicit_entities:
            logger.info(
                "implicit_entities_from_session_context",
                count=len(implicit_entities),
            )
        else:
            logger.debug("no_implicit_entities_from_context")

        # Step 3: Resolve each mention
        resolved_entities: list[ResolvedEntityDTO] = []
        successful_resolutions = 0
        ambiguous_entities: list[AmbiguousEntityError] = []

        for mention in mentions:
            try:
                result = await self.resolution_service.resolve_entity(mention, context)

                if result.is_successful:
                    # Convert to DTO
                    entity_dto = ResolvedEntityDTO(
                        entity_id=result.entity_id,
                        canonical_name=result.canonical_name,
                        entity_type=result.metadata.get("entity_type", "unknown"),
                        mention_text=result.mention_text,
                        confidence=result.confidence,
                        method=result.method.value,
                    )
                    resolved_entities.append(entity_dto)
                    successful_resolutions += 1

                    # Add to context for next mentions
                    context.recent_entities.append(
                        (result.entity_id, result.canonical_name)
                    )

                    logger.debug(
                        "mention_resolved",
                        mention=mention.text,
                        entity_id=result.entity_id,
                        method=result.method.value,
                    )
                else:
                    logger.debug(
                        "mention_not_resolved",
                        mention=mention.text,
                        reason=result.metadata.get("reason"),
                    )

            except AmbiguousEntityError as e:
                # Log ambiguity but continue processing
                logger.warning(
                    "ambiguous_entity_detected",
                    mention=mention.text,
                    candidates=e.candidates,
                )
                # Store the full exception to preserve entity details
                ambiguous_entities.append(e)
                # Continue processing other mentions

        # Step 4: Combine explicit and implicit entities (deduplicate by entity_id)
        # Implicit entities from session context are always included (Phase 2.2)
        combined_entities_dict: dict[str, ResolvedEntityDTO] = {}

        # Add implicit entities first (lower priority)
        for entity in implicit_entities:
            combined_entities_dict[entity.entity_id] = entity

        # Add explicit entities (higher priority - will overwrite implicit if same entity)
        for entity in resolved_entities:
            combined_entities_dict[entity.entity_id] = entity

        combined_entities = list(combined_entities_dict.values())

        # Step 5: Calculate success rate (based on explicit mentions only)
        resolution_success_rate = (
            (successful_resolutions / len(mentions) * 100) if mentions else 0.0
        )

        logger.info(
            "entity_resolution_complete",
            mentions=len(mentions),
            resolved_explicit=successful_resolutions,
            resolved_implicit=len(implicit_entities),
            combined_total=len(combined_entities),
            success_rate=f"{resolution_success_rate:.1f}%",
            ambiguous_count=len(ambiguous_entities),
        )

        return ResolveEntitiesResult(
            resolved_entities=combined_entities,
            mention_count=len(mentions),
            successful_resolutions=successful_resolutions,
            resolution_success_rate=resolution_success_rate,
            ambiguous_entities=ambiguous_entities,
        )

    async def _build_context(
        self,
        user_id: str,
        session_id: UUID,
        current_message: str,
    ) -> ConversationContext:
        """Build conversation context for entity resolution.

        Args:
            user_id: User identifier
            session_id: Session identifier
            current_message: Current message being processed

        Returns:
            ConversationContext with recent messages and entities
        """
        # Get recent messages in this session
        recent_messages_models = await self.chat_repo.get_recent_for_session(
            session_id, limit=5
        )

        recent_messages = [msg.content for msg in recent_messages_models]

        # Build list of recently mentioned entities
        # For Phase 1A, we'll keep this simple
        # Future enhancement: Maintain session-scoped entity cache
        recent_entities: list[tuple[str, str]] = []

        return ConversationContext(
            user_id=user_id,
            session_id=session_id,
            recent_messages=recent_messages,
            recent_entities=recent_entities,
            current_message=current_message,
        )

    async def _extract_implicit_entities_from_context(
        self,
        context: ConversationContext,
        user_id: str,
        session_id: UUID,
    ) -> list[ResolvedEntityDTO]:
        """Extract entities from recent session context (implicit resolution).

        Phase 2.2: Session-aware entity resolution
        When current message has no explicit entity mentions, extract entities from
        recent conversation context to enable confirmations and follow-ups.

        IMPORTANT: Only looks at PRIOR messages, not the current message being processed.
        This prevents circular dependencies where implicit resolution creates aliases
        that then get used by explicit resolution in the same turn.

        Args:
            context: Conversation context with recent messages
            user_id: User identifier
            session_id: Session identifier

        Returns:
            List of implicitly resolved entities from context (marked as implicit)
        """
        implicit_entities: list[ResolvedEntityDTO] = []
        seen_entity_ids: set[str] = set()

        # Look at recent messages (most recent first, up to 3 for focus)
        # CRITICAL: Filter out the current message to avoid circular dependency
        # The current message is being processed explicitly, so it shouldn't
        # also be processed implicitly.
        prior_messages = [
            msg for msg in context.recent_messages[:3]
            if msg.strip() != context.current_message.strip()
        ]

        for recent_message in prior_messages:
            # Extract mentions from this recent message
            mentions = await self.mention_extractor.extract_mentions(recent_message)

            if not mentions:
                continue

            # Resolve each mention
            for mention in mentions:
                try:
                    result = await self.resolution_service.resolve_entity(
                        mention, context
                    )

                    if result.is_successful and result.entity_id not in seen_entity_ids:
                        # Convert to DTO and mark as implicit
                        entity_dto = ResolvedEntityDTO(
                            entity_id=result.entity_id,
                            canonical_name=result.canonical_name,
                            entity_type=result.metadata.get("entity_type", "unknown"),
                            mention_text=result.mention_text,
                            confidence=result.confidence * 0.9,  # Slightly lower confidence for implicit
                            method="implicit_from_context",  # Special method for transparency
                            is_implicit=True,  # Mark as implicit
                        )
                        implicit_entities.append(entity_dto)
                        seen_entity_ids.add(result.entity_id)

                        logger.debug(
                            "implicit_entity_extracted_from_context",
                            entity_id=result.entity_id,
                            canonical_name=result.canonical_name,
                            from_message=recent_message[:50],
                        )

                except AmbiguousEntityError:
                    # Skip ambiguous entities in implicit resolution
                    # (Don't want to prompt disambiguation for context entities)
                    continue

        return implicit_entities
