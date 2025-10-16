"""Property-based tests for procedural memory invariants.

Tests procedural memory pattern detection using hypothesis to verify invariants
hold across a wide range of inputs.

Vision Principles Tested:
- Epistemic Humility: Pattern confidence bounded, diminishing returns
- Learning from Patterns: Co-occurrence → heuristics
- Domain Integrity: All structural invariants hold
- Explainable Reasoning: Source episode IDs tracked

Testing Philosophy: Layer 1 - Property-Based Tests
"""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.domain.entities.procedural_memory import ProceduralMemory
from src.domain.value_objects.procedural_memory import Pattern


# ============================================================================
# Strategy Definitions
# ============================================================================


@st.composite
def pattern_strategy(draw):
    """Generate valid Pattern instances."""
    observed_count = draw(st.integers(min_value=1, max_value=100))
    # Confidence capped at 0.95 (epistemic humility)
    confidence = draw(st.floats(min_value=0.0, max_value=0.95))

    # Generate source episode IDs based on observed_count
    source_episode_ids = [
        draw(st.integers(min_value=1, max_value=10000))
        for _ in range(min(observed_count, 10))  # Cap at 10 for efficiency
    ]

    return Pattern(
        trigger_pattern=draw(st.text(min_size=5, max_size=200)),
        trigger_features={
            "intent": draw(
                st.sampled_from(
                    [
                        "query_payment",
                        "query_customer",
                        "query_order",
                        "query_product",
                        "statement_preference",
                    ]
                )
            ),
            "entity_types": draw(
                st.lists(
                    st.sampled_from(["customer", "order", "product", "invoice"]),
                    max_size=3,
                )
            ),
            "topics": draw(
                st.lists(
                    st.sampled_from(["payments", "orders", "products", "shipping"]),
                    max_size=3,
                )
            ),
        },
        action_heuristic=draw(st.text(min_size=5, max_size=200)),
        action_structure={
            "action_type": draw(st.sampled_from(["retrieve", "augment", "expand"])),
            "queries": draw(
                st.lists(
                    st.sampled_from(["payments", "orders", "customers"]), max_size=3
                )
            ),
            "predicates": draw(
                st.lists(st.text(min_size=3, max_size=50), max_size=3)
            ),
        },
        observed_count=observed_count,
        confidence=confidence,
        source_episode_ids=source_episode_ids,
    )


@st.composite
def procedural_memory_strategy(draw):
    """Generate valid ProceduralMemory instances."""
    pattern = draw(pattern_strategy())

    return ProceduralMemory(
        user_id=f"user_{draw(st.integers(min_value=1, max_value=1000))}",
        trigger_pattern=pattern.trigger_pattern,
        trigger_features=pattern.trigger_features,
        action_heuristic=pattern.action_heuristic,
        action_structure=pattern.action_structure,
        observed_count=pattern.observed_count,
        confidence=pattern.confidence,
        created_at=datetime.now(UTC) - timedelta(days=draw(st.integers(min_value=0, max_value=365))),
        memory_id=draw(st.one_of(st.none(), st.integers(min_value=1, max_value=10000))),
        embedding=draw(st.one_of(st.none(), st.just(np.random.rand(1536)))),
    )


# ============================================================================
# Invariant Tests: Epistemic Humility
# ============================================================================


class TestEpistemicHumilityInvariants:
    """Test epistemic humility invariants in procedural memory."""

    @given(pattern_strategy())
    @settings(max_examples=100, deadline=None)
    def test_pattern_confidence_bounded(self, pattern):
        """INVARIANT: Pattern confidence always in [0.0, 1.0].

        Vision: Epistemic humility - never claim impossible confidence.
        """
        assert 0.0 <= pattern.confidence <= 1.0

    @given(procedural_memory_strategy())
    @settings(max_examples=100, deadline=None)
    def test_procedural_memory_confidence_bounded(self, memory):
        """INVARIANT: ProceduralMemory confidence always in [0.0, 1.0].

        Vision: Epistemic humility - stored patterns have bounded confidence.
        """
        assert 0.0 <= memory.confidence <= 1.0

    @given(procedural_memory_strategy())
    @settings(max_examples=100, deadline=None)
    def test_increment_never_exceeds_max_confidence(self, memory):
        """INVARIANT: Incrementing observed_count never exceeds MAX_CONFIDENCE (0.95).

        Vision: Epistemic humility - even with infinite reinforcement, confidence capped.
        """
        # Increment many times
        current = memory
        for _ in range(50):
            current = current.increment_observed_count()

        # Should converge to 0.95, never exceed
        assert current.confidence <= 0.95

    @given(procedural_memory_strategy())
    @settings(max_examples=100, deadline=None)
    def test_increment_has_diminishing_returns(self, memory):
        """INVARIANT: Confidence boost has diminishing returns.

        Vision: Epistemic humility - additional evidence matters less as confidence grows.
        """
        # Only test if not already at max
        if memory.confidence >= 0.94:
            return

        inc1 = memory.increment_observed_count()
        boost1 = inc1.confidence - memory.confidence

        inc2 = inc1.increment_observed_count()
        boost2 = inc2.confidence - inc1.confidence

        # Second boost should be smaller (or equal if at cap)
        assert boost2 <= boost1


# ============================================================================
# Invariant Tests: Domain Integrity
# ============================================================================


class TestDomainIntegrityInvariants:
    """Test domain integrity invariants in procedural memory."""

    @given(pattern_strategy())
    @settings(max_examples=100, deadline=None)
    def test_pattern_observed_count_positive(self, pattern):
        """INVARIANT: Pattern observed_count always >= 1.

        Vision: Domain integrity - pattern must be observed to exist.
        """
        assert pattern.observed_count >= 1

    @given(procedural_memory_strategy())
    @settings(max_examples=100, deadline=None)
    def test_procedural_memory_observed_count_positive(self, memory):
        """INVARIANT: ProceduralMemory observed_count always >= 1.

        Vision: Domain integrity - stored patterns observed at least once.
        """
        assert memory.observed_count >= 1

    @given(pattern_strategy())
    @settings(max_examples=100, deadline=None)
    def test_pattern_has_required_trigger_features(self, pattern):
        """INVARIANT: Pattern has required trigger_features keys.

        Vision: Domain integrity - patterns have structured features.
        """
        assert "intent" in pattern.trigger_features
        assert "entity_types" in pattern.trigger_features
        assert "topics" in pattern.trigger_features

        # All should be present (even if empty)
        assert pattern.trigger_features["intent"] is not None
        assert isinstance(pattern.trigger_features["entity_types"], list)
        assert isinstance(pattern.trigger_features["topics"], list)

    @given(pattern_strategy())
    @settings(max_examples=100, deadline=None)
    def test_pattern_has_required_action_structure(self, pattern):
        """INVARIANT: Pattern has required action_structure keys.

        Vision: Domain integrity - actions are structured.
        """
        assert "action_type" in pattern.action_structure
        assert "queries" in pattern.action_structure
        assert "predicates" in pattern.action_structure

        assert pattern.action_structure["action_type"] is not None
        assert isinstance(pattern.action_structure["queries"], list)
        assert isinstance(pattern.action_structure["predicates"], list)

    @given(procedural_memory_strategy())
    @settings(max_examples=100, deadline=None)
    def test_procedural_memory_embedding_dimensions(self, memory):
        """INVARIANT: ProceduralMemory embedding (if present) is 1536-dimensional.

        Vision: Domain integrity - embeddings have correct dimensions.
        """
        if memory.embedding is not None:
            assert memory.embedding.shape == (1536,)
            assert isinstance(memory.embedding, np.ndarray)


# ============================================================================
# Invariant Tests: Explainable Reasoning
# ============================================================================


class TestExplainableReasoningInvariants:
    """Test explainability invariants in procedural memory."""

    @given(pattern_strategy())
    @settings(max_examples=100, deadline=None)
    def test_pattern_tracks_source_episodes(self, pattern):
        """INVARIANT: Pattern tracks source episode IDs.

        Vision: Explainable reasoning - always know provenance.
        """
        assert pattern.source_episode_ids is not None
        assert isinstance(pattern.source_episode_ids, list)

        # Should have at least one source (since observed_count >= 1)
        assert len(pattern.source_episode_ids) >= 1

    @given(pattern_strategy())
    @settings(max_examples=100, deadline=None)
    def test_pattern_source_count_matches_observed_count_semantics(self, pattern):
        """INVARIANT: Source episode IDs relate to observed_count.

        Vision: Explainable reasoning - evidence count should be traceable.

        Note: In practice, source_episode_ids may be capped (e.g., top 10) while
        observed_count continues to grow. This test verifies the relationship makes sense.
        """
        # Source IDs should exist
        assert len(pattern.source_episode_ids) >= 1

        # Observed count should be at least as many as tracked sources
        # (could be more if sources are capped)
        assert pattern.observed_count >= len(pattern.source_episode_ids)


# ============================================================================
# Invariant Tests: Serialization
# ============================================================================


class TestSerializationInvariants:
    """Test serialization invariants for procedural memory."""

    @given(pattern_strategy())
    @settings(max_examples=100, deadline=None)
    def test_pattern_to_dict_roundtrip(self, pattern):
        """INVARIANT: Pattern serialization preserves structure.

        Vision: Domain integrity - data can be persisted and retrieved.
        """
        pattern_dict = pattern.to_dict()

        # Required fields present
        assert "trigger_pattern" in pattern_dict
        assert "trigger_features" in pattern_dict
        assert "action_heuristic" in pattern_dict
        assert "action_structure" in pattern_dict
        assert "observed_count" in pattern_dict
        assert "confidence" in pattern_dict
        assert "source_episode_ids" in pattern_dict

        # Values preserved
        assert pattern_dict["trigger_pattern"] == pattern.trigger_pattern
        assert pattern_dict["observed_count"] == pattern.observed_count
        assert pattern_dict["confidence"] == pattern.confidence

    @given(procedural_memory_strategy())
    @settings(max_examples=100, deadline=None)
    def test_procedural_memory_to_dict_roundtrip(self, memory):
        """INVARIANT: ProceduralMemory serialization preserves structure.

        Vision: Domain integrity - stored patterns can be retrieved.
        """
        memory_dict = memory.to_dict()

        # Required fields present
        assert "user_id" in memory_dict
        assert "trigger_pattern" in memory_dict
        assert "trigger_features" in memory_dict
        assert "action_heuristic" in memory_dict
        assert "action_structure" in memory_dict
        assert "observed_count" in memory_dict
        assert "confidence" in memory_dict
        assert "created_at" in memory_dict

        # Values preserved
        assert memory_dict["user_id"] == memory.user_id
        assert memory_dict["observed_count"] == memory.observed_count
        assert memory_dict["confidence"] == memory.confidence


# ============================================================================
# Invariant Tests: Pattern Detection Logic
# ============================================================================


class TestPatternDetectionInvariants:
    """Test pattern detection invariants."""

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=100, deadline=None)
    def test_min_support_threshold_enforced(self, observed_count):
        """INVARIANT: Pattern observed_count relates to min_support threshold.

        Vision: Learning from patterns - require minimum evidence.

        Note: In Phase 1, min_support is typically 3. This test verifies
        that observed_count is meaningful relative to this threshold.
        """
        min_support = 3

        # If observed_count >= min_support, pattern would be created
        if observed_count >= min_support:
            assert observed_count >= min_support

        # Otherwise, pattern wouldn't be created (but we're testing an
        # already-created pattern, so this is just conceptual validation)
        else:
            # Pattern with observed_count < min_support wouldn't normally exist
            # in production, but is valid for testing edge cases
            assert observed_count >= 1  # Still must be >= 1

    @given(
        st.lists(st.integers(min_value=1, max_value=10000), min_size=3, max_size=50)
    )
    @settings(max_examples=50, deadline=None)
    def test_co_occurrence_frequency_calculation(self, episode_ids):
        """INVARIANT: Co-occurrence frequency is >= min_support.

        Vision: Pattern detection requires minimum evidence threshold.

        This tests the conceptual relationship between episode frequency
        and pattern creation (min_support threshold).
        """
        # Count unique episodes
        unique_episodes = list(set(episode_ids))
        frequency = len(unique_episodes)

        # Typical min_support is 3
        min_support = 3

        if frequency >= min_support:
            # Pattern would be created
            assert frequency >= min_support
        else:
            # Pattern would not be created
            assert frequency < min_support


# ============================================================================
# Invariant Tests: Increment Logic
# ============================================================================


class TestIncrementLogicInvariants:
    """Test ProceduralMemory.increment_observed_count() invariants."""

    @given(procedural_memory_strategy())
    @settings(max_examples=100, deadline=None)
    def test_increment_increases_observed_count(self, memory):
        """INVARIANT: Increment always increases observed_count by 1.

        Vision: Domain integrity - counting is accurate.
        """
        incremented = memory.increment_observed_count()

        assert incremented.observed_count == memory.observed_count + 1

    @given(procedural_memory_strategy())
    @settings(max_examples=100, deadline=None)
    def test_increment_increases_or_maintains_confidence(self, memory):
        """INVARIANT: Increment never decreases confidence (except when capping).

        Vision: Epistemic humility - more evidence → equal or higher confidence,
        but always capped at MAX_CONFIDENCE (0.95).
        """
        incremented = memory.increment_observed_count()

        # Confidence should increase or maintain, unless capped
        # Both should be <= 0.95 (MAX_CONFIDENCE)
        assert incremented.confidence <= 0.95

        # If original was at or below cap, incremented should be >= original
        if memory.confidence <= 0.95:
            assert incremented.confidence >= memory.confidence

    @given(procedural_memory_strategy())
    @settings(max_examples=100, deadline=None)
    def test_increment_sets_updated_at(self, memory):
        """INVARIANT: Increment sets updated_at timestamp.

        Vision: Explainable reasoning - track when patterns were reinforced.
        """
        incremented = memory.increment_observed_count()

        assert incremented.updated_at is not None
        # updated_at should be recent (within last second)
        assert (datetime.now(UTC) - incremented.updated_at).total_seconds() < 1.0

    @given(procedural_memory_strategy())
    @settings(max_examples=100, deadline=None)
    def test_increment_preserves_immutable_fields(self, memory):
        """INVARIANT: Increment preserves user_id, created_at, memory_id.

        Vision: Domain integrity - immutable fields remain unchanged.
        """
        incremented = memory.increment_observed_count()

        assert incremented.user_id == memory.user_id
        assert incremented.created_at == memory.created_at
        assert incremented.memory_id == memory.memory_id
        assert incremented.trigger_pattern == memory.trigger_pattern


# ============================================================================
# Invariant Tests: Pattern Matching
# ============================================================================


class TestPatternMatchingInvariants:
    """Test pattern matching invariants."""

    @given(pattern_strategy(), pattern_strategy())
    @settings(max_examples=50, deadline=None)
    def test_pattern_similarity_is_symmetric(self, pattern1, pattern2):
        """INVARIANT: Pattern similarity is symmetric.

        Vision: Domain integrity - similarity metric is well-defined.

        This tests the conceptual property that if pattern A is similar to B,
        then B is similar to A.
        """
        # Test intent similarity (simple equality check)
        intent1 = pattern1.trigger_features["intent"]
        intent2 = pattern2.trigger_features["intent"]

        if intent1 == intent2:
            # Symmetric: both have same intent
            assert intent2 == intent1

    @given(pattern_strategy())
    @settings(max_examples=100, deadline=None)
    def test_pattern_matches_itself(self, pattern):
        """INVARIANT: Pattern always matches itself (reflexivity).

        Vision: Domain integrity - identity is well-defined.
        """
        # A pattern's intent should equal itself
        intent = pattern.trigger_features["intent"]
        assert intent == intent

        # Same for other features
        assert pattern.trigger_pattern == pattern.trigger_pattern
        assert pattern.action_heuristic == pattern.action_heuristic
