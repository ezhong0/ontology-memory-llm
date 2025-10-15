"""Memory summary repository port (interface).

Defines the contract for memory summary data access.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

import numpy as np

from src.domain.value_objects.consolidation import MemorySummary
from src.domain.value_objects.memory_candidate import MemoryCandidate


class ISummaryRepository(ABC):
    """Interface for memory summary data access.

    Hexagonal architecture: Domain defines the interface,
    infrastructure implements it.
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def create(self, summary: MemorySummary) -> MemorySummary:
        """Create a new memory summary.

        Args:
            summary: MemorySummary to store (summary_id will be assigned)

        Returns:
            MemorySummary with assigned summary_id

        Raises:
            RepositoryError: If creation fails
        """
        pass

    @abstractmethod
    async def get_by_id(
        self, summary_id: int, user_id: Optional[str] = None
    ) -> Optional[MemorySummary]:
        """Get memory summary by ID.

        Args:
            summary_id: Summary identifier
            user_id: Optional user filter for security

        Returns:
            MemorySummary if found, None otherwise

        Raises:
            RepositoryError: If query fails
        """
        pass
