# Architecture Deep Dive

> Understanding the "why" behind key design decisions

## Table of Contents
1. [Hexagonal Architecture](#hexagonal-architecture)
2. [6-Layer Memory Model](#6-layer-memory-model)
3. [5-Stage Entity Resolution](#5-stage-entity-resolution)
4. [Multi-Signal Retrieval](#multi-signal-retrieval)
5. [Dual Truth System](#dual-truth-system)
6. [Key Trade-Offs](#key-trade-offs)

---

## Hexagonal Architecture

### The Problem

Traditional layered architectures create tight coupling:

```python
# ❌ BAD: Domain logic depends on infrastructure
class EntityResolutionService:
    def resolve(self, mention: str):
        # Direct SQL query - can't test without database
        result = db.execute("SELECT * FROM entities WHERE name = %s", mention)
        return result
```

**Consequences**:
- Can't test business logic without spinning up PostgreSQL
- Switching databases requires rewriting domain code
- Business rules scattered across infrastructure code

### The Solution: Ports & Adapters

```
┌───────────────────────────────────────┐
│   API Layer (FastAPI)                 │
│   HTTP handlers, validation           │
└──────────────┬────────────────────────┘
               │
┌──────────────▼────────────────────────┐
│   Application Layer (Use Cases)       │
│   Orchestrate domain services         │
└──────────────┬────────────────────────┘
               │
┌──────────────▼────────────────────────┐
│   Domain Layer (Pure Business Logic)  │
│   • Entities (CanonicalEntity)        │
│   • Services (EntityResolution)       │
│   • Ports (IEntityRepository - ABC)   │
│   NO infrastructure imports!          │
└──────────────┬────────────────────────┘
               │
┌──────────────▼────────────────────────┐
│   Infrastructure (Adapters)           │
│   • PostgreSQLEntityRepository        │
│   • AnthropicLLMService               │
└───────────────────────────────────────┘
```

### Code Example

**Port (Interface)** `src/domain/ports/entity_repository.py`:
```python
from abc import ABC, abstractmethod

class IEntityRepository(ABC):
    @abstractmethod
    async def find_by_name(self, name: str) -> CanonicalEntity | None:
        pass
```

**Adapter (Implementation)** `src/infrastructure/database/repositories/entity_repository.py`:
```python
class PostgreSQLEntityRepository(IEntityRepository):
    async def find_by_name(self, name: str) -> CanonicalEntity | None:
        query = select(EntityModel).where(EntityModel.name == name)
        result = await self.session.execute(query)
        return self._to_entity(result.scalar_one_or_none())
```

**Domain Service** `src/domain/services/entity_resolution_service.py`:
```python
class EntityResolutionService:
    def __init__(self, entity_repo: IEntityRepository):  # ← Depends on port
        self.entity_repo = entity_repo

    async def resolve(self, mention: str) -> ResolutionResult:
        entity = await self.entity_repo.find_by_name(mention)
        if entity:
            return ResolutionResult(entity.id, confidence=1.0)
        # ... other stages
```

**Test** (no database needed):
```python
@pytest.mark.asyncio
async def test_exact_match():
    # Mock repository
    mock_repo = Mock(spec=IEntityRepository)
    mock_repo.find_by_name.return_value = CanonicalEntity(
        id="customer:123", name="Gai Media"
    )

    service = EntityResolutionService(entity_repo=mock_repo)
    result = await service.resolve("Gai Media")

    assert result.entity_id == "customer:123"
    assert result.confidence == 1.0
```

**Benefits**:
- ✅ Domain tests run in <10ms (vs 100ms+ with real DB)
- ✅ Swap PostgreSQL → MongoDB without changing business logic
- ✅ Business rules in pure Python (no SQL/HTTP)

---

## 6-Layer Memory Model

### The Problem

Flat storage makes retrieval expensive and imprecise:

```
User: "Gai Media prefers Friday deliveries and NET30 terms"

❌ Flat approach: Store entire sentence as single embedding
→ Later query: "What's Gai's delivery preference?"
→ Must search through ALL text (slow, imprecise)
```

### The Solution: Specialized Layers

```
Layer 6: Summaries     → "Gai: NET30, Friday, 3 orders"
              ↑ consolidates
Layer 5: Procedural    → "When invoice → check domain.invoices"
              ↑ derives
Layer 4: Semantic      → (Gai, delivery_pref, Friday)
              ↑ extracts
Layer 3: Episodic      → "Asked about Gai on 2024-10-15"
              ↑ identifies
Layer 2: Entities      → customer:gai_123 → "Gai Media"
              ↑ mentions
Layer 1: Chat Events   → "Remember: Gai Media prefers..."
```

### Layer Details

#### Layer 1: Chat Events (Audit Trail)
- **Purpose**: Immutable record of all conversations
- **Schema**: `(session_id, content, content_hash, timestamp)`
- **Query**: Never directly queried (source for upper layers)
- **Example**: `"Remember: Gai Media prefers Friday deliveries"`

#### Layer 2: Entities (Canonical References)
- **Purpose**: Resolve mentions to canonical IDs
- **Schema**: `(id, canonical_name, entity_type, external_refs)`
- **Query**: Name lookup (exact/fuzzy)
- **Example**: `"Gai" → customer:gai_123 → "Gai Media Productions"`

#### Layer 4: Semantic (Structured Facts)
- **Purpose**: Knowledge as subject-predicate-object triples
- **Schema**: `(subject_entity_id, predicate, object_value, confidence, embedding)`
- **Query**: pgvector similarity + (subject, predicate) indexes
- **Example**: `(customer:gai_123, delivery_preference, Friday)`

**Why triples?**
```python
# Later query: "What's Gai's delivery preference?"
# Direct lookup:
SELECT object_value
FROM semantic_memories
WHERE subject_entity_id = 'customer:gai_123'
  AND predicate = 'delivery_preference'
# → "Friday" (50ms)

# vs flat storage: semantic search through all text (500ms+)
```

#### Layer 5: Procedural (Learned Heuristics)
- **Purpose**: Trigger-action patterns
- **Schema**: `(trigger_pattern, action_structure, success_count)`
- **Query**: Pattern matching on user message
- **Example**: Trigger `"invoice mentioned"` → Action `"query domain.invoices"`

#### Layer 6: Summaries (Consolidations)
- **Purpose**: Cross-session aggregation
- **Schema**: `(user_id, time_range, summary_text, source_memory_ids)`
- **Query**: Time-range filtered retrieval
- **Example**: `"Last 7 days with Gai: discussed NET30, Friday delivery, SO-1001 status"`

---

## 5-Stage Entity Resolution

### The Problem

**Pure LLM approach**: Every mention requires LLM call ($0.03, 300ms)

**Our approach**: 95% resolved without LLM ($0.0015, 50ms avg)

### The 5 Stages

```python
async def resolve_entity(self, mention: str) -> ResolutionResult:
    # Stage 1: Exact match (70%)
    if entity := await self.entity_repo.find_by_name(mention):
        return ResolutionResult(entity.id, confidence=1.0, method="exact")

    # Stage 2: User alias (15%)
    if alias := await self.alias_repo.find(mention, user_id):
        return ResolutionResult(alias.entity_id, confidence=0.95, method="alias")

    # Stage 3: Fuzzy match (10%)
    candidates = await self.entity_repo.fuzzy_search(mention, threshold=0.7)
    if len(candidates) == 1:
        return ResolutionResult(candidates[0].id, confidence=0.85, method="fuzzy")

    # Stage 4: LLM coreference (5%)
    if len(candidates) > 1:
        resolved = await self.llm.resolve_coreference(mention, candidates, context)
        return ResolutionResult(resolved.id, confidence=0.75, method="llm")

    # Stage 5: Domain bootstrap (<1%)
    if domain_entity := await self.domain_db.find_by_name(mention):
        entity = await self.entity_repo.create_from_domain(domain_entity)
        return ResolutionResult(entity.id, confidence=0.90, method="domain")

    return ResolutionResult(None, confidence=0.0, method="unresolved")
```

### Performance Comparison

| Stage | Coverage | Latency | Cost/1k | Accuracy |
|-------|----------|---------|---------|----------|
| 1: Exact | 70% | 20ms | $0 | 100% |
| 2: Alias | 15% | 25ms | $0 | 98% |
| 3: Fuzzy | 10% | 50ms | $0 | 85% |
| 4: LLM | 5% | 300ms | $30 | 90% |
| 5: Domain | <1% | 40ms | $0 | 95% |
| **Hybrid** | **100%** | **50ms avg** | **$1.50** | **95%** |
| Pure LLM | 100% | 300ms | $30 | 90% |

**Savings**: 15x cost reduction, 6x latency reduction

---

## Multi-Signal Retrieval

### The Problem

**Naive vector search**: Only semantic similarity

```python
# ❌ Single signal
score = semantic_similarity(query_embedding, memory_embedding)
```

**Issues**:
- Misses recently discussed topics (recency bias)
- Ignores entity overlap (query mentions "Gai", memory about "Gai")
- No temporal coherence (conversation flow)

### The Solution: 5 Signals

```python
relevance_score = (
    0.40 × semantic_similarity    # Vector cosine similarity
  + 0.25 × entity_overlap         # Shared entities
  + 0.20 × recency                # Time-based decay
  + 0.10 × temporal_coherence     # Conversation flow
  + 0.05 × importance             # User-marked priority
)
```

### Example

```
Query: "What's Gai's delivery preference?"
Candidates (after pgvector search):
  Memory A: (Gai, delivery_pref, Friday)
  Memory B: (Gai, payment_terms, NET30)
  Memory C: (TC Boiler, delivery_pref, Monday)

Scoring:
  Memory A:
    semantic_sim = 0.92 (query mentions "delivery")
    entity_overlap = 1.0 (both mention "Gai")
    recency = 0.95 (created 2 days ago)
    temporal = 1.0 (same session)
    importance = 0.5 (default)
    → 0.40×0.92 + 0.25×1.0 + 0.20×0.95 + 0.10×1.0 + 0.05×0.5
    → 0.368 + 0.25 + 0.19 + 0.10 + 0.025 = 0.933

  Memory B:
    semantic_sim = 0.75 (query doesn't mention "payment")
    entity_overlap = 1.0 (both mention "Gai")
    recency = 0.95
    temporal = 1.0
    importance = 0.5
    → 0.40×0.75 + 0.25×1.0 + 0.20×0.95 + 0.10×1.0 + 0.05×0.5
    → 0.300 + 0.25 + 0.19 + 0.10 + 0.025 = 0.865

  Memory C:
    semantic_sim = 0.90 (query mentions "delivery")
    entity_overlap = 0.0 (different entity: TC Boiler)
    recency = 0.80 (created 10 days ago)
    temporal = 0.0 (different session)
    importance = 0.5
    → 0.40×0.90 + 0.25×0.0 + 0.20×0.80 + 0.10×0.0 + 0.05×0.5
    → 0.360 + 0.0 + 0.16 + 0.0 + 0.025 = 0.545

Ranking: A (0.933) > B (0.865) > C (0.545)
Result: Return Memory A (Friday delivery)
```

**Why this works**: Entity overlap prevents "delivery preference" for wrong entity from ranking higher.

---

## Dual Truth System

### The Problem

**Single source of truth doesn't work for hybrid systems**:

```
Monday: User says "Gai's status is in_fulfillment"
  → Store in memory (confidence: 0.85)

Tuesday: Database updated to "shipped"

Wednesday: User asks "What's Gai's status?"
  → Naive approach: Return "in_fulfillment" (WRONG!)
```

### The Solution: Database = Facts, Memory = Context

```python
# Correspondence Truth (database)
db_status = domain_db.query("SELECT status FROM sales_orders WHERE id = 'so_1001'")
# → "shipped"

# Contextual Truth (memory)
memory_status = memory_repo.find_semantic(subject="so_1001", predicate="status")
# → "in_fulfillment" (outdated)

# Conflict detection
if db_status != memory_status:
    conflicts.append(MemoryConflict(
        type="memory_vs_db",
        existing_value=memory_status,
        new_value=db_status,
        resolution="trust_db"
    ))

    # Mark memory for decay
    memory.mark_as_conflicted()
    memory.apply_decay()

# Response includes both
return f"Status is {db_status} (previously {memory_status})"
```

**Benefits**:
- ✅ **Epistemic Humility**: Expose conflicts, don't hide them
- ✅ **Authoritative Facts**: Database is source of truth
- ✅ **Contextual Understanding**: Memory provides preference/context
- ✅ **Self-Correction**: Conflicted memories decay

---

## Key Trade-Offs

### 1. Why 5-Stage Entity Resolution (Not Pure LLM)?

| Metric | Pure LLM | 5-Stage Hybrid |
|--------|----------|----------------|
| **Cost** | $0.03/turn | $0.0015/turn (15x cheaper) |
| **Latency** | 300ms | 50ms avg (6x faster) |
| **Accuracy** | 90% | 95% (deterministic stages = 100%) |
| **When to use** | Complex coreference | Production systems |

**Decision**: Hybrid wins for production (cost + latency + accuracy).

### 2. Why pgvector (Not Pinecone/Weaviate)?

| Feature | pgvector | Pinecone | Weaviate |
|---------|----------|----------|----------|
| **ACID Transactions** | ✅ Full | ❌ Eventual | ❌ Eventual |
| **Joins** | ✅ Native SQL | ❌ App layer | ❌ App layer |
| **Cost** | ✅ $0 (included) | ❌ $70/mo | ❌ $25/mo |
| **Ops** | ✅ Single DB | ❌ External service | ❌ External service |
| **Latency** | ✅ 30-50ms | ✅ 20-40ms | ✅ 25-45ms |
| **Scale** | ⚠️ 10M vectors | ✅ 1B+ | ✅ 1B+ |

**Decision**: pgvector for Phase 1 (<10M vectors, need ACID).

**Example: Atomic transaction**:
```python
async with session.begin():
    # Both succeed or both fail (ACID)
    entity = await entity_repo.create(entity)
    memory = await memory_repo.create(SemanticMemory(
        subject_entity_id=entity.id, ...
    ))
```

**Migration path**: Phase 3 → Weaviate if > 10M vectors.

### 3. Why Max Confidence = 0.95 (Not 1.0)?

**Problem**: Overconfidence → brittle systems

```python
# ❌ BAD: Confidence = 1.0
memory = SemanticMemory(
    predicate="delivery_preference",
    object="Friday",
    confidence=1.0  # "absolutely certain"
)
# → Never decays, never questions, breaks when preference changes
```

**Solution**: Cap at 0.95, apply decay

```python
# ✅ GOOD: Confidence = 0.95, exponential decay
confidence_t = confidence_0 × e^(-DECAY_RATE × days)

# Reaches 0.5 in ~60 days
# → Triggers active validation: "Still prefer Friday?"
```

**Benefits**:
- ✅ System admits uncertainty
- ✅ Asks for validation when confidence drops
- ✅ Self-correcting over time

### 4. Why Hexagonal Architecture (Not Layered)?

| Architecture | Testability | Flexibility | Complexity |
|--------------|-------------|-------------|------------|
| **Layered** | ⚠️ Needs DB | ⚠️ Tight coupling | ✅ Simple |
| **Hexagonal** | ✅ Mocks only | ✅ Swap adapters | ⚠️ More files |

**Decision**: Hexagonal for production systems (testability + flexibility > simplicity).

---

## Summary

### Architectural Principles

1. **Hexagonal**: Domain = pure Python, infrastructure = swappable adapters
2. **6-Layer Memory**: Specialized layers for query patterns (triples > flat storage)
3. **5-Stage Entity Resolution**: 95% deterministic (cost + latency optimization)
4. **Multi-Signal Scoring**: 5 signals (semantic + entity + recency + temporal + importance)
5. **Dual Truth**: Database = facts, Memory = context (expose conflicts)
6. **Epistemic Humility**: Max 0.95 confidence, decay over time, validate when stale

### Trade-Off Summary

| Decision | Optimizes For | Trades Off |
|----------|---------------|------------|
| 5-stage entity resolution | Cost (15x), latency (6x) | Some accuracy (95% vs 100%) |
| pgvector (not Pinecone) | ACID, cost, simplicity | Scale (10M vs 1B vectors) |
| Multi-signal scoring | Precision | Complexity (5 formulas) |
| Hexagonal architecture | Testability, flexibility | Code volume (ports + adapters) |
| Confidence decay | Self-correction | Must handle validation UX |

---

**Next**: [Cost Optimization](./cost_optimization.md) | [Conflict Resolution](./conflict_resolution.md)
