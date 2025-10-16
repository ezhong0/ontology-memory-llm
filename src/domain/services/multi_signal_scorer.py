"""Multi-signal relevance scoring for memory retrieval.

This module implements deterministic relevance scoring using 5 signals:
1. Semantic similarity (cosine distance)
2. Entity overlap (Jaccard similarity)
3. Recency (exponential temporal decay)
4. Importance (stored importance score)
5. Reinforcement (validation count)

Vision alignment: Fast, deterministic, explainable scoring (<100ms for 100+ candidates).
NO LLM - must be fast enough to score all candidates in real-time.

Design from: DESIGN.md v2.0 - Multi-Signal Retrieval Algorithm
"""

import math
from datetime import datetime

import numpy as np
import structlog

from src.config import heuristics
from src.domain.services.memory_validation_service import MemoryValidationService
from src.domain.value_objects.memory_candidate import (
    MemoryCandidate,
    ScoredMemory,
    SignalBreakdown,
)
from src.domain.value_objects.query_context import QueryContext

logger = structlog.get_logger()


class MultiSignalScorer:
    """Deterministic multi-signal relevance scoring.

    Scores memory candidates using a weighted combination of 5 signals,
    then applies confidence penalty (passive decay).

    Philosophy: Fast, deterministic, explainable. NO LLM.

    Example:
        >>> scorer = MultiSignalScorer(validation_service)
        >>> candidates = [...]  # List of MemoryCandidate
        >>> query_context = QueryContext(...)
        >>> scored = scorer.score_candidates(candidates, query_context)
        >>> # Returns sorted list (highest score first)
    """

    def __init__(self, validation_service: MemoryValidationService) -> None:
        """Initialize scorer.

        Args:
            validation_service: Service for calculating passive decay
        """
        self._validation_service = validation_service

    def score_candidates(
        self,
        candidates: list[MemoryCandidate],
        query_context: QueryContext,
    ) -> list[ScoredMemory]:
        """Score all candidates using weighted multi-signal formula.

        Args:
            candidates: List of memory candidates to score
            query_context: Query context with embedding and entities

        Returns:
            List of scored memories, sorted by relevance (highest first)
        """
        if not candidates:
            return []

        logger.info(
            "scoring_candidates",
            candidate_count=len(candidates),
            strategy=query_context.strategy,
        )

        # Get weights for retrieval strategy
        weights = heuristics.get_retrieval_weights(query_context.strategy)

        scored_memories = []
        for candidate in candidates:
            scored = self._score_single_candidate(candidate, query_context, weights)
            scored_memories.append(scored)

        # Sort by relevance score (descending)
        scored_memories.sort(key=lambda x: x.relevance_score, reverse=True)

        logger.info(
            "scoring_completed",
            scored_count=len(scored_memories),
            top_score=scored_memories[0].relevance_score if scored_memories else 0.0,
        )

        return scored_memories

    def _score_single_candidate(
        self,
        candidate: MemoryCandidate,
        query_context: QueryContext,
        weights: dict[str, float],
    ) -> ScoredMemory:
        """Score a single candidate.

        Args:
            candidate: Memory candidate to score
            query_context: Query context
            weights: Signal weights for strategy

        Returns:
            Scored memory with signal breakdown
        """
        # Calculate individual signals
        semantic_similarity = self._calculate_semantic_similarity(
            query_context.query_embedding, candidate.embedding
        )

        entity_overlap = self._calculate_entity_overlap(
            query_context.entity_ids, candidate.entities
        )

        recency_score = self._calculate_recency_score(candidate)

        importance_score = candidate.importance

        reinforcement_score = self._calculate_reinforcement_score(candidate)

        # Weighted combination
        relevance = (
            weights["semantic_similarity"] * semantic_similarity
            + weights["entity_overlap"] * entity_overlap
            + weights["temporal_relevance"] * recency_score
            + weights["importance"] * importance_score
            + weights["reinforcement"] * reinforcement_score
        )

        # Calculate effective confidence (passive decay)
        effective_confidence = self._calculate_effective_confidence(candidate)

        # Apply confidence penalty
        final_relevance = relevance * effective_confidence

        # Ensure final score is in [0, 1]
        final_relevance = max(0.0, min(1.0, final_relevance))

        signal_breakdown = SignalBreakdown(
            semantic_similarity=semantic_similarity,
            entity_overlap=entity_overlap,
            recency_score=recency_score,
            importance_score=importance_score,
            reinforcement_score=reinforcement_score,
            effective_confidence=effective_confidence,
        )

        return ScoredMemory(
            candidate=candidate,
            relevance_score=final_relevance,
            signal_breakdown=signal_breakdown,
        )

    def _calculate_semantic_similarity(
        self, query_embedding: np.ndarray, memory_embedding: np.ndarray
    ) -> float:
        """Calculate semantic similarity using cosine similarity.

        Args:
            query_embedding: Query embedding vector (1536-dim)
            memory_embedding: Memory embedding vector (1536-dim)

        Returns:
            Cosine similarity score [0.0, 1.0]
        """
        # Cosine similarity = 1 - cosine_distance
        # cosine_distance = 1 - dot(a, b) / (norm(a) * norm(b))

        dot_product = np.dot(query_embedding, memory_embedding)
        query_norm = np.linalg.norm(query_embedding)
        memory_norm = np.linalg.norm(memory_embedding)

        if query_norm == 0 or memory_norm == 0:
            return 0.0

        cosine_similarity = dot_product / (query_norm * memory_norm)

        # Clamp to [0, 1] (cosine similarity can be [-1, 1], but embeddings are typically [0, 1])
        return max(0.0, min(1.0, cosine_similarity))

    def _calculate_entity_overlap(
        self, query_entities: list[str], memory_entities: list[str]
    ) -> float:
        """Calculate entity overlap using Jaccard similarity.

        Args:
            query_entities: Entity IDs from query
            memory_entities: Entity IDs from memory

        Returns:
            Jaccard similarity [0.0, 1.0]
        """
        if not query_entities and not memory_entities:
            return 0.5  # Neutral score when no entities on either side

        if not query_entities or not memory_entities:
            return 0.0  # No overlap if one side has no entities

        query_set = set(query_entities)
        memory_set = set(memory_entities)

        intersection = query_set & memory_set
        union = query_set | memory_set

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _calculate_recency_score(self, candidate: MemoryCandidate) -> float:
        """Calculate recency score using exponential decay.

        Args:
            candidate: Memory candidate

        Returns:
            Recency score [0.0, 1.0]

        Formula:
            score = exp(-age_days * ln(2) / half_life)

        Half-life:
            - Episodic: 30 days
            - Semantic/Summary: 90 days
        """
        age_days = candidate.age_days

        # Determine half-life based on memory type
        if candidate.is_episodic:
            half_life = heuristics.EPISODIC_HALF_LIFE_DAYS
        else:
            half_life = heuristics.SEMANTIC_HALF_LIFE_DAYS

        # Exponential decay: score = exp(-age * ln(2) / half_life)
        decay_factor = -age_days * math.log(2) / half_life
        recency_score = math.exp(decay_factor)

        return max(0.0, min(1.0, recency_score))

    def _calculate_reinforcement_score(self, candidate: MemoryCandidate) -> float:
        """Calculate reinforcement score from validation count.

        Args:
            candidate: Memory candidate

        Returns:
            Reinforcement score [0.0, 1.0]

        Formula:
            - For semantic memories: min(1.0, reinforcement_count / 5)
            - For others: 0.5 (neutral)
        """
        if candidate.is_semantic and candidate.reinforcement_count is not None:
            # Scale to [0, 1] with saturation at 5 reinforcements
            return min(1.0, candidate.reinforcement_count / 5.0)
        else:
            # Neutral score for non-semantic memories
            return 0.5

    def _calculate_effective_confidence(self, candidate: MemoryCandidate) -> float:
        """Calculate effective confidence with passive decay.

        Args:
            candidate: Memory candidate

        Returns:
            Effective confidence [0.0, 1.0]

        For semantic memories:
            Applies exponential decay formula (same as MemoryValidationService)
        For others:
            Returns 1.0 (full confidence)
        """
        if not candidate.is_semantic or candidate.confidence is None:
            return 1.0  # Full confidence for non-semantic memories

        if candidate.last_validated_at is None:
            # No validation yet, use base confidence
            return candidate.confidence

        # Calculate days since last validation
        now = datetime.now(candidate.last_validated_at.tzinfo)
        days_since_validation = (now - candidate.last_validated_at).total_seconds() / 86400.0

        # Apply exponential decay (same formula as MemoryValidationService)
        # confidence(t) = initial_confidence * exp(-decay_rate * days)
        decay_rate = heuristics.DECAY_RATE_PER_DAY
        decay_factor = math.exp(-decay_rate * days_since_validation)
        effective_confidence = candidate.confidence * decay_factor

        return max(0.0, min(1.0, effective_confidence))
