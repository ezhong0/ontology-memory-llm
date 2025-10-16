"""Pydantic models for chat API.

Request/response models for FastAPI endpoints.
"""
from datetime import datetime
from typing import Any
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
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata"
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is valid."""
        valid_roles = {"user", "assistant", "system"}
        if v not in valid_roles:
            msg = f"role must be one of {valid_roles}"
            raise ValueError(msg)
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


class DomainFactResponse(BaseModel):
    """Response model for domain fact."""

    fact_type: str = Field(..., description="Type of fact (invoice_status, order_chain, sla_risk)")
    entity_id: str = Field(..., description="Entity this fact relates to")
    content: str = Field(..., description="Human-readable fact content")
    metadata: dict[str, Any] = Field(..., description="Structured metadata")
    source_table: str = Field(..., description="Source table(s) in domain schema")
    source_rows: list[str] = Field(..., description="Source row UUIDs")

    class Config:
        json_schema_extra = {
            "example": {
                "fact_type": "invoice_status",
                "entity_id": "customer:uuid-123",
                "content": "Invoice INV-1009: $1,200.00 due 2025-11-01 (status: open)",
                "metadata": {
                    "invoice_number": "INV-1009",
                    "amount": 1200.0,
                    "balance": 1200.0,
                    "due_date": "2025-11-01",
                },
                "source_table": "domain.invoices",
                "source_rows": ["uuid-456"],
            }
        }


class RetrievedMemoryResponse(BaseModel):
    """Response model for retrieved memory."""

    memory_id: int = Field(..., description="Memory ID")
    memory_type: str = Field(..., description="Memory type (episodic, semantic, summary)")
    content: str = Field(..., description="Memory content")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Memory confidence")

    class Config:
        json_schema_extra = {
            "example": {
                "memory_id": 42,
                "memory_type": "semantic",
                "content": "Acme Corporation prefers NET30 payment terms",
                "relevance_score": 0.87,
                "confidence": 0.92,
            }
        }


class EnhancedChatResponse(BaseModel):
    """Enhanced response model with memory retrieval, domain facts, and AI reply (Phase 1C)."""

    event_id: int = Field(..., description="Created chat event ID")
    session_id: UUID = Field(..., description="Conversation session ID")
    resolved_entities: list[ResolvedEntityResponse] = Field(
        default_factory=list, description="Entities resolved from the message"
    )
    retrieved_memories: list[RetrievedMemoryResponse] = Field(
        default_factory=list, description="Relevant memories retrieved"
    )
    domain_facts: list[DomainFactResponse] = Field(
        default_factory=list, description="Domain facts retrieved from database (Phase 1C)"
    )
    reply: str = Field(..., description="Natural language reply generated by LLM (Phase 1C)")
    context_summary: str = Field(default="", description="Summary of retrieved context")
    mention_count: int = Field(..., description="Total entity mentions extracted")
    memory_count: int = Field(..., description="Total memories retrieved")
    created_at: datetime = Field(..., description="Message timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": 12345,
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "resolved_entities": [
                    {
                        "entity_id": "customer:acme123",
                        "canonical_name": "Acme Corporation",
                        "entity_type": "customer",
                        "mention_text": "Acme",
                        "confidence": 0.95,
                        "method": "exact",
                    }
                ],
                "retrieved_memories": [
                    {
                        "memory_id": 42,
                        "memory_type": "semantic",
                        "content": "Acme Corporation prefers NET30 payment terms",
                        "relevance_score": 0.87,
                        "confidence": 0.92,
                    }
                ],
                "domain_facts": [
                    {
                        "fact_type": "invoice_status",
                        "entity_id": "customer:acme123",
                        "content": "Invoice INV-1009: $1,200.00 due 2025-11-01 (status: open)",
                        "metadata": {"invoice_number": "INV-1009", "amount": 1200.0},
                        "source_table": "domain.invoices",
                        "source_rows": ["uuid-456"],
                    }
                ],
                "reply": "According to our records, Acme Corporation has one open invoice (INV-1009) for $1,200 due November 1st. Based on their payment history, they typically pay within NET30 terms.",
                "context_summary": "Retrieved 3 memories and 2 domain facts about Acme Corporation.",
                "mention_count": 1,
                "memory_count": 3,
                "created_at": "2025-10-15T12:00:00Z",
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid input data",
                "detail": "content: field required",
            }
        }
