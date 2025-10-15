"""Semantic triple extraction domain service.

Responsible for extracting structured SPO (Subject-Predicate-Object) triples
from natural language chat messages using LLM.
"""

import logging
from typing import Any, Protocol

from src.domain.entities.chat_message import ChatMessage
from src.domain.value_objects import PredicateType, SemanticTriple

logger = logging.getLogger(__name__)


class LLMPort(Protocol):
    """Port for LLM service (dependency injection interface)."""

    async def extract_semantic_triples(
        self,
        message: str,
        resolved_entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract semantic triples from message.

        Args:
            message: Chat message content
            resolved_entities: List of resolved entity dictionaries

        Returns:
            List of triple dictionaries (subject, predicate, object, confidence)
        """
        ...


class SemanticExtractionService:
    """Domain service for extracting semantic triples from conversations.

    This service uses an LLM to identify subject-predicate-object relationships
    in chat messages, focusing on the resolved entities from Phase 1A.

    Responsibilities:
    - Build extraction prompts with resolved entities
    - Call LLM for triple extraction
    - Parse and validate LLM responses
    - Convert to domain SemanticTriple value objects
    """

    def __init__(self, llm_service: LLMPort) -> None:
        """Initialize extraction service.

        Args:
            llm_service: LLM service implementing extraction
        """
        self._llm_service = llm_service

    async def extract_triples(
        self,
        message: ChatMessage,
        resolved_entities: list[dict[str, Any]],
    ) -> list[SemanticTriple]:
        """Extract semantic triples from chat message.

        Args:
            message: Chat message to extract from
            resolved_entities: Resolved entities from Phase 1A
                Each dict should have: entity_id, canonical_name, entity_type

        Returns:
            List of validated SemanticTriple value objects

        Raises:
            ValueError: If message or entities are invalid
        """
        if not message.content or not message.content.strip():
            logger.warning("Empty message content, skipping extraction")
            return []

        if not resolved_entities:
            logger.info("No resolved entities, skipping triple extraction")
            return []

        # Call LLM for extraction
        logger.info(
            "Extracting semantic triples",
            extra={
                "event_id": message.event_id,
                "entity_count": len(resolved_entities),
            },
        )

        try:
            raw_triples = await self._llm_service.extract_semantic_triples(
                message=message.content,
                resolved_entities=resolved_entities,
            )
        except Exception as e:
            logger.error(
                "LLM extraction failed",
                extra={"error": str(e), "event_id": message.event_id},
            )
            return []

        # Parse and validate each triple
        validated_triples: list[SemanticTriple] = []
        for raw_triple in raw_triples:
            try:
                triple = self._parse_and_validate_triple(
                    raw_triple=raw_triple,
                    message=message,
                )
                validated_triples.append(triple)
            except ValueError as e:
                logger.warning(
                    "Invalid triple from LLM",
                    extra={"error": str(e), "raw_triple": raw_triple},
                )
                continue

        logger.info(
            "Extraction complete",
            extra={
                "event_id": message.event_id,
                "triple_count": len(validated_triples),
            },
        )

        return validated_triples

    def _parse_and_validate_triple(
        self,
        raw_triple: dict[str, Any],
        message: ChatMessage,
    ) -> SemanticTriple:
        """Parse and validate raw LLM output into SemanticTriple.

        Args:
            raw_triple: Raw triple dict from LLM
            message: Source message for metadata

        Returns:
            Validated SemanticTriple

        Raises:
            ValueError: If triple is invalid or missing required fields
        """
        # Validate required fields
        required_fields = [
            "subject_entity_id",
            "predicate",
            "predicate_type",
            "object_value",
            "confidence",
        ]
        for field in required_fields:
            if field not in raw_triple:
                raise ValueError(f"Missing required field: {field}")

        # Parse predicate type
        try:
            predicate_type = PredicateType(raw_triple["predicate_type"])
        except ValueError:
            raise ValueError(
                f"Invalid predicate_type: {raw_triple['predicate_type']}. "
                f"Must be one of: {[t.value for t in PredicateType]}"
            )

        # Validate object_value is dict
        if not isinstance(raw_triple["object_value"], dict):
            raise ValueError(
                f"object_value must be dict, got: {type(raw_triple['object_value'])}"
            )

        # Validate confidence
        confidence = raw_triple["confidence"]
        if not isinstance(confidence, (int, float)):
            raise ValueError(f"confidence must be numeric, got: {type(confidence)}")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got: {confidence}")

        # Build metadata
        metadata = {
            "source_event_id": message.event_id,
            "extraction_timestamp": message.created_at.isoformat(),
            "user_id": message.user_id,
            **raw_triple.get("metadata", {}),
        }

        # Create immutable SemanticTriple
        return SemanticTriple(
            subject_entity_id=raw_triple["subject_entity_id"],
            predicate=raw_triple["predicate"],
            predicate_type=predicate_type,
            object_value=raw_triple["object_value"],
            confidence=float(confidence),
            metadata=metadata,
        )
