"""Episodic memory repository implementation.

Implements episodic memory retrieval using SQLAlchemy and PostgreSQL with pgvector.
"""

from uuid import UUID

import numpy as np
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import RepositoryError
from src.domain.ports.episodic_memory_repository import IEpisodicMemoryRepository
from src.domain.value_objects.memory_candidate import MemoryCandidate

logger = structlog.get_logger(__name__)


class EpisodicMemoryRepository(IEpisodicMemoryRepository):
    """SQLAlchemy implementation of episodic memory retrieval.

    Retrieves episodic memories as MemoryCandidate objects for retrieval pipeline.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def find_similar(
        self,
        user_id: str,
        query_embedding: np.ndarray,
        limit: int = 50,
        session_id: UUID | None = None,
    ) -> list[MemoryCandidate]:
        """Find similar episodic memories using pgvector.

        Args:
            user_id: User identifier
            query_embedding: Query embedding vector (1536-dim)
            limit: Maximum number of results
            session_id: Optional session filter

        Returns:
            List of memory candidates from episodic layer
        """
        try:
            # Convert numpy array to list for JSON serialization
            embedding_list = query_embedding.tolist()

            session_filter = ""
            params = {
                "user_id": user_id,
                "query_embedding": embedding_list,
                "limit": limit,
            }

            if session_id:
                session_filter = "AND session_id = :session_id"
                params["session_id"] = str(session_id)

            stmt = text(
                f"""
                SELECT
                    memory_id, summary as content, entities,
                    embedding, importance, created_at,
                    1 - (embedding <=> :query_embedding::vector) as similarity
                FROM app.episodic_memories
                WHERE user_id = :user_id
                  AND embedding IS NOT NULL
                  {session_filter}
                ORDER BY embedding <=> :query_embedding::vector
                LIMIT :limit
                """
            )

            result = await self.session.execute(stmt, params)

            candidates = []
            for row in result:
                # Extract entity IDs from JSONB entities column
                entity_ids = self._extract_entity_ids(row.entities)

                candidate = MemoryCandidate(
                    memory_id=row.memory_id,
                    memory_type="episodic",
                    content=row.content,
                    entities=entity_ids,
                    embedding=np.array(row.embedding),
                    created_at=row.created_at,
                    importance=row.importance,
                )
                candidates.append(candidate)

            logger.debug(
                "found_similar_episodic_memories",
                user_id=user_id,
                count=len(candidates),
            )

            return candidates

        except Exception as e:
            logger.error(
                "find_similar_episodic_error",
                user_id=user_id,
                error=str(e),
            )
            msg = f"Error finding similar episodic memories: {e}"
            raise RepositoryError(msg) from e

    async def find_recent(
        self,
        user_id: str,
        limit: int = 10,
        session_id: UUID | None = None,
    ) -> list[MemoryCandidate]:
        """Find recent episodic memories.

        Args:
            user_id: User identifier
            limit: Maximum number of results
            session_id: Optional session filter

        Returns:
            List of recent memory candidates
        """
        try:
            session_filter = ""
            params = {
                "user_id": user_id,
                "limit": limit,
            }

            if session_id:
                session_filter = "AND session_id = :session_id"
                params["session_id"] = str(session_id)

            stmt = text(
                f"""
                SELECT
                    memory_id, summary as content, entities,
                    embedding, importance, created_at
                FROM app.episodic_memories
                WHERE user_id = :user_id
                  {session_filter}
                ORDER BY created_at DESC
                LIMIT :limit
                """
            )

            result = await self.session.execute(stmt, params)

            candidates = []
            for row in result:
                entity_ids = self._extract_entity_ids(row.entities)

                candidate = MemoryCandidate(
                    memory_id=row.memory_id,
                    memory_type="episodic",
                    content=row.content,
                    entities=entity_ids,
                    embedding=np.array(row.embedding) if row.embedding else None,
                    created_at=row.created_at,
                    importance=row.importance,
                )
                candidates.append(candidate)

            logger.debug(
                "found_recent_episodic_memories",
                user_id=user_id,
                count=len(candidates),
            )

            return candidates

        except Exception as e:
            logger.error(
                "find_recent_episodic_error",
                user_id=user_id,
                error=str(e),
            )
            msg = f"Error finding recent episodic memories: {e}"
            raise RepositoryError(msg) from e

    async def find_by_user(
        self,
        user_id: str,
        since: object | None = None,
        until: object | None = None,
        limit: int = 500,
        session_id: UUID | None = None,
    ) -> list[MemoryCandidate]:
        """Find episodic memories for a user within a time range.

        Args:
            user_id: User identifier
            since: Optional start datetime filter (inclusive)
            until: Optional end datetime filter (exclusive)
            limit: Maximum number of results
            session_id: Optional session filter

        Returns:
            List of memory candidates ordered by created_at DESC
        """
        try:
            filters = ["user_id = :user_id"]
            params = {
                "user_id": user_id,
                "limit": limit,
            }

            if since:
                filters.append("created_at >= :since")
                params["since"] = since

            if until:
                filters.append("created_at < :until")
                params["until"] = until

            if session_id:
                filters.append("session_id = :session_id")
                params["session_id"] = str(session_id)

            where_clause = " AND ".join(filters)

            stmt = text(
                f"""
                SELECT
                    memory_id, summary as content, entities,
                    embedding, importance, created_at
                FROM app.episodic_memories
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit
                """
            )

            result = await self.session.execute(stmt, params)

            candidates = []
            for row in result:
                entity_ids = self._extract_entity_ids(row.entities)

                candidate = MemoryCandidate(
                    memory_id=row.memory_id,
                    memory_type="episodic",
                    content=row.content,
                    entities=entity_ids,
                    embedding=np.array(row.embedding) if row.embedding else None,
                    created_at=row.created_at,
                    importance=row.importance,
                )
                candidates.append(candidate)

            logger.debug(
                "found_episodic_memories_by_user",
                user_id=user_id,
                count=len(candidates),
                since=since,
                until=until,
            )

            return candidates

        except Exception as e:
            logger.error(
                "find_episodic_memories_by_user_error",
                user_id=user_id,
                error=str(e),
            )
            msg = f"Error finding episodic memories by user: {e}"
            raise RepositoryError(msg) from e

    def _extract_entity_ids(self, entities_jsonb: dict) -> list[str]:
        """Extract entity IDs from JSONB entities column.

        Args:
            entities_jsonb: JSONB data from episodic_memories.entities

        Returns:
            List of entity IDs
        """
        if not entities_jsonb:
            return []

        # entities JSONB structure: {"entities": [{"id": "customer:xxx", ...}, ...]}
        if "entities" in entities_jsonb:
            return [e.get("id", "") for e in entities_jsonb["entities"] if e.get("id")]

        return []
