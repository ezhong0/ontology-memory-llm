"""Procedural memory value objects.

These objects represent learned patterns and heuristics for query augmentation.

Design from: PHASE1D_PLAN_ITERATION.md
Vision: Layer 5 - Learning from interaction patterns
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Optional

import numpy as np
from numpy import typing as npt


@dataclass(frozen=True)
class Pattern:
    """A learned pattern extracted from episodic memories.

    Represents a "When X, also Y" heuristic before storage.

    Vision: Learning from interaction patterns to augment future retrievals.

    Attributes:
        trigger_pattern: Natural language description of trigger
        trigger_features: Structured features {intent, entity_types, topics}
        action_heuristic: Natural language description of action
        action_structure: Structured action {action_type, queries, predicates}
        observed_count: Number of times pattern was observed
        confidence: Pattern confidence [0.0, 1.0]
        source_episode_ids: Episode IDs that contributed to this pattern

    Example:
        >>> pattern = Pattern(
        ...     trigger_pattern="User asks about customer payment history",
        ...     trigger_features={
        ...         "intent": "query_payment_history",
        ...         "entity_types": ["customer"],
        ...         "topics": ["payments", "invoices"]
        ...     },
        ...     action_heuristic="Also retrieve open invoices and credit status",
        ...     action_structure={
        ...         "action_type": "retrieve_related",
        ...         "queries": ["open_invoices", "credit_status"],
        ...         "predicates": ["has_open_invoice", "credit_limit"]
        ...     },
        ...     observed_count=5,
        ...     confidence=0.85,
        ...     source_episode_ids=[12, 24, 35, 42, 58]
        ... )
    """

    trigger_pattern: str
    trigger_features: dict[str, Any]
    action_heuristic: str
    action_structure: dict[str, Any]
    observed_count: int
    confidence: float
    source_episode_ids: list[int]

    def __post_init__(self) -> None:
        """Validate pattern."""
        if not self.trigger_pattern:
            raise ValueError("trigger_pattern cannot be empty")

        if not self.action_heuristic:
            raise ValueError("action_heuristic cannot be empty")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")

        if self.observed_count < 1:
            raise ValueError(f"observed_count must be >= 1, got {self.observed_count}")

        # Validate required feature keys
        required_features = ["intent", "entity_types", "topics"]
        for key in required_features:
            if key not in self.trigger_features:
                raise ValueError(f"trigger_features must contain '{key}'")

        # Validate required action keys
        required_actions = ["action_type", "queries", "predicates"]
        for key in required_actions:
            if key not in self.action_structure:
                raise ValueError(f"action_structure must contain '{key}'")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trigger_pattern": self.trigger_pattern,
            "trigger_features": self.trigger_features,
            "action_heuristic": self.action_heuristic,
            "action_structure": self.action_structure,
            "observed_count": self.observed_count,
            "confidence": self.confidence,
            "source_episode_ids": self.source_episode_ids,
        }


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
    memory_id: Optional[int] = None
    embedding: Optional[npt.NDArray[np.float64]] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate procedural memory."""
        if not self.user_id:
            raise ValueError("user_id cannot be empty")

        if not self.trigger_pattern:
            raise ValueError("trigger_pattern cannot be empty")

        if not self.action_heuristic:
            raise ValueError("action_heuristic cannot be empty")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")

        if self.observed_count < 1:
            raise ValueError(f"observed_count must be >= 1, got {self.observed_count}")

        # Validate embedding shape if present
        if self.embedding is not None:
            if not isinstance(self.embedding, np.ndarray):
                raise ValueError("embedding must be numpy array")
            if self.embedding.shape != (1536,):
                raise ValueError(f"embedding must be 1536-dimensional, got {self.embedding.shape}")

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
        created_at: Optional[datetime] = None,
        embedding: Optional[npt.NDArray[np.float64]] = None,
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
