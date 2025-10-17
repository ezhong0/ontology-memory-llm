"""Domain ports (interfaces).

Port interfaces define contracts for external dependencies.
Infrastructure layer implements these ports.
"""
from src.domain.ports.chat_repository import IChatEventRepository
from src.domain.ports.domain_database_port import DomainDatabasePort
from src.domain.ports.embedding_service import IEmbeddingService
from src.domain.ports.entity_repository import IEntityRepository
from src.domain.ports.episodic_memory_repository import IEpisodicMemoryRepository
from src.domain.ports.llm_service import ILLMService
from src.domain.ports.procedural_memory_repository import IProceduralMemoryRepository
from src.domain.ports.semantic_memory_repository import ISemanticMemoryRepository
from src.domain.ports.summary_repository import ISummaryRepository
from src.domain.ports.tool_usage_tracker_port import IToolUsageTracker

__all__ = [
    # Phase 1A
    "IEntityRepository",
    "IChatEventRepository",
    "IEmbeddingService",
    "ILLMService",
    # Phase 1B
    "ISemanticMemoryRepository",
    # Phase 1C
    "IEpisodicMemoryRepository",
    "ISummaryRepository",
    "DomainDatabasePort",
    # Phase 1D
    "IProceduralMemoryRepository",
    # LLM Tool Calling
    "IToolUsageTracker",
]
