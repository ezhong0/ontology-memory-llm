"""Registry of all scenario definitions.

18 scenarios matching ProjectDescription.md exactly.
These demonstrate the memory system aligned with the original requirements.
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
# 18 SCENARIOS FROM ProjectDescription.md
# =============================================================================

# Scenario 1: Overdue invoice follow-up with preference recall
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=1,
        title="Overdue invoice follow-up with preference recall",
        description=(
            "Finance agent wants to nudge customer while honoring delivery preferences. "
            "Retrieval surfaces INV-1009 (open, amount, due date) + memory preference."
        ),
        category="financial",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Kai Media", industry="Entertainment")
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
            "System retrieves INV-1009 (open, $1200, due 2025-09-30) from DB + "
            "'prefers Friday deliveries' from memory. Reply mentions invoice details "
            "and references Friday delivery. Memory update: adds episodic note that "
            "invoice reminder was initiated today."
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

# Scenario 2: Reschedule a work order based on technician availability
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=2,
        title="Reschedule work order based on technician availability",
        description=(
            "Ops manager wants to move a work order. Query WO row, update plan, "
            "store semantic memory about scheduling preference."
        ),
        category="operational",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Kai Media", industry="Entertainment")
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Kai Media",
                    so_number="SO-1001",
                    title="Album Fulfillment",
                    status="in_fulfillment",
                )
            ],
            work_orders=[
                WorkOrderSetup(
                    sales_order_number="SO-1001",
                    description="Pick-pack albums",
                    status="queued",
                    technician="Alex",
                    scheduled_for=date(2025, 9, 22),
                )
            ],
        ),
        expected_query=(
            "Reschedule Kai Media's pick-pack WO to Friday and keep Alex assigned."
        ),
        expected_behavior=(
            "Tool queries WO row, returns SQL suggestion to update scheduled_for to Friday. "
            "Stores semantic memory: 'Kai Media prefers Friday; align WO scheduling accordingly.' "
            "Trace lists WO row used."
        ),
    )
)

# Scenario 3: Ambiguous entity disambiguation
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=3,
        title="Ambiguous entity disambiguation (two similar names)",
        description=(
            "Two customers with similar names. System asks clarification only if "
            "top-k scores are within small margin; otherwise chooses higher confidence."
        ),
        category="entity_resolution",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Kai Media", industry="Entertainment"),
                CustomerSetup(name="Kai Media Europe", industry="Entertainment"),
            ],
            invoices=[
                InvoiceSetup(
                    sales_order_number="SO-1001",
                    invoice_number="INV-1001",
                    amount=Decimal("500.00"),
                    due_date=date(2025, 10, 1),
                    status="open",
                )
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Kai Media",
                    so_number="SO-1001",
                    title="Album Distribution",
                    status="fulfilled",
                )
            ],
        ),
        expected_query="What's Kai's latest invoice?",
        expected_behavior=(
            "System asks single-step clarification only if semantic & deterministic "
            "match scores are within small margin. Otherwise chooses higher-confidence "
            "entity. Memory update: stores user's clarification for future disambiguation."
        ),
    )
)

# Scenario 4: NET terms learning from conversation
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=4,
        title="NET terms learning from conversation",
        description=(
            "Terms aren't in DB; user states them. Create semantic memory entries. "
            "Later infer due date using invoice issued_at + NET15 from memory."
        ),
        category="memory_extraction",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="TC Boiler", industry="Industrial")
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="TC Boiler",
                    so_number="SO-2001",
                    title="On-site repair",
                    status="fulfilled",
                )
            ],
            invoices=[
                InvoiceSetup(
                    sales_order_number="SO-2001",
                    invoice_number="INV-2201",
                    amount=Decimal("3500.00"),
                    due_date=date(2025, 10, 20),
                    status="open",
                )
            ],
        ),
        expected_query=(
            "Remember: TC Boiler is NET15 and prefers ACH over credit card."
        ),
        expected_behavior=(
            "Create semantic memory entries (payment_terms=NET15, payment_method=ACH). "
            "On later: 'When should we expect payment from TC Boiler on INV-2201?' → "
            "system infers due date using invoice issued_at + NET15 from memory."
        ),
    )
)

# Scenario 5: Partial payments and balance calculation
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=5,
        title="Partial payments and balance calculation",
        description=(
            "Invoice has two payments totaling less than invoice amount. "
            "Join payments to compute remaining balance."
        ),
        category="financial",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="TC Boiler", industry="Industrial")
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="TC Boiler",
                    so_number="SO-2002",
                    title="Equipment repair",
                    status="fulfilled",
                )
            ],
            invoices=[
                InvoiceSetup(
                    sales_order_number="SO-2002",
                    invoice_number="INV-2201",
                    amount=Decimal("5000.00"),
                    due_date=date(2025, 10, 15),
                    status="open",
                )
            ],
            payments=[
                PaymentSetup(
                    invoice_number="INV-2201",
                    amount=Decimal("2000.00"),
                    method="ACH",
                ),
                PaymentSetup(
                    invoice_number="INV-2201",
                    amount=Decimal("1500.00"),
                    method="ACH",
                ),
            ],
        ),
        expected_query="How much does TC Boiler still owe on INV-2201?",
        expected_behavior=(
            "Join payments to compute: $5000 - ($2000 + $1500) = $1500 remaining. "
            "Store episodic memory that user asked about balances for this customer "
            "(improves future weighting for finance intents)."
        ),
    )
)

# Scenario 6: SLA breach detection from tasks + orders
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=6,
        title="SLA breach detection from tasks + orders",
        description=(
            "Support tasks reference an SLA window. Retrieve open task age + SO status; "
            "reply flags risk and suggests next steps."
        ),
        category="sla_monitoring",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Kai Media", industry="Entertainment")
            ],
            tasks=[
                TaskSetup(
                    customer_name="Kai Media",
                    title="Investigate shipping SLA for Kai Media",
                    body="Task created 10 days ago, status=todo",
                    status="todo",
                )
            ],
        ),
        expected_query="Are we at risk of an SLA breach for Kai Media?",
        expected_behavior=(
            "Retrieve open task age (10 days) + SO status. Reply flags SLA risk and "
            "suggests next steps. Memory logs risk tag to increase importance for related recalls."
        ),
    )
)

# Scenario 7: Conflicting memories → consolidation rules
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=7,
        title="Conflicting memories → consolidation rules",
        description=(
            "Two sessions recorded delivery preference as Thursday vs Friday. "
            "Consolidation picks most recent or most reinforced value."
        ),
        category="conflict_resolution",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Kai Media", industry="Entertainment")
            ],
        ),
        expected_query="What day should we deliver to Kai Media?",
        expected_behavior=(
            "Consolidation picks the most recent or most reinforced value. Reply cites "
            "confidence and offers to confirm. If confirmed, demote conflicting memory "
            "via decay and add corrective semantic memory."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Kai Media",
                predicate="prefers_delivery_day",
                predicate_type="preference",
                object_value={"day": "Thursday", "session": "older"},
                confidence=0.70,
            ),
            SemanticMemorySetup(
                subject="Kai Media",
                predicate="prefers_delivery_day",
                predicate_type="preference",
                object_value={"day": "Friday", "session": "recent"},
                confidence=0.85,
            ),
        ],
    )
)

# Scenario 8: Multilingual/alias handling
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=8,
        title="Multilingual/alias handling",
        description=(
            "User mixes languages. NER detects entity; memory stored in English canonical "
            "form with original text preserved. Add alias mapping for multilingual mentions."
        ),
        category="entity_resolution",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Kai Media", industry="Entertainment")
            ],
        ),
        expected_query=(
            "Recuérdame que Kai Media prefiere entregas los viernes."
        ),
        expected_behavior=(
            "NER detects 'Kai Media'; memory stored in English canonical form "
            "('prefers Friday deliveries') with original Spanish text preserved. "
            "Future English queries retrieve it. Add alias mapping."
        ),
    )
)

# Scenario 9: Cold-start grounding to DB facts
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=9,
        title="Cold-start grounding to DB facts",
        description=(
            "No prior memories. System returns purely DB-grounded answer from "
            "sales_orders/work_orders, creates episodic memory."
        ),
        category="db_grounding",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="TC Boiler", industry="Industrial")
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="TC Boiler",
                    so_number="SO-2002",
                    title="On-site repair",
                    status="in_fulfillment",
                )
            ],
            work_orders=[
                WorkOrderSetup(
                    sales_order_number="SO-2002",
                    description="Replace valve",
                    status="in_progress",
                    technician="Alex",
                )
            ],
        ),
        expected_query="What's the status of TC Boiler's order?",
        expected_behavior=(
            "System returns purely DB-grounded answer: SO-2002 is in_fulfillment, "
            "WO in_progress (Alex replacing valve). Creates episodic memory summarizing "
            "the question and returned facts."
        ),
    )
)

# Scenario 10: Active recall to validate stale facts
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=10,
        title="Active recall to validate stale facts",
        description=(
            "Preference older than 90 days with low reinforcement. Before finalizing, "
            "system asks: 'We have Friday preference on record from 2025-05-10; still accurate?'"
        ),
        category="confidence_management",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Kai Media", industry="Entertainment")
            ],
        ),
        expected_query="Schedule a delivery for Kai Media next week.",
        expected_behavior=(
            "Before finalizing, system asks: 'We have Friday preference on record from "
            "2025-05-10; still accurate?' If confirmed, resets decay; if changed, "
            "updates semantic memory and writes summary."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Kai Media",
                predicate="prefers_delivery_day",
                predicate_type="preference",
                object_value={"day": "Friday", "last_validated": "2025-05-10"},
                confidence=0.60,  # Decayed
            )
        ],
    )
)

# Scenario 11: Cross-object reasoning (SO → WO → Invoice chain)
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=11,
        title="Cross-object reasoning (SO → WO → Invoice chain)",
        description=(
            "Use chain: if work_orders.status=done for SO and no invoices exist, "
            "recommend generating invoice. Memory stores policy preference."
        ),
        category="operational",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="TC Boiler", industry="Industrial")
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="TC Boiler",
                    so_number="SO-2002",
                    title="On-site repair",
                    status="fulfilled",
                )
            ],
            work_orders=[
                WorkOrderSetup(
                    sales_order_number="SO-2002",
                    description="Replace valve",
                    status="done",
                    technician="Alex",
                )
            ],
        ),
        expected_query="Can we invoice as soon as the repair is done?",
        expected_behavior=(
            "Use chain: WO status=done for SO-2002, no invoices exist → recommend "
            "generating invoice. If invoice exists and is open, suggest sending it. "
            "Memory stores policy: 'Invoice immediately upon WO=done'."
        ),
    )
)

# Scenario 12: Conversation-driven entity linking with fuzzy match
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=12,
        title="Conversation-driven entity linking with fuzzy match",
        description=(
            "User types 'Kay Media'. Fuzzy match exceeds threshold to 'Kai Media'; "
            "system confirms once, then stores alias to avoid repeated confirmations."
        ),
        category="entity_resolution",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Kai Media", industry="Entertainment")
            ],
        ),
        expected_query="Open a WO for Kay Media for packaging.",
        expected_behavior=(
            "Fuzzy match exceeds threshold to 'Kai Media'. System confirms once: "
            "'Did you mean Kai Media?' Then stores alias 'Kay Media' → 'Kai Media' "
            "in entity_aliases to avoid repeated confirmations."
        ),
    )
)

# Scenario 13: Policy & PII guardrail memory
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=13,
        title="Policy & PII guardrail memory",
        description=(
            "User provides PII. Redact before storage per PII policy (store masked token + purpose). "
            "Later use masked contact, not raw PII."
        ),
        category="pii_safety",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Demo User", industry="Internal")
            ],
        ),
        expected_query="Remember my personal cell: 415-555-0199 for urgent alerts.",
        expected_behavior=(
            "Redact before storage per PII policy: store masked token '[PHONE_REDACTED]' + "
            "purpose 'urgent_alerts'. On later: 'Alert me about any overdue invoice today' → "
            "system uses masked contact, not raw PII."
        ),
    )
)

# Scenario 14: Session window consolidation example
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=14,
        title="Session window consolidation example",
        description=(
            "Three sessions discuss TC Boiler terms, rush WO, payment plan. "
            "/consolidate generates single summary."
        ),
        category="consolidation",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="TC Boiler", industry="Industrial")
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="TC Boiler",
                    so_number="SO-2002",
                    title="Rush repair",
                    status="fulfilled",
                )
            ],
        ),
        expected_query=(
            "What are TC Boiler's agreed terms and current commitments?"
        ),
        expected_behavior=(
            "/consolidate generates single summary capturing: NET15 terms, rush WO "
            "linked to SO-2002, payment plan. Subsequent retrieval uses this summary."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="TC Boiler",
                predicate="payment_terms",
                predicate_type="requirement",
                object_value={"terms": "NET15"},
                confidence=0.90,
            ),
        ],
    )
)

# Scenario 15: Audit trail / explainability
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=15,
        title="Audit trail / explainability",
        description=(
            "/explain returns memory IDs, similarity scores, specific chat event that "
            "created the memory, plus any reinforcing confirmations."
        ),
        category="explainability",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Kai Media", industry="Entertainment")
            ],
        ),
        expected_query="Why did you say Kai Media prefers Fridays?",
        expected_behavior=(
            "/explain returns: memory ID 42, similarity score 0.92, chat_event_id 108 "
            "(created 2025-08-15), reinforced 3 times (event IDs 115, 127, 134)."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="Kai Media",
                predicate="prefers_delivery_day",
                predicate_type="preference",
                object_value={"day": "Friday"},
                confidence=0.92,
            )
        ],
    )
)

# Scenario 16: Reminder creation from conversational intent
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=16,
        title="Reminder creation from conversational intent",
        description=(
            "Store semantic policy memory. On future /chat calls involving invoices, "
            "system checks due dates and surfaces proactive notices."
        ),
        category="procedural_memory",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Demo User", industry="Internal")
            ],
        ),
        expected_query=(
            "If an invoice is still open 3 days before due, remind me."
        ),
        expected_behavior=(
            "Store semantic policy memory: 'reminder_rule: open_invoice_3_days_before_due'. "
            "On future /chat calls involving invoices, system checks due dates and "
            "surfaces proactive notices."
        ),
    )
)

# Scenario 17: Error handling when DB and memory disagree
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=17,
        title="Error handling when DB and memory disagree",
        description=(
            "Memory says 'SO-1001 is fulfilled' but DB shows 'in_fulfillment'. "
            "Prefer authoritative DB; mark outdated memory for decay."
        ),
        category="conflict_resolution",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Kai Media", industry="Entertainment")
            ],
            sales_orders=[
                SalesOrderSetup(
                    customer_name="Kai Media",
                    so_number="SO-1001",
                    title="Album Fulfillment",
                    status="in_fulfillment",  # DB truth
                )
            ],
        ),
        expected_query="Is SO-1001 complete?",
        expected_behavior=(
            "Memory says 'SO-1001 is fulfilled' but DB shows 'in_fulfillment'. "
            "Prefer authoritative DB; respond with DB truth and mark outdated memory "
            "for decay and corrective summary."
        ),
        semantic_memories=[
            SemanticMemorySetup(
                subject="SO-1001",
                predicate="status",
                predicate_type="observation",
                object_value={"status": "fulfilled"},  # Outdated memory
                confidence=0.80,
            )
        ],
    )
)

# Scenario 18: Task completion via conversation
ScenarioRegistry.register(
    ScenarioDefinition(
        scenario_id=18,
        title="Task completion via conversation",
        description=(
            "Return SQL patch suggestion (or mocked effect), store summary as semantic memory."
        ),
        category="task_management",
        domain_setup=DomainDataSetup(
            customers=[
                CustomerSetup(name="Kai Media", industry="Entertainment")
            ],
            tasks=[
                TaskSetup(
                    customer_name="Kai Media",
                    title="SLA investigation task for Kai Media",
                    body="Investigate shipping SLA compliance",
                    status="doing",
                )
            ],
        ),
        expected_query=(
            "Mark the SLA investigation task for Kai Media as done and summarize what we learned."
        ),
        expected_behavior=(
            "Return SQL patch suggestion: UPDATE tasks SET status='done' WHERE title LIKE '%SLA investigation%'. "
            "Store summary as semantic memory: 'SLA investigation completed; compliance verified'."
        ),
    )
)
