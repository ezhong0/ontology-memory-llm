"""API routes for procedural memory (pattern detection and retrieval).

Exposes pattern detection and learned heuristics via REST API.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import (
    get_current_user_id,
    get_procedural_repository,
    get_procedural_service,
)
from src.api.models.procedural import (
    AugmentQueryRequest,
    AugmentQueryResponse,
    DetectPatternsRequest,
    DetectPatternsResponse,
    GetPatternsResponse,
    PatternResponse,
)
from src.domain.exceptions import DomainError
from src.domain.services import ProceduralMemoryService
from src.infrastructure.database.repositories import ProceduralMemoryRepository

router = APIRouter(prefix="/api/v1/patterns", tags=["procedural"])
logger = structlog.get_logger(__name__)


@router.post(
    "/detect",
    response_model=DetectPatternsResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect patterns from episodic memories",
    description="""
    Analyze user's episodic memories to detect behavioral patterns.

    **Pattern Detection**:
    1. Fetch recent episodic memories (last 30 days)
    2. Extract features (intent, entities, topics)
    3. Find frequent co-occurrence patterns
    4. Store as procedural memories

    **Use Cases**:
    - Learn that when user asks about payments, they usually want invoice info
    - Learn that queries about specific customers often include order history
    - Learn user's common question-answer patterns

    **Phase 1**: Manual triggering via API
    **Phase 2+**: Automatic pattern detection on schedule

    **Performance**: P95 < 1s (analyzes up to 500 episodes)
    """,
)
async def detect_patterns(
    request: DetectPatternsRequest,
    user_id: str = Depends(get_current_user_id),
    procedural_service: ProceduralMemoryService = Depends(get_procedural_service),
) -> DetectPatternsResponse:
    """Detect patterns from user's episodic memories.

    Args:
        request: Pattern detection parameters
        user_id: Current user ID (from auth)

    Returns:
        DetectPatternsResponse with detected patterns

    Raises:
        HTTPException: 400 for invalid input, 500 for server errors
    """
    logger.info(
        "detect_patterns_request",
        user_id=user_id,
        min_occurrences=request.min_occurrences,
        max_patterns=request.max_patterns,
    )

    try:
        patterns = await procedural_service.detect_patterns(
            user_id=user_id,
            lookback_days=30,
            min_support=request.min_occurrences,
        )

        # Convert to API response (limit to max_patterns)
        pattern_responses = [
            PatternResponse(
                memory_id=p.memory_id or 0,
                trigger_pattern=p.trigger_pattern,
                action_heuristic=p.action_heuristic,
                confidence=p.confidence,
                observed_count=p.observed_count,
                created_at=p.created_at.isoformat(),
            )
            for p in patterns[:request.max_patterns]
        ]

        return DetectPatternsResponse(
            patterns=pattern_responses,
            total_count=len(patterns),
            user_id=user_id,
        )

    except DomainError as e:
        logger.error(
            "detect_patterns_domain_error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pattern detection error: {e!s}",
        ) from e

    except Exception as e:
        logger.error(
            "detect_patterns_unexpected_error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during pattern detection",
        ) from e


@router.get(
    "/",
    response_model=GetPatternsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user's procedural memories",
    description="""
    Retrieve user's learned patterns (procedural memories).

    **Use Cases**:
    - List all patterns learned for a user
    - Filter by confidence threshold
    - Display learned behaviors in UI

    **Example**:
    ```
    GET /api/v1/patterns?min_confidence=0.7&limit=20
    ```

    Returns list of patterns ordered by confidence (highest first).
    """,
)
async def get_patterns(
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence"),
    limit: int = Query(20, ge=1, le=100, description="Maximum patterns to return"),
    user_id: str = Depends(get_current_user_id),
    procedural_repo: ProceduralMemoryRepository = Depends(get_procedural_repository),
) -> GetPatternsResponse:
    """Get user's procedural memories (learned patterns).

    Args:
        min_confidence: Minimum confidence threshold
        limit: Maximum patterns to return
        user_id: Current user ID (from auth)

    Returns:
        GetPatternsResponse with user's patterns

    Raises:
        HTTPException: 400 for invalid input, 500 for server errors
    """
    logger.info(
        "get_patterns_request",
        user_id=user_id,
        min_confidence=min_confidence,
        limit=limit,
    )

    try:
        patterns = await procedural_repo.find_by_user(
            user_id=user_id,
            min_confidence=min_confidence,
            limit=limit,
        )

        # Convert to API response
        pattern_responses = [
            PatternResponse(
                memory_id=p.memory_id or 0,
                trigger_pattern=p.trigger_pattern,
                action_heuristic=p.action_heuristic,
                confidence=p.confidence,
                observed_count=p.observed_count,
                created_at=p.created_at.isoformat(),
            )
            for p in patterns
        ]

        return GetPatternsResponse(
            patterns=pattern_responses,
            total_count=len(pattern_responses),
            user_id=user_id,
        )

    except DomainError as e:
        logger.error(
            "get_patterns_domain_error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error getting patterns: {e!s}",
        ) from e

    except Exception as e:
        logger.error(
            "get_patterns_unexpected_error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while getting patterns",
        ) from e


@router.post(
    "/augment",
    response_model=AugmentQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Augment query with procedural patterns",
    description="""
    Augment a query using learned procedural patterns.

    **Query Augmentation**:
    1. Generate query embedding
    2. Find similar procedural patterns
    3. Extract action heuristics from patterns
    4. Augment query with additional context

    **Use Case**:
    User asks: "What's the status of Acme's order?"
    Learned pattern: "When asking about orders, also retrieve payment info"
    Augmented query: "What's the status of Acme's order? Also show payment info."

    **Performance**: P95 < 200ms (includes embedding + retrieval)
    """,
)
async def augment_query(
    request: AugmentQueryRequest,
    user_id: str = Depends(get_current_user_id),
    procedural_service: ProceduralMemoryService = Depends(get_procedural_service),
) -> AugmentQueryResponse:
    """Augment query with procedural patterns.

    Args:
        request: Query augmentation request
        user_id: Current user ID (from auth)

    Returns:
        AugmentQueryResponse with augmented query

    Raises:
        HTTPException: 400 for invalid input, 500 for server errors
    """
    logger.info(
        "augment_query_request",
        user_id=user_id,
        query_length=len(request.query),
        max_patterns=request.max_patterns,
    )

    try:
        from src.infrastructure.di.container import container

        # Get embedding service from container
        embedding_service = container.embedding_service()

        # Generate query embedding
        query_embedding = await embedding_service.generate_embedding(request.query)

        # Find relevant patterns
        patterns = await procedural_service.augment_query(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=request.max_patterns,
        )

        if not patterns:
            # No patterns found, return original query
            return AugmentQueryResponse(
                original_query=request.query,
                augmented_query=request.query,
                patterns_applied=[],
                pattern_count=0,
            )

        # Build augmented query
        augmentations = []
        pattern_ids = []

        for pattern in patterns:
            augmentations.append(pattern.action_heuristic)
            pattern_ids.append(str(pattern.memory_id))

        augmented_query = f"{request.query} [{'; '.join(augmentations)}]"

        return AugmentQueryResponse(
            original_query=request.query,
            augmented_query=augmented_query,
            patterns_applied=pattern_ids,
            pattern_count=len(patterns),
        )

    except DomainError as e:
        logger.error(
            "augment_query_domain_error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query augmentation error: {e!s}",
        ) from e

    except Exception as e:
        logger.error(
            "augment_query_unexpected_error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during query augmentation",
        ) from e
