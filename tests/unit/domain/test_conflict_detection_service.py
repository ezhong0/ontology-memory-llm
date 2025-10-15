"""Unit tests for ConflictDetectionService.

Tests conflict detection and resolution recommendation logic.
"""
import pytest
from datetime import datetime, timedelta, timezone

from src.domain.entities.semantic_memory import SemanticMemory
from src.domain.services.conflict_detection_service import ConflictDetectionService
from src.domain.value_objects import (
    ConflictResolution,
    ConflictType,
    PredicateType,
    SemanticTriple,
)


@pytest.mark.unit
class TestConflictDetectionService:
    """Test ConflictDetectionService conflict detection and resolution."""

    @pytest.fixture
    def conflict_service(self):
        """Create conflict detection service with default config."""
        return ConflictDetectionService()

    @pytest.fixture
    def custom_conflict_service(self):
        """Create conflict detection service with custom thresholds."""
        return ConflictDetectionService(
            temporal_threshold_days=60,
            confidence_threshold=0.3,
            reinforcement_threshold=5,
        )

    @pytest.fixture
    def sample_memory(self):
        """Sample semantic memory."""
        return SemanticMemory(
            memory_id=100,
            user_id="user_test_123",
            subject_entity_id="company_acme_123",
            predicate="payment_terms",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "net-30"},
            confidence=0.75,
            source_event_ids=[10, 20],
            reinforcement_count=2,
            created_at=datetime.now(timezone.utc) - timedelta(days=60),
            updated_at=datetime.now(timezone.utc) - timedelta(days=60),
        )

    @pytest.fixture
    def conflicting_triple(self):
        """Semantic triple that conflicts with sample_memory."""
        return SemanticTriple(
            subject_entity_id="company_acme_123",
            predicate="payment_terms",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "net-60"},  # Different from net-30
            confidence=0.85,
            metadata={
                "source_event_id": 30,
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @pytest.fixture
    def matching_triple(self):
        """Semantic triple that does NOT conflict with sample_memory."""
        return SemanticTriple(
            subject_entity_id="company_acme_123",
            predicate="payment_terms",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "net-30"},  # Same as memory
            confidence=0.80,
            metadata={"source_event_id": 25},
        )

    # ============================================================================
    # Basic Conflict Detection Tests
    # ============================================================================

    def test_detect_conflict_value_mismatch(
        self, conflict_service, sample_memory, conflicting_triple
    ):
        """Test conflict detected when values differ."""
        conflict = conflict_service.detect_conflict(
            new_triple=conflicting_triple,
            existing_memory=sample_memory,
        )

        assert conflict is not None
        assert conflict.conflict_type == ConflictType.VALUE_MISMATCH
        assert conflict.subject_entity_id == "company_acme_123"
        assert conflict.predicate == "payment_terms"
        assert conflict.new_value == {"value": "net-60"}
        assert conflict.existing_value == {"value": "net-30"}
        assert conflict.existing_memory_id == 100

    def test_detect_conflict_no_conflict_when_values_match(
        self, conflict_service, sample_memory, matching_triple
    ):
        """Test no conflict when values are the same."""
        conflict = conflict_service.detect_conflict(
            new_triple=matching_triple,
            existing_memory=sample_memory,
        )

        assert conflict is None

    def test_detect_conflict_subject_mismatch_error(
        self, conflict_service, sample_memory
    ):
        """Test error when subject doesn't match."""
        mismatched_triple = SemanticTriple(
            subject_entity_id="different_entity",  # Different subject
            predicate="payment_terms",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "net-60"},
            confidence=0.8,
            metadata={},
        )

        with pytest.raises(ValueError, match="Subject mismatch"):
            conflict_service.detect_conflict(
                new_triple=mismatched_triple,
                existing_memory=sample_memory,
            )

    def test_detect_conflict_predicate_mismatch_error(
        self, conflict_service, sample_memory
    ):
        """Test error when predicate doesn't match."""
        mismatched_triple = SemanticTriple(
            subject_entity_id="company_acme_123",
            predicate="different_predicate",  # Different predicate
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "net-60"},
            confidence=0.8,
            metadata={},
        )

        with pytest.raises(ValueError, match="Predicate mismatch"):
            conflict_service.detect_conflict(
                new_triple=mismatched_triple,
                existing_memory=sample_memory,
            )

    # ============================================================================
    # Conflict Type Classification Tests
    # ============================================================================

    def test_classify_conflict_temporal_inconsistency(
        self, conflict_service, sample_memory
    ):
        """Test temporal inconsistency classification for action predicates."""
        action_memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="order_123",
            predicate="status",
            predicate_type=PredicateType.ACTION,  # Action type
            object_value={"value": "ordered"},
            confidence=0.8,
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        action_triple = SemanticTriple(
            subject_entity_id="order_123",
            predicate="status",
            predicate_type=PredicateType.ACTION,
            object_value={"value": "cancelled"},  # Different action
            confidence=0.8,
            metadata={"extraction_timestamp": datetime.now(timezone.utc).isoformat()},
        )

        conflict = conflict_service.detect_conflict(
            new_triple=action_triple,
            existing_memory=action_memory,
        )

        assert conflict.conflict_type == ConflictType.TEMPORAL_INCONSISTENCY

    def test_classify_conflict_value_mismatch_default(
        self, conflict_service, sample_memory, conflicting_triple
    ):
        """Test value mismatch is default classification."""
        conflict = conflict_service.detect_conflict(
            new_triple=conflicting_triple,
            existing_memory=sample_memory,
        )

        assert conflict.conflict_type == ConflictType.VALUE_MISMATCH

    # ============================================================================
    # Resolution Recommendation Tests
    # ============================================================================

    def test_resolution_temporal_newest_wins(
        self, conflict_service
    ):
        """Test KEEP_NEWEST resolution when temporal diff > threshold."""
        old_memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "old"},
            confidence=0.8,
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=datetime.now(timezone.utc) - timedelta(days=60),  # 60 days old
            updated_at=datetime.now(timezone.utc) - timedelta(days=60),
        )

        new_triple = SemanticTriple(
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "new"},
            confidence=0.75,  # Even with lower confidence
            metadata={
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        conflict = conflict_service.detect_conflict(
            new_triple=new_triple,
            existing_memory=old_memory,
        )

        # Temporal diff > 30 days, should recommend newest
        assert conflict.recommended_resolution == ConflictResolution.KEEP_NEWEST
        assert conflict.temporal_diff_days >= 30

    def test_resolution_confidence_highest_wins(
        self, conflict_service
    ):
        """Test KEEP_HIGHEST_CONFIDENCE resolution when confidence diff > threshold."""
        low_confidence_memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "old"},
            confidence=0.5,  # Low confidence
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=datetime.now(timezone.utc) - timedelta(days=10),
            updated_at=datetime.now(timezone.utc) - timedelta(days=10),
        )

        high_confidence_triple = SemanticTriple(
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "new"},
            confidence=0.9,  # High confidence (diff = 0.4 > 0.2)
            metadata={
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        conflict = conflict_service.detect_conflict(
            new_triple=high_confidence_triple,
            existing_memory=low_confidence_memory,
        )

        # Confidence diff > 0.2, should recommend highest confidence
        assert conflict.recommended_resolution == ConflictResolution.KEEP_HIGHEST_CONFIDENCE
        assert abs(conflict.confidence_diff) >= 0.2

    def test_resolution_require_clarification_ambiguous(
        self, conflict_service
    ):
        """Test REQUIRE_CLARIFICATION when no clear resolution strategy applies."""
        memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "old"},
            confidence=0.75,  # Similar confidence
            source_event_ids=[1],
            reinforcement_count=2,  # Similar reinforcement
            created_at=datetime.now(timezone.utc) - timedelta(days=10),  # Recent
            updated_at=datetime.now(timezone.utc) - timedelta(days=10),
        )

        similar_triple = SemanticTriple(
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "new"},
            confidence=0.78,  # Similar confidence (diff = 0.03 < 0.2)
            metadata={
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        conflict = conflict_service.detect_conflict(
            new_triple=similar_triple,
            existing_memory=memory,
        )

        # No clear winner, should require clarification
        assert conflict.recommended_resolution == ConflictResolution.REQUIRE_CLARIFICATION

    def test_resolution_custom_thresholds(
        self, custom_conflict_service
    ):
        """Test resolution with custom thresholds."""
        memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "old"},
            confidence=0.7,
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=datetime.now(timezone.utc) - timedelta(days=45),
            updated_at=datetime.now(timezone.utc) - timedelta(days=45),
        )

        new_triple = SemanticTriple(
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "new"},
            confidence=0.72,  # diff = 0.02 < custom threshold (0.3)
            metadata={
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        conflict = custom_conflict_service.detect_conflict(
            new_triple=new_triple,
            existing_memory=memory,
        )

        # With custom temporal_threshold=60, 45 days is not enough
        # With custom confidence_threshold=0.3, 0.02 diff is not enough
        # Should require clarification
        assert conflict.recommended_resolution == ConflictResolution.REQUIRE_CLARIFICATION

    # ============================================================================
    # Metadata Tests
    # ============================================================================

    def test_conflict_includes_metadata(
        self, conflict_service, sample_memory, conflicting_triple
    ):
        """Test conflict includes proper metadata."""
        conflict = conflict_service.detect_conflict(
            new_triple=conflicting_triple,
            existing_memory=sample_memory,
            new_memory_id=200,
        )

        assert conflict is not None

        # Check IDs
        assert conflict.new_memory_id == 200
        assert conflict.existing_memory_id == 100

        # Check metadata
        assert "new_confidence" in conflict.metadata
        assert conflict.metadata["new_confidence"] == conflicting_triple.confidence
        assert "existing_confidence" in conflict.metadata
        assert conflict.metadata["existing_confidence"] == sample_memory.confidence

        assert "new_reinforcement_count" in conflict.metadata
        assert conflict.metadata["new_reinforcement_count"] == 1
        assert "existing_reinforcement_count" in conflict.metadata
        assert conflict.metadata["existing_reinforcement_count"] == 2

        assert "new_source" in conflict.metadata
        assert "existing_sources" in conflict.metadata
        assert conflict.metadata["existing_sources"] == [10, 20]

    # ============================================================================
    # Value Comparison Tests
    # ============================================================================

    def test_values_conflict_simple_values(self, conflict_service):
        """Test value conflict detection with simple values."""
        value1 = {"value": "net-30"}
        value2 = {"value": "net-60"}

        assert conflict_service._values_conflict(value1, value2)

    def test_values_match_simple_values(self, conflict_service):
        """Test no conflict when simple values match."""
        value1 = {"value": "net-30"}
        value2 = {"value": "net-30"}

        assert not conflict_service._values_conflict(value1, value2)

    def test_values_conflict_complex_objects(self, conflict_service):
        """Test value conflict with complex objects (no value field)."""
        value1 = {"address": "123 Main St", "city": "NY"}
        value2 = {"address": "456 Oak Ave", "city": "LA"}

        assert conflict_service._values_conflict(value1, value2)

    def test_values_match_complex_objects(self, conflict_service):
        """Test no conflict when complex objects match."""
        value1 = {"address": "123 Main St", "city": "NY"}
        value2 = {"address": "123 Main St", "city": "NY"}

        assert not conflict_service._values_conflict(value1, value2)

    # ============================================================================
    # Temporal Calculation Tests
    # ============================================================================

    def test_calculate_temporal_diff_success(
        self, conflict_service
    ):
        """Test temporal diff calculation with valid timestamps."""
        created_at = datetime.now(timezone.utc) - timedelta(days=40)
        memory = SemanticMemory(
            memory_id=1,
            user_id="user_test_123",
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "old"},
            confidence=0.8,
            source_event_ids=[1],
            reinforcement_count=1,
            created_at=created_at,
            updated_at=created_at,
        )

        new_timestamp = datetime.now(timezone.utc)
        new_triple = SemanticTriple(
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "new"},
            confidence=0.8,
            metadata={
                "extraction_timestamp": new_timestamp.isoformat(),
            },
        )

        days_diff = conflict_service._calculate_temporal_diff(
            new_triple=new_triple,
            existing_memory=memory,
        )

        assert days_diff is not None
        assert 39 <= days_diff <= 41  # Approximately 40 days

    def test_calculate_temporal_diff_missing_timestamp(
        self, conflict_service, sample_memory
    ):
        """Test temporal diff returns None when timestamp missing."""
        triple_no_timestamp = SemanticTriple(
            subject_entity_id="entity_1",
            predicate="test",
            predicate_type=PredicateType.ATTRIBUTE,
            object_value={"value": "new"},
            confidence=0.8,
            metadata={},  # No extraction_timestamp
        )

        days_diff = conflict_service._calculate_temporal_diff(
            new_triple=triple_no_timestamp,
            existing_memory=sample_memory,
        )

        assert days_diff is None
