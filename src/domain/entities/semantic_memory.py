"""Semantic memory domain entity.

Represents entity-tagged natural language memory with importance scoring.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

@dataclass
class SemanticMemory:
    """Domain entity representing a semantic memory.

    A semantic memory is entity-tagged natural language extracted from conversation.
    Uses importance scoring (not reinforcement count) and relies on semantic search
    rather than structured predicate queries.

    Attributes:
        memory_id: Database primary key (None if not yet persisted)
        user_id: User who owns this memory
        content: The memory text (e.g., "Gai Media prefers Friday deliveries")
        entities: All entity IDs mentioned in this memory
        confidence: Confidence in this memory [0.0, 1.0]
        importance: Dynamic importance score [0.0, 1.0] (replaces reinforcement_count)
        status: Memory status (active, inactive, conflicted)
        source_event_ids: Chat event IDs that contributed to this memory
        embedding: Vector embedding for similarity search (1536 dimensions)
        source_text: Original chat message that created this memory
        metadata: Optional structured data (confirmations, tags, etc.)
        created_at: When this memory was first created
        updated_at: When this memory was last updated
        last_accessed_at: When this memory was last accessed (for decay)
    """

    user_id: str
    content: str  # The actual memory text
    entities: list[str]  # All entity IDs mentioned
    confidence: float  # Confidence in accuracy [0.0, 1.0]
    importance: float  # Dynamic importance [0.0, 1.0]
    status: str = "active"
    source_event_ids: list[int] = field(default_factory=list)
    embedding: list[float] | None = None
    source_text: str | None = None  # Original chat message for explainability
    metadata: dict[str, Any] = field(default_factory=dict)  # Flexible metadata storage
    memory_id: int | None = None
    superseded_by_memory_id: int | None = None  # Phase 2: Track supersession chain
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate semantic memory invariants."""
        if not self.user_id:
            msg = "user_id cannot be empty"
            raise ValueError(msg)
        if not self.content:
            msg = "content cannot be empty"
            raise ValueError(msg)
        if not isinstance(self.entities, list):
            msg = f"entities must be list, got: {type(self.entities)}"
            raise ValueError(msg)
        if not self.entities:
            msg = "entities list cannot be empty"
            raise ValueError(msg)
        if not (0.0 <= self.confidence <= 1.0):
            msg = f"confidence must be in [0.0, 1.0], got: {self.confidence}"
            raise ValueError(msg)
        if not (0.0 <= self.importance <= 1.0):
            msg = f"importance must be in [0.0, 1.0], got: {self.importance}"
            raise ValueError(msg)
        if self.status not in ["active", "inactive", "conflicted", "superseded", "invalidated", "aging"]:
            msg = f"status must be active/inactive/conflicted/superseded/invalidated/aging, got: {self.status}"
            raise ValueError(msg)
        if not isinstance(self.metadata, dict):
            msg = f"metadata must be dict, got: {type(self.metadata)}"
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
    def is_high_importance(self) -> bool:
        """Check if memory has high importance (>= 0.7)."""
        return self.importance >= 0.7

    @property
    def days_since_last_access(self) -> int:
        """Calculate days since last access (for decay calculation).

        Returns:
            Number of days since last_accessed_at
        """
        delta = datetime.now(UTC) - self.last_accessed_at
        return delta.days

    @property
    def confirmation_count(self) -> int:
        """Get confirmation count from metadata.

        Returns:
            Number of confirmations (0 if never confirmed)
        """
        return self.metadata.get("confirmation_count", 0)

    def confirm(self, new_event_id: int, importance_boost: float = 0.05) -> None:
        """Confirm memory with new observation (replaces reinforce).

        Args:
            new_event_id: Event ID of new observation
            importance_boost: Importance increase per confirmation (default: 0.05)
        """
        # Increment confirmation count in metadata
        self.metadata["confirmation_count"] = self.confirmation_count + 1

        # Track confirmation source
        if "confirmation_sources" not in self.metadata:
            self.metadata["confirmation_sources"] = []
        self.metadata["confirmation_sources"].append(new_event_id)
        self.metadata["last_confirmed_at"] = datetime.now(UTC).isoformat()

        # Boost importance (capped at 1.0)
        self.importance = min(1.0, self.importance + importance_boost)

        # Boost confidence slightly
        self.confidence = min(0.95, self.confidence + 0.02)

        # Add to source events if not already present
        if new_event_id not in self.source_event_ids:
            self.source_event_ids.append(new_event_id)

        # Update timestamps
        self.last_accessed_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def apply_decay(self, decay_rate: float = 0.01) -> None:
        """Apply temporal importance decay based on days since last access.

        Args:
            decay_rate: Decay rate (default: 0.01, ~69 day half-life)
        """
        import math
        days = self.days_since_last_access
        decay_factor = max(0.5, math.exp(-decay_rate * days))
        new_importance = self.importance * decay_factor

        if new_importance < self.importance:
            self.importance = max(0.0, new_importance)
            self.updated_at = datetime.now(UTC)

    def mark_accessed(self) -> None:
        """Mark memory as accessed (updates last_accessed_at)."""
        self.last_accessed_at = datetime.now(UTC)

    def mark_as_conflicted(self) -> None:
        """Mark memory as conflicted."""
        self.status = "conflicted"
        self.updated_at = datetime.now(UTC)

    def mark_as_inactive(self) -> None:
        """Mark memory as inactive."""
        self.status = "inactive"
        self.updated_at = datetime.now(UTC)

    def mark_as_superseded(self, superseded_by_memory_id: int | None) -> None:
        """Mark memory as superseded by another memory.

        Args:
            superseded_by_memory_id: ID of memory that supersedes this one (None if not yet created)
        """
        self.status = "superseded"
        self.superseded_by_memory_id = superseded_by_memory_id
        self.updated_at = datetime.now(UTC)

    def mark_as_invalidated(self) -> None:
        """Mark memory as invalidated (contradicts authoritative source)."""
        self.status = "invalidated"
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation (without embedding for size)
        """
        return {
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "content": self.content,
            "entities": self.entities,
            "confidence": self.confidence,
            "importance": self.importance,
            "status": self.status,
            "source_event_ids": self.source_event_ids,
            "source_text": self.source_text,
            "metadata": self.metadata,
            "confirmation_count": self.confirmation_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_accessed_at": self.last_accessed_at.isoformat(),
        }

    def __str__(self) -> str:
        """String representation for logging."""
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        entity_str = ", ".join(self.entities[:2])
        if len(self.entities) > 2:
            entity_str += f", +{len(self.entities) - 2} more"
        return (
            f"Memory({self.memory_id}): \"{content_preview}\" "
            f"[{entity_str}] "
            f"(imp={self.importance:.2f}, conf={self.confidence:.2f}, confirmations={self.confirmation_count})"
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
