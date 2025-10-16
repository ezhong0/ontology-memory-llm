"""Domain value objects.

Immutable value objects representing core domain concepts.
"""
from src.domain.value_objects.consolidation import (
    ConsolidationScope,
    KeyFact,
    SummaryData,
)
from src.domain.value_objects.conversation_context import ConversationContext
from src.domain.value_objects.domain_fact import DomainFact
from src.domain.value_objects.entity_mention import EntityMention
from src.domain.value_objects.entity_reference import EntityReference
from src.domain.value_objects.memory_candidate import MemoryCandidate, ScoredMemory, SignalBreakdown
from src.domain.value_objects.memory_conflict import (
    ConflictResolution,
    ConflictType,
    MemoryConflict,
)
from src.domain.value_objects.procedural_memory import Pattern
from src.domain.value_objects.query_context import QueryContext
from src.domain.value_objects.resolution_result import ResolutionMethod, ResolutionResult
from src.domain.value_objects.semantic_triple import PredicateType, SemanticTriple

__all__ = [
    # Phase 1A
    "EntityMention",
    "ResolutionResult",
    "ResolutionMethod",
    "EntityReference",
    "ConversationContext",
    # Phase 1B
    "ConflictResolution",
    "ConflictType",
    "MemoryConflict",
    "PredicateType",
    "SemanticTriple",
    # Phase 1D
    "ConsolidationScope",
    "KeyFact",
    "SummaryData",
    "Pattern",
    "MemoryCandidate",
    "ScoredMemory",
    "SignalBreakdown",
    "QueryContext",
    # Domain augmentation
    "DomainFact",
]
