"""Domain value objects.

Immutable value objects representing core domain concepts.
"""
from src.domain.value_objects.conversation_context import ConversationContext
from src.domain.value_objects.entity_mention import EntityMention
from src.domain.value_objects.entity_reference import EntityReference
from src.domain.value_objects.memory_conflict import (
    ConflictResolution,
    ConflictType,
    MemoryConflict,
)
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
]
