# API Reference

Complete specification for all HTTP endpoints.

**Base URL**: `http://localhost:8000`
**OpenAPI Docs**: http://localhost:8000/docs

---

## Authentication

Currently using header-based user ID:

```bash
# Method 1: JSON body (simplified endpoint)
curl -X POST /api/v1/chat -d '{"user_id": "demo"}'

# Method 2: Header (structured endpoints)
curl -X POST /api/v1/chat/message \
  -H "X-User-Id: demo_user"
```

---

## Chat Endpoints

### POST `/api/v1/chat`

**Purpose**: Simplified chat endpoint for E2E testing and quick interactions.

**Request**:
```json
{
  "user_id": "demo_user",
  "message": "What is Kai Media's order status?",
  "session_id": "optional-uuid"
}
```

**Response**:
```json
{
  "response": "Based on current data, Kai Media has...",
  "augmentation": {
    "entities_resolved": [
      {
        "mention": "Kai Media",
        "entity_id": "customer_kai_123",
        "canonical_name": "Kai Media Productions",
        "confidence": 1.0,
        "method": "exact_match"
      }
    ],
    "domain_facts": [
      {
        "fact_type": "sales_order",
        "entity_id": "customer_kai_123",
        "table": "domain.sales_orders",
        "content": "SO-1001: 500 units, in_fulfillment",
        "metadata": {
          "so_number": "SO-1001",
          "status": "in_fulfillment"
        }
      }
    ],
    "memories_retrieved": [
      {
        "memory_id": 1,
        "memory_type": "semantic",
        "predicate": "payment_terms",
        "object_value": {"value": "NET30"},
        "confidence": 0.85,
        "relevance_score": 0.89
      }
    ]
  },
  "memories_created": [
    {
      "memory_type": "semantic",
      "subject_entity_id": "customer_kai_123",
      "predicate": "status_inquiry",
      "object_value": {"timestamp": "2024-10-16"},
      "confidence": 0.70
    },
    {
      "memory_type": "episodic",
      "summary": "User asked about Kai Media order status",
      "event_id": "event_123"
    }
  ],
  "provenance": {
    "memory_ids": [1],
    "similarity_scores": [0.89],
    "memory_count": 1,
    "source_types": ["semantic"]
  },
  "conflicts_detected": []
}
```

**Status Codes**:
- `200 OK`: Success (may include disambiguation_required flag)
- `500 Internal Server Error`: Processing failed

**Special Case - Disambiguation**:
```json
{
  "disambiguation_required": true,
  "original_mention": "Apple",
  "candidates": [
    {
      "entity_id": "customer_apple_tech",
      "canonical_name": "Apple Inc",
      "similarity_score": 0.95,
      "properties": {"industry": "Technology"}
    },
    {
      "entity_id": "customer_apple_farm",
      "canonical_name": "Apple Farm Supply",
      "similarity_score": 0.95,
      "properties": {"industry": "Agriculture"}
    }
  ],
  "message": "Multiple entities match 'Apple'. Please select one."
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "message": "When should we deliver to Kai Media?"
  }'
```

---

### POST `/api/v1/chat/message`

**Purpose**: Structured chat endpoint with full entity resolution details.

**Request**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "What is the status of SO-1001?",
  "role": "user",
  "metadata": {}
}
```

**Headers**:
```
X-User-Id: demo_user
Content-Type: application/json
```

**Response**:
```json
{
  "event_id": "event_123",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "resolved_entities": [
    {
      "entity_id": "sales_order_so_1001",
      "canonical_name": "SO-1001",
      "entity_type": "sales_order",
      "mention_text": "SO-1001",
      "confidence": 1.0,
      "method": "exact_match"
    }
  ],
  "mention_count": 1,
  "resolution_success_rate": 1.0,
  "created_at": "2024-10-16T12:00:00Z"
}
```

**Status Codes**:
- `201 Created`: Message processed successfully
- `400 Bad Request`: Invalid request format
- `422 Unprocessable Entity`: Ambiguous entity (see disambiguation response)
- `500 Internal Server Error`: Processing failed

---

### POST `/api/v1/chat/message/enhanced`

**Purpose**: Full pipeline with memory retrieval and domain augmentation.

**Request**: Same as `/chat/message`

**Response**: Includes `retrieved_memories` and `domain_facts`:
```json
{
  "event_id": "event_123",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "resolved_entities": [...],
  "retrieved_memories": [
    {
      "memory_id": 1,
      "memory_type": "semantic",
      "content": "delivery_preference: Friday",
      "relevance_score": 0.94,
      "confidence": 0.85
    }
  ],
  "domain_facts": [
    {
      "fact_type": "invoice",
      "entity_id": "customer_kai_123",
      "content": "INV-1009: $1,200, open",
      "metadata": {...},
      "source_table": "domain.invoices",
      "source_rows": 1
    }
  ],
  "reply": "Based on your records, Kai Media...",
  "context_summary": "2 entities resolved | 1 domain fact | 1 memory retrieved",
  "mention_count": 2,
  "memory_count": 1,
  "created_at": "2024-10-16T12:00:00Z"
}
```

---

## Consolidation Endpoint

### POST `/api/v1/consolidate`

**Purpose**: Consolidate episodic memories into summaries.

**Request**:
```json
{
  "scope_type": "session_window",
  "scope_identifier": "5",
  "force": true
}
```

**Headers**:
```
X-User-Id: demo_user
```

**Parameters**:
- `scope_type`: `"session_window"` | `"time_window"` | `"entity_focused"`
- `scope_identifier`:
  - For session_window: number of sessions (e.g., "5" for last 5 sessions)
  - For time_window: ISO date range (e.g., "2024-10-01:2024-10-15")
  - For entity_focused: entity_id (e.g., "customer_kai_123")
- `force`: Boolean - Force consolidation even if below threshold

**Response**:
```json
{
  "summary_id": "summary_123",
  "summary_text": "Over the last 5 sessions, discussed Kai Media's NET30 terms, Friday delivery preference, and order SO-1001 status.",
  "scope_type": "session_window",
  "scope_identifier": "5",
  "confidence": 0.75,
  "key_facts": {
    "entities_mentioned": ["customer_kai_123", "sales_order_so_1001"],
    "predicates": ["payment_terms", "delivery_preference", "status"],
    "session_count": 5
  },
  "interaction_patterns": [
    "User frequently asks about order status",
    "Preference inquiries cluster on Fridays"
  ],
  "created_at": "2024-10-16T12:00:00Z"
}
```

**Status Codes**:
- `200 OK`: Consolidation successful
- `400 Bad Request`: Invalid scope parameters
- `404 Not Found`: No memories found in scope
- `500 Internal Server Error`: Consolidation failed

---

## Procedural Memory Endpoint

### GET `/api/v1/procedural`

**Purpose**: Retrieve learned procedural patterns.

**Query Parameters**:
- `min_confidence`: Minimum confidence threshold (default: 0.5)
- `min_support`: Minimum observation count (default: 3)
- `lookback_days`: Days to look back (default: 30)

**Example**:
```bash
curl "http://localhost:8000/api/v1/procedural?min_confidence=0.6" \
  -H "X-User-Id: demo_user"
```

**Response**:
```json
{
  "patterns": [
    {
      "pattern_id": "pattern_1",
      "trigger_pattern": "invoice mentioned",
      "action_structure": {
        "type": "query_domain",
        "table": "domain.invoices",
        "filter_entity": true
      },
      "confidence": 0.82,
      "support_count": 15,
      "success_rate": 0.93,
      "last_fired": "2024-10-15T10:30:00Z"
    }
  ]
}
```

---

## Health Check

### GET `/api/v1/health`

**Purpose**: System health status.

**Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "0.1.0",
  "uptime_seconds": 3600
}
```

---

## Response Models

### Entity Resolution

```typescript
interface ResolvedEntity {
  entity_id: string;           // "customer_kai_123"
  canonical_name: string;      // "Kai Media Productions"
  entity_type: string;         // "customer" | "sales_order" | ...
  mention_text: string;        // Original mention from user
  confidence: number;          // 0.0 - 1.0
  method: string;              // "exact_match" | "alias" | "fuzzy" | "llm" | "domain"
}
```

### Domain Fact

```typescript
interface DomainFact {
  fact_type: string;           // "invoice" | "sales_order" | "work_order"
  entity_id: string;           // Related entity ID
  table: string;               // "domain.invoices"
  content: string;             // Human-readable summary
  metadata: Record<string, any>;  // Structured data
  source_rows: number;         // Number of rows queried
}
```

### Retrieved Memory

```typescript
interface RetrievedMemory {
  memory_id: number;
  memory_type: string;         // "semantic" | "episodic" | "procedural"
  content: string;             // Human-readable content
  predicate?: string;          // For semantic memories
  object_value?: any;          // For semantic memories
  relevance_score: number;     // 0.0 - 1.0 (multi-signal score)
  confidence: number;          // 0.0 - 1.0 (epistemic confidence)
}
```

### Memory Conflict

```typescript
interface MemoryConflict {
  conflict_type: string;       // "memory_vs_db" | "value_mismatch" | "temporal"
  subject: string;             // Entity ID
  predicate: string;           // What's conflicted
  existing_value: any;         // Current memory value
  new_value: any;              // New/DB value
  existing_confidence: number;
  new_confidence: number;
  resolution_strategy: string; // "trust_db" | "keep_newest" | "keep_highest"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": "ErrorType",
  "message": "Human-readable description",
  "details": {
    // Additional context
  }
}
```

### Common Errors

**400 Bad Request**:
```json
{
  "error": "ValidationError",
  "message": "Invalid request format",
  "details": {
    "field": "user_id",
    "issue": "Required field missing"
  }
}
```

**422 Unprocessable Entity** (Disambiguation):
```json
{
  "error": "AmbiguousEntity",
  "message": "Multiple entities match 'Apple'",
  "candidates": [...]
}
```

**500 Internal Server Error**:
```json
{
  "error": "InternalServerError",
  "message": "An unexpected error occurred"
}
```

---

## Rate Limits

Currently no rate limiting (development mode).

**Production recommendations**:
- 100 requests/minute per user
- 10 consolidations/hour per user
- Burst: 20 requests in 10 seconds

---

## OpenAPI Specification

Full OpenAPI 3.0 spec available at:
- **Interactive docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **JSON spec**: http://localhost:8000/openapi.json

**Generate client SDK**:
```bash
# TypeScript
npx openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g typescript-fetch \
  -o ./client

# Python
openapi-python-client generate \
  --url http://localhost:8000/openapi.json
```

---

**Next**: [Database Schema](./database_schema.md) | [Configuration](./configuration_reference.md)
