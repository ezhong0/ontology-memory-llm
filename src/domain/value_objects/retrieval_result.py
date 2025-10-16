"""Retrieval result value objects.

Encapsulates the result of a memory retrieval operation with metadata.
"""

from dataclasses import dataclass
from typing import Any

from src.domain.value_objects.memory_candidate import ScoredMemory
from src.domain.value_objects.query_context import QueryContext


@dataclass(frozen=True)
class RetrievalMetadata:
    """Metadata about the retrieval operation.

    Provides transparency into the retrieval process for debugging
    and performance monitoring.

    Attributes:
        candidates_generated: Total number of candidates retrieved from all layers
        candidates_scored: Number of candidates that were scored
        top_score: Highest relevance score achieved
        retrieval_time_ms: Total retrieval time in milliseconds
    """

    candidates_generated: int
    candidates_scored: int
    top_score: float
    retrieval_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "candidates_generated": self.candidates_generated,
            "candidates_scored": self.candidates_scored,
            "top_score": self.top_score,
            "retrieval_time_ms": self.retrieval_time_ms,
        }


@dataclass(frozen=True)
class RetrievalResult:
    """Result of memory retrieval with provenance.

    Contains the scored memories, query context, and metadata about
    the retrieval operation.

    Attributes:
        memories: List of scored memories, sorted by relevance
        query_context: The query context used for retrieval
        metadata: Metadata about the retrieval operation
    """

    memories: list[ScoredMemory]
    query_context: QueryContext
    metadata: RetrievalMetadata

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "memories": [m.to_dict() for m in self.memories],
            "query_context": {
                "query_text": self.query_context.query_text,
                "entity_ids": self.query_context.entity_ids,
                "user_id": self.query_context.user_id,
                "strategy": self.query_context.strategy,
            },
            "metadata": self.metadata.to_dict(),
        }
