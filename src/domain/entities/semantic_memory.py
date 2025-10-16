"""Semantic memory domain entity.

Represents a stored piece of semantic knowledge (SPO triple with metadata).
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.domain.value_objects import PredicateType


@dataclass
class SemanticMemory:
    """Domain entity representing a semantic memory.

    A semantic memory is a stored SPO (subject-predicate-object) triple
    extracted from conversation. It includes confidence tracking, validation
    history, and vector embeddings for similarity search.

    Attributes:
        memory_id: Database primary key (None if not yet persisted)
        user_id: User who owns this memory
        subject_entity_id: Subject entity (from Phase 1A resolution)
        predicate: Normalized predicate name
        predicate_type: Type of predicate (attribute, preference, relationship, action)
        object_value: Structured object value (always dict)
        confidence: Current confidence [0.0, 1.0]
        status: Memory status (active, inactive, conflicted)
        reinforcement_count: Number of times this memory was reinforced
        source_event_ids: Chat event IDs that contributed to this memory
        embedding: Vector embedding for similarity search (1536 dimensions)
        created_at: When this memory was first created
        updated_at: When this memory was last updated
        last_validated_at: When this memory was last validated/reinforced
    """

    user_id: str
    subject_entity_id: str
    predicate: str
    predicate_type: PredicateType
    object_value: dict[str, Any]
    confidence: float
    status: str = "active"
    reinforcement_count: int = 1
    source_event_ids: list[int] = field(default_factory=list)
    embedding: list[float] | None = None
    memory_id: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_validated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate semantic memory invariants."""
        if not self.user_id:
            msg = "user_id cannot be empty"
            raise ValueError(msg)
        if not self.subject_entity_id:
            msg = "subject_entity_id cannot be empty"
            raise ValueError(msg)
        if not self.predicate:
            msg = "predicate cannot be empty"
            raise ValueError(msg)
        if not isinstance(self.predicate_type, PredicateType):
            msg = f"predicate_type must be PredicateType, got: {type(self.predicate_type)}"
            raise ValueError(msg)
        if not isinstance(self.object_value, dict):
            msg = f"object_value must be dict, got: {type(self.object_value)}"
            raise ValueError(msg)
        if not (0.0 <= self.confidence <= 1.0):
            msg = f"confidence must be in [0.0, 1.0], got: {self.confidence}"
            raise ValueError(msg)
        if self.status not in ["active", "inactive", "conflicted"]:
            msg = f"status must be active/inactive/conflicted, got: {self.status}"
            raise ValueError(msg)
        if self.reinforcement_count < 1:
            msg = f"reinforcement_count must be >= 1, got: {self.reinforcement_count}"
            raise ValueError(msg)

    @property
    def is_active(self) -> bool:
        """Check if memory is active."""
        return self.status == "active"

    @property
    def is_conflicted(self) -> bool:
        """Check if memory has conflicts."""
        return self.status == "conflicted"

    @property
    def is_high_confidence(self) -> bool:
        """Check if memory has high confidence (>= 0.8)."""
        return self.confidence >= 0.8

    @property
    def is_well_reinforced(self) -> bool:
        """Check if memory is well-reinforced (>= 3 observations)."""
        return self.reinforcement_count >= 3

    @property
    def days_since_last_validation(self) -> int | None:
        """Calculate days since last validation.

        Returns:
            Number of days, or None if never validated
        """
        if self.last_validated_at is None:
            return None
        delta = datetime.now(UTC) - self.last_validated_at
        return delta.days

    def reinforce(self, new_event_id: int, confidence_boost: float = 0.05) -> None:
        """Reinforce memory with new observation.

        Args:
            new_event_id: Event ID of new observation
            confidence_boost: Confidence increase per reinforcement (default: 0.05)
        """
        self.reinforcement_count += 1
        self.confidence = min(0.95, self.confidence + confidence_boost)
        if new_event_id not in self.source_event_ids:
            self.source_event_ids.append(new_event_id)
        self.last_validated_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def apply_decay(self, decayed_confidence: float) -> None:
        """Apply temporal confidence decay.

        Args:
            decayed_confidence: New confidence after decay calculation
        """
        if decayed_confidence < self.confidence:
            self.confidence = max(0.0, decayed_confidence)
            self.updated_at = datetime.now(UTC)

    def mark_as_conflicted(self) -> None:
        """Mark memory as conflicted."""
        self.status = "conflicted"
        self.updated_at = datetime.now(UTC)

    def mark_as_inactive(self) -> None:
        """Mark memory as inactive."""
        self.status = "inactive"
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation (without embedding for size)
        """
        return {
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "subject_entity_id": self.subject_entity_id,
            "predicate": self.predicate,
            "predicate_type": self.predicate_type.value,
            "object_value": self.object_value,
            "confidence": self.confidence,
            "status": self.status,
            "reinforcement_count": self.reinforcement_count,
            "source_event_ids": self.source_event_ids,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_validated_at": self.last_validated_at.isoformat() if self.last_validated_at else None,
        }

    def __str__(self) -> str:
        """String representation for logging."""
        obj_str = str(self.object_value.get("value", self.object_value))[:30]
        return (
            f"Memory({self.memory_id}): {self.subject_entity_id}.{self.predicate} = {obj_str} "
            f"(conf={self.confidence:.2f}, reinf={self.reinforcement_count})"
        )

    def __eq__(self, other: object) -> bool:
        """Memories are equal if they have the same memory_id."""
        if not isinstance(other, SemanticMemory):
            return False
        if self.memory_id is None or other.memory_id is None:
            return False
        return self.memory_id == other.memory_id

    def __hash__(self) -> int:
        """Hash based on memory_id."""
        return hash(self.memory_id) if self.memory_id else hash(id(self))
