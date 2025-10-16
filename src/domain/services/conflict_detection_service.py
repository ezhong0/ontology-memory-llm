"""Conflict detection domain service.

Responsible for detecting conflicts between new semantic observations
and existing memories in the knowledge base.
"""

from datetime import datetime
from typing import Any

import structlog

from src.config import heuristics
from src.domain.entities.semantic_memory import SemanticMemory
from src.domain.value_objects import (
    ConflictResolution,
    ConflictType,
    DomainFact,
    MemoryConflict,
    SemanticTriple,
)

logger = structlog.get_logger(__name__)


class ConflictDetectionService:
    """Domain service for detecting memory conflicts.

    This service identifies conflicts when:
    - Same subject + predicate, different object values
    - Temporal inconsistencies (contradictory time-based statements)
    - Logical contradictions (mutually exclusive states)

    Resolution Strategy:
    1. Temporal: Most recent wins (>30 days difference)
    2. Confidence: Highest confidence wins (>0.2 difference)
    3. Reinforcement: Most reinforced wins (>3 observations difference)
    4. Default: Require user clarification
    """

    def __init__(
        self,
        temporal_threshold_days: int | None = None,
        confidence_threshold: float | None = None,
        reinforcement_threshold: int | None = None,
    ) -> None:
        """Initialize conflict detection service.

        Args:
            temporal_threshold_days: Days difference for temporal resolution (defaults to heuristics)
            confidence_threshold: Confidence difference for resolution (defaults to heuristics)
            reinforcement_threshold: Reinforcement count difference for resolution (defaults to heuristics)
        """
        self._temporal_threshold = temporal_threshold_days or heuristics.CONFLICT_TEMPORAL_THRESHOLD_DAYS
        self._confidence_threshold = confidence_threshold or heuristics.CONFLICT_CONFIDENCE_THRESHOLD
        self._reinforcement_threshold = reinforcement_threshold or heuristics.CONFLICT_REINFORCEMENT_THRESHOLD

    def detect_conflict(
        self,
        new_triple: SemanticTriple,
        existing_memory: SemanticMemory,
        new_memory_id: int | None = None,
    ) -> MemoryConflict | None:
        """Detect conflict between new triple and existing memory.

        Args:
            new_triple: New semantic triple observation
            existing_memory: Existing memory to check against
            new_memory_id: ID of new memory if already stored (optional)

        Returns:
            MemoryConflict if conflict detected, None otherwise

        Raises:
            ValueError: If triple and memory don't share subject+predicate
        """
        # Validate they're for the same subject + predicate
        if new_triple.subject_entity_id != existing_memory.subject_entity_id:
            msg = "Subject mismatch - cannot detect conflict"
            raise ValueError(msg)

        if new_triple.predicate != existing_memory.predicate:
            msg = "Predicate mismatch - cannot detect conflict"
            raise ValueError(msg)

        # Check if values actually conflict
        if not self._values_conflict(new_triple.object_value, existing_memory.object_value):
            logger.debug(
                "no_conflict_values_match",
                subject=new_triple.subject_entity_id,
                predicate=new_triple.predicate,
            )
            return None

        # Determine conflict type
        conflict_type = self._classify_conflict(new_triple, existing_memory)

        # Calculate metrics for resolution
        confidence_diff = new_triple.confidence - existing_memory.confidence
        temporal_diff_days = self._calculate_temporal_diff(new_triple, existing_memory)

        # Recommend resolution strategy
        resolution = self._recommend_resolution(
            new_triple=new_triple,
            existing_memory=existing_memory,
            confidence_diff=confidence_diff,
            temporal_diff_days=temporal_diff_days,
        )

        # Build conflict metadata
        metadata = {
            "new_confidence": new_triple.confidence,
            "existing_confidence": existing_memory.confidence,
            "new_reinforcement_count": 1,
            "existing_reinforcement_count": existing_memory.reinforcement_count,
            "new_source": new_triple.metadata.get("source_event_id"),
            "existing_sources": existing_memory.source_event_ids,
        }

        conflict = MemoryConflict(
            conflict_type=conflict_type,
            new_memory_id=new_memory_id,
            existing_memory_id=existing_memory.memory_id or 0,
            subject_entity_id=new_triple.subject_entity_id,
            predicate=new_triple.predicate,
            new_value=new_triple.object_value,
            existing_value=existing_memory.object_value,
            recommended_resolution=resolution,
            confidence_diff=confidence_diff,
            temporal_diff_days=temporal_diff_days,
            metadata=metadata,
        )

        logger.warning(
            "conflict_detected",
            conflict_type=conflict_type.value,
            subject=new_triple.subject_entity_id,
            predicate=new_triple.predicate,
            resolution=resolution.value,
        )

        return conflict

    def _values_conflict(
        self,
        value1: dict[str, Any],
        value2: dict[str, Any],
    ) -> bool:
        """Check if two object values conflict.

        Args:
            value1: First object value
            value2: Second object value

        Returns:
            True if values conflict (are different)
        """
        # Simple value comparison - can be enhanced for complex logic
        # Extract the main value field
        v1 = value1.get("value")
        v2 = value2.get("value")

        if v1 is None or v2 is None:
            # If no value field, compare entire dicts
            return bool(value1 != value2)

        return bool(v1 != v2)

    def _classify_conflict(
        self,
        new_triple: SemanticTriple,
        existing_memory: SemanticMemory,
    ) -> ConflictType:
        """Classify the type of conflict.

        Args:
            new_triple: New observation
            existing_memory: Existing memory

        Returns:
            Conflict type classification
        """
        # For now, use simple classification
        # Can be enhanced with domain-specific logic

        # Check for temporal inconsistency (e.g., ordered → cancelled → ordered)
        if new_triple.predicate_type.value == "action":
            return ConflictType.TEMPORAL_INCONSISTENCY

        # Default to value mismatch
        return ConflictType.VALUE_MISMATCH

    def _calculate_temporal_diff(
        self,
        new_triple: SemanticTriple,
        existing_memory: SemanticMemory,
    ) -> int | None:
        """Calculate temporal difference in days.

        Args:
            new_triple: New observation
            existing_memory: Existing memory

        Returns:
            Days difference (new - existing), or None if can't calculate
        """
        # Extract timestamps from metadata/created_at
        new_timestamp_str = new_triple.metadata.get("extraction_timestamp")
        if not new_timestamp_str:
            return None

        try:
            new_timestamp = datetime.fromisoformat(new_timestamp_str)
        except (ValueError, TypeError):
            return None

        existing_timestamp = existing_memory.created_at

        # Calculate difference
        delta = new_timestamp - existing_timestamp
        return delta.days

    def _recommend_resolution(
        self,
        new_triple: SemanticTriple,
        existing_memory: SemanticMemory,
        confidence_diff: float,
        temporal_diff_days: int | None,
    ) -> ConflictResolution:
        """Recommend conflict resolution strategy.

        Resolution priority:
        1. Temporal: Most recent wins (>30 days difference)
        2. Confidence: Highest confidence wins (>0.2 difference)
        3. Reinforcement: Most reinforced wins (>3 observations difference)
        4. Default: Require clarification

        Args:
            new_triple: New observation
            existing_memory: Existing memory
            confidence_diff: Confidence difference (new - existing)
            temporal_diff_days: Temporal difference in days

        Returns:
            Recommended resolution strategy
        """
        # Strategy 1: Temporal resolution
        if temporal_diff_days is not None and abs(temporal_diff_days) >= self._temporal_threshold:
            return ConflictResolution.KEEP_NEWEST

        # Strategy 2: Confidence resolution
        if abs(confidence_diff) >= self._confidence_threshold:
            return ConflictResolution.KEEP_HIGHEST_CONFIDENCE

        # Strategy 3: Reinforcement resolution
        reinforcement_diff = 1 - existing_memory.reinforcement_count  # New always has count=1
        if abs(reinforcement_diff) >= self._reinforcement_threshold:
            return ConflictResolution.KEEP_MOST_REINFORCED

        # Default: Require user clarification
        return ConflictResolution.REQUIRE_CLARIFICATION

    def detect_memory_vs_db_conflict(
        self,
        memory: SemanticMemory,
        domain_fact: DomainFact,
    ) -> MemoryConflict | None:
        """Detect conflict between semantic memory and authoritative database fact.

        Philosophy: Database is Correspondence Truth (authoritative facts),
        Memory is Contextual Truth (interpretive understanding).
        When they conflict, DB wins.

        Args:
            memory: Semantic memory to check
            domain_fact: Domain fact from authoritative database

        Returns:
            MemoryConflict if conflict detected, None otherwise
        """
        # Check if they're about the same entity
        if memory.subject_entity_id != domain_fact.entity_id:
            return None

        # Map fact_type to predicate
        # For now, simple mapping for common cases
        predicate_map = {
            "order_status": "status",
            "invoice_status": "status",
            "work_order_status": "status",
        }

        inferred_predicate = predicate_map.get(domain_fact.fact_type)
        if not inferred_predicate or inferred_predicate != memory.predicate:
            return None

        # Extract value from domain fact metadata
        # For status facts, value is in metadata["status"]
        db_value = None
        if domain_fact.fact_type.endswith("_status"):
            db_value = domain_fact.metadata.get("status")

        if db_value is None:
            return None

        # Compare values
        memory_value = memory.object_value.get("value")
        if memory_value == db_value:
            # No conflict
            return None

        # Conflict detected: Memory disagrees with DB
        logger.warning(
            "memory_vs_db_conflict_detected",
            entity_id=memory.subject_entity_id,
            predicate=memory.predicate,
            memory_value=memory_value,
            db_value=db_value,
        )

        # Build conflict
        conflict = MemoryConflict(
            conflict_type=ConflictType.MEMORY_VS_DB,
            new_memory_id=None,  # DB fact, not a memory
            existing_memory_id=memory.memory_id or 0,
            subject_entity_id=memory.subject_entity_id,
            predicate=memory.predicate,
            new_value={"type": "status", "value": db_value},
            existing_value=memory.object_value,
            recommended_resolution=ConflictResolution.TRUST_DB,
            confidence_diff=1.0,  # DB has 100% confidence (authoritative)
            temporal_diff_days=None,
            metadata={
                "db_fact_type": domain_fact.fact_type,
                "db_source_table": domain_fact.source_table,
                "memory_confidence": memory.confidence,
                "rationale": "Database is authoritative source of truth (Correspondence Truth)",
            },
        )

        return conflict
