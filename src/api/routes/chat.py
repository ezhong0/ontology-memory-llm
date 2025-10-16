"""Chat API routes.

Endpoints for processing chat messages.
"""
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_current_user_id, get_process_chat_message_use_case
from src.api.models import (
    ChatMessageRequest,
    ChatMessageResponse,
    DomainFactResponse,
    EnhancedChatResponse,
    ErrorResponse,
    ResolvedEntityResponse,
    RetrievedMemoryResponse,
)
from src.application.dtos import ProcessChatMessageInput
from src.application.use_cases import ProcessChatMessageUseCase
from src.domain.exceptions import AmbiguousEntityError, DomainError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Process a chat message (simplified E2E endpoint)",
    description="""
    Simplified chat endpoint for E2E testing.

    Accepts a simple {user_id, message} payload and returns the full context
    including response, augmentation data, and created memories.
    """,
)
async def process_chat_simplified(
    request: dict[str, Any],
    use_case: ProcessChatMessageUseCase = Depends(get_process_chat_message_use_case),
) -> dict[str, Any]:
    """Process a chat message with simplified request/response format.

    This endpoint is designed for E2E tests and provides a simple interface.

    Args:
        request: Dict with user_id and message
        use_case: Chat processing use case

    Returns:
        Dict with response, augmentation, and memories_created
    """
    try:
        import uuid

        user_id = request.get("user_id", "default_user")
        message = request.get("message", "")
        session_id = request.get("session_id", str(uuid.uuid4()))

        logger.info(
            "simplified_chat_request",
            user_id=user_id,
            message_length=len(message),
            session_id=session_id,
        )

        # Task 1.2.1: Handle disambiguation selection from prior ambiguity
        disambiguation_selection = request.get("disambiguation_selection")
        if disambiguation_selection:
            # User selected from ambiguous candidates
            # TODO: Create user-specific alias for learning
            # This requires accessing EntityResolutionService with proper session
            # For now, log the selection and proceed
            logger.info(
                "disambiguation_selection_received",
                entity_id=disambiguation_selection["selected_entity_id"],
                mention=disambiguation_selection["original_mention"],
                user_id=user_id,
            )

        # Create input DTO
        input_dto = ProcessChatMessageInput(
            user_id=user_id,
            session_id=uuid.UUID(session_id) if isinstance(session_id, str) else session_id,
            content=message,
            role="user",
            metadata={},
        )

        # Execute use case
        output = await use_case.execute(input_dto)

        # Build simplified response matching E2E test expectations
        response_dict = {
            "response": output.reply,
            "augmentation": {
                "domain_facts": [
                    {
                        "fact_type": fact.fact_type,
                        "entity_id": fact.entity_id,
                        "table": fact.source_table,
                        "content": fact.content,
                        "metadata": fact.metadata,
                        # Flatten commonly queried metadata fields for test compatibility
                        **({"invoice_id": fact.metadata["invoice_id"]} if "invoice_id" in fact.metadata else {}),
                    }
                    for fact in output.domain_facts
                ],
                "memories_retrieved": [
                    {
                        "memory_id": mem.memory_id,
                        "memory_type": mem.memory_type,
                        "content": mem.content,
                        "relevance_score": mem.relevance_score,
                        "confidence": mem.confidence,
                        # Include predicate/object_value for semantic memories
                        **({"predicate": mem.predicate} if mem.predicate else {}),
                        **({"object_value": mem.object_value} if mem.object_value else {}),
                    }
                    for mem in output.retrieved_memories
                ],
                "entities_resolved": [
                    {
                        "entity_id": entity.entity_id,
                        "canonical_name": entity.canonical_name,
                        "entity_type": entity.entity_type,
                        "confidence": entity.confidence,
                        "mention_text": entity.mention_text,
                        "method": entity.method,
                    }
                    for entity in output.resolved_entities
                ]
            },
            "memories_created": [
                {
                    "memory_type": "episodic",
                    "summary": f"User said: {message[:100]}",
                    "event_id": output.event_id,
                }
            ],
        }

        # Add provenance/explainability data if memories were retrieved
        # (Vision Principle: Explainability - transparency as trust)
        if output.retrieved_memories:
            response_dict["provenance"] = {
                "memory_ids": [mem.memory_id for mem in output.retrieved_memories],
                "similarity_scores": [mem.relevance_score for mem in output.retrieved_memories],
                "memory_count": len(output.retrieved_memories),
                "source_types": [mem.memory_type for mem in output.retrieved_memories],
            }

        # Add conflicts if any detected (Vision Principle: Epistemic Humility)
        # Phase 2.1: Expose conflicts for transparency
        if output.conflicts_detected:
            response_dict["conflicts_detected"] = [
                {
                    "conflict_type": conflict.conflict_type,
                    "subject": conflict.subject_entity_id,
                    "predicate": conflict.predicate,
                    "existing_value": conflict.existing_value,
                    "new_value": conflict.new_value,
                    "existing_confidence": conflict.existing_confidence,
                    "new_confidence": conflict.new_confidence,
                    "resolution_strategy": conflict.resolution_strategy,
                }
                for conflict in output.conflicts_detected
            ]

        return response_dict

    except AmbiguousEntityError as e:
        # Task 1.2.1: Return disambiguation as structured response (not error)
        logger.warning(
            "ambiguous_entity_requires_disambiguation",
            mention=e.mention_text,
            candidates_count=len(e.candidates),
        )

        # Use full entity details from exception (includes canonical_name, properties, etc)
        # The exception now carries all entity details needed for disambiguation UI
        candidates_list = e.entities if e.entities else [
            {
                "entity_id": entity_id,
                "similarity_score": similarity_score,
            }
            for entity_id, similarity_score in e.candidates
        ]

        # Return 200 with disambiguation_required flag
        return {
            "disambiguation_required": True,
            "original_mention": e.mention_text,
            "candidates": candidates_list,
            "message": f"Multiple entities match '{e.mention_text}'. Please select one.",
        }

    except Exception as e:
        logger.error(
            "simplified_chat_error",
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "InternalServerError", "message": str(e)},
        ) from None


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
            created_at=datetime.now(UTC),
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
        ) from None

    except DomainError as e:
        logger.error(
            "domain_error_in_request",
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": type(e).__name__, "message": str(e)},
        ) from None

    except Exception as e:
        logger.error(
            "unexpected_error_in_request",
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
        ) from None


@router.post(
    "/message/enhanced",
    response_model=EnhancedChatResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Process a chat message with memory retrieval (Enhanced)",
    description="""
    Process a chat message with full memory retrieval pipeline.

    This enhanced endpoint demonstrates the complete system:
    1. Stores the chat message
    2. Extracts and resolves entities
    3. Extracts semantic facts
    4. Retrieves relevant memories using multi-signal scoring
    5. Returns resolved entities + retrieved memories with provenance

    This shows the "experienced colleague" vision:
    - Never forgets what matters (perfect recall via retrieval)
    - Knows relationships (entity resolution + ontology)
    - Shows confidence (epistemic humility)
    - Explains reasoning (provenance tracking)
    """,
)
async def process_message_enhanced(
    request: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id),
    use_case: ProcessChatMessageUseCase = Depends(get_process_chat_message_use_case),
) -> EnhancedChatResponse:
    """Process a chat message with memory retrieval.

    Args:
        request: Chat message request
        user_id: Current user ID (from auth)

    Returns:
        EnhancedChatResponse with entities, memories, and context

    Raises:
        HTTPException: On validation or processing errors
    """
    try:
        logger.info(
            "api_process_message_enhanced_request",
            user_id=user_id,
            session_id=str(request.session_id),
            content_length=len(request.content),
        )

        # Step 1: Process message (entity resolution + semantic extraction)
        input_dto = ProcessChatMessageInput(
            user_id=user_id,
            session_id=request.session_id,
            content=request.content,
            role=request.role,
            metadata=request.metadata,
        )

        output = await use_case.execute(input_dto)

        # Step 2: Build response (Phase 1C now provides domain_facts and reply)
        retrieved_memories: list[RetrievedMemoryResponse] = []
        context_parts: list[str] = []

        # Convert semantic memories to retrieved memory format for backward compatibility
        if output.semantic_memories:
            for sem_mem in output.semantic_memories[:5]:  # Limit to top 5
                retrieved_memories.append(
                    RetrievedMemoryResponse(
                        memory_id=sem_mem.memory_id,
                        memory_type="semantic",
                        content=f"{sem_mem.predicate}: {sem_mem.object_value}",
                        relevance_score=0.85,  # Phase 1C: Placeholder, Phase 1D adds scoring
                        confidence=sem_mem.confidence,
                    )
                )

        # Convert domain facts to response format
        domain_fact_responses = [
            DomainFactResponse(
                fact_type=fact.fact_type,
                entity_id=fact.entity_id,
                content=fact.content,
                metadata=fact.metadata,
                source_table=fact.source_table,
                source_rows=fact.source_rows,
            )
            for fact in output.domain_facts
        ]

        # Build context summary
        context_parts = []
        if output.resolved_entities:
            context_parts.append(f"{len(output.resolved_entities)} entities resolved")
        if output.domain_facts:
            context_parts.append(f"{len(output.domain_facts)} domain facts retrieved")
        if retrieved_memories:
            context_parts.append(f"{len(retrieved_memories)} memories retrieved")

        context_summary = " | ".join(context_parts) if context_parts else "No context retrieved"

        logger.info(
            "enhanced_message_processed",
            event_id=output.event_id,
            entities=len(output.resolved_entities),
            domain_facts=len(output.domain_facts),
            memories=len(retrieved_memories),
            reply_length=len(output.reply),
        )

        # Convert to response model
        return EnhancedChatResponse(
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
            retrieved_memories=retrieved_memories,
            domain_facts=domain_fact_responses,
            reply=output.reply,
            context_summary=context_summary,
            mention_count=output.mention_count,
            memory_count=len(retrieved_memories),
            created_at=datetime.now(UTC),
        )

    except AmbiguousEntityError as e:
        logger.warning(
            "ambiguous_entity_in_enhanced_request",
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
        ) from None

    except DomainError as e:
        logger.error(
            "domain_error_in_enhanced_request",
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": type(e).__name__, "message": str(e)},
        ) from None

    except Exception as e:
        logger.error(
            "unexpected_error_in_enhanced_request",
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
        ) from None
