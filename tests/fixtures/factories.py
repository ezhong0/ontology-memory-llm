"""
Test Data Factories

Provides factory functions for creating test data with sensible defaults.
Follows the Factory pattern for test data generation.

Usage:
    entity = EntityFactory.create(canonical_name="Acme Corp")
    memory = MemoryFactory.create_semantic(predicate="delivery_preference")
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid
import numpy as np


# ============================================================================
# Entity Factories
# ============================================================================

@dataclass
class CanonicalEntityBuilder:
    """Builder for CanonicalEntity test data"""
    entity_id: Optional[str] = None
    entity_type: str = "customer"
    canonical_name: str = "Test Corporation"
    external_ref: Optional[Dict] = None
    properties: Optional[Dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def build(self):
        """Build CanonicalEntity (will work once domain entities implemented)"""
        return type('CanonicalEntity', (), {
            'entity_id': self.entity_id or f"{self.entity_type}:{uuid.uuid4().hex[:8]}",
            'entity_type': self.entity_type,
            'canonical_name': self.canonical_name,
            'external_ref': self.external_ref or {"table": f"domain.{self.entity_type}s", "id": uuid.uuid4().hex[:8]},
            'properties': self.properties or {},
            'created_at': self.created_at or datetime.utcnow(),
            'updated_at': self.updated_at or datetime.utcnow()
        })()


@dataclass
class EntityAliasBuilder:
    """Builder for EntityAlias test data"""
    alias_id: Optional[int] = None
    canonical_entity_id: str = "customer:test_123"
    alias_text: str = "Test Corp"
    alias_source: str = "learned"  # 'exact'|'fuzzy'|'learned'|'user_stated'
    user_id: Optional[str] = None  # None = global alias
    confidence: float = 0.95
    use_count: int = 1
    alias_metadata: Optional[Dict] = None
    created_at: Optional[datetime] = None

    def build(self):
        """Build EntityAlias"""
        return type('EntityAlias', (), {
            'alias_id': self.alias_id,
            'canonical_entity_id': self.canonical_entity_id,
            'alias_text': self.alias_text,
            'alias_source': self.alias_source,
            'user_id': self.user_id,
            'confidence': self.confidence,
            'use_count': self.use_count,
            'alias_metadata': self.alias_metadata or {},
            'created_at': self.created_at or datetime.utcnow()
        })()


class EntityFactory:
    """Factory for creating test entities"""

    @staticmethod
    def create(
        entity_id: Optional[str] = None,
        entity_type: str = "customer",
        canonical_name: str = "Test Corporation",
        **kwargs
    ):
        """Create CanonicalEntity with sensible defaults"""
        builder = CanonicalEntityBuilder(
            entity_id=entity_id,
            entity_type=entity_type,
            canonical_name=canonical_name
        )

        # Override with kwargs
        for key, value in kwargs.items():
            if hasattr(builder, key):
                setattr(builder, key, value)

        return builder.build()

    @staticmethod
    def create_customer(name: str, customer_id: Optional[str] = None, **kwargs):
        """Convenience method for creating customer entities"""
        return EntityFactory.create(
            entity_id=customer_id or f"customer:{uuid.uuid4().hex[:8]}",
            entity_type="customer",
            canonical_name=name,
            external_ref={"table": "domain.customers", "id": customer_id or uuid.uuid4().hex[:8]},
            **kwargs
        )

    @staticmethod
    def create_product(name: str, product_id: Optional[str] = None, **kwargs):
        """Convenience method for creating product entities"""
        return EntityFactory.create(
            entity_id=product_id or f"product:{uuid.uuid4().hex[:8]}",
            entity_type="product",
            canonical_name=name,
            external_ref={"table": "domain.products", "id": product_id or uuid.uuid4().hex[:8]},
            **kwargs
        )

    @staticmethod
    def create_sales_order(so_number: str, so_id: Optional[str] = None, **kwargs):
        """Convenience method for creating sales order entities"""
        return EntityFactory.create(
            entity_id=so_id or f"sales_order:{uuid.uuid4().hex[:8]}",
            entity_type="sales_order",
            canonical_name=so_number,
            external_ref={"table": "domain.sales_orders", "id": so_id or uuid.uuid4().hex[:8]},
            **kwargs
        )

    @staticmethod
    def create_alias(
        canonical_entity_id: str,
        alias_text: str,
        alias_source: str = "learned",
        user_id: Optional[str] = None,
        **kwargs
    ):
        """Create EntityAlias"""
        builder = EntityAliasBuilder(
            canonical_entity_id=canonical_entity_id,
            alias_text=alias_text,
            alias_source=alias_source,
            user_id=user_id
        )

        for key, value in kwargs.items():
            if hasattr(builder, key):
                setattr(builder, key, value)

        return builder.build()


# ============================================================================
# Memory Factories
# ============================================================================

@dataclass
class SemanticMemoryBuilder:
    """Builder for SemanticMemory test data"""
    memory_id: Optional[int] = None
    user_id: str = "test_user"
    subject_entity_id: str = "customer:test_123"
    predicate: str = "preference"
    predicate_type: str = "preference"  # preference|requirement|observation|policy|attribute
    object_value: Any = field(default_factory=lambda: {"type": "text", "value": "test_value"})
    confidence: float = 0.7
    confidence_factors: Optional[Dict] = None
    reinforcement_count: int = 1
    last_validated_at: Optional[datetime] = None
    source_type: str = "episodic"  # episodic|consolidation|inference|correction
    source_memory_id: Optional[int] = None
    extracted_from_event_id: Optional[int] = None
    status: str = "active"  # active|aging|superseded|invalidated
    superseded_by_memory_id: Optional[int] = None
    embedding: Optional[np.ndarray] = None
    importance: float = 0.5
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def build(self):
        """Build SemanticMemory"""
        return type('SemanticMemory', (), {
            'memory_id': self.memory_id,
            'user_id': self.user_id,
            'subject_entity_id': self.subject_entity_id,
            'predicate': self.predicate,
            'predicate_type': self.predicate_type,
            'object_value': self.object_value,
            'confidence': self.confidence,
            'confidence_factors': self.confidence_factors or {"base": 0.7},
            'reinforcement_count': self.reinforcement_count,
            'last_validated_at': self.last_validated_at or datetime.utcnow(),
            'source_type': self.source_type,
            'source_memory_id': self.source_memory_id,
            'extracted_from_event_id': self.extracted_from_event_id,
            'status': self.status,
            'superseded_by_memory_id': self.superseded_by_memory_id,
            'embedding': self.embedding,
            'importance': self.importance,
            'created_at': self.created_at or datetime.utcnow(),
            'updated_at': self.updated_at or datetime.utcnow()
        })()


@dataclass
class EpisodicMemoryBuilder:
    """Builder for EpisodicMemory test data"""
    memory_id: Optional[int] = None
    user_id: str = "test_user"
    session_id: Optional[str] = None
    summary: str = "Test episodic memory"
    event_type: str = "statement"  # question|statement|command|correction|confirmation
    source_event_ids: List[int] = field(default_factory=lambda: [1])
    entities: List[Dict] = field(default_factory=list)
    domain_facts_referenced: Optional[Dict] = None
    importance: float = 0.5
    embedding: Optional[np.ndarray] = None
    created_at: Optional[datetime] = None

    def build(self):
        """Build EpisodicMemory"""
        return type('EpisodicMemory', (), {
            'memory_id': self.memory_id,
            'user_id': self.user_id,
            'session_id': self.session_id or str(uuid.uuid4()),
            'summary': self.summary,
            'event_type': self.event_type,
            'source_event_ids': self.source_event_ids,
            'entities': self.entities,
            'domain_facts_referenced': self.domain_facts_referenced or {},
            'importance': self.importance,
            'embedding': self.embedding,
            'created_at': self.created_at or datetime.utcnow()
        })()


@dataclass
class ChatEventBuilder:
    """Builder for ChatEvent test data"""
    event_id: Optional[int] = None
    session_id: Optional[str] = None
    user_id: str = "test_user"
    role: str = "user"  # user|assistant|system
    content: str = "Test message"
    content_hash: Optional[str] = None
    event_metadata: Optional[Dict] = None
    created_at: Optional[datetime] = None

    def build(self):
        """Build ChatEvent"""
        import hashlib
        return type('ChatEvent', (), {
            'event_id': self.event_id,
            'session_id': self.session_id or str(uuid.uuid4()),
            'user_id': self.user_id,
            'role': self.role,
            'content': self.content,
            'content_hash': self.content_hash or hashlib.sha256(self.content.encode()).hexdigest()[:16],
            'event_metadata': self.event_metadata or {},
            'created_at': self.created_at or datetime.utcnow()
        })()


class MemoryFactory:
    """Factory for creating test memories"""

    @staticmethod
    def create_semantic(
        subject_entity_id: str = "customer:test_123",
        predicate: str = "preference",
        object_value: Any = None,
        confidence: float = 0.7,
        **kwargs
    ):
        """Create SemanticMemory with sensible defaults"""
        builder = SemanticMemoryBuilder(
            subject_entity_id=subject_entity_id,
            predicate=predicate,
            object_value=object_value or {"type": "text", "value": "test"},
            confidence=confidence
        )

        for key, value in kwargs.items():
            if hasattr(builder, key):
                setattr(builder, key, value)

        return builder.build()

    @staticmethod
    def create_delivery_preference(
        entity_id: str,
        day: str = "Friday",
        confidence: float = 0.75,
        **kwargs
    ):
        """Convenience: Create delivery preference memory"""
        return MemoryFactory.create_semantic(
            subject_entity_id=entity_id,
            predicate="delivery_preference",
            predicate_type="preference",
            object_value={"type": "day_of_week", "value": day},
            confidence=confidence,
            **kwargs
        )

    @staticmethod
    def create_payment_terms(
        entity_id: str,
        terms: str = "NET30",
        confidence: float = 0.80,
        **kwargs
    ):
        """Convenience: Create payment terms memory"""
        return MemoryFactory.create_semantic(
            subject_entity_id=entity_id,
            predicate="payment_terms",
            predicate_type="attribute",
            object_value={"type": "payment_terms", "value": terms},
            confidence=confidence,
            **kwargs
        )

    @staticmethod
    def create_aged_memory(
        subject_entity_id: str,
        predicate: str,
        object_value: Any,
        days_old: int = 95,
        confidence: float = 0.7,
        **kwargs
    ):
        """Create memory that's aged (for testing decay)"""
        return MemoryFactory.create_semantic(
            subject_entity_id=subject_entity_id,
            predicate=predicate,
            object_value=object_value,
            confidence=confidence,
            last_validated_at=datetime.utcnow() - timedelta(days=days_old),
            created_at=datetime.utcnow() - timedelta(days=days_old),
            **kwargs
        )

    @staticmethod
    def create_episodic(
        summary: str = "Test episodic memory",
        event_type: str = "statement",
        entities: Optional[List[Dict]] = None,
        **kwargs
    ):
        """Create EpisodicMemory"""
        builder = EpisodicMemoryBuilder(
            summary=summary,
            event_type=event_type,
            entities=entities or []
        )

        for key, value in kwargs.items():
            if hasattr(builder, key):
                setattr(builder, key, value)

        return builder.build()

    @staticmethod
    def create_chat_event(
        content: str = "Test message",
        role: str = "user",
        **kwargs
    ):
        """Create ChatEvent"""
        builder = ChatEventBuilder(
            content=content,
            role=role
        )

        for key, value in kwargs.items():
            if hasattr(builder, key):
                setattr(builder, key, value)

        return builder.build()


# ============================================================================
# Domain Data Factories (for mocking domain DB)
# ============================================================================

class DomainDataFactory:
    """Factory for creating domain database test data"""

    @staticmethod
    def create_customer(
        customer_id: str = None,
        name: str = "Test Customer",
        **kwargs
    ) -> Dict:
        """Create customer record for domain.customers table"""
        return {
            "customer_id": customer_id or f"cust_{uuid.uuid4().hex[:8]}",
            "name": name,
            "email": kwargs.get("email", f"{name.lower().replace(' ', '.')}@example.com"),
            "phone": kwargs.get("phone", "555-0100"),
            "industry": kwargs.get("industry", "Technology"),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
            **kwargs
        }

    @staticmethod
    def create_invoice(
        invoice_id: str = None,
        customer_id: str = "cust_test",
        amount: float = 1200.00,
        status: str = "open",
        **kwargs
    ) -> Dict:
        """Create invoice record for domain.invoices table"""
        return {
            "invoice_id": invoice_id or f"inv_{uuid.uuid4().hex[:8]}",
            "invoice_number": kwargs.get("invoice_number", f"INV-{uuid.uuid4().hex[:4].upper()}"),
            "customer_id": customer_id,
            "amount": amount,
            "status": status,
            "due_date": kwargs.get("due_date", (datetime.utcnow() + timedelta(days=30)).date()),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
            **kwargs
        }

    @staticmethod
    def create_sales_order(
        so_id: str = None,
        customer_id: str = "cust_test",
        status: str = "open",
        **kwargs
    ) -> Dict:
        """Create sales order record for domain.sales_orders table"""
        return {
            "so_id": so_id or f"so_{uuid.uuid4().hex[:8]}",
            "so_number": kwargs.get("so_number", f"SO-{uuid.uuid4().hex[:4].upper()}"),
            "customer_id": customer_id,
            "status": status,
            "total_amount": kwargs.get("total_amount", 5000.00),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
            "updated_at": kwargs.get("updated_at", datetime.utcnow()),
            **kwargs
        }

    @staticmethod
    def create_product(
        product_id: str = None,
        name: str = "Test Product",
        **kwargs
    ) -> Dict:
        """Create product record for domain.products table"""
        return {
            "product_id": product_id or f"prod_{uuid.uuid4().hex[:8]}",
            "product_code": kwargs.get("product_code", f"PROD-{uuid.uuid4().hex[:4].upper()}"),
            "name": name,
            "price": kwargs.get("price", 99.99),
            "category": kwargs.get("category", "General"),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
            **kwargs
        }


# ============================================================================
# Embedding Helpers
# ============================================================================

def generate_test_embedding(text: str, dimension: int = 1536) -> np.ndarray:
    """
    Generate deterministic test embedding from text.

    Same text always produces same embedding (for test reproducibility).
    Uses text hash as random seed.
    """
    text_hash = hash(text)
    np.random.seed(text_hash % (2**32))
    embedding = np.random.rand(dimension).astype(np.float32)

    # Normalize to unit vector (like real embeddings)
    embedding = embedding / np.linalg.norm(embedding)

    return embedding
