"""Memory creation helpers for E2E tests.

Provides MemoryFactory class to programmatically create memories
(episodic, semantic, procedural) for scenario testing.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import uuid4
import json

from src.domain.entities import SemanticMemory
from src.infrastructure.database.repositories import SemanticMemoryRepository
from src.infrastructure.di.container import container


def calculate_importance(confidence: float, confirmation_count: int = 0) -> float:
    """Calculate importance from confidence and confirmation count.

    Formula: base_importance × confirmation_factor
    - Base: 0.3 + (confidence × 0.6) maps confidence [0..1] → importance [0.3..0.9]
    - Confirmation factor: 1.0 + (0.1 × confirmations), capped at 1.5

    Args:
        confidence: Memory confidence [0.0, 1.0]
        confirmation_count: Number of confirmations (default: 0)

    Returns:
        Importance score [0.0, 1.0]
    """
    base_importance = 0.3 + (confidence * 0.6)
    confirmation_factor = min(1.5, 1.0 + (0.1 * confirmation_count))
    importance = min(1.0, base_importance * confirmation_factor)
    return importance


class MemoryFactory:
    """Create memories programmatically for testing."""

    def __init__(self, session: AsyncSession):
        """
        Initialize memory factory.

        Args:
            session: Async database session
        """
        self.session = session
        self.semantic_repo = SemanticMemoryRepository(session)
        self.embedding_service = container.embedding_service()

    async def create_semantic_memory(
        self,
        user_id: str,
        content: str,
        entities: List[str],
        confidence: float = 0.7,
        importance: Optional[float] = None,
        status: str = "active",
        source_event_ids: Optional[List[int]] = None,
        source_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        last_accessed_at: Optional[datetime] = None,
    ) -> SemanticMemory:
        """
        Create semantic memory directly (bypass chat pipeline).

        Args:
            user_id: User ID
            content: The memory text (natural language)
            entities: List of entity IDs mentioned in this memory
            confidence: Confidence in accuracy [0.0, 1.0] (default: 0.7)
            importance: Importance score [0.0, 1.0] (auto-calculated if None)
            status: Memory status (active, inactive, conflicted)
            source_event_ids: Chat event IDs that contributed to this memory
            source_text: Original chat message
            metadata: Flexible metadata dict
            last_accessed_at: When last accessed (default: now)

        Returns:
            Created SemanticMemory entity
        """
        # Ensure metadata has confirmation_count (initial creation is first confirmation)
        if metadata is None:
            metadata = {}
        if "confirmation_count" not in metadata:
            metadata["confirmation_count"] = 1

        # Auto-calculate importance if not provided
        if importance is None:
            confirmation_count = metadata.get("confirmation_count", 1)
            importance = calculate_importance(confidence, confirmation_count)

        # Generate embedding from natural language content
        embedding = await self.embedding_service.generate_embedding(content)

        # Create memory entity
        memory = SemanticMemory(
            user_id=user_id,
            content=content,
            entities=entities,
            confidence=confidence,
            importance=importance,
            status=status,
            source_event_ids=source_event_ids or [],
            embedding=embedding,
            source_text=source_text or content,
            metadata=metadata,
            last_accessed_at=last_accessed_at or datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Save to database
        saved_memory = await self.semantic_repo.create(memory)

        # Commit to make data visible across all queries (E2E tests need this)
        # The test fixture will still rollback at the end for isolation
        await self.session.commit()

        return saved_memory

    async def create_episodic_memory(
        self,
        user_id: str,
        session_id: str,
        summary: str,
        event_type: str = "statement",
        entities: Optional[List[Dict[str, Any]]] = None,
        domain_facts_referenced: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        source_event_ids: Optional[List[int]] = None,
    ) -> int:
        """
        Create episodic memory directly.

        Args:
            user_id: User ID
            session_id: Session ID
            summary: Summary of the event
            event_type: Type of event (question, statement, command, correction, confirmation)
            entities: List of entities mentioned
            domain_facts_referenced: Domain facts used in this episode
            importance: Importance score 0-1
            source_event_ids: Chat event IDs this memory was derived from

        Returns:
            memory_id of created episodic memory
        """
        # Generate embedding
        embedding = await self.embedding_service.generate_embedding(summary)

        # Insert directly into database
        result = await self.session.execute(
            text("""
                INSERT INTO app.episodic_memories
                (user_id, session_id, summary, event_type, source_event_ids, entities,
                 domain_facts_referenced, importance, embedding, created_at)
                VALUES (:user_id, :session_id, :summary, :event_type, :source_event_ids,
                        :entities, :domain_facts_referenced, :importance, :embedding, :created_at)
                RETURNING memory_id
            """),
            {
                "user_id": user_id,
                "session_id": session_id,
                "summary": summary,
                "event_type": event_type,
                "source_event_ids": source_event_ids or [],
                "entities": json.dumps(entities or []),
                "domain_facts_referenced": json.dumps(domain_facts_referenced) if domain_facts_referenced else None,
                "importance": importance,
                "embedding": str(embedding),
                "created_at": datetime.now(timezone.utc),
            },
        )

        memory_id = result.scalar_one()
        await self.session.flush()
        return memory_id

    async def create_procedural_memory(
        self,
        user_id: str,
        trigger_pattern: str,
        action_heuristic: str,
        trigger_features: Optional[Dict[str, Any]] = None,
        action_structure: Optional[Dict[str, Any]] = None,
        observed_count: int = 1,
        confidence: float = 0.5,
    ) -> int:
        """
        Create procedural memory (learned pattern).

        Args:
            user_id: User ID
            trigger_pattern: When this pattern occurs...
            action_heuristic: ...do this action
            trigger_features: Features that trigger this pattern
            action_structure: Structured action to take
            observed_count: How many times observed
            confidence: Confidence in this pattern

        Returns:
            memory_id of created procedural memory
        """
        # Generate embedding from pattern
        pattern_text = f"{trigger_pattern} -> {action_heuristic}"
        embedding = await self.embedding_service.generate_embedding(pattern_text)

        # Insert directly into database
        result = await self.session.execute(
            text("""
                INSERT INTO app.procedural_memories
                (user_id, trigger_pattern, trigger_features, action_heuristic,
                 action_structure, observed_count, confidence, embedding, created_at, updated_at)
                VALUES (:user_id, :trigger_pattern, :trigger_features, :action_heuristic,
                        :action_structure, :observed_count, :confidence, :embedding, :created_at, :updated_at)
                RETURNING memory_id
            """),
            {
                "user_id": user_id,
                "trigger_pattern": trigger_pattern,
                "trigger_features": json.dumps(trigger_features
                or {"intent": "unknown", "entity_types": [], "topics": []}),
                "action_heuristic": action_heuristic,
                "action_structure": json.dumps(action_structure
                or {"action_type": "augment", "predicates": []}),
                "observed_count": observed_count,
                "confidence": confidence,
                "embedding": str(embedding),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        )

        memory_id = result.scalar_one()
        await self.session.flush()
        return memory_id

    async def create_canonical_entity(
        self,
        entity_id: str,
        entity_type: str,
        canonical_name: str,
        external_ref: Dict[str, Any],
        properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a canonical entity for testing.

        Args:
            entity_id: Entity ID (e.g., "customer:kai_123")
            entity_type: Type (customer, invoice, order, etc.)
            canonical_name: Human-readable name
            external_ref: Reference to domain DB with keys:
                         - table: Table name (e.g., "domain.customers")
                         - id: UUID value
            properties: Additional properties

        Returns:
            entity_id
        """
        # Transform external_ref to match EntityReference schema
        table = external_ref["table"]
        primary_value = external_ref["id"]

        # Determine primary_key column name from table
        primary_key_map = {
            "domain.customers": "customer_id",
            "domain.sales_orders": "so_id",
            "domain.invoices": "invoice_id",
            "domain.work_orders": "wo_id",
            "domain.tasks": "task_id",
            "domain.payments": "payment_id",
        }
        primary_key = primary_key_map.get(table, "id")

        transformed_external_ref = {
            "table": table,
            "primary_key": primary_key,
            "primary_value": primary_value,
            "display_name": canonical_name,
            "properties": properties or {}
        }

        await self.session.execute(
            text("""
                INSERT INTO app.canonical_entities
                (entity_id, entity_type, canonical_name, external_ref, properties, created_at, updated_at)
                VALUES (:entity_id, :entity_type, :canonical_name, :external_ref, :properties, :created_at, :updated_at)
                ON CONFLICT (entity_id) DO NOTHING
            """),
            {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "canonical_name": canonical_name,
                "external_ref": json.dumps(transformed_external_ref),
                "properties": json.dumps(properties or {}),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        )

        await self.session.commit()
        return entity_id

    async def create_entity_alias(
        self,
        canonical_entity_id: str,
        alias_text: str,
        alias_source: str = "user_stated",
        user_id: Optional[str] = None,
        confidence: float = 0.9,
    ) -> int:
        """
        Create an entity alias for testing.

        Args:
            canonical_entity_id: Entity ID this alias points to
            alias_text: Alias text
            alias_source: Source of alias (user_stated, learned, fuzzy)
            user_id: User ID for user-specific alias (None = global)
            confidence: Alias confidence (default 0.9)

        Returns:
            alias_id of created alias
        """
        result = await self.session.execute(
            text("""
                INSERT INTO app.entity_aliases
                (canonical_entity_id, alias_text, alias_source, user_id, confidence, use_count, alias_metadata, created_at)
                VALUES (:canonical_entity_id, :alias_text, :alias_source, :user_id, :confidence, :use_count, :alias_metadata, :created_at)
                RETURNING alias_id
            """),
            {
                "canonical_entity_id": canonical_entity_id,
                "alias_text": alias_text,
                "alias_source": alias_source,
                "user_id": user_id,
                "confidence": confidence,
                "use_count": 0,
                "alias_metadata": json.dumps({}),
                "created_at": datetime.now(timezone.utc),
            },
        )

        alias_id = result.scalar_one()
        await self.session.flush()
        return alias_id
