"""FastAPI dependencies.

Dependency injection for API routes.
"""
import re
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases import ProcessChatMessageUseCase

# User ID validation pattern (alphanumeric, dash, underscore, 1-64 chars)
USER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
from src.domain.services import (
    ConsolidationService,
    ConsolidationTriggerService,
    ProceduralMemoryService,
)
from src.infrastructure.database.repositories import (
    ChatEventRepository,
    EpisodicMemoryRepository,
    ProceduralMemoryRepository,
    SemanticMemoryRepository,
    SummaryRepository,
)
from src.infrastructure.database.session import get_db_session
from src.infrastructure.di.container import container


async def get_current_user_id(
    x_user_id: Annotated[str | None, Header()] = None
) -> str:
    """Extract user ID from request header.

    For Phase 1A, we use a simple header-based auth.
    In Phase 2+, this will be replaced with proper JWT auth.

    Args:
        x_user_id: User ID from X-User-Id header

    Returns:
        User ID

    Raises:
        HTTPException: If user ID is missing or invalid format
    """
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header",
        )

    # Validate user_id format
    if not USER_ID_PATTERN.match(x_user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format (alphanumeric, dash, underscore only, max 64 chars)",
        )

    return x_user_id


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for FastAPI dependency injection.

    Yields:
        AsyncSession: Database session
    """
    async with get_db_session() as session:
        yield session


async def get_process_chat_message_use_case(
    db: AsyncSession = Depends(get_db),
) -> ProcessChatMessageUseCase:
    """Get ProcessChatMessageUseCase with dependencies injected via container.

    Uses DI container to wire all dependencies. Only repositories are created
    per-request since they need the database session.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        Fully wired use case instance via container
    """
    # Create repositories with the session using container factories
    entity_repo = container.entity_repository_factory(db)
    chat_repo = container.chat_repository_factory(db)
    semantic_memory_repo = container.semantic_memory_repository_factory(db)
    domain_db_repo = container.domain_database_repository_factory(db)
    tool_usage_repo = container.tool_usage_repository_factory(db)

    # Create entity resolution service factory (needs per-request repository)
    entity_resolution_service = container.entity_resolution_service_factory(
        entity_repository=entity_repo,
        domain_db_port=domain_db_repo,
    )

    # Create conflict resolution service (needs per-request repository)
    conflict_resolution_service = container.conflict_resolution_service_factory(
        semantic_memory_repository=semantic_memory_repo,
    )

    # Create adaptive query orchestrator (needs per-request repositories)
    query_orchestrator = container.adaptive_query_orchestrator_factory(
        domain_db=domain_db_repo,
        usage_tracker=tool_usage_repo,
    )

    # Create use case factories (passing per-request repositories)
    resolve_entities_use_case = container.resolve_entities_use_case_factory(
        entity_repository=entity_repo,
        chat_repository=chat_repo,
        entity_resolution_service=entity_resolution_service,
    )

    extract_semantics_use_case = container.extract_semantics_use_case_factory(
        semantic_memory_repository=semantic_memory_repo,
        conflict_resolution_service=conflict_resolution_service,
        canonical_entity_repository=entity_repo,  # Phase 3.3: for system entity creation
    )

    augment_with_domain_use_case = container.augment_with_domain_use_case_factory(
        query_orchestrator=query_orchestrator,
    )

    score_memories_use_case = container.score_memories_use_case_factory(
        semantic_memory_repository=semantic_memory_repo,
    )

    # Create orchestrator use case using container factory
    return container.process_chat_message_use_case_factory(
        chat_repository=chat_repo,
        resolve_entities_use_case=resolve_entities_use_case,
        extract_semantics_use_case=extract_semantics_use_case,
        augment_with_domain_use_case=augment_with_domain_use_case,
        score_memories_use_case=score_memories_use_case,
        conflict_resolution_service=conflict_resolution_service,
    )



async def get_consolidation_service(
    db: AsyncSession = Depends(get_db),
) -> ConsolidationService:
    """Get ConsolidationService with dependencies injected.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        Fully wired consolidation service instance
    """
    # Create repositories
    episodic_repo = EpisodicMemoryRepository(db)
    semantic_repo = SemanticMemoryRepository(db)
    summary_repo = SummaryRepository(db)
    chat_repo = ChatEventRepository(db)

    # Get services from container
    llm_service = container.llm_service()
    embedding_service = container.embedding_service()

    # Create and return consolidation service
    return ConsolidationService(
        episodic_repo=episodic_repo,
        semantic_repo=semantic_repo,
        summary_repo=summary_repo,
        chat_repo=chat_repo,
        llm_service=llm_service,
        embedding_service=embedding_service,
    )



async def get_consolidation_trigger_service(
    db: AsyncSession = Depends(get_db),
) -> ConsolidationTriggerService:
    """Get ConsolidationTriggerService with dependencies injected.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        Fully wired consolidation trigger service instance
    """
    # Create repositories
    episodic_repo = EpisodicMemoryRepository(db)
    chat_repo = ChatEventRepository(db)

    # Create and return trigger service
    return ConsolidationTriggerService(
        episodic_repo=episodic_repo,
        chat_repo=chat_repo,
    )



async def get_summary_repository(
    db: AsyncSession = Depends(get_db),
) -> SummaryRepository:
    """Get SummaryRepository with database session.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        Summary repository instance
    """
    return SummaryRepository(db)


async def get_procedural_service(
    db: AsyncSession = Depends(get_db),
) -> ProceduralMemoryService:
    """Get ProceduralMemoryService with dependencies injected.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        Fully wired procedural memory service instance
    """
    # Create repositories
    episodic_repo = EpisodicMemoryRepository(db)
    procedural_repo = ProceduralMemoryRepository(db)

    # Create and return service
    return ProceduralMemoryService(
        episodic_repo=episodic_repo,
        procedural_repo=procedural_repo,
    )



async def get_procedural_repository(
    db: AsyncSession = Depends(get_db),
) -> ProceduralMemoryRepository:
    """Get ProceduralMemoryRepository with database session.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        Procedural memory repository instance
    """
    return ProceduralMemoryRepository(db)


async def get_semantic_memory_repository(
    db: AsyncSession = Depends(get_db),
) -> SemanticMemoryRepository:
    """Get SemanticMemoryRepository with database session.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        Semantic memory repository instance
    """
    return SemanticMemoryRepository(db)
