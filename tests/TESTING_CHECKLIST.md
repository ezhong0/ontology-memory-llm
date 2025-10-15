# Testing Implementation Checklist

**Status**: Foundation Complete - Ready for Phase 1A
**Last Updated**: 2025-10-15

This checklist tracks testing infrastructure implementation progress.

---

## ✅ Foundation (Complete)

- [x] Test directory structure created
- [x] `conftest.py` with global fixtures
- [x] `fixtures/mock_services.py` - Mock repositories and services
- [x] `fixtures/factories.py` - Test data factories
- [x] `fixtures/llm_test_evaluator.py` - LLM-based semantic evaluation
- [x] `docs/quality/TESTING_PHILOSOPHY.md` - Comprehensive testing philosophy
- [x] `tests/README.md` - Testing infrastructure guide
- [x] Example philosophy test: `tests/philosophy/test_epistemic_humility.py`
- [x] Property test template: `tests/property/test_confidence_invariants.py`
- [x] E2E test template: `tests/e2e/test_scenarios.py`

---

## 📋 Layer 0: LLM-Based Vision Validation

### Philosophy Tests (5% of suite)

- [x] **Epistemic Humility** - `tests/philosophy/test_epistemic_humility.py`
  - [x] Low confidence triggers hedging language
  - [x] No data acknowledges gap (doesn't hallucinate)
  - [x] Conflicts surface both sources
  - [x] Aged memories trigger validation prompts
- [ ] **Dual Truth Equilibrium** - `tests/philosophy/test_dual_truth.py`
  - [ ] DB facts always included when available
  - [ ] Memory never overrides current DB state
  - [ ] Conflicts explicitly acknowledged
- [ ] **Explainability** - `tests/philosophy/test_explainability.py`
  - [ ] All responses have traceable sources
  - [ ] Provenance data complete and accurate
- [ ] **Graceful Forgetting** - `tests/philosophy/test_graceful_forgetting.py`
  - [ ] Consolidation preserves essence
  - [ ] Summary replaces many episodes

---

## 📋 Layer 1: Property-Based Tests

### Invariant Tests (15% of suite)

- [x] **Confidence Invariants** - `tests/property/test_confidence_invariants.py`
  - [x] Reinforcement never exceeds MAX_CONFIDENCE
  - [x] Decay only decreases confidence
  - [x] Zero days decay is identity
  - [x] Passive decay is idempotent
  - [x] Reinforcement has diminishing returns
- [ ] **State Transition Invariants** - `tests/property/test_state_transitions.py`
  - [ ] Only valid state transitions allowed
  - [ ] Superseded memories retain provenance chain
  - [ ] Terminal states cannot transition
- [ ] **Retrieval Invariants** - `tests/property/test_retrieval_invariants.py`
  - [ ] Score components sum to 1.0
  - [ ] Entity overlap bounded [0, 1]
  - [ ] Temporal decay is monotonic

---

## 📋 Layer 2: Domain Unit Tests

### Entity Resolution (50% of suite - largest layer)

- [ ] `tests/unit/domain/test_entity_resolver.py`
  - [ ] Stage 1: Exact match returns confidence 1.0
  - [ ] Stage 2: User alias match returns confidence 0.95
  - [ ] Stage 3: Fuzzy match high similarity (>0.85)
  - [ ] Stage 3: Fuzzy match low similarity (0.70-0.85)
  - [ ] Stage 4: Coreference resolution
  - [ ] Stage 5: Disambiguation flow
  - [ ] High-confidence fuzzy creates global alias
  - [ ] User selection creates user-specific alias
  - [ ] Ambiguous raises AmbiguousEntityError
  - [ ] Not found raises EntityNotFoundError

### Memory Extraction

- [ ] `tests/unit/domain/test_memory_extractor.py`
  - [ ] Explicit statement extracts semantic memory
  - [ ] Question does NOT extract semantic
  - [ ] Correction has high confidence
  - [ ] Inferred fact has lower confidence
  - [ ] Event type classification correct
  - [ ] Confidence factors populated

### Memory Lifecycle

- [ ] `tests/unit/domain/test_lifecycle_manager.py`
  - [ ] Calculate effective confidence (passive decay)
  - [ ] State transitions (active → aging → superseded)
  - [ ] Reinforcement boosts confidence
  - [ ] Validation resets decay
  - [ ] Supersession creates chain
  - [ ] Conflict detection logic

### Memory Retrieval

- [ ] `tests/unit/domain/test_memory_retriever.py`
  - [ ] Semantic similarity signal
  - [ ] Entity overlap signal
  - [ ] Temporal relevance signal
  - [ ] Importance signal
  - [ ] Reinforcement signal
  - [ ] Multi-signal scoring (weighted sum)
  - [ ] Strategy selection (factual vs procedural vs exploratory)
  - [ ] Token budget allocation
  - [ ] Summary boost (15%)

---

## 📋 Layer 3: Integration Tests

### Database Operations (20% of suite)

- [ ] `tests/integration/test_entity_repository.py`
  - [ ] Create and retrieve canonical entity
  - [ ] Fuzzy search with pg_trgm
  - [ ] Create and retrieve alias
  - [ ] Get alias by text and user_id
  - [ ] Performance: fuzzy search < 30ms

- [ ] `tests/integration/test_memory_repository.py`
  - [ ] Create and retrieve episodic memory
  - [ ] Create and retrieve semantic memory
  - [ ] Semantic search with pgvector
  - [ ] Find similar semantic (reinforcement detection)
  - [ ] Update memory (reinforcement, state change)
  - [ ] Performance: semantic search < 50ms (1000 memories)

- [ ] `tests/integration/test_domain_db_connector.py`
  - [ ] Query domain.customers
  - [ ] Query domain.invoices
  - [ ] Query domain.sales_orders
  - [ ] Get related entities via ontology
  - [ ] Lazy entity creation

### External Services

- [ ] `tests/integration/test_llm_service.py`
  - [ ] Extract semantic triples (real OpenAI call)
  - [ ] Resolve coreference (real OpenAI call)
  - [ ] Cost tracking (<$0.002 per extraction)

- [ ] `tests/integration/test_embedding_service.py`
  - [ ] Generate embedding (real OpenAI call)
  - [ ] Embedding dimension = 1536
  - [ ] Embeddings normalized (unit vectors)

---

## 📋 Layer 4: E2E Scenario Tests

### Project Description Scenarios (10% of suite)

All scenarios in `tests/e2e/test_scenarios.py`:

- [x] Scenario 01: Overdue invoice with preference recall (template)
- [x] Scenario 02: Ambiguous entity disambiguation (template)
- [ ] Scenario 03: Multi-session memory consolidation
- [ ] Scenario 04: DB fact + memory enrichment
- [ ] Scenario 05: Episodic → semantic transformation
- [ ] Scenario 06: Coreference resolution
- [x] Scenario 07: Conflicting memories consolidation (template)
- [ ] Scenario 08: Procedural pattern learning
- [ ] Scenario 09: Cross-entity ontology traversal
- [x] Scenario 10: Active recall for stale facts (template)
- [ ] Scenario 11: Confidence-based hedging language
- [ ] Scenario 12: Importance-based retrieval
- [ ] Scenario 13: Temporal query (time range)
- [ ] Scenario 14: Entity alias learning
- [x] Scenario 15: Memory vs DB conflict → trust DB (template)
- [x] Scenario 16: Graceful forgetting → consolidation (template)
- [x] Scenario 17: Explainability → provenance tracking (template)
- [x] Scenario 18: Privacy → user-scoped memories (template)

**Progress**: 6/18 templates created (33%)

---

## 📋 Layer 5: Performance & Cost Tests

### Latency Benchmarks

- [ ] `tests/performance/test_latency.py`
  - [ ] Entity resolution fast path < 50ms P95
  - [ ] Semantic search < 50ms P95 (1000 memories)
  - [ ] Full retrieval < 100ms P95
  - [ ] Chat endpoint < 800ms P95

### Cost Validation

- [ ] `tests/performance/test_cost.py`
  - [ ] LLM usage < 10% of operations
  - [ ] Cost per turn < $0.002
  - [ ] Embedding cost tracking
  - [ ] Total monthly cost projection

---

## 📊 Coverage Tracking

### Current Coverage (Estimated)

| Layer | Target | Current | Status |
|-------|--------|---------|--------|
| Domain Services | 95% | 0% | 🔴 Not started |
| Domain Entities | 90% | 0% | 🔴 Not started |
| Repositories | 80% | 0% | 🔴 Not started |
| API Routes | 85% | 0% | 🔴 Not started |
| **Overall** | **85-90%** | **0%** | 🔴 Not started |

### Coverage Commands

```bash
# Check coverage
make test-cov

# Coverage by directory
pytest tests/unit/domain --cov=src/domain --cov-report=term-missing

# Enforce minimum coverage
pytest --cov=src --cov-fail-under=85
```

---

## 🎯 Phase 1A Priorities (Weeks 1-2)

Focus on these tests first to support initial implementation:

### Week 1
- [ ] `tests/unit/domain/test_entity_resolver.py` (exact match only)
- [ ] `tests/integration/test_entity_repository.py` (create/retrieve)
- [ ] Property tests for confidence bounds

### Week 2
- [ ] `tests/unit/domain/test_entity_resolver.py` (fuzzy match)
- [ ] `tests/integration/test_entity_repository.py` (fuzzy search)
- [ ] E2E scenario 2 (disambiguation)

---

## 🚀 Quick Start Commands

```bash
# Run existing tests (property + philosophy examples)
pytest tests/property tests/philosophy -v

# Run when first unit tests created
pytest tests/unit -v

# Run with coverage
pytest tests/unit --cov=src/domain --cov-report=html

# Watch mode (tests run on file changes)
pytest-watch tests/unit

# Run specific test file
pytest tests/unit/domain/test_entity_resolver.py -v

# Run specific test function
pytest tests/unit/domain/test_entity_resolver.py::test_exact_match_returns_confidence_1_0 -v
```

---

## 📝 Notes

### Test-Driven Development Workflow

1. **Write test first** (following template from TESTING_PHILOSOPHY.md)
2. **Run test** - should fail (red)
3. **Implement feature** - minimal code to pass
4. **Run test** - should pass (green)
5. **Refactor** - improve code while keeping tests green
6. **Repeat**

### When to Skip Tests

- Integration tests: Skip if PostgreSQL not running
- E2E tests: Skip if API not implemented
- LLM tests: Skip in CI if OpenAI quota exceeded
- Performance tests: Skip in watch mode (slow)

Use `@pytest.mark.skip(reason="...")` for temporary skips.

### Test Data Management

- Use **factories** for object creation: `EntityFactory.create(...)`
- Use **fixtures** for setup/teardown: `test_db_session`, `mock_repo`
- Use **builders** for complex objects: `CanonicalEntityBuilder().build()`
- Keep test data **minimal** - only what's needed for the test

### Common Pitfalls

1. **Don't test implementation details** - test behavior, not internals
2. **Don't share state between tests** - each test should be independent
3. **Don't mock what you don't own** - mock your ports, not external libraries
4. **Don't skip assertions** - every test should verify something
5. **Don't write flaky tests** - tests should be deterministic

---

## ✅ Definition of Done

A test layer is "done" when:

- [ ] All test files created and implemented
- [ ] All tests passing
- [ ] Coverage target met for that layer
- [ ] No skipped tests (except expected skips)
- [ ] CI/CD pipeline green
- [ ] Code review passed

---

**Next Action**: Start with `tests/unit/domain/test_entity_resolver.py` (exact match test)
