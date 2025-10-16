"""Domain database repository implementation.

Adapter that implements DomainDatabasePort using SQLAlchemy.
Executes queries against the external domain schema.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ports.domain_database_port import DomainDatabasePort
from src.domain.value_objects.domain_fact import DomainFact

logger = structlog.get_logger(__name__)


class DomainDatabaseRepository(DomainDatabasePort):
    """SQLAlchemy implementation of DomainDatabasePort.

    This adapter contains all SQL queries and database-specific logic.
    The domain layer only knows about the port interface.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Database session
        """
        self.session = session

        # Registry of custom query handlers
        self._custom_queries: dict[str, Any] = {}

    async def get_invoice_status(self, customer_id: str) -> list[DomainFact]:
        """Get all invoices for customer with payment details."""
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
            result = await self.session.execute(query, {"customer_id": UUID(customer_id)})
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
                        retrieved_at=datetime.now(UTC),
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

    async def get_order_chain(self, sales_order_number: str) -> list[DomainFact]:
        """Traverse SO → WO → Invoice chain."""
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
            result = await self.session.execute(query, {"so_number": sales_order_number})
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
                    retrieved_at=datetime.now(UTC),
                )
            ]

        except Exception as e:
            logger.error(
                "order_chain_query_failed",
                so_number=sales_order_number,
                error=str(e),
            )
            return []

    async def get_sla_risks(
        self, customer_id: str, sla_threshold_days: int = 10
    ) -> list[DomainFact]:
        """Find tasks and orders at risk of SLA breach."""
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
            result = await self.session.execute(
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
                        retrieved_at=datetime.now(UTC),
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

    async def get_work_orders_for_customer(
        self, customer_id: str, status_filter: str | None = None
    ) -> list[DomainFact]:
        """Get all work orders for a customer."""
        query_sql = """
            SELECT
                wo.wo_id,
                wo.description,
                wo.status,
                wo.technician,
                wo.scheduled_for,
                so.so_number,
                so.title as so_title,
                c.name as customer_name
            FROM domain.work_orders wo
            JOIN domain.sales_orders so ON wo.so_id = so.so_id
            JOIN domain.customers c ON so.customer_id = c.customer_id
            WHERE c.customer_id = :customer_id
        """

        if status_filter:
            query_sql += " AND wo.status = :status"

        query_sql += " ORDER BY wo.scheduled_for ASC NULLS LAST"

        query = text(query_sql)

        try:
            params: dict[str, Any] = {"customer_id": UUID(customer_id)}
            if status_filter:
                params["status"] = status_filter

            result = await self.session.execute(query, params)
            rows = result.fetchall()

            facts = []
            for row in rows:
                # Build human-readable content
                content_parts = [f"Work Order: {row.description}"]
                content_parts.append(f"Status: {row.status}")
                if row.technician:
                    content_parts.append(f"Technician: {row.technician}")
                if row.scheduled_for:
                    content_parts.append(f"Scheduled for: {row.scheduled_for}")
                content_parts.append(f"Sales Order: {row.so_number} ({row.so_title})")

                facts.append(
                    DomainFact(
                        fact_type="work_order_status",
                        entity_id=f"customer:{customer_id}",
                        content=" | ".join(content_parts),
                        metadata={
                            "wo_id": str(row.wo_id),
                            "description": row.description,
                            "status": row.status,
                            "technician": row.technician,
                            "scheduled_for": row.scheduled_for.isoformat() if row.scheduled_for else None,
                            "so_number": row.so_number,
                            "so_title": row.so_title,
                            "customer_name": row.customer_name,
                        },
                        source_table="domain.work_orders",
                        source_rows=[str(row.wo_id)],
                        retrieved_at=datetime.now(UTC),
                    )
                )

            logger.debug(
                "work_orders_query_executed",
                customer_id=customer_id,
                status_filter=status_filter,
                facts_retrieved=len(facts),
            )

            return facts

        except Exception as e:
            logger.error(
                "work_orders_query_failed",
                customer_id=customer_id,
                error=str(e),
            )
            return []

    async def get_tasks_for_customer(
        self, customer_id: str, status_filter: str | None = None
    ) -> list[DomainFact]:
        """Get all tasks for a customer."""
        query_sql = """
            SELECT
                t.task_id,
                t.title,
                t.body,
                t.status,
                t.created_at,
                EXTRACT(EPOCH FROM (NOW() - t.created_at)) / 86400 as age_days,
                c.name as customer_name
            FROM domain.tasks t
            JOIN domain.customers c ON t.customer_id = c.customer_id
            WHERE t.customer_id = :customer_id
        """

        if status_filter:
            query_sql += " AND t.status = :status"

        query_sql += " ORDER BY t.created_at DESC"

        query = text(query_sql)

        try:
            params: dict[str, Any] = {"customer_id": UUID(customer_id)}
            if status_filter:
                params["status"] = status_filter

            result = await self.session.execute(query, params)
            rows = result.fetchall()

            facts = []
            for row in rows:
                # Build human-readable content
                content_parts = [f"Task: {row.title}"]
                content_parts.append(f"Status: {row.status}")
                if row.body:
                    # Truncate body if too long
                    body_preview = row.body[:100] + "..." if len(row.body) > 100 else row.body
                    content_parts.append(f"Details: {body_preview}")
                content_parts.append(f"Age: {int(row.age_days)} days")

                facts.append(
                    DomainFact(
                        fact_type="task_status",
                        entity_id=f"customer:{customer_id}",
                        content=" | ".join(content_parts),
                        metadata={
                            "task_id": str(row.task_id),
                            "title": row.title,
                            "body": row.body,
                            "status": row.status,
                            "age_days": row.age_days,
                            "created_at": row.created_at.isoformat(),
                            "customer_name": row.customer_name,
                        },
                        source_table="domain.tasks",
                        source_rows=[str(row.task_id)],
                        retrieved_at=datetime.now(UTC),
                    )
                )

            logger.debug(
                "tasks_query_executed",
                customer_id=customer_id,
                status_filter=status_filter,
                facts_retrieved=len(facts),
            )

            return facts

        except Exception as e:
            logger.error(
                "tasks_query_failed",
                customer_id=customer_id,
                error=str(e),
            )
            return []

    async def execute_custom_query(
        self, query_name: str, params: dict[str, Any]
    ) -> list[DomainFact]:
        """Execute a registered custom query.

        Allows for extensibility via query registry pattern.
        """
        if query_name not in self._custom_queries:
            logger.warning("custom_query_not_found", query_name=query_name)
            return []

        handler = self._custom_queries[query_name]
        try:
            result: list[DomainFact] = await handler(self.session, **params)
            return result
        except Exception as e:
            logger.error(
                "custom_query_failed", query_name=query_name, error=str(e)
            )
            return []

    def register_custom_query(
        self, query_name: str, handler: Any
    ) -> None:
        """Register a custom query handler.

        Args:
            query_name: Unique query identifier
            handler: Async function that takes (session, **params) and returns list[DomainFact]
        """
        self._custom_queries[query_name] = handler
        logger.debug("custom_query_registered", query_name=query_name)
