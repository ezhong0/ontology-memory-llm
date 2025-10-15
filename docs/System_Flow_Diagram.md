# Ontology-Aware Memory System: System Flow Diagram

**Project Status**: Week 0 Complete - Foundation Ready for Phase 1 Implementation
**Last Updated**: 2025-10-15
**Implementation State**: Infrastructure ✅ | Domain Logic ⏳ | API Routes ⏳

---

## Table of Contents

1. [Implementation Status Overview](#implementation-status-overview)
2. [System Architecture](#system-architecture)
3. [Database Schema (IMPLEMENTED)](#database-schema-implemented)
4. [End-to-End Request Flow (PLANNED)](#end-to-end-request-flow-planned)
5. [Subsystem Flows](#subsystem-flows)
6. [Technology Stack & Configuration](#technology-stack--configuration)

---

## Implementation Status Overview

### ✅ Week 0: Foundation Complete

```
IMPLEMENTED (Ready to use):
├── Database Models (SQLAlchemy ORM)
│   ├── ✅ ChatEvent             (10 tables defined)
│   ├── ✅ CanonicalEntity       All with proper:
│   ├── ✅ EntityAlias           • Indexes
│   ├── ✅ EpisodicMemory        • Foreign keys
│   ├── ✅ SemanticMemory        • Check constraints
│   ├── ✅ ProceduralMemory      • pgvector columns
│   ├── ✅ MemorySummary         • JSONB fields
│   ├── ✅ DomainOntology
│   ├── ✅ MemoryConflict
│   └── ✅ SystemConfig
│
├── Configuration
│   ├── ✅ Settings (Pydantic)   Database, OpenAI, API config
│   └── ✅ Heuristics            All 43 parameters from calibration doc
│
├── Database Infrastructure
│   ├── ✅ Async session factory
│   ├── ✅ Connection pooling
│   └── ✅ Migration framework (Alembic)
│
└── API Scaffold
    ├── ✅ FastAPI app with lifespan
    ├── ✅ Basic routes (/, /health)
    ├── ✅ CORS middleware
    └── ✅ Error handlers

PENDING (To be implemented in Phase 1):
├── ⏳ Domain Layer (Business Logic)
│   ├── ⏳ Entity Resolution Service    (5-stage algorithm)
│   ├── ⏳ Memory Retrieval Service     (Multi-signal scoring)
│   ├── ⏳ Lifecycle Manager            (State transitions, decay)
│   ├── ⏳ Memory Extractor             (Chat → Episodic → Semantic)
│   └── ⏳ Conflict Detector            (Memory vs memory/DB conflicts)
│
├── ⏳ Infrastructure Adapters
│   ├── ⏳ Entity Repository            (PostgreSQL CRUD + search)
│   ├── ⏳ Memory Repository            (With vector search)
│   ├── ⏳ Embedding Service            (OpenAI integration)
│   └── ⏳ Domain DB Connector          (External database queries)
│
├── ⏳ API Layer
│   ├── ⏳ POST /chat                   (Primary endpoint)
│   ├── ⏳ Pydantic request/response models
│   ├── ⏳ Memory CRUD endpoints
│   ├── ⏳ Entity resolution endpoints
│   └── ⏳ Authentication (JWT)
│
└── ⏳ Utilities
    ├── ⏳ Text similarity (Levenshtein, fuzzy matching)
    ├── ⏳ Vector operations (cosine similarity)
    └── ⏳ Temporal parsing and decay functions
```

---

## System Architecture

### Hexagonal Architecture (Ports & Adapters)

```
┌───────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                          │
│  Status: ✅ Basic scaffold | ⏳ Routes pending                    │
│                                                                    │
│  ✅ src/api/main.py          FastAPI app, lifespan, health        │
│  ⏳ src/api/routes/          chat.py, memories.py, entities.py    │
│  ⏳ src/api/models/          Pydantic request/response models     │
│                                                                    │
│  Responsibilities:                                                 │
│  • HTTP request/response handling                                 │
│  • Input validation (Pydantic)                                    │
│  • Error translation (Domain exceptions → HTTP errors)            │
│  • Dependency injection setup                                     │
└────────────────────────────────┬──────────────────────────────────┘
                                 │
                                 ↓
┌───────────────────────────────────────────────────────────────────┐
│                    DOMAIN LAYER (Pure Python)                     │
│  Status: ⏳ Empty (only __init__.py scaffolding)                  │
│                                                                    │
│  ⏳ src/domain/entities/      CanonicalEntity, SemanticMemory     │
│  ⏳ src/domain/value_objects/ Confidence, ResolutionResult        │
│  ⏳ src/domain/services/      EntityResolver, MemoryRetriever     │
│  ⏳ src/domain/ports/         Repository interfaces (ABC)         │
│                                                                    │
│  Responsibilities:                                                 │
│  • Business logic (no I/O, testable without DB)                   │
│  • Entity resolution algorithm (5 stages)                         │
│  • Memory retrieval scoring (multi-signal)                        │
│  • Lifecycle management (state transitions, decay)                │
│  • Memory transformation (Episodic → Semantic)                    │
│                                                                    │
│  CRITICAL: NO imports from infrastructure layer                   │
│  Depends on ports (abstract interfaces), not concrete adapters    │
└────────────────────────────────┬──────────────────────────────────┘
                                 │
                                 ↓
┌───────────────────────────────────────────────────────────────────┐
│              INFRASTRUCTURE LAYER (External Systems)              │
│  Status: ✅ Models/Config | ⏳ Repositories/Services              │
│                                                                    │
│  Database (PostgreSQL + pgvector):                                │
│    ✅ src/infrastructure/database/models.py    All 10 tables      │
│    ✅ src/infrastructure/database/session.py   Async sessions     │
│    ⏳ src/infrastructure/database/repositories/ CRUD + search     │
│                                                                    │
│  External Services:                                                │
│    ⏳ src/infrastructure/embedding/            OpenAI embeddings  │
│    ⏳ src/infrastructure/domain_db/            External DB query  │
│    ⏳ src/infrastructure/cache/                Redis (Phase 2)    │
│                                                                    │
│  Configuration:                                                    │
│    ✅ src/config/settings.py                   Pydantic settings  │
│    ✅ src/config/heuristics.py                 43 parameters      │
│                                                                    │
│  Responsibilities:                                                 │
│  • Database access (SQLAlchemy)                                   │
│  • Vector search (pgvector)                                       │
│  • Embedding generation (OpenAI API)                              │
│  • Domain database queries (read-only)                            │
└───────────────────────────────────────────────────────────────────┘
```

### Dependency Flow

```
API Layer
    ↓ depends on
Domain Layer (via ports/interfaces)
    ↓ implemented by
Infrastructure Layer (adapters)

Critical Rule: One-way dependency
Domain NEVER imports from Infrastructure
Infrastructure implements Domain ports
```

---

## Database Schema (IMPLEMENTED)

### Complete Schema: 10 Tables (All Implemented ✅)

**Location**: `src/infrastructure/database/models.py`

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: RAW EVENTS (Immutable Audit Trail)                    │
└─────────────────────────────────────────────────────────────────┘

TABLE: app.chat_events ✅
┌────────────────────┬──────────────────┬──────────────────────────┐
│ Field              │ Type             │ Purpose                  │
├────────────────────┼──────────────────┼──────────────────────────┤
│ event_id           │ BIGSERIAL PK     │ Auto-increment ID        │
│ session_id         │ UUID NOT NULL    │ Conversation grouping    │
│ user_id            │ TEXT NOT NULL    │ User identifier          │
│ role               │ TEXT NOT NULL    │ user|assistant|system    │
│ content            │ TEXT NOT NULL    │ Message content          │
│ content_hash       │ TEXT NOT NULL    │ Deduplication            │
│ metadata           │ JSONB            │ Context-specific data    │
│ created_at         │ TIMESTAMPTZ      │ Event timestamp          │
├────────────────────┴──────────────────┴──────────────────────────┤
│ UNIQUE(session_id, content_hash)                                │
│ INDEX: session_id, (user_id, created_at)                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: ENTITY RESOLUTION (Grounding)                         │
└─────────────────────────────────────────────────────────────────┘

TABLE: app.canonical_entities ✅
┌────────────────────┬──────────────────┬──────────────────────────┐
│ Field              │ Type             │ Purpose                  │
├────────────────────┼──────────────────┼──────────────────────────┤
│ entity_id          │ TEXT PK          │ e.g., customer:gai_123   │
│ entity_type        │ TEXT NOT NULL    │ customer|product|order   │
│ canonical_name     │ TEXT NOT NULL    │ Gai Media Entertainment  │
│ external_ref       │ JSONB NOT NULL   │ {table: customers, id: }│
│ properties         │ JSONB            │ Cached domain data       │
│ created_at         │ TIMESTAMPTZ      │ First resolution         │
│ updated_at         │ TIMESTAMPTZ      │ Last property update     │
├────────────────────┴──────────────────┴──────────────────────────┤
│ INDEX: entity_type, canonical_name                              │
│                                                                  │
│ Design Note: Lazy creation - entities created on first mention │
│ external_ref links to domain DB (customers.customer_id, etc.)  │
└─────────────────────────────────────────────────────────────────┘

TABLE: app.entity_aliases ✅
┌────────────────────┬──────────────────┬──────────────────────────┐
│ Field              │ Type             │ Purpose                  │
├────────────────────┼──────────────────┼──────────────────────────┤
│ alias_id           │ BIGSERIAL PK     │ Auto-increment ID        │
│ canonical_entity_id│ TEXT FK          │ Links to canonical       │
│ alias_text         │ TEXT NOT NULL    │ "Gai", "Gai Corp"        │
│ alias_source       │ TEXT NOT NULL    │ exact|fuzzy|learned|user │
│ user_id            │ TEXT             │ NULL = global alias      │
│ confidence         │ REAL NOT NULL    │ 0.0-1.0 (default 1.0)    │
│ use_count          │ INT NOT NULL     │ Popularity tracking      │
│ metadata           │ JSONB            │ Disambiguation context   │
│ created_at         │ TIMESTAMPTZ      │ First learned            │
├────────────────────┴──────────────────┴──────────────────────────┤
│ UNIQUE(alias_text, user_id, canonical_entity_id)               │
│ INDEX: alias_text, canonical_entity_id, user_id (partial)      │
│                                                                  │
│ Design Note: NULL user_id = global alias (all users)           │
│ User-specific aliases checked first in resolution              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: EPISODIC MEMORY (Events with Meaning)                 │
└─────────────────────────────────────────────────────────────────┘

TABLE: app.episodic_memories ✅
┌────────────────────┬──────────────────┬──────────────────────────┐
│ Field              │ Type             │ Purpose                  │
├────────────────────┼──────────────────┼──────────────────────────┤
│ memory_id          │ BIGSERIAL PK     │ Auto-increment ID        │
│ user_id            │ TEXT NOT NULL    │ User scope               │
│ session_id         │ UUID NOT NULL    │ Conversation context     │
│ summary            │ TEXT NOT NULL    │ LLM-generated summary    │
│ event_type         │ TEXT NOT NULL    │ question|statement|...   │
│ source_event_ids   │ BIGINT[]         │ Chat events (provenance) │
│ entities           │ JSONB NOT NULL   │ Entity mentions + coref  │
│ domain_facts_ref   │ JSONB            │ Which DB facts queried   │
│ importance         │ REAL NOT NULL    │ 0.0-1.0 (default 0.5)    │
│ embedding          │ vector(1536)     │ Semantic search          │
│ created_at         │ TIMESTAMPTZ      │ Memory creation          │
├────────────────────┴──────────────────┴──────────────────────────┤
│ INDEX: (user_id, created_at), session_id                       │
│ IVFFLAT INDEX: embedding vector_cosine_ops (lists=100)         │
│                                                                  │
│ entities JSONB structure:                                       │
│ [{                                                               │
│   "id": "customer:gai_123",                                     │
│   "name": "Gai Media Entertainment",                            │
│   "type": "customer",                                           │
│   "mentions": [                                                  │
│     {"text": "Gai Media", "position": 10, "is_coreference": false},│
│     {"text": "they", "position": 45, "is_coreference": true}   │
│   ]                                                              │
│ }]                                                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LAYER 4: SEMANTIC MEMORY (Abstracted Facts)                    │
└─────────────────────────────────────────────────────────────────┘

TABLE: app.semantic_memories ✅
┌────────────────────┬──────────────────┬──────────────────────────┐
│ Field              │ Type             │ Purpose                  │
├────────────────────┼──────────────────┼──────────────────────────┤
│ memory_id          │ BIGSERIAL PK     │ Auto-increment ID        │
│ user_id            │ TEXT NOT NULL    │ User scope               │
│                                                                  │
│ --- TRIPLE STRUCTURE (Subject-Predicate-Object) ---            │
│ subject_entity_id  │ TEXT FK          │ Entity this is about     │
│ predicate          │ TEXT NOT NULL    │ prefers, requires, is... │
│ predicate_type     │ TEXT NOT NULL    │ preference|requirement|..│
│ object_value       │ JSONB NOT NULL   │ Flexible object repr.    │
│                                                                  │
│ --- CONFIDENCE & EVOLUTION ---                                  │
│ confidence         │ REAL NOT NULL    │ 0.0-1.0 (default 0.7)    │
│ confidence_factors │ JSONB            │ {base, reinforce, decay} │
│ reinforcement_count│ INT NOT NULL     │ Validation count         │
│ last_validated_at  │ TIMESTAMPTZ      │ Last reinforcement/use   │
│                                                                  │
│ --- PROVENANCE ---                                              │
│ source_type        │ TEXT NOT NULL    │ episodic|consolidation|..│
│ source_memory_id   │ BIGINT           │ Parent episodic ID       │
│ extracted_from_evt │ BIGINT FK        │ Original chat event      │
│                                                                  │
│ --- LIFECYCLE ---                                               │
│ status             │ TEXT NOT NULL    │ active|aging|superseded  │
│ superseded_by_id   │ BIGINT FK        │ Newer memory that won    │
│                                                                  │
│ --- RETRIEVAL ---                                               │
│ embedding          │ vector(1536)     │ Semantic search          │
│ importance         │ REAL NOT NULL    │ 0.0-1.0 (default 0.5)    │
│                                                                  │
│ created_at         │ TIMESTAMPTZ      │ First extracted          │
│ updated_at         │ TIMESTAMPTZ      │ Last modified            │
├────────────────────┴──────────────────┴──────────────────────────┤
│ CHECK: confidence >= 0 AND confidence <= 1                      │
│ CHECK: status IN ('active','aging','superseded','invalidated') │
│ INDEX: (user_id, status), (subject_entity_id, predicate)       │
│ IVFFLAT INDEX: embedding vector_cosine_ops (lists=100)         │
│                                                                  │
│ Design Note: Passive decay computation                         │
│ Current confidence = confidence * exp(-days * DECAY_RATE)      │
│ Computed on retrieval, NOT stored                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LAYER 5: PROCEDURAL MEMORY (Learned Heuristics)                │
└─────────────────────────────────────────────────────────────────┘

TABLE: app.procedural_memories ✅
┌────────────────────┬──────────────────┬──────────────────────────┐
│ Field              │ Type             │ Purpose                  │
├────────────────────┼──────────────────┼──────────────────────────┤
│ memory_id          │ BIGSERIAL PK     │ Auto-increment ID        │
│ user_id            │ TEXT NOT NULL    │ User scope               │
│ trigger_pattern    │ TEXT NOT NULL    │ "When X mentioned..."    │
│ trigger_features   │ JSONB NOT NULL   │ {intent, entities, ...}  │
│ action_heuristic   │ TEXT NOT NULL    │ "...also check Y"        │
│ action_structure   │ JSONB NOT NULL   │ {action_type, queries..} │
│ observed_count     │ INT NOT NULL     │ Pattern frequency        │
│ confidence         │ REAL NOT NULL    │ 0.0-1.0 (default 0.5)    │
│ embedding          │ vector(1536)     │ Semantic search          │
│ created_at         │ TIMESTAMPTZ      │ First learned            │
│ updated_at         │ TIMESTAMPTZ      │ Last observed            │
├────────────────────┴──────────────────┴──────────────────────────┤
│ INDEX: user_id, confidence                                      │
│ IVFFLAT INDEX: embedding vector_cosine_ops (lists=100)         │
│                                                                  │
│ Phase: 2/3 - Pattern learning from repeated behavior           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LAYER 6: MEMORY SUMMARIES (Cross-Session Consolidation)        │
└─────────────────────────────────────────────────────────────────┘

TABLE: app.memory_summaries ✅
┌────────────────────┬──────────────────┬──────────────────────────┐
│ Field              │ Type             │ Purpose                  │
├────────────────────┼──────────────────┼──────────────────────────┤
│ summary_id         │ BIGSERIAL PK     │ Auto-increment ID        │
│ user_id            │ TEXT NOT NULL    │ User scope               │
│ scope_type         │ TEXT NOT NULL    │ entity|topic|session_win │
│ scope_identifier   │ TEXT             │ entity_id or topic key   │
│ summary_text       │ TEXT NOT NULL    │ LLM-generated summary    │
│ key_facts          │ JSONB NOT NULL   │ Extracted highlights     │
│ source_data        │ JSONB NOT NULL   │ Provenance (memory IDs)  │
│ supersedes_id      │ BIGINT FK        │ Previous summary         │
│ confidence         │ REAL NOT NULL    │ 0.0-1.0 (default 0.8)    │
│ embedding          │ vector(1536)     │ Semantic search          │
│ created_at         │ TIMESTAMPTZ      │ Consolidation time       │
├────────────────────┴──────────────────┴──────────────────────────┤
│ INDEX: (user_id, scope_type, scope_identifier)                 │
│ IVFFLAT INDEX: embedding vector_cosine_ops (lists=100)         │
│                                                                  │
│ source_data JSONB structure:                                    │
│ {                                                                │
│   "episodic_ids": [101, 105, 112, ...],                        │
│   "semantic_ids": [45, 67],                                     │
│   "session_ids": ["uuid1", "uuid2", ...],                      │
│   "time_range": {"start": "2025-01-01", "end": "2025-01-15"}  │
│ }                                                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ SUPPORTING TABLES (Ontology & Conflict Tracking)               │
└─────────────────────────────────────────────────────────────────┘

TABLE: app.domain_ontology ✅
┌────────────────────┬──────────────────┬──────────────────────────┐
│ Field              │ Type             │ Purpose                  │
├────────────────────┼──────────────────┼──────────────────────────┤
│ relation_id        │ BIGSERIAL PK     │ Auto-increment ID        │
│ from_entity_type   │ TEXT NOT NULL    │ customer                 │
│ relation_type      │ TEXT NOT NULL    │ has|creates|requires     │
│ to_entity_type     │ TEXT NOT NULL    │ order                    │
│ cardinality        │ TEXT NOT NULL    │ 1:many                   │
│ relation_semantics │ TEXT NOT NULL    │ Business meaning         │
│ join_spec          │ JSONB NOT NULL   │ SQL join definition      │
│ constraints        │ JSONB            │ Business rules           │
│ created_at         │ TIMESTAMPTZ      │ Ontology definition      │
├────────────────────┴──────────────────┴──────────────────────────┤
│ UNIQUE(from_entity_type, relation_type, to_entity_type)        │
│ INDEX: from_entity_type, to_entity_type                         │
│                                                                  │
│ join_spec example:                                              │
│ {                                                                │
│   "from_table": "customers",                                    │
│   "to_table": "orders",                                         │
│   "join_on": "customers.customer_id = orders.customer_id"      │
│ }                                                                │
│                                                                  │
│ Usage: Automatic related data fetching via graph traversal     │
│ When resolving "Gai Media", also fetch orders using join_spec  │
└─────────────────────────────────────────────────────────────────┘

TABLE: app.memory_conflicts ✅
┌────────────────────┬──────────────────┬──────────────────────────┐
│ Field              │ Type             │ Purpose                  │
├────────────────────┼──────────────────┼──────────────────────────┤
│ conflict_id        │ BIGSERIAL PK     │ Auto-increment ID        │
│ detected_at_evt_id │ BIGINT FK        │ Chat event that revealed │
│ conflict_type      │ TEXT NOT NULL    │ memory_vs_memory|mem_vs_ │
│ conflict_data      │ JSONB NOT NULL   │ Conflicting values       │
│ resolution_strategy│ TEXT             │ trust_db|recent|ask_user │
│ resolution_outcome │ JSONB            │ What was decided         │
│ resolved_at        │ TIMESTAMPTZ      │ Resolution time          │
│ created_at         │ TIMESTAMPTZ      │ Detection time           │
├────────────────────┴──────────────────┴──────────────────────────┤
│ INDEX: detected_at_event_id, conflict_type                      │
│                                                                  │
│ Epistemic Humility: Never silently ignore contradictions       │
│ All conflicts logged, user can see system reasoning            │
└─────────────────────────────────────────────────────────────────┘

TABLE: app.system_config ✅
┌────────────────────┬──────────────────┬──────────────────────────┐
│ Field              │ Type             │ Purpose                  │
├────────────────────┼──────────────────┼──────────────────────────┤
│ config_key         │ TEXT PK          │ Parameter name           │
│ config_value       │ JSONB NOT NULL   │ Value (any type)         │
│ updated_at         │ TIMESTAMPTZ      │ Last tuning              │
├────────────────────┴──────────────────┴──────────────────────────┤
│ Stores: Heuristic overrides, feature flags, runtime config     │
│ Example: {"DECAY_RATE_PER_DAY": 0.012} (tuned in Phase 2)     │
└─────────────────────────────────────────────────────────────────┘
```

### Database Design Decisions

**1. pgvector for Semantic Search**
- All memory tables have `embedding vector(1536)` column
- IVFFlat indexes with `vector_cosine_ops` for fast approximate nearest neighbor
- Target: <50ms P95 for semantic search

**2. JSONB for Context-Specific Data**
- Used when data varies by instance and not queried independently
- Examples: `entities` in episodic memories, `confidence_factors`, `metadata`
- Avoids complex joins for data that's always loaded with parent

**3. Passive Decay Computation**
- Confidence decay NOT stored in database
- Formula: `effective_confidence = stored_confidence * exp(-days_since_validation * DECAY_RATE_PER_DAY)`
- Computed on-demand during retrieval
- Benefits: Simpler schema, no background jobs, always current

**4. Explicit Provenance Chain**
- Every semantic memory links back to episodic memory (`source_memory_id`)
- Every episodic memory links to chat events (`source_event_ids[]`)
- Enables "explain your reasoning" capability

**5. Lazy Entity Creation**
- Entities NOT pre-loaded from domain database
- Created on first mention during resolution
- `external_ref` JSONB stores link to domain DB record

---

## End-to-End Request Flow (PLANNED)

### Primary API: POST /chat

**Status**: ⏳ To be implemented (estimated Week 5-8 of Phase 1)

```
┌──────────────────────────────────────────────────────────────────┐
│ CLIENT REQUEST                                                    │
│ POST /api/v1/chat                                                │
│                                                                   │
│ {                                                                 │
│   "message": "What did Gai Media order last month?",            │
│   "user_id": "user_123",                                         │
│   "session_id": "session_abc"                                    │
│ }                                                                 │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│ STAGE 1: INGEST RAW EVENT (~5ms)                                 │
│ Status: ⏳ Pending                                                │
│                                                                   │
│ Actions:                                                          │
│ 1. Store message in chat_events table (immutable audit)          │
│ 2. Generate content_hash for deduplication                       │
│ 3. Extract metadata (client_info, timestamp)                     │
│                                                                   │
│ Database Write:                                                   │
│   INSERT INTO app.chat_events (session_id, user_id, role,       │
│                                 content, content_hash, ...)      │
│   VALUES ('session_abc', 'user_123', 'user',                    │
│           'What did Gai Media...', 'hash123', ...)               │
│                                                                   │
│ Output: event_id = 1042                                          │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│ STAGE 2: ENTITY RESOLUTION (~50ms)                               │
│ Status: ⏳ Pending (EntityResolver service)                      │
│                                                                   │
│ Query Analysis:                                                   │
│ • Detected mentions: ["Gai Media"]                               │
│ • Intent: factual_entity_focused (asking about specific entity) │
│                                                                   │
│ 5-Stage Resolution for "Gai Media":                              │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Stage 1: Exact Match                                       │  │
│ │   Query: SELECT * FROM canonical_entities                 │  │
│ │          WHERE canonical_name = 'Gai Media'               │  │
│ │   Result: ❌ Not found                                     │  │
│ └────────────────────────────────────────────────────────────┘  │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Stage 2: User-Specific Alias                              │  │
│ │   Query: SELECT * FROM entity_aliases                     │  │
│ │          WHERE alias_text = 'Gai Media'                   │  │
│ │            AND user_id = 'user_123'                       │  │
│ │   Result: ✅ Found → customer:gai_123 (confidence: 0.95)  │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ Resolution Result:                                                │
│ {                                                                 │
│   "mention": "Gai Media",                                        │
│   "entity_id": "customer:gai_123",                              │
│   "canonical_name": "Gai Media Entertainment",                  │
│   "entity_type": "customer",                                     │
│   "confidence": 0.95,                                            │
│   "resolution_method": "user_alias",                            │
│   "stage": 2                                                     │
│ }                                                                 │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│ STAGE 3: DOMAIN DATABASE ENRICHMENT (~50ms)                      │
│ Status: ⏳ Pending (DomainDBConnector)                           │
│                                                                   │
│ Step 3a: Fetch Entity Properties                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Query Domain DB (read-only connection):                   │  │
│ │   SELECT customer_id, company_name, payment_terms,        │  │
│ │          delivery_preference, status                      │  │
│ │   FROM customers                                          │  │
│ │   WHERE customer_id = 123  -- from external_ref           │  │
│ │                                                            │  │
│ │ Result:                                                    │  │
│ │   customer_id: 123                                        │  │
│ │   company_name: Gai Media Entertainment                   │  │
│ │   payment_terms: NET30                                    │  │
│ │   delivery_preference: Friday                             │  │
│ │   status: active                                          │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ Step 3b: Ontology-Aware Graph Traversal                          │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Query Ontology:                                            │  │
│ │   SELECT relation_type, to_entity_type, join_spec         │  │
│ │   FROM domain_ontology                                     │  │
│ │   WHERE from_entity_type = 'customer'                      │  │
│ │                                                            │  │
│ │ Found Relations:                                           │  │
│ │   • customer HAS orders (1:many)                          │  │
│ │   • customer HAS invoices (1:many)                        │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ Step 3c: Fetch Related Entities (Filtered by "last month")       │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Query Domain DB:                                           │  │
│ │   SELECT order_id, order_date, total_amount, status       │  │
│ │   FROM orders                                              │  │
│ │   WHERE customer_id = 123                                  │  │
│ │     AND order_date >= '2024-09-01'                         │  │
│ │     AND order_date < '2024-10-01'                          │  │
│ │                                                            │  │
│ │ Results (3 orders):                                        │  │
│ │   [                                                         │  │
│ │     {order_id: 1009, date: 2024-09-05, amount: 1200.00}, │  │
│ │     {order_id: 1015, date: 2024-09-12, amount: 850.00},  │  │
│ │     {order_id: 1023, date: 2024-09-26, amount: 2100.00}  │  │
│ │   ]                                                         │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ Domain Facts Collected (Correspondence Truth):                   │
│   • Customer details (name, payment terms, preferences)          │
│   • 3 orders from September 2024                                 │
│   • Total: $4,150.00                                             │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│ STAGE 4: MEMORY RETRIEVAL (~100ms)                               │
│ Status: ⏳ Pending (MemoryRetriever service)                     │
│                                                                   │
│ Step 4a: Query Understanding                                     │
│   Intent: factual_entity_focused                                 │
│   Strategy: factual_entity_focused weights                       │
│   Time filter: Last month (2024-09-01 to 2024-10-01)           │
│                                                                   │
│ Step 4b: Candidate Generation (Parallel)                         │
│                                                                   │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Source 1: Semantic Search (pgvector)                      │  │
│ │   SELECT memory_id, summary, embedding                     │  │
│ │   FROM episodic_memories                                   │  │
│ │   WHERE user_id = 'user_123'                              │  │
│ │   ORDER BY embedding <=> '[query_embedding]'              │  │
│ │   LIMIT 50                                                 │  │
│ │                                                            │  │
│ │   Results: 50 semantically similar memories                │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Source 2: Entity-Based Retrieval                          │  │
│ │   SELECT memory_id FROM episodic_memories                  │  │
│ │   WHERE user_id = 'user_123'                              │  │
│ │     AND entities @> '[{"id": "customer:gai_123"}]'        │  │
│ │   LIMIT 30                                                 │  │
│ │                                                            │  │
│ │   Results: 30 memories mentioning Gai Media                │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Source 3: Temporal Window                                  │  │
│ │   SELECT memory_id FROM episodic_memories                  │  │
│ │   WHERE user_id = 'user_123'                              │  │
│ │     AND created_at >= '2024-09-01'                        │  │
│ │     AND created_at < '2024-10-01'                         │  │
│ │   LIMIT 30                                                 │  │
│ │                                                            │  │
│ │   Results: 30 recent memories                              │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Source 4: Memory Summaries                                 │  │
│ │   SELECT summary_id FROM memory_summaries                  │  │
│ │   WHERE user_id = 'user_123'                              │  │
│ │     AND scope_identifier = 'customer:gai_123'             │  │
│ │   ORDER BY confidence DESC                                 │  │
│ │   LIMIT 5                                                  │  │
│ │                                                            │  │
│ │   Results: 2 entity summaries (get 15% boost)             │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ Step 4c: Multi-Signal Scoring                                    │
│                                                                   │
│ Strategy Weights (factual_entity_focused):                       │
│   semantic_similarity:  0.25                                     │
│   entity_overlap:       0.40  ← Dominant for this query          │
│   temporal_relevance:   0.20                                     │
│   importance:           0.10                                     │
│   reinforcement:        0.05                                     │
│                                                                   │
│ For each candidate memory:                                       │
│   score = 0.25 * semantic_sim(query, memory)                    │
│         + 0.40 * entity_overlap(["customer:gai_123"], memory)   │
│         + 0.20 * temporal_score(memory, "last month")           │
│         + 0.10 * memory.importance                               │
│         + 0.05 * reinforcement_score(memory)                     │
│                                                                   │
│ Example Score Calculation (memory_id=512):                       │
│   semantic_sim:     0.82  → 0.25 * 0.82 = 0.205                 │
│   entity_overlap:   1.00  → 0.40 * 1.00 = 0.400  ← Key match    │
│   temporal:         0.90  → 0.20 * 0.90 = 0.180                 │
│   importance:       0.70  → 0.10 * 0.70 = 0.070                 │
│   reinforcement:    0.60  → 0.05 * 0.60 = 0.030                 │
│   TOTAL SCORE:      0.885  ← High relevance!                    │
│                                                                   │
│ Step 4d: Selection & Context Budget                              │
│                                                                   │
│ Token Budget (max_context_tokens = 3000):                        │
│   Domain facts:    40% = 1200 tokens                             │
│   Summaries:       20% =  600 tokens                             │
│   Semantic facts:  20% =  600 tokens                             │
│   Episodic:        15% =  450 tokens                             │
│   Procedural:       5% =  150 tokens                             │
│                                                                   │
│ Selected Memories (top 15, fitting within budget):               │
│   • 2 memory summaries about Gai Media (high-level patterns)    │
│   • 5 semantic facts (payment preferences, delivery notes)       │
│   • 8 episodic memories (past conversations about orders)        │
│                                                                   │
│ Memories Collected (Contextual Truth):                           │
│   • "Gai Media prefers Friday deliveries" (confidence: 0.85)    │
│   • "User previously asked about invoice INV-1009" (Sept 5)     │
│   • "Customer was unhappy with late delivery in July"           │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│ STAGE 5: CONTEXT ASSEMBLY (~20ms)                                │
│ Status: ⏳ Pending                                                │
│                                                                   │
│ Combine Domain Facts + Memories:                                 │
│                                                                   │
│ Context Structure:                                                │
│ {                                                                 │
│   "domain_facts": {                                              │
│     "customer": {                                                │
│       "name": "Gai Media Entertainment",                        │
│       "payment_terms": "NET30",                                  │
│       "delivery_preference": "Friday",                           │
│       "status": "active"                                         │
│     },                                                            │
│     "orders_last_month": [                                       │
│       {"id": 1009, "date": "2024-09-05", "amount": 1200.00},   │
│       {"id": 1015, "date": "2024-09-12", "amount": 850.00},    │
│       {"id": 1023, "date": "2024-09-26", "amount": 2100.00}    │
│     ],                                                            │
│     "total_amount": 4150.00                                      │
│   },                                                              │
│   "memories": {                                                   │
│     "summaries": [                                               │
│       "Gai Media: Consistent customer since 2023, prefers..."   │
│     ],                                                            │
│     "semantic_facts": [                                          │
│       {"fact": "Prefers Friday deliveries", "confidence": 0.85},│
│       {"fact": "Sensitive about invoice timing", "conf": 0.78}  │
│     ],                                                            │
│     "episodic": [                                                │
│       {"summary": "User asked about INV-1009 on Sept 10"},      │
│       {"summary": "Customer complained about July delivery"}    │
│     ]                                                             │
│   },                                                              │
│   "entities_resolved": [                                         │
│     {"mention": "Gai Media", "entity_id": "customer:gai_123"}  │
│   ]                                                               │
│ }                                                                 │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│ STAGE 6: LLM SYNTHESIS (~1500ms)                                 │
│ Status: ⏳ Pending (OpenAI/Claude API integration)               │
│                                                                   │
│ Prompt to LLM:                                                    │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ System:                                                    │  │
│ │ You are an experienced business intelligence assistant.   │  │
│ │ Answer the user's question using BOTH authoritative       │  │
│ │ database facts AND contextual memory.                     │  │
│ │                                                            │  │
│ │ When memory conflicts with database, trust the database   │  │
│ │ but note the discrepancy. Always cite sources.            │  │
│ │                                                            │  │
│ │ User Query:                                                │  │
│ │ "What did Gai Media order last month?"                    │  │
│ │                                                            │  │
│ │ Context:                                                   │  │
│ │ [Full context from Stage 5]                               │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ LLM Response:                                                     │
│ {                                                                 │
│   "answer": "Gai Media Entertainment placed 3 orders in         │
│              September 2024:\n\n                                 │
│              1. Order #1009 (Sept 5) - $1,200.00\n             │
│              2. Order #1015 (Sept 12) - $850.00\n              │
│              3. Order #1023 (Sept 26) - $2,100.00\n            │
│              \nTotal: $4,150.00\n\n                             │
│              Note: Based on their delivery preference, these    │
│              likely went out on Fridays. I noticed you asked    │
│              about invoice INV-1009 previously - that's from    │
│              the first order above.",                            │
│                                                                   │
│   "citations": [                                                 │
│     {                                                             │
│       "source": "domain_db",                                     │
│       "table": "orders",                                         │
│       "data": "3 orders from September 2024"                    │
│     },                                                            │
│     {                                                             │
│       "source": "semantic_memory",                               │
│       "memory_id": 145,                                          │
│       "fact": "Prefers Friday deliveries",                      │
│       "confidence": 0.85                                         │
│     },                                                            │
│     {                                                             │
│       "source": "episodic_memory",                               │
│       "memory_id": 512,                                          │
│       "summary": "User asked about INV-1009 on Sept 10"         │
│     }                                                             │
│   ],                                                              │
│                                                                   │
│   "confidence": 0.95,  // High confidence (DB + memory agree)   │
│   "conflicts_detected": []                                       │
│ }                                                                 │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│ STAGE 7: MEMORY CREATION (Async, ~50ms)                          │
│ Status: ⏳ Pending (MemoryExtractor service)                     │
│                                                                   │
│ Step 7a: Create Episodic Memory                                  │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ INSERT INTO app.episodic_memories (                        │  │
│ │   user_id, session_id, summary, event_type,               │  │
│ │   source_event_ids, entities, importance, embedding       │  │
│ │ ) VALUES (                                                 │  │
│ │   'user_123',                                              │  │
│ │   'session_abc',                                           │  │
│ │   'User asked about Gai Media orders from September',     │  │
│ │   'question',                                              │  │
│ │   ARRAY[1042],  -- chat event ID                          │  │
│ │   '[{"id": "customer:gai_123", "name": "Gai Media", ...}]',│  │
│ │   0.6,  -- Importance (question type = 0.4 base + boost)  │  │
│ │   '[embedding_vector]'                                     │  │
│ │ )                                                          │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ Step 7b: Extract Semantic Facts (if applicable)                  │
│   Analysis: Query is question, not statement                     │
│   Decision: No new semantic facts to extract                     │
│   (Would extract if user said: "Remember: Gai prefers X")       │
│                                                                   │
│ Step 7c: Reinforce Existing Memories                             │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Memory ID 145 was retrieved ("Prefers Friday deliveries")│  │
│ │ Action: Reinforce (validation count: 2 → 3)               │  │
│ │                                                            │  │
│ │ UPDATE app.semantic_memories                               │  │
│ │ SET reinforcement_count = 3,                               │  │
│ │     confidence = confidence + 0.05,  -- 3rd boost         │  │
│ │     last_validated_at = NOW()                              │  │
│ │ WHERE memory_id = 145                                      │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ Step 7d: Check for Conflicts (Phase 1)                           │
│   Compare LLM response with existing memories                    │
│   Check domain DB facts vs semantic memories                     │
│   Result: No conflicts detected (DB and memory aligned)          │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│ STAGE 8: RESPONSE (~5ms)                                          │
│ Status: ⏳ Pending                                                │
│                                                                   │
│ {                                                                 │
│   "response": "Gai Media Entertainment placed 3 orders in       │
│                September 2024:\n\n                               │
│                1. Order #1009 (Sept 5) - $1,200.00\n           │
│                2. Order #1015 (Sept 12) - $850.00\n            │
│                3. Order #1023 (Sept 26) - $2,100.00\n          │
│                \nTotal: $4,150.00\n\n                           │
│                Note: Based on their delivery preference...",     │
│                                                                   │
│   "augmentation": {                                              │
│     "entities_resolved": [                                       │
│       {                                                           │
│         "mention": "Gai Media",                                  │
│         "entity_id": "customer:gai_123",                        │
│         "canonical_name": "Gai Media Entertainment",            │
│         "resolution_method": "user_alias",                      │
│         "confidence": 0.95                                       │
│       }                                                           │
│     ],                                                            │
│     "domain_facts_used": 4,    // 3 orders + 1 customer detail │
│     "memories_retrieved": 15,   // Total memories considered     │
│     "memories_used": 8,        // Actually in context            │
│     "memories_created": 1,     // New episodic memory            │
│     "memories_reinforced": 1   // Updated semantic memory        │
│   },                                                              │
│                                                                   │
│   "citations": [                                                 │
│     {"source": "domain_db", "table": "orders", ...},            │
│     {"source": "semantic_memory", "memory_id": 145, ...},       │
│     {"source": "episodic_memory", "memory_id": 512, ...}        │
│   ],                                                              │
│                                                                   │
│   "confidence": 0.95,                                            │
│   "conflicts": [],                                               │
│   "timestamp": "2025-10-15T10:30:42Z"                           │
│ }                                                                 │
└───────────────────────────────────────────────────────────────────┘

TOTAL LATENCY: ~1770ms
  Ingest:        5ms
  Entity Res:   50ms
  Domain Query: 50ms
  Retrieval:   100ms
  Assembly:     20ms
  LLM:        1500ms  ← Dominates latency
  Memory:      50ms (async, doesn't block response)
  Response:     5ms
```

---

## Subsystem Flows

### Subsystem 1: Entity Resolution (5-Stage Algorithm)

**Implementation**: ⏳ `src/domain/services/entity_resolver.py` (pending)

**Design Document**: `docs/design/ENTITY_RESOLUTION_DESIGN_V2.md`

```
ENTITY RESOLUTION: "Gai" → customer:gai_123

Input:
  mention = "Gai"
  user_id = "user_123"
  context = ResolutionContext(session_id, recent_entities, conversation)

┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: EXACT MATCH (confidence: 1.0)                         │
│ Status: ⏳ Pending                                              │
│                                                                  │
│ Query:                                                           │
│   SELECT entity_id, canonical_name, entity_type                │
│   FROM app.canonical_entities                                   │
│   WHERE canonical_name = 'Gai'  -- Case-sensitive exact match  │
│                                                                  │
│ Result: ❌ No match                                             │
│ Next: Try Stage 2                                               │
└─────────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: USER-SPECIFIC ALIAS (confidence: 0.95)                │
│ Status: ⏳ Pending                                              │
│                                                                  │
│ Query:                                                           │
│   SELECT ea.canonical_entity_id, ea.confidence, ce.canonical_name│
│   FROM app.entity_aliases ea                                    │
│   JOIN app.canonical_entities ce                                │
│     ON ea.canonical_entity_id = ce.entity_id                    │
│   WHERE ea.alias_text = 'Gai'                                   │
│     AND ea.user_id = 'user_123'  -- User-specific first         │
│   ORDER BY ea.use_count DESC, ea.confidence DESC                │
│   LIMIT 5                                                        │
│                                                                  │
│ Result: ✅ Found                                                │
│   entity_id: customer:gai_123                                   │
│   canonical_name: Gai Media Entertainment                       │
│   confidence: 0.95                                               │
│   alias_source: user_stated                                     │
│                                                                  │
│ Update Alias:                                                    │
│   UPDATE app.entity_aliases                                     │
│   SET use_count = use_count + 1                                 │
│   WHERE alias_id = 42                                            │
│                                                                  │
│ Return: ResolutionResult(entity_id=customer:gai_123, ...)      │
│ Success! Skip remaining stages.                                 │
└─────────────────────────────────────────────────────────────────┘

IF Stage 2 fails, continue to Stage 3...

┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: FUZZY MATCH (confidence: 0.70-0.85)                   │
│ Status: ⏳ Pending (requires pg_trgm extension)                 │
│                                                                  │
│ Query (uses PostgreSQL pg_trgm extension):                      │
│   SELECT entity_id, canonical_name,                             │
│          similarity(canonical_name, 'Gai') AS sim               │
│   FROM app.canonical_entities                                   │
│   WHERE similarity(canonical_name, 'Gai') > 0.70  -- Threshold │
│   ORDER BY sim DESC                                              │
│   LIMIT 10                                                       │
│                                                                  │
│ Example Results:                                                 │
│   • "Gai Media Entertainment" (sim: 0.82) → confidence: 0.82   │
│   • "Gai Corporation" (sim: 0.78) → confidence: 0.78           │
│                                                                  │
│ Decision Logic:                                                  │
│   IF top_match.similarity >= 0.85:                              │
│     Auto-resolve (high confidence)                              │
│     Create learned alias for future                             │
│   ELIF top_match.similarity >= 0.70:                            │
│     IF confidence_gap < 0.15 (close matches):                   │
│       → Go to Stage 5 (User Disambiguation)                     │
│     ELSE:                                                        │
│       Auto-resolve with confidence = similarity                 │
│   ELSE:                                                          │
│     → Go to Stage 4 (Coreference)                               │
└─────────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 4: COREFERENCE RESOLUTION (confidence: 0.60)             │
│ Status: ⏳ Pending (requires LLM integration)                   │
│                                                                  │
│ Context Analysis:                                                │
│   Recent conversation (last 5 turns):                           │
│   [Turn 1] User: "Tell me about Gai Media Entertainment"       │
│   [Turn 2] Asst: "[info about customer:gai_123]"               │
│   [Turn 3] User: "What did Gai order last month?"  ← Current   │
│                                                                  │
│ Coreference Detection:                                           │
│   • "Gai" likely refers to most recently mentioned entity       │
│   • Extract entities from context.recent_entities               │
│   • Find entity with highest recency score + name similarity    │
│                                                                  │
│ LLM-Assisted Coreference (if ambiguous):                        │
│   Prompt: "In this context, does 'Gai' refer to:              │
│            A) Gai Media Entertainment (customer:gai_123)       │
│            B) A new entity?"                                    │
│                                                                  │
│ Result:                                                          │
│   entity_id: customer:gai_123                                   │
│   confidence: 0.60  (coreference confidence from heuristics)   │
│   method: coreference                                           │
│                                                                  │
│ Create Coreference Alias:                                       │
│   INSERT INTO app.entity_aliases (                              │
│     canonical_entity_id, alias_text, alias_source,             │
│     user_id, confidence                                         │
│   ) VALUES (                                                     │
│     'customer:gai_123', 'Gai', 'learned', 'user_123', 0.60    │
│   )                                                              │
└─────────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 5: USER DISAMBIGUATION (confidence: 0.85 after choice)   │
│ Status: ⏳ Pending                                              │
│                                                                  │
│ Trigger: Multiple candidates with confidence_gap < 0.15         │
│                                                                  │
│ Present to User:                                                 │
│   "I found multiple matches for 'Gai':                         │
│    1. Gai Media Entertainment (customer, last seen Sept 20)    │
│    2. Gai Corporation (customer, last seen March 15)           │
│    3. Create new entity                                         │
│    Which did you mean?"                                         │
│                                                                  │
│ User Selection → entity_id = customer:gai_123                   │
│                                                                  │
│ Actions:                                                         │
│ 1. Return resolution with confidence: 0.85                      │
│ 2. Create high-confidence user-stated alias:                    │
│    INSERT INTO app.entity_aliases (                             │
│      canonical_entity_id, alias_text, alias_source,            │
│      user_id, confidence                                        │
│    ) VALUES (                                                    │
│      'customer:gai_123', 'Gai', 'user_stated', 'user_123', 0.95│
│    )                                                             │
│ 3. Future mentions of "Gai" by this user → resolve at Stage 2  │
└─────────────────────────────────────────────────────────────────┘

LAZY ENTITY CREATION:
If ALL 5 stages fail, query domain database:
  SELECT customer_id, company_name FROM customers
  WHERE company_name ILIKE '%Gai%'

If found:
  CREATE canonical_entity:
    entity_id = generate_entity_id("customer", customer_id)
    external_ref = {"table": "customers", "id": customer_id}

  CREATE alias:
    INSERT INTO entity_aliases (mention → entity_id)

  Return resolution

If not found:
  RAISE EntityNotFoundError(mention="Gai", context=...)
  API returns: requires_clarification = true
```

### Subsystem 2: Memory Retrieval (3-Stage Pipeline)

**Implementation**: ⏳ `src/domain/services/memory_retriever.py` (pending)

**Design Document**: `docs/design/RETRIEVAL_DESIGN.md`

```
MEMORY RETRIEVAL: Multi-Signal Scoring

┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: QUERY UNDERSTANDING (~10ms)                            │
│ Status: ⏳ Pending                                              │
│                                                                  │
│ Input: "What did Gai Media order last month?"                  │
│                                                                  │
│ Extract Features:                                                │
│   • Intent Classification:                                      │
│     - Type: Question (vs statement, command)                    │
│     - Category: Factual (about specific entities/data)          │
│     - Temporal: Yes ("last month")                              │
│   • Entities: ["customer:gai_123"]                             │
│   • Temporal Filter: 2024-09-01 to 2024-10-01                  │
│   • Keywords: ["order", "last month"]                           │
│                                                                  │
│ Select Retrieval Strategy:                                      │
│   Intent: Factual + Entity-focused                             │
│   → Strategy: "factual_entity_focused"                          │
│                                                                  │
│ Load Strategy Weights (from heuristics.py):                    │
│   semantic_similarity:  0.25                                    │
│   entity_overlap:       0.40  ← Primary signal                 │
│   temporal_relevance:   0.20                                    │
│   importance:           0.10                                    │
│   reinforcement:        0.05                                    │
│                                                                  │
│ Generate Query Embedding:                                       │
│   embedding = openai.embeddings.create(                         │
│     model="text-embedding-3-small",                             │
│     input="What did Gai Media order last month?"                │
│   )                                                              │
│   → vector(1536)                                                │
└─────────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: CANDIDATE GENERATION (~60ms - Parallel Queries)       │
│ Status: ⏳ Pending                                              │
│                                                                  │
│ Execute 4 Parallel Queries:                                     │
│                                                                  │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ Query 1: Semantic Search (pgvector) - 30ms              │   │
│ │                                                          │   │
│ │ SELECT m.memory_id, m.summary, m.importance,            │   │
│ │        m.reinforcement_count, m.created_at,             │   │
│ │        m.embedding <=> $1::vector AS distance           │   │
│ │ FROM app.episodic_memories m                            │   │
│ │ WHERE m.user_id = 'user_123'                            │   │
│ │ ORDER BY m.embedding <=> $1::vector                     │   │
│ │ LIMIT 50                                                │   │
│ │                                                          │   │
│ │ Result: 50 semantically similar memories                │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ Query 2: Entity-Based - 20ms                            │   │
│ │                                                          │   │
│ │ SELECT m.memory_id, m.summary, m.entities, ...          │   │
│ │ FROM app.episodic_memories m                            │   │
│ │ WHERE m.user_id = 'user_123'                            │   │
│ │   AND m.entities @> '[{"id":"customer:gai_123"}]'       │   │
│ │ ORDER BY m.created_at DESC                               │   │
│ │ LIMIT 30                                                │   │
│ │                                                          │   │
│ │ Result: 30 memories mentioning target entity            │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ Query 3: Temporal Window - 20ms                         │   │
│ │                                                          │   │
│ │ SELECT m.memory_id, m.summary, m.importance, ...        │   │
│ │ FROM app.episodic_memories m                            │   │
│ │ WHERE m.user_id = 'user_123'                            │   │
│ │   AND m.created_at >= '2024-09-01'                      │   │
│ │   AND m.created_at < '2024-10-01'                       │   │
│ │ ORDER BY m.importance DESC                               │   │
│ │ LIMIT 30                                                │   │
│ │                                                          │   │
│ │ Result: 30 recent memories in time window               │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ Query 4: Memory Summaries - 15ms                        │   │
│ │                                                          │   │
│ │ SELECT s.summary_id, s.summary_text, s.key_facts,      │   │
│ │        s.confidence, s.embedding                         │   │
│ │ FROM app.memory_summaries s                             │   │
│ │ WHERE s.user_id = 'user_123'                            │   │
│ │   AND (s.scope_identifier = 'customer:gai_123'         │   │
│ │        OR s.scope_type = 'session_window')              │   │
│ │ ORDER BY s.confidence DESC                               │   │
│ │ LIMIT 5                                                 │   │
│ │                                                          │   │
│ │ Result: 5 relevant summaries (get 15% scoring boost)   │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Deduplication:                                                   │
│   Union all candidates → 85 unique memory_ids                  │
└─────────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: RANKING & SELECTION (~30ms)                            │
│ Status: ⏳ Pending                                              │
│                                                                  │
│ For Each Candidate Memory:                                      │
│                                                                  │
│ Step 3a: Compute 5 Signal Scores (0.0-1.0 each)                │
│                                                                  │
│ 1. Semantic Similarity:                                         │
│    score = 1 - (cosine_distance / 2)  # pgvector distance      │
│    Example: distance=0.18 → score=0.91                          │
│                                                                  │
│ 2. Entity Overlap:                                              │
│    query_entities = {"customer:gai_123"}                        │
│    memory_entities = extract_entity_ids(memory.entities)        │
│    score = len(intersection) / len(union)  # Jaccard            │
│    Example: {gai_123} ∩ {gai_123, order:1009} → 1/2 = 0.50     │
│                                                                  │
│ 3. Temporal Relevance:                                          │
│    IF temporal_filter:                                           │
│      days_diff = |memory.created_at - filter_midpoint|          │
│      score = exp(-days_diff / 30)  # Decay over time            │
│    ELSE:                                                         │
│      score = 1.0                                                │
│    Example: memory from Sept 15, filter Sept 1-30 → high       │
│                                                                  │
│ 4. Importance:                                                   │
│    score = memory.importance  # Stored in DB                    │
│    Example: 0.70                                                │
│                                                                  │
│ 5. Reinforcement:                                                │
│    score = min(memory.reinforcement_count / 10, 1.0)           │
│    Example: reinforced 3 times → 0.30                           │
│                                                                  │
│ Step 3b: Apply Strategy Weights                                 │
│                                                                  │
│ final_score = 0.25 * semantic_similarity                        │
│             + 0.40 * entity_overlap                             │
│             + 0.20 * temporal_relevance                         │
│             + 0.10 * importance                                 │
│             + 0.05 * reinforcement                              │
│                                                                  │
│ Example Calculation (memory_id=512):                            │
│   0.25 * 0.91 = 0.2275  (semantic)                              │
│   0.40 * 0.50 = 0.2000  (entity) ← Key match                    │
│   0.20 * 0.95 = 0.1900  (temporal)                              │
│   0.10 * 0.70 = 0.0700  (importance)                            │
│   0.05 * 0.30 = 0.0150  (reinforcement)                         │
│   ─────────────────────                                         │
│   TOTAL:        0.7025                                          │
│                                                                  │
│ Step 3c: Apply Boosts                                           │
│                                                                  │
│ IF memory is from memory_summaries:                             │
│   final_score *= 1.15  # 15% boost from heuristics             │
│                                                                  │
│ Step 3d: Apply Confidence Decay (Passive Computation)           │
│                                                                  │
│ For semantic memories only:                                     │
│   days_since_validation =                                       │
│     (now - memory.last_validated_at).days                       │
│   effective_confidence =                                        │
│     memory.confidence * exp(-days_since_validation * 0.01)      │
│   final_score *= effective_confidence                           │
│                                                                  │
│ Step 3e: Sort & Select Top Memories                             │
│                                                                  │
│ Sort all 85 candidates by final_score DESC                      │
│                                                                  │
│ Token Budget Allocation:                                        │
│   Total: 3000 tokens (from settings.max_context_tokens)        │
│   Reserved for domain facts: 40% = 1200 tokens                 │
│   Available for memories: 60% = 1800 tokens                    │
│                                                                  │
│ Select Memories:                                                 │
│   Start with top-scored memory                                  │
│   Estimate tokens (summary length * 0.25)                       │
│   Add to context if within budget                               │
│   Continue until budget exhausted or max 15 memories            │
│                                                                  │
│ Selected (top 12 fitting in 1800 tokens):                       │
│   1. memory_id=512, score=0.881, tokens=120 (episodic)         │
│   2. memory_id=145, score=0.856, tokens=80 (semantic)          │
│   3. memory_id=89,  score=0.843, tokens=200 (summary) ← boost  │
│   ...                                                            │
│   12. memory_id=423, score=0.612, tokens=90 (episodic)         │
│                                                                  │
│ Output:                                                          │
│   memories_retrieved: 12                                        │
│   total_tokens_used: 1750                                       │
│   retrieval_strategy: "factual_entity_focused"                 │
└─────────────────────────────────────────────────────────────────┘
```

### Subsystem 3: Memory Lifecycle

**Implementation**: ⏳ `src/domain/services/lifecycle_manager.py` (pending)

**Design Document**: `docs/design/LIFECYCLE_DESIGN.md`

```
MEMORY LIFECYCLE: State Transitions & Evolution

┌─────────────────────────────────────────────────────────────────┐
│ STATE MACHINE (4 States)                                        │
│                                                                  │
│                    ┌──────────┐                                 │
│           ┌────────│  ACTIVE  │────────┐                        │
│           │        └──────────┘        │                        │
│           │                             │                        │
│      Validation                    Decay/Conflict                │
│      (reinforces)                  (confidence < 0.3)            │
│           │                             │                        │
│           │                             ↓                        │
│           │                       ┌──────────┐                  │
│           └───────────────────────│  AGING   │                  │
│                                   └──────────┘                  │
│                                         │                        │
│                    ┌────────────────────┼────────────┐          │
│                    │                    │            │          │
│              New memory          User validates  User corrects  │
│              supersedes           (reinforces)   ("That's wrong")│
│                    │                    │            │          │
│                    ↓                    ↓            ↓          │
│              ┌───────────┐         ┌──────────┐ ┌──────────────┐│
│              │SUPERSEDED │         │  ACTIVE  │ │ INVALIDATED  ││
│              └───────────┘         └──────────┘ └──────────────┘│
│              (Historical            (Recovered)  (Explicit       │
│               record kept)                        rejection)     │
│                                                                  │
│ Passive Computation: States computed on-demand, NOT stored     │
│ Exception: SUPERSEDED and INVALIDATED are explicitly stored     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ CONFIDENCE EVOLUTION                                            │
│                                                                  │
│ Initial Extraction:                                             │
│   Base confidence depends on source:                            │
│   • Explicit statement:  0.70  ("Remember: X prefers Y")       │
│   • Inferred:            0.50  (LLM extraction from context)    │
│   • Consolidation:       0.75  (Cross-episodic pattern)         │
│   • User correction:     0.85  ("No, actually it's Z")         │
│                                                                  │
│ Reinforcement (Diminishing Returns):                            │
│   On each validation (memory used & confirmed):                 │
│   • 1st validation: confidence += 0.15                          │
│   • 2nd validation: confidence += 0.10                          │
│   • 3rd validation: confidence += 0.05                          │
│   • 4th+ validation: confidence += 0.02                         │
│   • Max confidence: 0.95 (epistemic humility - never 100%)     │
│                                                                  │
│ Decay (Passive - Computed on Retrieval):                        │
│   days_since_validation =                                       │
│     (now - memory.last_validated_at).days                       │
│   effective_confidence =                                        │
│     stored_confidence * exp(-days * DECAY_RATE_PER_DAY)        │
│     where DECAY_RATE_PER_DAY = 0.01  (from heuristics.py)      │
│                                                                  │
│   Example Timeline:                                             │
│     Day 0:   confidence = 0.70 (stored)                         │
│     Day 30:  effective  = 0.70 * exp(-30 * 0.01) = 0.52       │
│     Day 60:  effective  = 0.70 * exp(-60 * 0.01) = 0.38       │
│     Day 90:  effective  = 0.70 * exp(-90 * 0.01) = 0.28       │
│                          ↑ Below 0.30 threshold → AGING state   │
│                                                                  │
│ Confidence Breakdown (stored in confidence_factors JSONB):      │
│   {                                                              │
│     "base": 0.70,              // Initial extraction            │
│     "reinforcement": 0.15,     // From 2 validations (0.15+0.10)│
│     "recency": -0.12,          // Decay over 60 days            │
│     "source": 0.05,            // Consolidation boost           │
│     "effective": 0.78          // Final after decay             │
│   }                                                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STATE TRANSITIONS (Triggers & Actions)                          │
│                                                                  │
│ ACTIVE → AGING:                                                 │
│   Trigger: effective_confidence < 0.30                          │
│   Action: Mark for active recall in next relevant query         │
│   Query: Computed passively on retrieval (no DB update)         │
│   Response: Include validation prompt if memory used            │
│             "Is this still accurate: [fact]? (last validated 90d ago)"│
│                                                                  │
│ ACTIVE → SUPERSEDED:                                            │
│   Trigger: New memory conflicts with existing                   │
│           AND (confidence_gap > 0.30 OR age_gap > 60 days)     │
│   Action:                                                        │
│     1. Set old memory status = 'superseded'                     │
│     2. Set old memory superseded_by_memory_id = new_memory_id   │
│     3. Create memory_conflict record                            │
│     4. Insert new memory with higher confidence                 │
│   Example:                                                       │
│     Old: "Gai prefers NET15" (confidence: 0.72, 120 days old)  │
│     New: "Gai prefers NET30" (confidence: 0.85, just learned)  │
│     → Old superseded, new becomes ACTIVE                        │
│                                                                  │
│ ACTIVE → INVALIDATED:                                           │
│   Trigger: User explicit correction                             │
│           "No, that's wrong" or "Actually, it's..."             │
│   Action:                                                        │
│     1. Set status = 'invalidated'                               │
│     2. Create memory_conflict record (type: user_correction)    │
│     3. Create new memory with corrected value (confidence: 0.85)│
│   DB Update:                                                     │
│     UPDATE app.semantic_memories                                │
│     SET status = 'invalidated',                                 │
│         updated_at = NOW()                                      │
│     WHERE memory_id = 145                                       │
│                                                                  │
│ AGING → ACTIVE:                                                 │
│   Trigger: User validates during active recall                  │
│           "Yes, that's still correct"                           │
│   Action:                                                        │
│     1. Apply reinforcement boost                                │
│     2. Update last_validated_at = NOW()                         │
│     3. Effective confidence increases (decay resets)            │
│   DB Update:                                                     │
│     UPDATE app.semantic_memories                                │
│     SET reinforcement_count = reinforcement_count + 1,          │
│         confidence = confidence + [boost],                      │
│         last_validated_at = NOW()                               │
│     WHERE memory_id = 145                                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ CONSOLIDATION (Episodic → Semantic → Summary)                  │
│                                                                  │
│ Trigger Conditions (from LIFECYCLE_DESIGN.md):                  │
│   • Min 10 episodic memories in window                          │
│   • Min 3 distinct sessions                                     │
│   • Default window: Last 5 sessions                             │
│                                                                  │
│ Example Scenario:                                                │
│   User has had 5 conversations about customer "Gai Media"       │
│   12 episodic memories created across these sessions            │
│   → Trigger consolidation                                       │
│                                                                  │
│ Consolidation Process:                                           │
│                                                                  │
│ Step 1: Identify Pattern Cluster                                │
│   Query:                                                         │
│     SELECT * FROM app.episodic_memories                         │
│     WHERE user_id = 'user_123'                                  │
│       AND entities @> '[{"id":"customer:gai_123"}]'             │
│       AND session_id IN (last_5_sessions)                       │
│     ORDER BY created_at DESC                                    │
│     LIMIT 20                                                     │
│                                                                  │
│ Step 2: LLM-Based Pattern Extraction                            │
│   Prompt to LLM:                                                │
│     "Analyze these 12 conversation memories and extract:        │
│      1. Recurring patterns about this customer                  │
│      2. Key preferences or requirements                         │
│      3. Relationship insights                                   │
│      Output as structured facts."                               │
│                                                                  │
│   LLM Output:                                                    │
│     {                                                            │
│       "patterns": [                                             │
│         {                                                        │
│           "type": "preference",                                 │
│           "subject": "customer:gai_123",                        │
│           "predicate": "delivery_timing",                       │
│           "object": "Friday afternoons",                        │
│           "evidence_count": 5,                                  │
│           "confidence": 0.85                                    │
│         },                                                       │
│         {                                                        │
│           "type": "observation",                                │
│           "subject": "customer:gai_123",                        │
│           "predicate": "payment_behavior",                      │
│           "object": "typically 2-3 days late on NET30",        │
│           "evidence_count": 3,                                  │
│           "confidence": 0.70                                    │
│         }                                                        │
│       ]                                                          │
│     }                                                            │
│                                                                  │
│ Step 3: Create/Update Semantic Memories                         │
│   For each pattern:                                             │
│     Check if similar semantic memory exists                     │
│     IF exists AND confidence_gap < 0.30:                        │
│       Reinforce existing (increment reinforcement_count)        │
│     ELSE:                                                        │
│       Create new semantic memory:                               │
│         INSERT INTO app.semantic_memories (                     │
│           user_id, subject_entity_id, predicate,                │
│           object_value, confidence,                             │
│           source_type, source_memory_id,                        │
│           status, embedding                                     │
│         ) VALUES (                                               │
│           'user_123', 'customer:gai_123',                       │
│           'delivery_timing',                                    │
│           '{"type": "time_preference", "value": "Friday pm"}', │
│           0.85 + 0.05,  -- Base + consolidation boost          │
│           'consolidation', [episodic_ids],                      │
│           'active', [embedding]                                 │
│         )                                                        │
│                                                                  │
│ Step 4: Create Memory Summary                                   │
│   INSERT INTO app.memory_summaries (                            │
│     user_id, scope_type, scope_identifier,                      │
│     summary_text, key_facts, source_data,                       │
│     confidence, embedding                                       │
│   ) VALUES (                                                     │
│     'user_123', 'entity', 'customer:gai_123',                  │
│     'Gai Media: Prefers Friday deliveries, NET30 payment...',  │
│     '[{pattern_1}, {pattern_2}]',                               │
│     '{"episodic_ids": [101,105,...], "session_ids": [...]}',   │
│     0.80, [embedding]                                           │
│   )                                                              │
│                                                                  │
│ Consolidation Benefits:                                          │
│   • Compresses 12 episodic memories → 2 semantic facts + 1 summary│
│   • Faster retrieval (fewer candidates to score)                │
│   • Higher confidence (patterns across multiple sessions)       │
│   • Graceful forgetting (episodic details fade, patterns remain)│
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack & Configuration

### Implementation Status

```
✅ FULLY CONFIGURED:

Database:
  • PostgreSQL 15+ with pgvector extension
  • Connection: Async via asyncpg
  • Pool size: 10 (configurable in settings.py)
  • Location: src/infrastructure/database/

ORM:
  • SQLAlchemy 2.0 (async)
  • All 10 tables defined with proper:
    - Indexes (standard + vector IVFFlat)
    - Foreign keys
    - Check constraints
    - JSONB columns
  • Location: src/infrastructure/database/models.py

API Framework:
  • FastAPI (async)
  • Lifespan events for DB init/cleanup
  • CORS middleware configured
  • Basic routes (/, /health)
  • Location: src/api/main.py

Configuration:
  • Pydantic BaseSettings
  • Environment variable loading (.env)
  • All Phase 1 parameters defined:
    - Database URLs (memory DB + domain DB)
    - OpenAI API key & models
    - API host/port settings
    - Performance limits (pool size, context tokens)
    - Feature flags (embedding async, conflict detection)
  • Location: src/config/settings.py

Heuristics:
  • All 43 parameters from HEURISTICS_CALIBRATION.md
  • Organized by subsystem:
    - Lifecycle (decay, reinforcement, confidence limits)
    - Entity resolution (fuzzy thresholds, disambiguation)
    - Retrieval (strategy weights, candidate limits)
    - Conflict detection (confidence gaps, age thresholds)
    - Consolidation (triggers, thresholds)
    - Extraction (base confidence by source type)
    - Context management (token budget allocation)
  • Helper functions for weight lookup
  • Location: src/config/heuristics.py

Migration Framework:
  • Alembic configured
  • Initial migration ready to create all 10 tables
  • Location: alembic.ini, src/infrastructure/database/migrations/

Development Infrastructure:
  • Docker Compose (PostgreSQL + Redis)
  • Makefile with common commands
  • pytest configured
  • mypy, ruff configs in pyproject.toml
  • Location: docker-compose.yml, Makefile

⏳ PENDING IMPLEMENTATION (Phase 1):

Domain Services:
  • EntityResolver (5-stage algorithm)
  • MemoryRetriever (multi-signal scoring)
  • LifecycleManager (state transitions, decay)
  • MemoryExtractor (chat → episodic → semantic)
  • ConflictDetector (memory vs memory/DB)
  • Location: src/domain/services/ (empty)

Infrastructure Adapters:
  • PostgresEntityRepository (CRUD + fuzzy search)
  • PostgresMemoryRepository (CRUD + vector search)
  • OpenAIEmbeddingService (text → vector(1536))
  • DomainDBConnector (read-only external DB queries)
  • Location: src/infrastructure/ (scaffolded, no implementations)

API Routes:
  • POST /api/v1/chat (primary endpoint)
  • Memory CRUD (/memories, /memories/{id})
  • Entity resolution (/entities/resolve)
  • Conflict management (/conflicts)
  • Location: src/api/routes/ (empty)

Pydantic Models:
  • Request models (ChatRequest, EntityResolutionRequest)
  • Response models (ChatResponse, MemoryResponse)
  • Shared models (Entity, Memory, Citation)
  • Location: src/api/models/ (empty)

Utilities:
  • text_similarity.py (Levenshtein, fuzzy matching)
  • vector_ops.py (cosine similarity, vector utils)
  • temporal.py (date parsing, decay functions)
  • Location: src/utils/ (empty)

Tests:
  • Unit tests (domain logic with mocks)
  • Integration tests (database operations)
  • E2E tests (full API flows)
  • Location: tests/ (scaffolded, no tests written)
```

### Configuration Reference

**Database** (`src/config/settings.py`):
```python
database_url: postgresql+asyncpg://memoryuser:memorypass@localhost:5432/memorydb
db_pool_size: 10
db_max_overflow: 20
db_echo: False  # SQL logging (dev only)

domain_db_url: postgresql+asyncpg://readonly:password@localhost:5432/domain
domain_db_enabled: True
```

**OpenAI** (`src/config/settings.py`):
```python
openai_api_key: [from environment]
openai_embedding_model: text-embedding-3-small
openai_embedding_dimensions: 1536
openai_llm_model: gpt-4-turbo-preview
```

**Performance Limits** (`src/config/settings.py`):
```python
max_conversation_history: 50
max_retrieval_candidates: 50
max_selected_memories: 15
max_context_tokens: 3000
```

**Feature Flags** (`src/config/settings.py`):
```python
enable_embedding_async: True    # Generate embeddings async (don't block)
enable_conflict_detection: True  # Log all memory conflicts
enable_procedural_memory: False  # Phase 2 feature
```

**Heuristics** (`src/config/heuristics.py`):
```python
# Lifecycle
DECAY_RATE_PER_DAY = 0.01
REINFORCEMENT_BOOSTS = [0.15, 0.10, 0.05, 0.02]
MAX_CONFIDENCE = 0.95  # Epistemic humility
MIN_CONFIDENCE_FOR_USE = 0.3

# Entity Resolution
CONFIDENCE_EXACT_MATCH = 1.0
CONFIDENCE_USER_ALIAS = 0.95
FUZZY_MATCH_THRESHOLD = 0.70
FUZZY_MATCH_AUTO_RESOLVE = 0.85
DISAMBIGUATION_MIN_CONFIDENCE_GAP = 0.15

# Retrieval
RETRIEVAL_STRATEGY_WEIGHTS = {
  "factual_entity_focused": {...},
  "procedural": {...},
  "exploratory": {...},
  "temporal": {...}
}
MAX_SEMANTIC_CANDIDATES = 50
MAX_ENTITY_CANDIDATES = 30

# Conflict Detection
CONFIDENCE_GAP_THRESHOLD = 0.30
AGE_THRESHOLD_DAYS = 60

# Consolidation
CONSOLIDATION_MIN_EPISODIC = 10
CONSOLIDATION_MIN_SESSIONS = 3

# Context Budget
CONTEXT_DB_FACTS = 0.40  # 40% for domain DB
CONTEXT_SUMMARIES = 0.20
CONTEXT_SEMANTIC = 0.20
CONTEXT_EPISODIC = 0.15
CONTEXT_PROCEDURAL = 0.05
```

---

## Next Steps: Phase 1 Implementation

**Current Status**: Week 0 complete - Foundation ready

**Recommended Implementation Order** (10-12 weeks):

### Week 1-2: Database Foundation
- [ ] Create initial Alembic migration (all 10 tables)
- [ ] Apply migration to dev database
- [ ] Seed system_config with default heuristics
- [ ] Test database connectivity and session management
- [ ] Write first integration test (insert/retrieve chat_event)

### Week 3-4: Entity Resolution
- [ ] Implement domain entities (CanonicalEntity, EntityAlias)
- [ ] Implement EntityRepositoryPort (interface)
- [ ] Implement PostgresEntityRepository
- [ ] Implement EntityResolver service (5-stage algorithm)
- [ ] Write unit tests (mock repository)
- [ ] Write integration tests (real database)
- [ ] Add pg_trgm extension for fuzzy matching

### Week 5-6: Memory Extraction & Storage
- [ ] Implement domain entities (EpisodicMemory, SemanticMemory)
- [ ] Implement MemoryRepositoryPort (interface)
- [ ] Implement PostgresMemoryRepository
- [ ] Implement MemoryExtractor service
- [ ] Implement LifecycleManager service
- [ ] Write unit + integration tests
- [ ] Implement OpenAIEmbeddingService

### Week 7-8: Memory Retrieval
- [ ] Implement MemoryRetriever service
- [ ] Implement multi-signal scoring
- [ ] Test pgvector semantic search performance
- [ ] Optimize IVFFlat index parameters
- [ ] Write unit + integration tests
- [ ] Benchmark retrieval latency (target: <100ms P95)

### Week 9: API Layer
- [ ] Implement POST /chat endpoint
- [ ] Implement Pydantic request/response models
- [ ] Implement memory CRUD endpoints
- [ ] Implement entity resolution endpoint
- [ ] Add authentication (JWT)
- [ ] Write E2E tests

### Week 10-11: Integration & Testing
- [ ] End-to-end testing of full chat flow
- [ ] Performance testing & optimization
- [ ] Achieve 80%+ test coverage
- [ ] Fix bugs and edge cases
- [ ] Structured logging throughout

### Week 12: Deployment & Documentation
- [ ] Dockerize application
- [ ] Deploy to staging environment
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Performance tuning based on real usage
- [ ] Begin Phase 2 data collection

**Key Milestones**:
- ✅ Week 0: Foundation complete
- Week 4: Entity resolution working
- Week 6: Memory creation working
- Week 8: Memory retrieval working
- Week 9: Chat API functional
- Week 12: Phase 1 MVP deployed

**Success Criteria**:
- All 10 core database tables in use
- POST /chat endpoint fully functional
- 80%+ test coverage (all checks passing)
- P95 latency <300ms for chat endpoint
- No critical security vulnerabilities
- Ready for Phase 2 heuristic calibration

---

## Design Decisions Summary

**1. Passive Computation Philosophy**
- Confidence decay computed on-demand (not stored)
- Memory states computed during retrieval (not background jobs)
- Benefit: Simpler architecture, always current values
- Trade-off: Slightly higher retrieval latency (negligible)

**2. JSONB for Context-Specific Data**
- Used when data is always loaded with parent
- Examples: entity mentions, confidence factors, metadata
- Benefit: Avoids complex joins, flexible schema
- When NOT to use: Data queried independently (use separate table)

**3. pgvector for Semantic Search**
- IVFFlat indexes for approximate nearest neighbor
- Target: <50ms P95 for 50-candidate search
- Alternative (Phase 3): Pinecone if scaling beyond 1M vectors

**4. Hexagonal Architecture**
- Domain layer never imports infrastructure
- Repositories use port/adapter pattern
- Benefit: Testable without database, swappable adapters

**5. Explicit Provenance**
- Every memory links to source (episodic → chat events)
- Enables "explain your reasoning" capability
- Epistemic transparency for user trust

**6. Lazy Entity Creation**
- Entities created on first mention (not pre-loaded)
- Query domain DB when entity not found
- Benefit: No sync overhead, always fresh data

**7. Multi-Signal Retrieval**
- Combines 5 signals with strategy-based weights
- Strategy selection based on query intent classification
- More sophisticated than pure semantic search

**8. Epistemic Humility**
- Max confidence capped at 0.95 (never 100%)
- All conflicts explicitly logged in memory_conflicts table
- System admits uncertainty when appropriate

---

## Performance Targets (Phase 1)

**Latency Goals** (P95):
- Semantic search (pgvector): <50ms
- Entity resolution: <30ms
- Memory retrieval (full): <100ms
- Chat endpoint (end-to-end): <300ms

**Throughput Goals**:
- Concurrent users: 100+
- Requests/second: 50+

**Storage Goals**:
- 100K+ memories per user
- 1M+ total vectors (pgvector performant up to 10M)

**Quality Goals**:
- Test coverage: 80%+ (90%+ for domain layer)
- Type coverage: 100% (mypy strict)
- No critical security vulnerabilities

---

## Key Documents Reference

**Architecture & Design**:
- `/Users/edwardzhong/Projects/adenAssessment2/ARCHITECTURE.md` - Code structure, patterns
- `/Users/edwardzhong/Projects/adenAssessment2/docs/design/DESIGN.md` - Database schema
- `/Users/edwardzhong/Projects/adenAssessment2/docs/design/ENTITY_RESOLUTION_DESIGN_V2.md` - 5-stage algorithm
- `/Users/edwardzhong/Projects/adenAssessment2/docs/design/RETRIEVAL_DESIGN.md` - Multi-signal scoring
- `/Users/edwardzhong/Projects/adenAssessment2/docs/design/LIFECYCLE_DESIGN.md` - Memory states, decay

**Configuration**:
- `/Users/edwardzhong/Projects/adenAssessment2/src/config/settings.py` - All settings
- `/Users/edwardzhong/Projects/adenAssessment2/src/config/heuristics.py` - 43 parameters

**Implementation**:
- `/Users/edwardzhong/Projects/adenAssessment2/src/infrastructure/database/models.py` - SQLAlchemy models (complete)
- `/Users/edwardzhong/Projects/adenAssessment2/src/api/main.py` - FastAPI app (basic)

**Development**:
- `/Users/edwardzhong/Projects/adenAssessment2/CLAUDE.md` - Developer guide
- `/Users/edwardzhong/Projects/adenAssessment2/DEVELOPMENT_GUIDE.md` - Setup, workflows
- `/Users/edwardzhong/Projects/adenAssessment2/Makefile` - Common commands

---

**End of System Flow Diagram**

*This document reflects the actual codebase state as of Week 0. All database models are implemented and ready. Domain logic and API routes are next in Phase 1 implementation (estimated 10-12 weeks).*
