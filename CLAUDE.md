# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

**Ontology-Aware Memory System**: A sophisticated memory system for LLM agents that transforms raw conversations into structured, retrievable knowledge with domain ontology integration.

**Memory Pipeline**: `Raw Chat → Episodic Memory → Semantic Memory → Procedural Memory → Summaries`

**Current Status**: Week 0 implementation complete. Foundation ready for Phase 1 development (10-12 weeks).

**Design Quality**: 9.74/10 (Exceptional) | 97% Philosophy Alignment

### The Core Metaphor

From `docs/vision/VISION.md`:

> "The system should behave like an **experienced colleague** who has worked with this company for years"

This colleague:
- Never forgets what matters (perfect recall of relevant context)
- Knows the business deeply (understands data, processes, relationships)
- Learns your way of working (adapts to preferences)
- Admits uncertainty (doesn't pretend to know when unsure)
- Explains their thinking (always traces reasoning to sources)
- Gets smarter over time (each conversation improves future ones)

### Philosophical Foundation: Dual Truth

**The central thesis**: An intelligent agent requires **both correspondence truth (database) and contextual truth (memory)** in dynamic equilibrium.

- **Correspondence Truth** (Database): Objective facts, verifiable, authoritative
  - Example: `invoice_id: INV-1009, amount: $1200, status: open`

- **Contextual Truth** (Memory): Interpretive layers that transform data into understanding
  - Example: "Customer is sensitive about reminders", "They typically pay 2-3 days late"

**Neither alone is sufficient**. The database without memory is precise but hollow; memory without database is meaningful but ungrounded.

## Essential Commands

### Development Workflow
```bash
# First-time setup (installs deps, starts DB, runs migrations)
make setup

# Daily development
make docker-up                # Start PostgreSQL
make run                      # Start API server (http://localhost:8000)
make test-watch              # Run tests on file changes

# Before committing
make check-all               # Run all quality checks (lint + typecheck + test coverage)
```

### Database Operations
```bash
# Migrations
make db-migrate                                        # Apply pending migrations
make db-create-migration MSG="description"            # Create new migration (autogenerate)
make db-rollback                                       # Rollback last migration
make db-reset                                         # ⚠️ Reset database (destroys data)

# Direct access
make db-shell                                         # Open psql shell
```

### Testing
```bash
# Run tests
make test                    # All tests
make test-unit              # Unit tests only (fast, no DB)
make test-integration       # Integration tests (requires DB)
make test-cov               # With coverage report (HTML in htmlcov/)

# Test single file/function
poetry run pytest tests/unit/domain/test_entity_resolver.py           # Single file
poetry run pytest tests/unit/domain/test_entity_resolver.py::test_exact_match  # Single test
poetry run pytest -k "entity"                                          # All tests matching "entity"
```

### Code Quality
```bash
make lint                    # Check code style (ruff)
make lint-fix               # Auto-fix linting issues
make format                 # Format code (ruff)
make typecheck              # Type checking (mypy strict mode)
make security               # Security checks (bandit + pip-audit)
```

## Architecture: The Big Picture

### Hexagonal Architecture (Ports & Adapters)

```
┌─────────────────────────────────────────────┐
│  API Layer (FastAPI)                        │  ← HTTP requests
│  - Routes in src/api/routes/                │
│  - Pydantic models in src/api/models/       │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  Domain Layer (Pure Python)                 │  ← Business logic
│  - Entities (CanonicalEntity, SemanticMemory)│
│  - Services (EntityResolver, MemoryRetriever)│
│  - Ports (Repository interfaces - ABC)      │
│  NO INFRASTRUCTURE IMPORTS                   │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  Infrastructure Layer (Adapters)            │  ← External systems
│  - PostgreSQL repositories                   │
│  - OpenAI embedding service                  │
│  - Domain database connector                 │
└─────────────────────────────────────────────┘
```

**Critical Rule**: Domain layer never imports from infrastructure. Dependency direction is one-way: API → Domain → Infrastructure (via interfaces).

### Key Subsystems & Their Files

**Entity Resolution (5-stage algorithm)**:
- Design: `docs/design/ENTITY_RESOLUTION_DESIGN.md`
- Domain service: `src/domain/services/entity_resolver.py` (to implement)
- Repository port: `src/domain/ports/entity_repository.py` (to implement)
- Repository impl: `src/infrastructure/database/repositories/entity_repository.py` (to implement)
- Database models: `src/infrastructure/database/models.py` (✅ complete: CanonicalEntity, EntityAlias)

**5-Stage Resolution Process with Confidence Scores**:
1. **Exact Match** (confidence: 1.0) - Lookup canonical_name in canonical_entities
2. **User-Specific Alias** (confidence: 0.95) - Check entity_aliases WHERE user_id = current_user
3. **Fuzzy Match** (confidence: 0.85 high, 0.70 low) - pg_trgm similarity > 0.70 threshold
4. **Coreference Resolution** (confidence: 0.60) - Use conversation context ("it", "they", "that customer")
5. **User Disambiguation** (confidence: 0.85 after selection) - Present top 5 candidates, user selects

**Lazy Entity Creation**: Entities are NOT pre-loaded. When a mention like "ACME Corp" fails resolution, query domain DB (customers table), create canonical_entity with external_ref pointing to customer record, then resolve.

**Memory Lifecycle (4 states: ACTIVE, AGING, SUPERSEDED, INVALIDATED)**:
- Design: `docs/design/LIFECYCLE_DESIGN.md`
- Domain service: `src/domain/services/lifecycle_manager.py` (to implement)
- Database model: `src/infrastructure/database/models.py` (✅ complete: SemanticMemory with status field)
- Heuristics: `src/config/heuristics.py` (✅ complete: DECAY_RATE_PER_DAY, REINFORCEMENT_BOOSTS)

**State Transitions**:
- **ACTIVE** → **AGING**: When confidence < 0.3 threshold (due to decay or conflicting info)
- **ACTIVE** → **SUPERSEDED**: When new memory replaces old (confidence_gap > 0.30 or age_gap > 60 days)
- **ACTIVE** → **INVALIDATED**: When user explicitly corrects ("No, that's wrong")
- **AGING** → **ACTIVE**: When user validates during active recall ("Yes, that's still correct")

**Passive Computation (Critical Pattern)**:
- Decay is NOT stored in database (no background jobs)
- Current confidence = `stored_confidence * exp(-days_since_validation * DECAY_RATE_PER_DAY)`
- Computed on-demand during retrieval
- Only write to DB on reinforcement or state change

**Reinforcement with Diminishing Returns**:
- 1st validation: +0.15 confidence boost
- 2nd validation: +0.10
- 3rd validation: +0.05
- 4th+ validations: +0.02 each (capped at MAX_CONFIDENCE = 0.95 for epistemic humility)

**Memory Retrieval (Multi-signal scoring)**:
- Design: `docs/design/RETRIEVAL_DESIGN.md`
- Domain service: `src/domain/services/memory_retriever.py` (to implement)
- Strategy weights: `src/config/heuristics.py` (✅ complete: RETRIEVAL_STRATEGY_WEIGHTS)
- Database queries: Use pgvector for semantic search (embedding <=> operator)

**3-Stage Retrieval Pipeline**:
1. **Query Understanding**: Classify query intent → select retrieval strategy (factual_entity_focused, procedural, exploratory, temporal)
2. **Candidate Generation** (parallel):
   - Semantic: pgvector KNN search (top 50 candidates)
   - Entity-based: Exact entity_id matches (top 30)
   - Temporal: Recent memories in time window (top 30)
   - Summaries: Cross-session summaries (top 5, get 15% boost)
3. **Ranking & Selection**:
   - Score each candidate using strategy weights
   - Final score = weighted sum of 5 signals
   - Select top 15 memories fitting within max_context_tokens (3000)

**4 Retrieval Strategies (from heuristics.py)**:
```python
# Factual/Entity-Focused (when query is about specific entities)
"factual_entity_focused": {
    "semantic_similarity": 0.25, "entity_overlap": 0.40,  # Entity overlap dominates
    "temporal_relevance": 0.20, "importance": 0.10, "reinforcement": 0.05
}

# Procedural (when query asks "how to" or about processes)
"procedural": {
    "semantic_similarity": 0.45, "entity_overlap": 0.05,
    "temporal_relevance": 0.05, "importance": 0.15, "reinforcement": 0.30  # Reinforcement matters
}

# Exploratory (open-ended queries)
"exploratory": {
    "semantic_similarity": 0.35, "entity_overlap": 0.25,
    "temporal_relevance": 0.15, "importance": 0.20, "reinforcement": 0.05
}

# Temporal (time-specific queries like "what happened last week?")
"temporal": {
    "semantic_similarity": 0.20, "entity_overlap": 0.20,
    "temporal_relevance": 0.40,  # Temporal dominates
    "importance": 0.15, "reinforcement": 0.05
}
```

**Chat Pipeline (Primary API endpoint)**:
- API endpoint: `src/api/routes/chat.py` (to implement)
- Orchestration: Combines entity resolution → retrieval → LLM generation → memory creation
- Response model: `src/api/models/responses.py` (to implement, see API_DESIGN.md)

**Chat Pipeline Flow** (from API_DESIGN.md):
1. **Ingest**: Store user message as chat_event (immutable audit trail)
2. **Entity Resolution**: Extract mentions → resolve to canonical_entities (5-stage algorithm)
3. **Domain Enrichment**: Query domain DB for authoritative facts about resolved entities
4. **Memory Retrieval**: Fetch relevant memories (multi-signal scoring)
5. **Context Assembly**: Combine domain facts (40% of token budget) + memories (60%)
6. **LLM Generation**: Generate response with full context
7. **Memory Creation**: Extract episodic memory, possibly semantic facts
8. **Conflict Detection**: Check for contradictions with existing memories or domain DB
9. **Response**: Return answer with citations (which memories/domain facts were used)

**Context Window Token Budget Allocation** (from heuristics.py):
```python
# Total: max_context_tokens = 3000 (default in settings.py)
CONTEXT_DB_FACTS = 0.40      # 1200 tokens - Domain DB facts (authoritative)
CONTEXT_SUMMARIES = 0.20     # 600 tokens  - Memory summaries (high-level patterns)
CONTEXT_SEMANTIC = 0.20      # 600 tokens  - Semantic facts (user preferences/policies)
CONTEXT_EPISODIC = 0.15      # 450 tokens  - Recent episodic memories (specific events)
CONTEXT_PROCEDURAL = 0.05    # 150 tokens  - Procedural hints (how-to patterns)

# Token estimation: TOKENS_PER_CHAR = 0.25 (rough estimate: 4 chars per token)
```

**Priority Order for Context Assembly**:
1. Domain DB facts (correspondence truth) - always included first
2. Summaries (consolidated patterns) - high information density
3. Semantic facts (user-specific context)
4. Episodic memories (specific recent events)
5. Procedural hints (learned workflows)

**Domain Ontology Integration**:
- Design: `docs/design/DESIGN.md` (domain_ontology table)
- Purpose: Defines business relationship semantics (customer HAS orders, order REQUIRES product)
- Database model: `src/infrastructure/database/models.py` (✅ complete: DomainOntology)
- Example:
  ```python
  # Ontology record: customer HAS orders (1:many)
  {
    "from_entity_type": "customer",
    "relation_type": "has",
    "to_entity_type": "order",
    "cardinality": "1:many",
    "relation_semantics": "A customer can have multiple orders",
    "join_spec": {
      "from_table": "customers",
      "to_table": "orders",
      "join_on": "customers.customer_id = orders.customer_id"
    }
  }
  ```
- Usage: When user asks about a customer, automatically fetch related orders using ontology join specs
- Repository: `src/infrastructure/external/domain_db_connector.py` (to implement)

### Database Schema (10 Core Tables)

All models defined in `src/infrastructure/database/models.py`:

1. **chat_events**: Raw conversation audit trail (immutable)
2. **canonical_entities**: Entity layer with external_ref (customer ID, order ID, etc.)
3. **entity_aliases**: User-specific + global aliases for resolution
4. **episodic_memories**: Event summaries with entity coreference
5. **semantic_memories**: Facts (subject-predicate-object triples) with confidence + lifecycle
6. **procedural_memories**: Learned heuristics (Phase 2/3)
7. **memory_summaries**: Cross-session consolidation
8. **domain_ontology**: Business relationship semantics (customer HAS orders, etc.)
9. **memory_conflicts**: Conflict tracking for epistemic humility
10. **system_config**: Heuristic parameters (stored as JSONB)

**pgvector indexes**: All memory tables have `embedding vector(1536)` with IVFFlat indexes for semantic search.

## Critical Design Patterns

### Pattern 1: Passive vs Pre-Computed

**Passive Computation** (Preferred for Phase 1):
- Compute values on-demand during retrieval
- Example: Memory decay, current confidence, memory state
- Benefit: Simpler schema, no background jobs
- Trade-off: Slightly slower reads (negligible with proper indexing)

**Pre-Computed** (Only when necessary):
- Store computed values in database
- Example: Memory embeddings (expensive to compute, used frequently)
- Benefit: Faster retrieval for expensive operations
- Cost: Schema complexity, potential stale data

**When to use which**:
```python
# ✅ Passive - Decay computation
def get_current_confidence(memory: SemanticMemory) -> float:
    days_since_validation = (now - memory.last_validated_at).days
    return memory.confidence * math.exp(-days_since_validation * DECAY_RATE_PER_DAY)

# ✅ Pre-computed - Embeddings
async def create_semantic_memory(fact: str) -> SemanticMemory:
    embedding = await embedding_service.generate(fact)  # Expensive OpenAI call
    return SemanticMemory(fact=fact, embedding=embedding)  # Store for retrieval
```

### Pattern 2: JSONB vs Separate Table

**Use JSONB when**:
- Data is rarely queried independently (only needed with parent)
- Example: `entity_mentions` in episodic_memories - always retrieved with the episode
- Example: `confidence_factors` in semantic_memories - just metadata for debugging

**Use Separate Table when**:
- Need to query/filter/join independently
- Example: `entity_aliases` - queried during resolution without loading full entities
- Example: `canonical_entities` - referenced by many memories via foreign key

**From QUALITY_EVALUATION.md**:
> "Entity mentions stored as JSONB in episodic_memories is justified because:
> 1. They're always needed when retrieving the episode (never queried alone)
> 2. Coreference chains are episode-specific (no cross-episode queries)
> 3. Avoids 4-5 table joins on every retrieval"

### Pattern 3: Confidence Tracking and Epistemic Humility

**Core Principle**: The system never claims 100% certainty (MAX_CONFIDENCE = 0.95).

**Confidence Structure**:
```python
@dataclass(frozen=True)
class Confidence:
    value: float  # Overall confidence (0.0 to 0.95)
    factors: dict[str, float]  # Component breakdown
    # {
    #   "base": 0.7,           # Initial extraction confidence
    #   "reinforcement": 0.15,  # From validations
    #   "recency": -0.05,      # From decay
    #   "source": 0.05         # From consolidation boost
    # }
```

**Conflict Detection** (memory_conflicts table):
When retrieving contradictory information:
1. Detect: Check for same subject-predicate with different object_value
2. Log: Create memory_conflict record
3. Resolve:
   - Trust domain DB if conflict is memory_vs_db
   - Trust higher confidence if gap > 0.30
   - Trust recency if age gap > 60 days
   - Ask user if ambiguous
4. **Never silently ignore conflicts** - epistemic humility requires explicit acknowledgment

### Pattern 4: Memory Transformation Decision Logic

**When to Extract Semantic from Episodic**:
```python
# Heuristic: Extract if episodic contains subject-predicate-object triple about an entity
# Example episodic: "User asked about customer ACME's payment preferences"
# → Extract semantic: (customer:acme_123, "prefers", "net-30 payment terms")

if (
    episodic.event_type in ["statement", "correction", "confirmation"]
    and len(episodic.entities) > 0
    and contains_factual_claim(episodic.summary)
):
    extract_semantic_memory(episodic)
```

**Reinforcement vs New Memory Decision**:
```python
# Check if similar semantic memory exists
existing = await find_similar_semantic(
    subject=entity_id,
    predicate=predicate,
    semantic_similarity_threshold=0.85  # High threshold for "same fact"
)

if existing and confidence_gap < 0.30:
    # Reinforce existing memory
    existing.reinforcement_count += 1
    existing.confidence += get_reinforcement_boost(existing.reinforcement_count)
    existing.last_validated_at = now
else:
    # Create new memory (or supersede if conflict)
    if existing and confidence_gap >= 0.30:
        existing.status = "SUPERSEDED"
        existing.superseded_by_memory_id = new_memory.memory_id
    create_new_semantic_memory(...)
```

**Consolidation Triggers** (from LIFECYCLE_DESIGN.md):
```python
# Trigger consolidation when:
if (
    len(recent_episodic_memories) >= 10  # Min 10 episodic in window
    and len(distinct_sessions) >= 3      # Min 3 sessions
    and session_window <= 5              # Last 5 sessions
):
    # Extract patterns across episodes
    summary = await llm_consolidate(recent_episodic_memories)
    create_memory_summary(summary, source_data={
        "episodic_ids": [m.memory_id for m in recent_episodic_memories],
        "session_ids": distinct_sessions,
        "time_range": {"start": earliest.created_at, "end": latest.created_at}
    })
```

## Design Philosophy: Three Questions Framework

**Before adding any feature, table, field, or complexity, answer**:

1. **Which vision principle does this serve?** (If none, remove it. See `docs/vision/VISION.md`)
2. **Does this contribute enough to justify its cost?** (Cost = schema complexity, query complexity, maintenance)
3. **Is this the right phase for this complexity?** (Phase 1 = essential, Phase 2 = enhancements with data, Phase 3 = learning)

**Example application**:
- Procedural memories table: ✅ In vision (Layer 5), essential for system completeness → Keep
- Access count field: ❌ Useful for Phase 3 learning, not essential now → Defer
- Entity mentions table: ❌ Can use JSONB in episodic_memories, rarely queried alone → Inline with JSONB

**Key Vision Principles** (from VISION.md):

1. **Perfect Recall of Relevant Context** - Never forget what matters
   - Implemented via: Multi-signal retrieval, pgvector semantic search, entity-based lookup

2. **Deep Business Understanding** - Knows data, processes, relationships
   - Implemented via: Domain ontology integration, external_ref in canonical_entities, lazy entity loading

3. **Adaptive Learning** - Gets smarter with each conversation
   - Implemented via: Reinforcement (diminishing returns), consolidation, procedural memory extraction

4. **Epistemic Humility** - Admits uncertainty, never claims 100% confidence
   - Implemented via: Confidence tracking (max 0.95), memory_conflicts table, explicit provenance

5. **Explainable Reasoning** - Always traces reasoning to sources
   - Implemented via: source_memory_id, extracted_from_event_id, confidence_factors JSONB

6. **Continuous Improvement** - Each conversation makes future ones better
   - Implemented via: Episodic → Semantic transformation, consolidation, alias learning

See `docs/vision/DESIGN_PHILOSOPHY.md` for full guidance and case studies.

## Code Conventions

### Type Hints (Required - 100% coverage enforced)
```python
from typing import Optional, List
from datetime import datetime

async def resolve_entity(
    mention: str,
    user_id: str,
    context: ResolutionContext
) -> ResolutionResult:
    """All public functions must have type hints."""
    ...
```

### Immutable Value Objects
```python
from dataclasses import dataclass

@dataclass(frozen=True)  # Always frozen
class Confidence:
    value: float  # 0.0 to 1.0
    source: str
    factors: dict[str, float]

    def __post_init__(self):
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.value}")
```

### Domain Exceptions (Not HTTP exceptions)
```python
# domain/exceptions.py
class EntityNotFoundError(DomainException):
    """Raised when entity resolution fails."""
    def __init__(self, mention: str, context: str):
        self.mention = mention
        self.context = context
        super().__init__(f"Entity '{mention}' not found")

# API layer catches and converts to HTTP responses
# api/errors.py
@app.exception_handler(EntityNotFoundError)
async def handle_entity_not_found(request, exc):
    return JSONResponse(status_code=404, content={...})
```

### Repository Pattern (Ports & Adapters)
```python
# domain/ports/entity_repository.py
from abc import ABC, abstractmethod

class EntityRepositoryPort(ABC):
    """Port (interface) for entity data access."""

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[CanonicalEntity]:
        pass

# infrastructure/database/repositories/entity_repository.py
class PostgresEntityRepository(EntityRepositoryPort):
    """Adapter (implementation) for PostgreSQL."""

    async def get_by_id(self, entity_id: str) -> Optional[CanonicalEntity]:
        # SQLAlchemy queries here
        ...
        return self._to_domain(model)  # Convert DB model → Domain entity
```

### Heuristic Values (Never hardcode)
```python
# ❌ BAD - Hardcoded
def compute_decay(days: int) -> float:
    return math.exp(-days * 0.01)  # Magic number!

# ✅ GOOD - From config
from config.heuristics import DECAY_RATE_PER_DAY

def compute_decay(days: int) -> float:
    return math.exp(-days * DECAY_RATE_PER_DAY)
```

### Async Everything (I/O operations)
```python
# All database, LLM, and external API calls are async
async def retrieve_memories(query: str) -> List[Memory]:
    async with get_db_session() as session:
        result = await session.execute(select(...))
        return result.scalars().all()
```

### Structured Logging
```python
import structlog

logger = structlog.get_logger()

async def resolve_entity(mention: str, context: ResolutionContext) -> ResolutionResult:
    logger.info(
        "entity_resolution_started",
        mention=mention,
        user_id=context.user_id,
        session_id=context.session_id
    )

    try:
        result = await _resolve(mention, context)
        logger.info(
            "entity_resolution_completed",
            mention=mention,
            entity_id=result.entity_id,
            confidence=result.confidence,
            method=result.resolution_method
        )
        return result
    except AmbiguousEntityError as e:
        logger.warning(
            "entity_resolution_ambiguous",
            mention=mention,
            candidate_count=len(e.candidates)
        )
        raise
```

## Testing Strategy

**Test Pyramid**: 70% unit (fast, no I/O) | 20% integration (DB) | 10% E2E (full API)

### Unit Tests (Domain logic)
```python
# tests/unit/domain/test_entity_resolver.py
@pytest.mark.unit
@pytest.mark.asyncio
async def test_exact_match_returns_high_confidence():
    # Use mock repositories - no database
    mock_repo = MockEntityRepository()
    mock_repo.add_entity(entity_id="customer:acme_123", canonical_name="Acme Corporation")

    resolver = EntityResolver(entity_repo=mock_repo, embedding_service=None)
    context = ResolutionContext(user_id="user_1", ...)

    result = await resolver.resolve(mention="Acme Corporation", context=context)

    assert result.entity_id == "customer:acme_123"
    assert result.confidence == 1.0
    assert result.method == "exact_match"
```

### Integration Tests (Database)
```python
# tests/integration/test_entity_repository.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_retrieve_entity(test_db_session):
    repo = PostgresEntityRepository(test_db_session)
    entity = CanonicalEntity(
        entity_id="customer:test_123",
        entity_type="customer",
        canonical_name="Test Corp"
    )

    created = await repo.create(entity)
    retrieved = await repo.get_by_id("customer:test_123")

    assert retrieved.entity_id == "customer:test_123"
```

### Coverage Requirements
- Domain layer: 90% minimum (business logic is critical)
- API layer: 80% minimum
- Infrastructure: 70% minimum (tested via integration)
- Overall: 80% enforced in CI/CD (make check-all fails below threshold)

## Phase 1 Implementation Roadmap

**Current**: Week 0 complete (foundation ready)

**Next Steps** (see `docs/quality/PHASE1_ROADMAP.md` for week-by-week details):
- **Week 1-2**: Create initial migration with all 10 tables, seed system_config
- **Week 3-4**: Implement entity resolution (5-stage algorithm)
- **Week 5-6**: Implement memory transformation pipeline (chat → episodic → semantic)
- **Week 7-8**: Implement retrieval system (multi-signal scoring)
- **Week 9**: Implement API endpoints (chat, memories, entities, health)
- **Week 10-12**: Testing, optimization, deployment

## Critical Files Reference

When implementing features, always reference these design documents:

- **Database Schema**: `docs/design/DESIGN.md` - All 10 tables with field justifications
- **Heuristic Values**: `docs/reference/HEURISTICS_CALIBRATION.md` - All 43 parameters (already in `src/config/heuristics.py`)
- **API Contracts**: `docs/design/API_DESIGN.md` - Request/response models for all endpoints
- **Entity Resolution**: `docs/design/ENTITY_RESOLUTION_DESIGN.md` - 5-stage algorithm specification
- **Memory Lifecycle**: `docs/design/LIFECYCLE_DESIGN.md` - State transitions, decay, reinforcement
- **Retrieval**: `docs/design/RETRIEVAL_DESIGN.md` - Multi-signal scoring formula
- **Architecture**: `ARCHITECTURE.md` - Hexagonal architecture, DDD patterns, testing strategy
- **Development**: `DEVELOPMENT_GUIDE.md` - Setup, workflows, troubleshooting

## Performance Targets (Phase 1)

| Operation | P95 Target | Implementation Note |
|-----------|------------|---------------------|
| Semantic search | <50ms | pgvector with IVFFlat index |
| Entity resolution | <30ms | Indexed lookups on canonical_name |
| Full retrieval | <100ms | Multi-signal scoring (parallel candidate generation) |
| Chat endpoint | <300ms | End-to-end (includes LLM call which dominates) |

## Common Pitfalls to Avoid

1. **Don't hardcode heuristic values** - Always use `config/heuristics.py`
   - Example: `DECAY_RATE_PER_DAY = 0.01` is in heuristics.py with calibration notes
   - These values are marked for Phase 2 tuning with real data

2. **Don't import infrastructure in domain layer** - Use ports (ABC interfaces)
   - Domain service `EntityResolver` depends on `EntityRepositoryPort` (abstract)
   - Infrastructure provides `PostgresEntityRepository` implementation
   - Dependency injection happens at API layer

3. **Don't skip type hints** - mypy strict mode enforced (100% coverage required)
   - All public functions must have full type signatures
   - Use `from typing import Optional, List, Dict` for Python 3.9 compatibility

4. **Don't create background jobs** - Use passive computation (compute on-demand)
   - NO cron jobs for decay updates
   - NO background workers for state transitions
   - Compute current confidence during retrieval, only write on explicit events

5. **Don't add features without Three Questions justification** - Document which vision principle it serves
   - From QUALITY_EVALUATION.md: "Access count field deferred to Phase 3 - not essential for Phase 1 MVP"
   - Ask: Which vision principle? Does it justify cost? Is this the right phase?

6. **Don't use blocking I/O** - All database/LLM calls must be async
   - Use `async with get_db_session()` for database operations
   - Use `await embedding_service.generate(text)` for OpenAI calls
   - FastAPI endpoints are all `async def`

7. **Don't test infrastructure in unit tests** - Use mocks; save DB tests for integration tests
   - Unit tests: Mock repositories, test domain logic only
   - Integration tests: Real database, test repository implementations
   - Test pyramid: 70% unit, 20% integration, 10% E2E

8. **Don't assume heuristic values are final** - All 43 parameters need Phase 2 calibration
   - From QUALITY_EVALUATION.md: "High-risk heuristics needing early validation: FUZZY_MATCH_THRESHOLD (0.70), DISAMBIGUATION_MIN_CONFIDENCE_GAP (0.15)"
   - Track actual performance metrics to tune in Phase 2

9. **Don't over-normalize the schema** - Inline with JSONB when data isn't queried independently
   - Example: Entity mentions in episodic_memories uses JSONB (not separate table)
   - Reason: Always retrieved with parent episode, never queried alone

10. **Don't silently ignore conflicts** - Epistemic humility requires explicit conflict tracking
    - Always create `memory_conflict` record when detecting contradictions
    - Never auto-resolve without logging the decision and reasoning
    - Provide user visibility into "why the system chose this answer"

## Environment Setup

Required environment variables (see `.env.example`):
```bash
# Database
DATABASE_URL=postgresql+asyncpg://memoryuser:memorypass@localhost:5432/memorydb

# OpenAI (for embeddings + extraction)
OPENAI_API_KEY=sk-...your-key...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # 1536 dimensions
OPENAI_LLM_MODEL=gpt-4-turbo-preview

# API
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # json for production, text for development
```

## Commit Message Convention

Format: `<type>(<scope>): <subject>`

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

Examples:
```
feat(entity-resolution): implement five-stage resolution algorithm
fix(retrieval): correct temporal decay calculation
test(lifecycle): add tests for AGING state transition
docs(api): add phase tags to endpoint descriptions
```

## When to Reference Full Documentation

- **Before implementing a subsystem**: Read the relevant design doc in `docs/design/`
- **Before adding a field to a table**: Check `docs/design/DESIGN.md` for field justifications
- **Before changing a heuristic value**: Check `docs/reference/HEURISTICS_CALIBRATION.md` for Phase 2 tuning requirements
- **When unsure about complexity**: Apply Three Questions Framework from `docs/vision/DESIGN_PHILOSOPHY.md`
- **When implementing API endpoint**: Check `docs/design/API_DESIGN.md` for contracts

## Quick Reference: Make Commands

```bash
make setup          # First-time setup (install + docker + migrate)
make run            # Start dev server
make test           # Run all tests
make test-unit      # Fast unit tests only
make test-cov       # Tests with HTML coverage report
make check-all      # All quality checks (lint + typecheck + coverage)
make lint-fix       # Auto-fix linting issues
make format         # Format all code
make db-migrate     # Apply migrations
make db-shell       # Open psql shell
make clean          # Remove caches
make stats          # Show project statistics
```
