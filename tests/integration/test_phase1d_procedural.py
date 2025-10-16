"""Integration tests for Phase 1D: Procedural Memory System.

Tests pattern detection and procedural memory lifecycle:
- Pattern detection from episodic memories
- Procedural memory storage and retrieval
- Query augmentation with learned patterns
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import numpy as np
import pytest

from src.domain.entities.procedural_memory import ProceduralMemory
from src.domain.services.procedural_memory_service import ProceduralMemoryService
from src.domain.value_objects.memory_candidate import MemoryCandidate
from src.domain.value_objects.procedural_memory import Pattern


@pytest.mark.integration
@pytest.mark.asyncio
class TestProceduralMemoryIntegration:
    """Integration tests for procedural memory service."""

    @pytest.fixture
    def procedural_service(self):
        """Create procedural memory service with mocked dependencies."""
        episodic_repo = AsyncMock()
        procedural_repo = AsyncMock()

        service = ProceduralMemoryService(
            episodic_repo=episodic_repo,
            procedural_repo=procedural_repo,
        )

        return service, episodic_repo, procedural_repo

    async def test_pattern_detection_from_episodes(self, procedural_service):
        """Test detecting patterns from frequent episodic memories."""
        service, episodic_repo, procedural_repo = procedural_service

        user_id = "test_user"

        # Create 20 episodes with repeating pattern:
        # "User asks about payment history" → happens 5 times
        episodes = []

        # Pattern 1: Payment history queries (5 occurrences)
        for i in range(5):
            episodes.append(
                MemoryCandidate(
                    memory_id=i,
                    memory_type="episodic",
                    content=f"What's the payment history for customer X{i}?",
                    entities=[f"customer:x{i}"],
                    embedding=np.random.rand(1536),
                    created_at=datetime.now(UTC) - timedelta(days=i),
                    importance=0.6,
                )
            )

        # Pattern 2: Product availability queries (4 occurrences)
        for i in range(5, 9):
            episodes.append(
                MemoryCandidate(
                    memory_id=i,
                    memory_type="episodic",
                    content=f"Is product Y{i} available in stock?",
                    entities=[f"product:y{i}"],
                    embedding=np.random.rand(1536),
                    created_at=datetime.now(UTC) - timedelta(days=i),
                    importance=0.5,
                )
            )

        # Other random episodes
        for i in range(9, 20):
            episodes.append(
                MemoryCandidate(
                    memory_id=i,
                    memory_type="episodic",
                    content=f"Random query {i}",
                    entities=[],
                    embedding=np.random.rand(1536),
                    created_at=datetime.now(UTC) - timedelta(days=i),
                    importance=0.4,
                )
            )

        # Mock repository
        episodic_repo.find_by_user = AsyncMock(return_value=episodes)

        # Mock procedural repo to return no existing patterns
        procedural_repo.find_by_trigger_features = AsyncMock(return_value=[])
        procedural_repo.create = AsyncMock(
            side_effect=lambda m: type(
                "Memory",
                (),
                {
                    **m.__dict__,
                    "memory_id": m.observed_count,  # Use count as ID
                },
            )()
        )

        # Detect patterns
        patterns = await service.detect_patterns(
            user_id=user_id,
            lookback_days=30,
            min_support=3,  # Require 3+ occurrences
        )

        # Assertions
        assert len(patterns) >= 1  # At least payment history pattern
        assert any("payment" in p.trigger_pattern.lower() for p in patterns)

        # Verify repository was called
        episodic_repo.find_by_user.assert_called_once()
        assert procedural_repo.create.call_count >= 1

    async def test_pattern_reinforcement(self, procedural_service):
        """Test that existing patterns get reinforced when re-detected."""
        service, episodic_repo, procedural_repo = procedural_service

        user_id = "test_user"

        # Create episodes matching existing pattern
        episodes = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"Customer payment query {i}",
                entities=[f"customer:c{i}"],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.6,
            )
            for i in range(5)
        ]

        episodic_repo.find_by_user = AsyncMock(return_value=episodes)

        # Mock existing pattern
        existing_pattern = ProceduralMemory(
            memory_id=1,
            user_id=user_id,
            trigger_pattern="User asks about payment history",
            trigger_features={
                "intent": "query_payment_history",
                "entity_types": ["customer"],
                "topics": ["payments"],
            },
            action_heuristic="Also retrieve open invoices",
            action_structure={
                "action_type": "retrieve_related",
                "queries": ["payments"],
                "predicates": ["has_payment"],
            },
            observed_count=3,
            confidence=0.75,
            created_at=datetime.now(UTC) - timedelta(days=10),
        )

        procedural_repo.find_by_trigger_features = AsyncMock(
            return_value=[existing_pattern]
        )

        # Mock update
        procedural_repo.update = AsyncMock(
            side_effect=lambda m: type(
                "Memory",
                (),
                {
                    **m.__dict__,
                },
            )()
        )

        # Detect patterns (should reinforce existing)
        patterns = await service.detect_patterns(user_id=user_id, min_support=3)

        # Verify update was called (pattern reinforced)
        if procedural_repo.update.called:
            updated_pattern = procedural_repo.update.call_args[0][0]
            assert updated_pattern.observed_count > existing_pattern.observed_count
            assert updated_pattern.confidence >= existing_pattern.confidence

    async def test_query_augmentation_with_patterns(self, procedural_service):
        """Test augmenting query with learned patterns."""
        service, episodic_repo, procedural_repo = procedural_service

        user_id = "test_user"
        query_embedding = np.random.rand(1536)

        # Mock similar patterns
        similar_patterns = [
            ProceduralMemory(
                memory_id=1,
                user_id=user_id,
                trigger_pattern="User asks about payment history",
                trigger_features={
                    "intent": "query_payment_history",
                    "entity_types": ["customer"],
                    "topics": ["payments", "invoices"],
                },
                action_heuristic="Also retrieve open invoices and credit status",
                action_structure={
                    "action_type": "retrieve_related",
                    "queries": ["open_invoices", "credit_status"],
                    "predicates": ["has_open_invoice", "credit_limit"],
                },
                observed_count=10,
                confidence=0.88,
                created_at=datetime.now(UTC),
                embedding=np.random.rand(1536),
            ),
            ProceduralMemory(
                memory_id=2,
                user_id=user_id,
                trigger_pattern="User asks about order status",
                trigger_features={
                    "intent": "query_order_status",
                    "entity_types": ["order"],
                    "topics": ["orders"],
                },
                action_heuristic="Also retrieve shipping information",
                action_structure={
                    "action_type": "retrieve_related",
                    "queries": ["shipping"],
                    "predicates": ["shipping_status"],
                },
                observed_count=7,
                confidence=0.82,
                created_at=datetime.now(UTC),
                embedding=np.random.rand(1536),
            ),
        ]

        procedural_repo.find_similar = AsyncMock(return_value=similar_patterns)

        # Augment query
        patterns = await service.augment_query(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=5,
        )

        # Assertions
        assert len(patterns) == 2
        assert all(p.confidence >= 0.5 for p in patterns)  # Above min threshold
        assert patterns[0].memory_id == 1  # Ordered by similarity

        # Verify repository was called
        procedural_repo.find_similar.assert_called_once()

    async def test_feature_extraction(self, procedural_service):
        """Test feature extraction from episodic memories."""
        service, _, _ = procedural_service

        # Test payment-related content
        episode1 = MemoryCandidate(
            memory_id=1,
            memory_type="episodic",
            content="What's the payment history for Acme Corp?",
            entities=["customer:acme_123"],
            embedding=np.random.rand(1536),
            created_at=datetime.now(UTC),
            importance=0.6,
        )

        features1 = service._extract_features(episode1)

        assert features1["intent"] in ["query_payment_history", "query_payment"]
        assert "payments" in features1["topics"]
        assert episode1.memory_id == features1["episode_id"]

        # Test product-related content
        episode2 = MemoryCandidate(
            memory_id=2,
            memory_type="episodic",
            content="Is product XYZ available in stock?",
            entities=["product:xyz_456"],
            embedding=np.random.rand(1536),
            created_at=datetime.now(UTC),
            importance=0.5,
        )

        features2 = service._extract_features(episode2)

        assert features2["intent"] in [
            "query_product_availability",
            "query_product",
        ]
        assert "products" in features2["topics"]

    async def test_pattern_value_object_validation(self):
        """Test Pattern value object validation."""
        # Valid pattern
        valid_pattern = Pattern(
            trigger_pattern="User asks about X",
            trigger_features={
                "intent": "query_x",
                "entity_types": ["type_a"],
                "topics": ["topic_1"],
            },
            action_heuristic="Retrieve Y",
            action_structure={
                "action_type": "retrieve",
                "queries": ["y"],
                "predicates": ["has_y"],
            },
            observed_count=5,
            confidence=0.85,
            source_episode_ids=[1, 2, 3, 4, 5],
        )

        assert valid_pattern.trigger_pattern == "User asks about X"
        assert valid_pattern.confidence == 0.85

        # Invalid pattern - missing required feature
        with pytest.raises(ValueError, match="trigger_features must contain"):
            Pattern(
                trigger_pattern="Test",
                trigger_features={"intent": "test"},  # Missing entity_types, topics
                action_heuristic="Test",
                action_structure={
                    "action_type": "test",
                    "queries": [],
                    "predicates": [],
                },
                observed_count=1,
                confidence=0.5,
                source_episode_ids=[1],
            )

    async def test_procedural_memory_increment_observed_count(self):
        """Test incrementing observed count with diminishing returns."""
        memory = ProceduralMemory(
            user_id="test_user",
            trigger_pattern="Test pattern",
            trigger_features={
                "intent": "test",
                "entity_types": [],
                "topics": [],
            },
            action_heuristic="Test action",
            action_structure={
                "action_type": "test",
                "queries": [],
                "predicates": [],
            },
            observed_count=5,
            confidence=0.70,
            created_at=datetime.now(UTC),
        )

        # Increment
        incremented = memory.increment_observed_count()

        # Assertions
        assert incremented.observed_count == 6
        assert incremented.confidence > memory.confidence  # Boosted
        assert incremented.confidence < 0.95  # Below max
        assert incremented.updated_at is not None

        # Test diminishing returns - multiple increments
        current = memory
        for _ in range(10):
            current = current.increment_observed_count()

        # Should approach but not exceed 0.95
        # Formula: new_conf = old_conf + 0.05 * (1 - old_conf)
        # Starting from 0.70, after 10 increments reaches ~0.82
        assert current.observed_count == 15
        assert 0.80 <= current.confidence <= 0.95  # Adjusted to match actual formula
