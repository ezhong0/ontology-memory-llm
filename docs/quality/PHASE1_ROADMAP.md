# Phase 1 Implementation Roadmap

**Version**: 1.0
**Status**: Ready for Implementation
**Estimated Duration**: 10-12 weeks (2.5-3 months)
**Target**: Production-ready MVP with all essential features

---

## Executive Summary

This roadmap details the implementation of Phase 1 essential features for the Ontology-Aware Memory System. Phase 1 focuses on building a **functional MVP** that embodies the core vision principles without learning/optimization features.

**What Phase 1 Delivers**:
- 10 core database tables with all relationships
- Complete entity resolution (5-stage algorithm)
- Memory transformation pipeline (Raw → Episodic → Semantic → Procedural → Summaries)
- Multi-signal retrieval system (3-stage architecture)
- 10 essential API endpoints
- Full conversation-to-memory-to-retrieval flow

**What Phase 1 Defers**:
- Learning from operational data (requires data collection)
- Per-user weight tuning (Phase 2)
- Meta-memory and adaptive decay rates (Phase 3)

---

## Prerequisites and Setup

### Technical Requirements

**Infrastructure**:
- PostgreSQL 15+ with pgvector extension
- Python 3.11+ (or Node.js 18+ if TypeScript implementation)
- Redis (for caching entity resolutions)
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
- **ML Engineer** (0.5 FTE): Embedding pipeline, entity resolution
- **QA Engineer** (0.5 FTE): Testing, quality assurance
- **Product Manager** (0.25 FTE): Requirements, prioritization

**Single-person implementation possible**: Extend timeline to 16-20 weeks

### Pre-Implementation Tasks (Week 0)

**Task 1.1: Repository Setup**
- [ ] Initialize Git repository with branching strategy
- [ ] Set up development, staging, production environments
- [ ] Configure CI/CD pipeline (GitHub Actions, GitLab CI, etc.)
- [ ] Set up code quality tools (linters, formatters)

**Task 1.2: Database Setup**
- [ ] Provision PostgreSQL database (local + cloud)
- [ ] Install pgvector extension
- [ ] Create database schemas (`app` and `domain`)
- [ ] Set up migration framework

**Task 1.3: Domain Database Integration**
- [ ] Obtain read-only access to domain database
- [ ] Document domain schema (tables, relationships, constraints)
- [ ] Create domain ontology mapping (customer → orders → invoices, etc.)
- [ ] Write sample queries for each entity type

**Task 1.4: API Foundation**
- [ ] Choose framework (FastAPI/Flask/Express/NestJS)
- [ ] Set up project structure
- [ ] Configure logging and error handling
- [ ] Set up OpenAPI documentation

**Deliverable**: Development environment ready, team onboarded, domain database accessible

---

## Week 1-2: Database Schema and Migrations

### Milestone: Core schema implemented with all tables and relationships

**Task 2.1: Create Migration Files** (Day 1-2)

Implement all 10 core tables from DESIGN.md:

```python
# Migration 001: Layer 1 - Raw Events
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

**All Migrations**:
- Migration 001: `chat_events`
- Migration 002: `canonical_entities`, `entity_aliases`
- Migration 003: `episodic_memories`
- Migration 004: `semantic_memories`
- Migration 005: `procedural_memories` (stub for Phase 2)
- Migration 006: `memory_summaries` (stub for Phase 2)
- Migration 007: `domain_ontology`
- Migration 008: `memory_conflicts`
- Migration 009: `system_config`
- Migration 010: All indexes (pgvector, GIN, B-tree)

**Task 2.2: Seed Data** (Day 3)

```python
# Seed system_config with Phase 1 heuristics
INSERT INTO app.system_config VALUES
  ('embedding', '{"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536}'),
  ('retrieval_limits', '{"summaries": 5, "semantic": 10, "episodic": 10}'),
  ('confidence_thresholds', '{"high": 0.85, "medium": 0.6, "low": 0.4}'),
  ('decay', '{"default_rate_per_day": 0.01, "validation_threshold_days": 90}'),
  ('retrieval_weights_factual', '{"semantic_similarity": 0.25, "entity_overlap": 0.40, "temporal_relevance": 0.20, "importance": 0.10, "reinforcement": 0.05}'),
  ('retrieval_weights_procedural', '{"semantic_similarity": 0.45, "entity_overlap": 0.05, "temporal_relevance": 0.05, "importance": 0.15, "reinforcement": 0.30}'),
  ('retrieval_weights_exploratory', '{"semantic_similarity": 0.35, "entity_overlap": 0.25, "temporal_relevance": 0.15, "importance": 0.20, "reinforcement": 0.05}');
```

**Task 2.3: Domain Ontology Mapping** (Day 4-5)

Map domain database relationships into `domain_ontology` table:

```python
# Example: customer → sales_orders relationship
INSERT INTO app.domain_ontology VALUES
(
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

**Complete all relationships**:
- customer → sales_orders
- sales_order → work_orders
- work_order → invoices
- invoice → payments
- (etc., based on domain schema)

**Task 2.4: Schema Validation** (Day 6-7)

- [ ] Run all migrations on clean database
- [ ] Verify all tables created correctly
- [ ] Verify all indexes created
- [ ] Run rollback tests (migration down)
- [ ] Document any schema deviations from design

**Task 2.5: Database Testing** (Day 8-10)

```python
def test_schema():
    """Verify schema matches design specifications"""
    # Test all tables exist
    assert table_exists('app.chat_events')
    assert table_exists('app.canonical_entities')
    # ... all tables

    # Test constraints
    assert check_constraint_exists('semantic_memories', 'valid_confidence')
    assert foreign_key_exists('semantic_memories', 'canonical_entities')

    # Test indexes
    assert index_exists('idx_chat_events_session')
    assert index_exists('idx_episodic_embedding')  # pgvector index
```

**Deliverable**:
- ✅ All 10 tables created with correct schema
- ✅ All indexes in place
- ✅ system_config seeded with Phase 1 heuristics
- ✅ domain_ontology mapped
- ✅ Schema tests passing

---

## Week 3-4: Entity Resolution System

### Milestone: Five-stage entity resolution operational

**Task 3.1: Canonical Entity Management** (Day 1-3)

Implement CRUD operations for canonical entities:

```python
class CanonicalEntityService:
    async def create_or_get_entity(
        self,
        entity_type: str,
        external_ref: dict,
        canonical_name: str,
        properties: dict | None = None
    ) -> CanonicalEntity:
        """
        Create canonical entity or return existing.
        Idempotent: (entity_type, external_ref) is natural key.
        """
        # Check if exists
        existing = await self.db.fetchone("""
            SELECT * FROM app.canonical_entities
            WHERE entity_type = $1 AND external_ref = $2
        """, entity_type, external_ref)

        if existing:
            return CanonicalEntity(**existing)

        # Create new
        entity_id = f"{entity_type}:{uuid4()}"
        await self.db.execute("""
            INSERT INTO app.canonical_entities
            (entity_id, entity_type, canonical_name, external_ref, properties)
            VALUES ($1, $2, $3, $4, $5)
        """, entity_id, entity_type, canonical_name, external_ref, properties)

        return await self.get_entity(entity_id)
```

**Task 3.2: Entity Alias Management** (Day 4-6)

```python
class EntityAliasService:
    async def create_alias(
        self,
        canonical_entity_id: str,
        alias_text: str,
        alias_source: str,
        user_id: str | None,
        confidence: float,
        metadata: dict | None = None
    ) -> EntityAlias:
        """Create or update entity alias."""
        await self.db.execute("""
            INSERT INTO app.entity_aliases
            (canonical_entity_id, alias_text, alias_source, user_id, confidence, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (alias_text, user_id, canonical_entity_id) DO UPDATE SET
              use_count = app.entity_aliases.use_count + 1,
              confidence = LEAST(0.95, app.entity_aliases.confidence + 0.02)
        """, canonical_entity_id, alias_text, alias_source, user_id, confidence, metadata)
```

**Task 3.3: Five-Stage Resolution Algorithm** (Day 7-12)

Implement as specified in ENTITY_RESOLUTION_DESIGN.md:

```python
class EntityResolver:
    async def resolve(
        self,
        mention_text: str,
        user_id: str,
        context: ResolutionContext
    ) -> ResolutionResult:
        """Five-stage entity resolution."""

        # Stage 1: Exact match
        if result := await self._exact_match(mention_text):
            return result

        # Stage 2: User-specific alias
        if result := await self._user_alias_match(mention_text, user_id, context):
            return result

        # Stage 3: Fuzzy match
        candidates = await self._fuzzy_match(mention_text, user_id)
        if len(candidates) == 1 and candidates[0].score > 0.85:
            return ResolutionResult(
                canonical_entity_id=candidates[0].entity_id,
                confidence=candidates[0].score,
                candidates=[],
                requires_disambiguation=False
            )

        # Stage 4: Coreference resolution
        if self._is_pronoun(mention_text):
            if result := await self._resolve_coreference(mention_text, context):
                return result

        # Stage 5: Disambiguation required
        if not candidates:
            # Try domain database
            candidates = await self._search_domain_db(mention_text)

        return ResolutionResult(
            canonical_entity_id=candidates[0].entity_id if candidates else None,
            confidence=candidates[0].score if candidates else 0.0,
            candidates=candidates,
            requires_disambiguation=len(candidates) != 1 or candidates[0].score < 0.65
        )
```

**Implement all stages**:
- `_exact_match()`: Direct alias lookup
- `_user_alias_match()`: User-specific with context
- `_fuzzy_match()`: Levenshtein + semantic similarity
- `_resolve_coreference()`: Recent entity in conversation
- `_search_domain_db()`: Query domain tables

**Task 3.4: Domain Database Integration** (Day 13-14)

```python
class DomainDatabaseService:
    async def search_entities(
        self,
        mention_text: str,
        entity_type_hint: str | None = None
    ) -> List[DomainEntity]:
        """Search domain database for matching entities."""
        if entity_type_hint == "customer":
            return await self.db.fetch("""
                SELECT customer_id, name, industry
                FROM domain.customers
                WHERE name ILIKE $1 OR similarity(name, $2) > 0.7
                ORDER BY similarity(name, $2) DESC
                LIMIT 5
            """, f"%{mention_text}%", mention_text)

        # Search all entity types if no hint
        # Use domain_ontology to determine which tables to search
        ...
```

**Task 3.5: Testing** (Throughout + Day 15-16)

```python
def test_entity_resolution():
    # Test Stage 1: Exact match
    result = await resolver.resolve("Acme Corporation", user_id, context)
    assert result.canonical_entity_id == "customer:xxx"
    assert result.confidence >= 0.95

    # Test Stage 2: User alias
    result = await resolver.resolve("my main customer", user_id, context)
    assert result.requires_disambiguation == False

    # Test Stage 3: Fuzzy match
    result = await resolver.resolve("Acme", user_id, context)
    assert result.canonical_entity_id == "customer:xxx"
    assert 0.70 <= result.confidence <= 0.90

    # Test Stage 4: Coreference
    context.recent_entities = [("customer:xxx", 1)]
    result = await resolver.resolve("they", user_id, context)
    assert result.canonical_entity_id == "customer:xxx"

    # Test Stage 5: Disambiguation
    result = await resolver.resolve("the customer", user_id, context={})
    assert result.requires_disambiguation == True
    assert len(result.candidates) > 1
```

**Deliverable**:
- ✅ Entity resolution working end-to-end
- ✅ All 5 stages implemented
- ✅ Domain database integration functional
- ✅ 95%+ test coverage on resolution logic
- ✅ Performance: <50ms for stages 1-3, <100ms for stage 5

---

## Week 5-6: Memory Transformation Pipeline

### Milestone: Raw events → Episodic → Semantic transformation working

**Task 4.1: Chat Event Storage** (Day 1-2)

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
            event = await self.db.fetchone("""
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

**Task 4.2: LLM-Based Memory Extraction** (Day 3-5)

```python
class MemoryExtractor:
    async def extract_from_event(
        self,
        event: ChatEvent,
        context: ConversationContext
    ) -> ExtractionResult:
        """Extract entities, intent, and potential memories from chat event."""

        prompt = f"""
        Analyze this conversation message and extract:
        1. All entity mentions (customers, orders, products, etc.)
        2. Event type (question, statement, command, correction, confirmation)
        3. Any facts worth remembering (preferences, policies, observations)

        Message: "{event.content}"
        Recent context: {context.recent_messages}

        Output as JSON:
        {{
          "entities": [{{"text": "...", "type": "..."}}, ...],
          "event_type": "...",
          "extractable_facts": [
            {{"subject": "...", "predicate": "...", "object": "...", "confidence": 0.X}}
          ],
          "summary": "Brief summary of this interaction"
        }}
        """

        llm_response = await self.llm.complete(prompt, response_format="json")
        return ExtractionResult.parse(llm_response)
```

**Task 4.3: Episodic Memory Creation** (Day 6-8)

```python
class EpisodicMemoryService:
    async def create_from_event(
        self,
        event: ChatEvent,
        extraction: ExtractionResult,
        resolved_entities: List[ResolvedEntity],
        domain_facts: dict | None = None
    ) -> EpisodicMemory:
        """Create episodic memory from event."""

        # Compute importance
        importance = self._compute_importance(
            event_type=extraction.event_type,
            entity_count=len(resolved_entities),
            has_domain_facts=bool(domain_facts)
        )

        # Create memory
        memory = await self.db.fetchone("""
            INSERT INTO app.episodic_memories
            (user_id, session_id, summary, event_type, source_event_ids,
             entities, domain_facts_referenced, importance)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """, event.user_id, event.session_id, extraction.summary,
            extraction.event_type, [event.event_id],
            self._format_entities(resolved_entities),
            domain_facts, importance)

        # Async: Generate embedding
        await self.embedding_queue.enqueue(memory.memory_id, memory.summary)

        return EpisodicMemory(**memory)

    def _compute_importance(self, event_type, entity_count, has_domain_facts):
        """From LIFECYCLE_DESIGN.md"""
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

**Task 4.4: Semantic Memory Extraction** (Day 9-12)

```python
class SemanticMemoryService:
    async def extract_from_episodic(
        self,
        episodic: EpisodicMemory,
        extraction: ExtractionResult
    ) -> List[SemanticMemory]:
        """Extract semantic facts from episodic memory."""

        semantic_memories = []

        for fact in extraction.extractable_facts:
            # Resolve subject entity
            subject_id = self._find_entity_id(fact.subject, episodic.entities)
            if not subject_id:
                continue

            # Check for existing memory (reinforcement vs new)
            existing = await self._find_matching_memory(
                subject_id,
                fact.predicate,
                fact.object
            )

            if existing and self._values_compatible(existing.object_value, fact.object):
                # Reinforcement
                await self._reinforce_memory(existing)
            elif existing:
                # Conflict
                await self._handle_conflict(existing, fact)
            else:
                # New memory
                semantic = await self._create_semantic_memory(
                    subject_id,
                    fact.predicate,
                    fact.object,
                    confidence=fact.confidence,
                    source_memory_id=episodic.memory_id,
                    source_event_id=episodic.source_event_ids[0]
                )
                semantic_memories.append(semantic)

        return semantic_memories

    async def _reinforce_memory(self, memory: SemanticMemory):
        """Apply reinforcement boost from HEURISTICS_CALIBRATION.md"""
        boost = self._get_reinforcement_boost(memory.reinforcement_count + 1)

        await self.db.execute("""
            UPDATE app.semantic_memories
            SET reinforcement_count = reinforcement_count + 1,
                confidence = LEAST(0.95, confidence + $1),
                last_validated_at = now(),
                status = 'active',
                updated_at = now()
            WHERE memory_id = $2
        """, boost, memory.memory_id)

    def _get_reinforcement_boost(self, count: int) -> float:
        """From HEURISTICS_CALIBRATION.md"""
        boosts = [0.15, 0.10, 0.05, 0.02]
        index = min(count - 1, len(boosts) - 1)
        return boosts[index]
```

**Task 4.5: Conflict Detection** (Day 13-14)

```python
class ConflictService:
    async def detect_and_log(
        self,
        existing_memory: SemanticMemory,
        new_fact: dict,
        event_id: int
    ) -> MemoryConflict:
        """Detect conflict and log in memory_conflicts table."""

        conflict_data = {
            "existing": {
                "memory_id": existing_memory.memory_id,
                "value": existing_memory.object_value,
                "confidence": existing_memory.confidence,
                "created_at": existing_memory.created_at.isoformat()
            },
            "new": {
                "value": new_fact['object'],
                "confidence": new_fact['confidence'],
                "source": "extraction"
            }
        }

        resolution_strategy = self._determine_strategy(
            existing_memory.confidence,
            new_fact['confidence'],
            (datetime.now() - existing_memory.created_at).days
        )

        conflict = await self.db.fetchone("""
            INSERT INTO app.memory_conflicts
            (detected_at_event_id, conflict_type, conflict_data, resolution_strategy)
            VALUES ($1, $2, $3, $4)
            RETURNING *
        """, event_id, "memory_vs_memory", conflict_data, resolution_strategy)

        return MemoryConflict(**conflict)

    def _determine_strategy(self, old_conf, new_conf, age_days):
        """From LIFECYCLE_DESIGN.md conflict resolution"""
        if abs(old_conf - new_conf) > 0.3:
            return "trust_higher_confidence"
        elif age_days > 60:
            return "trust_recent"
        else:
            return "ask_user"
```

**Task 4.6: Embedding Pipeline** (Day 15-16)

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

**Task 4.7: Integration Testing** (Throughout + Day 17-18)

```python
async def test_full_pipeline():
    """End-to-end test: message → episodic → semantic"""

    # 1. Store event
    event = await chat_service.store_event(
        session_id=uuid4(),
        user_id="test_user",
        role="user",
        content="Remember, Acme prefers Friday deliveries"
    )

    # 2. Extract
    extraction = await extractor.extract_from_event(event, context)
    assert extraction.event_type == "statement"
    assert len(extraction.extractable_facts) >= 1

    # 3. Resolve entities
    entities = await resolver.resolve_all(extraction.entities, context)
    assert entities[0].canonical_entity_id.startswith("customer:")

    # 4. Create episodic
    episodic = await episodic_service.create_from_event(event, extraction, entities)
    assert episodic.importance >= 0.6  # statement with entity

    # 5. Extract semantic
    semantic_memories = await semantic_service.extract_from_episodic(episodic, extraction)
    assert len(semantic_memories) >= 1
    assert semantic_memories[0].predicate == "delivery_day_preference"
    assert semantic_memories[0].confidence >= 0.6

    # 6. Verify embedding generated (async)
    await asyncio.sleep(2)  # Wait for embedding worker
    refreshed = await semantic_service.get(semantic_memories[0].memory_id)
    assert refreshed.embedding is not None
```

**Deliverable**:
- ✅ Complete transformation pipeline functional
- ✅ Chat events → Episodic → Semantic working
- ✅ Reinforcement logic operational
- ✅ Conflict detection and logging
- ✅ Embedding generation pipeline
- ✅ End-to-end tests passing

---

## Week 7-8: Retrieval System

### Milestone: Multi-signal retrieval returning relevant memories

**Task 5.1: Query Understanding** (Day 1-3)

```python
class QueryAnalyzer:
    async def analyze(
        self,
        query: str,
        context: ConversationContext
    ) -> QueryAnalysis:
        """Classify query and extract key information."""

        # Extract entities
        entities = await self.entity_resolver.extract_and_resolve(query, context)

        # Extract temporal scope
        time_range = self._extract_temporal_scope(query)

        # Classify query type
        query_type = await self._classify_query(query, entities, time_range)

        # Select retrieval strategy
        strategy_weights = self._select_strategy(query_type)

        return QueryAnalysis(
            query_type=query_type,
            entities=entities,
            time_range=time_range,
            strategy_weights=strategy_weights
        )

    async def _classify_query(self, query, entities, time_range):
        """LLM-based query classification"""
        prompt = f"""
        Classify this query:
        Query: "{query}"
        Has entities: {bool(entities)}
        Has time reference: {bool(time_range)}

        Choose one:
        - factual: Asking for specific facts about entities
        - procedural: Asking how to do something
        - exploratory: Open-ended exploration
        - analytical: Analyzing patterns or trends

        Output JSON: {{"type": "...", "entity_focused": true/false, "procedural": true/false}}
        """

        response = await self.llm.complete(prompt, response_format="json")
        return QueryType.parse(response)

    def _select_strategy(self, query_type):
        """From HEURISTICS_CALIBRATION.md"""
        strategies = {
            "factual": "retrieval_weights_factual",
            "procedural": "retrieval_weights_procedural",
            "exploratory": "retrieval_weights_exploratory"
        }
        key = strategies.get(query_type.category, "retrieval_weights_exploratory")
        return self.config.get(key)
```

**Task 5.2: Candidate Generation** (Day 4-7)

```python
class CandidateGenerator:
    async def generate(
        self,
        query_embedding: np.ndarray,
        query_entities: List[str],
        time_range: TimeRange | None,
        user_id: str
    ) -> List[MemoryCandidate]:
        """Generate candidates from multiple sources in parallel."""

        async with asyncio.TaskGroup() as tg:
            # Parallel retrieval
            semantic_task = tg.create_task(
                self._semantic_similarity(query_embedding, user_id, limit=50)
            )
            entity_task = tg.create_task(
                self._entity_overlap(query_entities, user_id, limit=30)
            ) if query_entities else None
            temporal_task = tg.create_task(
                self._temporal_range(time_range, user_id, limit=30)
            ) if time_range else None
            summary_task = tg.create_task(
                self._summaries(user_id, limit=5)
            )

        # Combine and deduplicate
        all_candidates = []
        all_candidates.extend(semantic_task.result())
        if entity_task:
            all_candidates.extend(entity_task.result())
        if temporal_task:
            all_candidates.extend(temporal_task.result())
        all_candidates.extend(summary_task.result())

        # Deduplicate by memory_id
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
              UNION ALL
              SELECT summary_id AS memory_id, 'summary' AS memory_type, summary_text,
                     NULL AS entities, 0.9 AS importance, embedding, created_at
              FROM app.memory_summaries WHERE user_id = $2
            ) AS all_memories
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1
            LIMIT $3
        """, embedding, user_id, limit)

        return [MemoryCandidate(**r) for r in results]
```

**Task 5.3: Multi-Signal Scoring** (Day 8-10)

```python
class MemoryScorer:
    def score(
        self,
        candidate: MemoryCandidate,
        query_embedding: np.ndarray,
        query_entities: List[str],
        time_range: TimeRange | None,
        strategy_weights: dict
    ) -> float:
        """Compute final relevance score from RETRIEVAL_DESIGN.md"""

        signals = {}

        # Signal 1: Semantic similarity
        if candidate.embedding is not None:
            signals['semantic_similarity'] = 1 - cosine_distance(
                query_embedding,
                candidate.embedding
            )
        else:
            signals['semantic_similarity'] = 0.0

        # Signal 2: Entity overlap
        candidate_entities = self._extract_entity_ids(candidate.entities)
        if query_entities and candidate_entities:
            overlap = len(set(query_entities) & set(candidate_entities))
            signals['entity_overlap'] = overlap / len(query_entities)
        else:
            signals['entity_overlap'] = 0.0

        # Signal 3: Temporal relevance
        if time_range:
            if time_range.start <= candidate.created_at <= time_range.end:
                signals['temporal_relevance'] = 1.0
            else:
                distance_days = min(
                    abs((candidate.created_at - time_range.start).days),
                    abs((candidate.created_at - time_range.end).days)
                )
                signals['temporal_relevance'] = math.exp(-0.1 * distance_days)
        else:
            age_days = (datetime.now() - candidate.created_at).days
            signals['temporal_relevance'] = math.exp(-0.01 * age_days)

        # Signal 4: Importance
        signals['importance'] = candidate.importance

        # Signal 5: Reinforcement
        signals['reinforcement'] = 0.5  # Placeholder (Phase 2: use retrieval logs)

        # Weighted combination
        final_score = sum(
            signals[sig] * strategy_weights[sig]
            for sig in signals
        )

        # Type boost
        if candidate.memory_type == 'summary':
            final_score *= 1.15

        return final_score
```

**Task 5.4: Ranking and Selection** (Day 11-12)

```python
class MemorySelector:
    def select(
        self,
        scored_candidates: List[Tuple[MemoryCandidate, float]],
        max_memories: int = 15,
        max_tokens: int = 3000
    ) -> List[MemoryCandidate]:
        """Select top memories within token budget."""

        # Sort by score
        ranked = sorted(scored_candidates, key=lambda x: x[1], reverse=True)

        # Summaries first (always include if present)
        summaries = [(c, s) for c, s in ranked if c.memory_type == 'summary']
        others = [(c, s) for c, s in ranked if c.memory_type != 'summary']

        selected = []
        tokens_used = 0

        # Add summaries
        for candidate, score in summaries[:5]:  # Max 5 summaries
            tokens = self._estimate_tokens(candidate.summary_text)
            if tokens_used + tokens <= max_tokens:
                selected.append(candidate)
                tokens_used += tokens

        # Add others until budget exhausted or max count reached
        for candidate, score in others:
            if len(selected) >= max_memories:
                break
            tokens = self._estimate_tokens(candidate.summary_text)
            if tokens_used + tokens <= max_tokens:
                selected.append(candidate)
                tokens_used += tokens

        return selected

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate: 1 token ≈ 4 characters"""
        return len(text) // 4
```

**Task 5.5: Context Formatting** (Day 13-14)

```python
class ContextFormatter:
    def format(
        self,
        memories: List[MemoryCandidate],
        query: str
    ) -> str:
        """Format memories for LLM prompt."""

        sections = []
        by_type = defaultdict(list)
        for m in memories:
            by_type[m.memory_type].append(m)

        # Summaries
        if by_type['summary']:
            sections.append("## Relevant Context Summaries\n")
            for summary in by_type['summary']:
                sections.append(f"- {summary.summary_text}\n")

        # Semantic facts
        if by_type['semantic']:
            sections.append("\n## Relevant Facts\n")
            for sem in by_type['semantic']:
                sections.append(f"- {sem.summary_text}\n")

        # Episodic memories
        if by_type['episodic']:
            sections.append("\n## Relevant Past Interactions\n")
            for ep in by_type['episodic']:
                time_ago = self._format_time_ago(ep.created_at)
                sections.append(f"- {ep.summary_text} ({time_ago})\n")

        prompt = f"""# Retrieved Memory Context

The following information from your memory may be relevant to: "{query}"

{"".join(sections)}

Use this context to inform your response, citing sources when appropriate.
"""
        return prompt
```

**Task 5.6: Integration Testing** (Day 15-16)

```python
async def test_retrieval_pipeline():
    """End-to-end retrieval test"""

    # Setup: Create test memories
    await create_test_memories()

    # Query
    query = "What did Acme Corporation order last month?"

    # Analyze
    analysis = await analyzer.analyze(query, context)
    assert analysis.query_type.category == "factual"
    assert len(analysis.entities) >= 1
    assert analysis.time_range is not None

    # Generate embedding
    query_embedding = await embedding_service.generate(query)

    # Retrieve
    candidates = await generator.generate(
        query_embedding,
        [e.canonical_id for e in analysis.entities],
        analysis.time_range,
        "test_user"
    )
    assert len(candidates) > 0

    # Score
    scored = [
        (c, scorer.score(c, query_embedding, [...], analysis.time_range, analysis.strategy_weights))
        for c in candidates
    ]

    # Select
    selected = selector.select(scored, max_memories=10)
    assert len(selected) <= 10
    assert any(m.memory_type == 'summary' for m in selected)  # Summaries prioritized

    # Format
    context_prompt = formatter.format(selected, query)
    assert "Relevant Context Summaries" in context_prompt or len(selected) == 0
```

**Deliverable**:
- ✅ Complete retrieval pipeline operational
- ✅ Multi-signal scoring working
- ✅ Context window management
- ✅ Performance: <100ms total latency
- ✅ Retrieval tests passing

---

## Week 9: API Implementation

### Milestone: All 10 Phase 1 endpoints implemented

**Task 6.1: Core Chat Endpoint** (Day 1-3)

```python
@router.post("/api/v1/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
) -> ChatResponse:
    """Primary conversation interface - orchestrates full pipeline."""

    try:
        # 1. Store event
        event = await chat_service.store_event(
            session_id=request.session_id,
            user_id=current_user.user_id,
            role="user",
            content=request.message,
            metadata=request.metadata
        )

        # 2. Extract information
        extraction = await extractor.extract_from_event(
            event,
            ConversationContext.from_history(request.conversation_history)
        )

        # 3. Resolve entities
        resolved_entities = await resolver.resolve_all(
            extraction.entities,
            current_user.user_id,
            request.session_id
        )

        # 4. Retrieve relevant memories
        query_analysis = await query_analyzer.analyze(request.message, context)
        query_embedding = await embedding_service.generate(request.message)
        retrieved_memories = await retriever.retrieve(
            query_embedding,
            query_analysis,
            current_user.user_id
        )

        # 5. Query domain database if needed
        domain_results = None
        if query_analysis.query_type.requires_domain_db:
            domain_results = await domain_service.query(
                resolved_entities,
                query_analysis.time_range
            )

        # 6. Create episodic memory
        episodic = await episodic_service.create_from_event(
            event,
            extraction,
            resolved_entities,
            domain_results
        )

        # 7. Extract semantic memories
        semantic_memories = await semantic_service.extract_from_episodic(
            episodic,
            extraction
        )

        # 8. Format context for LLM
        memory_context = context_formatter.format(retrieved_memories, request.message)

        # 9. Generate response (call external LLM)
        llm_response = await llm_service.generate_response(
            message=request.message,
            memory_context=memory_context,
            domain_results=domain_results
        )

        # 10. Store assistant response
        assistant_event = await chat_service.store_event(
            session_id=request.session_id,
            user_id=current_user.user_id,
            role="assistant",
            content=llm_response.content
        )

        return ChatResponse(
            response=llm_response,
            augmentation=AugmentationMetadata(
                retrieved_memories=[m.to_dict() for m in retrieved_memories],
                domain_queries=domain_results.queries if domain_results else []
            ),
            memories_created=[
                {"memory_id": episodic.memory_id, "type": "episodic"},
                *[{"memory_id": m.memory_id, "type": "semantic"} for m in semantic_memories]
            ],
            entities_resolved=[e.to_dict() for e in resolved_entities]
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

**Task 6.2: Memory Management Endpoints** (Day 4-5)

```python
@router.get("/api/v1/memories")
async def list_memories(
    user_id: str = Query(...),
    type: str | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user)
) -> MemoryListResponse:
    """List memories with filtering and pagination."""
    # Implementation
    ...

@router.get("/api/v1/memories/{memory_id}")
async def get_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user)
) -> MemoryDetailResponse:
    """Get detailed memory information."""
    ...

@router.post("/api/v1/memories")
async def create_memory(
    request: CreateMemoryRequest,
    current_user: User = Depends(get_current_user)
) -> MemoryResponse:
    """Explicitly create a memory (testing/admin)."""
    ...

@router.patch("/api/v1/memories/{memory_id}")
async def update_memory(
    memory_id: int,
    request: UpdateMemoryRequest,
    current_user: User = Depends(get_current_user)
) -> MemoryResponse:
    """Update memory fields."""
    ...

@router.delete("/api/v1/memories/{memory_id}")
async def delete_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user)
) -> DeleteResponse:
    """Soft-delete memory."""
    ...
```

**Task 6.3: Entity Resolution Endpoints** (Day 6)

```python
@router.post("/api/v1/entities/resolve")
async def resolve_entity(
    request: ResolveEntityRequest,
    current_user: User = Depends(get_current_user)
) -> EntityResolutionResponse:
    """Resolve entity mention to canonical entity."""

    result = await entity_resolver.resolve(
        mention_text=request.mention,
        user_id=current_user.user_id,
        context=ResolutionContext.from_request(request.context)
    )

    return EntityResolutionResponse(
        resolved=result.canonical_entity_id is not None,
        canonical_entity=await entity_service.get(result.canonical_entity_id) if result.canonical_entity_id else None,
        confidence=result.confidence,
        alternatives=[c.to_dict() for c in result.candidates],
        requires_disambiguation=result.requires_disambiguation
    )

@router.post("/api/v1/entities/disambiguate")
async def disambiguate_entity(
    request: DisambiguateRequest,
    current_user: User = Depends(get_current_user)
) -> DisambiguationResponse:
    """User selects from ambiguous candidates."""

    alias = await alias_service.create_alias(
        canonical_entity_id=request.chosen_entity_id,
        alias_text=request.mention,
        alias_source="disambiguation",
        user_id=current_user.user_id,
        confidence=0.85,
        metadata={"disambiguation_context": request.context}
    )

    return DisambiguationResponse(
        alias_created=True,
        alias_id=alias.alias_id,
        entity_id=alias.canonical_entity_id
    )

@router.get("/api/v1/entities")
async def list_entities(
    user_id: str = Query(...),
    type: str | None = Query(None),
    limit: int = Query(20),
    current_user: User = Depends(get_current_user)
) -> EntityListResponse:
    """List canonical entities."""
    ...
```

**Task 6.4: Health and System Endpoints** (Day 7)

```python
@router.get("/api/v1/health")
async def health_check() -> HealthResponse:
    """System health check."""

    db_status = await check_database_health()
    vector_status = await check_vector_index_health()

    return HealthResponse(
        status="healthy" if db_status and vector_status else "degraded",
        version="1.0.0",
        components={
            "database": {"status": "up" if db_status else "down"},
            "vector_search": {"status": "up" if vector_status else "down"}
        }
    )
```

**Task 6.5: Error Handling and Validation** (Day 8)

```python
# Request validation
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    user_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    session_id: UUID
    conversation_history: List[Message] = Field(default_factory=list, max_length=50)
    metadata: dict | None = None

    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v

# Error handling middleware
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "INVALID_REQUEST", "message": str(exc)}}
    )

@app.exception_handler(EntityNotFoundError)
async def entity_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "ENTITY_NOT_FOUND", "message": str(exc)}}
    )
```

**Task 6.6: API Documentation** (Day 9)

- [ ] Generate OpenAPI spec
- [ ] Set up Swagger UI
- [ ] Write API usage examples
- [ ] Document authentication flow

**Task 6.7: Integration Testing** (Day 10)

```python
async def test_api_full_flow():
    """End-to-end API test"""
    client = TestClient(app)

    # 1. Health check
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    # 2. Chat request
    response = client.post("/api/v1/chat", json={
        "message": "What did Acme order last month?",
        "user_id": "test_user",
        "session_id": str(uuid4())
    })
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "augmentation" in data
    assert len(data["memories_created"]) > 0

    # 3. List memories
    response = client.get(f"/api/v1/memories?user_id=test_user")
    assert response.status_code == 200
    assert len(response.json()["memories"]) > 0

    # 4. Entity resolution
    response = client.post("/api/v1/entities/resolve", json={
        "mention": "Acme",
        "user_id": "test_user"
    })
    assert response.status_code == 200
    assert response.json()["resolved"] == True
```

**Deliverable**:
- ✅ All 10 Phase 1 endpoints implemented
- ✅ Request validation and error handling
- ✅ OpenAPI documentation
- ✅ API integration tests passing
- ✅ Performance: <500ms P95 for /chat endpoint

---

## Week 10: Testing, Optimization, and Documentation

### Milestone: Production-ready system with comprehensive tests

**Task 7.1: Unit Testing** (Day 1-3)

Target: 90%+ code coverage

```bash
pytest tests/unit/ --cov=src --cov-report=html --cov-report=term
```

**Critical tests**:
- Entity resolution (all 5 stages)
- Memory transformation pipeline
- Multi-signal scoring
- Conflict detection
- Embedding generation

**Task 7.2: Integration Testing** (Day 4-5)

```python
# Test full conversation flow
async def test_multi_turn_conversation():
    """Test memory accumulation over conversation"""

    session_id = uuid4()

    # Turn 1: User provides information
    response1 = await api_client.chat(
        "Remember, Acme prefers Friday deliveries",
        session_id=session_id
    )
    assert len(response1.memories_created) >= 1

    # Turn 2: Query that information
    response2 = await api_client.chat(
        "When should I schedule Acme's delivery?",
        session_id=session_id
    )
    assert "Friday" in response2.response.content
    assert len(response2.augmentation.retrieved_memories) > 0

    # Turn 3: Correction
    response3 = await api_client.chat(
        "Actually, they changed to Thursday",
        session_id=session_id
    )
    # Verify conflict detected and resolved
    conflicts = await conflict_service.list_conflicts(user_id="test_user")
    assert len(conflicts) >= 1
```

**Task 7.3: Performance Testing** (Day 6)

```python
import pytest
from locust import HttpUser, task, between

class MemorySystemUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def chat(self):
        self.client.post("/api/v1/chat", json={
            "message": "What is the status of order #12345?",
            "user_id": f"user_{random.randint(1, 100)}",
            "session_id": str(uuid4())
        })

# Run load test
# locust -f tests/performance/load_test.py --users 100 --spawn-rate 10
```

**Performance targets**:
- P50: <200ms for /chat
- P95: <500ms for /chat
- P99: <1000ms for /chat
- Throughput: 100 req/sec per instance

**Task 7.4: Database Optimization** (Day 7)

- [ ] Analyze slow queries (pg_stat_statements)
- [ ] Add missing indexes if needed
- [ ] Tune pgvector parameters (lists count)
- [ ] Set up connection pooling
- [ ] Configure autovacuum

```sql
-- Analyze query performance
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query LIKE '%app.semantic_memories%'
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Tune pgvector index
ALTER INDEX idx_episodic_embedding SET (lists = 200);  -- Adjust based on data size
REINDEX INDEX idx_episodic_embedding;
```

**Task 7.5: Documentation** (Day 8-9)

**API Documentation**:
- [ ] OpenAPI spec complete
- [ ] Endpoint usage examples
- [ ] Authentication guide
- [ ] Rate limiting documentation
- [ ] Error code reference

**Developer Documentation**:
- [ ] Architecture overview
- [ ] Database schema diagram
- [ ] Setup guide (local development)
- [ ] Deployment guide
- [ ] Troubleshooting guide

**User Documentation**:
- [ ] Getting started guide
- [ ] Common use cases
- [ ] Best practices
- [ ] FAQ

**Task 7.6: Security Audit** (Day 10)

- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output escaping)
- [ ] Authentication/authorization review
- [ ] Rate limiting implementation
- [ ] Input validation audit
- [ ] Secrets management (environment variables, not hardcoded)
- [ ] HTTPS enforcement
- [ ] CORS configuration

**Deliverable**:
- ✅ 90%+ code coverage
- ✅ All integration tests passing
- ✅ Performance targets met
- ✅ Complete documentation
- ✅ Security audit passed

---

## Week 11-12: Deployment and Monitoring

### Milestone: Production deployment with monitoring

**Task 8.1: Infrastructure Setup** (Day 1-3)

**Production Environment**:
```yaml
# docker-compose.yml (production)
version: '3.8'
services:
  api:
    image: memory-system-api:latest
    replicas: 3
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  database:
    image: ankane/pgvector:latest
    volumes:
      - db_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7-alpine

  worker:
    image: memory-system-worker:latest
    command: celery -A app.worker worker --loglevel=info
    replicas: 2
```

**Task 8.2: Monitoring Setup** (Day 4-5)

**Metrics to track**:
- API latency (P50, P95, P99)
- Error rate
- Throughput (requests/sec)
- Database query latency
- Embedding generation latency
- Memory creation rate
- Entity resolution success rate
- Retrieval quality (user feedback, Phase 2)

**Tools**:
- Prometheus for metrics collection
- Grafana for dashboards
- Sentry for error tracking
- CloudWatch/Datadog for infrastructure

```python
# Instrumentation
from prometheus_client import Counter, Histogram

chat_requests = Counter('chat_requests_total', 'Total chat requests')
chat_latency = Histogram('chat_latency_seconds', 'Chat endpoint latency')
memory_created = Counter('memories_created_total', 'Total memories created', ['type'])
entity_resolution_attempts = Counter('entity_resolution_attempts', 'Entity resolution attempts', ['stage', 'success'])

@chat_latency.time()
@router.post("/api/v1/chat")
async def chat(...):
    chat_requests.inc()
    # ... implementation
    memory_created.labels(type='episodic').inc()
    ...
```

**Task 8.3: Logging Setup** (Day 6)

```python
import structlog

logger = structlog.get_logger()

# Structured logging
logger.info(
    "memory_created",
    memory_id=memory.memory_id,
    memory_type="semantic",
    user_id=user.user_id,
    confidence=memory.confidence,
    predicate=memory.predicate
)

logger.error(
    "entity_resolution_failed",
    mention_text=mention,
    user_id=user.user_id,
    stage="fuzzy_match",
    error=str(e)
)
```

**Log aggregation**: ELK stack, CloudWatch Logs, or similar

**Task 8.4: Deployment** (Day 7-8)

**Deployment checklist**:
- [ ] Database migrations applied
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] DNS configured
- [ ] Load balancer configured
- [ ] Auto-scaling configured
- [ ] Backup strategy implemented
- [ ] Disaster recovery plan documented

**Deployment steps**:
1. Run database migrations
2. Deploy API servers (blue-green deployment)
3. Deploy workers
4. Smoke tests on production
5. Switch traffic to new deployment
6. Monitor for 24 hours

**Task 8.5: Operational Runbooks** (Day 9)

Document procedures for:
- Scaling up/down
- Database backup and restore
- Handling API outages
- Embedding service failures
- Database migration failures
- Rollback procedure

**Task 8.6: Handoff and Training** (Day 10)

- [ ] Operations team training
- [ ] Runbook walkthrough
- [ ] Monitoring dashboard review
- [ ] Alert configuration
- [ ] On-call rotation setup

**Deliverable**:
- ✅ Production environment deployed
- ✅ Monitoring and alerting operational
- ✅ Logging and tracing configured
- ✅ Runbooks documented
- ✅ Team trained

---

## Risk Management

### High-Risk Items

**Risk 1: Domain Database Integration Complexity**
- **Probability**: High
- **Impact**: High
- **Mitigation**:
  - Start with schema documentation in Week 0
  - Create mock domain database for testing
  - Allocate extra time for ontology mapping
  - Plan for unknown schema issues

**Risk 2: LLM Extraction Quality**
- **Probability**: Medium
- **Impact**: High
- **Mitigation**:
  - Start with simple extraction patterns
  - Build extensive test cases
  - Plan for manual review in early deployment
  - Iterate on prompts based on failures
  - Log all extractions for Phase 2 learning

**Risk 3**: Embedding Service Latency/Cost**
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**:
  - Use async embedding generation (don't block API)
  - Batch embeddings where possible
  - Monitor OpenAI API costs closely
  - Consider alternative embedding providers if needed

**Risk 4: pgvector Performance at Scale**
- **Probability**: Low
- **Impact**: Medium
- **Mitigation**:
  - Start performance testing early (Week 10)
  - Benchmark with realistic data volumes
  - Plan for index tuning
  - Have fallback plan (dedicated vector DB)

### Medium-Risk Items

**Risk 5: Memory Quality (Noise)**
- **Impact**: Medium
- **Mitigation**: Log all extractions, manual review initially, iterate on extraction prompts

**Risk 6: Coreference Resolution Accuracy**
- **Impact**: Medium
- **Mitigation**: Start with conservative approach, test extensively, handle disambiguation gracefully

**Risk 7: Timeline Slippage**
- **Impact**: Medium
- **Mitigation**: Build in 2-week buffer, prioritize ruthlessly, defer non-essential features

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
- [ ] All 10 API endpoints functional

### Performance Requirements

- [ ] /chat endpoint: P95 < 500ms
- [ ] Semantic search: P95 < 50ms
- [ ] Entity resolution: P95 < 100ms
- [ ] System handles 100 concurrent users
- [ ] Database query performance acceptable (<100ms P95)

### Quality Requirements

- [ ] 90%+ code coverage
- [ ] All integration tests passing
- [ ] API documentation complete
- [ ] Security audit passed
- [ ] No critical bugs in production

### Operational Requirements

- [ ] Monitoring dashboards operational
- [ ] Logging and error tracking configured
- [ ] Deployment process documented
- [ ] Runbooks created
- [ ] Team trained

---

## Phase 1 to Phase 2 Transition

### Data Collection Requirements

During Phase 1 operation, collect:

**For Phase 2 Calibration** (from HEURISTICS_CALIBRATION.md):
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

### Phase 1 Completion Checklist

- [ ] All 10 Phase 1 endpoints implemented
- [ ] Memory transformation pipeline working end-to-end
- [ ] Entity resolution 5-stage algorithm operational
- [ ] Retrieval system returning relevant results
- [ ] Production deployment complete
- [ ] Monitoring and logging operational
- [ ] Data collection for Phase 2 in place
- [ ] Team trained and comfortable with system
- [ ] Documentation complete
- [ ] Performance targets met
- [ ] 90%+ test coverage

**Sign-off required from**:
- Engineering lead
- Product manager
- Operations team
- QA lead

---

## Conclusion

This roadmap provides a realistic 10-12 week path to a **production-ready Phase 1 MVP** that embodies all core vision principles. The system will be functional, performant, and ready to collect operational data for Phase 2 improvements.

**Key Success Factors**:
1. **Focus**: Build only Phase 1 essentials, defer everything else
2. **Testing**: Comprehensive testing at every stage
3. **Documentation**: Keep docs current as you build
4. **Incremental**: Build, test, integrate continuously
5. **Realistic**: 12 weeks is aggressive but achievable with dedicated team

**Next Steps After Phase 1**:
- Operate system for 1-3 months to collect data
- Analyze collected data against heuristics
- Begin Phase 2: Calibrate all numeric parameters using real operational data
- Implement learning features (signal weight tuning, adaptive decay rates, etc.)

**The vision is ambitious. Phase 1 makes it real.**
