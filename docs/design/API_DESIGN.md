# API Design and System Interfaces

## Vision Alignment

The API embodies the **"experienced colleague"** metaphor - enabling natural conversation, not database operations.

From VISION.md:
> "The system should behave like an experienced colleague who has worked with this company for years."

**Design Philosophy Applied**:
- **Conversation-first**: Primary interface is `/chat`, not CRUD operations
- **Epistemic transparency**: Expose confidence, sources, conflicts
- **Minimal client complexity**: Rich context in, simple interface out
- **Phase distinction**: Core endpoints (Phase 1) vs advanced features (Phase 2/3)

---

## Phase Roadmap

**Phase 1 (Essential) Endpoints**:
- `POST /chat` - Primary conversation interface
- `GET /memories` - List/inspect memories
- `POST /entities/resolve` - Entity resolution
- `GET /health` - Health check
- Basic memory CRUD operations

**Phase 2 (Enhancements) Endpoints**:
- `POST /chat/stream` - Streaming responses
- `POST /webhooks` - Event subscriptions
- `GET /config` - Learned parameters inspection
- `GET /conflicts` - Conflict management
- Advanced retrieval analytics

**Phase 3 (Learning) Endpoints**:
- Learning parameter overrides
- Cross-user pattern insights
- Meta-memory inspection
- System improvement feedback

---

## API Principles

### 1. Conversation-First Design

The primary interface is **conversational**, not CRUD:
- `POST /chat` (not `POST /memories`)
- System handles extraction, storage, retrieval internally
- Explicit memory operations are secondary (for inspection/admin)

### 2. Rich Context, Simple Interface

Clients provide rich context, system handles complexity:
```python
# Good: Rich context, simple request
POST /chat
{
  "message": "What did Acme order last month?",
  "session_id": "...",
  "user_id": "...",
  "conversation_history": [...]
}

# Bad: Forcing client to do memory operations
GET /memories?entity=acme&type=order&date_range=...
POST /augment with [manually selected memories]
```

### 3. Epistemic Transparency

Responses include confidence, sources, conflicts:
```json
{
  "response": "Acme ordered 50 units of Product X",
  "confidence": 0.85,
  "sources": ["semantic_memory:123", "domain_db:orders.456"],
  "conflicts": null,
  "explanation": "Based on order record from domain database"
}
```

### 4. Idempotency and Retry Safety

All state-changing operations are idempotent:
- Use content hashing for chat events
- Use entity IDs for canonical entities
- Support `Idempotency-Key` header

## Core API: Chat Interface

### Primary Endpoint: Chat **[Phase 1]**

```
POST /api/v1/chat
```

**Purpose**: Process a user message, retrieve relevant memories, augment LLM response, store new memories.

**Request**:
```json
{
  "message": "What did Acme Corporation order last month?",
  "user_id": "user_123",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_history": [
    {
      "role": "user",
      "content": "Tell me about my customers",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "You have three main customers: Acme Corp, Initech, and Umbrella Inc...",
      "timestamp": "2024-01-15T10:30:05Z"
    }
  ],
  "metadata": {
    "source": "web_ui",
    "user_agent": "Mozilla/5.0...",
    "timezone": "America/New_York"
  }
}
```

**Response**:
```json
{
  "response": {
    "content": "Based on our records, Acme Corporation ordered:\n- 50 units of Product X on Jan 12, 2024\n- 25 units of Product Y on Jan 28, 2024\n\nTotal: $12,500",
    "role": "assistant"
  },
  "augmentation": {
    "retrieved_memories": [
      {
        "memory_id": "episodic:789",
        "memory_type": "episodic",
        "summary": "Discussed Acme's Q4 order patterns, noted increase in Product X orders",
        "relevance_score": 0.82,
        "created_at": "2023-12-20T15:00:00Z"
      },
      {
        "memory_id": "semantic:456",
        "memory_type": "semantic",
        "summary": "Acme Corporation prefers expedited shipping",
        "relevance_score": 0.65,
        "created_at": "2023-11-05T09:00:00Z"
      }
    ],
    "domain_queries": [
      {
        "query_type": "orders",
        "entity": "customer:acme_a1b2c3d4",
        "filters": {"date_range": ["2024-01-01", "2024-01-31"]},
        "result_count": 2
      }
    ]
  },
  "memories_created": [
    {
      "memory_id": "episodic:1001",
      "memory_type": "episodic",
      "summary": "User inquired about Acme Corporation's January orders"
    }
  ],
  "entities_resolved": [
    {
      "mention": "Acme Corporation",
      "canonical_id": "customer:acme_a1b2c3d4",
      "confidence": 0.95
    },
    {
      "mention": "last month",
      "temporal_scope": {"start": "2024-01-01", "end": "2024-01-31"},
      "confidence": 1.0
    }
  ],
  "conflicts": null,
  "metadata": {
    "processing_time_ms": 245,
    "retrieval_count": 2,
    "extraction_count": 1
  }
}
```

**Status Codes**:
- `200 OK`: Success
- `400 Bad Request`: Invalid request format
- `401 Unauthorized`: Invalid authentication
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: System error

### Streaming Response **[Phase 2]**

For real-time LLM response streaming:

```
POST /api/v1/chat/stream
```

**Response**: Server-Sent Events (SSE)

```
event: entity_resolution
data: {"mention": "Acme", "canonical_id": "customer:acme_a1b2c3d4", "confidence": 0.95}

event: memory_retrieval
data: {"memory_id": "episodic:789", "relevance_score": 0.82}

event: response_chunk
data: {"content": "Based on our records, Acme Corporation ordered:\n"}

event: response_chunk
data: {"content": "- 50 units of Product X on Jan 12, 2024\n"}

event: memory_creation
data: {"memory_id": "episodic:1001", "type": "episodic"}

event: done
data: {"processing_time_ms": 1850}
```

## Memory Management API

### List Memories **[Phase 1]**

```
GET /api/v1/memories?user_id={user_id}&type={type}&limit={limit}&offset={offset}
```

**Query Parameters**:
- `user_id` (required): User identifier
- `type` (optional): Filter by memory type (`episodic`, `semantic`, `procedural`, `summary`)
- `entity` (optional): Filter by entity ID
- `session_id` (optional): Filter by session
- `date_from`, `date_to` (optional): Temporal range
- `limit` (optional, default: 20, max: 100): Page size
- `offset` (optional, default: 0): Pagination offset

**Response**:
```json
{
  "memories": [
    {
      "memory_id": "episodic:789",
      "memory_type": "episodic",
      "summary": "Discussed rush order with Acme Corporation",
      "entities": [
        {"canonical_id": "customer:acme_a1b2c3d4", "canonical_name": "Acme Corporation"},
        {"canonical_id": "order:12345", "canonical_name": "Order #12345"}
      ],
      "importance": 0.75,
      "confidence": 0.9,
      "created_at": "2024-01-15T14:30:00Z"
    }
  ],
  "pagination": {
    "total": 1247,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

### Get Memory Details **[Phase 1]**

```
GET /api/v1/memories/{memory_id}
```

**Response**:
```json
{
  "memory_id": "semantic:456",
  "memory_type": "semantic",
  "subject": {
    "entity_id": "customer:acme_a1b2c3d4",
    "entity_name": "Acme Corporation"
  },
  "predicate": "prefers",
  "predicate_type": "preference",
  "object": {
    "value": "expedited_shipping",
    "display": "Expedited Shipping"
  },
  "confidence": 0.85,
  "confidence_factors": {
    "observed_count": 5,
    "reinforcement": 3,
    "source_reliability": 0.9
  },
  "importance": 0.7,
  "status": "active",
  "created_at": "2023-11-05T09:00:00Z",
  "updated_at": "2024-01-10T11:20:00Z",
  "source": {
    "type": "extracted_from_event",
    "event_id": 12345
  },
  "related_memories": [
    {"memory_id": "episodic:789", "relationship": "extracted_from"},
    {"memory_id": "semantic:457", "relationship": "related_fact"}
  ]
}
```

### Create Memory (Explicit) **[Phase 1]**

```
POST /api/v1/memories
```

**Purpose**: Explicitly create a memory (typically used for testing or admin operations; normal flow uses `/chat`).

**Request**:
```json
{
  "user_id": "user_123",
  "memory_type": "semantic",
  "data": {
    "subject_entity_id": "customer:acme_a1b2c3d4",
    "predicate": "prefers",
    "predicate_type": "preference",
    "object_value": {"value": "expedited_shipping", "display": "Expedited Shipping"}
  },
  "confidence": 0.8,
  "importance": 0.7,
  "source": {
    "type": "user_explicit",
    "note": "User manually added this preference"
  }
}
```

**Response**: Created memory object (same as GET response).

### Update Memory **[Phase 1]**

```
PATCH /api/v1/memories/{memory_id}
```

**Request**:
```json
{
  "confidence": 0.9,
  "importance": 0.8,
  "status": "active"
}
```

**Response**: Updated memory object.

### Delete Memory **[Phase 1]**

```
DELETE /api/v1/memories/{memory_id}
```

**Response**:
```json
{
  "deleted": true,
  "memory_id": "semantic:456"
}
```

**Note**: Soft delete (marks as `status: 'deleted'`), not hard delete. Preserves audit trail.

## Entity Resolution API

### Resolve Entity **[Phase 1]**

```
POST /api/v1/entities/resolve
```

**Purpose**: Resolve a textual mention to canonical entity.

**Request**:
```json
{
  "mention": "Acme",
  "user_id": "user_123",
  "context": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "recent_entities": ["customer:initech_x7y8z9"],
    "conversation_text": "We discussed their order yesterday"
  }
}
```

**Response**:
```json
{
  "resolved": true,
  "canonical_entity": {
    "entity_id": "customer:acme_a1b2c3d4",
    "entity_type": "customer",
    "canonical_name": "Acme Corporation",
    "properties": {
      "industry": "technology",
      "region": "Northeast"
    }
  },
  "confidence": 0.95,
  "resolution_method": "exact_alias_match",
  "alternatives": [],
  "requires_disambiguation": false
}
```

**Response (Ambiguous)**:
```json
{
  "resolved": false,
  "canonical_entity": null,
  "confidence": 0.0,
  "resolution_method": "multiple_candidates",
  "alternatives": [
    {
      "entity_id": "customer:acme_a1b2c3d4",
      "entity_name": "Acme Corporation",
      "confidence": 0.65,
      "reason": "Last mentioned 2 messages ago"
    },
    {
      "entity_id": "customer:acme_x9y8z7",
      "entity_name": "Acme Industries",
      "confidence": 0.60,
      "reason": "Similar name in customer database"
    }
  ],
  "requires_disambiguation": true,
  "disambiguation_prompt": "I found multiple entities matching 'Acme'. Which one do you mean?"
}
```

### Disambiguate Entity **[Phase 1]**

```
POST /api/v1/entities/disambiguate
```

**Purpose**: User selects from ambiguous entity candidates.

**Request**:
```json
{
  "mention": "Acme",
  "chosen_entity_id": "customer:acme_a1b2c3d4",
  "user_id": "user_123",
  "context": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Response**:
```json
{
  "alias_created": true,
  "alias_id": 5678,
  "entity_id": "customer:acme_a1b2c3d4",
  "confidence": 0.85
}
```

### List Entities **[Phase 1]**

```
GET /api/v1/entities?user_id={user_id}&type={type}&search={query}
```

**Response**:
```json
{
  "entities": [
    {
      "entity_id": "customer:acme_a1b2c3d4",
      "entity_type": "customer",
      "canonical_name": "Acme Corporation",
      "aliases": ["Acme", "Acme Corp", "ACME"],
      "properties": {
        "industry": "technology",
        "region": "Northeast"
      },
      "memory_count": 47,
      "last_referenced": "2024-01-15T14:30:00Z"
    }
  ],
  "pagination": {
    "total": 156,
    "limit": 20,
    "offset": 0
  }
}
```

## Retrieval API

### Search Memories **[Phase 2]**

```
POST /api/v1/retrieval/search
```

**Purpose**: Explicitly search for relevant memories (typically used by advanced clients; normal flow uses `/chat`).

**Request**:
```json
{
  "query": "What are Acme's payment preferences?",
  "user_id": "user_123",
  "filters": {
    "memory_types": ["semantic", "procedural"],
    "entities": ["customer:acme_a1b2c3d4"],
    "date_range": {"start": "2023-01-01", "end": "2024-12-31"}
  },
  "limit": 10,
  "include_scores": true
}
```

**Response**:
```json
{
  "results": [
    {
      "memory_id": "semantic:456",
      "memory_type": "semantic",
      "summary": "Acme Corporation prefers NET30 payment terms",
      "relevance_score": 0.89,
      "score_breakdown": {
        "semantic_similarity": 0.85,
        "entity_overlap": 1.0,
        "temporal_relevance": 0.7,
        "importance": 0.8,
        "reinforcement": 0.9
      },
      "entities": [
        {"canonical_id": "customer:acme_a1b2c3d4", "canonical_name": "Acme Corporation"}
      ],
      "created_at": "2023-06-15T10:00:00Z"
    }
  ],
  "query_analysis": {
    "query_type": "factual_entity_focused",
    "extracted_entities": [
      {"mention": "Acme", "canonical_id": "customer:acme_a1b2c3d4", "confidence": 0.95}
    ],
    "temporal_scope": null
  },
  "retrieval_strategy": {
    "semantic_similarity": 0.25,
    "entity_overlap": 0.40,
    "temporal_relevance": 0.20,
    "importance": 0.10,
    "reinforcement": 0.05
  }
}
```

## Conflict and Validation API

### List Conflicts **[Phase 2]**

```
GET /api/v1/conflicts?user_id={user_id}&resolved={false}
```

**Response**:
```json
{
  "conflicts": [
    {
      "conflict_id": 123,
      "conflict_type": "contradictory_facts",
      "detected_at": "2024-01-15T16:00:00Z",
      "severity": "high",
      "description": "Conflicting information about Acme's payment terms",
      "conflicting_memories": [
        {
          "memory_id": "semantic:456",
          "summary": "Acme prefers NET30 payment terms",
          "confidence": 0.85,
          "created_at": "2023-06-15T10:00:00Z"
        },
        {
          "memory_id": "semantic:789",
          "summary": "Acme prefers NET15 payment terms",
          "confidence": 0.75,
          "created_at": "2024-01-10T11:00:00Z"
        }
      ],
      "resolution_status": "unresolved",
      "suggested_resolution": "More recent memory (NET15) may supersede older (NET30). Validate with user or domain database."
    }
  ]
}
```

### Resolve Conflict **[Phase 2]**

```
POST /api/v1/conflicts/{conflict_id}/resolve
```

**Request**:
```json
{
  "resolution_strategy": "keep_newer",
  "chosen_memory_id": "semantic:789",
  "supersede_memory_ids": ["semantic:456"],
  "note": "Confirmed NET15 is current preference"
}
```

**Response**:
```json
{
  "resolved": true,
  "conflict_id": 123,
  "resolution_applied": {
    "kept_memory": "semantic:789",
    "superseded_memories": ["semantic:456"]
  }
}
```

## System Introspection API

### Health Check **[Phase 1]**

```
GET /api/v1/health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": {"status": "up", "latency_ms": 5},
    "vector_search": {"status": "up", "latency_ms": 12},
    "domain_database": {"status": "up", "latency_ms": 8}
  },
  "timestamp": "2024-01-15T17:00:00Z"
}
```

### System Metrics **[Phase 2]**

```
GET /api/v1/metrics?user_id={user_id}
```

**Response**:
```json
{
  "user_id": "user_123",
  "memory_stats": {
    "total_memories": 1523,
    "by_type": {
      "episodic": 856,
      "semantic": 523,
      "procedural": 98,
      "summary": 46
    }
  },
  "entity_stats": {
    "total_entities": 234,
    "by_type": {
      "customer": 47,
      "order": 156,
      "product": 31
    }
  },
  "activity_stats": {
    "total_sessions": 89,
    "total_messages": 1847,
    "avg_retrieval_count": 2.3,
    "avg_extraction_count": 1.1
  },
  "quality_stats": {
    "avg_confidence": 0.78,
    "conflict_rate": 0.02,
    "disambiguation_rate": 0.08
  }
}
```

### Get User Configuration **[Phase 2]**

```
GET /api/v1/config?user_id={user_id}
```

**Response**:
```json
{
  "user_id": "user_123",
  "preferences": {
    "auto_disambiguation_threshold": 0.75,
    "memory_retention_days": null,
    "confidence_decay_rate": "standard"
  },
  "learned_parameters": {
    "retrieval_weights": {
      "factual_entity_focused": {
        "semantic_similarity": 0.22,
        "entity_overlap": 0.45,
        "temporal_relevance": 0.18,
        "importance": 0.10,
        "reinforcement": 0.05
      }
    },
    "last_learning_run": "2024-01-10T08:00:00Z"
  }
}
```

### Update User Configuration **[Phase 2]**

```
PATCH /api/v1/config?user_id={user_id}
```

**Request**:
```json
{
  "preferences": {
    "auto_disambiguation_threshold": 0.80
  }
}
```

## Authentication and Authorization

### Authentication Scheme

Use **Bearer token authentication**:
```
Authorization: Bearer <jwt_token>
```

**JWT Claims**:
```json
{
  "sub": "user_123",
  "iss": "memory-system",
  "iat": 1642284000,
  "exp": 1642370400,
  "scopes": ["read:memories", "write:memories", "read:entities"]
}
```

### Scopes

- `read:memories`: Read memory data
- `write:memories`: Create/update/delete memories
- `read:entities`: Read entity data
- `write:entities`: Resolve/disambiguate entities
- `read:config`: Read system configuration
- `write:config`: Update system configuration
- `admin`: Full system access

### Rate Limiting

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642284000
```

**Limits** (per user):
- `/chat`: 100 requests/minute
- `/chat/stream`: 20 requests/minute
- `/retrieval/search`: 200 requests/minute
- Other endpoints: 1000 requests/minute

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Entity with ID 'customer:invalid' not found",
    "details": {
      "entity_id": "customer:invalid",
      "user_id": "user_123"
    },
    "request_id": "req_a1b2c3d4",
    "documentation_url": "https://docs.memory-system.example.com/errors/entity-not-found"
  }
}
```

### Error Codes

**Client Errors (4xx)**:
- `INVALID_REQUEST`: Malformed request
- `UNAUTHORIZED`: Invalid or missing authentication
- `FORBIDDEN`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `ENTITY_NOT_FOUND`: Entity not found
- `MEMORY_NOT_FOUND`: Memory not found
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `DISAMBIGUATION_REQUIRED`: Entity resolution ambiguous

**Server Errors (5xx)**:
- `INTERNAL_ERROR`: Unexpected server error
- `DATABASE_ERROR`: Database connection or query error
- `EMBEDDING_SERVICE_ERROR`: Embedding computation failed
- `DOMAIN_DB_ERROR`: Domain database query failed

## Webhooks (Phase 2)

### Register Webhook **[Phase 2]**

```
POST /api/v1/webhooks
```

**Request**:
```json
{
  "url": "https://client.example.com/webhooks/memory-events",
  "events": ["memory.created", "conflict.detected"],
  "secret": "webhook_secret_key"
}
```

### Webhook Events

- `memory.created`: New memory created
- `memory.updated`: Memory updated
- `conflict.detected`: Conflict detected
- `conflict.resolved`: Conflict resolved
- `entity.created`: New entity discovered
- `learning.completed`: Learning algorithm completed

**Webhook Payload**:
```json
{
  "event": "conflict.detected",
  "timestamp": "2024-01-15T16:00:00Z",
  "data": {
    "conflict_id": 123,
    "conflict_type": "contradictory_facts",
    "user_id": "user_123"
  }
}
```

## SDK and Client Libraries

### Python SDK

```python
from memory_system import MemoryClient

client = MemoryClient(api_key="your_api_key")

# Chat interface
response = await client.chat(
    message="What did Acme order last month?",
    user_id="user_123",
    session_id="550e8400-e29b-41d4-a716-446655440000"
)

print(response.content)
print(f"Retrieved {len(response.augmentation.memories)} memories")

# Streaming
async for event in client.chat_stream(message="...", user_id="..."):
    if event.type == "response_chunk":
        print(event.data.content, end="")
    elif event.type == "memory_creation":
        print(f"\nCreated memory: {event.data.memory_id}")

# Entity resolution
entity = await client.resolve_entity(
    mention="Acme",
    user_id="user_123",
    context={"session_id": "..."}
)

if entity.requires_disambiguation:
    chosen = await client.disambiguate_entity(
        mention="Acme",
        chosen_entity_id=entity.alternatives[0].entity_id,
        user_id="user_123"
    )

# Memory search
results = await client.search_memories(
    query="customer payment preferences",
    user_id="user_123",
    limit=10
)

for memory in results:
    print(f"{memory.summary} (score: {memory.relevance_score})")
```

### TypeScript SDK

```typescript
import { MemoryClient } from '@memory-system/client';

const client = new MemoryClient({ apiKey: 'your_api_key' });

// Chat interface
const response = await client.chat({
  message: 'What did Acme order last month?',
  userId: 'user_123',
  sessionId: '550e8400-e29b-41d4-a716-446655440000'
});

console.log(response.content);

// Streaming
const stream = client.chatStream({
  message: '...',
  userId: 'user_123'
});

for await (const event of stream) {
  if (event.type === 'response_chunk') {
    process.stdout.write(event.data.content);
  }
}

// Entity resolution
const entity = await client.resolveEntity({
  mention: 'Acme',
  userId: 'user_123',
  context: { sessionId: '...' }
});

if (entity.requiresDisambiguation) {
  await client.disambiguateEntity({
    mention: 'Acme',
    chosenEntityId: entity.alternatives[0].entityId,
    userId: 'user_123'
  });
}
```

## Internal System Interfaces

### Memory Processor Interface

```python
class MemoryProcessor(Protocol):
    """Internal interface for memory processing pipeline."""

    async def process_chat_event(
        self,
        event: ChatEvent
    ) -> ProcessingResult:
        """
        Process chat event through full pipeline:
        1. Entity resolution
        2. Memory extraction
        3. Memory storage
        4. Retrieval augmentation

        Returns: ProcessingResult with created memories and augmentation context
        """
        ...

    async def extract_memories(
        self,
        event: ChatEvent,
        resolved_entities: List[ResolvedEntity]
    ) -> List[ExtractedMemory]:
        """Extract memories from chat event."""
        ...

    async def retrieve_memories(
        self,
        query: str,
        user_id: str,
        context: ConversationContext
    ) -> List[RetrievedMemory]:
        """Retrieve relevant memories for query."""
        ...
```

### Entity Resolver Interface

```python
class EntityResolver(Protocol):
    """Internal interface for entity resolution."""

    async def resolve(
        self,
        mention: str,
        context: ResolutionContext
    ) -> ResolutionResult:
        """Resolve mention to canonical entity."""
        ...

    async def create_canonical_entity(
        self,
        entity_type: str,
        external_ref: dict,
        canonical_name: str,
        properties: dict
    ) -> CanonicalEntity:
        """Create or get canonical entity."""
        ...

    async def create_alias(
        self,
        canonical_entity_id: str,
        alias_text: str,
        user_id: str,
        confidence: float,
        metadata: dict
    ) -> EntityAlias:
        """Create entity alias."""
        ...
```

### Domain Database Interface

```python
class DomainDatabase(Protocol):
    """Internal interface for domain database queries."""

    async def query_entity(
        self,
        entity_type: str,
        filters: dict
    ) -> List[dict]:
        """Query domain database for entities."""
        ...

    async def get_entity_by_id(
        self,
        entity_type: str,
        entity_id: str
    ) -> Optional[dict]:
        """Get specific entity from domain database."""
        ...

    async def get_related_entities(
        self,
        entity_id: str,
        relation_type: str
    ) -> List[dict]:
        """Get entities related via ontology."""
        ...
```

## API Versioning

### Versioning Strategy

Use URL-based versioning:
- `/api/v1/...` - Current stable version
- `/api/v2/...` - Next version (when needed)

### Version Support Policy

- **Current version (v1)**: Fully supported, all new features
- **Previous version**: Security updates only, 6-month deprecation notice
- **Deprecated version**: 6 months until removal

### Breaking Changes

Considered breaking (require new version):
- Removing endpoints
- Removing request/response fields
- Changing field types
- Changing authentication scheme

Not breaking (can be added to current version):
- Adding endpoints
- Adding optional request fields
- Adding response fields
- Adding new error codes

## Testing the API

### Health Check

```bash
curl https://api.memory-system.example.com/api/v1/health
```

### Chat Request

```bash
curl -X POST https://api.memory-system.example.com/api/v1/chat \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What did Acme order last month?",
    "user_id": "user_123",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

### Entity Resolution

```bash
curl -X POST https://api.memory-system.example.com/api/v1/entities/resolve \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "mention": "Acme",
    "user_id": "user_123",
    "context": {
      "session_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }'
```

---

## Summary: API Design

**Core Architecture**: Conversation-first REST API enabling natural interaction with ontology-aware memory system.

**Primary Endpoint**: `POST /api/v1/chat`
- Single endpoint handles full pipeline: ingestion → extraction → retrieval → augmentation → response
- Clients provide message + context, system handles all memory operations
- Returns: LLM response + augmentation metadata + created memories + entity resolutions

**Key Principles**:
1. **Conversation-first**: Not a database API - natural language interface
2. **Epistemic transparency**: All responses include confidence, sources, conflicts
3. **Rich context in, simple interface out**: Client provides conversation history, system handles complexity
4. **Idempotent operations**: Content hashing, entity IDs, `Idempotency-Key` header
5. **Graceful degradation**: Works with incomplete info, requests disambiguation when needed

**Endpoint Categories**:

**Phase 1 Essential**:
- `POST /chat` - Main conversation interface
- `GET /memories` - Inspect memories
- `POST /entities/resolve` - Entity resolution
- Memory CRUD (create, read, update, delete)
- `GET /health` - System health

**Phase 2 Enhancements**:
- `POST /chat/stream` - SSE streaming
- `GET /conflicts` - Conflict inspection
- `POST /webhooks` - Event subscriptions
- `GET /config` - Learned parameters
- `GET /metrics` - System analytics

**Phase 3 Learning**:
- Learning control endpoints
- Meta-memory inspection
- Cross-user insights

**Response Structure** (epistemic transparency):
```json
{
  "response": {"content": "...", "role": "assistant"},
  "augmentation": {
    "retrieved_memories": [...],
    "domain_queries": [...]
  },
  "memories_created": [...],
  "entities_resolved": [...],
  "conflicts": null  // or conflict details
}
```

**Authentication**: Bearer token (JWT)
**Rate Limiting**: Per-user, endpoint-specific
**Error Handling**: Structured errors with codes, messages, details
**Versioning**: URL-based (`/api/v1/`, `/api/v2/`)

**SDK Support**:
- Python SDK (`memory_system.MemoryClient`)
- TypeScript SDK (`@memory-system/client`)
- Both support: chat, streaming, entity resolution, memory search

---

**Vision Alignment**:
- ✅ Conversation-first: Primary interface is `/chat`, not CRUD
- ✅ Epistemic transparency: Responses include confidence, sources, conflicts
- ✅ Rich context: API accepts full conversation history, system handles complexity
- ✅ Graceful degradation: Supports partial information, disambiguation flows
- ✅ Experienced colleague metaphor: Natural interaction, not database operations
- ✅ Design Philosophy: Phase distinction clear (essential vs enhancements vs learning)
