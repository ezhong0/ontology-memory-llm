"""FastAPI dependencies.

Dependency injection for API routes.
"""
from typing import Annotated, AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases import ProcessChatMessageUseCase
from src.domain.services import (
    ConflictDetectionService,
    MemoryValidationService,
    SemanticExtractionService,
)
from src.infrastructure.database.repositories import (
    ChatEventRepository,
    EntityRepository,
    SemanticMemoryRepository,
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
        HTTPException: If user ID is missing
    """
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header",
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
    """Get ProcessChatMessageUseCase with dependencies injected.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        Fully wired use case instance
    """
    # Create repositories with the session
    entity_repo = EntityRepository(db)
    chat_repo = ChatEventRepository(db)
    semantic_memory_repo = SemanticMemoryRepository(db)

    # Get services from container (these are singletons)
    llm_service = container.llm_service()
    embedding_service = container.embedding_service()
    mention_extractor = container.mention_extractor()

    # Create entity resolution service (Phase 1A)
    entity_resolution_service = container.entity_resolution_service_factory(
        entity_repository=entity_repo,
    )

    # Create Phase 1B services
    semantic_extraction_service = SemanticExtractionService(llm_service=llm_service)
    memory_validation_service = MemoryValidationService()
    conflict_detection_service = ConflictDetectionService()

    # Create and return use case
    use_case = ProcessChatMessageUseCase(
        entity_repository=entity_repo,
        chat_repository=chat_repo,
        entity_resolution_service=entity_resolution_service,
        mention_extractor=mention_extractor,
        semantic_extraction_service=semantic_extraction_service,
        memory_validation_service=memory_validation_service,
        conflict_detection_service=conflict_detection_service,
        semantic_memory_repository=semantic_memory_repo,
        embedding_service=embedding_service,
    )

    return use_case
