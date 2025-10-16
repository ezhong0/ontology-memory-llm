"""Candidate generation service for memory retrieval.

Generates memory candidates by retrieving from all layers (semantic, episodic, summary)
in parallel using pgvector similarity search.

Design from: DESIGN.md v2.0 - Retrieval Pipeline
"""

import asyncio
from uuid import UUID

import numpy as np
import structlog

from src.config import heuristics
from src.domain.entities.semantic_memory import SemanticMemory
from src.domain.exceptions import DomainError
from src.domain.ports.episodic_memory_repository import IEpisodicMemoryRepository
from src.domain.ports.semantic_memory_repository import ISemanticMemoryRepository
from src.domain.ports.summary_repository import ISummaryRepository
from src.domain.value_objects.memory_candidate import MemoryCandidate
from src.domain.value_objects.query_context import QueryContext, RetrievalFilters

logger = structlog.get_logger()


class CandidateGenerator:
    """Generate memory candidates using parallel retrieval from all layers.

    Retrieves from:
    - Semantic memories (Layer 4): Facts with lifecycle
    - Episodic memories (Layer 3): Events with meaning
    - Memory summaries (Layer 6): Consolidated cross-session knowledge

    Philosophy: Fast parallel retrieval, deduplication, layer-specific limits.

    Example:
        >>> generator = CandidateGenerator(semantic_repo, episodic_repo, summary_repo)
        >>> candidates = await generator.generate_candidates(query_context)
        >>> # Returns deduplicated list from all layers
    """

    def __init__(
        self,
        semantic_repo: ISemanticMemoryRepository,
        episodic_repo: IEpisodicMemoryRepository,
        summary_repo: ISummaryRepository,
    ) -> None:
        """Initialize candidate generator.

        Args:
            semantic_repo: Repository for semantic memories (port/interface)
            episodic_repo: Repository for episodic memories (port/interface)
            summary_repo: Repository for memory summaries (port/interface)
        """
        self._semantic_repo = semantic_repo
        self._episodic_repo = episodic_repo
        self._summary_repo = summary_repo

    async def generate_candidates(
        self,
        query_context: QueryContext,
        filters: RetrievalFilters | None = None,
    ) -> list[MemoryCandidate]:
        """Generate candidates from all memory layers in parallel.

        Args:
            query_context: Query context with embedding and user_id
            filters: Optional filters for candidate selection

        Returns:
            Deduplicated list of memory candidates from all layers

        Raises:
            DomainError: If candidate generation fails
        """
        try:
            logger.info(
                "generating_candidates",
                user_id=query_context.user_id,
                strategy=query_context.strategy,
            )

            # Determine which layers to retrieve from based on filters
            retrieve_semantic = self._should_retrieve_layer("semantic", filters)
            retrieve_episodic = self._should_retrieve_layer("episodic", filters)
            retrieve_summary = self._should_retrieve_layer("summary", filters)

            # Parallel retrieval from all layers
            tasks = []

            if retrieve_semantic:
                tasks.append(self._retrieve_semantic_candidates(query_context, filters))

            if retrieve_episodic:
                tasks.append(self._retrieve_episodic_candidates(query_context, filters))

            if retrieve_summary:
                tasks.append(self._retrieve_summary_candidates(query_context, filters))

            # Execute all retrievals in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Combine results and handle exceptions
            all_candidates = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        "layer_retrieval_failed",
                        layer_index=i,
                        error=str(result),
                    )
                    # Continue with other layers even if one fails
                    continue

                all_candidates.extend(result)

            # Deduplicate candidates
            deduplicated = self._deduplicate_candidates(all_candidates)

            logger.info(
                "candidates_generated",
                total_candidates=len(all_candidates),
                deduplicated_count=len(deduplicated),
            )

            return deduplicated

        except Exception as e:
            logger.error(
                "generate_candidates_error",
                user_id=query_context.user_id,
                error=str(e),
            )
            msg = f"Error generating candidates: {e}"
            raise DomainError(msg) from e

    async def _retrieve_semantic_candidates(
        self,
        query_context: QueryContext,
        filters: RetrievalFilters | None,
    ) -> list[MemoryCandidate]:
        """Retrieve candidates from semantic memory layer.

        Args:
            query_context: Query context
            filters: Optional filters

        Returns:
            List of semantic memory candidates
        """
        limit = heuristics.MAX_SEMANTIC_CANDIDATES
        min_confidence = filters.min_confidence if filters else heuristics.MIN_CONFIDENCE_FOR_USE

        # Semantic repository returns (SemanticMemory, float) tuples
        results = await self._semantic_repo.find_similar(
            query_embedding=query_context.query_embedding.tolist(),
            user_id=query_context.user_id,
            limit=limit,
            min_confidence=min_confidence,
        )

        # Convert SemanticMemory to MemoryCandidate
        candidates = []
        for memory, _similarity in results:
            candidate = self._semantic_to_candidate(memory)
            candidates.append(candidate)

        logger.debug(
            "retrieved_semantic_candidates",
            count=len(candidates),
        )

        return candidates

    async def _retrieve_episodic_candidates(
        self,
        query_context: QueryContext,
        filters: RetrievalFilters | None,
    ) -> list[MemoryCandidate]:
        """Retrieve candidates from episodic memory layer.

        Args:
            query_context: Query context
            filters: Optional filters

        Returns:
            List of episodic memory candidates
        """
        limit = heuristics.MAX_TEMPORAL_CANDIDATES
        session_id = UUID(query_context.session_id) if query_context.session_id else None

        candidates = await self._episodic_repo.find_similar(
            user_id=query_context.user_id,
            query_embedding=query_context.query_embedding,
            limit=limit,
            session_id=session_id,
        )

        logger.debug(
            "retrieved_episodic_candidates",
            count=len(candidates),
        )

        return candidates

    async def _retrieve_summary_candidates(
        self,
        query_context: QueryContext,
        filters: RetrievalFilters | None,
    ) -> list[MemoryCandidate]:
        """Retrieve candidates from summary layer.

        Args:
            query_context: Query context
            filters: Optional filters

        Returns:
            List of summary candidates
        """
        limit = heuristics.MAX_SUMMARY_CANDIDATES

        candidates = await self._summary_repo.find_similar(
            user_id=query_context.user_id,
            query_embedding=query_context.query_embedding,
            limit=limit,
            scope_type=None,  # Retrieve all scope types
        )

        logger.debug(
            "retrieved_summary_candidates",
            count=len(candidates),
        )

        return candidates

    def _should_retrieve_layer(
        self, layer_type: str, filters: RetrievalFilters | None
    ) -> bool:
        """Check if layer should be retrieved based on filters.

        Args:
            layer_type: Layer type (semantic, episodic, summary)
            filters: Optional filters

        Returns:
            True if layer should be retrieved
        """
        if not filters or not filters.memory_types:
            return True  # Retrieve all layers by default

        return layer_type in filters.memory_types

    def _semantic_to_candidate(self, memory: SemanticMemory) -> MemoryCandidate:
        """Convert SemanticMemory domain entity to MemoryCandidate.

        Args:
            memory: Semantic memory entity

        Returns:
            Memory candidate for scoring
        """
        # Format content as human-readable triple
        obj_value = memory.object_value
        if isinstance(obj_value, dict):
            obj_value = obj_value.get("value", str(obj_value))

        content = f"{memory.subject_entity_id} {memory.predicate} {obj_value}"

        # Extract entities (subject only for semantic memories)
        entities = [memory.subject_entity_id] if memory.subject_entity_id else []

        return MemoryCandidate(
            memory_id=memory.memory_id,
            memory_type="semantic",
            content=content,
            entities=entities,
            embedding=np.array(memory.embedding) if memory.embedding else np.zeros(1536),
            created_at=memory.created_at,
            importance=0.5,  # Default importance for semantic memories
            confidence=memory.confidence,
            reinforcement_count=memory.reinforcement_count,
            last_validated_at=memory.last_validated_at,
        )

    def _deduplicate_candidates(
        self, candidates: list[MemoryCandidate]
    ) -> list[MemoryCandidate]:
        """Deduplicate candidates by (memory_type, memory_id).

        Args:
            candidates: List of candidates possibly containing duplicates

        Returns:
            Deduplicated list (first occurrence wins)
        """
        seen = set()
        deduplicated = []

        for candidate in candidates:
            key = (candidate.memory_type, candidate.memory_id)
            if key not in seen:
                seen.add(key)
                deduplicated.append(candidate)

        return deduplicated
