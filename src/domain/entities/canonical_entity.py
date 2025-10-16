"""Canonical entity domain model.

Represents a resolved, canonical entity in the memory system.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.domain.value_objects import EntityReference


@dataclass
class CanonicalEntity:
    """Domain entity representing a canonical (resolved) entity.

    A canonical entity is the system's internal representation of a real-world
    entity (customer, order, product, etc.). It links conversational mentions
    to domain database records.

    Attributes:
        entity_id: Unique identifier (format: "{entity_type}_{external_id}")
        entity_type: Type of entity (e.g., "customer", "order", "product")
        canonical_name: Canonical display name
        external_ref: Reference to external domain database record
        properties: Additional properties from domain DB (cached)
        created_at: When this entity was first created
        updated_at: When this entity was last updated
    """

    entity_id: str
    entity_type: str
    canonical_name: str
    external_ref: EntityReference
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate entity invariants."""
        if not self.entity_id:
            msg = "entity_id cannot be empty"
            raise ValueError(msg)
        if not self.entity_type:
            msg = "entity_type cannot be empty"
            raise ValueError(msg)
        if not self.canonical_name:
            msg = "canonical_name cannot be empty"
            raise ValueError(msg)

        # Validate entity_id format
        if "_" not in self.entity_id:
            msg = f"entity_id must follow format '{{type}}_{{id}}', got: {self.entity_id}"
            raise ValueError(
                msg
            )

        # Verify entity_id starts with entity_type
        expected_prefix = f"{self.entity_type}_"
        if not self.entity_id.startswith(expected_prefix):
            msg = f"entity_id must start with '{expected_prefix}', got: {self.entity_id}"
            raise ValueError(
                msg
            )

    def update_properties(self, new_properties: dict[str, Any]) -> None:
        """Update cached properties from domain database.

        Args:
            new_properties: New properties to merge
        """
        self.properties.update(new_properties)
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "canonical_name": self.canonical_name,
            "external_ref": self.external_ref.to_dict(),
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def generate_entity_id(cls, entity_type: str, external_value: Any) -> str:
        """Generate a canonical entity ID.

        Args:
            entity_type: Type of entity (e.g., "customer", "order")
            external_value: External primary key value

        Returns:
            Entity ID in format: "{entity_type}_{external_value}"
        """
        return f"{entity_type}_{external_value}"

    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.canonical_name} (id={self.entity_id}, type={self.entity_type})"

    def __eq__(self, other: object) -> bool:
        """Entities are equal if they have the same entity_id."""
        if not isinstance(other, CanonicalEntity):
            return False
        return self.entity_id == other.entity_id

    def __hash__(self) -> int:
        """Hash based on entity_id for use in sets/dicts."""
        return hash(self.entity_id)
