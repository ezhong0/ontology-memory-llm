"""Unit tests for EntityResolutionService.

Tests all 5 stages of the hybrid entity resolution algorithm:
1. Exact match on canonical name
2. User alias lookup
3. Fuzzy match using pg_trgm
4. Coreference resolution via LLM
5. Domain database lookup
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.domain.entities import CanonicalEntity, EntityAlias
from src.domain.services import EntityResolutionService
from src.domain.value_objects import (
    ConversationContext,
    EntityMention,
    EntityReference,
    ResolutionMethod,
    ResolutionResult,
)


@pytest.mark.unit
class TestEntityResolutionService:
    """Test EntityResolutionService with all 5 stages."""

    @pytest.fixture
    def mock_entity_repo(self):
        """Mock entity repository."""
        repo = AsyncMock()
        repo.find_by_canonical_name = AsyncMock(return_value=None)
        repo.find_by_alias = AsyncMock(return_value=None)
        repo.fuzzy_search = AsyncMock(return_value=[])
        repo.find_by_entity_id = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service."""
        llm = AsyncMock()
        llm.resolve_coreference = AsyncMock(
            return_value=ResolutionResult.failed("test", "No coreference")
        )
        return llm

    @pytest.fixture
    def resolution_service(self, mock_entity_repo, mock_llm_service):
        """Create EntityResolutionService with mocks."""
        return EntityResolutionService(
            entity_repository=mock_entity_repo,
            llm_service=mock_llm_service,
        )

    @pytest.fixture
    def sample_entity(self):
        """Sample canonical entity for testing."""
        return CanonicalEntity(
            entity_id="company_acme_123",
            entity_type="company",
            canonical_name="Acme Corporation",
            external_ref=EntityReference(
                table="companies",
                primary_key="company_id",
                primary_value="acme_123",
                display_name="Acme Corporation",
                properties={"industry": "Technology"},
            ),
            properties={"tier": "enterprise"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_mention(self):
        """Sample entity mention."""
        return EntityMention(
            text="Acme Corp",
            position=10,
            context_before="I spoke with ",
            context_after=" about pricing",
            is_pronoun=False,
            sentence="I spoke with Acme Corp about pricing.",
        )

    @pytest.fixture
    def sample_context(self):
        """Sample conversation context."""
        return ConversationContext(
            user_id="test-user-123",
            session_id=uuid4(),
            recent_messages=["Hello", "How are you?"],
            recent_entities=[],
            current_message="I spoke with Acme Corp about pricing.",
        )

    # ============================================================================
    # Stage 1: Exact Match Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_stage1_exact_match_success(
        self, resolution_service, mock_entity_repo, sample_entity, sample_mention, sample_context
    ):
        """Test Stage 1: Exact match returns entity with high confidence."""
        # Setup: Repository returns exact match
        mock_entity_repo.find_by_canonical_name.return_value = sample_entity

        # Execute
        result = await resolution_service.resolve_entity(sample_mention, sample_context)

        # Assert
        assert result.is_successful
        assert result.entity_id == "company_acme_123"
        assert result.canonical_name == "Acme Corporation"
        assert result.method == ResolutionMethod.EXACT_MATCH
        assert result.confidence == resolution_service.high_confidence
        mock_entity_repo.find_by_canonical_name.assert_called_once_with("Acme Corp")

    @pytest.mark.asyncio
    async def test_stage1_exact_match_case_insensitive(
        self, resolution_service, mock_entity_repo, sample_entity, sample_context
    ):
        """Test Stage 1: Exact match is case-insensitive."""
        mention = EntityMention(
            text="acme corporation",  # lowercase
            position=0,
            context_before="",
            context_after="",
            is_pronoun=False,
            sentence="acme corporation",
        )

        mock_entity_repo.find_by_canonical_name.return_value = sample_entity

        result = await resolution_service.resolve_entity(mention, sample_context)

        assert result.is_successful
        assert result.entity_id == "company_acme_123"

    # ============================================================================
    # Stage 2: User Alias Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_stage2_alias_match_success(
        self, resolution_service, mock_entity_repo, sample_entity, sample_mention, sample_context
    ):
        """Test Stage 2: User alias match works when exact match fails."""
        # Setup: No exact match, but alias matches
        mock_entity_repo.find_by_canonical_name.return_value = None
        mock_entity_repo.find_by_alias.return_value = sample_entity

        # Execute
        result = await resolution_service.resolve_entity(sample_mention, sample_context)

        # Assert
        assert result.is_successful
        assert result.entity_id == "company_acme_123"
        assert result.method == ResolutionMethod.USER_ALIAS
        assert result.confidence == resolution_service.medium_confidence
        mock_entity_repo.find_by_alias.assert_called_once_with(
            "Acme Corp", "test-user-123"
        )

    @pytest.mark.asyncio
    async def test_stage2_alias_lookup_with_user_id(
        self, resolution_service, mock_entity_repo, sample_entity, sample_mention
    ):
        """Test Stage 2: Alias lookup uses user_id from context."""
        context = ConversationContext(
            user_id="user-456",
            session_id=uuid4(),
            recent_messages=[],
            recent_entities=[],
            current_message="test",
        )

        mock_entity_repo.find_by_canonical_name.return_value = None
        mock_entity_repo.find_by_alias.return_value = sample_entity

        result = await resolution_service.resolve_entity(sample_mention, context)

        assert result.is_successful
        mock_entity_repo.find_by_alias.assert_called_once_with("Acme Corp", "user-456")

    # ============================================================================
    # Stage 3: Fuzzy Match Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_stage3_fuzzy_match_success(
        self, resolution_service, mock_entity_repo, sample_entity, sample_mention, sample_context
    ):
        """Test Stage 3: Fuzzy match works for typos."""
        # Setup: No exact match or alias, but fuzzy match succeeds
        mock_entity_repo.find_by_canonical_name.return_value = None
        mock_entity_repo.find_by_alias.return_value = None
        mock_entity_repo.fuzzy_search.return_value = [
            (sample_entity, 0.75)  # (entity, similarity_score)
        ]

        # Execute
        result = await resolution_service.resolve_entity(sample_mention, sample_context)

        # Assert
        assert result.is_successful
        assert result.entity_id == "company_acme_123"
        assert result.method == ResolutionMethod.FUZZY_MATCH
        assert result.confidence <= resolution_service.medium_confidence
        mock_entity_repo.fuzzy_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_stage3_fuzzy_match_skipped_for_pronouns(
        self, resolution_service, mock_entity_repo, sample_context
    ):
        """Test Stage 3: Fuzzy match is skipped for pronouns."""
        pronoun_mention = EntityMention(
            text="they",
            position=0,
            context_before="",
            context_after=" said yes",
            is_pronoun=True,
            sentence="They said yes.",
        )

        mock_entity_repo.find_by_canonical_name.return_value = None
        mock_entity_repo.find_by_alias.return_value = None

        result = await resolution_service.resolve_entity(pronoun_mention, sample_context)

        # Fuzzy search should NOT be called for pronouns
        mock_entity_repo.fuzzy_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_stage3_fuzzy_match_ambiguity_detection(
        self, resolution_service, mock_entity_repo, sample_mention, sample_context
    ):
        """Test Stage 3: Ambiguity error when multiple entities have similar scores."""
        from src.domain.exceptions import AmbiguousEntityError

        entity1 = CanonicalEntity(
            entity_id="company_acme_123",
            entity_type="company",
            canonical_name="Acme Corporation",
            external_ref=EntityReference(
                table="companies", primary_key="id", primary_value="123",
                display_name="Acme Corporation", properties=None
            ),
            properties={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        entity2 = CanonicalEntity(
            entity_id="company_acme_456",
            entity_type="company",
            canonical_name="Acme Industries",
            external_ref=EntityReference(
                table="companies", primary_key="id", primary_value="456",
                display_name="Acme Industries", properties=None
            ),
            properties={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Setup: Two entities with very similar scores (ambiguous)
        mock_entity_repo.find_by_canonical_name.return_value = None
        mock_entity_repo.find_by_alias.return_value = None
        mock_entity_repo.fuzzy_search.return_value = [
            (entity1, 0.75),
            (entity2, 0.73),  # Diff = 0.02 < AMBIGUITY_DIFF_THRESHOLD (0.1)
        ]

        # Execute & Assert
        with pytest.raises(AmbiguousEntityError) as exc_info:
            await resolution_service.resolve_entity(sample_mention, sample_context)

        assert exc_info.value.mention_text == "Acme Corp"
        assert len(exc_info.value.candidates) >= 2

    # ============================================================================
    # Stage 4: Coreference Resolution Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_stage4_coreference_resolution_success(
        self, resolution_service, mock_llm_service, sample_entity
    ):
        """Test Stage 4: Coreference resolution via LLM."""
        pronoun_mention = EntityMention(
            text="they",
            position=0,
            context_before="",
            context_after=" confirmed the order",
            is_pronoun=True,
            sentence="They confirmed the order.",
        )

        context = ConversationContext(
            user_id="test-user",
            session_id=uuid4(),
            recent_messages=["I spoke with Acme Corp."],
            recent_entities=[("company_acme_123", "Acme Corporation")],
            current_message="They confirmed the order.",
        )

        # Mock LLM service returns successful resolution
        mock_llm_service.resolve_coreference.return_value = ResolutionResult(
            entity_id="company_acme_123",
            confidence=0.85,
            method=ResolutionMethod.COREFERENCE,
            mention_text="they",
            canonical_name="Acme Corporation",
            metadata={"resolved_by": "llm"},
        )

        result = await resolution_service.resolve_entity(pronoun_mention, context)

        assert result.is_successful
        assert result.entity_id == "company_acme_123"
        assert result.method == ResolutionMethod.COREFERENCE
        mock_llm_service.resolve_coreference.assert_called_once()

    @pytest.mark.asyncio
    async def test_stage4_coreference_skipped_when_no_recent_entities(
        self, resolution_service, mock_llm_service
    ):
        """Test Stage 4: Coreference is skipped when no recent entities in context."""
        pronoun_mention = EntityMention(
            text="they",
            position=0,
            context_before="",
            context_after="",
            is_pronoun=True,
            sentence="They are good.",
        )

        context = ConversationContext(
            user_id="test-user",
            session_id=uuid4(),
            recent_messages=[],
            recent_entities=[],  # No recent entities
            current_message="They are good.",
        )

        result = await resolution_service.resolve_entity(pronoun_mention, context)

        # LLM should not be called when no entities in context
        mock_llm_service.resolve_coreference.assert_not_called()
        assert not result.is_successful

    # ============================================================================
    # Stage 5: Domain DB Lookup Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_stage5_domain_db_not_implemented(
        self, resolution_service, mock_entity_repo, sample_mention, sample_context
    ):
        """Test Stage 5: Domain DB lookup returns failed result (not implemented)."""
        # Setup: All previous stages fail
        mock_entity_repo.find_by_canonical_name.return_value = None
        mock_entity_repo.find_by_alias.return_value = None
        mock_entity_repo.fuzzy_search.return_value = []

        result = await resolution_service.resolve_entity(sample_mention, sample_context)

        # Stage 5 is not implemented in Phase 1A
        assert not result.is_successful
        assert result.method == ResolutionMethod.FAILED

    # ============================================================================
    # Integration Tests (Multiple Stages)
    # ============================================================================

    @pytest.mark.asyncio
    async def test_resolution_pipeline_order(
        self, resolution_service, mock_entity_repo, sample_entity, sample_mention, sample_context
    ):
        """Test that stages execute in correct order (1, 2, 3, skip 4, 5)."""
        # Setup: Stage 2 (alias) succeeds
        mock_entity_repo.find_by_canonical_name.return_value = None  # Stage 1 fails
        mock_entity_repo.find_by_alias.return_value = sample_entity  # Stage 2 succeeds

        result = await resolution_service.resolve_entity(sample_mention, sample_context)

        # Assert: Stage 1 was tried, Stage 2 succeeded, Stage 3 not called
        assert result.method == ResolutionMethod.USER_ALIAS
        mock_entity_repo.find_by_canonical_name.assert_called_once()
        mock_entity_repo.find_by_alias.assert_called_once()
        mock_entity_repo.fuzzy_search.assert_not_called()  # Stopped at Stage 2

    @pytest.mark.asyncio
    async def test_failed_resolution_returns_failed_result(
        self, resolution_service, mock_entity_repo, sample_mention, sample_context
    ):
        """Test that failed resolution returns appropriate result."""
        # Setup: All stages fail
        mock_entity_repo.find_by_canonical_name.return_value = None
        mock_entity_repo.find_by_alias.return_value = None
        mock_entity_repo.fuzzy_search.return_value = []

        result = await resolution_service.resolve_entity(sample_mention, sample_context)

        assert not result.is_successful
        assert result.method == ResolutionMethod.FAILED
        assert "No matching entity" in result.metadata.get("reason", "")

    # ============================================================================
    # Alias Learning Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_learn_alias_creates_new_alias(
        self, resolution_service, mock_entity_repo, sample_entity
    ):
        """Test that learn_alias creates a new alias."""
        mock_entity_repo.find_by_entity_id.return_value = sample_entity
        mock_entity_repo.find_by_alias.return_value = None
        mock_entity_repo.get_aliases.return_value = []

        created_alias = EntityAlias(
            alias_id=1,
            canonical_entity_id="company_acme_123",
            alias_text="ACME",
            alias_source="user_stated",
            confidence=0.9,
            user_id="test-user",
        )
        mock_entity_repo.create_alias.return_value = created_alias

        result = await resolution_service.learn_alias(
            entity_id="company_acme_123",
            alias_text="ACME",
            user_id="test-user",
            source="user_stated",
        )

        assert result.alias_text == "ACME"
        assert result.confidence == 0.9
        mock_entity_repo.create_alias.assert_called_once()

    @pytest.mark.asyncio
    async def test_learn_alias_validates_entity_exists(
        self, resolution_service, mock_entity_repo
    ):
        """Test that learn_alias fails if entity doesn't exist."""
        mock_entity_repo.find_by_entity_id.return_value = None

        with pytest.raises(ValueError, match="Entity .* not found"):
            await resolution_service.learn_alias(
                entity_id="nonexistent_entity",
                alias_text="Test",
                user_id="test-user",
            )
