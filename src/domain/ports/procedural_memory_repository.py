"""Procedural memory repository port.

Interface for procedural memory persistence and retrieval.
"""

from abc import ABC, abstractmethod

import numpy as np
from numpy import typing as npt

from src.domain.entities.procedural_memory import ProceduralMemory


class IProceduralMemoryRepository(ABC):
    """Port for procedural memory data access.

    Philosophy: Repository returns domain value objects, not database models.
    Infrastructure layer handles conversion.
    """

    @abstractmethod
    async def create(self, memory: ProceduralMemory) -> ProceduralMemory:
        """Create a new procedural memory.

        Args:
            memory: ProceduralMemory to store (memory_id will be assigned)

        Returns:
            ProceduralMemory with assigned memory_id

        Raises:
            RepositoryError: If creation fails
        """

    @abstractmethod
    async def get_by_id(
        self, memory_id: int, user_id: str | None = None
    ) -> ProceduralMemory | None:
        """Get procedural memory by ID.

        Args:
            memory_id: Memory identifier
            user_id: Optional user filter for security

        Returns:
            ProceduralMemory if found, None otherwise

        Raises:
            RepositoryError: If query fails
        """

    @abstractmethod
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

        Raises:
            RepositoryError: If query fails
        """

    @abstractmethod
    async def find_similar(
        self,
        user_id: str,
        query_embedding: npt.NDArray[np.float64],
        limit: int = 10,
        min_confidence: float = 0.5,
    ) -> list[ProceduralMemory]:
        """Find procedural memories similar to query.

        Uses pgvector cosine similarity on trigger_pattern embeddings.

        Philosophy: Find patterns with similar triggers to augment retrieval.

        Args:
            user_id: User identifier
            query_embedding: Query embedding (1536-dimensional)
            limit: Maximum number of results
            min_confidence: Minimum pattern confidence

        Returns:
            List of ProceduralMemory instances ordered by similarity

        Raises:
            RepositoryError: If query fails
        """

    @abstractmethod
    async def update(self, memory: ProceduralMemory) -> ProceduralMemory:
        """Update an existing procedural memory.

        Typically used to increment observed_count and adjust confidence.

        Args:
            memory: ProceduralMemory to update (must have memory_id)

        Returns:
            Updated ProceduralMemory

        Raises:
            RepositoryError: If update fails or memory_id not found
        """

    @abstractmethod
    async def delete(self, memory_id: int, user_id: str) -> bool:
        """Delete a procedural memory.

        Args:
            memory_id: Memory identifier
            user_id: User identifier (for security)

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """

    @abstractmethod
    async def find_by_trigger_features(
        self,
        user_id: str,
        intent: str | None = None,
        entity_types: list[str] | None = None,
        topics: list[str] | None = None,
        min_confidence: float = 0.5,
        limit: int = 20,
    ) -> list[ProceduralMemory]:
        """Find procedural memories matching trigger features.

        Deterministic matching based on JSONB trigger_features.

        Args:
            user_id: User identifier
            intent: Optional intent filter
            entity_types: Optional entity type filters
            topics: Optional topic filters
            min_confidence: Minimum confidence threshold
            limit: Maximum number of results

        Returns:
            List of ProceduralMemory instances

        Raises:
            RepositoryError: If query fails
        """
