"""Memory summary repository implementation.

Implements memory summary retrieval using SQLAlchemy and PostgreSQL with pgvector.
"""

from typing import List, Optional

import numpy as np
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import RepositoryError
from src.domain.ports.summary_repository import ISummaryRepository
from src.domain.value_objects.memory_candidate import MemoryCandidate

logger = structlog.get_logger(__name__)


class SummaryRepository(ISummaryRepository):
    """SQLAlchemy implementation of memory summary retrieval.

    Retrieves memory summaries as MemoryCandidate objects for retrieval pipeline.
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
        limit: int = 5,
        scope_type: Optional[str] = None,
    ) -> List[MemoryCandidate]:
        """Find similar memory summaries using pgvector.

        Args:
            user_id: User identifier
            query_embedding: Query embedding vector (1536-dim)
            limit: Maximum number of results
            scope_type: Optional scope filter (entity, topic, session_window)

        Returns:
            List of memory candidates from summary layer
        """
        try:
            # Convert numpy array to list for JSON serialization
            embedding_list = query_embedding.tolist()

            scope_filter = ""
            params = {
                "user_id": user_id,
                "query_embedding": embedding_list,
                "limit": limit,
            }

            if scope_type:
                scope_filter = "AND scope_type = :scope_type"
                params["scope_type"] = scope_type

            stmt = text(
                f"""
                SELECT
                    summary_id as memory_id, summary_text as content,
                    embedding, confidence, created_at, key_facts,
                    1 - (embedding <=> :query_embedding::vector) as similarity
                FROM app.memory_summaries
                WHERE user_id = :user_id
                  AND embedding IS NOT NULL
                  {scope_filter}
                ORDER BY embedding <=> :query_embedding::vector
                LIMIT :limit
                """
            )

            result = await self.session.execute(stmt, params)

            candidates = []
            for row in result:
                # Extract entity IDs from key_facts JSONB
                entity_ids = self._extract_entity_ids(row.key_facts)

                # Summaries don't have importance stored, but are implicitly important
                # Give them a boost (handled in scoring via SUMMARY_BOOST)
                importance = 0.8

                candidate = MemoryCandidate(
                    memory_id=row.memory_id,
                    memory_type="summary",
                    content=row.content,
                    entities=entity_ids,
                    embedding=np.array(row.embedding),
                    created_at=row.created_at,
                    importance=importance,
                    confidence=row.confidence,
                )
                candidates.append(candidate)

            logger.debug(
                "found_similar_summaries",
                user_id=user_id,
                count=len(candidates),
            )

            return candidates

        except Exception as e:
            logger.error(
                "find_similar_summaries_error",
                user_id=user_id,
                error=str(e),
            )
            raise RepositoryError(f"Error finding similar summaries: {e}") from e

    async def find_by_scope(
        self,
        user_id: str,
        scope_type: str,
        scope_identifier: str,
    ) -> Optional[MemoryCandidate]:
        """Find summary by scope.

        Args:
            user_id: User identifier
            scope_type: Scope type (entity, topic, session_window)
            scope_identifier: Scope identifier

        Returns:
            Memory candidate if found, None otherwise
        """
        try:
            stmt = text(
                """
                SELECT
                    summary_id as memory_id, summary_text as content,
                    embedding, confidence, created_at, key_facts
                FROM app.memory_summaries
                WHERE user_id = :user_id
                  AND scope_type = :scope_type
                  AND scope_identifier = :scope_identifier
                ORDER BY created_at DESC
                LIMIT 1
                """
            )

            result = await self.session.execute(
                stmt,
                {
                    "user_id": user_id,
                    "scope_type": scope_type,
                    "scope_identifier": scope_identifier,
                },
            )

            row = result.one_or_none()
            if not row:
                return None

            entity_ids = self._extract_entity_ids(row.key_facts)
            importance = 0.8

            candidate = MemoryCandidate(
                memory_id=row.memory_id,
                memory_type="summary",
                content=row.content,
                entities=entity_ids,
                embedding=np.array(row.embedding) if row.embedding else None,
                created_at=row.created_at,
                importance=importance,
                confidence=row.confidence,
            )

            logger.debug(
                "found_summary_by_scope",
                user_id=user_id,
                scope_type=scope_type,
                scope_identifier=scope_identifier,
            )

            return candidate

        except Exception as e:
            logger.error(
                "find_by_scope_error",
                user_id=user_id,
                scope_type=scope_type,
                scope_identifier=scope_identifier,
                error=str(e),
            )
            raise RepositoryError(f"Error finding summary by scope: {e}") from e

    def _extract_entity_ids(self, key_facts_jsonb: dict) -> List[str]:
        """Extract entity IDs from key_facts JSONB.

        Args:
            key_facts_jsonb: JSONB data from memory_summaries.key_facts

        Returns:
            List of entity IDs
        """
        if not key_facts_jsonb:
            return []

        # key_facts structure varies, try to extract entity_id
        # Example: {"entity_profile": {"entity_id": "customer:xxx", ...}}
        entity_ids = []

        if "entity_profile" in key_facts_jsonb:
            profile = key_facts_jsonb["entity_profile"]
            if "entity_id" in profile:
                entity_ids.append(profile["entity_id"])

        # Could have multiple entities in different structures
        # For now, just extract from entity_profile
        return entity_ids
