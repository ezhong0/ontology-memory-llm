# Phase 1 Implementation Roadmap

**Version**: 2.0 - Aligned with DESIGN.md v2.0
**Status**: Ready for Implementation
**Estimated Duration**: 8 weeks (2 months)
**Target**: Production-ready MVP with all essential features

---

## Executive Summary

This roadmap details the implementation of Phase 1 essential features for the Ontology-Aware Memory System, aligned with the ground-up redesign (DESIGN.md v2.0).

**What Phase 1 Delivers**:
- 10 core database tables implementing layered memory architecture
- Hybrid entity resolution (deterministic 95% + LLM coreference 5%)
- Memory transformation pipeline (Raw → Episodic → Semantic → Procedural → Summaries)
- Multi-signal retrieval system (deterministic formula, <100ms)
- Surgical LLM integration ($3,000/month at scale)
- Full conversation-to-memory-to-retrieval flow

**What Phase 1 Defers**:
- Learning from operational data (requires data collection)
- Per-user weight tuning (Phase 2)
- Meta-memory and adaptive decay rates (Phase 3)

**Key Design Principles** (from DESIGN.md v2.0):
- **Dual Truth**: Database (Layer 0) + Memory (Layers 1-6) in equilibrium
- **Surgical LLM Use**: Deterministic where it excels, LLM only where it adds clear value
- **Passive Computation**: Calculate on-demand (decay, effective confidence)
- **Vision-Driven**: Every table and algorithm serves explicit vision principles

---

## Prerequisites and Setup

### Technical Requirements

**Infrastructure**:
- PostgreSQL 15+ with pgvector extension
- PostgreSQL pg_trgm extension (for fuzzy text matching)
- Python 3.11+ (or Node.js 18+ if TypeScript implementation)
- Redis (optional, for caching entity resolutions)
- OpenAI API access (for embeddings and LLM extraction)

**Development Environment**:
- Docker and Docker Compose for local development
- Database migration tool (Alembic for Python, Prisma for TypeScript)
- Testing framework (pytest/jest)
- API documentation (OpenAPI/Swagger)

**Domain Database Access**:
- Read-only connection to existing domain database
- Database schema documentation
- Sample queries for common entity types

### Team Composition

**Recommended Team** (can scale up/down):
- **Backend Engineer** (2 FTE): Core system implementation
- **Database Engineer** (0.5 FTE): Schema design, optimization
- **ML Engineer** (0.5 FTE): Embedding pipeline, LLM integration
- **QA Engineer** (0.5 FTE): Testing, quality assurance
- **Product Manager** (0.25 FTE): Requirements, prioritization

**Single-person implementation possible**: Extend timeline to 12-14 weeks

### Pre-Implementation Tasks (Week 0)

**Task 0.1: Repository Setup**
- [ ] Initialize Git repository with branching strategy
- [ ] Set up development, staging, production environments
- [ ] Configure CI/CD pipeline (GitHub Actions, GitLab CI, etc.)
- [ ] Set up code quality tools (linters, formatters)

**Task 0.2: Database Setup**
- [ ] Provision PostgreSQL database (local + cloud)
- [ ] Install pgvector extension
- [ ] Install pg_trgm extension
- [ ] Create database schemas (`app` and `domain`)
- [ ] Set up migration framework

**Task 0.3: Domain Database Integration**
- [ ] Obtain read-only access to domain database
- [ ] Document domain schema (tables, relationships, constraints)
- [ ] Create domain ontology mapping (customer → orders → invoices, etc.)
- [ ] Write sample queries for each entity type

**Task 0.4: API Foundation**
- [ ] Choose framework (FastAPI/Flask/Express/NestJS)
- [ ] Set up project structure
- [ ] Configure logging and error handling
- [ ] Set up OpenAPI documentation

**Deliverable**: Development environment ready, team onboarded, domain database accessible

---

## Phase 1A: Foundation (Week 1-2)

### Milestone: Core schema + Entity resolution operational

**Vision Principles**: Provenance, problem of reference

---

### Week 1: Database Schema and Migrations

**Task 1A.1: Create Migration Files** (Day 1-2)

Implement Layer 1 (Raw Events) and Layer 2 (Entity Resolution) tables:

```sql
-- Migration 001: Layer 1 - Raw Events
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

-- Migration 002: Layer 2 - Entity Resolution
CREATE TABLE app.canonical_entities (
  entity_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  canonical_name TEXT NOT NULL,
  external_ref JSONB NOT NULL,
  properties JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_entities_type ON app.canonical_entities(entity_type);
CREATE INDEX idx_entities_name ON app.canonical_entities(canonical_name);

CREATE TABLE app.entity_aliases (
  alias_id BIGSERIAL PRIMARY KEY,
  canonical_entity_id TEXT NOT NULL REFERENCES app.canonical_entities(entity_id),
  alias_text TEXT NOT NULL,
  alias_source TEXT NOT NULL,
  user_id TEXT,
  confidence REAL NOT NULL DEFAULT 1.0,
  use_count INT NOT NULL DEFAULT 1,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(alias_text, user_id, canonical_entity_id)
);

CREATE INDEX idx_aliases_lookup ON app.entity_aliases(alias_text, user_id, confidence DESC);
CREATE INDEX idx_aliases_entity ON app.entity_aliases(canonical_entity_id);
CREATE INDEX idx_aliases_trigram ON app.entity_aliases USING gin(alias_text gin_trgm_ops);

-- Migration 003: System Configuration
CREATE TABLE app.system_config (
  config_key TEXT PRIMARY KEY,
  config_value JSONB NOT NULL,
  description TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Task 1A.2: Seed Data** (Day 3)

```sql
-- Seed system_config with Phase 1 parameters
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

**Task 1A.3: Domain Ontology Mapping** (Day 4-5)

Map domain database relationships into `domain_ontology` table:

```sql
-- Migration 004: Domain Ontology
CREATE TABLE app.domain_ontology (
  relation_id BIGSERIAL PRIMARY KEY,
  from_entity_type TEXT NOT NULL,
  relation_type TEXT NOT NULL,
  to_entity_type TEXT NOT NULL,
  cardinality TEXT NOT NULL,
  relation_semantics TEXT NOT NULL,
  join_spec JSONB NOT NULL,
  constraints JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(from_entity_type, relation_type, to_entity_type)
);

-- Example: customer → sales_orders relationship
INSERT INTO app.domain_ontology VALUES
(
  DEFAULT,
  'customer',
  'HAS_MANY',
  'sales_order',
  'one_to_many',
  'Customer places sales orders for fulfillment',
  jsonb_build_object(
    'from_table', 'domain.customers',
    'to_table', 'domain.sales_orders',
    'on', 'domain.customers.customer_id = domain.sales_orders.customer_id'
  ),
  jsonb_build_object(
    'lifecycle', 'sales_order must have valid customer_id'
  )
);
```

**Task 1A.4: Schema Validation** (Day 6-7)

- [ ] Run all migrations on clean database
- [ ] Verify all tables created correctly
- [ ] Verify all indexes created
- [ ] Run rollback tests (migration down)
- [ ] Document any schema deviations from design

**Deliverable**:
- ✅ Layer 1 and Layer 2 tables created
- ✅ All indexes in place
- ✅ system_config seeded
- ✅ domain_ontology mapped
- ✅ Schema tests passing

---

### Week 2: Entity Resolution System

**Task 1A.5: Canonical Entity Management** (Day 1-3)

Implement lazy entity creation:

```python
class CanonicalEntityService:
    async def ensure_canonical_entity(
        self,
        entity_type: str,
        external_ref: dict,
        canonical_name: str,
        properties: dict | None = None
    ) -> CanonicalEntity:
        """
        Create canonical entity or return existing.
        Idempotent: (entity_type, external_ref) is natural key.
        Lazy creation: Create on-demand when first mentioned.
        """
        # Check if exists
        existing = await self.db.fetchrow("""
            SELECT * FROM app.canonical_entities
            WHERE entity_type = $1 AND external_ref = $2
        """, entity_type, external_ref)

        if existing:
            return CanonicalEntity(**existing)

        # Create new (lazy)
        entity_id = f"{entity_type}:{uuid4()}"
        await self.db.execute("""
            INSERT INTO app.canonical_entities
            (entity_id, entity_type, canonical_name, external_ref, properties)
            VALUES ($1, $2, $3, $4, $5)
        """, entity_id, entity_type, canonical_name, external_ref, properties)

        return await self.get_entity(entity_id)
```

**Task 1A.6: Entity Alias Management** (Day 4-6)

Self-improving alias system:

```python
class EntityAliasService:
    async def learn_alias(
        self,
        canonical_entity_id: str,
        alias_text: str,
        alias_source: str,
        user_id: str | None,
        confidence: float,
        metadata: dict | None = None
    ) -> EntityAlias:
        """Create or update entity alias. Self-improving."""
        await self.db.execute("""
            INSERT INTO app.entity_aliases
            (canonical_entity_id, alias_text, alias_source, user_id, confidence, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (alias_text, user_id, canonical_entity_id) DO UPDATE SET
              use_count = app.entity_aliases.use_count + 1,
              confidence = LEAST(0.95, app.entity_aliases.confidence + 0.02)
        """, canonical_entity_id, alias_text, alias_source, user_id, confidence, metadata)
```

**Task 1A.7: Hybrid Resolution Algorithm** (Day 7-12)

Implement deterministic fast path + LLM coreference (from DESIGN.md):

```python
async def resolve_entity(mention: str, user_id: str, context: ConversationContext) -> ResolutionResult:
    """
    Hybrid entity resolution: deterministic for 95%, LLM for coreference (5%).
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

**Task 1A.8: Domain Database Integration** (Day 13-14)

```python
class DomainDatabaseService:
    async def search_entities(
        self,
        mention_text: str,
        entity_type_hint: str | None = None
    ) -> List[DomainEntity]:
        """Search domain database for matching entities using pg_trgm."""
        if entity_type_hint == "customer":
            return await self.db.fetch("""
                SELECT customer_id, name, industry
                FROM domain.customers
                WHERE name ILIKE $1 OR similarity(name, $2) > 0.7
                ORDER BY similarity(name, $2) DESC
                LIMIT 5
            """, f"%{mention_text}%", mention_text)

        # Use domain_ontology to determine which tables to search
        ...
```

**Deliverable**:
- ✅ Hybrid entity resolution working end-to-end
- ✅ Deterministic fast path (exact, alias, fuzzy) implemented
- ✅ LLM coreference resolution functional
- ✅ Domain database integration operational
- ✅ 95%+ test coverage on resolution logic
- ✅ Performance: <50ms for fast path, <300ms for LLM path

---

## Phase 1B: Memory Core (Week 3-4)

### Milestone: Episodic → Semantic transformation working

**Vision Principles**: Events with meaning, contextual truth, epistemic humility

---

### Week 3: Memory Schema and Episodic Memories

**Task 1B.1: Create Memory Tables** (Day 1-2)

```sql
-- Migration 005: Layer 3 - Episodic Memory
CREATE TABLE app.episodic_memories (
  memory_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  session_id UUID NOT NULL,

  summary TEXT NOT NULL,
  event_type TEXT NOT NULL,
  source_event_ids BIGINT[] NOT NULL,

  entities JSONB NOT NULL,
  domain_facts_referenced JSONB,

  importance REAL NOT NULL DEFAULT 0.5,
  embedding vector(1536),

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_episodic_user_time ON app.episodic_memories(user_id, created_at DESC);
CREATE INDEX idx_episodic_session ON app.episodic_memories(session_id);
CREATE INDEX idx_episodic_embedding ON app.episodic_memories
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Migration 006: Layer 4 - Semantic Memory
CREATE TABLE app.semantic_memories (
  memory_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,

  subject_entity_id TEXT REFERENCES app.canonical_entities(entity_id),
  predicate TEXT NOT NULL,
  predicate_type TEXT NOT NULL,
  object_value JSONB NOT NULL,

  confidence REAL NOT NULL DEFAULT 0.7,
  confidence_factors JSONB,
  reinforcement_count INT NOT NULL DEFAULT 1,
  last_validated_at TIMESTAMPTZ,

  source_type TEXT NOT NULL,
  source_memory_id BIGINT,
  extracted_from_event_id BIGINT REFERENCES app.chat_events(event_id),

  status TEXT NOT NULL DEFAULT 'active',
  superseded_by_memory_id BIGINT REFERENCES app.semantic_memories(memory_id),

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

**Task 1B.2: Chat Event Storage** (Day 3-4)

```python
class ChatEventService:
    async def store_event(
        self,
        session_id: UUID,
        user_id: str,
        role: str,
        content: str,
        metadata: dict | None = None
    ) -> ChatEvent:
        """Store raw chat event (idempotent)."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]

        try:
            event = await self.db.fetchrow("""
                INSERT INTO app.chat_events
                (session_id, user_id, role, content, content_hash, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
            """, session_id, user_id, role, content, content_hash, metadata)
            return ChatEvent(**event)
        except UniqueViolationError:
            # Idempotent: return existing
            return await self.get_by_hash(session_id, content_hash)
```

**Task 1B.3: Episodic Memory Creation** (Day 5-8)

```python
class EpisodicMemoryService:
    async def create_from_event(
        self,
        event: ChatEvent,
        resolved_entities: List[ResolvedEntity],
        domain_facts: dict | None = None
    ) -> EpisodicMemory:
        """Create episodic memory from event."""

        # Classify event type (deterministic patterns)
        event_type = classify_event_type(event.content)

        # Generate summary
        summary = await self._generate_summary(event.content, resolved_entities)

        # Compute importance
        importance = self._compute_importance(
            event_type=event_type,
            entity_count=len(resolved_entities),
            has_domain_facts=bool(domain_facts)
        )

        # Create memory
        memory = await self.db.fetchrow("""
            INSERT INTO app.episodic_memories
            (user_id, session_id, summary, event_type, source_event_ids,
             entities, domain_facts_referenced, importance)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """, event.user_id, event.session_id, summary,
            event_type, [event.event_id],
            self._format_entities(resolved_entities),
            domain_facts, importance)

        # Async: Generate embedding
        await self.embedding_queue.enqueue(memory['memory_id'], summary)

        return EpisodicMemory(**memory)

    def _compute_importance(self, event_type, entity_count, has_domain_facts):
        """From DESIGN.md importance calculation"""
        base = {
            'question': 0.4,
            'statement': 0.6,
            'command': 0.7,
            'correction': 0.9,
            'confirmation': 0.8
        }[event_type]

        entity_boost = min(0.2, entity_count * 0.05)
        db_boost = 0.1 if has_domain_facts else 0.0

        return max(0.0, min(1.0, base + entity_boost + db_boost))
```

**Deliverable**:
- ✅ Memory schema created
- ✅ Chat event storage operational
- ✅ Episodic memory creation working
- ✅ Event type classification functional
- ✅ Importance calculation implemented

---

### Week 4: Semantic Memory Extraction

**Task 1B.4: LLM-Based Memory Extraction** (Day 1-5)

Pattern detection + LLM semantic parsing (from DESIGN.md):

```python
async def extract_memories(event: ChatEvent, entities: List[Entity]) -> ExtractionResult:
    """
    Extract semantic facts from episodic events.
    Deterministic patterns for event classification,
    LLM for semantic parsing.
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
                # REINFORCE
                await reinforce_memory(existing['memory_id'])
            else:
                # CONFLICT
                await handle_memory_conflict(existing, triple, event)
        else:
            # CREATE NEW
            memory = await create_semantic_memory(triple, event)
            semantic_memories.append(memory)

    return ExtractionResult(semantic_memories=semantic_memories)
```

**LLM Extraction Prompt**:

```python
async def extract_triples_llm(text: str, entities: List[Entity],
                              event_type: str) -> ExtractionResult:
    """
    Use LLM for semantic parsing - extracting structured triples.
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

**Task 1B.5: Reinforcement Logic** (Day 6-8)

```python
async def reinforce_memory(memory_id: int):
    """Apply reinforcement boost"""
    await db.execute("""
        UPDATE semantic_memories
        SET reinforcement_count = reinforcement_count + 1,
            confidence = LEAST(0.95, confidence + 0.08),
            last_validated_at = now(),
            status = 'active',
            updated_at = now()
        WHERE memory_id = $1
    """, memory_id)
```

**Task 1B.6: Embedding Pipeline** (Day 9-10)

```python
class EmbeddingService:
    async def generate_and_store(
        self,
        memory_id: int,
        memory_type: str,
        text: str
    ):
        """Generate embedding and update memory."""
        embedding = await self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )

        vector = embedding.data[0].embedding

        table_map = {
            "episodic": "app.episodic_memories",
            "semantic": "app.semantic_memories",
            "procedural": "app.procedural_memories",
            "summary": "app.memory_summaries"
        }

        await self.db.execute(f"""
            UPDATE {table_map[memory_type]}
            SET embedding = $1
            WHERE memory_id = $2
        """, vector, memory_id)
```

**Deliverable**:
- ✅ LLM semantic extraction working
- ✅ Triple extraction functional
- ✅ Reinforcement logic operational
- ✅ Embedding generation pipeline
- ✅ End-to-end tests: event → episodic → semantic

---

## Phase 1C: Intelligence (Week 5-6)

### Milestone: Multi-signal retrieval + Conflict detection operational

**Vision Principles**: Ontology-awareness, epistemic humility

---

### Week 5: Retrieval System

**Task 1C.1: Conflict Detection Schema** (Day 1)

```sql
-- Migration 007: Conflict Detection
CREATE TABLE app.memory_conflicts (
  conflict_id BIGSERIAL PRIMARY KEY,
  detected_at_event_id BIGINT NOT NULL REFERENCES app.chat_events(event_id),

  conflict_type TEXT NOT NULL,
  conflict_data JSONB NOT NULL,

  resolution_strategy TEXT,
  resolution_outcome JSONB,
  resolved_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conflicts_event ON app.memory_conflicts(detected_at_event_id);
CREATE INDEX idx_conflicts_unresolved ON app.memory_conflicts(resolved_at) WHERE resolved_at IS NULL;
```

**Task 1C.2: Candidate Generation** (Day 2-5)

Parallel retrieval from all layers:

```python
class CandidateGenerator:
    async def generate(
        self,
        query_embedding: np.ndarray,
        query_entities: List[str],
        user_id: str
    ) -> List[MemoryCandidate]:
        """Generate candidates from multiple sources in parallel."""

        # Parallel retrieval using pgvector
        semantic_search = await self._semantic_similarity(query_embedding, user_id, limit=50)
        entity_search = await self._entity_overlap(query_entities, user_id, limit=30) if query_entities else []

        # Combine and deduplicate
        all_candidates = semantic_search + entity_search
        unique = {c.memory_id: c for c in all_candidates}
        return list(unique.values())

    async def _semantic_similarity(self, embedding, user_id, limit):
        """Semantic search using pgvector"""
        results = await self.db.fetch("""
            SELECT memory_id, memory_type, summary_text, entities,
                   importance, created_at, embedding,
                   1 - (embedding <=> $1) AS cosine_similarity
            FROM (
              SELECT memory_id, 'episodic' AS memory_type, summary AS summary_text,
                     entities, importance, embedding, created_at
              FROM app.episodic_memories WHERE user_id = $2
              UNION ALL
              SELECT memory_id, 'semantic' AS memory_type,
                     subject_entity_id || ' ' || predicate AS summary_text,
                     jsonb_build_array(jsonb_build_object('canonical_id', subject_entity_id)) AS entities,
                     importance, embedding, created_at
              FROM app.semantic_memories WHERE user_id = $2 AND status = 'active'
            ) AS all_memories
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1
            LIMIT $3
        """, embedding, user_id, limit)

        return [MemoryCandidate(**r) for r in results]
```

**Task 1C.3: Multi-Signal Scoring** (Day 6-8)

Deterministic formula (NO LLM):

```python
def score_memory_relevance(memory: Memory, query: Query) -> float:
    """
    Multi-signal relevance scoring using weighted formula.
    NO LLM: Would be too slow (need to score 100+ candidates in <100ms)
    """
    weights = get_config('multi_signal_weights')

    # Signal 1: Semantic similarity
    semantic_score = 1 - cosine_distance(memory.embedding, query.embedding)

    # Signal 2: Entity overlap (Jaccard)
    entity_score = jaccard(memory.entities, query.entities)

    # Signal 3: Recency (exponential decay)
    age_days = (now() - memory.created_at).days
    half_life = 30 if memory.type == 'episodic' else 90
    recency_score = exp(-age_days * ln(2) / half_life)

    # Signal 4: Importance
    importance_score = memory.importance

    # Signal 5: Reinforcement
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

**Task 1C.4: Passive Decay Calculation** (Day 9-10)

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

**Deliverable**:
- ✅ Parallel candidate generation working
- ✅ Multi-signal scoring implemented
- ✅ Passive decay calculation operational
- ✅ Performance: <100ms total retrieval latency

---

### Week 6: Conflict Detection and Ontology

**Task 1C.5: Conflict Detection** (Day 1-4)

Deterministic pre-filtering (99%) + LLM semantic (1%):

```python
async def detect_conflicts(new_memory: SemanticMemory):
    """
    Deterministic for obvious conflicts (same predicate),
    LLM only for semantic conflicts across different predicates.
    """

    # ═══════════════════════════════════════════════════════════
    # DETERMINISTIC: Same predicate conflicts (99% of conflicts)
    # ═══════════════════════════════════════════════════════════

    existing = await db.fetch("""
        SELECT memory_id, object_value, confidence
        FROM semantic_memories
        WHERE user_id = $1
          AND subject_entity_id = $2
          AND predicate = $3
          AND status = 'active'
    """, new_memory.user_id, new_memory.subject_entity_id, new_memory.predicate)

    for mem in existing:
        if not values_match(mem['object_value'], new_memory.object_value):
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
        await log_conflict(
            conflict_type='memory_vs_db',
            memory_id=new_memory.memory_id,
            db_source=db_value.source,
            resolution_strategy='trust_db'
        )
```

**Task 1C.6: Ontology-Aware Traversal** (Day 5-8)

```python
class OntologyService:
    async def traverse_graph(
        self,
        entity_id: str,
        max_hops: int = 2
    ) -> Dict[str, Any]:
        """
        Traverse domain graph using ontology relationships.
        Vision: Foreign keys connect tables. Ontology connects meaning.
        """
        entity_type = entity_id.split(':')[0]

        # Get all relationships for this entity type
        relations = await self.db.fetch("""
            SELECT relation_type, to_entity_type, relation_semantics, join_spec
            FROM domain_ontology
            WHERE from_entity_type = $1
        """, entity_type)

        graph = {entity_id: {}}

        for rel in relations:
            # Execute domain query based on join_spec
            related = await self._execute_ontology_query(entity_id, rel)
            graph[entity_id][rel['relation_type']] = related

        return graph
```

**Task 1C.7: Integration Testing** (Day 9-10)

End-to-end test: conversation → memories → retrieval → conflicts

**Deliverable**:
- ✅ Conflict detection operational
- ✅ Ontology-aware graph traversal working
- ✅ Complete retrieval pipeline functional
- ✅ Integration tests passing

---

## Phase 1D: Learning (Week 7-8)

### Milestone: Consolidation + Procedural patterns operational

**Vision Principles**: Learning from patterns, graceful forgetting

---

### Week 7: Procedural Memory and Patterns

**Task 1D.1: Procedural Memory Schema** (Day 1-2)

```sql
-- Migration 008: Layer 5 - Procedural Memory
CREATE TABLE app.procedural_memories (
  memory_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,

  trigger_pattern TEXT NOT NULL,
  trigger_features JSONB NOT NULL,

  action_heuristic TEXT NOT NULL,
  action_structure JSONB NOT NULL,

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

-- Migration 009: Layer 6 - Memory Summaries
CREATE TABLE app.memory_summaries (
  summary_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,

  scope_type TEXT NOT NULL,
  scope_identifier TEXT,

  summary_text TEXT NOT NULL,
  key_facts JSONB NOT NULL,

  source_data JSONB NOT NULL,
  supersedes_summary_id BIGINT REFERENCES app.memory_summaries(summary_id),

  confidence REAL NOT NULL DEFAULT 0.8,
  embedding vector(1536),

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_summaries_user_scope ON app.memory_summaries(user_id, scope_type, scope_identifier);
CREATE INDEX idx_summaries_embedding ON app.memory_summaries
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Task 1D.2: Pattern Detection** (Day 3-6)

Basic procedural pattern detection:

```python
class PatternDetector:
    async def detect_query_patterns(self, user_id: str):
        """
        Detect repeated query patterns.
        Basic implementation: look for common (intent, entities, topics) sequences.
        """
        # Analyze recent episodic memories
        episodes = await self.db.fetch("""
            SELECT event_type, entities, summary
            FROM episodic_memories
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 100
        """, user_id)

        # Look for patterns (simple frequency analysis)
        patterns = self._analyze_sequences(episodes)

        # Create procedural memories for high-confidence patterns
        for pattern in patterns:
            if pattern.confidence > 0.7:
                await self._create_procedural_memory(pattern)
```

**Deliverable**:
- ✅ Procedural memory schema created
- ✅ Basic pattern detection operational
- ✅ Procedural memory creation working

---

### Week 8: Consolidation and Production Readiness

**Task 1D.3: Consolidation (LLM Synthesis)** (Day 1-4)

```python
async def consolidate_memories(user_id: str, scope: ConsolidationScope) -> MemorySummary:
    """
    Consolidate episodic and semantic memories into summary.
    LLM synthesis: this is exactly what LLMs excel at.
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

**Task 1D.4: API Implementation** (Day 5-6)

Core chat endpoint orchestrating full pipeline:

```python
@router.post("/api/v1/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
) -> ChatResponse:
    """Primary conversation interface - orchestrates full pipeline."""

    # 1. Store event
    event = await chat_service.store_event(...)

    # 2. Entity resolution
    resolved_entities = await resolver.resolve_all(...)

    # 3. Domain database query
    domain_results = await domain_service.query(...)

    # 4. Create episodic memory
    episodic = await episodic_service.create_from_event(...)

    # 5. Extract semantic memories
    semantic_memories = await semantic_service.extract_from_episodic(...)

    # 6. Retrieve relevant memories
    retrieved_memories = await retriever.retrieve(...)

    # 7. Format context for LLM
    memory_context = context_formatter.format(...)

    # 8. Generate response
    llm_response = await llm_service.generate_response(...)

    # 9. Store assistant response
    assistant_event = await chat_service.store_event(...)

    return ChatResponse(...)
```

**Task 1D.5: Testing and Documentation** (Day 7-8)

- [ ] Unit tests: 90%+ coverage
- [ ] Integration tests: Full pipeline
- [ ] Performance tests: <800ms P95 latency
- [ ] API documentation: OpenAPI spec
- [ ] Deployment guide
- [ ] Operational runbooks

**Deliverable**:
- ✅ Consolidation working
- ✅ All API endpoints implemented
- ✅ Comprehensive tests passing
- ✅ Documentation complete
- ✅ Ready for production deployment

---

## Success Criteria

### Functional Requirements

- [ ] User can have a conversation and system creates memories
- [ ] User can query for information and system retrieves relevant memories
- [ ] Entity resolution works with >90% accuracy (after disambiguation)
- [ ] Semantic facts are extracted correctly from statements
- [ ] Conflicts are detected and logged
- [ ] Memory confidence decays over time (passive computation)
- [ ] Domain database queries return correct results
- [ ] Consolidation creates accurate summaries
- [ ] All 10 API endpoints functional

### Performance Requirements

- [ ] /chat endpoint: P95 < 800ms
- [ ] Semantic search: P95 < 50ms
- [ ] Entity resolution: P95 < 100ms (fast path), < 300ms (LLM)
- [ ] System handles 100 concurrent users
- [ ] Database query performance acceptable (<100ms P95)

### Quality Requirements

- [ ] 90%+ code coverage
- [ ] All integration tests passing
- [ ] API documentation complete
- [ ] Security audit passed
- [ ] No critical bugs in production

### Cost Requirements

- [ ] LLM costs within budget (~$0.002 per turn)
- [ ] At scale: ~$3,000/month for 1,000 users × 50 turns/day
- [ ] 10x cheaper than pure LLM approach
- [ ] 85-90% accuracy (vs 90%+ pure LLM, 70% pure deterministic)

---

## LLM Usage Summary (Surgical Approach)

| Component | Approach | Cost per Use |
|-----------|----------|--------------|
| **Entity Resolution** | Deterministic (95%) + LLM coreference (5%) | $0.00015 avg |
| **Memory Extraction** | Pattern classification + LLM triple parsing | $0.002 (statements only) |
| **Query Understanding** | Patterns (90%) + LLM fallback (10%) | $0.0001 avg |
| **Retrieval Scoring** | Deterministic formula (100%) | $0 |
| **Conflict Detection** | Deterministic (99%) + LLM semantic (1%) | $0.00002 avg |
| **Consolidation** | LLM synthesis (100%) | $0.005 (periodic) |

**Average cost per conversational turn**: ~$0.002

---

## Risk Management

### High-Risk Items

**Risk 1: LLM Extraction Quality**
- **Probability**: Medium
- **Impact**: High
- **Mitigation**:
  - Start with simple extraction patterns
  - Build extensive test cases
  - Log all extractions for analysis
  - Iterate on prompts based on failures

**Risk 2: pgvector Performance at Scale**
- **Probability**: Low
- **Impact**: Medium
- **Mitigation**:
  - Start performance testing early (Week 5)
  - Benchmark with realistic data volumes
  - Plan for index tuning
  - Have fallback plan (dedicated vector DB)

**Risk 3: Domain Database Integration Complexity**
- **Probability**: High
- **Impact**: High
- **Mitigation**:
  - Start with schema documentation in Week 0
  - Create mock domain database for testing
  - Allocate extra time for ontology mapping

---

## Phase 1 to Phase 2 Transition

### Data Collection Requirements

During Phase 1 operation, collect:

**For Phase 2 Calibration**:
- All retrieval events (query, retrieved memories, user actions)
- All entity resolution events (stage, confidence, disambiguations)
- All memory corrections (what changed, when)
- All consolidation events (sources, resulting summary)
- Retrieval feedback (which memories proved useful)

**Minimum data for Phase 2**:
- 100+ semantic memories with lifecycle events
- 500+ retrieval events
- 100+ entity resolution events
- 50+ user corrections

**Phase 2 Trigger**: When minimum thresholds reached (typically 1-3 months of operation)

---

## Conclusion

This roadmap provides a realistic **8-week path** to a production-ready Phase 1 MVP that embodies all core vision principles.

**Key Success Factors**:
1. **Focus**: Build only Phase 1 essentials, defer everything else
2. **Surgical LLM Use**: Deterministic where it excels, LLM only where it adds clear value
3. **Testing**: Comprehensive testing at every stage
4. **Vision-Driven**: Every decision traceable to VISION.md and DESIGN_PHILOSOPHY.md

**Cost-Effectiveness**:
- ~$3,000/month at scale (vs $15,000 pure LLM)
- 85-90% accuracy (vs 90%+ pure LLM, 70% pure deterministic)
- Sweet spot: balance of cost and quality

**Next Steps After Phase 1**:
- Operate system for 1-3 months to collect data
- Analyze collected data against heuristics
- Begin Phase 2: Calibrate all numeric parameters using real operational data
- Implement learning features (signal weight tuning, adaptive decay rates, etc.)

**The vision is ambitious. Phase 1 makes it real.**
