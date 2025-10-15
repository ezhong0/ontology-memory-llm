"""Domain ports (interfaces).

Port interfaces define contracts for external dependencies.
Infrastructure layer implements these ports.
"""
from src.domain.ports.chat_repository import IChatEventRepository
from src.domain.ports.embedding_service import IEmbeddingService
from src.domain.ports.entity_repository import IEntityRepository
from src.domain.ports.llm_service import ILLMService

__all__ = [
    "IEntityRepository",
    "IChatEventRepository",
    "ILLMService",
    "IEmbeddingService",
]
