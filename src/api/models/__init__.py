"""API models.

Pydantic models for request/response validation.
"""
from src.api.models.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    EnhancedChatResponse,
    ErrorResponse,
    ResolvedEntityResponse,
    RetrievedMemoryResponse,
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
    "EnhancedChatResponse",
    "ResolvedEntityResponse",
    "RetrievedMemoryResponse",
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
