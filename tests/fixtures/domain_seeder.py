"""Domain database seeding for E2E tests.

Provides DomainSeeder class to populate domain.* tables with test data
for scenario testing.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, date
import uuid


class DomainSeeder:
    """Seed domain database with test data for E2E scenarios."""

    def __init__(self, session: AsyncSession):
        """
        Initialize domain seeder.

        Args:
            session: Async database session
        """
        self.session = session
        self._id_mapping: Dict[str, str] = {}  # Map friendly names to UUIDs

    async def seed(self, data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
        """
        Seed domain database with test data.

        Args:
            data: Dictionary with table names as keys, list of records as values
                  Example:
                  {
                      "customers": [
                          {"name": "Kai Media", "industry": "Entertainment", "id": "kai_123"}
                      ],
                      "sales_orders": [
                          {"customer": "kai_123", "so_number": "SO-1001", "title": "Album", "status": "in_fulfillment"}
                      ]
                  }

        Returns:
            Dictionary mapping friendly IDs to actual UUIDs
        """
        # Create customers first (no dependencies)
        for customer_data in data.get("customers", []):
            await self._create_customer(customer_data)

        # Create tasks (depends on customers)
        for task_data in data.get("tasks", []):
            await self._create_task(task_data)

        # Create sales_orders (depends on customers)
        for so_data in data.get("sales_orders", []):
            await self._create_sales_order(so_data)

        # Create work_orders (depends on sales_orders)
        for wo_data in data.get("work_orders", []):
            await self._create_work_order(wo_data)

        # Create invoices (depends on sales_orders)
        for invoice_data in data.get("invoices", []):
            await self._create_invoice(invoice_data)

        # Create payments (depends on invoices)
        for payment_data in data.get("payments", []):
            await self._create_payment(payment_data)

        # Commit to make data visible across all queries (E2E tests need this)
        # The test fixture will still rollback at the end for isolation
        await self.session.commit()

        return self._id_mapping

    async def _create_customer(self, data: Dict[str, Any]) -> str:
        """
        Create customer and return customer_id.

        Args:
            data: Customer data with keys:
                  - name (required)
                  - industry (optional)
                  - notes (optional)
                  - id (optional): friendly ID for reference

        Returns:
            UUID of created customer
        """
        customer_id = uuid.uuid4()
        friendly_id = data.get("id", data["name"].lower().replace(" ", "_"))

        await self.session.execute(
            text("""
                INSERT INTO domain.customers (customer_id, name, industry, notes)
                VALUES (:customer_id, :name, :industry, :notes)
            """),
            {
                "customer_id": customer_id,
                "name": data["name"],
                "industry": data.get("industry"),
                "notes": data.get("notes"),
            },
        )

        # Store mapping
        self._id_mapping[friendly_id] = str(customer_id)
        return str(customer_id)

    async def _create_sales_order(self, data: Dict[str, Any]) -> str:
        """
        Create sales order.

        Args:
            data: SO data with keys:
                  - customer: friendly customer ID or UUID
                  - so_number (required)
                  - title (required)
                  - status (required)
                  - id (optional): friendly ID for reference

        Returns:
            UUID of created sales order
        """
        so_id = uuid.uuid4()
        friendly_id = data.get("id", data["so_number"])

        # Resolve customer ID
        customer_ref = data["customer"]
        customer_id = self._id_mapping.get(customer_ref, customer_ref)

        await self.session.execute(
            text("""
                INSERT INTO domain.sales_orders
                (so_id, customer_id, so_number, title, status, created_at)
                VALUES (:so_id, :customer_id, :so_number, :title, :status, :created_at)
            """),
            {
                "so_id": so_id,
                "customer_id": customer_id,
                "so_number": data["so_number"],
                "title": data["title"],
                "status": data["status"],
                "created_at": data.get("created_at", datetime.now()),
            },
        )

        self._id_mapping[friendly_id] = str(so_id)
        return str(so_id)

    async def _create_work_order(self, data: Dict[str, Any]) -> str:
        """Create work order."""
        wo_id = uuid.uuid4()
        friendly_id = data.get("id", f"wo_{wo_id}")

        # Resolve sales_order ID
        so_ref = data["sales_order"]
        so_id = self._id_mapping.get(so_ref, so_ref)

        await self.session.execute(
            text("""
                INSERT INTO domain.work_orders
                (wo_id, so_id, description, status, technician, scheduled_for)
                VALUES (:wo_id, :so_id, :description, :status, :technician, :scheduled_for)
            """),
            {
                "wo_id": wo_id,
                "so_id": so_id,
                "description": data.get("description"),
                "status": data["status"],
                "technician": data.get("technician"),
                "scheduled_for": data.get("scheduled_for"),
            },
        )

        self._id_mapping[friendly_id] = str(wo_id)
        return str(wo_id)

    async def _create_invoice(self, data: Dict[str, Any]) -> str:
        """Create invoice."""
        invoice_id = uuid.uuid4()
        friendly_id = data.get("id", data["invoice_number"])

        # Resolve sales_order ID
        so_ref = data["sales_order"]
        so_id = self._id_mapping.get(so_ref, so_ref)

        await self.session.execute(
            text("""
                INSERT INTO domain.invoices
                (invoice_id, so_id, invoice_number, amount, due_date, status, issued_at)
                VALUES (:invoice_id, :so_id, :invoice_number, :amount, :due_date, :status, :issued_at)
            """),
            {
                "invoice_id": invoice_id,
                "so_id": so_id,
                "invoice_number": data["invoice_number"],
                "amount": data["amount"],
                "due_date": data["due_date"],
                "status": data["status"],
                "issued_at": data.get("issued_at", datetime.now()),
            },
        )

        self._id_mapping[friendly_id] = str(invoice_id)
        return str(invoice_id)

    async def _create_payment(self, data: Dict[str, Any]) -> str:
        """Create payment."""
        payment_id = uuid.uuid4()
        friendly_id = data.get("id", f"payment_{payment_id}")

        # Resolve invoice ID
        invoice_ref = data["invoice"]
        invoice_id = self._id_mapping.get(invoice_ref, invoice_ref)

        await self.session.execute(
            text("""
                INSERT INTO domain.payments
                (payment_id, invoice_id, amount, method, paid_at)
                VALUES (:payment_id, :invoice_id, :amount, :method, :paid_at)
            """),
            {
                "payment_id": payment_id,
                "invoice_id": invoice_id,
                "amount": data["amount"],
                "method": data.get("method"),
                "paid_at": data.get("paid_at", datetime.now()),
            },
        )

        self._id_mapping[friendly_id] = str(payment_id)
        return str(payment_id)

    async def _create_task(self, data: Dict[str, Any]) -> str:
        """Create task."""
        task_id = uuid.uuid4()
        friendly_id = data.get("id", f"task_{task_id}")

        # Resolve customer ID (optional)
        customer_id = None
        if "customer" in data:
            customer_ref = data["customer"]
            customer_id = self._id_mapping.get(customer_ref, customer_ref)

        await self.session.execute(
            text("""
                INSERT INTO domain.tasks
                (task_id, customer_id, title, body, status, created_at)
                VALUES (:task_id, :customer_id, :title, :body, :status, :created_at)
            """),
            {
                "task_id": task_id,
                "customer_id": customer_id,
                "title": data["title"],
                "body": data.get("body"),
                "status": data["status"],
                "created_at": data.get("created_at", datetime.now()),
            },
        )

        self._id_mapping[friendly_id] = str(task_id)
        return str(task_id)

    def get_uuid(self, friendly_id: str) -> Optional[str]:
        """Get UUID for a friendly ID."""
        return self._id_mapping.get(friendly_id)
