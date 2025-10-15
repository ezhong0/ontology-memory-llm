"""API endpoints for memory data exploration."""
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    CanonicalEntity,
    EntityAlias,
    SemanticMemory,
)
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/memories", tags=["demo-memories"])


# =============================================================================
# Response Models
# =============================================================================


class SemanticMemoryResponse(BaseModel):
    """Semantic memory with entity name resolved."""

    memory_id: str
    subject_entity_id: str
    subject_entity_name: str
    predicate: str
    predicate_type: str
    object_value: dict
    confidence: float
    reinforcement_count: int
    created_at: str
    last_validated_at: Optional[str] = None

    class Config:
        from_attributes = True


class CanonicalEntityResponse(BaseModel):
    """Canonical entity with alias count."""

    entity_id: str
    entity_type: str
    canonical_name: str
    external_ref: Optional[dict] = None
    properties: Optional[dict] = None
    alias_count: int
    created_at: str

    class Config:
        from_attributes = True


class EntityAliasResponse(BaseModel):
    """Entity alias with canonical name."""

    alias_id: str
    canonical_entity_id: str
    canonical_entity_name: str
    alias_text: str
    alias_source: str
    confidence: float
    use_count: int
    created_at: str

    class Config:
        from_attributes = True


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/semantic", response_model=List[SemanticMemoryResponse])
async def list_semantic_memories(
    user_id: str = "demo-user", session: AsyncSession = Depends(get_db)
) -> List[SemanticMemoryResponse]:
    """Get all semantic memories for a user with entity names resolved.

    Args:
        user_id: User ID to filter memories (default: demo-user)
        session: Database session (injected)

    Returns:
        List of semantic memories with subject entity names
    """
    # Join with canonical_entities to get entity names
    query = (
        select(SemanticMemory, CanonicalEntity.canonical_name)
        .join(CanonicalEntity, SemanticMemory.subject_entity_id == CanonicalEntity.entity_id)
        .where(SemanticMemory.user_id == user_id)
        .where(SemanticMemory.status == "active")
        .order_by(SemanticMemory.created_at.desc())
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        SemanticMemoryResponse(
            memory_id=str(memory.memory_id),
            subject_entity_id=memory.subject_entity_id,
            subject_entity_name=entity_name,
            predicate=memory.predicate,
            predicate_type=memory.predicate_type,
            object_value=memory.object_value,
            confidence=memory.confidence,
            reinforcement_count=memory.reinforcement_count,
            created_at=memory.created_at.isoformat(),
            last_validated_at=memory.last_validated_at.isoformat()
            if memory.last_validated_at
            else None,
        )
        for memory, entity_name in rows
    ]


@router.get("/entities", response_model=List[CanonicalEntityResponse])
async def list_canonical_entities(
    entity_type: Optional[str] = None, session: AsyncSession = Depends(get_db)
) -> List[CanonicalEntityResponse]:
    """Get all canonical entities with alias counts.

    Args:
        entity_type: Filter by entity type (e.g., 'customer')
        session: Database session (injected)

    Returns:
        List of canonical entities with alias counts
    """
    # Base query
    query = select(CanonicalEntity).order_by(CanonicalEntity.created_at.desc())

    # Filter by type if provided
    if entity_type:
        query = query.where(CanonicalEntity.entity_type == entity_type)

    result = await session.execute(query)
    entities = result.scalars().all()

    # Get alias counts for each entity
    responses = []
    for entity in entities:
        alias_count_query = select(EntityAlias).where(
            EntityAlias.canonical_entity_id == entity.entity_id
        )
        alias_result = await session.execute(alias_count_query)
        alias_count = len(alias_result.scalars().all())

        responses.append(
            CanonicalEntityResponse(
                entity_id=entity.entity_id,
                entity_type=entity.entity_type,
                canonical_name=entity.canonical_name,
                external_ref=entity.external_ref,
                properties=entity.properties,
                alias_count=alias_count,
                created_at=entity.created_at.isoformat(),
            )
        )

    return responses


@router.get("/aliases", response_model=List[EntityAliasResponse])
async def list_entity_aliases(
    user_id: Optional[str] = "demo-user", session: AsyncSession = Depends(get_db)
) -> List[EntityAliasResponse]:
    """Get all entity aliases with canonical names.

    Args:
        user_id: Filter by user ID (optional)
        session: Database session (injected)

    Returns:
        List of entity aliases with canonical names
    """
    # Join with canonical_entities to get entity names
    query = (
        select(EntityAlias, CanonicalEntity.canonical_name)
        .join(CanonicalEntity, EntityAlias.canonical_entity_id == CanonicalEntity.entity_id)
        .order_by(EntityAlias.created_at.desc())
    )

    # Filter by user if provided
    if user_id:
        query = query.where(EntityAlias.user_id == user_id)

    result = await session.execute(query)
    rows = result.all()

    return [
        EntityAliasResponse(
            alias_id=str(alias.alias_id),
            canonical_entity_id=alias.canonical_entity_id,
            canonical_entity_name=entity_name,
            alias_text=alias.alias_text,
            alias_source=alias.alias_source,
            confidence=alias.confidence,
            use_count=alias.use_count,
            created_at=alias.created_at.isoformat(),
        )
        for alias, entity_name in rows
    ]


@router.get("/stats")
async def get_memory_stats(
    user_id: str = "demo-user", session: AsyncSession = Depends(get_db)
) -> dict:
    """Get summary statistics for memory data.

    Args:
        user_id: User ID to filter memories (default: demo-user)
        session: Database session (injected)

    Returns:
        Dictionary of memory statistics
    """
    # Count semantic memories
    semantic_result = await session.execute(
        select(SemanticMemory).where(
            SemanticMemory.user_id == user_id, SemanticMemory.status == "active"
        )
    )
    semantic_count = len(semantic_result.scalars().all())

    # Count canonical entities (customers only for demo)
    entity_result = await session.execute(
        select(CanonicalEntity).where(CanonicalEntity.entity_id.like("customer:%"))
    )
    entity_count = len(entity_result.scalars().all())

    # Count aliases for demo user
    alias_result = await session.execute(
        select(EntityAlias).where(EntityAlias.user_id == user_id)
    )
    alias_count = len(alias_result.scalars().all())

    return {
        "semantic_memories": semantic_count,
        "canonical_entities": entity_count,
        "entity_aliases": alias_count,
    }
