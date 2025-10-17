"""Score memories use case - Phase 1D extraction.

Extracts memory scoring logic from ProcessChatMessageUseCase god object.
Handles multi-signal relevance scoring for memory retrieval.
"""

from uuid import UUID

import numpy as np
import structlog

from src.application.dtos.chat_dtos import ResolvedEntityDTO
from src.domain.entities import SemanticMemory
from src.domain.ports import IEmbeddingService, ISemanticMemoryRepository
from src.domain.services import MultiSignalScorer
from src.domain.value_objects import MemoryCandidate, QueryContext
from src.domain.value_objects.conversation_context_reply import RetrievedMemory

logger = structlog.get_logger(__name__)


class ScoreMemoriesUseCase:
    """Use case for scoring memories with multi-signal relevance.

    Extracted from ProcessChatMessageUseCase to follow Single Responsibility Principle.
    Handles Phase 1D: Multi-Signal Retrieval.

    Responsibilities:
    - Retrieve existing memories from database (cross-turn retrieval)
    - Convert semantic memories to memory candidates
    - Generate query embedding
    - Score candidates using multi-signal scorer
    - Convert scored memories to retrieved memories
    """

    def __init__(
        self,
        multi_signal_scorer: MultiSignalScorer,
        embedding_service: IEmbeddingService,
        semantic_memory_repository: ISemanticMemoryRepository,
    ):
        """Initialize use case.

        Args:
            multi_signal_scorer: Service for multi-signal relevance scoring
            embedding_service: Service for generating embeddings
            semantic_memory_repository: Repository for retrieving existing memories
        """
        self.multi_signal_scorer = multi_signal_scorer
        self.embedding_service = embedding_service
        self.semantic_memory_repo = semantic_memory_repository

    async def execute(
        self,
        semantic_memory_entities: list[SemanticMemory],
        resolved_entities: list[ResolvedEntityDTO],
        query_text: str,
        user_id: str,
        session_id: UUID,
    ) -> tuple[list[RetrievedMemory], dict[int, SemanticMemory]]:
        """Score memories using multi-signal relevance.

        Retrieves existing memories from database and combines with current-turn memories.

        Args:
            semantic_memory_entities: List of semantic memories created this turn
            resolved_entities: List of resolved entities from query
            query_text: Original query text
            user_id: User identifier
            session_id: Session identifier

        Returns:
            Tuple of (retrieved memories, semantic memory map by ID)
        """
        logger.info(
            "starting_memory_scoring",
            current_turn_memories=len(semantic_memory_entities),
        )

        # Generate query embedding (needed for retrieval and scoring)
        query_embedding_list = await self.embedding_service.generate_embedding(
            query_text
        )
        query_embedding = np.array(query_embedding_list, dtype=np.float64)

        # Retrieve existing memories from database using vector similarity
        existing_memories_with_scores: list[tuple[SemanticMemory, float]] = await self.semantic_memory_repo.find_similar(
            query_embedding=query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding,
            user_id=user_id,
            limit=50,  # Retrieve top 50 candidates
            min_confidence=0.3,  # Minimum confidence threshold
        )

        # Extract just the memory entities (discard similarity scores from find_similar)
        existing_memories: list[SemanticMemory] = [mem for mem, _ in existing_memories_with_scores]

        # Phase 2.2: Also retrieve aging memories from recent session context
        # (Confirmation messages may not match semantically, so we need to include aging memories)
        # This ensures validation prompts can be confirmed even with simple "Yes" responses
        aging_memories = await self.semantic_memory_repo.find_aging_memories(
            user_id=user_id,
            days=7,  # Last week
        )

        # Add aging memories to existing_memories if not already present
        for aging_memory in aging_memories:
            # Check if not already in list
            if aging_memory.memory_id and not any(m.memory_id == aging_memory.memory_id for m in existing_memories):
                existing_memories.append(aging_memory)

        logger.info(
            "included_aging_memories_for_validation",
            aging_count=len(aging_memories),
        )

        # Also retrieve memories by entity (for memories without embeddings, e.g., from scenarios)
        entity_ids = [e.entity_id for e in resolved_entities]
        if entity_ids:
            entity_memories = await self.semantic_memory_repo.find_by_entities(
                entity_ids=entity_ids,
                user_id=user_id,
                status_filter="active",
                match_all=False,  # Match ANY entity
            )

            # Add entity-based memories to existing_memories if not already present
            for entity_memory in entity_memories:
                if entity_memory.memory_id and not any(m.memory_id == entity_memory.memory_id for m in existing_memories):
                    existing_memories.append(entity_memory)

            logger.info(
                "included_entity_based_memories",
                entity_count=len(entity_memories),
                entity_ids=entity_ids,
            )

        logger.info(
            "retrieved_existing_memories",
            count=len(existing_memories),
        )

        # Phase 2.2: Check for aged memories and mark as "aging"
        # (Epistemic Humility - admit uncertainty for aged data)
        from datetime import datetime, timedelta, timezone
        from src.config import heuristics

        aged_threshold = datetime.now(timezone.utc) - timedelta(
            days=heuristics.VALIDATION_THRESHOLD_DAYS
        )

        for mem in existing_memories:
            # Check if memory is older than threshold and not already marked as aging
            if (
                mem.last_accessed_at
                and mem.last_accessed_at < aged_threshold
                and mem.status == "active"
            ):
                # Mark as aging (requires validation)
                mem.status = "aging"
                await self.semantic_memory_repo.update(mem)

                logger.info(
                    "memory_marked_as_aging",
                    memory_id=mem.memory_id,
                    entities=mem.entities,
                    days_since_access=(datetime.now(timezone.utc) - mem.last_accessed_at).days,
                )

        # Combine current-turn memories with existing memories
        # Deduplicate by memory_id to avoid scoring the same memory twice
        all_memories_dict = {}

        # Add existing memories first
        for mem in existing_memories:
            if mem.memory_id:
                all_memories_dict[mem.memory_id] = mem

        # Add current-turn memories (will overwrite if same ID, keeping fresher version)
        for mem in semantic_memory_entities:
            if mem.memory_id:
                all_memories_dict[mem.memory_id] = mem

        all_memories = list(all_memories_dict.values())

        if not all_memories:
            logger.debug("no_memories_to_score")
            return ([], {})

        logger.info(
            "total_memories_for_scoring",
            count=len(all_memories),
            current_turn=len(semantic_memory_entities),
            existing=len(existing_memories),
            deduplicated=len(all_memories),
        )

        # Convert SemanticMemory entities to MemoryCandidate for scoring
        memory_candidates = []
        for mem in all_memories:
            # Handle memories without embeddings (e.g., from scenario loading)
            # Use zero-vector fallback so they can still be scored by entity overlap
            if mem.embedding is None:
                logger.info(
                    "memory_missing_embedding_using_zero_vector",
                    memory_id=mem.memory_id,
                    entities=mem.entities,
                )
                # Create zero-vector embedding (1536 dimensions for text-embedding-3-small)
                embedding_array = np.zeros(1536, dtype=np.float64)
            else:
                # Normal case: convert existing embedding to numpy array
                embedding_array = np.array(mem.embedding, dtype=np.float64) if not isinstance(mem.embedding, np.ndarray) else mem.embedding

            # Debug logging
            logger.debug(
                "embedding_prepared",
                memory_id=mem.memory_id,
                embedding_type=type(embedding_array).__name__,
                is_zero_vector=(mem.embedding is None),
            )

            memory_candidates.append(
                MemoryCandidate(
                    memory_id=mem.memory_id or 0,
                    memory_type="semantic",
                    content=mem.content,
                    entities=mem.entities,
                    embedding=embedding_array,
                    created_at=mem.created_at,
                    importance=mem.importance,
                    confidence=mem.confidence,
                    confirmation_count=mem.confirmation_count,
                    last_accessed_at=mem.last_accessed_at,
                )
            )

        # Build query context for scoring (entity_ids already computed above for retrieval)
        # Debug logging for query_embedding
        logger.debug(
            "creating_query_context",
            query_embedding_type=type(query_embedding).__name__,
            is_ndarray=isinstance(query_embedding, np.ndarray),
            has_shape=hasattr(query_embedding, "shape"),
        )

        query_context = QueryContext(
            query_text=query_text,
            query_embedding=query_embedding,
            entity_ids=entity_ids,
            user_id=user_id,
            session_id=str(session_id),
            strategy="exploratory",  # Default strategy for conversational queries
        )

        # Score candidates using multi-signal scorer
        scored_memories = self.multi_signal_scorer.score_candidates(
            candidates=memory_candidates,
            query_context=query_context,
        )

        # Convert ScoredMemory to RetrievedMemory
        retrieved_memories = []
        for scored in scored_memories:
            # Get the full memory entity to access last_accessed_at and status
            memory_entity = all_memories_dict.get(scored.candidate.memory_id)

            retrieved_memories.append(
                RetrievedMemory(
                    memory_id=scored.candidate.memory_id,
                    memory_type=scored.candidate.memory_type,
                    content=scored.candidate.content,
                    relevance_score=scored.relevance_score,
                    confidence=scored.candidate.confidence or 1.0,
                    last_accessed_at=memory_entity.last_accessed_at if memory_entity else None,
                    status=memory_entity.status if memory_entity else "active",
                )
            )

        logger.info(
            "memories_scored",
            candidate_count=len(memory_candidates),
            scored_count=len(scored_memories),
            top_score=scored_memories[0].relevance_score if scored_memories else 0.0,
        )

        return (retrieved_memories, all_memories_dict)
