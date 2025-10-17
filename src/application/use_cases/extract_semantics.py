"""Extract semantics use case - Phase 1B extraction.

Extracts semantic facts from conversation as entity-tagged natural language.
Handles fact extraction, conflict detection, and memory storage with importance scoring.
"""

from typing import Any

import structlog

from src.application.dtos.chat_dtos import (
    ResolvedEntityDTO,
    SemanticMemoryDTO,
)
from src.domain.entities import ChatMessage, SemanticMemory
from src.domain.ports import IEmbeddingService, ISemanticMemoryRepository
from src.domain.services import (
    ConflictDetectionService,
    ConflictResolutionService,
    MemoryValidationService,
)
from src.domain.value_objects import MemoryConflict

logger = structlog.get_logger(__name__)


def calculate_importance(confidence: float, confirmation_count: int = 0) -> float:
    """Calculate importance from confidence and confirmation count.

    Formula: base_importance × confirmation_factor
    - Base: 0.3 + (confidence × 0.6) maps confidence [0..1] → importance [0.3..0.9]
    - Confirmation factor: 1.0 + (0.1 × confirmations), capped at 1.5

    Args:
        confidence: Memory confidence [0.0, 1.0]
        confirmation_count: Number of confirmations (default: 0)

    Returns:
        Importance score [0.0, 1.0]
    """
    base_importance = 0.3 + (confidence * 0.6)
    confirmation_factor = min(1.5, 1.0 + (0.1 * confirmation_count))
    importance = min(1.0, base_importance * confirmation_factor)
    return importance


class ExtractSemanticsResult:
    """Result of semantic extraction.

    Attributes:
        semantic_memory_dtos: List of semantic memory DTOs for API response
        semantic_memory_entities: List of full semantic memory entities for scoring
        conflict_count: Number of conflicts detected
        conflicts_detected: List of actual conflict objects for transparency
    """

    def __init__(
        self,
        semantic_memory_dtos: list[SemanticMemoryDTO],
        semantic_memory_entities: list[SemanticMemory],
        conflict_count: int,
        conflicts_detected: list[MemoryConflict] | None = None,
    ):
        self.semantic_memory_dtos = semantic_memory_dtos
        self.semantic_memory_entities = semantic_memory_entities
        self.conflict_count = conflict_count
        self.conflicts_detected = conflicts_detected or []


class ExtractSemanticsUseCase:
    """Use case for extracting semantic memories from chat messages.

    Extracted from ProcessChatMessageUseCase to follow Single Responsibility Principle.
    Handles Phase 1B: Semantic Extraction (entity-tagged natural language).

    Responsibilities:
    - Extract semantic facts as natural language using LLM
    - Detect conflicts with existing memories (semantic similarity-based)
    - Create or confirm memories with importance scoring
    - Handle automatic conflict resolution
    """

    def __init__(
        self,
        llm_service: Any,  # LLM service with extract_facts method
        memory_validation_service: MemoryValidationService,
        conflict_detection_service: ConflictDetectionService,
        conflict_resolution_service: ConflictResolutionService,
        semantic_memory_repository: ISemanticMemoryRepository,
        embedding_service: IEmbeddingService,
        canonical_entity_repository: Any = None,  # ICanonicalEntityRepository
    ):
        """Initialize use case.

        Args:
            llm_service: LLM service for extracting natural language facts
            memory_validation_service: Service for memory confirmation and decay
            conflict_detection_service: Service for detecting memory conflicts
            conflict_resolution_service: Service for resolving detected conflicts
            semantic_memory_repository: Repository for semantic memory storage
            embedding_service: Service for generating embeddings
            canonical_entity_repository: Repository for canonical entities (optional)
        """
        self.llm_service = llm_service
        self.memory_validation_service = memory_validation_service
        self.conflict_detection_service = conflict_detection_service
        self.conflict_resolution_service = conflict_resolution_service
        self.semantic_memory_repo = semantic_memory_repository
        self.embedding_service = embedding_service
        self.canonical_entity_repo = canonical_entity_repository

    async def execute(
        self,
        message: ChatMessage,
        resolved_entities: list[ResolvedEntityDTO],
        user_id: str,
    ) -> ExtractSemanticsResult:
        """Extract semantic memories from message.

        Args:
            message: The stored chat message (must have event_id)
            resolved_entities: List of entities resolved from the message
            user_id: User identifier for memory ownership

        Returns:
            ExtractSemanticsResult with created/updated memories and conflict count
        """
        # Guard: message must have event_id (should be persisted before calling this)
        if message.event_id is None:
            msg = "Message must be persisted (have event_id) before semantic extraction"
            raise ValueError(msg)

        semantic_memory_dtos: list[SemanticMemoryDTO] = []
        semantic_memory_entities: list[SemanticMemory] = []
        conflict_count = 0
        conflicts_detected: list[MemoryConflict] = []

        # Check for resolved entities (needed for semantic extraction)
        if not resolved_entities:
            logger.debug("no_resolved_entities_for_semantic_extraction")
            return ExtractSemanticsResult(
                semantic_memory_dtos=[],
                semantic_memory_entities=[],
                conflict_count=0,
                conflicts_detected=[],
            )

        logger.info(
            "starting_semantic_extraction",
            event_id=message.event_id,
            entity_count=len(resolved_entities),
        )

        # Build entity_id -> canonical_name mapping
        entity_name_map = {
            e.entity_id: e.canonical_name
            for e in resolved_entities
        }

        # Step 1: Extract semantic facts (natural language)
        # LLM returns: [{"content": "...", "entities": [...], "confidence": 0.9}]
        try:
            facts = await self.llm_service.extract_semantic_facts(
                message=message.content,
                resolved_entities=[
                    {
                        "entity_id": e.entity_id,
                        "canonical_name": e.canonical_name,
                        "entity_type": e.entity_type,
                    }
                    for e in resolved_entities
                ],
            )
        except Exception as e:
            logger.error("fact_extraction_failed", error=str(e))
            return ExtractSemanticsResult(
                semantic_memory_dtos=[],
                semantic_memory_entities=[],
                conflict_count=0,
                conflicts_detected=[],
            )

        logger.info(
            "semantic_facts_extracted",
            fact_count=len(facts),
        )

        # Step 2: Process each fact (conflict detection + storage)
        for fact in facts:
            try:
                content = fact["content"]
                fact_entities = fact["entities"]
                confidence = fact["confidence"]

                # Calculate importance from confidence
                importance = calculate_importance(confidence)

                # Check for conflicts with existing memories about same entities
                existing_memories = await self.semantic_memory_repo.find_by_entities(
                    entity_ids=fact_entities,
                    user_id=user_id,
                    status_filter="active",
                    match_all=False,  # Match ANY entity
                )

                conflict = None
                if existing_memories:
                    # Check for semantic conflicts (similar topic but contradictory content)
                    for existing_memory in existing_memories:
                        conflict = await self.conflict_detection_service.detect_semantic_conflict(
                            new_content=content,
                            new_entities=fact_entities,
                            existing_memory=existing_memory,
                            embedding_service=self.embedding_service,
                        )

                        if conflict:
                            conflict_count += 1
                            conflicts_detected.append(conflict)
                            logger.warning(
                                "memory_conflict_detected",
                                conflict_type=conflict.conflict_type.value,
                                entities=fact_entities,
                            )

                            # Handle conflict resolution
                            if conflict.is_resolvable_automatically:
                                resolution_result = await self.conflict_resolution_service.resolve_conflict(
                                    conflict=conflict,
                                    strategy=None,  # Use recommended strategy
                                )
                                logger.info(
                                    "conflict_resolved",
                                    action=resolution_result.action,
                                    rationale=resolution_result.rationale,
                                )

                                if resolution_result.action == "supersede":
                                    # Old memory superseded, create new one
                                    break  # Exit conflict check loop, create new memory below
                                else:
                                    # Invalidate or ask_user - skip creating new memory
                                    break  # Exit processing this fact
                            else:
                                # Mark as conflicted, skip creating new memory
                                existing_memory.mark_as_conflicted()
                                await self.semantic_memory_repo.update(existing_memory)
                                break

                        # If similar content (no contradiction), confirm existing memory
                        elif await self._is_confirmation(content, existing_memory.content):
                            logger.info("confirming_existing_memory", memory_id=existing_memory.memory_id)
                            existing_memory.confirm(message.event_id)
                            await self.semantic_memory_repo.update(existing_memory)

                            semantic_memory_dtos.append(self._memory_to_dto(existing_memory))
                            semantic_memory_entities.append(existing_memory)
                            break  # Don't create new memory, confirmed existing one

                # If we got here without confirming/conflicting, create new memory
                if not conflict or (conflict and conflict.is_resolvable_automatically):
                    # Generate embedding from natural language content
                    embedding = await self.embedding_service.generate_embedding(content)

                    logger.debug(
                        "generating_memory_embedding",
                        content_preview=content[:50],
                    )

                    # Create semantic memory entity
                    memory = SemanticMemory(
                        user_id=user_id,
                        content=content,
                        entities=fact_entities,
                        confidence=confidence,
                        importance=importance,
                        source_event_ids=[message.event_id],
                        embedding=embedding,
                        source_text=message.content,
                        metadata={"confirmation_count": 1},  # Initial creation is first confirmation
                    )

                    # Store in database
                    stored_memory = await self.semantic_memory_repo.create(memory)

                    # Add to response
                    semantic_memory_dtos.append(self._memory_to_dto(stored_memory))
                    semantic_memory_entities.append(stored_memory)

            except Exception as e:
                logger.error(
                    "semantic_memory_processing_error",
                    fact=str(fact),
                    error=str(e),
                )
                # Continue processing other facts

        logger.info(
            "semantic_extraction_complete",
            memory_count=len(semantic_memory_dtos),
            conflict_count=conflict_count,
        )

        return ExtractSemanticsResult(
            semantic_memory_dtos=semantic_memory_dtos,
            semantic_memory_entities=semantic_memory_entities,
            conflict_count=conflict_count,
            conflicts_detected=conflicts_detected,
        )

    async def _is_confirmation(self, new_content: str, existing_content: str) -> bool:
        """Check if new content confirms existing memory (not contradicts).

        Uses simple heuristic: high semantic similarity without contradiction.

        Args:
            new_content: New fact content
            existing_content: Existing memory content

        Returns:
            True if new content confirms existing memory
        """
        # Generate embeddings
        new_embedding = await self.embedding_service.generate_embedding(new_content)
        existing_embedding = await self.embedding_service.generate_embedding(existing_content)

        # Calculate cosine similarity
        import numpy as np
        similarity = np.dot(new_embedding, existing_embedding) / (
            np.linalg.norm(new_embedding) * np.linalg.norm(existing_embedding)
        )

        # High similarity (>0.85) = confirmation
        return similarity > 0.85

    def _memory_to_dto(self, memory: SemanticMemory) -> SemanticMemoryDTO:
        """Convert SemanticMemory entity to DTO.

        Args:
            memory: Semantic memory entity

        Returns:
            SemanticMemoryDTO
        """
        return SemanticMemoryDTO(
            memory_id=memory.memory_id or 0,
            content=memory.content,
            entities=memory.entities,
            confidence=memory.confidence,
            importance=memory.importance,
            status=memory.status,
        )
