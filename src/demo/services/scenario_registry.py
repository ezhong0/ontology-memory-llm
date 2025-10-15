"""Registry of all scenario definitions.

Each scenario defines a complete test case for the memory system.
Scenarios are numbered 1-18 matching ProjectDescription.md.

For Phase 1, we start with Scenario 1 only.
"""
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from src.demo.models.scenario import (
    CustomerSetup,
    DomainDataSetup,
    InvoiceSetup,
    PaymentSetup,
    SalesOrderSetup,
    ScenarioDefinition,
    SemanticMemorySetup,
    TaskSetup,
    WorkOrderSetup,
)


class ScenarioRegistry:
    """Registry of all scenario definitions."""

    _scenarios: Dict[int, ScenarioDefinition] = {}

    @classmethod
    def register(cls, scenario: ScenarioDefinition) -> None:
        """Register a scenario."""
        cls._scenarios[scenario.scenario_id] = scenario

    @classmethod
    def get(cls, scenario_id: int) -> Optional[ScenarioDefinition]:
        """Get scenario by ID."""
        return cls._scenarios.get(scenario_id)

    @classmethod
    def get_all(cls) -> List[ScenarioDefinition]:
        """Get all scenarios."""
        return sorted(cls._scenarios.values(), key=lambda s: s.scenario_id)

    @classmethod
    def get_by_category(cls, category: str) -> List[ScenarioDefinition]:
        """Get all scenarios in a category."""
        return [s for s in cls.get_all() if s.category == category]


# =============================================================================
# SCENARIO DEFINITIONS
# =============================================================================

# Scenario 1: Overdue invoice follow-up with preference recall
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=1,
        title="Overdue invoice follow-up with preference recall",
        description=(
            "Finance agent wants to nudge customer while honoring delivery preferences. "
            "System must retrieve invoice from DB and preference from memory."
        ),
        category="memory_retrieval",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Kai Media", industry="Entertainment", notes="Music distribution company"
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Kai Media",
                    so_number="SO-1001",
                    title="Album Fulfillment",
                    status="in_fulfillment",
                )
            ],
            invoices=[
                InvoiceSetup(
                    sales_order_number="SO-1001",
                    invoice_number="INV-1009",
                    amount=Decimal("1200.00"),
                    due_date=date(2025, 9, 30),
                    status="open",
                )
            ],
        ),
        expected_query=(
            "Draft an email for Kai Media about their unpaid invoice and mention "
            "their preferred delivery day for the next shipment."
        ),
        expected_behavior=(
            "Retrieval surfaces INV-1009 (open, $1200, due 2025-09-30) + memory "
            "preference. Reply mentions invoice details and references Friday delivery. "
            "Memory update: add episodic note that an invoice reminder was initiated today."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Kai Media",
                predicate="prefers_delivery_day",
                predicate_type="preference",
                object_value={"day": "Friday"},
                confidence=0.85,
            )
        ],
    )
)

# Scenario 2: Multiple preferences recall
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=2,
        title="Multiple preferences recall for customer outreach",
        description=(
            "Sales agent needs to contact customer about upcoming invoice. "
            "System must retrieve multiple preferences (contact method, payment terms, timezone)."
        ),
        category="memory_retrieval",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="TechStart Inc",
                    industry="Technology",
                    notes="Early-stage startup, rapid growth"
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="TechStart Inc",
                    so_number="SO-2001",
                    title="Cloud Infrastructure Setup",
                    status="fulfilled",
                )
            ],
            invoices=[
                InvoiceSetup(
                    sales_order_number="SO-2001",
                    invoice_number="INV-2034",
                    amount=Decimal("8500.00"),
                    due_date=date(2025, 10, 15),
                    status="open",
                )
            ],
        ),
        expected_query=(
            "What's the best way to reach TechStart Inc about their upcoming invoice?"
        ),
        expected_behavior=(
            "Retrieval surfaces INV-2034 (open, $8500, due 2025-10-15) + contact preferences. "
            "Reply mentions Slack as preferred contact method, NET45 payment terms, and PST timezone. "
            "Memory update: episodic note about outreach attempt."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="TechStart Inc",
                predicate="prefers_contact_method",
                predicate_type="preference",
                object_value={"method": "Slack", "handle": "@techstart-finance"},
                confidence=0.90,
            ),
            SemanticMemorySetup(
                subject="TechStart Inc",
                predicate="payment_terms",
                predicate_type="requirement",
                object_value={"terms": "NET45", "reason": "cash flow planning"},
                confidence=0.95,
            ),
            SemanticMemorySetup(
                subject="TechStart Inc",
                predicate="timezone",
                predicate_type="attribute",
                object_value={"timezone": "America/Los_Angeles", "label": "PST/PDT"},
                confidence=0.85,
            ),
        ],
    )
)

# Scenario 3: Historical context and past issues
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=3,
        title="Past issue recall for quality-sensitive customer",
        description=(
            "Sales team preparing quote for customer with past quality issues. "
            "System must surface historical context to inform current work."
        ),
        category="memory_retrieval",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="BuildRight Construction",
                    industry="Construction",
                    notes="Mid-sized regional contractor"
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="BuildRight Construction",
                    so_number="SO-3001",
                    title="Steel Beams - Downtown Project",
                    status="fulfilled",
                )
            ],
            tasks=[
                TaskSetup(
                    customer_name="BuildRight Construction",
                    title="Prepare quote for new residential project",
                    body="BuildRight requesting quote for 50-unit development",
                    status="todo",
                )
            ],
        ),
        expected_query=(
            "Prepare a quote for BuildRight's new project"
        ),
        expected_behavior=(
            "Retrieval surfaces task + past issue memory. Reply includes quote but emphasizes "
            "quality controls, detailed specifications, and reference to resolved past complaint. "
            "Shows awareness of customer's high standards."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="BuildRight Construction",
                predicate="past_issue",
                predicate_type="observation",
                object_value={
                    "issue": "Quality complaint on SO-3001",
                    "resolution": "Replaced 3 beams, added extra QC step",
                    "date": "2025-08-15",
                    "resolved": True
                },
                confidence=0.95,
            ),
            SemanticMemorySetup(
                subject="BuildRight Construction",
                predicate="requires_detailed_specs",
                predicate_type="requirement",
                object_value={
                    "detail_level": "high",
                    "includes": ["material certs", "tolerance specs", "delivery schedule"]
                },
                confidence=0.88,
            ),
        ],
    )
)

# Scenario 4: Payment behavior patterns
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=4,
        title="Payment behavior prediction for collections",
        description=(
            "Finance team managing collections for customer with known payment patterns. "
            "System must retrieve behavioral observations to predict payment timing."
        ),
        category="memory_retrieval",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="MediCare Plus",
                    industry="Healthcare",
                    notes="Regional healthcare provider network"
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="MediCare Plus",
                    so_number="SO-4001",
                    title="Medical Supplies - Q3 Batch",
                    status="fulfilled",
                )
            ],
            invoices=[
                InvoiceSetup(
                    sales_order_number="SO-4001",
                    invoice_number="INV-4045",
                    amount=Decimal("15000.00"),
                    due_date=date(2025, 10, 1),
                    status="open",
                )
            ],
            payments=[
                PaymentSetup(
                    invoice_number="INV-4045",
                    amount=Decimal("5000.00"),
                    method="wire",
                )
            ],
        ),
        expected_query=(
            "When should we expect payment from MediCare for INV-4045?"
        ),
        expected_behavior=(
            "Retrieval surfaces invoice ($15k due Oct 1, $5k paid, $10k outstanding) + payment patterns. "
            "Reply predicts payment 2-3 days after due date based on history, mentions wire transfer preference, "
            "notes PO number requirement for remaining balance."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="MediCare Plus",
                predicate="payment_timing_pattern",
                predicate_type="observation",
                object_value={
                    "pattern": "typically_late",
                    "average_days_late": 2.5,
                    "sample_size": 12
                },
                confidence=0.87,
            ),
            SemanticMemorySetup(
                subject="MediCare Plus",
                predicate="payment_method_preference",
                predicate_type="preference",
                object_value={"method": "wire", "reason": "accounting policy"},
                confidence=0.92,
            ),
            SemanticMemorySetup(
                subject="MediCare Plus",
                predicate="requires_po_number",
                predicate_type="requirement",
                object_value={"required": True, "for_amounts_over": 1000},
                confidence=0.95,
            ),
        ],
    )
)

# Scenario 5: Organizational relationships and policies
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=5,
        title="Corporate hierarchy and policy enforcement",
        description=(
            "Sales team handling subsidiary request that requires understanding of "
            "parent company policies and organizational structure."
        ),
        category="memory_retrieval",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Global Dynamics Corp",
                    industry="Manufacturing",
                    notes="Fortune 500 parent company"
                ),
                CustomerSetup(
                    name="Global Dynamics EU",
                    industry="Manufacturing",
                    notes="European subsidiary of Global Dynamics Corp"
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Global Dynamics EU",
                    so_number="SO-5001",
                    title="Industrial Equipment - Frankfurt Facility",
                    status="draft",
                )
            ],
        ),
        expected_query=(
            "Can we fast-track the order for Global Dynamics EU?"
        ),
        expected_behavior=(
            "Retrieval surfaces SO-5001 (draft) + parent company relationship + policy. "
            "Reply explains that Global Dynamics EU is a subsidiary, all contracts require "
            "legal review by parent company regardless of subsidiary, cannot fast-track without "
            "parent approval."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Global Dynamics EU",
                predicate="parent_company",
                predicate_type="attribute",
                object_value={
                    "parent": "Global Dynamics Corp",
                    "relationship": "wholly_owned_subsidiary"
                },
                confidence=0.98,
            ),
            SemanticMemorySetup(
                subject="Global Dynamics Corp",
                predicate="contract_policy",
                predicate_type="policy",
                object_value={
                    "requirement": "legal_review_required",
                    "applies_to": ["parent", "all_subsidiaries"],
                    "minimum_review_time_days": 5
                },
                confidence=0.95,
            ),
        ],
    )
)

# Scenario 6: Multi-entity task prioritization
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=6,
        title="Multi-customer task and context management",
        description=(
            "Sales rep reviewing daily priorities across multiple customers. "
            "System must surface tasks and relevant context for each customer."
        ),
        category="memory_retrieval",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Zephyr Airlines",
                    industry="Transportation",
                    notes="Budget airline, cost-conscious"
                ),
                CustomerSetup(
                    name="Acme Manufacturing",
                    industry="Manufacturing",
                    notes="High-volume repeat customer"
                )
            ],
            tasks=[
                TaskSetup(
                    customer_name="Zephyr Airlines",
                    title="Follow-up call about Q4 contract renewal",
                    body="Zephyr contract expires Nov 30, discuss renewal terms",
                    status="todo",
                ),
                TaskSetup(
                    customer_name="Acme Manufacturing",
                    title="Expedite shipping for rush order SO-6002",
                    body="Acme needs delivery by Oct 20 for production deadline",
                    status="doing",
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Acme Manufacturing",
                    so_number="SO-6002",
                    title="Steel Components - Rush Order",
                    status="in_fulfillment",
                )
            ],
        ),
        expected_query=(
            "What are my priorities for today?"
        ),
        expected_behavior=(
            "Retrieval surfaces both tasks + customer context. Reply lists: "
            "(1) Expedite Acme shipping (in progress, high priority, customer values speed). "
            "(2) Call Zephyr about renewal (emphasize value/cost savings, customer is price-sensitive). "
            "Shows understanding of different customer priorities."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Zephyr Airlines",
                predicate="price_sensitivity",
                predicate_type="observation",
                object_value={
                    "sensitivity": "high",
                    "pattern": "always_requests_discount",
                    "decision_factor": "primary"
                },
                confidence=0.90,
            ),
            SemanticMemorySetup(
                subject="Acme Manufacturing",
                predicate="values_speed",
                predicate_type="preference",
                object_value={
                    "priority": "delivery_speed",
                    "willing_to_pay_premium": True
                },
                confidence=0.88,
            ),
        ],
    )
)
