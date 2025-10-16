"""API endpoints for memory data exploration."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    CanonicalEntity,
    ChatEvent,
    EntityAlias,
    EpisodicMemory,
    MemoryConflict,
    MemorySummary,
    ProceduralMemory,
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
    last_validated_at: str | None = None

    class Config:
        from_attributes = True


class CanonicalEntityResponse(BaseModel):
    """Canonical entity with alias count."""

    entity_id: str
    entity_type: str
    canonical_name: str
    external_ref: dict | None = None
    properties: dict | None = None
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


class ChatEventResponse(BaseModel):
    """Chat event (raw conversation data)."""

    event_id: int
    session_id: str
    user_id: str
    role: str
    content: str
    created_at: str

    class Config:
        from_attributes = True


class EpisodicMemoryResponse(BaseModel):
    """Episodic memory (event with meaning)."""

    memory_id: int
    user_id: str
    session_id: str
    summary: str
    event_type: str
    entities: dict
    importance: float
    created_at: str

    class Config:
        from_attributes = True


class ProceduralMemoryResponse(BaseModel):
    """Procedural memory (learned heuristic)."""

    memory_id: int
    user_id: str
    trigger_pattern: str
    action_heuristic: str
    observed_count: int
    confidence: float
    created_at: str

    class Config:
        from_attributes = True


class MemorySummaryResponse(BaseModel):
    """Memory summary (cross-session consolidation)."""

    summary_id: int
    user_id: str
    scope_type: str
    scope_identifier: str | None
    summary_text: str
    key_facts: dict
    confidence: float
    created_at: str

    class Config:
        from_attributes = True


class MemoryConflictResponse(BaseModel):
    """Memory conflict (detected inconsistency)."""

    conflict_id: int
    conflict_type: str
    conflict_data: dict
    resolution_strategy: str | None
    resolved_at: str | None
    created_at: str

    class Config:
        from_attributes = True


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/semantic", response_model=list[SemanticMemoryResponse])
async def list_semantic_memories(
    user_id: str = "demo-user", session: AsyncSession = Depends(get_db)
) -> list[SemanticMemoryResponse]:
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


@router.get("/entities", response_model=list[CanonicalEntityResponse])
async def list_canonical_entities(
    entity_type: str | None = None, session: AsyncSession = Depends(get_db)
) -> list[CanonicalEntityResponse]:
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


@router.get("/aliases", response_model=list[EntityAliasResponse])
async def list_entity_aliases(
    user_id: str | None = "demo-user", session: AsyncSession = Depends(get_db)
) -> list[EntityAliasResponse]:
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


@router.get("/chat_events", response_model=list[ChatEventResponse])
async def list_chat_events(
    user_id: str = "demo-user",
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
) -> list[ChatEventResponse]:
    """Get raw chat events for a user.

    Args:
        user_id: User ID to filter events (default: demo-user)
        limit: Maximum number of events to return (default: 50)
        session: Database session (injected)

    Returns:
        List of chat events ordered by creation time (most recent first)
    """
    query = (
        select(ChatEvent)
        .where(ChatEvent.user_id == user_id)
        .order_by(ChatEvent.created_at.desc())
        .limit(limit)
    )

    result = await session.execute(query)
    events = result.scalars().all()

    return [
        ChatEventResponse(
            event_id=event.event_id,
            session_id=str(event.session_id),
            user_id=event.user_id,
            role=event.role,
            content=event.content,
            created_at=event.created_at.isoformat(),
        )
        for event in events
    ]


@router.get("/episodic", response_model=list[EpisodicMemoryResponse])
async def list_episodic_memories(
    user_id: str = "demo-user",
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
) -> list[EpisodicMemoryResponse]:
    """Get episodic memories for a user.

    Args:
        user_id: User ID to filter memories (default: demo-user)
        limit: Maximum number of memories to return (default: 50)
        session: Database session (injected)

    Returns:
        List of episodic memories ordered by creation time (most recent first)
    """
    query = (
        select(EpisodicMemory)
        .where(EpisodicMemory.user_id == user_id)
        .order_by(EpisodicMemory.created_at.desc())
        .limit(limit)
    )

    result = await session.execute(query)
    memories = result.scalars().all()

    return [
        EpisodicMemoryResponse(
            memory_id=memory.memory_id,
            user_id=memory.user_id,
            session_id=str(memory.session_id),
            summary=memory.summary,
            event_type=memory.event_type,
            entities=memory.entities,
            importance=memory.importance,
            created_at=memory.created_at.isoformat(),
        )
        for memory in memories
    ]


@router.get("/procedural", response_model=list[ProceduralMemoryResponse])
async def list_procedural_memories(
    user_id: str = "demo-user", session: AsyncSession = Depends(get_db)
) -> list[ProceduralMemoryResponse]:
    """Get procedural memories (learned heuristics) for a user.

    Args:
        user_id: User ID to filter memories (default: demo-user)
        session: Database session (injected)

    Returns:
        List of procedural memories ordered by confidence (highest first)
    """
    query = (
        select(ProceduralMemory)
        .where(ProceduralMemory.user_id == user_id)
        .order_by(ProceduralMemory.confidence.desc())
    )

    result = await session.execute(query)
    memories = result.scalars().all()

    return [
        ProceduralMemoryResponse(
            memory_id=memory.memory_id,
            user_id=memory.user_id,
            trigger_pattern=memory.trigger_pattern,
            action_heuristic=memory.action_heuristic,
            observed_count=memory.observed_count,
            confidence=memory.confidence,
            created_at=memory.created_at.isoformat(),
        )
        for memory in memories
    ]


@router.get("/summaries", response_model=list[MemorySummaryResponse])
async def list_memory_summaries(
    user_id: str = "demo-user", session: AsyncSession = Depends(get_db)
) -> list[MemorySummaryResponse]:
    """Get memory summaries (cross-session consolidation) for a user.

    Args:
        user_id: User ID to filter summaries (default: demo-user)
        session: Database session (injected)

    Returns:
        List of memory summaries ordered by creation time (most recent first)
    """
    query = (
        select(MemorySummary)
        .where(MemorySummary.user_id == user_id)
        .order_by(MemorySummary.created_at.desc())
    )

    result = await session.execute(query)
    summaries = result.scalars().all()

    return [
        MemorySummaryResponse(
            summary_id=summary.summary_id,
            user_id=summary.user_id,
            scope_type=summary.scope_type,
            scope_identifier=summary.scope_identifier,
            summary_text=summary.summary_text,
            key_facts=summary.key_facts,
            confidence=summary.confidence,
            created_at=summary.created_at.isoformat(),
        )
        for summary in summaries
    ]


@router.get("/conflicts", response_model=list[MemoryConflictResponse])
async def list_memory_conflicts(
    session: AsyncSession = Depends(get_db),
) -> list[MemoryConflictResponse]:
    """Get memory conflicts (detected inconsistencies).

    Args:
        session: Database session (injected)

    Returns:
        List of memory conflicts ordered by creation time (most recent first)
    """
    query = select(MemoryConflict).order_by(MemoryConflict.created_at.desc())

    result = await session.execute(query)
    conflicts = result.scalars().all()

    return [
        MemoryConflictResponse(
            conflict_id=conflict.conflict_id,
            conflict_type=conflict.conflict_type,
            conflict_data=conflict.conflict_data,
            resolution_strategy=conflict.resolution_strategy,
            resolved_at=conflict.resolved_at.isoformat() if conflict.resolved_at else None,
            created_at=conflict.created_at.isoformat(),
        )
        for conflict in conflicts
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
        Dictionary of memory statistics for all 6 layers
    """
    # Layer 1: Chat events
    chat_events_result = await session.execute(
        select(ChatEvent).where(ChatEvent.user_id == user_id)
    )
    chat_events_count = len(chat_events_result.scalars().all())

    # Layer 2: Entities and aliases
    entity_result = await session.execute(
        select(CanonicalEntity).where(CanonicalEntity.entity_id.like("customer:%"))
    )
    entity_count = len(entity_result.scalars().all())

    alias_result = await session.execute(
        select(EntityAlias).where(EntityAlias.user_id == user_id)
    )
    alias_count = len(alias_result.scalars().all())

    # Layer 3: Episodic memories
    episodic_result = await session.execute(
        select(EpisodicMemory).where(EpisodicMemory.user_id == user_id)
    )
    episodic_count = len(episodic_result.scalars().all())

    # Layer 4: Semantic memories
    semantic_result = await session.execute(
        select(SemanticMemory).where(
            SemanticMemory.user_id == user_id, SemanticMemory.status == "active"
        )
    )
    semantic_count = len(semantic_result.scalars().all())

    # Layer 5: Procedural memories
    procedural_result = await session.execute(
        select(ProceduralMemory).where(ProceduralMemory.user_id == user_id)
    )
    procedural_count = len(procedural_result.scalars().all())

    # Layer 6: Memory summaries
    summaries_result = await session.execute(
        select(MemorySummary).where(MemorySummary.user_id == user_id)
    )
    summaries_count = len(summaries_result.scalars().all())

    # Supporting: Memory conflicts
    conflicts_result = await session.execute(select(MemoryConflict))
    conflicts_count = len(conflicts_result.scalars().all())

    return {
        "chat_events": chat_events_count,
        "canonical_entities": entity_count,
        "entity_aliases": alias_count,
        "episodic_memories": episodic_count,
        "semantic_memories": semantic_count,
        "procedural_memories": procedural_count,
        "memory_summaries": summaries_count,
        "memory_conflicts": conflicts_count,
    }


@router.delete("/clear")
async def clear_memories(
    user_id: str = "demo-user", session: AsyncSession = Depends(get_db)
) -> dict:
    """Clear all memories for a user (demo/development only).

    CAUTION: This is a destructive operation that deletes:
    - All chat events
    - All episodic memories
    - All semantic memories
    - All procedural memories
    - All memory summaries
    - All entity aliases (user-specific)
    - All memory conflicts

    Args:
        user_id: User ID to clear memories for (default: demo-user)
        session: Database session (injected)

    Returns:
        Dictionary with count of deleted records per table
    """
    from sqlalchemy import delete

    # Track deletion counts
    deleted_counts = {}

    # Layer 1: Chat events
    chat_result = await session.execute(
        delete(ChatEvent).where(ChatEvent.user_id == user_id).returning(ChatEvent.event_id)
    )
    deleted_counts["chat_events"] = len(chat_result.fetchall())

    # Layer 2: Entity aliases (user-specific only, keep canonical entities)
    alias_result = await session.execute(
        delete(EntityAlias).where(EntityAlias.user_id == user_id).returning(EntityAlias.alias_id)
    )
    deleted_counts["entity_aliases"] = len(alias_result.fetchall())

    # Layer 3: Episodic memories
    episodic_result = await session.execute(
        delete(EpisodicMemory)
        .where(EpisodicMemory.user_id == user_id)
        .returning(EpisodicMemory.memory_id)
    )
    deleted_counts["episodic_memories"] = len(episodic_result.fetchall())

    # Layer 4: Semantic memories
    semantic_result = await session.execute(
        delete(SemanticMemory)
        .where(SemanticMemory.user_id == user_id)
        .returning(SemanticMemory.memory_id)
    )
    deleted_counts["semantic_memories"] = len(semantic_result.fetchall())

    # Layer 5: Procedural memories
    procedural_result = await session.execute(
        delete(ProceduralMemory)
        .where(ProceduralMemory.user_id == user_id)
        .returning(ProceduralMemory.memory_id)
    )
    deleted_counts["procedural_memories"] = len(procedural_result.fetchall())

    # Layer 6: Memory summaries
    summaries_result = await session.execute(
        delete(MemorySummary)
        .where(MemorySummary.user_id == user_id)
        .returning(MemorySummary.summary_id)
    )
    deleted_counts["memory_summaries"] = len(summaries_result.fetchall())

    # Supporting: Memory conflicts (delete all for simplicity)
    conflicts_result = await session.execute(
        delete(MemoryConflict).returning(MemoryConflict.conflict_id)
    )
    deleted_counts["memory_conflicts"] = len(conflicts_result.fetchall())

    # Commit all deletions
    await session.commit()

    return {
        "status": "success",
        "message": f"All memories cleared for user: {user_id}",
        "deleted": deleted_counts,
        "total_deleted": sum(deleted_counts.values()),
    }
