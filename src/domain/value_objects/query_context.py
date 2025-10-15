"""Query context value objects for retrieval.

These objects encapsulate the context needed for memory retrieval and scoring.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import numpy as np


@dataclass(frozen=True)
class QueryContext:
    """Context for a retrieval query.

    Encapsulates the query embedding, resolved entities, and metadata
    needed for multi-signal relevance scoring.

    Attributes:
        query_text: Original query string
        query_embedding: 1536-dimensional embedding vector
        entity_ids: List of resolved entity IDs from the query
        user_id: User making the query
        session_id: Optional session context
        timestamp: When the query was made
        strategy: Retrieval strategy (factual_entity_focused, procedural, exploratory, temporal)
    """

    query_text: str
    query_embedding: np.ndarray
    entity_ids: List[str]
    user_id: str
    session_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    strategy: str = "exploratory"

    def __post_init__(self) -> None:
        """Validate query context."""
        if len(self.query_embedding.shape) != 1:
            raise ValueError(f"query_embedding must be 1D, got shape {self.query_embedding.shape}")

        if self.query_embedding.shape[0] != 1536:
            raise ValueError(
                f"query_embedding must be 1536-dimensional, got {self.query_embedding.shape[0]}"
            )

        if not self.user_id:
            raise ValueError("user_id is required")

        valid_strategies = [
            "factual_entity_focused",
            "procedural",
            "exploratory",
            "temporal",
        ]
        if self.strategy not in valid_strategies:
            raise ValueError(f"strategy must be one of {valid_strategies}, got {self.strategy}")


@dataclass(frozen=True)
class RetrievalFilters:
    """Filters for retrieval queries.

    Optional filters to narrow down candidate selection.

    Attributes:
        entity_types: Filter to specific entity types (customer, order, etc.)
        memory_types: Filter to specific memory types (semantic, episodic, summary)
        min_confidence: Minimum confidence threshold
        max_age_days: Maximum age in days
        min_importance: Minimum importance threshold
    """

    entity_types: Optional[List[str]] = None
    memory_types: Optional[List[str]] = None
    min_confidence: Optional[float] = None
    max_age_days: Optional[int] = None
    min_importance: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate filters."""
        if self.min_confidence is not None:
            if not 0.0 <= self.min_confidence <= 1.0:
                raise ValueError(f"min_confidence must be in [0, 1], got {self.min_confidence}")

        if self.max_age_days is not None:
            if self.max_age_days < 0:
                raise ValueError(f"max_age_days must be >= 0, got {self.max_age_days}")

        if self.min_importance is not None:
            if not 0.0 <= self.min_importance <= 1.0:
                raise ValueError(f"min_importance must be in [0, 1], got {self.min_importance}")
