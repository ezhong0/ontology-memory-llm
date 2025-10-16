"""Episodic memory repository port (interface).

Defines the contract for episodic memory data access.
"""

from abc import ABC, abstractmethod
from uuid import UUID

import numpy as np
import numpy.typing as npt

from src.domain.value_objects.memory_candidate import MemoryCandidate


class IEpisodicMemoryRepository(ABC):
    """Interface for episodic memory data access.

    Hexagonal architecture: Domain defines the interface,
    infrastructure implements it.
    """

    @abstractmethod
    async def find_similar(
        self,
        user_id: str,
        query_embedding: npt.NDArray[np.float64],
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

    @abstractmethod
    async def find_recent(
        self,
        user_id: str,
        limit: int = 10,
        session_id: UUID | None = None,
    ) -> list[MemoryCandidate]:
        """Find recent episodic memories (chronological order).

        Args:
            user_id: User identifier
            limit: Maximum number of results
            session_id: Optional session filter

        Returns:
            List of recent memory candidates
        """

    @abstractmethod
    async def find_by_user(
        self,
        user_id: str,
        since: object | None = None,
        until: object | None = None,
        limit: int = 500,
        session_id: UUID | None = None,
    ) -> list[MemoryCandidate]:
        """Find episodic memories for a user within a time range.

        Used for pattern detection and consolidation.

        Args:
            user_id: User identifier
            since: Optional start datetime filter (inclusive)
            until: Optional end datetime filter (exclusive)
            limit: Maximum number of results
            session_id: Optional session filter

        Returns:
            List of memory candidates ordered by created_at DESC
        """
