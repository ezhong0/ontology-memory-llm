"""Conflict resolution domain service.

Responsible for resolving detected conflicts between semantic memories
using explicit resolution strategies.

Phase 2.1: Conflict Resolution Strategies
Vision Principle: Epistemic Humility - System explicitly resolves conflicts
rather than silently preferring one value.
"""

from dataclasses import dataclass
from typing import Optional

import structlog

from src.domain.entities import SemanticMemory
from src.domain.ports import ISemanticMemoryRepository
from src.domain.value_objects import (
    ConflictResolution,
    MemoryConflict,
)

logger = structlog.get_logger(__name__)


@dataclass
class ResolutionResult:
    """Result of conflict resolution.

    Attributes:
        winning_memory_id: ID of memory that won (or None for DB/ask_user)
        losing_memory_id: ID of memory that lost (or None for ask_user)
        strategy_used: Resolution strategy applied
        rationale: Human-readable explanation
        action: Action taken (supersede, invalidate, ask_user)
    """

    winning_memory_id: int | None
    losing_memory_id: int | None
    strategy_used: ConflictResolution
    rationale: str
    action: str  # "supersede" | "invalidate" | "ask_user"


class ConflictResolutionService:
    """Domain service for resolving memory conflicts.

    Vision Principle: Epistemic Humility - System explicitly tracks and resolves
    conflicts rather than silently preferring one value over another.

    Resolution Strategies:
    - TRUST_DB: Database is authoritative (Correspondence Truth)
    - TRUST_RECENT: Most recent observation wins (temporal resolution)
    - TRUST_REINFORCED: Most reinforced memory wins (confidence in repetition)
    - ASK_USER: Conflict too ambiguous, require user clarification
    """

    def __init__(
        self,
        semantic_memory_repository: ISemanticMemoryRepository,
    ) -> None:
        """Initialize conflict resolution service.

        Args:
            semantic_memory_repository: Repository for semantic memory persistence
        """
        self.semantic_memory_repo = semantic_memory_repository

    async def resolve_conflict(
        self,
        conflict: MemoryConflict,
        strategy: ConflictResolution | None = None,
    ) -> ResolutionResult:
        """Resolve a detected conflict using specified strategy.

        Args:
            conflict: The detected conflict to resolve
            strategy: Resolution strategy (uses conflict's recommended if None)

        Returns:
            ResolutionResult with outcome and actions taken

        Raises:
            ValueError: If conflict type or strategy is unsupported
        """
        # Use recommended strategy if not overridden
        if strategy is None:
            strategy = conflict.recommended_resolution

        logger.info(
            "resolving_conflict",
            conflict_id=conflict.existing_memory_id,
            conflict_type=conflict.conflict_type.value,
            strategy=strategy.value,
        )

        # Route to appropriate resolution handler
        if strategy == ConflictResolution.TRUST_DB:
            return await self._resolve_trust_db(conflict)
        elif strategy == ConflictResolution.KEEP_NEWEST:
            return await self._resolve_keep_newest(conflict)
        elif strategy == ConflictResolution.KEEP_HIGHEST_CONFIDENCE:
            return await self._resolve_keep_highest_confidence(conflict)
        elif strategy == ConflictResolution.KEEP_MOST_REINFORCED:
            return await self._resolve_keep_most_reinforced(conflict)
        elif strategy == ConflictResolution.REQUIRE_CLARIFICATION:
            return await self._resolve_ask_user(conflict)
        else:
            msg = f"Unsupported resolution strategy: {strategy}"
            raise ValueError(msg)

    async def _resolve_trust_db(self, conflict: MemoryConflict) -> ResolutionResult:
        """Resolve memory vs DB conflict - always trust database.

        Philosophy: Database is Correspondence Truth (authoritative facts),
        Memory is Contextual Truth (interpretive understanding).
        When they conflict, database wins.

        Args:
            conflict: Memory vs DB conflict

        Returns:
            ResolutionResult with memory invalidated
        """
        memory_id = conflict.existing_memory_id

        # Fetch and invalidate memory
        memory = await self.semantic_memory_repo.get_by_id(memory_id)
        if not memory:
            msg = f"Memory {memory_id} not found"
            raise ValueError(msg)

        memory.mark_as_invalidated()
        await self.semantic_memory_repo.update(memory)

        logger.info(
            "conflict_resolved_trust_db",
            memory_id=memory_id,
            action="invalidated",
        )

        return ResolutionResult(
            winning_memory_id=None,  # DB wins (not a memory)
            losing_memory_id=memory_id,
            strategy_used=ConflictResolution.TRUST_DB,
            rationale="Database is authoritative source of truth (Correspondence Truth)",
            action="invalidate",
        )

    async def _resolve_keep_newest(self, conflict: MemoryConflict) -> ResolutionResult:
        """Resolve by trusting more recent memory.

        Rationale: More recent information supersedes older information.
        Assumption: User's most recent statement reflects current state.

        Args:
            conflict: Memory vs memory conflict with temporal difference

        Returns:
            ResolutionResult with older memory superseded
        """
        # Determine which is newer based on temporal_diff_days
        # Positive = new is newer, Negative = existing is newer
        if conflict.temporal_diff_days and conflict.temporal_diff_days > 0:
            # New is newer - mark existing as superseded
            winner_id = conflict.new_memory_id
            loser_id = conflict.existing_memory_id
        else:
            # Existing is newer or same age - keep existing
            winner_id = conflict.existing_memory_id
            loser_id = conflict.new_memory_id

        # Mark loser as superseded (if both exist)
        if loser_id:
            loser = await self.semantic_memory_repo.get_by_id(loser_id)
            if loser and winner_id:
                loser.mark_as_superseded(superseded_by_memory_id=winner_id)
                await self.semantic_memory_repo.update(loser)

        logger.info(
            "conflict_resolved_keep_newest",
            winner_id=winner_id,
            loser_id=loser_id,
            temporal_diff=conflict.temporal_diff_days,
        )

        return ResolutionResult(
            winning_memory_id=winner_id,
            losing_memory_id=loser_id,
            strategy_used=ConflictResolution.KEEP_NEWEST,
            rationale="More recent information supersedes older",
            action="supersede",
        )

    async def _resolve_keep_highest_confidence(
        self, conflict: MemoryConflict
    ) -> ResolutionResult:
        """Resolve by trusting memory with highest confidence.

        Rationale: Higher confidence indicates more reliable information.

        Args:
            conflict: Memory vs memory conflict with confidence difference

        Returns:
            ResolutionResult with lower confidence memory superseded
        """
        # Positive confidence_diff = new is higher
        if conflict.confidence_diff > 0:
            winner_id = conflict.new_memory_id
            loser_id = conflict.existing_memory_id
        else:
            winner_id = conflict.existing_memory_id
            loser_id = conflict.new_memory_id

        # Mark loser as superseded
        if loser_id and winner_id:
            loser = await self.semantic_memory_repo.get_by_id(loser_id)
            if loser:
                loser.mark_as_superseded(superseded_by_memory_id=winner_id)
                await self.semantic_memory_repo.update(loser)

        logger.info(
            "conflict_resolved_keep_highest_confidence",
            winner_id=winner_id,
            loser_id=loser_id,
            confidence_diff=conflict.confidence_diff,
        )

        return ResolutionResult(
            winning_memory_id=winner_id,
            losing_memory_id=loser_id,
            strategy_used=ConflictResolution.KEEP_HIGHEST_CONFIDENCE,
            rationale="Higher confidence indicates more reliable information",
            action="supersede",
        )

    async def _resolve_keep_most_reinforced(
        self, conflict: MemoryConflict
    ) -> ResolutionResult:
        """Resolve by trusting most reinforced memory.

        Rationale: More reinforcements indicate more frequently confirmed information.

        Args:
            conflict: Memory vs memory conflict with reinforcement difference

        Returns:
            ResolutionResult with less reinforced memory superseded
        """
        existing_reinforcement = conflict.metadata.get(
            "existing_reinforcement_count", 1
        )
        new_reinforcement = conflict.metadata.get("new_reinforcement_count", 1)

        # Compare reinforcement counts
        if new_reinforcement > existing_reinforcement:
            winner_id = conflict.new_memory_id
            loser_id = conflict.existing_memory_id
        else:
            winner_id = conflict.existing_memory_id
            loser_id = conflict.new_memory_id

        # Mark loser as superseded
        if loser_id and winner_id:
            loser = await self.semantic_memory_repo.get_by_id(loser_id)
            if loser:
                loser.mark_as_superseded(superseded_by_memory_id=winner_id)
                await self.semantic_memory_repo.update(loser)

        logger.info(
            "conflict_resolved_keep_most_reinforced",
            winner_id=winner_id,
            loser_id=loser_id,
            existing_reinforcement=existing_reinforcement,
            new_reinforcement=new_reinforcement,
        )

        return ResolutionResult(
            winning_memory_id=winner_id,
            losing_memory_id=loser_id,
            strategy_used=ConflictResolution.KEEP_MOST_REINFORCED,
            rationale="More frequently confirmed information preferred",
            action="supersede",
        )

    async def _resolve_ask_user(self, conflict: MemoryConflict) -> ResolutionResult:
        """Resolve by asking user - don't auto-resolve ambiguous conflicts.

        Rationale: System admits uncertainty and requires user clarification.

        Args:
            conflict: Ambiguous conflict requiring clarification

        Returns:
            ResolutionResult indicating user clarification needed
        """
        logger.info(
            "conflict_requires_user_clarification",
            existing_memory_id=conflict.existing_memory_id,
            new_memory_id=conflict.new_memory_id,
        )

        return ResolutionResult(
            winning_memory_id=None,
            losing_memory_id=None,
            strategy_used=ConflictResolution.REQUIRE_CLARIFICATION,
            rationale="Conflict is ambiguous - require user clarification",
            action="ask_user",
        )
