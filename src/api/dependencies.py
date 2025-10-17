"""FastAPI dependencies.

Dependency injection for API routes.
"""
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases import ProcessChatMessageUseCase
from src.domain.services import (
    ConflictDetectionService,
    ConflictResolutionService,
    ConsolidationService,
    ConsolidationTriggerService,
    MemoryValidationService,
    MultiSignalScorer,
    PIIRedactionService,
    ProceduralMemoryService,
    SemanticExtractionService,
)
from src.application.services.adaptive_query_orchestrator import (
    AdaptiveQueryOrchestrator,
)
from src.infrastructure.database.repositories import (
    ChatEventRepository,
    DomainDatabaseRepository,
    EntityRepository,
    EpisodicMemoryRepository,
    PostgresToolUsageRepository,
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
        Fully wired use case instance with Phase 1A, 1B, 1C, and 1D use cases
    """
    from src.application.use_cases import (
        AugmentWithDomainUseCase,
        ExtractSemanticsUseCase,
        ResolveEntitiesUseCase,
        ScoreMemoriesUseCase,
    )

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

    # Phase 2.1 service
    conflict_resolution_service = ConflictResolutionService(
        semantic_memory_repository=semantic_memory_repo,
    )

    # Create Phase 1C services - LLM Tool Calling
    domain_db_repo = DomainDatabaseRepository(db)
    tool_usage_repo = PostgresToolUsageRepository(db)

    # Create adaptive query orchestrator (replaces keyword-based augmentation)
    query_orchestrator = AdaptiveQueryOrchestrator(
        llm_service=llm_service,
        domain_db=domain_db_repo,
        usage_tracker=tool_usage_repo,
    )

    llm_reply_generator = container.llm_reply_generator()

    # Create Phase 1D services
    multi_signal_scorer = MultiSignalScorer(validation_service=memory_validation_service)

    # Phase 3.1: PII Redaction Service
    pii_redaction_service = PIIRedactionService()

    # Create individual use cases (refactored architecture)
    resolve_entities_use_case = ResolveEntitiesUseCase(
        entity_repository=entity_repo,
        chat_repository=chat_repo,
        entity_resolution_service=entity_resolution_service,
        mention_extractor=mention_extractor,
    )

    extract_semantics_use_case = ExtractSemanticsUseCase(
        semantic_memory_repository=semantic_memory_repo,
        semantic_extraction_service=semantic_extraction_service,
        memory_validation_service=memory_validation_service,
        conflict_detection_service=conflict_detection_service,
        conflict_resolution_service=conflict_resolution_service,  # Phase 2.1
        embedding_service=embedding_service,
        canonical_entity_repository=entity_repo,  # Phase 3.3: for system entity creation
    )

    augment_with_domain_use_case = AugmentWithDomainUseCase(
        query_orchestrator=query_orchestrator,
    )

    score_memories_use_case = ScoreMemoriesUseCase(
        multi_signal_scorer=multi_signal_scorer,
        embedding_service=embedding_service,
        semantic_memory_repository=semantic_memory_repo,
    )

    # Create orchestrator use case
    return ProcessChatMessageUseCase(
        chat_repository=chat_repo,
        resolve_entities_use_case=resolve_entities_use_case,
        extract_semantics_use_case=extract_semantics_use_case,
        augment_with_domain_use_case=augment_with_domain_use_case,
        score_memories_use_case=score_memories_use_case,
        conflict_detection_service=conflict_detection_service,
        conflict_resolution_service=conflict_resolution_service,
        llm_reply_generator=llm_reply_generator,
        pii_redaction_service=pii_redaction_service,
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
