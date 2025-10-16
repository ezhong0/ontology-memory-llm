# E2E Test Implementation Plan

**Date**: 2025-10-16
**Goal**: Achieve 100% E2E test coverage for all 18 ProjectDescription.md scenarios
**Philosophy**: Following CLAUDE.md - **understand deeply, execute with quality, test thoroughly**

---

## Executive Plan

This plan follows the **incremental perfection** approach from CLAUDE.md:
> "Complete each piece fully before moving to the next."

We will implement in **4 phases** corresponding to the 4 priorities, with each phase completed to 100% before moving forward.

---

## Phase 1: E2E Test Infrastructure (Days 1-3)

### Goal
Enable all 18 scenario tests to run against a real database with proper isolation.

### Success Criteria
- ✅ Domain database can be seeded from test data
- ✅ Semantic memories can be created programmatically
- ✅ Demo mode provides isolated database
- ✅ At least 1 E2E scenario test passes end-to-end
- ✅ All 18 scenarios have test implementations

---

### Step 1.1: Investigation Phase (2-3 hours)

**Understand before executing** (CLAUDE.md principle)

**Tasks**:
1. ✅ Read and understand demo mode structure
2. ✅ Understand how domain database is configured
3. ✅ Understand database migration structure
4. ✅ Review existing test fixtures (`tests/conftest.py`)
5. ✅ Analyze one detailed E2E test (Scenario 1) to understand requirements

**Questions to answer**:
- How does demo mode database isolation work?
- What's the schema for `domain.*` tables?
- Are migrations already creating `domain.*` tables?
- What test fixtures already exist?
- What's missing?

**Deliverables**:
- Clear understanding of database structure
- List of required test fixtures
- Understanding of demo mode architecture

---

### Step 1.2: Create Test Fixtures Infrastructure (3-4 hours)

**Directory structure**:
```
tests/
├── fixtures/
│   ├── __init__.py
│   ├── domain_seeder.py      # NEW: Domain DB seeding
│   ├── memory_factory.py     # NEW: Programmatic memory creation
│   ├── api_client.py          # NEW: Test client with auth
│   └── database.py            # NEW: DB session management
└── conftest.py                # UPDATE: Register fixtures
```

**Tasks**:
1. ✅ Create `tests/fixtures/` directory
2. ✅ Create `domain_seeder.py` with `seed_domain_db()` function
3. ✅ Create `memory_factory.py` with `create_semantic_memory()` helper
4. ✅ Create `api_client.py` with authenticated test client
5. ✅ Update `conftest.py` to register all fixtures

**Implementation Details**:

#### `domain_seeder.py`
```python
"""Domain database seeding for E2E tests."""
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date

class DomainSeeder:
    """Seed domain database with test data."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def seed(self, data: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Seed domain database with test data.

        Args:
            data: Dictionary with table names as keys, list of records as values
                  Example:
                  {
                      "customers": [{"name": "Kai Media", "industry": "Entertainment"}],
                      "invoices": [{"invoice_number": "INV-1009", "amount": 1200.00}]
                  }
        """
        # Create customers
        for customer_data in data.get("customers", []):
            await self._create_customer(customer_data)

        # Create sales_orders
        for so_data in data.get("sales_orders", []):
            await self._create_sales_order(so_data)

        # Create work_orders, invoices, payments, tasks
        ...

        await self.session.commit()

    async def _create_customer(self, data: Dict[str, Any]) -> str:
        """Create customer and return customer_id."""
        # Insert into domain.customers
        ...

    # Similar methods for other domain tables
```

#### `memory_factory.py`
```python
"""Memory creation helpers for E2E tests."""
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities import SemanticMemory
from src.infrastructure.database.repositories import SemanticMemoryRepository
from src.infrastructure.di.container import container

class MemoryFactory:
    """Create memories programmatically for testing."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.semantic_repo = SemanticMemoryRepository(session)
        self.embedding_service = container.embedding_service()

    async def create_semantic_memory(
        self,
        user_id: str,
        subject_entity_id: str,
        predicate: str,
        object_value: Any,
        confidence: float = 0.7,
        last_validated_at: datetime = None,
    ) -> SemanticMemory:
        """
        Create semantic memory directly (bypass chat pipeline).

        Args:
            user_id: User ID
            subject_entity_id: Entity this memory is about
            predicate: Relationship type (e.g., "prefers_delivery_day")
            object_value: Value (can be dict, string, etc.)
            confidence: Initial confidence (default 0.7)
            last_validated_at: When last validated (default: now)

        Returns:
            Created SemanticMemory entity
        """
        # Generate embedding
        text_for_embedding = f"{subject_entity_id} {predicate}: {object_value}"
        embedding = await self.embedding_service.generate_embedding(text_for_embedding)

        # Create memory entity
        memory = SemanticMemory(
            user_id=user_id,
            subject_entity_id=subject_entity_id,
            predicate=predicate,
            predicate_type="preference",  # Infer or pass as parameter
            object_value=object_value if isinstance(object_value, dict) else {"value": object_value},
            confidence=confidence,
            reinforcement_count=1,
            last_validated_at=last_validated_at or datetime.now(timezone.utc),
            source_type="test_fixture",
            status="active",
            embedding=embedding,
            importance=0.5,
        )

        # Save to database
        saved_memory = await self.semantic_repo.create(memory)
        await self.session.commit()

        return saved_memory
```

**Deliverables**:
- ✅ All fixture files created and tested
- ✅ Fixtures registered in conftest.py
- ✅ Unit tests for fixtures themselves

---

### Step 1.3: Verify Domain Database Schema (1-2 hours)

**Understand the current state** (CLAUDE.md principle)

**Tasks**:
1. ✅ Check if `domain.*` schema exists in migrations
2. ✅ Check if `domain.*` tables are created
3. ✅ If missing, create migration for domain schema
4. ✅ If missing, create seed data script

**Investigation**:
```bash
# Check existing migrations
ls src/infrastructure/database/migrations/versions/

# Check what tables exist
make db-shell
# Then in psql:
\dn  # List schemas
\dt domain.*  # List domain tables
```

**If domain schema doesn't exist**, create it:
```bash
make db-create-migration MSG="add domain schema and tables"
```

**Deliverables**:
- ✅ Domain schema exists
- ✅ All 6 domain tables created (customers, sales_orders, work_orders, invoices, payments, tasks)
- ✅ Seed data available for testing

---

### Step 1.4: Fix Demo Mode Database Isolation (2-3 hours)

**Understand the current issue** (CLAUDE.md principle)

**Tasks**:
1. ✅ Read `src/demo/api/router.py` to understand demo mode
2. ✅ Understand how `DEMO_MODE_ENABLED` flag works
3. ✅ Check if demo mode uses separate database
4. ✅ Fix Pydantic/SQLAlchemy warnings in demo integration tests

**Investigation**:
```bash
# Read demo mode code
cat src/demo/api/router.py

# Check demo config
grep -r "DEMO_MODE" src/config/

# Run demo integration tests to see exact error
poetry run pytest tests/demo/integration/test_scenario_api.py -v
```

**Potential fixes**:
1. Update pytest.ini to ignore Pydantic warnings from demo mode
2. Fix deprecated Pydantic model configurations
3. Ensure demo mode uses transaction rollback for isolation

**Deliverables**:
- ✅ Demo integration tests pass
- ✅ Demo mode properly isolated from main database
- ✅ No collection errors in test suite

---

### Step 1.5: Unskip Scenario 1 and Verify (3-4 hours)

**Incremental perfection** (CLAUDE.md principle): Complete one scenario fully before moving to next.

**Tasks**:
1. ✅ Remove `@pytest.mark.skip` from Scenario 1
2. ✅ Update test to use new fixtures
3. ✅ Run test and debug failures
4. ✅ Fix all issues until test passes
5. ✅ Document any learnings for other scenarios

**Implementation**:
```python
# tests/e2e/test_scenarios.py

@pytest.mark.e2e
@pytest.mark.asyncio
# REMOVE: @pytest.mark.skip(reason="TODO: Implement after chat pipeline ready")
async def test_scenario_01_overdue_invoice_with_preference_recall(
    api_client: AsyncClient,
    domain_seeder: DomainSeeder,
    memory_factory: MemoryFactory,
):
    """SCENARIO 1: Overdue invoice follow-up with preference recall."""

    # ARRANGE: Seed domain database
    await domain_seeder.seed({
        "customers": [{
            "name": "Kai Media",
            "industry": "Entertainment"
        }],
        "sales_orders": [{
            "customer_id": "kai_123",  # Will be linked
            "so_number": "SO-1001",
            "title": "Album Fulfillment",
            "status": "in_fulfillment",
        }],
        "invoices": [{
            "so_id": "so_1001_id",  # Will be linked
            "invoice_number": "INV-1009",
            "amount": 1200.00,
            "due_date": "2025-09-30",
            "status": "open"
        }]
    })

    # ARRANGE: Create semantic memory (preference)
    await memory_factory.create_semantic_memory(
        user_id="finance_agent",
        subject_entity_id="customer:kai_123",
        predicate="prefers_delivery_day",
        object_value={"day": "Friday"},
        confidence=0.8,
    )

    # ACT: User query
    response = await api_client.post("/api/v1/chat", json={
        "user_id": "finance_agent",
        "message": "Draft an email for Kai Media about their unpaid invoice and mention their preferred delivery day for the next shipment."
    })

    # ASSERT: Response structure
    assert response.status_code == 200
    data = response.json()

    # ... rest of assertions from existing test
```

**Debugging strategy**:
1. Run test with verbose output
2. Check each assertion one by one
3. Add logging to see what's being retrieved
4. Fix integration issues as they arise
5. Document fixes for reuse in other scenarios

**Deliverables**:
- ✅ Scenario 1 test passes completely
- ✅ Template established for other scenarios
- ✅ Lessons learned documented

---

### Step 1.6: Implement Remaining 10 Scenario Stubs (4-6 hours)

**Use Scenario 1 as template** (pattern recognition from CLAUDE.md)

**Scenarios to implement** (in order of complexity):

1. **Scenario 9: Cold-start grounding** (easiest - no prior memories)
2. **Scenario 4: NET terms learning** (simple memory creation)
3. **Scenario 12: Fuzzy entity matching** (entity resolution test)
4. **Scenario 8: Multilingual handling** (alias creation)
5. **Scenario 5: Partial payments** (DB aggregation)
6. **Scenario 6: SLA breach detection** (cross-table reasoning)
7. **Scenario 11: Cross-object reasoning** (chain: SO→WO→Invoice)
8. **Scenario 13: Policy memory** (PII redaction test)
9. **Scenario 14: Session consolidation** (multi-session test)
10. **Scenario 2: Reschedule work order** (DB update simulation)

**For each scenario**:
1. Read ProjectDescription.md to understand requirements
2. Design test data setup
3. Implement test using fixtures
4. Run and verify
5. Document any issues

**Deliverables**:
- ✅ All 18 scenarios have complete implementations
- ✅ All tests documented with vision principles
- ✅ Pattern library for common test operations

---

### Step 1.7: Run Full E2E Test Suite (1 hour)

**Final verification** (CLAUDE.md: test thoroughly)

**Tasks**:
1. ✅ Run all 18 E2E tests together
2. ✅ Verify no flaky tests (run 3 times)
3. ✅ Check test isolation (each test cleans up properly)
4. ✅ Measure test execution time
5. ✅ Document any remaining issues

**Acceptance criteria**:
- All 18 E2E tests pass consistently
- Tests complete in < 5 minutes total
- No test pollution (each test independent)

---

## Phase 2: Philosophy Tests (Days 4-5)

### Goal
Verify that epistemic humility and other vision principles work in practice.

### Success Criteria
- ✅ All 12 philosophy tests pass
- ✅ LLM service properly integrated into test pipeline
- ✅ Vision principles validated with real LLM responses

---

### Step 2.1: Analyze Philosophy Test Failures (1-2 hours)

**Understand before fixing** (CLAUDE.md principle)

**Tasks**:
1. ✅ Run philosophy tests with full traceback
2. ✅ Categorize failures by root cause
3. ✅ Identify which tests need LLM vs which need integration fixes

**Investigation**:
```bash
# Run with full output
poetry run pytest tests/philosophy/test_epistemic_humility.py -v --tb=long

# Analyze each failure
```

**Expected failure categories**:
1. **LLM integration** - Tests that need real LLM responses
2. **Integration issues** - Tests that need full pipeline wired
3. **Test design issues** - Tests that need assertion updates

**Deliverables**:
- ✅ Clear categorization of all 10 failures
- ✅ Root cause for each
- ✅ Fix strategy for each category

---

### Step 2.2: Create LLM Test Fixtures (2-3 hours)

**Tasks**:
1. ✅ Create mock LLM service for deterministic tests
2. ✅ Create real LLM service fixture for vision validation
3. ✅ Create test configuration for LLM selection

**Implementation**:

```python
# tests/fixtures/llm_fixtures.py

class MockLLMService:
    """Mock LLM service with deterministic responses."""

    async def generate_reply(self, prompt: str, context: str) -> str:
        """Return deterministic response based on prompt patterns."""
        if "low confidence" in context:
            return "I'm not entirely sure, but based on..."  # Hedging language

        if "no data" in context:
            return "I don't have information about..."  # Acknowledge gap

        # ... pattern-based responses

class RealLLMService:
    """Real LLM service for vision validation."""
    # Uses actual OpenAI API for testing vision principles

@pytest.fixture
def llm_service(request):
    """Provide LLM service based on test marker."""
    if request.node.get_closest_marker("use_real_llm"):
        return RealLLMService()
    else:
        return MockLLMService()
```

**Deliverables**:
- ✅ Mock LLM service for fast, deterministic tests
- ✅ Real LLM service for vision validation
- ✅ Test markers for LLM selection

---

### Step 2.3: Fix Philosophy Tests One by One (3-4 hours)

**Incremental approach** (CLAUDE.md principle)

**Order** (simplest to hardest):
1. `test_decay_only_decreases_confidence` - Integration fix
2. `test_zero_days_decay_is_identity` - Integration fix
3. `test_explicit_statement_has_medium_confidence` - Semantic extraction
4. `test_inferred_fact_has_lower_confidence` - Semantic extraction
5. `test_correction_has_high_confidence` - Semantic extraction
6. `test_low_confidence_triggers_hedging_language` - LLM integration
7. `test_no_data_acknowledges_gap_doesnt_hallucinate` - LLM integration
8. `test_conflict_detection_surfaces_both_sources` - Conflict API
9. `test_aged_memory_triggers_validation_prompt` - Full pipeline
10. `test_epistemic_humility_test_coverage` - Meta-test

**For each test**:
1. Understand what vision principle it validates
2. Wire required services
3. Run test
4. Debug failures
5. Verify fix doesn't break other tests
6. Document fix

**Deliverables**:
- ✅ All 12 philosophy tests passing
- ✅ Vision principles validated
- ✅ Test fixtures reusable for future philosophy tests

---

## Phase 3: Integration Tests (Day 6)

### Goal
Fix 2 failing Phase 1D integration tests.

### Success Criteria
- ✅ Consolidation integration test passes
- ✅ Procedural memory integration test passes
- ✅ Phase 1D features verified end-to-end

---

### Step 3.1: Debug Consolidation Test (2-3 hours)

**Tasks**:
1. ✅ Run test with full traceback
2. ✅ Understand what it's testing
3. ✅ Identify root cause
4. ✅ Fix issue
5. ✅ Verify consolidation works

**Investigation**:
```bash
poetry run pytest tests/integration/test_phase1d_consolidation.py::TestConsolidationIntegration::test_entity_consolidation_success -v --tb=long
```

**Deliverables**:
- ✅ Test passes
- ✅ Consolidation service verified

---

### Step 3.2: Debug Procedural Memory Test (2-3 hours)

**Tasks**:
1. ✅ Run test with full traceback
2. ✅ Understand what it's testing
3. ✅ Identify root cause
4. ✅ Fix issue
5. ✅ Verify procedural memory works

**Investigation**:
```bash
poetry run pytest tests/integration/test_phase1d_procedural.py::TestProceduralMemoryIntegration::test_procedural_memory_increment_observed_count -v --tb=long
```

**Deliverables**:
- ✅ Test passes
- ✅ Procedural memory service verified

---

## Phase 4: Missing API Endpoints (Day 7)

### Goal
Implement 2 missing functional requirements from ProjectDescription.md.

### Success Criteria
- ✅ `GET /memory` endpoint implemented and tested
- ✅ `GET /entities` endpoint implemented and tested
- ✅ 100% functional requirement coverage

---

### Step 4.1: Implement GET /memory (2-3 hours)

**Follow existing patterns** (CLAUDE.md: learn from codebase)

**Tasks**:
1. ✅ Review existing retrieval patterns (study `/api/v1/chat`)
2. ✅ Create Pydantic request/response models
3. ✅ Implement endpoint in `src/api/routes/retrieval.py`
4. ✅ Wire dependencies
5. ✅ Write integration test
6. ✅ Test manually with curl

**Implementation**:
```python
# src/api/models/retrieval.py

class GetMemoryRequest(BaseModel):
    """Request model for GET /memory."""
    user_id: str = Query(..., description="User ID")
    k: int = Query(10, ge=1, le=100, description="Number of memories to retrieve")
    memory_type: Optional[str] = Query(None, description="Filter by type: episodic|semantic|procedural|summary")

class MemoryResponse(BaseModel):
    """Individual memory in response."""
    memory_id: int
    memory_type: str
    content: str
    confidence: float
    created_at: str
    importance: float

class GetMemoryResponse(BaseModel):
    """Response model for GET /memory."""
    user_id: str
    memories: List[MemoryResponse]
    total_count: int

# src/api/routes/retrieval.py

@router.get("/api/v1/memory", response_model=GetMemoryResponse)
async def get_memories(
    user_id: str = Query(...),
    k: int = Query(10, ge=1, le=100),
    memory_type: Optional[str] = Query(None),
    episodic_repo: EpisodicMemoryRepository = Depends(get_episodic_repository),
    semantic_repo: SemanticMemoryRepository = Depends(get_semantic_repository),
    procedural_repo: ProceduralMemoryRepository = Depends(get_procedural_repository),
    summary_repo: SummaryRepository = Depends(get_summary_repository),
) -> GetMemoryResponse:
    """
    Retrieve top memories and summaries for a user.

    Returns most recent memories across all types, sorted by importance and recency.
    """
    memories = []

    # Fetch from each repository if not filtered
    if not memory_type or memory_type == "episodic":
        episodic_memories = await episodic_repo.find_by_user(user_id, limit=k)
        memories.extend([...])  # Convert to MemoryResponse

    if not memory_type or memory_type == "semantic":
        semantic_memories = await semantic_repo.find_by_user(user_id, limit=k)
        memories.extend([...])

    # ... procedural, summary

    # Sort by importance * recency score
    memories.sort(key=lambda m: m.importance * recency_factor(m.created_at), reverse=True)

    return GetMemoryResponse(
        user_id=user_id,
        memories=memories[:k],
        total_count=len(memories),
    )
```

**Test**:
```python
# tests/integration/test_retrieval_api.py

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_memory_endpoint(api_client, test_user_memories):
    """Test GET /memory returns user's memories."""
    response = await api_client.get("/api/v1/memory", params={
        "user_id": "test_user",
        "k": 10
    })

    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == "test_user"
    assert len(data["memories"]) <= 10
    assert all("memory_id" in m for m in data["memories"])
```

**Deliverables**:
- ✅ Endpoint implemented
- ✅ Integration test passing
- ✅ Documented in API docs

---

### Step 4.2: Implement GET /entities (2-3 hours)

**Similar to /memory** (pattern reuse)

**Tasks**:
1. ✅ Create Pydantic models
2. ✅ Implement endpoint
3. ✅ Wire dependencies
4. ✅ Write integration test
5. ✅ Test manually

**Implementation**:
```python
# src/api/models/retrieval.py

class GetEntitiesRequest(BaseModel):
    """Request model for GET /entities."""
    session_id: Optional[str] = Query(None)
    user_id: Optional[str] = Query(None)
    entity_type: Optional[str] = Query(None)

class EntityResponse(BaseModel):
    """Individual entity in response."""
    entity_id: str
    canonical_name: str
    entity_type: str
    external_ref: Dict[str, Any]
    properties: Optional[Dict[str, Any]]
    aliases: List[str]

class GetEntitiesResponse(BaseModel):
    """Response model for GET /entities."""
    entities: List[EntityResponse]
    total_count: int

# src/api/routes/retrieval.py

@router.get("/api/v1/entities", response_model=GetEntitiesResponse)
async def get_entities(
    session_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_repo: EntityRepository = Depends(get_entity_repository),
    episodic_repo: EpisodicMemoryRepository = Depends(get_episodic_repository),
) -> GetEntitiesResponse:
    """
    List detected entities and their external references.

    Can filter by session_id, user_id, or entity_type.
    """
    entities = []

    if session_id:
        # Get entities from episodic memories in this session
        episodic_memories = await episodic_repo.find_by_session(session_id)
        entity_ids = set()
        for memory in episodic_memories:
            for entity in memory.entities:
                entity_ids.add(entity["id"])

        # Fetch entity details
        for entity_id in entity_ids:
            entity = await entity_repo.get_by_id(entity_id)
            if entity:
                # Get aliases
                aliases = await entity_repo.get_aliases(entity_id)
                entities.append(EntityResponse(
                    entity_id=entity.entity_id,
                    canonical_name=entity.canonical_name,
                    entity_type=entity.entity_type,
                    external_ref=entity.external_ref,
                    properties=entity.properties,
                    aliases=[a.alias_text for a in aliases],
                ))

    elif user_id:
        # Get all entities mentioned by user
        # (via episodic memories)
        ...

    return GetEntitiesResponse(
        entities=entities,
        total_count=len(entities),
    )
```

**Deliverables**:
- ✅ Endpoint implemented
- ✅ Integration test passing
- ✅ Documented in API docs

---

## Execution Philosophy (from CLAUDE.md)

### 1. **Understand Before Executing**

For each task:
- Read all relevant code first
- Understand existing patterns
- Ask clarifying questions if needed
- Plan approach before coding

### 2. **Incremental Perfection**

- Complete each step to 100% before moving to next
- Don't rough-in multiple features
- Each deliverable should be production-ready

### 3. **Test Thoroughly**

- Unit test each new component
- Integration test each API endpoint
- E2E test each scenario
- Run full test suite after each phase

### 4. **Root Cause Thinking**

When debugging:
- Don't fix symptoms
- Understand WHY the failure occurs
- Fix the root cause
- Prevent recurrence

### 5. **Pattern Recognition**

- Study existing code for patterns
- Reuse successful approaches
- Don't reinvent patterns
- Document new patterns for future use

### 6. **Documentation as Contract**

- Update docs as we implement
- Keep DESIGN.md in sync with code
- Document decisions and rationale
- Create examples for future reference

---

## Risk Management

### Potential Blockers

1. **Domain DB not in migrations**
   - **Mitigation**: Check early (Step 1.3), create if missing
   - **Fallback**: Use in-memory SQLite for tests

2. **Demo mode isolation broken**
   - **Mitigation**: Fix Pydantic warnings (Step 1.4)
   - **Fallback**: Use pytest-postgresql for isolation

3. **LLM API costs for tests**
   - **Mitigation**: Use mock LLM for most tests (Step 2.2)
   - **Fallback**: Only use real LLM for critical vision tests

4. **Flaky E2E tests**
   - **Mitigation**: Proper database cleanup between tests
   - **Fallback**: Retry mechanism for network-dependent tests

5. **Test execution time too long**
   - **Mitigation**: Parallel test execution where safe
   - **Fallback**: Mark slow tests, run separately in CI

---

## Success Metrics

### Phase 1 Complete When:
- ✅ 18/18 E2E tests passing
- ✅ All scenarios cover ProjectDescription.md requirements
- ✅ Tests run in < 5 minutes
- ✅ 100% test pass rate on E2E suite

### Phase 2 Complete When:
- ✅ 12/12 philosophy tests passing
- ✅ Vision principles validated with LLM
- ✅ Test fixtures reusable

### Phase 3 Complete When:
- ✅ 2/2 integration tests passing
- ✅ Phase 1D features verified

### Phase 4 Complete When:
- ✅ 4/4 functional requirements implemented
- ✅ All API endpoints documented
- ✅ Integration tests passing

### Overall Success:
- ✅ **325/325 tests passing (100%)**
- ✅ **100% ProjectDescription.md coverage**
- ✅ **Production-ready for deployment**

---

## Timeline

**Estimated Total**: 6-7 days (assuming 6-8 hours/day)

| Phase | Duration | Days |
|-------|----------|------|
| **Phase 1: E2E Infrastructure** | 16-20 hours | 2-3 days |
| **Phase 2: Philosophy Tests** | 8-12 hours | 1-2 days |
| **Phase 3: Integration Tests** | 4-6 hours | 1 day |
| **Phase 4: Missing Endpoints** | 4-6 hours | 1 day |
| **Buffer** | 4-6 hours | 0.5-1 day |
| **Total** | 36-50 hours | 6-7 days |

**Aggressive timeline**: 5 days (8-10 hours/day)
**Conservative timeline**: 8 days (4-6 hours/day)

---

## Next Steps

1. ✅ Review this plan with stakeholder
2. ✅ Get approval to proceed
3. ✅ Start Phase 1, Step 1.1 (Investigation)
4. ✅ Execute systematically, one step at a time

**Let's build something production-ready.** 🚀

---

**Document Version**: 1.0
**Last Updated**: 2025-10-16
**Status**: Ready for execution
