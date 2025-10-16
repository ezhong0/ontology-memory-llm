"""Chat interface for demo - shows memory system working end-to-end.

Week 2 implementation: Simple but functional chat that demonstrates:
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


# ============================================================================
# Chat Endpoint
# ============================================================================


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    session: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """Send chat message and get reply with full memory system integration.

    Week 2 Implementation:
    - Fetches domain facts (customers, invoices, sales orders)
    - Fetches semantic memories for context
    - Builds reply context
    - Generates LLM reply
    - Returns reply + debug traces

    Args:
        request: Chat message request
        session: Database session

    Returns:
        Chat response with reply and debug info
    """
    logger.info(
        "chat_message_received",
        user_id=request.user_id,
        message_length=len(request.message),
    )

    # Start debug trace context
    trace_context = DebugTraceService.start_trace(
        metadata={
            "user_id": request.user_id,
            "message": request.message,
        }
    )

    try:
        # Step 0: Get or create session_id and store user message
        session_id = UUID(request.session_id) if request.session_id else uuid4()

        # Store user message in chat_events
        user_event = ChatEvent(
            session_id=session_id,
            user_id=request.user_id,
            role="user",
            content=request.message,
            content_hash=hashlib.sha256(request.message.encode()).hexdigest(),
            created_at=datetime.now(UTC),
        )
        session.add(user_event)
        await session.flush()  # Get event_id for potential use

        # Step 1: Fetch domain facts
        start_time = datetime.now(UTC)
        domain_facts = await _fetch_domain_facts(session, request.user_id)
        duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        DebugTraceService.add_database_query_trace(
            query_type="SELECT",
            table="domain.customers, domain.invoices",
            rows_affected=len(domain_facts),
            duration_ms=duration_ms,
        )

        DebugTraceService.add_reasoning_step_trace(
            step="domain_fact_retrieval",
            description=f"Retrieved {len(domain_facts)} domain facts",
            output_data={"facts_count": len(domain_facts)},
        )

        logger.info(
            "domain_facts_fetched",
            user_id=request.user_id,
            facts_count=len(domain_facts),
        )

        # Step 2: Fetch relevant memories
        start_time = datetime.now(UTC)
        memories = await _fetch_relevant_memories(session, request.user_id)
        duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        DebugTraceService.add_memory_retrieval_trace(
            query=request.message,
            memories_found=len(memories),
            top_memory={
                "content": memories[0].content,
                "confidence": memories[0].confidence,
                "relevance": memories[0].relevance_score,
            }
            if memories
            else None,
            retrieval_method="simple_fetch",
        )

        logger.info(
            "memories_fetched",
            user_id=request.user_id,
            memories_count=len(memories),
        )

        # Step 2.5: Fetch recent conversation history
        chat_history = await _fetch_recent_chat_events(session, session_id, exclude_event_id=user_event.event_id)

        # Step 3: Build reply context
        context = ReplyContext(
            query=request.message,
            domain_facts=domain_facts,
            retrieved_memories=memories,
            recent_chat_events=chat_history,
            user_id=request.user_id,
            session_id=session_id,
        )

        # Step 4: Generate reply using LLM (with automatic fallback if no API key)
        # Get LLM reply generator from DI container (properly configured with OpenAI provider)
        generator = container.llm_reply_generator()
        reply = await generator.generate(context)

        logger.info(
            "chat_reply_generated",
            user_id=request.user_id,
            reply_length=len(reply),
        )

        # Store assistant reply in chat_events
        assistant_event = ChatEvent(
            session_id=session_id,
            user_id=request.user_id,
            role="assistant",
            content=reply,
            content_hash=hashlib.sha256(reply.encode()).hexdigest(),
            created_at=datetime.now(UTC),
        )
        session.add(assistant_event)
        await session.commit()  # Commit all changes

        # Step 5: Build debug response
        debug_info = {
            "domain_facts_used": [
                {
                    "type": fact.fact_type,
                    "content": fact.content,
                    "source": fact.source_table,
                }
                for fact in domain_facts
            ],
            "memories_used": [
                {
                    "type": mem.memory_type,
                    "content": mem.content,
                    "confidence": mem.confidence,
                    "relevance": mem.relevance_score,
                }
                for mem in memories
            ],
            "context_summary": context.to_debug_summary(),
            "conversation_history_count": len(chat_history),
        }

        # Get collected traces
        trace_data = trace_context.to_dict() if trace_context else None

        return ChatMessageResponse(
            reply=reply,
            session_id=str(session_id),
            debug=debug_info,
            traces=trace_data
        )

    except Exception as e:
        logger.error(
            "chat_message_failed",
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


async def _fetch_relevant_memories(
    session: AsyncSession, user_id: str
) -> list[RetrievedMemory]:
    """Fetch relevant memories for user.

    Week 2: Simple approach - fetch all active semantic memories.
    Phase 1C will add proper semantic search and relevance scoring.

    Args:
        session: Database session
        user_id: User identifier

    Returns:
        List of retrieved memories
    """
    # Fetch semantic memories with entity names
    query = (
        select(SemanticMemory, CanonicalEntity.canonical_name)
        .join(
            CanonicalEntity,
            SemanticMemory.subject_entity_id == CanonicalEntity.entity_id,
        )
        .where(SemanticMemory.user_id == user_id)
        .where(SemanticMemory.status == "active")
        .order_by(SemanticMemory.created_at.desc())
        .limit(10)
    )

    result = await session.execute(query)
    rows = result.all()

    memories: list[RetrievedMemory] = []
    for memory, entity_name in rows:
        # Build human-readable content
        obj_value = memory.object_value
        if isinstance(obj_value, dict):
            # Format dict nicely
            obj_str = ", ".join(f"{k}: {v}" for k, v in obj_value.items())
        else:
            obj_str = str(obj_value)

        content = f"{entity_name} {memory.predicate}: {obj_str}"

        memories.append(
            RetrievedMemory(
                memory_id=memory.memory_id,
                memory_type="semantic",
                content=content,
                relevance_score=0.8,  # Week 2: Placeholder, Phase 1C adds real scoring
                confidence=memory.confidence,
            )
        )

    return memories


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
