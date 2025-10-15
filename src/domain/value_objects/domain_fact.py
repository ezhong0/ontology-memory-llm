"""Domain fact value object.

Represents a fact retrieved from the domain database with full provenance.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class DomainFact:
    """Immutable domain fact with full provenance.

    Philosophy: Every fact must be traceable to its source (VISION.md: "Explain Everything").

    Examples:
        Invoice status:
            DomainFact(
                fact_type="invoice_status",
                entity_id="customer:uuid",
                content="Invoice INV-1009: $1,200 due 2025-09-30 (status: open)",
                metadata={"invoice_number": "INV-1009", "amount": 1200.0, ...},
                source_table="domain.invoices",
                source_rows=["uuid-xxx"],
                retrieved_at=datetime.now(timezone.utc),
            )

        Order chain reasoning:
            DomainFact(
                fact_type="order_chain",
                entity_id="SO-1001",
                content="SO-1001: All work complete, ready to invoice",
                metadata={"total_wo": 2, "done_wo": 2, "recommended_action": "generate_invoice"},
                source_table="domain.sales_orders,work_orders,invoices",
                source_rows=["SO-1001"],
                retrieved_at=datetime.now(timezone.utc),
            )
    """

    fact_type: str
    """Type of fact: invoice_status, order_chain, sla_risk, payment_balance, etc."""

    entity_id: str
    """Canonical entity ID this fact is about (e.g., 'customer:uuid', 'SO-1001')"""

    content: str
    """Human-readable fact content for LLM prompts and user display"""

    metadata: dict[str, Any]
    """Structured data (amounts, dates, IDs, recommended actions)"""

    source_table: str
    """Source table(s) in domain schema (e.g., 'domain.invoices', 'domain.sales_orders,work_orders')"""

    source_rows: list[str]
    """UUIDs or identifiers of specific rows used (for traceability)"""

    retrieved_at: datetime
    """When this fact was retrieved (for cache invalidation)"""

    def to_prompt_fragment(self) -> str:
        """Convert to prompt injection format.

        Format:
            DB Fact [fact_type]:
            - <content>
            - Source: <source_table>[<source_rows>]

        Example:
            DB Fact [invoice_status]:
            - Invoice INV-1009 for Kai Media: $1,200 due 2025-09-30 (status: open)
            - Source: domain.invoices[uuid-xxx]

        Returns:
            Formatted string for LLM prompt
        """
        # Truncate source_rows if too many
        source_ids = (
            ", ".join(self.source_rows[:3])
            if len(self.source_rows) <= 3
            else f"{', '.join(self.source_rows[:2])}, ... ({len(self.source_rows)} total)"
        )

        return (
            f"DB Fact [{self.fact_type}]:\n"
            f"- {self.content}\n"
            f"- Source: {self.source_table}[{source_ids}]"
        )

    def to_api_response(self) -> dict[str, Any]:
        """Convert to API response format.

        Used in ChatMessageResponse.used_domain_facts.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "fact_type": self.fact_type,
            "entity_id": self.entity_id,
            "content": self.content,
            "metadata": self.metadata,
            "source": {
                "table": self.source_table,
                "rows": self.source_rows,
                "retrieved_at": self.retrieved_at.isoformat(),
            },
        }
