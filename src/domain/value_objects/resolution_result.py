"""Resolution result value object.

Represents the result of entity resolution (immutable).
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ResolutionMethod(str, Enum):
    """Method used to resolve an entity mention.

    Maps to the 5-stage entity resolution algorithm in DESIGN.md.
    """

    EXACT_MATCH = "exact"  # Stage 1: Exact match on canonical name
    USER_ALIAS = "alias"  # Stage 2: User-specific alias
    FUZZY_MATCH = "fuzzy"  # Stage 3: pg_trgm fuzzy match
    COREFERENCE = "coreference"  # Stage 4: LLM coreference resolution
    DOMAIN_DB = "domain_db"  # Stage 5: Domain database lookup (lazy creation)
    FAILED = "failed"  # Resolution failed


@dataclass(frozen=True)
class ResolutionResult:
    """Immutable result of entity resolution.

    Attributes:
        entity_id: Resolved canonical entity ID
        confidence: Confidence score [0.0, 1.0]
        method: Resolution method used
        mention_text: Original mention text that was resolved
        canonical_name: Canonical name of resolved entity
        metadata: Additional resolution metadata (method-specific)
    """

    entity_id: str
    confidence: float
    method: ResolutionMethod
    mention_text: str
    canonical_name: str
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate resolution result invariants."""
        if not self.entity_id and self.method != ResolutionMethod.FAILED:
            raise ValueError("entity_id required unless method is FAILED")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")

        if not self.mention_text:
            raise ValueError("mention_text cannot be empty")

        if self.method == ResolutionMethod.FAILED and self.confidence > 0.0:
            raise ValueError("Failed resolution must have confidence 0.0")

    @property
    def is_high_confidence(self) -> bool:
        """Check if resolution is high confidence.

        Returns:
            True if confidence >= 0.8
        """
        return self.confidence >= 0.8

    @property
    def is_successful(self) -> bool:
        """Check if resolution succeeded.

        Returns:
            True if method is not FAILED
        """
        return self.method != ResolutionMethod.FAILED

    @classmethod
    def failed(cls, mention_text: str, reason: str) -> "ResolutionResult":
        """Create a failed resolution result.

        Args:
            mention_text: The mention text that failed to resolve
            reason: Reason for failure

        Returns:
            ResolutionResult with method=FAILED and confidence=0.0
        """
        return cls(
            entity_id="",
            confidence=0.0,
            method=ResolutionMethod.FAILED,
            mention_text=mention_text,
            canonical_name="",
            metadata={"reason": reason},
        )

    def __str__(self) -> str:
        """String representation for logging."""
        if not self.is_successful:
            return f'Failed to resolve "{self.mention_text}": {self.metadata.get("reason", "unknown")}'

        return (
            f'Resolved "{self.mention_text}" → {self.canonical_name} '
            f'(id={self.entity_id}, method={self.method.value}, confidence={self.confidence:.2f})'
        )
