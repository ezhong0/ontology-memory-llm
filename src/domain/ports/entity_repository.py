"""Entity repository port (interface).

Defines the contract for entity persistence without implementation details.
"""
from typing import Optional, Protocol

from src.domain.entities import CanonicalEntity, EntityAlias


class IEntityRepository(Protocol):
    """Repository interface for canonical entities and aliases.

    This is a port (interface) in hexagonal architecture. The domain defines
    what it needs from persistence without knowing implementation details.

    Infrastructure layer will implement this using SQLAlchemy/PostgreSQL.
    """

    async def find_by_canonical_name(self, name: str) -> Optional[CanonicalEntity]:
        """Find entity by exact canonical name.

        Args:
            name: Exact canonical name to search for

        Returns:
            CanonicalEntity if found, None otherwise
        """
        ...

    async def find_by_entity_id(self, entity_id: str) -> Optional[CanonicalEntity]:
        """Find entity by entity ID.

        Args:
            entity_id: Entity ID to search for

        Returns:
            CanonicalEntity if found, None otherwise
        """
        ...

    async def find_by_alias(
        self, alias: str, user_id: Optional[str] = None
    ) -> Optional[CanonicalEntity]:
        """Find entity by alias (user-specific or global).

        Searches in priority order:
        1. User-specific aliases (if user_id provided)
        2. Global aliases

        Args:
            alias: Alias text to search for
            user_id: User ID for user-specific aliases (optional)

        Returns:
            CanonicalEntity if alias found, None otherwise
        """
        ...

    async def fuzzy_search(
        self, search_text: str, threshold: float = 0.6, limit: int = 5
    ) -> list[tuple[CanonicalEntity, float]]:
        """Fuzzy search entities using pg_trgm similarity.

        Args:
            search_text: Text to search for
            threshold: Minimum similarity threshold [0.0, 1.0]
            limit: Maximum number of results

        Returns:
            List of (entity, similarity_score) tuples, sorted by similarity descending
        """
        ...

    async def create(self, entity: CanonicalEntity) -> CanonicalEntity:
        """Create a new canonical entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity (with any generated fields populated)

        Raises:
            ValueError: If entity with same entity_id already exists
        """
        ...

    async def update(self, entity: CanonicalEntity) -> CanonicalEntity:
        """Update an existing canonical entity.

        Args:
            entity: Entity to update

        Returns:
            Updated entity

        Raises:
            ValueError: If entity not found
        """
        ...

    async def create_alias(self, alias: EntityAlias) -> EntityAlias:
        """Create a new entity alias.

        Args:
            alias: Alias to create

        Returns:
            Created alias (with alias_id populated)

        Raises:
            ValueError: If alias already exists for this entity
        """
        ...

    async def get_aliases(self, entity_id: str) -> list[EntityAlias]:
        """Get all aliases for an entity.

        Args:
            entity_id: Entity ID to get aliases for

        Returns:
            List of aliases (may be empty)
        """
        ...

    async def increment_alias_use_count(self, alias_id: int) -> None:
        """Increment use count for an alias.

        Args:
            alias_id: Alias ID to increment
        """
        ...
