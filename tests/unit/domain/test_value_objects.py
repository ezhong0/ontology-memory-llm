"""Unit tests for domain value objects.

Tests immutability, validation, and behavior of value objects.
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.value_objects import (
    EntityMention,
    EntityReference,
    ResolutionResult,
    ResolutionMethod,
    ConversationContext,
)


@pytest.mark.unit
class TestEntityMention:
    """Test EntityMention value object."""

    def test_entity_mention_is_immutable(self):
        """Test that EntityMention is immutable (frozen dataclass)."""
        mention = EntityMention(
            text="Acme Corp",
            position=10,
            context_before="I met with ",
            context_after=" today",
            is_pronoun=False,
            sentence="I met with Acme Corp today.",
        )

        with pytest.raises(AttributeError):
            mention.text = "Something else"  # type: ignore

    def test_requires_coreference_for_pronouns(self):
        """Test that requires_coreference is True for pronouns."""
        pronoun = EntityMention(
            text="they",
            position=0,
            context_before="",
            context_after="",
            is_pronoun=True,
            sentence="They are good.",
        )
        assert pronoun.requires_coreference

    def test_requires_coreference_false_for_named_entities(self):
        """Test that requires_coreference is False for named entities."""
        entity = EntityMention(
            text="Acme Corp",
            position=0,
            context_before="",
            context_after="",
            is_pronoun=False,
            sentence="Acme Corp is great.",
        )
        assert not entity.requires_coreference


@pytest.mark.unit
class TestEntityReference:
    """Test EntityReference value object."""

    def test_entity_reference_is_immutable(self):
        """Test that EntityReference is immutable."""
        ref = EntityReference(
            table="companies",
            primary_key="company_id",
            primary_value="acme_123",
            display_name="Acme Corporation",
            properties={"industry": "Tech"},
        )

        with pytest.raises(AttributeError):
            ref.table = "customers"  # type: ignore

    def test_to_dict(self):
        """Test to_dict conversion."""
        ref = EntityReference(
            table="companies",
            primary_key="company_id",
            primary_value="acme_123",
            display_name="Acme Corporation",
            properties={"industry": "Tech"},
        )

        result = ref.to_dict()

        assert result == {
            "table": "companies",
            "primary_key": "company_id",
            "primary_value": "acme_123",
            "display_name": "Acme Corporation",
            "properties": {"industry": "Tech"},
        }

    def test_from_dict(self):
        """Test from_dict construction."""
        data = {
            "table": "companies",
            "primary_key": "company_id",
            "primary_value": "acme_123",
            "display_name": "Acme Corporation",
            "properties": {"industry": "Tech"},
        }

        ref = EntityReference.from_dict(data)

        assert ref.table == "companies"
        assert ref.primary_key == "company_id"
        assert ref.primary_value == "acme_123"
        assert ref.display_name == "Acme Corporation"
        assert ref.properties == {"industry": "Tech"}

    def test_from_dict_with_none_properties(self):
        """Test from_dict with None properties."""
        data = {
            "table": "companies",
            "primary_key": "company_id",
            "primary_value": "acme_123",
            "display_name": "Acme Corporation",
            "properties": None,
        }

        ref = EntityReference.from_dict(data)
        assert ref.properties is None


@pytest.mark.unit
class TestResolutionResult:
    """Test ResolutionResult value object."""

    def test_resolution_result_is_immutable(self):
        """Test that ResolutionResult is immutable."""
        result = ResolutionResult(
            entity_id="company_acme_123",
            confidence=0.9,
            method=ResolutionMethod.EXACT_MATCH,
            mention_text="Acme Corp",
            canonical_name="Acme Corporation",
            metadata={},
        )

        with pytest.raises(AttributeError):
            result.confidence = 0.5  # type: ignore

    def test_is_successful_when_not_failed(self):
        """Test that is_successful is True for non-failed results."""
        result = ResolutionResult(
            entity_id="company_acme_123",
            confidence=0.9,
            method=ResolutionMethod.EXACT_MATCH,
            mention_text="Acme Corp",
            canonical_name="Acme Corporation",
            metadata={},
        )
        assert result.is_successful

    def test_is_successful_false_when_failed(self):
        """Test that is_successful is False for failed results."""
        result = ResolutionResult.failed("unknown entity", "Not found")
        assert not result.is_successful

    def test_failed_factory_method(self):
        """Test that failed() factory creates a failed result."""
        result = ResolutionResult.failed("unknown entity", "Not found in database")

        assert result.method == ResolutionMethod.FAILED
        assert result.confidence == 0.0
        assert result.entity_id == ""
        assert result.canonical_name == ""
        assert result.mention_text == "unknown entity"
        assert result.metadata["reason"] == "Not found in database"

    def test_all_resolution_methods_defined(self):
        """Test that all 5 resolution methods are defined."""
        methods = list(ResolutionMethod)
        assert len(methods) >= 5
        assert ResolutionMethod.EXACT_MATCH in methods
        assert ResolutionMethod.USER_ALIAS in methods
        assert ResolutionMethod.FUZZY_MATCH in methods
        assert ResolutionMethod.COREFERENCE in methods
        assert ResolutionMethod.FAILED in methods


@pytest.mark.unit
class TestConversationContext:
    """Test ConversationContext value object."""

    def test_conversation_context_is_immutable(self):
        """Test that ConversationContext is immutable."""
        context = ConversationContext(
            user_id="user-123",
            session_id=uuid4(),
            recent_messages=["Hello"],
            recent_entities=[],
            current_message="How are you?",
        )

        with pytest.raises(AttributeError):
            context.user_id = "user-456"  # type: ignore

    def test_has_recent_entities_true(self):
        """Test has_recent_entities property when entities exist."""
        context = ConversationContext(
            user_id="user-123",
            session_id=uuid4(),
            recent_messages=["Hello"],
            recent_entities=[("entity_1", "Acme Corp")],
            current_message="How are you?",
        )
        assert context.has_recent_entities

    def test_has_recent_entities_false(self):
        """Test has_recent_entities property when no entities."""
        context = ConversationContext(
            user_id="user-123",
            session_id=uuid4(),
            recent_messages=["Hello"],
            recent_entities=[],
            current_message="How are you?",
        )
        assert not context.has_recent_entities

    def test_context_summary_generation(self):
        """Test context_summary property formatting."""
        context = ConversationContext(
            user_id="user-123",
            session_id=uuid4(),
            recent_messages=["Hello", "How are you?"],
            recent_entities=[("entity_1", "Acme Corp"), ("entity_2", "John Smith")],
            current_message="They called today.",
        )

        summary = context.context_summary

        # Should contain recent messages
        assert "Hello" in summary or "How are you?" in summary
        # Should contain recent entities
        assert "Acme Corp" in summary or "John Smith" in summary
        # Should contain section headers
        assert "Recent conversation" in summary
        assert "Recently mentioned entities" in summary

    def test_empty_context_summary(self):
        """Test context_summary with no messages or entities."""
        context = ConversationContext(
            user_id="user-123",
            session_id=uuid4(),
            recent_messages=[],
            recent_entities=[],
            current_message="Hello",
        )

        summary = context.context_summary
        # When no recent context, should return "No recent context"
        assert summary == "No recent context"

    def test_get_most_recent_entity(self):
        """Test get_most_recent_entity method."""
        context = ConversationContext(
            user_id="user-123",
            session_id=uuid4(),
            recent_messages=[],
            recent_entities=[("entity_1", "Acme"), ("entity_2", "Corp")],
            current_message="Test",
        )

        entity = context.get_most_recent_entity()
        assert entity == ("entity_2", "Corp")

    def test_get_most_recent_entity_when_none(self):
        """Test get_most_recent_entity when no entities."""
        context = ConversationContext(
            user_id="user-123",
            session_id=uuid4(),
            recent_messages=[],
            recent_entities=[],
            current_message="Test",
        )

        entity = context.get_most_recent_entity()
        assert entity is None
