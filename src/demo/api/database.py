"""API endpoints for domain database exploration."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.domain_models import (
    DomainCustomer,
    DomainInvoice,
    DomainPayment,
    DomainSalesOrder,
    DomainTask,
    DomainWorkOrder,
)
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/database", tags=["demo-database"])


# =============================================================================
# Response Models
# =============================================================================


class CustomerResponse(BaseModel):
    """Customer data."""

    customer_id: str
    name: str
    industry: str | None = None
    notes: str | None = None

    class Config:
        from_attributes = True


class SalesOrderResponse(BaseModel):
    """Sales order data with customer name."""

    so_id: str
    customer_id: str
    customer_name: str
    so_number: str
    title: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    """Invoice data with sales order details."""

    invoice_id: str
    so_id: str
    so_number: str
    invoice_number: str
    amount: str  # Convert Decimal to string for JSON
    due_date: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class WorkOrderResponse(BaseModel):
    """Work order data with sales order details."""

    wo_id: str
    so_id: str
    so_number: str
    description: str
    status: str
    technician: str | None = None
    scheduled_for: str | None = None

    class Config:
        from_attributes = True


class PaymentResponse(BaseModel):
    """Payment data with invoice details."""

    payment_id: str
    invoice_id: str
    invoice_number: str
    amount: str
    method: str | None = None
    created_at: str

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    """Task data with optional customer name."""

    task_id: str
    customer_id: str | None = None
    customer_name: str | None = None
    title: str
    body: str | None = None
    status: str
    created_at: str

    class Config:
        from_attributes = True


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/customers", response_model=list[CustomerResponse])
async def list_customers(session: AsyncSession = Depends(get_db)) -> list[CustomerResponse]:
    """Get all customers from domain schema.

    Returns:
        List of all customers
    """
    result = await session.execute(select(DomainCustomer).order_by(DomainCustomer.name))
    customers = result.scalars().all()

    return [
        CustomerResponse(
            customer_id=str(c.customer_id),
            name=c.name,
            industry=c.industry,
            notes=c.notes,
        )
        for c in customers
    ]


@router.get("/sales_orders", response_model=list[SalesOrderResponse])
async def list_sales_orders(
    session: AsyncSession = Depends(get_db),
) -> list[SalesOrderResponse]:
    """Get all sales orders with customer names.

    Returns:
        List of all sales orders with customer information
    """
    # Join with customers to get customer names
    query = (
        select(DomainSalesOrder, DomainCustomer.name)
        .join(DomainCustomer, DomainSalesOrder.customer_id == DomainCustomer.customer_id)
        .order_by(DomainSalesOrder.created_at.desc())
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        SalesOrderResponse(
            so_id=str(so.so_id),
            customer_id=str(so.customer_id),
            customer_name=customer_name,
            so_number=so.so_number,
            title=so.title,
            status=so.status,
            created_at=so.created_at.isoformat(),
        )
        for so, customer_name in rows
    ]


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(session: AsyncSession = Depends(get_db)) -> list[InvoiceResponse]:
    """Get all invoices with sales order details.

    Returns:
        List of all invoices with SO information
    """
    # Join with sales_orders to get SO numbers
    query = (
        select(DomainInvoice, DomainSalesOrder.so_number)
        .join(DomainSalesOrder, DomainInvoice.so_id == DomainSalesOrder.so_id)
        .order_by(DomainInvoice.issued_at.desc())
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        InvoiceResponse(
            invoice_id=str(inv.invoice_id),
            so_id=str(inv.so_id),
            so_number=so_number,
            invoice_number=inv.invoice_number,
            amount=str(inv.amount),  # Convert Decimal to string
            due_date=inv.due_date.isoformat(),
            status=inv.status,
            created_at=inv.issued_at.isoformat(),  # Use issued_at
        )
        for inv, so_number in rows
    ]


@router.get("/work_orders", response_model=list[WorkOrderResponse])
async def list_work_orders(
    session: AsyncSession = Depends(get_db),
) -> list[WorkOrderResponse]:
    """Get all work orders with sales order details.

    Returns:
        List of all work orders with SO information
    """
    # Join with sales_orders to get SO numbers
    query = (
        select(DomainWorkOrder, DomainSalesOrder.so_number)
        .join(DomainSalesOrder, DomainWorkOrder.so_id == DomainSalesOrder.so_id)
        .order_by(DomainWorkOrder.status)
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        WorkOrderResponse(
            wo_id=str(wo.wo_id),
            so_id=str(wo.so_id),
            so_number=so_number,
            description=wo.description,
            status=wo.status,
            technician=wo.technician,
            scheduled_for=wo.scheduled_for.isoformat() if wo.scheduled_for else None,
        )
        for wo, so_number in rows
    ]


@router.get("/payments", response_model=list[PaymentResponse])
async def list_payments(session: AsyncSession = Depends(get_db)) -> list[PaymentResponse]:
    """Get all payments with invoice details.

    Returns:
        List of all payments with invoice information
    """
    # Join with invoices to get invoice numbers
    query = (
        select(DomainPayment, DomainInvoice.invoice_number)
        .join(DomainInvoice, DomainPayment.invoice_id == DomainInvoice.invoice_id)
        .order_by(DomainPayment.paid_at.desc())
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        PaymentResponse(
            payment_id=str(pmt.payment_id),
            invoice_id=str(pmt.invoice_id),
            invoice_number=inv_number,
            amount=str(pmt.amount),
            method=pmt.method,
            created_at=pmt.paid_at.isoformat(),  # Use paid_at
        )
        for pmt, inv_number in rows
    ]


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(session: AsyncSession = Depends(get_db)) -> list[TaskResponse]:
    """Get all tasks with optional customer names.

    Returns:
        List of all tasks with customer information when available
    """
    # Left join with customers to get names (tasks may not have customers)
    query = (
        select(DomainTask, DomainCustomer.name)
        .outerjoin(DomainCustomer, DomainTask.customer_id == DomainCustomer.customer_id)
        .order_by(DomainTask.created_at.desc())
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        TaskResponse(
            task_id=str(task.task_id),
            customer_id=str(task.customer_id) if task.customer_id else None,
            customer_name=customer_name,
            title=task.title,
            body=task.body,
            status=task.status,
            created_at=task.created_at.isoformat(),
        )
        for task, customer_name in rows
    ]


@router.get("/stats")
async def get_database_stats(session: AsyncSession = Depends(get_db)) -> dict:
    """Get summary statistics for domain database.

    Efficient implementation using SQL COUNT() instead of fetching all rows.

    Returns:
        Dictionary of table row counts

    Performance: O(1) for each table (index scan) vs O(n) (full table scan)
    """
    # Use SQL COUNT() for efficient counting (database-side aggregation)
    customers_result = await session.execute(
        select(func.count()).select_from(DomainCustomer)
    )
    customers_count = customers_result.scalar_one()

    sales_orders_result = await session.execute(
        select(func.count()).select_from(DomainSalesOrder)
    )
    sales_orders_count = sales_orders_result.scalar_one()

    invoices_result = await session.execute(
        select(func.count()).select_from(DomainInvoice)
    )
    invoices_count = invoices_result.scalar_one()

    work_orders_result = await session.execute(
        select(func.count()).select_from(DomainWorkOrder)
    )
    work_orders_count = work_orders_result.scalar_one()

    payments_result = await session.execute(
        select(func.count()).select_from(DomainPayment)
    )
    payments_count = payments_result.scalar_one()

    tasks_result = await session.execute(
        select(func.count()).select_from(DomainTask)
    )
    tasks_count = tasks_result.scalar_one()

    return {
        "customers": customers_count,
        "sales_orders": sales_orders_count,
        "invoices": invoices_count,
        "work_orders": work_orders_count,
        "payments": payments_count,
        "tasks": tasks_count,
    }
