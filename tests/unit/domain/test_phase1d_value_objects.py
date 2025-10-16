"""Unit tests for Phase 1D value objects.

Tests validation logic and business rules for:
- Pattern (from procedural_memory.py)
- ProceduralMemory (from procedural_memory.py)
- ConsolidationScope (from consolidation.py)
- SummaryData (from consolidation.py)
- KeyFact (from consolidation.py)

Vision Principles Tested:
- Epistemic humility: Confidence bounds, MAX_CONFIDENCE enforcement
- Domain integrity: Validation of required fields
"""

from datetime import UTC, datetime

import numpy as np
import pytest

from src.domain.entities.procedural_memory import ProceduralMemory
from src.domain.value_objects.consolidation import (
    ConsolidationScope,
    KeyFact,
    SummaryData,
)
from src.domain.value_objects.procedural_memory import Pattern


# ============================================================================
# Pattern Value Object Tests
# ============================================================================


class TestPattern:
    """Test Pattern value object."""

    def test_pattern_creation_valid(self):
        """Should create pattern with valid data."""
        pattern = Pattern(
            trigger_pattern="User asks about payments",
            trigger_features={
                "intent": "query_payment",
                "entity_types": ["customer"],
                "topics": ["payments"],
            },
            action_heuristic="Retrieve payment history",
            action_structure={
                "action_type": "retrieve",
                "queries": ["payments"],
                "predicates": ["has_payment"],
            },
            observed_count=5,
            confidence=0.85,
            source_episode_ids=[1, 2, 3, 4, 5],
        )

        assert pattern.trigger_pattern == "User asks about payments"
        assert pattern.confidence == 0.85
        assert pattern.observed_count == 5

    def test_pattern_confidence_bounds(self):
        """Should validate confidence in [0.0, 1.0]."""
        # Valid confidence
        pattern = Pattern(
            trigger_pattern="Test",
            trigger_features={"intent": "test", "entity_types": [], "topics": []},
            action_heuristic="Test",
            action_structure={"action_type": "test", "queries": [], "predicates": []},
            observed_count=1,
            confidence=0.5,
            source_episode_ids=[1],
        )
        assert pattern.confidence == 0.5

        # Invalid: confidence > 1.0
        with pytest.raises(ValueError, match="confidence must be in"):
            Pattern(
                trigger_pattern="Test",
                trigger_features={"intent": "test", "entity_types": [], "topics": []},
                action_heuristic="Test",
                action_structure={
                    "action_type": "test",
                    "queries": [],
                    "predicates": [],
                },
                observed_count=1,
                confidence=1.5,
                source_episode_ids=[1],
            )

        # Invalid: confidence < 0.0
        with pytest.raises(ValueError, match="confidence must be in"):
            Pattern(
                trigger_pattern="Test",
                trigger_features={"intent": "test", "entity_types": [], "topics": []},
                action_heuristic="Test",
                action_structure={
                    "action_type": "test",
                    "queries": [],
                    "predicates": [],
                },
                observed_count=1,
                confidence=-0.1,
                source_episode_ids=[1],
            )

    def test_pattern_observed_count_positive(self):
        """Should require observed_count >= 1."""
        # Valid
        pattern = Pattern(
            trigger_pattern="Test",
            trigger_features={"intent": "test", "entity_types": [], "topics": []},
            action_heuristic="Test",
            action_structure={"action_type": "test", "queries": [], "predicates": []},
            observed_count=1,
            confidence=0.5,
            source_episode_ids=[1],
        )
        assert pattern.observed_count == 1

        # Invalid: observed_count = 0
        with pytest.raises(ValueError, match="observed_count must be >= 1"):
            Pattern(
                trigger_pattern="Test",
                trigger_features={"intent": "test", "entity_types": [], "topics": []},
                action_heuristic="Test",
                action_structure={
                    "action_type": "test",
                    "queries": [],
                    "predicates": [],
                },
                observed_count=0,
                confidence=0.5,
                source_episode_ids=[],
            )

    def test_pattern_required_trigger_features(self):
        """Should require trigger_features to have intent, entity_types, topics."""
        # Missing intent
        with pytest.raises(ValueError, match="trigger_features must contain 'intent'"):
            Pattern(
                trigger_pattern="Test",
                trigger_features={"entity_types": [], "topics": []},  # Missing intent
                action_heuristic="Test",
                action_structure={
                    "action_type": "test",
                    "queries": [],
                    "predicates": [],
                },
                observed_count=1,
                confidence=0.5,
                source_episode_ids=[1],
            )

        # Missing entity_types
        with pytest.raises(
            ValueError, match="trigger_features must contain 'entity_types'"
        ):
            Pattern(
                trigger_pattern="Test",
                trigger_features={"intent": "test", "topics": []},  # Missing entity_types
                action_heuristic="Test",
                action_structure={
                    "action_type": "test",
                    "queries": [],
                    "predicates": [],
                },
                observed_count=1,
                confidence=0.5,
                source_episode_ids=[1],
            )

    def test_pattern_to_dict(self):
        """Should serialize to dict correctly."""
        pattern = Pattern(
            trigger_pattern="User asks about X",
            trigger_features={"intent": "test", "entity_types": ["a"], "topics": ["b"]},
            action_heuristic="Do Y",
            action_structure={"action_type": "test", "queries": [], "predicates": []},
            observed_count=3,
            confidence=0.75,
            source_episode_ids=[1, 2, 3],
        )

        d = pattern.to_dict()

        assert d["trigger_pattern"] == "User asks about X"
        assert d["confidence"] == 0.75
        assert d["observed_count"] == 3
        assert d["source_episode_ids"] == [1, 2, 3]


# ============================================================================
# ProceduralMemory Value Object Tests
# ============================================================================


class TestProceduralMemory:
    """Test ProceduralMemory value object."""

    def test_procedural_memory_creation(self):
        """Should create procedural memory with valid data."""
        memory = ProceduralMemory(
            user_id="test_user",
            trigger_pattern="User asks about payment",
            trigger_features={"intent": "query_payment", "entity_types": [], "topics": []},
            action_heuristic="Retrieve payment info",
            action_structure={"action_type": "retrieve", "queries": [], "predicates": []},
            observed_count=5,
            confidence=0.80,
            created_at=datetime.now(UTC),
        )

        assert memory.user_id == "test_user"
        assert memory.observed_count == 5
        assert memory.confidence == 0.80

    def test_procedural_memory_from_pattern(self):
        """Should create ProceduralMemory from Pattern."""
        pattern = Pattern(
            trigger_pattern="Test pattern",
            trigger_features={"intent": "test", "entity_types": [], "topics": []},
            action_heuristic="Test action",
            action_structure={"action_type": "test", "queries": [], "predicates": []},
            observed_count=3,
            confidence=0.70,
            source_episode_ids=[1, 2, 3],
        )

        memory = ProceduralMemory.from_pattern(pattern=pattern, user_id="user_1")

        assert memory.user_id == "user_1"
        assert memory.trigger_pattern == pattern.trigger_pattern
        assert memory.observed_count == pattern.observed_count
        assert memory.confidence == pattern.confidence

    def test_procedural_memory_increment_observed_count(self):
        """Should increment observed_count and boost confidence."""
        memory = ProceduralMemory(
            user_id="test_user",
            trigger_pattern="Test",
            trigger_features={"intent": "test", "entity_types": [], "topics": []},
            action_heuristic="Test",
            action_structure={"action_type": "test", "queries": [], "predicates": []},
            observed_count=5,
            confidence=0.70,
            created_at=datetime.now(UTC),
        )

        incremented = memory.increment_observed_count()

        # Observed count should increase
        assert incremented.observed_count == 6

        # Confidence should increase with diminishing returns
        assert incremented.confidence > memory.confidence
        assert incremented.confidence < 0.95  # Below MAX_CONFIDENCE

        # Updated timestamp should be set
        assert incremented.updated_at is not None

    def test_procedural_memory_increment_diminishing_returns(self):
        """Should have diminishing returns on confidence boost."""
        memory = ProceduralMemory(
            user_id="test_user",
            trigger_pattern="Test",
            trigger_features={"intent": "test", "entity_types": [], "topics": []},
            action_heuristic="Test",
            action_structure={"action_type": "test", "queries": [], "predicates": []},
            observed_count=2,
            confidence=0.60,
            created_at=datetime.now(UTC),
        )

        # First increment
        inc1 = memory.increment_observed_count()
        boost1 = inc1.confidence - memory.confidence

        # Second increment (from higher confidence)
        inc2 = inc1.increment_observed_count()
        boost2 = inc2.confidence - inc1.confidence

        # Boost should diminish
        assert boost2 < boost1

    def test_procedural_memory_confidence_capped_at_max(self):
        """VISION: Epistemic humility - confidence capped at 0.95."""
        # Start with very high confidence
        memory = ProceduralMemory(
            user_id="test_user",
            trigger_pattern="Test",
            trigger_features={"intent": "test", "entity_types": [], "topics": []},
            action_heuristic="Test",
            action_structure={"action_type": "test", "queries": [], "predicates": []},
            observed_count=10,
            confidence=0.94,
            created_at=datetime.now(UTC),
        )

        # Multiple increments
        current = memory
        for _ in range(20):
            current = current.increment_observed_count()

        # Should never exceed 0.95
        assert current.confidence <= 0.95

    def test_procedural_memory_embedding_validation(self):
        """Should validate embedding dimensions."""
        # Valid 1536-dim embedding
        memory = ProceduralMemory(
            user_id="test_user",
            trigger_pattern="Test",
            trigger_features={"intent": "test", "entity_types": [], "topics": []},
            action_heuristic="Test",
            action_structure={"action_type": "test", "queries": [], "predicates": []},
            observed_count=1,
            confidence=0.5,
            created_at=datetime.now(UTC),
            embedding=np.random.rand(1536),
        )
        assert memory.embedding.shape == (1536,)

        # Invalid dimensions
        with pytest.raises(ValueError, match="embedding must be 1536-dimensional"):
            ProceduralMemory(
                user_id="test_user",
                trigger_pattern="Test",
                trigger_features={"intent": "test", "entity_types": [], "topics": []},
                action_heuristic="Test",
                action_structure={
                    "action_type": "test",
                    "queries": [],
                    "predicates": [],
                },
                observed_count=1,
                confidence=0.5,
                created_at=datetime.now(UTC),
                embedding=np.random.rand(512),  # Wrong dimension
            )


# ============================================================================
# ConsolidationScope Value Object Tests
# ============================================================================


class TestConsolidationScope:
    """Test ConsolidationScope value object."""

    def test_entity_scope(self):
        """Should create entity scope."""
        scope = ConsolidationScope.entity_scope("customer:test_123")

        assert scope.type == "entity"
        assert scope.identifier == "customer:test_123"

    def test_topic_scope(self):
        """Should create topic scope."""
        scope = ConsolidationScope.topic_scope("delivery_*")

        assert scope.type == "topic"
        assert scope.identifier == "delivery_*"

    def test_session_window_scope(self):
        """Should create session window scope."""
        scope = ConsolidationScope.session_window_scope(5)

        assert scope.type == "session_window"
        assert scope.identifier == "5"

    def test_scope_to_dict(self):
        """Should serialize to dict."""
        scope = ConsolidationScope.entity_scope("customer:test")
        d = scope.to_dict()

        assert d["type"] == "entity"
        assert d["identifier"] == "customer:test"


# ============================================================================
# KeyFact Value Object Tests
# ============================================================================


class TestKeyFact:
    """Test KeyFact value object."""

    def test_key_fact_creation(self):
        """Should create key fact with valid data."""
        fact = KeyFact(
            value="Friday",
            confidence=0.90,
            reinforced=5,
            source_memory_ids=[1, 2, 3, 4, 5],
        )

        assert fact.value == "Friday"
        assert fact.confidence == 0.90
        assert fact.reinforced == 5
        assert len(fact.source_memory_ids) == 5

    def test_key_fact_confidence_bounds(self):
        """Should validate confidence in [0.0, 1.0]."""
        # Valid
        fact = KeyFact(value="test", confidence=0.5, reinforced=1, source_memory_ids=[1])
        assert fact.confidence == 0.5

        # Invalid: > 1.0
        with pytest.raises(ValueError, match="confidence must be in"):
            KeyFact(value="test", confidence=1.5, reinforced=1, source_memory_ids=[1])

        # Invalid: < 0.0
        with pytest.raises(ValueError, match="confidence must be in"):
            KeyFact(value="test", confidence=-0.1, reinforced=1, source_memory_ids=[1])

    def test_key_fact_reinforced_positive(self):
        """Should validate reinforced >= 1."""
        # Valid: reinforced = 1
        fact = KeyFact(value="test", confidence=0.5, reinforced=1, source_memory_ids=[1])
        assert fact.reinforced == 1

        # Invalid: reinforced = 0
        with pytest.raises(ValueError, match="reinforced must be >= 1"):
            KeyFact(value="test", confidence=0.5, reinforced=0, source_memory_ids=[])

        # Invalid: reinforced < 0
        with pytest.raises(ValueError, match="reinforced must be >= 1"):
            KeyFact(value="test", confidence=0.5, reinforced=-1, source_memory_ids=[])

    def test_key_fact_to_dict(self):
        """Should serialize to dict."""
        fact = KeyFact(
            value="Monday",
            confidence=0.85,
            reinforced=3,
            source_memory_ids=[10, 20, 30],
        )

        d = fact.to_dict()

        assert d["value"] == "Monday"
        assert d["confidence"] == 0.85
        assert d["reinforced"] == 3
        assert d["source_memory_ids"] == [10, 20, 30]


# ============================================================================
# SummaryData Value Object Tests
# ============================================================================


class TestSummaryData:
    """Test SummaryData value object."""

    def test_summary_data_creation(self):
        """Should create summary data with valid fields."""
        summary_data = SummaryData(
            summary_text="Test summary text",
            key_facts={
                "delivery_day": KeyFact(
                    value="Friday",
                    confidence=0.90,
                    reinforced=5,
                    source_memory_ids=[1, 2, 3],
                )
            },
            interaction_patterns=["Pattern A", "Pattern B"],
            needs_validation=["Old fact"],
            confirmed_memory_ids=[1, 2, 3],
        )

        assert summary_data.summary_text == "Test summary text"
        assert len(summary_data.key_facts) == 1
        assert len(summary_data.interaction_patterns) == 2
        assert len(summary_data.confirmed_memory_ids) == 3

    def test_summary_data_from_llm_response(self):
        """Should parse LLM response into SummaryData."""
        llm_response = {
            "summary_text": "Customer prefers Friday deliveries",
            "key_facts": {
                "delivery_day": {
                    "value": "Friday",
                    "confidence": 0.92,
                    "reinforced": 5,
                    "source_memory_ids": [1, 3, 7, 10, 12],
                }
            },
            "interaction_patterns": ["Asks about delivery status frequently"],
            "needs_validation": [],
            "confirmed_memory_ids": [1, 3, 7],
        }

        summary_data = SummaryData.from_llm_response(llm_response)

        assert summary_data.summary_text == "Customer prefers Friday deliveries"
        assert "delivery_day" in summary_data.key_facts
        assert summary_data.key_facts["delivery_day"].value == "Friday"
        assert summary_data.key_facts["delivery_day"].confidence == 0.92
        assert len(summary_data.confirmed_memory_ids) == 3

    def test_summary_data_from_llm_response_missing_fields(self):
        """Should raise ValueError if required fields missing."""
        # Missing summary_text - should raise "Invalid LLM response structure"
        with pytest.raises(ValueError, match="Invalid LLM response structure"):
            SummaryData.from_llm_response(
                {
                    "key_facts": {},
                    "interaction_patterns": [],
                    "needs_validation": [],
                    "confirmed_memory_ids": [],
                }
            )

        # NOTE: key_facts is NOT required - it defaults to empty dict via .get()
        # So we don't test for missing key_facts

    def test_summary_data_empty_key_facts(self):
        """Should handle empty key facts."""
        summary_data = SummaryData(
            summary_text="No facts yet",
            key_facts={},
            interaction_patterns=[],
            needs_validation=[],
            confirmed_memory_ids=[],
        )

        assert len(summary_data.key_facts) == 0
        assert summary_data.summary_text == "No facts yet"


# ============================================================================
# Vision Principle Validation Tests
# ============================================================================


class TestVisionPrinciplesValueObjects:
    """Test value objects embody vision principles."""

    def test_epistemic_humility_max_confidence_enforcement(self):
        """VISION: Epistemic humility - MAX_CONFIDENCE enforced.

        ProceduralMemory.increment_observed_count() should never exceed 0.95.
        """
        # Start at 0.93
        memory = ProceduralMemory(
            user_id="test_user",
            trigger_pattern="Test",
            trigger_features={"intent": "test", "entity_types": [], "topics": []},
            action_heuristic="Test",
            action_structure={"action_type": "test", "queries": [], "predicates": []},
            observed_count=1,
            confidence=0.93,
            created_at=datetime.now(UTC),
        )

        # Increment many times
        current = memory
        for _ in range(50):
            current = current.increment_observed_count()

        # Should converge to 0.95, never exceed
        assert current.confidence <= 0.95
        assert 0.94 <= current.confidence <= 0.95  # Should be very close to 0.95

    def test_domain_integrity_immutable_patterns(self):
        """VISION: Domain integrity - Pattern is frozen (immutable)."""
        pattern = Pattern(
            trigger_pattern="Test",
            trigger_features={"intent": "test", "entity_types": [], "topics": []},
            action_heuristic="Test",
            action_structure={"action_type": "test", "queries": [], "predicates": []},
            observed_count=1,
            confidence=0.5,
            source_episode_ids=[1],
        )

        # Should not be able to modify frozen dataclass
        with pytest.raises(Exception):  # FrozenInstanceError
            pattern.confidence = 0.9
