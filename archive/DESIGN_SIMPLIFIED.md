# Simplified System Design - Essential Architecture

## Design Philosophy: Simplicity First

**Core Principle**: Build the **minimum viable system** that embodies the vision. Avoid premature optimization and speculative features.

**What's Essential**:
1. Store conversations (raw events)
2. Extract and link entities (identity resolution)
3. Create memories with confidence (episodic → semantic)
4. Retrieve with multiple signals (hybrid search)
5. Ground in domain DB (ontology-aware queries)
6. Consolidate over time (summaries)

**What's Deferred**:
- Procedural memory (emergent patterns) → Phase 2
- Meta-memory (learning decay rates) → Phase 3
- Extraction pattern learning → Phase 3
- Detailed tracking tables → Can add later if needed

---

## Storage Choice: SQL vs NoSQL

### Option 1: Postgres + pgvector (Recommended)

**Pros**:
- **Strong consistency**: ACID transactions for memory updates
- **Relational power**: Easy ontology traversal (joins across domain tables)
- **pgvector maturity**: Battle-tested vector extension
- **JSONB flexibility**: Schema evolution where needed
- **Cost**: Free, self-hosted

**Cons**:
- **Scaling**: Vertical scaling primarily (but fine for <1M memories)
- **Learning curve**: SQL + vector queries

**When to use**: You need **transactional consistency** and **relational queries** (our case).

### Option 2: MongoDB + Vector Search

**Pros**:
- **Document model**: Memories are naturally documents
- **Schema flexibility**: Easy to evolve structure
- **Horizontal scaling**: Sharding built-in
- **Native JSON**: No JSONB conversion

**Cons**:
- **Joins are hard**: Ontology traversal requires application logic
- **No foreign keys**: Data integrity enforced in app
- **Transactions limited**: Multi-document transactions exist but complex
- **Vector search newer**: Less mature than pgvector

**When to use**: You prioritize **flexibility** and **horizontal scale** over **relational integrity**.

### Option 3: Hybrid (Postgres + Pinecone/Weaviate)

**Pros**:
- **Best of both**: Relational DB + specialized vector DB
- **Vector performance**: Optimized for similarity search
- **Independent scaling**: Scale vector layer separately

**Cons**:
- **Complexity**: Two databases to manage
- **Consistency challenges**: Keep embeddings in sync
- **Cost**: Pinecone has usage costs

**When to use**: You have **massive scale** (millions of vectors) and need **extreme vector performance**.

### Decision: Postgres + pgvector

**Rationale**: For this system (business context, ontology traversal, consistency needs, reasonable scale), Postgres is the right choice. JSONB gives us flexibility without sacrificing relational power.

---

## Simplified Schema: Core Tables Only

### 1. Raw Events (Immutable Audit Trail)

```sql
CREATE TABLE app.chat_events (
  event_id BIGSERIAL PRIMARY KEY,
  session_id UUID NOT NULL,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB,  -- {intent, entities_mentioned, language}
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_session ON app.chat_events(session_id);
CREATE INDEX idx_events_user_time ON app.chat_events(user_id, created_at DESC);
```

**Philosophy**: Everything stems from events. Keep them immutable.

### 2. Entity Resolution

```sql
CREATE TABLE app.entities (
  entity_id TEXT PRIMARY KEY,  -- "customer:uuid" format
  entity_type TEXT NOT NULL,
  canonical_name TEXT NOT NULL,
  external_ref JSONB NOT NULL,  -- {table, id}
  properties JSONB,  -- cached display data
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE app.entity_aliases (
  alias_id BIGSERIAL PRIMARY KEY,
  entity_id TEXT NOT NULL REFERENCES app.entities(entity_id),
  alias_text TEXT NOT NULL,
  user_id TEXT,  -- NULL = global
  confidence REAL NOT NULL DEFAULT 1.0,
  use_count INT NOT NULL DEFAULT 1,
  metadata JSONB,  -- {source, learned_from_event_id, disambiguation_context}
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(alias_text, user_id, entity_id)
);

CREATE INDEX idx_aliases_text ON app.entity_aliases(alias_text);
CREATE INDEX idx_aliases_entity ON app.entity_aliases(entity_id);
```

**Simplification**: Merged disambiguation_preferences into entity_aliases.metadata. One table, not two.

### 3. Episodic Memory

```sql
CREATE TABLE app.episodic_memories (
  memory_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  session_id UUID NOT NULL,

  summary TEXT NOT NULL,
  event_type TEXT NOT NULL,  -- question|statement|command|correction|confirmation
  source_event_ids BIGINT[] NOT NULL,

  entities JSONB NOT NULL,  -- [{id, name, type, mentions: [{text, position}]}]
  domain_context JSONB,     -- {queries_run, facts_found}

  importance REAL NOT NULL DEFAULT 0.5,
  embedding vector,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_episodic_user_time ON app.episodic_memories(user_id, created_at DESC);
CREATE INDEX idx_episodic_session ON app.episodic_memories(session_id);
CREATE INDEX idx_episodic_embedding ON app.episodic_memories
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Simplification**:
- `entities` JSONB includes entity mentions (no separate entity_mentions table)
- `domain_context` captures what DB queries were run (no separate snapshot table)
- Dropped `accessed_count` (can track in application logs if needed)

**Entity JSONB Structure**:
```json
{
  "entities": [
    {
      "id": "customer:xxx",
      "name": "Gai Media",
      "type": "customer",
      "mentions": [
        {"text": "Gai Media", "position": 15},
        {"text": "they", "position": 45, "coreference": true}
      ]
    }
  ]
}
```

### 4. Semantic Memory

```sql
CREATE TABLE app.semantic_memories (
  memory_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,

  -- Triple: Subject-Predicate-Object
  subject_entity_id TEXT REFERENCES app.entities(entity_id),
  predicate TEXT NOT NULL,
  predicate_type TEXT NOT NULL,
  object_value JSONB NOT NULL,

  -- Confidence & evolution
  confidence REAL NOT NULL DEFAULT 0.7,
  confidence_factors JSONB,  -- {base, reinforcement, recency, source}
  reinforcement_count INT NOT NULL DEFAULT 1,
  last_validated_at TIMESTAMPTZ,

  -- Provenance
  source_type TEXT NOT NULL,  -- episodic|consolidation|correction
  source_memory_id BIGINT,
  extracted_from_event_id BIGINT REFERENCES app.chat_events(event_id),

  -- Lifecycle
  status TEXT NOT NULL DEFAULT 'active',
  superseded_by_memory_id BIGINT REFERENCES app.semantic_memories(memory_id),

  -- Retrieval
  embedding vector,
  importance REAL NOT NULL DEFAULT 0.5,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT valid_status CHECK (status IN ('active', 'aging', 'superseded', 'invalidated'))
);

CREATE INDEX idx_semantic_user_status ON app.semantic_memories(user_id, status)
  WHERE status IN ('active', 'aging');
CREATE INDEX idx_semantic_entity_pred ON app.semantic_memories(subject_entity_id, predicate);
CREATE INDEX idx_semantic_embedding ON app.semantic_memories
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Simplification**:
- Removed `contradiction_count`, `decay_factor`, `validation_requested_at` (can compute on-demand)
- Dropped separate state transition table (status changes tracked via updated_at + app logs)

### 5. Memory Summaries

```sql
CREATE TABLE app.memory_summaries (
  summary_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,

  scope_type TEXT NOT NULL,  -- entity|topic|session_window
  scope_identifier TEXT,

  summary_text TEXT NOT NULL,
  key_facts JSONB NOT NULL,

  source_data JSONB NOT NULL,  -- {episodic_ids, semantic_ids, session_ids, time_range}
  supersedes_summary_id BIGINT REFERENCES app.memory_summaries(summary_id),

  confidence REAL NOT NULL DEFAULT 0.8,
  embedding vector,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_summaries_user_scope ON app.memory_summaries(user_id, scope_type, scope_identifier);
CREATE INDEX idx_summaries_embedding ON app.memory_summaries
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Simplification**:
- `source_data` JSONB combines source tracking (no separate arrays)
- Removed `coverage_score`, `version` (not essential for MVP)

### 6. Domain Ontology (Relationship Semantics)

```sql
CREATE TABLE app.domain_ontology (
  relation_id BIGSERIAL PRIMARY KEY,
  from_entity_type TEXT NOT NULL,
  relation_type TEXT NOT NULL,  -- has|creates|requires|fulfills
  to_entity_type TEXT NOT NULL,
  cardinality TEXT NOT NULL,
  join_path JSONB NOT NULL,  -- {from_table, to_table, join_on, optional_filters}
  constraints JSONB,  -- business rules
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(from_entity_type, relation_type, to_entity_type)
);

CREATE INDEX idx_ontology_from ON app.domain_ontology(from_entity_type);
```

**Purpose**: Enables graph traversal. Populate with domain relationships:
```json
{
  "from_entity_type": "customer",
  "relation_type": "has",
  "to_entity_type": "sales_order",
  "cardinality": "one_to_many",
  "join_path": {
    "from_table": "domain.customers",
    "to_table": "domain.sales_orders",
    "join_on": "customer_id"
  }
}
```

### 7. Configuration

```sql
CREATE TABLE app.config (
  config_key TEXT PRIMARY KEY,
  config_value JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Initial config
INSERT INTO app.config VALUES
  ('embedding', '{"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536}'),
  ('retrieval_limits', '{"summaries": 5, "semantic": 10, "episodic": 10}'),
  ('confidence_thresholds', '{"high": 0.85, "medium": 0.6, "low": 0.4}'),
  ('decay', '{"default_rate_per_day": 0.01, "validation_threshold_days": 90}');
```

### 8. Memory Conflicts (Optional but Useful)

```sql
CREATE TABLE app.memory_conflicts (
  conflict_id BIGSERIAL PRIMARY KEY,
  detected_at_event_id BIGINT REFERENCES app.chat_events(event_id),
  conflict_type TEXT NOT NULL,  -- memory_vs_memory|memory_vs_db
  conflict_data JSONB NOT NULL,  -- {memory_ids, values, confidences}
  resolution_strategy TEXT,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Purpose**: Log conflicts for debugging and explainability. Can be deferred if needed.

---

## Total Tables: 8 (was 15+)

**Core**: 8 tables
**Deferred**: procedural_memories, meta_memories, extraction_patterns, retrieval_weights, state_transitions, entity_mentions, retrieval_log, disambiguation_preferences

**Simplification Impact**:
- ~50% fewer tables
- Cleaner schema
- Less code to maintain
- Still covers all essential functionality

---

## Avoiding Bloat: Design Principles

### 1. JSONB: Use Judiciously

**Good uses**:
- `metadata` fields (variable structure, low query frequency)
- `object_value` (semantic memory values vary widely)
- `key_facts` (summary structured data)
- `entities` in episodic (includes mentions inline)

**Avoid**:
- Don't JSONB what should be columns (user_id, confidence, status)
- Don't JSONB what you'll query frequently (entity_id, predicate)

**Rule**: If you'll filter/sort/join on it → column. If it's variable/nested → JSONB.

### 2. Premature Optimization: Resist It

**Deferred Features** (add only when needed):
- State transition tracking → Just log status changes, track in app logs
- Procedural memory → Build when you have patterns to codify (Phase 2+)
- Meta-memory → Add when you have data to learn from (Phase 3+)
- Materialized views → Add when queries are slow (optimization phase)
- Retrieval logging → Use application metrics first

### 3. Keep It Queryable

**Don't sacrifice queryability for flexibility**:
- Entity IDs: typed strings ("customer:uuid") not opaque UUIDs
- Predicates: semantic names ("delivery_day_preference") not codes
- Status: explicit enum not numeric codes
- Timestamps: always TIMESTAMPTZ for temporal queries

### 4. One Source of Truth

**Avoid duplication**:
- Don't cache domain DB data long-term (query fresh)
- Don't denormalize prematurely (join when needed)
- Summaries can duplicate for efficiency (but mark as derived)

**Exception**: `properties` in entities (cached for display, not authoritative)

---

## Retrieval: Simplified Multi-Signal Scoring

**No separate weights table** - start with hardcoded, tune empirically.

```python
def compute_relevance(memory, query, memory_type):
    """
    Simple weighted scoring - hardcoded weights
    """
    # Semantic similarity (vector distance)
    semantic_score = 1 - cosine_distance(memory.embedding, query.embedding)

    # Entity overlap (Jaccard)
    entity_score = jaccard(memory.entities, query.entities)

    # Recency (exponential decay)
    age_days = (now() - memory.created_at).days
    recency_half_life = 30 if memory_type == 'episodic' else 90  # semantic decays slower
    recency_score = exp(-age_days * ln(2) / recency_half_life)

    # Type-specific weights
    if memory_type == 'summary':
        weights = {'semantic': 0.6, 'entity': 0.3, 'recency': 0.1}
    elif memory_type == 'semantic':
        weights = {'semantic': 0.4, 'entity': 0.3, 'recency': 0.3}
    else:  # episodic
        weights = {'semantic': 0.3, 'entity': 0.2, 'recency': 0.5}

    relevance = (
        weights['semantic'] * semantic_score +
        weights['entity'] * entity_score +
        weights['recency'] * recency_score
    )

    # Apply confidence multiplier (for semantic memories)
    if hasattr(memory, 'confidence'):
        relevance *= memory.confidence

    return relevance
```

**Start simple, optimize later based on actual usage.**

---

## Decay: Simplified Computation

**No separate decay_factor column** - compute on retrieval.

```python
def get_effective_confidence(semantic_memory):
    """
    Apply time-based decay to confidence
    """
    days_since_validation = (now() - (semantic_memory.last_validated_at or semantic_memory.created_at)).days

    # Get decay rate from config (default 1% per day)
    decay_config = get_config('decay')
    decay_rate = decay_config['default_rate_per_day']

    # Exponential decay
    decay_multiplier = exp(-days_since_validation * decay_rate)

    effective_confidence = semantic_memory.confidence * decay_multiplier

    # Mark as aging if below threshold
    if days_since_validation > decay_config['validation_threshold_days'] and effective_confidence < 0.5:
        mark_for_validation(semantic_memory)

    return effective_confidence
```

**No background jobs needed** - decay computed on-demand.

---

## Context Building: Token Budget

**Simple budget allocation**:

```python
def build_context(domain_facts, summaries, semantic_mems, episodic_mems, max_tokens=4000):
    """
    Simple budget allocation - fill buckets in priority order
    """
    context = []
    remaining = max_tokens

    # 1. Domain facts (highest priority, ~40%)
    db_text, db_tokens = format_domain_facts(domain_facts, limit=int(max_tokens * 0.4))
    context.append(f"## Domain Facts (Authoritative)\n{db_text}")
    remaining -= db_tokens

    # 2. Summaries (high-level context, ~20%)
    if summaries and remaining > 0:
        sum_text, sum_tokens = format_summaries(summaries, limit=int(remaining * 0.33))
        context.append(f"\n## Entity Profiles\n{sum_text}")
        remaining -= sum_tokens

    # 3. Semantic memories (specific facts, ~20%)
    if semantic_mems and remaining > 0:
        sem_text, sem_tokens = format_semantic(semantic_mems, limit=int(remaining * 0.5))
        context.append(f"\n## Learned Facts\n{sem_text}")
        remaining -= sem_tokens

    # 4. Episodic (recent context, remaining)
    if episodic_mems and remaining > 0:
        epi_text, epi_tokens = format_episodic(episodic_mems, limit=remaining)
        context.append(f"\n## Recent Context\n{epi_text}")

    return "\n".join(context)
```

**No complex ContextBuilder class** - simple function with priority order.

---

## Consolidated Architecture Diagram

```
User Message
    ↓
[1] Store event (app.chat_events)
    ↓
[2] Extract entities → app.entities + app.entity_aliases
    ↓
[3] Query domain DB (using app.domain_ontology for graph traversal)
    ↓
[4] Create episodic memory (app.episodic_memories)
    ↓
[5] Extract semantic facts? (if explicit or high-confidence)
    ├─→ Check existing (app.semantic_memories)
    ├─→ If match: Reinforce (confidence++, reinforcement_count++)
    └─→ If new: Create semantic memory
    ↓
[6] Detect conflicts? (app.memory_conflicts)
    └─→ Resolve (supersede, validate, or ask user)
    ↓
[7] Build context for LLM:
    - Query domain DB (current authoritative facts)
    - Retrieve summaries (vector search)
    - Retrieve semantic memories (vector + entity filter)
    - Retrieve episodic memories (vector + recency)
    - Compute effective confidence (apply decay)
    - Build context with token budget
    ↓
[8] LLM generates response
    ↓
[9] Store assistant response as event
    ↓
[Background: Async embedding generation]
[Background: Periodic consolidation if threshold met]
```

**Simplified from 15+ steps to 9 clear stages.**

---

## Migration Path: Start Simple, Add Complexity When Needed

### Phase 0: MVP (Week 1-2)
- Tables: chat_events, entities, entity_aliases, episodic_memories, semantic_memories
- Features: Basic entity resolution, memory creation, vector search
- **No**: Summaries, ontology, conflicts

### Phase 1: Intelligent Retrieval (Week 3-4)
- Add: domain_ontology, config
- Features: Graph traversal, multi-signal scoring, confidence/decay
- **No**: Consolidation yet

### Phase 2: Consolidation (Week 5-6)
- Add: memory_summaries
- Features: Cross-session synthesis, conflict detection
- Add: memory_conflicts (optional)

### Phase 3: Learning (Week 7+)
- Add: procedural_memories (if patterns emerge)
- Add: meta_memories (if have data to learn from)
- Add: tracking/logging tables (if need observability)

**Start with 5 tables. Add tables only when you need the functionality.**

---

## Summary: Simplified Design

**From**:
- 15+ tables
- Complex state machines
- Separate tracking tables
- Premature optimization

**To**:
- 8 core tables (5 for MVP)
- Essential state (active/aging/superseded/invalidated)
- Inline tracking (JSONB where appropriate)
- Optimize when needed

**Philosophy**: Build the simplest thing that embodies the vision. Add complexity only when you have concrete use cases and data to justify it.

**NoSQL Decision**: Postgres + pgvector is right for this system. Provides relational power for ontology, JSONB flexibility for schema evolution, and proven vector search. Start here; migrate only if you hit real scale limits.
