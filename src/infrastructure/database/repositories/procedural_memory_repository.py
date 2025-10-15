"""Procedural memory repository implementation.

Implements procedural memory storage and retrieval using SQLAlchemy and PostgreSQL with pgvector.
"""

from datetime import datetime
from typing import Any, Optional

import numpy as np
from numpy import typing as npt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.domain.exceptions import RepositoryError
from src.domain.ports.procedural_memory_repository import IProceduralMemoryRepository
from src.domain.value_objects.procedural_memory import ProceduralMemory

logger = structlog.get_logger(__name__)


class ProceduralMemoryRepository(IProceduralMemoryRepository):
    """SQLAlchemy implementation of procedural memory persistence.

    Stores and retrieves learned patterns for query augmentation.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(self, memory: ProceduralMemory) -> ProceduralMemory:
        """Create a new procedural memory.

        Args:
            memory: ProceduralMemory to store

        Returns:
            ProceduralMemory with assigned memory_id
        """
        try:
            # Convert embedding to list if present
            embedding_list = memory.embedding.tolist() if memory.embedding is not None else None

            stmt = text(
                """
                INSERT INTO app.procedural_memories (
                    user_id, trigger_pattern, trigger_features,
                    action_heuristic, action_structure,
                    observed_count, confidence, embedding, created_at
                ) VALUES (
                    :user_id, :trigger_pattern, :trigger_features,
                    :action_heuristic, :action_structure,
                    :observed_count, :confidence, :embedding::vector, :created_at
                )
                RETURNING memory_id, created_at, updated_at
                """
            )

            params = {
                "user_id": memory.user_id,
                "trigger_pattern": memory.trigger_pattern,
                "trigger_features": memory.trigger_features,
                "action_heuristic": memory.action_heuristic,
                "action_structure": memory.action_structure,
                "observed_count": memory.observed_count,
                "confidence": memory.confidence,
                "embedding": embedding_list,
                "created_at": memory.created_at,
            }

            result = await self.session.execute(stmt, params)
            row = result.fetchone()
            await self.session.commit()

            logger.info(
                "procedural_memory_created",
                memory_id=row.memory_id,
                user_id=memory.user_id,
                trigger=memory.trigger_pattern,
            )

            # Return memory with assigned ID
            return ProceduralMemory(
                memory_id=row.memory_id,
                user_id=memory.user_id,
                trigger_pattern=memory.trigger_pattern,
                trigger_features=memory.trigger_features,
                action_heuristic=memory.action_heuristic,
                action_structure=memory.action_structure,
                observed_count=memory.observed_count,
                confidence=memory.confidence,
                embedding=memory.embedding,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "create_procedural_memory_error",
                user_id=memory.user_id,
                error=str(e),
            )
            raise RepositoryError(f"Error creating procedural memory: {e}") from e

    async def get_by_id(
        self, memory_id: int, user_id: Optional[str] = None
    ) -> Optional[ProceduralMemory]:
        """Get procedural memory by ID.

        Args:
            memory_id: Memory identifier
            user_id: Optional user filter for security

        Returns:
            ProceduralMemory if found, None otherwise
        """
        try:
            user_filter = ""
            params = {"memory_id": memory_id}

            if user_id:
                user_filter = "AND user_id = :user_id"
                params["user_id"] = user_id

            stmt = text(
                f"""
                SELECT
                    memory_id, user_id, trigger_pattern, trigger_features,
                    action_heuristic, action_structure,
                    observed_count, confidence, embedding,
                    created_at, updated_at
                FROM app.procedural_memories
                WHERE memory_id = :memory_id
                  {user_filter}
                """
            )

            result = await self.session.execute(stmt, params)
            row = result.fetchone()

            if not row:
                return None

            return self._row_to_procedural_memory(row)

        except Exception as e:
            logger.error(
                "get_procedural_memory_by_id_error",
                memory_id=memory_id,
                error=str(e),
            )
            raise RepositoryError(f"Error getting procedural memory by ID: {e}") from e

    async def find_by_user(
        self,
        user_id: str,
        min_confidence: float = 0.5,
        limit: int = 100,
    ) -> list[ProceduralMemory]:
        """Find all procedural memories for a user.

        Args:
            user_id: User identifier
            min_confidence: Minimum confidence threshold
            limit: Maximum number of results

        Returns:
            List of ProceduralMemory instances
        """
        try:
            stmt = text(
                """
                SELECT
                    memory_id, user_id, trigger_pattern, trigger_features,
                    action_heuristic, action_structure,
                    observed_count, confidence, embedding,
                    created_at, updated_at
                FROM app.procedural_memories
                WHERE user_id = :user_id
                  AND confidence >= :min_confidence
                ORDER BY confidence DESC, observed_count DESC
                LIMIT :limit
                """
            )

            params = {
                "user_id": user_id,
                "min_confidence": min_confidence,
                "limit": limit,
            }

            result = await self.session.execute(stmt, params)

            memories = [self._row_to_procedural_memory(row) for row in result]

            logger.debug(
                "found_procedural_memories_by_user",
                user_id=user_id,
                count=len(memories),
            )

            return memories

        except Exception as e:
            logger.error(
                "find_procedural_memories_by_user_error",
                user_id=user_id,
                error=str(e),
            )
            raise RepositoryError(f"Error finding procedural memories by user: {e}") from e

    async def find_similar(
        self,
        user_id: str,
        query_embedding: npt.NDArray[np.float64],
        limit: int = 10,
        min_confidence: float = 0.5,
    ) -> list[ProceduralMemory]:
        """Find procedural memories similar to query.

        Uses pgvector cosine similarity on trigger_pattern embeddings.

        Args:
            user_id: User identifier
            query_embedding: Query embedding (1536-dimensional)
            limit: Maximum number of results
            min_confidence: Minimum pattern confidence

        Returns:
            List of ProceduralMemory instances ordered by similarity
        """
        try:
            # Convert numpy array to list for JSON serialization
            embedding_list = query_embedding.tolist()

            stmt = text(
                """
                SELECT
                    memory_id, user_id, trigger_pattern, trigger_features,
                    action_heuristic, action_structure,
                    observed_count, confidence, embedding,
                    created_at, updated_at,
                    1 - (embedding <=> :query_embedding::vector) as similarity
                FROM app.procedural_memories
                WHERE user_id = :user_id
                  AND confidence >= :min_confidence
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> :query_embedding::vector
                LIMIT :limit
                """
            )

            params = {
                "user_id": user_id,
                "query_embedding": embedding_list,
                "min_confidence": min_confidence,
                "limit": limit,
            }

            result = await self.session.execute(stmt, params)

            memories = [self._row_to_procedural_memory(row) for row in result]

            logger.debug(
                "found_similar_procedural_memories",
                user_id=user_id,
                count=len(memories),
            )

            return memories

        except Exception as e:
            logger.error(
                "find_similar_procedural_memories_error",
                user_id=user_id,
                error=str(e),
            )
            raise RepositoryError(f"Error finding similar procedural memories: {e}") from e

    async def update(self, memory: ProceduralMemory) -> ProceduralMemory:
        """Update an existing procedural memory.

        Args:
            memory: ProceduralMemory to update (must have memory_id)

        Returns:
            Updated ProceduralMemory
        """
        try:
            if memory.memory_id is None:
                raise ValueError("memory_id is required for update")

            # Convert embedding to list if present
            embedding_list = memory.embedding.tolist() if memory.embedding is not None else None

            stmt = text(
                """
                UPDATE app.procedural_memories
                SET
                    trigger_pattern = :trigger_pattern,
                    trigger_features = :trigger_features,
                    action_heuristic = :action_heuristic,
                    action_structure = :action_structure,
                    observed_count = :observed_count,
                    confidence = :confidence,
                    embedding = :embedding::vector,
                    updated_at = :updated_at
                WHERE memory_id = :memory_id
                  AND user_id = :user_id
                RETURNING updated_at
                """
            )

            params = {
                "memory_id": memory.memory_id,
                "user_id": memory.user_id,
                "trigger_pattern": memory.trigger_pattern,
                "trigger_features": memory.trigger_features,
                "action_heuristic": memory.action_heuristic,
                "action_structure": memory.action_structure,
                "observed_count": memory.observed_count,
                "confidence": memory.confidence,
                "embedding": embedding_list,
                "updated_at": datetime.utcnow(),
            }

            result = await self.session.execute(stmt, params)
            row = result.fetchone()
            await self.session.commit()

            if not row:
                raise RepositoryError(f"Procedural memory {memory.memory_id} not found")

            logger.info(
                "procedural_memory_updated",
                memory_id=memory.memory_id,
                observed_count=memory.observed_count,
                confidence=memory.confidence,
            )

            # Return memory with updated timestamp
            return ProceduralMemory(
                memory_id=memory.memory_id,
                user_id=memory.user_id,
                trigger_pattern=memory.trigger_pattern,
                trigger_features=memory.trigger_features,
                action_heuristic=memory.action_heuristic,
                action_structure=memory.action_structure,
                observed_count=memory.observed_count,
                confidence=memory.confidence,
                embedding=memory.embedding,
                created_at=memory.created_at,
                updated_at=row.updated_at,
            )

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "update_procedural_memory_error",
                memory_id=memory.memory_id,
                error=str(e),
            )
            raise RepositoryError(f"Error updating procedural memory: {e}") from e

    async def delete(self, memory_id: int, user_id: str) -> bool:
        """Delete a procedural memory.

        Args:
            memory_id: Memory identifier
            user_id: User identifier (for security)

        Returns:
            True if deleted, False if not found
        """
        try:
            stmt = text(
                """
                DELETE FROM app.procedural_memories
                WHERE memory_id = :memory_id
                  AND user_id = :user_id
                """
            )

            params = {
                "memory_id": memory_id,
                "user_id": user_id,
            }

            result = await self.session.execute(stmt, params)
            await self.session.commit()

            deleted = result.rowcount > 0

            if deleted:
                logger.info(
                    "procedural_memory_deleted",
                    memory_id=memory_id,
                    user_id=user_id,
                )
            else:
                logger.warning(
                    "procedural_memory_not_found_for_deletion",
                    memory_id=memory_id,
                    user_id=user_id,
                )

            return deleted

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "delete_procedural_memory_error",
                memory_id=memory_id,
                error=str(e),
            )
            raise RepositoryError(f"Error deleting procedural memory: {e}") from e

    async def find_by_trigger_features(
        self,
        user_id: str,
        intent: Optional[str] = None,
        entity_types: Optional[list[str]] = None,
        topics: Optional[list[str]] = None,
        min_confidence: float = 0.5,
        limit: int = 20,
    ) -> list[ProceduralMemory]:
        """Find procedural memories matching trigger features.

        Uses JSONB operators for deterministic matching.

        Args:
            user_id: User identifier
            intent: Optional intent filter
            entity_types: Optional entity type filters
            topics: Optional topic filters
            min_confidence: Minimum confidence threshold
            limit: Maximum number of results

        Returns:
            List of ProceduralMemory instances
        """
        try:
            # Build filters dynamically
            filters = ["user_id = :user_id", "confidence >= :min_confidence"]
            params = {
                "user_id": user_id,
                "min_confidence": min_confidence,
                "limit": limit,
            }

            if intent:
                filters.append("trigger_features->>'intent' = :intent")
                params["intent"] = intent

            if entity_types:
                # Check if any entity_type in the list matches
                # JSONB array containment: trigger_features->'entity_types' ?| array['customer', 'order']
                filters.append("trigger_features->'entity_types' ??| :entity_types")
                params["entity_types"] = entity_types

            if topics:
                # Check if any topic in the list matches
                filters.append("trigger_features->'topics' ??| :topics")
                params["topics"] = topics

            where_clause = " AND ".join(filters)

            stmt = text(
                f"""
                SELECT
                    memory_id, user_id, trigger_pattern, trigger_features,
                    action_heuristic, action_structure,
                    observed_count, confidence, embedding,
                    created_at, updated_at
                FROM app.procedural_memories
                WHERE {where_clause}
                ORDER BY confidence DESC, observed_count DESC
                LIMIT :limit
                """
            )

            result = await self.session.execute(stmt, params)

            memories = [self._row_to_procedural_memory(row) for row in result]

            logger.debug(
                "found_procedural_memories_by_features",
                user_id=user_id,
                intent=intent,
                count=len(memories),
            )

            return memories

        except Exception as e:
            logger.error(
                "find_procedural_memories_by_features_error",
                user_id=user_id,
                error=str(e),
            )
            raise RepositoryError(f"Error finding procedural memories by features: {e}") from e

    def _row_to_procedural_memory(self, row: Any) -> ProceduralMemory:
        """Convert database row to ProceduralMemory.

        Args:
            row: Database row

        Returns:
            ProceduralMemory instance
        """
        return ProceduralMemory(
            memory_id=row.memory_id,
            user_id=row.user_id,
            trigger_pattern=row.trigger_pattern,
            trigger_features=row.trigger_features,
            action_heuristic=row.action_heuristic,
            action_structure=row.action_structure,
            observed_count=row.observed_count,
            confidence=row.confidence,
            embedding=np.array(row.embedding) if row.embedding else None,
            created_at=row.created_at,
            updated_at=row.updated_at if hasattr(row, "updated_at") else None,
        )
