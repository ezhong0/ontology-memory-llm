"""Extract semantics use case - Phase 1B extraction.

Extracts semantic extraction logic from ProcessChatMessageUseCase god object.
Handles triple extraction, conflict detection, and memory storage.
"""

import structlog

from src.application.dtos.chat_dtos import (
    ResolvedEntityDTO,
    SemanticMemoryDTO,
)
from src.domain.entities import ChatMessage, SemanticMemory
from src.domain.ports import IEmbeddingService, ISemanticMemoryRepository
from src.domain.services import (
    ConflictDetectionService,
    MemoryValidationService,
    SemanticExtractionService,
)
from src.domain.value_objects import ConflictResolution, MemoryConflict, SemanticTriple

logger = structlog.get_logger(__name__)


class ExtractSemanticsResult:
    """Result of semantic extraction.

    Attributes:
        semantic_memory_dtos: List of semantic memory DTOs for API response
        semantic_memory_entities: List of full semantic memory entities for scoring
        conflict_count: Number of conflicts detected
    """

    def __init__(
        self,
        semantic_memory_dtos: list[SemanticMemoryDTO],
        semantic_memory_entities: list[SemanticMemory],
        conflict_count: int,
    ):
        self.semantic_memory_dtos = semantic_memory_dtos
        self.semantic_memory_entities = semantic_memory_entities
        self.conflict_count = conflict_count


class ExtractSemanticsUseCase:
    """Use case for extracting semantic memories from chat messages.

    Extracted from ProcessChatMessageUseCase to follow Single Responsibility Principle.
    Handles Phase 1B: Semantic Extraction.

    Responsibilities:
    - Extract semantic triples using LLM
    - Detect conflicts with existing memories
    - Create or reinforce memories
    - Handle automatic conflict resolution
    """

    def __init__(
        self,
        semantic_extraction_service: SemanticExtractionService,
        memory_validation_service: MemoryValidationService,
        conflict_detection_service: ConflictDetectionService,
        semantic_memory_repository: ISemanticMemoryRepository,
        embedding_service: IEmbeddingService,
    ):
        """Initialize use case.

        Args:
            semantic_extraction_service: Service for extracting semantic triples
            memory_validation_service: Service for memory reinforcement and decay
            conflict_detection_service: Service for detecting memory conflicts
            semantic_memory_repository: Repository for semantic memory storage
            embedding_service: Service for generating embeddings
        """
        self.semantic_extraction_service = semantic_extraction_service
        self.memory_validation_service = memory_validation_service
        self.conflict_detection_service = conflict_detection_service
        self.semantic_memory_repo = semantic_memory_repository
        self.embedding_service = embedding_service

    async def execute(
        self,
        message: ChatMessage,
        resolved_entities: list[ResolvedEntityDTO],
        user_id: str,
    ) -> ExtractSemanticsResult:
        """Extract semantic memories from message.

        Args:
            message: The stored chat message
            resolved_entities: List of entities resolved from the message
            user_id: User identifier for memory ownership

        Returns:
            ExtractSemanticsResult with created/updated memories and conflict count
        """
        semantic_memory_dtos: list[SemanticMemoryDTO] = []
        semantic_memory_entities: list[SemanticMemory] = []
        conflict_count = 0

        if not resolved_entities:
            logger.debug("no_resolved_entities_for_semantic_extraction")
            return ExtractSemanticsResult(
                semantic_memory_dtos=[],
                semantic_memory_entities=[],
                conflict_count=0,
            )

        logger.info(
            "starting_semantic_extraction",
            event_id=message.event_id,
            entity_count=len(resolved_entities),
        )

        # Step 1: Extract semantic triples
        triples = await self.semantic_extraction_service.extract_triples(
            message=message,
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

        # Step 2: Process each triple (conflict detection + storage)
        for triple in triples:
            try:
                # Check for conflicts with existing memories
                existing_memories = (
                    await self.semantic_memory_repo.find_by_subject_predicate(
                        subject_entity_id=triple.subject_entity_id,
                        predicate=triple.predicate,
                        user_id=user_id,
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
                                conflict, triple, existing_memory, message.event_id
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
                        event_id=message.event_id,
                    )
                    await self.semantic_memory_repo.update(existing_memory)

                    # Add to response
                    semantic_memory_dtos.append(
                        self._memory_to_dto(existing_memory)
                    )
                    semantic_memory_entities.append(existing_memory)
                else:
                    # Create new memory
                    # Generate embedding
                    embedding_text = f"{triple.subject_entity_id} {triple.predicate} {triple.object_value}"
                    embedding = await self.embedding_service.generate_embedding(
                        embedding_text
                    )

                    # Create semantic memory entity
                    memory = SemanticMemory(
                        user_id=user_id,
                        subject_entity_id=triple.subject_entity_id,
                        predicate=triple.predicate,
                        predicate_type=triple.predicate_type,
                        object_value=triple.object_value,
                        confidence=triple.confidence,
                        source_event_ids=[message.event_id],
                        embedding=embedding,
                    )

                    # Store in database
                    stored_memory = await self.semantic_memory_repo.create(memory)

                    # Add to response
                    semantic_memory_dtos.append(self._memory_to_dto(stored_memory))
                    semantic_memory_entities.append(stored_memory)

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

        return ExtractSemanticsResult(
            semantic_memory_dtos=semantic_memory_dtos,
            semantic_memory_entities=semantic_memory_entities,
            conflict_count=conflict_count,
        )

    async def _handle_auto_resolvable_conflict(
        self,
        conflict: MemoryConflict,
        new_triple: SemanticTriple,
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
