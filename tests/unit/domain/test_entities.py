"""Unit tests for domain entities.

Tests behavior and validation of domain entities.
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.entities import CanonicalEntity, EntityAlias, ChatMessage
from src.domain.value_objects import EntityReference


@pytest.mark.unit
class TestCanonicalEntity:
    """Test CanonicalEntity domain entity."""

    def test_canonical_entity_creation(self):
        """Test creating a canonical entity."""
        ref = EntityReference(
            table="companies",
            primary_key="id",
            primary_value="123",
            display_name="Acme Corp",
            properties=None,
        )

        entity = CanonicalEntity(
            entity_id="company_acme_123",
            entity_type="company",
            canonical_name="Acme Corporation",
            external_ref=ref,
            properties={"industry": "Tech"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        assert entity.entity_id == "company_acme_123"
        assert entity.entity_type == "company"
        assert entity.canonical_name == "Acme Corporation"
        assert entity.properties["industry"] == "Tech"

    def test_generate_entity_id(self):
        """Test entity ID generation."""
        entity_id = CanonicalEntity.generate_entity_id("customer", "acme_123")
        assert entity_id == "customer_acme_123"

        entity_id2 = CanonicalEntity.generate_entity_id("order", 12345)
        assert entity_id2 == "order_12345"

    def test_entity_type_checking(self):
        """Test entity type is accessible."""
        ref = EntityReference(
            table="companies",
            primary_key="id",
            primary_value="123",
            display_name="Acme",
            properties=None,
        )

        entity = CanonicalEntity(
            entity_id="company_acme_123",
            entity_type="company",
            canonical_name="Acme Corporation",
            external_ref=ref,
            properties={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        assert entity.entity_type == "company"
        assert entity.entity_id.startswith("company_")

    def test_update_properties(self):
        """Test updating entity properties."""
        ref = EntityReference(
            table="companies",
            primary_key="id",
            primary_value="123",
            display_name="Acme",
            properties=None,
        )

        entity = CanonicalEntity(
            entity_id="company_acme_123",
            entity_type="company",
            canonical_name="Acme Corporation",
            external_ref=ref,
            properties={"industry": "Tech"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        entity.update_properties({"industry": "Tech", "size": "Large"})
        assert entity.properties["size"] == "Large"
        assert entity.properties["industry"] == "Tech"


@pytest.mark.unit
class TestEntityAlias:
    """Test EntityAlias domain entity."""

    def test_entity_alias_creation(self):
        """Test creating an entity alias."""
        alias = EntityAlias(
            alias_id=1,
            canonical_entity_id="company_acme_123",
            alias_text="ACME",
            alias_source="user_stated",
            confidence=0.9,
            user_id="user-123",
        )

        assert alias.alias_text == "ACME"
        assert alias.confidence == 0.9
        assert alias.user_id == "user-123"

    def test_global_vs_user_alias(self):
        """Test global vs user-specific alias distinction."""
        global_alias = EntityAlias(
            alias_id=1,
            canonical_entity_id="company_acme_123",
            alias_text="ACME",
            alias_source="user_stated",
            confidence=0.9,
            user_id=None,  # Global
        )
        assert global_alias.user_id is None

        user_alias = EntityAlias(
            alias_id=2,
            canonical_entity_id="company_acme_123",
            alias_text="ACME",
            alias_source="user_stated",
            confidence=0.9,
            user_id="user-123",  # User-specific
        )
        assert user_alias.user_id == "user-123"

    def test_increment_use_count(self):
        """Test incrementing use count."""
        alias = EntityAlias(
            alias_id=1,
            canonical_entity_id="company_acme_123",
            alias_text="ACME",
            alias_source="user_stated",
            confidence=0.9,
            user_id="user-123",
        )

        initial_count = alias.use_count
        alias.increment_use_count()
        assert alias.use_count == initial_count + 1

    def test_confidence_value(self):
        """Test confidence value is stored correctly."""
        alias = EntityAlias(
            alias_id=1,
            canonical_entity_id="company_acme_123",
            alias_text="ACME",
            alias_source="user_stated",
            confidence=0.8,
            user_id="user-123",
        )

        assert alias.confidence == 0.8

        # Can update confidence directly (dataclass)
        alias.confidence = 0.95
        assert alias.confidence == 0.95


@pytest.mark.unit
class TestChatMessage:
    """Test ChatMessage domain entity."""

    def test_chat_message_creation(self):
        """Test creating a chat message."""
        session_id = uuid4()
        message = ChatMessage(
            session_id=session_id,
            user_id="user-123",
            role="user",
            content="Hello, how are you?",
        )

        assert message.session_id == session_id
        assert message.user_id == "user-123"
        assert message.role == "user"
        assert message.content == "Hello, how are you?"

    def test_content_hash_computed_automatically(self):
        """Test that content hash is computed on creation."""
        message = ChatMessage(
            session_id=uuid4(),
            user_id="user-123",
            role="user",
            content="Test message",
        )

        # Content hash should be computed
        assert message.content_hash is not None
        assert len(message.content_hash) == 64  # SHA256 hex digest

    def test_same_content_produces_same_hash(self):
        """Test that same content produces same hash."""
        content = "Test message"

        message1 = ChatMessage(
            session_id=uuid4(),
            user_id="user-123",
            role="user",
            content=content,
        )

        message2 = ChatMessage(
            session_id=uuid4(),
            user_id="user-456",
            role="user",
            content=content,
        )

        assert message1.content_hash == message2.content_hash

    def test_message_role_checking(self):
        """Test message role is stored correctly."""
        user_message = ChatMessage(
            session_id=uuid4(),
            user_id="user-123",
            role="user",
            content="Hello",
        )
        assert user_message.role == "user"

        assistant_message = ChatMessage(
            session_id=uuid4(),
            user_id="user-123",
            role="assistant",
            content="Hi",
        )
        assert assistant_message.role == "assistant"

    def test_event_metadata(self):
        """Test event_metadata field."""
        message = ChatMessage(
            session_id=uuid4(),
            user_id="user-123",
            role="user",
            content="Hello",
            event_metadata={"source": "web"},
        )
        assert message.event_metadata == {"source": "web"}

        message_no_metadata = ChatMessage(
            session_id=uuid4(),
            user_id="user-123",
            role="user",
            content="Hello",
        )
        assert message_no_metadata.event_metadata == {}
