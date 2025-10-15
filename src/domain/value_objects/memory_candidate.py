"""Memory candidate value objects for retrieval.

These objects represent memory candidates retrieved from various layers
before scoring and ranking.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

import numpy as np


@dataclass(frozen=True)
class MemoryCandidate:
    """A candidate memory from retrieval.

    Represents a memory retrieved from any layer (semantic, episodic, summary)
    before multi-signal scoring is applied.

    Attributes:
        memory_id: Unique memory identifier within its type
        memory_type: Layer the memory came from
        content: Human-readable memory content
        entities: List of entity IDs mentioned in the memory
        embedding: 1536-dimensional embedding vector
        created_at: When the memory was created
        importance: Stored importance score [0.0, 1.0]
        confidence: For semantic memories, confidence score
        reinforcement_count: For semantic memories, validation count
        last_validated_at: For semantic memories, last validation timestamp
        metadata: Additional type-specific metadata
    """

    memory_id: int
    memory_type: Literal["semantic", "episodic", "summary"]
    content: str
    entities: List[str]
    embedding: np.ndarray
    created_at: datetime
    importance: float

    # Type-specific fields
    confidence: Optional[float] = None
    reinforcement_count: Optional[int] = None
    last_validated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate memory candidate."""
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(f"importance must be in [0, 1], got {self.importance}")

        if len(self.embedding.shape) != 1:
            raise ValueError(f"embedding must be 1D, got shape {self.embedding.shape}")

        if self.embedding.shape[0] != 1536:
            raise ValueError(f"embedding must be 1536-dimensional, got {self.embedding.shape[0]}")

        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")

        if self.reinforcement_count is not None:
            if self.reinforcement_count < 0:
                raise ValueError(
                    f"reinforcement_count must be >= 0, got {self.reinforcement_count}"
                )

    @property
    def is_semantic(self) -> bool:
        """Check if this is a semantic memory."""
        return self.memory_type == "semantic"

    @property
    def is_episodic(self) -> bool:
        """Check if this is an episodic memory."""
        return self.memory_type == "episodic"

    @property
    def is_summary(self) -> bool:
        """Check if this is a memory summary."""
        return self.memory_type == "summary"

    @property
    def age_days(self) -> float:
        """Calculate age of memory in days."""
        now = datetime.now(self.created_at.tzinfo)
        delta = now - self.created_at
        return delta.total_seconds() / 86400.0  # 86400 seconds in a day


@dataclass(frozen=True)
class SignalBreakdown:
    """Breakdown of individual signals contributing to relevance score.

    Provides explainability for why a memory was scored as relevant.

    Attributes:
        semantic_similarity: Cosine similarity score [0.0, 1.0]
        entity_overlap: Jaccard similarity of entities [0.0, 1.0]
        recency_score: Exponential decay score [0.0, 1.0]
        importance_score: Stored importance [0.0, 1.0]
        reinforcement_score: Reinforcement-based score [0.0, 1.0]
        effective_confidence: Confidence after passive decay [0.0, 1.0]
    """

    semantic_similarity: float
    entity_overlap: float
    recency_score: float
    importance_score: float
    reinforcement_score: float
    effective_confidence: float

    def __post_init__(self) -> None:
        """Validate signal values."""
        signals = {
            "semantic_similarity": self.semantic_similarity,
            "entity_overlap": self.entity_overlap,
            "recency_score": self.recency_score,
            "importance_score": self.importance_score,
            "reinforcement_score": self.reinforcement_score,
            "effective_confidence": self.effective_confidence,
        }

        for name, value in signals.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value}")

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization."""
        return {
            "semantic_similarity": self.semantic_similarity,
            "entity_overlap": self.entity_overlap,
            "recency_score": self.recency_score,
            "importance_score": self.importance_score,
            "reinforcement_score": self.reinforcement_score,
            "effective_confidence": self.effective_confidence,
        }


@dataclass(frozen=True)
class ScoredMemory:
    """Memory with relevance score and signal breakdown.

    Result of multi-signal scoring, ready for ranking and selection.

    Attributes:
        candidate: The original memory candidate
        relevance_score: Final weighted relevance score [0.0, 1.0]
        signal_breakdown: Breakdown of individual signal contributions
    """

    candidate: MemoryCandidate
    relevance_score: float
    signal_breakdown: SignalBreakdown

    def __post_init__(self) -> None:
        """Validate scored memory."""
        if not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError(f"relevance_score must be in [0, 1], got {self.relevance_score}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "memory_id": self.candidate.memory_id,
            "memory_type": self.candidate.memory_type,
            "content": self.candidate.content,
            "relevance_score": self.relevance_score,
            "signal_breakdown": self.signal_breakdown.to_dict(),
            "created_at": self.candidate.created_at.isoformat(),
            "importance": self.candidate.importance,
            "confidence": self.candidate.confidence,
            "reinforcement_count": self.candidate.reinforcement_count,
        }
