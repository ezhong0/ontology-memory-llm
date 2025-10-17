"""Semantic memory repository implementation.

Implements entity-tagged natural language memory storage using SQLAlchemy and PostgreSQL with pgvector.
"""

import structlog
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.semantic_memory import SemanticMemory
from src.domain.exceptions import RepositoryError
from src.infrastructure.database.models import SemanticMemory as SemanticMemoryModel

logger = structlog.get_logger(__name__)


class SemanticMemoryRepository:
    """SQLAlchemy implementation of semantic memory storage.

    Maps between domain SemanticMemory entities and SQLAlchemy ORM models.
    Handles vector similarity search using pgvector extension.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(self, memory: SemanticMemory) -> SemanticMemory:
        """Store semantic memory with embedding.

        Args:
            memory: Semantic memory to store

        Returns:
            Created memory with memory_id populated

        Raises:
            RepositoryError: If creation fails
        """
        try:
            # Convert to ORM model
            model = self._to_orm_model(memory)

            self.session.add(model)
            await self.session.flush()  # Get generated memory_id

            # Update domain object with generated ID
            memory.memory_id = model.memory_id

            logger.info(
                "semantic_memory_created",
                memory_id=memory.memory_id,
                entities=memory.entities,
                content_preview=memory.content[:50],
                importance=memory.importance,
            )

            return memory

        except Exception as e:
            logger.error(
                "create_semantic_memory_error",
                entities=memory.entities,
                error=str(e),
            )
            msg = f"Error creating semantic memory: {e}"
            raise RepositoryError(msg) from e

    async def find_by_id(self, memory_id: int) -> SemanticMemory | None:
        """Find semantic memory by ID.

        Args:
            memory_id: Memory ID to search for

        Returns:
            SemanticMemory if found, None otherwise
        """
        try:
            stmt = select(SemanticMemoryModel).where(
                SemanticMemoryModel.memory_id == memory_id
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            return self._to_domain_entity(model) if model else None

        except Exception as e:
            logger.error("find_by_id_error", memory_id=memory_id, error=str(e))
            msg = f"Error finding memory by ID: {e}"
            raise RepositoryError(msg) from e

    async def find_by_entities(
        self,
        entity_ids: list[str],
        user_id: str,
        status_filter: str = "active",
        match_all: bool = False,
    ) -> list[SemanticMemory]:
        """Find memories that mention specific entities.

        Args:
            entity_ids: Entity IDs to search for
            user_id: User ID to filter by
            status_filter: Status to filter by (default: "active")
            match_all: If True, memory must contain ALL entities; if False, ANY entity

        Returns:
            List of matching memories (may be empty)
        """
        try:
            if match_all:
                # Memory must contain all entities (array contains all)
                stmt = select(SemanticMemoryModel).where(
                    and_(
                        SemanticMemoryModel.user_id == user_id,
                        SemanticMemoryModel.status == status_filter,
                        SemanticMemoryModel.entities.contains(entity_ids),
                    )
                )
            else:
                # Memory must contain at least one entity (array overlaps)
                stmt = select(SemanticMemoryModel).where(
                    and_(
                        SemanticMemoryModel.user_id == user_id,
                        SemanticMemoryModel.status == status_filter,
                        SemanticMemoryModel.entities.overlap(entity_ids),
                    )
                )

            result = await self.session.execute(stmt)
            models = result.scalars().all()

            memories = [self._to_domain_entity(model) for model in models]

            logger.debug(
                "found_memories_by_entities",
                entity_ids=entity_ids,
                match_all=match_all,
                count=len(memories),
            )

            return memories

        except Exception as e:
            logger.error(
                "find_by_entities_error",
                entity_ids=entity_ids,
                error=str(e),
            )
            msg = f"Error finding memories by entities: {e}"
            raise RepositoryError(msg) from e

    async def find_similar(
        self,
        query_embedding: list[float],
        user_id: str,
        limit: int = 50,
        min_confidence: float = 0.3,
        min_importance: float = 0.3,
    ) -> list[tuple[SemanticMemory, float]]:
        """Find similar memories using pgvector cosine similarity.

        Args:
            query_embedding: Query vector (1536 dimensions)
            user_id: User ID to filter by
            limit: Maximum number of results
            min_confidence: Minimum confidence threshold (default: 0.3)
            min_importance: Minimum importance threshold (default: 0.3)

        Returns:
            List of (memory, similarity_score) tuples, sorted by similarity descending
        """
        try:
            # Convert embedding to string format for pgvector
            if isinstance(query_embedding, list):
                embedding_str = str(query_embedding).replace(" ", "")
            else:
                embedding_str = str(query_embedding.tolist()).replace(" ", "")

            # Build raw SQL for pgvector similarity
            stmt = text(
                f"""
                SELECT
                    memory_id, user_id, content, entities, memory_metadata,
                    confidence, importance, source_type, source_memory_id,
                    extracted_from_event_id, source_text,
                    status, superseded_by_memory_id, embedding,
                    last_accessed_at, created_at, updated_at,
                    1 - (embedding <=> '{embedding_str}'::vector) as similarity
                FROM app.semantic_memories
                WHERE user_id = :user_id
                  AND status = 'active'
                  AND confidence >= :min_confidence
                  AND importance >= :min_importance
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> '{embedding_str}'::vector
                LIMIT :limit
                """
            )

            result = await self.session.execute(
                stmt,
                {
                    "user_id": user_id,
                    "min_confidence": min_confidence,
                    "min_importance": min_importance,
                    "limit": limit,
                },
            )

            matches: list[tuple[SemanticMemory, float]] = []
            for row in result:
                memory = self._row_to_domain_entity(row)
                similarity = float(row.similarity)
                matches.append((memory, similarity))

            logger.debug(
                "found_similar_memories",
                user_id=user_id,
                count=len(matches),
            )

            return matches

        except Exception as e:
            logger.error(
                "find_similar_error",
                user_id=user_id,
                error=str(e),
            )
            msg = f"Error finding similar memories: {e}"
            raise RepositoryError(msg) from e

    async def update(self, memory: SemanticMemory) -> SemanticMemory:
        """Update an existing semantic memory.

        Args:
            memory: Memory to update (must have memory_id)

        Returns:
            Updated memory

        Raises:
            RepositoryError: If memory not found or update fails
        """
        try:
            if memory.memory_id is None:
                msg = "Cannot update memory without memory_id"
                raise RepositoryError(msg)

            stmt = select(SemanticMemoryModel).where(
                SemanticMemoryModel.memory_id == memory.memory_id
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                msg = f"Memory {memory.memory_id} not found"
                raise RepositoryError(msg)

            # Update mutable fields
            model.content = memory.content
            model.entities = memory.entities
            model.memory_metadata = memory.metadata
            model.confidence = memory.confidence
            model.importance = memory.importance
            model.status = self._map_status_to_orm(memory.status)
            model.last_accessed_at = memory.last_accessed_at
            model.updated_at = memory.updated_at
            model.superseded_by_memory_id = memory.superseded_by_memory_id

            await self.session.flush()

            logger.info(
                "semantic_memory_updated",
                memory_id=memory.memory_id,
                importance=memory.importance,
                status=memory.status,
            )

            return memory

        except RepositoryError:
            raise
        except Exception as e:
            logger.error(
                "update_semantic_memory_error",
                memory_id=memory.memory_id,
                error=str(e),
            )
            msg = f"Error updating semantic memory: {e}"
            raise RepositoryError(msg) from e

    async def find_aging_memories(
        self,
        user_id: str,
        days: int = 7,
    ) -> list[SemanticMemory]:
        """Find aging memories from recent session context.

        Phase 2.2: Retrieve aging memories for validation prompts.

        Args:
            user_id: User identifier
            days: Number of days to look back (default: 7)

        Returns:
            List of aging memories from recent context
        """
        try:
            from datetime import datetime, timedelta, timezone

            recent_cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            stmt = select(SemanticMemoryModel).where(
                and_(
                    SemanticMemoryModel.user_id == user_id,
                    SemanticMemoryModel.status == "aging",
                    SemanticMemoryModel.updated_at >= recent_cutoff,
                )
            )

            result = await self.session.execute(stmt)
            models = result.scalars().all()

            aging_memories = [self._to_domain_entity(model) for model in models]

            logger.debug(
                "found_aging_memories",
                user_id=user_id,
                count=len(aging_memories),
                days=days,
            )

            return aging_memories

        except Exception as e:
            logger.error(
                "find_aging_memories_error",
                user_id=user_id,
                error=str(e),
            )
            msg = f"Error finding aging memories: {e}"
            raise RepositoryError(msg) from e

    def _to_domain_entity(self, model: SemanticMemoryModel) -> SemanticMemory:
        """Convert ORM model to domain entity.

        Args:
            model: SQLAlchemy model

        Returns:
            Domain entity
        """
        # Extract source_event_ids from extracted_from_event_id
        source_event_ids = []
        if model.extracted_from_event_id:
            source_event_ids = [model.extracted_from_event_id]

        # Convert embedding to list if present
        embedding = None
        if model.embedding is not None:
            embedding = list(model.embedding) if hasattr(model.embedding, "__iter__") else model.embedding

        return SemanticMemory(
            memory_id=model.memory_id,
            user_id=model.user_id,
            content=model.content,
            entities=list(model.entities) if model.entities else [],
            confidence=model.confidence,
            importance=model.importance,
            status=self._map_status_from_orm(model.status),
            source_event_ids=source_event_ids,
            embedding=embedding,
            source_text=model.source_text,
            metadata=model.memory_metadata or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_accessed_at=model.last_accessed_at,
        )

    def _row_to_domain_entity(self, row) -> SemanticMemory:
        """Convert raw SQL row to domain entity.

        Args:
            row: SQLAlchemy row result

        Returns:
            Domain entity
        """
        # Extract source_event_ids from extracted_from_event_id
        source_event_ids = []
        if row.extracted_from_event_id:
            source_event_ids = [row.extracted_from_event_id]

        # Convert embedding to list if present
        embedding = None
        if row.embedding is not None:
            if isinstance(row.embedding, str):
                # Parse string representation to list of floats
                import json
                embedding = json.loads(row.embedding.replace("'", '"'))
            elif hasattr(row.embedding, "__iter__"):
                embedding = list(row.embedding)
            else:
                embedding = row.embedding

        return SemanticMemory(
            memory_id=row.memory_id,
            user_id=row.user_id,
            content=row.content,
            entities=list(row.entities) if row.entities else [],
            confidence=row.confidence,
            importance=row.importance,
            status=self._map_status_from_orm(row.status),
            source_event_ids=source_event_ids,
            embedding=embedding,
            source_text=row.source_text,
            metadata=row.memory_metadata if hasattr(row, 'memory_metadata') else (row.metadata if hasattr(row, 'metadata') else {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
            last_accessed_at=row.last_accessed_at,
        )

    def _to_orm_model(self, memory: SemanticMemory) -> SemanticMemoryModel:
        """Convert domain entity to ORM model.

        Args:
            memory: Domain entity

        Returns:
            SQLAlchemy model
        """
        # Get first event ID for extracted_from_event_id
        extracted_from_event_id = (
            memory.source_event_ids[0] if memory.source_event_ids else None
        )

        return SemanticMemoryModel(
            memory_id=memory.memory_id,
            user_id=memory.user_id,
            content=memory.content,
            entities=memory.entities,
            memory_metadata=memory.metadata,
            confidence=memory.confidence,
            importance=memory.importance,
            source_type="episodic",  # Phase 1B: all from chat events
            source_memory_id=None,
            extracted_from_event_id=extracted_from_event_id,
            status=self._map_status_to_orm(memory.status),
            superseded_by_memory_id=None,
            embedding=memory.embedding,
            source_text=memory.source_text,
            last_accessed_at=memory.last_accessed_at,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
        )

    def _map_status_to_orm(self, domain_status: str) -> str:
        """Map domain status to ORM status.

        Args:
            domain_status: Domain status (active|inactive|aging|conflicted|superseded|invalidated)

        Returns:
            ORM status (active|aging|superseded|invalidated)
        """
        status_map = {
            "active": "active",
            "inactive": "aging",  # Inactive = aging but not superseded
            "aging": "aging",  # Phase 2.2: Memory requires validation
            "conflicted": "invalidated",  # Conflicted = invalidated pending resolution
            "superseded": "superseded",  # Phase 2.1: Memory superseded by newer
            "invalidated": "invalidated",  # Phase 2.1: Memory invalidated by DB conflict
        }
        return status_map.get(domain_status, "active")

    def _map_status_from_orm(self, orm_status: str) -> str:
        """Map ORM status to domain status.

        Args:
            orm_status: ORM status (active|aging|superseded|invalidated)

        Returns:
            Domain status (active|aging|inactive|conflicted)
        """
        status_map = {
            "active": "active",
            "aging": "aging",  # Phase 2.2: Preserve aging status
            "superseded": "inactive",
            "invalidated": "conflicted",
        }
        return status_map.get(orm_status, "active")
