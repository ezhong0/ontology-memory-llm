# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

**Ontology-Aware Memory System**: A sophisticated memory system for LLM agents that transforms raw conversations into structured, retrievable knowledge with domain ontology integration.

**Memory Pipeline**: `Raw Chat → Episodic Memory → Semantic Memory → Procedural Memory → Summaries`

**Current Status**: Design v2.0 complete (ground-up redesign). Ready for Phase 1 implementation (8 weeks).

**Design Approach**: Vision-driven architecture with surgical LLM integration (deterministic where it excels, LLM only where it adds clear value)

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

### The Layered Memory Architecture

From DESIGN.md v2.0, the system implements 6 layers of memory transformation:

```
┌────────────────────────────────────────────────────────────┐
│ Layer 6: CONSOLIDATED SUMMARIES (memory_summaries)        │
│          Cross-session synthesis, entity profiles          │
│          Vision: Forgetting through consolidation          │
└────────────────────────────────────────────────────────────┘
                         ↑ distills
┌────────────────────────────────────────────────────────────┐
│ Layer 5: PROCEDURAL MEMORY (procedural_memories)          │
│          Learned heuristics: "When X, also Y"             │
│          Vision: Learning from interaction patterns        │
└────────────────────────────────────────────────────────────┘
                         ↑ emerges from
┌────────────────────────────────────────────────────────────┐
│ Layer 4: SEMANTIC MEMORY (semantic_memories)              │
│          Abstracted facts with lifecycle                   │
│          Vision: Contextual truth, epistemic humility      │
└────────────────────────────────────────────────────────────┘
                         ↑ extracted from
┌────────────────────────────────────────────────────────────┐
│ Layer 3: EPISODIC MEMORY (episodic_memories)              │
│          Events with meaning: "What happened"              │
│          Vision: Foundation for learning                   │
└────────────────────────────────────────────────────────────┘
                         ↑ interprets
┌────────────────────────────────────────────────────────────┐
│ Layer 2: ENTITY RESOLUTION (canonical_entities, aliases)  │
│          Text mentions → canonical entities                │
│          Vision: Solving problem of reference              │
└────────────────────────────────────────────────────────────┘
                         ↑ links
┌────────────────────────────────────────────────────────────┐
│ Layer 1: RAW EVENTS (chat_events)                         │
│          Immutable audit trail of conversations            │
│          Vision: Provenance, explainability                │
└────────────────────────────────────────────────────────────┘
                         ↑ queries
┌────────────────────────────────────────────────────────────┐
│ Layer 0: DOMAIN DATABASE (external)                       │
│          Authoritative truth about business                │
│          Vision: Correspondence truth                      │
└────────────────────────────────────────────────────────────┘
```

**Information Flow**:
- **Abstraction (up)**: Raw events → Episodes → Facts → Patterns → Summaries
- **Grounding (down)**: Queries start at DB, enrich with memory layers

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

### Database Schema (10 Core Tables)

All models defined in `src/infrastructure/database/models.py`:

| Layer | Table | Vision Principle Served |
|-------|-------|------------------------|
| 1 | `chat_events` | Provenance, explainability |
| 2 | `canonical_entities` | Problem of reference |
| 2 | `entity_aliases` | Identity across time, learning |
| 3 | `episodic_memories` | Events with meaning, learning substrate |
| 4 | `semantic_memories` | Contextual truth, epistemic humility, forgetting |
| 5 | `procedural_memories` | Learning from patterns |
| 6 | `memory_summaries` | Graceful forgetting through consolidation |
| Support | `domain_ontology` | Ontology-awareness |
| Support | `memory_conflicts` | Epistemic humility |
| Support | `system_config` | Flexibility |

**Every table directly serves the vision. No table is "nice to have."**

**pgvector indexes**: All memory tables have `embedding vector(1536)` with IVFFlat indexes for semantic search.

## Key Subsystems & Algorithms

### 1. Entity Resolution (Hybrid Approach)

**Design**: `docs/design/DESIGN.md` (Section: Entity Resolution Algorithm)

**Approach**: **Deterministic fast path (95%) + LLM coreference (5%)**

**Algorithm**:

```python
async def resolve_entity(mention: str, user_id: str, context: ConversationContext) -> ResolutionResult:
    """
    Hybrid entity resolution: deterministic for 95%, LLM for coreference (5%).

    Vision alignment: Fast path for efficiency, LLM only where semantic
    understanding is genuinely needed (pronouns, contextual references).
    """

    # ═══════════════════════════════════════════════════════════
    # FAST PATH: Deterministic (handles 95% of cases)
    # ═══════════════════════════════════════════════════════════

    # Stage 1: Exact match on canonical name
    exact = await db.fetchrow("""
        SELECT entity_id, 1.0 as confidence
        FROM canonical_entities
        WHERE canonical_name = $1
    """, mention)
    if exact:
        return ResolutionResult(entity_id=exact['entity_id'], confidence=1.0, method='exact')

    # Stage 2: Known alias (user-specific first, then global)
    alias = await db.fetchrow("""
        SELECT canonical_entity_id, confidence
        FROM entity_aliases
        WHERE alias_text = $1 AND (user_id = $2 OR user_id IS NULL)
        ORDER BY user_id NULLS LAST, confidence DESC
        LIMIT 1
    """, mention, user_id)
    if alias and alias['confidence'] > 0.85:
        return ResolutionResult(entity_id=alias['canonical_entity_id'],
                               confidence=alias['confidence'],
                               method='alias')

    # Stage 3: Fuzzy match using pg_trgm
    fuzzy = await db.fetch("""
        SELECT ce.entity_id, ce.canonical_name, similarity(ea.alias_text, $1) as score
        FROM canonical_entities ce
        JOIN entity_aliases ea ON ea.canonical_entity_id = ce.entity_id
        WHERE similarity(ea.alias_text, $1) > 0.7
        ORDER BY score DESC
        LIMIT 5
    """, mention)

    if len(fuzzy) == 1 and fuzzy[0]['score'] > 0.85:
        await learn_alias(mention, fuzzy[0]['entity_id'], user_id, 'fuzzy', fuzzy[0]['score'])
        return ResolutionResult(entity_id=fuzzy[0]['entity_id'],
                               confidence=fuzzy[0]['score'],
                               method='fuzzy')

    if len(fuzzy) > 1:
        # Need user disambiguation
        return DisambiguationRequired(candidates=fuzzy)

    # ═══════════════════════════════════════════════════════════
    # LLM PATH: Coreference resolution (handles 5% of cases)
    # ═══════════════════════════════════════════════════════════

    if is_coreference_candidate(mention):  # "they", "it", "them", "the customer"
        candidates = context.recent_entities
        if not candidates:
            return ResolutionResult(entity_id=None, confidence=0.0, method='no_candidates')

        # Use LLM for coreference resolution
        llm_result = await resolve_coreference_llm(
            mention=mention,
            candidates=candidates,
            conversation_history=context.recent_messages
        )

        if llm_result.confidence > 0.7:
            await learn_alias(mention, llm_result.entity_id, user_id,
                            'coreference', llm_result.confidence)

        return ResolutionResult(entity_id=llm_result.entity_id,
                               confidence=llm_result.confidence,
                               method='llm_coreference',
                               reasoning=llm_result.reasoning)

    # Stage 4: Search domain database (lazy entity creation)
    domain_matches = await search_domain_database(mention, limit=3)
    if domain_matches:
        entity = await ensure_canonical_entity(domain_matches[0])
        await learn_alias(mention, entity.entity_id, user_id, 'domain_db', 0.85)
        return ResolutionResult(entity_id=entity.entity_id, confidence=0.85, method='domain_db')

    return ResolutionResult(entity_id=None, confidence=0.0, method='not_found')
```

**Why This Design**:
- **Deterministic for 95%**: Exact, alias, and fuzzy matching use SQL/pg_trgm (fast, reliable)
- **LLM only for coreference**: Pronouns need conversation context to resolve
- **Self-improving**: High-confidence resolutions create aliases, moving to fast path
- **Cost**: $0.00015 per resolution (only 5% of cases use LLM)

**Key Files**:
- Domain service: `src/domain/services/entity_resolver.py` (to implement)
- Repository port: `src/domain/ports/entity_repository.py` (to implement)
- Repository impl: `src/infrastructure/database/repositories/entity_repository.py` (to implement)
- Database models: `src/infrastructure/database/models.py` (✅ complete)

### 2. Memory Extraction (Pattern Detection + LLM Semantic Parsing)

**Design**: `docs/design/DESIGN.md` (Section: Memory Extraction Algorithm)

**Approach**: **Deterministic event classification + LLM triple extraction**

**Algorithm**:

```python
async def extract_memories(event: ChatEvent, entities: List[Entity]) -> ExtractionResult:
    """
    Extract semantic facts from episodic events.

    Vision alignment: Deterministic patterns for event classification,
    LLM for semantic parsing (genuinely hard with rules).
    """

    # ═══════════════════════════════════════════════════════════
    # DETERMINISTIC: Event type classification
    # ═══════════════════════════════════════════════════════════

    event_type = classify_event_type(event.content)
    # Patterns: "?" = question, "remember" = explicit statement, etc.

    if event_type not in ['statement', 'correction', 'explicit_preference']:
        # Don't extract from questions, commands, confirmations
        return ExtractionResult(semantic_memories=[])

    # ═══════════════════════════════════════════════════════════
    # LLM: Semantic triple extraction
    # ═══════════════════════════════════════════════════════════

    extraction = await extract_triples_llm(
        text=event.content,
        entities=entities,
        event_type=event_type
    )

    semantic_memories = []
    for triple in extraction.triples:
        # Check for existing memory (same subject + predicate)
        existing = await db.fetchrow("""
            SELECT memory_id, confidence, reinforcement_count, object_value
            FROM semantic_memories
            WHERE user_id = $1
              AND subject_entity_id = $2
              AND predicate = $3
              AND status = 'active'
        """, event.user_id, triple.subject, triple.predicate)

        if existing:
            if values_match(existing['object_value'], triple.object_value):
                # REINFORCE: Increase confidence
                await reinforce_memory(existing['memory_id'])
            else:
                # CONFLICT: Log and decide resolution
                await handle_memory_conflict(existing, triple, event)
        else:
            # CREATE: New semantic memory
            memory = await create_semantic_memory(triple, event)
            semantic_memories.append(memory)

    return ExtractionResult(semantic_memories=semantic_memories)
```

**Why LLM Here**: Parsing "Acme prefers Friday deliveries and NET30 terms" into structured triples is genuinely hard with patterns.

**Cost**: $0.002 per extraction (only for statements, not all messages)

### 3. Multi-Signal Retrieval (Deterministic Scoring)

**Design**: `docs/design/DESIGN.md` (Section: Multi-Signal Retrieval)

**Approach**: **Deterministic formula (NO LLM)**

**Algorithm**:

```python
def score_memory_relevance(memory: Memory, query: Query) -> float:
    """
    Multi-signal relevance scoring using weighted formula.

    Vision alignment: Combines semantic similarity, entity overlap, recency,
    importance, and reinforcement to approximate "what would a knowledgeable
    human consider relevant here?"

    NO LLM: Would be too slow (need to score 100+ candidates in <100ms)
    """
    weights = get_config('multi_signal_weights')

    # Signal 1: Semantic similarity (cosine)
    semantic_score = 1 - cosine_distance(memory.embedding, query.embedding)

    # Signal 2: Entity overlap (Jaccard)
    entity_score = jaccard(memory.entities, query.entities)

    # Signal 3: Recency (exponential decay)
    age_days = (now() - memory.created_at).days
    half_life = 30 if memory.type == 'episodic' else 90
    recency_score = exp(-age_days * ln(2) / half_life)

    # Signal 4: Importance (stored)
    importance_score = memory.importance

    # Signal 5: Reinforcement (for semantic memories)
    if hasattr(memory, 'reinforcement_count'):
        reinforce_score = min(1.0, memory.reinforcement_count / 5)
    else:
        reinforce_score = 0.5

    # Weighted combination
    relevance = (
        weights['semantic'] * semantic_score +
        weights['entity'] * entity_score +
        weights['recency'] * recency_score +
        weights['importance'] * importance_score +
        weights['reinforcement'] * reinforce_score
    )

    # Apply confidence penalty (passive decay)
    if hasattr(memory, 'confidence'):
        effective_confidence = calculate_effective_confidence(memory)
        relevance *= effective_confidence

    return relevance
```

**Why NO LLM**:
- Need to score 100+ candidates in <100ms
- LLM would take 20+ seconds (200x slower)
- Formula works well and is deterministic
- Can tune weights from usage data (Phase 2)

**Retrieval Strategy Weights** (from `src/config/heuristics.py`):

```python
# Default weights for multi-signal scoring
"multi_signal_weights": {
    "semantic": 0.4,        # Semantic similarity (cosine)
    "entity": 0.25,         # Entity overlap (Jaccard)
    "recency": 0.2,         # Temporal relevance (exponential decay)
    "importance": 0.1,      # Stored importance
    "reinforcement": 0.05   # Validation count
}
```

### 4. Conflict Detection (Deterministic + LLM Semantic)

**Design**: `docs/design/DESIGN.md` (Section: Conflict Detection)

**Approach**: **Deterministic pre-filtering (99%) + LLM semantic conflicts (1%)**

**Algorithm**:

```python
async def detect_conflicts(new_memory: SemanticMemory):
    """
    Detect conflicts between memories and database facts.

    Vision alignment: Deterministic for obvious conflicts (same predicate),
    LLM only for semantic conflicts across different predicates.
    """

    # ═══════════════════════════════════════════════════════════
    # DETERMINISTIC: Same predicate conflicts (99% of conflicts)
    # ═══════════════════════════════════════════════════════════

    existing = await db.fetch("""
        SELECT memory_id, object_value, confidence, last_validated_at
        FROM semantic_memories
        WHERE user_id = $1
          AND subject_entity_id = $2
          AND predicate = $3
          AND status = 'active'
    """, new_memory.user_id, new_memory.subject_entity_id, new_memory.predicate)

    for mem in existing:
        if not values_match(mem['object_value'], new_memory.object_value):
            # Direct conflict: same predicate, different values
            await log_conflict(
                conflict_type='memory_vs_memory',
                memories=[mem['memory_id'], new_memory.memory_id],
                resolution_strategy='trust_recent'
            )

    # Check against domain database
    db_value = await query_domain_for_predicate(
        new_memory.subject_entity_id,
        new_memory.predicate
    )

    if db_value and not values_match(db_value, new_memory.object_value):
        # Memory vs DB conflict
        await log_conflict(
            conflict_type='memory_vs_db',
            memory_id=new_memory.memory_id,
            db_source=db_value.source,
            resolution_strategy='trust_db'
        )

    # ═══════════════════════════════════════════════════════════
    # LLM: Semantic conflicts across predicates (1% of conflicts)
    # ═══════════════════════════════════════════════════════════

    # Check if new memory semantically conflicts with existing memories
    # Example: "prefers email" vs "hates electronic communication"
    related_memories = await db.fetch("""
        SELECT memory_id, predicate, object_value
        FROM semantic_memories
        WHERE user_id = $1
          AND subject_entity_id = $2
          AND status = 'active'
          AND predicate != $3
    """, new_memory.user_id, new_memory.subject_entity_id, new_memory.predicate)

    if related_memories:
        semantic_conflicts = await detect_semantic_conflicts_llm(
            new_memory=new_memory,
            existing_memories=related_memories
        )

        for conflict in semantic_conflicts:
            await log_conflict(
                conflict_type='semantic_conflict',
                memory_ids=[new_memory.memory_id, conflict.memory_id],
                reasoning=conflict.reasoning,
                resolution_strategy='ask_user'
            )
```

**Why LLM Only for Semantic**:
- 99% of conflicts are obvious (same predicate, different values)
- LLM only for edge cases: "prefers email" vs "dislikes electronic communication"
- Cost: $0.00002 average (1% × $0.002)

### 5. Consolidation (LLM Synthesis)

**Design**: `docs/design/DESIGN.md` (Section: Consolidation Algorithm)

**Approach**: **LLM synthesis (Essential)**

**Algorithm**:

```python
async def consolidate_memories(user_id: str, scope: ConsolidationScope) -> MemorySummary:
    """
    Consolidate episodic and semantic memories into summary.

    Vision alignment: This is exactly what LLMs excel at - reading multiple
    memories and synthesizing coherent summaries.
    """

    # Fetch memories to consolidate
    episodic = await db.fetch("""
        SELECT summary, entities, created_at
        FROM episodic_memories
        WHERE user_id = $1 AND {scope.filter}
        ORDER BY created_at DESC
    """, user_id)

    semantic = await db.fetch("""
        SELECT predicate, object_value, confidence, reinforcement_count
        FROM semantic_memories
        WHERE user_id = $1 AND {scope.filter} AND status = 'active'
        ORDER BY confidence DESC, reinforcement_count DESC
    """, user_id)

    # Use LLM for synthesis
    summary = await synthesize_summary_llm(
        episodic_memories=episodic,
        semantic_memories=semantic,
        scope=scope
    )

    # Store summary
    summary_id = await db.fetchrow("""
        INSERT INTO memory_summaries (
            user_id, scope_type, scope_identifier,
            summary_text, key_facts, source_data,
            confidence, embedding
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING summary_id
    """, user_id, scope.type, scope.identifier,
         summary.text, summary.key_facts, summary.source_data,
         summary.confidence, await embed(summary.text))

    # Boost confidence of confirmed facts
    for fact_id in summary.confirmed_memory_ids:
        await db.execute("""
            UPDATE semantic_memories
            SET confidence = LEAST(0.95, confidence + 0.1),
                last_validated_at = now()
            WHERE memory_id = $1
        """, fact_id)

    return summary
```

**Why LLM Essential**: Reading 20+ memories and synthesizing coherent summary is exactly what LLMs excel at.

## Surgical LLM Integration Summary

Based on the principle: **Use LLMs where they add clear value, deterministic systems where they excel**

| Component | Approach | Rationale | Cost per Use |
|-----------|----------|-----------|--------------|
| **Entity Resolution** | Deterministic (95%) + LLM coreference (5%) | pg_trgm excellent for fuzzy matching. Only pronouns need context. | $0.00015 avg |
| **Memory Extraction** | Pattern classification + LLM triple parsing | Event types are pattern-matchable. Semantic parsing genuinely needs LLM. | $0.002 (statements only) |
| **Query Understanding** | Pattern-based (90%) + LLM fallback (10%) | Simple patterns work most of time. LLM for compound/ambiguous queries. | $0.0001 avg |
| **Retrieval Scoring** | Deterministic formula (100%) | Must be fast (<100ms). Formula works well. NO LLM. | $0 |
| **Conflict Detection** | Deterministic (99%) + LLM semantic (1%) | Most conflicts are obvious. LLM only for cross-predicate semantic conflicts. | $0.00002 avg |
| **Consolidation** | LLM synthesis (100%) | This is what LLMs excel at. Reading and synthesizing summaries. | $0.005 (periodic) |

**Average cost per conversational turn**: ~$0.002

**At scale** (1,000 users × 50 turns/day):
- 50,000 turns/day
- Cost: $100/day = **$3,000/month**

**Comparison to alternatives**:
- Pure deterministic: $0/month, but 60-70% accuracy on hard cases
- Pure LLM: $15,000/month, but 90%+ accuracy
- **Surgical (this design)**: $3,000/month, 85-90% accuracy ✅

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

**Passive Decay Example**:
```python
def calculate_effective_confidence(memory: SemanticMemory) -> float:
    """
    Passive decay: compute on-demand, not pre-computed.
    Philosophy: No background jobs, always accurate.
    """
    config = get_config('decay')
    decay_rate = config['default_rate_per_day']

    days_since_validation = (now() - memory.last_validated_at).days

    # Exponential decay
    effective_conf = memory.confidence * exp(-days_since_validation * decay_rate)

    return max(0.0, min(1.0, effective_conf))
```

### Pattern 2: JSONB vs Separate Table

**Use JSONB when**:
- Data is rarely queried independently (only needed with parent)
- Example: `entities` in episodic_memories - always retrieved with the episode
- Example: `confidence_factors` in semantic_memories - just metadata for explainability

**Use Separate Table when**:
- Need to query/filter/join independently
- Example: `entity_aliases` - queried during resolution without loading full entities
- Example: `canonical_entities` - referenced by many memories via foreign key

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

### Pattern 4: Lazy Entity Creation

**Philosophy**: Entities are NOT pre-loaded. Create on-demand when first mentioned.

**Process**:
1. User mentions "Acme Corporation"
2. Entity resolution fails (not in canonical_entities)
3. Query domain database (customers table) for "Acme Corporation"
4. Create canonical_entity with external_ref pointing to customer record
5. Create alias for "Acme Corporation" → entity_id
6. Resolve future mentions via fast path

**Example**:
```python
async def ensure_canonical_entity(domain_match: DomainEntity) -> CanonicalEntity:
    """
    Lazy entity creation: Create canonical entity from domain database match.
    """
    entity_id = f"{domain_match.type}:{uuid4()}"

    entity = await db.fetchrow("""
        INSERT INTO canonical_entities (
            entity_id, entity_type, canonical_name, external_ref, properties
        ) VALUES ($1, $2, $3, $4, $5)
        RETURNING *
    """, entity_id, domain_match.type, domain_match.name,
         {"table": domain_match.source_table, "id": domain_match.id},
         domain_match.properties)

    # Create initial alias
    await create_alias(entity_id, domain_match.name, 'domain_db', confidence=1.0)

    return CanonicalEntity(**entity)
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

**Duration**: 8 weeks (2 months)

**Structure**: 4 phases, week-by-week breakdown in `docs/quality/PHASE1_ROADMAP.md`

### Phase 1A: Foundation (Week 1-2)
**Tables**: chat_events, canonical_entities, entity_aliases, system_config, domain_ontology
**Capabilities**: Store conversations, Entity resolution (hybrid algorithm), Basic domain DB queries
**Deliverable**: Can store events and resolve entities

### Phase 1B: Memory Core (Week 3-4)
**Add**: episodic_memories, semantic_memories
**Capabilities**: Create episodic memories, Extract semantic facts (with LLM), Reinforce, Basic retrieval
**Deliverable**: Can remember and retrieve facts

### Phase 1C: Intelligence (Week 5-6)
**Add**: memory_conflicts
**Capabilities**: Multi-signal retrieval scoring, Conflict detection, Passive decay, Ontology traversal
**Deliverable**: Can reason about business relationships and handle uncertainty

### Phase 1D: Learning (Week 7-8)
**Add**: procedural_memories, memory_summaries
**Capabilities**: Pattern detection (basic), Consolidation, Complete lifecycle, API endpoints
**Deliverable**: Full vision implementation, ready for production

## Performance Targets (Phase 1)

| Operation | P95 Target | Implementation Note |
|-----------|------------|---------------------|
| Entity resolution (fast path) | <50ms | Indexed lookups, pg_trgm |
| Entity resolution (LLM path) | <300ms | LLM coreference (5% of cases) |
| Semantic search | <50ms | pgvector with IVFFlat index |
| Multi-signal scoring | <100ms | Deterministic formula |
| Chat endpoint | <800ms | End-to-end (includes LLM generation) |

## Common Pitfalls to Avoid

1. **Don't hardcode heuristic values** - Always use `config/heuristics.py`

2. **Don't import infrastructure in domain layer** - Use ports (ABC interfaces)

3. **Don't skip type hints** - mypy strict mode enforced (100% coverage required)

4. **Don't create background jobs** - Use passive computation (compute on-demand)

5. **Don't add features without Three Questions justification** - Document which vision principle it serves

6. **Don't use blocking I/O** - All database/LLM calls must be async

7. **Don't test infrastructure in unit tests** - Use mocks; save DB tests for integration tests

8. **Don't assume heuristic values are final** - All parameters need Phase 2 calibration

9. **Don't over-normalize the schema** - Inline with JSONB when data isn't queried independently

10. **Don't silently ignore conflicts** - Epistemic humility requires explicit conflict tracking

11. **Don't use LLM when deterministic works** - Follow surgical LLM integration principle

12. **Don't pre-compute when passive works** - Compute decay/confidence on-demand

## Critical Files Reference

When implementing features, always reference these design documents:

- **Core Design**: `docs/design/DESIGN.md` - Ground-up redesign (v2.0), all algorithms, complete specifications
- **Roadmap**: `docs/quality/PHASE1_ROADMAP.md` - 8-week implementation plan with detailed tasks
- **Vision**: `docs/vision/VISION.md` - Philosophical foundation, core principles
- **Philosophy**: `docs/vision/DESIGN_PHILOSOPHY.md` - Three Questions Framework, decision criteria
- **Heuristics**: `docs/reference/HEURISTICS_CALIBRATION.md` - All 43 parameters (in `src/config/heuristics.py`)
- **API Contracts**: `docs/design/API_DESIGN.md` - Request/response models for all endpoints
- **Lifecycle**: `docs/design/LIFECYCLE_DESIGN.md` - State transitions, decay, reinforcement
- **Retrieval**: `docs/design/RETRIEVAL_DESIGN.md` - Multi-signal scoring formula
- **Architecture**: `docs/ARCHITECTURE.md` - Hexagonal architecture, DDD patterns
- **Development**: `docs/DEVELOPMENT_GUIDE.md` - Setup, workflows, troubleshooting

## Environment Setup

Required environment variables (see `.env.example`):
```bash
# Database
DATABASE_URL=postgresql+asyncpg://memoryuser:memorypass@localhost:5432/memorydb

# OpenAI (for embeddings + extraction)
OPENAI_API_KEY=sk-...your-key...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # 1536 dimensions
OPENAI_LLM_MODEL=gpt-4o  # For extraction quality

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
feat(entity-resolution): implement hybrid resolution algorithm with LLM coreference
fix(retrieval): correct passive decay calculation
test(lifecycle): add tests for confidence reinforcement
docs(design): update DESIGN.md with surgical LLM approach
```

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

## Design Evolution History

This system has undergone a comprehensive ground-up redesign (v2.0). See `docs/design/ARCHIVE_DESIGN_EVOLUTION.md` for the complete evolution history from initial exploration through surgical LLM approach to the current vision-driven architecture.

**Key learnings**:
- Start from vision, not from solution
- Surgical over blanket LLM use
- Justify every piece of complexity
- Iteration is essential
- Documentation serves implementation

**Current design** (v2.0) represents the culmination of this iterative refinement process, fully grounded in vision principles with explicit justification for every design decision.
