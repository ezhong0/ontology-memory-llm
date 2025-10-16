"""Memory validation domain service.

Responsible for managing semantic memory lifecycle: confidence decay,
reinforcement from repeated observations, and validation tracking.
"""

import math
from datetime import UTC, datetime

import structlog

from src.config import heuristics
from src.domain.entities.semantic_memory import SemanticMemory
from src.domain.value_objects import SemanticTriple

logger = structlog.get_logger(__name__)


class MemoryValidationService:
    """Domain service for semantic memory validation and lifecycle management.

    This service handles:
    - Temporal confidence decay (memories fade over time)
    - Reinforcement from repeated observations
    - Validation tracking

    Design:
    - Decay rate: Loaded from heuristics (calibrated in Phase 2)
    - Max confidence: 0.95 (never 100% certain - epistemic humility)
    - Reinforcement boost: Loaded from heuristics with diminishing returns
    """

    def __init__(
        self,
        decay_rate: float | None = None,
        reinforcement_boost: float | None = None,
    ) -> None:
        """Initialize validation service.

        Args:
            decay_rate: Confidence decay rate per day (defaults to heuristics)
            reinforcement_boost: Confidence boost per reinforcement (defaults to heuristics)
        """
        self._decay_rate = decay_rate or heuristics.DECAY_RATE_PER_DAY
        self._reinforcement_boost = reinforcement_boost or heuristics.REINFORCEMENT_BOOSTS[0]
        self._max_confidence = heuristics.MAX_CONFIDENCE
        self._min_confidence = 0.0  # Conceptual floor

    def calculate_confidence_decay(
        self,
        memory: SemanticMemory,
        current_date: datetime | None = None,
    ) -> float:
        """Calculate decayed confidence based on time since last validation.

        Uses exponential decay formula:
            confidence(t) = initial_confidence * exp(-decay_rate * days)

        Args:
            memory: Semantic memory to calculate decay for
            current_date: Current datetime (defaults to now)

        Returns:
            Decayed confidence value [0.0, 1.0]
        """
        if current_date is None:
            current_date = datetime.now(UTC)

        # If never validated, use creation date
        last_validation = memory.last_validated_at or memory.created_at

        # Calculate days since last validation
        time_delta = current_date - last_validation
        days_elapsed = time_delta.total_seconds() / 86400  # seconds per day

        if days_elapsed <= 0:
            return memory.confidence

        # Apply exponential decay
        decay_factor = math.exp(-self._decay_rate * days_elapsed)
        decayed_confidence = memory.confidence * decay_factor

        # Apply floor
        decayed_confidence = max(self._min_confidence, decayed_confidence)

        logger.debug(
            "calculated_confidence_decay",
            memory_id=memory.memory_id,
            days_elapsed=days_elapsed,
            original_confidence=memory.confidence,
            decayed_confidence=decayed_confidence,
        )

        return decayed_confidence

    def reinforce_memory(
        self,
        memory: SemanticMemory,
        new_observation: SemanticTriple,
        event_id: int,
    ) -> None:
        """Reinforce existing memory with new observation.

        Applies confidence boost and updates reinforcement count.
        Modifies the memory entity in-place.

        Args:
            memory: Existing memory to reinforce
            new_observation: New triple observation (same subject + predicate)
            event_id: Chat event ID of new observation

        Raises:
            ValueError: If observation doesn't match memory subject/predicate
        """
        # Validate observation matches memory
        if new_observation.subject_entity_id != memory.subject_entity_id:
            msg = (
                f"Subject mismatch: {new_observation.subject_entity_id} "
                f"!= {memory.subject_entity_id}"
            )
            raise ValueError(
                msg
            )

        if new_observation.predicate != memory.predicate:
            msg = (
                f"Predicate mismatch: {new_observation.predicate} "
                f"!= {memory.predicate}"
            )
            raise ValueError(
                msg
            )

        # Apply reinforcement (uses entity method)
        old_confidence = memory.confidence
        memory.reinforce(
            new_event_id=event_id,
            confidence_boost=self._reinforcement_boost,
        )

        logger.info(
            "memory_reinforced",
            memory_id=memory.memory_id,
            subject=memory.subject_entity_id,
            predicate=memory.predicate,
            old_confidence=old_confidence,
            new_confidence=memory.confidence,
            reinforcement_count=memory.reinforcement_count,
        )

    def apply_decay_if_needed(
        self,
        memory: SemanticMemory,
        current_date: datetime | None = None,
    ) -> bool:
        """Apply confidence decay if memory is stale.

        Args:
            memory: Memory to check and potentially decay
            current_date: Current datetime (defaults to now)

        Returns:
            True if decay was applied, False otherwise
        """
        if current_date is None:
            current_date = datetime.now(UTC)

        # Calculate what confidence should be
        decayed_confidence = self.calculate_confidence_decay(
            memory=memory,
            current_date=current_date,
        )

        # Only apply if confidence actually decreased
        if decayed_confidence < memory.confidence:
            old_confidence = memory.confidence
            memory.apply_decay(decayed_confidence)

            logger.info(
                "confidence_decay_applied",
                memory_id=memory.memory_id,
                old_confidence=old_confidence,
                new_confidence=memory.confidence,
            )
            return True

        return False

    def should_deactivate(
        self,
        memory: SemanticMemory,
        min_confidence_threshold: float | None = None,
    ) -> bool:
        """Check if memory should be deactivated due to low confidence.

        Args:
            memory: Memory to check
            min_confidence_threshold: Minimum confidence to remain active (defaults to heuristics)

        Returns:
            True if memory should be deactivated
        """
        threshold = min_confidence_threshold or heuristics.MIN_CONFIDENCE_FOR_USE
        return memory.confidence < threshold
