"""Procedural memory service.

Detects and applies learned patterns from episodic memories.

Design from: PHASE1D_PLAN_ITERATION.md
Vision: Layer 5 - "When X, also Y" learned heuristics
"""

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from src.config import heuristics
from src.domain.exceptions import DomainError
from src.domain.ports.episodic_memory_repository import IEpisodicMemoryRepository
from src.domain.ports.procedural_memory_repository import IProceduralMemoryRepository
from src.domain.value_objects.memory_candidate import MemoryCandidate
from src.domain.value_objects.procedural_memory import Pattern, ProceduralMemory

logger = structlog.get_logger()


class ProceduralMemoryService:
    """Detects and applies procedural patterns.

    Philosophy: Learn from interaction patterns to augment future retrievals.

    Phase 1 Approach:
    - Basic frequency analysis (co-occurrence patterns)
    - Threshold-based detection (min_support parameter)
    - Phase 2+: Use ML for more sophisticated detection

    Example pattern:
        Trigger: "User asks about customer payment history"
        Action: "Also retrieve open invoices and credit status"
        Confidence: 0.85 (observed 5+ times)

    Usage:
        >>> service = ProceduralMemoryService(episodic_repo, procedural_repo)
        >>> patterns = await service.detect_patterns(user_id="user_1")
        >>> print(f"Found {len(patterns)} new patterns")
    """

    def __init__(
        self,
        episodic_repo: IEpisodicMemoryRepository,
        procedural_repo: IProceduralMemoryRepository,
    ) -> None:
        """Initialize procedural memory service.

        Args:
            episodic_repo: Repository for episodic memories
            procedural_repo: Repository for procedural memories
        """
        self._episodic_repo = episodic_repo
        self._procedural_repo = procedural_repo

    async def detect_patterns(
        self,
        user_id: str,
        lookback_days: int = 30,
        min_support: int = 3,
    ) -> list[ProceduralMemory]:
        """Detect new patterns from recent episodic memories.

        Analyzes recent episodes to find co-occurrence patterns.

        Args:
            user_id: User identifier
            lookback_days: How far back to analyze (default 30 days)
            min_support: Minimum occurrences to consider pattern (default 3)

        Returns:
            List of newly created ProceduralMemory instances

        Raises:
            DomainError: If pattern detection fails
        """
        try:
            logger.info(
                "detecting_patterns",
                user_id=user_id,
                lookback_days=lookback_days,
                min_support=min_support,
            )

            # Fetch recent episodes
            since = datetime.now(UTC) - timedelta(days=lookback_days)
            episodes = await self._episodic_repo.find_by_user(
                user_id=user_id,
                since=since,
                limit=500,  # Analyze last 500 episodes
            )

            if len(episodes) < min_support * 2:
                logger.info(
                    "insufficient_episodes_for_pattern_detection",
                    user_id=user_id,
                    episode_count=len(episodes),
                    min_required=min_support * 2,
                )
                return []

            # Extract features from episodes
            episode_features = [
                self._extract_features(episode) for episode in episodes
            ]

            # Find frequent sequences (basic frequency analysis)
            patterns = self._find_frequent_sequences(
                episode_features, min_support=min_support
            )

            if not patterns:
                logger.info("no_patterns_found", user_id=user_id)
                return []

            # Convert patterns to ProceduralMemory and store
            procedural_memories = []
            for pattern in patterns:
                # Check if pattern already exists
                existing = await self._procedural_repo.find_by_trigger_features(
                    user_id=user_id,
                    intent=pattern.trigger_features.get("intent"),
                    entity_types=pattern.trigger_features.get("entity_types"),
                    min_confidence=0.0,
                    limit=1,
                )

                if existing:
                    # Pattern exists, increment observed_count
                    updated = existing[0].increment_observed_count()
                    procedural_memories.append(
                        await self._procedural_repo.update(updated)
                    )
                    logger.info(
                        "pattern_reinforced",
                        memory_id=updated.memory_id,
                        observed_count=updated.observed_count,
                        confidence=updated.confidence,
                    )
                else:
                    # New pattern, create
                    memory = ProceduralMemory.from_pattern(
                        pattern=pattern, user_id=user_id
                    )
                    created = await self._procedural_repo.create(memory)
                    procedural_memories.append(created)
                    logger.info(
                        "pattern_created",
                        memory_id=created.memory_id,
                        trigger=created.trigger_pattern,
                        confidence=created.confidence,
                    )

            logger.info(
                "pattern_detection_completed",
                user_id=user_id,
                patterns_found=len(procedural_memories),
            )

            return procedural_memories

        except Exception as e:
            logger.error(
                "pattern_detection_error", user_id=user_id, error=str(e)
            )
            raise DomainError(f"Error detecting patterns: {e}") from e

    def _extract_features(self, episode: MemoryCandidate) -> dict[str, Any]:
        """Extract features from episodic memory.

        Phase 1: Simple heuristic-based extraction
        Phase 2+: Use NLP or LLM for better feature extraction

        Args:
            episode: Memory candidate (episodic memory)

        Returns:
            Feature dictionary
        """
        content_lower = episode.content.lower()

        # Extract intent (simple pattern matching)
        intent = self._classify_intent(content_lower)

        # Extract entity types from episode
        entity_types = list(set([ent for ent in episode.entities]))

        # Extract topics (simple keyword matching)
        topics = self._extract_topics(content_lower)

        return {
            "intent": intent,
            "entity_types": sorted(entity_types),  # Sort for consistency
            "topics": sorted(topics),  # Sort for consistency
            "episode_id": episode.memory_id,
            "timestamp": episode.created_at,
        }

    def _classify_intent(self, content: str) -> str:
        """Classify query intent using simple patterns.

        Phase 1: Simple keyword-based classification
        Phase 2+: Use ML classifier

        Args:
            content: Content text (lowercased)

        Returns:
            Intent label
        """
        # Payment-related
        if any(
            word in content
            for word in ["payment", "invoice", "bill", "pay", "paid"]
        ):
            if "history" in content or "past" in content:
                return "query_payment_history"
            elif "open" in content or "outstanding" in content:
                return "query_open_payments"
            else:
                return "query_payment"

        # Customer-related
        if any(word in content for word in ["customer", "client", "account"]):
            if "status" in content:
                return "query_customer_status"
            elif "history" in content:
                return "query_customer_history"
            else:
                return "query_customer"

        # Product-related
        if any(
            word in content for word in ["product", "item", "inventory", "stock"]
        ):
            if "availability" in content or "stock" in content:
                return "query_product_availability"
            else:
                return "query_product"

        # Order-related
        if any(word in content for word in ["order", "purchase", "transaction"]):
            if "status" in content:
                return "query_order_status"
            elif "history" in content:
                return "query_order_history"
            else:
                return "query_order"

        # Preference-related
        if any(word in content for word in ["prefer", "like", "want", "need"]):
            return "statement_preference"

        # Default
        return "query_general"

    def _extract_topics(self, content: str) -> list[str]:
        """Extract topics from content using keyword matching.

        Phase 1: Simple keyword matching
        Phase 2+: Use topic modeling or LLM

        Args:
            content: Content text (lowercased)

        Returns:
            List of topics
        """
        topics = []

        topic_keywords = {
            "payments": ["payment", "invoice", "bill", "pay", "paid", "charge"],
            "orders": ["order", "purchase", "transaction", "buy", "bought"],
            "products": [
                "product",
                "item",
                "inventory",
                "stock",
                "merchandise",
            ],
            "customers": ["customer", "client", "account", "user"],
            "shipping": ["ship", "delivery", "shipment", "deliver", "freight"],
            "credit": ["credit", "balance", "limit", "outstanding"],
            "preferences": ["prefer", "like", "want", "need", "requirement"],
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in content for keyword in keywords):
                topics.append(topic)

        return topics

    def _find_frequent_sequences(
        self, episode_features: list[dict[str, Any]], min_support: int = 3
    ) -> list[Pattern]:
        """Find frequent co-occurrence patterns.

        Phase 1: Basic frequency analysis
        - Find pairs of (trigger_intent, action_entities/topics) that co-occur frequently

        Phase 2+: Use sequence mining algorithms (e.g., PrefixSpan)

        Args:
            episode_features: List of feature dictionaries
            min_support: Minimum occurrences to consider pattern

        Returns:
            List of Pattern instances
        """
        # Group episodes by intent
        intent_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for features in episode_features:
            intent = features["intent"]
            intent_groups[intent].append(features)

        patterns = []

        # For each intent, find common entity_types and topics
        for intent, episodes in intent_groups.items():
            if len(episodes) < min_support:
                continue  # Not frequent enough

            # Count entity_type co-occurrences
            entity_counter: Counter[str] = Counter()
            topic_counter: Counter[str] = Counter()

            for ep in episodes:
                for entity_type in ep["entity_types"]:
                    entity_counter[entity_type] += 1
                for topic in ep["topics"]:
                    topic_counter[topic] += 1

            # Find frequent entity_types (appear in >50% of episodes for this intent)
            threshold = len(episodes) * 0.5
            frequent_entities = [
                entity
                for entity, count in entity_counter.items()
                if count >= threshold
            ]
            frequent_topics = [
                topic for topic, count in topic_counter.items() if count >= threshold
            ]

            if not frequent_entities and not frequent_topics:
                continue  # No strong associations

            # Create pattern
            trigger_pattern = self._format_trigger_pattern(intent)
            action_heuristic = self._format_action_heuristic(
                frequent_entities, frequent_topics
            )

            # Get source episode IDs
            source_episode_ids = [ep["episode_id"] for ep in episodes]

            # Calculate confidence (higher frequency → higher confidence)
            # Cap at 0.90 for Phase 1 patterns (not ML-based)
            confidence = min(0.90, 0.5 + (len(episodes) / 20.0))

            pattern = Pattern(
                trigger_pattern=trigger_pattern,
                trigger_features={
                    "intent": intent,
                    "entity_types": frequent_entities,
                    "topics": frequent_topics,
                },
                action_heuristic=action_heuristic,
                action_structure={
                    "action_type": "retrieve_related",
                    "queries": frequent_topics,
                    "predicates": [
                        f"has_{topic}" for topic in frequent_topics
                    ],  # Simplified
                },
                observed_count=len(episodes),
                confidence=confidence,
                source_episode_ids=source_episode_ids,
            )

            patterns.append(pattern)

        return patterns

    def _format_trigger_pattern(self, intent: str) -> str:
        """Format intent into natural language trigger pattern.

        Args:
            intent: Intent label

        Returns:
            Natural language trigger description
        """
        intent_templates = {
            "query_payment_history": "User asks about payment history",
            "query_open_payments": "User asks about open/outstanding payments",
            "query_payment": "User asks about payments",
            "query_customer_status": "User asks about customer status",
            "query_customer_history": "User asks about customer history",
            "query_customer": "User asks about customer information",
            "query_product_availability": "User asks about product availability",
            "query_product": "User asks about products",
            "query_order_status": "User asks about order status",
            "query_order_history": "User asks about order history",
            "query_order": "User asks about orders",
            "statement_preference": "User states a preference or requirement",
            "query_general": "User asks a general question",
        }

        return intent_templates.get(intent, f"User intent: {intent}")

    def _format_action_heuristic(
        self, entity_types: list[str], topics: list[str]
    ) -> str:
        """Format action heuristic into natural language.

        Args:
            entity_types: Frequent entity types
            topics: Frequent topics

        Returns:
            Natural language action description
        """
        parts = []

        if entity_types:
            entities_str = ", ".join(entity_types)
            parts.append(f"entities: {entities_str}")

        if topics:
            topics_str = ", ".join(topics)
            parts.append(f"topics: {topics_str}")

        if parts:
            return f"Also retrieve related {' and '.join(parts)}"
        else:
            return "Retrieve related context"

    async def augment_query(
        self,
        user_id: str,
        query_embedding: Any,
        top_k: int = 5,
    ) -> list[ProceduralMemory]:
        """Get procedural patterns to augment query retrieval.

        Finds patterns with similar triggers to enhance retrieval.

        Args:
            user_id: User identifier
            query_embedding: Query embedding vector
            top_k: Number of patterns to retrieve

        Returns:
            List of relevant ProceduralMemory instances

        Raises:
            DomainError: If augmentation fails
        """
        try:
            logger.debug(
                "augmenting_query_with_patterns",
                user_id=user_id,
                top_k=top_k,
            )

            # Find similar patterns
            patterns = await self._procedural_repo.find_similar(
                user_id=user_id,
                query_embedding=query_embedding,
                limit=top_k,
                min_confidence=heuristics.PROCEDURAL_MIN_CONFIDENCE,
            )

            logger.debug(
                "query_augmentation_completed",
                user_id=user_id,
                patterns_found=len(patterns),
            )

            return patterns

        except Exception as e:
            logger.error("query_augmentation_error", user_id=user_id, error=str(e))
            # Don't raise - query augmentation is optional, should fail gracefully
            return []
