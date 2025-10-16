"""API models for procedural memory endpoints.

Request and response models for pattern detection and retrieval.
"""

from pydantic import BaseModel, Field


class DetectPatternsRequest(BaseModel):
    """Request to detect patterns from user's episodic memories."""

    min_occurrences: int = Field(
        default=3,
        ge=2,
        le=100,
        description="Minimum number of times pattern must appear to be detected",
    )
    max_patterns: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of patterns to return",
    )


class PatternResponse(BaseModel):
    """Response model for a detected pattern."""

    memory_id: int = Field(description="Procedural memory ID")
    trigger_pattern: str = Field(description="Pattern trigger description")
    action_heuristic: str = Field(description="Action/behavior pattern")
    confidence: float = Field(description="Pattern confidence (0.0-1.0)")
    observed_count: int = Field(description="Number of times pattern observed")
    created_at: str = Field(description="Pattern creation timestamp (ISO format)")


class DetectPatternsResponse(BaseModel):
    """Response to pattern detection request."""

    patterns: list[PatternResponse] = Field(description="Detected patterns")
    total_count: int = Field(description="Total patterns detected")
    user_id: str = Field(description="User ID")


class GetPatternsRequest(BaseModel):
    """Request to retrieve patterns for a user."""

    min_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of patterns to return",
    )


class GetPatternsResponse(BaseModel):
    """Response with user's procedural memories."""

    patterns: list[PatternResponse] = Field(description="User's patterns")
    total_count: int = Field(description="Total patterns found")
    user_id: str = Field(description="User ID")


class AugmentQueryRequest(BaseModel):
    """Request to augment a query with procedural memory patterns."""

    query: str = Field(description="Query text to augment")
    max_patterns: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of patterns to include",
    )


class AugmentQueryResponse(BaseModel):
    """Response with query augmented by procedural patterns."""

    original_query: str = Field(description="Original query text")
    augmented_query: str = Field(description="Query augmented with pattern context")
    patterns_applied: list[str] = Field(description="Pattern IDs applied")
    pattern_count: int = Field(description="Number of patterns applied")
