"""Memory Summary entity.

A consolidated memory summary with identity and lifecycle.
This is an ENTITY (not a value object) because it has:
- Identity (summary_id)
- Mutable state
- Lifecycle (created, updated, superseded)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class MemorySummary:
    """A consolidated memory summary.

    Result of consolidation stored in memory_summaries table.

    Attributes:
        summary_id: Unique identifier (None before storage)
        user_id: User who owns this summary
        scope_type: Scope type (entity, topic, session_window)
        scope_identifier: Scope identifier
        summary_text: Concise narrative summary
        key_facts: Dictionary of key facts
        source_data: Metadata about source memories
        confidence: Overall summary confidence
        embedding: 1536-dim embedding vector (None before embedding)
        created_at: Creation timestamp
        supersedes_summary_id: Previous summary this replaces (if any)
    """

    user_id: str
    scope_type: str
    scope_identifier: str
    summary_text: str
    key_facts: dict[str, dict[str, Any]]
    source_data: dict[str, Any]
    confidence: float
    created_at: datetime
    summary_id: int | None = None
    embedding: list[float] | None = None
    supersedes_summary_id: int | None = None

    def __post_init__(self) -> None:
        """Validate memory summary."""
        if not 0.0 <= self.confidence <= 1.0:
            msg = f"confidence must be in [0, 1], got {self.confidence}"
            raise ValueError(msg)

        valid_scopes = ["entity", "topic", "session_window"]
        if self.scope_type not in valid_scopes:
            msg = f"scope_type must be one of {valid_scopes}"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "summary_id": self.summary_id,
            "user_id": self.user_id,
            "scope_type": self.scope_type,
            "scope_identifier": self.scope_identifier,
            "summary_text": self.summary_text,
            "key_facts": self.key_facts,
            "source_data": self.source_data,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "supersedes_summary_id": self.supersedes_summary_id,
        }
