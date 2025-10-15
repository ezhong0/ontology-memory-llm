"""Entity alias domain model.

Represents an alias/alternative name for a canonical entity.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class EntityAlias:
    """Domain entity representing an alias for a canonical entity.

    Aliases are learned from:
    - User-stated equivalences: "Acme is short for Acme Corporation"
    - Fuzzy matches that were confirmed
    - Historical usage patterns

    Attributes:
        alias_id: Unique identifier (auto-generated, optional for new aliases)
        canonical_entity_id: ID of the canonical entity this aliases
        alias_text: The alias text (e.g., "Acme" for "Acme Corporation")
        alias_source: How this alias was learned (exact|fuzzy|learned|user_stated)
        user_id: User-specific alias (None = global)
        confidence: Confidence in this alias [0.0, 1.0]
        use_count: Number of times this alias has been used
        metadata: Additional metadata (e.g., context where alias was learned)
        created_at: When this alias was created
    """

    canonical_entity_id: str
    alias_text: str
    alias_source: str  # exact | fuzzy | learned | user_stated
    confidence: float
    alias_id: Optional[int] = None  # Set by repository after persistence
    user_id: Optional[str] = None  # None = global alias
    use_count: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate alias invariants."""
        if not self.canonical_entity_id:
            raise ValueError("canonical_entity_id cannot be empty")
        if not self.alias_text:
            raise ValueError("alias_text cannot be empty")
        if not self.alias_source:
            raise ValueError("alias_source cannot be empty")

        valid_sources = {"exact", "fuzzy", "learned", "user_stated"}
        if self.alias_source not in valid_sources:
            raise ValueError(
                f"alias_source must be one of {valid_sources}, got: {self.alias_source}"
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")

        if self.use_count < 1:
            raise ValueError(f"use_count must be >= 1, got {self.use_count}")

    def increment_use_count(self) -> None:
        """Increment usage counter and potentially boost confidence."""
        self.use_count += 1

        # Boost confidence slightly with repeated use (max 0.95)
        if self.confidence < 0.95:
            boost = 0.02 * (1.0 - self.confidence)  # Smaller boost as confidence approaches 1.0
            self.confidence = min(0.95, self.confidence + boost)

    def is_global(self) -> bool:
        """Check if this is a global alias (not user-specific).

        Returns:
            True if user_id is None
        """
        return self.user_id is None

    def is_user_specific(self) -> bool:
        """Check if this is a user-specific alias.

        Returns:
            True if user_id is not None
        """
        return self.user_id is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        result: dict[str, Any] = {
            "canonical_entity_id": self.canonical_entity_id,
            "alias_text": self.alias_text,
            "alias_source": self.alias_source,
            "confidence": self.confidence,
            "use_count": self.use_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

        if self.alias_id is not None:
            result["alias_id"] = self.alias_id
        if self.user_id is not None:
            result["user_id"] = self.user_id

        return result

    def __str__(self) -> str:
        """String representation for logging."""
        scope = f"user={self.user_id}" if self.user_id else "global"
        return (
            f'"{self.alias_text}" → {self.canonical_entity_id} '
            f'({scope}, source={self.alias_source}, confidence={self.confidence:.2f})'
        )

    def __eq__(self, other: object) -> bool:
        """Aliases are equal if they have the same alias_id."""
        if not isinstance(other, EntityAlias):
            return False
        # If either has no ID, compare by canonical_entity_id + alias_text + user_id
        if self.alias_id is None or other.alias_id is None:
            return (
                self.canonical_entity_id == other.canonical_entity_id
                and self.alias_text == other.alias_text
                and self.user_id == other.user_id
            )
        return self.alias_id == other.alias_id

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        if self.alias_id is not None:
            return hash(self.alias_id)
        return hash((self.canonical_entity_id, self.alias_text, self.user_id))
