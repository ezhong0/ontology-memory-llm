"""Domain augmentation service.

Retrieves live facts from the domain database to enrich memory retrieval.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.canonical_entity import CanonicalEntity
from src.domain.value_objects.domain_fact import DomainFact

logger = structlog.get_logger(__name__)


class InvoiceStatusQuery:
    """Query invoice status for a customer.

    Philosophy: One query class per domain concern.
    Each query is self-contained, testable, composable.

    Retrieves:
        - All invoices for customer (open, paid, void)
        - Payment details (amount paid, balance remaining)
        - Due dates and aging information
    """

    async def execute(
        self, session: AsyncSession, customer_id: str
    ) -> List[DomainFact]:
        """Get all invoices for customer with payment details.

        Args:
            session: Database session
            customer_id: Customer UUID (from external_ref)

        Returns:
            List of domain facts about invoice status
        """
        query = text("""
            SELECT
                i.invoice_id,
                i.invoice_number,
                i.amount,
                i.due_date,
                i.status,
                i.issued_at,
                COALESCE(SUM(p.amount), 0) as paid_amount,
                i.amount - COALESCE(SUM(p.amount), 0) as balance
            FROM domain.invoices i
            LEFT JOIN domain.payments p ON i.invoice_id = p.invoice_id
            WHERE i.so_id IN (
                SELECT so_id FROM domain.sales_orders WHERE customer_id = :customer_id
            )
            GROUP BY i.invoice_id, i.invoice_number, i.amount, i.due_date, i.status, i.issued_at
            ORDER BY i.due_date ASC
        """)

        try:
            result = await session.execute(query, {"customer_id": UUID(customer_id)})
            rows = result.fetchall()

            facts = []
            for row in rows:
                # Build human-readable fact
                status_desc = f"${float(row.amount):.2f} due {row.due_date} (status: {row.status})"
                if row.paid_amount > 0:
                    status_desc += (
                        f" - ${float(row.paid_amount):.2f} paid, "
                        f"${float(row.balance):.2f} remaining"
                    )

                facts.append(
                    DomainFact(
                        fact_type="invoice_status",
                        entity_id=f"customer:{customer_id}",
                        content=f"Invoice {row.invoice_number}: {status_desc}",
                        metadata={
                            "invoice_number": row.invoice_number,
                            "amount": float(row.amount),
                            "paid": float(row.paid_amount),
                            "balance": float(row.balance),
                            "due_date": row.due_date.isoformat(),
                            "status": row.status,
                            "invoice_id": str(row.invoice_id),
                        },
                        source_table="domain.invoices",
                        source_rows=[str(row.invoice_id)],
                        retrieved_at=datetime.now(timezone.utc),
                    )
                )

            logger.debug(
                "invoice_status_query_executed",
                customer_id=customer_id,
                facts_retrieved=len(facts),
            )

            return facts

        except Exception as e:
            logger.error(
                "invoice_status_query_failed", customer_id=customer_id, error=str(e)
            )
            return []


class OrderChainQuery:
    """Query complete order chain: SO → WO → Invoice.

    Scenario 11: Cross-object reasoning

    Retrieves:
        - Sales order status
        - All work orders (status, technician, schedule)
        - All invoices
        - Readiness analysis (can we invoice? send invoice? track payment?)
    """

    async def execute(
        self, session: AsyncSession, sales_order_number: str
    ) -> List[DomainFact]:
        """Traverse SO → WO → Invoice chain.

        Args:
            session: Database session
            sales_order_number: Sales order number (e.g., "SO-1001")

        Returns:
            List of domain facts about order chain
        """
        query = text("""
            SELECT
                so.so_id,
                so.so_number,
                so.status as so_status,
                so.title as so_title,
                json_agg(DISTINCT jsonb_build_object(
                    'wo_id', wo.wo_id,
                    'description', wo.description,
                    'status', wo.status,
                    'technician', wo.technician,
                    'scheduled_for', wo.scheduled_for
                )) FILTER (WHERE wo.wo_id IS NOT NULL) as work_orders,
                json_agg(DISTINCT jsonb_build_object(
                    'invoice_id', i.invoice_id,
                    'invoice_number', i.invoice_number,
                    'amount', i.amount,
                    'status', i.status
                )) FILTER (WHERE i.invoice_id IS NOT NULL) as invoices
            FROM domain.sales_orders so
            LEFT JOIN domain.work_orders wo ON so.so_id = wo.so_id
            LEFT JOIN domain.invoices i ON so.so_id = i.so_id
            WHERE so.so_number = :so_number
            GROUP BY so.so_id, so.so_number, so.status, so.title
        """)

        try:
            result = await session.execute(query, {"so_number": sales_order_number})
            row = result.fetchone()

            if not row:
                logger.debug(
                    "order_chain_not_found", so_number=sales_order_number
                )
                return []

            # Analyze chain state
            wos = row.work_orders or []
            invoices = row.invoices or []

            total_wo = len(wos)
            done_wo = sum(1 for wo in wos if wo["status"] == "done")

            # Determine readiness
            if total_wo == 0:
                content = f"{sales_order_number}: No work orders defined yet (status: {row.so_status})"
                recommended_action = "create_work_orders"
            elif done_wo < total_wo:
                content = (
                    f"{sales_order_number}: {done_wo}/{total_wo} work orders complete "
                    f"({total_wo - done_wo} remaining)"
                )
                recommended_action = "complete_work_orders"
            elif len(invoices) == 0:
                content = f"{sales_order_number}: All work complete, ready to invoice"
                recommended_action = "generate_invoice"
            else:
                inv = invoices[0]
                content = f"{sales_order_number}: Invoice {inv['invoice_number']} {inv['status']} (${inv['amount']})"
                recommended_action = (
                    "send_invoice" if inv["status"] == "open" else "track_payment"
                )

            return [
                DomainFact(
                    fact_type="order_chain",
                    entity_id=sales_order_number,
                    content=content,
                    metadata={
                        "so_number": sales_order_number,
                        "so_title": row.so_title,
                        "so_status": row.so_status,
                        "work_orders": wos,
                        "invoices": invoices,
                        "total_wo": total_wo,
                        "done_wo": done_wo,
                        "recommended_action": recommended_action,
                    },
                    source_table="domain.sales_orders,work_orders,invoices",
                    source_rows=[str(row.so_id)],
                    retrieved_at=datetime.now(timezone.utc),
                )
            ]

        except Exception as e:
            logger.error(
                "order_chain_query_failed",
                so_number=sales_order_number,
                error=str(e),
            )
            return []


class SLARiskQuery:
    """Detect SLA breach risks.

    Scenario 6: SLA breach detection from tasks + orders

    Retrieves:
        - Open tasks past threshold
        - Task age in days
        - Risk level (medium, high, critical)
    """

    async def execute(
        self,
        session: AsyncSession,
        customer_id: str,
        sla_threshold_days: int = 10,
    ) -> List[DomainFact]:
        """Find tasks and orders at risk of SLA breach.

        Args:
            session: Database session
            customer_id: Customer UUID
            sla_threshold_days: Age threshold for SLA risk (default: 10 days)

        Returns:
            List of domain facts about SLA risks
        """
        query = text("""
            SELECT
                t.task_id,
                t.title,
                t.status,
                t.created_at,
                EXTRACT(EPOCH FROM (NOW() - t.created_at)) / 86400 as age_days,
                c.name as customer_name
            FROM domain.tasks t
            JOIN domain.customers c ON t.customer_id = c.customer_id
            WHERE t.customer_id = :customer_id
              AND t.status != 'done'
              AND EXTRACT(EPOCH FROM (NOW() - t.created_at)) / 86400 > :threshold
            ORDER BY age_days DESC
        """)

        try:
            result = await session.execute(
                query,
                {"customer_id": UUID(customer_id), "threshold": sla_threshold_days},
            )
            rows = result.fetchall()

            facts = []
            for row in rows:
                # Determine risk level
                if row.age_days > sla_threshold_days * 2:
                    risk_level = "critical"
                elif row.age_days > sla_threshold_days * 1.5:
                    risk_level = "high"
                else:
                    risk_level = "medium"

                facts.append(
                    DomainFact(
                        fact_type="sla_risk",
                        entity_id=f"customer:{customer_id}",
                        content=(
                            f"SLA RISK [{risk_level.upper()}]: Task '{row.title}' "
                            f"open for {int(row.age_days)} days (threshold: {sla_threshold_days})"
                        ),
                        metadata={
                            "task_id": str(row.task_id),
                            "task_title": row.title,
                            "age_days": row.age_days,
                            "threshold": sla_threshold_days,
                            "risk_level": risk_level,
                            "status": row.status,
                        },
                        source_table="domain.tasks",
                        source_rows=[str(row.task_id)],
                        retrieved_at=datetime.now(timezone.utc),
                    )
                )

            logger.debug(
                "sla_risk_query_executed",
                customer_id=customer_id,
                risks_found=len(facts),
            )

            return facts

        except Exception as e:
            logger.error(
                "sla_risk_query_failed", customer_id=customer_id, error=str(e)
            )
            return []


class DomainAugmentationService:
    """Orchestrate domain fact retrieval based on entities and intent.

    Philosophy: Beautiful solutions are declarative and composable (BEAUTIFUL_SOLUTIONS_ANALYSIS.md).

    Instead of:
        if "invoice" in query: run_invoice_query()

    We have:
        queries = select_queries(entities, intent)
        facts = await execute_all(queries)

    This is:
        - Composable (queries are independent)
        - Extensible (add queries via registry)
        - Testable (mock session, test each query)
        - Parallel (queries run concurrently)
        - Observable (structured logging)
    """

    def __init__(self, session: AsyncSession):
        """Initialize service.

        Args:
            session: Database session (shared with memory repositories)
        """
        self.session = session

        # Register domain queries (extensible)
        self.query_registry = {
            "invoice_status": InvoiceStatusQuery(),
            "order_chain": OrderChainQuery(),
            "sla_risk": SLARiskQuery(),
        }

    async def augment(
        self,
        entities: List[CanonicalEntity],
        query_text: str,
        intent: Optional[str] = None,
    ) -> List[DomainFact]:
        """Augment with relevant domain facts.

        Philosophy: Let intent and entities drive query selection.

        Args:
            entities: Resolved canonical entities from query
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
        for query_name, query_instance, params in queries_to_run:
            tasks.append(query_instance.execute(self.session, **params))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten and filter out errors
        facts = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                query_name = queries_to_run[i][0]
                logger.warning(
                    "domain_query_failed", query=query_name, error=str(result)
                )
            else:
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
            for word in ["order", "status", "work", "delivery", "schedule"]
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
        entities: List[CanonicalEntity],
        intent: str,
    ) -> List[tuple[str, object, dict]]:
        """Select which queries to run based on entities and intent.

        Returns:
            List of (query_name, query_instance, params) tuples
        """
        queries = []

        for entity in entities:
            # Extract UUID from entity_id (format: "customer:uuid" or "SO-1001")
            if entity.entity_type == "customer" and entity.external_ref:
                customer_uuid = entity.external_ref.get("id")

                if intent in ["financial", "general"]:
                    queries.append(
                        (
                            "invoice_status",
                            self.query_registry["invoice_status"],
                            {"customer_id": customer_uuid},
                        )
                    )

                if intent in ["sla_monitoring", "operational", "general"]:
                    queries.append(
                        (
                            "sla_risk",
                            self.query_registry["sla_risk"],
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
                            self.query_registry["order_chain"],
                            {"sales_order_number": so_number},
                        )
                    )

        return queries
