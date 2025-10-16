"""Domain augmentation service.

Retrieves live facts from the domain database to enrich memory retrieval.

IMPORTANT: This service follows hexagonal architecture.
It depends ONLY on domain ports (ABC interfaces), NOT on infrastructure.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import structlog

from src.domain.ports.domain_database_port import DomainDatabasePort
from src.domain.value_objects.domain_fact import DomainFact

logger = structlog.get_logger(__name__)


@dataclass
class EntityInfo:
    """Simplified entity information for domain augmentation."""

    entity_id: str  # Full entity_id (e.g., "customer:uuid" or "SO-1001")
    entity_type: str  # customer, sales_order, etc.
    canonical_name: str  # Display name


class DomainAugmentationService:
    """Orchestrate domain fact retrieval based on entities and intent.

    Philosophy: Beautiful solutions are declarative and composable.

    Instead of:
        if "invoice" in query: run_invoice_query()

    We have:
        queries = select_queries(entities, intent)
        facts = await execute_all(queries)

    This is:
        - Composable (queries are independent)
        - Extensible (add queries via registry)
        - Testable (mock port, test business logic)
        - Parallel (queries run concurrently)
        - Observable (structured logging)
        - Hexagonal (depends on port, not infrastructure)
    """

    def __init__(self, domain_db_port: DomainDatabasePort) -> None:
        """Initialize service.

        Args:
            domain_db_port: Port for accessing domain database (injected)
        """
        self.domain_db = domain_db_port

    async def augment(
        self,
        entities: list[EntityInfo],
        query_text: str,
        intent: str | None = None,
    ) -> list[DomainFact]:
        """Augment with relevant domain facts.

        Philosophy: Let intent and entities drive query selection.

        Args:
            entities: List of entity information (id, type, name)
            query_text: Original user query
            intent: Optional intent override (default: classify from query_text)

        Returns:
            List of domain facts from database
        """
        if not entities:
            logger.debug("domain_augmentation_skipped_no_entities")
            return []

        # Determine intent (simple heuristics or can be LLM-based in Phase 2)
        if intent is None:
            intent = self._classify_intent(query_text)

        # Select relevant queries based on intent and entities
        queries_to_run = self._select_queries(entities, intent)

        if not queries_to_run:
            logger.debug(
                "domain_augmentation_no_queries_selected",
                entity_count=len(entities),
                intent=intent,
            )
            return []

        # Execute queries in parallel (beautiful: declarative + parallel)
        tasks = []
        for query_type, params in queries_to_run:
            if query_type == "invoice_status":
                tasks.append(self.domain_db.get_invoice_status(**params))
            elif query_type == "order_chain":
                tasks.append(self.domain_db.get_order_chain(**params))
            elif query_type == "sla_risk":
                tasks.append(self.domain_db.get_sla_risks(**params))
            elif query_type == "work_orders":
                tasks.append(self.domain_db.get_work_orders_for_customer(**params))
            elif query_type == "tasks":
                tasks.append(self.domain_db.get_tasks_for_customer(**params))
            else:
                # Extensibility: custom queries
                tasks.append(self.domain_db.execute_custom_query(query_type, params))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten and filter out errors
        facts: list[DomainFact] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                query_type = queries_to_run[i][0]
                logger.warning(
                    "domain_query_failed", query=query_type, error=str(result)
                )
            elif isinstance(result, list):
                facts.extend(result)

        logger.info(
            "domain_augmentation_complete",
            entity_count=len(entities),
            intent=intent,
            queries_executed=len(queries_to_run),
            facts_retrieved=len(facts),
        )

        return facts

    def _classify_intent(self, query_text: str) -> str:
        """Simple intent classification.

        Can be LLM-based in Phase 2 for better accuracy.

        Args:
            query_text: User query

        Returns:
            Intent category (financial, operational, sla_monitoring, general)
        """
        query_lower = query_text.lower()

        if any(
            word in query_lower
            for word in ["invoice", "payment", "owe", "balance", "due", "pay"]
        ):
            return "financial"
        elif any(
            word in query_lower
            for word in ["work order", "wo", "technician", "schedule", "reschedule", "pick-pack"]
        ):
            return "work_orders"
        elif any(
            word in query_lower
            for word in ["task", "todo", "doing", "complete", "mark as done", "investigation"]
        ):
            return "tasks"
        elif any(
            word in query_lower
            for word in ["order", "status", "delivery"]
        ):
            return "operational"
        elif any(
            word in query_lower
            for word in ["sla", "risk", "breach", "late", "overdue", "urgent"]
        ):
            return "sla_monitoring"
        else:
            return "general"

    def _select_queries(
        self,
        entities: list[EntityInfo],
        intent: str,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Select which queries to run based on entities and intent.

        Returns:
            List of (query_type, params) tuples
        """
        queries: list[tuple[str, dict[str, Any]]] = []

        for entity in entities:
            # Extract UUID from entity_id (format: "customer_uuid" per CanonicalEntity spec)
            if entity.entity_type == "customer":
                # Extract UUID from entity_id (format: "customer_uuid")
                if "_" in entity.entity_id:
                    customer_uuid = entity.entity_id.split("_", 1)[1]
                else:
                    # Fallback: entity_id might be just the UUID
                    customer_uuid = entity.entity_id

                if intent in ["financial", "general"]:
                    queries.append(
                        (
                            "invoice_status",
                            {"customer_id": customer_uuid},
                        )
                    )

                if intent in ["sla_monitoring", "operational", "general"]:
                    queries.append(
                        (
                            "sla_risk",
                            {"customer_id": customer_uuid},
                        )
                    )

                if intent in ["work_orders", "operational", "general"]:
                    queries.append(
                        (
                            "work_orders",
                            {"customer_id": customer_uuid},
                        )
                    )

                if intent in ["tasks", "sla_monitoring", "general"]:
                    queries.append(
                        (
                            "tasks",
                            {"customer_id": customer_uuid},
                        )
                    )

            elif entity.entity_type == "sales_order" or entity.canonical_name.startswith("SO-"):
                # Extract SO number from entity
                so_number = entity.canonical_name
                if "SO-" in so_number:
                    # Extract just the SO number part
                    so_number = so_number.split("SO-")[-1]
                    if not so_number.startswith("SO-"):
                        so_number = f"SO-{so_number}"

                if intent in ["operational", "financial", "general"]:
                    queries.append(
                        (
                            "order_chain",
                            {"sales_order_number": so_number},
                        )
                    )

        return queries
