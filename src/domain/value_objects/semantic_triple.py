"""Semantic triple value object.

Represents a subject-predicate-object relationship extracted from conversation.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PredicateType(str, Enum):
    """Type of semantic predicate.

    Maps to the predicate taxonomy in DESIGN.md Phase 1B.
    """

    ATTRIBUTE = "attribute"  # Factual properties (payment_terms, industry)
    PREFERENCE = "preference"  # User preferences (prefers_x, dislikes_y)
    RELATIONSHIP = "relationship"  # Inter-entity relationships (supplies_to, works_with)
    ACTION = "action"  # Completed actions (ordered, cancelled, requested)


@dataclass(frozen=True)
class SemanticTriple:
    """Immutable semantic triple (SPO: Subject-Predicate-Object).

    Represents a structured piece of knowledge extracted from conversation.
    The subject is always a resolved entity from Phase 1A.

    Attributes:
        subject_entity_id: ID of subject entity (e.g., "customer_acme_123")
        predicate: Normalized predicate name (e.g., "prefers_delivery_day")
        predicate_type: Type of predicate (attribute, preference, relationship, action)
        object_value: Structured object value (always a dict with type/value)
        confidence: Extraction confidence [0.0, 1.0]
        metadata: Additional extraction metadata
    """

    subject_entity_id: str
    predicate: str
    predicate_type: PredicateType
    object_value: dict[str, Any]
    confidence: float
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate semantic triple invariants."""
        if not self.subject_entity_id:
            msg = "subject_entity_id cannot be empty"
            raise ValueError(msg)
        if not self.predicate:
            msg = "predicate cannot be empty"
            raise ValueError(msg)
        if not isinstance(self.predicate_type, PredicateType):
            msg = f"predicate_type must be PredicateType enum, got: {type(self.predicate_type)}"
            raise ValueError(msg)
        if not isinstance(self.object_value, dict):
            msg = f"object_value must be dict, got: {type(self.object_value)}"
            raise ValueError(msg)
        if not (0.0 <= self.confidence <= 1.0):
            msg = f"confidence must be in [0.0, 1.0], got: {self.confidence}"
            raise ValueError(msg)

    @property
    def is_high_confidence(self) -> bool:
        """Check if triple has high confidence (>= 0.8)."""
        return self.confidence >= 0.8

    @property
    def is_low_confidence(self) -> bool:
        """Check if triple has low confidence (< 0.5)."""
        return self.confidence < 0.5

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "subject_entity_id": self.subject_entity_id,
            "predicate": self.predicate,
            "predicate_type": self.predicate_type.value,
            "object_value": self.object_value,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation for logging."""
        obj_str = str(self.object_value.get("value", self.object_value))[:50]
        return f"{self.subject_entity_id} -{self.predicate}-> {obj_str} (conf={self.confidence:.2f})"
