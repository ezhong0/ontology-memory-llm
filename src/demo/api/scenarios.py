"""API endpoints for scenario management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.demo.services.scenario_loader import ScenarioLoadError, ScenarioLoaderService
from src.demo.services.scenario_registry import ScenarioRegistry
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/scenarios", tags=["demo-scenarios"])


# =============================================================================
# Response Models
# =============================================================================


class ScenarioSummaryResponse(BaseModel):
    """Summary information about a scenario."""

    scenario_id: int
    title: str
    description: str
    category: str
    expected_query: str
    expected_behavior: str | None = None
    # Setup preview - what will be created
    customers_count: int = 0
    sales_orders_count: int = 0
    invoices_count: int = 0
    work_orders_count: int = 0
    payments_count: int = 0
    tasks_count: int = 0
    memories_count: int = 0

    class Config:
        from_attributes = True


class ScenarioLoadResponse(BaseModel):
    """Response from loading a scenario."""

    scenario_id: int
    title: str
    customers_created: int
    sales_orders_created: int
    invoices_created: int
    work_orders_created: int
    payments_created: int
    tasks_created: int
    semantic_memories_created: int
    episodic_memories_created: int
    message: str

    class Config:
        from_attributes = True


class ResetResponse(BaseModel):
    """Response from reset operation."""

    message: str


class ScenarioDataResponse(BaseModel):
    """Full data that will be loaded by a scenario."""

    scenario_id: int
    title: str
    description: str
    category: str
    # Domain data that will be loaded
    customers: list[dict]
    sales_orders: list[dict]
    invoices: list[dict]
    work_orders: list[dict]
    payments: list[dict]
    tasks: list[dict]
    # Memory data that will be loaded
    semantic_memories: list[dict]

    class Config:
        from_attributes = True


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=list[ScenarioSummaryResponse])
async def list_scenarios() -> list[ScenarioSummaryResponse]:
    """List all available scenarios.

    Returns:
        List of scenario summaries with ID, title, description, expected query, and setup counts.
    """
    scenarios = ScenarioRegistry.get_all()
    return [
        ScenarioSummaryResponse(
            scenario_id=s.scenario_id,
            title=s.title,
            description=s.description,
            category=s.category,
            expected_query=s.expected_query,
            expected_behavior=s.expected_behavior,
            # Count what will be created
            customers_count=len(s.domain_setup.customers),
            sales_orders_count=len(s.domain_setup.sales_orders),
            invoices_count=len(s.domain_setup.invoices),
            work_orders_count=len(s.domain_setup.work_orders),
            payments_count=len(s.domain_setup.payments),
            tasks_count=len(s.domain_setup.tasks),
            memories_count=len(s.semantic_memories),
        )
        for s in scenarios
    ]


@router.get("/{scenario_id}", response_model=ScenarioSummaryResponse)
async def get_scenario(scenario_id: int) -> ScenarioSummaryResponse:
    """Get detailed information about a specific scenario.

    Args:
        scenario_id: ID of the scenario (1-18)

    Returns:
        Scenario summary with setup counts

    Raises:
        404: If scenario not found
    """
    scenario = ScenarioRegistry.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")

    return ScenarioSummaryResponse(
        scenario_id=scenario.scenario_id,
        title=scenario.title,
        description=scenario.description,
        category=scenario.category,
        expected_query=scenario.expected_query,
        expected_behavior=scenario.expected_behavior,
        # Count what will be created
        customers_count=len(scenario.domain_setup.customers),
        sales_orders_count=len(scenario.domain_setup.sales_orders),
        invoices_count=len(scenario.domain_setup.invoices),
        work_orders_count=len(scenario.domain_setup.work_orders),
        payments_count=len(scenario.domain_setup.payments),
        tasks_count=len(scenario.domain_setup.tasks),
        memories_count=len(scenario.semantic_memories),
    )


@router.get("/{scenario_id}/data", response_model=ScenarioDataResponse)
async def get_scenario_data(scenario_id: int) -> ScenarioDataResponse:
    """Get full data that will be loaded by a scenario.

    This returns the actual customer names, invoice numbers, memory details, etc.
    that will be created when the scenario is loaded.

    Args:
        scenario_id: ID of the scenario (1-18)

    Returns:
        Full scenario data including all domain records and memories

    Raises:
        404: If scenario not found
    """
    scenario = ScenarioRegistry.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")

    # Convert setup objects to dicts
    customers = [
        {
            "name": c.name,
            "industry": c.industry,
        }
        for c in scenario.domain_setup.customers
    ]

    sales_orders = [
        {
            "so_number": so.so_number,
            "customer_name": so.customer_name,
            "title": so.title,
            "status": so.status,
        }
        for so in scenario.domain_setup.sales_orders
    ]

    invoices = [
        {
            "invoice_number": inv.invoice_number,
            "sales_order_number": inv.sales_order_number,
            "amount": str(inv.amount),
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "status": inv.status,
        }
        for inv in scenario.domain_setup.invoices
    ]

    work_orders = [
        {
            "sales_order_number": wo.sales_order_number,
            "description": wo.description,
            "status": wo.status,
            "technician": wo.technician,
            "scheduled_for": wo.scheduled_for.isoformat() if wo.scheduled_for else None,
        }
        for wo in scenario.domain_setup.work_orders
    ]

    payments = [
        {
            "invoice_number": pay.invoice_number,
            "amount": str(pay.amount),
            "method": pay.method,
        }
        for pay in scenario.domain_setup.payments
    ]

    tasks = [
        {
            "customer_name": task.customer_name,
            "title": task.title,
            "body": task.body,
            "status": task.status,
        }
        for task in scenario.domain_setup.tasks
    ]

    semantic_memories = [
        {
            "subject": mem.subject,
            "predicate": mem.predicate,
            "predicate_type": mem.predicate_type,
            "object_value": mem.object_value,
            "confidence": mem.confidence,
        }
        for mem in scenario.semantic_memories
    ]

    return ScenarioDataResponse(
        scenario_id=scenario.scenario_id,
        title=scenario.title,
        description=scenario.description,
        category=scenario.category,
        customers=customers,
        sales_orders=sales_orders,
        invoices=invoices,
        work_orders=work_orders,
        payments=payments,
        tasks=tasks,
        semantic_memories=semantic_memories,
    )


@router.post("/{scenario_id}/load", response_model=ScenarioLoadResponse)
async def load_scenario(
    scenario_id: int, session: AsyncSession = Depends(get_db)
) -> ScenarioLoadResponse:
    """Load a scenario into the system.

    This will:
    1. Insert domain data (customers, orders, invoices, etc.)
    2. Create canonical entities
    3. Create initial memories

    The operation is idempotent (can be called multiple times safely).

    Args:
        scenario_id: ID of the scenario to load (1-18)
        session: Database session (injected)

    Returns:
        Scenario load result with counts

    Raises:
        404: If scenario not found
        500: If scenario loading fails
    """
    try:
        loader = ScenarioLoaderService(session)
        result = await loader.load_scenario(scenario_id)
        return ScenarioLoadResponse(
            scenario_id=result.scenario_id,
            title=result.title,
            customers_created=result.customers_created,
            sales_orders_created=result.sales_orders_created,
            invoices_created=result.invoices_created,
            work_orders_created=result.work_orders_created,
            payments_created=result.payments_created,
            tasks_created=result.tasks_created,
            semantic_memories_created=result.semantic_memories_created,
            episodic_memories_created=result.episodic_memories_created,
            message=result.message,
        )
    except ScenarioLoadError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=f"Scenario {scenario_id} not found. Available scenarios: 1-18."
            ) from None
        # Provide user-friendly error messages
        if "IntegrityError" in error_msg or "duplicate key" in error_msg.lower():
            raise HTTPException(
                status_code=409,
                detail=f"Scenario {scenario_id} data conflicts with existing data. Use reset endpoint first."
            ) from None
        # Generic error with sanitized message
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load scenario {scenario_id}. Please check server logs for details."
        ) from None


@router.post("/reset", response_model=ResetResponse)
async def reset_all(session: AsyncSession = Depends(get_db)) -> ResetResponse:
    """Reset all demo data (domain and memory data).

    WARNING: This is destructive and cannot be undone.
    Deletes all data in domain schema and all demo-user data in app schema.

    Args:
        session: Database session (injected)

    Returns:
        Success message

    Raises:
        500: If reset fails
    """
    try:
        loader = ScenarioLoaderService(session)
        await loader.reset()
        return ResetResponse(message="All demo data reset successfully")
    except ScenarioLoadError:
        raise HTTPException(
            status_code=500,
            detail="Failed to reset demo data. Please check server logs for details."
        ) from None


@router.post("/reset-memories", response_model=ResetResponse)
async def reset_memories(session: AsyncSession = Depends(get_db)) -> ResetResponse:
    """Reset only memory data (keep domain data intact).

    WARNING: This is destructive and cannot be undone.
    Deletes all chat events, entities, aliases, and memories for demo users.

    Args:
        session: Database session (injected)

    Returns:
        Success message

    Raises:
        500: If reset fails
    """
    try:
        loader = ScenarioLoaderService(session)
        await loader.reset_memories_only()
        return ResetResponse(message="Memory data cleared successfully")
    except ScenarioLoadError:
        raise HTTPException(
            status_code=500,
            detail="Failed to clear memory data. Please check server logs for details."
        ) from None
