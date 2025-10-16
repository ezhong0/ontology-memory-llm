"""Entity repository implementation.

Implements IEntityRepository using SQLAlchemy and PostgreSQL.
"""

import structlog
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import CanonicalEntity, EntityAlias
from src.domain.exceptions import RepositoryError
from src.domain.ports import IEntityRepository
from src.domain.value_objects import EntityReference
from src.infrastructure.database.models import (
    CanonicalEntity as CanonicalEntityModel,
)
from src.infrastructure.database.models import (
    EntityAlias as EntityAliasModel,
)

logger = structlog.get_logger(__name__)


class EntityRepository(IEntityRepository):
    """SQLAlchemy implementation of IEntityRepository.

    Maps between domain entities and SQLAlchemy ORM models.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def find_by_canonical_name(self, name: str) -> CanonicalEntity | None:
        """Find entity by exact canonical name (case-insensitive).

        Args:
            name: Exact canonical name to search for

        Returns:
            CanonicalEntity if found, None otherwise
        """
        try:
            stmt = select(CanonicalEntityModel).where(
                func.lower(CanonicalEntityModel.canonical_name) == func.lower(name)
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            return self._to_domain_entity(model) if model else None

        except Exception as e:
            logger.error("find_by_canonical_name_error", name=name, error=str(e))
            msg = f"Error finding entity by name: {e}"
            raise RepositoryError(msg) from e

    async def find_by_entity_id(self, entity_id: str) -> CanonicalEntity | None:
        """Find entity by entity ID.

        Args:
            entity_id: Entity ID to search for

        Returns:
            CanonicalEntity if found, None otherwise
        """
        try:
            stmt = select(CanonicalEntityModel).where(
                CanonicalEntityModel.entity_id == entity_id
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            return self._to_domain_entity(model) if model else None

        except Exception as e:
            logger.error("find_by_entity_id_error", entity_id=entity_id, error=str(e))
            msg = f"Error finding entity by ID: {e}"
            raise RepositoryError(msg) from e

    async def find_by_alias(
        self, alias: str, user_id: str | None = None
    ) -> CanonicalEntity | None:
        """Find entity by alias (user-specific or global).

        Priority: user-specific aliases first, then global.

        Args:
            alias: Alias text to search for
            user_id: User ID for user-specific aliases

        Returns:
            CanonicalEntity if alias found, None otherwise
        """
        try:
            # Build query: search user-specific first, then global
            if user_id:
                # Try user-specific first
                stmt = (
                    select(CanonicalEntityModel)
                    .join(EntityAliasModel)
                    .where(
                        and_(
                            func.lower(EntityAliasModel.alias_text) == func.lower(alias),
                            EntityAliasModel.user_id == user_id,
                        )
                    )
                )
                result = await self.session.execute(stmt)
                model = result.scalar_one_or_none()

                if model:
                    return self._to_domain_entity(model)

            # Try global alias
            stmt = (
                select(CanonicalEntityModel)
                .join(EntityAliasModel)
                .where(
                    and_(
                        func.lower(EntityAliasModel.alias_text) == func.lower(alias),
                        EntityAliasModel.user_id.is_(None),
                    )
                )
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            return self._to_domain_entity(model) if model else None

        except Exception as e:
            logger.error("find_by_alias_error", alias=alias, error=str(e))
            msg = f"Error finding entity by alias: {e}"
            raise RepositoryError(msg) from e

    async def fuzzy_search(
        self, search_text: str, threshold: float = 0.6, limit: int = 5
    ) -> list[tuple[CanonicalEntity, float]]:
        """Fuzzy search using pg_trgm similarity.

        Uses PostgreSQL pg_trgm extension for trigram similarity matching.

        Args:
            search_text: Text to search for
            threshold: Minimum similarity threshold [0.0, 1.0]
            limit: Maximum number of results

        Returns:
            List of (entity, similarity_score) tuples, sorted by similarity descending
        """
        try:
            # Use pg_trgm similarity function
            stmt = text(
                """
                SELECT entity_id, canonical_name, entity_type, external_ref,
                       properties, created_at, updated_at,
                       similarity(canonical_name, :search_text) as sim_score
                FROM app.canonical_entities
                WHERE similarity(canonical_name, :search_text) > :threshold
                ORDER BY sim_score DESC
                LIMIT :limit
                """
            )

            result = await self.session.execute(
                stmt,
                {
                    "search_text": search_text,
                    "threshold": threshold,
                    "limit": limit,
                },
            )

            matches: list[tuple[CanonicalEntity, float]] = []
            for row in result:
                # Convert row to domain entity using from_dict to handle JSONB properly
                entity_ref = EntityReference.from_dict(row.external_ref)

                entity = CanonicalEntity(
                    entity_id=row.entity_id,
                    entity_type=row.entity_type,
                    canonical_name=row.canonical_name,
                    external_ref=entity_ref,
                    properties=row.properties or {},
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )

                matches.append((entity, float(row.sim_score)))

            return matches

        except Exception as e:
            logger.error("fuzzy_search_error", search_text=search_text, error=str(e))
            msg = f"Error in fuzzy search: {e}"
            raise RepositoryError(msg) from e

    async def create(self, entity: CanonicalEntity) -> CanonicalEntity:
        """Create a new canonical entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity

        Raises:
            RepositoryError: If entity already exists or creation fails
        """
        try:
            # Check if entity already exists
            existing = await self.find_by_entity_id(entity.entity_id)
            if existing:
                msg = f"Entity {entity.entity_id} already exists"
                raise RepositoryError(msg)

            # Convert to ORM model
            model = self._to_orm_model(entity)

            self.session.add(model)
            await self.session.flush()  # Get any generated values

            logger.info(
                "entity_created",
                entity_id=entity.entity_id,
                entity_type=entity.entity_type,
            )

            return entity

        except RepositoryError:
            raise
        except Exception as e:
            logger.error("create_entity_error", entity_id=entity.entity_id, error=str(e))
            msg = f"Error creating entity: {e}"
            raise RepositoryError(msg) from e

    async def update(self, entity: CanonicalEntity) -> CanonicalEntity:
        """Update an existing canonical entity.

        Args:
            entity: Entity to update

        Returns:
            Updated entity

        Raises:
            RepositoryError: If entity not found
        """
        try:
            stmt = select(CanonicalEntityModel).where(
                CanonicalEntityModel.entity_id == entity.entity_id
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                msg = f"Entity {entity.entity_id} not found"
                raise RepositoryError(msg)

            # Update fields
            model.canonical_name = entity.canonical_name
            model.external_ref = entity.external_ref.to_dict()
            model.properties = entity.properties
            model.updated_at = entity.updated_at

            await self.session.flush()

            logger.info("entity_updated", entity_id=entity.entity_id)

            return entity

        except RepositoryError:
            raise
        except Exception as e:
            logger.error("update_entity_error", entity_id=entity.entity_id, error=str(e))
            msg = f"Error updating entity: {e}"
            raise RepositoryError(msg) from e

    async def create_alias(self, alias: EntityAlias) -> EntityAlias:
        """Create a new entity alias.

        Args:
            alias: Alias to create

        Returns:
            Created alias (with alias_id populated)

        Raises:
            RepositoryError: If alias creation fails
        """
        try:
            model = EntityAliasModel(
                canonical_entity_id=alias.canonical_entity_id,
                alias_text=alias.alias_text,
                alias_source=alias.alias_source,
                user_id=alias.user_id,
                confidence=alias.confidence,
                use_count=alias.use_count,
                alias_metadata=alias.metadata,
                created_at=alias.created_at,
            )

            self.session.add(model)
            await self.session.flush()

            # Update domain object with generated ID
            alias.alias_id = model.alias_id

            logger.info(
                "alias_created",
                alias_id=alias.alias_id,
                entity_id=alias.canonical_entity_id,
                alias_text=alias.alias_text,
            )

            return alias

        except Exception as e:
            logger.error(
                "create_alias_error",
                entity_id=alias.canonical_entity_id,
                alias=alias.alias_text,
                error=str(e),
            )
            msg = f"Error creating alias: {e}"
            raise RepositoryError(msg) from e

    async def get_aliases(self, entity_id: str) -> list[EntityAlias]:
        """Get all aliases for an entity.

        Args:
            entity_id: Entity ID to get aliases for

        Returns:
            List of aliases (may be empty)
        """
        try:
            stmt = select(EntityAliasModel).where(
                EntityAliasModel.canonical_entity_id == entity_id
            )
            result = await self.session.execute(stmt)
            models = result.scalars().all()

            return [self._to_domain_alias(model) for model in models]

        except Exception as e:
            logger.error("get_aliases_error", entity_id=entity_id, error=str(e))
            msg = f"Error getting aliases: {e}"
            raise RepositoryError(msg) from e

    async def increment_alias_use_count(self, alias_id: int) -> None:
        """Increment use count for an alias.

        Args:
            alias_id: Alias ID to increment
        """
        try:
            stmt = select(EntityAliasModel).where(EntityAliasModel.alias_id == alias_id)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if model:
                model.use_count += 1
                await self.session.flush()

        except Exception as e:
            logger.error("increment_alias_use_count_error", alias_id=alias_id, error=str(e))
            # Don't raise - this is not critical

    def _to_domain_entity(self, model: CanonicalEntityModel) -> CanonicalEntity:
        """Convert ORM model to domain entity.

        Args:
            model: SQLAlchemy model

        Returns:
            Domain entity
        """
        entity_ref = EntityReference.from_dict(model.external_ref)

        return CanonicalEntity(
            entity_id=model.entity_id,
            entity_type=model.entity_type,
            canonical_name=model.canonical_name,
            external_ref=entity_ref,
            properties=model.properties or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_orm_model(self, entity: CanonicalEntity) -> CanonicalEntityModel:
        """Convert domain entity to ORM model.

        Args:
            entity: Domain entity

        Returns:
            SQLAlchemy model
        """
        return CanonicalEntityModel(
            entity_id=entity.entity_id,
            entity_type=entity.entity_type,
            canonical_name=entity.canonical_name,
            external_ref=entity.external_ref.to_dict(),
            properties=entity.properties,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _to_domain_alias(self, model: EntityAliasModel) -> EntityAlias:
        """Convert ORM model to domain alias.

        Args:
            model: SQLAlchemy model

        Returns:
            Domain entity alias
        """
        return EntityAlias(
            alias_id=model.alias_id,
            canonical_entity_id=model.canonical_entity_id,
            alias_text=model.alias_text,
            alias_source=model.alias_source,
            user_id=model.user_id,
            confidence=model.confidence,
            use_count=model.use_count,
            metadata=model.alias_metadata or {},
            created_at=model.created_at,
        )
