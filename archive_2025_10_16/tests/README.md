# Testing Infrastructure

**Status**: Ready for Phase 1A Implementation
**Coverage Target**: 90%+ domain layer, 85%+ overall
**Philosophy**: Testing validates both correctness AND philosophical alignment

---

## Quick Start

```bash
# Install test dependencies
poetry install

# Run all tests
make test

# Run specific test layers
make test-unit              # Fast unit tests only (70% of test suite)
pytest tests/integration    # Integration tests (DB required)
pytest tests/e2e           # End-to-end scenario tests
pytest tests/philosophy    # Vision principle validation
pytest tests/property      # Property-based invariant tests

# Run with coverage
make test-cov              # HTML report in htmlcov/

# Watch mode (run tests on file changes)
make test-watch
```

---

## Test Directory Structure

```
tests/
├── README.md                          # This file
├── conftest.py                        # Global fixtures & pytest configuration
│
├── fixtures/                          # Shared test infrastructure
│   ├── __init__.py
│   ├── factories.py                   # Test data factories (EntityFactory, MemoryFactory)
│   ├── mock_services.py              # Mock repositories & services (no I/O)
│   └── llm_test_evaluator.py        # LLM-based semantic evaluation
│
├── property/                          # Property-based tests (hypothesis)
│   ├── __init__.py
│   └── test_confidence_invariants.py # Epistemic humility invariants
│
├── unit/                              # Unit tests (fast, no I/O)
│   ├── domain/                        # Domain logic tests
│   │   ├── test_entity_resolver.py   # 5-stage resolution algorithm (TODO)
│   │   ├── test_memory_extractor.py  # LLM extraction logic (TODO)
│   │   └── test_lifecycle_manager.py # Memory state transitions (TODO)
│   └── utils/                         # Utility function tests
│
├── integration/                       # Integration tests (with DB/external services)
│   ├── test_entity_repository.py     # PostgreSQL entity operations (TODO)
│   ├── test_memory_repository.py     # pgvector semantic search (TODO)
│   └── test_domain_db_connector.py   # Domain ontology integration (TODO)
│
├── e2e/                               # End-to-end scenario tests
│   └── test_scenarios.py             # All 18 scenarios from ProjectDescription.md (TODO)
│
├── philosophy/                        # Vision principle validation
│   └── test_epistemic_humility.py    # Epistemic humility behaviors (✅ example complete)
│
└── performance/                       # Performance & cost benchmarks
    ├── test_latency.py               # P95 latency targets (TODO)
    └── test_cost.py                  # LLM cost budgets (TODO)
```

---

## Test Layers (Pyramid)

### Layer 0: LLM-Based Vision Validation (Foundation)
**Purpose**: Verify philosophical alignment where traditional assertions can't
**Coverage**: ~5% of test suite
**Speed**: Slow (LLM API calls)
**Cost**: ~$0.90 per full test run

**When to use**:
- Testing semantic nuances (e.g., "Does tone match confidence level?")
- Detecting hallucinations vs honest gap acknowledgment
- Validating dual truth equilibrium (DB grounding vs memory enrichment)
- Edge case generation from vision principles

**Example**:
```python
# tests/philosophy/test_epistemic_humility.py
evaluator = LLMTestEvaluator()
result = await evaluator.evaluate_epistemic_humility(
    response=system_response,
    confidence=0.4,  # Low confidence
    context={"memory_age_days": 95}
)

assert result.passes, f"Epistemic humility violation: {result.reasoning}"
```

**Files**:
- `tests/fixtures/llm_test_evaluator.py` - LLM evaluation infrastructure
- `tests/philosophy/test_epistemic_humility.py` - Example philosophy tests

---

### Layer 1: Property-Based Tests (Philosophical Invariants)
**Purpose**: Verify invariants hold for ALL possible inputs
**Coverage**: ~15% of test suite
**Speed**: Medium (generates many test cases)
**Library**: `hypothesis`

**When to use**:
- Testing mathematical properties (e.g., "Decay is monotonically decreasing")
- Invariant verification (e.g., "Confidence never exceeds 0.95")
- State machine properties (e.g., "Valid state transitions only")

**Example**:
```python
# tests/property/test_confidence_invariants.py
from hypothesis import given, strategies as st

@given(
    base_confidence=st.floats(min_value=0.0, max_value=1.0),
    days_old=st.integers(min_value=0, max_value=365)
)
def test_decay_only_decreases_confidence(base_confidence, days_old):
    effective = calculate_effective_confidence(base_confidence, days_old)
    assert effective <= base_confidence
```

**Files**:
- `tests/property/test_confidence_invariants.py` - Confidence bounds, decay, reinforcement

---

### Layer 2: Domain Unit Tests (Business Logic)
**Purpose**: Test pure domain logic in isolation
**Coverage**: ~50% of test suite (largest layer)
**Speed**: Fast (no I/O, uses mocks)

**When to use**:
- Testing domain services (entity resolution, memory extraction, retrieval scoring)
- Testing value objects and entities
- Testing business logic algorithms

**Example**:
```python
# tests/unit/domain/test_entity_resolver.py
@pytest.mark.asyncio
async def test_exact_match_returns_confidence_1_0(mock_repo):
    resolver = EntityResolver(entity_repo=mock_repo)
    result = await resolver.resolve(mention="Acme Corporation", context=...)

    assert result.entity_id == "customer:acme_123"
    assert result.confidence == 1.0
    assert result.method == "exact"
```

**Fixtures to use**:
- `mock_entity_repository` - In-memory entity storage
- `mock_llm_service` - Deterministic LLM responses
- `mock_embedding_service` - Consistent embeddings
- Factories from `tests/fixtures/factories.py`

**Files to create**:
- `tests/unit/domain/test_entity_resolver.py`
- `tests/unit/domain/test_memory_extractor.py`
- `tests/unit/domain/test_memory_retriever.py`
- `tests/unit/domain/test_lifecycle_manager.py`

---

### Layer 3: Integration Tests (Infrastructure)
**Purpose**: Test database operations and external services
**Coverage**: ~20% of test suite
**Speed**: Medium (requires PostgreSQL)

**When to use**:
- Testing repository implementations (PostgreSQL queries)
- Testing pgvector semantic search
- Testing pg_trgm fuzzy matching
- Testing domain DB connector

**Example**:
```python
# tests/integration/test_entity_repository.py
@pytest.mark.asyncio
async def test_fuzzy_search_uses_pg_trgm(test_db_session):
    repo = PostgresEntityRepository(test_db_session)
    await repo.create(Entity(canonical_name="Acme Corporation"))

    results = await repo.fuzzy_search(query="ACME Corp", threshold=0.7)

    assert len(results) == 1
    assert results[0].similarity_score >= 0.7
```

**Fixtures to use**:
- `test_db_session` - Isolated database session (auto-rollback)
- `test_db_with_seed_data` - Database with common test data
- `test_db_with_1000_memories` - For performance testing

**Files to create**:
- `tests/integration/test_entity_repository.py`
- `tests/integration/test_memory_repository.py`
- `tests/integration/test_domain_db_connector.py`

---

### Layer 4: E2E Scenario Tests (Project Description)
**Purpose**: Test all 18 scenarios from ProjectDescription.md end-to-end
**Coverage**: ~10% of test suite
**Speed**: Slow (full API stack)

**When to use**:
- Validating complete user journeys
- Testing full chat pipeline (ingest → resolve → retrieve → generate → remember)
- Verifying all functional requirements

**Example**:
```python
# tests/e2e/test_scenarios.py
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_01_overdue_invoice_with_preference_recall(api_client):
    # Seed domain DB
    await seed_domain_db({"invoices": [...]})

    # Seed memory
    await api_client.post("/api/v1/chat", json={
        "message": "Remember: Kai Media prefers Friday deliveries"
    })

    # User query
    response = await api_client.post("/api/v1/chat", json={
        "message": "Draft email for Kai Media about unpaid invoice..."
    })

    # Assertions
    assert "INV-1009" in response.json()["response"]
    assert "Friday" in response.json()["response"]
```

**Fixtures to use**:
- `api_client` - HTTP client for API testing
- `test_db_session` - Database isolation

**Files to create**:
- `tests/e2e/test_scenarios.py` - All 18 scenarios

**Scenario checklist** (from ProjectDescription.md):
1. ☐ Overdue invoice with preference recall
2. ☐ Ambiguous entity disambiguation
3. ☐ Multi-session memory consolidation
4. ☐ DB fact + memory enrichment
5. ☐ Episodic → semantic transformation
6. ☐ Coreference resolution
7. ☐ Conflicting memories consolidation
8. ☐ Procedural pattern learning
9. ☐ Cross-entity ontology traversal
10. ☐ Active recall for stale facts
11. ☐ Confidence-based hedging language
12. ☐ Importance-based retrieval
13. ☐ Temporal query (time range)
14. ☐ Entity alias learning
15. ☐ Memory vs DB conflict (trust DB)
16. ☐ Graceful forgetting (consolidation)
17. ☐ Explainability (provenance)
18. ☐ Privacy (user-scoped memories)

---

### Layer 5: Performance & Cost Tests
**Purpose**: Verify P95 latency targets and cost budgets
**Coverage**: Benchmarks only
**Speed**: Medium

**Example**:
```python
# tests/performance/test_latency.py
@pytest.mark.benchmark
async def test_semantic_search_under_50ms(benchmark, test_db_with_1000_memories):
    def search():
        return asyncio.run(repo.semantic_search(...))

    result = benchmark(search)
    assert result.stats['mean'] * 1000 < 50  # P95 < 50ms
```

**Targets** (from PHASE1_ROADMAP.md):
- Entity resolution (fast path): P95 < 50ms
- Semantic search (pgvector): P95 < 50ms
- Full retrieval: P95 < 100ms
- Chat endpoint: P95 < 800ms
- LLM cost: ~$0.002 per turn

**Files to create**:
- `tests/performance/test_latency.py`
- `tests/performance/test_cost.py`

---

## Test Markers

Use pytest markers to run specific test categories:

```python
@pytest.mark.unit          # Unit test (fast, no I/O)
@pytest.mark.integration   # Integration test (DB required)
@pytest.mark.e2e          # End-to-end test (full API)
@pytest.mark.philosophy   # Vision principle validation
@pytest.mark.property     # Property-based test (hypothesis)
@pytest.mark.slow         # Slow test (real LLM API)
@pytest.mark.benchmark    # Performance benchmark
```

**Run by marker**:
```bash
pytest -m unit              # Only unit tests
pytest -m "not slow"        # Skip slow tests
pytest -m "philosophy or property"  # Vision validation only
```

---

## Fixtures Reference

### Database Fixtures (from `conftest.py`)

**`test_db_session`** - Isolated database session (transaction auto-rollback)
```python
@pytest.mark.asyncio
async def test_something(test_db_session):
    repo = PostgresEntityRepository(test_db_session)
    # Test database operations
    # Automatically rolls back after test
```

**`test_db_with_seed_data`** - Database with common test data
```python
async def test_with_seed_data(test_db_with_seed_data):
    # Database already has:
    # - system_config entries
    # - Sample canonical entities (Gai Media, TC Boiler)
```

**`test_db_with_1000_memories`** - For performance testing
```python
async def test_performance(test_db_with_1000_memories):
    # Database has 1000 semantic memories with embeddings
    # Use for pgvector performance testing
```

### Mock Service Fixtures (from `conftest.py`)

**`mock_entity_repository`** - In-memory entity storage
**`mock_llm_service`** - Deterministic LLM responses
**`mock_embedding_service`** - Consistent embeddings
**`mock_domain_db_service`** - In-memory domain DB

### Factory Fixtures (from `fixtures/factories.py`)

**EntityFactory** - Create test entities
```python
entity = EntityFactory.create(canonical_name="Acme Corp")
customer = EntityFactory.create_customer(name="Gai Media", customer_id="gai_123")
```

**MemoryFactory** - Create test memories
```python
memory = MemoryFactory.create_semantic(
    subject_entity_id="customer:gai_123",
    predicate="delivery_preference",
    confidence=0.75
)

aged = MemoryFactory.create_aged_memory(
    subject_entity_id="customer:test",
    predicate="pref",
    object_value="value",
    days_old=95  # Triggers active recall
)
```

**DomainDataFactory** - Create domain database records
```python
customer = DomainDataFactory.create_customer(name="Gai Media")
invoice = DomainDataFactory.create_invoice(
    customer_id="gai_123",
    amount=1200.00,
    status="open"
)
```

### Helper Fixtures

**`freeze_time`** - Freeze time for testing temporal behavior
```python
def test_with_frozen_time(freeze_time):
    freeze_time(datetime(2025, 9, 15, 12, 0, 0))
    # All datetime.utcnow() calls return frozen time
```

**`assert_confidence_in_range`** - Validate confidence bounds
```python
def test_confidence(assert_confidence_in_range):
    assert_confidence_in_range(0.75, min_val=0.6, max_val=0.9)
```

---

## Testing Best Practices

### 1. Test One Thing at a Time
```python
# ❌ Bad: Testing multiple concerns
def test_entity_resolution():
    result = resolver.resolve("Acme")
    assert result.entity_id == "customer:acme_123"  # Resolution correctness
    assert result.latency_ms < 50  # Performance
    assert result.confidence > 0.8  # Confidence logic

# ✅ Good: Separate tests
def test_exact_match_resolves_correctly():
    result = resolver.resolve("Acme Corporation")
    assert result.entity_id == "customer:acme_123"

def test_exact_match_meets_latency_target():
    result = resolver.resolve("Acme Corporation")
    assert result.latency_ms < 50
```

### 2. Use Factories for Test Data
```python
# ❌ Bad: Manual construction
entity = CanonicalEntity(
    entity_id="customer:test_123",
    entity_type="customer",
    canonical_name="Test",
    external_ref={"table": "domain.customers", "id": "test_123"},
    properties={},
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow()
)

# ✅ Good: Use factory
entity = EntityFactory.create(canonical_name="Test")
```

### 3. Arrange-Act-Assert Pattern
```python
def test_fuzzy_match_creates_alias():
    # ARRANGE: Setup test state
    mock_repo = MockEntityRepository()
    mock_repo.add_entity(EntityFactory.create(canonical_name="Acme Corporation"))
    resolver = EntityResolver(entity_repo=mock_repo)

    # ACT: Execute the behavior under test
    result = resolver.resolve(mention="ACME Corp", context=...)

    # ASSERT: Verify outcomes
    assert result.entity_id == "customer:acme_123"
    assert result.method == "fuzzy"
```

### 4. Test Error Cases
```python
def test_ambiguous_resolution_raises_error():
    # Setup: Two entities that match "Apple"
    mock_repo.add_entity(EntityFactory.create(canonical_name="Apple Inc"))
    mock_repo.add_entity(EntityFactory.create(canonical_name="Apple Farm"))

    # Should raise AmbiguousEntityError
    with pytest.raises(AmbiguousEntityError) as exc_info:
        resolver.resolve(mention="Apple", context=...)

    # Verify error details
    assert len(exc_info.value.candidates) == 2
    assert exc_info.value.disambiguation_required
```

### 5. Use Descriptive Test Names
```python
# ❌ Bad: Vague
def test_resolution():
    ...

# ✅ Good: Clear intent
def test_exact_match_returns_confidence_1_0():
    ...

def test_fuzzy_match_above_threshold_creates_alias():
    ...

def test_ambiguous_resolution_requires_disambiguation():
    ...
```

---

## Coverage Enforcement

**Pre-commit hook** (fast unit tests only):
```bash
pytest tests/unit --cov=src --cov-fail-under=90
```

**CI/CD pipeline** (full test suite):
```yaml
- run: pytest tests/unit --cov-fail-under=90
- run: pytest tests/integration --cov-fail-under=80
- run: pytest tests/e2e --cov-fail-under=70
- run: pytest tests/property tests/philosophy
```

**Coverage targets**:
- Domain services: 95% (core business logic)
- Domain entities: 90%
- Repository implementations: 80%
- API routes: 85%
- Overall: 85-90%

**View coverage report**:
```bash
make test-cov
open htmlcov/index.html
```

---

## Running Tests During Development

### Watch Mode (Recommended)
```bash
make test-watch
# Tests run automatically on file changes
```

### Fast Feedback Loop
```bash
# Only run tests for file you're working on
pytest tests/unit/domain/test_entity_resolver.py -v

# Only run specific test function
pytest tests/unit/domain/test_entity_resolver.py::test_exact_match_returns_confidence_1_0

# Run tests matching pattern
pytest -k "entity and exact"
```

### Debug Mode
```bash
# Run with print statements visible
pytest tests/unit/domain/test_entity_resolver.py -s

# Drop into debugger on failure
pytest tests/unit/domain/test_entity_resolver.py --pdb

# More verbose output
pytest tests/unit/domain/test_entity_resolver.py -vv
```

---

## Philosophy → Code Traceability

Every vision principle has explicit tests:

| Vision Principle | Test File | Verification Method |
|-----------------|-----------|---------------------|
| **Epistemic Humility** | `tests/property/test_confidence_invariants.py` | Property-based: confidence ≤ 0.95 |
| | `tests/philosophy/test_epistemic_humility.py` | LLM-based: tone matches confidence |
| **Dual Truth** | `tests/e2e/test_scenarios.py` (Scenario 4, 15) | E2E: DB grounding + memory enrichment |
| **Graceful Forgetting** | `tests/property/test_confidence_invariants.py` | Property-based: decay monotonicity |
| | `tests/e2e/test_scenarios.py` (Scenario 16) | E2E: consolidation behavior |
| **Problem of Reference** | `tests/unit/domain/test_entity_resolver.py` | Unit: 5-stage resolution accuracy |
| **Temporal Validity** | `tests/property/test_confidence_invariants.py` | Property-based: decay + reinforcement |
| | `tests/e2e/test_scenarios.py` (Scenario 10) | E2E: active recall for stale facts |
| **Explainability** | `tests/e2e/test_scenarios.py` (Scenario 17) | E2E: all responses have citations |
| **Learning** | `tests/e2e/test_scenarios.py` (Scenarios 5, 8) | E2E: episodic→semantic→procedural flow |

---

## Next Steps for Phase 1A

### Week 1-2: Foundation Tests
- [ ] Create `tests/unit/domain/test_entity_resolver.py`
- [ ] Create `tests/integration/test_entity_repository.py`
- [ ] Implement and test exact match resolution (fastest path)

### Week 3-4: Memory Core Tests
- [ ] Create `tests/unit/domain/test_memory_extractor.py`
- [ ] Create `tests/unit/domain/test_lifecycle_manager.py`
- [ ] Create `tests/integration/test_memory_repository.py`

### Week 5-6: Retrieval Tests
- [ ] Create `tests/unit/domain/test_memory_retriever.py`
- [ ] Create performance tests for pgvector
- [ ] Benchmark multi-signal scoring

### Week 7-8: E2E Scenario Tests
- [ ] Implement all 18 scenarios in `tests/e2e/test_scenarios.py`
- [ ] Run full test suite with coverage
- [ ] Generate philosophy alignment report

---

## Questions?

Refer to:
- **Philosophy**: `/docs/quality/TESTING_PHILOSOPHY.md`
- **Roadmap**: `/docs/quality/PHASE1_ROADMAP.md`
- **Fixtures**: `tests/conftest.py` and `tests/fixtures/`
- **Examples**: `tests/philosophy/test_epistemic_humility.py` (complete example)
