"""Ontology repository port (interface).

Defines the contract for domain ontology data access.
"""

from abc import ABC, abstractmethod
from typing import List

from src.domain.value_objects.ontology import OntologyRelation


class IOntologyRepository(ABC):
    """Interface for domain ontology data access.

    Hexagonal architecture: Domain defines the interface,
    infrastructure implements it.
    """

    @abstractmethod
    async def get_relations_for_type(self, entity_type: str) -> List[OntologyRelation]:
        """Get all ontology relations originating from an entity type.

        Args:
            entity_type: Entity type to get relations for

        Returns:
            List of ontology relations
        """
        pass

    @abstractmethod
    async def get_all_relations(self) -> List[OntologyRelation]:
        """Get all ontology relations.

        Returns:
            List of all ontology relations in the system
        """
        pass
