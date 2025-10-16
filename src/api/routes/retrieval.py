"""API routes for memory retrieval.

Exposes the memory retrieval pipeline via REST API.
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_id, get_db
from src.api.models.retrieval import RetrievalRequest, RetrievalResponse
from src.domain.exceptions import DomainError
from src.infrastructure.database.models import CanonicalEntity, SemanticMemory

router = APIRouter(prefix="/api/v1", tags=["retrieval"])
logger = structlog.get_logger(__name__)


# Response models for GET endpoints
class MemoryResponse(BaseModel):
    """Response model for memory item."""

    memory_id: int
    user_id: str
    subject_entity_id: str
    predicate: str
    predicate_type: str
    object_value: dict[str, Any]
    confidence: float
    status: str
    created_at: str


class EntityResponse(BaseModel):
    """Response model for entity item."""

    entity_id: str
    entity_type: str
    canonical_name: str
    properties: dict[str, Any]
    created_at: str


class MemoryListResponse(BaseModel):
    """Response model for memory list."""

    memories: list[MemoryResponse]
    total: int
    limit: int
    offset: int


class EntityListResponse(BaseModel):
    """Response model for entity list."""

    entities: list[EntityResponse]
    total: int
    limit: int
    offset: int


@router.post(
    "/retrieve",
    response_model=RetrievalResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve relevant memories",
    description="""
    Retrieve relevant memories for a query using multi-signal relevance scoring.

    **Pipeline**:
    1. Embed query
    2. Resolve entities
    3. Generate candidates (parallel retrieval from semantic, episodic, summary layers)
    4. Score with multi-signal (semantic similarity, entity overlap, recency, importance, reinforcement)
    5. Return top-k scored memories with provenance

    **Strategies**:
    - `factual_entity_focused`: Emphasizes entity overlap (good for specific entity queries)
    - `procedural`: Emphasizes reinforcement (good for "how to" queries)
    - `exploratory`: Balanced (good for open-ended queries)
    - `temporal`: Emphasizes recency (good for time-sensitive queries)

    **Performance**: P95 < 100ms for candidate scoring
    """,
)
async def retrieve_memories(
    request: RetrievalRequest,
    user_id: str = Depends(get_current_user_id),
    # Phase 1C: MemoryRetriever DI pending - requires get_memory_retriever() in dependencies.py
    # retriever: MemoryRetriever = Depends(get_memory_retriever),
) -> RetrievalResponse:
    """Retrieve relevant memories for a query.

    Args:
        request: Retrieval request with query and parameters
        user_id: Current user ID (from auth)

    Returns:
        RetrievalResponse with scored memories and metadata

    Raises:
        HTTPException: 400 for invalid input, 500 for server errors
    """
    logger.info(
        "retrieve_request",
        user_id=user_id,
        query=request.query,
        strategy=request.strategy,
        top_k=request.top_k,
    )

    try:
        # Phase 1C: MemoryRetriever integration pending - raises 501 until DI wired
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Retrieval endpoint implementation in progress. "
            "MemoryRetriever service needs dependency injection setup.",
        )

        # Future implementation:
        # result = await retriever.retrieve(
        #     query=request.query,
        #     user_id=user_id,
        #     strategy=request.strategy,
        #     top_k=request.top_k,
        #     filters=request.filters,
        # )
        #
        # # Convert to API response model
        # memories_response = [
        #     ScoredMemoryResponse(
        #         memory_id=m.candidate.memory_id,
        #         memory_type=m.candidate.memory_type,
        #         content=m.candidate.content,
        #         relevance_score=m.relevance_score,
        #         signal_breakdown=SignalBreakdownResponse(**m.signal_breakdown.to_dict()),
        #         created_at=m.candidate.created_at.isoformat(),
        #         importance=m.candidate.importance,
        #         confidence=m.candidate.confidence,
        #         reinforcement_count=m.candidate.reinforcement_count,
        #     )
        #     for m in result.memories
        # ]
        #
        # return RetrievalResponse(
        #     memories=memories_response,
        #     query_context=QueryContextResponse(
        #         query_text=result.query_context.query_text,
        #         entity_ids=result.query_context.entity_ids,
        #         user_id=result.query_context.user_id,
        #         strategy=result.query_context.strategy,
        #     ),
        #     metadata=RetrievalMetadataResponse(**result.metadata.to_dict()),
        # )

    except DomainError as e:
        logger.error(
            "retrieve_domain_error",
            user_id=user_id,
            query=request.query,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Retrieval error: {e!s}",
        ) from e

    except Exception as e:
        logger.error(
            "retrieve_unexpected_error",
            user_id=user_id,
            query=request.query,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during retrieval",
        ) from e


@router.get(
    "/memory",
    response_model=MemoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get memories for user",
    description="""
    Retrieve semantic memories for the current user.

    **Query Parameters**:
    - `limit`: Maximum number of memories to return (default: 50, max: 100)
    - `offset`: Number of memories to skip (default: 0)
    - `status`: Filter by memory status (active, inactive, conflicted)
    - `entity_id`: Filter by specific entity ID

    **Use Cases**:
    - Browsing user's memory catalog
    - Debugging memory extraction
    - Memory management interfaces
    """,
)
async def get_memories(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(50, ge=1, le=100, description="Maximum memories to return"),
    offset: int = Query(0, ge=0, description="Number of memories to skip"),
    status_filter: str | None = Query(None, description="Filter by status"),
    entity_id: str | None = Query(None, description="Filter by entity ID"),
) -> MemoryListResponse:
    """Get memories for user with optional filters.

    Args:
        db: Database session
        user_id: Current user ID
        limit: Maximum results
        offset: Results offset
        status_filter: Optional status filter
        entity_id: Optional entity filter

    Returns:
        MemoryListResponse with memories and pagination info
    """
    logger.info(
        "get_memories_request",
        user_id=user_id,
        limit=limit,
        offset=offset,
        status=status_filter,
        entity_id=entity_id,
    )

    try:
        # Build query
        query = select(SemanticMemory).where(SemanticMemory.user_id == user_id)

        if status_filter:
            query = query.where(SemanticMemory.status == status_filter)

        if entity_id:
            query = query.where(SemanticMemory.subject_entity_id == entity_id)

        # Get total count
        count_result = await db.execute(query)
        total = len(count_result.scalars().all())

        # Apply pagination and fetch
        query = query.order_by(SemanticMemory.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        memories = result.scalars().all()

        # Convert to response
        memory_responses = [
            MemoryResponse(
                memory_id=mem.memory_id,
                user_id=mem.user_id,
                subject_entity_id=mem.subject_entity_id,
                predicate=mem.predicate,
                predicate_type=mem.predicate_type,
                object_value=mem.object_value,
                confidence=mem.confidence,
                status=mem.status,
                created_at=mem.created_at.isoformat(),
            )
            for mem in memories
        ]

        logger.info(
            "get_memories_success",
            user_id=user_id,
            returned=len(memory_responses),
            total=total,
        )

        return MemoryListResponse(
            memories=memory_responses,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(
            "get_memories_error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memories: {e!s}",
        ) from e


@router.get(
    "/entities",
    response_model=EntityListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get entities for user",
    description="""
    Retrieve canonical entities for the current user.

    **Query Parameters**:
    - `limit`: Maximum number of entities to return (default: 50, max: 100)
    - `offset`: Number of entities to skip (default: 0)
    - `entity_type`: Filter by entity type (customer, order, etc.)

    **Use Cases**:
    - Browsing entity catalog
    - Debugging entity resolution
    - Entity management interfaces
    """,
)
async def get_entities(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(50, ge=1, le=100, description="Maximum entities to return"),
    offset: int = Query(0, ge=0, description="Number of entities to skip"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
) -> EntityListResponse:
    """Get entities for user with optional filters.

    Args:
        db: Database session
        user_id: Current user ID
        limit: Maximum results
        offset: Results offset
        entity_type: Optional type filter

    Returns:
        EntityListResponse with entities and pagination info
    """
    logger.info(
        "get_entities_request",
        user_id=user_id,
        limit=limit,
        offset=offset,
        entity_type=entity_type,
    )

    try:
        # Build query
        query = select(CanonicalEntity).where(CanonicalEntity.user_id == user_id)

        if entity_type:
            query = query.where(CanonicalEntity.entity_type == entity_type)

        # Get total count
        count_result = await db.execute(query)
        total = len(count_result.scalars().all())

        # Apply pagination and fetch
        query = query.order_by(CanonicalEntity.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        entities = result.scalars().all()

        # Convert to response
        entity_responses = [
            EntityResponse(
                entity_id=ent.entity_id,
                entity_type=ent.entity_type,
                canonical_name=ent.canonical_name,
                properties=ent.properties or {},
                created_at=ent.created_at.isoformat(),
            )
            for ent in entities
        ]

        logger.info(
            "get_entities_success",
            user_id=user_id,
            returned=len(entity_responses),
            total=total,
        )

        return EntityListResponse(
            entities=entity_responses,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(
            "get_entities_error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entities: {e!s}",
        ) from e
