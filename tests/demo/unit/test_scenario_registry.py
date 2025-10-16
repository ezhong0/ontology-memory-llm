"""Unit tests for scenario registry."""
import pytest

from src.demo.services.scenario_registry import ScenarioRegistry


class TestScenarioRegistry:
    """Test scenario registry operations."""

    def test_get_scenario_1(self):
        """Test retrieving Scenario 1."""
        scenario = ScenarioRegistry.get(1)

        assert scenario is not None
        assert scenario.scenario_id == 1
        assert scenario.title == "Overdue invoice follow-up with preference recall"
        assert scenario.category == "financial"

    def test_get_nonexistent_scenario(self):
        """Test retrieving non-existent scenario returns None."""
        scenario = ScenarioRegistry.get(999)
        assert scenario is None

    def test_get_all_scenarios(self):
        """Test getting all scenarios."""
        scenarios = ScenarioRegistry.get_all()

        assert len(scenarios) > 0
        assert all(s.scenario_id for s in scenarios)
        # Should be sorted by scenario_id
        assert scenarios == sorted(scenarios, key=lambda s: s.scenario_id)

    def test_get_by_category(self):
        """Test getting scenarios by category."""
        scenarios = ScenarioRegistry.get_by_category("financial")

        assert len(scenarios) > 0
        assert all(s.category == "financial" for s in scenarios)

    def test_scenario_1_structure(self):
        """Test Scenario 1 has correct structure."""
        scenario = ScenarioRegistry.get(1)

        # Check domain setup
        assert len(scenario.domain_setup.customers) == 1
        assert scenario.domain_setup.customers[0].name == "Kai Media"

        assert len(scenario.domain_setup.sales_orders) == 1
        assert scenario.domain_setup.sales_orders[0].so_number == "SO-1001"

        assert len(scenario.domain_setup.invoices) == 1
        assert scenario.domain_setup.invoices[0].invoice_number == "INV-1009"
        assert scenario.domain_setup.invoices[0].amount == 1200.00

        # Check semantic memories
        assert len(scenario.semantic_memories) == 1
        memory = scenario.semantic_memories[0]
        assert memory.subject == "Kai Media"
        assert memory.predicate == "prefers_delivery_day"
        assert memory.object_value == {"day": "Friday"}
