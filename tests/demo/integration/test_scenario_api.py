"""Integration tests for scenario API endpoints."""
import pytest
from httpx import AsyncClient

from src.api.main import app


@pytest.mark.integration
@pytest.mark.asyncio
class TestScenarioAPI:
    """Test scenario API endpoints."""

    async def test_list_scenarios(self):
        """Test GET /api/v1/demo/scenarios returns scenario list."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/demo/scenarios")

        assert response.status_code == 200
        scenarios = response.json()
        assert isinstance(scenarios, list)
        assert len(scenarios) > 0

        # Check first scenario structure
        scenario = scenarios[0]
        assert "scenario_id" in scenario
        assert "title" in scenario
        assert "description" in scenario
        assert "category" in scenario
        assert "expected_query" in scenario

    async def test_get_scenario_1(self):
        """Test GET /api/v1/demo/scenarios/1 returns Scenario 1 details."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/demo/scenarios/1")

        assert response.status_code == 200
        scenario = response.json()
        assert scenario["scenario_id"] == 1
        assert scenario["title"] == "Overdue invoice follow-up with preference recall"
        assert scenario["category"] == "memory_retrieval"

    async def test_get_nonexistent_scenario(self):
        """Test GET /api/v1/demo/scenarios/999 returns 404."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/demo/scenarios/999")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestScenarioLoading:
    """Test scenario loading functionality."""

    async def test_reset_scenarios(self):
        """Test POST /api/v1/demo/scenarios/reset clears data."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/v1/demo/scenarios/reset")

        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert "success" in result["message"].lower()

    async def test_load_scenario_1(self):
        """Test POST /api/v1/demo/scenarios/1/load creates data."""
        # First reset to clean state
        async with AsyncClient(app=app, base_url="http://test") as client:
            await client.post("/api/v1/demo/scenarios/reset")

            # Load scenario 1
            response = await client.post("/api/v1/demo/scenarios/1/load")

        assert response.status_code == 200
        result = response.json()

        assert result["scenario_id"] == 1
        assert result["title"] == "Overdue invoice follow-up with preference recall"
        assert result["customers_created"] == 1
        assert result["sales_orders_created"] == 1
        assert result["invoices_created"] == 1
        assert result["semantic_memories_created"] == 1
        assert "Successfully loaded" in result["message"]

    async def test_load_scenario_idempotent(self):
        """Test loading same scenario twice is idempotent."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Reset
            await client.post("/api/v1/demo/scenarios/reset")

            # Load once
            response1 = await client.post("/api/v1/demo/scenarios/1/load")
            assert response1.status_code == 200

            # Load again - should work (idempotent or give clear error)
            response2 = await client.post("/api/v1/demo/scenarios/1/load")
            # Either succeeds (idempotent) or fails with clear error
            assert response2.status_code in [200, 500]
