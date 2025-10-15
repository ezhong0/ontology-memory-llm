"""Dependency injection container.

Uses dependency-injector to wire all application components.
"""
from dependency_injector import containers, providers

from src.application.use_cases import ProcessChatMessageUseCase
from src.config.settings import Settings
from src.domain.services import EntityResolutionService, SimpleMentionExtractor
from src.infrastructure.database.repositories import ChatEventRepository, EntityRepository
from src.infrastructure.database.session import async_session_factory
from src.infrastructure.embedding import OpenAIEmbeddingService
from src.infrastructure.llm import OpenAILLMService


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
    llm_service = providers.Singleton(
        OpenAILLMService,
        api_key=settings.provided.openai_api_key,
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

    # Use Cases
    process_chat_message_use_case_factory = providers.Factory(
        ProcessChatMessageUseCase,
        # Repositories will be provided per-request
        # Services are singletons
        entity_resolution_service=entity_resolution_service_factory,
        mention_extractor=mention_extractor,
    )


# Global container instance
container = Container()
