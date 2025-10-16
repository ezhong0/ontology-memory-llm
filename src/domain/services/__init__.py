"""Domain services.

Business logic services that don't belong to a single entity.
"""
from src.domain.services.conflict_detection_service import ConflictDetectionService
from src.domain.services.conflict_resolution_service import ConflictResolutionService
from src.domain.services.consolidation_service import ConsolidationService
from src.domain.services.consolidation_trigger_service import (
    ConsolidationTriggerService,
)
from src.domain.services.debug_trace_service import (
    DebugTraceService,
    TraceContext,
    TraceType,
)
from src.domain.services.domain_augmentation_service import (
    DomainAugmentationService,
    EntityInfo,
)
from src.domain.services.entity_resolution_service import EntityResolutionService
from src.domain.services.llm_reply_generator import LLMReplyGenerator
from src.domain.services.memory_validation_service import MemoryValidationService
from src.domain.services.mention_extractor import SimpleMentionExtractor
from src.domain.services.multi_signal_scorer import MultiSignalScorer
from src.domain.services.pii_redaction_service import PIIRedactionService
from src.domain.services.procedural_memory_service import ProceduralMemoryService
from src.domain.services.semantic_extraction_service import SemanticExtractionService

__all__ = [
    # Phase 1A
    "EntityResolutionService",
    "SimpleMentionExtractor",
    # Phase 1B
    "SemanticExtractionService",
    "MemoryValidationService",
    "ConflictDetectionService",
    # Phase 2.1
    "ConflictResolutionService",
    # Phase 1D
    "ConsolidationService",
    "ConsolidationTriggerService",
    "ProceduralMemoryService",
    "MultiSignalScorer",
    # Domain augmentation & reply generation
    "DomainAugmentationService",
    "EntityInfo",
    "LLMReplyGenerator",
    "PIIRedactionService",
    # Debug & observability
    "DebugTraceService",
    "TraceContext",
    "TraceType",
]
