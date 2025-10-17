"""Conflict detection domain service.

Responsible for detecting conflicts between new semantic observations
and existing memories in the knowledge base.

Entity-Tagged Natural Language Approach:
- Conflicts detected via entity overlap + semantic similarity + content contradiction
- No longer relies on predicate matching (triple structure removed)
- Uses embeddings and optional LLM for contradiction detection
"""

from datetime import datetime
from typing import Any

import numpy as np
import structlog

from src.config import heuristics
from src.domain.entities.semantic_memory import SemanticMemory
from src.domain.ports import IEmbeddingService
from src.domain.value_objects import (
    ConflictResolution,
    ConflictType,
    DomainFact,
    MemoryConflict,
)

logger = structlog.get_logger(__name__)


class ConflictDetectionService:
    """Domain service for detecting memory conflicts.

    This service identifies conflicts when:
    - High entity overlap (≥80% shared entities)
    - High semantic similarity (≥0.85 cosine similarity)
    - Content contradiction (different statements about same topic)

    Resolution Strategy:
    1. Temporal: Most recent wins (>30 days difference)
    2. Confidence: Highest confidence wins (>0.2 difference)
    3. Importance: Most important wins (>0.15 difference)
    4. Default: Require user clarification
    """

    def __init__(
        self,
        temporal_threshold_days: int | None = None,
        confidence_threshold: float | None = None,
        importance_threshold: float | None = None,
        entity_overlap_threshold: float | None = None,
        semantic_similarity_threshold: float | None = None,
    ) -> None:
        """Initialize conflict detection service.

        Args:
            temporal_threshold_days: Days difference for temporal resolution
            confidence_threshold: Confidence difference for resolution
            importance_threshold: Importance difference for resolution
            entity_overlap_threshold: Entity overlap ratio to consider conflict
            semantic_similarity_threshold: Semantic similarity threshold
        """
        self._temporal_threshold = temporal_threshold_days or heuristics.CONFLICT_TEMPORAL_THRESHOLD_DAYS
        self._confidence_threshold = confidence_threshold or heuristics.CONFLICT_CONFIDENCE_THRESHOLD
        self._importance_threshold = importance_threshold or heuristics.CONFLICT_IMPORTANCE_THRESHOLD
        self._entity_overlap_threshold = entity_overlap_threshold or heuristics.CONFLICT_ENTITY_OVERLAP_THRESHOLD
        self._semantic_similarity_threshold = (
            semantic_similarity_threshold or heuristics.CONFLICT_SEMANTIC_SIMILARITY_THRESHOLD
        )

    async def detect_semantic_conflict(
        self,
        new_content: str,
        new_entities: list[str],
        existing_memory: SemanticMemory,
        embedding_service: IEmbeddingService,
        new_confidence: float = 0.7,
        new_memory_id: int | None = None,
    ) -> MemoryConflict | None:
        """Detect conflict between new observation and existing memory.

        Uses three-stage detection:
        1. Entity overlap: Are they about the same entities?
        2. Semantic similarity: Are they about the same topic?
        3. Content contradiction: Do they say different things?

        Args:
            new_content: New observation content (natural language)
            new_entities: Entity IDs mentioned in new observation
            existing_memory: Existing memory to check against
            embedding_service: Service for generating embeddings
            new_confidence: Confidence of new observation (default: 0.7)
            new_memory_id: ID of new memory if already stored (optional)

        Returns:
            MemoryConflict if conflict detected, None otherwise
        """
        # Stage 1: Check entity overlap
        entity_overlap = self._calculate_entity_overlap(new_entities, existing_memory.entities)

        if entity_overlap < self._entity_overlap_threshold:
            logger.debug(
                "no_conflict_low_entity_overlap",
                overlap=entity_overlap,
                threshold=self._entity_overlap_threshold,
            )
            return None

        # Stage 2: Check semantic similarity
        new_embedding = await embedding_service.generate_embedding(new_content)
        semantic_similarity = self._calculate_semantic_similarity(
            new_embedding,
            existing_memory.embedding,
        )

        if semantic_similarity < self._semantic_similarity_threshold:
            logger.debug(
                "no_conflict_low_semantic_similarity",
                similarity=semantic_similarity,
                threshold=self._semantic_similarity_threshold,
            )
            return None

        # Stage 3: Check for contradiction
        # For Phase 1: Use simple heuristic - if similarity is high but content differs, it's a conflict
        # For Phase 2: Can enhance with LLM-based contradiction detection
        is_contradiction = await self._detect_contradiction(
            new_content,
            existing_memory.content,
            semantic_similarity,
        )

        if not is_contradiction:
            logger.debug(
                "no_conflict_no_contradiction",
                new_content_preview=new_content[:50],
                existing_content_preview=existing_memory.content[:50],
            )
            return None

        # Conflict detected!
        logger.warning(
            "semantic_conflict_detected",
            entity_overlap=entity_overlap,
            semantic_similarity=semantic_similarity,
            entities=new_entities,
        )

        # Determine conflict type
        conflict_type = self._classify_conflict(new_content, existing_memory.content)

        # Calculate metrics for resolution
        confidence_diff = new_confidence - existing_memory.confidence
        importance_diff = 0.5 - existing_memory.importance  # Assume new has default importance
        temporal_diff_days = self._calculate_temporal_diff(existing_memory)

        # Recommend resolution strategy
        resolution = self._recommend_resolution(
            confidence_diff=confidence_diff,
            importance_diff=importance_diff,
            temporal_diff_days=temporal_diff_days,
        )

        # Get overlapping entities for conflict
        overlapping_entities = list(set(new_entities) & set(existing_memory.entities))

        # Build conflict
        conflict = MemoryConflict(
            conflict_type=conflict_type,
            new_memory_id=new_memory_id,
            existing_memory_id=existing_memory.memory_id or 0,
            entities=overlapping_entities or new_entities,  # Fallback to new_entities
            existing_content=existing_memory.content,
            new_content=new_content,
            recommended_resolution=resolution,
            confidence_diff=confidence_diff,
            temporal_diff_days=temporal_diff_days,
            semantic_similarity=semantic_similarity,
            metadata={
                "new_confidence": new_confidence,
                "existing_confidence": existing_memory.confidence,
                "new_importance": 0.5,  # Default for new observation
                "existing_importance": existing_memory.importance,
                "entity_overlap": entity_overlap,
                "overlapping_entities": overlapping_entities,
                "existing_sources": existing_memory.source_event_ids,
            },
        )

        return conflict

    def _calculate_entity_overlap(
        self,
        entities1: list[str],
        entities2: list[str],
    ) -> float:
        """Calculate entity overlap ratio using Jaccard index.

        Args:
            entities1: First entity list
            entities2: Second entity list

        Returns:
            Jaccard index [0.0, 1.0] = |intersection| / |union|
        """
        if not entities1 or not entities2:
            return 0.0

        set1 = set(entities1)
        set2 = set(entities2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        return intersection / union

    def _calculate_semantic_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """Calculate cosine similarity between embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity [0.0, 1.0]
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Cosine similarity: dot(v1, v2) / (||v1|| * ||v2||)
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

        # Clamp to [0, 1] range (similarity can be negative for opposite vectors)
        return float(max(0.0, min(1.0, similarity)))

    async def _detect_contradiction(
        self,
        content1: str,
        content2: str,
        semantic_similarity: float,
    ) -> bool:
        """Detect if two contents contradict each other.

        Phase 1 implementation: Simple heuristic based on content difference
        Phase 2 enhancement: Use LLM for sophisticated contradiction detection

        Args:
            content1: First content
            content2: Second content
            semantic_similarity: Pre-calculated semantic similarity

        Returns:
            True if contents contradict
        """
        # Phase 1: High similarity but different text = likely contradiction
        # If they're very similar (>0.85) but not identical, assume contradiction
        if semantic_similarity >= self._semantic_similarity_threshold:
            # Check if contents are actually different
            if content1.strip().lower() != content2.strip().lower():
                logger.debug(
                    "contradiction_detected_heuristic",
                    similarity=semantic_similarity,
                    rationale="High semantic similarity but different content",
                )
                return True

        # Phase 2 TODO: Add LLM-based contradiction detection
        # contradiction = await llm_service.detect_contradiction(content1, content2)

        return False

    def _classify_conflict(
        self,
        new_content: str,
        existing_content: str,
    ) -> ConflictType:
        """Classify the type of conflict.

        Args:
            new_content: New observation content
            existing_content: Existing memory content

        Returns:
            Conflict type classification
        """
        # For now, default to VALUE_MISMATCH (semantic contradiction)
        # Can be enhanced with pattern matching for temporal/logical conflicts
        return ConflictType.VALUE_MISMATCH

    def _calculate_temporal_diff(
        self,
        existing_memory: SemanticMemory,
    ) -> int | None:
        """Calculate temporal difference in days from now.

        Args:
            existing_memory: Existing memory

        Returns:
            Days difference (now - existing), or None if can't calculate
        """
        if not existing_memory.created_at:
            return None

        delta = datetime.now(existing_memory.created_at.tzinfo) - existing_memory.created_at
        return delta.days

    def _recommend_resolution(
        self,
        confidence_diff: float,
        importance_diff: float,
        temporal_diff_days: int | None,
    ) -> ConflictResolution:
        """Recommend conflict resolution strategy.

        Resolution priority:
        1. Temporal: Most recent wins (>30 days difference)
        2. Confidence: Highest confidence wins (>0.2 difference)
        3. Importance: Most important wins (>0.15 difference)
        4. Default: Require clarification

        Args:
            confidence_diff: Confidence difference (new - existing)
            importance_diff: Importance difference (new - existing)
            temporal_diff_days: Temporal difference in days

        Returns:
            Recommended resolution strategy
        """
        logger.debug(
            "evaluating_conflict_resolution",
            temporal_diff_days=temporal_diff_days,
            confidence_diff=confidence_diff,
            importance_diff=importance_diff,
        )

        # Strategy 1: Temporal resolution
        if temporal_diff_days is not None and abs(temporal_diff_days) >= self._temporal_threshold:
            return ConflictResolution.KEEP_NEWEST

        # Strategy 2: Confidence resolution
        if abs(confidence_diff) >= self._confidence_threshold:
            return ConflictResolution.KEEP_HIGHEST_CONFIDENCE

        # Strategy 3: Importance resolution (replaces reinforcement)
        if abs(importance_diff) >= self._importance_threshold:
            # Note: We'd need to add a new resolution type or reuse KEEP_MOST_REINFORCED
            return ConflictResolution.KEEP_MOST_REINFORCED  # Interpret as "most important"

        # Strategy 4: Temporal tiebreaker
        if temporal_diff_days is not None and temporal_diff_days > 0:
            logger.debug(
                "conflict_resolution_temporal_tiebreaker",
                temporal_diff_days=temporal_diff_days,
                threshold=self._temporal_threshold,
                rationale="Temporal difference exists but below threshold, using as tiebreaker",
            )
            return ConflictResolution.KEEP_NEWEST

        # Default: Require user clarification
        return ConflictResolution.REQUIRE_CLARIFICATION

    async def detect_memory_vs_db_conflict(
        self,
        memory: SemanticMemory,
        domain_fact: DomainFact,
        embedding_service: IEmbeddingService,
    ) -> MemoryConflict | None:
        """Detect conflict between semantic memory and authoritative database fact.

        Philosophy: Database is Correspondence Truth (authoritative facts),
        Memory is Contextual Truth (interpretive understanding).
        When they conflict, DB wins.

        Args:
            memory: Semantic memory to check
            domain_fact: Domain fact from authoritative database
            embedding_service: Service for generating embeddings

        Returns:
            MemoryConflict if conflict detected, None otherwise
        """
        # Check if memory mentions the entity from domain fact
        if domain_fact.entity_id not in memory.entities:
            return None

        # Extract status/value from domain fact metadata
        db_value_str = self._extract_db_value(domain_fact)
        if db_value_str is None:
            return None

        # Check if memory content contradicts DB fact
        # Use simple keyword check for now (can enhance with LLM)
        if db_value_str.lower() in memory.content.lower():
            # Memory agrees with DB
            return None

        # Conflict detected: Memory disagrees with DB
        logger.warning(
            "memory_vs_db_conflict_detected",
            entity_id=domain_fact.entity_id,
            fact_type=domain_fact.fact_type,
            memory_content=memory.content[:100],
            db_value=db_value_str,
        )

        # Calculate semantic similarity for transparency
        db_embedding = await embedding_service.generate_embedding(domain_fact.content)
        semantic_similarity = self._calculate_semantic_similarity(
            memory.embedding,
            db_embedding,
        )

        # Build conflict
        conflict = MemoryConflict(
            conflict_type=ConflictType.MEMORY_VS_DB,
            new_memory_id=None,  # DB fact, not a memory
            existing_memory_id=memory.memory_id or 0,
            entities=[domain_fact.entity_id],
            existing_content=memory.content,
            new_content=domain_fact.content,
            recommended_resolution=ConflictResolution.TRUST_DB,
            confidence_diff=1.0,  # DB has 100% confidence (authoritative)
            temporal_diff_days=None,
            semantic_similarity=semantic_similarity,
            metadata={
                "db_fact_type": domain_fact.fact_type,
                "db_source_table": domain_fact.source_table,
                "db_value": db_value_str,
                "memory_confidence": memory.confidence,
                "memory_importance": memory.importance,
                "rationale": "Database is authoritative source of truth (Correspondence Truth)",
            },
        )

        return conflict

    def _extract_db_value(self, domain_fact: DomainFact) -> str | None:
        """Extract value from domain fact metadata.

        Args:
            domain_fact: Domain fact

        Returns:
            Extracted value string, or None if not found
        """
        # For status facts, value is in metadata["status"] or metadata["so_status"]
        if domain_fact.fact_type == "order_chain":
            return domain_fact.metadata.get("so_status")
        elif domain_fact.fact_type.endswith("_status"):
            return domain_fact.metadata.get("status")

        # For other facts, try to extract any status-like field
        for key in ["status", "state", "value"]:
            if key in domain_fact.metadata:
                return str(domain_fact.metadata[key])

        return None
