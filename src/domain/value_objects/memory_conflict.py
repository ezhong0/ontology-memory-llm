"""Memory conflict value object.

Represents a detected conflict between semantic memories.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ConflictType(str, Enum):
    """Type of memory conflict."""

    VALUE_MISMATCH = "value_mismatch"  # Same predicate, different values
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"  # Time-based contradiction
    LOGICAL_CONTRADICTION = "logical_contradiction"  # Logically impossible
    MEMORY_VS_DB = "memory_vs_db"  # Memory contradicts authoritative database


class ConflictResolution(str, Enum):
    """How a conflict should be resolved."""

    KEEP_NEWEST = "keep_newest"  # Keep most recent observation
    KEEP_HIGHEST_CONFIDENCE = "keep_highest_confidence"  # Keep highest confidence
    KEEP_MOST_REINFORCED = "keep_most_reinforced"  # Keep most observations
    REQUIRE_CLARIFICATION = "require_clarification"  # User must clarify
    MARK_BOTH_INVALID = "mark_both_invalid"  # Both are wrong
    TRUST_DB = "trust_db"  # Trust authoritative database over memory (Correspondence Truth)


@dataclass(frozen=True)
class MemoryConflict:
    """Immutable conflict detection result.

    Represents a detected conflict between a new observation and existing memory.

    Entity-tagged natural language approach: Conflicts detected via semantic
    similarity + entity overlap + LLM-detected contradiction.

    Attributes:
        conflict_type: Type of conflict detected
        new_memory_id: ID of new conflicting memory (if stored)
        existing_memory_id: ID of existing conflicting memory
        entities: Entity IDs that both memories are about
        existing_content: Content of existing memory (natural language)
        new_content: Content of new observation (natural language)
        recommended_resolution: Recommended resolution strategy
        confidence_diff: Confidence difference (new - existing)
        temporal_diff_days: Time difference in days (new - existing)
        semantic_similarity: Cosine similarity between embeddings [0.0, 1.0]
        metadata: Additional conflict details
    """

    conflict_type: ConflictType
    new_memory_id: int | None
    existing_memory_id: int
    entities: list[str]
    existing_content: str
    new_content: str
    recommended_resolution: ConflictResolution
    confidence_diff: float
    temporal_diff_days: int | None
    semantic_similarity: float
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate conflict invariants."""
        if not self.entities:
            msg = "entities cannot be empty"
            raise ValueError(msg)
        if not self.existing_content:
            msg = "existing_content cannot be empty"
            raise ValueError(msg)
        if not self.new_content:
            msg = "new_content cannot be empty"
            raise ValueError(msg)
        if not 0.0 <= self.semantic_similarity <= 1.0:
            msg = f"semantic_similarity must be [0.0, 1.0], got {self.semantic_similarity}"
            raise ValueError(msg)

    @property
    def is_severe(self) -> bool:
        """Check if conflict is severe (requires immediate attention)."""
        return self.conflict_type == ConflictType.LOGICAL_CONTRADICTION

    @property
    def is_resolvable_automatically(self) -> bool:
        """Check if conflict can be resolved automatically."""
        return self.recommended_resolution in [
            ConflictResolution.KEEP_NEWEST,
            ConflictResolution.KEEP_HIGHEST_CONFIDENCE,
            ConflictResolution.KEEP_MOST_REINFORCED,
            ConflictResolution.TRUST_DB,
        ]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "conflict_type": self.conflict_type.value,
            "new_memory_id": self.new_memory_id,
            "existing_memory_id": self.existing_memory_id,
            "entities": self.entities,
            "existing_content": self.existing_content,
            "new_content": self.new_content,
            "recommended_resolution": self.recommended_resolution.value,
            "confidence_diff": self.confidence_diff,
            "temporal_diff_days": self.temporal_diff_days,
            "semantic_similarity": self.semantic_similarity,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation for logging."""
        entities_str = ", ".join(self.entities[:2])  # Show first 2 entities
        if len(self.entities) > 2:
            entities_str += f", +{len(self.entities) - 2} more"

        # Show first 50 chars of each content
        existing_preview = self.existing_content[:50] + "..." if len(self.existing_content) > 50 else self.existing_content
        new_preview = self.new_content[:50] + "..." if len(self.new_content) > 50 else self.new_content

        return (
            f"Conflict({self.conflict_type.value}): entities=[{entities_str}] "
            f"sim={self.semantic_similarity:.2f} "
            f"[{existing_preview} → {new_preview}] "
            f"→ {self.recommended_resolution.value}"
        )
