"""API models for consolidation endpoints.

Pydantic models for request/response validation.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ConsolidationRequest(BaseModel):
    """Request to consolidate memories.

    Example:
        POST /api/v1/consolidate
        {
            "scope_type": "entity",
            "scope_identifier": "customer:acme_123",
            "force": false
        }
    """

    scope_type: str = Field(
        ...,
        description="Scope type for consolidation",
        examples=["entity", "topic", "session_window"],
    )
    scope_identifier: str = Field(
        ..., description="Scope identifier (entity_id, predicate_pattern, or session_count)"
    )
    force: bool = Field(
        default=False,
        description="Force consolidation even if threshold not met",
    )

    @field_validator("scope_type")
    @classmethod
    def validate_scope_type(cls, v: str) -> str:
        """Validate scope type."""
        valid_types = ["entity", "topic", "session_window"]
        if v not in valid_types:
            raise ValueError(f"scope_type must be one of {valid_types}, got {v}")
        return v


class KeyFactResponse(BaseModel):
    """Key fact in consolidation response."""

    value: Any = Field(..., description="Fact value")
    confidence: float = Field(..., description="Fact confidence [0.0, 1.0]", ge=0.0, le=1.0)
    reinforced: int = Field(..., description="Number of observations", ge=1)
    source_memory_ids: list[int] = Field(..., description="Source memory IDs")


class ConsolidationResponse(BaseModel):
    """Response from consolidation.

    Example:
        {
            "summary_id": 123,
            "scope_type": "entity",
            "scope_identifier": "customer:acme_123",
            "summary_text": "Acme Corporation prefers Friday deliveries...",
            "key_facts": {
                "delivery_preference": {
                    "value": "Friday deliveries",
                    "confidence": 0.90,
                    "reinforced": 5,
                    "source_memory_ids": [12, 24, 35, 42, 58]
                }
            },
            "interaction_patterns": ["Asks about payment history first"],
            "needs_validation": ["Credit limit last validated 120 days ago"],
            "confidence": 0.85,
            "created_at": "2025-10-15T10:30:00Z"
        }
    """

    summary_id: int = Field(..., description="Summary identifier")
    scope_type: str = Field(..., description="Scope type")
    scope_identifier: str = Field(..., description="Scope identifier")
    summary_text: str = Field(..., description="Concise narrative summary")
    key_facts: dict[str, KeyFactResponse] = Field(..., description="Key facts extracted")
    interaction_patterns: list[str] = Field(
        default_factory=list, description="Observed interaction patterns"
    )
    needs_validation: list[str] = Field(
        default_factory=list, description="Facts needing validation"
    )
    confidence: float = Field(..., description="Overall summary confidence", ge=0.0, le=1.0)
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")


class GetSummariesRequest(BaseModel):
    """Query parameters for getting summaries."""

    limit: int = Field(default=10, description="Maximum number of summaries", ge=1, le=100)
    min_confidence: float = Field(
        default=0.5, description="Minimum confidence threshold", ge=0.0, le=1.0
    )


class SummaryMetadataResponse(BaseModel):
    """Metadata for a single summary."""

    summary_id: int = Field(..., description="Summary identifier")
    scope_type: str = Field(..., description="Scope type")
    scope_identifier: str = Field(..., description="Scope identifier")
    summary_text: str = Field(..., description="Summary text preview")
    confidence: float = Field(..., description="Summary confidence", ge=0.0, le=1.0)
    key_fact_count: int = Field(..., description="Number of key facts")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")


class GetSummariesResponse(BaseModel):
    """Response with list of summaries.

    Example:
        GET /api/v1/summaries/entity/customer:acme_123
        {
            "summaries": [
                {
                    "summary_id": 123,
                    "scope_type": "entity",
                    "scope_identifier": "customer:acme_123",
                    "summary_text": "Acme Corporation prefers Friday deliveries...",
                    "confidence": 0.85,
                    "key_fact_count": 5,
                    "created_at": "2025-10-15T10:30:00Z"
                }
            ],
            "total_count": 1
        }
    """

    summaries: list[SummaryMetadataResponse] = Field(..., description="List of summaries")
    total_count: int = Field(..., description="Total number of summaries")


class TriggerStatusResponse(BaseModel):
    """Status of consolidation trigger check.

    Example:
        GET /api/v1/consolidate/status?user_id=user_1
        {
            "user_id": "user_1",
            "should_consolidate": true,
            "pending_scopes": [
                {
                    "scope_type": "entity",
                    "scope_identifier": "customer:acme_123",
                    "reason": "10+ episodic memories about entity"
                }
            ],
            "checked_at": "2025-10-15T10:30:00Z"
        }
    """

    user_id: str = Field(..., description="User identifier")
    should_consolidate: bool = Field(..., description="Whether consolidation is recommended")
    pending_scopes: list[dict[str, str]] = Field(
        default_factory=list, description="Scopes pending consolidation"
    )
    checked_at: str = Field(..., description="Check timestamp (ISO 8601)")
