"""API routes for memory consolidation.

Exposes consolidation and summary retrieval via REST API.
"""


import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from src.api.dependencies import (
    get_consolidation_service,
    get_consolidation_trigger_service,
    get_current_user_id,
    get_summary_repository,
)
from src.api.models.consolidation import (
    ConsolidationRequest,
    ConsolidationResponse,
    GetSummariesResponse,
    TriggerStatusResponse,
)
from src.domain.exceptions import DomainError
from src.domain.services import ConsolidationService, ConsolidationTriggerService
from src.infrastructure.database.repositories import SummaryRepository

router = APIRouter(prefix="/api/v1", tags=["consolidation"])
logger = structlog.get_logger(__name__)


@router.post(
    "/consolidate",
    response_model=ConsolidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Consolidate memories",
    description="""
    Consolidate episodic and semantic memories into a summary for a given scope.

    **Consolidation Process**:
    1. Fetch episodic and semantic memories for scope
    2. Use LLM to synthesize coherent summary
    3. Extract key facts with confidence tracking
    4. Identify interaction patterns
    5. Boost confidence of validated facts
    6. Store summary with embedding

    **Scope Types**:
    - `entity`: Consolidate all memories about a specific entity (e.g., customer, product)
    - `topic`: Consolidate memories matching a predicate pattern
    - `session_window`: Consolidate memories from recent N sessions

    **Phase 1**: Manual triggering via API
    **Phase 2+**: Automatic background consolidation when thresholds met

    **Performance**: P95 < 2s (includes LLM synthesis)
    """,
)
async def consolidate_memories(
    request: ConsolidationRequest,
    user_id: str = Depends(get_current_user_id),
    consolidation_service: ConsolidationService = Depends(get_consolidation_service),
) -> ConsolidationResponse:
    """Consolidate memories for a scope.

    Args:
        request: Consolidation request with scope and options
        user_id: Current user ID (from auth)

    Returns:
        ConsolidationResponse with summary and key facts

    Raises:
        HTTPException: 400 for invalid input, 500 for server errors
    """
    logger.info(
        "consolidate_request",
        user_id=user_id,
        scope_type=request.scope_type,
        scope_identifier=request.scope_identifier,
        force=request.force,
    )

    try:
        from src.api.models.consolidation import KeyFactResponse
        from src.domain.value_objects.consolidation import ConsolidationScope

        scope = ConsolidationScope(
            type=request.scope_type,
            identifier=request.scope_identifier,
        )

        summary = await consolidation_service.consolidate(
            user_id=user_id,
            scope=scope,
            force=request.force,
        )

        # Convert to API response
        key_facts_response = {
            name: KeyFactResponse(
                value=fact["value"],
                confidence=fact["confidence"],
                reinforced=fact["reinforced"],
                source_memory_ids=fact["source_memory_ids"],
            )
            for name, fact in summary.key_facts.items()
        }

        return ConsolidationResponse(
            summary_id=summary.summary_id or 0,
            scope_type=summary.scope_type,
            scope_identifier=summary.scope_identifier or "",
            summary_text=summary.summary_text,
            key_facts=key_facts_response,
            interaction_patterns=summary.source_data.get("interaction_patterns", []),
            needs_validation=summary.source_data.get("needs_validation", []),
            confidence=summary.confidence,
            created_at=summary.created_at.isoformat(),
        )

    except DomainError as e:
        logger.error(
            "consolidate_domain_error",
            user_id=user_id,
            scope_type=request.scope_type,
            scope_identifier=request.scope_identifier,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Consolidation error: {e!s}",
        ) from e

    except Exception as e:
        logger.error(
            "consolidate_unexpected_error",
            user_id=user_id,
            scope_type=request.scope_type,
            scope_identifier=request.scope_identifier,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during consolidation",
        ) from e


@router.get(
    "/summaries/{scope_type}/{scope_identifier}",
    response_model=GetSummariesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get summaries for scope",
    description="""
    Retrieve memory summaries for a specific scope.

    **Use Cases**:
    - Get entity profile summary (all memories about a customer)
    - Get topic summary (all memories about a specific predicate pattern)
    - Get session window summary (summary of recent sessions)

    **Example**:
    ```
    GET /api/v1/summaries/entity/customer:acme_123?limit=10&min_confidence=0.5
    ```

    Returns list of summaries ordered by creation date (newest first).
    """,
)
async def get_summaries(
    scope_type: str = Path(..., description="Scope type (entity, topic, session_window)"),
    scope_identifier: str = Path(..., description="Scope identifier"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of summaries"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence"),
    user_id: str = Depends(get_current_user_id),
    summary_repo: SummaryRepository = Depends(get_summary_repository),
) -> GetSummariesResponse:
    """Get summaries for a scope.

    Args:
        scope_type: Scope type (entity, topic, session_window)
        scope_identifier: Scope identifier
        limit: Maximum number of summaries
        min_confidence: Minimum confidence threshold
        user_id: Current user ID (from auth)

    Returns:
        GetSummariesResponse with list of summaries

    Raises:
        HTTPException: 400 for invalid input, 404 if not found, 500 for server errors
    """
    logger.info(
        "get_summaries_request",
        user_id=user_id,
        scope_type=scope_type,
        scope_identifier=scope_identifier,
        limit=limit,
        min_confidence=min_confidence,
    )

    try:
        from src.api.models.consolidation import SummaryMetadataResponse

        # Get summaries from repository
        summaries = await summary_repo.find_by_scope_with_filters(
            user_id=user_id,
            scope_type=scope_type,
            scope_identifier=scope_identifier,
            limit=limit,
            min_confidence=min_confidence,
        )

        if not summaries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No summaries found for {scope_type}:{scope_identifier}",
            )

        # Convert to API response
        summary_responses = [
            SummaryMetadataResponse(
                summary_id=s.summary_id or 0,
                scope_type=s.scope_type,
                scope_identifier=s.scope_identifier or "",
                summary_text=s.summary_text[:200] + "..." if len(s.summary_text) > 200 else s.summary_text,
                confidence=s.confidence,
                key_fact_count=len(s.key_facts),
                created_at=s.created_at.isoformat(),
            )
            for s in summaries
        ]

        return GetSummariesResponse(
            summaries=summary_responses,
            total_count=len(summary_responses),
        )

    except HTTPException:
        raise

    except DomainError as e:
        logger.error(
            "get_summaries_domain_error",
            user_id=user_id,
            scope_type=scope_type,
            scope_identifier=scope_identifier,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error getting summaries: {e!s}",
        ) from e

    except Exception as e:
        logger.error(
            "get_summaries_unexpected_error",
            user_id=user_id,
            scope_type=scope_type,
            scope_identifier=scope_identifier,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while getting summaries",
        ) from e


@router.get(
    "/consolidate/status",
    response_model=TriggerStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check consolidation status",
    description="""
    Check if consolidation is recommended for a user.

    Scans user's interaction history to find scopes meeting consolidation thresholds.

    **Thresholds**:
    - Entity scope: 10+ episodic memories about entity
    - Session window: 3+ completed sessions
    - Topic scope: Pattern-specific (Phase 2+)

    **Use Case**: Background jobs can poll this endpoint to trigger consolidation
    """,
)
async def get_consolidation_status(
    user_id: str = Depends(get_current_user_id),
    trigger_service: ConsolidationTriggerService = Depends(get_consolidation_trigger_service),
) -> TriggerStatusResponse:
    """Check consolidation status for user.

    Args:
        user_id: Current user ID (from auth)

    Returns:
        TriggerStatusResponse with pending scopes

    Raises:
        HTTPException: 500 for server errors
    """
    logger.info("consolidation_status_request", user_id=user_id)

    try:
        from datetime import UTC, datetime

        pending_scopes = await trigger_service.get_pending_consolidations(user_id)

        pending_scope_dicts = [
            {
                "scope_type": scope.type,
                "scope_identifier": scope.identifier,
                "reason": f"Threshold met for {scope.type} consolidation",
            }
            for scope in pending_scopes
        ]

        return TriggerStatusResponse(
            user_id=user_id,
            should_consolidate=len(pending_scopes) > 0,
            pending_scopes=pending_scope_dicts,
            checked_at=datetime.now(UTC).isoformat(),
        )

    except DomainError as e:
        logger.error(
            "consolidation_status_domain_error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error checking consolidation status: {e!s}",
        ) from e

    except Exception as e:
        logger.error(
            "consolidation_status_unexpected_error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while checking consolidation status",
        ) from e
