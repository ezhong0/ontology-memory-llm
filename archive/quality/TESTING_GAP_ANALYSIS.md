# Testing Gap Analysis and Execution Plan

**Date**: 2025-10-15
**Phase**: Phase 1D (Learning Layer) - Testing Focus
**Reference**: TESTING_PHILOSOPHY.md (6-layer testing pyramid)

## Executive Summary

Current testing coverage: **~35%** of TESTING_PHILOSOPHY.md requirements
- ✅ Layer 3 (Integration): Complete for Phase 1D
- ⚠️ Layer 2 (Domain Unit): 60% complete (missing Phase 1D unit tests)
- ⚠️ Layer 1 (Property-Based): 30% complete (missing consolidation/procedural invariants)
- ❌ Layer 0 (LLM Vision Validation): 0% complete
- ❌ Layer 4 (E2E Scenarios): 0% complete
- ❌ Layer 5 (Philosophy Validation): 0% complete
- ❌ Layer 6 (Performance/Cost): 0% complete

**Target**: 90%+ domain coverage, 85%+ overall by end of Phase 1

---

## Current Test Infrastructure Assessment

### ✅ What We Have

#### 1. **Test Configuration (conftest.py)**
- Comprehensive fixtures for DB, mocks, API client
- Proper pytest markers: unit, integration, e2e, philosophy, benchmark, slow
- Time manipulation fixtures (`freeze_time`)
- Performance testing fixtures (`test_db_with_1000_memories`)
- **Assessment**: Excellent foundation

#### 2. **Property-Based Tests**
**File**: `tests/property/test_confidence_invariants.py` (330 lines)
- ✅ Confidence bounds testing (epistemic humility)
- ✅ Decay properties (monotonicity, identity, idempotence)
- ✅ Reinforcement properties (diminishing returns)
- ✅ Decay-reinforcement interaction
- **Coverage**: 5 test classes, ~25 test cases
- **Assessment**: Strong philosophical grounding

#### 3. **Domain Unit Tests**
**Files**:
- `test_multi_signal_scorer.py` (559 lines) - Comprehensive
- `test_entity_resolution_service.py` - Exists
- `test_semantic_extraction_service.py` - Exists
- `test_memory_validation_service.py` - Exists
- `test_conflict_detection_service.py` - Exists

**Assessment**: Good coverage for Phases 1A-1C, missing Phase 1D

#### 4. **Integration Tests**
**Files**:
- `test_phase1d_consolidation.py` (370 lines) - ✅ Just created
  - 8 test cases: success, LLM fallback, confidence boosting, scope types
- `test_phase1d_procedural.py` (374 lines) - ✅ Just created
  - 6 test cases: pattern detection, reinforcement, query augmentation, feature extraction

**Assessment**: Phase 1D integration testing complete

### ❌ What's Missing

#### Layer 0: LLM-Based Vision Validation (5%)
**Priority**: HIGH
**Estimated Lines**: 400-500
**Cost per run**: ~$0.90

**Missing Tests**:
1. **Epistemic Humility Validator**
   - Use GPT-4o to evaluate consolidation summaries for certainty language
   - Verify API responses never claim 100% confidence
   - Check conflict resolution shows uncertainty appropriately

2. **Dual Truth Validator**
   - Verify memory responses cite both DB facts and contextual memory
   - Check that DB facts override memory in conflicts
   - Validate provenance tracking

3. **Graceful Forgetting Validator**
   - Verify consolidation synthesizes insights without preserving all details
   - Check passive decay reduces noise over time

**Implementation**: `tests/philosophy/test_vision_validation_llm.py`

#### Layer 1: Property-Based Tests (15%)
**Priority**: HIGH
**Estimated Lines**: 600-800

**Missing Tests**:
1. **Consolidation Invariants** (`test_consolidation_invariants.py`)
   - Property: Summary confidence ≤ min(source_confidences)
   - Property: Key facts always sourced from episodic/semantic memories
   - Property: Consolidation never invents facts not in sources
   - Property: Multiple consolidations produce semantically consistent summaries

2. **Procedural Memory Invariants** (`test_procedural_invariants.py`)
   - Property: Pattern confidence ≤ 0.90 (Phase 1 limit)
   - Property: increment_observed_count() is monotonically increasing
   - Property: Pattern detection is deterministic (same input → same patterns)
   - Property: Reinforcement provides diminishing returns

3. **State Machine Invariants** (`test_state_machine_invariants.py`)
   - Property: Memory state transitions are valid (active → superseded/validated, never backwards)
   - Property: Consolidated memories remain immutable

**Implementation**: `tests/property/test_consolidation_invariants.py`, `test_procedural_invariants.py`

#### Layer 2: Domain Unit Tests (50%)
**Priority**: CRITICAL
**Estimated Lines**: 1200-1500

**Missing Tests**:
1. **ConsolidationService Unit Tests** (`test_consolidation_service_unit.py`)
   - Test _fetch_memories() with various scopes
   - Test _synthesize_with_llm() with mocked LLM responses
   - Test _create_fallback_summary() logic
   - Test _boost_confirmed_facts() with various confidence levels
   - Test _store_summary() validation
   - Test error handling and retry logic
   - **Estimated**: 15-20 test cases, ~400 lines

2. **ProceduralMemoryService Unit Tests** (`test_procedural_service_unit.py`)
   - Test _extract_features() with various episode types
   - Test _classify_intent() with edge cases
   - Test _extract_topics() coverage
   - Test _find_frequent_sequences() with different min_support values
   - Test _format_trigger_pattern() and _format_action_heuristic()
   - Test pattern reinforcement logic
   - **Estimated**: 18-25 test cases, ~500 lines

3. **Value Object Unit Tests** (`test_phase1d_value_objects.py`)
   - Test Pattern validation (required fields, confidence bounds)
   - Test ProceduralMemory.increment_observed_count() edge cases
   - Test ConsolidationScope factory methods
   - Test SummaryData.from_llm_response() parsing
   - **Estimated**: 10-15 test cases, ~300 lines

**Implementation**: `tests/unit/domain/services/test_consolidation_service_unit.py`, etc.

#### Layer 4: E2E Scenario Tests (10%)
**Priority**: MEDIUM
**Estimated Lines**: 1500-2000

**Missing Tests**:
From `ProjectDescription.md`, need E2E tests for 18 scenarios:
1. Gai Media Friday delivery preference (consolidation)
2. TC Boiler safety gear reminder (semantic extraction + retrieval)
3. Regal Cinemas NET15 terms (conflict detection)
4. Wild Rivers payment authorization (procedural memory)
5. ... (14 more scenarios)

**Implementation**: `tests/e2e/test_scenarios.py` (one test function per scenario)

#### Layer 5: Philosophy Validation Tests
**Priority**: MEDIUM
**Estimated Lines**: 400-500

**Missing Tests**:
1. **Epistemic Humility Tests** (`test_epistemic_humility.py`)
   - Never return confidence > 0.95
   - Always provide confidence_factors breakdown
   - Acknowledge conflicts explicitly (not silently resolve)

2. **Dual Truth Tests** (`test_dual_truth.py`)
   - Memory retrieval includes both DB and semantic facts
   - DB facts marked as "correspondence truth"
   - Memory facts marked as "contextual truth"
   - Provenance always tracked

3. **Graceful Forgetting Tests** (`test_graceful_forgetting.py`)
   - Old memories decay passively
   - Consolidation reduces episodic clutter
   - Summaries preserve insights, not details

**Implementation**: `tests/philosophy/test_epistemic_humility.py`, etc.

#### Layer 6: Performance & Cost Tests
**Priority**: LOW (but required for Phase 1 completion)
**Estimated Lines**: 300-400

**Missing Tests**:
1. **Performance Benchmarks** (`test_performance.py`)
   - Entity resolution fast path: <50ms (P95)
   - Entity resolution LLM path: <300ms (P95)
   - Semantic search: <50ms (P95)
   - Multi-signal scoring: <100ms (P95)
   - Chat endpoint: <800ms (P95)
   - Consolidation: <2000ms (P95)

2. **Cost Validation** (`test_cost_tracking.py`)
   - Track LLM API calls per operation
   - Verify average cost per turn ~$0.002
   - Verify surgical LLM usage (5% entity resolution, not 100%)

**Implementation**: `tests/benchmark/test_performance.py`, `tests/benchmark/test_cost_tracking.py`

---

## Prioritized Execution Plan

### Phase 1: Critical Unit Tests (Days 9-10 Focus)
**Goal**: Achieve 90%+ domain layer coverage

**Tasks**:
1. ✅ **ConsolidationService Unit Tests** (400 lines)
   - Priority: CRITICAL
   - Estimated time: 3-4 hours
   - File: `tests/unit/domain/services/test_consolidation_service_unit.py`

2. ✅ **ProceduralMemoryService Unit Tests** (500 lines)
   - Priority: CRITICAL
   - Estimated time: 3-4 hours
   - File: `tests/unit/domain/services/test_procedural_service_unit.py`

3. ✅ **Phase 1D Value Object Tests** (300 lines)
   - Priority: HIGH
   - Estimated time: 2 hours
   - File: `tests/unit/domain/test_phase1d_value_objects.py`

**Total**: 1200 lines, ~8-10 hours

### Phase 2: Property-Based Tests (Day 10 AM)
**Goal**: Expand property testing for Phase 1D invariants

**Tasks**:
4. ✅ **Consolidation Invariants** (300 lines)
   - Priority: HIGH
   - Estimated time: 2-3 hours
   - File: `tests/property/test_consolidation_invariants.py`

5. ✅ **Procedural Memory Invariants** (300 lines)
   - Priority: HIGH
   - Estimated time: 2-3 hours
   - File: `tests/property/test_procedural_invariants.py`

**Total**: 600 lines, ~4-6 hours

### Phase 3: Philosophy Validation (Day 10 PM - If Time)
**Goal**: Verify vision principles are embodied in code

**Tasks**:
6. ⏭️ **Epistemic Humility Tests** (200 lines)
   - Priority: MEDIUM
   - Estimated time: 2 hours
   - File: `tests/philosophy/test_epistemic_humility.py`

7. ⏭️ **LLM Vision Validator** (250 lines)
   - Priority: MEDIUM
   - Estimated time: 2-3 hours
   - File: `tests/philosophy/test_vision_validation_llm.py`

**Total**: 450 lines, ~4-5 hours

### Phase 4: Documentation & Review (Final Day)
**Goal**: Ensure all tests are documented and passing

**Tasks**:
8. Run full test suite with coverage
9. Fix any failing tests
10. Document test results in PHASE1_STATUS.md
11. Update TESTING_PHILOSOPHY.md with actual implementation notes

---

## Test Coverage Targets

| Layer | Component | Current | Target | Gap |
|-------|-----------|---------|--------|-----|
| **Layer 2: Domain Unit** |
| | ConsolidationService | 0% | 90% | ❌ 400 lines |
| | ProceduralMemoryService | 0% | 90% | ❌ 500 lines |
| | Value Objects (Phase 1D) | 0% | 85% | ❌ 300 lines |
| **Layer 1: Property-Based** |
| | Consolidation Invariants | 0% | 100% | ❌ 300 lines |
| | Procedural Invariants | 0% | 100% | ❌ 300 lines |
| | Confidence Invariants | ✅ 100% | 100% | ✅ Complete |
| **Layer 3: Integration** |
| | Phase 1D Consolidation | ✅ 100% | 100% | ✅ Complete |
| | Phase 1D Procedural | ✅ 100% | 100% | ✅ Complete |
| **Layer 5: Philosophy** |
| | Epistemic Humility | 0% | 100% | ⏭️ 200 lines |
| | LLM Vision Validation | 0% | 100% | ⏭️ 250 lines |

**Overall Domain Coverage Goal**: 90%+
**Current Estimate**: 60% (with existing tests) → Target 90% after execution

---

## Implementation Strategy

### 1. Test-First Approach
- Write tests before fixing/refactoring
- Tests serve as living documentation
- Use TDD for bug fixes

### 2. Fast Feedback Loop
- Run `make test-watch` during development
- Run `make test-unit` frequently (fast, no DB)
- Run `make test-integration` after unit tests pass
- Run `make test-cov` before committing

### 3. Quality Gates
```bash
# All must pass before completion
make typecheck       # Zero type errors
make lint           # Zero linting errors
make test-unit      # All unit tests pass
make test-integration # All integration tests pass
make test-cov       # Coverage ≥ 85%
```

---

## Success Criteria

### Phase 1D Testing Complete When:
- ✅ All domain services have 90%+ unit test coverage
- ✅ All value objects have 85%+ test coverage
- ✅ Property-based tests validate core invariants
- ✅ Integration tests validate full pipelines
- ✅ Philosophy tests validate vision principles
- ✅ `make check-all` passes without errors
- ✅ Coverage report shows ≥85% overall, ≥90% domain layer

---

## Risk Assessment

### High Risk
- **Property tests may find bugs**: Hypothesis can discover edge cases we missed
- **LLM-based tests are expensive**: ~$0.90 per full run (limit to CI only)

### Medium Risk
- **Time constraint**: 1200+ lines of tests in ~10-12 hours (aggressive)
- **Consolidation logic complexity**: LLM retry logic and fallback paths need thorough testing

### Low Risk
- **Integration tests already complete**: Phase 1D integration coverage is solid
- **Existing test infrastructure is robust**: conftest.py and fixtures are comprehensive

---

## Next Steps

**Immediate (Start Now)**:
1. Create `tests/unit/domain/services/test_consolidation_service_unit.py`
2. Implement 15-20 unit tests for ConsolidationService
3. Run tests and verify coverage increases

**After Unit Tests Complete**:
4. Create property-based tests for consolidation/procedural invariants
5. Run hypothesis with `--hypothesis-show-statistics` to see coverage

**Final Steps**:
6. Implement philosophy validation tests
7. Run full test suite with coverage
8. Document results and update PHASE1_STATUS.md

---

## Appendix: Testing Philosophy Alignment

Every test should answer:
1. **What vision principle does this test validate?**
2. **What invariant must hold for ALL inputs?**
3. **How does this prevent regression?**

Examples:
- Unit test for `consolidate_entity()` → Validates **Graceful Forgetting** (summaries don't preserve all details)
- Property test for `increment_observed_count()` → Validates **Epistemic Humility** (never exceeds MAX_CONFIDENCE)
- Philosophy test for API responses → Validates **Explainable Reasoning** (always includes provenance)
