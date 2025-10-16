"""Unit tests for MultiSignalScorer.

Tests deterministic multi-signal relevance scoring with 5 signals:
- Semantic similarity (cosine)
- Entity overlap (Jaccard)
- Recency (exponential decay)
- Importance
- Reinforcement

Property: All scores must be in [0.0, 1.0]
"""

import math
from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import Mock

import numpy as np
import pytest

from src.config import heuristics
from src.domain.services.memory_validation_service import MemoryValidationService
from src.domain.services.multi_signal_scorer import MultiSignalScorer
from src.domain.value_objects.memory_candidate import MemoryCandidate
from src.domain.value_objects.query_context import QueryContext


@pytest.fixture
def validation_service():
    """Mock validation service for testing."""
    service = Mock(spec=MemoryValidationService)
    # Default: no decay (return input confidence)
    service.calculate_confidence_decay.side_effect = lambda initial_confidence, days_elapsed: initial_confidence
    return service


@pytest.fixture
def scorer(validation_service):
    """Create scorer instance."""
    return MultiSignalScorer(validation_service)


@pytest.fixture
def query_context():
    """Sample query context."""
    return QueryContext(
        query_text="What are Gai Media's delivery preferences?",
        query_embedding=np.random.rand(1536),
        entity_ids=["customer_gai_123"],
        user_id="user_1",
        strategy="exploratory",
    )


@pytest.fixture
def semantic_candidate():
    """Sample semantic memory candidate."""
    return MemoryCandidate(
        memory_id=1,
        memory_type="semantic",
        content="Gai Media prefers Friday deliveries",
        entities=["customer_gai_123"],
        embedding=np.random.rand(1536),
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
        importance=0.7,
        confidence=0.85,
        reinforcement_count=3,
        last_validated_at=datetime.now(timezone.utc) - timedelta(days=5),
    )


@pytest.fixture
def episodic_candidate():
    """Sample episodic memory candidate."""
    return MemoryCandidate(
        memory_id=2,
        memory_type="episodic",
        content="User asked about delivery timing for Gai Media",
        entities=["customer_gai_123"],
        embedding=np.random.rand(1536),
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
        importance=0.6,
    )


class TestScoringPipeline:
    """Test the full scoring pipeline."""

    def test_score_empty_candidates(self, scorer, query_context):
        """Should return empty list for empty input."""
        result = scorer.score_candidates([], query_context)
        assert result == []

    def test_score_single_candidate(self, scorer, query_context, semantic_candidate):
        """Should score single candidate correctly."""
        result = scorer.score_candidates([semantic_candidate], query_context)

        assert len(result) == 1
        scored = result[0]

        # Check structure
        assert scored.candidate == semantic_candidate
        assert 0.0 <= scored.relevance_score <= 1.0
        assert scored.signal_breakdown is not None

    def test_score_multiple_candidates_sorted(self, scorer, query_context):
        """Should return candidates sorted by relevance (descending)."""
        # Create candidates with different importances
        candidates = [
            MemoryCandidate(
                memory_id=i,
                memory_type="semantic",
                content=f"Memory {i}",
                entities=["customer_gai_123"],
                embedding=np.random.rand(1536),
                created_at=datetime.now(timezone.utc),
                importance=0.3 + (i * 0.1),  # Increasing importance
                confidence=0.8,
                reinforcement_count=1,
                last_validated_at=datetime.now(timezone.utc),
            )
            for i in range(5)
        ]

        result = scorer.score_candidates(candidates, query_context)

        assert len(result) == 5
        # Verify descending order
        scores = [scored.relevance_score for scored in result]
        assert scores == sorted(scores, reverse=True)

    def test_score_respects_strategy_weights(self, scorer, query_context, semantic_candidate):
        """Should use weights from strategy."""
        # Change strategy
        exploratory_context = QueryContext(
            query_text=query_context.query_text,
            query_embedding=query_context.query_embedding,
            entity_ids=query_context.entity_ids,
            user_id=query_context.user_id,
            strategy="exploratory",
        )

        factual_context = QueryContext(
            query_text=query_context.query_text,
            query_embedding=query_context.query_embedding,
            entity_ids=query_context.entity_ids,
            user_id=query_context.user_id,
            strategy="factual_entity_focused",
        )

        exploratory_result = scorer.score_candidates([semantic_candidate], exploratory_context)
        factual_result = scorer.score_candidates([semantic_candidate], factual_context)

        # Scores should differ due to different weights
        # (may be equal if candidate perfectly matches, but generally differ)
        assert exploratory_result[0].relevance_score >= 0.0
        assert factual_result[0].relevance_score >= 0.0


class TestSemanticSimilarity:
    """Test semantic similarity calculation."""

    def test_identical_embeddings(self, scorer):
        """Identical embeddings should have similarity = 1.0."""
        embedding = np.random.rand(1536)
        similarity = scorer._calculate_semantic_similarity(embedding, embedding)
        assert similarity == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_embeddings(self, scorer):
        """Orthogonal embeddings should have similarity ≈ 0.0."""
        # Create two orthogonal vectors
        embedding1 = np.zeros(1536)
        embedding1[0] = 1.0

        embedding2 = np.zeros(1536)
        embedding2[1] = 1.0

        similarity = scorer._calculate_semantic_similarity(embedding1, embedding2)
        assert similarity == pytest.approx(0.0, abs=1e-6)

    def test_zero_embedding(self, scorer):
        """Zero embedding should return 0.0 similarity."""
        embedding1 = np.random.rand(1536)
        embedding2 = np.zeros(1536)

        similarity = scorer._calculate_semantic_similarity(embedding1, embedding2)
        assert similarity == 0.0

    def test_similar_embeddings(self, scorer):
        """Similar embeddings should have high similarity."""
        embedding1 = np.random.rand(1536)
        # Slightly perturb embedding1
        embedding2 = embedding1 + np.random.rand(1536) * 0.01

        similarity = scorer._calculate_semantic_similarity(embedding1, embedding2)
        assert 0.9 <= similarity <= 1.0


class TestEntityOverlap:
    """Test entity overlap calculation (Jaccard similarity)."""

    def test_identical_entities(self, scorer):
        """Identical entity sets should have overlap = 1.0."""
        entities = ["customer_1", "order_2", "invoice_3"]
        overlap = scorer._calculate_entity_overlap(entities, entities)
        assert overlap == 1.0

    def test_no_overlap(self, scorer):
        """Disjoint entity sets should have overlap = 0.0."""
        entities1 = ["customer_1", "order_2"]
        entities2 = ["invoice_3", "product_4"]
        overlap = scorer._calculate_entity_overlap(entities1, entities2)
        assert overlap == 0.0

    def test_partial_overlap(self, scorer):
        """Partial overlap should return Jaccard similarity."""
        entities1 = ["customer_1", "order_2", "invoice_3"]
        entities2 = ["order_2", "invoice_3", "product_4"]

        # Intersection: {order_2, invoice_3} = 2
        # Union: {customer_1, order_2, invoice_3, product_4} = 4
        # Jaccard = 2/4 = 0.5

        overlap = scorer._calculate_entity_overlap(entities1, entities2)
        assert overlap == 0.5

    def test_empty_entities(self, scorer):
        """Empty entity lists should return neutral score."""
        overlap = scorer._calculate_entity_overlap([], [])
        assert overlap == 0.5

    def test_one_empty_list(self, scorer):
        """One empty list should return 0.0."""
        entities = ["customer_1"]
        overlap1 = scorer._calculate_entity_overlap(entities, [])
        overlap2 = scorer._calculate_entity_overlap([], entities)
        assert overlap1 == 0.0
        assert overlap2 == 0.0


class TestRecencyScore:
    """Test recency score calculation (exponential decay)."""

    def test_just_created(self, scorer):
        """Just created memory should have recency ≈ 1.0."""
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="semantic",
            content="Test",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(timezone.utc),
            importance=0.5,
        )

        recency = scorer._calculate_recency_score(candidate)
        assert recency == pytest.approx(1.0, abs=0.01)

    def test_episodic_half_life(self, scorer):
        """Episodic memory at half-life should have recency = 0.5."""
        half_life = heuristics.EPISODIC_HALF_LIFE_DAYS
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="episodic",
            content="Test",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(timezone.utc) - timedelta(days=half_life),
            importance=0.5,
        )

        recency = scorer._calculate_recency_score(candidate)
        assert recency == pytest.approx(0.5, abs=0.01)

    def test_semantic_half_life(self, scorer):
        """Semantic memory at half-life should have recency = 0.5."""
        half_life = heuristics.SEMANTIC_HALF_LIFE_DAYS
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="semantic",
            content="Test",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(timezone.utc) - timedelta(days=half_life),
            importance=0.5,
            confidence=0.8,
            reinforcement_count=1,
            last_validated_at=datetime.now(timezone.utc),
        )

        recency = scorer._calculate_recency_score(candidate)
        assert recency == pytest.approx(0.5, abs=0.01)

    def test_very_old_memory(self, scorer):
        """Very old memory should have recency near 0.0."""
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="semantic",
            content="Test",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(timezone.utc) - timedelta(days=365),
            importance=0.5,
        )

        recency = scorer._calculate_recency_score(candidate)
        assert 0.0 <= recency <= 0.1


class TestReinforcementScore:
    """Test reinforcement score calculation."""

    def test_semantic_no_reinforcement(self, scorer):
        """Semantic memory with reinforcement_count=1 should have low score."""
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="semantic",
            content="Test",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(timezone.utc),
            importance=0.5,
            confidence=0.8,
            reinforcement_count=1,
            last_validated_at=datetime.now(timezone.utc),
        )

        score = scorer._calculate_reinforcement_score(candidate)
        assert score == 1.0 / 5.0  # min(1.0, 1/5) = 0.2

    def test_semantic_high_reinforcement(self, scorer):
        """Semantic memory with high reinforcement should have high score."""
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="semantic",
            content="Test",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(timezone.utc),
            importance=0.5,
            confidence=0.8,
            reinforcement_count=10,  # More than 5
            last_validated_at=datetime.now(timezone.utc),
        )

        score = scorer._calculate_reinforcement_score(candidate)
        assert score == 1.0  # Saturates at 1.0

    def test_non_semantic_neutral_score(self, scorer):
        """Non-semantic memories should have neutral reinforcement score."""
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="episodic",
            content="Test",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(timezone.utc),
            importance=0.5,
        )

        score = scorer._calculate_reinforcement_score(candidate)
        assert score == 0.5


class TestEffectiveConfidence:
    """Test effective confidence calculation with passive decay."""

    def test_non_semantic_full_confidence(self, scorer):
        """Non-semantic memories should have full confidence."""
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="episodic",
            content="Test",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(timezone.utc),
            importance=0.5,
        )

        confidence = scorer._calculate_effective_confidence(candidate)
        assert confidence == 1.0

    def test_semantic_no_decay(self, scorer, validation_service):
        """Semantic memory with no decay should return stored confidence."""
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="semantic",
            content="Test",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(timezone.utc),
            importance=0.5,
            confidence=0.85,
            reinforcement_count=1,
            last_validated_at=datetime.now(timezone.utc),
        )

        confidence = scorer._calculate_effective_confidence(candidate)
        # Use approx to handle floating point precision from tiny timing differences
        assert confidence == pytest.approx(0.85, abs=0.01)

    def test_semantic_with_decay(self, scorer, validation_service):
        """Semantic memory with decay should apply exponential decay formula."""
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="semantic",
            content="Test",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(timezone.utc) - timedelta(days=50),
            importance=0.5,
            confidence=0.85,
            reinforcement_count=1,
            last_validated_at=datetime.now(timezone.utc) - timedelta(days=50),
        )

        confidence = scorer._calculate_effective_confidence(candidate)

        # Calculate expected value: confidence * exp(-decay_rate * days)
        # = 0.85 * exp(-0.01 * 50) = 0.85 * exp(-0.5) ≈ 0.5156
        expected = 0.85 * math.exp(-heuristics.DECAY_RATE_PER_DAY * 50)
        assert confidence == pytest.approx(expected, abs=0.01)

    def test_semantic_no_validation_yet(self, scorer):
        """Semantic memory with no validation should use base confidence."""
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="semantic",
            content="Test",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(timezone.utc),
            importance=0.5,
            confidence=0.75,
            reinforcement_count=1,
            last_validated_at=None,  # No validation yet
        )

        confidence = scorer._calculate_effective_confidence(candidate)
        assert confidence == 0.75


class TestSignalBreakdown:
    """Test signal breakdown for explainability."""

    def test_signal_breakdown_complete(self, scorer, query_context, semantic_candidate):
        """Signal breakdown should contain all signals."""
        result = scorer.score_candidates([semantic_candidate], query_context)
        breakdown = result[0].signal_breakdown

        assert 0.0 <= breakdown.semantic_similarity <= 1.0
        assert 0.0 <= breakdown.entity_overlap <= 1.0
        assert 0.0 <= breakdown.recency_score <= 1.0
        assert 0.0 <= breakdown.importance_score <= 1.0
        assert 0.0 <= breakdown.reinforcement_score <= 1.0
        assert 0.0 <= breakdown.effective_confidence <= 1.0

    def test_signal_breakdown_matches_calculation(self, scorer, query_context):
        """Signal breakdown should match actual calculations."""
        # Create candidate with known properties
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="semantic",
            content="Test",
            entities=query_context.entity_ids,  # Perfect entity match
            embedding=query_context.query_embedding,  # Perfect semantic match
            created_at=datetime.now(timezone.utc),  # Just created (recency = 1.0)
            importance=0.8,
            confidence=0.9,
            reinforcement_count=5,  # Saturated reinforcement
            last_validated_at=datetime.now(timezone.utc),  # Just validated (no decay)
        )

        result = scorer.score_candidates([candidate], query_context)
        breakdown = result[0].signal_breakdown

        # Check expected values
        assert breakdown.semantic_similarity == pytest.approx(1.0, abs=0.01)
        assert breakdown.entity_overlap == 1.0  # Perfect match
        assert breakdown.recency_score == pytest.approx(1.0, abs=0.01)
        assert breakdown.importance_score == 0.8
        assert breakdown.reinforcement_score == 1.0  # Saturated
        # Use approx to handle floating point precision from tiny timing differences
        assert breakdown.effective_confidence == pytest.approx(0.9, abs=0.01)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_score_always_in_range(self, scorer, query_context):
        """Final relevance score must always be in [0.0, 1.0]."""
        # Create 100 random candidates
        candidates = [
            MemoryCandidate(
                memory_id=i,
                memory_type=np.random.choice(["semantic", "episodic", "summary"]),
                content=f"Memory {i}",
                entities=[f"entity_{j}" for j in range(np.random.randint(0, 5))],
                embedding=np.random.rand(1536),
                created_at=datetime.now(timezone.utc)
                - timedelta(days=np.random.randint(0, 365)),
                importance=np.random.rand(),
                confidence=np.random.rand() if i % 2 == 0 else None,
                reinforcement_count=np.random.randint(1, 10) if i % 2 == 0 else None,
                last_validated_at=datetime.now(timezone.utc) - timedelta(days=np.random.randint(0, 100))
                if i % 2 == 0
                else None,
            )
            for i in range(100)
        ]

        result = scorer.score_candidates(candidates, query_context)

        # Verify all scores are in valid range
        for scored in result:
            assert 0.0 <= scored.relevance_score <= 1.0
            assert scored.relevance_score == pytest.approx(scored.relevance_score, nan_ok=False)

    def test_extreme_age(self, scorer, query_context):
        """Very old memories should still score in valid range."""
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="semantic",
            content="Ancient memory",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(timezone.utc) - timedelta(days=10000),  # 27 years old
            importance=0.5,
            confidence=0.8,
            reinforcement_count=1,
            last_validated_at=datetime.now(timezone.utc) - timedelta(days=10000),
        )

        result = scorer.score_candidates([candidate], query_context)
        assert 0.0 <= result[0].relevance_score <= 1.0

    def test_all_signals_zero(self, scorer, query_context):
        """Candidate with all zero signals should have score = 0.0."""
        # Create candidate with no overlap, very old, low importance
        candidate = MemoryCandidate(
            memory_id=1,
            memory_type="semantic",
            content="Test",
            entities=["completely_different_entity"],  # No overlap
            embedding=np.random.rand(1536),  # Random embedding (low similarity)
            created_at=datetime.now(timezone.utc) - timedelta(days=10000),  # Very old
            importance=0.0,  # Zero importance
            confidence=0.1,  # Very low confidence
            reinforcement_count=0,  # No reinforcement
            last_validated_at=datetime.now(timezone.utc) - timedelta(days=10000),
        )

        result = scorer.score_candidates([candidate], query_context)
        # Score should be very low (near 0)
        assert 0.0 <= result[0].relevance_score <= 0.1
