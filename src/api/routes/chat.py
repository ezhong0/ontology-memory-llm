"""Chat API routes.

Endpoints for processing chat messages.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from src.api.dependencies import get_current_user_id, get_process_chat_message_use_case
from src.api.models import (
    ChatMessageRequest,
    ChatMessageResponse,
    ErrorResponse,
    ResolvedEntityResponse,
)
from src.application.dtos import ProcessChatMessageInput
from src.application.use_cases import ProcessChatMessageUseCase
from src.domain.exceptions import AmbiguousEntityError, DomainError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "/message",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Process a chat message",
    description="""
    Process a chat message with entity resolution.

    This endpoint:
    1. Stores the chat message
    2. Extracts entity mentions
    3. Resolves entities using a 5-stage hybrid algorithm
    4. Returns resolved entities with confidence scores

    The entity resolution algorithm uses:
    - Stage 1: Exact match (70% of cases)
    - Stage 2: User aliases (15% of cases)
    - Stage 3: Fuzzy matching via pg_trgm (10% of cases)
    - Stage 4: LLM coreference resolution (5% of cases)
    - Stage 5: Domain database lookup (lazy entity creation)
    """,
)
async def process_message(
    request: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id),
    use_case: ProcessChatMessageUseCase = Depends(get_process_chat_message_use_case),
) -> ChatMessageResponse:
    """Process a chat message and resolve entities.

    Args:
        request: Chat message request
        user_id: Current user ID (from auth)

    Returns:
        ChatMessageResponse with resolved entities

    Raises:
        HTTPException: On validation or processing errors
    """
    try:
        logger.info(
            "api_process_message_request",
            user_id=user_id,
            session_id=str(request.session_id),
            content_length=len(request.content),
        )

        # Create input DTO
        input_dto = ProcessChatMessageInput(
            user_id=user_id,
            session_id=request.session_id,
            content=request.content,
            role=request.role,
            metadata=request.metadata,
        )

        # Execute use case
        output = await use_case.execute(input_dto)

        # Convert to response model
        return ChatMessageResponse(
            event_id=output.event_id,
            session_id=output.session_id,
            resolved_entities=[
                ResolvedEntityResponse(
                    entity_id=entity.entity_id,
                    canonical_name=entity.canonical_name,
                    entity_type=entity.entity_type,
                    mention_text=entity.mention_text,
                    confidence=entity.confidence,
                    method=entity.method,
                )
                for entity in output.resolved_entities
            ],
            mention_count=output.mention_count,
            resolution_success_rate=output.resolution_success_rate,
            created_at=datetime.now(timezone.utc),
        )

    except AmbiguousEntityError as e:
        logger.warning(
            "ambiguous_entity_in_request",
            mention=e.mention_text,
            candidates_count=len(e.candidates),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "AmbiguousEntity",
                "message": f"Multiple entities match '{e.mention_text}'",
                "candidates": e.candidates,
            },
        )

    except DomainError as e:
        logger.error(
            "domain_error_in_request",
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": type(e).__name__, "message": str(e)},
        )

    except Exception as e:
        logger.error(
            "unexpected_error_in_request",
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
        )
