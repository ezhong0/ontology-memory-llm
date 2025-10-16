"""Dependency injection container.

Uses dependency-injector to wire all application components.
"""
from dependency_injector import containers, providers

from src.application.use_cases import (
    AugmentWithDomainUseCase,
    ExtractSemanticsUseCase,
    ProcessChatMessageUseCase,
    ResolveEntitiesUseCase,
    ScoreMemoriesUseCase,
)
from src.config.settings import Settings
from src.domain.services import (
    ConflictDetectionService,
    ConflictResolutionService,
    DomainAugmentationService,
    EntityResolutionService,
    LLMReplyGenerator,
    MemoryValidationService,
    MultiSignalScorer,
    SemanticExtractionService,
    SimpleMentionExtractor,
)
from src.infrastructure.database.repositories import (
    ChatEventRepository,
    EntityRepository,
    SemanticMemoryRepository,
)
from src.infrastructure.database.session import async_session_factory
from src.infrastructure.embedding import OpenAIEmbeddingService
from src.infrastructure.llm import (
    AnthropicLLMService,
    AnthropicProvider,
    OpenAILLMService,
    OpenAIProvider,
)


def create_llm_service(settings: Settings) -> OpenAILLMService | AnthropicLLMService:
    """Factory function to create LLM service based on configuration.

    Args:
        settings: Application settings

    Returns:
        Configured LLM service (OpenAI or Anthropic)
    """
    if settings.llm_provider == "anthropic":
        return AnthropicLLMService(api_key=settings.anthropic_api_key)
    else:
        return OpenAILLMService(api_key=settings.openai_api_key)


def create_llm_provider(settings: Settings) -> OpenAIProvider | AnthropicProvider:
    """Factory function to create LLM provider for reply generation.

    Args:
        settings: Application settings

    Returns:
        Configured LLM provider (OpenAI or Anthropic)
    """
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(api_key=settings.anthropic_api_key)
    else:
        return OpenAIProvider(api_key=settings.openai_api_key)


def get_llm_model(settings: Settings) -> str:
    """Get the LLM model name based on provider configuration.

    Args:
        settings: Application settings

    Returns:
        Model name for the configured provider
    """
    if settings.llm_provider == "anthropic":
        return settings.anthropic_model
    else:
        return settings.openai_llm_model


class Container(containers.DeclarativeContainer):
    """Application dependency injection container.

    Wires together all layers:
    - Configuration (Settings)
    - Infrastructure (Repositories, Services)
    - Domain Services
    - Use Cases
    """

    # Configuration
    config = providers.Configuration()

    # Settings (loaded from environment)
    settings = providers.Singleton(Settings)

    # Infrastructure - LLM and Embedding Services
    # Conditionally use OpenAI or Anthropic based on configuration
    llm_service = providers.Singleton(
        create_llm_service,
        settings=settings,
    )

    # LLM Provider for reply generation (conditionally uses OpenAI or Anthropic)
    llm_provider = providers.Singleton(
        create_llm_provider,
        settings=settings,
    )

    embedding_service = providers.Singleton(
        OpenAIEmbeddingService,
        api_key=settings.provided.openai_api_key,
    )

    # Infrastructure - Database Session
    # Note: Session is created per-request in FastAPI dependency
    # This is just the factory
    db_session_factory = providers.Singleton(
        lambda: async_session_factory
    )

    # Infrastructure - Repositories
    # These are factories that take a session
    entity_repository_factory = providers.Factory(
        EntityRepository,
    )

    chat_repository_factory = providers.Factory(
        ChatEventRepository,
    )

    semantic_memory_repository_factory = providers.Factory(
        SemanticMemoryRepository,
    )

    # Domain Services
    mention_extractor = providers.Singleton(
        SimpleMentionExtractor,
    )

    entity_resolution_service_factory = providers.Factory(
        EntityResolutionService,
        # entity_repository will be provided per-request
        # llm_service is singleton
        llm_service=llm_service,
    )

    # Phase 1B Services
    semantic_extraction_service = providers.Singleton(
        SemanticExtractionService,
        llm_service=llm_service,
    )

    memory_validation_service = providers.Singleton(
        MemoryValidationService,
    )

    conflict_detection_service = providers.Singleton(
        ConflictDetectionService,
    )

    # Phase 2.1 Services
    conflict_resolution_service_factory = providers.Factory(
        ConflictResolutionService,
        # semantic_memory_repository provided per-request
    )

    # Phase 1C Services
    domain_augmentation_service = providers.Singleton(
        DomainAugmentationService,
    )

    # LLM Reply Generator (uses configurable provider and model)
    llm_reply_generator = providers.Singleton(
        LLMReplyGenerator,
        llm_provider=llm_provider,
        model=providers.Callable(
            get_llm_model,
            settings=settings,
        ),
    )

    # Phase 1D Services
    multi_signal_scorer = providers.Singleton(
        MultiSignalScorer,
    )

    # Use Cases
    # Phase 1A: Entity Resolution
    resolve_entities_use_case_factory = providers.Factory(
        ResolveEntitiesUseCase,
        # Repositories provided per-request
        entity_resolution_service=entity_resolution_service_factory,
        mention_extractor=mention_extractor,
    )

    # Phase 1B: Semantic Extraction (updated for Phase 2.1 conflict resolution)
    extract_semantics_use_case_factory = providers.Factory(
        ExtractSemanticsUseCase,
        # Repository provided per-request
        semantic_extraction_service=semantic_extraction_service,
        memory_validation_service=memory_validation_service,
        conflict_detection_service=conflict_detection_service,
        conflict_resolution_service=conflict_resolution_service_factory,
        embedding_service=embedding_service,
    )

    # Phase 1C: Domain Augmentation
    augment_with_domain_use_case_factory = providers.Factory(
        AugmentWithDomainUseCase,
        domain_augmentation_service=domain_augmentation_service,
    )

    # Phase 1D: Memory Scoring
    score_memories_use_case_factory = providers.Factory(
        ScoreMemoriesUseCase,
        multi_signal_scorer=multi_signal_scorer,
        embedding_service=embedding_service,
        # Repository provided per-request
    )

    # Orchestrator: Coordinates all phases
    process_chat_message_use_case_factory = providers.Factory(
        ProcessChatMessageUseCase,
        # Repositories provided per-request
        # Use cases are factories
        resolve_entities_use_case=resolve_entities_use_case_factory,
        extract_semantics_use_case=extract_semantics_use_case_factory,
        augment_with_domain_use_case=augment_with_domain_use_case_factory,
        score_memories_use_case=score_memories_use_case_factory,
        llm_reply_generator=llm_reply_generator,
    )


# Global container instance
container = Container()
