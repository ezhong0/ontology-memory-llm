"""Prometheus metrics for API performance monitoring.

Provides P95/P99 latency tracking and request counting for observability.

Philosophy: Measure what matters for the 800ms P95 SLA.
"""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# ============================================================================
# Request Metrics
# ============================================================================

# HTTP request duration histogram
# Buckets designed for 800ms P95 SLA: [100ms, 200ms, 400ms, 800ms, 1.6s, 3.2s]
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=["method", "endpoint", "status_code"],
    buckets=[0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, float("inf")],
)

# Chat endpoint latency (most critical for SLA)
chat_request_duration_seconds = Histogram(
    "chat_request_duration_seconds",
    "Chat endpoint latency in seconds",
    labelnames=["user_id", "status"],
    buckets=[0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, float("inf")],
)

# Request counter
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)

# ============================================================================
# Memory Retrieval Metrics
# ============================================================================

# Memory retrieval duration
memory_retrieval_duration_seconds = Histogram(
    "memory_retrieval_duration_seconds",
    "Memory retrieval latency in seconds",
    labelnames=["layer", "user_id"],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, float("inf")],
)

# Memories retrieved count
memories_retrieved_total = Counter(
    "memories_retrieved_total",
    "Total memories retrieved",
    labelnames=["layer", "user_id"],
)

# Similarity scores distribution
similarity_score_distribution = Histogram(
    "similarity_score_distribution",
    "Distribution of similarity scores from vector search",
    labelnames=["layer"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

# ============================================================================
# Entity Resolution Metrics
# ============================================================================

# Entity resolution duration
entity_resolution_duration_seconds = Histogram(
    "entity_resolution_duration_seconds",
    "Entity resolution latency in seconds",
    labelnames=["method", "success"],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, float("inf")],
)

# Entity resolution count
entity_resolutions_total = Counter(
    "entity_resolutions_total",
    "Total entity resolution attempts",
    labelnames=["method", "success"],
)

# ============================================================================
# Database Metrics
# ============================================================================

# Database query duration
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query latency in seconds",
    labelnames=["query_type", "table"],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, float("inf")],
)

# Database queries count
db_queries_total = Counter(
    "db_queries_total",
    "Total database queries",
    labelnames=["query_type", "table", "status"],
)

# ============================================================================
# LLM Metrics
# ============================================================================

# LLM call duration
llm_call_duration_seconds = Histogram(
    "llm_call_duration_seconds",
    "LLM API call latency in seconds",
    labelnames=["provider", "model", "operation"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, float("inf")],
)

# LLM tokens used
llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    labelnames=["provider", "model", "token_type"],  # token_type: prompt|completion
)

# LLM cost tracking
llm_cost_usd_total = Counter(
    "llm_cost_usd_total",
    "Total LLM cost in USD",
    labelnames=["provider", "model"],
)

# ============================================================================
# Business Metrics
# ============================================================================

# PII redactions
pii_redactions_total = Counter(
    "pii_redactions_total",
    "Total PII redactions performed",
    labelnames=["pii_type"],
)

# Memory conflicts detected
memory_conflicts_total = Counter(
    "memory_conflicts_total",
    "Total memory conflicts detected",
    labelnames=["conflict_type", "resolution_strategy"],
)

# Idempotent duplicate detections
duplicate_messages_total = Counter(
    "duplicate_messages_total",
    "Total duplicate messages detected (idempotency)",
    labelnames=["user_id"],
)

# ============================================================================
# Helper Functions
# ============================================================================


def get_metrics() -> tuple[bytes, str]:
    """Generate Prometheus metrics in exposition format.

    Returns:
        Tuple of (metrics_bytes, content_type)
    """
    return generate_latest(), CONTENT_TYPE_LATEST
