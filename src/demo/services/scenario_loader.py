"""Scenario loading service for demo system.

This service loads scenario data into the database, creating both domain data
(customers, orders, invoices) and memory data (canonical entities, memories).

Phase 1: Simplified implementation for Scenario 1
Phase 2: Generalized for all scenarios with production service integration
"""
import logging
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.demo.models.scenario import ScenarioDefinition, ScenarioLoadResult
from src.demo.services.scenario_registry import ScenarioRegistry
from src.infrastructure.database.domain_models import (
    DomainCustomer,
    DomainInvoice,
    DomainPayment,
    DomainSalesOrder,
    DomainTask,
    DomainWorkOrder,
)
from src.infrastructure.database.models import (
    CanonicalEntity,
    ChatEvent,
    DomainOntology,
    EntityAlias,
    EpisodicMemory,
    MemoryConflict,
    MemorySummary,
    ProceduralMemory,
    SemanticMemory,
    ToolUsageLog,
)

logger = logging.getLogger(__name__)


class ScenarioLoadError(Exception):
    """Raised when scenario loading fails."""



class ScenarioLoaderService:
    """Service for loading scenarios into the system.

    Supports idempotent loading - scenarios can be loaded multiple times safely.
    """

    def __init__(self, session: AsyncSession, user_id: str = "demo-user"):
        """Initialize scenario loader.

        Args:
            session: SQLAlchemy async session for database operations
            user_id: User ID for memory data (default: "demo-user")
        """
        self.session = session
        self.user_id = user_id
        # Track created entities for memory creation
        self._entity_map: dict[str, UUID] = {}  # name -> domain entity UUID
        self._canonical_entity_map: dict[str, str] = {}  # name -> canonical entity_id

    async def load_scenario(self, scenario_id: int) -> ScenarioLoadResult:
        """Load a scenario into the system.

        Args:
            scenario_id: ID of scenario to load (1-18)

        Returns:
            ScenarioLoadResult with counts and status

        Raises:
            ScenarioLoadError: If scenario loading fails
        """
        # Get scenario definition
        scenario = ScenarioRegistry.get(scenario_id)
        if not scenario:
            msg = f"Scenario {scenario_id} not found in registry"
            raise ScenarioLoadError(msg)

        logger.info(f"Loading scenario {scenario_id}: {scenario.title}")

        # Validate scenario before loading
        self._validate_scenario(scenario)

        try:
            # Reset all data first (clear everything from DB)
            logger.info("Clearing all existing demo data before loading scenario")
            await self.reset()

            # Clear tracking dicts
            self._entity_map = {}
            self._canonical_entity_map = {}

            # Load domain data
            customers_count = await self._load_customers(scenario)
            sales_orders_count = await self._load_sales_orders(scenario)
            invoices_count = await self._load_invoices(scenario)
            work_orders_count = await self._load_work_orders(scenario)
            payments_count = await self._load_payments(scenario)
            tasks_count = await self._load_tasks(scenario)

            # Create canonical entities for all domain entities
            await self._create_canonical_entities()

            # Load memories
            semantic_memories_count = await self._load_semantic_memories(scenario)
            episodic_memories_count = 0  # Not implemented in Phase 1

            # Commit transaction
            await self.session.commit()

            result = ScenarioLoadResult(
                scenario_id=scenario.scenario_id,
                title=scenario.title,
                customers_created=customers_count,
                sales_orders_created=sales_orders_count,
                invoices_created=invoices_count,
                work_orders_created=work_orders_count,
                payments_created=payments_count,
                tasks_created=tasks_count,
                semantic_memories_created=semantic_memories_count,
                episodic_memories_created=episodic_memories_count,
                message=f"Successfully loaded scenario {scenario_id}",
            )

            logger.info(f"Scenario {scenario_id} loaded successfully: {result}")
            return result

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to load scenario {scenario_id}: {e}")
            msg = f"Failed to load scenario {scenario_id}: {e}"
            raise ScenarioLoadError(msg) from e

    def _validate_scenario(self, scenario: ScenarioDefinition) -> None:
        """Validate scenario definition before loading.

        Checks for:
        - Referenced customers exist in customers list
        - Referenced sales orders exist in sales_orders list
        - Referenced invoices exist in invoices list
        - Semantic memory subjects reference defined customers

        Raises:
            ScenarioLoadError: If validation fails with specific error message
        """
        customer_names = {c.name for c in scenario.domain_setup.customers}
        so_numbers = {so.so_number for so in scenario.domain_setup.sales_orders}
        invoice_numbers = {inv.invoice_number for inv in scenario.domain_setup.invoices}

        # Validate sales orders reference existing customers
        for so_setup in scenario.domain_setup.sales_orders:
            if so_setup.customer_name not in customer_names:
                msg = (
                    f"Validation failed: Sales order '{so_setup.so_number}' references "
                    f"customer '{so_setup.customer_name}' which is not defined in scenario. "
                    f"Available customers: {sorted(customer_names)}"
                )
                raise ScenarioLoadError(msg)

        # Validate invoices reference existing sales orders
        for invoice_setup in scenario.domain_setup.invoices:
            if invoice_setup.sales_order_number not in so_numbers:
                msg = (
                    f"Validation failed: Invoice '{invoice_setup.invoice_number}' references "
                    f"sales order '{invoice_setup.sales_order_number}' which is not defined in scenario. "
                    f"Available sales orders: {sorted(so_numbers)}"
                )
                raise ScenarioLoadError(msg)

        # Validate work orders reference existing sales orders
        for wo_setup in scenario.domain_setup.work_orders:
            if wo_setup.sales_order_number not in so_numbers:
                msg = (
                    f"Validation failed: Work order references "
                    f"sales order '{wo_setup.sales_order_number}' which is not defined in scenario. "
                    f"Available sales orders: {sorted(so_numbers)}"
                )
                raise ScenarioLoadError(msg)

        # Validate payments reference existing invoices
        for payment_setup in scenario.domain_setup.payments:
            if payment_setup.invoice_number not in invoice_numbers:
                msg = (
                    f"Validation failed: Payment references "
                    f"invoice '{payment_setup.invoice_number}' which is not defined in scenario. "
                    f"Available invoices: {sorted(invoice_numbers)}"
                )
                raise ScenarioLoadError(msg)

        # Validate tasks reference existing customers (if specified)
        for task_setup in scenario.domain_setup.tasks:
            if task_setup.customer_name and task_setup.customer_name not in customer_names:
                msg = (
                    f"Validation failed: Task '{task_setup.title}' references "
                    f"customer '{task_setup.customer_name}' which is not defined in scenario. "
                    f"Available customers: {sorted(customer_names)}"
                )
                raise ScenarioLoadError(msg)

        # Validate semantic memories reference existing customers
        for memory_setup in scenario.semantic_memories:
            for entity_name in memory_setup.entities:
                if entity_name not in customer_names:
                    msg = (
                        f"Validation failed: Semantic memory '{memory_setup.content[:50]}...' references "
                        f"entity '{entity_name}' which is not defined as a customer in scenario. "
                        f"Available customers: {sorted(customer_names)}"
                    )
                    raise ScenarioLoadError(msg)

        logger.debug(f"Scenario {scenario.scenario_id} validation passed")

    async def _load_customers(self, scenario: ScenarioDefinition) -> int:
        """Load customers from scenario (idempotent)."""
        count = 0
        for customer_setup in scenario.domain_setup.customers:
            # Check if customer already exists
            result = await self.session.execute(
                select(DomainCustomer).where(DomainCustomer.name == customer_setup.name)
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug("Customer '%s' already exists, using existing ID", customer_setup.name)
                self._entity_map[customer_setup.name] = existing.customer_id
                continue

            # Create new customer
            customer = DomainCustomer(
                name=customer_setup.name,
                industry=customer_setup.industry,
                notes=customer_setup.notes,
            )
            self.session.add(customer)
            await self.session.flush()  # Get the generated UUID

            # Track for foreign key references
            self._entity_map[customer.name] = customer.customer_id
            count += 1
            logger.debug("Created customer: %s (ID: %s)", customer.name, customer.customer_id)

        return count

    async def _load_sales_orders(self, scenario: ScenarioDefinition) -> int:
        """Load sales orders from scenario (idempotent)."""
        count = 0
        for so_setup in scenario.domain_setup.sales_orders:
            # Check if sales order already exists
            result = await self.session.execute(
                select(DomainSalesOrder).where(DomainSalesOrder.so_number == so_setup.so_number)
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug("Sales order '%s' already exists, using existing ID", so_setup.so_number)
                self._entity_map[so_setup.so_number] = existing.so_id
                continue

            # Look up customer UUID
            customer_id = self._entity_map.get(so_setup.customer_name)
            if not customer_id:
                msg = f"Customer '{so_setup.customer_name}' not found for sales order {so_setup.so_number}"
                raise ScenarioLoadError(
                    msg
                )

            # Create new sales order
            sales_order = DomainSalesOrder(
                customer_id=customer_id,
                so_number=so_setup.so_number,
                title=so_setup.title,
                status=so_setup.status,
            )
            self.session.add(sales_order)
            await self.session.flush()

            # Track for foreign key references
            self._entity_map[so_setup.so_number] = sales_order.so_id
            count += 1
            logger.debug("Created sales order: %s (ID: %s)", sales_order.so_number, sales_order.so_id)

        return count

    async def _load_invoices(self, scenario: ScenarioDefinition) -> int:
        """Load invoices from scenario (idempotent)."""
        count = 0
        for invoice_setup in scenario.domain_setup.invoices:
            # Check if invoice already exists
            result = await self.session.execute(
                select(DomainInvoice).where(DomainInvoice.invoice_number == invoice_setup.invoice_number)
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug("Invoice '%s' already exists, using existing ID", invoice_setup.invoice_number)
                self._entity_map[invoice_setup.invoice_number] = existing.invoice_id
                continue

            # Look up sales order UUID
            so_id = self._entity_map.get(invoice_setup.sales_order_number)
            if not so_id:
                msg = f"Sales order '{invoice_setup.sales_order_number}' not found for invoice {invoice_setup.invoice_number}"
                raise ScenarioLoadError(
                    msg
                )

            # Create new invoice
            invoice = DomainInvoice(
                so_id=so_id,
                invoice_number=invoice_setup.invoice_number,
                amount=invoice_setup.amount,
                due_date=invoice_setup.due_date,
                status=invoice_setup.status,
            )
            self.session.add(invoice)
            await self.session.flush()

            # Track for foreign key references
            self._entity_map[invoice_setup.invoice_number] = invoice.invoice_id
            count += 1
            logger.debug("Created invoice: %s (ID: %s)", invoice.invoice_number, invoice.invoice_id)

        return count

    async def _load_work_orders(self, scenario: ScenarioDefinition) -> int:
        """Load work orders from scenario (idempotent)."""
        count = 0
        for wo_setup in scenario.domain_setup.work_orders:
            so_id = self._entity_map.get(wo_setup.sales_order_number)
            if not so_id:
                msg = f"Sales order '{wo_setup.sales_order_number}' not found for work order"
                raise ScenarioLoadError(
                    msg
                )

            # Check if work order already exists (match by SO + description)
            result = await self.session.execute(
                select(DomainWorkOrder).where(
                    DomainWorkOrder.so_id == so_id,
                    DomainWorkOrder.description == wo_setup.description
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug("Work order for '%s' already exists", wo_setup.description)
                continue

            work_order = DomainWorkOrder(
                so_id=so_id,
                description=wo_setup.description,
                status=wo_setup.status,
                technician=wo_setup.technician,
                scheduled_for=wo_setup.scheduled_for,
            )
            self.session.add(work_order)
            count += 1
            logger.debug("Created work order: %s for SO %s", wo_setup.description, wo_setup.sales_order_number)

        await self.session.flush()
        return count

    async def _load_payments(self, scenario: ScenarioDefinition) -> int:
        """Load payments from scenario (idempotent)."""
        count = 0
        for payment_setup in scenario.domain_setup.payments:
            invoice_id = self._entity_map.get(payment_setup.invoice_number)
            if not invoice_id:
                msg = f"Invoice '{payment_setup.invoice_number}' not found for payment"
                raise ScenarioLoadError(
                    msg
                )

            # Check if payment already exists (match by invoice + amount + method)
            result = await self.session.execute(
                select(DomainPayment).where(
                    DomainPayment.invoice_id == invoice_id,
                    DomainPayment.amount == payment_setup.amount,
                    DomainPayment.method == payment_setup.method
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug("Payment of $%s for invoice %s already exists", payment_setup.amount, payment_setup.invoice_number)
                continue

            payment = DomainPayment(
                invoice_id=invoice_id,
                amount=payment_setup.amount,
                method=payment_setup.method,
            )
            self.session.add(payment)
            count += 1
            logger.debug("Created payment: $%s for invoice %s", payment_setup.amount, payment_setup.invoice_number)

        await self.session.flush()
        return count

    async def _load_tasks(self, scenario: ScenarioDefinition) -> int:
        """Load tasks from scenario (idempotent)."""
        count = 0
        for task_setup in scenario.domain_setup.tasks:
            customer_id = None
            if task_setup.customer_name:
                customer_id = self._entity_map.get(task_setup.customer_name)
                if not customer_id:
                    msg = f"Customer '{task_setup.customer_name}' not found for task"
                    raise ScenarioLoadError(
                        msg
                    )

            # Check if task already exists (match by title)
            result = await self.session.execute(
                select(DomainTask).where(DomainTask.title == task_setup.title)
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug("Task '%s' already exists", task_setup.title)
                continue

            task = DomainTask(
                customer_id=customer_id,
                title=task_setup.title,
                body=task_setup.body,
                status=task_setup.status,
            )
            self.session.add(task)
            count += 1
            logger.debug("Created task: %s", task_setup.title)

        await self.session.flush()
        return count

    async def _create_canonical_entities(self) -> None:
        """Create canonical entities for customers loaded in this scenario (idempotent).

        For Phase 1: Simple approach - create canonical entity for each customer.
        Phase 2: Integrate with EntityResolutionService.
        """
        # Only process customers created/referenced in this load
        for customer_id in self._entity_map.values():
            # Skip non-customer entities
            if not isinstance(customer_id, UUID):
                continue

            # Fetch customer details
            result = await self.session.execute(
                select(DomainCustomer).where(DomainCustomer.customer_id == customer_id)
            )
            customer = result.scalar_one_or_none()
            if not customer:
                continue  # Customer might be a sales order or invoice

            entity_id = f"customer:{customer.customer_id}"

            # Check if canonical entity already exists
            existing_entity = await self.session.execute(
                select(CanonicalEntity).where(CanonicalEntity.entity_id == entity_id)
            )
            if existing_entity.scalar_one_or_none():
                logger.debug("Canonical entity %s already exists", entity_id)
                self._canonical_entity_map[customer.name] = entity_id
                continue

            # Create canonical entity
            canonical_entity = CanonicalEntity(
                entity_id=entity_id,
                entity_type="customer",
                canonical_name=customer.name,
                external_ref={
                    "table": "domain.customers",
                    "id": str(customer.customer_id),
                },
                properties={"industry": customer.industry, "notes": customer.notes},
            )
            self.session.add(canonical_entity)

            # Check if alias already exists
            existing_alias = await self.session.execute(
                select(EntityAlias).where(
                    EntityAlias.canonical_entity_id == entity_id,
                    EntityAlias.alias_text == customer.name,
                    EntityAlias.user_id == self.user_id
                )
            )
            if not existing_alias.scalar_one_or_none():
                # Create primary alias
                alias = EntityAlias(
                    canonical_entity_id=entity_id,
                    alias_text=customer.name,
                    alias_source="exact",
                    user_id=self.user_id,
                    confidence=1.0,
                    use_count=1,
                )
                self.session.add(alias)

            # Track for memory creation
            self._canonical_entity_map[customer.name] = entity_id

            logger.debug("Created canonical entity: %s for %s", entity_id, customer.name)

        await self.session.flush()

    async def _load_semantic_memories(self, scenario: ScenarioDefinition) -> int:
        """Load semantic memories from scenario (idempotent).

        For Phase 1: Direct creation using natural language schema.
        Phase 2: Use SemanticExtractionService.
        """
        count = 0
        for memory_setup in scenario.semantic_memories:
            # Resolve all entity names to entity_ids
            entity_ids = []
            for entity_name in memory_setup.entities:
                entity_id = self._canonical_entity_map.get(entity_name)
                if not entity_id:
                    msg = f"Canonical entity for '{entity_name}' not found in loaded scenario"
                    raise ScenarioLoadError(msg)
                entity_ids.append(entity_id)

            # Check if memory already exists (match by content and user_id)
            existing = await self.session.execute(
                select(SemanticMemory).where(
                    SemanticMemory.user_id == self.user_id,
                    SemanticMemory.content == memory_setup.content,
                    SemanticMemory.status == "active"
                )
            )
            if existing.scalar_one_or_none():
                logger.debug("Semantic memory '%s' already exists", memory_setup.content[:50])
                continue

            # Create semantic memory using natural language schema
            memory = SemanticMemory(
                user_id=self.user_id,
                content=memory_setup.content,  # Natural language statement
                entities=entity_ids,  # Array of resolved entity IDs
                confidence=memory_setup.confidence,
                importance=memory_setup.importance,
                source_type="scenario_load",
                source_text=memory_setup.content,  # For explainability
                status="active",
                memory_metadata={
                    "base_confidence": memory_setup.confidence,
                    "source": "scenario_load",
                },
                # embedding will be None for Phase 1
            )
            self.session.add(memory)
            count += 1
            logger.debug("Created semantic memory: %s", memory_setup.content[:50])

        await self.session.flush()
        return count

    async def reset(self) -> None:
        """Delete ALL data from both domain and app schemas.

        WARNING: This is destructive and cannot be undone.
        Clears everything from domain schema and all user data from app schema.
        """
        logger.warning("Resetting ALL demo data (domain + app schemas)")

        try:
            # ============================================================
            # DOMAIN SCHEMA - Delete ALL data (respect foreign keys)
            # ============================================================
            logger.info("Clearing domain schema...")
            await self.session.execute(delete(DomainPayment))
            await self.session.execute(delete(DomainInvoice))
            await self.session.execute(delete(DomainWorkOrder))
            await self.session.execute(delete(DomainSalesOrder))
            await self.session.execute(delete(DomainTask))
            await self.session.execute(delete(DomainCustomer))

            # ============================================================
            # APP SCHEMA - Delete ALL user data (respect foreign keys)
            # ============================================================
            logger.info("Clearing app schema...")

            # Step 1: Delete tool usage logs (no FK dependencies)
            await self.session.execute(delete(ToolUsageLog))

            # Step 2: Delete memory conflicts (no FK dependencies)
            await self.session.execute(delete(MemoryConflict))

            # Step 3: Delete memory summaries (self-referencing FK)
            await self.session.execute(delete(MemorySummary))

            # Step 4: Delete all memory types
            await self.session.execute(delete(ProceduralMemory))
            await self.session.execute(delete(SemanticMemory))
            await self.session.execute(delete(EpisodicMemory))

            # Step 5: Delete chat events
            await self.session.execute(delete(ChatEvent))

            # Step 6: Delete entity aliases (FK to canonical_entities)
            await self.session.execute(delete(EntityAlias))

            # Step 7: Delete canonical entities
            await self.session.execute(delete(CanonicalEntity))

            # Step 8: Delete domain ontology
            await self.session.execute(delete(DomainOntology))

            # Note: We do NOT delete from:
            # - alembic_version (migration tracking)
            # - system_config (system settings)

            await self.session.commit()
            logger.info("ALL demo data reset successfully (domain + app schemas cleared)")

        except Exception as e:
            await self.session.rollback()
            logger.error("Failed to reset demo data: %s", str(e))
            msg = f"Failed to reset demo data: {e!s}"
            raise ScenarioLoadError(msg) from e

    async def reset_memories_only(self) -> None:
        """Delete ALL memory/chat/entity data from app schema (keep domain data intact).

        WARNING: This is destructive and cannot be undone.
        Clears everything from app schema except system_config and alembic_version.
        Keeps all domain schema data (customers, invoices, etc.).
        """
        logger.warning("Clearing ALL app schema data (keeping domain data)")

        try:
            # ============================================================
            # APP SCHEMA ONLY - Delete ALL data (respect foreign keys)
            # Keep domain schema untouched
            # ============================================================

            # Step 1: Delete tool usage logs (no FK dependencies)
            await self.session.execute(delete(ToolUsageLog))

            # Step 2: Delete memory conflicts (no FK dependencies)
            await self.session.execute(delete(MemoryConflict))

            # Step 3: Delete memory summaries (self-referencing FK)
            await self.session.execute(delete(MemorySummary))

            # Step 4: Delete all memory types
            await self.session.execute(delete(ProceduralMemory))
            await self.session.execute(delete(SemanticMemory))
            await self.session.execute(delete(EpisodicMemory))

            # Step 5: Delete chat events
            await self.session.execute(delete(ChatEvent))

            # Step 6: Delete entity aliases (FK to canonical_entities)
            await self.session.execute(delete(EntityAlias))

            # Step 7: Delete canonical entities
            await self.session.execute(delete(CanonicalEntity))

            # Step 8: Delete domain ontology
            await self.session.execute(delete(DomainOntology))

            # Note: We do NOT delete from:
            # - alembic_version (migration tracking)
            # - system_config (system settings)
            # - domain schema (customers, invoices, etc. - preserved)

            await self.session.commit()
            logger.info("ALL app schema data cleared successfully (domain data preserved)")

        except Exception as e:
            await self.session.rollback()
            logger.error("Failed to clear memory data: %s", str(e))
            msg = f"Failed to clear memory data: {e!s}"
            raise ScenarioLoadError(msg) from e
