"""API endpoints for scenario management."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.demo.services.scenario_loader import ScenarioLoaderService, ScenarioLoadError
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


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=List[ScenarioSummaryResponse])
async def list_scenarios() -> List[ScenarioSummaryResponse]:
    """List all available scenarios.

    Returns:
        List of scenario summaries with ID, title, description, and expected query.
    """
    scenarios = ScenarioRegistry.get_all()
    return [
        ScenarioSummaryResponse(
            scenario_id=s.scenario_id,
            title=s.title,
            description=s.description,
            category=s.category,
            expected_query=s.expected_query,
        )
        for s in scenarios
    ]


@router.get("/{scenario_id}", response_model=ScenarioSummaryResponse)
async def get_scenario(scenario_id: int) -> ScenarioSummaryResponse:
    """Get detailed information about a specific scenario.

    Args:
        scenario_id: ID of the scenario (1-18)

    Returns:
        Scenario summary

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
            )
        # Provide user-friendly error messages
        if "IntegrityError" in error_msg or "duplicate key" in error_msg.lower():
            raise HTTPException(
                status_code=409,
                detail=f"Scenario {scenario_id} data conflicts with existing data. Use reset endpoint first."
            )
        # Generic error with sanitized message
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load scenario {scenario_id}. Please check server logs for details."
        )


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
    except ScenarioLoadError as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to reset demo data. Please check server logs for details."
        )
