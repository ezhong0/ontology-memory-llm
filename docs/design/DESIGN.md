# System Design: Ontology-Aware Memory System

**Version**: 2.0 - Ground-Up Redesign
**Date**: 2025-10-15
**Status**: Active Design

---

## From Vision to Architecture

This design is derived directly from the vision document, with every architectural decision justified by the Three Questions Framework from the design philosophy.

### The Vision's Core Requirements

The vision describes a system that behaves like an **experienced colleague who has worked with this company for years**. This colleague:

1. **Never forgets what matters** - but also doesn't drown you in irrelevant details (graceful forgetting)
2. **Knows the business deeply** - understands data, processes, relationships (ontology-awareness)
3. **Learns your way of working** - adapts to preferences and patterns (continuous learning)
4. **Admits uncertainty** - doesn't pretend to know when unsure (epistemic humility)
5. **Explains their thinking** - can trace reasoning back to sources (explainability)
6. **Gets smarter over time** - each conversation improves future ones (learning)

### The Fundamental Architecture: Dual Truth in Equilibrium

```
┌─────────────────────────────────────────────────────────────┐
│                  DOMAIN DATABASE (Layer 0)                  │
│                 Correspondence Truth: "What IS"             │
│            • Customers, Orders, Invoices, Payments          │
│            • Authoritative, transactional, current state    │
└─────────────────────────────────────────────────────────────┘
                            ↕
              [Queries down, enriches up]
                            ↕
┌─────────────────────────────────────────────────────────────┐
│              MEMORY SYSTEM (Layers 1-6)                     │
│           Contextual Truth: "What it MEANS"                 │
│     • Events, interpretations, preferences, patterns        │
│     • Learned, contextual, confidence-tracked               │
└─────────────────────────────────────────────────────────────┘
```

**Vision Principle Served**: Dual truth - "business operations exist at the intersection of objective fact and subjective meaning"

The database alone is "precise but hollow." Memory alone is "meaningful but ungrounded." Together they create understanding.

---

## The Layered Memory Architecture

The vision explicitly describes memory transformation across layers. This architecture directly implements that vision:

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

---

## Core Schema: 10 Essential Tables

Each table directly serves one or more vision principles. Tables are ordered by layer.

### Layer 1: Raw Events (Provenance)

#### Table 1: chat_events

**Vision Principles**: Explainability (provenance), Learning (historical record)

```sql
CREATE TABLE app.chat_events (
  event_id BIGSERIAL PRIMARY KEY,
  session_id UUID NOT NULL,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(session_id, content_hash)
);

CREATE INDEX idx_chat_events_session ON app.chat_events(session_id);
CREATE INDEX idx_chat_events_user_time ON app.chat_events(user_id, created_at DESC);
```

**Why This Design**:
- **Immutable**: Never updated after creation (historical record principle)
- **content_hash**: Enables idempotent ingestion (network retries)
- **No embeddings**: Raw events are for audit, not retrieval
- **metadata JSONB**: Flexible for processing version tracking, intent labels

**What's NOT Here** (and why):
- ❌ `embedding`: Events aren't retrieved by similarity, memories are
- ❌ `importance`: Computed at episodic memory level after interpretation

---

### Layer 2: Entity Resolution (Grounding)

**Vision Principle**: "Problem of reference" - linking text mentions to canonical entities

#### Table 2: canonical_entities

```sql
CREATE TABLE app.canonical_entities (
  entity_id TEXT PRIMARY KEY,           -- Format: "customer:uuid"
  entity_type TEXT NOT NULL,            -- "customer", "order", "invoice", etc.
  canonical_name TEXT NOT NULL,         -- "Gai Media"
  external_ref JSONB NOT NULL,          -- {"table": "domain.customers", "id": "uuid"}
  properties JSONB,                     -- Cached display data, NOT authoritative
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_entities_type ON app.canonical_entities(entity_type);
CREATE INDEX idx_entities_name ON app.canonical_entities(canonical_name);
```

**Why This Design**:
- **entity_id format**: Self-documenting ("customer:xxx" vs "order:SO-1001")
- **external_ref**: Links to domain DB without duplication
- **properties**: Denormalized for disambiguation UI only (not queried for truth)

**Lazy Creation**: Entities created on-demand when first mentioned or queried

#### Table 3: entity_aliases

```sql
CREATE TABLE app.entity_aliases (
  alias_id BIGSERIAL PRIMARY KEY,
  canonical_entity_id TEXT NOT NULL REFERENCES app.canonical_entities(entity_id),
  alias_text TEXT NOT NULL,
  alias_source TEXT NOT NULL,          -- 'exact'|'fuzzy'|'coreference'|'user_stated'
  user_id TEXT,                        -- NULL = global, not-null = user-specific
  confidence REAL NOT NULL DEFAULT 1.0,
  use_count INT NOT NULL DEFAULT 1,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(alias_text, user_id, canonical_entity_id)
);

CREATE INDEX idx_aliases_lookup ON app.entity_aliases(alias_text, user_id, confidence DESC);
CREATE INDEX idx_aliases_entity ON app.entity_aliases(canonical_entity_id);
CREATE INDEX idx_aliases_trigram ON app.entity_aliases USING gin(alias_text gin_trgm_ops);
```

**Why This Design**:
- **user_id NULL/not-null**: Global vs user-specific aliases ("Gai" → different entities for different users)
- **confidence + use_count**: Learn which aliases are reliable
- **alias_source**: Track how alias was learned (exact, fuzzy, coreference resolution, user stated)
- **metadata**: Stores disambiguation context, alternative candidates

**Self-Improving**: High-confidence resolutions create aliases, moving future lookups to fast path

---

### Layer 3: Episodic Memory (Events with Meaning)

**Vision Principle**: "Events with meaning (not just raw text), foundation for learning"

#### Table 4: episodic_memories

```sql
CREATE TABLE app.episodic_memories (
  memory_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  session_id UUID NOT NULL,

  summary TEXT NOT NULL,
  event_type TEXT NOT NULL,            -- question|statement|command|correction|confirmation
  source_event_ids BIGINT[] NOT NULL,

  -- Entities with coreference resolved
  entities JSONB NOT NULL,             -- [{id, name, type, mentions: [{text, is_coreference}]}]

  -- Domain context at time of event
  domain_facts_referenced JSONB,       -- {queries: [{table, filter, results}]}

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
- **entities JSONB**: Coreference resolved inline ("they" → customer:xxx)
  ```json
  {
    "entities": [
      {
        "id": "customer:xxx",
        "name": "Gai Media",
        "type": "customer",
        "mentions": [
          {"text": "Gai Media", "position": 15, "is_coreference": false},
          {"text": "they", "position": 45, "is_coreference": true}
        ]
      }
    ]
  }
  ```
- **domain_facts_referenced**: Explainability - which DB queries informed this memory
- **source_event_ids**: Provenance chain back to raw events

**Philosophy Decision**: Inline entities (not separate table) because coreference is context-specific

---

### Layer 4: Semantic Memory (Contextual Truth)

**Vision Principles**: Contextual truth, epistemic humility, graceful forgetting

#### Table 5: semantic_memories

```sql
CREATE TABLE app.semantic_memories (
  memory_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,

  -- Triple: Subject-Predicate-Object
  subject_entity_id TEXT REFERENCES app.canonical_entities(entity_id),
  predicate TEXT NOT NULL,
  predicate_type TEXT NOT NULL,       -- preference|requirement|observation|policy|attribute
  object_value JSONB NOT NULL,

  -- Confidence & Evolution
  confidence REAL NOT NULL DEFAULT 0.7,
  confidence_factors JSONB,           -- Explainability: {base, reinforcement, recency}
  reinforcement_count INT NOT NULL DEFAULT 1,
  last_validated_at TIMESTAMPTZ,

  -- Provenance
  source_type TEXT NOT NULL,          -- episodic|consolidation|inference|correction
  source_memory_id BIGINT,
  extracted_from_event_id BIGINT REFERENCES app.chat_events(event_id),

  -- Lifecycle (Graceful Forgetting)
  status TEXT NOT NULL DEFAULT 'active',
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
- **Subject-Predicate-Object**: Structured knowledge, queryable by entity+predicate
- **confidence_factors**: Explainability - show HOW confidence was calculated
- **status lifecycle**: Essential for forgetting (active → aging → superseded)
- **superseded_by_memory_id**: Correction chain (never lose history)
- **last_validated_at**: Enables temporal decay calculation

**Passive Decay** (Philosophy: compute on-demand):
```python
effective_confidence = stored_confidence * exp(-days_since_validation * decay_rate)
```

**What's REMOVED** (from earlier iterations):
- ❌ `decay_factor`: Computed on-demand, not stored
- ❌ `accessed_count`: Deferred to Phase 3 (learning from usage)
- ❌ `contradiction_count`: Status transitions capture this
- ❌ `validation_requested_at`: Application state, not persistent

---

### Layer 5: Procedural Memory (Learned Heuristics)

**Vision Principle**: "Procedural memory captures patterns" - learning from repeated behaviors

#### Table 6: procedural_memories

```sql
CREATE TABLE app.procedural_memories (
  memory_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,

  trigger_pattern TEXT NOT NULL,
  trigger_features JSONB NOT NULL,     -- {intent, entity_types, topics}

  action_heuristic TEXT NOT NULL,
  action_structure JSONB NOT NULL,     -- {action_type, augment_retrieval, suggest_query}

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

The vision explicitly includes Layer 5 procedural memory. This enables:
- Learning query patterns: "When user asks about delivery, also check invoices"
- Encoding domain heuristics: "If work_order done, suggest invoicing"
- Continuous improvement: System gets smarter from repeated interactions

**Example Procedural Memory**:
```json
{
  "trigger_pattern": "When user asks about delivery for customer entity",
  "trigger_features": {
    "intent": "question",
    "entity_types": ["customer"],
    "topics": ["delivery", "shipping"]
  },
  "action_heuristic": "Augment retrieval: delivery preferences + active orders + pending invoices",
  "action_structure": {
    "augment_retrieval": [
      {"predicate_pattern": "delivery_.*_preference", "entity": "{customer}"},
      {"domain_query": "sales_orders", "filter": {"status": "in_fulfillment"}},
      {"domain_query": "invoices", "filter": {"status": "open"}}
    ]
  }
}
```

---

### Layer 6: Consolidated Summaries (Graceful Forgetting)

**Vision Principle**: "Forgetting is essential to intelligence" - consolidation compresses detail into essence

#### Table 7: memory_summaries

```sql
CREATE TABLE app.memory_summaries (
  summary_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,

  scope_type TEXT NOT NULL,            -- entity|topic|session_window
  scope_identifier TEXT,

  summary_text TEXT NOT NULL,
  key_facts JSONB NOT NULL,

  source_data JSONB NOT NULL,          -- {episodic_ids, semantic_ids, session_ids, time_range}
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

Vision: "Replace many specific memories with one abstract summary"

After 5 sessions discussing a customer:
- 50 episodic memories
- 12 semantic memories
→ Consolidate into 1 summary: "Gai Media profile: Friday deliveries (confirmed 3x), NET30 terms, prefers email, typically pays 2-3 days late"

**Benefits**:
1. **Efficiency**: Search summaries (fast) instead of all episodes
2. **Abstraction**: Patterns emerge from synthesis
3. **Forgetting**: Original memories retained for provenance, but deprioritized

**key_facts Structure**:
```json
{
  "entity_profile": {
    "entity_id": "customer:xxx",
    "confirmed_facts": {
      "delivery_preference": {"value": "Friday", "confidence": 0.95, "reinforced": 3},
      "payment_terms": {"value": "NET30", "confidence": 0.9}
    }
  },
  "interaction_patterns": {
    "frequent_queries": ["invoice status", "delivery timing"],
    "typical_cadence": "weekly"
  }
}
```

---

### Supporting Tables (Cross-Layer)

#### Table 8: domain_ontology

**Vision Principle**: "Ontology-Awareness" - relationships have semantic meaning

```sql
CREATE TABLE app.domain_ontology (
  relation_id BIGSERIAL PRIMARY KEY,
  from_entity_type TEXT NOT NULL,
  relation_type TEXT NOT NULL,         -- has|creates|requires|fulfills|depends_on
  to_entity_type TEXT NOT NULL,

  cardinality TEXT NOT NULL,           -- one_to_one|one_to_many|many_to_many
  relation_semantics TEXT NOT NULL,

  join_spec JSONB NOT NULL,            -- {from_table, to_table, on}
  constraints JSONB,                   -- Business rules

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(from_entity_type, relation_type, to_entity_type)
);

CREATE INDEX idx_ontology_from ON app.domain_ontology(from_entity_type);
CREATE INDEX idx_ontology_to ON app.domain_ontology(to_entity_type);
```

**Why This Table is ESSENTIAL**:

The system is literally called "**Ontology-Aware** Memory System". Vision: "Foreign keys connect tables. Ontology connects meaning."

This enables:
- Understanding relationship semantics: "creates" vs "fulfills" vs "requires"
- Graph traversal with business logic: "Can we invoice?" → Check work_order.status first
- Multi-hop reasoning: customer → orders → work_orders → invoices

**Example**:
```json
{
  "from_entity_type": "work_order",
  "relation_type": "enables_creation_of",
  "to_entity_type": "invoice",
  "relation_semantics": "Work must be completed before invoice can be created",
  "constraints": {
    "prerequisite": "work_order.status = 'done'"
  }
}
```

---

#### Table 9: memory_conflicts

**Vision Principle**: Epistemic humility - "system knows what it doesn't know"

```sql
CREATE TABLE app.memory_conflicts (
  conflict_id BIGSERIAL PRIMARY KEY,
  detected_at_event_id BIGINT NOT NULL REFERENCES app.chat_events(event_id),

  conflict_type TEXT NOT NULL,         -- memory_vs_memory|memory_vs_db|temporal
  conflict_data JSONB NOT NULL,        -- {memory_ids, values, confidences, db_source}

  resolution_strategy TEXT,            -- trust_db|trust_recent|ask_user|both_valid
  resolution_outcome JSONB,
  resolved_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conflicts_event ON app.memory_conflicts(detected_at_event_id);
CREATE INDEX idx_conflicts_unresolved ON app.memory_conflicts(resolved_at) WHERE resolved_at IS NULL;
```

**Why This Table is ESSENTIAL**:

Vision: "When memory conflicts with DB, make the conflict explicit"

This enables:
- **Transparency**: Show user why system is uncertain
- **Trust**: Explainability builds confidence
- **Learning**: Analyze conflict patterns to improve extraction

**Example Conflict**:
```json
{
  "conflict_type": "memory_vs_db",
  "conflict_data": {
    "memory": {
      "id": 100,
      "predicate": "delivery_preference",
      "value": "Friday",
      "confidence": 0.8,
      "last_validated": "2025-09-01"
    },
    "db_source": {
      "table": "domain.customer_preferences",
      "value": "Thursday",
      "queried_at": "2025-10-15"
    }
  },
  "resolution_strategy": "trust_db",
  "resolution_outcome": {
    "action": "supersede_memory",
    "old_memory_status": "invalidated",
    "reasoning": "Database is authoritative for current preferences"
  }
}
```

---

#### Table 10: system_config

**Philosophy**: Configuration-driven behavior, tunable without code changes

```sql
CREATE TABLE app.system_config (
  config_key TEXT PRIMARY KEY,
  config_value JSONB NOT NULL,
  description TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Initial Configuration**:
```sql
INSERT INTO app.system_config (config_key, config_value, description) VALUES
  ('embedding',
   '{"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536}',
   'Embedding model configuration'),

  ('retrieval_limits',
   '{"summaries": 5, "semantic": 10, "episodic": 10}',
   'Max memories retrieved per layer'),

  ('confidence_thresholds',
   '{"high": 0.85, "medium": 0.6, "low": 0.4}',
   'Confidence interpretation thresholds'),

  ('decay',
   '{"default_rate_per_day": 0.01, "validation_threshold_days": 90}',
   'Memory decay parameters'),

  ('multi_signal_weights',
   '{"semantic": 0.4, "entity": 0.25, "recency": 0.2, "importance": 0.1, "reinforcement": 0.05}',
   'Retrieval scoring weights');
```

---

## Summary: 10 Essential Tables

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

---

## Key Algorithms and Processes

### 1. Entity Resolution (Layer 2)

**Vision Principle**: Solving the "problem of reference"

**Algorithm**: Deterministic fast path + LLM coreference fallback

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
        # Single high-confidence fuzzy match
        await learn_alias(mention, fuzzy[0]['entity_id'], user_id, 'fuzzy', fuzzy[0]['score'])
        return ResolutionResult(entity_id=fuzzy[0]['entity_id'],
                               confidence=fuzzy[0]['score'],
                               method='fuzzy')

    if len(fuzzy) > 1:
        # Multiple candidates - check for learned disambiguation preference
        pref = await get_disambiguation_preference(user_id, mention, [f['entity_id'] for f in fuzzy])
        if pref:
            return ResolutionResult(entity_id=pref['entity_id'],
                                   confidence=0.9,
                                   method='disambiguation_learned')

        # Need user disambiguation
        return DisambiguationRequired(candidates=fuzzy)

    # ═══════════════════════════════════════════════════════════
    # LLM PATH: Coreference resolution (handles 5% of cases)
    # ═══════════════════════════════════════════════════════════

    # Check if mention is a pronoun or contextual reference
    if is_coreference_candidate(mention):  # "they", "it", "them", "the customer"
        candidates = context.recent_entities  # Entities from recent conversation

        if not candidates:
            return ResolutionResult(entity_id=None, confidence=0.0, method='no_candidates')

        # Use LLM for coreference resolution
        llm_result = await resolve_coreference_llm(
            mention=mention,
            candidates=candidates,
            conversation_history=context.recent_messages
        )

        if llm_result.confidence > 0.7:
            # Learn from LLM decision
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

**LLM Usage (Surgical)**:
```python
async def resolve_coreference_llm(mention: str, candidates: List[Entity],
                                  conversation_history: List[Message]) -> LLMResult:
    """
    Use LLM only for coreference resolution - pronouns and contextual references.

    This is the 5% of cases where semantic understanding of conversation
    context is genuinely required.
    """
    prompt = f"""
You are resolving entity references in a business conversation.

**Mention to resolve**: "{mention}"

**Candidate entities** (from recent conversation):
{format_candidates(candidates)}

**Recent conversation**:
{format_messages(conversation_history)}

**Task**: Determine which candidate entity (if any) the mention "{mention}" refers to.

**Output** (JSON):
{{
  "entity_id": "customer:xxx" or null,
  "confidence": 0.85,
  "reasoning": "The pronoun 'they' refers to Gai Media because..."
}}
"""

    response = await llm.generate(
        prompt=prompt,
        model="gpt-4o-mini",  # Fast model sufficient for this task
        temperature=0.0,
        response_format="json"
    )

    return LLMResult.parse(response)
```

**Cost**: $0.00015 per resolution (only 5% of cases use LLM)

---

### 2. Memory Extraction (Layer 3→4 Transition)

**Vision Principle**: Transforming experience into understanding

**Algorithm**: Pattern detection + LLM semantic parsing

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
            # Check if values match
            if values_match(existing['object_value'], triple.object_value):
                # REINFORCE: Increase confidence
                new_confidence = min(0.95, existing['confidence'] + 0.08)
                await db.execute("""
                    UPDATE semantic_memories
                    SET reinforcement_count = reinforcement_count + 1,
                        confidence = $1,
                        last_validated_at = now(),
                        updated_at = now()
                    WHERE memory_id = $2
                """, new_confidence, existing['memory_id'])
            else:
                # CONFLICT: Log and decide resolution
                await handle_memory_conflict(
                    existing_memory_id=existing['memory_id'],
                    new_value=triple.object_value,
                    event_id=event.event_id
                )
        else:
            # CREATE: New semantic memory
            memory = await db.fetchrow("""
                INSERT INTO semantic_memories (
                    user_id, subject_entity_id, predicate, predicate_type,
                    object_value, confidence, confidence_factors,
                    source_type, extracted_from_event_id, embedding
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING memory_id
            """, event.user_id, triple.subject, triple.predicate, triple.predicate_type,
                 triple.object_value, triple.confidence, triple.confidence_factors,
                 'episodic', event.event_id, await embed(triple.as_text()))

            semantic_memories.append(memory)

    return ExtractionResult(semantic_memories=semantic_memories)
```

**LLM Usage (Essential)**:
```python
async def extract_triples_llm(text: str, entities: List[Entity],
                              event_type: str) -> ExtractionResult:
    """
    Use LLM for semantic parsing - extracting structured triples from natural language.

    This is genuinely hard with pattern matching. LLM excels at semantic parsing.
    """
    prompt = f"""
Extract structured knowledge triples from this statement.

**Statement**: "{text}"

**Known entities**: {format_entities(entities)}

**Task**: Extract subject-predicate-object triples representing facts, preferences, or policies.

**Examples**:
- "Gai Media prefers Friday deliveries" → (Gai Media, delivery_preference, Friday)
- "They want NET30 terms" → (Gai Media, payment_terms, NET30)
- "Always email for invoices" → (Gai Media, invoice_contact_method, email)

**Output** (JSON array):
[
  {{
    "subject_entity_id": "customer:xxx",
    "predicate": "delivery_preference",
    "predicate_type": "preference",
    "object_value": {{"type": "string", "value": "Friday"}},
    "confidence": 0.75,
    "confidence_rationale": "Explicitly stated preference"
  }}
]
"""

    response = await llm.generate(
        prompt=prompt,
        model="gpt-4o",  # Stronger model for extraction quality
        temperature=0.0,
        response_format="json"
    )

    return ExtractionResult.parse(response)
```

**Why LLM Here**: Parsing "Acme prefers Friday deliveries and NET30 terms" into structured triples is genuinely hard with patterns.

**Cost**: $0.002 per extraction (only for statements, not all messages)

---

### 3. Multi-Signal Retrieval (Scoring)

**Vision Principle**: Context is constitutive of meaning - multi-dimensional relevance

**Algorithm**: Deterministic formula (NO LLM)

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

---

### 4. Conflict Detection

**Vision Principle**: Epistemic humility - make uncertainty explicit

**Algorithm**: Deterministic pre-filtering (99%) + LLM semantic conflicts (1%)

```python
async def detect_conflicts(new_memory: SemanticMemory, query_context: QueryContext):
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
    if new_memory.subject_entity_id:
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
    # even if predicates differ
    related_memories = await db.fetch("""
        SELECT memory_id, predicate, object_value
        FROM semantic_memories
        WHERE user_id = $1
          AND subject_entity_id = $2
          AND status = 'active'
          AND predicate != $3
    """, new_memory.user_id, new_memory.subject_entity_id, new_memory.predicate)

    if related_memories:
        # Use LLM to detect semantic conflicts
        # Example: "prefers email" vs "hates electronic communication"
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

---

### 5. Consolidation (Layer 4→6 Transition)

**Vision Principle**: Graceful forgetting through compression

**Algorithm**: LLM synthesis (Essential)

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

**LLM Usage (Essential)**:
```python
async def synthesize_summary_llm(episodic: List, semantic: List,
                                 scope: ConsolidationScope) -> Summary:
    """
    Use LLM for synthesis - this is what LLMs do best.

    Reading 20+ memories and creating coherent summary requires semantic
    understanding and synthesis capability.
    """
    prompt = f"""
Synthesize a consolidated summary from these memories.

**Episodic memories** (specific events):
{format_episodic_memories(episodic)}

**Semantic memories** (extracted facts):
{format_semantic_memories(semantic)}

**Task**: Create a coherent summary that:
1. Highlights confirmed facts (mentioned multiple times with high confidence)
2. Notes patterns in interactions
3. Captures key preferences and policies
4. Identifies facts that need validation (low confidence or aged)

**Output** (JSON):
{{
  "summary_text": "Gai Media profile (3 sessions, Sept 1-15): Friday deliveries (confirmed 3x)...",
  "key_facts": {{
    "delivery_preference": {{"value": "Friday", "confidence": 0.95, "reinforced": 3}},
    "payment_terms": {{"value": "NET30", "confidence": 0.9}}
  }},
  "interaction_patterns": ["Frequent invoice status queries", "Weekly cadence"],
  "needs_validation": ["Contact person (last validated 90+ days ago)"]
}}
"""

    response = await llm.generate(
        prompt=prompt,
        model="gpt-4o",  # Quality matters for synthesis
        temperature=0.3,  # Some creativity for synthesis
        response_format="json"
    )

    return Summary.parse(response)
```

**Why LLM Essential**: Reading 20+ memories and synthesizing coherent summary is exactly what LLMs excel at.

---

## Information Flow: The Complete Pipeline

### Memory Creation Pipeline

```
1. USER MESSAGE
   ↓
2. STORE RAW EVENT (chat_events)
   ↓
3. ENTITY RESOLUTION (Layer 2)
   • Extract entity mentions from text
   • Resolve using hybrid algorithm:
     - Fast path: exact → alias → fuzzy (95%)
     - LLM path: coreference resolution (5%)
   • Create/update entity_aliases based on learned resolutions
   ↓
4. DOMAIN DATABASE QUERY (Layer 0)
   • Query current facts for resolved entities
   • Use ontology graph for multi-hop traversal
   • Capture results in domain_facts_referenced
   ↓
5. CREATE EPISODIC MEMORY (Layer 3)
   • Summary, event_type, entities (with coreference)
   • domain_facts_referenced (provenance)
   • Embed asynchronously
   ↓
6. EXTRACT SEMANTIC FACTS (Layer 3→4)
   • Pattern: Classify event type (deterministic)
   • LLM: Extract triples if statement/correction (semantic parsing)
   • Check for existing memory (subject + predicate)
   • REINFORCE if values match (confidence++, reinforcement_count++)
   • CREATE if new fact
   • CONFLICT if values differ → log in memory_conflicts
   ↓
7. DETECT PROCEDURAL PATTERNS (Background, Layer 3→5)
   • After N memories, analyze query patterns
   • Detect repeated sequences
   • Create procedural_memories for common patterns
   ↓
8. CONSOLIDATE (Triggered: N sessions or M days, Layer 4→6)
   • LLM: Synthesize summary from episodic + semantic
   • Create memory_summary
   • Boost confidence of confirmed facts (validation)
```

### Retrieval Pipeline

```
1. USER QUERY
   ↓
2. ENTITY RESOLUTION (Layer 2)
   • Extract entity mentions
   • Resolve to canonical IDs
   ↓
3. PARALLEL RETRIEVAL
   ├─→ Summaries (Layer 6): Vector search, top-5
   ├─→ Semantic (Layer 4): Vector search + entity filter, top-10
   ├─→ Episodic (Layer 3): Vector search + recency boost, top-10
   └─→ Procedural (Layer 5): Pattern match on trigger features
   ↓
4. MULTI-SIGNAL SCORING (Deterministic formula)
   • semantic_similarity × 0.4
   • entity_overlap × 0.25
   • recency × 0.2
   • importance × 0.1
   • reinforcement × 0.05
   • Multiply by effective_confidence (passive decay)
   ↓
5. DOMAIN DATABASE AUGMENTATION (Layer 0)
   • For each entity: query current facts
   • Use ontology to traverse: customer → orders → work_orders → invoices
   • Get authoritative current state
   ↓
6. CONFLICT DETECTION
   • Compare semantic memories vs DB facts
   • Deterministic: same predicate conflicts
   • LLM: semantic conflicts across predicates (rare)
   • Log in memory_conflicts if detected
   ↓
7. PASSIVE DECAY CALCULATION
   • effective_conf = stored_conf × exp(-days_since_validation × decay_rate)
   • If old + low reinforcement → mark for validation
   ↓
8. BUILD CONTEXT (Token budget allocation)
   • 40% DB facts (authoritative, always first)
   • 20% Summaries (high-level profiles)
   • 20% Semantic facts (specific preferences)
   • 15% Episodic (recent context)
   • 5% Procedural hints (suggested actions)
   ↓
9. RETURN CONTEXT + METADATA
   • Facts with provenance (memory IDs, DB sources)
   • Confidence levels per fact
   • Conflicts (if any)
   • Validation needs (aged facts)
```

---

## Where LLMs Are Used (Surgical Approach)

Based on the principle: **Use LLMs where they add clear value, deterministic systems where they excel**

| Component | Approach | Rationale |
|-----------|----------|-----------|
| **Entity Resolution** | Hybrid: Deterministic (95%) + LLM coreference (5%) | pg_trgm excellent for fuzzy matching. Only pronouns need context. |
| **Memory Extraction** | Deterministic classification + LLM triple extraction | Event types are pattern-matchable. Semantic parsing genuinely needs LLM. |
| **Query Understanding** | Pattern-based (90%) + LLM fallback (10%) | Simple patterns work most of time. LLM for compound/ambiguous queries. |
| **Retrieval Scoring** | Deterministic formula (100%) | Must be fast (<100ms). Formula works well. NO LLM. |
| **Conflict Detection** | Deterministic pre-filtering (99%) + LLM semantic (1%) | Most conflicts are obvious. LLM only for cross-predicate semantic conflicts. |
| **Consolidation** | LLM synthesis (100%) | This is what LLMs excel at. Reading and synthesizing summaries. |

### Cost Analysis

**Per Request** (assuming 1 entity resolution, 1 extraction, 1 query):
- Entity resolution: $0.00015 (5% × $0.003)
- Memory extraction: $0.002 (only on statements)
- Query understanding: $0.0001 (10% × $0.001)
- Consolidation: $0.005 (periodic, not per-request)

**Average per conversational turn**: ~$0.002

**At scale** (1,000 users × 50 turns/day):
- 50,000 turns/day
- Cost: $100/day = **$3,000/month**

**Comparison to alternatives**:
- Pure deterministic: $0/month, but 60-70% accuracy on hard cases
- Pure LLM: $15,000/month, but 90%+ accuracy
- **Surgical (this design)**: $3,000/month, 85-90% accuracy ✅

---

## What's Deferred (and Why)

### Phase 2: Useful Enhancements

**memory_state_transitions**: Track lifecycle transitions for analysis
- **Why defer**: Can reconstruct from status + updated_at + superseded_by
- **When to add**: When need detailed lifecycle analytics

**retrieval_scoring_weights per user**: Learned retrieval weights
- **Why defer**: Need usage data to learn from
- **When to add**: After Phase 1 deployed, analyze retrieval patterns

### Phase 3: Learning & Adaptation

**meta_memories**: Learn decay rates per fact type
- **Why defer**: Need 1000+ semantic memories with correction patterns
- **When to add**: When have enough data to detect fact type stability patterns

**extraction_patterns**: Improve extraction from corrections
- **Why defer**: Need significant correction data to learn patterns
- **When to add**: When extraction failures are quantified and categorized

---

## Critical Design Decisions

### Decision 1: JSONB vs Separate Tables

**Used JSONB for**:
- `entity_aliases.metadata`: Disambiguation context (variable structure)
- `episodic_memories.entities`: Coreference chains (context-specific)
- `semantic_memories.confidence_factors`: Evidence varies per memory
- `*_memories.properties`: Discovery over time (flexible)

**Used Separate Tables for**:
- `canonical_entities`: Frequently queried independently
- `semantic_memories`: Foreign key relationships, lifecycle management
- All memory layers: Independent lifecycles, fixed schema

**Philosophy**: JSONB for context-specific variable data, separate tables for core entities

### Decision 2: Passive vs Pre-Computed Decay

**Passive** (compute on-demand):
```python
effective_confidence = stored_confidence * exp(-days_since_validation * decay_rate)
```

**Why**:
- No background jobs required
- Always accurate (no stale pre-computed values)
- Simpler implementation

**Trade-off**: Can't efficiently query by effective_confidence. Acceptable - we query by stored confidence and filter in application layer.

### Decision 3: Inline Coreference Resolution

**Could have**: Separate `entity_mentions` table linking events to entities

**Did instead**: Inline in `episodic_memories.entities` JSONB

**Why**:
- Coreference is context-specific to episodic memory
- Inline storage maintains cohesion
- Avoids joins for common operation (entity extraction from episode)
- Can still query via JSONB operators if needed

### Decision 4: Procedural & Summaries are Essential

**Not optional** because:
- Vision explicitly includes Layer 5 (procedural) and Layer 6 (summaries)
- Procedural: "Procedural memory captures patterns" (Vision, Layer 5)
- Summaries: "Forgetting is essential to intelligence" (Vision, consolidation)

Removing these would violate vision, not simplify toward it.

### Decision 5: Ontology Table is Essential

**System name**: "**Ontology-Aware** Memory System"

**Vision**: "Foreign keys connect tables. Ontology connects meaning."

Without `domain_ontology`, system isn't ontology-aware - it's just a chatbot with vector search.

---

## Success Metrics

### Quantitative (Vision: "Optimize for humans")

- **Correctness**: 95%+ of DB facts cited are accurate
- **Relevance**: 90%+ of retrieved memories used in response
- **Learning**: 80%+ preference recall across sessions
- **Efficiency**: P95 latency <800ms (retrieval + generation)
- **Consistency**: 95%+ entity resolution accuracy after disambiguation

### Qualitative (Vision: "Experienced colleague")

- Users stop restating known preferences (system remembers)
- Conversations feel continuous across sessions
- Users trust responses without always verifying
- Disambiguation requests decrease over time (learning aliases)
- Users proactively correct the system (comfortable collaboration)
- System catches potential issues proactively (aged memory validation, conflicts)

### The Ultimate Test

After extended use, if the system were removed, users should feel like they **lost a knowledgeable colleague** - not just a tool, but a memory layer integrated into workflow.

---

## Implementation Roadmap

### Phase 1A: Foundation (Week 1-2)

**Tables**: chat_events, canonical_entities, entity_aliases, system_config

**Capabilities**:
- Store conversations
- Entity resolution (exact, alias, fuzzy, lazy creation)
- Basic domain DB queries

**Deliverable**: Can store events and resolve entities

### Phase 1B: Memory Core (Week 3-4)

**Add**: episodic_memories, semantic_memories

**Capabilities**:
- Create episodic memories from events
- Extract semantic facts (with LLM)
- Reinforce existing memories
- Basic vector search retrieval

**Deliverable**: Can remember and retrieve facts

### Phase 1C: Intelligence (Week 5-6)

**Add**: domain_ontology, memory_conflicts

**Capabilities**:
- Ontology-aware graph traversal
- Multi-signal retrieval scoring
- Conflict detection and logging
- Passive decay calculation

**Deliverable**: Can reason about business relationships and handle uncertainty

### Phase 1D: Learning (Week 7-8)

**Add**: procedural_memories, memory_summaries

**Capabilities**:
- Detect procedural patterns (basic)
- Consolidate memories into summaries
- Confidence boosting from validation
- Complete memory lifecycle

**Deliverable**: Full vision implementation, ready for production

---

## Closing: Every Decision Serves the Vision

This design embodies the vision's core principles:

1. **Dual Truth**: Database (Layer 0) + Memory (Layers 1-6) in equilibrium
2. **Memory Transformation**: Episodic → Semantic → Procedural → Summaries
3. **Epistemic Humility**: Confidence tracking, conflict detection, validation
4. **Graceful Forgetting**: Passive decay, consolidation, status lifecycle
5. **Explainability**: Provenance chains, reasoning traces, source attribution
6. **Ontology-Awareness**: Semantic relationships, graph traversal, business logic
7. **Continuous Learning**: Alias learning, reinforcement, pattern detection

**Complexity that serves vision**: Kept (procedural, summaries, ontology, conflicts)

**Complexity that doesn't**: Removed or deferred (pre-computed decay, redundant fields, separate disambiguation table)

**LLM usage**: Surgical - only where semantic understanding genuinely adds value

**Result**: 10 essential tables that enable an LLM to behave like **an experienced colleague who has worked with this company for years**.

---

**The North Star**: Memory is the transformation of experience into understanding. This design gives an LLM agent the foundation of intelligence itself - memory that learns, adapts, and evolves while remaining anchored in truth.
