# Roadmap to 100% Scenario Coverage

**Philosophy**: Incremental Perfection - Complete each piece 100% before moving to the next

> "Progress should be: 100% → 100% → 100%, not 60% → 60% → 60%"

**Current Status**: 4/18 scenarios passing (22.2%)
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
- ✅ Documentation updated
- ✅ Quality checks pass (lint, typecheck, coverage)

### 3. Root Cause Solutions
Fix root causes, not symptoms:
- Understand WHY the gap exists
- Solve the problem completely
- Don't create band-aids

### 4. Vision-Driven
Every feature serves explicit vision principles:
- Perfect recall of relevant context
- Deep business understanding
- Adaptive learning
- Epistemic humility
- Explainable reasoning
- Continuous improvement

---

## Phase 0: Foundation Check (2-3 hours)

> **Before building new features, ensure current foundation is solid.**

### Task 0.1: Fix Failing Unit Tests (1-2 hours)

**Vision Principle**: Quality Over Speed - Never build on broken foundation

**Current Issue**: 9/130 tests failing
- 8 in `test_memory_validation_service.py` (decay formula mismatch)
- 1 in `test_semantic_extraction_service.py`

**Investigation Steps**:
1. Read failing test output carefully
2. Read `docs/design/LIFECYCLE_DESIGN.md` for decay formula spec
3. Compare implementation in `memory_validation_service.py` with spec
4. Determine if test or implementation is wrong

**Implementation**:
- If implementation wrong: Update to match LIFECYCLE_DESIGN.md
- If test wrong: Update test expectations
- Add regression tests for edge cases (days=0, days=90, never validated)

**Completion Criteria**:
- [ ] All 130 tests passing
- [ ] `make test` succeeds
- [ ] `make typecheck` succeeds
- [ ] Decay formula documented in code comments

**Time Estimate**: 1-2 hours

---

### Task 0.2: Verify 4 Passing E2E Scenarios (30 min)

**Purpose**: Ensure current passing tests are stable

**Actions**:
```bash
poetry run pytest tests/e2e/test_scenarios.py::test_scenario_01_overdue_invoice_with_preference_recall \
  tests/e2e/test_scenarios.py::test_scenario_04_net_terms_learning_from_conversation \
  tests/e2e/test_scenarios.py::test_scenario_05_partial_payments_and_balance \
  tests/e2e/test_scenarios.py::test_scenario_09_cold_start_grounding_to_db -v
```

**Success Criteria**:
- [ ] All 4 tests pass consistently
- [ ] No flaky behavior
- [ ] Logs show expected pipeline flow

**If any fail**: Fix before proceeding. Don't build on unstable foundation.

---

## Phase 1: Quick Wins (12-16 hours) → 11/18 Scenarios (61%)

> **Goal**: Unblock scenarios with minimal implementation gaps. Focus on features where infrastructure exists.

### Milestone 1.1: Domain Table Queries (3-4 hours) → +2 scenarios

**Scenarios Unblocked**: #2 (work orders), #6 (tasks)

**Vision Principles**:
- Deep Business Understanding (ontology-awareness)
- Dual Truth (DB as correspondence truth)

---

#### Task 1.1.1: Add Work Order Queries (1.5-2 hours)

**Investigation** (30 min):
1. Read domain schema: What fields exist in `domain.work_orders`?
   ```sql
   \d domain.work_orders
   ```
2. Study existing pattern: How does `DomainAugmentationService` handle invoices?
   - File: `src/domain/services/domain_augmentation_service.py`
   - Look for `_get_entity_info()` method
3. Check relationships: How do work_orders join to sales_orders?
   - Foreign key: `wo.so_id → so.so_id`
4. Read test: What does Scenario 2 expect?
   - File: `tests/e2e/test_scenarios.py` lines ~150-200

**Implementation** (45 min):
```python
# In src/domain/services/domain_augmentation_service.py

# Add to _get_entity_info()
elif entity_type == "work_order":
    return EntityInfo(
        table="domain.work_orders",
        id_field="wo_id",
        name_field="wo_number",
        join_from="sales_orders",  # work_orders.so_id → sales_orders.so_id
        related_tables=["tasks"],
        typical_queries=[
            "work_order_status",
            "technician_assignment",
            "completion_date"
        ]
    )
```

**Testing** (45 min):
1. Unit test: `test_domain_augmentation_work_order_query.py`
   - Given: work_order entity resolved
   - When: domain augmentation runs
   - Then: work_order facts returned with status, technician, dates

2. Integration test: Real DB query
   - Seed: Create work_order in domain.work_orders
   - Query: Via DomainAugmentationService
   - Assert: Correct joins, fields populated

3. E2E test: Unskip Scenario 2
   ```bash
   poetry run pytest tests/e2e/test_scenarios.py::test_scenario_02_work_order_rescheduling -v
   ```

**Completion Criteria**:
- [ ] EntityInfo mapping added for "work_order"
- [ ] Unit tests pass (mocked repository)
- [ ] Integration tests pass (real DB)
- [ ] E2E Scenario 2 passes
- [ ] No regressions in existing tests
- [ ] Code follows established patterns
- [ ] Structured logging added

**Commit**: `feat(domain-augmentation): add work order query support for Scenario 2`

---

#### Task 1.1.2: Add Task Queries (1.5-2 hours)

**Investigation** (30 min):
1. Read domain schema: `domain.tasks` fields
2. Check relationships: `tasks.customer_id → customers.customer_id`
3. Understand SLA breach logic: What defines a breach?
   - Read Scenario 6 test expectations
   - SLA = 7 days? 14 days? (Check test or add heuristic)

**Implementation** (45 min):
```python
# In src/domain/services/domain_augmentation_service.py

elif entity_type == "task":
    return EntityInfo(
        table="domain.tasks",
        id_field="task_id",
        name_field="title",
        join_from="customers",
        related_tables=[],
        typical_queries=[
            "task_status",
            "assigned_to",
            "created_date",
            "sla_info"
        ]
    )

# Add SLA breach detection in _augment_entity_facts()
def _calculate_task_risk(task: dict) -> dict:
    """Calculate SLA breach risk for task."""
    created_at = task["created_at"]
    age_days = (datetime.now(UTC) - created_at).days
    sla_threshold = get_config("tasks.sla_days")  # e.g., 7 days

    risk_metadata = {"age_days": age_days}
    if age_days > sla_threshold:
        risk_metadata["risk_level"] = "high"
        risk_metadata["days_overdue"] = age_days - sla_threshold
        risk_metadata["sla_breach"] = True
    elif age_days > sla_threshold * 0.8:
        risk_metadata["risk_level"] = "medium"
        risk_metadata["sla_breach"] = False
    else:
        risk_metadata["risk_level"] = "low"
        risk_metadata["sla_breach"] = False

    return risk_metadata
```

**Configuration** (add to `src/config/heuristics.py`):
```python
HEURISTICS = {
    # ... existing ...
    "tasks": {
        "sla_days": 7,  # Default SLA for tasks
        "medium_risk_threshold": 0.8,  # 80% of SLA
    }
}
```

**Testing** (45 min):
1. Unit test: SLA risk calculation
   - Test: 0 days old → low risk
   - Test: 6 days old → medium risk
   - Test: 8 days old → high risk, 1 day overdue

2. Integration test: Task query with risk tagging

3. E2E test: Unskip Scenario 6

**Completion Criteria**:
- [ ] EntityInfo mapping for "task"
- [ ] Risk calculation logic with heuristic config
- [ ] Unit tests for risk calculation
- [ ] Integration tests for task queries
- [ ] E2E Scenario 6 passes
- [ ] Heuristic documented in HEURISTICS_CALIBRATION.md

**Commit**: `feat(domain-augmentation): add task queries with SLA breach detection for Scenario 6`

---

### Milestone 1.2: API Endpoint Exposure (4-6 hours) → +3 scenarios

**Scenarios Unblocked**: #3 (disambiguation), #14 (consolidation), #15 (explainability)

**Vision Principles**:
- Epistemic Humility (disambiguation shows uncertainty)
- Graceful Forgetting (consolidation)
- Explainable Reasoning (provenance)

---

#### Task 1.2.1: Disambiguation Flow API (1.5-2 hours)

**Investigation** (30 min):
1. Current behavior: What happens when `AmbiguousEntityError` is raised?
   - File: `src/api/routes/chat.py` lines 227-240
   - Returns 422 with candidate list
2. What's missing: Endpoint to accept user selection
3. Study alias learning: How does `EntityRepository.create_alias()` work?

**Implementation** (45 min):
```python
# In src/api/routes/chat.py (or new disambiguate.py)

from src.api.models import DisambiguationRequest, DisambiguationResponse

@router.post(
    "/api/v1/disambiguate",
    response_model=DisambiguationResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve ambiguous entity reference",
    description="""
    After receiving a 422 AmbiguousEntity error, user selects the correct entity.
    This endpoint creates a user-specific alias to avoid future ambiguity.

    Vision Principle: Epistemic Humility - System admits uncertainty and learns from clarification.
    """
)
async def resolve_disambiguation(
    request: DisambiguationRequest,
    user_id: str = Depends(get_current_user_id),
    entity_repo: IEntityRepository = Depends(get_entity_repository)
) -> DisambiguationResponse:
    """Resolve ambiguous entity and learn alias.

    Args:
        request: Contains mention_text and selected_entity_id
        user_id: Current user
        entity_repo: Entity repository

    Returns:
        Resolved entity with confirmation
    """
    logger.info(
        "disambiguation_request",
        user_id=user_id,
        mention=request.mention_text,
        selected=request.selected_entity_id
    )

    # Create user-specific alias for future resolution
    await entity_repo.create_alias(
        canonical_entity_id=request.selected_entity_id,
        alias_text=request.mention_text,
        alias_source="user_disambiguation",
        user_id=user_id,  # User-specific
        confidence=1.0,  # High confidence (explicit user choice)
        metadata={"disambiguation_session": request.session_id}
    )

    # Fetch the selected entity
    entity = await entity_repo.get_by_id(request.selected_entity_id)
    if not entity:
        raise HTTPException(404, f"Entity {request.selected_entity_id} not found")

    logger.info(
        "disambiguation_resolved",
        entity_id=entity.entity_id,
        canonical_name=entity.canonical_name
    )

    return DisambiguationResponse(
        entity_id=entity.entity_id,
        canonical_name=entity.canonical_name,
        entity_type=entity.entity_type,
        alias_learned=request.mention_text,
        message=f"Future mentions of '{request.mention_text}' will resolve to {entity.canonical_name}"
    )
```

**API Models** (in `src/api/models/`):
```python
class DisambiguationRequest(BaseModel):
    session_id: UUID
    mention_text: str
    selected_entity_id: str

class DisambiguationResponse(BaseModel):
    entity_id: str
    canonical_name: str
    entity_type: str
    alias_learned: str
    message: str
```

**Testing** (45 min):
1. Unit test: API handler (mocked repo)
2. Integration test: Real alias creation
3. E2E test: Full disambiguation flow
   - Trigger AmbiguousEntityError
   - Call /disambiguate
   - Verify alias created
   - Future query uses alias (no ambiguity)

**Completion Criteria**:
- [ ] /api/v1/disambiguate endpoint implemented
- [ ] API models defined
- [ ] Alias creation works
- [ ] E2E Scenario 3 passes
- [ ] OpenAPI docs updated

**Commit**: `feat(api): add disambiguation endpoint for Scenario 3`

---

#### Task 1.2.2: Consolidation Endpoint (1.5-2 hours)

**Investigation** (30 min):
1. Existing services: `ConsolidationService`, `ConsolidationTriggerService`
2. What do they return? Study method signatures
3. What should endpoint accept? scope_type, scope_identifier, user_id

**Implementation** (45 min):
```python
# In src/api/routes/consolidation.py (file exists, add endpoint)

@router.post(
    "/api/v1/consolidate",
    response_model=ConsolidationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger memory consolidation",
    description="""
    Consolidate episodic and semantic memories into a summary.

    Supports:
    - Entity consolidation: All memories about a specific entity
    - Topic consolidation: All memories about a topic
    - Session window: All memories in a time range

    Vision Principle: Graceful Forgetting - Abstract details into summaries,
    deprioritize source memories, maintain provenance.
    """
)
async def trigger_consolidation(
    request: ConsolidationRequest,
    user_id: str = Depends(get_current_user_id),
    consolidation_trigger: ConsolidationTriggerService = Depends(get_consolidation_trigger),
    consolidation_service: ConsolidationService = Depends(get_consolidation_service)
) -> ConsolidationResponse:
    """Trigger consolidation for a scope."""

    logger.info(
        "consolidation_request",
        user_id=user_id,
        scope_type=request.scope_type,
        scope_identifier=request.scope_identifier
    )

    # Check if consolidation threshold met
    should_consolidate = await consolidation_trigger.should_consolidate(
        scope_type=request.scope_type,
        scope_identifier=request.scope_identifier,
        user_id=user_id
    )

    if not should_consolidate:
        return ConsolidationResponse(
            consolidation_triggered=False,
            message="Consolidation threshold not met. Need ≥10 episodes or ≥3 sessions."
        )

    # Run consolidation
    summary = await consolidation_service.consolidate(
        scope_type=request.scope_type,
        scope_identifier=request.scope_identifier,
        user_id=user_id
    )

    logger.info(
        "consolidation_complete",
        summary_id=summary.summary_id,
        source_memory_count=len(summary.source_data.get("episodic_ids", []))
    )

    return ConsolidationResponse(
        consolidation_triggered=True,
        summary_id=summary.summary_id,
        summary_text=summary.summary_text,
        key_facts=summary.key_facts,
        source_memory_count=len(summary.source_data.get("episodic_ids", [])),
        message=f"Consolidated {len(summary.source_data.get('episodic_ids', []))} memories into summary"
    )
```

**Testing** (45 min):
1. Unit test: Threshold check, consolidation service call
2. Integration test: Real consolidation with seeded memories
3. E2E test: Unskip Scenario 14

**Completion Criteria**:
- [ ] /api/v1/consolidate endpoint
- [ ] Threshold checking works
- [ ] Summary creation works
- [ ] E2E Scenario 14 passes

**Commit**: `feat(api): add consolidation endpoint for Scenario 14`

---

#### Task 1.2.3: Explainability Endpoint (1.5-2 hours)

**Investigation** (30 min):
1. What provenance data exists?
   - `SemanticMemory.extracted_from_event_id` → ChatEvent
   - `SemanticMemory.source_memory_id` → EpisodicMemory
   - `SemanticMemory.reinforcement_count` → How many confirmations
2. What should /explain return? Memory provenance chain

**Implementation** (45 min):
```python
# In src/api/routes/retrieval.py (or new explainability.py)

@router.get(
    "/api/v1/explain/{memory_id}",
    response_model=ExplainResponse,
    summary="Explain memory provenance",
    description="""
    Return provenance trail for a specific memory.

    Shows:
    - Source chat event (when/how memory was created)
    - Reinforcement events (confirmations)
    - Consolidation source (if from summary)
    - Confidence factors

    Vision Principle: Explainable Reasoning - Transparency as trust.
    """
)
async def explain_memory(
    memory_id: int,
    user_id: str = Depends(get_current_user_id),
    semantic_repo: ISemanticMemoryRepository = Depends(get_semantic_repo),
    episodic_repo: IEpisodicMemoryRepository = Depends(get_episodic_repo),
    chat_repo: IChatEventRepository = Depends(get_chat_repo)
) -> ExplainResponse:
    """Return provenance chain for memory."""

    # Fetch semantic memory
    memory = await semantic_repo.get_by_id(memory_id)
    if not memory or memory.user_id != user_id:
        raise HTTPException(404, "Memory not found")

    # Fetch source event
    source_event = None
    if memory.extracted_from_event_id:
        source_event = await chat_repo.get_by_id(memory.extracted_from_event_id)

    # Fetch episodic source
    episodic_source = None
    if memory.source_memory_id:
        episodic_source = await episodic_repo.get_by_id(memory.source_memory_id)

    # Find reinforcement events (other semantic memories with same subject+predicate)
    reinforcements = await semantic_repo.find_reinforcements(
        subject_entity_id=memory.subject_entity_id,
        predicate=memory.predicate,
        exclude_memory_id=memory_id
    )

    return ExplainResponse(
        memory_id=memory_id,
        predicate=memory.predicate,
        object_value=memory.object_value,
        confidence=memory.confidence,
        confidence_factors=memory.confidence_factors,
        source_event={
            "event_id": source_event.event_id,
            "content": source_event.content,
            "created_at": source_event.created_at.isoformat()
        } if source_event else None,
        episodic_source={
            "memory_id": episodic_source.memory_id,
            "summary": episodic_source.summary
        } if episodic_source else None,
        reinforcements=[
            {
                "memory_id": r.memory_id,
                "created_at": r.created_at.isoformat(),
                "confidence": r.confidence
            }
            for r in reinforcements
        ],
        reinforcement_count=memory.reinforcement_count
    )
```

**Testing** (45 min):
1. Unit test: Provenance chain fetching
2. Integration test: Real memory with source event
3. E2E test: Unskip Scenario 15

**Completion Criteria**:
- [ ] /api/v1/explain/{memory_id} endpoint
- [ ] Provenance chain complete
- [ ] E2E Scenario 15 passes

**Commit**: `feat(api): add explainability endpoint for Scenario 15`

---

### Milestone 1.3: Minor Enhancements (2-3 hours) → +2 scenarios

**Scenarios Unblocked**: #12 (auto-alias), #17 (conflict exposure)

---

#### Task 1.3.1: Auto-Alias from Fuzzy Match (1-1.5 hours)

**Investigation** (20 min):
1. Where does fuzzy matching happen?
   - `EntityResolutionService.resolve()` Stage 3
2. What's returned? `ResolutionResult` with confidence
3. What's missing? Automatic alias creation after successful fuzzy match

**Implementation** (30 min):
```python
# In src/domain/services/entity_resolution_service.py

# In resolve() method, after Stage 3 (fuzzy match):
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
            user_id=user_id,  # User-specific
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

**Testing** (30 min):
1. Unit test: Fuzzy match → alias created
2. Integration test: Next query uses exact match (faster)
3. E2E test: Unskip Scenario 12

**Completion Criteria**:
- [ ] Auto-alias after fuzzy match
- [ ] Graceful failure (doesn't break resolution if alias creation fails)
- [ ] E2E Scenario 12 passes

**Commit**: `feat(entity-resolution): auto-create alias from fuzzy matches for Scenario 12`

---

#### Task 1.3.2: Expose Conflicts in API Response (1-1.5 hours)

**Investigation** (20 min):
1. Where are conflicts detected? `ConflictDetectionService`
2. What's returned? List of `MemoryConflict` entities
3. What's missing? Conflicts not in API response DTOs

**Implementation** (30 min):
```python
# In src/application/dtos/chat_dtos.py

@dataclass
class ConflictDTO:
    """Conflict information for API response."""
    conflict_id: int
    conflict_type: str  # "memory_vs_memory" | "memory_vs_db"
    memory_value: Any
    db_value: Optional[Any]
    resolution_strategy: str  # "trust_db" | "trust_recent" | "ask_user"
    confidence_diff: Optional[float]

@dataclass
class ProcessChatMessageOutput:
    # ... existing fields ...
    conflicts_detected: List[ConflictDTO] = field(default_factory=list)  # ADD THIS
```

```python
# In src/application/use_cases/extract_semantics.py

# Ensure ConflictDetectionService returns conflicts
@dataclass
class ExtractSemanticsOutput:
    # ... existing fields ...
    conflicts: List[MemoryConflict] = field(default_factory=list)  # ADD THIS
```

```python
# In src/application/use_cases/process_chat_message.py

# After semantic extraction:
conflicts = semantics_result.conflicts

# In final ProcessChatMessageOutput:
return ProcessChatMessageOutput(
    # ... existing fields ...
    conflicts_detected=[
        ConflictDTO(
            conflict_id=c.conflict_id,
            conflict_type=c.conflict_type,
            memory_value=c.conflict_data.get("memory_value"),
            db_value=c.conflict_data.get("db_value"),
            resolution_strategy=c.resolution_strategy,
            confidence_diff=c.conflict_data.get("confidence_diff")
        )
        for c in conflicts
    ]
)
```

```python
# In src/api/routes/chat.py (simplified endpoint)

# Add to response dict:
return {
    "response": output.reply,
    "augmentation": { ... },
    "memories_created": [...],
    "conflicts_detected": [  # ADD THIS
        {
            "conflict_type": c.conflict_type,
            "memory_value": c.memory_value,
            "db_value": c.db_value,
            "resolution": c.resolution_strategy
        }
        for c in output.conflicts_detected
    ]
}
```

**Testing** (30 min):
1. Unit test: Conflict in semantics → appears in output
2. Integration test: Real conflict detected and returned
3. E2E test: Unskip Scenario 17

**Completion Criteria**:
- [ ] ConflictDTO defined
- [ ] Conflicts in ProcessChatMessageOutput
- [ ] Conflicts in API response
- [ ] E2E Scenario 17 passes

**Commit**: `feat(api): expose memory conflicts in chat response for Scenario 17`

---

### Phase 1 Completion Check

**Before proceeding to Phase 2, verify**:
- [ ] 11/18 scenarios passing (61%)
- [ ] All new tests passing
- [ ] No regressions in original 4 scenarios
- [ ] Code quality: `make check-all` passes
- [ ] Documentation: Update E2E_SCENARIOS_PROGRESS.md

**Celebration**: 🎉 You've gone from 4 to 11 passing scenarios with ~16 hours of focused work!

---

## Phase 2: Core Features (16-20 hours) → 15/18 Scenarios (83%)

> **Goal**: Implement features requiring moderate complexity. Build on Phase 1 foundation.

### Milestone 2.1: Consolidation Resolution Strategies (3-4 hours) → +1 scenario

**Scenario Unblocked**: #7 (conflicting memories → consolidation)

**Vision Principle**: Epistemic Humility - Explicit conflict resolution

---

#### Task 2.1.1: Implement Resolution Strategies (3-4 hours)

**Investigation** (45 min):
1. Read LIFECYCLE_DESIGN.md: How should conflicts be resolved?
2. Study MemoryConflict table: What data is available?
3. Review ConflictDetectionService: What conflicts are detected?

**Implementation** (2 hours):
```python
# In src/domain/services/conflict_resolution_service.py (NEW)

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class ResolutionStrategy(str, Enum):
    TRUST_DB = "trust_db"
    TRUST_RECENT = "trust_recent"
    TRUST_REINFORCED = "trust_reinforced"
    ASK_USER = "ask_user"
    BOTH = "both"  # Present both, let LLM explain discrepancy

@dataclass
class ResolutionResult:
    """Result of conflict resolution."""
    winning_memory_id: Optional[int]
    losing_memory_id: Optional[int]
    strategy_used: ResolutionStrategy
    rationale: str
    action: str  # "supersede" | "mark_invalidated" | "ask_user"

class ConflictResolutionService:
    """Resolve memory conflicts using explicit strategies.

    Vision Principle: Epistemic Humility - System explicitly resolves conflicts
    rather than silently preferring one value.
    """

    def __init__(
        self,
        semantic_repo: ISemanticMemoryRepository,
        conflict_repo: IMemoryConflictRepository
    ):
        self.semantic_repo = semantic_repo
        self.conflict_repo = conflict_repo

    async def resolve_conflict(
        self,
        conflict: MemoryConflict,
        strategy: Optional[ResolutionStrategy] = None
    ) -> ResolutionResult:
        """Resolve a detected conflict using specified strategy.

        Args:
            conflict: The detected conflict
            strategy: Resolution strategy (auto-selected if None)

        Returns:
            ResolutionResult with winning memory and action taken
        """
        # Auto-select strategy if not provided
        if strategy is None:
            strategy = self._select_strategy(conflict)

        logger.info(
            "resolving_conflict",
            conflict_id=conflict.conflict_id,
            conflict_type=conflict.conflict_type,
            strategy=strategy
        )

        if conflict.conflict_type == "memory_vs_db":
            return await self._resolve_memory_vs_db(conflict)
        elif conflict.conflict_type == "memory_vs_memory":
            if strategy == ResolutionStrategy.TRUST_RECENT:
                return await self._resolve_trust_recent(conflict)
            elif strategy == ResolutionStrategy.TRUST_REINFORCED:
                return await self._resolve_trust_reinforced(conflict)
            elif strategy == ResolutionStrategy.ASK_USER:
                return await self._resolve_ask_user(conflict)

        raise ValueError(f"Unsupported conflict type or strategy: {conflict.conflict_type}, {strategy}")

    def _select_strategy(self, conflict: MemoryConflict) -> ResolutionStrategy:
        """Auto-select resolution strategy based on conflict characteristics."""
        if conflict.conflict_type == "memory_vs_db":
            return ResolutionStrategy.TRUST_DB

        # For memory_vs_memory
        data = conflict.conflict_data
        mem1_reinforcement = data.get("memory1_reinforcement_count", 1)
        mem2_reinforcement = data.get("memory2_reinforcement_count", 1)

        # If one memory is significantly more reinforced, trust it
        if mem1_reinforcement > mem2_reinforcement * 2:
            return ResolutionStrategy.TRUST_REINFORCED
        if mem2_reinforcement > mem1_reinforcement * 2:
            return ResolutionStrategy.TRUST_REINFORCED

        # Otherwise, trust more recent
        return ResolutionStrategy.TRUST_RECENT

    async def _resolve_memory_vs_db(self, conflict: MemoryConflict) -> ResolutionResult:
        """Resolve memory vs DB conflict - always trust DB."""
        data = conflict.conflict_data
        memory_id = data["memory_id"]

        # Mark memory as invalidated (DB truth is authoritative)
        memory = await self.semantic_repo.get_by_id(memory_id)
        memory.status = "invalidated"
        await self.semantic_repo.update(memory)

        logger.info(
            "conflict_resolved_trust_db",
            memory_id=memory_id,
            action="invalidated"
        )

        return ResolutionResult(
            winning_memory_id=None,  # DB wins (not a memory)
            losing_memory_id=memory_id,
            strategy_used=ResolutionStrategy.TRUST_DB,
            rationale="Database is authoritative source of truth",
            action="mark_invalidated"
        )

    async def _resolve_trust_recent(self, conflict: MemoryConflict) -> ResolutionResult:
        """Resolve by trusting more recent memory."""
        data = conflict.conflict_data
        mem1_id = data["memory1_id"]
        mem2_id = data["memory2_id"]
        mem1_created = data["memory1_created_at"]
        mem2_created = data["memory2_created_at"]

        if mem1_created > mem2_created:
            winner_id, loser_id = mem1_id, mem2_id
        else:
            winner_id, loser_id = mem2_id, mem1_id

        # Mark older memory as superseded
        loser = await self.semantic_repo.get_by_id(loser_id)
        loser.status = "superseded"
        loser.superseded_by_memory_id = winner_id
        await self.semantic_repo.update(loser)

        logger.info(
            "conflict_resolved_trust_recent",
            winner_id=winner_id,
            loser_id=loser_id
        )

        return ResolutionResult(
            winning_memory_id=winner_id,
            losing_memory_id=loser_id,
            strategy_used=ResolutionStrategy.TRUST_RECENT,
            rationale="More recent information supersedes older",
            action="supersede"
        )

    async def _resolve_trust_reinforced(self, conflict: MemoryConflict) -> ResolutionResult:
        """Resolve by trusting more reinforced memory."""
        data = conflict.conflict_data
        mem1_id = data["memory1_id"]
        mem2_id = data["memory2_id"]
        mem1_reinforcement = data["memory1_reinforcement_count"]
        mem2_reinforcement = data["memory2_reinforcement_count"]

        if mem1_reinforcement > mem2_reinforcement:
            winner_id, loser_id = mem1_id, mem2_id
        else:
            winner_id, loser_id = mem2_id, mem1_id

        # Mark less reinforced memory as superseded
        loser = await self.semantic_repo.get_by_id(loser_id)
        loser.status = "superseded"
        loser.superseded_by_memory_id = winner_id
        await self.semantic_repo.update(loser)

        logger.info(
            "conflict_resolved_trust_reinforced",
            winner_id=winner_id,
            loser_id=loser_id
        )

        return ResolutionResult(
            winning_memory_id=winner_id,
            losing_memory_id=loser_id,
            strategy_used=ResolutionStrategy.TRUST_REINFORCED,
            rationale="More frequently confirmed information preferred",
            action="supersede"
        )

    async def _resolve_ask_user(self, conflict: MemoryConflict) -> ResolutionResult:
        """Resolve by asking user - return both values."""
        # Don't auto-resolve - return both for user clarification
        return ResolutionResult(
            winning_memory_id=None,
            losing_memory_id=None,
            strategy_used=ResolutionStrategy.ASK_USER,
            rationale="Ambiguous - require user clarification",
            action="ask_user"
        )
```

**Integration** (30 min):
```python
# In src/application/use_cases/extract_semantics.py

# After conflict detection:
for conflict in detected_conflicts:
    resolution = await self.conflict_resolution_service.resolve_conflict(
        conflict=conflict,
        strategy=None  # Auto-select
    )

    # Update conflict record with resolution
    conflict.resolution_strategy = resolution.strategy_used
    conflict.resolution_outcome = {
        "winner_id": resolution.winning_memory_id,
        "loser_id": resolution.losing_memory_id,
        "rationale": resolution.rationale
    }
    conflict.resolved_at = datetime.now(UTC)
    await self.conflict_repo.update(conflict)
```

**Testing** (1-1.5 hours):
1. Unit tests: Each resolution strategy
   - trust_db: Memory marked invalidated
   - trust_recent: Newer memory wins, older superseded
   - trust_reinforced: More reinforced wins
   - ask_user: Both returned

2. Integration tests: Real conflicts, real resolution

3. E2E test: Unskip Scenario 7
   - Create conflicting memories (NET30 → NET15)
   - Trigger conflict detection
   - Verify resolution (trust_recent)
   - Check older memory status = "superseded"

**Completion Criteria**:
- [ ] ConflictResolutionService implemented
- [ ] All resolution strategies work
- [ ] Memory status updates (invalidated, superseded)
- [ ] E2E Scenario 7 passes
- [ ] Conflicts recorded with resolution outcome

**Commit**: `feat(conflict-resolution): implement resolution strategies for Scenario 7`

---

### Milestone 2.2: Active Validation (3-4 hours) → +1 scenario

**Scenario Unblocked**: #10 (active recall for stale facts)

**Vision Principle**: Epistemic Humility - System questions aged information

---

#### Task 2.2.1: Validation Prompting (2-2.5 hours)

**Investigation** (30 min):
1. Where to inject validation prompts? In `LLMReplyGenerator`
2. How to detect stale memories? `MemoryValidationService.calculate_effective_confidence()`
3. What threshold defines "stale"? Check heuristics

**Implementation** (1-1.5 hours):
```python
# In src/domain/services/llm_reply_generator.py

async def _check_for_validation_needs(
    self,
    retrieved_memories: List[RetrievedMemory]
) -> List[str]:
    """Generate validation prompts for stale memories.

    Vision Principle: Epistemic Humility - Proactively validate aged information
    before using it for important decisions.

    Returns:
        List of validation questions to inject in reply
    """
    validation_questions = []

    stale_threshold_days = get_config("validation.stale_threshold_days")  # e.g., 90
    low_confidence_threshold = get_config("validation.low_confidence_threshold")  # e.g., 0.6

    for mem in retrieved_memories:
        # Skip if not semantic memory
        if mem.memory_type != "semantic":
            continue

        # Calculate days since validation
        # (Would need last_validated_at in RetrievedMemory DTO)
        # For now, assume we have it
        days_old = mem.days_since_validation
        effective_confidence = mem.confidence  # Already has decay applied

        if days_old > stale_threshold_days and effective_confidence < low_confidence_threshold:
            # Generate validation question
            question = f"Quick verification: Is '{mem.predicate}: {mem.object_value}' still accurate?"
            validation_questions.append(question)

            logger.info(
                "validation_prompt_generated",
                memory_id=mem.memory_id,
                days_old=days_old,
                confidence=effective_confidence
            )

    return validation_questions

async def generate(self, context: ReplyContext) -> str:
    """Generate reply with validation prompts if needed."""

    # Check for stale memories needing validation
    validation_prompts = await self._check_for_validation_needs(context.retrieved_memories)

    # Build prompt with validation questions
    system_prompt = self._build_system_prompt(context)

    if validation_prompts:
        system_prompt += "\n\nIMPORTANT: The following facts are old and need validation. Ask the user to confirm:\n"
        for q in validation_prompts:
            system_prompt += f"- {q}\n"

    # ... rest of generation ...
```

**Configuration** (add to heuristics):
```python
HEURISTICS = {
    # ... existing ...
    "validation": {
        "stale_threshold_days": 90,  # Prompt validation after 90 days
        "low_confidence_threshold": 0.6,  # Only validate if confidence dropped below 0.6
    }
}
```

**Testing** (1-1.5 hours):
1. Unit test: Stale memory detection
2. Unit test: Validation prompt generation
3. Integration test: Full reply with validation prompt
4. E2E test: Unskip Scenario 10

**Completion Criteria**:
- [ ] Validation prompt generation in LLMReplyGenerator
- [ ] Heuristic configuration
- [ ] E2E Scenario 10 passes (validation prompt appears)

**Commit**: `feat(memory-validation): add active validation prompting for Scenario 10`

---

#### Task 2.2.2: Validation Endpoint (1-1.5 hours)

**Purpose**: Allow user to confirm or invalidate a memory

**Implementation** (45 min):
```python
# In src/api/routes/retrieval.py (or new validation.py)

@router.post(
    "/api/v1/validate/{memory_id}",
    response_model=ValidationResponse,
    summary="Validate or invalidate a memory",
    description="""
    User confirms whether a memory is still accurate.

    If valid: Update last_validated_at, boost confidence
    If invalid: Mark status="invalidated"

    Vision Principle: Epistemic Humility + Adaptive Learning
    """
)
async def validate_memory(
    memory_id: int,
    request: ValidationRequest,
    user_id: str = Depends(get_current_user_id),
    semantic_repo: ISemanticMemoryRepository = Depends(get_semantic_repo)
) -> ValidationResponse:
    """Validate or invalidate a memory."""

    memory = await semantic_repo.get_by_id(memory_id)
    if not memory or memory.user_id != user_id:
        raise HTTPException(404, "Memory not found")

    if request.is_valid:
        # Memory confirmed valid
        memory.last_validated_at = datetime.now(UTC)
        memory.confidence = min(0.95, memory.confidence + 0.05)  # Small boost
        logger.info("memory_validated", memory_id=memory_id)
    else:
        # Memory invalidated
        memory.status = "invalidated"
        logger.info("memory_invalidated", memory_id=memory_id)

    await semantic_repo.update(memory)

    return ValidationResponse(
        memory_id=memory_id,
        action="validated" if request.is_valid else "invalidated",
        new_confidence=memory.confidence,
        message=f"Memory {memory_id} {'confirmed' if request.is_valid else 'marked as outdated'}"
    )
```

**Testing** (45 min):
1. Unit test: Validation logic
2. Integration test: Real memory update
3. E2E test: Full validation flow

**Completion Criteria**:
- [ ] /api/v1/validate/{memory_id} endpoint
- [ ] Memory update works (last_validated_at or status)
- [ ] E2E Scenario 10 fully passes (prompt + validation)

**Commit**: `feat(api): add memory validation endpoint for Scenario 10`

---

### Milestone 2.3: Multi-Hop Ontology Traversal (5-6 hours) → +1 scenario

**Scenario Unblocked**: #11 (cross-object reasoning)

**Vision Principle**: Deep Business Understanding (ontology-awareness)

---

#### Task 2.3.1: Ontology Traversal Service (5-6 hours)

**Investigation** (1 hour):
1. Study DomainOntology table: What relationships are defined?
2. Read DESIGN.md: How should multi-hop queries work?
3. Example query: Customer → Sales Orders → Work Orders → Invoices
4. Check OntologyService: What methods exist?

**Implementation** (3-3.5 hours):
```python
# In src/domain/services/ontology_traversal_service.py (NEW)

from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class TraversalStep:
    """One step in ontology traversal."""
    from_table: str
    to_table: str
    relation_type: str  # "has" | "creates" | "requires" | "fulfills"
    join_condition: str  # e.g., "customers.customer_id = sales_orders.customer_id"

@dataclass
class TraversalPath:
    """Complete path from source to target entity type."""
    steps: List[TraversalStep]
    total_hops: int

class OntologyTraversalService:
    """Multi-hop ontology traversal for cross-object reasoning.

    Vision Principle: Deep Business Understanding - Navigate relationship
    graph to fetch related entities across multiple hops.

    Example: Customer → Sales Orders → Work Orders → Invoices
    """

    def __init__(
        self,
        ontology_repo: IDomainOntologyRepository,
        domain_query_executor: IDomainQueryExecutor
    ):
        self.ontology_repo = ontology_repo
        self.query_executor = domain_query_executor

    async def traverse(
        self,
        start_entity_id: str,
        start_entity_type: str,
        target_entity_types: List[str],
        max_hops: int = 3
    ) -> Dict[str, List[DomainFact]]:
        """Traverse ontology from source entity to target types.

        Args:
            start_entity_id: Source entity (e.g., "customer_123")
            start_entity_type: Type (e.g., "customer")
            target_entity_types: Target types to fetch (e.g., ["work_order", "invoice"])
            max_hops: Maximum traversal depth

        Returns:
            Dict mapping target_type → list of DomainFacts
        """
        logger.info(
            "ontology_traversal_start",
            start_entity=start_entity_id,
            start_type=start_entity_type,
            targets=target_entity_types,
            max_hops=max_hops
        )

        results = {}

        for target_type in target_entity_types:
            # Find path from start to target
            path = await self._find_path(start_entity_type, target_type, max_hops)

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
        """Find shortest path from source to target entity type.

        Uses BFS through ontology graph.
        """
        if from_type == to_type:
            return TraversalPath(steps=[], total_hops=0)

        # Fetch all ontology relationships
        all_relations = await self.ontology_repo.get_all()

        # Build adjacency list
        graph: Dict[str, List[Tuple[str, DomainOntology]]] = {}
        for rel in all_relations:
            if rel.from_entity_type not in graph:
                graph[rel.from_entity_type] = []
            graph[rel.from_entity_type].append((rel.to_entity_type, rel))

        # BFS to find shortest path
        from collections import deque

        queue = deque([(from_type, [])])  # (current_type, path_so_far)
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
                    from_table=relation.from_entity_type,
                    to_table=relation.to_entity_type,
                    relation_type=relation.relation_type,
                    join_condition=self._build_join_condition(relation)
                )]

                if next_type == to_type:
                    return TraversalPath(steps=new_path, total_hops=len(new_path))

                visited.add(next_type)
                queue.append((next_type, new_path))

        return None  # No path found

    def _build_join_condition(self, relation: DomainOntology) -> str:
        """Build SQL JOIN condition from relation spec."""
        join_spec = relation.join_spec
        return f"{join_spec['from_table']}.{join_spec['from_field']} = {join_spec['to_table']}.{join_spec['to_field']}"

    async def _execute_traversal(
        self,
        start_entity_id: str,
        path: TraversalPath
    ) -> List[DomainFact]:
        """Execute multi-hop query following path."""

        # Build SQL query with multiple JOINs
        # Example for Customer → SO → WO → Invoice:
        # SELECT i.*, wo.status as work_status
        # FROM domain.customers c
        # JOIN domain.sales_orders so ON c.customer_id = so.customer_id
        # JOIN domain.work_orders wo ON so.so_id = wo.so_id
        # LEFT JOIN domain.invoices i ON so.so_id = i.so_id
        # WHERE c.customer_id = :start_entity_id

        if not path.steps:
            return []

        # Build query
        from_table = f"domain.{path.steps[0].from_table}"
        select_clauses = [f"{from_table}.*"]
        join_clauses = []

        current_alias = from_table.split(".")[-1][0]  # First letter as alias

        for step in path.steps:
            to_table = f"domain.{step.to_table}"
            to_alias = step.to_table[0]

            join_type = "LEFT JOIN" if step.relation_type == "has" else "JOIN"
            join_clauses.append(
                f"{join_type} {to_table} {to_alias} ON {step.join_condition}"
            )

            select_clauses.append(f"{to_alias}.*")

        query = f"""
        SELECT {', '.join(select_clauses)}
        FROM {from_table} {current_alias}
        {' '.join(join_clauses)}
        WHERE {current_alias}.{path.steps[0].from_table}_id = :start_entity_id
        """

        # Execute query
        rows = await self.query_executor.execute(query, {"start_entity_id": start_entity_id})

        # Convert rows to DomainFacts
        facts = []
        for row in rows:
            facts.append(DomainFact(
                fact_type="multi_hop_traversal",
                entity_id=start_entity_id,
                content=f"Related {path.steps[-1].to_table}",
                metadata=dict(row),
                source_table=path.steps[-1].to_table,
                source_rows=[dict(row)],
                retrieved_at=datetime.now(UTC)
            ))

        return facts
```

**Integration** (30 min):
```python
# In src/domain/services/domain_augmentation_service.py

# Add method:
async def augment_with_related_entities(
    self,
    entity_id: str,
    entity_type: str,
    related_types: List[str]
) -> List[DomainFact]:
    """Fetch related entities via ontology traversal."""

    if not self.ontology_traversal_service:
        return []

    results = await self.ontology_traversal_service.traverse(
        start_entity_id=entity_id,
        start_entity_type=entity_type,
        target_entity_types=related_types,
        max_hops=3
    )

    # Flatten results
    all_facts = []
    for target_type, facts in results.items():
        all_facts.extend(facts)

    return all_facts
```

**Testing** (1.5-2 hours):
1. Unit test: Path finding (BFS)
   - Customer → Sales Order (1 hop)
   - Customer → Invoice (2 hops: Customer → SO → Invoice)
   - Customer → Work Order (2 hops)

2. Integration test: Real multi-hop query
   - Seed: Customer, Sales Order, Work Order, Invoice
   - Query: Traverse from customer to invoice
   - Assert: Invoice facts returned with work order status

3. E2E test: Unskip Scenario 11
   - User asks: "Can we invoice Gai Media?"
   - System traverses: Customer → SO → WO → Invoice
   - Response includes: Work not complete, invoice exists

**Completion Criteria**:
- [ ] OntologyTraversalService implemented
- [ ] BFS path finding works
- [ ] Multi-hop SQL generation correct
- [ ] Integration with DomainAugmentationService
- [ ] E2E Scenario 11 passes

**Commit**: `feat(ontology): add multi-hop traversal for Scenario 11`

---

### Milestone 2.4: Task Completion Flow (4-5 hours) → +1 scenario

**Scenario Unblocked**: #18 (task completion via conversation)

**Vision Principle**: Domain Augmentation + Semantic Extraction

---

#### Task 2.4.1: Task Update API (4-5 hours)

**Investigation** (45 min):
1. How to handle task updates? SQL patch or direct update?
2. Read Scenario 18 test: What's expected?
3. Should we actually update domain.tasks or mock it?

**Decision**: For Phase 1, return SQL patch suggestion. Actual update requires domain DB write access (Phase 2 decision).

**Implementation** (2.5-3 hours):
```python
# In src/api/routes/tasks.py (NEW)

from src.api.models.tasks import TaskCompletionRequest, TaskCompletionResponse

@router.post(
    "/api/v1/tasks/{task_id}/complete",
    response_model=TaskCompletionResponse,
    summary="Mark task complete with summary",
    description="""
    Mark a task as complete and store completion summary as semantic memory.

    Returns SQL patch suggestion for domain DB update.
    Can be configured to actually update if given write access.

    Vision Principle: Domain Augmentation + Semantic Extraction
    """
)
async def complete_task(
    task_id: str,
    request: TaskCompletionRequest,
    user_id: str = Depends(get_current_user_id),
    domain_augmentation: DomainAugmentationService = Depends(get_domain_augmentation),
    semantic_extraction: SemanticExtractionService = Depends(get_semantic_extraction)
) -> TaskCompletionResponse:
    """Complete task and store summary."""

    logger.info(
        "task_completion_request",
        task_id=task_id,
        user_id=user_id,
        summary_length=len(request.summary)
    )

    # Fetch task details
    task_facts = await domain_augmentation.get_entity_facts(
        entity_type="task",
        entity_id=task_id
    )

    if not task_facts:
        raise HTTPException(404, f"Task {task_id} not found")

    # Generate SQL patch
    sql_patch = f"""
    UPDATE domain.tasks
    SET status = 'done',
        completed_at = NOW(),
        completion_notes = '{request.summary}'
    WHERE task_id = '{task_id}';
    """

    # Store summary as semantic memory
    semantic_memory = await semantic_extraction.create_memory_from_statement(
        subject_entity_id=f"task_{task_id}",
        predicate="completion_summary",
        object_value={
            "type": "summary",
            "value": request.summary,
            "completed_at": datetime.now(UTC).isoformat()
        },
        confidence=0.9,
        user_id=user_id,
        source_type="task_completion",
        predicate_type="observation"
    )

    logger.info(
        "task_completed",
        task_id=task_id,
        semantic_memory_id=semantic_memory.memory_id
    )

    return TaskCompletionResponse(
        task_id=task_id,
        status="completed",
        sql_patch=sql_patch,
        semantic_memory_id=semantic_memory.memory_id,
        message=f"Task {task_id} marked complete. Summary stored as semantic memory."
    )
```

**API Models**:
```python
# In src/api/models/tasks.py (NEW)

class TaskCompletionRequest(BaseModel):
    summary: str  # Completion summary

class TaskCompletionResponse(BaseModel):
    task_id: str
    status: str  # "completed"
    sql_patch: str  # SQL to update domain.tasks
    semantic_memory_id: int  # ID of created semantic memory
    message: str
```

**Testing** (1.5-2 hours):
1. Unit test: SQL patch generation
2. Integration test: Semantic memory creation
3. E2E test: Unskip Scenario 18

**Completion Criteria**:
- [ ] /api/v1/tasks/{task_id}/complete endpoint
- [ ] SQL patch returned
- [ ] Semantic memory created with summary
- [ ] E2E Scenario 18 passes

**Commit**: `feat(api): add task completion endpoint for Scenario 18`

---

### Phase 2 Completion Check

**Before proceeding to Phase 3, verify**:
- [ ] 15/18 scenarios passing (83%)
- [ ] All Phase 2 features tested
- [ ] No regressions
- [ ] Code quality: `make check-all` passes
- [ ] Documentation updated

**Celebration**: 🎉 You've reached 83% coverage! Only 3 scenarios left.

---

## Phase 3: Advanced Features (16-21 hours) → 18/18 Scenarios (100%)

> **Goal**: Implement complex features requiring significant LLM integration or advanced logic.

### Milestone 3.1: Procedural Memory Extraction (6-8 hours) → +1 scenario

**Scenario Unblocked**: #16 (reminder creation from conversational intent)

**Vision Principle**: Procedural Memory + Proactive Intelligence

---

#### Task 3.1.1: LLM Procedural Extraction (4-5 hours)

**Investigation** (1 hour):
1. Study ProceduralMemory table schema
2. Read VISION.md: What are procedural memories?
3. Example policies: "If X, then Y"
4. Design LLM prompt for policy extraction

**Implementation** (2.5-3 hours):
```python
# In src/domain/services/procedural_extraction_service.py (NEW)

from typing import Optional
from dataclasses import dataclass

@dataclass
class ProceduralPattern:
    """Extracted procedural pattern."""
    trigger_pattern: str
    trigger_features: dict  # {intent, entity_types, topics}
    action_heuristic: str
    action_structure: dict  # {action_type, queries, predicates}
    confidence: float

class ProceduralExtractionService:
    """Extract procedural memories from conversational policy statements.

    Vision Principle: Procedural Memory - Learn trigger-action patterns.

    Examples:
    - "If invoice is 3 days before due, remind me" → Trigger + action
    - "When delivery is mentioned, check related invoices" → Pattern
    """

    def __init__(self, llm_service: ILLMService):
        self.llm_service = llm_service

    async def extract_procedural_memory(
        self,
        content: str,
        resolved_entities: List[ResolvedEntity]
    ) -> Optional[ProceduralPattern]:
        """Extract procedural memory if policy statement detected."""

        # Step 1: Detect if this is a policy statement
        is_policy = await self._detect_policy_statement(content)
        if not is_policy:
            return None

        # Step 2: Extract trigger and action
        pattern = await self._extract_trigger_action(content, resolved_entities)

        logger.info(
            "procedural_memory_extracted",
            trigger_pattern=pattern.trigger_pattern,
            action=pattern.action_heuristic
        )

        return pattern

    async def _detect_policy_statement(self, content: str) -> bool:
        """Detect if text expresses a policy or trigger-action rule."""

        prompt = f"""
        Does this statement express a policy, rule, or trigger-action pattern?

        Examples of policy statements:
        - "If invoice is open 3 days before due, remind me"
        - "When delivery is mentioned, check invoices"
        - "Always verify work order status before invoicing"

        Examples of non-policy statements:
        - "What is the invoice status?" (question)
        - "Gai Media prefers Friday deliveries" (preference, not policy)
        - "Mark task as done" (command, not policy)

        Statement: "{content}"

        Is this a policy statement? Answer yes or no.
        """

        response = await self.llm_service.complete(prompt)
        return "yes" in response.lower()

    async def _extract_trigger_action(
        self,
        content: str,
        resolved_entities: List[ResolvedEntity]
    ) -> ProceduralPattern:
        """Extract trigger pattern and action from policy statement."""

        entity_types = [e.entity_type for e in resolved_entities]

        prompt = f"""
        Extract the trigger-action pattern from this policy statement.

        Statement: "{content}"
        Entities mentioned: {entity_types}

        Extract:
        1. trigger_pattern: When does this apply? (concise phrase)
        2. trigger_intent: What intent triggers this? (e.g., "payment_reminder", "status_check")
        3. trigger_entity_types: What entity types are involved?
        4. trigger_topics: What topics/domains? (e.g., ["invoices", "due_dates", "payments"])
        5. action_heuristic: What should happen? (detailed description)
        6. action_type: Type of action (e.g., "proactive_notice", "query", "validation")
        7. action_queries: What queries to run? (SQL-ish description)
        8. action_predicates: What conditions to check?

        Return as JSON:
        {{
          "trigger_pattern": "...",
          "trigger_intent": "...",
          "trigger_entity_types": [...],
          "trigger_topics": [...],
          "action_heuristic": "...",
          "action_type": "...",
          "action_queries": [...],
          "action_predicates": [...]
        }}
        """

        response = await self.llm_service.complete(prompt)
        data = json.loads(response)

        return ProceduralPattern(
            trigger_pattern=data["trigger_pattern"],
            trigger_features={
                "intent": data["trigger_intent"],
                "entity_types": data["trigger_entity_types"],
                "topics": data["trigger_topics"]
            },
            action_heuristic=data["action_heuristic"],
            action_structure={
                "action_type": data["action_type"],
                "queries": data["action_queries"],
                "predicates": data["action_predicates"]
            },
            confidence=0.7  # Moderate confidence for LLM extraction
        )
```

**Integration** (30 min):
```python
# In src/application/use_cases/process_chat_message.py

# After semantic extraction:
procedural_pattern = await self.procedural_extraction.extract_procedural_memory(
    content=input_dto.content,
    resolved_entities=entities_result.resolved_entities
)

if procedural_pattern:
    # Store procedural memory
    await self.procedural_memory_service.create(
        user_id=input_dto.user_id,
        trigger_pattern=procedural_pattern.trigger_pattern,
        trigger_features=procedural_pattern.trigger_features,
        action_heuristic=procedural_pattern.action_heuristic,
        action_structure=procedural_pattern.action_structure,
        confidence=procedural_pattern.confidence
    )
```

**Testing** (1.5-2 hours):
1. Unit test: Policy detection
   - "If invoice open 3 days before due, remind me" → True
   - "What's the invoice status?" → False

2. Unit test: Trigger-action extraction
   - Verify trigger_pattern, action_heuristic extracted

3. Integration test: ProceduralMemory created

**Completion Criteria**:
- [ ] ProceduralExtractionService implemented
- [ ] Policy detection works
- [ ] Trigger-action extraction works
- [ ] ProceduralMemory created in pipeline

**Commit**: `feat(procedural): add LLM-based procedural memory extraction`

---

#### Task 3.1.2: Proactive Trigger Checking (2-3 hours)

**Purpose**: Check if any procedural memories trigger in current context

**Implementation** (1.5-2 hours):
```python
# In src/domain/services/proactive_notice_service.py (NEW)

from typing import List
from dataclasses import dataclass

@dataclass
class ProactiveNotice:
    """Proactive notice to surface in response."""
    trigger_id: int  # ProceduralMemory.memory_id
    notice_text: str
    priority: str  # "low" | "medium" | "high"
    metadata: dict

class ProactiveNoticeService:
    """Check for procedural memory triggers and generate proactive notices.

    Vision Principle: Proactive Intelligence - Surface relevant information
    before user asks.
    """

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
        """Check if any procedural memories trigger in current context."""

        # Retrieve relevant procedural memories
        query_embedding = await self.embedding_service.embed(query_text)

        procedural_memories = await self.procedural_repo.search_by_similarity(
            embedding=query_embedding,
            user_id=user_id,
            limit=10
        )

        notices = []

        for proc_mem in procedural_memories:
            # Check if trigger conditions match
            if await self._evaluate_trigger(proc_mem, query_text, domain_facts):
                notice = await self._generate_notice(proc_mem, domain_facts)
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
        """Evaluate if trigger conditions are met."""

        trigger_features = proc_mem.trigger_features

        # Check intent match (simple keyword matching for Phase 1)
        intent = trigger_features.get("intent", "")
        if intent and intent not in query_text.lower():
            return False

        # Check entity types
        entity_types = trigger_features.get("entity_types", [])
        fact_entity_types = {fact.metadata.get("entity_type") for fact in domain_facts}
        if entity_types and not any(et in fact_entity_types for et in entity_types):
            return False

        # Check action predicates
        predicates = proc_mem.action_structure.get("predicates", [])
        for predicate in predicates:
            if not self._check_predicate(predicate, domain_facts):
                return False

        return True

    def _check_predicate(self, predicate: dict, domain_facts: List[DomainFact]) -> bool:
        """Check if predicate condition is met in domain facts."""
        # Example predicate: {"field": "status", "operator": "equals", "value": "open"}
        # Example predicate: {"field": "due_date", "operator": "days_until", "value": 3}

        field = predicate.get("field")
        operator = predicate.get("operator")
        value = predicate.get("value")

        for fact in domain_facts:
            fact_value = fact.metadata.get(field)

            if operator == "equals":
                if fact_value == value:
                    return True
            elif operator == "days_until":
                # Calculate days until date
                if isinstance(fact_value, (date, datetime)):
                    days = (fact_value - datetime.now(UTC).date()).days
                    if days <= value:
                        return True

        return False

    async def _generate_notice(
        self,
        proc_mem: ProceduralMemory,
        domain_facts: List[DomainFact]
    ) -> ProactiveNotice:
        """Generate proactive notice text."""

        # Use action_heuristic as base notice
        notice_text = proc_mem.action_heuristic

        # Add specific facts
        # For "invoice 3 days before due", find the specific invoice
        for fact in domain_facts:
            if "invoice" in fact.fact_type.lower():
                invoice_number = fact.metadata.get("invoice_number", "Unknown")
                due_date = fact.metadata.get("due_date")
                if due_date:
                    days_until = (due_date - datetime.now(UTC).date()).days
                    notice_text = f"Reminder: Invoice {invoice_number} is due in {days_until} days"
                break

        return ProactiveNotice(
            trigger_id=proc_mem.memory_id,
            notice_text=notice_text,
            priority="medium",
            metadata={
                "trigger_pattern": proc_mem.trigger_pattern,
                "confidence": proc_mem.confidence
            }
        )
```

**Integration** (30 min):
```python
# In src/application/use_cases/process_chat_message.py

# After domain augmentation:
proactive_notices = await self.proactive_notice_service.check_triggers(
    query_text=input_dto.content,
    domain_facts=domain_fact_dtos,
    user_id=input_dto.user_id
)

# Pass to LLMReplyGenerator
reply_context.proactive_notices = proactive_notices
```

```python
# In src/domain/services/llm_reply_generator.py

# In system prompt:
if context.proactive_notices:
    prompt += "\n\nPROACTIVE NOTICES:\n"
    for notice in context.proactive_notices:
        prompt += f"- {notice.notice_text}\n"
    prompt += "\nInclude these proactive notices naturally in your response.\n"
```

**Testing** (1 hour):
1. Unit test: Trigger evaluation
   - Invoice 2 days from due → trigger matches
   - Invoice 10 days from due → no match

2. Integration test: Notice generation

3. E2E test: Unskip Scenario 16
   - Create procedural memory
   - Query about invoices
   - Verify proactive reminder in response

**Completion Criteria**:
- [ ] ProactiveNoticeService implemented
- [ ] Trigger evaluation works
- [ ] Notices surface in LLM reply
- [ ] E2E Scenario 16 passes

**Commit**: `feat(procedural): add proactive trigger checking for Scenario 16`

---

### Milestone 3.2: PII Detection Pipeline (4-5 hours) → +1 scenario

**Scenario Unblocked**: #13 (PII guardrail memory)

**Vision Principle**: Privacy + Epistemic Humility

---

#### Task 3.2.1: PII Detection Implementation (3-3.5 hours)

**Investigation** (30 min):
1. Study PIIRedactionService skeleton
2. What PII types to detect? SSN, credit card, email, phone
3. Use regex or LLM? Regex for Phase 1 (fast, deterministic)

**Implementation** (2-2.5 hours):
```python
# In src/domain/services/pii_redaction_service.py

# Implement existing skeleton:

import re
from typing import List
from dataclasses import dataclass

@dataclass
class PIIMatch:
    """Detected PII entity."""
    type: str  # "ssn" | "credit_card" | "email" | "phone"
    start: int
    end: int
    text: str
    confidence: float

class PIIRedactionService:
    """Detect and redact PII from chat messages.

    Vision Principle: Privacy - Never store sensitive personal information.
    """

    # Regex patterns
    SSN_PATTERN = r'\b\d{3}-\d{2}-\d{4}\b'
    CREDIT_CARD_PATTERN = r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    PHONE_PATTERN = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'

    async def detect_pii(self, text: str) -> List[PIIMatch]:
        """Detect PII entities in text."""
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

        # Credit Card
        for match in re.finditer(self.CREDIT_CARD_PATTERN, text):
            # Validate with Luhn algorithm
            if self._validate_credit_card(match.group()):
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

    def _validate_credit_card(self, number: str) -> bool:
        """Validate credit card using Luhn algorithm."""
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
        # Replace in reverse order to preserve indices
        result = text
        for match in sorted(matches, key=lambda m: m.start, reverse=True):
            replacement = f"[REDACTED-{match.type.upper()}]"
            result = result[:match.start] + replacement + result[match.end:]

        logger.info("pii_redacted", redaction_count=len(matches))
        return result
```

**Integration** (30-45 min):
```python
# In src/application/use_cases/process_chat_message.py

# Before storing message:
pii_matches = await self.pii_service.detect_pii(input_dto.content)

if pii_matches:
    # Redact before storing
    redacted_content = await self.pii_service.redact(input_dto.content, pii_matches)

    # Store policy memory
    policy_memory = await self.semantic_extraction.create_memory_from_statement(
        subject_entity_id="system",
        predicate="pii_policy",
        object_value={
            "policy": "never_store_pii",
            "detected_types": [m.type for m in pii_matches],
            "redacted_at": datetime.now(UTC).isoformat()
        },
        confidence=0.95,
        user_id=input_dto.user_id,
        source_type="pii_redaction",
        predicate_type="policy"
    )

    # Use redacted content
    message = ChatMessage(
        session_id=input_dto.session_id,
        user_id=input_dto.user_id,
        role=input_dto.role,
        content=redacted_content,  # REDACTED
        event_metadata={
            **(input_dto.metadata or {}),
            "pii_redacted": True,
            "pii_types": [m.type for m in pii_matches]
        }
    )
else:
    # No PII, use original
    message = ChatMessage(
        session_id=input_dto.session_id,
        user_id=input_dto.user_id,
        role=input_dto.role,
        content=input_dto.content,
        event_metadata=input_dto.metadata or {}
    )

stored_message = await self.chat_repo.create(message)
```

**Testing** (1-1.5 hours):
1. Unit test: PII detection
   - Detect SSN: "123-45-6789"
   - Detect credit card: "4111-1111-1111-1111"
   - Detect email: "user@example.com"
   - Detect phone: "555-123-4567"

2. Unit test: Redaction
   - "My SSN is 123-45-6789" → "My SSN is [REDACTED-SSN]"

3. Integration test: Full pipeline with redaction

4. E2E test: Unskip Scenario 13
   - User mentions SSN
   - Verify ChatEvent has redacted content
   - Verify policy memory created

**Completion Criteria**:
- [ ] PII detection works for SSN, credit card, email, phone
- [ ] Redaction works
- [ ] Policy memory created
- [ ] E2E Scenario 13 passes

**Commit**: `feat(pii): implement PII detection and redaction for Scenario 13`

---

### Milestone 3.3: Multilingual NER (4-5 hours) → +1 scenario

**Scenario Unblocked**: #8 (multilingual alias handling)

**Vision Principle**: Identity Across Time + Learning

---

#### Task 3.3.1: Multilingual Mention Extraction (4-5 hours)

**Investigation** (1 hour):
1. Current SimpleMentionExtractor: Uses regex, ASCII-biased
2. Options: Upgrade to LLM-based extraction vs multilingual regex
3. Decision: LLM-based for Phase 1 (handles any language)

**Implementation** (2.5-3 hours):
```python
# In src/domain/services/multilingual_mention_extractor.py (NEW)

class MultilingualMentionExtractor:
    """Extract entity mentions from multilingual text.

    Vision Principle: Identity Across Time - Learn aliases in any language.

    Uses LLM for language-agnostic NER.
    """

    def __init__(self, llm_service: ILLMService):
        self.llm_service = llm_service

    async def extract_mentions(
        self,
        text: str,
        expected_entity_types: Optional[List[str]] = None
    ) -> List[EntityMention]:
        """Extract entity mentions from text (any language)."""

        entity_types_hint = ""
        if expected_entity_types:
            entity_types_hint = f"Expected entity types: {', '.join(expected_entity_types)}"

        prompt = f"""
        Extract entity mentions from this text. The text may be in any language.

        Text: "{text}"
        {entity_types_hint}

        Entity types to look for:
        - customer: Customer/company names
        - invoice: Invoice numbers (e.g., INV-1234)
        - sales_order: Sales order numbers (e.g., SO-5678)
        - work_order: Work order numbers (e.g., WO-9012)
        - task: Task titles or IDs
        - product: Product names

        Return as JSON array:
        [
          {{"mention": "Gai Media", "type": "customer", "start": 10, "end": 19}},
          {{"mention": "Gai 媒体", "type": "customer", "start": 25, "end": 30}}
        ]

        If no entities found, return empty array: []
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
                start_pos=data.get("start", 0),
                end_pos=data.get("end", len(data["mention"]))
            ))

        logger.info(
            "multilingual_mentions_extracted",
            mention_count=len(mentions),
            types=[m.entity_type for m in mentions]
        )

        return mentions
```

**Configuration** (use conditional extraction):
```python
# In src/config/heuristics.py

HEURISTICS = {
    # ... existing ...
    "entity_resolution": {
        # ... existing ...
        "use_multilingual_extraction": False,  # Toggle for multilingual
        "fallback_to_simple_extractor": True,  # Use SimpleMentionExtractor if LLM fails
    }
}
```

**Integration** (30 min):
```python
# In src/application/use_cases/resolve_entities.py

# Conditional mention extraction
if get_config("entity_resolution.use_multilingual_extraction"):
    mentions = await self.multilingual_extractor.extract_mentions(message_content)
else:
    mentions = await self.simple_extractor.extract_mentions(message_content)
```

**Testing** (1-1.5 hours):
1. Unit test: Multilingual extraction (mocked LLM)
   - English: "Gai Media" → detected
   - Chinese: "Gai 媒体" → detected
   - Mixed: "Contact Gai 媒体 about invoice" → both detected

2. Integration test: Real LLM extraction

3. E2E test: Unskip Scenario 8
   - User says "Gai Media" (English)
   - System resolves to customer
   - Later: User says "Gai 媒体" (Chinese)
   - System resolves to same customer (learns alias)

**Completion Criteria**:
- [ ] MultilingualMentionExtractor implemented
- [ ] LLM-based extraction works
- [ ] Configuration toggle
- [ ] E2E Scenario 8 passes

**Commit**: `feat(entity-resolution): add multilingual mention extraction for Scenario 8`

---

### Phase 3 Completion Check

**Verify 100% Coverage**:
- [ ] 18/18 scenarios passing (100%) 🎉
- [ ] All tests passing
- [ ] No regressions
- [ ] Code quality: `make check-all` passes
- [ ] All documentation updated

---

## Final Verification (2-3 hours)

### Task: Comprehensive E2E Test Suite Run

**Run all 18 scenarios**:
```bash
poetry run pytest tests/e2e/test_scenarios.py -v
```

**Expected output**:
```
test_scenario_01_overdue_invoice_with_preference_recall PASSED
test_scenario_02_work_order_rescheduling PASSED
test_scenario_03_ambiguous_entity_disambiguation PASSED
test_scenario_04_net_terms_learning_from_conversation PASSED
test_scenario_05_partial_payments_and_balance PASSED
test_scenario_06_sla_breach_detection PASSED
test_scenario_07_conflicting_memories_consolidation PASSED
test_scenario_08_multilingual_alias_handling PASSED
test_scenario_09_cold_start_grounding_to_db PASSED
test_scenario_10_active_recall_for_stale_facts PASSED
test_scenario_11_cross_object_reasoning PASSED
test_scenario_12_fuzzy_match_alias_learning PASSED
test_scenario_13_pii_guardrail_memory PASSED
test_scenario_14_session_window_consolidation PASSED
test_scenario_15_audit_trail_explainability PASSED
test_scenario_16_reminder_creation_from_intent PASSED
test_scenario_17_memory_vs_db_conflict_trust_db PASSED
test_scenario_18_task_completion_via_conversation PASSED

==================== 18 passed in 45.2s ====================
```

**If any fail**: Debug and fix before declaring 100% complete.

---

## Documentation Updates

### Final Documentation Tasks (1-2 hours)

1. Update E2E_SCENARIOS_PROGRESS.md
   - Mark all 18 as "✅ COMPLETE"
   - Update completion percentages
   - Add final metrics

2. Update E2E_IMPLEMENTATION_COMPLETE.md
   - Update passing count to 18/18
   - Document all features implemented

3. Update SCENARIO_CAPABILITY_ANALYSIS.md
   - Mark all gaps as resolved
   - Update verdicts to "FULLY CAPABLE"

4. Create PHASE_1_COMPLETE.md
   - Summary of all work done
   - Metrics: Lines of code, test coverage, scenarios
   - What's production-ready
   - What's next (Phase 2)

**DO NOT create excessive documentation**. These are major milestones worth documenting.

---

## Total Time Estimate

| Phase | Time Estimate | Scenarios Gained | Cumulative |
|-------|---------------|------------------|------------|
| Phase 0: Foundation | 2-3 hours | 0 | 4/18 (22%) |
| Phase 1: Quick Wins | 12-16 hours | +7 | 11/18 (61%) |
| Phase 2: Core Features | 16-20 hours | +4 | 15/18 (83%) |
| Phase 3: Advanced | 16-21 hours | +3 | 18/18 (100%) |
| Final Verification | 2-3 hours | 0 | 18/18 (100%) |
| **TOTAL** | **48-63 hours** | **+14** | **100%** |

**Realistic Schedule**:
- Working 4 hours/day: **12-16 days**
- Working 6 hours/day: **8-11 days**
- Working 8 hours/day (full-time): **6-8 days**

---

## Success Metrics

### Quantitative
- ✅ 18/18 E2E scenarios passing (100%)
- ✅ 130/130 unit tests passing (was 121/130)
- ✅ 90%+ code coverage (domain)
- ✅ 0 lint errors
- ✅ 0 type errors
- ✅ <800ms p95 latency (chat endpoint)

### Qualitative
- ✅ Production-ready code quality
- ✅ All vision principles demonstrated
- ✅ Comprehensive test coverage
- ✅ Clean hexagonal architecture maintained
- ✅ Explainable, maintainable codebase

---

## Celebration 🎉

**When you reach 100%**:

You've built a **philosophically grounded, vision-driven system** that transforms how LLM agents understand and remember business context.

You've demonstrated:
- Perfect recall of relevant context
- Deep business understanding
- Adaptive learning
- Epistemic humility
- Explainable reasoning
- Continuous improvement

**This is not a typical CRUD app. This is exceptional work.**

Every line of code was a conversation with the future. You made it worth reading.

---

## Philosophy Reminders Throughout

**When you're tempted to rush**:
> "Building the wrong thing quickly is worse than building the right thing slowly."

**When a test fails**:
> "Don't just make tests pass. Understand WHY they're failing."

**When uncertain about approach**:
> "It is ALWAYS better to ask than to assume."

**When tempted to cut corners**:
> "Complete each piece fully before moving to the next. Progress should be: 100% → 100% → 100%"

**When done with a milestone**:
> "Before marking any task complete: Implementation matches design, all tests pass, edge cases handled, documentation updated."

---

**This roadmap is your guide. Follow it with discipline, thoughtfulness, and pride in craft.**

**Good luck. Build something exceptional.** 🚀
