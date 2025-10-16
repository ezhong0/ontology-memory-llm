"""Memory summary repository implementation.

Implements memory summary storage and retrieval using SQLAlchemy and PostgreSQL with pgvector.
"""


import numpy as np
import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.memory_summary import MemorySummary
from src.domain.exceptions import RepositoryError
from src.domain.ports.embedding_service import IEmbeddingService
from src.domain.ports.summary_repository import ISummaryRepository
from src.domain.value_objects.memory_candidate import MemoryCandidate
from src.infrastructure.database.models import MemorySummary as MemorySummaryModel

logger = structlog.get_logger(__name__)


class SummaryRepository(ISummaryRepository):
    """SQLAlchemy implementation of memory summary storage and retrieval.

    Handles both:
    1. Storage: Creating and updating memory summaries (consolidation output)
    2. Retrieval: Finding summaries as MemoryCandidate objects for retrieval pipeline

    Vision alignment: Graceful forgetting through consolidation (VISION.md)
    """

    def __init__(
        self, session: AsyncSession, embedding_service: IEmbeddingService | None = None
    ):
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
            embedding_service: Optional embedding service for create()
        """
        self.session = session
        self._embedding_service = embedding_service

    async def find_similar(
        self,
        user_id: str,
        query_embedding: np.ndarray,
        limit: int = 5,
        scope_type: str | None = None,
    ) -> list[MemoryCandidate]:
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
            msg = f"Error finding similar summaries: {e}"
            raise RepositoryError(msg) from e

    async def find_by_scope(
        self,
        user_id: str,
        scope_type: str,
        scope_identifier: str,
    ) -> MemoryCandidate | None:
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
            msg = f"Error finding summary by scope: {e}"
            raise RepositoryError(msg) from e

    async def find_by_scope_with_filters(
        self,
        user_id: str,
        scope_type: str,
        scope_identifier: str,
        limit: int = 10,
        min_confidence: float = 0.5,
    ) -> list[MemorySummary]:
        """Find summaries by scope with filtering.

        Args:
            user_id: User identifier
            scope_type: Scope type (entity, topic, session_window)
            scope_identifier: Scope identifier
            limit: Maximum number of results
            min_confidence: Minimum confidence threshold

        Returns:
            List of memory summaries matching filters
        """
        try:
            stmt = select(MemorySummaryModel).where(
                MemorySummaryModel.user_id == user_id,
                MemorySummaryModel.scope_type == scope_type,
                MemorySummaryModel.scope_identifier == scope_identifier,
                MemorySummaryModel.confidence >= min_confidence,
            ).order_by(MemorySummaryModel.created_at.desc()).limit(limit)

            result = await self.session.execute(stmt)
            models = result.scalars().all()

            summaries = [
                MemorySummary(
                    summary_id=model.summary_id,
                    user_id=model.user_id,
                    scope_type=model.scope_type,
                    scope_identifier=model.scope_identifier,
                    summary_text=model.summary_text,
                    key_facts=model.key_facts,
                    source_data=model.source_data,
                    confidence=model.confidence,
                    embedding=list(model.embedding) if model.embedding else None,
                    created_at=model.created_at,
                    supersedes_summary_id=model.supersedes_summary_id,
                )
                for model in models
            ]

            logger.debug(
                "found_summaries_with_filters",
                user_id=user_id,
                scope_type=scope_type,
                scope_identifier=scope_identifier,
                count=len(summaries),
            )

            return summaries

        except Exception as e:
            logger.error(
                "find_summaries_with_filters_error",
                user_id=user_id,
                scope_type=scope_type,
                scope_identifier=scope_identifier,
                error=str(e),
            )
            msg = f"Error finding summaries with filters: {e}"
            raise RepositoryError(msg) from e

    async def create(self, summary: MemorySummary) -> MemorySummary:
        """Create a new memory summary.

        Args:
            summary: Memory summary to create (without summary_id)

        Returns:
            Created summary with assigned summary_id

        Raises:
            RepositoryError: If creation fails
        """
        try:
            # Generate embedding if not present
            embedding_vector = summary.embedding
            if embedding_vector is None:
                if self._embedding_service is None:
                    msg = (
                        "Cannot create summary without embedding: "
                        "embedding_service not provided"
                    )
                    raise RepositoryError(
                        msg
                    )

                logger.debug(
                    "generating_summary_embedding",
                    user_id=summary.user_id,
                    scope_type=summary.scope_type,
                )

                embedding_vector = await self._embedding_service.generate_embedding(
                    summary.summary_text
                )

            # Create database model
            model = MemorySummaryModel(
                user_id=summary.user_id,
                scope_type=summary.scope_type,
                scope_identifier=summary.scope_identifier,
                summary_text=summary.summary_text,
                key_facts=summary.key_facts,
                source_data=summary.source_data,
                confidence=summary.confidence,
                embedding=embedding_vector,
                created_at=summary.created_at,
                supersedes_summary_id=summary.supersedes_summary_id,
            )

            self.session.add(model)
            await self.session.flush()  # Get assigned summary_id

            logger.info(
                "summary_created",
                summary_id=model.summary_id,
                user_id=summary.user_id,
                scope_type=summary.scope_type,
                scope_identifier=summary.scope_identifier,
            )

            # Return value object with assigned ID
            return MemorySummary(
                summary_id=model.summary_id,
                user_id=model.user_id,
                scope_type=model.scope_type,
                scope_identifier=model.scope_identifier,
                summary_text=model.summary_text,
                key_facts=model.key_facts,
                source_data=model.source_data,
                confidence=model.confidence,
                embedding=list(model.embedding) if model.embedding else None,
                created_at=model.created_at,
                supersedes_summary_id=model.supersedes_summary_id,
            )

        except Exception as e:
            logger.error(
                "summary_creation_error",
                user_id=summary.user_id,
                scope_type=summary.scope_type,
                error=str(e),
            )
            msg = f"Error creating summary: {e}"
            raise RepositoryError(msg) from e

    async def get_by_id(
        self,
        summary_id: int,
        user_id: str | None = None,
    ) -> MemorySummary | None:
        """Get memory summary by ID.

        Args:
            summary_id: Summary identifier
            user_id: Optional user ID for security filtering

        Returns:
            Memory summary if found, None otherwise

        Raises:
            RepositoryError: If query fails
        """
        try:
            stmt = select(MemorySummaryModel).where(
                MemorySummaryModel.summary_id == summary_id
            )

            if user_id:
                stmt = stmt.where(MemorySummaryModel.user_id == user_id)

            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                logger.debug(
                    "summary_not_found",
                    summary_id=summary_id,
                    user_id=user_id,
                )
                return None

            logger.debug(
                "summary_retrieved",
                summary_id=summary_id,
                user_id=model.user_id,
                scope_type=model.scope_type,
            )

            # Convert to value object
            return MemorySummary(
                summary_id=model.summary_id,
                user_id=model.user_id,
                scope_type=model.scope_type,
                scope_identifier=model.scope_identifier,
                summary_text=model.summary_text,
                key_facts=model.key_facts,
                source_data=model.source_data,
                confidence=model.confidence,
                embedding=list(model.embedding) if model.embedding else None,
                created_at=model.created_at,
                supersedes_summary_id=model.supersedes_summary_id,
            )

        except Exception as e:
            logger.error(
                "summary_retrieval_error",
                summary_id=summary_id,
                user_id=user_id,
                error=str(e),
            )
            msg = f"Error retrieving summary: {e}"
            raise RepositoryError(msg) from e

    def _extract_entity_ids(self, key_facts_jsonb: dict) -> list[str]:
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
