"""Procedural memory service.

Detects and applies learned patterns from tool usage logs.

Design from: PHASE1D_PLAN_ITERATION.md
Vision: Layer 5 - "When X, also Y" learned heuristics

VISION ALIGNMENT:
- NO hardcoded keyword matching (emergent intelligence, not brittle rules)
- Learn from actual tool call patterns (what LLM actually does)
- Context-aware (tool combinations, not isolated keywords)
"""

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from src.config import heuristics
from src.domain.entities.procedural_memory import ProceduralMemory
from src.domain.exceptions import DomainError
from src.domain.ports.tool_usage_tracker_port import IToolUsageTracker
from src.domain.ports.procedural_memory_repository import IProceduralMemoryRepository
from src.domain.value_objects.procedural_memory import Pattern

logger = structlog.get_logger()


class ProceduralMemoryService:
    """Detects and applies procedural patterns from tool usage.

    Philosophy: Learn from what the LLM actually does, not keyword matching.

    Phase 1 Approach:
    - Analyze tool usage logs (what tools are called together)
    - Detect co-occurrence patterns (frequency analysis)
    - Phase 2+: Use sequence mining for temporal patterns

    Example pattern:
        Trigger: "LLM calls get_invoice_status"
        Action: "Also call get_credit_status and get_work_orders_for_customer"
        Confidence: 0.85 (observed 5+ times)

    Usage:
        >>> service = ProceduralMemoryService(tool_usage_tracker, procedural_repo)
        >>> patterns = await service.detect_patterns(user_id="user_1")
        >>> print(f"Found {len(patterns)} new patterns")
    """

    def __init__(
        self,
        tool_usage_tracker: IToolUsageTracker,
        procedural_repo: IProceduralMemoryRepository,
    ) -> None:
        """Initialize procedural memory service.

        Args:
            tool_usage_tracker: Tracks tool usage logs for pattern mining
            procedural_repo: Repository for procedural memories
        """
        self._tool_tracker = tool_usage_tracker
        self._procedural_repo = procedural_repo

    async def detect_patterns(
        self,
        user_id: str,
        lookback_days: int = 30,
        min_support: int = 3,
    ) -> list[ProceduralMemory]:
        """Detect new patterns from tool usage logs.

        Analyzes recent tool calls to find co-occurrence patterns.

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
                "detecting_tool_patterns",
                user_id=user_id,
                lookback_days=lookback_days,
                min_support=min_support,
            )

            # Fetch recent tool usage logs
            since = datetime.now(UTC) - timedelta(days=lookback_days)
            usage_logs = await self._tool_tracker.get_usage_logs(
                user_id=user_id,
                since=since,
                limit=500,  # Analyze last 500 interactions
            )

            if len(usage_logs) < min_support * 2:
                logger.info(
                    "insufficient_tool_usage_for_pattern_detection",
                    user_id=user_id,
                    log_count=len(usage_logs),
                    min_required=min_support * 2,
                )
                return []

            # Extract tool call sequences from logs
            tool_sequences = [
                self._extract_tool_sequence(log) for log in usage_logs
            ]

            # Find frequent co-occurrence patterns
            patterns = self._find_frequent_tool_patterns(
                tool_sequences, min_support=min_support
            )

            if not patterns:
                logger.info("no_tool_patterns_found", user_id=user_id)
                return []

            # Convert patterns to ProceduralMemory and store
            procedural_memories = []
            for pattern in patterns:
                # Check if pattern already exists
                existing = await self._procedural_repo.find_by_trigger_features(
                    user_id=user_id,
                    intent=pattern.trigger_features.get("anchor_tool"),
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
                        "tool_pattern_reinforced",
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
                        "tool_pattern_created",
                        memory_id=created.memory_id,
                        trigger=created.trigger_pattern,
                        confidence=created.confidence,
                    )

            logger.info(
                "tool_pattern_detection_completed",
                user_id=user_id,
                patterns_found=len(procedural_memories),
            )

            return procedural_memories

        except Exception as e:
            logger.error(
                "tool_pattern_detection_error", user_id=user_id, error=str(e)
            )
            msg = f"Error detecting tool patterns: {e}"
            raise DomainError(msg) from e

    def _extract_tool_sequence(self, usage_log: dict[str, Any]) -> dict[str, Any]:
        """Extract tool call sequence from usage log.

        Args:
            usage_log: Tool usage log entry

        Returns:
            Sequence dictionary with tools called and metadata
        """
        tools_called = usage_log.get("tools_called", [])

        # Extract unique tool names (order preserved)
        tool_names = []
        seen = set()
        for tool_call in tools_called:
            tool_name = tool_call.get("tool")
            if tool_name and tool_name not in seen:
                tool_names.append(tool_name)
                seen.add(tool_name)

        # Extract entity types from tool arguments
        # (e.g., customer_id in get_invoice_status implies "customer" entity type)
        entity_types: set[str] = set()
        for tool_call in tools_called:
            args = tool_call.get("arguments", {})
            # Infer entity types from argument names
            if "customer_id" in args:
                entity_types.add("customer")
            if "sales_order_number" in args:
                entity_types.add("sales_order")
            # Add more inferences as needed

        return {
            "tools": tool_names,
            "entity_types": sorted(list(entity_types)),
            "timestamp": usage_log.get("timestamp"),
            "conversation_id": usage_log.get("conversation_id"),
            "facts_count": usage_log.get("facts_count", 0),
        }

    def _find_frequent_tool_patterns(
        self, tool_sequences: list[dict[str, Any]], min_support: int = 3
    ) -> list[Pattern]:
        """Find frequent tool co-occurrence patterns.

        Phase 1: Basic frequency analysis
        - Find pairs/groups of tools that are called together frequently
        - Anchor pattern to the first tool called

        Phase 2+: Use sequence mining algorithms (e.g., PrefixSpan)

        Args:
            tool_sequences: List of tool call sequences
            min_support: Minimum occurrences to consider pattern

        Returns:
            List of Pattern instances
        """
        # Group sequences by anchor tool (first tool called)
        anchor_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for sequence in tool_sequences:
            tools = sequence["tools"]
            if not tools:
                continue
            anchor_tool = tools[0]
            anchor_groups[anchor_tool].append(sequence)

        patterns = []

        # For each anchor tool, find commonly co-occurring tools
        for anchor_tool, sequences in anchor_groups.items():
            if len(sequences) < min_support:
                continue  # Not frequent enough

            # Count co-occurring tools (excluding anchor)
            cooccurrence_counter: Counter[str] = Counter()
            entity_counter: Counter[str] = Counter()

            for seq in sequences:
                # Count all tools after the anchor
                for tool in seq["tools"][1:]:
                    cooccurrence_counter[tool] += 1
                # Count entity types
                for entity_type in seq["entity_types"]:
                    entity_counter[entity_type] += 1

            # Find tools that co-occur in >50% of cases
            threshold = len(sequences) * 0.5
            frequent_cooccurrences = [
                tool
                for tool, count in cooccurrence_counter.items()
                if count >= threshold
            ]

            if not frequent_cooccurrences:
                continue  # No strong co-occurrence pattern

            # Find frequent entity types
            frequent_entities = [
                entity
                for entity, count in entity_counter.items()
                if count >= threshold
            ]

            # Create pattern
            trigger_pattern = self._format_trigger_pattern(anchor_tool)
            action_heuristic = self._format_action_heuristic(
                anchor_tool, frequent_cooccurrences
            )

            # Get conversation IDs as source
            source_conversation_ids = [
                seq["conversation_id"] for seq in sequences
            ]

            # Calculate confidence (higher frequency → higher confidence)
            # Cap at 0.90 for Phase 1 patterns (not ML-based)
            confidence = min(0.90, 0.5 + (len(sequences) / 20.0))

            pattern = Pattern(
                trigger_pattern=trigger_pattern,
                trigger_features={
                    "anchor_tool": anchor_tool,
                    "entity_types": frequent_entities,
                    "tool_type": "domain_query",
                },
                action_heuristic=action_heuristic,
                action_structure={
                    "action_type": "call_additional_tools",
                    "tools": frequent_cooccurrences,
                    "reason": f"These tools are frequently called after {anchor_tool}",
                },
                observed_count=len(sequences),
                confidence=confidence,
                source_episode_ids=source_conversation_ids,  # Using conversation IDs
            )

            patterns.append(pattern)

        return patterns

    def _format_trigger_pattern(self, anchor_tool: str) -> str:
        """Format anchor tool into natural language trigger pattern.

        Args:
            anchor_tool: Anchor tool name

        Returns:
            Natural language trigger description
        """
        # Convert snake_case to readable form
        readable = anchor_tool.replace("_", " ").title()
        return f"When LLM calls {readable}"

    def _format_action_heuristic(
        self, anchor_tool: str, cooccurring_tools: list[str]
    ) -> str:
        """Format action heuristic into natural language.

        Args:
            anchor_tool: Anchor tool name
            cooccurring_tools: Frequently co-occurring tool names

        Returns:
            Natural language action description
        """
        if not cooccurring_tools:
            return "No additional actions detected"

        tools_readable = [
            tool.replace("_", " ").title() for tool in cooccurring_tools
        ]
        tools_str = ", ".join(tools_readable)

        return f"Also call: {tools_str}"

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
                "augmenting_query_with_tool_patterns",
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
