"""Scenario data structures for demo system.

Scenarios define test cases that demonstrate the memory system's capabilities.
Each scenario includes:
- Domain data setup (customers, orders, invoices, etc.)
- Initial memories (if any)
- Expected user query
- Expected system behavior
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID


# =============================================================================
# Domain Data Setup Structures
# =============================================================================

@dataclass(frozen=True)
class CustomerSetup:
    """Definition of a customer to create in domain schema."""
    name: str
    industry: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class SalesOrderSetup:
    """Definition of a sales order to create in domain schema."""
    customer_name: str  # Reference to customer by name
    so_number: str
    title: str
    status: str = "draft"  # draft, approved, in_fulfillment, fulfilled, cancelled


@dataclass(frozen=True)
class InvoiceSetup:
    """Definition of an invoice to create in domain schema."""
    sales_order_number: str  # Reference to SO by number
    invoice_number: str
    amount: Decimal
    due_date: date
    status: str = "open"  # open, paid, void


@dataclass(frozen=True)
class WorkOrderSetup:
    """Definition of a work order to create in domain schema."""
    sales_order_number: str  # Reference to SO by number
    description: str
    status: str = "queued"  # queued, in_progress, blocked, done
    technician: Optional[str] = None
    scheduled_for: Optional[date] = None


@dataclass(frozen=True)
class PaymentSetup:
    """Definition of a payment to create in domain schema."""
    invoice_number: str  # Reference to invoice by number
    amount: Decimal
    method: Optional[str] = None  # ACH, credit_card, check, wire


@dataclass(frozen=True)
class TaskSetup:
    """Definition of a task to create in domain schema."""
    title: str
    customer_name: Optional[str] = None  # Reference to customer by name
    body: Optional[str] = None
    status: str = "todo"  # todo, doing, done


@dataclass(frozen=True)
class DomainDataSetup:
    """All domain data for a scenario."""
    customers: List[CustomerSetup] = field(default_factory=list)
    sales_orders: List[SalesOrderSetup] = field(default_factory=list)
    invoices: List[InvoiceSetup] = field(default_factory=list)
    work_orders: List[WorkOrderSetup] = field(default_factory=list)
    payments: List[PaymentSetup] = field(default_factory=list)
    tasks: List[TaskSetup] = field(default_factory=list)


# =============================================================================
# Memory Setup Structures
# =============================================================================

@dataclass(frozen=True)
class SemanticMemorySetup:
    """Definition of a semantic memory to create."""
    subject: str  # Entity name (will be resolved to entity_id)
    predicate: str
    predicate_type: str  # preference, requirement, observation, policy, attribute
    object_value: Dict[str, Any]
    confidence: float = 0.8


@dataclass(frozen=True)
class EpisodicMemorySetup:
    """Definition of an episodic memory to create."""
    summary: str
    event_type: str  # question, statement, command, correction, confirmation
    entities: List[str]  # Entity names (will be resolved to entity_ids)
    importance: float = 0.5


# =============================================================================
# Scenario Definition
# =============================================================================

@dataclass(frozen=True)
class ScenarioDefinition:
    """Complete definition of a test scenario."""
    scenario_id: int
    title: str
    description: str
    category: str  # entity_resolution, memory_extraction, conflict_detection, etc.

    # Data setup
    domain_setup: DomainDataSetup

    # Expected behavior
    expected_query: str
    expected_behavior: str

    # Optional memories
    semantic_memories: List[SemanticMemorySetup] = field(default_factory=list)
    episodic_memories: List[EpisodicMemorySetup] = field(default_factory=list)


# =============================================================================
# API Response Models
# =============================================================================

@dataclass(frozen=True)
class ScenarioLoadResult:
    """Result of loading a scenario."""
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


@dataclass(frozen=True)
class ScenarioSummary:
    """Summary information about a scenario."""
    scenario_id: int
    title: str
    description: str
    category: str
    expected_query: str
