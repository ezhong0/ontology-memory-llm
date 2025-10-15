"""SQLAlchemy models for domain schema (external business data).

This schema represents the external business system that the memory system
integrates with. It's separate from the app schema (memory system tables).

Schema: domain.*
Purpose: Demo scenarios and test data
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

DomainBase = declarative_base()


class DomainCustomer(DomainBase):
    """Customer entity in domain schema."""

    __tablename__ = "customers"
    __table_args__ = {"schema": "domain"}

    customer_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )
    name = Column(Text, nullable=False)
    industry = Column(Text)
    notes = Column(Text)

    def __repr__(self) -> str:
        return f"<DomainCustomer(name={self.name}, industry={self.industry})>"


class DomainSalesOrder(DomainBase):
    """Sales order entity in domain schema."""

    __tablename__ = "sales_orders"
    __table_args__ = {"schema": "domain"}

    so_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("domain.customers.customer_id", ondelete="CASCADE"),
        nullable=False
    )
    so_number = Column(Text, unique=True, nullable=False)
    title = Column(Text, nullable=False)
    status = Column(
        Text,
        CheckConstraint(
            "status IN ('draft', 'approved', 'in_fulfillment', 'fulfilled', 'cancelled')"
        ),
        nullable=False,
        default="draft"
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<DomainSalesOrder(so_number={self.so_number}, status={self.status})>"


class DomainWorkOrder(DomainBase):
    """Work order entity in domain schema."""

    __tablename__ = "work_orders"
    __table_args__ = {"schema": "domain"}

    wo_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )
    so_id = Column(
        UUID(as_uuid=True),
        ForeignKey("domain.sales_orders.so_id", ondelete="CASCADE"),
        nullable=False
    )
    description = Column(Text)
    status = Column(
        Text,
        CheckConstraint(
            "status IN ('queued', 'in_progress', 'blocked', 'done')"
        ),
        nullable=False,
        default="queued"
    )
    technician = Column(Text)
    scheduled_for = Column(Date)

    def __repr__(self) -> str:
        return f"<DomainWorkOrder(status={self.status}, technician={self.technician})>"


class DomainInvoice(DomainBase):
    """Invoice entity in domain schema."""

    __tablename__ = "invoices"
    __table_args__ = {"schema": "domain"}

    invoice_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )
    so_id = Column(
        UUID(as_uuid=True),
        ForeignKey("domain.sales_orders.so_id", ondelete="CASCADE"),
        nullable=False
    )
    invoice_number = Column(Text, unique=True, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(
        Text,
        CheckConstraint("status IN ('open', 'paid', 'void')"),
        nullable=False,
        default="open"
    )
    issued_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<DomainInvoice(invoice_number={self.invoice_number}, amount={self.amount}, status={self.status})>"


class DomainPayment(DomainBase):
    """Payment entity in domain schema."""

    __tablename__ = "payments"
    __table_args__ = {"schema": "domain"}

    payment_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )
    invoice_id = Column(
        UUID(as_uuid=True),
        ForeignKey("domain.invoices.invoice_id", ondelete="CASCADE"),
        nullable=False
    )
    amount = Column(Numeric(12, 2), nullable=False)
    method = Column(Text)  # ACH, credit_card, check, wire
    paid_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<DomainPayment(amount={self.amount}, method={self.method})>"


class DomainTask(DomainBase):
    """Task entity in domain schema."""

    __tablename__ = "tasks"
    __table_args__ = {"schema": "domain"}

    task_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("domain.customers.customer_id", ondelete="SET NULL"),
        nullable=True
    )
    title = Column(Text, nullable=False)
    body = Column(Text)
    status = Column(
        Text,
        CheckConstraint("status IN ('todo', 'doing', 'done')"),
        nullable=False,
        default="todo"
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<DomainTask(title={self.title}, status={self.status})>"
