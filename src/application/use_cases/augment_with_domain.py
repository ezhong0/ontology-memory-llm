"""Augment with domain use case - Phase 1C extraction.

Extracts domain augmentation logic from ProcessChatMessageUseCase god object.
Handles retrieving facts from domain database.
"""

import structlog

from src.application.dtos.chat_dtos import DomainFactDTO, ResolvedEntityDTO
from src.domain.services import DomainAugmentationService, EntityInfo

logger = structlog.get_logger(__name__)


class AugmentWithDomainUseCase:
    """Use case for augmenting with domain database facts.

    Extracted from ProcessChatMessageUseCase to follow Single Responsibility Principle.
    Handles Phase 1C: Domain Augmentation.

    Responsibilities:
    - Convert resolved entities to EntityInfo
    - Query domain database for relevant facts
    - Convert domain facts to DTOs
    """

    def __init__(
        self,
        domain_augmentation_service: DomainAugmentationService,
    ):
        """Initialize use case.

        Args:
            domain_augmentation_service: Service for retrieving domain database facts
        """
        self.domain_augmentation_service = domain_augmentation_service

    async def execute(
        self,
        resolved_entities: list[ResolvedEntityDTO],
        query_text: str,
    ) -> list[DomainFactDTO]:
        """Augment with domain database facts.

        Args:
            resolved_entities: List of entities resolved from the message
            query_text: Original query text for context

        Returns:
            List of domain facts retrieved from database
        """
        # Phase 3.3: Allow general queries without entities (e.g., "What invoices do we have?")
        entity_count = len(resolved_entities) if resolved_entities else 0

        logger.info(
            "starting_domain_augmentation",
            entity_count=entity_count,
            general_query=not resolved_entities,
        )

        # Convert DTOs to EntityInfo for augmentation service
        entities_for_augmentation = [
            EntityInfo(
                entity_id=e.entity_id,
                entity_type=e.entity_type,
                canonical_name=e.canonical_name,
            )
            for e in resolved_entities
        ] if resolved_entities else []

        # Query domain database (now supports general queries without entities)
        domain_facts = await self.domain_augmentation_service.augment(
            entities=entities_for_augmentation,
            query_text=query_text,
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
            "domain_facts_retrieved",
            fact_count=len(domain_fact_dtos),
        )

        return domain_fact_dtos
