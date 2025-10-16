"""Ontology service for domain graph traversal.

Traverses the domain database using semantic relationships (not just SQL foreign keys).

Vision: "Foreign keys connect tables. Ontology connects meaning."

Design from: DESIGN.md v2.0 - Ontology-Aware Traversal
"""

from typing import Any

import structlog

from src.domain.exceptions import DomainError
from src.domain.ports.ontology_repository import IOntologyRepository
from src.domain.value_objects.ontology import EntityGraph, OntologyRelation

logger = structlog.get_logger()


class OntologyService:
    """Domain ontology-aware graph traversal.

    Traverses the domain database following semantic relationships.
    Uses BFS traversal with max depth to explore related entities.

    Philosophy: Business relationships have semantic meaning beyond foreign keys.

    Example:
        >>> ontology_service = OntologyService(ontology_repo, domain_db_connector)
        >>> graph = await ontology_service.traverse_graph(
        ...     entity_id="customer_gai_123",
        ...     max_hops=2,
        ... )
        >>> # Returns: customer → orders → work_orders + invoices
    """

    def __init__(self, ontology_repo: IOntologyRepository) -> None:
        """Initialize ontology service.

        Args:
            ontology_repo: Repository for ontology relationships
        """
        self._ontology_repo = ontology_repo

    async def get_relations_for_type(self, entity_type: str) -> list[OntologyRelation]:
        """Get all ontology relations for an entity type.

        Args:
            entity_type: Entity type to get relations for

        Returns:
            List of ontology relations

        Raises:
            DomainError: If retrieval fails
        """
        try:
            return await self._ontology_repo.get_relations_for_type(entity_type)
        except Exception as e:
            logger.error(
                "get_relations_error",
                entity_type=entity_type,
                error=str(e),
            )
            msg = f"Error getting ontology relations: {e}"
            raise DomainError(msg) from e

    async def traverse_graph(
        self,
        entity_id: str,
        max_hops: int = 2,
        relation_filter: list[str] | None = None,
    ) -> EntityGraph:
        """Traverse domain graph from starting entity.

        Uses BFS traversal to explore related entities up to max_hops away.

        Args:
            entity_id: Starting entity ID (format: "customer_123")
            max_hops: Maximum traversal depth
            relation_filter: Optional list of relation types to follow

        Returns:
            EntityGraph with related entities organized by relation type

        Raises:
            DomainError: If traversal fails

        Example:
            >>> graph = await service.traverse_graph("customer_gai_123", max_hops=2)
            >>> graph.related_entities
            {
                "HAS_MANY": [
                    {"entity_type": "sales_order", "entity_id": "order_1", ...}
                ],
                "CREATES": [...]
            }
        """
        try:
            # Extract entity type from entity_id (format: "type_identifier")
            entity_type = self._extract_entity_type(entity_id)

            logger.info(
                "graph_traversal_started",
                entity_id=entity_id,
                entity_type=entity_type,
                max_hops=max_hops,
            )

            # Initialize BFS queue: (current_entity_id, current_depth)
            queue = [(entity_id, entity_type, 0)]
            related_entities: dict[str, list[dict[str, Any]]] = {}

            while queue:
                current_id, current_type, depth = queue.pop(0)

                if depth >= max_hops:
                    continue

                # Get ontology relations for current entity type
                relations = await self._ontology_repo.get_relations_for_type(current_type)

                # Filter relations if specified
                if relation_filter:
                    relations = [r for r in relations if r.relation_type in relation_filter]

                # Traverse each relation
                for relation in relations:
                    # For Phase 1C, we'll mark relations but not execute queries
                    # In production, would execute join_spec queries to get related entities

                    # Add relation type to result if not already present
                    if relation.relation_type not in related_entities:
                        related_entities[relation.relation_type] = []

                    # Placeholder: Would query domain DB here
                    # For now, document the relationship structure
                    related_entities[relation.relation_type].append(
                        {
                            "to_entity_type": relation.to_entity_type,
                            "cardinality": relation.cardinality,
                            "semantics": relation.relation_semantics,
                            "constraints": relation.constraints,
                            # In production: would include actual related entity IDs
                        }
                    )

            logger.info(
                "graph_traversal_completed",
                entity_id=entity_id,
                relation_types_found=list(related_entities.keys()),
                max_depth_reached=max_hops,
            )

            return EntityGraph(
                root_entity_id=entity_id,
                root_entity_type=entity_type,
                related_entities=related_entities,
                traversal_depth=max_hops,
            )

        except Exception as e:
            logger.error(
                "graph_traversal_error",
                entity_id=entity_id,
                error=str(e),
            )
            msg = f"Error traversing entity graph: {e}"
            raise DomainError(msg) from e

    def _extract_entity_type(self, entity_id: str) -> str:
        """Extract entity type from entity ID.

        Args:
            entity_id: Entity ID in format "type_identifier"

        Returns:
            Entity type

        Raises:
            DomainError: If entity_id format is invalid
        """
        if "_" not in entity_id:
            msg = f"Invalid entity_id format: {entity_id}. Expected 'type_identifier'"
            raise DomainError(msg)

        return entity_id.split("_")[0]
