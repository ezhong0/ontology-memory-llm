"""Ontology value objects for domain graph traversal.

These objects represent semantic relationships between entity types
in the domain database.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OntologyRelation:
    """A semantic relationship between entity types.

    Represents how entity types relate to each other with business semantics,
    not just SQL foreign keys.

    Vision: "Foreign keys connect tables. Ontology connects meaning."

    Attributes:
        relation_id: Unique identifier
        from_entity_type: Source entity type (e.g., "customer")
        relation_type: Semantic relation (HAS_MANY, CREATES, REQUIRES, FULFILLS)
        to_entity_type: Target entity type (e.g., "sales_order")
        cardinality: Relationship cardinality (one_to_one, one_to_many, many_to_many)
        relation_semantics: Human-readable description of the relationship
        join_spec: SQL join specification for traversing the relationship
        constraints: Optional business logic constraints
    """

    relation_id: int
    from_entity_type: str
    relation_type: str
    to_entity_type: str
    cardinality: str
    relation_semantics: str
    join_spec: dict[str, Any]
    constraints: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate ontology relation."""
        valid_cardinalities = ["one_to_one", "one_to_many", "many_to_many"]
        if self.cardinality not in valid_cardinalities:
            msg = f"cardinality must be one of {valid_cardinalities}, got {self.cardinality}"
            raise ValueError(
                msg
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "relation_id": self.relation_id,
            "from_entity_type": self.from_entity_type,
            "relation_type": self.relation_type,
            "to_entity_type": self.to_entity_type,
            "cardinality": self.cardinality,
            "relation_semantics": self.relation_semantics,
            "join_spec": self.join_spec,
            "constraints": self.constraints,
        }


@dataclass(frozen=True)
class EntityGraph:
    """A graph of related entities starting from a root entity.

    Result of ontology-aware graph traversal.

    Attributes:
        root_entity_id: Starting entity ID
        root_entity_type: Starting entity type
        related_entities: Nested dict of related entities by relation type
        traversal_depth: Maximum depth traversed
    """

    root_entity_id: str
    root_entity_type: str
    related_entities: dict[str, list[dict[str, Any]]]
    traversal_depth: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "root_entity_id": self.root_entity_id,
            "root_entity_type": self.root_entity_type,
            "related_entities": self.related_entities,
            "traversal_depth": self.traversal_depth,
        }
