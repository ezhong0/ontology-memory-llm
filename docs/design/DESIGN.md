# System Design: Ontology-Aware Memory System

## Design Philosophy

This design serves the vision's core principles with **justified complexity** - every table, every field exists because it directly enables a core capability from the vision. Complexity that doesn't serve the vision is deferred or eliminated.

**Core Vision Principles This Design Serves**:
1. **Dual Truth**: Database (authoritative) + Memory (contextual) in equilibrium
2. **Memory Transformation**: Episodic → Semantic → Procedural → Meta (layered evolution)
3. **Epistemic Humility**: Confidence tracking, knowing what we don't know
4. **Graceful Forgetting**: Decay, consolidation, active validation
5. **Explainability**: Complete provenance, reasoning traces
6. **Ontology-Awareness**: Relationships have semantic meaning, not just foreign keys
7. **Continuous Learning**: Every interaction improves the system

---

## Information Architecture: The Layered Model

```
┌────────────────────────────────────────────────────────┐
│ Layer 6: Consolidated Summaries (cross-session)       │
│          • Entity profiles, patterns                   │
│          Serves: Forgetting (compression)              │
└────────────────────────────────────────────────────────┘
                         ↓ distills
┌────────────────────────────────────────────────────────┐
│ Layer 5: Procedural Memory (learned heuristics)       │
│          • "When X, also Y"                            │
│          Serves: Learning from interaction patterns    │
└────────────────────────────────────────────────────────┘
                         ↓ emerges from
┌────────────────────────────────────────────────────────┐
│ Layer 4: Semantic Memory (abstracted facts)           │
│          • Preferences, policies, observations         │
│          Serves: Contextual truth                      │
└────────────────────────────────────────────────────────┘
                         ↓ extracted from
┌────────────────────────────────────────────────────────┐
│ Layer 3: Episodic Memory (events with meaning)        │
│          • "User asked about X on Y"                   │
│          Serves: Historical record, learning substrate │
└────────────────────────────────────────────────────────┘
                         ↓ interprets
┌────────────────────────────────────────────────────────┐
│ Layer 2: Entity Resolution (text → entities)          │
│          • Canonical entities, aliases                 │
│          Serves: Grounding (problem of reference)      │
└────────────────────────────────────────────────────────┘
                         ↓ links
┌────────────────────────────────────────────────────────┐
│ Layer 1: Raw Events (immutable audit trail)           │
│          • Chat messages as they occurred              │
│          Serves: Provenance, historical record         │
└────────────────────────────────────────────────────────┘
                         ↓ queries
┌────────────────────────────────────────────────────────┐
│ Layer 0: Domain Database (authoritative truth)        │
│          • Customers, orders, invoices                 │
│          Serves: Current state, source of truth        │
└────────────────────────────────────────────────────────┘
```

**Information Flow**:
- **UP (abstraction)**: Events → Episodic → Semantic → Procedural → Summaries
- **DOWN (grounding)**: Queries start at DB, enrich with memory layers

---

## Core Schema: 10 Essential Tables

### Layer 0: Domain Database (External, Read-Only)

```sql
CREATE SCHEMA IF NOT EXISTS domain;

-- Provided tables:
-- domain.customers, domain.sales_orders, domain.work_orders,
-- domain.invoices, domain.payments, domain.tasks
```

**Design Notes**:
- Source of authoritative truth ("what IS")
- Never cache long-term (always query fresh)
- Read-only from memory system perspective

---

### Layer 1: Raw Events

```sql
CREATE TABLE app.chat_events (
  event_id BIGSERIAL PRIMARY KEY,
  session_id UUID NOT NULL,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  metadata JSONB,  -- {intent, entities_mentioned, language, processing_version}
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(session_id, content_hash)  -- idempotency
);

CREATE INDEX idx_chat_events_session ON app.chat_events(session_id);
CREATE INDEX idx_chat_events_user_time ON app.chat_events(user_id, created_at DESC);
```

**Why This Design**:
- **No embeddings**: Raw events are for audit/provenance, not retrieval
- **content_hash**: Enables idempotent ingestion (network retries)
- **metadata JSONB**: Flexible for schema evolution, processing version tracking
- **Immutable**: Never updated after insert (historical record principle)

**Vision Alignment**: Provenance (explainability), historical record (learning from past)

---

### Layer 2: Entity Resolution

#### Table 1: Canonical Entities

```sql
CREATE TABLE app.canonical_entities (
  entity_id TEXT PRIMARY KEY,  -- format: "customer:uuid" or "order:SO-1001"
  entity_type TEXT NOT NULL,
  canonical_name TEXT NOT NULL,
  external_ref JSONB NOT NULL,  -- {table: "domain.customers", id: "uuid"}
  properties JSONB,  -- cached display data (industry, status) - not authoritative
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_entities_type ON app.canonical_entities(entity_type);
CREATE INDEX idx_entities_name ON app.canonical_entities(canonical_name);
```

**Why This Design**:
- **entity_id format**: Self-documenting type prefix ("customer:xxx")
- **external_ref**: Links to domain DB without duplication
- **properties**: Denormalized cache for disambiguation display only

**Vision Alignment**: Solves "problem of reference" (identity across time)

#### Table 2: Entity Aliases

```sql
CREATE TABLE app.entity_aliases (
  alias_id BIGSERIAL PRIMARY KEY,
  canonical_entity_id TEXT NOT NULL REFERENCES app.canonical_entities(entity_id),
  alias_text TEXT NOT NULL,
  alias_source TEXT NOT NULL,  -- 'exact'|'fuzzy'|'learned'|'user_stated'
  user_id TEXT,  -- NULL = global, not-null = user-specific
  confidence REAL NOT NULL DEFAULT 1.0,
  use_count INT NOT NULL DEFAULT 1,
  metadata JSONB,  -- {learned_from_event_id, disambiguation_context, alternative_entities}
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(alias_text, user_id, canonical_entity_id)
);

CREATE INDEX idx_aliases_text ON app.entity_aliases(alias_text);
CREATE INDEX idx_aliases_entity ON app.entity_aliases(canonical_entity_id);
CREATE INDEX idx_aliases_user ON app.entity_aliases(user_id) WHERE user_id IS NOT NULL;
```

**Why This Design**:
- **user_id NULL/not-null**: Global aliases ("SO-1001") vs user-specific ("Gai" → entity X for Alice)
- **confidence + use_count**: Learn which aliases are reliable
- **metadata.disambiguation_context**: Store context patterns for disambiguation
  ```json
  {
    "learned_from_event_id": 123,
    "alternative_entities": ["customer:yyy"],
    "context_patterns": ["invoice", "entertainment"],
    "preferred_for_user": true
  }
  ```

**Why NOT Separate disambiguation_preferences Table**:
Disambiguation is just a special case of alias learning. Storing in metadata avoids table proliferation while preserving functionality.

**Vision Alignment**: Contextual identity resolution, learning from usage

---

### Layer 3: Episodic Memory

```sql
CREATE TABLE app.episodic_memories (
  memory_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  session_id UUID NOT NULL,

  summary TEXT NOT NULL,
  event_type TEXT NOT NULL,  -- question|statement|command|correction|confirmation
  source_event_ids BIGINT[] NOT NULL,

  -- Entities with inline coreference
  entities JSONB NOT NULL,  -- [{id, name, type, mentions: [{text, position, is_coreference}]}]

  -- Domain context
  domain_facts_referenced JSONB,  -- {queries: [{table, filter, results}]}

  importance REAL NOT NULL DEFAULT 0.5,
  embedding vector(1536),

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_episodic_user_time ON app.episodic_memories(user_id, created_at DESC);
CREATE INDEX idx_episodic_session ON app.episodic_memories(session_id);
CREATE INDEX idx_episodic_embedding ON app.episodic_memories
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Why This Design**:
- **entities JSONB**: Inline coreference resolution ("they" → customer:xxx)
  ```json
  {
    "entities": [
      {
        "id": "customer:xxx",
        "name": "Gai Media",
        "type": "customer",
        "mentions": [
          {"text": "Gai Media", "position": 15, "is_coreference": false},
          {"text": "they", "position": 45, "is_coreference": true, "refers_to_position": 15}
        ]
      }
    ]
  }
  ```

- **domain_facts_referenced**: Track which DB queries informed this memory (explainability)
- **No accessed_count**: If needed, track via retrieval logs (separation of concerns)

**Why NOT Separate entity_mentions Table**:
Coreference is tied to specific episodic memory context. Inline storage maintains cohesion, avoids joins.

**Vision Alignment**: Events with meaning (not just raw text), provenance

---

### Layer 4: Semantic Memory

```sql
CREATE TABLE app.semantic_memories (
  memory_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,

  -- Triple: Subject-Predicate-Object
  subject_entity_id TEXT REFERENCES app.canonical_entities(entity_id),
  predicate TEXT NOT NULL,
  predicate_type TEXT NOT NULL,  -- preference|requirement|observation|policy|attribute
  object_value JSONB NOT NULL,

  -- Confidence & evolution
  confidence REAL NOT NULL DEFAULT 0.7,
  confidence_factors JSONB,  -- {base, reinforcement, recency, source} for explainability
  reinforcement_count INT NOT NULL DEFAULT 1,
  last_validated_at TIMESTAMPTZ,

  -- Provenance
  source_type TEXT NOT NULL,  -- episodic|consolidation|inference|correction
  source_memory_id BIGINT,
  extracted_from_event_id BIGINT REFERENCES app.chat_events(event_id),

  -- Lifecycle
  status TEXT NOT NULL DEFAULT 'active',  -- active|aging|superseded|invalidated
  superseded_by_memory_id BIGINT REFERENCES app.semantic_memories(memory_id),

  -- Retrieval
  embedding vector(1536),
  importance REAL NOT NULL DEFAULT 0.5,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT valid_confidence CHECK (confidence >= 0 AND confidence <= 1),
  CONSTRAINT valid_status CHECK (status IN ('active', 'aging', 'superseded', 'invalidated'))
);

CREATE INDEX idx_semantic_user_status ON app.semantic_memories(user_id, status);
CREATE INDEX idx_semantic_entity_pred ON app.semantic_memories(subject_entity_id, predicate);
CREATE INDEX idx_semantic_embedding ON app.semantic_memories
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Why This Design**:
- **Subject-Predicate-Object**: Structured knowledge triples, queryable by entity+predicate
- **confidence_factors JSONB**: Explainability - show how confidence was computed
- **status lifecycle**: Essential for forgetting (aging) and corrections (superseded/invalidated)
- **superseded_by_memory_id**: Correction chain for explainability

**What's REMOVED (from original design)**:
- ❌ `contradiction_count`: Redundant with status transitions, adds no value
- ❌ `validation_requested_at`: Application state, not persistent data concern
- ❌ `decay_factor`: Compute on-demand, don't pre-compute and store
- ❌ `accessed_count`: If tracked, should be in retrieval logs (separation of concerns)

**object_value Structure**:
```json
// Simple
{"type": "string", "value": "Friday"}

// Temporal
{"type": "temporal", "value": "Friday", "valid_from": "2025-09-01"}

// Quantified
{"type": "numeric", "value": 30, "unit": "days", "context": "NET30 terms"}

// Structured
{"type": "contact", "method": "email", "preference_order": 1}
```

**Vision Alignment**: Contextual truth, confidence tracking (epistemic humility), forgetting (status lifecycle)

---

### Layer 5: Procedural Memory

```sql
CREATE TABLE app.procedural_memories (
  memory_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,

  trigger_pattern TEXT NOT NULL,
  trigger_features JSONB NOT NULL,  -- {intent, entity_types, topics}

  action_heuristic TEXT NOT NULL,
  action_structure JSONB NOT NULL,  -- {action_type, queries, predicates}

  observed_count INT NOT NULL DEFAULT 1,
  confidence REAL NOT NULL DEFAULT 0.5,

  embedding vector(1536),

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_procedural_user ON app.procedural_memories(user_id);
CREATE INDEX idx_procedural_confidence ON app.procedural_memories(confidence DESC);
CREATE INDEX idx_procedural_embedding ON app.procedural_memories
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Why This Table is ESSENTIAL** (not bloat):
Vision explicitly includes procedural memory in Layer 5 transformation pipeline. This table enables:
- Learning query patterns: "When user asks about delivery, also check invoices"
- Encoding domain heuristics: "If work_order done, suggest invoicing"
- Continuous improvement from interaction patterns

**Example**:
```json
{
  "trigger_pattern": "When user asks about delivery for customer entity",
  "trigger_features": {
    "intent": "question",
    "entity_types": ["customer"],
    "topics": ["delivery", "shipping"]
  },
  "action_heuristic": "Also retrieve delivery preferences, current orders, pending invoices",
  "action_structure": {
    "augment_retrieval": [
      {"memory_predicate": "delivery_.*_preference", "entity": "{customer}"},
      {"domain_query": "sales_orders", "filter": {"customer_id": "{customer}", "status": "in_fulfillment"}},
      {"domain_query": "invoices", "filter": {"customer_id": "{customer}", "status": "open"}}
    ]
  }
}
```

**Vision Alignment**: "Procedural memory captures patterns" - learning from repeated behaviors

---

### Layer 6: Memory Summaries

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
  embedding vector(1536),

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_summaries_user_scope ON app.memory_summaries(user_id, scope_type, scope_identifier);
CREATE INDEX idx_summaries_embedding ON app.memory_summaries
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Why This Table is ESSENTIAL** (not bloat):
Vision: "Forgetting is not a bug; it's essential to intelligence." Summaries enable:
- **Consolidation**: Replace 50 episodic memories with 1 coherent profile
- **Efficiency**: Faster retrieval (search summaries, not all episodes)
- **Abstraction**: Patterns emerge from synthesis

**key_facts Structure**:
```json
{
  "entity_profile": {
    "entity_id": "customer:xxx",
    "facts": {
      "delivery_preference": {"value": "Friday", "confidence": 0.95},
      "payment_terms": {"value": "NET30", "confidence": 0.9}
    }
  },
  "interaction_patterns": {
    "frequent_queries": ["invoice status", "delivery timing"],
    "typical_cadence": "weekly"
  }
}
```

**Vision Alignment**: Graceful forgetting (consolidation), efficiency

---

### Supporting Tables

#### Table 7: Domain Ontology

```sql
CREATE TABLE app.domain_ontology (
  relation_id BIGSERIAL PRIMARY KEY,
  from_entity_type TEXT NOT NULL,
  relation_type TEXT NOT NULL,  -- has|creates|requires|fulfills
  to_entity_type TEXT NOT NULL,

  cardinality TEXT NOT NULL,
  relation_semantics TEXT NOT NULL,

  join_spec JSONB NOT NULL,  -- {from_table, to_table, join_on}
  constraints JSONB,  -- business rules

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(from_entity_type, relation_type, to_entity_type)
);

CREATE INDEX idx_ontology_from ON app.domain_ontology(from_entity_type);
CREATE INDEX idx_ontology_to ON app.domain_ontology(to_entity_type);
```

**Why This Table is ESSENTIAL** (not optional):
System is literally called "**Ontology-Aware** Memory System." This table enables:
- Understanding relationship **meaning**: "creates" vs "fulfills" vs "requires"
- Graph traversal with semantic awareness
- Business rule encoding: "can't invoice until work_order done"

**Example**:
```json
{
  "from_entity_type": "sales_order",
  "relation_type": "creates",
  "to_entity_type": "work_order",
  "cardinality": "one_to_many",
  "relation_semantics": "sales order creates work orders for fulfillment",
  "join_spec": {
    "from_table": "domain.sales_orders",
    "to_table": "domain.work_orders",
    "on": "domain.sales_orders.so_id = domain.work_orders.so_id"
  },
  "constraints": {
    "lifecycle": "work_order.status='done' required before invoice created"
  }
}
```

**Vision Alignment**: "Foreign keys connect tables. Ontology connects meaning."

---

#### Table 8: Memory Conflicts

```sql
CREATE TABLE app.memory_conflicts (
  conflict_id BIGSERIAL PRIMARY KEY,
  detected_at_event_id BIGINT NOT NULL REFERENCES app.chat_events(event_id),

  conflict_type TEXT NOT NULL,  -- memory_vs_memory|memory_vs_db|temporal
  conflict_data JSONB NOT NULL,  -- {memory_ids, values, confidences, db_source}

  resolution_strategy TEXT,  -- trust_db|trust_recent|ask_user|both
  resolution_outcome JSONB,
  resolved_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conflicts_event ON app.memory_conflicts(detected_at_event_id);
CREATE INDEX idx_conflicts_type ON app.memory_conflicts(conflict_type);
```

**Why This Table is ESSENTIAL** (not optional):
Vision: "When memory conflicts with DB, make the conflict explicit." Enables:
- **Explainability**: Show user why system is uncertain
- **Trust**: Transparency about conflicts builds trust
- **Learning**: Analyze conflict patterns to improve extraction

**Example**:
```json
{
  "conflict_type": "memory_vs_db",
  "conflict_data": {
    "memory": {
      "id": 100,
      "predicate": "delivery_preference",
      "value": "Friday",
      "confidence": 0.8
    },
    "db_source": {
      "table": "domain.customer_preferences",
      "value": "Thursday",
      "queried_at": "2025-10-15T10:00:00Z"
    }
  },
  "resolution_strategy": "trust_db",
  "resolution_outcome": {
    "action": "supersede_memory",
    "memory_marked": "invalidated"
  }
}
```

**Vision Alignment**: Epistemic humility, explainability, truth hierarchy

---

#### Table 9: System Configuration

```sql
CREATE TABLE app.system_config (
  config_key TEXT PRIMARY KEY,
  config_value JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Initial values
INSERT INTO app.system_config VALUES
  ('embedding', '{"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536}'),
  ('retrieval_limits', '{"summaries": 5, "semantic": 10, "episodic": 10}'),
  ('confidence_thresholds', '{"high": 0.85, "medium": 0.6, "low": 0.4}'),
  ('decay', '{"default_rate_per_day": 0.01, "validation_threshold_days": 90}'),
  ('multi_signal_weights', '{"semantic": 0.4, "entity": 0.25, "recency": 0.2, "importance": 0.1, "reinforcement": 0.05}');
```

**Why This Table**:
- **Flexibility**: Swap embedding providers without code changes
- **Tuning**: Adjust thresholds based on empirical observation
- **Small table, high value**: Configuration-driven behavior

---

## Total: 10 Core Tables (Phase 1)

**Layer 1**: 1 table (chat_events)
**Layer 2**: 2 tables (entities, aliases)
**Layer 3**: 1 table (episodic_memories)
**Layer 4**: 1 table (semantic_memories)
**Layer 5**: 1 table (procedural_memories) ✅ **ESSENTIAL PER VISION**
**Layer 6**: 1 table (memory_summaries) ✅ **ESSENTIAL PER VISION**
**Supporting**: 3 tables (ontology, conflicts, config)

---

## What's DEFERRED (and Why)

### Deferred to Phase 2

**memory_state_transitions**: Useful for analysis but not core functionality.
- Can reconstruct from status + superseded_by + updated_at
- Add when you need detailed lifecycle analysis

**retrieval_scoring_weights**: Learning feature.
- Start with hardcoded weights in config
- Add per-user learned weights when you have usage data

### Deferred to Phase 3

**meta_memories**: Learning decay rates per fact type.
- Vision includes this, but requires observation data
- Start with default decay rates
- Add when you have 1000+ semantic memories with corrections

**extraction_patterns**: Learning from corrections.
- Requires significant correction data first
- Add in Phase 3 for extraction quality improvement

---

## Key Design Decisions & Rationale

### Decision 1: Inline vs Separate Tables

**Disambiguation in entity_aliases.metadata** (not separate table):
- Disambiguation is learned alias preference
- JSONB metadata provides flexibility without table proliferation
- One lookup instead of join

**Coreference in episodic_memories.entities** (not separate table):
- Coreference is context-specific to episodic memory
- Inline storage maintains cohesion
- Avoids joins for common operation (entity extraction)

**Trade-off**: Less normalized, but better performance and simpler queries

### Decision 2: What Fields to Remove

**Removed from semantic_memories**:
- `contradiction_count`: Status already tracks superseded/invalidated
- `validation_requested_at`: Ephemeral application state
- `decay_factor`: Compute on-demand (passive decay)
- `accessed_count`: If needed, belongs in retrieval logs

**Why**: Each field must justify its existence. If derivable or ephemeral, don't store.

### Decision 3: Procedural & Summaries are NOT Optional

Both directly serve vision's core principles:
- **Procedural**: "Procedural memory captures patterns" (Vision Layer 5)
- **Summaries**: "Forgetting is essential to intelligence" (Vision: Consolidation)

Removing these would violate the vision, not simplify toward it.

### Decision 4: Ontology Table is NOT Optional

System name: "**Ontology-Aware** Memory System"

Vision: "Foreign keys connect tables. Ontology connects meaning."

Without domain_ontology, the system isn't ontology-aware - it's just a chatbot with vector search.

### Decision 5: Passive Decay

Don't pre-compute and store decay_factor. Compute on retrieval:

```python
effective_confidence = confidence * exp(-days_since_validation * decay_rate)
```

**Why**: No background jobs, no stale pre-computed values, simpler.

**Trade-off**: Can't query by effective_confidence. Acceptable - we query by stored confidence and filter in application.

---

## Information Flow

### Memory Creation Pipeline

```
User Message
  ↓
[1] Store event (chat_events) + extract entities
  ↓
[2] Resolve entities (canonical_entities + entity_aliases)
      - Exact match → confidence 1.0
      - Known alias → confidence 0.95
      - Fuzzy match → confidence 0.85
      - Disambiguation → learn preference in alias metadata
  ↓
[3] Query domain DB using ontology graph
      - Get authoritative facts
      - Follow relationships (customer → orders → invoices)
  ↓
[4] Create episodic memory
      - Summary, entities (with coreference), domain_facts_referenced
  ↓
[5] Extract semantic facts (if applicable)
      - Check for existing memory (subject + predicate)
      - IF EXISTS: Reinforce (confidence++, reinforcement_count++)
      - IF NEW: Create semantic memory
      - IF CONFLICT: Log in memory_conflicts
  ↓
[6] Detect procedural patterns (background, after N memories)
      - Repeated query sequences → procedural memory
  ↓
[7] Consolidate (triggered: N sessions or M days)
      - LLM synthesizes summary from episodic + semantic
      - Create memory_summary
      - Boost confidence of confirmed facts
```

### Retrieval Pipeline

```
User Query
  ↓
[1] Extract entities → resolve to canonical IDs
  ↓
[2] Parallel retrieval:
      ├─→ Vector search: memory_summaries (top-5)
      ├─→ Vector search: semantic_memories (top-10, filter by entity)
      ├─→ Vector search: episodic_memories (top-10, recency boost)
      └─→ Pattern match: procedural_memories (trigger features)
  ↓
[3] Score each memory (multi-signal):
      semantic_similarity * 0.4 +
      entity_overlap * 0.25 +
      recency * 0.2 +
      importance * 0.1 +
      reinforcement * 0.05

      Multiply by: confidence (for semantic memories)
  ↓
[4] Domain DB augmentation:
      - For each entity: query current facts
      - Use ontology to traverse: customer → orders → work_orders → invoices
  ↓
[5] Conflict detection:
      - Compare semantic memories vs DB facts
      - If conflict: log in memory_conflicts
  ↓
[6] Compute effective confidence (passive decay):
      - effective_conf = stored_conf * exp(-days_since_validation * decay_rate)
      - If old + low reinforcement → mark for validation
  ↓
[7] Build context (token budget):
      - 40% DB facts (authoritative, always first)
      - 20% Summaries (high-level profiles)
      - 20% Semantic facts (specific preferences)
      - 15% Episodic (recent context)
      - 5% Procedural hints (suggested actions)
  ↓
[8] Return context + metadata for LLM
```

---

## Implementation Roadmap

### Phase 0: Foundation (Week 1-2)
**Tables**: chat_events, canonical_entities, entity_aliases, episodic_memories, semantic_memories, system_config

**Capabilities**:
- Store conversations
- Basic entity resolution (exact + fuzzy)
- Create episodic + semantic memories
- Vector search retrieval
- Simple domain DB queries

**Not Yet**: Procedural, summaries, ontology graph, conflicts

### Phase 1: Intelligence (Week 3-4)
**Add**: domain_ontology, memory_conflicts, procedural_memories

**Capabilities**:
- Ontology-aware graph traversal
- Multi-signal retrieval scoring
- Conflict detection + logging
- Procedural pattern detection (basic)
- Reinforcement + decay

**Not Yet**: Consolidation, meta-learning

### Phase 2: Consolidation (Week 5-6)
**Add**: memory_summaries

**Capabilities**:
- Cross-session consolidation
- LLM-based summary generation
- Confidence boosting from consolidation
- Retrieval from summaries

**Not Yet**: Advanced learning, per-user weights

### Phase 3: Learning (Week 7+)
**Add**: meta_memories, retrieval_scoring_weights, extraction_patterns

**Capabilities**:
- Adaptive decay rates per fact type
- Per-user learned retrieval weights
- Extraction quality improvement from corrections

---

## Critical Implementation Details

### Idempotency

```sql
UNIQUE(session_id, content_hash) ON app.chat_events
```

Retry-safe ingestion: hash content, reject duplicates.

### Embedding Strategy

**Async embed**: Don't block request on embedding generation.

```
Create memory → Publish to queue → Worker embeds → Update embedding field
```

**Cost optimization**: Only embed what you'll search (memories, not raw events).

### Entity Resolution Algorithm

```python
def resolve_entity(text, user_id, context):
    # 1. Exact match on canonical name
    if exact_match := find_canonical(text):
        return exact_match, confidence=1.0

    # 2. Known alias (user-specific first, then global)
    if alias := find_alias(text, user_id):
        return alias.canonical_entity_id, confidence=0.95

    # 3. Fuzzy match (Levenshtein)
    candidates = fuzzy_search(text, threshold=0.7)

    if len(candidates) == 1 and candidates[0].similarity > 0.85:
        return candidates[0].entity_id, confidence=candidates[0].similarity

    if len(candidates) > 1:
        # Check for learned disambiguation preference
        if pref := get_disambiguation_pref(user_id, text):
            return pref.entity_id, confidence=0.9

        # Multiple candidates, need disambiguation
        return DISAMBIGUATE(candidates)

    # 4. Check domain DB
    if db_entity := query_domain_db(text):
        new_entity = create_canonical_entity(db_entity)
        return new_entity.entity_id, confidence=0.8

    return NOT_FOUND
```

### Confidence Calculation

```python
# Base confidence
base = {
    'explicit_statement': 0.7,  # "Remember: X"
    'inferred': 0.5,
    'consolidation': 0.75
}[source_type]

# Reinforcement boost (diminishing returns)
reinforce_boost = min(0.25, reinforcement_count * 0.08)

# Combine
confidence = min(0.95, base + reinforce_boost)

# Store factors for explainability
confidence_factors = {
    'base_confidence': base,
    'reinforcement_boost': reinforce_boost,
    'reinforcement_count': reinforcement_count,
    'source_type': source_type,
    'final_confidence': confidence
}
```

### Decay (Passive)

```python
def get_effective_confidence(semantic_memory):
    days_since_validation = (now() - semantic_memory.last_validated_at).days
    decay_rate = get_config('decay')['default_rate_per_day']  # 0.01

    decay_multiplier = exp(-days_since_validation * decay_rate)
    effective_conf = semantic_memory.confidence * decay_multiplier

    # Trigger validation if needed
    validation_threshold = get_config('decay')['validation_threshold_days']  # 90
    if days_since_validation > validation_threshold and effective_conf < 0.5:
        mark_for_validation(semantic_memory)

    return effective_conf
```

### Multi-Signal Retrieval

```python
def score_memory(memory, query):
    weights = get_config('multi_signal_weights')

    # Semantic similarity (cosine)
    sem_score = 1 - cosine_distance(memory.embedding, query.embedding)

    # Entity overlap (Jaccard)
    entity_score = jaccard(memory.entities, query.entities)

    # Recency (exponential decay)
    age_days = (now() - memory.created_at).days
    half_life = 30 if memory_type == 'episodic' else 90
    recency_score = exp(-age_days * ln(2) / half_life)

    # Importance (stored)
    importance_score = memory.importance

    # Reinforcement (for semantic)
    reinforce_score = min(1.0, memory.reinforcement_count / 5) if hasattr(memory, 'reinforcement_count') else 0.5

    # Weighted sum
    relevance = (
        weights['semantic'] * sem_score +
        weights['entity'] * entity_score +
        weights['recency'] * recency_score +
        weights['importance'] * importance_score +
        weights['reinforcement'] * reinforce_score
    )

    # Apply confidence penalty
    if hasattr(memory, 'confidence'):
        effective_conf = get_effective_confidence(memory)
        relevance *= effective_conf

    return relevance
```

---

## Summary: Design Justification

**Every table serves the vision**:
- Layers 1-6: Direct mapping to vision's memory transformation pipeline
- Ontology: Core to system identity ("ontology-aware")
- Conflicts: Core to epistemic humility ("make conflicts explicit")
- Config: Flexibility without hardcoding

**Complexity removed**:
- Separate disambiguation table (inline in aliases)
- Separate entity mentions (inline in episodic)
- Pre-computed decay (compute on-demand)
- Ephemeral state fields (validation_requested_at)
- Redundant counters (contradiction_count)

**Complexity deferred**:
- State transitions (Phase 2, useful but not core)
- Meta-memory (Phase 3, needs observation data)
- Extraction patterns (Phase 3, needs correction data)
- Learned weights (Phase 2, needs usage data)

**Result**: 10 essential tables that embody the vision without bloat.
