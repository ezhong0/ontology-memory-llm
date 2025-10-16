# Roadmap to 100% Scenario Coverage

**Philosophy**: Incremental Perfection - Complete each piece 100% before moving to the next

> "Progress should be: 100% → 100% → 100%, not 60% → 60% → 60%"

---

## Current Status (Updated 2025-01-16)

**E2E Tests Passing**: **10/18 (55.6%)** ✅

**Passing Scenarios**:
- ✅ Scenario 1: Overdue invoice with preference recall
- ✅ Scenario 2: Work order rescheduling
- ✅ Scenario 3: Ambiguous entity disambiguation
- ✅ Scenario 4: NET terms learning
- ✅ Scenario 5: Partial payments and balance
- ✅ Scenario 6: SLA breach detection
- ✅ Scenario 7: Conflicting memories consolidation **(JUST FIXED)**
- ✅ Scenario 9: Cold start grounding to DB
- ✅ Scenario 15: Audit trail explainability
- ✅ Scenario 17: Memory-vs-DB conflict trust DB

**Remaining Scenarios** (8):
- ⏳ Scenario 8: Multilingual alias handling
- ⏳ Scenario 10: Active recall for stale facts
- ⏳ Scenario 11: Cross-object reasoning
- ⏳ Scenario 12: Fuzzy match alias learning
- ⏳ Scenario 13: PII guardrail memory
- ⏳ Scenario 14: Session window consolidation
- ⏳ Scenario 16: Reminder creation from intent
- ⏳ Scenario 18: Task completion via conversation

**Recent Completion**: Phase 2.1 (Conflict Resolution) ✅
- 6 fundamental bugs fixed
- Same-day timestamp precision
- Memory status lifecycle (active → superseded → invalidated)
- Conflicts exposed in API with structured data

**Infrastructure Status**:
- ✅ Core services: Entity resolution, semantic extraction, conflict detection/resolution
- ✅ Domain queries: work_orders, tasks, invoices, SLA detection
- ✅ API endpoints: /chat, /conflicts
- ⏳ **Missing**: /disambiguate, /consolidate, /validate, /tasks/{id}/complete
- ✅ **Quality**: All 198 unit/integration tests passing, typecheck clean

**Target**: 18/18 scenarios passing (100%)
**Approach**: Quality over speed. Comprehensive solutions over quick fixes.

---

## Guiding Principles

### 1. Understanding Before Execution
Every task begins with investigation, not implementation:
- Read design docs
- Study existing patterns
- Understand vision principles
- Consider ripple effects
- Plan tests first

### 2. Incremental Perfection
Each milestone is **production-ready** before moving forward:
- ✅ Implementation complete (not 80%, 100%)
- ✅ All tests passing (unit + integration + E2E)
- ✅ Edge cases handled
- ✅ Error paths tested
- ✅ Quality checks pass (lint, typecheck, coverage)

### 3. Test-Driven Progress
**Before starting any task, know which tests must pass.**
**Before moving to next task, verify all tests pass.**

### 4. Root Cause Solutions
Fix root causes, not symptoms:
- Understand WHY the gap exists
- Solve the problem completely
- Don't create band-aids

### 5. Vision-Driven
Every feature serves explicit vision principles:
- Perfect recall of relevant context
- Deep business understanding
- Adaptive learning
- Epistemic humility
- Explainable reasoning
- Continuous improvement

---

## Phase 0: Foundation ✅ COMPLETE

### Status
- ✅ All 198 unit/integration tests passing
- ✅ `make test` succeeds
- ✅ `make typecheck` succeeds
- ✅ 10/18 E2E scenarios passing

**Foundation is solid. Ready to proceed.**

---

## Phase 1: Quick Wins → 12/18 Scenarios (67%)

> **Goal**: Unblock scenarios with minimal implementation gaps. Wire up existing services to API.

**Time Estimate**: 3-4 hours
**Scenarios to Unlock**: #12 (fuzzy auto-alias), #14 (consolidation)

---

### Milestone 1.1: Auto-Alias from Fuzzy Match

**Vision Principle**: Learning - System improves resolution speed over time

**Scenario**: #12 (fuzzy match alias learning)

**Investigation** (15 min):
1. Read `src/domain/services/entity_resolution_service.py` lines 200-250
2. Find Stage 3 fuzzy match logic
3. Check if `EntityRepository.create_alias()` method exists
4. Understand: After fuzzy match succeeds, should auto-create alias for next time

**Implementation** (30 min):
```python
# In src/domain/services/entity_resolution_service.py
# After Stage 3 fuzzy match succeeds (around line 240):

if fuzzy_result:
    logger.info(
        "fuzzy_match_success",
        mention=mention_text,
        entity_id=fuzzy_result.entity_id,
        confidence=fuzzy_result.confidence
    )

    # Auto-create alias for future exact matches
    try:
        await self.entity_repo.create_alias(
            canonical_entity_id=fuzzy_result.entity_id,
            alias_text=mention_text,
            alias_source="fuzzy_learned",
            user_id=user_id,
            confidence=fuzzy_result.confidence,
            metadata={"learned_from": "fuzzy_match_stage_3"}
        )
        logger.info(
            "alias_learned_from_fuzzy_match",
            alias_text=mention_text,
            entity_id=fuzzy_result.entity_id
        )
    except Exception as e:
        # Don't fail resolution if alias creation fails
        logger.warning(
            "alias_creation_failed",
            error=str(e),
            mention=mention_text
        )

    return fuzzy_result
```

**Tests That MUST Pass**:

1. **Unit Test**: `tests/unit/domain/services/test_entity_resolution_service.py`
   ```python
   async def test_fuzzy_match_creates_alias():
       """After fuzzy match, alias should be auto-created."""
       # Given: "Gy Media" fuzzy matches "Gai Media"
       # When: resolve() called
       # Then: Alias created for "Gy Media" → "Gai Media"
       # Then: Next resolve("Gy Media") uses exact match (faster)
   ```

2. **E2E Test**: `tests/e2e/test_scenarios.py::test_scenario_12_fuzzy_match_alias_learning`
   ```bash
   poetry run pytest tests/e2e/test_scenarios.py::test_scenario_12_fuzzy_match_alias_learning -xvs
   ```
   - Turn 1: "Gy Media" (typo) → fuzzy match resolves to Gai Media
   - Turn 2: "Gy Media" (same typo) → exact match (alias learned)
   - Logs show: `alias_learned_from_fuzzy_match`

**Success Criteria**:
- [ ] Alias created after fuzzy match success
- [ ] Graceful failure if alias creation fails (doesn't break resolution)
- [ ] Unit test passes
- [ ] E2E Scenario 12 passes
- [ ] No regressions (run full test suite)

**Verification Before Proceeding**:
```bash
# Run this BEFORE moving to next task:
poetry run pytest tests/e2e/test_scenarios.py::test_scenario_12_fuzzy_match_alias_learning -xvs
poetry run pytest tests/e2e/test_scenarios.py -v  # Ensure no regressions
```

**Commit**: `feat(entity-resolution): auto-create alias from fuzzy matches (Scenario 12)`

**Status After**: 11/18 passing (61%)

---

### Milestone 1.2: Consolidation Endpoint

**Vision Principle**: Graceful Forgetting - Abstract details into summaries

**Scenario**: #14 (session window consolidation)

**Investigation** (20 min):
1. Check `src/domain/services/consolidation_service.py` - does it exist?
2. Check `src/domain/services/consolidation_trigger_service.py` - what thresholds?
3. Read `tests/e2e/test_scenarios.py` lines for Scenario 14 - what's expected?
4. Check if `/api/v1/consolidate` endpoint exists

**Implementation** (45 min):

File: `src/api/models/consolidation.py` (NEW)
```python
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class ConsolidationRequest(BaseModel):
    scope_type: str  # "entity" | "session" | "topic"
    scope_identifier: str  # entity_id | session_id | topic_name

class ConsolidationResponse(BaseModel):
    consolidation_triggered: bool
    summary_id: Optional[int] = None
    summary_text: Optional[str] = None
    source_memory_count: Optional[int] = None
    message: str
```

File: `src/api/routes/consolidation.py` (EDIT - add endpoint)
```python
@router.post(
    "/api/v1/consolidate",
    response_model=ConsolidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger memory consolidation"
)
async def trigger_consolidation(
    request: ConsolidationRequest,
    user_id: str = Depends(get_current_user_id),
    consolidation_service: ConsolidationService = Depends(get_consolidation_service)
) -> ConsolidationResponse:
    """Consolidate memories into summary.

    Requires ≥10 episodes or ≥3 sessions to trigger.
    """
    logger.info(
        "consolidation_request",
        user_id=user_id,
        scope_type=request.scope_type,
        scope_identifier=request.scope_identifier
    )

    # Run consolidation (service checks thresholds internally)
    summary = await consolidation_service.consolidate(
        scope_type=request.scope_type,
        scope_identifier=request.scope_identifier,
        user_id=user_id
    )

    if not summary:
        return ConsolidationResponse(
            consolidation_triggered=False,
            message="Consolidation threshold not met. Need ≥10 episodes or ≥3 sessions."
        )

    logger.info(
        "consolidation_complete",
        summary_id=summary.summary_id,
        source_count=len(summary.source_memory_ids)
    )

    return ConsolidationResponse(
        consolidation_triggered=True,
        summary_id=summary.summary_id,
        summary_text=summary.summary_text,
        source_memory_count=len(summary.source_memory_ids),
        message=f"Consolidated {len(summary.source_memory_ids)} memories"
    )
```

**Tests That MUST Pass**:

1. **Unit Test**: `tests/unit/api/routes/test_consolidation.py` (NEW)
   ```python
   async def test_consolidation_endpoint_below_threshold():
       """Below threshold → no consolidation."""
       # Given: Only 2 sessions for entity
       # When: POST /api/v1/consolidate
       # Then: consolidation_triggered=False

   async def test_consolidation_endpoint_above_threshold():
       """Above threshold → consolidation happens."""
       # Given: 12 episodes for entity
       # When: POST /api/v1/consolidate
       # Then: consolidation_triggered=True, summary_id returned
   ```

2. **E2E Test**: `tests/e2e/test_scenarios.py::test_scenario_14_session_window_consolidation`
   ```bash
   poetry run pytest tests/e2e/test_scenarios.py::test_scenario_14_session_window_consolidation -xvs
   ```
   - Create 10+ chat turns about Gai Media
   - Call `/api/v1/consolidate` with scope="entity", identifier="customer_xxx"
   - Verify: `consolidation_triggered=True`, summary contains key facts

**Success Criteria**:
- [ ] `/api/v1/consolidate` endpoint implemented
- [ ] Request/Response models defined
- [ ] Threshold checking works
- [ ] Summary creation returns correct data
- [ ] Unit tests pass
- [ ] E2E Scenario 14 passes
- [ ] OpenAPI docs updated (auto via FastAPI)

**Verification Before Proceeding**:
```bash
poetry run pytest tests/e2e/test_scenarios.py::test_scenario_14_session_window_consolidation -xvs
poetry run pytest tests/e2e/test_scenarios.py -v  # No regressions
```

**Commit**: `feat(api): add consolidation endpoint (Scenario 14)`

**Status After**: 12/18 passing (67%)

---

### Phase 1 Completion Check

**Before proceeding to Phase 2, verify**:
```bash
# Must show 12 passing:
poetry run pytest tests/e2e/test_scenarios.py -v

# Must pass:
make test
make typecheck
```

**Metrics**:
- [ ] 12/18 scenarios passing (67%)
- [ ] All 198+ unit/integration tests passing
- [ ] 0 type errors
- [ ] No regressions

---

## Phase 2: Core Features → 15/18 Scenarios (83%)

> **Goal**: Implement features requiring moderate complexity.

**Time Estimate**: 12-15 hours
**Scenarios to Unlock**: #10 (validation), #11 (ontology), #18 (task completion)

---

### Milestone 2.1: Conflict Resolution ✅ COMPLETE

**Status**: ✅ Scenario 7 passing

**Completion Summary**:
- ✅ ConflictResolutionService with 4 strategies
- ✅ Same-day timestamp precision
- ✅ Memory status lifecycle
- ✅ Conflicts exposed in API responses
- ✅ 6 fundamental bugs fixed

---

### Milestone 2.2: Active Memory Validation

**Vision Principle**: Epistemic Humility - Question aged information

**Scenario**: #10 (active recall for stale facts)

**Investigation** (30 min):
1. Read Scenario 10 test - what's expected?
2. Study `src/domain/services/memory_validation_service.py` - what exists?
3. Check `SemanticMemory` table - does `last_validated_at` field exist?
4. Understand: System should prompt user to validate old memories

**Implementation Part 1: Validation Prompting** (1.5 hours):

File: `src/config/heuristics.py` (ADD)
```python
HEURISTICS = {
    # ... existing ...
    "validation": {
        "stale_threshold_days": 90,  # Prompt validation after 90 days
        "low_confidence_threshold": 0.6,  # Only if confidence dropped
    }
}
```

File: `src/domain/services/llm_reply_generator.py` (EDIT)
```python
async def _check_for_validation_needs(
    self,
    retrieved_memories: List[RetrievedMemory]
) -> List[dict]:
    """Generate validation prompts for stale memories."""
    validation_needed = []

    stale_days = get_config("validation.stale_threshold_days")
    low_conf = get_config("validation.low_confidence_threshold")

    for mem in retrieved_memories:
        if mem.memory_type != "semantic":
            continue

        days_old = (datetime.now(UTC) - mem.created_at).days

        if days_old > stale_days and mem.confidence < low_conf:
            validation_needed.append({
                "memory_id": mem.memory_id,
                "predicate": mem.predicate,
                "object_value": mem.object_value,
                "days_old": days_old
            })

            logger.info(
                "validation_prompt_needed",
                memory_id=mem.memory_id,
                days_old=days_old,
                confidence=mem.confidence
            )

    return validation_needed

async def generate(self, context: ReplyContext) -> str:
    """Generate reply with validation prompts if needed."""

    # Check for stale memories
    validation_needed = await self._check_for_validation_needs(
        context.retrieved_memories
    )

    # Build system prompt
    system_prompt = self._build_system_prompt(context)

    if validation_needed:
        system_prompt += "\n\nIMPORTANT: The following facts are old and should be validated. Ask the user to confirm:\n"
        for v in validation_needed:
            system_prompt += f"- '{v['predicate']}: {v['object_value']}' (from {v['days_old']} days ago)\n"

    # ... rest of generation ...
```

**Implementation Part 2: Validation Endpoint** (1 hour):

File: `src/api/models/validation.py` (NEW)
```python
from pydantic import BaseModel

class ValidationRequest(BaseModel):
    is_valid: bool  # True = confirm, False = invalidate

class ValidationResponse(BaseModel):
    memory_id: int
    action: str  # "validated" | "invalidated"
    new_confidence: float
    message: str
```

File: `src/api/routes/validation.py` (NEW)
```python
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

@router.post(
    "/api/v1/memories/{memory_id}/validate",
    response_model=ValidationResponse
)
async def validate_memory(
    memory_id: int,
    request: ValidationRequest,
    user_id: str = Depends(get_current_user_id),
    semantic_repo: ISemanticMemoryRepository = Depends(get_semantic_repo)
) -> ValidationResponse:
    """Validate or invalidate a memory."""

    memory = await semantic_repo.find_by_id(memory_id)
    if not memory or memory.user_id != user_id:
        raise HTTPException(404, "Memory not found")

    if request.is_valid:
        # Confirm memory is still valid
        memory.last_validated_at = datetime.now(UTC)
        memory.confidence = min(0.95, memory.confidence + 0.05)
        action = "validated"
        logger.info("memory_validated", memory_id=memory_id)
    else:
        # Mark as outdated
        memory.status = "invalidated"
        action = "invalidated"
        logger.info("memory_invalidated", memory_id=memory_id)

    await semantic_repo.update(memory)

    return ValidationResponse(
        memory_id=memory_id,
        action=action,
        new_confidence=memory.confidence,
        message=f"Memory {action}"
    )
```

**Tests That MUST Pass**:

1. **Unit Test**: `tests/unit/domain/services/test_llm_reply_generator.py`
   ```python
   async def test_validation_prompt_for_stale_memory():
       """Stale memory triggers validation prompt."""
       # Given: Memory is 100 days old, confidence 0.5
       # When: generate() called
       # Then: System prompt includes validation question
   ```

2. **Unit Test**: `tests/unit/api/routes/test_validation.py`
   ```python
   async def test_validate_memory_confirmed():
       """Valid=True updates last_validated_at."""
       # When: POST /memories/123/validate with is_valid=true
       # Then: last_validated_at updated, confidence boosted

   async def test_validate_memory_invalidated():
       """Valid=False marks as invalidated."""
       # When: POST /memories/123/validate with is_valid=false
       # Then: status='invalidated'
   ```

3. **E2E Test**: `tests/e2e/test_scenarios.py::test_scenario_10_active_recall_for_stale_facts`
   ```bash
   poetry run pytest tests/e2e/test_scenarios.py::test_scenario_10_active_recall_for_stale_facts -xvs
   ```
   - Create memory 95 days ago (mock `created_at`)
   - Query triggers retrieval
   - Response includes validation prompt
   - Call `/memories/{id}/validate` to confirm/invalidate

**Success Criteria**:
- [ ] Validation prompt generation works
- [ ] Heuristic configuration added
- [ ] `/api/v1/memories/{id}/validate` endpoint works
- [ ] Unit tests pass
- [ ] E2E Scenario 10 passes

**Verification Before Proceeding**:
```bash
poetry run pytest tests/e2e/test_scenarios.py::test_scenario_10_active_recall_for_stale_facts -xvs
poetry run pytest tests/e2e/test_scenarios.py -v
```

**Commit**: `feat(validation): add active memory validation (Scenario 10)`

**Status After**: 13/18 passing (72%)

---

### Milestone 2.3: Multi-Hop Ontology Traversal

**Vision Principle**: Deep Business Understanding - Cross-object reasoning

**Scenario**: #11 (cross-object reasoning)

**Investigation** (1 hour):
1. Read `tests/e2e/test_scenarios.py` Scenario 11 - what query is being tested?
2. Study `src/domain/entities/domain_ontology.py` - what schema?
3. Check database - does `domain_ontology` table have relationships?
4. Example: Customer → Sales Order → Work Order → Invoice (3 hops)

**Implementation** (3-4 hours):

File: `src/domain/services/ontology_traversal_service.py` (NEW)
```python
from typing import List, Dict
from dataclasses import dataclass
from collections import deque

@dataclass
class TraversalStep:
    from_table: str
    to_table: str
    join_condition: str

@dataclass
class TraversalPath:
    steps: List[TraversalStep]
    total_hops: int

class OntologyTraversalService:
    """Multi-hop ontology traversal for cross-object reasoning.

    Example: Customer → SalesOrder → WorkOrder → Invoice
    """

    def __init__(
        self,
        ontology_repo: IDomainOntologyRepository,
        domain_db_repo: IDomainDatabaseRepository
    ):
        self.ontology_repo = ontology_repo
        self.domain_db_repo = domain_db_repo

    async def traverse(
        self,
        start_entity_id: str,
        start_entity_type: str,
        target_entity_types: List[str],
        max_hops: int = 3
    ) -> Dict[str, List[DomainFact]]:
        """Traverse ontology to fetch related entities."""

        results = {}

        for target_type in target_entity_types:
            # Find path via BFS
            path = await self._find_path(
                start_entity_type,
                target_type,
                max_hops
            )

            if not path:
                logger.warning(
                    "no_path_found",
                    from_type=start_entity_type,
                    to_type=target_type
                )
                results[target_type] = []
                continue

            # Execute multi-hop query
            facts = await self._execute_traversal(start_entity_id, path)
            results[target_type] = facts

            logger.info(
                "ontology_traversal_complete",
                target_type=target_type,
                facts_found=len(facts),
                hops=path.total_hops
            )

        return results

    async def _find_path(
        self,
        from_type: str,
        to_type: str,
        max_hops: int
    ) -> Optional[TraversalPath]:
        """Find shortest path via BFS."""

        if from_type == to_type:
            return TraversalPath(steps=[], total_hops=0)

        # Fetch ontology relationships
        all_relations = await self.ontology_repo.get_all_relationships()

        # Build adjacency graph
        graph: Dict[str, List[Tuple[str, DomainOntology]]] = {}
        for rel in all_relations:
            if rel.from_entity_type not in graph:
                graph[rel.from_entity_type] = []
            graph[rel.from_entity_type].append((rel.to_entity_type, rel))

        # BFS
        queue = deque([(from_type, [])])
        visited = {from_type}

        while queue:
            current_type, path = queue.popleft()

            if len(path) >= max_hops:
                continue

            if current_type not in graph:
                continue

            for next_type, relation in graph[current_type]:
                if next_type in visited:
                    continue

                new_path = path + [TraversalStep(
                    from_table=relation.from_table,
                    to_table=relation.to_table,
                    join_condition=relation.join_condition
                )]

                if next_type == to_type:
                    return TraversalPath(
                        steps=new_path,
                        total_hops=len(new_path)
                    )

                visited.add(next_type)
                queue.append((next_type, new_path))

        return None

    async def _execute_traversal(
        self,
        start_entity_id: str,
        path: TraversalPath
    ) -> List[DomainFact]:
        """Execute multi-hop SQL query."""

        if not path.steps:
            return []

        # Build SQL with JOINs
        # Example: SELECT * FROM customers c
        #          JOIN sales_orders so ON c.customer_id = so.customer_id
        #          JOIN work_orders wo ON so.so_id = wo.so_id
        #          WHERE c.customer_id = :start_id

        from_table = path.steps[0].from_table
        query_parts = [f"SELECT * FROM domain.{from_table} t0"]

        for i, step in enumerate(path.steps):
            alias_from = f"t{i}"
            alias_to = f"t{i+1}"
            query_parts.append(
                f"JOIN domain.{step.to_table} {alias_to} ON {step.join_condition}"
            )

        query_parts.append(f"WHERE t0.{from_table}_id = :start_id")

        query = "\n".join(query_parts)

        rows = await self.domain_db_repo.execute_raw_query(
            query,
            {"start_id": start_entity_id}
        )

        # Convert to DomainFacts
        facts = []
        for row in rows:
            facts.append(DomainFact(
                fact_type="multi_hop_traversal",
                entity_id=start_entity_id,
                content=f"Related {path.steps[-1].to_table}",
                metadata=dict(row),
                source_table=path.steps[-1].to_table,
                retrieved_at=datetime.now(UTC)
            ))

        return facts
```

**Tests That MUST Pass**:

1. **Unit Test**: `tests/unit/domain/services/test_ontology_traversal_service.py`
   ```python
   async def test_find_path_single_hop():
       """Customer → SalesOrder (1 hop)."""
       # Given: Ontology has customer→sales_order relationship
       # When: _find_path("customer", "sales_order", max_hops=3)
       # Then: Path with 1 step returned

   async def test_find_path_multi_hop():
       """Customer → SalesOrder → Invoice (2 hops)."""
       # Given: customer→sales_order, sales_order→invoice
       # When: _find_path("customer", "invoice", max_hops=3)
       # Then: Path with 2 steps returned

   async def test_find_path_no_route():
       """No path available."""
       # Given: No relationship to target
       # When: _find_path("customer", "orphan_entity", max_hops=3)
       # Then: None returned
   ```

2. **Integration Test**: `tests/integration/domain/services/test_ontology_traversal_integration.py`
   ```python
   async def test_execute_traversal_real_db():
       """Execute multi-hop query on real DB."""
       # Given: Seeded customer, sales_order, work_order, invoice
       # When: traverse(customer_id, ["work_order", "invoice"])
       # Then: Facts returned with work_order and invoice data
   ```

3. **E2E Test**: `tests/e2e/test_scenarios.py::test_scenario_11_cross_object_reasoning`
   ```bash
   poetry run pytest tests/e2e/test_scenarios.py::test_scenario_11_cross_object_reasoning -xvs
   ```
   - User asks: "Can we invoice Gai Media?"
   - System traverses: Customer → Sales Order → Work Order → Invoice
   - Response includes: Work order status, invoice status

**Success Criteria**:
- [ ] OntologyTraversalService implemented
- [ ] BFS path finding works
- [ ] Multi-hop SQL generation correct
- [ ] Unit tests pass
- [ ] Integration test passes
- [ ] E2E Scenario 11 passes

**Verification Before Proceeding**:
```bash
poetry run pytest tests/e2e/test_scenarios.py::test_scenario_11_cross_object_reasoning -xvs
poetry run pytest tests/e2e/test_scenarios.py -v
```

**Commit**: `feat(ontology): add multi-hop traversal (Scenario 11)`

**Status After**: 14/18 passing (78%)

---

### Milestone 2.4: Task Completion Flow

**Vision Principle**: Domain Augmentation + Semantic Extraction

**Scenario**: #18 (task completion via conversation)

**Investigation** (30 min):
1. Read Scenario 18 test - what's expected?
2. Should we actually update `domain.tasks` or return SQL patch?
3. Check if task completion summary should be stored as semantic memory

**Implementation** (2 hours):

File: `src/api/models/tasks.py` (NEW)
```python
from pydantic import BaseModel

class TaskCompletionRequest(BaseModel):
    summary: str

class TaskCompletionResponse(BaseModel):
    task_id: str
    status: str  # "completed"
    semantic_memory_id: int
    message: str
```

File: `src/api/routes/tasks.py` (NEW)
```python
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

@router.post(
    "/api/v1/tasks/{task_id}/complete",
    response_model=TaskCompletionResponse
)
async def complete_task(
    task_id: str,
    request: TaskCompletionRequest,
    user_id: str = Depends(get_current_user_id),
    extract_semantics: ExtractSemanticsUseCase = Depends(get_extract_semantics_use_case)
) -> TaskCompletionResponse:
    """Mark task complete and store summary as semantic memory."""

    logger.info(
        "task_completion_request",
        task_id=task_id,
        user_id=user_id,
        summary_length=len(request.summary)
    )

    # Store completion summary as semantic memory
    # Subject: task entity, Predicate: completion_summary, Object: summary text
    triple = SemanticTriple(
        subject_entity_id=f"task_{task_id}",
        predicate="completion_summary",
        object_value=request.summary,
        confidence=0.9,
        predicate_type="observation",
        metadata={
            "source_type": "task_completion",
            "completed_at": datetime.now(UTC).isoformat()
        }
    )

    # Create semantic memory
    memory = await extract_semantics.create_memory_from_triple(
        triple=triple,
        user_id=user_id,
        source_event_id=None
    )

    logger.info(
        "task_completed",
        task_id=task_id,
        semantic_memory_id=memory.memory_id
    )

    return TaskCompletionResponse(
        task_id=task_id,
        status="completed",
        semantic_memory_id=memory.memory_id,
        message=f"Task {task_id} completion stored as memory"
    )
```

**Tests That MUST Pass**:

1. **Unit Test**: `tests/unit/api/routes/test_tasks.py`
   ```python
   async def test_complete_task_creates_semantic_memory():
       """Task completion stores semantic memory."""
       # When: POST /tasks/123/complete with summary
       # Then: Semantic memory created
       # Then: subject=task_123, predicate=completion_summary
   ```

2. **E2E Test**: `tests/e2e/test_scenarios.py::test_scenario_18_task_completion_via_conversation`
   ```bash
   poetry run pytest tests/e2e/test_scenarios.py::test_scenario_18_task_completion_via_conversation -xvs
   ```
   - User says: "I completed task X. Summary: ..."
   - System extracts task_id and summary
   - Calls `/tasks/{id}/complete`
   - Semantic memory created
   - Future queries about task X retrieve completion summary

**Success Criteria**:
- [ ] `/api/v1/tasks/{id}/complete` endpoint
- [ ] Semantic memory created with completion summary
- [ ] Unit test passes
- [ ] E2E Scenario 18 passes

**Verification Before Proceeding**:
```bash
poetry run pytest tests/e2e/test_scenarios.py::test_scenario_18_task_completion_via_conversation -xvs
poetry run pytest tests/e2e/test_scenarios.py -v
```

**Commit**: `feat(api): add task completion endpoint (Scenario 18)`

**Status After**: 15/18 passing (83%)

---

### Phase 2 Completion Check

**Before proceeding to Phase 3, verify**:
```bash
# Must show 15 passing:
poetry run pytest tests/e2e/test_scenarios.py -v

# Must pass:
make test
make typecheck
make check-all
```

**Metrics**:
- [ ] 15/18 scenarios passing (83%)
- [ ] All unit/integration tests passing
- [ ] 0 type errors, 0 lint errors
- [ ] No regressions

---

## Phase 3: Advanced Features → 18/18 Scenarios (100%)

> **Goal**: Implement complex features requiring significant LLM integration.

**Time Estimate**: 12-16 hours
**Scenarios to Unlock**: #8 (multilingual), #13 (PII), #16 (procedural)

---

### Milestone 3.1: PII Detection and Redaction

**Vision Principle**: Privacy - Never store sensitive information

**Scenario**: #13 (PII guardrail memory)

**Investigation** (30 min):
1. Read Scenario 13 test
2. Check `src/domain/services/pii_redaction_service.py` - skeleton exists?
3. What PII types: SSN, credit card, email, phone
4. Decision: Regex-based (fast, deterministic)

**Implementation** (2-3 hours):

File: `src/domain/services/pii_redaction_service.py` (IMPLEMENT)
```python
import re
from typing import List
from dataclasses import dataclass

@dataclass
class PIIMatch:
    type: str  # "ssn" | "credit_card" | "email" | "phone"
    start: int
    end: int
    text: str
    confidence: float

class PIIRedactionService:
    """Detect and redact PII from chat messages."""

    SSN_PATTERN = r'\b\d{3}-\d{2}-\d{4}\b'
    CREDIT_CARD_PATTERN = r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    PHONE_PATTERN = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'

    async def detect_pii(self, text: str) -> List[PIIMatch]:
        """Detect PII in text."""
        matches = []

        # SSN
        for match in re.finditer(self.SSN_PATTERN, text):
            matches.append(PIIMatch(
                type="ssn",
                start=match.start(),
                end=match.end(),
                text=match.group(),
                confidence=0.95
            ))

        # Credit Card (with Luhn validation)
        for match in re.finditer(self.CREDIT_CARD_PATTERN, text):
            if self._validate_luhn(match.group()):
                matches.append(PIIMatch(
                    type="credit_card",
                    start=match.start(),
                    end=match.end(),
                    text=match.group(),
                    confidence=0.9
                ))

        # Email
        for match in re.finditer(self.EMAIL_PATTERN, text):
            matches.append(PIIMatch(
                type="email",
                start=match.start(),
                end=match.end(),
                text=match.group(),
                confidence=0.85
            ))

        # Phone
        for match in re.finditer(self.PHONE_PATTERN, text):
            matches.append(PIIMatch(
                type="phone",
                start=match.start(),
                end=match.end(),
                text=match.group(),
                confidence=0.8
            ))

        logger.info("pii_detection_complete", pii_count=len(matches))
        return matches

    def _validate_luhn(self, number: str) -> bool:
        """Validate credit card with Luhn algorithm."""
        digits = [int(d) for d in number if d.isdigit()]
        checksum = 0
        for i, d in enumerate(reversed(digits)):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        return checksum % 10 == 0

    async def redact(self, text: str, matches: List[PIIMatch]) -> str:
        """Replace PII with [REDACTED-{type}]."""
        result = text
        for match in sorted(matches, key=lambda m: m.start, reverse=True):
            replacement = f"[REDACTED-{match.type.upper()}]"
            result = result[:match.start] + replacement + result[match.end:]

        logger.info("pii_redacted", redaction_count=len(matches))
        return result
```

File: `src/application/use_cases/process_chat_message.py` (EDIT - add PII check)
```python
# Before storing message:
pii_matches = await self.pii_service.detect_pii(input_dto.content)

if pii_matches:
    # Redact before storing
    redacted_content = await self.pii_service.redact(
        input_dto.content,
        pii_matches
    )

    # Store policy memory
    await self.extract_semantics.create_memory_from_statement(
        subject_entity_id="system",
        predicate="pii_policy",
        object_value={
            "policy": "never_store_pii",
            "detected_types": [m.type for m in pii_matches],
            "redacted_at": datetime.now(UTC).isoformat()
        },
        user_id=input_dto.user_id,
        source_type="pii_redaction"
    )

    content_to_store = redacted_content
else:
    content_to_store = input_dto.content
```

**Tests That MUST Pass**:

1. **Unit Test**: `tests/unit/domain/services/test_pii_redaction_service.py`
   ```python
   async def test_detect_ssn():
       """Detect SSN pattern."""
       text = "My SSN is 123-45-6789"
       matches = await pii_service.detect_pii(text)
       assert len(matches) == 1
       assert matches[0].type == "ssn"

   async def test_redact_pii():
       """Redact PII from text."""
       text = "My SSN is 123-45-6789"
       matches = [PIIMatch(type="ssn", start=10, end=21, text="123-45-6789", confidence=0.95)]
       result = await pii_service.redact(text, matches)
       assert result == "My SSN is [REDACTED-SSN]"
   ```

2. **E2E Test**: `tests/e2e/test_scenarios.py::test_scenario_13_pii_guardrail_memory`
   ```bash
   poetry run pytest tests/e2e/test_scenarios.py::test_scenario_13_pii_guardrail_memory -xvs
   ```
   - User mentions SSN in message
   - System detects PII
   - ChatEvent stored with redacted content
   - Policy memory created
   - Response acknowledges PII was detected and redacted

**Success Criteria**:
- [ ] PII detection works (SSN, CC, email, phone)
- [ ] Luhn validation for credit cards
- [ ] Redaction works correctly
- [ ] Policy memory created
- [ ] Unit tests pass
- [ ] E2E Scenario 13 passes

**Verification Before Proceeding**:
```bash
poetry run pytest tests/e2e/test_scenarios.py::test_scenario_13_pii_guardrail_memory -xvs
poetry run pytest tests/e2e/test_scenarios.py -v
```

**Commit**: `feat(pii): implement PII detection and redaction (Scenario 13)`

**Status After**: 16/18 passing (89%)

---

### Milestone 3.2: Multilingual NER

**Vision Principle**: Identity Across Time - Learn aliases in any language

**Scenario**: #8 (multilingual alias handling)

**Investigation** (30 min):
1. Read Scenario 8 test
2. Current `SimpleMentionExtractor` - ASCII-biased?
3. Decision: LLM-based extraction (handles any language)
4. Add configuration toggle

**Implementation** (3-4 hours):

File: `src/domain/services/multilingual_mention_extractor.py` (NEW)
```python
from typing import List, Optional
import json

class MultilingualMentionExtractor:
    """Extract entity mentions from multilingual text using LLM."""

    def __init__(self, llm_service: ILLMService):
        self.llm_service = llm_service

    async def extract_mentions(
        self,
        text: str,
        expected_entity_types: Optional[List[str]] = None
    ) -> List[EntityMention]:
        """Extract mentions (any language)."""

        prompt = f"""
Extract entity mentions from this text. The text may be in any language.

Text: "{text}"

Entity types to look for:
- customer: Customer/company names
- invoice: Invoice numbers (INV-1234)
- sales_order: Sales order numbers (SO-5678)
- work_order: Work order numbers (WO-9012)

Return as JSON array:
[
  {{"mention": "Gai Media", "type": "customer"}},
  {{"mention": "Gai 媒体", "type": "customer"}}
]

If no entities found, return: []
"""

        response = await self.llm_service.complete(prompt)

        try:
            mentions_data = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("llm_mention_extraction_failed", response=response)
            return []

        mentions = []
        for data in mentions_data:
            mentions.append(EntityMention(
                text=data["mention"],
                entity_type=data["type"],
                start_pos=0,  # LLM doesn't give positions
                end_pos=len(data["mention"])
            ))

        logger.info(
            "multilingual_mentions_extracted",
            mention_count=len(mentions)
        )

        return mentions
```

File: `src/config/heuristics.py` (ADD)
```python
HEURISTICS = {
    # ... existing ...
    "entity_resolution": {
        # ... existing ...
        "use_multilingual_extraction": False,  # Toggle
    }
}
```

File: `src/application/use_cases/resolve_entities.py` (EDIT)
```python
# Conditional mention extraction
if get_config("entity_resolution.use_multilingual_extraction"):
    mentions = await self.multilingual_extractor.extract_mentions(content)
else:
    mentions = await self.simple_extractor.extract_mentions(content)
```

**Tests That MUST Pass**:

1. **Unit Test**: `tests/unit/domain/services/test_multilingual_mention_extractor.py`
   ```python
   async def test_extract_english_mention(mock_llm):
       """Extract English entity."""
       # Given: "Contact Gai Media about invoice"
       # When: extract_mentions()
       # Then: [EntityMention("Gai Media", "customer")]

   async def test_extract_chinese_mention(mock_llm):
       """Extract Chinese entity."""
       # Given: "联系 Gai 媒体 关于发票"
       # When: extract_mentions()
       # Then: [EntityMention("Gai 媒体", "customer")]
   ```

2. **E2E Test**: `tests/e2e/test_scenarios.py::test_scenario_08_multilingual_alias_handling`
   ```bash
   poetry run pytest tests/e2e/test_scenarios.py::test_scenario_08_multilingual_alias_handling -xvs
   ```
   - Turn 1: "Gai Media" (English) → resolves to customer
   - Turn 2: "Gai 媒体" (Chinese) → resolves to same customer
   - Alias learned for Chinese name

**Success Criteria**:
- [ ] MultilingualMentionExtractor implemented
- [ ] LLM-based extraction works
- [ ] Configuration toggle added
- [ ] Unit tests pass
- [ ] E2E Scenario 8 passes

**Verification Before Proceeding**:
```bash
poetry run pytest tests/e2e/test_scenarios.py::test_scenario_08_multilingual_alias_handling -xvs
poetry run pytest tests/e2e/test_scenarios.py -v
```

**Commit**: `feat(entity-resolution): add multilingual mention extraction (Scenario 8)`

**Status After**: 17/18 passing (94%)

---

### Milestone 3.3: Procedural Memory Extraction

**Vision Principle**: Proactive Intelligence - Learn trigger-action patterns

**Scenario**: #16 (reminder creation from intent)

**Investigation** (1 hour):
1. Read Scenario 16 test
2. Study `ProceduralMemory` table schema
3. Example: "If invoice is 3 days before due, remind me"
4. Understand: Trigger (condition) + Action (what to do)

**Implementation Part 1: Policy Detection** (2-3 hours):

File: `src/domain/services/procedural_extraction_service.py` (NEW)
```python
from typing import Optional
from dataclasses import dataclass
import json

@dataclass
class ProceduralPattern:
    trigger_pattern: str
    trigger_features: dict
    action_heuristic: str
    action_structure: dict
    confidence: float

class ProceduralExtractionService:
    """Extract procedural memories from policy statements."""

    def __init__(self, llm_service: ILLMService):
        self.llm_service = llm_service

    async def extract_procedural_memory(
        self,
        content: str,
        resolved_entities: List[ResolvedEntity]
    ) -> Optional[ProceduralPattern]:
        """Extract trigger-action pattern if policy detected."""

        # Step 1: Detect policy
        is_policy = await self._detect_policy_statement(content)
        if not is_policy:
            return None

        # Step 2: Extract trigger and action
        pattern = await self._extract_trigger_action(content, resolved_entities)

        logger.info(
            "procedural_memory_extracted",
            trigger_pattern=pattern.trigger_pattern
        )

        return pattern

    async def _detect_policy_statement(self, content: str) -> bool:
        """Detect if this is a policy/rule statement."""

        prompt = f"""
Does this express a policy, rule, or trigger-action pattern?

Examples of policy statements:
- "If invoice is open 3 days before due, remind me"
- "When delivery is mentioned, check invoices"

Examples of NON-policy statements:
- "What is the invoice status?" (question)
- "Gai Media prefers Friday" (preference)

Statement: "{content}"

Answer: yes or no
"""

        response = await self.llm_service.complete(prompt)
        return "yes" in response.lower()

    async def _extract_trigger_action(
        self,
        content: str,
        resolved_entities: List[ResolvedEntity]
    ) -> ProceduralPattern:
        """Extract trigger and action from policy."""

        entity_types = [e.entity_type for e in resolved_entities]

        prompt = f"""
Extract trigger-action pattern from this policy.

Statement: "{content}"
Entities: {entity_types}

Extract as JSON:
{{
  "trigger_pattern": "when does this apply?",
  "trigger_intent": "payment_reminder / status_check / etc",
  "trigger_topics": ["invoices", "due_dates"],
  "action_heuristic": "what should happen?",
  "action_type": "proactive_notice / query / validation"
}}
"""

        response = await self.llm_service.complete(prompt)
        data = json.loads(response)

        return ProceduralPattern(
            trigger_pattern=data["trigger_pattern"],
            trigger_features={
                "intent": data["trigger_intent"],
                "topics": data["trigger_topics"]
            },
            action_heuristic=data["action_heuristic"],
            action_structure={
                "action_type": data["action_type"]
            },
            confidence=0.7
        )
```

**Implementation Part 2: Proactive Trigger Checking** (1-2 hours):

File: `src/domain/services/proactive_notice_service.py` (NEW)
```python
from typing import List
from dataclasses import dataclass

@dataclass
class ProactiveNotice:
    trigger_id: int
    notice_text: str
    priority: str

class ProactiveNoticeService:
    """Check for procedural memory triggers."""

    def __init__(
        self,
        procedural_repo: IProceduralMemoryRepository,
        embedding_service: IEmbeddingService
    ):
        self.procedural_repo = procedural_repo
        self.embedding_service = embedding_service

    async def check_triggers(
        self,
        query_text: str,
        domain_facts: List[DomainFact],
        user_id: str
    ) -> List[ProactiveNotice]:
        """Check if any procedural memories trigger."""

        # Retrieve relevant procedural memories
        query_embedding = await self.embedding_service.embed(query_text)

        procedural_memories = await self.procedural_repo.search_by_similarity(
            embedding=query_embedding,
            user_id=user_id,
            limit=10
        )

        notices = []

        for proc_mem in procedural_memories:
            # Check if trigger matches
            if await self._evaluate_trigger(proc_mem, query_text, domain_facts):
                notice = self._generate_notice(proc_mem, domain_facts)
                notices.append(notice)

                logger.info(
                    "proactive_trigger_matched",
                    trigger_id=proc_mem.memory_id,
                    trigger_pattern=proc_mem.trigger_pattern
                )

        return notices

    async def _evaluate_trigger(
        self,
        proc_mem: ProceduralMemory,
        query_text: str,
        domain_facts: List[DomainFact]
    ) -> bool:
        """Evaluate if trigger conditions met."""

        # Simple keyword matching for Phase 1
        trigger_features = proc_mem.trigger_features
        intent = trigger_features.get("intent", "")

        if intent and intent in query_text.lower():
            return True

        return False

    def _generate_notice(
        self,
        proc_mem: ProceduralMemory,
        domain_facts: List[DomainFact]
    ) -> ProactiveNotice:
        """Generate notice text."""

        return ProactiveNotice(
            trigger_id=proc_mem.memory_id,
            notice_text=proc_mem.action_heuristic,
            priority="medium"
        )
```

**Tests That MUST Pass**:

1. **Unit Test**: `tests/unit/domain/services/test_procedural_extraction_service.py`
   ```python
   async def test_detect_policy_statement(mock_llm):
       """Detect policy vs non-policy."""
       # "If invoice is 3 days before due, remind me" → True
       # "What is the invoice status?" → False

   async def test_extract_trigger_action(mock_llm):
       """Extract trigger and action from policy."""
       # Given: "If invoice is 3 days before due, remind me"
       # Then: trigger_pattern includes "3 days before due"
       # Then: action_heuristic includes "remind"
   ```

2. **E2E Test**: `tests/e2e/test_scenarios.py::test_scenario_16_reminder_creation_from_intent`
   ```bash
   poetry run pytest tests/e2e/test_scenarios.py::test_scenario_16_reminder_creation_from_intent -xvs
   ```
   - Turn 1: User states policy "If invoice 3 days before due, remind me"
   - System extracts procedural memory
   - Turn 2: User queries about invoices
   - System checks if any are 3 days before due
   - Response includes proactive reminder

**Success Criteria**:
- [ ] ProceduralExtractionService implemented
- [ ] Policy detection works
- [ ] Trigger-action extraction works
- [ ] ProactiveNoticeService implemented
- [ ] Trigger evaluation works
- [ ] Unit tests pass
- [ ] E2E Scenario 16 passes

**Verification Before Proceeding**:
```bash
poetry run pytest tests/e2e/test_scenarios.py::test_scenario_16_reminder_creation_from_intent -xvs
poetry run pytest tests/e2e/test_scenarios.py -v
```

**Commit**: `feat(procedural): add procedural memory extraction and proactive triggers (Scenario 16)`

**Status After**: 18/18 passing (100%) 🎉

---

### Phase 3 Completion Check

**Verify 100% Coverage**:
```bash
# MUST show 18 passed:
poetry run pytest tests/e2e/test_scenarios.py -v

# MUST pass:
make test
make typecheck
make check-all
```

**Metrics**:
- [ ] 18/18 E2E scenarios passing (100%)
- [ ] All unit/integration tests passing
- [ ] 0 type errors
- [ ] 0 lint errors
- [ ] >85% code coverage

---

## Final Verification

### Comprehensive Test Run

```bash
# Run EVERYTHING:
make test              # All unit + integration tests
make typecheck         # Type checking
poetry run pytest tests/e2e/test_scenarios.py -v  # All E2E scenarios

# Expected: ALL PASS
```

**If any fail**: Debug and fix before declaring 100% complete.

---

## Success Metrics

### Quantitative
- ✅ 18/18 E2E scenarios passing (100%)
- ✅ 200+ unit/integration tests passing
- ✅ >85% code coverage (domain)
- ✅ 0 lint errors
- ✅ 0 type errors

### Qualitative
- ✅ Production-ready code quality
- ✅ All vision principles demonstrated
- ✅ Comprehensive test coverage
- ✅ Clean hexagonal architecture maintained
- ✅ Explainable, maintainable codebase

---

## Philosophy Reminders

**When you're tempted to rush**:
> "Building the wrong thing quickly is worse than building the right thing slowly."

**When a test fails**:
> "Don't just make tests pass. Understand WHY they're failing."

**When uncertain about approach**:
> "It is ALWAYS better to ask than to assume."

**When tempted to cut corners**:
> "Complete each piece fully before moving to the next. Progress should be: 100% → 100% → 100%"

**Before marking any task complete**:
> "Implementation matches design, all tests pass, edge cases handled, no regressions."

---

**This roadmap is your guide. Follow it with discipline, thoughtfulness, and pride in craft.**

**Build something exceptional.** 🚀
