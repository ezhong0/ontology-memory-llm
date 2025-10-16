"""Unit tests for MemoryValidationService.

Tests memory lifecycle management: confidence decay, reinforcement, and validation.
"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.domain.entities.semantic_memory import SemanticMemory
from src.domain.services.memory_validation_service import MemoryValidationService
from src.domain.value_objects import PredicateType, SemanticTriple


@pytest.mark.unit
class TestMemoryValidationService:
    """Test MemoryValidationService lifecycle management."""

    @pytest.fixture
    def validation_service(self):
        """Create validation service with default config."""
        return MemoryValidationService()

    @pytest.fixture
    def custom_validation_service(self):
        """Create validation service with custom config."""
        return MemoryValidationService(
            decay_rate=0.02,  # 2% per day
            reinforcement_boost=0.10,  # 10% per reinforcement
        )

    @pytest.fixture
    def sample_memory(self):
        """Sample semantic memory."""
        created_at = datetime.now(timezone.utc) - timedelta(days=30)
        return SemanticMemory(
            memory_id=123,
            user_id="user_test_123",
            subject_entity_id="company_acme_123",
            predicate="prefers",
            predicate_type=PredicateType.PREFERENCE,
            object_value={"value": "net-30 payment terms"},
            confidence=0.8,
            source_event_ids=[100, 101],
            reinforcement_count=2,
            created_at=created_at,
            updated_at=created_at,
            last_validated_at=created_at,
        )

    @pytest.fixture
    def sample_triple(self):
        """Sample semantic triple for reinforcement."""
        return SemanticTriple(
            subject_entity_id="company_acme_123",
            predicate="prefers",
            predicate_type=PredicateType.PREFERENCE,
            object_value={"value": "net-30 payment terms"},
            confidence=0.85,
            metadata={"source_event_id": 150},
        )

    # ============================================================================
    # Confidence Decay Tests
    # ============================================================================

    def test_calculate_confidence_decay_no_time_passed(
        self, validation_service, sample_memory
    ):
        """Test no decay when zero days have passed."""
        # Current time = last validation time
        current_time = sample_memory.last_validated_at

        decayed = validation_service.calculate_confidence_decay(
            memory=sample_memory,
            current_date=current_time,
        )

        assert decayed == sample_memory.confidence

    def test_calculate_confidence_decay_exponential(
        self, validation_service, sample_memory
    ):
        """Test exponential decay formula."""
        # Memory is 30 days old
        # Formula: confidence * exp(-decay_rate * days)
        # Expected: 0.8 * exp(-0.01 * 30) = 0.8 * 0.7408 ≈ 0.593
        current_time = sample_memory.last_validated_at + timedelta(days=30)

        decayed = validation_service.calculate_confidence_decay(
            memory=sample_memory,
            current_date=current_time,
        )

        # Should be less than original
        assert decayed < sample_memory.confidence
        # Should be approximately 0.593
        assert 0.59 < decayed < 0.60

    def test_calculate_confidence_decay_uses_last_validated(
        self, validation_service
    ):
        """Test decay uses last_validated_at, not created_at."""
        created_at = datetime.now(timezone.utc) - timedelta(days=60)
        validated_at = datetime.now(timezone.utc) - timedelta(days=10)

        memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "test"},
            confidence=0.9,
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=created_at,
            updated_at=validated_at,
            last_validated_at=validated_at,  # More recent than created_at
        )

        current_time = validated_at + timedelta(days=10)

        decayed = validation_service.calculate_confidence_decay(
            memory=memory,
            current_date=current_time,
        )

        # Should decay from 10 days ago (validated_at), not 60 days ago (created_at)
        # Formula: 0.9 * exp(-0.01 * 10) ≈ 0.8145
        assert 0.81 < decayed < 0.82

    def test_calculate_confidence_decay_never_validated(
        self, validation_service
    ):
        """Test decay uses created_at when never validated."""
        created_at = datetime.now(timezone.utc) - timedelta(days=20)

        memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "test"},
            confidence=0.8,
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=created_at,
            updated_at=created_at,
            last_validated_at=None,  # Never validated
        )

        current_time = datetime.now(timezone.utc)

        decayed = validation_service.calculate_confidence_decay(
            memory=memory,
            current_date=current_time,
        )

        # Should decay from created_at (20 days)
        # Formula: 0.8 * exp(-0.01 * 20) ≈ 0.6548
        assert 0.65 < decayed < 0.66

    def test_calculate_confidence_decay_floor(self, validation_service):
        """Test decay doesn't go below MIN_CONFIDENCE (0.0)."""
        old_memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "test"},
            confidence=0.01,  # Very low confidence
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=datetime.now(timezone.utc) - timedelta(days=365),
            updated_at=datetime.now(timezone.utc) - timedelta(days=365),
            last_validated_at=datetime.now(timezone.utc) - timedelta(days=365),
        )

        current_time = datetime.now(timezone.utc)

        decayed = validation_service.calculate_confidence_decay(
            memory=old_memory,
            current_date=current_time,
        )

        # Should not go below 0.0
        assert decayed >= validation_service._min_confidence
        assert decayed >= 0.0

    def test_calculate_confidence_decay_custom_rate(
        self, custom_validation_service, sample_memory
    ):
        """Test decay with custom decay rate."""
        # Custom service has decay_rate = 0.02 (2% per day)
        current_time = sample_memory.last_validated_at + timedelta(days=10)

        decayed = custom_validation_service.calculate_confidence_decay(
            memory=sample_memory,
            current_date=current_time,
        )

        # Formula: 0.8 * exp(-0.02 * 10) ≈ 0.8 * 0.8187 ≈ 0.655
        assert 0.65 < decayed < 0.66

    # ============================================================================
    # Reinforcement Tests
    # ============================================================================

    def test_reinforce_memory_success(
        self, validation_service, sample_memory, sample_triple
    ):
        """Test successful memory reinforcement."""
        old_confidence = sample_memory.confidence
        old_count = sample_memory.reinforcement_count
        event_id = 150

        validation_service.reinforce_memory(
            memory=sample_memory,
            new_observation=sample_triple,
            event_id=event_id,
        )

        # Confidence should increase
        assert sample_memory.confidence > old_confidence
        # Boost should be applied (0.15), but capped at MAX_CONFIDENCE (0.95)
        expected = min(validation_service._max_confidence, old_confidence + validation_service._reinforcement_boost)
        assert sample_memory.confidence == expected

        # Reinforcement count should increase
        assert sample_memory.reinforcement_count == old_count + 1

        # Event should be added to sources
        assert event_id in sample_memory.source_event_ids

    def test_reinforce_memory_capped_at_max(
        self, validation_service
    ):
        """Test reinforcement respects MAX_CONFIDENCE cap."""
        high_confidence_memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "test"},
            confidence=0.92,  # Close to MAX_CONFIDENCE (0.95)
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        triple = SemanticTriple(
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "test"},
            confidence=0.9,
            metadata={},
        )

        validation_service.reinforce_memory(
            memory=high_confidence_memory,
            new_observation=triple,
            event_id=2,
        )

        # Should be capped at MAX_CONFIDENCE
        assert high_confidence_memory.confidence <= validation_service._max_confidence
        assert high_confidence_memory.confidence == 0.95

    def test_reinforce_memory_subject_mismatch_error(
        self, validation_service, sample_memory
    ):
        """Test reinforcement fails on subject mismatch."""
        mismatched_triple = SemanticTriple(
            subject_entity_id="different_entity",  # Different subject
            predicate="prefers",
            predicate_type=PredicateType.PREFERENCE,
            object_value={"value": "test"},
            confidence=0.8,
            metadata={},
        )

        with pytest.raises(ValueError, match="Subject mismatch"):
            validation_service.reinforce_memory(
                memory=sample_memory,
                new_observation=mismatched_triple,
                event_id=1,
            )

    def test_reinforce_memory_predicate_mismatch_error(
        self, validation_service, sample_memory
    ):
        """Test reinforcement fails on predicate mismatch."""
        mismatched_triple = SemanticTriple(
            subject_entity_id="company_acme_123",
            predicate="different_predicate",  # Different predicate
            predicate_type=PredicateType.PREFERENCE,
            object_value={"value": "test"},
            confidence=0.8,
            metadata={},
        )

        with pytest.raises(ValueError, match="Predicate mismatch"):
            validation_service.reinforce_memory(
                memory=sample_memory,
                new_observation=mismatched_triple,
                event_id=1,
            )

    # ============================================================================
    # Apply Decay Tests
    # ============================================================================

    def test_apply_decay_if_needed_applies_when_stale(
        self, validation_service
    ):
        """Test decay is applied when memory is stale."""
        old_memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "test"},
            confidence=0.8,
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
            updated_at=datetime.now(timezone.utc) - timedelta(days=30),
            last_validated_at=datetime.now(timezone.utc) - timedelta(days=30),
        )

        old_confidence = old_memory.confidence

        was_applied = validation_service.apply_decay_if_needed(
            memory=old_memory,
            current_date=datetime.now(timezone.utc),
        )

        assert was_applied
        assert old_memory.confidence < old_confidence

    def test_apply_decay_if_needed_skips_when_recent(
        self, validation_service
    ):
        """Test decay is not applied when memory is recent."""
        # Use single timestamp to avoid microsecond differences
        now = datetime.now(timezone.utc)

        recent_memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "test"},
            confidence=0.8,
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=now,
            updated_at=now,
            last_validated_at=now,
        )

        old_confidence = recent_memory.confidence

        was_applied = validation_service.apply_decay_if_needed(
            memory=recent_memory,
            current_date=now,  # Same timestamp = zero time elapsed
        )

        assert not was_applied
        assert recent_memory.confidence == old_confidence

    # ============================================================================
    # Deactivation Decision Tests
    # ============================================================================

    def test_should_deactivate_low_confidence(self, validation_service):
        """Test low confidence memories should be deactivated."""
        low_confidence_memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "test"},
            confidence=0.2,  # Below default threshold (0.3)
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        should_deactivate = validation_service.should_deactivate(
            memory=low_confidence_memory
        )

        assert should_deactivate

    def test_should_deactivate_adequate_confidence(self, validation_service):
        """Test adequate confidence memories should not be deactivated."""
        good_memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "test"},
            confidence=0.7,  # Above threshold
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        should_deactivate = validation_service.should_deactivate(
            memory=good_memory
        )

        assert not should_deactivate

    def test_should_deactivate_custom_threshold(self, validation_service):
        """Test deactivation with custom threshold."""
        memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "test"},
            confidence=0.4,
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # With default threshold (0.3), should not deactivate
        assert not validation_service.should_deactivate(memory)

        # With custom threshold (0.5), should deactivate
        assert validation_service.should_deactivate(memory, min_confidence_threshold=0.5)
