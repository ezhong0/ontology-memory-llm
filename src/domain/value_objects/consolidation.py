"""Consolidation value objects.

These objects represent consolidation scopes and summary data for memory synthesis.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ConsolidationScope:
    """Scope for memory consolidation.

    Defines what memories should be consolidated together.

    Vision: "Replace many specific memories with one abstract summary"

    Attributes:
        type: Scope type (entity, topic, session_window)
        identifier: Scope identifier (entity_id, predicate_pattern, or session_count)
        metadata: Optional scope-specific metadata
    """

    type: str  # entity, topic, session_window
    identifier: str
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate consolidation scope."""
        valid_types = ["entity", "topic", "session_window"]
        if self.type not in valid_types:
            raise ValueError(f"type must be one of {valid_types}, got {self.type}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type,
            "identifier": self.identifier,
            "metadata": self.metadata,
        }

    @classmethod
    def entity_scope(cls, entity_id: str) -> "ConsolidationScope":
        """Create entity scope for consolidating memories about a specific entity."""
        return cls(type="entity", identifier=entity_id)

    @classmethod
    def topic_scope(cls, predicate_pattern: str) -> "ConsolidationScope":
        """Create topic scope for consolidating memories matching a predicate pattern."""
        return cls(type="topic", identifier=predicate_pattern)

    @classmethod
    def session_window_scope(cls, num_sessions: int = 5) -> "ConsolidationScope":
        """Create session window scope for consolidating recent N sessions."""
        return cls(type="session_window", identifier=str(num_sessions))


@dataclass(frozen=True)
class KeyFact:
    """A key fact extracted from consolidation.

    Attributes:
        value: Fact value
        confidence: Confidence score [0.0, 1.0]
        reinforced: Number of times fact was observed
        source_memory_ids: Memory IDs that contributed to this fact
    """

    value: Any
    confidence: float
    reinforced: int
    source_memory_ids: List[int]

    def __post_init__(self) -> None:
        """Validate key fact."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")

        if self.reinforced < 1:
            raise ValueError(f"reinforced must be >= 1, got {self.reinforced}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "value": self.value,
            "confidence": self.confidence,
            "reinforced": self.reinforced,
            "source_memory_ids": self.source_memory_ids,
        }


@dataclass(frozen=True)
class SummaryData:
    """Data extracted from LLM synthesis.

    Result of LLM consolidation before storage.

    Attributes:
        summary_text: Concise narrative summary (2-3 sentences)
        key_facts: Dictionary of key facts extracted
        interaction_patterns: List of observed interaction patterns
        needs_validation: List of facts needing validation (aged or low confidence)
        confirmed_memory_ids: Memory IDs to boost confidence (high-confidence in summary)
    """

    summary_text: str
    key_facts: Dict[str, KeyFact]
    interaction_patterns: List[str]
    needs_validation: List[str]
    confirmed_memory_ids: List[int]

    def __post_init__(self) -> None:
        """Validate summary data."""
        if not self.summary_text:
            raise ValueError("summary_text cannot be empty")

        if len(self.summary_text) < 10:
            raise ValueError(f"summary_text too short: {self.summary_text}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "summary_text": self.summary_text,
            "key_facts": {k: v.to_dict() for k, v in self.key_facts.items()},
            "interaction_patterns": self.interaction_patterns,
            "needs_validation": self.needs_validation,
            "confirmed_memory_ids": self.confirmed_memory_ids,
        }

    @classmethod
    def from_llm_response(cls, response: Dict[str, Any]) -> "SummaryData":
        """Parse LLM response into SummaryData.

        Args:
            response: LLM response dictionary

        Returns:
            Validated SummaryData

        Raises:
            ValueError: If LLM response is invalid
        """
        try:
            # Parse key facts
            key_facts = {}
            for fact_name, fact_data in response.get("key_facts", {}).items():
                key_facts[fact_name] = KeyFact(
                    value=fact_data["value"],
                    confidence=fact_data["confidence"],
                    reinforced=fact_data.get("reinforced", 1),
                    source_memory_ids=fact_data.get("source_memory_ids", []),
                )

            return cls(
                summary_text=response["summary_text"],
                key_facts=key_facts,
                interaction_patterns=response.get("interaction_patterns", []),
                needs_validation=response.get("needs_validation", []),
                confirmed_memory_ids=response.get("confirmed_memory_ids", []),
            )

        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Invalid LLM response structure: {e}") from e


@dataclass
class MemorySummary:
    """A consolidated memory summary.

    Result of consolidation stored in memory_summaries table.

    Attributes:
        summary_id: Unique identifier (None before storage)
        user_id: User who owns this summary
        scope_type: Scope type (entity, topic, session_window)
        scope_identifier: Scope identifier
        summary_text: Concise narrative summary
        key_facts: Dictionary of key facts
        source_data: Metadata about source memories
        confidence: Overall summary confidence
        embedding: 1536-dim embedding vector (None before embedding)
        created_at: Creation timestamp
        supersedes_summary_id: Previous summary this replaces (if any)
    """

    user_id: str
    scope_type: str
    scope_identifier: str
    summary_text: str
    key_facts: Dict[str, Dict[str, Any]]
    source_data: Dict[str, Any]
    confidence: float
    created_at: datetime
    summary_id: Optional[int] = None
    embedding: Optional[List[float]] = None
    supersedes_summary_id: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate memory summary."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")

        valid_scopes = ["entity", "topic", "session_window"]
        if self.scope_type not in valid_scopes:
            raise ValueError(f"scope_type must be one of {valid_scopes}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "summary_id": self.summary_id,
            "user_id": self.user_id,
            "scope_type": self.scope_type,
            "scope_identifier": self.scope_identifier,
            "summary_text": self.summary_text,
            "key_facts": self.key_facts,
            "source_data": self.source_data,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "supersedes_summary_id": self.supersedes_summary_id,
        }
