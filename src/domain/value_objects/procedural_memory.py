"""Procedural memory value objects.

These objects represent learned patterns before storage.

Note: ProceduralMemory has been moved to src/domain/entities/procedural_memory.py
(it's an entity with identity and lifecycle, not a value object).

Design from: PHASE1D_PLAN_ITERATION.md
Vision: Layer 5 - Learning from interaction patterns
"""

from dataclasses import dataclass
from typing import Any


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

        # Validate required feature keys
        required_features = ["intent", "entity_types", "topics"]
        for key in required_features:
            if key not in self.trigger_features:
                msg = f"trigger_features must contain '{key}'"
                raise ValueError(msg)

        # Validate required action keys
        required_actions = ["action_type", "queries", "predicates"]
        for key in required_actions:
            if key not in self.action_structure:
                msg = f"action_structure must contain '{key}'"
                raise ValueError(msg)

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
