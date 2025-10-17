"""Domain database repository port.

Port for accessing external domain database (customers, orders, invoices, etc.).
This is the ABC interface - implementations are in infrastructure layer.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.domain.value_objects.domain_fact import DomainFact


class DomainDatabasePort(ABC):
    """Port for querying external domain database.

    Philosophy: The domain database is external authoritative data.
    This port provides structured access without leaking SQLAlchemy into domain.

    Each method corresponds to a specific business query pattern.
    Implementations live in infrastructure layer.
    """

    @abstractmethod
    async def get_invoice_status(self, customer_id: str) -> list[DomainFact]:
        """Get all invoices for a customer with payment details.

        Args:
            customer_id: Customer UUID (from external_ref)

        Returns:
            List of domain facts about invoice status
        """

    @abstractmethod
    async def get_order_chain(self, sales_order_number: str) -> list[DomainFact]:
        """Traverse SO → WO → Invoice chain.

        Args:
            sales_order_number: Sales order number (e.g., "SO-1001")

        Returns:
            List of domain facts about order chain
        """

    @abstractmethod
    async def get_sla_risks(
        self, customer_id: str, sla_threshold_days: int = 10
    ) -> list[DomainFact]:
        """Find tasks and orders at risk of SLA breach.

        Args:
            customer_id: Customer UUID
            sla_threshold_days: Age threshold for SLA risk (default: 10 days)

        Returns:
            List of domain facts about SLA risks
        """

    @abstractmethod
    async def get_work_orders_for_customer(
        self, customer_id: str, status_filter: str | None = None
    ) -> list[DomainFact]:
        """Get all work orders for a customer.

        Args:
            customer_id: Customer UUID
            status_filter: Optional status filter (e.g., "queued", "in_progress", "done")

        Returns:
            List of domain facts about work orders
        """

    @abstractmethod
    async def get_tasks_for_customer(
        self, customer_id: str, status_filter: str | None = None
    ) -> list[DomainFact]:
        """Get all tasks for a customer.

        Args:
            customer_id: Customer UUID
            status_filter: Optional status filter (e.g., "todo", "doing", "done")

        Returns:
            List of domain facts about tasks
        """

    @abstractmethod
    async def get_all_invoices(
        self, status_filter: str | None = None, limit: int = 50
    ) -> list[DomainFact]:
        """Get all invoices (general query, not customer-specific).

        Phase 3.3: Support for general queries like "What invoices do we have?"

        Args:
            status_filter: Optional status filter (e.g., "open", "paid")
            limit: Maximum number of invoices to return (default: 50)

        Returns:
            List of domain facts about invoices
        """

    @abstractmethod
    async def find_customer_by_name(self, name: str) -> dict[str, Any] | None:
        """Find a customer by name (case-insensitive).

        Used by Stage 5 of entity resolution for lazy entity creation.

        Args:
            name: Customer name to search for

        Returns:
            Dict with customer_id, name, and other properties, or None if not found
        """

    @abstractmethod
    async def execute_custom_query(
        self, query_name: str, params: dict[str, Any]
    ) -> list[DomainFact]:
        """Execute a registered custom query.

        Allows for extensibility without modifying the port interface.
        Implementations maintain a registry of query handlers.

        Args:
            query_name: Name of registered query
            params: Query parameters

        Returns:
            List of domain facts
        """
