"""Ontology repository implementation.

Implements domain ontology retrieval using SQLAlchemy and PostgreSQL.
"""

from typing import List

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import RepositoryError
from src.domain.ports.ontology_repository import IOntologyRepository
from src.domain.value_objects.ontology import OntologyRelation

logger = structlog.get_logger(__name__)


class OntologyRepository(IOntologyRepository):
    """SQLAlchemy implementation of ontology repository.

    Retrieves domain ontology relationships from the domain_ontology table.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_relations_for_type(self, entity_type: str) -> List[OntologyRelation]:
        """Get all ontology relations originating from an entity type.

        Args:
            entity_type: Entity type to get relations for

        Returns:
            List of ontology relations
        """
        try:
            stmt = text(
                """
                SELECT
                    relation_id, from_entity_type, relation_type, to_entity_type,
                    cardinality, relation_semantics, join_spec, constraints
                FROM app.domain_ontology
                WHERE from_entity_type = :entity_type
                ORDER BY relation_type
                """
            )

            result = await self.session.execute(stmt, {"entity_type": entity_type})

            relations = []
            for row in result:
                relation = OntologyRelation(
                    relation_id=row.relation_id,
                    from_entity_type=row.from_entity_type,
                    relation_type=row.relation_type,
                    to_entity_type=row.to_entity_type,
                    cardinality=row.cardinality,
                    relation_semantics=row.relation_semantics,
                    join_spec=row.join_spec,
                    constraints=row.constraints,
                )
                relations.append(relation)

            logger.debug(
                "found_ontology_relations",
                entity_type=entity_type,
                count=len(relations),
            )

            return relations

        except Exception as e:
            logger.error(
                "get_relations_error",
                entity_type=entity_type,
                error=str(e),
            )
            raise RepositoryError(f"Error getting ontology relations: {e}") from e

    async def get_all_relations(self) -> List[OntologyRelation]:
        """Get all ontology relations.

        Returns:
            List of all ontology relations
        """
        try:
            stmt = text(
                """
                SELECT
                    relation_id, from_entity_type, relation_type, to_entity_type,
                    cardinality, relation_semantics, join_spec, constraints
                FROM app.domain_ontology
                ORDER BY from_entity_type, relation_type
                """
            )

            result = await self.session.execute(stmt)

            relations = []
            for row in result:
                relation = OntologyRelation(
                    relation_id=row.relation_id,
                    from_entity_type=row.from_entity_type,
                    relation_type=row.relation_type,
                    to_entity_type=row.to_entity_type,
                    cardinality=row.cardinality,
                    relation_semantics=row.relation_semantics,
                    join_spec=row.join_spec,
                    constraints=row.constraints,
                )
                relations.append(relation)

            logger.debug("found_all_ontology_relations", count=len(relations))

            return relations

        except Exception as e:
            logger.error("get_all_relations_error", error=str(e))
            raise RepositoryError(f"Error getting all ontology relations: {e}") from e
