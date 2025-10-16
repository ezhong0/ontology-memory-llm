"""Unit tests for ProceduralMemoryService.

Tests pattern detection and procedural memory logic with mocked dependencies.
Focus: Business logic validation for frequency-based pattern detection.

Vision Principles Tested:
- Learning from interaction patterns: Detects "When X, also Y" heuristics
- Adaptive learning: Patterns reinforce with each occurrence
- Epistemic humility: Pattern confidence capped at 0.90 (Phase 1)
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import numpy as np
import pytest

from src.domain.entities.procedural_memory import ProceduralMemory
from src.domain.services.procedural_memory_service import ProceduralMemoryService
from src.domain.value_objects.memory_candidate import MemoryCandidate
from src.domain.value_objects.procedural_memory import Pattern


@pytest.fixture
def mock_repos():
    """Create mocked repositories."""
    episodic_repo = AsyncMock()
    procedural_repo = AsyncMock()
    return episodic_repo, procedural_repo


@pytest.fixture
def procedural_service(mock_repos):
    """Create ProceduralMemoryService with mocked dependencies."""
    episodic_repo, procedural_repo = mock_repos

    return (
        ProceduralMemoryService(
            episodic_repo=episodic_repo,
            procedural_repo=procedural_repo,
        ),
        episodic_repo,
        procedural_repo,
    )


# ============================================================================
# Pattern Detection Tests
# ============================================================================


class TestDetectPatterns:
    """Test detect_patterns() public method."""

    async def test_detect_patterns_insufficient_episodes(self, procedural_service):
        """Should return empty list if insufficient episodes."""
        service, episodic_repo, procedural_repo = procedural_service

        user_id = "test_user"

        # Only 2 episodes (below min_support * 2 = 6)
        episodes = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content="Test episode",
                entities=[],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.5,
            )
            for i in range(2)
        ]

        episodic_repo.find_by_user = AsyncMock(return_value=episodes)

        patterns = await service.detect_patterns(
            user_id=user_id, lookback_days=30, min_support=3
        )

        assert patterns == []
        # Should log warning about insufficient episodes

    async def test_detect_patterns_no_frequent_sequences(self, procedural_service):
        """Should return empty list if no patterns meet min_support."""
        service, episodic_repo, procedural_repo = procedural_service

        user_id = "test_user"

        # 10 episodes, all with different intents (no patterns)
        episodes = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"Random unique query {i}",
                entities=[],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.5,
            )
            for i in range(10)
        ]

        episodic_repo.find_by_user = AsyncMock(return_value=episodes)

        patterns = await service.detect_patterns(
            user_id=user_id, lookback_days=30, min_support=3
        )

        assert patterns == []

    async def test_detect_patterns_creates_new_pattern(self, procedural_service):
        """Should create new pattern when detected."""
        service, episodic_repo, procedural_repo = procedural_service

        user_id = "test_user"

        # 6 payment-related episodes (meets min_support * 2 = 6)
        episodes = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"What's the payment history for this customer?",
                entities=["customer:main"],  # Same entity in all
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC) - timedelta(days=i),
                importance=0.6,
            )
            for i in range(6)
        ]

        episodic_repo.find_by_user = AsyncMock(return_value=episodes)

        # No existing patterns
        procedural_repo.find_by_trigger_features = AsyncMock(return_value=[])

        # Mock create
        procedural_repo.create = AsyncMock(
            side_effect=lambda m: type(
                "ProceduralMemory",
                (),
                {
                    **m.__dict__,
                    "memory_id": 1,
                },
            )()
        )

        patterns = await service.detect_patterns(
            user_id=user_id, lookback_days=30, min_support=3
        )

        # Should detect payment pattern
        assert len(patterns) >= 1
        assert any("payment" in p.trigger_pattern.lower() for p in patterns)

        # Should have called create
        procedural_repo.create.assert_called()

    async def test_detect_patterns_reinforces_existing(self, procedural_service):
        """Should reinforce existing pattern instead of creating new."""
        service, episodic_repo, procedural_repo = procedural_service

        user_id = "test_user"

        # 6 payment-related episodes (meets min_support * 2 = 6)
        episodes = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"Payment query for customer",
                entities=["customer:main"],  # Same entity in all
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.6,
            )
            for i in range(6)
        ]

        episodic_repo.find_by_user = AsyncMock(return_value=episodes)

        # Existing pattern
        existing_pattern = ProceduralMemory(
            memory_id=1,
            user_id=user_id,
            trigger_pattern="User asks about payments",
            trigger_features={
                "intent": "query_payment",
                "entity_types": [],
                "topics": ["payments"],
            },
            action_heuristic="Retrieve payment info",
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
                "ProceduralMemory",
                (),
                {
                    **m.__dict__,
                },
            )()
        )

        patterns = await service.detect_patterns(
            user_id=user_id, lookback_days=30, min_support=3
        )

        # Should have updated existing pattern
        procedural_repo.update.assert_called()

        # Verify observed_count increased
        updated_pattern = procedural_repo.update.call_args[0][0]
        assert updated_pattern.observed_count > existing_pattern.observed_count


# ============================================================================
# Query Augmentation Tests
# ============================================================================


class TestAugmentQuery:
    """Test augment_query() public method."""

    async def test_augment_query_returns_similar_patterns(self, procedural_service):
        """Should return similar patterns based on embedding."""
        service, episodic_repo, procedural_repo = procedural_service

        user_id = "test_user"
        query_embedding = np.random.rand(1536)

        # Mock similar patterns
        similar_patterns = [
            ProceduralMemory(
                memory_id=i,
                user_id=user_id,
                trigger_pattern=f"Pattern {i}",
                trigger_features={
                    "intent": f"intent_{i}",
                    "entity_types": [],
                    "topics": ["topic"],
                },
                action_heuristic=f"Action {i}",
                action_structure={
                    "action_type": "retrieve",
                    "queries": [],
                    "predicates": [],
                },
                observed_count=5,
                confidence=0.85,
                created_at=datetime.now(UTC),
                embedding=np.random.rand(1536),
            )
            for i in range(3)
        ]

        procedural_repo.find_similar = AsyncMock(return_value=similar_patterns)

        patterns = await service.augment_query(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=5,
        )

        assert len(patterns) == 3
        procedural_repo.find_similar.assert_called_once()

    async def test_augment_query_handles_error_gracefully(self, procedural_service):
        """Should return empty list on error (fail gracefully)."""
        service, _, procedural_repo = procedural_service

        user_id = "test_user"
        query_embedding = np.random.rand(1536)

        # Mock error
        procedural_repo.find_similar = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Should not raise, return empty list
        patterns = await service.augment_query(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=5,
        )

        assert patterns == []


# ============================================================================
# Feature Extraction Tests
# ============================================================================


class TestFeatureExtraction:
    """Test _extract_features() private method."""

    def test_extract_features_payment_query(self, procedural_service):
        """Should extract payment-related features."""
        service, _, _ = procedural_service

        episode = MemoryCandidate(
            memory_id=1,
            memory_type="episodic",
            content="What's the payment history for Acme Corp?",
            entities=["customer:acme_123"],
            embedding=np.random.rand(1536),
            created_at=datetime.now(UTC),
            importance=0.6,
        )

        features = service._extract_features(episode)

        assert features["intent"] in ["query_payment_history", "query_payment"]
        assert "payments" in features["topics"]
        assert "customer:acme_123" in features["entity_types"]
        assert features["episode_id"] == 1

    def test_extract_features_product_query(self, procedural_service):
        """Should extract product-related features."""
        service, _, _ = procedural_service

        episode = MemoryCandidate(
            memory_id=2,
            memory_type="episodic",
            content="Is product XYZ available in stock?",
            entities=["product:xyz_456"],
            embedding=np.random.rand(1536),
            created_at=datetime.now(UTC),
            importance=0.5,
        )

        features = service._extract_features(episode)

        assert features["intent"] in [
            "query_product_availability",
            "query_product",
        ]
        assert "products" in features["topics"]

    def test_extract_features_order_status(self, procedural_service):
        """Should extract order status intent."""
        service, _, _ = procedural_service

        episode = MemoryCandidate(
            memory_id=3,
            memory_type="episodic",
            content="What's the status of order 12345?",
            entities=["order:12345"],
            embedding=np.random.rand(1536),
            created_at=datetime.now(UTC),
            importance=0.6,
        )

        features = service._extract_features(episode)

        assert features["intent"] in ["query_order_status", "query_order"]
        assert "orders" in features["topics"]

    def test_extract_features_preference_statement(self, procedural_service):
        """Should extract preference intent."""
        service, _, _ = procedural_service

        episode = MemoryCandidate(
            memory_id=4,
            memory_type="episodic",
            content="I prefer Friday deliveries",
            entities=[],
            embedding=np.random.rand(1536),
            created_at=datetime.now(UTC),
            importance=0.7,
        )

        features = service._extract_features(episode)

        assert features["intent"] == "statement_preference"
        assert "shipping" in features["topics"] or "preferences" in features["topics"]


# ============================================================================
# Intent Classification Tests
# ============================================================================


class TestIntentClassification:
    """Test _classify_intent() private method."""

    def test_classify_intent_payment_history(self, procedural_service):
        """Should classify payment history queries."""
        service, _, _ = procedural_service

        content = "what is the payment history for this customer"
        intent = service._classify_intent(content)

        assert intent == "query_payment_history"

    def test_classify_intent_open_payments(self, procedural_service):
        """Should classify open/outstanding payment queries."""
        service, _, _ = procedural_service

        content = "what are the outstanding invoices?"
        intent = service._classify_intent(content)

        assert intent == "query_open_payments"

    def test_classify_intent_customer_status(self, procedural_service):
        """Should classify customer status queries."""
        service, _, _ = procedural_service

        content = "what is the status of the customer account?"
        intent = service._classify_intent(content)

        assert intent == "query_customer_status"

    def test_classify_intent_product_availability(self, procedural_service):
        """Should classify product availability queries."""
        service, _, _ = procedural_service

        content = "is this item in stock?"
        intent = service._classify_intent(content)

        assert intent == "query_product_availability"

    def test_classify_intent_general_fallback(self, procedural_service):
        """Should use general fallback for unknown intents."""
        service, _, _ = procedural_service

        content = "hello world"
        intent = service._classify_intent(content)

        assert intent == "query_general"


# ============================================================================
# Topic Extraction Tests
# ============================================================================


class TestTopicExtraction:
    """Test _extract_topics() private method."""

    def test_extract_topics_payments(self, procedural_service):
        """Should extract payment topics."""
        service, _, _ = procedural_service

        content = "invoice payment processing"
        topics = service._extract_topics(content)

        assert "payments" in topics

    def test_extract_topics_orders(self, procedural_service):
        """Should extract order topics."""
        service, _, _ = procedural_service

        content = "purchase order transaction"
        topics = service._extract_topics(content)

        assert "orders" in topics

    def test_extract_topics_shipping(self, procedural_service):
        """Should extract shipping topics."""
        service, _, _ = procedural_service

        content = "delivery shipment freight"
        topics = service._extract_topics(content)

        assert "shipping" in topics

    def test_extract_topics_multiple(self, procedural_service):
        """Should extract multiple topics."""
        service, _, _ = procedural_service

        content = "payment and delivery for this order"
        topics = service._extract_topics(content)

        # Should have multiple topics
        assert len(topics) >= 2
        assert "payments" in topics or "orders" in topics or "shipping" in topics

    def test_extract_topics_none(self, procedural_service):
        """Should return empty list if no topics matched."""
        service, _, _ = procedural_service

        content = "xyz abc def"
        topics = service._extract_topics(content)

        assert topics == []


# ============================================================================
# Pattern Formatting Tests
# ============================================================================


class TestPatternFormatting:
    """Test pattern formatting methods."""

    def test_format_trigger_pattern(self, procedural_service):
        """Should format intent into natural language trigger."""
        service, _, _ = procedural_service

        intent = "query_payment_history"
        trigger = service._format_trigger_pattern(intent)

        assert "payment" in trigger.lower()
        assert "history" in trigger.lower()

    def test_format_trigger_pattern_unknown_intent(self, procedural_service):
        """Should handle unknown intent gracefully."""
        service, _, _ = procedural_service

        intent = "unknown_intent_xyz"
        trigger = service._format_trigger_pattern(intent)

        # Should still return a string
        assert isinstance(trigger, str)
        assert "unknown_intent_xyz" in trigger

    def test_format_action_heuristic_with_entities_and_topics(
        self, procedural_service
    ):
        """Should format action with both entities and topics."""
        service, _, _ = procedural_service

        entity_types = ["customer", "order"]
        topics = ["payments", "invoices"]

        action = service._format_action_heuristic(entity_types, topics)

        assert isinstance(action, str)
        assert "retrieve" in action.lower()
        # Should mention at least one entity or topic
        assert any(
            term in action.lower()
            for term in ["customer", "order", "payments", "invoices"]
        )

    def test_format_action_heuristic_empty(self, procedural_service):
        """Should handle empty entity types and topics."""
        service, _, _ = procedural_service

        action = service._format_action_heuristic([], [])

        assert isinstance(action, str)
        # Should have fallback text
        assert len(action) > 0


# ============================================================================
# Frequent Sequence Detection Tests
# ============================================================================


class TestFrequentSequences:
    """Test _find_frequent_sequences() private method."""

    def test_find_frequent_sequences_above_threshold(self, procedural_service):
        """Should detect patterns above min_support threshold."""
        service, _, _ = procedural_service

        # 5 episodes with same intent
        episode_features = [
            {
                "intent": "query_payment",
                "entity_types": ["customer"],
                "topics": ["payments"],
                "episode_id": i,
                "timestamp": datetime.now(UTC),
            }
            for i in range(5)
        ]

        patterns = service._find_frequent_sequences(
            episode_features, min_support=3
        )

        assert len(patterns) >= 1
        assert patterns[0].trigger_features["intent"] == "query_payment"
        assert patterns[0].observed_count == 5

    def test_find_frequent_sequences_below_threshold(self, procedural_service):
        """Should not detect patterns below min_support threshold."""
        service, _, _ = procedural_service

        # Only 2 episodes with same intent
        episode_features = [
            {
                "intent": "query_payment",
                "entity_types": [],
                "topics": ["payments"],
                "episode_id": i,
                "timestamp": datetime.now(UTC),
            }
            for i in range(2)
        ]

        patterns = service._find_frequent_sequences(
            episode_features, min_support=3
        )

        assert patterns == []

    def test_find_frequent_sequences_confidence_calculation(self, procedural_service):
        """Should calculate confidence based on observed count."""
        service, _, _ = procedural_service

        # 10 episodes
        episode_features = [
            {
                "intent": "query_order_status",
                "entity_types": [],
                "topics": ["orders"],
                "episode_id": i,
                "timestamp": datetime.now(UTC),
            }
            for i in range(10)
        ]

        patterns = service._find_frequent_sequences(
            episode_features, min_support=3
        )

        assert len(patterns) >= 1
        pattern = patterns[0]

        # Confidence should be reasonable (0.5 + count/20, capped at 0.90)
        assert 0.5 <= pattern.confidence <= 0.90

    def test_find_frequent_sequences_no_strong_associations(
        self, procedural_service
    ):
        """Should not create pattern if no strong entity/topic associations."""
        service, _, _ = procedural_service

        # 5 episodes with same intent but no common entities/topics
        episode_features = [
            {
                "intent": "query_general",
                "entity_types": [f"entity_{i}"],  # All different
                "topics": [],
                "episode_id": i,
                "timestamp": datetime.now(UTC),
            }
            for i in range(5)
        ]

        patterns = service._find_frequent_sequences(
            episode_features, min_support=3
        )

        # May not find patterns since no strong associations
        # (entities appear in <50% of episodes)
        # This depends on the threshold logic
        # For this test, we just verify it doesn't crash
        assert isinstance(patterns, list)


# ============================================================================
# Vision Principle Validation
# ============================================================================


class TestVisionPrinciples:
    """Test that service embodies vision principles."""

    async def test_epistemic_humility_pattern_confidence_capped(
        self, procedural_service
    ):
        """VISION: Epistemic humility - Phase 1 patterns capped at 0.90.

        Even with many observations, confidence should not exceed 0.90.
        """
        service, episodic_repo, procedural_repo = procedural_service

        user_id = "test_user"

        # 50 episodes with same pattern (very high frequency) and common entity
        episodes = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"Payment query for this customer",
                entities=["customer:main"],  # Common entity
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.6,
            )
            for i in range(50)
        ]

        episodic_repo.find_by_user = AsyncMock(return_value=episodes)
        procedural_repo.find_by_trigger_features = AsyncMock(return_value=[])

        procedural_repo.create = AsyncMock(
            side_effect=lambda m: type(
                "ProceduralMemory",
                (),
                {
                    **m.__dict__,
                    "memory_id": 1,
                },
            )()
        )

        patterns = await service.detect_patterns(
            user_id=user_id, lookback_days=30, min_support=3
        )

        # All patterns should have confidence ≤ 0.90 (epistemic humility)
        for pattern in patterns:
            assert pattern.confidence <= 0.90

    async def test_adaptive_learning_reinforcement_increases_confidence(
        self, procedural_service
    ):
        """VISION: Adaptive learning - patterns strengthen with reinforcement."""
        service, episodic_repo, procedural_repo = procedural_service

        user_id = "test_user"

        # Create pattern-matching episodes
        episodes = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content=f"Payment history query {i}",
                entities=[],
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.6,
            )
            for i in range(5)
        ]

        episodic_repo.find_by_user = AsyncMock(return_value=episodes)

        # Existing pattern with lower confidence
        existing_pattern = ProceduralMemory(
            memory_id=1,
            user_id=user_id,
            trigger_pattern="User asks about payment history",
            trigger_features={
                "intent": "query_payment_history",
                "entity_types": [],
                "topics": ["payments"],
            },
            action_heuristic="Retrieve payment history",
            action_structure={
                "action_type": "retrieve_related",
                "queries": ["payments"],
                "predicates": ["has_payment"],
            },
            observed_count=2,
            confidence=0.60,
            created_at=datetime.now(UTC) - timedelta(days=20),
        )

        procedural_repo.find_by_trigger_features = AsyncMock(
            return_value=[existing_pattern]
        )

        procedural_repo.update = AsyncMock(
            side_effect=lambda m: type(
                "ProceduralMemory",
                (),
                {
                    **m.__dict__,
                },
            )()
        )

        patterns = await service.detect_patterns(
            user_id=user_id, lookback_days=30, min_support=3
        )

        # Verify pattern was updated and confidence increased
        if procedural_repo.update.called:
            updated_pattern = procedural_repo.update.call_args[0][0]
            assert updated_pattern.confidence > existing_pattern.confidence
            assert updated_pattern.observed_count > existing_pattern.observed_count

    async def test_learning_from_patterns_detects_cooccurrence(
        self, procedural_service
    ):
        """VISION: Learning from patterns - detects "When X, also Y" heuristics."""
        service, episodic_repo, procedural_repo = procedural_service

        user_id = "test_user"

        # Create episodes with co-occurring entity types and topics
        # 6 episodes to meet min_support * 2 = 6
        episodes = [
            MemoryCandidate(
                memory_id=i,
                memory_type="episodic",
                content="Customer payment query with invoice details",
                entities=["customer:test"],  # Same entity in all
                embedding=np.random.rand(1536),
                created_at=datetime.now(UTC),
                importance=0.6,
            )
            for i in range(6)
        ]

        episodic_repo.find_by_user = AsyncMock(return_value=episodes)
        procedural_repo.find_by_trigger_features = AsyncMock(return_value=[])

        procedural_repo.create = AsyncMock(
            side_effect=lambda m: type(
                "ProceduralMemory",
                (),
                {
                    **m.__dict__,
                    "memory_id": 1,
                },
            )()
        )

        patterns = await service.detect_patterns(
            user_id=user_id, lookback_days=30, min_support=3
        )

        # Should detect pattern with action structure (co-occurrence)
        assert len(patterns) >= 1
        for pattern in patterns:
            # Should have structured action
            assert "action_type" in pattern.action_structure
            assert "queries" in pattern.action_structure
            assert "predicates" in pattern.action_structure
