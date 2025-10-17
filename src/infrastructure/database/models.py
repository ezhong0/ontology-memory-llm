"""SQLAlchemy models for the ontology-aware memory system.

This module defines all database tables as SQLAlchemy ORM models.
Schema follows DESIGN.md specification with 10 core tables.
"""
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# Layer 1: Raw Events
class ChatEvent(Base):
    """Raw conversation events (immutable audit trail)."""

    __tablename__ = "chat_events"
    __table_args__ = (
        UniqueConstraint("session_id", "content_hash", name="uq_session_content"),
        Index("idx_chat_events_session", "session_id"),
        Index("idx_chat_events_user_time", "user_id", "created_at"),
        {"schema": "app"},
    )

    event_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(Text, nullable=False)
    role = Column(Text, CheckConstraint("role IN ('user', 'assistant', 'system')"), nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False)
    event_metadata = Column(JSONB)  # Renamed from metadata (reserved by SQLAlchemy)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# Layer 2: Entity Resolution
class CanonicalEntity(Base):
    """Canonical entities with external database references."""

    __tablename__ = "canonical_entities"
    __table_args__ = (
        Index("idx_entities_type", "entity_type"),
        Index("idx_entities_name", "canonical_name"),
        {"schema": "app"},
    )

    entity_id = Column(Text, primary_key=True)
    entity_type = Column(Text, nullable=False)
    canonical_name = Column(Text, nullable=False)
    external_ref = Column(JSONB, nullable=False)
    properties = Column(JSONB)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class EntityAlias(Base):
    """Entity aliases for resolution (global and user-specific)."""

    __tablename__ = "entity_aliases"
    __table_args__ = (
        UniqueConstraint("alias_text", "user_id", "canonical_entity_id", name="uq_alias_user_entity"),
        Index("idx_aliases_text", "alias_text"),
        Index("idx_aliases_entity", "canonical_entity_id"),
        Index("idx_aliases_user", "user_id", postgresql_where=Column("user_id").isnot(None)),
        {"schema": "app"},
    )

    alias_id = Column(BigInteger, primary_key=True, autoincrement=True)
    canonical_entity_id = Column(Text, ForeignKey("app.canonical_entities.entity_id"), nullable=False)
    alias_text = Column(Text, nullable=False)
    alias_source = Column(Text, nullable=False)  # 'exact'|'fuzzy'|'learned'|'user_stated'
    user_id = Column(Text)  # NULL = global, not-null = user-specific
    confidence = Column(Float, nullable=False, default=1.0)
    use_count = Column(Integer, nullable=False, default=1)
    alias_metadata = Column(JSONB)  # Renamed from metadata (reserved by SQLAlchemy)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# Layer 3: Episodic Memory
class EpisodicMemory(Base):
    """Episodic memories (events with meaning)."""

    __tablename__ = "episodic_memories"
    __table_args__ = (
        Index("idx_episodic_user_time", "user_id", "created_at"),
        Index("idx_episodic_session", "session_id"),
        Index("idx_episodic_embedding", "embedding", postgresql_using="ivfflat", postgresql_ops={"embedding": "vector_cosine_ops"}, postgresql_with={"lists": 100}),
        {"schema": "app"},
    )

    memory_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    summary = Column(Text, nullable=False)
    event_type = Column(Text, nullable=False)  # question|statement|command|correction|confirmation
    source_event_ids = Column(ARRAY(BigInteger), nullable=False)
    entities = Column(JSONB, nullable=False)  # [{id, name, type, mentions: [{text, position, is_coreference}]}]
    domain_facts_referenced = Column(JSONB)  # {queries: [{table, filter, results}]}
    importance = Column(Float, nullable=False, default=0.5)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# Layer 4: Semantic Memory
class SemanticMemory(Base):
    """Semantic memories (abstracted facts with lifecycle)."""

    __tablename__ = "semantic_memories"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="valid_confidence"),
        CheckConstraint("status IN ('active', 'aging', 'superseded', 'invalidated')", name="valid_status"),
        Index("idx_semantic_user_status", "user_id", "status"),
        Index("idx_semantic_entity_pred", "subject_entity_id", "predicate"),
        Index("idx_semantic_embedding", "embedding", postgresql_using="ivfflat", postgresql_ops={"embedding": "vector_cosine_ops"}, postgresql_with={"lists": 100}),
        {"schema": "app"},
    )

    memory_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)

    # Subject-Predicate-Object triple
    subject_entity_id = Column(Text, ForeignKey("app.canonical_entities.entity_id"))
    predicate = Column(Text, nullable=False)
    predicate_type = Column(Text, nullable=False)  # preference|requirement|observation|policy|attribute
    object_value = Column(JSONB, nullable=False)

    # Confidence & evolution
    confidence = Column(Float, nullable=False, default=0.7)
    confidence_factors = Column(JSONB)  # {base, reinforcement, recency, source}
    reinforcement_count = Column(Integer, nullable=False, default=1)
    last_validated_at = Column(DateTime(timezone=True))

    # Provenance
    source_type = Column(Text, nullable=False)  # episodic|consolidation|inference|correction
    source_memory_id = Column(BigInteger)
    extracted_from_event_id = Column(BigInteger, ForeignKey("app.chat_events.event_id"))

    # Context (hybrid structured + natural language)
    original_text = Column(Text)  # Normalized triple text: "Gai Media prefers Friday deliveries"
    source_text = Column(Text)  # Original chat message that created this memory
    related_entities = Column(ARRAY(Text))  # All entity IDs mentioned (for multi-entity retrieval)

    # Lifecycle
    status = Column(Text, nullable=False, default="active")
    superseded_by_memory_id = Column(BigInteger, ForeignKey("app.semantic_memories.memory_id"))

    # Retrieval
    embedding = Column(Vector(1536))
    importance = Column(Float, nullable=False, default=0.5)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# Layer 5: Procedural Memory
class ProceduralMemory(Base):
    """Procedural memories (learned heuristics)."""

    __tablename__ = "procedural_memories"
    __table_args__ = (
        Index("idx_procedural_user", "user_id"),
        Index("idx_procedural_confidence", "confidence"),
        Index("idx_procedural_embedding", "embedding", postgresql_using="ivfflat", postgresql_ops={"embedding": "vector_cosine_ops"}, postgresql_with={"lists": 100}),
        {"schema": "app"},
    )

    memory_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    trigger_pattern = Column(Text, nullable=False)
    trigger_features = Column(JSONB, nullable=False)  # {intent, entity_types, topics}
    action_heuristic = Column(Text, nullable=False)
    action_structure = Column(JSONB, nullable=False)  # {action_type, queries, predicates}
    observed_count = Column(Integer, nullable=False, default=1)
    confidence = Column(Float, nullable=False, default=0.5)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# Layer 6: Memory Summaries
class MemorySummary(Base):
    """Memory summaries (cross-session consolidation)."""

    __tablename__ = "memory_summaries"
    __table_args__ = (
        Index("idx_summaries_user_scope", "user_id", "scope_type", "scope_identifier"),
        Index("idx_summaries_embedding", "embedding", postgresql_using="ivfflat", postgresql_ops={"embedding": "vector_cosine_ops"}, postgresql_with={"lists": 100}),
        {"schema": "app"},
    )

    summary_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    scope_type = Column(Text, nullable=False)  # entity|topic|session_window
    scope_identifier = Column(Text)
    summary_text = Column(Text, nullable=False)
    key_facts = Column(JSONB, nullable=False)
    source_data = Column(JSONB, nullable=False)  # {episodic_ids, semantic_ids, session_ids, time_range}
    supersedes_summary_id = Column(BigInteger, ForeignKey("app.memory_summaries.summary_id"))
    confidence = Column(Float, nullable=False, default=0.8)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# Supporting Tables
class DomainOntology(Base):
    """Domain ontology (relationship semantics)."""

    __tablename__ = "domain_ontology"
    __table_args__ = (
        UniqueConstraint("from_entity_type", "relation_type", "to_entity_type", name="uq_ontology_relation"),
        Index("idx_ontology_from", "from_entity_type"),
        Index("idx_ontology_to", "to_entity_type"),
        {"schema": "app"},
    )

    relation_id = Column(BigInteger, primary_key=True, autoincrement=True)
    from_entity_type = Column(Text, nullable=False)
    relation_type = Column(Text, nullable=False)  # has|creates|requires|fulfills
    to_entity_type = Column(Text, nullable=False)
    cardinality = Column(Text, nullable=False)
    relation_semantics = Column(Text, nullable=False)
    join_spec = Column(JSONB, nullable=False)  # {from_table, to_table, join_on}
    constraints = Column(JSONB)  # business rules
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class MemoryConflict(Base):
    """Memory conflicts (explicit conflict tracking)."""

    __tablename__ = "memory_conflicts"
    __table_args__ = (
        Index("idx_conflicts_event", "detected_at_event_id"),
        Index("idx_conflicts_type", "conflict_type"),
        {"schema": "app"},
    )

    conflict_id = Column(BigInteger, primary_key=True, autoincrement=True)
    detected_at_event_id = Column(BigInteger, ForeignKey("app.chat_events.event_id"), nullable=False)
    conflict_type = Column(Text, nullable=False)  # memory_vs_memory|memory_vs_db|temporal
    conflict_data = Column(JSONB, nullable=False)  # {memory_ids, values, confidences, db_source}
    resolution_strategy = Column(Text)  # trust_db|trust_recent|ask_user|both
    resolution_outcome = Column(JSONB)
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class SystemConfig(Base):
    """System configuration (heuristics and settings)."""

    __tablename__ = "system_config"
    __table_args__ = {"schema": "app"}

    config_key = Column(Text, primary_key=True)
    config_value = Column(JSONB, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ToolUsageLog(Base):
    """Tool usage log (track LLM tool calling patterns for learning).

    Vision Alignment:
    - Learning from usage (track what works)
    - Feedback loop infrastructure
    - Phase 2: Analyze patterns, optimize tool selection
    """

    __tablename__ = "tool_usage_log"
    __table_args__ = (
        Index("idx_tool_usage_conversation", "conversation_id"),
        Index("idx_tool_usage_timestamp", "timestamp"),
        Index("idx_tool_usage_tools_called", "tools_called", postgresql_using="gin"),
        {"schema": "app"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Text, nullable=False)
    query = Column(Text, nullable=False)
    tools_called = Column(JSONB, nullable=False)  # Array of {tool, arguments, iteration}
    facts_count = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    outcome_satisfaction = Column(Integer)  # NULL=unknown, 1=satisfied, 0=not satisfied
    outcome_feedback = Column(Text)
