"""Consolidation service for memory synthesis.

Consolidates episodic and semantic memories into coherent summaries using LLM synthesis.

Vision: "Replace many specific memories with one abstract summary" - graceful forgetting.

Design from: PHASE1D_IMPLEMENTATION_PLAN.md
"""

import json
from datetime import UTC, datetime

import structlog

from src.config import heuristics
from src.domain.entities.memory_summary import MemorySummary
from src.domain.entities.semantic_memory import SemanticMemory
from src.domain.exceptions import DomainError
from src.domain.ports.chat_repository import IChatEventRepository
from src.domain.ports.embedding_service import IEmbeddingService
from src.domain.ports.episodic_memory_repository import IEpisodicMemoryRepository
from src.domain.ports.llm_service import ILLMService
from src.domain.ports.semantic_memory_repository import ISemanticMemoryRepository
from src.domain.ports.summary_repository import ISummaryRepository
from src.domain.value_objects.consolidation import (
    ConsolidationScope,
    SummaryData,
)
from src.domain.value_objects.memory_candidate import MemoryCandidate

logger = structlog.get_logger()


class ConsolidationService:
    """Consolidates episodic and semantic memories into summaries.

    Uses LLM synthesis to create coherent summaries from many specific memories.
    Includes robust error handling with retry logic and fallback strategies.

    Philosophy: Graceful forgetting through consolidation.

    Example:
        >>> consolidation_service = ConsolidationService(
        ...     episodic_repo=episodic_repo,
        ...     semantic_repo=semantic_repo,
        ...     summary_repo=summary_repo,
        ...     llm_service=llm_service,
        ...     embedding_service=embedding_service
        ... )
        >>> summary = await consolidation_service.consolidate(
        ...     user_id="user_1",
        ...     scope=ConsolidationScope.entity_scope("customer_gai_123")
        ... )
    """

    def __init__(
        self,
        episodic_repo: IEpisodicMemoryRepository,
        semantic_repo: ISemanticMemoryRepository,
        summary_repo: ISummaryRepository,
        chat_repo: IChatEventRepository,
        llm_service: ILLMService,
        embedding_service: IEmbeddingService,
    ) -> None:
        """Initialize consolidation service.

        Args:
            episodic_repo: Repository for episodic memories
            semantic_repo: Repository for semantic memories
            summary_repo: Repository for memory summaries
            chat_repo: Repository for chat events
            llm_service: LLM service for synthesis
            embedding_service: Service for generating embeddings
        """
        self._episodic_repo = episodic_repo
        self._semantic_repo = semantic_repo
        self._summary_repo = summary_repo
        self._chat_repo = chat_repo
        self._llm_service = llm_service
        self._embedding_service = embedding_service

    async def consolidate(
        self,
        user_id: str,
        scope: ConsolidationScope,
        max_retries: int = 3,
        force: bool = False,
    ) -> MemorySummary:
        """Consolidate memories into a summary.

        Args:
            user_id: User identifier
            scope: Consolidation scope (entity, topic, session_window)
            max_retries: Maximum LLM synthesis retry attempts
            force: Force consolidation even if below thresholds

        Returns:
            Created memory summary

        Raises:
            DomainError: If consolidation fails
        """
        try:
            logger.info(
                "consolidation_started",
                user_id=user_id,
                scope_type=scope.type,
                scope_identifier=scope.identifier,
            )

            # Dispatch to specific consolidation method
            if scope.type == "entity":
                return await self.consolidate_entity(
                    user_id=user_id,
                    entity_id=scope.identifier,
                    max_retries=max_retries,
                )
            elif scope.type == "session_window":
                return await self.consolidate_session_window(
                    user_id=user_id,
                    num_sessions=int(scope.identifier),
                    max_retries=max_retries,
                )
            elif scope.type == "topic":
                return await self.consolidate_topic(
                    user_id=user_id,
                    predicate_pattern=scope.identifier,
                    max_retries=max_retries,
                )
            else:
                msg = f"Unknown consolidation scope type: {scope.type}"
                raise DomainError(msg)

        except Exception as e:
            logger.error(
                "consolidation_error",
                user_id=user_id,
                scope=scope.to_dict(),
                error=str(e),
            )
            msg = f"Error consolidating memories: {e}"
            raise DomainError(msg) from e

    async def consolidate_entity(
        self, user_id: str, entity_id: str, max_retries: int = 3
    ) -> MemorySummary:
        """Consolidate all memories about a specific entity.

        Args:
            user_id: User identifier
            entity_id: Entity identifier
            max_retries: Maximum LLM synthesis retry attempts

        Returns:
            Created memory summary for entity
        """
        logger.info(
            "entity_consolidation_started",
            user_id=user_id,
            entity_id=entity_id,
        )

        scope = ConsolidationScope.entity_scope(entity_id)

        # Fetch memories
        episodic, semantic = await self._fetch_memories(user_id, scope)

        # Check threshold
        if len(episodic) < heuristics.CONSOLIDATION_MIN_EPISODIC:
            logger.warning(
                "insufficient_memories_for_consolidation",
                user_id=user_id,
                entity_id=entity_id,
                episodic_count=len(episodic),
                threshold=heuristics.CONSOLIDATION_MIN_EPISODIC,
            )
            # For Phase 1: Allow manual consolidation even below threshold
            # raise DomainError(f"Insufficient memories: {len(episodic)} < {heuristics.CONSOLIDATION_MIN_EPISODIC}")

        # Try LLM synthesis with retries
        for attempt in range(max_retries):
            try:
                summary_data = await self._synthesize_with_llm(
                    episodic=episodic,
                    semantic=semantic,
                    scope=scope,
                )

                # Store summary
                summary = await self._store_summary(user_id, scope, summary_data)

                # Boost confidence of confirmed facts
                await self._boost_confirmed_facts(summary_data.confirmed_memory_ids)

                logger.info(
                    "consolidation_completed",
                    user_id=user_id,
                    entity_id=entity_id,
                    summary_id=summary.summary_id,
                )

                return summary

            except ValueError as e:
                logger.warning(
                    "llm_synthesis_failed",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                )

                if attempt == max_retries - 1:
                    # Fallback: Create basic summary without LLM
                    logger.info("using_fallback_summary", user_id=user_id)
                    return await self._create_fallback_summary(
                        user_id=user_id,
                        scope=scope,
                        episodic=episodic,
                        semantic=semantic,
                    )

        # Should not reach here, but add safety
        return await self._create_fallback_summary(
            user_id=user_id, scope=scope, episodic=episodic, semantic=semantic
        )

    async def consolidate_topic(
        self, user_id: str, predicate_pattern: str, max_retries: int = 3
    ) -> MemorySummary:
        """Consolidate memories matching a predicate pattern.

        Args:
            user_id: User identifier
            predicate_pattern: Predicate pattern (e.g., "delivery_*")
            max_retries: Maximum LLM synthesis retry attempts

        Returns:
            Created memory summary for topic
        """
        logger.info(
            "topic_consolidation_started",
            user_id=user_id,
            predicate_pattern=predicate_pattern,
        )

        ConsolidationScope.topic_scope(predicate_pattern)

        # For Phase 1, topic consolidation is simplified
        # Would need semantic memory filtering by predicate pattern
        msg = "Topic consolidation not yet implemented in Phase 1"
        raise DomainError(msg)

    async def consolidate_session_window(
        self, user_id: str, num_sessions: int = 5, max_retries: int = 3
    ) -> MemorySummary:
        """Consolidate recent N sessions.

        Args:
            user_id: User identifier
            num_sessions: Number of recent sessions to consolidate
            max_retries: Maximum LLM synthesis retry attempts

        Returns:
            Created memory summary for session window
        """
        logger.info(
            "session_window_consolidation_started",
            user_id=user_id,
            num_sessions=num_sessions,
        )

        scope = ConsolidationScope.session_window_scope(num_sessions)

        # Fetch memories from last N sessions
        episodic, semantic = await self._fetch_memories(user_id, scope)

        # Check threshold
        if len(episodic) < heuristics.CONSOLIDATION_MIN_EPISODIC:
            logger.warning(
                "insufficient_memories_for_session_consolidation",
                user_id=user_id,
                num_sessions=num_sessions,
                episodic_count=len(episodic),
                threshold=heuristics.CONSOLIDATION_MIN_EPISODIC,
            )
            # For Phase 1: Allow manual consolidation even below threshold
            # raise DomainError(f"Insufficient memories: {len(episodic)} < {heuristics.CONSOLIDATION_MIN_EPISODIC}")

        # Try LLM synthesis with retries
        for attempt in range(max_retries):
            try:
                summary_data = await self._synthesize_with_llm(
                    episodic=episodic,
                    semantic=semantic,
                    scope=scope,
                )

                # Store summary
                summary = await self._store_summary(user_id, scope, summary_data)

                # Boost confidence of confirmed facts
                await self._boost_confirmed_facts(summary_data.confirmed_memory_ids)

                logger.info(
                    "session_window_consolidation_completed",
                    user_id=user_id,
                    num_sessions=num_sessions,
                    summary_id=summary.summary_id,
                )

                return summary

            except ValueError as e:
                logger.warning(
                    "llm_synthesis_failed",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                )

                if attempt == max_retries - 1:
                    # Fallback: Create basic summary without LLM
                    logger.info("using_fallback_summary", user_id=user_id)
                    return await self._create_fallback_summary(
                        user_id=user_id,
                        scope=scope,
                        episodic=episodic,
                        semantic=semantic,
                    )

        # Should not reach here, but add safety
        return await self._create_fallback_summary(
            user_id=user_id, scope=scope, episodic=episodic, semantic=semantic
        )

    async def _fetch_memories(
        self, user_id: str, scope: ConsolidationScope
    ) -> tuple[list[MemoryCandidate], list[SemanticMemory]]:
        """Fetch episodic and semantic memories for a scope.

        Args:
            user_id: User identifier
            scope: Consolidation scope

        Returns:
            Tuple of (episodic_memories, semantic_memories)
        """
        if scope.type == "entity":
            # Fetch episodic memories about entity
            # For Phase 1: Simplified - fetch recent memories
            episodic = await self._episodic_repo.find_recent(user_id, limit=50)

            # Filter to entity (simplified - in production would have entity filter in query)
            entity_id = scope.identifier
            episodic_filtered = [
                e for e in episodic if entity_id in e.entities
            ]

            # Fetch semantic memories about entity
            # For Phase 1: Simplified - would need semantic repo method for entity filter
            semantic: list[SemanticMemory] = []

            logger.debug(
                "memories_fetched",
                user_id=user_id,
                entity_id=entity_id,
                episodic_count=len(episodic_filtered),
                semantic_count=len(semantic),
            )

            return episodic_filtered, semantic

        elif scope.type == "session_window":
            # Fetch recent N sessions worth of memories
            num_sessions = int(scope.identifier)

            # Get recent chat events to identify recent sessions
            recent_messages = await self._chat_repo.get_recent_for_user(
                user_id=user_id,
                limit=100  # Fetch enough to cover N sessions
            )

            # Extract distinct session IDs (most recent first)
            seen_sessions = []
            for msg in reversed(recent_messages):  # Reverse to get chronological order
                if msg.session_id not in seen_sessions:
                    seen_sessions.append(msg.session_id)
                if len(seen_sessions) >= num_sessions:
                    break

            if not seen_sessions:
                logger.warning(
                    "no_recent_sessions_found",
                    user_id=user_id,
                    num_sessions=num_sessions,
                )
                return [], []

            logger.debug(
                "session_window_identified",
                user_id=user_id,
                num_sessions=num_sessions,
                found_sessions=len(seen_sessions),
                session_ids=[str(sid) for sid in seen_sessions],
            )

            # Fetch episodic memories from these sessions
            all_episodic: list[MemoryCandidate] = []
            for session_id in seen_sessions:
                episodic = await self._episodic_repo.find_recent(
                    user_id=user_id,
                    limit=50,
                    session_id=session_id,
                )
                all_episodic.extend(episodic)

            # For Phase 1: Fetch semantic memories created in this time window
            # Simplified - fetch all active semantic memories for user
            # In Phase 2, would filter by creation timestamp
            all_semantic: list[SemanticMemory] = []

            logger.debug(
                "session_window_memories_fetched",
                user_id=user_id,
                num_sessions=num_sessions,
                episodic_count=len(all_episodic),
                semantic_count=len(all_semantic),
            )

            return all_episodic, all_semantic

        return [], []

    async def _synthesize_with_llm(
        self,
        episodic: list[MemoryCandidate],
        semantic: list[SemanticMemory],
        scope: ConsolidationScope,
    ) -> SummaryData:
        """Synthesize summary using LLM.

        Args:
            episodic: List of episodic memories
            semantic: List of semantic memories
            scope: Consolidation scope

        Returns:
            Synthesized summary data

        Raises:
            ValueError: If LLM synthesis fails or output is invalid
        """
        # Format memories for LLM
        episodic_text = self._format_episodic_memories(episodic)
        semantic_text = self._format_semantic_memories(semantic)

        prompt = f"""Synthesize a consolidated summary from these memories.

**Scope**: {scope.type} - {scope.identifier}

**Episodic memories** ({len(episodic)} events):
{episodic_text}

**Semantic memories** ({len(semantic)} facts):
{semantic_text}

**Task**: Create a coherent summary that:
1. Highlights confirmed facts (mentioned multiple times with high confidence)
2. Notes patterns in interactions
3. Captures key preferences and policies
4. Identifies facts that need validation (low confidence or aged)

**Output** (JSON):
{{
  "summary_text": "Concise narrative summary (2-3 sentences)",
  "key_facts": {{
    "fact_name": {{
      "value": "...",
      "confidence": 0.95,
      "reinforced": 3,
      "source_memory_ids": [1, 5, 12]
    }}
  }},
  "interaction_patterns": ["Pattern 1", "Pattern 2"],
  "needs_validation": ["Fact that hasn't been seen in 90+ days"],
  "confirmed_memory_ids": [1, 5, 12]
}}
"""

        # Call LLM for synthesis
        logger.debug("calling_llm_for_synthesis", scope=scope.to_dict(), prompt_length=len(prompt))

        try:
            # Use LLM service to synthesize summary
            response_text = await self._llm_service.generate_structured_output(
                prompt=prompt,
                response_format="json",
                temperature=0.3,  # Lower temperature for consistent structured output
            )

            logger.debug("llm_synthesis_response", response_length=len(response_text))

        except Exception as e:
            logger.error("llm_synthesis_call_failed", error=str(e))
            # Fallback to simple summary if LLM call fails
            response_text = json.dumps({
                "summary_text": f"Summary for {scope.identifier}: {len(episodic)} episodes analyzed",
                "key_facts": {},
                "interaction_patterns": [],
                "needs_validation": [],
                "confirmed_memory_ids": [],
            })

        # Parse LLM response
        try:
            response = json.loads(response_text)
            return SummaryData.from_llm_response(response)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("invalid_llm_response", response=response_text, error=str(e))
            msg = f"Invalid LLM response: {e}"
            raise ValueError(msg) from e

    def _format_episodic_memories(self, episodic: list[MemoryCandidate]) -> str:
        """Format episodic memories for LLM prompt."""
        if not episodic:
            return "(None)"

        lines = []
        for i, memory in enumerate(episodic[:20], 1):  # Limit to 20 for token budget
            lines.append(
                f"{i}. [{memory.created_at.strftime('%Y-%m-%d')}] {memory.content}"
            )

        return "\n".join(lines)

    def _format_semantic_memories(self, semantic: list[SemanticMemory]) -> str:
        """Format semantic memories for LLM prompt."""
        if not semantic:
            return "(None)"

        lines = []
        for i, memory in enumerate(semantic[:20], 1):  # Limit to 20
            entities_str = ", ".join(memory.entities[:3])
            confirmations = memory.confirmation_count
            lines.append(
                f"{i}. [{entities_str}] {memory.content} "
                f"(confidence: {memory.confidence:.2f}, importance: {memory.importance:.2f}, confirmations: {confirmations}x)"
            )

        return "\n".join(lines)

    async def _store_summary(
        self, user_id: str, scope: ConsolidationScope, summary_data: SummaryData
    ) -> MemorySummary:
        """Store synthesized summary.

        Args:
            user_id: User identifier
            scope: Consolidation scope
            summary_data: Synthesized summary data

        Returns:
            Stored memory summary
        """
        # Create summary entity
        summary = MemorySummary(
            user_id=user_id,
            scope_type=scope.type,
            scope_identifier=scope.identifier,
            summary_text=summary_data.summary_text,
            key_facts={k: v.to_dict() for k, v in summary_data.key_facts.items()},
            source_data={
                "interaction_patterns": summary_data.interaction_patterns,
                "needs_validation": summary_data.needs_validation,
            },
            confidence=heuristics.CONFIDENCE_LLM_SYNTHESIS,  # Base confidence for LLM synthesis
            created_at=datetime.now(UTC),
        )

        # Generate embedding
        embedding = await self._embedding_service.generate_embedding(summary.summary_text)
        summary.embedding = embedding

        # Store in repository
        stored = await self._summary_repo.create(summary)

        logger.info(
            "summary_stored",
            summary_id=stored.summary_id,
            user_id=user_id,
            scope=scope.to_dict(),
        )

        return stored

    async def _boost_confirmed_facts(self, confirmed_memory_ids: list[int]) -> None:
        """Boost confidence of confirmed facts.

        Args:
            confirmed_memory_ids: Memory IDs to boost confidence for
        """
        if not confirmed_memory_ids:
            return

        boost_amount = heuristics.CONSOLIDATION_BOOST

        for memory_id in confirmed_memory_ids:
            try:
                # Fetch semantic memory
                memory = await self._semantic_repo.find_by_id(memory_id)
                if not memory:
                    logger.warning("memory_not_found_for_boost", memory_id=memory_id)
                    continue

                # Boost confidence
                new_confidence = min(heuristics.MAX_CONFIDENCE, memory.confidence + boost_amount)
                memory.confidence = new_confidence

                # Mark as validated in metadata
                memory.metadata["last_validated_at"] = datetime.now(UTC).isoformat()
                memory.updated_at = datetime.now(UTC)

                # Update
                await self._semantic_repo.update(memory)

                logger.debug(
                    "confidence_boosted",
                    memory_id=memory_id,
                    old_confidence=memory.confidence - boost_amount,
                    new_confidence=new_confidence,
                )

            except Exception as e:
                logger.error(
                    "boost_confidence_error",
                    memory_id=memory_id,
                    error=str(e),
                )
                # Continue with other memories

    async def _create_fallback_summary(
        self,
        user_id: str,
        scope: ConsolidationScope,
        episodic: list[MemoryCandidate],
        semantic: list[SemanticMemory],
    ) -> MemorySummary:
        """Create basic summary without LLM (fallback).

        Args:
            user_id: User identifier
            scope: Consolidation scope
            episodic: Episodic memories
            semantic: Semantic memories

        Returns:
            Basic memory summary
        """
        logger.warning(
            "creating_fallback_summary",
            user_id=user_id,
            scope=scope.to_dict(),
        )

        # Create basic key facts from high-confidence semantic memories
        key_facts = {}
        for memory in semantic:
            if memory.confidence > heuristics.CONFIDENCE_FUZZY_LOW:
                fact_name = f"fact_{memory.memory_id}"
                key_facts[fact_name] = {
                    "value": memory.content,
                    "confidence": memory.confidence,
                    "reinforced": memory.confirmation_count,
                    "source_memory_ids": memory.source_event_ids,
                }

        summary_text = (
            f"Summary for {scope.identifier}: "
            f"{len(episodic)} episodes, {len(key_facts)} confirmed facts"
        )

        summary = MemorySummary(
            user_id=user_id,
            scope_type=scope.type,
            scope_identifier=scope.identifier,
            summary_text=summary_text,
            key_facts=key_facts,
            source_data={
                "episodic_count": len(episodic),
                "semantic_count": len(semantic),
                "fallback": True,  # Flag that this is a fallback summary
            },
            confidence=heuristics.CONFIDENCE_FALLBACK,  # Lower confidence for fallback
            created_at=datetime.now(UTC),
        )

        # Generate embedding
        embedding = await self._embedding_service.generate_embedding(summary.summary_text)
        summary.embedding = embedding

        # Store
        stored = await self._summary_repo.create(summary)

        logger.info(
            "fallback_summary_created",
            summary_id=stored.summary_id,
            user_id=user_id,
        )

        return stored
