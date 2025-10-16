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
from src.domain.services import EntityResolutionService, SimpleMentionExtractor
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
        mention_extractor: SimpleMentionExtractor,
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

        # Step 1: Extract entity mentions
        mentions = self.mention_extractor.extract_mentions(message_content)

        if not mentions:
            logger.debug("no_entity_mentions_found")
            return ResolveEntitiesResult(
                resolved_entities=[],
                mention_count=0,
                successful_resolutions=0,
                resolution_success_rate=0.0,
                ambiguous_entities=[],
            )

        logger.info(
            "entity_mentions_extracted",
            count=len(mentions),
        )

        # Step 2: Build conversation context
        context = await self._build_context(user_id, session_id, message_content)

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

        # Step 4: Calculate success rate
        resolution_success_rate = (
            (successful_resolutions / len(mentions) * 100) if mentions else 0.0
        )

        logger.info(
            "entity_resolution_complete",
            mentions=len(mentions),
            resolved=successful_resolutions,
            success_rate=f"{resolution_success_rate:.1f}%",
            ambiguous_count=len(ambiguous_entities),
        )

        return ResolveEntitiesResult(
            resolved_entities=resolved_entities,
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
