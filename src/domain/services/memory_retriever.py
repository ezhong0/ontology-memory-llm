"""Memory retrieval service - orchestrates full retrieval pipeline.

This service coordinates:
1. Query embedding
2. Entity resolution
3. Candidate generation (parallel retrieval from all layers)
4. Multi-signal scoring
5. Top-k selection

Design from: DESIGN.md v2.0 - Complete Retrieval Pipeline
"""

import time
from typing import List, Optional
from uuid import UUID

import numpy as np
import structlog

from src.domain.exceptions import DomainError
from src.domain.ports.embedding_service import IEmbeddingService
from src.domain.services.candidate_generator import CandidateGenerator
from src.domain.services.entity_resolution_service import EntityResolutionService
from src.domain.services.multi_signal_scorer import MultiSignalScorer
from src.domain.value_objects.query_context import QueryContext, RetrievalFilters
from src.domain.value_objects.retrieval_result import RetrievalMetadata, RetrievalResult

logger = structlog.get_logger()


class MemoryRetriever:
    """Orchestrates full memory retrieval pipeline.

    Single entry point for memory retrieval. Coordinates embedding,
    entity resolution, candidate generation, and multi-signal scoring.

    Philosophy: Clean orchestration, dependency injection, structured errors.

    Example:
        >>> retriever = MemoryRetriever(
        ...     embedding_service=embedding_service,
        ...     entity_resolver=entity_resolver,
        ...     candidate_generator=candidate_generator,
        ...     scorer=scorer,
        ... )
        >>> result = await retriever.retrieve(
        ...     query="What are Gai Media's delivery preferences?",
        ...     user_id="user_1",
        ...     top_k=20,
        ... )
        >>> # Returns top 20 most relevant memories with provenance
    """

    def __init__(
        self,
        embedding_service: IEmbeddingService,
        entity_resolver: EntityResolutionService,
        candidate_generator: CandidateGenerator,
        scorer: MultiSignalScorer,
    ) -> None:
        """Initialize memory retriever.

        Args:
            embedding_service: Service for generating query embeddings
            entity_resolver: Service for resolving entities from query
            candidate_generator: Service for parallel candidate generation
            scorer: Service for multi-signal relevance scoring
        """
        self._embedding_service = embedding_service
        self._entity_resolver = entity_resolver
        self._candidate_generator = candidate_generator
        self._scorer = scorer

    async def retrieve(
        self,
        query: str,
        user_id: str,
        session_id: Optional[UUID] = None,
        strategy: str = "exploratory",
        top_k: int = 20,
        filters: Optional[RetrievalFilters] = None,
    ) -> RetrievalResult:
        """Retrieve relevant memories for a query.

        Full pipeline:
        1. Embed query
        2. Resolve entities
        3. Generate candidates (parallel retrieval)
        4. Score with multi-signal
        5. Return top-k

        Args:
            query: Query text
            user_id: User identifier
            session_id: Optional session context
            strategy: Retrieval strategy (factual_entity_focused, procedural, exploratory, temporal)
            top_k: Number of top memories to return
            filters: Optional filters for candidate selection

        Returns:
            RetrievalResult with scored memories, query context, and metadata

        Raises:
            DomainError: If retrieval pipeline fails
        """
        start_time = time.perf_counter()

        try:
            logger.info(
                "retrieval_started",
                query=query,
                user_id=user_id,
                strategy=strategy,
                top_k=top_k,
            )

            # Step 1: Embed query
            query_embedding = await self._embedding_service.embed_text(query)
            if not isinstance(query_embedding, np.ndarray):
                query_embedding = np.array(query_embedding)

            # Step 2: Resolve entities from query
            # For Phase 1C, we'll use a simplified approach
            # In production, would extract mentions and resolve each
            entity_ids = await self._resolve_query_entities(query, user_id)

            # Step 3: Build query context
            query_context = QueryContext(
                query_text=query,
                query_embedding=query_embedding,
                entity_ids=entity_ids,
                user_id=user_id,
                session_id=str(session_id) if session_id else None,
                strategy=strategy,
            )

            # Step 4: Generate candidates (parallel retrieval from all layers)
            candidates = await self._candidate_generator.generate_candidates(
                query_context=query_context,
                filters=filters,
            )

            if not candidates:
                logger.warning(
                    "no_candidates_found",
                    query=query,
                    user_id=user_id,
                )
                return RetrievalResult(
                    memories=[],
                    query_context=query_context,
                    metadata=RetrievalMetadata(
                        candidates_generated=0,
                        candidates_scored=0,
                        top_score=0.0,
                        retrieval_time_ms=(time.perf_counter() - start_time) * 1000,
                    ),
                )

            # Step 5: Score all candidates with multi-signal
            scored_memories = self._scorer.score_candidates(
                candidates=candidates,
                query_context=query_context,
            )

            # Step 6: Select top-k
            top_memories = scored_memories[:top_k]

            # Calculate metadata
            end_time = time.perf_counter()
            retrieval_time_ms = (end_time - start_time) * 1000

            metadata = RetrievalMetadata(
                candidates_generated=len(candidates),
                candidates_scored=len(scored_memories),
                top_score=top_memories[0].relevance_score if top_memories else 0.0,
                retrieval_time_ms=retrieval_time_ms,
            )

            logger.info(
                "retrieval_completed",
                user_id=user_id,
                candidates_generated=len(candidates),
                top_k_count=len(top_memories),
                top_score=metadata.top_score,
                retrieval_time_ms=retrieval_time_ms,
            )

            return RetrievalResult(
                memories=top_memories,
                query_context=query_context,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(
                "retrieval_error",
                query=query,
                user_id=user_id,
                error=str(e),
            )
            raise DomainError(f"Error retrieving memories: {e}") from e

    async def _resolve_query_entities(self, query: str, user_id: str) -> List[str]:
        """Resolve entities from query text.

        Simplified implementation for Phase 1C.
        In production, would use mention extraction + full resolution.

        Args:
            query: Query text
            user_id: User identifier

        Returns:
            List of resolved entity IDs
        """
        # TODO: Implement full entity resolution pipeline
        # For now, return empty list - will be enhanced in integration
        return []
