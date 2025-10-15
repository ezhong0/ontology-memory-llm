"""Memory validation domain service.

Responsible for managing semantic memory lifecycle: confidence decay,
reinforcement from repeated observations, and validation tracking.
"""

import logging
import math
from datetime import datetime, timezone

from src.domain.entities.semantic_memory import SemanticMemory
from src.domain.value_objects import SemanticTriple

logger = logging.getLogger(__name__)


class MemoryValidationService:
    """Domain service for semantic memory validation and lifecycle management.

    This service handles:
    - Temporal confidence decay (memories fade over time)
    - Reinforcement from repeated observations
    - Validation tracking

    Design:
    - Decay rate: 0.01 per day (memories decay slowly)
    - Max confidence: 0.95 (never 100% certain)
    - Reinforcement boost: 0.05 per observation
    """

    # Configuration constants
    DECAY_RATE_PER_DAY = 0.01  # 1% decay per day
    REINFORCEMENT_BOOST = 0.05  # 5% boost per reinforcement
    MAX_CONFIDENCE = 0.95  # Cap at 95% confidence
    MIN_CONFIDENCE = 0.0  # Floor at 0% confidence

    def __init__(
        self,
        decay_rate: float = DECAY_RATE_PER_DAY,
        reinforcement_boost: float = REINFORCEMENT_BOOST,
    ) -> None:
        """Initialize validation service.

        Args:
            decay_rate: Confidence decay rate per day (default: 0.01)
            reinforcement_boost: Confidence boost per reinforcement (default: 0.05)
        """
        self._decay_rate = decay_rate
        self._reinforcement_boost = reinforcement_boost

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
            current_date = datetime.now(timezone.utc)

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
        decayed_confidence = max(self.MIN_CONFIDENCE, decayed_confidence)

        logger.debug(
            "Calculated confidence decay",
            extra={
                "memory_id": memory.memory_id,
                "days_elapsed": days_elapsed,
                "original_confidence": memory.confidence,
                "decayed_confidence": decayed_confidence,
            },
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
            raise ValueError(
                f"Subject mismatch: {new_observation.subject_entity_id} "
                f"!= {memory.subject_entity_id}"
            )

        if new_observation.predicate != memory.predicate:
            raise ValueError(
                f"Predicate mismatch: {new_observation.predicate} "
                f"!= {memory.predicate}"
            )

        # Apply reinforcement (uses entity method)
        old_confidence = memory.confidence
        memory.reinforce(
            new_event_id=event_id,
            confidence_boost=self._reinforcement_boost,
        )

        logger.info(
            "Memory reinforced",
            extra={
                "memory_id": memory.memory_id,
                "subject": memory.subject_entity_id,
                "predicate": memory.predicate,
                "old_confidence": old_confidence,
                "new_confidence": memory.confidence,
                "reinforcement_count": memory.reinforcement_count,
            },
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
            current_date = datetime.now(timezone.utc)

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
                "Confidence decay applied",
                extra={
                    "memory_id": memory.memory_id,
                    "old_confidence": old_confidence,
                    "new_confidence": memory.confidence,
                },
            )
            return True

        return False

    def should_deactivate(
        self,
        memory: SemanticMemory,
        min_confidence_threshold: float = 0.3,
    ) -> bool:
        """Check if memory should be deactivated due to low confidence.

        Args:
            memory: Memory to check
            min_confidence_threshold: Minimum confidence to remain active (default: 0.3)

        Returns:
            True if memory should be deactivated
        """
        return memory.confidence < min_confidence_threshold
