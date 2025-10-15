"""Pydantic models for chat API.

Request/response models for FastAPI endpoints.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ResolvedEntityResponse(BaseModel):
    """Response model for resolved entity."""

    entity_id: str = Field(..., description="Canonical entity ID")
    canonical_name: str = Field(..., description="Entity display name")
    entity_type: str = Field(..., description="Entity type (customer, order, etc.)")
    mention_text: str = Field(..., description="Original text that was resolved")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Resolution confidence")
    method: str = Field(..., description="Resolution method (exact, alias, fuzzy, coreference)")

    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "customer_12345",
                "canonical_name": "Acme Corporation",
                "entity_type": "customer",
                "mention_text": "Acme Corp",
                "confidence": 0.85,
                "method": "fuzzy",
            }
        }


class ChatMessageRequest(BaseModel):
    """Request model for processing a chat message."""

    session_id: UUID = Field(..., description="Conversation session ID")
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    role: str = Field(default="user", description="Message role")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Optional metadata"
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is valid."""
        valid_roles = {"user", "assistant", "system"}
        if v not in valid_roles:
            raise ValueError(f"role must be one of {valid_roles}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "I need a quote for Acme Corporation",
                "role": "user",
                "metadata": {"source": "web_chat"},
            }
        }


class ChatMessageResponse(BaseModel):
    """Response model for processed chat message."""

    event_id: int = Field(..., description="Created chat event ID")
    session_id: UUID = Field(..., description="Conversation session ID")
    resolved_entities: list[ResolvedEntityResponse] = Field(
        ..., description="Entities resolved from the message"
    )
    mention_count: int = Field(..., description="Total entity mentions extracted")
    resolution_success_rate: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage of mentions successfully resolved"
    )
    created_at: datetime = Field(..., description="Message timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": 12345,
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "resolved_entities": [
                    {
                        "entity_id": "customer_12345",
                        "canonical_name": "Acme Corporation",
                        "entity_type": "customer",
                        "mention_text": "Acme",
                        "confidence": 0.9,
                        "method": "exact",
                    }
                ],
                "mention_count": 1,
                "resolution_success_rate": 100.0,
                "created_at": "2025-10-15T12:00:00Z",
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid input data",
                "detail": "content: field required",
            }
        }
