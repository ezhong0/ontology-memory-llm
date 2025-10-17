"""Chat interface for demo - shows memory system working end-to-end.

Full implementation: Uses the same ProcessChatMessageUseCase as production API
- Entity resolution
- Semantic memory extraction
- Domain fact retrieval
- Memory retrieval
- Context building
- LLM reply generation with full provenance
"""

import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_process_chat_message_use_case
from src.application.dtos import ProcessChatMessageInput
from src.application.use_cases import ProcessChatMessageUseCase
from src.domain.services import DebugTraceService
from src.domain.value_objects.conversation_context_reply import (
    RecentChatEvent,
    ReplyContext,
    RetrievedMemory,
)
from src.domain.value_objects.domain_fact import DomainFact
from src.infrastructure.database.domain_models import (
    DomainCustomer,
    DomainInvoice,
    DomainSalesOrder,
)
from src.infrastructure.database.models import (
    CanonicalEntity,
    ChatEvent,
    SemanticMemory,
)
from src.infrastructure.database.session import get_db
from src.infrastructure.di.container import container

# Import activity publisher
from src.demo.api import activity

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ChatMessageRequest(BaseModel):
    """Request model for chat message."""

    message: str
    user_id: str = "demo-user"
    session_id: str | None = None  # Optional session ID for conversation continuity


class ChatMessageResponse(BaseModel):
    """Response model for chat message with debug traces."""

    reply: str
    session_id: str  # Return session ID for conversation continuity
    debug: dict
    traces: dict | None = None  # Debug traces for visualization
    step_timings: dict[str, float] | None = None  # Step timings in seconds for UI


# ============================================================================
# Chat Endpoint
# ============================================================================


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    use_case: ProcessChatMessageUseCase = Depends(get_process_chat_message_use_case),
) -> ChatMessageResponse:
    """Send chat message and get reply with full memory system integration.

    Full Implementation (uses production ProcessChatMessageUseCase):
    - Entity resolution (extracts and resolves entities like "I like ice cream")
    - Semantic memory extraction (creates memories from user statements)
    - Domain fact retrieval (fetches relevant customer/order data)
    - Memory retrieval (finds relevant existing memories)
    - Builds reply context
    - Generates LLM reply with full provenance
    - Returns reply + debug traces + created memories

    Args:
        request: Chat message request
        use_case: Chat processing use case (injected)

    Returns:
        Chat response with reply, debug info, and created memories
    """
    logger.info(
        "demo_chat_message_received",
        user_id=request.user_id,
        message_length=len(request.message),
    )

    try:
        # Get or create session_id
        session_id = UUID(request.session_id) if request.session_id else uuid4()

        # Create input DTO for use case
        input_dto = ProcessChatMessageInput(
            user_id=request.user_id,
            session_id=session_id,
            content=request.message,
            role="user",
            metadata={},
        )

        # Execute full chat processing pipeline (entity resolution + semantic extraction + reply generation)
        output = await use_case.execute(input_dto)

        # Build debug response
        debug_info = {
            "domain_facts_used": [
                {
                    "type": fact.fact_type,
                    "content": fact.content,
                    "source": fact.source_table,
                }
                for fact in output.domain_facts
            ],
            "memories_retrieved": [
                {
                    "memory_id": mem.memory_id,
                    "type": mem.memory_type,
                    "content": mem.content,
                    "confidence": mem.confidence,
                    "relevance": mem.relevance_score,
                }
                for mem in output.retrieved_memories
            ],
            "memories_created": [
                {
                    "memory_id": mem.memory_id,
                    "type": "semantic",
                    "content": mem.content,  # Natural language content
                    "entities": mem.entities,  # Array of entity IDs
                    "confidence": mem.confidence,
                    "importance": mem.importance,
                    "status": mem.status,
                }
                for mem in output.semantic_memories
            ],
            "entities_resolved": [
                {
                    "entity_id": entity.entity_id,
                    "canonical_name": entity.canonical_name,
                    "mention_text": entity.mention_text,
                    "confidence": entity.confidence,
                    "method": entity.method,
                }
                for entity in output.resolved_entities
            ],
        }

        # Publish activity for created memories
        if output.semantic_memories:
            activity.add_activity(
                event_type="memory_creation",
                summary=f"Created {len(output.semantic_memories)} new semantic memories",
                details={
                    "user_id": request.user_id,
                    "memories_count": len(output.semantic_memories),
                    "memory_contents": [mem.content[:50] + "..." if len(mem.content) > 50 else mem.content for mem in output.semantic_memories],
                },
            )

        logger.info(
            "demo_chat_reply_generated",
            user_id=request.user_id,
            reply_length=len(output.reply),
            memories_created=len(output.semantic_memories),
            entities_resolved=len(output.resolved_entities),
        )

        return ChatMessageResponse(
            reply=output.reply,
            session_id=str(session_id),
            debug=debug_info,
            traces=None,  # Traces not needed for demo
            step_timings=output.step_timings,  # Include step timings for UI
        )

    except Exception as e:
        logger.error(
            "demo_chat_message_failed",
            user_id=request.user_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {e!s}",
        ) from None


# ============================================================================
# Helper Functions
# ============================================================================


async def _fetch_domain_facts(
    session: AsyncSession, user_id: str
) -> list[DomainFact]:
    """Fetch domain facts from database.

    Week 2: Simple approach - fetch recent customers and invoices.

    Args:
        session: Database session
        user_id: User identifier

    Returns:
        List of domain facts
    """
    facts: list[DomainFact] = []
    now = datetime.now(UTC)

    # Fetch customers with their details
    customer_result = await session.execute(
        select(DomainCustomer).order_by(DomainCustomer.name).limit(10)
    )
    customers = customer_result.scalars().all()

    for customer in customers:
        facts.append(
            DomainFact(
                fact_type="customer_info",
                entity_id=f"customer:{customer.customer_id}",
                content=f"Customer: {customer.name} (Industry: {customer.industry})",
                metadata={
                    "name": customer.name,
                    "industry": customer.industry,
                    "notes": customer.notes,
                },
                source_table="domain.customers",
                source_rows=[str(customer.customer_id)],
                retrieved_at=now,
            )
        )

    # Fetch invoices with customer names
    invoice_query = (
        select(DomainInvoice, DomainCustomer.name, DomainSalesOrder.so_number)
        .join(DomainSalesOrder, DomainInvoice.so_id == DomainSalesOrder.so_id)
        .join(DomainCustomer, DomainSalesOrder.customer_id == DomainCustomer.customer_id)
        .order_by(DomainInvoice.issued_at.desc())
        .limit(10)
    )

    invoice_result = await session.execute(invoice_query)
    invoices = invoice_result.all()

    for inv, customer_name, so_number in invoices:
        status_desc = "paid" if inv.status == "paid" else f"due {inv.due_date}"
        facts.append(
            DomainFact(
                fact_type="invoice_status",
                entity_id=f"invoice:{inv.invoice_id}",
                content=f"Invoice {inv.invoice_number} for {customer_name}: ${float(inv.amount):,.2f} ({status_desc})",
                metadata={
                    "invoice_number": inv.invoice_number,
                    "customer_name": customer_name,
                    "so_number": so_number,
                    "amount": float(inv.amount),
                    "due_date": inv.due_date.isoformat() if inv.due_date else None,
                    "status": inv.status,
                },
                source_table="domain.invoices",
                source_rows=[str(inv.invoice_id)],
                retrieved_at=now,
            )
        )

    # Fetch sales orders with customer names
    sales_order_query = (
        select(DomainSalesOrder, DomainCustomer.name)
        .join(DomainCustomer, DomainSalesOrder.customer_id == DomainCustomer.customer_id)
        .order_by(DomainSalesOrder.created_at.desc())
        .limit(10)
    )

    so_result = await session.execute(sales_order_query)
    sales_orders = so_result.all()

    for so, customer_name in sales_orders:
        facts.append(
            DomainFact(
                fact_type="sales_order_status",
                entity_id=f"sales_order:{so.so_id}",
                content=f"Sales Order {so.so_number} for {customer_name}: {so.title} (Status: {so.status})",
                metadata={
                    "so_number": so.so_number,
                    "customer_name": customer_name,
                    "title": so.title,
                    "status": so.status,
                    "created_at": so.created_at.isoformat() if so.created_at else None,
                },
                source_table="domain.sales_orders",
                source_rows=[str(so.so_id)],
                retrieved_at=now,
            )
        )

    return facts


async def _fetch_recent_chat_events(
    session: AsyncSession, session_id: UUID, exclude_event_id: int | None = None, limit: int = 10
) -> list[RecentChatEvent]:
    """Fetch recent chat history for conversation context.

    Args:
        session: Database session
        session_id: Session identifier
        exclude_event_id: Event ID to exclude (usually the current user message)
        limit: Maximum number of events to fetch

    Returns:
        List of RecentChatEvent objects for conversation continuity
    """
    query = (
        select(ChatEvent)
        .where(ChatEvent.session_id == session_id)
        .order_by(ChatEvent.created_at.desc())
        .limit(limit)
    )

    if exclude_event_id:
        query = query.where(ChatEvent.event_id != exclude_event_id)

    result = await session.execute(query)
    events = result.scalars().all()

    # Reverse to get chronological order (oldest first)
    return [RecentChatEvent(role=event.role, content=event.content) for event in reversed(events)]


# NOTE: This helper function is unused (legacy from Week 2)
# The endpoint now uses ProcessChatMessageUseCase which handles memory retrieval
# async def _fetch_relevant_memories(
#     session: AsyncSession, user_id: str
# ) -> list[RetrievedMemory]:
#     """Fetch relevant memories for user - UNUSED."""
#     pass


def _generate_fallback_reply(context: ReplyContext) -> str:
    """Generate fallback reply when OpenAI API key is not configured.

    Week 2 demo: Returns a formatted response showing the context
    that would have been sent to the LLM.

    Args:
        context: Reply context

    Returns:
        Fallback reply string
    """
    sections = []

    sections.append("**[Demo Mode - No LLM]**")
    sections.append("I would have used the following context to generate a reply:\n")

    if context.domain_facts:
        sections.append(f"**Domain Facts ({len(context.domain_facts)}):**")
        for fact in context.domain_facts[:5]:  # Show first 5
            sections.append(f"- {fact.content}")
        if len(context.domain_facts) > 5:
            sections.append(f"... and {len(context.domain_facts) - 5} more")
        sections.append("")

    if context.retrieved_memories:
        sections.append(f"**Memories ({len(context.retrieved_memories)}):**")
        for mem in context.retrieved_memories[:5]:  # Show first 5
            sections.append(f"- {mem.content} (confidence: {mem.confidence:.0%})")
        if len(context.retrieved_memories) > 5:
            sections.append(f"... and {len(context.retrieved_memories) - 5} more")
        sections.append("")

    sections.append(
        "**To enable full LLM replies**, set OPENAI_API_KEY environment variable."
    )

    return "\n".join(sections)
