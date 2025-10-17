"""Augment with domain use case - Phase 1C extraction.

Extracts domain augmentation logic from ProcessChatMessageUseCase god object.
Handles retrieving facts from domain database using LLM tool calling.

Vision Alignment:
- Emergent intelligence (LLM decides what to fetch)
- No hardcoded keywords
- Adaptive to context
"""

import structlog

from src.application.dtos.chat_dtos import DomainFactDTO, ResolvedEntityDTO
from src.application.services.adaptive_query_orchestrator import (
    AdaptiveQueryOrchestrator,
)

logger = structlog.get_logger(__name__)


class AugmentWithDomainUseCase:
    """Use case for augmenting with domain database facts.

    Extracted from ProcessChatMessageUseCase to follow Single Responsibility Principle.
    Handles Phase 1C: Domain Augmentation using LLM tool calling.

    Vision Alignment:
    - Emergent intelligence (LLM decides queries based on context)
    - No hardcoded keywords
    - Feedback-driven (tracks tool usage)

    Responsibilities:
    - Convert resolved entities to dict format
    - Orchestrate LLM tool calling for domain fact retrieval
    - Convert domain facts to DTOs
    """

    def __init__(
        self,
        query_orchestrator: AdaptiveQueryOrchestrator,
    ):
        """Initialize use case.

        Args:
            query_orchestrator: Orchestrator for LLM-based domain fact retrieval
        """
        self.query_orchestrator = query_orchestrator

    async def execute(
        self,
        resolved_entities: list[ResolvedEntityDTO],
        query_text: str,
        session_id: str,
    ) -> list[DomainFactDTO]:
        """Augment with domain database facts using LLM tool calling.

        Vision Alignment:
        - LLM decides what to fetch based on context (not keywords)
        - Tracks tool usage for learning
        - Adaptive to query intent

        Args:
            resolved_entities: List of entities resolved from the message
            query_text: Original query text for context
            session_id: Session ID for tracking tool usage

        Returns:
            List of domain facts retrieved from database
        """
        entity_count = len(resolved_entities) if resolved_entities else 0

        logger.info(
            "starting_llm_domain_augmentation",
            entity_count=entity_count,
            session_id=session_id,
        )

        # Convert DTOs to dict format for orchestrator
        entities_for_orchestrator = [
            {
                "entity_id": e.entity_id,
                "entity_type": e.entity_type,
                "canonical_name": e.canonical_name,
            }
            for e in resolved_entities
        ] if resolved_entities else []

        # Use LLM-based orchestrator (replaces keyword classification)
        domain_facts = await self.query_orchestrator.augment(
            query=query_text,
            entities=entities_for_orchestrator,
            conversation_id=session_id,
        )

        # Convert DomainFact to DomainFactDTO
        domain_fact_dtos = [
            DomainFactDTO(
                fact_type=fact.fact_type,
                entity_id=fact.entity_id,
                content=fact.content,
                metadata=fact.metadata,
                source_table=fact.source_table,
                source_rows=fact.source_rows,
                retrieved_at=fact.retrieved_at,
            )
            for fact in domain_facts
        ]

        logger.info(
            "llm_domain_facts_retrieved",
            fact_count=len(domain_fact_dtos),
        )

        return domain_fact_dtos
