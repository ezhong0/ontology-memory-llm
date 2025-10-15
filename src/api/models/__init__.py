"""API models.

Pydantic models for request/response validation.
"""
from src.api.models.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ErrorResponse,
    ResolvedEntityResponse,
)
from src.api.models.consolidation import (
    ConsolidationRequest,
    ConsolidationResponse,
    GetSummariesRequest,
    GetSummariesResponse,
    KeyFactResponse,
    SummaryMetadataResponse,
    TriggerStatusResponse,
)
from src.api.models.retrieval import RetrievalRequest, RetrievalResponse

__all__ = [
    # Chat
    "ChatMessageRequest",
    "ChatMessageResponse",
    "ResolvedEntityResponse",
    "ErrorResponse",
    # Retrieval
    "RetrievalRequest",
    "RetrievalResponse",
    # Consolidation
    "ConsolidationRequest",
    "ConsolidationResponse",
    "GetSummariesRequest",
    "GetSummariesResponse",
    "KeyFactResponse",
    "SummaryMetadataResponse",
    "TriggerStatusResponse",
]
