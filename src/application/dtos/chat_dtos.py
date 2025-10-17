"""DTOs for chat operations.

Data Transfer Objects for application layer.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class ResolvedEntityDTO:
    """DTO for resolved entity information (Phase 1A).

    Attributes:
        entity_id: Canonical entity ID
        canonical_name: Display name
        entity_type: Type of entity (customer, order, etc.)
        mention_text: Original text that was resolved
        confidence: Resolution confidence [0.0, 1.0]
        method: Resolution method used (exact, alias, fuzzy, coreference)
        is_implicit: True if entity inferred from session context (not explicitly mentioned)
    """

    entity_id: str
    canonical_name: str
    entity_type: str
    mention_text: str
    confidence: float
    method: str
    is_implicit: bool = False  # Phase 2.2: Session-aware context


@dataclass
class SemanticMemoryDTO:
    """DTO for semantic memory (Phase 1B).

    Entity-tagged natural language with importance scoring.

    Attributes:
        memory_id: Database primary key
        content: The memory text (natural language)
        entities: Entity IDs mentioned in this memory
        confidence: Confidence in accuracy [0.0, 1.0]
        importance: Dynamic importance score [0.0, 1.0]
        status: Memory status (active, inactive, conflicted)
    """

    memory_id: int
    content: str
    entities: list[str]
    confidence: float
    importance: float
    status: str


@dataclass
class DomainFactDTO:
    """DTO for domain fact from database (Phase 1C).

    Attributes:
        fact_type: Type of fact (invoice_status, order_chain, sla_risk)
        entity_id: Canonical entity ID
        content: Human-readable summary
        metadata: Structured data
        source_table: Source table(s) in domain schema
        source_rows: UUIDs of specific rows
        retrieved_at: Timestamp when fact was retrieved
    """

    fact_type: str
    entity_id: str
    content: str
    metadata: dict[str, Any]
    source_table: str
    source_rows: list[str]
    retrieved_at: datetime


@dataclass
class RetrievedMemoryDTO:
    """DTO for retrieved memory from Phase 1D scoring.

    Attributes:
        memory_id: Database primary key
        memory_type: Type of memory (episodic, semantic, summary)
        content: Human-readable content
        relevance_score: Multi-signal relevance score [0.0, 1.0]
        confidence: Memory confidence [0.0, 0.95]
        importance: Importance score [0.0, 1.0] (semantic memories only)
        entities: Entity IDs mentioned (semantic memories only)
    """

    memory_id: int
    memory_type: str
    content: str
    relevance_score: float
    confidence: float
    importance: float | None = None
    entities: list[str] | None = None


@dataclass
class MemoryConflictDTO:
    """DTO for memory conflict information (Phase 2.1 Epistemic Humility).

    Attributes:
        conflict_type: Type of conflict (memory_vs_memory, memory_vs_db)
        entities: Entities the conflict is about
        existing_content: Content of existing memory
        new_content: Content of new observation
        existing_confidence: Confidence of existing memory
        new_confidence: Confidence of new observation
        resolution_strategy: How conflict was resolved
    """

    conflict_type: str
    entities: list[str]
    existing_content: str
    new_content: str
    existing_confidence: float
    new_confidence: float
    resolution_strategy: str


@dataclass
class ProcessChatMessageInput:
    """Input DTO for processing a chat message.

    Attributes:
        user_id: User ID (from authentication)
        session_id: Conversation session ID
        content: Message content
        role: Message role (user | assistant | system)
        metadata: Optional metadata
    """

    user_id: str
    session_id: UUID
    content: str
    role: str = "user"
    metadata: dict[str, Any] | None = None


@dataclass
class ProcessChatMessageOutput:
    """Output DTO for processed chat message.

    Attributes:
        event_id: Created chat event ID
        session_id: Conversation session ID
        resolved_entities: List of resolved entities from the message (Phase 1A)
        mention_count: Total number of mentions extracted
        resolution_success_rate: Percentage of mentions successfully resolved
        semantic_memories: List of semantic memories extracted (Phase 1B)
        conflict_count: Number of conflicts detected (Phase 1B)
        conflicts_detected: Detailed conflict information for transparency (Phase 1C)
        domain_facts: List of domain facts retrieved (Phase 1C)
        retrieved_memories: List of memories retrieved from past conversations (Phase 1D)
        reply: Generated natural language reply (Phase 1C)
        step_timings: Optional dict mapping step names to duration in seconds
    """

    event_id: int
    session_id: UUID
    resolved_entities: list[ResolvedEntityDTO]
    mention_count: int
    resolution_success_rate: float
    semantic_memories: list[SemanticMemoryDTO]
    conflict_count: int
    conflicts_detected: list[MemoryConflictDTO]
    domain_facts: list[DomainFactDTO]
    retrieved_memories: list[RetrievedMemoryDTO]
    reply: str
    step_timings: dict[str, float] | None = None
