# Phase 1 Completion Plan - Comprehensive Roadmap

**Created**: 2025-10-15
**Objective**: Complete Phase 1 to deliver a production-ready system that is a **superset** of the project description requirements while fully embodying the vision

---

## Executive Summary

**Current Status**: 75% complete (Phase 1A-C done, Phase 1D testing complete, infrastructure gaps remain)

**Remaining Work**: 25% (~40-50 hours)
- 🔧 **Infrastructure**: 20% (domain data, repositories, API layer)
- 🧪 **E2E Testing**: 3% (acceptance tests, scenarios)
- 📚 **Documentation**: 2% (write-up, API docs)

**Target Completion**: 1-2 weeks with focused effort

---

## Vision Alignment Check

### Project Description Requirements vs Current Implementation

| Project Requirement | Vision Principle | Current Status | Gap |
|---------------------|------------------|----------------|-----|
| `/chat` endpoint | Perfect recall, Dual truth | ❌ Not implemented | API layer missing |
| `/memory` endpoint | Explainability, Provenance | ❌ Not implemented | API layer missing |
| `/consolidate` endpoint | Graceful forgetting | ⚠️ Service exists, no API | API layer missing |
| `/entities` endpoint | Identity, Canonical representation | ❌ Not implemented | API layer missing |
| Domain DB with seed data | Correspondence truth, Grounding | ⚠️ Schema exists, no data | Seed script missing |
| Memory growth across sessions | Learning as transformation | ✅ Implemented | Complete |
| Entity linking & disambiguation | Problem of reference | ✅ Implemented | Complete |
| Hybrid retrieval (vector + SQL) | Multi-dimensional relevance | ✅ Implemented | Complete |
| Consolidation (episodic→semantic→summary) | Compression, Abstraction | ✅ Implemented | Complete |
| Confidence tracking & decay | Epistemic humility | ✅ Implemented | Complete |
| Provenance & explainability | Transparency as trust | ✅ Implemented | API exposure needed |
| 18 user scenarios | North Star: Experienced colleague | ❌ Not tested | E2E tests missing |

**Vision Embodiment**: ✅ 90% (core principles implemented in domain layer)
**Project Requirements**: ⚠️ 60% (missing API layer and demo data)

---

## Critical Gaps Analysis

### Gap 1: API Layer (HIGH PRIORITY)

**Current State**:
- ✅ Domain services fully implemented
- ✅ Repository pattern with ports
- ❌ NO FastAPI routes for core endpoints
- ❌ NO Pydantic request/response models for chat

**What's Missing**:
```
src/api/routes/
├── chat.py              ❌ POST /chat (CRITICAL)
├── memory.py            ❌ GET /memory, GET /entities
├── consolidation.py     ❌ POST /consolidate, GET /summaries
└── explain.py           ❌ GET /explain (optional)

src/api/models/
├── chat.py              ❌ ChatRequest, ChatResponse
├── memory.py            ❌ MemoryResponse, EntityResponse
└── consolidation.py     ❌ ConsolidationRequest, SummaryResponse
```

**Impact**: Without API layer, the system cannot be used or tested end-to-end.

**Estimated Work**: 16-20 hours

---

### Gap 2: Domain Database Population (HIGH PRIORITY)

**Current State**:
- ✅ Domain schema created (6 tables: customers, sales_orders, work_orders, invoices, payments, tasks)
- ✅ SQLAlchemy ORM models (domain_models.py)
- ❌ NO seed data script
- ❌ Empty tables (cannot demo)

**What's Missing**:
```
scripts/
└── seed_data.py         ❌ Seed domain database with demo entities

Expected Demo Data:
- Customers: "Gai Media" (Entertainment), "TC Boiler" (Industrial), "Kai Media"
- Sales Orders: SO-1001, SO-2002 (various statuses)
- Work Orders: Linked to SOs with technicians
- Invoices: INV-1009 ($1200, due 2025-09-30, open), INV-2201
- Payments: Partial payments for testing
- Tasks: Support tasks (SLA investigation, etc.)
```

**Impact**: Cannot demonstrate core use cases (grounding to DB, entity linking, multi-hop reasoning).

**Estimated Work**: 4-6 hours

---

### Gap 3: Chat Service Orchestration (HIGH PRIORITY)

**Current State**:
- ✅ All individual services implemented
- ✅ Entity resolution, semantic extraction, retrieval, consolidation
- ❌ NO chat orchestration service that brings everything together
- ❌ NO response formatting with provenance

**What's Missing**:
```python
# src/domain/services/chat_service.py (NEW)
class ChatService:
    """Orchestrates chat flow: ingest → extract → retrieve → respond."""

    async def process_message(
        self,
        user_id: str,
        session_id: UUID,
        message: str
    ) -> ChatResponse:
        """
        Full chat pipeline:
        1. Store chat event
        2. Extract entities (entity resolution)
        3. Extract semantic facts (semantic extraction)
        4. Retrieve relevant memories (multi-signal retrieval)
        5. Query domain database for entity facts
        6. Augment LLM context with memories + DB facts
        7. Generate response
        8. Return with provenance (used_memories, used_domain_facts)
        """
        pass
```

**Impact**: Individual pieces work in isolation but cannot handle full conversation flow.

**Estimated Work**: 8-12 hours

---

### Gap 4: E2E Acceptance Tests (MEDIUM PRIORITY)

**Current State**:
- ✅ Unit tests (270 passing)
- ✅ Integration tests (Phase 1D complete)
- ✅ Property-based tests (consolidation, procedural)
- ❌ NO E2E scenario tests (all marked TODO)
- ❌ NO acceptance script

**What's Missing**:
```
tests/e2e/
├── test_scenarios.py    ⚠️ 18 scenarios defined but all marked TODO
└── conftest.py          ⚠️ seed_domain_db() placeholder

scripts/
└── acceptance.sh        ❌ Executable validation script
```

**Required Scenarios** (from project description):
1. Overdue invoice follow-up with preference recall
2. Reschedule work order based on technician availability
3. Ambiguous entity disambiguation
4. NET terms learning from conversation
5. Partial payments and balance calculation
6. SLA breach detection
7. Conflicting memories consolidation
8. Multilingual/alias handling
9. Cold-start grounding to DB facts
10. Active recall to validate stale facts
11. Cross-object reasoning (SO → WO → Invoice)
12. Fuzzy match with alias learning
13. PII guardrail memory
14. Session window consolidation
15. Audit trail / explainability
16. Reminder creation from intent
17. DB vs memory disagreement
18. Task completion via conversation

**Impact**: Cannot validate system works end-to-end or demonstrate core value propositions.

**Estimated Work**: 12-16 hours

---

### Gap 5: Repository Completeness (MEDIUM PRIORITY)

**Current State**:
- ✅ Most repositories implemented
- ⚠️ SummaryRepository missing create() method
- ❌ ProceduralMemoryRepository not fully implemented

**What's Missing**:
```python
# src/infrastructure/database/repositories/summary_repository.py
class SummaryRepository(ISummaryRepository):
    async def create(self, summary: MemorySummary) -> MemorySummary:
        """Create new summary with embedding."""
        # TODO: Implement

# src/infrastructure/database/repositories/procedural_repository.py (NEW)
class ProceduralMemoryRepository(IProceduralMemoryRepository):
    """Full CRUD + similarity search for procedural memories."""
    async def create(self, memory: ProceduralMemory) -> ProceduralMemory: pass
    async def find_by_id(self, memory_id: int) -> Optional[ProceduralMemory]: pass
    async def find_similar(self, query_embedding, limit, min_confidence) -> list: pass
    async def find_by_trigger_features(...) -> list: pass
    async def update(self, memory: ProceduralMemory) -> ProceduralMemory: pass
```

**Impact**: Services cannot persist consolidation summaries or procedural patterns.

**Estimated Work**: 6-8 hours

---

### Gap 6: Documentation & Deliverables (LOW PRIORITY)

**Current State**:
- ✅ Extensive design docs (VISION.md, DESIGN.md, etc.)
- ✅ Architecture docs
- ⚠️ No API documentation (OpenAPI/Swagger)
- ❌ No 1-page write-up (project description requirement)
- ⚠️ README incomplete for end-user setup

**What's Missing**:
```
docs/
├── API_DOCUMENTATION.md           ❌ OpenAPI spec or endpoint reference
├── WRITEUP.md                     ❌ 1-page summary (memory lifecycle, linking, prompts)
└── DEPLOYMENT_GUIDE.md            ❌ Production deployment instructions

README.md                          ⚠️ Needs: Quick start, .env.example, sample requests
```

**Impact**: Harder for evaluators/users to understand and use the system.

**Estimated Work**: 4-6 hours

---

## Detailed Implementation Plan

### Week 1: Core Infrastructure (Days 1-5)

#### Day 1: Domain Database Seed Data (CRITICAL PATH)

**Deliverable**: `scripts/seed_data.py` with comprehensive demo data

**Tasks**:
1. Create seed script using SQLAlchemy domain models
2. Populate demo data matching project description scenarios:
   - **Customers** (4-5):
     - Gai Media (Entertainment) - for invoice scenarios
     - TC Boiler (Industrial) - for payment terms scenarios
     - Kai Media (similar name for disambiguation)
     - Kai Media Europe (disambiguation test)
   - **Sales Orders** (5-6):
     - SO-1001 (Gai Media, "Album Fulfillment", in_fulfillment)
     - SO-2002 (TC Boiler, "On-site repair", fulfilled)
     - SO-123 (various statuses for testing)
   - **Work Orders** (5-6):
     - Linked to SOs with technicians (Alex, Sarah)
     - Various statuses (queued, in_progress, done)
     - Scheduled dates
   - **Invoices** (4-5):
     - INV-1009 ($1200, due 2025-09-30, open) - for Gai Media
     - INV-2201 (TC Boiler, NET15 testing)
     - Some paid, some open
   - **Payments** (2-3):
     - Partial payments for balance calculation tests
   - **Tasks** (3-4):
     - SLA investigation tasks
     - Support items
3. Add idempotency (check if data exists before inserting)
4. Test: `make seed` populates data successfully

**Acceptance Criteria**:
- ✅ `make seed` runs without errors
- ✅ All 6 domain tables have data
- ✅ Foreign keys correctly linked
- ✅ Can query: "SELECT * FROM domain.customers" returns 4+ rows

**Estimated**: 4-6 hours

---

#### Day 2: Chat Service Orchestration (CRITICAL PATH)

**Deliverable**: `src/domain/services/chat_service.py` - Full conversation pipeline

**Tasks**:
1. Create ChatService with dependencies injected:
   ```python
   def __init__(
       self,
       chat_repo: IChatRepository,
       entity_resolver: EntityResolutionService,
       semantic_extractor: SemanticExtractionService,
       retriever: MemoryRetriever,
       domain_connector: DomainDatabaseConnector,
       llm_service: ILLMService,
   ):
   ```

2. Implement `process_message()`:
   - Store chat event (user message)
   - Extract entities from message (entity resolution)
   - Resolve entities to canonical forms
   - Extract semantic triples (if statement/preference)
   - Retrieve relevant memories (multi-signal retrieval)
   - Query domain DB for entity-related facts (multi-hop)
   - Build augmented context (DB facts + memories)
   - Generate LLM response
   - Store assistant response as chat event
   - Return ChatResponse with provenance

3. Implement `_build_augmented_context()`:
   - Format DB facts: "Customer[Gai Media] industry=Entertainment; open_invoices=1; last_invoice: INV-1009..."
   - Format memories: "[semantic 0.78] Gai Media prefers NET30 and Friday deliveries"
   - Return structured prompt sections

4. Implement `_query_domain_facts()`:
   - Based on resolved entities, query relevant domain tables
   - Multi-hop: customer → orders → work_orders → invoices → payments
   - Return structured facts with IDs for traceability

**Acceptance Criteria**:
- ✅ Can process message end-to-end
- ✅ Returns response with used_memories and used_domain_facts
- ✅ Stores all events in chat_events table
- ✅ Extracts entities and semantic facts automatically

**Estimated**: 8-10 hours

---

#### Day 3: Repository Completions (CRITICAL PATH)

**Deliverable**: Complete SummaryRepository and ProceduralMemoryRepository

**Tasks**:

1. **SummaryRepository.create()**:
   ```python
   async def create(self, summary: MemorySummary) -> MemorySummary:
       """Create summary with embedding generation."""
       # Generate embedding if not present
       if summary.embedding is None:
           summary.embedding = await self._embedding_service.generate_embedding(
               summary.summary_text
           )

       # Insert into memory_summaries table
       # Return with summary_id populated
   ```

2. **ProceduralMemoryRepository** (full implementation):
   - `create()`: Insert with embedding
   - `find_by_id()`: Retrieve single pattern
   - `find_similar()`: Vector similarity search
   - `find_by_trigger_features()`: Filter by intent/entities/topics
   - `update()`: Update observed_count, confidence, updated_at
   - All methods return ProceduralMemory value objects

3. Add to dependency injection container

**Acceptance Criteria**:
- ✅ ConsolidationService can create summaries
- ✅ ProceduralMemoryService can persist patterns
- ✅ Integration tests pass for both repositories

**Estimated**: 6-8 hours

---

#### Day 4-5: API Layer (CRITICAL PATH)

**Deliverable**: Complete FastAPI routes and Pydantic models

**Tasks**:

1. **Create Pydantic Models** (`src/api/models/`):
   ```python
   # chat.py
   class ChatRequest(BaseModel):
       user_id: str
       session_id: Optional[UUID] = None
       message: str

   class UsedMemory(BaseModel):
       memory_id: int
       type: str  # episodic, semantic, summary
       content: str
       similarity_score: float

   class UsedDomainFact(BaseModel):
       table: str
       record_id: str
       fields: dict

   class ChatResponse(BaseModel):
       reply: str
       session_id: UUID
       used_memories: list[UsedMemory]
       used_domain_facts: list[UsedDomainFact]

   # memory.py
   class MemoryInspectionResponse(BaseModel):
       memories: list[dict]
       summaries: list[dict]
       total_count: int

   class EntityResponse(BaseModel):
       entities: list[dict]

   # consolidation.py
   class ConsolidationRequest(BaseModel):
       user_id: str
       scope_type: str = "session_window"  # entity, topic, session_window
       scope_identifier: Optional[str] = None

   class SummaryResponse(BaseModel):
       summary_id: int
       summary_text: str
       key_facts: dict
       confidence: float
       created_at: datetime
   ```

2. **Create Route Handlers** (`src/api/routes/`):

   **chat.py**:
   ```python
   @router.post("/chat", response_model=ChatResponse)
   async def chat(
       request: ChatRequest,
       chat_service: ChatService = Depends(get_chat_service)
   ):
       """Main chat endpoint - orchestrates full conversation flow."""
       # Generate session_id if not provided
       session_id = request.session_id or uuid4()

       # Process message through chat service
       result = await chat_service.process_message(
           user_id=request.user_id,
           session_id=session_id,
           message=request.message
       )

       # Format response
       return ChatResponse(
           reply=result.reply,
           session_id=session_id,
           used_memories=[...],
           used_domain_facts=[...]
       )
   ```

   **memory.py**:
   ```python
   @router.get("/memory", response_model=MemoryInspectionResponse)
   async def get_memories(
       user_id: str,
       k: int = 50,
       episodic_repo: IEpisodicMemoryRepository = Depends(...)
   ):
       """Retrieve top-k memories for inspection."""

   @router.get("/entities", response_model=EntityResponse)
   async def get_entities(
       session_id: UUID,
       entity_repo: IEntityRepository = Depends(...)
   ):
       """List detected entities for a session."""
   ```

   **consolidation.py**:
   ```python
   @router.post("/consolidate", response_model=SummaryResponse)
   async def consolidate(
       request: ConsolidationRequest,
       service: ConsolidationService = Depends(...)
   ):
       """Trigger consolidation for user."""

   @router.get("/summaries/{scope_type}/{scope_identifier}")
   async def get_summary(...):
       """Retrieve existing summary."""
   ```

   **explain.py** (optional but valuable):
   ```python
   @router.get("/explain")
   async def explain_response(
       session_id: UUID,
       message_id: int
   ):
       """Return provenance for a specific response."""
   ```

3. **Register routes in main.py**:
   ```python
   from src.api.routes import chat, memory, consolidation, explain

   app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
   app.include_router(memory.router, prefix="/api/v1", tags=["memory"])
   app.include_router(consolidation.router, prefix="/api/v1", tags=["consolidation"])
   app.include_router(explain.router, prefix="/api/v1", tags=["explainability"])
   ```

4. **Dependency injection setup**:
   - Create `src/api/dependencies.py`
   - Wire all services with proper dependency injection
   - Use FastAPI Depends() for clean injection

**Acceptance Criteria**:
- ✅ All 4 core endpoints functional
- ✅ POST /chat returns ChatResponse with provenance
- ✅ GET /memory returns user memories
- ✅ POST /consolidate creates summaries
- ✅ GET /entities returns entity links
- ✅ OpenAPI docs auto-generated at /docs

**Estimated**: 10-12 hours

---

### Week 2: Testing & Documentation (Days 6-10)

#### Day 6-7: E2E Acceptance Tests (HIGH PRIORITY)

**Deliverable**: Executable E2E scenarios and acceptance script

**Tasks**:

1. **Implement seed_domain_db() in test fixtures**:
   ```python
   # tests/e2e/conftest.py
   async def seed_domain_db(data: dict):
       """Seed domain database with test-specific data."""
       async with get_db_session() as session:
           # Use domain models to create records
           customer = DomainCustomer(
               customer_id=data["customer_id"],
               name=data["name"],
               industry=data["industry"]
           )
           session.add(customer)
           # ... more entities
           await session.commit()
   ```

2. **Implement Priority Scenarios** (focus on top 10):

   **Scenario 1: Overdue invoice with preference recall**
   ```python
   async def test_scenario_01_overdue_invoice_with_preference_recall(api_client, seed_db):
       # Seed: Gai Media, INV-1009 (open, overdue)
       # Seed memory: "prefers Friday deliveries"

       response = await api_client.post("/api/v1/chat", json={
           "user_id": "demo_user",
           "message": "Draft email for Gai Media about unpaid invoice mentioning delivery preference"
       })

       assert response.status_code == 200
       data = response.json()

       # Should mention invoice details
       assert "INV-1009" in data["reply"]
       assert "1200" in data["reply"] or "$1,200" in data["reply"]

       # Should recall preference
       assert "Friday" in data["reply"]

       # Should track provenance
       assert len(data["used_domain_facts"]) > 0
       assert len(data["used_memories"]) > 0

       # Check memory was created
       memories_response = await api_client.get(
           "/api/v1/memory",
           params={"user_id": "demo_user"}
       )
       assert "invoice reminder" in memories_response.json()["memories"]
   ```

   **Scenario 3: Ambiguous entity disambiguation**
   ```python
   async def test_scenario_02_ambiguous_entity_disambiguation(api_client, seed_db):
       # Seed: "Kai Media" and "Kai Media Europe"

       response = await api_client.post("/api/v1/chat", json={
           "user_id": "demo_user",
           "message": "What's Kai's latest invoice?"
       })

       # If ambiguous, should ask for clarification
       # OR if one has higher confidence, should choose and cite
       data = response.json()

       # Check entity resolution was attempted
       assert len(data["used_domain_facts"]) > 0
   ```

   **Scenario 9: Cold-start grounding**
   ```python
   async def test_scenario_09_cold_start_grounding_to_db(api_client, seed_db):
       # No prior memories

       response = await api_client.post("/api/v1/chat", json={
           "user_id": "new_user",
           "session_id": str(uuid4()),
           "message": "What's the status of TC Boiler's order?"
       })

       data = response.json()

       # Should ground to DB
       assert len(data["used_domain_facts"]) > 0
       assert "TC Boiler" in data["reply"]
       assert "status" in data["reply"].lower()

       # Should create episodic memory
       assert len(data["used_memories"]) == 0  # No prior memories

       # Verify memory was created
       # ... check episodic_memories table
   ```

3. **Create acceptance script**:
   ```bash
   #!/bin/bash
   # scripts/acceptance.sh

   set -e  # Exit on error

   echo "🧪 Running acceptance tests..."

   # 1. Check domain data exists
   echo "Checking domain data..."
   docker-compose exec -T db psql -U memoryuser -d memorydb -c \
     "SELECT COUNT(*) FROM domain.customers;" | grep -q "[1-9]"

   # 2. Test chat endpoint
   echo "Testing /chat endpoint..."
   curl -sf http://localhost:8000/api/v1/chat \
     -H 'Content-Type: application/json' \
     -d '{"user_id":"test","message":"What is Gai Media?"}' | \
     jq -e '.reply'

   # 3. Test memory growth
   echo "Testing memory growth..."
   # Session A: Store preference
   curl -sf http://localhost:8000/api/v1/chat \
     -H 'Content-Type: application/json' \
     -d '{"user_id":"test","session_id":"00000000-0000-0000-0000-000000000001","message":"Gai Media prefers Friday deliveries"}' \
     > /dev/null

   # Session B: Recall preference
   RESPONSE=$(curl -sf http://localhost:8000/api/v1/chat \
     -H 'Content-Type: application/json' \
     -d '{"user_id":"test","message":"When should we deliver to Gai Media?"}')

   echo "$RESPONSE" | jq -e '.reply | contains("Friday")'

   # 4. Test consolidation
   echo "Testing consolidation..."
   curl -sf http://localhost:8000/api/v1/consolidate \
     -H 'Content-Type: application/json' \
     -d '{"user_id":"test"}' | \
     jq -e '.summary_id'

   # 5. Test entities
   echo "Testing entities..."
   curl -sf "http://localhost:8000/api/v1/entities?session_id=00000000-0000-0000-0000-000000000001" | \
     jq -e '.entities | length > 0'

   echo "✅ All acceptance tests passed!"
   exit 0
   ```

4. Make executable: `chmod +x scripts/acceptance.sh`

**Acceptance Criteria**:
- ✅ Top 10 scenarios pass
- ✅ scripts/acceptance.sh exits 0 (success)
- ✅ All project description requirements validated

**Estimated**: 12-16 hours

---

#### Day 8: Documentation (MEDIUM PRIORITY)

**Deliverable**: Complete API docs and write-up

**Tasks**:

1. **Create API_DOCUMENTATION.md**:
   - Document all endpoints with examples
   - Request/response schemas
   - Error codes
   - Rate limiting (if any)
   - Authentication (if any)

2. **Create WRITEUP.md** (1-page summary for project description):
   ```markdown
   # Memory System Write-Up

   ## Memory Lifecycle

   **Extraction → Storage → Consolidation → Retrieval**

   1. **Extraction**: Chat messages parsed for entities and semantic triples
   2. **Storage**: Episodic events + semantic facts with embeddings
   3. **Consolidation**: Periodic synthesis into summaries
   4. **Retrieval**: Multi-signal relevance scoring

   ## Linking Strategy

   - **Exact match**: Canonical names and IDs (95% of cases)
   - **Fuzzy match**: pg_trgm similarity for typos/variations
   - **LLM coreference**: Pronouns and contextual references (5% of cases)
   - **Collision resolution**: Disambiguation dialogs when similarity scores within margin
   - **Alias learning**: High-confidence resolutions become aliases

   ## Prompt Format & Guardrails

   **Augmented Context Structure**:
   ```
   System: Use the following facts and memories.
   DB Facts:
   - Customer[Gai Media] industry=Entertainment; invoices: INV-1009 ($1200, open)
   Memories:
   - [semantic 0.85] Gai Media prefers Friday deliveries (confirmed 3x)
   ```

   **Guardrails**:
   - PII redaction before storage (emails, phones masked)
   - Hallucination mitigation: Always cite DB facts or memory sources
   - Confidence-based hedging: Low confidence → "Based on limited information..."
   - Conflict detection: When DB ≠ memory, surface both with sources

   ## Future Improvements

   1. Active learning: Tune multi-signal weights from user feedback
   2. ML-based entity resolution: Replace fuzzy matching with learned model
   3. Automatic decay rate calibration per fact type
   4. Procedural pattern mining: More sophisticated ML for pattern detection
   5. Multi-tenant isolation: User-specific memory stores
   ```

3. **Update README.md**:
   - Quick start guide
   - `.env.example` with all required variables
   - Sample API requests (curl examples)
   - Architecture diagram (link to existing docs)
   - Testing instructions

**Acceptance Criteria**:
- ✅ API docs complete with examples
- ✅ 1-page write-up covers all required sections
- ✅ README provides clear onboarding path

**Estimated**: 4-6 hours

---

#### Day 9-10: Polish & Validation (LOW PRIORITY)

**Deliverable**: Production-ready system

**Tasks**:

1. **Code cleanup**:
   - Remove TODO comments
   - Add missing docstrings
   - Fix any linting issues
   - Ensure 100% type coverage

2. **Performance validation**:
   - Run load tests (100 concurrent requests)
   - Verify p95 latency < 800ms
   - Check database query counts (N+1 issues)
   - Profile slow endpoints

3. **Security audit**:
   - Verify no secrets in logs
   - Check .env.example vs .env
   - Test PII redaction
   - Validate input sanitization

4. **Final integration test run**:
   ```bash
   make clean
   make docker-down
   make setup
   make test-all
   scripts/acceptance.sh
   ```

5. **Create deployment guide** (if time permits):
   - Docker compose for production
   - Environment variables
   - Database backups
   - Monitoring recommendations

**Acceptance Criteria**:
- ✅ All tests pass (unit, integration, property-based, E2E)
- ✅ Acceptance script passes
- ✅ No linting errors
- ✅ Performance targets met

**Estimated**: 6-8 hours

---

## Prioritized Task Backlog

### Must Have (Critical Path)

| Priority | Task | Estimated Hours | Blocker For |
|----------|------|----------------|-------------|
| 🔴 P0 | Domain database seed script | 4-6 | E2E tests, demos |
| 🔴 P0 | ChatService orchestration | 8-10 | API layer, E2E tests |
| 🔴 P0 | Repository completions (Summary, Procedural) | 6-8 | Consolidation, patterns |
| 🔴 P0 | API routes (chat, memory, consolidation, entities) | 10-12 | E2E tests, acceptance |
| 🔴 P0 | Pydantic models (request/response) | 2-3 | API routes |

**Subtotal: 30-39 hours**

### Should Have (High Value)

| Priority | Task | Estimated Hours | Value |
|----------|------|----------------|-------|
| 🟡 P1 | Top 10 E2E scenarios | 10-12 | Validation, demos |
| 🟡 P1 | Acceptance script | 2-3 | Automated validation |
| 🟡 P1 | API documentation | 3-4 | Evaluator guidance |
| 🟡 P1 | 1-page write-up | 2-3 | Project requirement |

**Subtotal: 17-22 hours**

### Nice to Have (Polish)

| Priority | Task | Estimated Hours | Value |
|----------|------|----------------|-------|
| 🟢 P2 | Remaining 8 E2E scenarios | 4-6 | Comprehensive validation |
| 🟢 P2 | GET /explain endpoint | 2-3 | Enhanced explainability |
| 🟢 P2 | Performance profiling | 2-3 | Optimization insights |
| 🟢 P2 | Deployment guide | 2-3 | Production readiness |

**Subtotal: 10-15 hours**

---

## Success Criteria

### Functional Requirements ✅

- [ ] All 4 core API endpoints functional (POST /chat, GET /memory, POST /consolidate, GET /entities)
- [ ] Domain database populated with demo data (6 tables, 20+ records)
- [ ] Chat orchestration processes full conversation flow
- [ ] Memory growth across sessions demonstrated
- [ ] Entity linking and disambiguation working
- [ ] Consolidation creates summaries
- [ ] Provenance tracking (used_memories, used_domain_facts)

### Testing Requirements ✅

- [ ] Top 10 E2E scenarios passing
- [ ] Acceptance script passes all checks
- [ ] Unit test coverage remains >90% for Phase 1D components
- [ ] Integration tests cover full repository layer
- [ ] Property-based tests verify invariants

### Documentation Requirements ✅

- [ ] API documentation complete
- [ ] 1-page write-up completed (memory lifecycle, linking, prompts, improvements)
- [ ] README updated with quick start
- [ ] .env.example provided
- [ ] Sample curl requests documented

### Vision Alignment ✅

**The North Star: Experienced Colleague**

Test by completing these statements:

- [ ] "Never forgets what matters" - ✅ Memory retrieval surfaces relevant context
- [ ] "Knows the business deeply" - ✅ Domain database grounding + ontology traversal
- [ ] "Learns your way of working" - ✅ Preference learning, pattern detection
- [ ] "Admits uncertainty" - ✅ Confidence tracking, low-confidence hedging
- [ ] "Explains their thinking" - ✅ Provenance in every response
- [ ] "Gets smarter over time" - ✅ Consolidation, reinforcement, alias learning
- [ ] "Handles mistakes gracefully" - ✅ Conflict detection, correction mechanism
- [ ] "Respects your time" - ✅ p95 latency < 800ms

### Project Description Superset ✅

Your system should be **more** than the project description:

| Project Description | Your System (Superset) |
|---------------------|------------------------|
| 4 core endpoints | ✅ 4 core + /explain (explainability) |
| Basic memory (episodic, semantic) | ✅ + Procedural patterns + Consolidation summaries |
| Simple retrieval (vector search) | ✅ Multi-signal scoring (5 signals) |
| Entity linking | ✅ + Hybrid resolution (deterministic + LLM) + Alias learning |
| Consolidation | ✅ + Multiple scope types (entity, topic, session) + LLM synthesis |
| 18 scenarios | ✅ Full implementation (not just stubs) |
| Minimal confidence tracking | ✅ Epistemic humility framework (decay, reinforcement, validation) |
| Basic provenance | ✅ Full explainability (signal breakdown, source tracking) |

**Vision embodiment**: Your system fully implements all 10 design principles from VISION.md, making it a production-ready cognitive memory layer, not just a feature demo.

---

## Execution Strategy

### Recommended Approach: Iterative Vertical Slices

**Week 1, Day 1-3**: Build one complete vertical slice
1. Seed domain data
2. Implement ChatService
3. Create POST /chat endpoint
4. Test Scenario 9 (cold start grounding)

✅ **Milestone**: Can demo end-to-end chat with DB grounding

**Week 1, Day 4-5**: Complete API layer
1. Finish all repository methods
2. Create remaining endpoints
3. Test Scenario 1 (invoice + preference recall)

✅ **Milestone**: All core endpoints functional

**Week 2, Day 6-8**: Comprehensive testing
1. Implement top 10 scenarios
2. Create acceptance script
3. Validate all requirements met

✅ **Milestone**: System fully validated

**Week 2, Day 9-10**: Documentation & polish
1. Complete write-up and API docs
2. Final testing and validation
3. Deploy demo instance (if time)

✅ **Milestone**: Production-ready deliverable

---

## Risk Mitigation

### Risk 1: LLM Integration Complexity

**Risk**: Chat orchestration might be more complex than estimated

**Mitigation**:
- Start with simplest implementation (direct LLM call)
- Add retry logic and fallbacks incrementally
- Use existing SemanticExtractionService as reference

### Risk 2: E2E Test Fragility

**Risk**: E2E tests may be flaky due to LLM non-determinism

**Mitigation**:
- Test business logic, not exact phrasing
- Use content assertions ("contains X") not exact matches
- Mock LLM for deterministic scenarios where possible

### Risk 3: Time Overrun

**Risk**: 40-50 hours might not be enough for all tasks

**Mitigation**:
- Focus on P0 and P1 tasks first (critical path)
- P2 tasks are truly optional enhancements
- Accept minimum viable E2E coverage (10 scenarios vs all 18)

---

## Timeline Estimates

### Aggressive (Full-Time): 1 Week
- 8-10 hours/day
- Days 1-3: Infrastructure (seed + chat + repos)
- Days 4-5: API layer + basic E2E
- Days 6-7: Documentation + polish

### Standard (Part-Time): 2 Weeks
- 4-6 hours/day
- Week 1: Infrastructure + API layer
- Week 2: Testing + documentation

### Conservative (Comfortable): 3 Weeks
- 2-3 hours/day
- Week 1: Seed data + ChatService
- Week 2: API layer + repositories
- Week 3: E2E tests + documentation

---

## Deliverables Checklist

### Code
- [ ] `scripts/seed_data.py` - Domain data population
- [ ] `src/domain/services/chat_service.py` - Orchestration
- [ ] `src/infrastructure/database/repositories/summary_repository.py` - Complete
- [ ] `src/infrastructure/database/repositories/procedural_repository.py` - New file
- [ ] `src/api/routes/chat.py` - POST /chat
- [ ] `src/api/routes/memory.py` - GET /memory, GET /entities
- [ ] `src/api/routes/consolidation.py` - POST /consolidate, GET /summaries
- [ ] `src/api/routes/explain.py` - GET /explain (optional)
- [ ] `src/api/models/chat.py` - Request/response models
- [ ] `src/api/models/memory.py` - Response models
- [ ] `src/api/models/consolidation.py` - Request/response models

### Tests
- [ ] `tests/e2e/test_scenarios.py` - 10+ scenarios implemented
- [ ] `tests/e2e/conftest.py` - seed_domain_db() implemented
- [ ] `scripts/acceptance.sh` - Executable validation

### Documentation
- [ ] `docs/API_DOCUMENTATION.md` - Complete API reference
- [ ] `docs/WRITEUP.md` - 1-page summary
- [ ] `README.md` - Updated with quick start
- [ ] `.env.example` - All required variables

---

## Final Notes

**This plan is comprehensive and achievable.** The domain layer is already 75% complete with excellent test coverage. The remaining work focuses on:

1. **Wiring** (ChatService brings everything together)
2. **Exposure** (API layer makes it usable)
3. **Validation** (E2E tests prove it works)
4. **Documentation** (Users can understand and use it)

**Your system will be a true superset** of the project description because you've implemented the full vision:
- ✅ All 6 memory layers (not just episodic/semantic)
- ✅ Multi-signal retrieval (not just vector search)
- ✅ Epistemic humility framework (not just confidence scores)
- ✅ Full explainability (not just basic provenance)
- ✅ Learning and adaptation (procedural patterns, consolidation)

**Follow this plan and you'll deliver a production-ready cognitive memory system that demonstrates mastery of:**
- Software architecture (hexagonal, DDD)
- AI/ML integration (LLM, embeddings, vector search)
- Database design (multi-schema, pgvector, migrations)
- Testing philosophy (unit, integration, property-based, E2E)
- Vision-driven development (every decision traced to principles)

**Good luck! 🚀**
