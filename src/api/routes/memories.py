"""Memory API routes.

Endpoints for retrieving and validating memories.
"""
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timezone

from src.api.models import SemanticMemoryResponse, ValidationRequest, ValidationResponse
from src.api.dependencies import get_semantic_memory_repository
from src.infrastructure.database.repositories import SemanticMemoryRepository
from src.config import heuristics

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/memories", tags=["Memories"])


@router.get(
    "/{memory_id}",
    response_model=SemanticMemoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get semantic memory by ID",
    description="""
    Retrieve a semantic memory by its ID.

    Used for:
    - Checking memory status (active, aging, superseded, invalidated)
    - Retrieving memory details for validation
    - Inspecting confidence and reinforcement history
    """,
)
async def get_memory(
    memory_id: int,
    semantic_repo: SemanticMemoryRepository = Depends(get_semantic_memory_repository),
) -> SemanticMemoryResponse:
    """Get semantic memory by ID.

    Args:
        memory_id: Memory ID
        semantic_repo: Semantic memory repository

    Returns:
        SemanticMemoryResponse with memory details

    Raises:
        HTTPException: If memory not found
    """
    try:
        logger.info("get_memory_request", memory_id=memory_id)

        # Retrieve memory
        memory = await semantic_repo.find_by_id(memory_id)

        if not memory:
            logger.warning("memory_not_found", memory_id=memory_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "MemoryNotFound",
                    "message": f"Memory with ID {memory_id} not found",
                },
            )

        # Convert to response model
        return SemanticMemoryResponse(
            memory_id=memory.memory_id,
            user_id=memory.user_id,
            content=memory.content,
            entities=memory.entities,
            confidence=memory.confidence,
            importance=memory.importance,
            status=memory.status,
            confirmation_count=memory.confirmation_count,
            last_accessed_at=memory.last_accessed_at,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_memory_error",
            memory_id=memory_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "Failed to retrieve memory",
            },
        ) from None


@router.post(
    "/{memory_id}/validate",
    response_model=ValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a memory",
    description="""
    Validate an aged or uncertain memory.

    When a memory is validated:
    - If confirmed: Status returns to 'active', confidence increases, reinforcement count increments
    - If corrected: Old memory marked superseded, new memory created with corrected value
    - last_validated_at timestamp updated

    Vision Principles:
    - Epistemic Humility (admit uncertainty, ask for confirmation)
    - Temporal Validity (validate aged memories)
    - Adaptive Learning (learn from validation)
    """,
)
async def validate_memory(
    memory_id: int,
    request: ValidationRequest,
    semantic_repo: SemanticMemoryRepository = Depends(get_semantic_memory_repository),
) -> ValidationResponse:
    """Validate a memory.

    Args:
        memory_id: Memory ID
        request: Validation request
        semantic_repo: Semantic memory repository

    Returns:
        ValidationResponse with updated memory details

    Raises:
        HTTPException: If memory not found or validation fails
    """
    try:
        logger.info(
            "validate_memory_request",
            memory_id=memory_id,
            user_id=request.user_id,
            confirmed=request.confirmed,
        )

        # Retrieve memory
        memory = await semantic_repo.find_by_id(memory_id)

        if not memory:
            logger.warning("memory_not_found_for_validation", memory_id=memory_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "MemoryNotFound",
                    "message": f"Memory with ID {memory_id} not found",
                },
            )

        # Validate ownership
        if memory.user_id != request.user_id:
            logger.warning(
                "validation_unauthorized",
                memory_id=memory_id,
                memory_user=memory.user_id,
                request_user=request.user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Unauthorized",
                    "message": "Cannot validate another user's memory",
                },
            )

        if request.confirmed:
            # Memory confirmed - increase confidence and confirmation count
            memory.status = "active"
            memory.confirmation_count += 1
            memory.last_accessed_at = datetime.now(timezone.utc)

            # Apply confirmation boost to confidence
            boost = heuristics.get_reinforcement_boost(memory.confirmation_count)
            memory.confidence = min(
                memory.confidence + boost,
                heuristics.MAX_CONFIDENCE,
            )

            # Update memory
            updated_memory = await semantic_repo.update(memory)

            logger.info(
                "memory_validated_confirmed",
                memory_id=memory_id,
                new_confidence=updated_memory.confidence,
                confirmation_count=updated_memory.confirmation_count,
            )

            return ValidationResponse(
                memory_id=updated_memory.memory_id,
                status=updated_memory.status,
                confidence=updated_memory.confidence,
                confirmation_count=updated_memory.confirmation_count,
                last_accessed_at=updated_memory.last_accessed_at,
            )

        else:
            # Memory invalidated - mark as superseded if correction provided
            if request.corrected_content:
                # TODO: Create new memory with corrected content (Phase 2.2 enhancement)
                # For now, just mark as superseded
                memory.status = "superseded"
                logger.info(
                    "memory_validated_corrected",
                    memory_id=memory_id,
                    old_content=memory.content,
                    new_content=request.corrected_content,
                )
            else:
                memory.status = "invalidated"
                logger.info("memory_validated_invalidated", memory_id=memory_id)

            memory.last_accessed_at = datetime.now(timezone.utc)

            # Update memory
            updated_memory = await semantic_repo.update(memory)

            return ValidationResponse(
                memory_id=updated_memory.memory_id,
                status=updated_memory.status,
                confidence=updated_memory.confidence,
                confirmation_count=updated_memory.confirmation_count,
                last_accessed_at=updated_memory.last_accessed_at,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "validate_memory_error",
            memory_id=memory_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "Failed to validate memory",
            },
        ) from None
