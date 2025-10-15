"""Unit tests for SemanticExtractionService.

Tests the LLM-based semantic triple extraction from chat messages.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from src.domain.entities.chat_message import ChatMessage
from src.domain.services.semantic_extraction_service import SemanticExtractionService
from src.domain.value_objects import PredicateType, SemanticTriple


@pytest.mark.unit
class TestSemanticExtractionService:
    """Test SemanticExtractionService triple extraction."""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service for extraction."""
        llm = AsyncMock()
        llm.extract_semantic_triples = AsyncMock(return_value=[])
        return llm

    @pytest.fixture
    def extraction_service(self, mock_llm_service):
        """Create SemanticExtractionService with mock LLM."""
        return SemanticExtractionService(llm_service=mock_llm_service)

    @pytest.fixture
    def sample_message(self):
        """Sample chat message."""
        return ChatMessage(
            event_id=123,
            user_id="user_test_456",
            session_id=uuid4(),
            role="user",
            content="Acme Corporation prefers net-30 payment terms.",
            created_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_resolved_entities(self):
        """Sample resolved entities."""
        return [
            {
                "entity_id": "company_acme_123",
                "canonical_name": "Acme Corporation",
                "entity_type": "company",
            }
        ]

    # ============================================================================
    # Basic Extraction Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_extract_triples_success(
        self, extraction_service, mock_llm_service, sample_message, sample_resolved_entities
    ):
        """Test successful triple extraction."""
        # Setup: LLM returns valid triples
        mock_llm_service.extract_semantic_triples.return_value = [
            {
                "subject_entity_id": "company_acme_123",
                "predicate": "prefers",
                "predicate_type": "preference",
                "object_value": {"value": "net-30 payment terms", "type": "payment_term"},
                "confidence": 0.9,
            }
        ]

        # Execute
        triples = await extraction_service.extract_triples(
            message=sample_message,
            resolved_entities=sample_resolved_entities,
        )

        # Assert
        assert len(triples) == 1
        triple = triples[0]
        assert isinstance(triple, SemanticTriple)
        assert triple.subject_entity_id == "company_acme_123"
        assert triple.predicate == "prefers"
        assert triple.predicate_type == PredicateType.PREFERENCE
        assert triple.confidence == 0.9
        assert triple.metadata["source_event_id"] == 123
        assert triple.metadata["user_id"] == "user_test_456"

        mock_llm_service.extract_semantic_triples.assert_called_once_with(
            message="Acme Corporation prefers net-30 payment terms.",
            resolved_entities=sample_resolved_entities,
        )

    @pytest.mark.asyncio
    async def test_extract_triples_empty_message(
        self, extraction_service, mock_llm_service, sample_resolved_entities
    ):
        """Test extraction with empty message content."""
        empty_message = ChatMessage(
            event_id=1,
            user_id="user_1",
            session_id=uuid4(),
            role="user",
            content="",
            created_at=datetime.now(timezone.utc),
        )

        triples = await extraction_service.extract_triples(
            message=empty_message,
            resolved_entities=sample_resolved_entities,
        )

        assert triples == []
        mock_llm_service.extract_semantic_triples.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_triples_no_entities(
        self, extraction_service, mock_llm_service, sample_message
    ):
        """Test extraction with no resolved entities."""
        triples = await extraction_service.extract_triples(
            message=sample_message,
            resolved_entities=[],
        )

        assert triples == []
        mock_llm_service.extract_semantic_triples.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_triples_multiple_results(
        self, extraction_service, mock_llm_service, sample_message, sample_resolved_entities
    ):
        """Test extraction returns multiple triples."""
        # Setup: LLM returns multiple triples
        mock_llm_service.extract_semantic_triples.return_value = [
            {
                "subject_entity_id": "company_acme_123",
                "predicate": "prefers",
                "predicate_type": "preference",
                "object_value": {"value": "net-30 payment terms"},
                "confidence": 0.9,
            },
            {
                "subject_entity_id": "company_acme_123",
                "predicate": "has_tier",
                "predicate_type": "attribute",
                "object_value": {"value": "enterprise"},
                "confidence": 0.85,
            },
        ]

        triples = await extraction_service.extract_triples(
            message=sample_message,
            resolved_entities=sample_resolved_entities,
        )

        assert len(triples) == 2
        assert all(isinstance(t, SemanticTriple) for t in triples)
        assert triples[0].predicate == "prefers"
        assert triples[1].predicate == "has_tier"

    # ============================================================================
    # LLM Error Handling Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_extract_triples_llm_error(
        self, extraction_service, mock_llm_service, sample_message, sample_resolved_entities
    ):
        """Test extraction handles LLM errors gracefully."""
        # Setup: LLM raises exception
        mock_llm_service.extract_semantic_triples.side_effect = Exception("LLM API error")

        # Execute
        triples = await extraction_service.extract_triples(
            message=sample_message,
            resolved_entities=sample_resolved_entities,
        )

        # Should return empty list, not raise exception
        assert triples == []

    @pytest.mark.asyncio
    async def test_extract_triples_invalid_triple_skipped(
        self, extraction_service, mock_llm_service, sample_message, sample_resolved_entities
    ):
        """Test extraction skips invalid triples from LLM."""
        # Setup: LLM returns mix of valid and invalid triples
        mock_llm_service.extract_semantic_triples.return_value = [
            {
                # Valid triple
                "subject_entity_id": "company_acme_123",
                "predicate": "prefers",
                "predicate_type": "preference",
                "object_value": {"value": "net-30"},
                "confidence": 0.9,
            },
            {
                # Invalid: missing predicate
                "subject_entity_id": "company_acme_123",
                "predicate_type": "preference",
                "object_value": {"value": "test"},
                "confidence": 0.8,
            },
            {
                # Invalid: confidence out of range
                "subject_entity_id": "company_acme_123",
                "predicate": "test",
                "predicate_type": "preference",
                "object_value": {"value": "test"},
                "confidence": 1.5,
            },
        ]

        triples = await extraction_service.extract_triples(
            message=sample_message,
            resolved_entities=sample_resolved_entities,
        )

        # Only valid triple should be returned
        assert len(triples) == 1
        assert triples[0].predicate == "prefers"

    # ============================================================================
    # Validation Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_parse_validates_required_fields(self, extraction_service):
        """Test that missing required fields are rejected."""
        from src.domain.entities.chat_message import ChatMessage

        message = ChatMessage(
            event_id=1,
            user_id="user_1",
            session_id=uuid4(),
            role="user",
            content="test",
            created_at=datetime.now(timezone.utc),
        )

        # Missing 'predicate' field
        invalid_triple = {
            "subject_entity_id": "entity_1",
            "predicate_type": "attribute",
            "object_value": {"value": "test"},
            "confidence": 0.8,
        }

        with pytest.raises(ValueError, match="Missing required field: predicate"):
            extraction_service._parse_and_validate_triple(
                raw_triple=invalid_triple,
                message=message,
            )

    @pytest.mark.asyncio
    async def test_parse_validates_predicate_type(self, extraction_service):
        """Test that invalid predicate_type is rejected."""
        from src.domain.entities.chat_message import ChatMessage

        message = ChatMessage(
            event_id=1,
            user_id="user_1",
            session_id=uuid4(),
            role="user",
            content="test",
            created_at=datetime.now(timezone.utc),
        )

        invalid_triple = {
            "subject_entity_id": "entity_1",
            "predicate": "test",
            "predicate_type": "invalid_type",  # Not a valid PredicateType
            "object_value": {"value": "test"},
            "confidence": 0.8,
        }

        with pytest.raises(ValueError, match="Invalid predicate_type"):
            extraction_service._parse_and_validate_triple(
                raw_triple=invalid_triple,
                message=message,
            )

    @pytest.mark.asyncio
    async def test_parse_validates_object_value_is_dict(self, extraction_service):
        """Test that non-dict object_value is rejected."""
        from src.domain.entities.chat_message import ChatMessage

        message = ChatMessage(
            event_id=1,
            user_id="user_1",
            session_id=uuid4(),
            role="user",
            content="test",
            created_at=datetime.now(timezone.utc),
        )

        invalid_triple = {
            "subject_entity_id": "entity_1",
            "predicate": "test",
            "predicate_type": "attribute",
            "object_value": "not a dict",  # Should be dict
            "confidence": 0.8,
        }

        with pytest.raises(ValueError, match="object_value must be dict"):
            extraction_service._parse_and_validate_triple(
                raw_triple=invalid_triple,
                message=message,
            )

    @pytest.mark.asyncio
    async def test_parse_validates_confidence_range(self, extraction_service):
        """Test that confidence out of [0, 1] range is rejected."""
        from src.domain.entities.chat_message import ChatMessage

        message = ChatMessage(
            event_id=1,
            user_id="user_1",
            session_id=uuid4(),
            role="user",
            content="test",
            created_at=datetime.now(timezone.utc),
        )

        invalid_triple = {
            "subject_entity_id": "entity_1",
            "predicate": "test",
            "predicate_type": "attribute",
            "object_value": {"value": "test"},
            "confidence": 2.0,  # > 1.0
        }

        with pytest.raises(ValueError, match="confidence must be in"):
            extraction_service._parse_and_validate_triple(
                raw_triple=invalid_triple,
                message=message,
            )

    # ============================================================================
    # Metadata Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_extracted_triples_have_metadata(
        self, extraction_service, mock_llm_service, sample_message, sample_resolved_entities
    ):
        """Test that extracted triples include proper metadata."""
        mock_llm_service.extract_semantic_triples.return_value = [
            {
                "subject_entity_id": "company_acme_123",
                "predicate": "prefers",
                "predicate_type": "preference",
                "object_value": {"value": "test"},
                "confidence": 0.9,
                "metadata": {"extra_field": "extra_value"},
            }
        ]

        triples = await extraction_service.extract_triples(
            message=sample_message,
            resolved_entities=sample_resolved_entities,
        )

        assert len(triples) == 1
        triple = triples[0]

        # Check standard metadata fields
        assert "source_event_id" in triple.metadata
        assert triple.metadata["source_event_id"] == 123
        assert "user_id" in triple.metadata
        assert triple.metadata["user_id"] == "user_test_456"
        assert "extraction_timestamp" in triple.metadata

        # Check extra metadata is preserved
        assert "extra_field" in triple.metadata
        assert triple.metadata["extra_field"] == "extra_value"
