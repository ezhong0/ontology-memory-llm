"""Memory conflict value object.

Represents a detected conflict between semantic memories.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ConflictType(str, Enum):
    """Type of memory conflict."""

    VALUE_MISMATCH = "value_mismatch"  # Same predicate, different values
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"  # Time-based contradiction
    LOGICAL_CONTRADICTION = "logical_contradiction"  # Logically impossible


class ConflictResolution(str, Enum):
    """How a conflict should be resolved."""

    KEEP_NEWEST = "keep_newest"  # Keep most recent observation
    KEEP_HIGHEST_CONFIDENCE = "keep_highest_confidence"  # Keep highest confidence
    KEEP_MOST_REINFORCED = "keep_most_reinforced"  # Keep most observations
    REQUIRE_CLARIFICATION = "require_clarification"  # User must clarify
    MARK_BOTH_INVALID = "mark_both_invalid"  # Both are wrong


@dataclass(frozen=True)
class MemoryConflict:
    """Immutable conflict detection result.

    Represents a detected conflict between a new observation and existing memory.

    Attributes:
        conflict_type: Type of conflict detected
        new_memory_id: ID of new conflicting memory (if stored)
        existing_memory_id: ID of existing conflicting memory
        subject_entity_id: Entity that both memories are about
        predicate: The predicate where conflict occurs
        new_value: New observed value
        existing_value: Existing memory value
        recommended_resolution: Recommended resolution strategy
        confidence_diff: Confidence difference (new - existing)
        temporal_diff_days: Time difference in days (new - existing)
        metadata: Additional conflict details
    """

    conflict_type: ConflictType
    new_memory_id: int | None
    existing_memory_id: int
    subject_entity_id: str
    predicate: str
    new_value: dict[str, Any]
    existing_value: dict[str, Any]
    recommended_resolution: ConflictResolution
    confidence_diff: float
    temporal_diff_days: int | None
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate conflict invariants."""
        if not self.subject_entity_id:
            msg = "subject_entity_id cannot be empty"
            raise ValueError(msg)
        if not self.predicate:
            msg = "predicate cannot be empty"
            raise ValueError(msg)

    @property
    def is_severe(self) -> bool:
        """Check if conflict is severe (requires immediate attention)."""
        return self.conflict_type == ConflictType.LOGICAL_CONTRADICTION

    @property
    def is_resolvable_automatically(self) -> bool:
        """Check if conflict can be resolved automatically."""
        return self.recommended_resolution in [
            ConflictResolution.KEEP_NEWEST,
            ConflictResolution.KEEP_HIGHEST_CONFIDENCE,
            ConflictResolution.KEEP_MOST_REINFORCED,
        ]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "conflict_type": self.conflict_type.value,
            "new_memory_id": self.new_memory_id,
            "existing_memory_id": self.existing_memory_id,
            "subject_entity_id": self.subject_entity_id,
            "predicate": self.predicate,
            "new_value": self.new_value,
            "existing_value": self.existing_value,
            "recommended_resolution": self.recommended_resolution.value,
            "confidence_diff": self.confidence_diff,
            "temporal_diff_days": self.temporal_diff_days,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"Conflict({self.conflict_type.value}): {self.subject_entity_id}.{self.predicate} "
            f"[{self.existing_value.get('value')} -> {self.new_value.get('value')}] "
            f"→ {self.recommended_resolution.value}"
        )
