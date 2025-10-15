"""Process chat message use case.

Orchestrates the entire flow of processing a chat message.
Includes both Phase 1A (entity resolution) and Phase 1B (semantic extraction).
"""

import structlog

from src.application.dtos.chat_dtos import (
    ProcessChatMessageInput,
    ProcessChatMessageOutput,
    ResolvedEntityDTO,
    SemanticMemoryDTO,
)
from src.domain.entities import ChatMessage, SemanticMemory
from src.domain.exceptions import AmbiguousEntityError
from src.domain.ports import IChatEventRepository, IEmbeddingService, IEntityRepository
from src.domain.services import (
    ConflictDetectionService,
    EntityResolutionService,
    MemoryValidationService,
    SemanticExtractionService,
    SimpleMentionExtractor,
)
from src.domain.value_objects import (
    ConversationContext,
    MemoryConflict,
    SemanticTriple,
)
from src.infrastructure.database.repositories import SemanticMemoryRepository

logger = structlog.get_logger(__name__)


class ProcessChatMessageUseCase:
    """Use case for processing a chat message.

    Orchestrates both Phase 1A and Phase 1B:

    Phase 1A (Entity Resolution):
    1. Extract entity mentions from message
    2. Build conversation context
    3. Resolve each entity mention
    4. Store chat event

    Phase 1B (Semantic Extraction):
    5. Extract semantic triples from message
    6. Detect conflicts with existing memories
    7. Generate embeddings for memories
    8. Store semantic memories

    This is the main entry point from the API layer.
    """

    def __init__(
        self,
        entity_repository: IEntityRepository,
        chat_repository: IChatEventRepository,
        entity_resolution_service: EntityResolutionService,
        mention_extractor: SimpleMentionExtractor,
        # Phase 1B services
        semantic_extraction_service: SemanticExtractionService,
        memory_validation_service: MemoryValidationService,
        conflict_detection_service: ConflictDetectionService,
        semantic_memory_repository: SemanticMemoryRepository,
        embedding_service: IEmbeddingService,
    ):
        """Initialize use case.

        Args:
            entity_repository: Entity repository
            chat_repository: Chat event repository
            entity_resolution_service: Entity resolution service (Phase 1A)
            mention_extractor: Mention extraction service (Phase 1A)
            semantic_extraction_service: Semantic triple extraction (Phase 1B)
            memory_validation_service: Memory validation service (Phase 1B)
            conflict_detection_service: Conflict detection service (Phase 1B)
            semantic_memory_repository: Semantic memory storage (Phase 1B)
            embedding_service: Embedding generation service (Phase 1B)
        """
        # Phase 1A dependencies
        self.entity_repo = entity_repository
        self.chat_repo = chat_repository
        self.resolution_service = entity_resolution_service
        self.mention_extractor = mention_extractor

        # Phase 1B dependencies
        self.semantic_extraction_service = semantic_extraction_service
        self.memory_validation_service = memory_validation_service
        self.conflict_detection_service = conflict_detection_service
        self.semantic_memory_repo = semantic_memory_repository
        self.embedding_service = embedding_service

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

        # After creation, event_id should always be set
        if stored_message.event_id is None:
            raise ValueError("Event ID not set after message creation")

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
                semantic_memories=[],
                conflict_count=0,
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

        # ========== Phase 1B: Semantic Extraction ==========

        semantic_memory_dtos: list[SemanticMemoryDTO] = []
        conflict_count = 0

        if resolved_entities:
            logger.info(
                "starting_semantic_extraction",
                event_id=stored_message.event_id,
                entity_count=len(resolved_entities),
            )

            # Step 6: Extract semantic triples
            triples = await self.semantic_extraction_service.extract_triples(
                message=stored_message,
                resolved_entities=[
                    {
                        "entity_id": e.entity_id,
                        "canonical_name": e.canonical_name,
                        "entity_type": e.entity_type,
                    }
                    for e in resolved_entities
                ],
            )

            logger.info(
                "semantic_triples_extracted",
                triple_count=len(triples),
            )

            # Step 7: Process each triple (conflict detection + storage)
            for triple in triples:
                try:
                    # Check for conflicts with existing memories
                    existing_memories = (
                        await self.semantic_memory_repo.find_by_subject_predicate(
                            subject_entity_id=triple.subject_entity_id,
                            predicate=triple.predicate,
                            user_id=input_dto.user_id,
                            status_filter="active",
                        )
                    )

                    conflict = None
                    if existing_memories:
                        # Check first memory for conflict
                        existing_memory = existing_memories[0]
                        conflict = self.conflict_detection_service.detect_conflict(
                            new_triple=triple,
                            existing_memory=existing_memory,
                        )

                        if conflict:
                            conflict_count += 1
                            logger.warning(
                                "memory_conflict_detected",
                                conflict_type=conflict.conflict_type.value,
                                subject=triple.subject_entity_id,
                                predicate=triple.predicate,
                            )

                            # If conflict can be auto-resolved, handle it
                            if conflict.is_resolvable_automatically:
                                await self._handle_auto_resolvable_conflict(
                                    conflict, triple, existing_memory, stored_message.event_id
                                )
                                continue
                            else:
                                # Mark both as conflicted
                                existing_memory.mark_as_conflicted()
                                await self.semantic_memory_repo.update(existing_memory)
                                # Don't create new memory if unresolvable conflict
                                continue

                    # No conflict or conflict was handled - create/reinforce memory
                    if existing_memories and not conflict:
                        # Reinforce existing memory
                        existing_memory = existing_memories[0]
                        self.memory_validation_service.reinforce_memory(
                            memory=existing_memory,
                            new_observation=triple,
                            event_id=stored_message.event_id,
                        )
                        await self.semantic_memory_repo.update(existing_memory)

                        # Add to response
                        semantic_memory_dtos.append(
                            self._memory_to_dto(existing_memory)
                        )
                    else:
                        # Create new memory
                        # Generate embedding
                        embedding_text = f"{triple.subject_entity_id} {triple.predicate} {triple.object_value}"
                        embedding = await self.embedding_service.generate_embedding(
                            embedding_text
                        )

                        # Create semantic memory entity
                        memory = SemanticMemory(
                            user_id=input_dto.user_id,
                            subject_entity_id=triple.subject_entity_id,
                            predicate=triple.predicate,
                            predicate_type=triple.predicate_type,
                            object_value=triple.object_value,
                            confidence=triple.confidence,
                            source_event_ids=[stored_message.event_id],
                            embedding=embedding,
                        )

                        # Store in database
                        stored_memory = await self.semantic_memory_repo.create(memory)

                        # Add to response
                        semantic_memory_dtos.append(self._memory_to_dto(stored_memory))

                except Exception as e:
                    logger.error(
                        "semantic_memory_processing_error",
                        triple=str(triple),
                        error=str(e),
                    )
                    # Continue processing other triples

            logger.info(
                "semantic_extraction_complete",
                memory_count=len(semantic_memory_dtos),
                conflict_count=conflict_count,
            )
        else:
            logger.debug("no_resolved_entities_for_semantic_extraction")

        # ========== Final Response ==========

        logger.info(
            "chat_message_processed",
            event_id=stored_message.event_id,
            mentions=len(mentions),
            resolved=successful_resolutions,
            success_rate=f"{resolution_success_rate:.1f}%",
            semantic_memories=len(semantic_memory_dtos),
            conflicts=conflict_count,
        )

        return ProcessChatMessageOutput(
            event_id=stored_message.event_id,
            session_id=input_dto.session_id,
            resolved_entities=resolved_entities,
            mention_count=len(mentions),
            resolution_success_rate=resolution_success_rate,
            semantic_memories=semantic_memory_dtos,
            conflict_count=conflict_count,
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

    async def _handle_auto_resolvable_conflict(
        self,
        conflict: "MemoryConflict",
        new_triple: "SemanticTriple",
        existing_memory: SemanticMemory,
        event_id: int,
    ) -> None:
        """Handle automatically resolvable memory conflicts.

        Args:
            conflict: Detected conflict
            new_triple: New semantic triple
            existing_memory: Existing conflicting memory
            event_id: Current chat event ID
        """
        from src.domain.value_objects import ConflictResolution

        if conflict.recommended_resolution == ConflictResolution.KEEP_NEWEST:
            # Update existing memory with new value
            existing_memory.object_value = new_triple.object_value
            existing_memory.confidence = new_triple.confidence
            existing_memory.source_event_ids.append(event_id)
            await self.semantic_memory_repo.update(existing_memory)
            logger.info(
                "conflict_auto_resolved_keep_newest",
                memory_id=existing_memory.memory_id,
            )

        elif conflict.recommended_resolution == ConflictResolution.KEEP_HIGHEST_CONFIDENCE:
            if new_triple.confidence > existing_memory.confidence:
                # New is more confident - update
                existing_memory.object_value = new_triple.object_value
                existing_memory.confidence = new_triple.confidence
                existing_memory.source_event_ids.append(event_id)
                await self.semantic_memory_repo.update(existing_memory)
                logger.info(
                    "conflict_auto_resolved_keep_highest_conf",
                    memory_id=existing_memory.memory_id,
                    kept="new",
                )
            else:
                # Existing is more confident - keep it
                logger.info(
                    "conflict_auto_resolved_keep_highest_conf",
                    memory_id=existing_memory.memory_id,
                    kept="existing",
                )

        elif conflict.recommended_resolution == ConflictResolution.KEEP_MOST_REINFORCED:
            # Existing is always more reinforced (new has count=1)
            logger.info(
                "conflict_auto_resolved_keep_most_reinforced",
                memory_id=existing_memory.memory_id,
            )

    def _memory_to_dto(self, memory: SemanticMemory) -> SemanticMemoryDTO:
        """Convert SemanticMemory entity to DTO.

        Args:
            memory: Semantic memory entity

        Returns:
            SemanticMemoryDTO
        """
        return SemanticMemoryDTO(
            memory_id=memory.memory_id or 0,
            subject_entity_id=memory.subject_entity_id,
            predicate=memory.predicate,
            predicate_type=memory.predicate_type.value,
            object_value=memory.object_value,
            confidence=memory.confidence,
            status=memory.status,
        )
