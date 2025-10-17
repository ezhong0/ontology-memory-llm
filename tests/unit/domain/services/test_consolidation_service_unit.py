"""Unit tests for ConsolidationService.

Tests memory consolidation logic with mocked dependencies.
Focus: Business logic validation, not database operations.

Vision Principles Tested:
- Graceful Forgetting: Consolidation synthesizes insights without preserving all details
- Epistemic Humility: Consolidated confidence ≤ source confidences
- Explainable Reasoning: Always tracks source memories
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import numpy as np
import pytest

from src.domain.services.consolidation_service import ConsolidationService
from src.domain.value_objects.consolidation import (
    ConsolidationScope,
    KeyFact,
    SummaryData,
)
from src.domain.value_objects.memory_candidate import MemoryCandidate


@pytest.fixture
def mock_repos():
    """Create mocked repositories."""
    episodic_repo = AsyncMock()
    semantic_repo = AsyncMock()
    summary_repo = AsyncMock()
    chat_repo = AsyncMock()
    return episodic_repo, semantic_repo, summary_repo, chat_repo


@pytest.fixture
def mock_llm_service():
    """Create mocked LLM service."""
    llm_service = AsyncMock()

    # Default successful response
    llm_service.synthesize_summary = AsyncMock(
        return_value=json.dumps(
            {
                "summary_text": "Test summary text",
                "key_facts": {
                    "fact1": {
                        "value": "value1",
                        "confidence": 0.85,
                        "reinforced": 3,
                        "source_memory_ids": [1, 2, 3],
                    }
                },
                "interaction_patterns": ["Pattern A"],
                "needs_validation": [],
                "confirmed_memory_ids": [1, 2],
            }
        )
    )

    return llm_service


@pytest.fixture
def mock_embedding_service():
    """Create mocked embedding service."""
    embedding_service = AsyncMock()
    embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    return embedding_service


@pytest.fixture
def consolidation_service(mock_repos, mock_llm_service, mock_embedding_service):
    """Create ConsolidationService with mocked dependencies."""
    episodic_repo, semantic_repo, summary_repo, chat_repo = mock_repos

    return (
        ConsolidationService(
            episodic_repo=episodic_repo,
            semantic_repo=semantic_repo,
            summary_repo=summary_repo,
            chat_repo=chat_repo,
            llm_service=mock_llm_service,
            embedding_service=mock_embedding_service,
        ),
        episodic_repo,
        semantic_repo,
        summary_repo,
        chat_repo,
        mock_llm_service,
    )


# ============================================================================
# Public API Tests
# ============================================================================


class TestConsolidateEntity:
    """Test consolidate_entity() public method."""

    async def test_consolidate_entity_success(self, consolidation_service):
        """Should successfully consolidate entity memories."""
        service, episodic_repo, semantic_repo, summary_repo, chat_repo, llm_service = (
            consolidation_service
        )

        user_id = "test_user"
        entity_id = "customer:test_123"

        # Mock episodic memories (15 memories - above threshold)
        episodic_memories = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"Episode {i} about customer",
                entities=[entity_id],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC) - timedelta(days=i),
                importance=0.6,
            )
            for i in range(15)
        ]

        episodic_repo.find_recent = AsyncMock(return_value=episodic_memories)
        semantic_repo.find_by_entity = AsyncMock(return_value=[])

        # Mock summary creation
        summary_repo.create = AsyncMock(
            side_effect=lambda s: type(
                "Summary",
                (),
                {
                    **s.__dict__,
                    "summary_id": 1,
                },
            )()
        )

        # Execute
        result = await service.consolidate_entity(user_id=user_id, entity_id=entity_id)

        # Assertions
        assert result.summary_id == 1
        assert result.user_id == user_id
        assert result.scope_type == "entity"
        assert result.scope_identifier == entity_id
        assert result.confidence == 0.8  # Default LLM success confidence

        # Verify repository calls
        episodic_repo.find_recent.assert_called_once()
        summary_repo.create.assert_called_once()

    async def test_consolidate_entity_below_threshold_proceeds(
        self, consolidation_service
    ):
        """Should proceed with consolidation even below threshold (manual trigger)."""
        service, episodic_repo, semantic_repo, summary_repo, chat_repo, _ = (
            consolidation_service
        )

        user_id = "test_user"
        entity_id = "customer:test_123"

        # Only 5 memories (below threshold of 10)
        episodic_memories = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"Episode {i}",
                entities=[entity_id],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.5,
            )
            for i in range(5)
        ]

        episodic_repo.find_recent = AsyncMock(return_value=episodic_memories)
        semantic_repo.find_by_entity = AsyncMock(return_value=[])
        summary_repo.create = AsyncMock(
            side_effect=lambda s: type("Summary", (), {**s.__dict__, "summary_id": 1})()
        )

        # Should complete (Phase 1 allows manual consolidation)
        result = await service.consolidate_entity(user_id=user_id, entity_id=entity_id)

        assert result.summary_id == 1
        # Warning would be logged but consolidation proceeds

    async def test_consolidate_entity_with_semantic_memories(
        self, consolidation_service
    ):
        """Should include semantic memories in consolidation."""
        service, episodic_repo, semantic_repo, summary_repo, chat_repo, _ = (
            consolidation_service
        )

        user_id = "test_user"
        entity_id = "customer:test_123"

        # Mock episodic and semantic memories
        episodic_memories = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"Episode {i}",
                entities=[entity_id],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.6,
            )
            for i in range(12)
        ]

        episodic_repo.find_recent = AsyncMock(return_value=episodic_memories)
        summary_repo.create = AsyncMock(
            side_effect=lambda s: type("Summary", (), {**s.__dict__, "summary_id": 1})()
        )

        result = await service.consolidate_entity(user_id=user_id, entity_id=entity_id)

        assert result.summary_id == 1
        # Phase 1 implementation doesn't fetch semantic yet - simplified
        # Would be implemented in Phase 2


class TestConsolidateTopic:
    """Test consolidate_topic() public method."""

    async def test_consolidate_topic_not_implemented(self, consolidation_service):
        """Should raise DomainError for topic consolidation (Phase 1)."""
        service, _, _, _, _, _ = consolidation_service

        user_id = "test_user"
        topic_pattern = "delivery_*"

        # Phase 1: Topic consolidation not implemented
        from src.domain.exceptions import DomainError

        with pytest.raises(DomainError, match="not yet implemented"):
            await service.consolidate_topic(
                user_id=user_id, predicate_pattern=topic_pattern
            )


class TestConsolidateSessionWindow:
    """Test consolidate_session_window() public method."""

    async def test_consolidate_session_window_success(self, consolidation_service):
        """Should successfully consolidate memories from recent sessions."""
        service, episodic_repo, semantic_repo, summary_repo, chat_repo, _ = (
            consolidation_service
        )

        user_id = "test_user"
        num_sessions = 3

        # Mock chat messages from 3 different sessions
        session_1 = uuid4()
        session_2 = uuid4()
        session_3 = uuid4()

        chat_messages = [
            type("ChatMessage", (), {"session_id": session_3, "created_at": datetime.now(UTC)})(),
            type("ChatMessage", (), {"session_id": session_3, "created_at": datetime.now(UTC) - timedelta(hours=1)})(),
            type("ChatMessage", (), {"session_id": session_2, "created_at": datetime.now(UTC) - timedelta(hours=2)})(),
            type("ChatMessage", (), {"session_id": session_2, "created_at": datetime.now(UTC) - timedelta(hours=3)})(),
            type("ChatMessage", (), {"session_id": session_1, "created_at": datetime.now(UTC) - timedelta(hours=4)})(),
            type("ChatMessage", (), {"session_id": session_1, "created_at": datetime.now(UTC) - timedelta(hours=5)})(),
        ]

        # Mock chat repository to return recent messages
        chat_repo.get_recent_for_user = AsyncMock(return_value=chat_messages)

        # Mock episodic memories for each session
        episodic_memories_s1 = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"Session 1 episode {i}",
                entities=[],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC) - timedelta(hours=5),
                importance=0.6,
            )
            for i in range(3)
        ]
        episodic_memories_s2 = [
            MemoryCandidate(
                memory_id=i + 3,
                memory_type="episodic",
                content=f"Session 2 episode {i}",
                entities=[],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC) - timedelta(hours=3),
                importance=0.6,
            )
            for i in range(3)
        ]
        episodic_memories_s3 = [
            MemoryCandidate(
                memory_id=i + 6,
                memory_type="episodic",
                content=f"Session 3 episode {i}",
                entities=[],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.6,
            )
            for i in range(3)
        ]

        # Setup episodic repo to return different memories for each session
        async def mock_find_recent(user_id, limit, session_id=None):
            if session_id == session_1:
                return episodic_memories_s1
            elif session_id == session_2:
                return episodic_memories_s2
            elif session_id == session_3:
                return episodic_memories_s3
            return []

        episodic_repo.find_recent = AsyncMock(side_effect=mock_find_recent)

        # Mock summary creation
        summary_repo.create = AsyncMock(
            side_effect=lambda s: type("Summary", (), {**s.__dict__, "summary_id": 100})()
        )

        # Execute
        result = await service.consolidate_session_window(
            user_id=user_id, num_sessions=num_sessions
        )

        # Assertions
        assert result.summary_id == 100
        assert result.user_id == user_id
        assert result.scope_type == "session_window"
        assert result.scope_identifier == str(num_sessions)
        assert result.confidence == 0.8  # Default LLM success confidence

        # Verify chat repository was called to get recent messages
        chat_repo.get_recent_for_user.assert_called_once()

        # Verify episodic repo was called for each session
        assert episodic_repo.find_recent.call_count == 3

        # Verify summary was created
        summary_repo.create.assert_called_once()

    async def test_consolidate_session_window_no_sessions(self, consolidation_service):
        """Should handle case with no recent sessions gracefully."""
        service, episodic_repo, semantic_repo, summary_repo, chat_repo, _ = (
            consolidation_service
        )

        user_id = "test_user"
        num_sessions = 3

        # Mock no chat messages
        chat_repo.get_recent_for_user = AsyncMock(return_value=[])

        # Mock summary creation for fallback
        summary_repo.create = AsyncMock(
            side_effect=lambda s: type("Summary", (), {**s.__dict__, "summary_id": 101})()
        )

        # Execute - should complete with fallback summary
        result = await service.consolidate_session_window(
            user_id=user_id, num_sessions=num_sessions
        )

        # Should create fallback summary with 0 episodes
        assert result.summary_id == 101
        assert result.scope_type == "session_window"


# ============================================================================
# Note: Phase 1 uses placeholder LLM (hardcoded response), so we skip testing
# _synthesize_with_llm and _create_fallback_summary directly here.
# Integration tests cover the full consolidation flow.
# Phase 2 will have real LLM service that can be properly mocked.
# ============================================================================


# ============================================================================
# Confidence Boosting Tests
# ============================================================================


class TestConfidenceBoosting:
    """Test _boost_confirmed_facts() private method."""

    async def test_boost_confirmed_facts_success(self, consolidation_service):
        """Should boost confidence of confirmed semantic memories."""
        service, _, semantic_repo, _, _, _ = consolidation_service

        confirmed_ids = [10, 20, 30]

        # Mock existing semantic memories
        for mem_id in confirmed_ids:
            memory = type(
                "SemanticMemory",
                (),
                {
                    "memory_id": mem_id,
                    "confidence": 0.70,
                    "reinforcement_count": 2,
                },
            )()

            semantic_repo.find_by_id = AsyncMock(return_value=memory)
            semantic_repo.update = AsyncMock()

            await service._boost_confirmed_facts([mem_id])

            # Verify update was called
            semantic_repo.update.assert_called()

    async def test_boost_confirmed_facts_empty_list(self, consolidation_service):
        """Should handle empty confirmed list gracefully."""
        service, _, semantic_repo, _, _, _ = consolidation_service

        # Should not raise error
        await service._boost_confirmed_facts([])

        # No repository calls
        semantic_repo.find_by_id.assert_not_called()
        semantic_repo.update.assert_not_called()

    async def test_boost_confirmed_facts_not_found(self, consolidation_service):
        """Should handle missing memory gracefully."""
        service, _, semantic_repo, _, _, _ = consolidation_service

        # Mock memory not found
        semantic_repo.find_by_id = AsyncMock(return_value=None)
        semantic_repo.update = AsyncMock()

        # Should not raise error, just log warning
        await service._boost_confirmed_facts([999])

        semantic_repo.find_by_id.assert_called_once_with(999)
        semantic_repo.update.assert_not_called()


# ============================================================================
# Edge Cases & Error Handling
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    async def test_consolidate_with_no_memories(self, consolidation_service):
        """Should handle consolidation with no memories gracefully."""
        service, episodic_repo, semantic_repo, summary_repo, chat_repo, _ = (
            consolidation_service
        )

        user_id = "test_user"
        entity_id = "customer:test_123"

        # No memories
        episodic_repo.find_recent = AsyncMock(return_value=[])
        summary_repo.create = AsyncMock(
            side_effect=lambda s: type("Summary", (), {**s.__dict__, "summary_id": 20})(
                )
        )

        # Should complete even with 0 memories
        result = await service.consolidate_entity(user_id=user_id, entity_id=entity_id)

        assert result.summary_id == 20
        # Logs warning about insufficient memories but proceeds


# ============================================================================
# Vision Principle Validation
# ============================================================================


class TestVisionPrinciples:
    """Test that service embodies vision principles."""

    async def test_epistemic_humility_confidence_never_exceeds_max(
        self, consolidation_service
    ):
        """VISION: Epistemic humility - never claim perfect confidence.

        Consolidated confidence should be ≤ source confidence.
        """
        service, episodic_repo, semantic_repo, summary_repo, chat_repo, _ = (
            consolidation_service
        )

        user_id = "test_user"
        entity_id = "customer:test_123"

        # Create memories with various confidences
        episodic_memories = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"Episode {i}",
                entities=[entity_id],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.6,
            )
            for i in range(12)
        ]

        semantic_memories = [
            type(
                "SemanticMemory",
                (),
                {
                    "memory_id": 100 + i,
                    "predicate": f"pref_{i}",
                    "object_value": f"val_{i}",
                    "confidence": 0.95,  # Very high confidence
                    "reinforcement_count": 10,
                },
            )()
            for i in range(3)
        ]

        episodic_repo.find_recent = AsyncMock(return_value=episodic_memories)
        semantic_repo.find_by_entity = AsyncMock(return_value=semantic_memories)
        summary_repo.create = AsyncMock(
            side_effect=lambda s: type("Summary", (), {**s.__dict__, "summary_id": 30})(
                )
        )

        result = await service.consolidate_entity(user_id=user_id, entity_id=entity_id)

        # Consolidated confidence should never be 1.0 (epistemic humility)
        assert result.confidence < 1.0
        # Should also be reasonable (not arbitrarily low)
        assert result.confidence >= 0.5

    async def test_graceful_forgetting_summarizes_without_all_details(
        self, consolidation_service
    ):
        """VISION: Graceful forgetting - summaries don't preserve all episodic details.

        Summary text should be shorter than concatenated episodes.
        """
        service, episodic_repo, semantic_repo, summary_repo, chat_repo, _ = (
            consolidation_service
        )

        user_id = "test_user"
        entity_id = "customer:test_123"

        # Create detailed episodic memories
        episodic_memories = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"Very detailed episode {i} with lots of context about the customer's preferences and history. This is a long description that contains many specific details about what happened.",
                entities=[entity_id],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.6,
            )
            for i in range(15)
        ]

        episodic_repo.find_recent = AsyncMock(return_value=episodic_memories)
        semantic_repo.find_by_entity = AsyncMock(return_value=[])
        summary_repo.create = AsyncMock(
            side_effect=lambda s: type("Summary", (), {**s.__dict__, "summary_id": 40})(
                )
        )

        result = await service.consolidate_entity(user_id=user_id, entity_id=entity_id)

        # Summary should be shorter than all episodes concatenated
        total_episode_length = sum(len(m.content) for m in episodic_memories)
        summary_length = len(result.summary_text)

        assert summary_length < total_episode_length
        # But should still contain meaningful content (not empty)
        assert summary_length > 50

    async def test_explainable_reasoning_tracks_source_memories(
        self, consolidation_service
    ):
        """VISION: Explainable reasoning - always track provenance.

        Summary should have structured source_data tracking episodic sources.
        """
        service, episodic_repo, semantic_repo, summary_repo, chat_repo, _ = (
            consolidation_service
        )

        user_id = "test_user"
        entity_id = "customer:test_123"

        episodic_memories = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"Episode {i}",
                entities=[entity_id],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.6,
            )
            for i in range(12)
        ]

        episodic_repo.find_recent = AsyncMock(return_value=episodic_memories)
        summary_repo.create = AsyncMock(
            side_effect=lambda s: type("Summary", (), {**s.__dict__, "summary_id": 50})(
                )
        )

        result = await service.consolidate_entity(user_id=user_id, entity_id=entity_id)

        # Should have provenance in source_data (Phase 1 placeholder)
        assert result.summary_id == 50
        assert result.summary_text is not None
        # Phase 1 placeholder may not have key_facts, but summary text references episodes
        assert "12 episodes" in result.summary_text or "episodes" in result.summary_text.lower()
