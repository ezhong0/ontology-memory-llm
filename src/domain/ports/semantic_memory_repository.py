"""Semantic memory repository port (interface).

Defines the contract for semantic memory data access.
"""

from abc import ABC, abstractmethod

import numpy as np
import numpy.typing as npt

from src.domain.entities.semantic_memory import SemanticMemory


class ISemanticMemoryRepository(ABC):
    """Interface for semantic memory data access.

    Hexagonal architecture: Domain defines the interface,
    infrastructure implements it.
    """

    @abstractmethod
    async def create(self, memory: SemanticMemory) -> SemanticMemory:
        """Create a new semantic memory.

        Args:
            memory: Semantic memory to create

        Returns:
            Created memory with assigned memory_id
        """

    @abstractmethod
    async def find_by_id(self, memory_id: int) -> SemanticMemory | None:
        """Find semantic memory by ID.

        Args:
            memory_id: Memory identifier

        Returns:
            Semantic memory if found, None otherwise
        """

    @abstractmethod
    async def find_by_subject_predicate(
        self,
        subject_entity_id: str,
        predicate: str,
        user_id: str,
        status_filter: str = "active",
    ) -> list[SemanticMemory]:
        """Find semantic memories by subject and predicate.

        Used for conflict detection.

        Args:
            subject_entity_id: Subject entity ID
            predicate: Predicate name
            user_id: User identifier
            status_filter: Filter by status (default: "active")

        Returns:
            List of matching semantic memories
        """

    @abstractmethod
    async def find_similar(
        self,
        user_id: str,
        query_embedding: npt.NDArray[np.float64],
        limit: int = 50,
        min_confidence: float | None = None,
    ) -> list[tuple[SemanticMemory, float]]:
        """Find similar semantic memories using pgvector.

        Args:
            user_id: User identifier
            query_embedding: Query embedding vector (1536-dim)
            limit: Maximum number of results
            min_confidence: Optional minimum confidence threshold

        Returns:
            List of tuples (semantic_memory, similarity_score), ordered by similarity descending
        """

    @abstractmethod
    async def update(self, memory: SemanticMemory) -> SemanticMemory:
        """Update an existing semantic memory.

        Args:
            memory: Memory with updated fields

        Returns:
            Updated memory
        """
