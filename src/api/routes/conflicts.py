"""Conflicts API routes.

Transparency endpoint for viewing detected conflicts.
Phase 2.1: Epistemic Humility - expose conflicts explicitly.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_id, get_db

router = APIRouter(prefix="/api/v1/conflicts", tags=["conflicts"])


@router.get("/")
async def get_conflicts(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
) -> dict:
    """Get recent conflicts detected for a user.

    Returns conflicts from semantic memories that have been:
    - Superseded (status = 'superseded')
    - Marked as conflicted (status = 'conflicted')

    Args:
        user_id: User ID (from auth header)
        db: Database session
        limit: Maximum number of conflicts to return (default 50, max 100)

    Returns:
        Dict with list of conflicts
    """
    from sqlalchemy import select, desc
    from src.infrastructure.database.models import SemanticMemoryModel

    # Query for memories that were superseded or conflicted
    query = (
        select(SemanticMemoryModel)
        .where(SemanticMemoryModel.user_id == user_id)
        .where(
            SemanticMemoryModel.status.in_(["superseded", "conflicted", "invalidated"])
        )
        .order_by(desc(SemanticMemoryModel.updated_at))
        .limit(limit)
    )

    result = await db.execute(query)
    conflicted_memories = result.scalars().all()

    # Build conflict responses
    conflicts = []
    for memory in conflicted_memories:
        # Determine conflict type from status
        conflict_type = "memory_vs_memory"  # Default
        if memory.status == "invalidated":
            conflict_type = "memory_vs_db"

        # Build conflict data
        conflict_data = {
            "memory_id": memory.memory_id,
            "subject_entity_id": memory.subject_entity_id,
            "predicate": memory.predicate,
            "object_value": memory.object_value,
            "confidence": float(memory.confidence),
            "status": memory.status,
            "superseded_by": memory.superseded_by_memory_id,
        }

        # Determine resolution strategy based on status
        resolution_strategy = "trust_recent"  # Default for superseded
        if memory.status == "invalidated":
            resolution_strategy = "trust_db"
        elif memory.status == "conflicted":
            resolution_strategy = "ask_user"

        conflicts.append({
            "conflict_type": conflict_type,
            "conflict_data": conflict_data,
            "resolution_strategy": resolution_strategy,
            "detected_at": memory.updated_at.isoformat() if memory.updated_at else None,
        })

    return {
        "conflicts": conflicts,
        "count": len(conflicts),
        "limit": limit,
    }
