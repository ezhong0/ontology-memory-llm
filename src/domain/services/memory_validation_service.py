"""Memory validation domain service.

Responsible for managing semantic memory lifecycle: importance decay,
confirmation from repeated observations, and access tracking.

Entity-Tagged Natural Language Approach:
- Uses importance score (0-1) instead of reinforcement_count
- Tracks last_accessed_at instead of last_validated_at
- Confirms memories with importance boost instead of confidence boost
"""

import math
from datetime import UTC, datetime

import structlog

from src.config import heuristics
from src.domain.entities.semantic_memory import SemanticMemory

logger = structlog.get_logger(__name__)


class MemoryValidationService:
    """Domain service for semantic memory validation and lifecycle management.

    This service handles:
    - Temporal importance decay (memories fade over time)
    - Confirmation from repeated observations (importance boost)
    - Access tracking

    Design:
    - Decay rate: Loaded from heuristics (calibrated in Phase 2)
    - Max confidence: 0.95 (never 100% certain - epistemic humility)
    - Importance boost: Fixed per confirmation (diminishing returns handled in entity)
    """

    def __init__(
        self,
        decay_rate: float | None = None,
        importance_boost: float | None = None,
    ) -> None:
        """Initialize validation service.

        Args:
            decay_rate: Importance decay rate per day (defaults to heuristics)
            importance_boost: Importance boost per confirmation (default: 0.05)
        """
        self._decay_rate = decay_rate or heuristics.DECAY_RATE_PER_DAY
        self._importance_boost = importance_boost or 0.05  # Fixed boost per confirmation
        self._max_confidence = heuristics.MAX_CONFIDENCE
        self._min_importance = 0.0  # Conceptual floor

    def calculate_importance_decay(
        self,
        memory: SemanticMemory,
        current_date: datetime | None = None,
    ) -> float:
        """Calculate decayed importance based on time since last access.

        Uses exponential decay formula with floor at 0.5:
            importance(t) = max(0.5, initial_importance * exp(-decay_rate * days))

        This ensures memories don't completely fade but become less prominent.

        Args:
            memory: Semantic memory to calculate decay for
            current_date: Current datetime (defaults to now)

        Returns:
            Decayed importance value [0.5, 1.0]
        """
        if current_date is None:
            current_date = datetime.now(UTC)

        # Use last_accessed_at (replaces last_validated_at)
        last_access = memory.last_accessed_at or memory.created_at

        # Calculate days since last access
        time_delta = current_date - last_access
        days_elapsed = time_delta.total_seconds() / 86400  # seconds per day

        if days_elapsed <= 0:
            return memory.importance

        # Apply exponential decay with floor at 0.5
        decay_factor = math.exp(-self._decay_rate * days_elapsed)
        decayed_importance = memory.importance * decay_factor

        # Apply floor (memories don't completely fade)
        decayed_importance = max(0.5, decayed_importance)

        logger.debug(
            "calculated_importance_decay",
            memory_id=memory.memory_id,
            days_elapsed=days_elapsed,
            original_importance=memory.importance,
            decayed_importance=decayed_importance,
        )

        return decayed_importance

    def confirm_memory(
        self,
        memory: SemanticMemory,
        new_observation_content: str,
        event_id: int,
        importance_boost: float | None = None,
    ) -> None:
        """Confirm existing memory with new observation.

        Applies importance boost and updates confirmation count.
        Modifies the memory entity in-place.

        Args:
            memory: Existing memory to confirm
            new_observation_content: New observation content (for logging)
            event_id: Chat event ID of new observation
            importance_boost: Custom importance boost (uses default if None)

        Note:
            No validation of content similarity - caller should verify the
            observation is actually confirming the memory before calling this.
        """
        boost = importance_boost or self._importance_boost

        # Apply confirmation (uses entity method)
        old_importance = memory.importance
        old_confirmation_count = memory.confirmation_count

        memory.confirm(
            new_event_id=event_id,
            importance_boost=boost,
        )

        logger.info(
            "memory_confirmed",
            memory_id=memory.memory_id,
            entities=memory.entities,
            content_preview=memory.content[:50],
            old_importance=old_importance,
            new_importance=memory.importance,
            old_confirmation_count=old_confirmation_count,
            new_confirmation_count=memory.confirmation_count,
        )

    def apply_decay_if_needed(
        self,
        memory: SemanticMemory,
        current_date: datetime | None = None,
    ) -> bool:
        """Apply importance decay if memory is stale.

        Args:
            memory: Memory to check and potentially decay
            current_date: Current datetime (defaults to now)

        Returns:
            True if decay was applied, False otherwise
        """
        if current_date is None:
            current_date = datetime.now(UTC)

        # Calculate what importance should be
        decayed_importance = self.calculate_importance_decay(
            memory=memory,
            current_date=current_date,
        )

        # Only apply if importance actually decreased
        if decayed_importance < memory.importance:
            old_importance = memory.importance
            memory.apply_decay(decayed_importance)

            logger.info(
                "importance_decay_applied",
                memory_id=memory.memory_id,
                old_importance=old_importance,
                new_importance=memory.importance,
            )
            return True

        return False

    def should_deactivate(
        self,
        memory: SemanticMemory,
        min_confidence_threshold: float | None = None,
    ) -> bool:
        """Check if memory should be deactivated due to low confidence.

        Note: This checks confidence, not importance. Importance affects
        retrieval priority but doesn't trigger deactivation.

        Args:
            memory: Memory to check
            min_confidence_threshold: Minimum confidence to remain active (defaults to heuristics)

        Returns:
            True if memory should be deactivated
        """
        threshold = min_confidence_threshold or heuristics.MIN_CONFIDENCE_FOR_USE
        return memory.confidence < threshold
