"""Registry of all scenario definitions.

Each scenario defines a complete test case for the memory system.
Scenarios are numbered 1-18 matching ProjectDescription.md.

For Phase 1, we start with Scenario 1 only.
"""
from datetime import date
from decimal import Decimal

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

    _scenarios: dict[int, ScenarioDefinition] = {}

    @classmethod
    def register(cls, scenario: ScenarioDefinition) -> None:
        """Register a scenario."""
        cls._scenarios[scenario.scenario_id] = scenario

    @classmethod
    def get(cls, scenario_id: int) -> ScenarioDefinition | None:
        """Get scenario by ID."""
        return cls._scenarios.get(scenario_id)

    @classmethod
    def get_all(cls) -> list[ScenarioDefinition]:
        """Get all scenarios."""
        return sorted(cls._scenarios.values(), key=lambda s: s.scenario_id)

    @classmethod
    def get_by_category(cls, category: str) -> list[ScenarioDefinition]:
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

# Scenario 7: Payment terms negotiation and update
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=7,
        title="Payment terms change request handling",
        description=(
            "Customer requests extended payment terms mid-contract. "
            "System must track the change and update memory while maintaining history."
        ),
        category="memory_update",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Vertex Solutions",
                    industry="Technology",
                    notes="SaaS company, seasonal cash flow"
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Vertex Solutions",
                    so_number="SO-7001",
                    title="Enterprise Software Licenses",
                    status="fulfilled",
                )
            ],
            invoices=[
                InvoiceSetup(
                    sales_order_number="SO-7001",
                    invoice_number="INV-7023",
                    amount=Decimal("25000.00"),
                    due_date=date(2025, 11, 15),
                    status="open",
                )
            ],
        ),
        expected_query=(
            "Vertex Solutions wants to change from NET30 to NET60 for future invoices"
        ),
        expected_behavior=(
            "Retrieval surfaces existing NET30 terms memory. Reply acknowledges change request, "
            "notes current INV-7023 still follows NET30, but future invoices will use NET60. "
            "Memory update: supersede old payment_terms memory with new one, noting change date."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Vertex Solutions",
                predicate="payment_terms",
                predicate_type="requirement",
                object_value={"terms": "NET30", "established": "2025-01-15"},
                confidence=0.93,
            ),
        ],
    )
)

# Scenario 8: Invoice inquiry with historical context
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=8,
        title="Invoice status check with payment history",
        description=(
            "Customer inquires about invoice status. System provides DB facts enriched "
            "with payment behavior patterns and relationship context."
        ),
        category="context_enrichment",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Pinnacle Retail Group",
                    industry="Retail",
                    notes="Multi-location retail chain"
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Pinnacle Retail Group",
                    so_number="SO-8001",
                    title="POS System Upgrade",
                    status="fulfilled",
                )
            ],
            invoices=[
                InvoiceSetup(
                    sales_order_number="SO-8001",
                    invoice_number="INV-8067",
                    amount=Decimal("42000.00"),
                    due_date=date(2025, 10, 25),
                    status="open",
                )
            ],
        ),
        expected_query=(
            "What's the status of the Pinnacle invoice?"
        ),
        expected_behavior=(
            "Retrieval surfaces INV-8067 ($42k, due Oct 25) + payment pattern memory. "
            "Reply provides invoice details and notes customer has excellent payment history, "
            "typically pays 1-2 days early, prefers ACH. No concern about this invoice."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Pinnacle Retail Group",
                predicate="payment_reliability",
                predicate_type="observation",
                object_value={
                    "rating": "excellent",
                    "average_days_early": 1.5,
                    "missed_payments": 0,
                    "history_months": 18
                },
                confidence=0.96,
            ),
            SemanticMemorySetup(
                subject="Pinnacle Retail Group",
                predicate="payment_method_preference",
                predicate_type="preference",
                object_value={"method": "ACH", "routing_on_file": True},
                confidence=0.92,
            ),
        ],
    )
)

# Scenario 9: Work order scheduling with customer preferences
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=9,
        title="Installation scheduling respecting operational constraints",
        description=(
            "Ops team scheduling work order. System must incorporate customer's "
            "operational hours, blackout dates, and site access requirements."
        ),
        category="scheduling",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="FreshMarket Grocery",
                    industry="Retail",
                    notes="24-hour grocery chain"
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="FreshMarket Grocery",
                    so_number="SO-9001",
                    title="Refrigeration System Installation",
                    status="in_fulfillment",
                )
            ],
            work_orders=[
                WorkOrderSetup(
                    sales_order_number="SO-9001",
                    description="Install commercial refrigeration units",
                    status="scheduled",
                    technician="Mike Chen",
                    scheduled_for=date(2025, 10, 22),
                )
            ],
        ),
        expected_query=(
            "When can we install the refrigeration system at FreshMarket?"
        ),
        expected_behavior=(
            "Retrieval surfaces WO + operational constraints memory. Reply recommends "
            "overnight installation (2am-6am preferred window), must avoid Nov 20-25 "
            "(Thanksgiving prep), requires facility manager sign-off before work."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="FreshMarket Grocery",
                predicate="operational_hours",
                predicate_type="constraint",
                object_value={
                    "store_hours": "24/7",
                    "preferred_work_window": "2am-6am",
                    "reason": "minimal_customer_disruption"
                },
                confidence=0.91,
            ),
            SemanticMemorySetup(
                subject="FreshMarket Grocery",
                predicate="blackout_dates",
                predicate_type="constraint",
                object_value={
                    "dates": ["2025-11-20 to 2025-11-25"],
                    "reason": "Thanksgiving high-volume period"
                },
                confidence=0.89,
            ),
            SemanticMemorySetup(
                subject="FreshMarket Grocery",
                predicate="site_access_requirements",
                predicate_type="requirement",
                object_value={
                    "requires": "facility_manager_approval",
                    "contact": "Jorge Martinez",
                    "lead_time_days": 3
                },
                confidence=0.87,
            ),
        ],
    )
)

# Scenario 10: Timezone-aware communication scheduling
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=10,
        title="Multi-timezone customer outreach coordination",
        description=(
            "Sales team planning calls across multiple timezones. System must prevent "
            "calls at inappropriate times using timezone awareness."
        ),
        category="temporal_awareness",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Pacific Tech Partners",
                    industry="Technology",
                    notes="West Coast startup"
                ),
                CustomerSetup(
                    name="Atlantic Ventures",
                    industry="Finance",
                    notes="East Coast investment firm"
                )
            ],
        ),
        expected_query=(
            "Schedule calls for Pacific Tech (PST) and Atlantic Ventures (EST) at 3pm my time (CST)"
        ),
        expected_behavior=(
            "Retrieval surfaces timezone memories. Reply warns: "
            "3pm CST = 1pm PST (acceptable) but calls to Atlantic Ventures should avoid after 5pm EST "
            "(would be 4pm CST). Suggests 2pm CST for Atlantic Ventures call."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Pacific Tech Partners",
                predicate="timezone",
                predicate_type="attribute",
                object_value={
                    "timezone": "America/Los_Angeles",
                    "label": "PST/PDT"
                },
                confidence=0.94,
            ),
            SemanticMemorySetup(
                subject="Atlantic Ventures",
                predicate="timezone",
                predicate_type="attribute",
                object_value={
                    "timezone": "America/New_York",
                    "label": "EST/EDT"
                },
                confidence=0.96,
            ),
            SemanticMemorySetup(
                subject="Atlantic Ventures",
                predicate="business_hours_preference",
                predicate_type="preference",
                object_value={
                    "preferred_call_times": "9am-5pm ET",
                    "no_calls_after": "5pm ET"
                },
                confidence=0.88,
            ),
        ],
    )
)

# Scenario 11: Multi-entity relationship tracking
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=11,
        title="Corporate family and decision-making hierarchy",
        description=(
            "Deal involving multiple related entities. System must track corporate "
            "relationships and decision authority across the family of companies."
        ),
        category="relationship_mapping",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Titan Industries Inc",
                    industry="Manufacturing",
                    notes="Parent holding company"
                ),
                CustomerSetup(
                    name="Titan Automotive Division",
                    industry="Automotive",
                    notes="Subsidiary of Titan Industries"
                ),
                CustomerSetup(
                    name="Titan Aerospace Unit",
                    industry="Aerospace",
                    notes="Subsidiary of Titan Industries"
                )
            ],
        ),
        expected_query=(
            "Who needs to approve a deal with Titan Automotive?"
        ),
        expected_behavior=(
            "Retrieval surfaces organizational hierarchy memory. Reply explains "
            "Titan Automotive is a division requiring parent company approval for contracts >$50k. "
            "Decision authority rests with Titan Industries CFO. Contact subsidiary for <$50k deals."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Titan Automotive Division",
                predicate="parent_company",
                predicate_type="attribute",
                object_value={
                    "parent": "Titan Industries Inc",
                    "relationship": "wholly_owned_subsidiary"
                },
                confidence=0.97,
            ),
            SemanticMemorySetup(
                subject="Titan Industries Inc",
                predicate="approval_authority",
                predicate_type="policy",
                object_value={
                    "contracts_over": 50000,
                    "requires_approval_from": "CFO",
                    "applies_to_subsidiaries": True
                },
                confidence=0.93,
            ),
            SemanticMemorySetup(
                subject="Titan Automotive Division",
                predicate="local_authority_limit",
                predicate_type="policy",
                object_value={
                    "can_approve_up_to": 50000,
                    "contact": "Division VP of Operations"
                },
                confidence=0.90,
            ),
        ],
    )
)

# Scenario 12: Memory confidence decay demonstration
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=12,
        title="Stale information recognition and validation prompt",
        description=(
            "System detects old memory (90+ days) and proactively suggests validation. "
            "Demonstrates epistemic humility and confidence decay."
        ),
        category="confidence_management",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Legacy Systems Corp",
                    industry="Technology",
                    notes="Long-term customer, infrequent orders"
                )
            ],
        ),
        expected_query=(
            "What's the preferred contact method for Legacy Systems?"
        ),
        expected_behavior=(
            "Retrieval surfaces old contact preference (120 days old, confidence decayed to ~0.40). "
            "Reply provides the information but explicitly notes: 'Last validated 4 months ago, "
            "confidence is low. Recommend confirming with customer before using.'"
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Legacy Systems Corp",
                predicate="prefers_contact_method",
                predicate_type="preference",
                object_value={"method": "email", "address": "contracts@legacysys.com"},
                confidence=0.85,  # Will decay based on created_at being 120 days ago
            ),
        ],
    )
)

# Scenario 13: Memory reinforcement through repetition
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=13,
        title="Confidence boost from repeated confirmation",
        description=(
            "Customer confirms same preference multiple times in different contexts. "
            "System increases confidence with each confirmation (reinforcement learning)."
        ),
        category="confidence_management",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Precision Tools Ltd",
                    industry="Manufacturing",
                    notes="Quality-focused machine shop"
                )
            ],
        ),
        expected_query=(
            "Precision Tools confirmed again they only accept deliveries on Tuesday mornings"
        ),
        expected_behavior=(
            "Retrieval surfaces existing Tuesday delivery preference (confidence 0.75). "
            "Reply acknowledges this is the 3rd confirmation, reinforcing memory. "
            "Memory update: increase confidence to 0.92, add reinforcement metadata."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Precision Tools Ltd",
                predicate="delivery_schedule",
                predicate_type="preference",
                object_value={
                    "day": "Tuesday",
                    "time": "morning",
                    "reason": "receiving_dock_availability"
                },
                confidence=0.75,
            ),
        ],
    )
)

# Scenario 14: Contradictory information conflict resolution
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=14,
        title="Detecting and resolving contradictory preferences",
        description=(
            "New information contradicts existing memory. System must detect conflict, "
            "flag for resolution, and update with proper supersession tracking."
        ),
        category="conflict_resolution",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Evolve Fitness Centers",
                    industry="Healthcare",
                    notes="Growing gym chain, 15 locations"
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Evolve Fitness Centers",
                    so_number="SO-14001",
                    title="Gym Equipment Package",
                    status="draft",
                )
            ],
        ),
        expected_query=(
            "Evolve Fitness says they now prefer phone calls, not email"
        ),
        expected_behavior=(
            "Retrieval surfaces existing email preference (confidence 0.88). "
            "Reply detects conflict, notes preference change from email to phone. "
            "Memory update: mark old memory as superseded, create new phone preference, "
            "log conflict with resolution = 'updated_per_customer_request'."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Evolve Fitness Centers",
                predicate="prefers_contact_method",
                predicate_type="preference",
                object_value={"method": "email", "address": "ops@evolvefit.com"},
                confidence=0.88,
            ),
        ],
    )
)

# Scenario 15: Cross-reference resolution across entities
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=15,
        title="Multi-hop entity resolution and data linking",
        description=(
            "Query references nested entities (customer → SO → invoice → payment). "
            "System must resolve the full chain and provide comprehensive context."
        ),
        category="entity_resolution",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Quantum Dynamics",
                    industry="Technology",
                    notes="Research & Development firm"
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Quantum Dynamics",
                    so_number="SO-15001",
                    title="Specialized Lab Equipment",
                    status="fulfilled",
                )
            ],
            invoices=[
                InvoiceSetup(
                    sales_order_number="SO-15001",
                    invoice_number="INV-15089",
                    amount=Decimal("67000.00"),
                    due_date=date(2025, 10, 30),
                    status="paid",
                )
            ],
            payments=[
                PaymentSetup(
                    invoice_number="INV-15089",
                    amount=Decimal("67000.00"),
                    method="wire",
                )
            ],
        ),
        expected_query=(
            "Show me the payment for the Quantum Dynamics lab equipment order"
        ),
        expected_behavior=(
            "Retrieval resolves: Quantum Dynamics → SO-15001 → INV-15089 → Payment. "
            "Reply provides full chain: 'Lab Equipment order (SO-15001) was invoiced "
            "as INV-15089 for $67k, paid in full via wire transfer on [date].' "
            "Demonstrates cross-entity linking and comprehensive context."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Quantum Dynamics",
                predicate="payment_method_preference",
                predicate_type="preference",
                object_value={"method": "wire", "reason": "university_accounting_policy"},
                confidence=0.91,
            ),
        ],
    )
)

# Scenario 16: Bulk query with context enrichment
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=16,
        title="Portfolio analysis with memory-enhanced insights",
        description=(
            "User requests bulk data (all invoices, all customers, etc). System enriches "
            "results with relevant memories for each entity, providing smart summaries."
        ),
        category="bulk_operations",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Beta Solutions",
                    industry="Technology",
                    notes="Mid-market SaaS provider"
                ),
                CustomerSetup(
                    name="Gamma Industries",
                    industry="Manufacturing",
                    notes="Industrial equipment manufacturer"
                ),
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Beta Solutions",
                    so_number="SO-16001",
                    title="Cloud Services Q4",
                    status="fulfilled",
                ),
                SalesOrderSetup(
                    customer_name="Gamma Industries",
                    so_number="SO-16002",
                    title="Machine Parts Batch 45",
                    status="fulfilled",
                )
            ],
            invoices=[
                InvoiceSetup(
                    sales_order_number="SO-16001",
                    invoice_number="INV-16101",
                    amount=Decimal("12000.00"),
                    due_date=date(2025, 9, 15),
                    status="open",
                ),
                InvoiceSetup(
                    sales_order_number="SO-16002",
                    invoice_number="INV-16102",
                    amount=Decimal("8500.00"),
                    due_date=date(2025, 9, 20),
                    status="open",
                )
            ],
        ),
        expected_query=(
            "Show me all open invoices and their collection risk"
        ),
        expected_behavior=(
            "Retrieval surfaces 2 open invoices + payment behavior memories. "
            "Reply enriches with context: INV-16101 (Beta: reliable payer, low risk) and "
            "INV-16102 (Gamma: slow payer, medium risk). Provides prioritized collection plan."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Beta Solutions",
                predicate="payment_reliability",
                predicate_type="observation",
                object_value={
                    "rating": "good",
                    "average_days_late": 0.5,
                    "risk_level": "low"
                },
                confidence=0.89,
            ),
            SemanticMemorySetup(
                subject="Gamma Industries",
                predicate="payment_reliability",
                predicate_type="observation",
                object_value={
                    "rating": "fair",
                    "average_days_late": 7.2,
                    "risk_level": "medium",
                    "note": "always pays eventually"
                },
                confidence=0.86,
            ),
        ],
    )
)

# Scenario 17: Historical pattern extraction
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=17,
        title="Behavioral pattern recognition for predictions",
        description=(
            "System has observed repeated behavior pattern (e.g., always late by X days). "
            "Demonstrates pattern recognition and predictive capabilities."
        ),
        category="pattern_recognition",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Cyclical Manufacturing Co",
                    industry="Manufacturing",
                    notes="Seasonal business, cash flow varies"
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Cyclical Manufacturing Co",
                    so_number="SO-17001",
                    title="Raw Materials Q4 Order",
                    status="fulfilled",
                )
            ],
            invoices=[
                InvoiceSetup(
                    sales_order_number="SO-17001",
                    invoice_number="INV-17234",
                    amount=Decimal("18000.00"),
                    due_date=date(2025, 10, 10),
                    status="open",
                )
            ],
        ),
        expected_query=(
            "When will Cyclical Manufacturing actually pay INV-17234?"
        ),
        expected_behavior=(
            "Retrieval surfaces invoice ($18k, due Oct 10) + payment pattern observation. "
            "Reply predicts: 'Based on 8 previous invoices, Cyclical Manufacturing typically "
            "pays 5-7 days late during Q4 (low season). Expect payment around Oct 15-17.'"
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Cyclical Manufacturing Co",
                predicate="seasonal_payment_pattern",
                predicate_type="observation",
                object_value={
                    "q4_average_days_late": 6.2,
                    "q2_average_days_late": 1.1,
                    "pattern": "cash_constrained_in_low_season",
                    "sample_size": 8
                },
                confidence=0.84,
            ),
        ],
    )
)

# Scenario 18: Complex multi-dimensional query
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=18,
        title="Advanced query combining multiple memories and DB facts",
        description=(
            "Complex business question requiring synthesis of domain facts, multiple memories, "
            "and reasoning across entities. Demonstrates system's full intelligence."
        ),
        category="complex_reasoning",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(
                    name="Apex Tech Solutions",
                    industry="Technology",
                    notes="Fast-growing startup"
                ),
                CustomerSetup(
                    name="Summit Manufacturing",
                    industry="Manufacturing",
                    notes="Established manufacturer"
                ),
                CustomerSetup(
                    name="Zenith Logistics",
                    industry="Transportation",
                    notes="Logistics provider"
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Apex Tech Solutions",
                    so_number="SO-18001",
                    title="Server Infrastructure",
                    status="fulfilled",
                ),
                SalesOrderSetup(
                    customer_name="Summit Manufacturing",
                    so_number="SO-18002",
                    title="Industrial Equipment",
                    status="in_fulfillment",
                ),
            ],
            invoices=[
                InvoiceSetup(
                    sales_order_number="SO-18001",
                    invoice_number="INV-18301",
                    amount=Decimal("45000.00"),
                    due_date=date(2025, 9, 30),
                    status="open",
                ),
                InvoiceSetup(
                    sales_order_number="SO-18002",
                    invoice_number="INV-18302",
                    amount=Decimal("32000.00"),
                    due_date=date(2025, 10, 5),
                    status="open",
                )
            ],
        ),
        expected_query=(
            "Which tech industry customers have overdue invoices and prefer Slack for communication?"
        ),
        expected_behavior=(
            "Retrieval combines: (1) industry filter (tech), (2) invoice status (overdue), "
            "(3) contact preference (Slack). Reply identifies Apex Tech (tech industry, "
            "INV-18301 past due Sept 30, prefers Slack @apex-finance). Demonstrates "
            "multi-dimensional filtering across DB and memories."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Apex Tech Solutions",
                predicate="prefers_contact_method",
                predicate_type="preference",
                object_value={"method": "Slack", "handle": "@apex-finance"},
                confidence=0.91,
            ),
            SemanticMemorySetup(
                subject="Summit Manufacturing",
                predicate="prefers_contact_method",
                predicate_type="preference",
                object_value={"method": "email", "address": "ar@summit.com"},
                confidence=0.88,
            ),
            SemanticMemorySetup(
                subject="Zenith Logistics",
                predicate="prefers_contact_method",
                predicate_type="preference",
                object_value={"method": "phone", "number": "555-0199"},
                confidence=0.85,
            ),
        ],
    )
)
