"""Consolidation trigger service.

Determines when memory consolidation should occur based on thresholds.

Design from: PHASE1D_PLAN_ITERATION.md
"""


import structlog

from src.config import heuristics
from src.domain.exceptions import DomainError
from src.domain.ports.chat_repository import IChatEventRepository
from src.domain.ports.episodic_memory_repository import IEpisodicMemoryRepository
from src.domain.value_objects.consolidation import ConsolidationScope

logger = structlog.get_logger()


class ConsolidationTriggerService:
    """Determines when consolidation should occur.

    Checks thresholds to decide if consolidation is needed:
    - Entity scope: N+ episodic memories about entity
    - Session window: M+ completed sessions
    - Topic scope: K+ semantic memories with predicate pattern

    Philosophy: Consolidation is periodic, not per-request.
    Consolidation happens in background when thresholds are met.

    Example:
        >>> trigger_service = ConsolidationTriggerService(episodic_repo, chat_repo)
        >>> should = await trigger_service.should_consolidate(
        ...     user_id="user_1",
        ...     scope=ConsolidationScope.entity_scope("customer_gai_123")
        ... )
        >>> if should:
        ...     # Trigger background consolidation
    """

    def __init__(
        self,
        episodic_repo: IEpisodicMemoryRepository,
        chat_repo: IChatEventRepository,
    ) -> None:
        """Initialize consolidation trigger service.

        Args:
            episodic_repo: Repository for episodic memories
            chat_repo: Repository for chat events (for session counting)
        """
        self._episodic_repo = episodic_repo
        self._chat_repo = chat_repo

    async def should_consolidate(
        self,
        user_id: str,
        scope: ConsolidationScope,
    ) -> bool:
        """Check if consolidation thresholds are met.

        Args:
            user_id: User identifier
            scope: Consolidation scope to check

        Returns:
            True if consolidation should occur

        Raises:
            DomainError: If threshold check fails
        """
        try:
            logger.debug(
                "checking_consolidation_threshold",
                user_id=user_id,
                scope_type=scope.type,
                scope_identifier=scope.identifier,
            )

            if scope.type == "entity":
                return await self._should_consolidate_entity(user_id, scope.identifier)

            elif scope.type == "session_window":
                return await self._should_consolidate_session_window(
                    user_id, int(scope.identifier)
                )

            elif scope.type == "topic":
                # Topic consolidation is more specialized (Phase 2+)
                # For Phase 1, return False
                return False

            else:
                logger.warning("unknown_scope_type", scope_type=scope.type)
                return False

        except Exception as e:
            logger.error(
                "consolidation_threshold_check_error",
                user_id=user_id,
                scope=scope.to_dict(),
                error=str(e),
            )
            msg = f"Error checking consolidation threshold: {e}"
            raise DomainError(msg) from e

    async def _should_consolidate_entity(self, user_id: str, entity_id: str) -> bool:
        """Check if entity should be consolidated.

        Threshold: CONSOLIDATION_MIN_EPISODIC+ episodic memories about entity.

        Args:
            user_id: User identifier
            entity_id: Entity identifier

        Returns:
            True if threshold met
        """
        # For Phase 1, simplified: check recent episodic memories
        # In production, would have a specific query for entity-filtered count

        # Simplified implementation: Always return False for Phase 1
        # In Phase 1D integration, we'll implement proper counting
        # For now, manual trigger via API will work

        logger.debug(
            "entity_consolidation_check",
            user_id=user_id,
            entity_id=entity_id,
            threshold=heuristics.CONSOLIDATION_MIN_EPISODIC,
        )

        # Phase 1D: Automatic triggering deferred - requires count_by_entity() repository method
        # Implementation:
        # count = await self._episodic_repo.count_by_entity(user_id, entity_id)
        # return count >= heuristics.CONSOLIDATION_MIN_EPISODIC
        #
        # For Phase 1, consolidation is triggered manually via API endpoint
        return False

    async def _should_consolidate_session_window(
        self, user_id: str, num_sessions: int
    ) -> bool:
        """Check if session window should be consolidated.

        Threshold: CONSOLIDATION_MIN_SESSIONS+ completed sessions.

        Args:
            user_id: User identifier
            num_sessions: Number of sessions in window

        Returns:
            True if threshold met
        """
        # Count recent sessions
        # For Phase 1, simplified: always return False (manual trigger)

        logger.debug(
            "session_window_consolidation_check",
            user_id=user_id,
            num_sessions=num_sessions,
            threshold=heuristics.CONSOLIDATION_MIN_SESSIONS,
        )

        # Phase 1D: Automatic triggering deferred - requires count_recent_sessions() repository method
        # Implementation:
        # sessions = await self._chat_repo.count_recent_sessions(user_id)
        # return sessions >= heuristics.CONSOLIDATION_MIN_SESSIONS
        #
        # For Phase 1, consolidation is triggered manually via API endpoint
        return False

    async def get_pending_consolidations(self, user_id: str) -> list[ConsolidationScope]:
        """Get all scopes that need consolidation.

        Scans user's interaction history to find scopes meeting thresholds.

        Args:
            user_id: User identifier

        Returns:
            List of consolidation scopes needing attention

        Raises:
            DomainError: If scan fails
        """
        try:
            logger.info("scanning_pending_consolidations", user_id=user_id)

            pending: list[ConsolidationScope] = []

            # Check session window
            if await self._should_consolidate_session_window(
                user_id, heuristics.CONSOLIDATION_SESSION_WINDOW_DEFAULT
            ):
                pending.append(
                    ConsolidationScope.session_window_scope(
                        heuristics.CONSOLIDATION_SESSION_WINDOW_DEFAULT
                    )
                )

            # Phase 1D: Entity scanning deferred - requires _get_active_entities() method
            # Implementation:
            # entities = await self._get_active_entities(user_id)
            # for entity_id in entities:
            #     if await self._should_consolidate_entity(user_id, entity_id):
            #         pending.append(ConsolidationScope.entity_scope(entity_id))
            #
            # For Phase 1, only session window consolidation is checked

            logger.info(
                "pending_consolidations_found",
                user_id=user_id,
                count=len(pending),
            )

            return pending

        except Exception as e:
            logger.error(
                "scan_pending_consolidations_error",
                user_id=user_id,
                error=str(e),
            )
            msg = f"Error scanning pending consolidations: {e}"
            raise DomainError(msg) from e
