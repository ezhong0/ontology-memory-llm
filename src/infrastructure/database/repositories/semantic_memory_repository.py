"""Semantic memory repository implementation.

Implements semantic memory storage using SQLAlchemy and PostgreSQL with pgvector.
"""

from typing import Optional

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.semantic_memory import SemanticMemory
from src.domain.exceptions import RepositoryError
from src.domain.value_objects import PredicateType
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
                subject=memory.subject_entity_id,
                predicate=memory.predicate,
                confidence=memory.confidence,
            )

            return memory

        except Exception as e:
            logger.error(
                "create_semantic_memory_error",
                subject=memory.subject_entity_id,
                predicate=memory.predicate,
                error=str(e),
            )
            raise RepositoryError(f"Error creating semantic memory: {e}") from e

    async def find_by_id(self, memory_id: int) -> Optional[SemanticMemory]:
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
            raise RepositoryError(f"Error finding memory by ID: {e}") from e

    async def find_by_subject_predicate(
        self,
        subject_entity_id: str,
        predicate: str,
        user_id: str,
        status_filter: str = "active",
    ) -> list[SemanticMemory]:
        """Find memories for a specific subject and predicate.

        Used primarily for conflict detection.

        Args:
            subject_entity_id: Subject entity ID
            predicate: Predicate name
            user_id: User ID to filter by
            status_filter: Status to filter by (default: "active")

        Returns:
            List of matching memories (may be empty)
        """
        try:
            stmt = select(SemanticMemoryModel).where(
                and_(
                    SemanticMemoryModel.subject_entity_id == subject_entity_id,
                    SemanticMemoryModel.predicate == predicate,
                    SemanticMemoryModel.user_id == user_id,
                    SemanticMemoryModel.status == status_filter,
                )
            )
            result = await self.session.execute(stmt)
            models = result.scalars().all()

            memories = [self._to_domain_entity(model) for model in models]

            logger.debug(
                "found_memories_by_subject_predicate",
                subject=subject_entity_id,
                predicate=predicate,
                count=len(memories),
            )

            return memories

        except Exception as e:
            logger.error(
                "find_by_subject_predicate_error",
                subject=subject_entity_id,
                predicate=predicate,
                error=str(e),
            )
            raise RepositoryError(f"Error finding memories: {e}") from e

    async def find_similar(
        self,
        query_embedding: list[float],
        user_id: str,
        limit: int = 50,
        min_confidence: float = 0.3,
    ) -> list[tuple[SemanticMemory, float]]:
        """Find similar memories using pgvector cosine similarity.

        Args:
            query_embedding: Query vector (1536 dimensions)
            user_id: User ID to filter by
            limit: Maximum number of results
            min_confidence: Minimum confidence threshold (default: 0.3)

        Returns:
            List of (memory, similarity_score) tuples, sorted by similarity descending
        """
        try:
            # Use pgvector's cosine similarity operator <=>
            # Note: We filter to active memories with sufficient confidence
            from sqlalchemy import func, text

            # Build raw SQL for pgvector similarity
            # Using 1 - (embedding <=> query) to get similarity (higher = more similar)
            stmt = text(
                """
                SELECT
                    memory_id, user_id, subject_entity_id, predicate, predicate_type,
                    object_value, confidence, confidence_factors, reinforcement_count,
                    last_validated_at, source_type, source_memory_id, extracted_from_event_id,
                    status, superseded_by_memory_id, embedding, importance,
                    created_at, updated_at,
                    1 - (embedding <=> :query_embedding::vector) as similarity
                FROM app.semantic_memories
                WHERE user_id = :user_id
                  AND status = 'active'
                  AND confidence >= :min_confidence
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> :query_embedding::vector
                LIMIT :limit
                """
            )

            result = await self.session.execute(
                stmt,
                {
                    "query_embedding": query_embedding,
                    "user_id": user_id,
                    "min_confidence": min_confidence,
                    "limit": limit,
                },
            )

            matches: list[tuple[SemanticMemory, float]] = []
            for row in result:
                # Convert row to domain entity
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
            raise RepositoryError(f"Error finding similar memories: {e}") from e

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
                raise RepositoryError("Cannot update memory without memory_id")

            stmt = select(SemanticMemoryModel).where(
                SemanticMemoryModel.memory_id == memory.memory_id
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                raise RepositoryError(f"Memory {memory.memory_id} not found")

            # Update fields (only fields that can change)
            model.confidence = memory.confidence
            model.status = self._map_status_to_orm(memory.status)
            model.reinforcement_count = memory.reinforcement_count
            model.last_validated_at = memory.last_validated_at
            model.updated_at = memory.updated_at

            # Update confidence_factors to track source events
            model.confidence_factors = {
                "source_event_ids": memory.source_event_ids,
            }

            await self.session.flush()

            logger.info(
                "semantic_memory_updated",
                memory_id=memory.memory_id,
                confidence=memory.confidence,
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
            raise RepositoryError(f"Error updating semantic memory: {e}") from e

    def _to_domain_entity(self, model: SemanticMemoryModel) -> SemanticMemory:
        """Convert ORM model to domain entity.

        Args:
            model: SQLAlchemy model

        Returns:
            Domain entity
        """
        # Extract source_event_ids from confidence_factors if available
        source_event_ids = []
        if model.confidence_factors:
            source_event_ids = model.confidence_factors.get("source_event_ids", [])

        # If no source_event_ids but has extracted_from_event_id, use that
        if not source_event_ids and model.extracted_from_event_id:
            source_event_ids = [model.extracted_from_event_id]

        return SemanticMemory(
            memory_id=model.memory_id,
            user_id=model.user_id,
            subject_entity_id=model.subject_entity_id,
            predicate=model.predicate,
            predicate_type=PredicateType(model.predicate_type),
            object_value=model.object_value,
            confidence=model.confidence,
            status=self._map_status_from_orm(model.status),
            reinforcement_count=model.reinforcement_count,
            source_event_ids=source_event_ids,
            embedding=list(model.embedding) if model.embedding else None,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_validated_at=model.last_validated_at,
        )

    def _row_to_domain_entity(self, row) -> SemanticMemory:
        """Convert raw SQL row to domain entity.

        Args:
            row: SQLAlchemy row result

        Returns:
            Domain entity
        """
        # Extract source_event_ids from confidence_factors if available
        source_event_ids = []
        if row.confidence_factors:
            source_event_ids = row.confidence_factors.get("source_event_ids", [])

        # If no source_event_ids but has extracted_from_event_id, use that
        if not source_event_ids and row.extracted_from_event_id:
            source_event_ids = [row.extracted_from_event_id]

        return SemanticMemory(
            memory_id=row.memory_id,
            user_id=row.user_id,
            subject_entity_id=row.subject_entity_id,
            predicate=row.predicate,
            predicate_type=PredicateType(row.predicate_type),
            object_value=row.object_value,
            confidence=row.confidence,
            status=self._map_status_from_orm(row.status),
            reinforcement_count=row.reinforcement_count,
            source_event_ids=source_event_ids,
            embedding=list(row.embedding) if row.embedding else None,
            created_at=row.created_at,
            updated_at=row.updated_at,
            last_validated_at=row.last_validated_at,
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
            subject_entity_id=memory.subject_entity_id,
            predicate=memory.predicate,
            predicate_type=memory.predicate_type.value,
            object_value=memory.object_value,
            confidence=memory.confidence,
            confidence_factors={"source_event_ids": memory.source_event_ids},
            reinforcement_count=memory.reinforcement_count,
            last_validated_at=memory.last_validated_at,
            source_type="episodic",  # Phase 1B: all from chat events
            source_memory_id=None,
            extracted_from_event_id=extracted_from_event_id,
            status=self._map_status_to_orm(memory.status),
            superseded_by_memory_id=None,
            embedding=memory.embedding,
            importance=0.5,  # Default importance for Phase 1B
            created_at=memory.created_at,
            updated_at=memory.updated_at,
        )

    def _map_status_to_orm(self, domain_status: str) -> str:
        """Map domain status to ORM status.

        Args:
            domain_status: Domain status (active|inactive|conflicted)

        Returns:
            ORM status (active|aging|superseded|invalidated)
        """
        status_map = {
            "active": "active",
            "inactive": "aging",  # Inactive = aging but not superseded
            "conflicted": "invalidated",  # Conflicted = invalidated pending resolution
        }
        return status_map.get(domain_status, "active")

    def _map_status_from_orm(self, orm_status: str) -> str:
        """Map ORM status to domain status.

        Args:
            orm_status: ORM status (active|aging|superseded|invalidated)

        Returns:
            Domain status (active|inactive|conflicted)
        """
        status_map = {
            "active": "active",
            "aging": "inactive",
            "superseded": "inactive",
            "invalidated": "conflicted",
        }
        return status_map.get(orm_status, "active")
