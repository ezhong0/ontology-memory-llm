"""Process chat message use case.

Orchestrates the entire flow of processing a chat message.
"""
import structlog
from typing import Optional

from src.application.dtos.chat_dtos import (
    ProcessChatMessageInput,
    ProcessChatMessageOutput,
    ResolvedEntityDTO,
)
from src.domain.entities import ChatMessage
from src.domain.exceptions import AmbiguousEntityError
from src.domain.ports import IChatEventRepository, IEntityRepository
from src.domain.services import EntityResolutionService, SimpleMentionExtractor
from src.domain.value_objects import ConversationContext

logger = structlog.get_logger(__name__)


class ProcessChatMessageUseCase:
    """Use case for processing a chat message.

    Orchestrates:
    1. Extract entity mentions from message
    2. Build conversation context
    3. Resolve each entity mention
    4. Store chat event
    5. Return results

    This is the main entry point from the API layer.
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
            entity_repository: Entity repository
            chat_repository: Chat event repository
            entity_resolution_service: Entity resolution service
            mention_extractor: Mention extraction service
        """
        self.entity_repo = entity_repository
        self.chat_repo = chat_repository
        self.resolution_service = entity_resolution_service
        self.mention_extractor = mention_extractor

    async def execute(
        self, input_dto: ProcessChatMessageInput
    ) -> ProcessChatMessageOutput:
        """Execute the use case.

        Args:
            input_dto: Input data

        Returns:
            Output with resolved entities and stored event

        Raises:
            InvalidMessageError: If message validation fails
            RepositoryError: If database operations fail
        """
        logger.info(
            "processing_chat_message",
            user_id=input_dto.user_id,
            session_id=str(input_dto.session_id),
            content_length=len(input_dto.content),
        )

        # Step 1: Create and store chat message
        message = ChatMessage(
            session_id=input_dto.session_id,
            user_id=input_dto.user_id,
            role=input_dto.role,
            content=input_dto.content,
            event_metadata=input_dto.metadata or {},
        )

        stored_message = await self.chat_repo.create(message)

        logger.debug(
            "chat_message_stored",
            event_id=stored_message.event_id,
        )

        # Step 2: Extract entity mentions
        mentions = self.mention_extractor.extract_mentions(input_dto.content)

        if not mentions:
            logger.debug("no_entity_mentions_found")
            return ProcessChatMessageOutput(
                event_id=stored_message.event_id,
                session_id=input_dto.session_id,
                resolved_entities=[],
                mention_count=0,
                resolution_success_rate=0.0,
            )

        logger.info(
            "entity_mentions_extracted",
            count=len(mentions),
        )

        # Step 3: Build conversation context
        context = await self._build_context(input_dto)

        # Step 4: Resolve each mention
        resolved_entities: list[ResolvedEntityDTO] = []
        successful_resolutions = 0

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
                # Could return this to API for user clarification

        # Step 5: Calculate success rate
        resolution_success_rate = (
            (successful_resolutions / len(mentions) * 100) if mentions else 0.0
        )

        logger.info(
            "chat_message_processed",
            event_id=stored_message.event_id,
            mentions=len(mentions),
            resolved=successful_resolutions,
            success_rate=f"{resolution_success_rate:.1f}%",
        )

        return ProcessChatMessageOutput(
            event_id=stored_message.event_id,
            session_id=input_dto.session_id,
            resolved_entities=resolved_entities,
            mention_count=len(mentions),
            resolution_success_rate=resolution_success_rate,
        )

    async def _build_context(
        self, input_dto: ProcessChatMessageInput
    ) -> ConversationContext:
        """Build conversation context for entity resolution.

        Args:
            input_dto: Input data with user and session

        Returns:
            ConversationContext with recent messages and entities
        """
        # Get recent messages in this session
        recent_messages_models = await self.chat_repo.get_recent_for_session(
            input_dto.session_id, limit=5
        )

        recent_messages = [msg.content for msg in recent_messages_models]

        # Build list of recently mentioned entities
        # For Phase 1A, we'll keep this simple and extract from recent messages
        # In Phase 1B+, we can track this more systematically
        recent_entities: list[tuple[str, str]] = []

        # TODO: In Phase 1B, maintain a session-scoped entity cache
        # For now, recent_entities will be built incrementally as we resolve
        # mentions in the current message

        return ConversationContext(
            user_id=input_dto.user_id,
            session_id=input_dto.session_id,
            recent_messages=recent_messages,
            recent_entities=recent_entities,
            current_message=input_dto.content,
        )
