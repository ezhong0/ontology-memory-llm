"""Debug trace service - Non-invasive request tracing using contextvars.

This service collects debug traces throughout request processing without
coupling to the core business logic. Uses Python's contextvars for
async-safe, thread-local storage.

Architecture: Pure domain service with no infrastructure dependencies.

Design Philosophy:
- Non-invasive: Services don't need to know about tracing
- Async-safe: Works correctly with async/await
- Type-safe: Structured trace models with full type hints
- Performance: Zero overhead when tracing disabled
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

# ============================================================================
# Trace Models
# ============================================================================


class TraceType(str, Enum):
    """Types of debug traces."""

    ENTITY_RESOLUTION = "entity_resolution"
    MEMORY_RETRIEVAL = "memory_retrieval"
    DATABASE_QUERY = "database_query"
    LLM_CALL = "llm_call"
    REASONING_STEP = "reasoning_step"
    ERROR = "error"


@dataclass(frozen=True)
class DebugTrace:
    """Single debug trace event.

    Immutable value object representing one trace event in the request.
    """

    trace_id: UUID
    trace_type: TraceType
    timestamp: datetime
    duration_ms: float | None
    data: dict[str, Any]
    parent_trace_id: UUID | None = None


@dataclass
class TraceContext:
    """Trace collection context for a single request.

    Mutable container that accumulates traces during request processing.
    """

    request_id: UUID
    started_at: datetime
    traces: list[DebugTrace] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_trace(
        self,
        trace_type: TraceType,
        data: dict[str, Any],
        duration_ms: float | None = None,
        parent_trace_id: UUID | None = None,
    ) -> UUID:
        """Add a trace to this context.

        Args:
            trace_type: Type of trace
            data: Trace-specific data
            duration_ms: Optional duration in milliseconds
            parent_trace_id: Optional parent trace for hierarchical traces

        Returns:
            UUID of created trace
        """
        trace = DebugTrace(
            trace_id=uuid4(),
            trace_type=trace_type,
            timestamp=datetime.now(UTC),
            duration_ms=duration_ms,
            data=data,
            parent_trace_id=parent_trace_id,
        )
        self.traces.append(trace)
        return trace.trace_id

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "request_id": str(self.request_id),
            "started_at": self.started_at.isoformat(),
            "duration_ms": (datetime.now(UTC) - self.started_at).total_seconds() * 1000,
            "traces": [
                {
                    "trace_id": str(trace.trace_id),
                    "type": trace.trace_type.value,
                    "timestamp": trace.timestamp.isoformat(),
                    "duration_ms": trace.duration_ms,
                    "data": trace.data,
                    "parent_trace_id": str(trace.parent_trace_id) if trace.parent_trace_id else None,
                }
                for trace in self.traces
            ],
            "metadata": self.metadata,
            "trace_count": len(self.traces),
        }


# ============================================================================
# Context Variable Storage
# ============================================================================

# Thread-local, async-safe storage for current trace context
_trace_context: ContextVar[TraceContext | None] = ContextVar(
    "_trace_context", default=None
)


# ============================================================================
# Debug Trace Service
# ============================================================================


class DebugTraceService:
    """Service for collecting debug traces using contextvars.

    Usage:
        # Start tracing for a request
        trace_service = DebugTraceService()
        context = trace_service.start_trace(metadata={"user_id": "user-123"})

        # Add traces throughout processing
        trace_service.add_entity_resolution_trace(
            mention="Acme",
            resolved_id="customer:acme_123",
            method="exact_match",
            confidence=1.0
        )

        # Get all collected traces
        traces = trace_service.get_current_context()
    """

    @staticmethod
    def start_trace(metadata: dict[str, Any] | None = None) -> TraceContext:
        """Start a new trace context for the current request.

        Args:
            metadata: Optional metadata for this request (user_id, session_id, etc.)

        Returns:
            Created trace context
        """
        context = TraceContext(
            request_id=uuid4(),
            started_at=datetime.now(UTC),
            metadata=metadata or {},
        )
        _trace_context.set(context)
        return context

    @staticmethod
    def get_current_context() -> TraceContext | None:
        """Get the current trace context.

        Returns:
            Current trace context, or None if tracing not active
        """
        return _trace_context.get()

    @staticmethod
    def clear_context() -> None:
        """Clear the current trace context."""
        _trace_context.set(None)

    @staticmethod
    def add_trace(
        trace_type: TraceType,
        data: dict[str, Any],
        duration_ms: float | None = None,
    ) -> UUID | None:
        """Add a trace to the current context.

        Args:
            trace_type: Type of trace
            data: Trace-specific data
            duration_ms: Optional duration in milliseconds

        Returns:
            UUID of created trace, or None if tracing not active
        """
        context = _trace_context.get()
        if context is None:
            return None

        return context.add_trace(trace_type, data, duration_ms)

    # ========================================================================
    # Convenience Methods for Common Trace Types
    # ========================================================================

    @staticmethod
    def add_entity_resolution_trace(
        mention: str,
        resolved_id: str | None,
        method: str,
        confidence: float,
        candidates: list[dict[str, Any]] | None = None,
    ) -> UUID | None:
        """Add entity resolution trace.

        Args:
            mention: Original mention text
            resolved_id: Resolved entity ID (None if failed)
            method: Resolution method used (exact, alias, fuzzy, llm, domain_db)
            confidence: Confidence score (0.0-1.0)
            candidates: Optional list of candidate entities considered

        Returns:
            Trace ID if tracing active, else None
        """
        return DebugTraceService.add_trace(
            TraceType.ENTITY_RESOLUTION,
            {
                "mention": mention,
                "resolved_id": resolved_id,
                "method": method,
                "confidence": confidence,
                "candidates": candidates or [],
                "success": resolved_id is not None,
            },
        )

    @staticmethod
    def add_memory_retrieval_trace(
        query: str,
        memories_found: int,
        top_memory: dict[str, Any] | None = None,
        retrieval_method: str = "semantic_search",
    ) -> UUID | None:
        """Add memory retrieval trace.

        Args:
            query: Search query
            memories_found: Number of memories retrieved
            top_memory: Optional top-ranked memory details
            retrieval_method: Method used (semantic_search, keyword, hybrid)

        Returns:
            Trace ID if tracing active, else None
        """
        return DebugTraceService.add_trace(
            TraceType.MEMORY_RETRIEVAL,
            {
                "query": query,
                "memories_found": memories_found,
                "top_memory": top_memory,
                "retrieval_method": retrieval_method,
            },
        )

    @staticmethod
    def add_database_query_trace(
        query_type: str,
        table: str,
        rows_affected: int,
        duration_ms: float,
    ) -> UUID | None:
        """Add database query trace.

        Args:
            query_type: Type of query (SELECT, INSERT, UPDATE, etc.)
            table: Table name
            rows_affected: Number of rows affected
            duration_ms: Query duration in milliseconds

        Returns:
            Trace ID if tracing active, else None
        """
        return DebugTraceService.add_trace(
            TraceType.DATABASE_QUERY,
            {
                "query_type": query_type,
                "table": table,
                "rows_affected": rows_affected,
            },
            duration_ms=duration_ms,
        )

    @staticmethod
    def add_llm_call_trace(
        model: str,
        prompt_length: int,
        response_length: int,
        tokens_used: int,
        cost_usd: float,
        duration_ms: float,
    ) -> UUID | None:
        """Add LLM call trace.

        Args:
            model: Model used (gpt-4o-mini, etc.)
            prompt_length: Length of prompt in characters
            response_length: Length of response in characters
            tokens_used: Total tokens consumed
            cost_usd: Cost in USD
            duration_ms: Call duration in milliseconds

        Returns:
            Trace ID if tracing active, else None
        """
        return DebugTraceService.add_trace(
            TraceType.LLM_CALL,
            {
                "model": model,
                "prompt_length": prompt_length,
                "response_length": response_length,
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
            },
            duration_ms=duration_ms,
        )

    @staticmethod
    def add_reasoning_step_trace(
        step: str,
        description: str,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
    ) -> UUID | None:
        """Add reasoning step trace.

        Args:
            step: Step name/identifier
            description: Human-readable description
            input_data: Optional input data
            output_data: Optional output data

        Returns:
            Trace ID if tracing active, else None
        """
        return DebugTraceService.add_trace(
            TraceType.REASONING_STEP,
            {
                "step": step,
                "description": description,
                "input": input_data or {},
                "output": output_data or {},
            },
        )

    @staticmethod
    def add_error_trace(
        error_type: str,
        error_message: str,
        context: dict[str, Any] | None = None,
    ) -> UUID | None:
        """Add error trace.

        Args:
            error_type: Type/class of error
            error_message: Error message
            context: Optional error context

        Returns:
            Trace ID if tracing active, else None
        """
        return DebugTraceService.add_trace(
            TraceType.ERROR,
            {
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {},
            },
        )
