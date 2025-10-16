"""Procedural Memory entity.

A stored procedural memory representing a learned "When X, also Y" heuristic.

This is an ENTITY (not a value object) because it has:
- Identity (memory_id)
- Mutable state (observed_count, confidence, updated_at)
- Behavior (increment_observed_count)
- Lifecycle (created, updated)

Design from: PHASE1D_PLAN_ITERATION.md
Vision: Layer 5 - Learning from interaction patterns
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
from numpy import typing as npt

from src.domain.value_objects.procedural_memory import Pattern


@dataclass
class ProceduralMemory:
    """A stored procedural memory (learned heuristic).

    Represents a pattern stored in the procedural_memories table.

    Vision: "When X, also Y" learned patterns that augment retrieval.

    Embedding Strategy:
    - Embed trigger_pattern (not action)
    - Reason: Match similar query intents, not similar actions
    - During retrieval: Find patterns with similar triggers to current query

    Attributes:
        user_id: User who owns this procedural memory
        trigger_pattern: Natural language description of trigger
        trigger_features: Structured features {intent, entity_types, topics}
        action_heuristic: Natural language description of action
        action_structure: Structured action {action_type, queries, predicates}
        observed_count: Number of times pattern was observed
        confidence: Pattern confidence [0.0, 1.0]
        created_at: Creation timestamp
        memory_id: Unique identifier (None before storage)
        embedding: 1536-dim embedding of trigger_pattern (None before embedding)
        updated_at: Last update timestamp (None before storage)

    Phase 1 Simplification:
    - Basic frequency-based detection (observed_count threshold)
    - Phase 2+: Use ML for more sophisticated pattern detection
    """

    user_id: str
    trigger_pattern: str
    trigger_features: dict[str, Any]
    action_heuristic: str
    action_structure: dict[str, Any]
    observed_count: int
    confidence: float
    created_at: datetime
    memory_id: int | None = None
    embedding: npt.NDArray[np.float64] | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate procedural memory."""
        if not self.user_id:
            msg = "user_id cannot be empty"
            raise ValueError(msg)

        if not self.trigger_pattern:
            msg = "trigger_pattern cannot be empty"
            raise ValueError(msg)

        if not self.action_heuristic:
            msg = "action_heuristic cannot be empty"
            raise ValueError(msg)

        if not 0.0 <= self.confidence <= 1.0:
            msg = f"confidence must be in [0, 1], got {self.confidence}"
            raise ValueError(msg)

        if self.observed_count < 1:
            msg = f"observed_count must be >= 1, got {self.observed_count}"
            raise ValueError(msg)

        # Validate embedding shape if present
        if self.embedding is not None:
            if not isinstance(self.embedding, np.ndarray):
                msg = "embedding must be numpy array"
                raise ValueError(msg)
            if self.embedding.shape != (1536,):
                msg = f"embedding must be 1536-dimensional, got {self.embedding.shape}"
                raise ValueError(
                    msg
                )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "trigger_pattern": self.trigger_pattern,
            "trigger_features": self.trigger_features,
            "action_heuristic": self.action_heuristic,
            "action_structure": self.action_structure,
            "observed_count": self.observed_count,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }

        if self.updated_at:
            result["updated_at"] = self.updated_at.isoformat()

        # Don't include embedding in dict (too large for JSON)
        # Embedding is stored separately in database

        return result

    @classmethod
    def from_pattern(
        cls,
        pattern: Pattern,
        user_id: str,
        created_at: datetime | None = None,
        embedding: npt.NDArray[np.float64] | None = None,
    ) -> "ProceduralMemory":
        """Create ProceduralMemory from Pattern.

        Args:
            pattern: Pattern to convert
            user_id: User identifier
            created_at: Creation timestamp (defaults to now)
            embedding: Embedding vector (optional, will be generated if None)

        Returns:
            ProceduralMemory instance
        """
        return cls(
            user_id=user_id,
            trigger_pattern=pattern.trigger_pattern,
            trigger_features=pattern.trigger_features,
            action_heuristic=pattern.action_heuristic,
            action_structure=pattern.action_structure,
            observed_count=pattern.observed_count,
            confidence=pattern.confidence,
            created_at=created_at or datetime.now(UTC),
            embedding=embedding,
        )

    def increment_observed_count(self) -> "ProceduralMemory":
        """Increment observed count and adjust confidence.

        Returns a new ProceduralMemory with updated count and confidence.

        Confidence formula (diminishing returns):
            new_confidence = min(0.95, old_confidence + 0.05 * (1.0 - old_confidence))

        Philosophy: Each observation increases confidence, but with diminishing
        returns. Max confidence is 0.95 (epistemic humility).
        """
        new_count = self.observed_count + 1

        # Diminishing returns on confidence boost
        boost = 0.05 * (1.0 - self.confidence)
        new_confidence = min(0.95, self.confidence + boost)

        return ProceduralMemory(
            memory_id=self.memory_id,
            user_id=self.user_id,
            trigger_pattern=self.trigger_pattern,
            trigger_features=self.trigger_features,
            action_heuristic=self.action_heuristic,
            action_structure=self.action_structure,
            observed_count=new_count,
            confidence=new_confidence,
            created_at=self.created_at,
            embedding=self.embedding,
            updated_at=datetime.now(UTC),
        )
