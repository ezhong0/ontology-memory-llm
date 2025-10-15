"""API models for memory retrieval endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class RetrievalRequest(BaseModel):
    """Request model for memory retrieval.

    Attributes:
        query: Query text to search for
        strategy: Retrieval strategy (factual_entity_focused, procedural, exploratory, temporal)
        top_k: Number of top memories to return
        filters: Optional filters for candidate selection
    """

    query: str = Field(..., min_length=1, description="Query text")
    strategy: str = Field(
        default="exploratory",
        description="Retrieval strategy",
    )
    top_k: int = Field(default=20, ge=1, le=100, description="Number of results to return")
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional filters (entity_types, memory_types, min_confidence, etc.)",
    )

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Validate retrieval strategy."""
        valid_strategies = ["factual_entity_focused", "procedural", "exploratory", "temporal"]
        if v not in valid_strategies:
            raise ValueError(f"strategy must be one of {valid_strategies}")
        return v


class SignalBreakdownResponse(BaseModel):
    """Signal breakdown for explainability."""

    semantic_similarity: float
    entity_overlap: float
    recency_score: float
    importance_score: float
    reinforcement_score: float
    effective_confidence: float


class ScoredMemoryResponse(BaseModel):
    """Response model for a scored memory."""

    memory_id: int
    memory_type: str
    content: str
    relevance_score: float
    signal_breakdown: SignalBreakdownResponse
    created_at: str
    importance: float
    confidence: Optional[float] = None
    reinforcement_count: Optional[int] = None


class RetrievalMetadataResponse(BaseModel):
    """Metadata about retrieval operation."""

    candidates_generated: int
    candidates_scored: int
    top_score: float
    retrieval_time_ms: float


class QueryContextResponse(BaseModel):
    """Query context information."""

    query_text: str
    entity_ids: List[str]
    user_id: str
    strategy: str


class RetrievalResponse(BaseModel):
    """Response model for memory retrieval.

    Attributes:
        memories: List of scored memories, sorted by relevance
        query_context: Query context used for retrieval
        metadata: Metadata about the retrieval operation
    """

    memories: List[ScoredMemoryResponse]
    query_context: QueryContextResponse
    metadata: RetrievalMetadataResponse
