"""Memory API models.

Pydantic models for memory retrieval and validation endpoints.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SemanticMemoryResponse(BaseModel):
    """Response model for semantic memory retrieval."""

    memory_id: int = Field(..., description="Memory ID")
    user_id: str = Field(..., description="User who owns this memory")
    subject_entity_id: str = Field(..., description="Entity this memory is about")
    predicate: str = Field(..., description="Relationship type")
    predicate_type: str = Field(..., description="Type of predicate")
    object_value: dict[str, Any] = Field(..., description="Memory value")
    confidence: float = Field(..., description="Confidence score (0-1)")
    status: str = Field(..., description="Memory status (active, aging, superseded, invalidated)")
    reinforcement_count: int = Field(..., description="Number of times reinforced")
    last_validated_at: Optional[datetime] = Field(None, description="When last validated")
    created_at: datetime = Field(..., description="When memory was created")
    updated_at: datetime = Field(..., description="When memory was last updated")


class ValidationRequest(BaseModel):
    """Request model for memory validation."""

    user_id: str = Field(..., description="User validating the memory")
    confirmed: bool = Field(..., description="Whether memory is still valid")
    corrected_value: Optional[dict[str, Any]] = Field(None, description="Corrected value if memory is outdated")


class ValidationResponse(BaseModel):
    """Response model for memory validation."""

    memory_id: int = Field(..., description="Memory ID")
    status: str = Field(..., description="New memory status")
    confidence: float = Field(..., description="Updated confidence")
    reinforcement_count: int = Field(..., description="Updated reinforcement count")
    last_validated_at: datetime = Field(..., description="Updated validation timestamp")
