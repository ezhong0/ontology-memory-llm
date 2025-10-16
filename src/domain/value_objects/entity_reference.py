"""Entity reference value object.

Represents a reference to an external domain database entity (immutable).
"""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntityReference:
    """Immutable reference to an external domain database entity.

    Links a canonical entity to its source record in the domain database
    (e.g., ERP system, CRM, etc.).

    Attributes:
        table: Source table name (e.g., "customers", "orders", "products")
        primary_key: Primary key column name (e.g., "id", "customer_id")
        primary_value: Primary key value (e.g., 12345, "ORD-2024-001")
        display_name: Human-readable name from domain DB
        properties: Additional properties from domain DB (optional)
    """

    table: str
    primary_key: str
    primary_value: Any  # Can be int, str, UUID, etc.
    display_name: str
    properties: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate entity reference invariants."""
        if not self.table:
            msg = "table name cannot be empty"
            raise ValueError(msg)
        if not self.primary_key:
            msg = "primary_key name cannot be empty"
            raise ValueError(msg)
        if self.primary_value is None:
            msg = "primary_value cannot be None"
            raise ValueError(msg)
        if not self.display_name:
            msg = "display_name cannot be empty"
            raise ValueError(msg)

    @property
    def external_id(self) -> str:
        """Get external ID in standard format.

        Returns:
            Format: "table:primary_key=value" (e.g., "customers:id=12345")
        """
        return f"{self.table}:{self.primary_key}={self.primary_value}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with table, primary_key, primary_value, display_name
        """
        result: dict[str, Any] = {
            "table": self.table,
            "primary_key": self.primary_key,
            "primary_value": self.primary_value,
            "display_name": self.display_name,
            "properties": self.properties,
        }
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EntityReference":
        """Create EntityReference from dictionary.

        Args:
            data: Dictionary with entity reference fields

        Returns:
            EntityReference instance

        Raises:
            ValueError: If required fields are missing
        """
        return cls(
            table=data["table"],
            primary_key=data["primary_key"],
            primary_value=data["primary_value"],
            display_name=data["display_name"],
            properties=data.get("properties"),
        )

    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.display_name} (external_id={self.external_id})"
