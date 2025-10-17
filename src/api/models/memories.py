"""Memory API models.

Pydantic models for memory retrieval and validation endpoints.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SemanticMemoryResponse(BaseModel):
    """Response model for semantic memory retrieval (entity-tagged natural language)."""

    memory_id: int = Field(..., description="Memory ID")
    user_id: str = Field(..., description="User who owns this memory")
    content: str = Field(..., description="Natural language memory content")
    entities: list[str] = Field(..., description="Entity IDs mentioned in this memory")
    confidence: float = Field(..., description="Confidence score (0-1)")
    importance: float = Field(..., description="Dynamic importance score (0-1)")
    status: str = Field(..., description="Memory status (active, aging, superseded, invalidated)")
    confirmation_count: int = Field(..., description="Number of times confirmed")
    last_accessed_at: Optional[datetime] = Field(None, description="When last accessed or confirmed")
    created_at: datetime = Field(..., description="When memory was created")
    updated_at: datetime = Field(..., description="When memory was last updated")


class ValidationRequest(BaseModel):
    """Request model for memory validation."""

    user_id: str = Field(..., description="User validating the memory")
    confirmed: bool = Field(..., description="Whether memory is still valid")
    corrected_content: Optional[str] = Field(None, description="Corrected natural language content if memory is outdated")


class ValidationResponse(BaseModel):
    """Response model for memory validation."""

    memory_id: int = Field(..., description="Memory ID")
    status: str = Field(..., description="New memory status")
    confidence: float = Field(..., description="Updated confidence")
    confirmation_count: int = Field(..., description="Updated confirmation count")
    last_accessed_at: datetime = Field(..., description="Updated access timestamp")
