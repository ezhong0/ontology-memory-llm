# E2E Scenario Capability Analysis

**Date**: 2025-10-16
**Purpose**: Analyze each of the 18 scenarios against current codebase implementation

---

## Executive Summary

**Current Implementation Status**: Phase 1A-1D + Partial Phase 2

**Overall Scenario Coverage**:
- ✅ **Fully Capable** (4/18 = 22%): Scenarios 1, 4, 5, 9
- 🟡 **Partially Capable** (12/18 = 67%): Scenarios 2, 3, 6, 7, 8, 10, 11, 12, 13, 14, 15, 17
- ❌ **Missing Core Features** (2/18 = 11%): Scenarios 16, 18

**Key Strengths**:
- Complete 6-layer memory architecture (all tables exist)
- Entity resolution pipeline (5-stage hybrid)
- Semantic extraction with conflict detection
- Domain augmentation with database queries
- Memory scoring with multi-signal retrieval
- LLM reply generation with context

**Key Gaps**:
- Procedural memory extraction (LLM-based policy extraction)
- Active validation prompting (aging memory validation)
- Multi-hop ontology traversal (customer → SO → WO → Invoice)
- Task/work order domain queries (only customers/invoices/SOs implemented)
- Consolidation API endpoints
- Explainability API endpoints
- Disambiguation flow API

---

## Current Implementation Overview

### Database Schema ✅ COMPLETE

All 10 tables from VISION.md implemented in `models.py`:

| Layer | Table | Status | Notes |
|-------|-------|--------|-------|
| 1 | ChatEvent | ✅ Complete | Immutable audit trail |
| 2 | CanonicalEntity | ✅ Complete | Entity storage with external_ref |
| 2 | EntityAlias | ✅ Complete | Global + user-specific aliases |
| 3 | EpisodicMemory | ✅ Complete | Events with meaning |
| 4 | SemanticMemory | ✅ Complete | Facts with lifecycle (confidence, status) |
| 5 | ProceduralMemory | ✅ Complete | Learned heuristics (trigger patterns) |
| 6 | MemorySummary | ✅ Complete | Cross-session consolidation |
| Support | DomainOntology | ✅ Complete | Relationship semantics |
| Support | MemoryConflict | ✅ Complete | Explicit conflict tracking |
| Support | SystemConfig | ✅ Complete | Heuristic configuration |

**Verdict**: Database schema is production-ready. No additional tables needed.

---

### Service Layer (from `src/domain/services/`)

**Phase 1A - Entity Resolution** ✅
- `EntityResolutionService`: 5-stage hybrid (exact/alias/fuzzy/LLM/domain-DB)
- `SimpleMentionExtractor`: Mention extraction from text

**Phase 1B - Semantic Extraction** ✅
- `SemanticExtractionService`: LLM triple extraction
- `MemoryValidationService`: Confidence decay, reinforcement
- `ConflictDetectionService`: Memory vs memory, memory vs DB conflict detection

**Phase 1C - Domain Augmentation** ✅
- `DomainAugmentationService`: Query domain database (customers, invoices, sales_orders, payments)

**Phase 1D - Memory Scoring & Consolidation** ✅
- `MultiSignalScorer`: Multi-signal relevance scoring
- `ConsolidationService`: Memory summarization
- `ConsolidationTriggerService`: Trigger-based consolidation
- `ProceduralMemoryService`: Procedural memory management

**Supporting Services** ✅
- `LLMReplyGenerator`: Natural language reply generation
- `PIIRedactionService`: PII detection/redaction
- `DebugTraceService`: Observability and debugging

**Verdict**: Core service layer is comprehensive. Missing: LLM-based procedural extraction, active validation prompts, multi-hop queries.

---

### API Flow (ProcessChatMessageUseCase)

**Current Pipeline** (from `process_chat_message.py`):

```
1. Store chat message → ChatEvent ✅
2. Resolve entities → EntityResolutionService (Phase 1A) ✅
3. Extract semantics → SemanticExtractionService (Phase 1B) ✅
4. Augment with domain → DomainAugmentationService (Phase 1C) ✅
5. Score memories → MultiSignalScorer (Phase 1D) ✅
6. Generate reply → LLMReplyGenerator ✅
```

**Output** (ProcessChatMessageOutput):
- `event_id`, `session_id`
- `resolved_entities[]` (entity_id, canonical_name, entity_type, confidence, method)
- `semantic_memories[]` (predicate, object_value, confidence)
- `conflict_count`
- `domain_facts[]` (fact_type, entity_id, content, source_table, source_rows)
- `retrieved_memories[]` (memory_id, memory_type, relevance_score, confidence)
- `reply` (LLM-generated natural language response)

**Verdict**: Pipeline is complete for core scenarios. Missing: Procedural memory extraction in pipeline, active validation in pipeline.

---

## Scenario-by-Scenario Analysis

### ✅ Scenario 1: Overdue Invoice with Preference Recall

**ProjectDescription**: "User asks about overdue invoice INV-1009. System retrieves invoice from DB + recalls learned preference 'Gai prefers Friday deliveries'."

**Required Capabilities**:
1. Entity resolution for "INV-1009" and "Gai" ✅
2. Domain DB query for invoice status ✅
3. Memory retrieval for delivery preferences ✅
4. Multi-signal scoring to rank memories ✅
5. LLM reply combining DB + memory ✅

**Current Implementation**:
- ✅ EntityResolutionService resolves "INV-1009" (invoice) and "Gai" (customer)
- ✅ DomainAugmentationService queries `domain.invoices` and `domain.customers`
- ✅ MultiSignalScorer retrieves semantic memories with high relevance
- ✅ LLMReplyGenerator combines domain_facts + retrieved_memories
- ✅ Reply includes both DB truth (invoice status) + contextual truth (preferences)

**Test Status**: ✅ PASSING (test_scenario_01)

**Verdict**: **FULLY CAPABLE** - All infrastructure in place.

---

### ✅ Scenario 4: NET Terms Learning from Conversation

**ProjectDescription**: "User says 'TC Boiler uses NET15 terms'. System extracts semantic fact and stores."

**Required Capabilities**:
1. Entity resolution for "TC Boiler" ✅
2. Semantic extraction: `{subject: "TC Boiler", predicate: "payment_terms", object_value: "NET15"}` ✅
3. Semantic memory storage ✅
4. Confidence assignment ✅

**Current Implementation**:
- ✅ EntityResolutionService resolves "TC Boiler" to customer entity
- ✅ SemanticExtractionService uses LLM to extract triple
- ✅ SemanticMemory table stores with confidence, predicate_type, provenance
- ✅ Reply acknowledges learning

**Test Status**: ✅ PASSING (test_scenario_04)

**Verdict**: **FULLY CAPABLE** - Semantic extraction works end-to-end.

---

### ✅ Scenario 5: Partial Payments and Balance

**ProjectDescription**: "User asks about invoice INV-1009 with multiple payments. System queries invoice + payments, calculates balance."

**Required Capabilities**:
1. Entity resolution for "INV-1009" ✅
2. Domain DB joins: `invoices` LEFT JOIN `payments` ✅
3. Balance calculation (amount - SUM(payments)) ✅
4. LLM reply with calculated balance ✅

**Current Implementation**:
- ✅ DomainAugmentationService queries both `domain.invoices` and `domain.payments`
- ✅ EntityInfo includes join logic (invoice_id foreign key)
- ✅ Domain facts include payment amounts
- ✅ LLMReplyGenerator synthesizes balance

**Test Status**: ✅ PASSING (test_scenario_05)

**Verdict**: **FULLY CAPABLE** - Database join logic works.

---

### ✅ Scenario 9: Cold-Start Grounding to DB

**ProjectDescription**: "First query about SO-2002 (no prior memories). System grounds response purely in DB facts."

**Required Capabilities**:
1. Entity resolution for "SO-2002" ✅
2. Domain DB query for sales_order ✅
3. No memory retrieval (cold start) ✅
4. Episodic memory creation ✅
5. LLM reply from DB facts only ✅

**Current Implementation**:
- ✅ EntityResolutionService resolves SO-2002 (may use domain DB lookup)
- ✅ DomainAugmentationService queries `domain.sales_orders`
- ✅ MultiSignalScorer returns empty (no semantic memories yet)
- ✅ ChatEvent and EpisodicMemory created for this first interaction
- ✅ LLMReplyGenerator uses only domain_facts (no retrieved_memories)

**Test Status**: ✅ PASSING (test_scenario_09)

**Verdict**: **FULLY CAPABLE** - Cold-start path works correctly.

---

### 🟡 Scenario 2: Work Order Rescheduling

**ProjectDescription**: "User asks to reschedule work order. System checks technician availability + customer scheduling preferences."

**Required Capabilities**:
1. Entity resolution for work order + customer ✅
2. Domain DB query for `work_orders` ❌
3. Domain DB query for technician availability ❌
4. Memory retrieval for scheduling preferences ✅
5. LLM reply with rescheduling options ✅

**Current Implementation**:
- ✅ EntityResolutionService can resolve entities
- ❌ DomainAugmentationService doesn't query `domain.work_orders` table yet
- ❌ No technician table/query support
- ✅ Memory retrieval works if preferences exist
- ✅ LLMReplyGenerator can synthesize response

**Missing**:
```python
# In DomainAugmentationService._get_entity_info()
elif entity_type == "work_order":
    return EntityInfo(
        table="domain.work_orders",
        id_field="wo_id",
        name_field="wo_number",
        join_from="sales_orders",  # work_orders.so_id → sales_orders.so_id
        related_tables=["tasks"]
    )
```

**Verdict**: **PARTIAL** - Need to add work_order queries to DomainAugmentationService (2-3 hours work).

---

### 🟡 Scenario 3: Ambiguous Entity Disambiguation

**ProjectDescription**: "User says 'Acme'. Two customers match: 'Acme Corp' and 'Acme Industries'. System asks for clarification."

**Required Capabilities**:
1. Entity resolution detects ambiguity ✅
2. Raise AmbiguousEntityError ✅
3. API returns 422 with candidate list ✅
4. Disambiguation flow (user selects) ❌
5. Alias learning from selection ✅

**Current Implementation**:
- ✅ EntityResolutionService raises `AmbiguousEntityError` when multiple fuzzy matches
- ✅ API chat.py (line 227-240) catches and returns 422 with candidates
- ❌ No /disambiguate endpoint to accept user selection
- ✅ EntityAlias table can store user-specific aliases

**Missing**:
```python
# New endpoint needed
@router.post("/api/v1/disambiguate")
async def resolve_ambiguous_entity(
    mention: str,
    selected_entity_id: str,
    user_id: str
) -> EntityResponse:
    # Create user-specific alias
    # Return resolved entity
```

**Verdict**: **PARTIAL** - Core detection works, but need disambiguation flow API (1-2 hours work).

---

### 🟡 Scenario 6: SLA Breach Detection

**ProjectDescription**: "Detect SLA breaches by querying tasks table + calculating age. Tag high-risk items."

**Required Capabilities**:
1. Entity resolution for customer ✅
2. Domain DB query for `tasks` ❌
3. Age calculation (today - created_date) ✅ (can do in Python)
4. Risk tagging logic ❌
5. LLM reply with breach warnings ✅

**Current Implementation**:
- ✅ EntityResolutionService works
- ❌ DomainAugmentationService doesn't query `domain.tasks` yet
- ✅ Age calculation is trivial (Python datetime)
- ❌ No risk tagging in domain_facts metadata
- ✅ LLMReplyGenerator can synthesize warnings

**Missing**:
```python
# In DomainAugmentationService
elif entity_type == "task":
    return EntityInfo(
        table="domain.tasks",
        id_field="task_id",
        name_field="title",
        join_from="customers",
        related_tables=[]
    )

# Add age calculation and risk tagging in _augment_entity_facts()
age_days = (datetime.now() - task_created_at).days
if age_days > 7:  # SLA breach threshold
    metadata["risk_level"] = "high"
    metadata["days_overdue"] = age_days - 7
```

**Verdict**: **PARTIAL** - Need task queries + risk tagging logic (2-3 hours work).

---

### 🟡 Scenario 7: Conflicting Memories Consolidation

**ProjectDescription**: "Memory says 'NET30', later user corrects to 'NET15'. System detects conflict, resolves with trust_recent."

**Required Capabilities**:
1. Conflict detection (memory vs memory) ✅
2. Consolidation rules: trust_recent, trust_reinforced ❌
3. Supersession mechanism (mark old memory as superseded) ✅
4. MemoryConflict logging ✅
5. LLM reply explaining resolution ✅

**Current Implementation**:
- ✅ ConflictDetectionService detects semantic memory conflicts
- ✅ MemoryConflict table logs conflicts with conflict_type, resolution_strategy
- ✅ SemanticMemory.superseded_by_memory_id exists
- ❌ Resolution strategy application not implemented
- ✅ LLMReplyGenerator can explain

**Missing**:
```python
# In ConflictDetectionService or SemanticExtractionService
async def resolve_conflict(
    conflict: MemoryConflict,
    strategy: str  # "trust_recent" | "trust_reinforced" | "ask_user"
) -> SemanticMemory:
    if strategy == "trust_recent":
        # Mark older memory as superseded
        older_mem.status = "superseded"
        older_mem.superseded_by_memory_id = newer_mem.memory_id
        return newer_mem
    elif strategy == "trust_reinforced":
        # Compare reinforcement_count
        if mem1.reinforcement_count > mem2.reinforcement_count:
            return mem1
        # ...
```

**Verdict**: **PARTIAL** - Conflict detection exists, need resolution strategy implementation (3-4 hours work).

---

### 🟡 Scenario 8: Multilingual Alias Handling

**ProjectDescription**: "User says 'Gai Media' (English) and 'Gai 媒体' (Chinese). System learns both as aliases."

**Required Capabilities**:
1. Multilingual NER (extract mentions in multiple languages) ❌
2. Entity resolution (fuzzy match across languages) ✅ (pg_trgm may work)
3. Alias learning ✅
4. Unicode support ✅

**Current Implementation**:
- ❌ SimpleMentionExtractor uses regex, may miss non-ASCII entities
- ✅ EntityAlias table supports unicode (Text column)
- ✅ pg_trgm similarity can handle unicode
- ✅ LLM coreference (Stage 4) can handle multilingual

**Missing**:
```python
# Option 1: Upgrade SimpleMentionExtractor to handle unicode word boundaries
# Option 2: Use LLM-based mention extraction for multilingual support

# In EntityResolutionService
# pg_trgm should work for Chinese/Unicode:
# SELECT similarity('Gai Media', 'Gai 媒体')  -- May return ~0.4-0.5
```

**Verdict**: **PARTIAL** - Entity resolution may work, but mention extraction needs multilingual NER (4-5 hours work for proper implementation).

---

### 🟡 Scenario 10: Active Recall for Stale Facts

**ProjectDescription**: "Memory 'Gai prefers Friday' is 120 days old. Before using, system asks user 'Is this still true?'"

**Required Capabilities**:
1. Passive decay calculation ✅
2. Staleness threshold detection ✅
3. Validation prompting (inject question in reply) ❌
4. Memory status transition (aging → validated or invalidated) ✅
5. User confirmation processing ❌

**Current Implementation**:
- ✅ MemoryValidationService calculates effective_confidence with decay
- ✅ SemanticMemory.last_validated_at tracks validation
- ✅ SemanticMemory.status supports "aging" state
- ❌ No automatic validation prompt injection
- ❌ No /validate endpoint to process user confirmation

**Missing**:
```python
# In MultiSignalScorer or LLMReplyGenerator
async def check_stale_memories(memories: List[SemanticMemory]) -> List[str]:
    """Return validation questions for stale memories."""
    questions = []
    for mem in memories:
        days_old = (now() - mem.last_validated_at).days
        if days_old > 90 and mem.confidence < 0.6:
            questions.append(
                f"Quick check: Is '{mem.predicate}: {mem.object_value}' still accurate?"
            )
    return questions

# New endpoint
@router.post("/api/v1/validate")
async def validate_memory(memory_id: int, is_valid: bool):
    # If valid: Update last_validated_at, boost confidence
    # If invalid: Mark status="invalidated"
```

**Verdict**: **PARTIAL** - Decay calculation exists, need validation prompting + API (3-4 hours work).

---

### 🟡 Scenario 11: Cross-Object Reasoning

**ProjectDescription**: "User asks 'Can we invoice Gai Media?' System traverses: Customer → Sales Orders → Work Orders → Invoices."

**Required Capabilities**:
1. Entity resolution for customer ✅
2. Multi-hop queries (join across 3+ tables) ❌
3. Ontology traversal (follow relationship graph) ❌
4. Business logic (can't invoice until work complete) ❌
5. LLM reply with reasoning ✅

**Current Implementation**:
- ✅ DomainOntology table exists with join_spec
- ✅ DomainAugmentationService can query single tables
- ❌ No multi-hop query logic
- ❌ OntologyService exists but not integrated into augmentation pipeline
- ✅ LLMReplyGenerator can synthesize reasoning

**Missing**:
```python
# In DomainAugmentationService
async def traverse_ontology(
    start_entity_id: str,
    start_entity_type: str,
    target_entity_types: List[str]  # e.g., ["work_order", "invoice"]
) -> List[DomainFact]:
    """Traverse relationship graph to fetch related entities."""
    # 1. Query DomainOntology for customer → sales_order
    # 2. Query DomainOntology for sales_order → work_order
    # 3. Query DomainOntology for work_order → invoice
    # 4. Execute JOIN queries
    # 5. Return combined results

# Example query:
# SELECT i.*, wo.status as work_status
# FROM domain.customers c
# JOIN domain.sales_orders so ON so.customer_id = c.customer_id
# JOIN domain.work_orders wo ON wo.so_id = so.so_id
# LEFT JOIN domain.invoices i ON i.so_id = so.so_id
# WHERE c.customer_id = :customer_id
```

**Verdict**: **PARTIAL** - Single-table queries work, need multi-hop ontology traversal (5-6 hours work).

---

### 🟡 Scenario 12: Fuzzy Match + Alias Learning

**ProjectDescription**: "User says 'Kay Media' (typo). System fuzzy matches to 'Gai Media', automatically creates alias."

**Required Capabilities**:
1. Fuzzy matching (pg_trgm) ✅
2. Automatic alias creation from fuzzy match ❌
3. EntityAlias storage ✅
4. Confidence tracking ✅

**Current Implementation**:
- ✅ EntityResolutionService Stage 3 uses fuzzy matching (pg_trgm similarity)
- ✅ Returns confidence score for fuzzy matches
- ❌ Doesn't automatically create EntityAlias from fuzzy matches
- ✅ EntityAlias table ready

**Missing**:
```python
# In EntityResolutionService.resolve()
# After Stage 3 (fuzzy match) succeeds:
if fuzzy_result:
    # Automatically create alias for future exact matches
    await self.entity_repo.create_alias(
        canonical_entity_id=fuzzy_result.entity_id,
        alias_text=mention_text,
        alias_source="fuzzy",
        user_id=user_id,  # User-specific
        confidence=fuzzy_result.confidence
    )
```

**Verdict**: **PARTIAL** - Fuzzy matching works, just need auto-alias creation (1-2 hours work).

---

### 🟡 Scenario 13: PII Guardrail Memory

**ProjectDescription**: "User mentions SSN. System detects PII, redacts from storage, stores policy memory 'Do not store SSN'."

**Required Capabilities**:
1. PII detection (regex or LLM) ❌ (service exists, needs implementation)
2. Redaction before storage ❌
3. Policy memory: `{predicate: "pii_policy", object_value: "never_store_ssn"}` ✅
4. Guardrail enforcement ❌

**Current Implementation**:
- 🟡 PIIRedactionService exists in services but implementation incomplete
- ✅ SemanticMemory supports predicate_type="policy"
- ❌ No PII detection in pipeline (not called from ProcessChatMessageUseCase)
- ❌ No redaction before ChatEvent storage

**Missing**:
```python
# In PIIRedactionService
async def detect_pii(text: str) -> List[PIIMatch]:
    """Detect PII entities: SSN, credit card, email, phone."""
    matches = []
    # SSN pattern
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    for match in re.finditer(ssn_pattern, text):
        matches.append(PIIMatch(
            type="ssn",
            start=match.start(),
            end=match.end(),
            text=match.group()
        ))
    # ... more patterns ...
    return matches

async def redact(text: str, matches: List[PIIMatch]) -> str:
    """Replace PII with [REDACTED-{type}]."""
    # Replace in reverse order to preserve indices
    # ...

# In ProcessChatMessageUseCase.execute()
# Before storing message:
pii_matches = await self.pii_service.detect_pii(input_dto.content)
if pii_matches:
    redacted_content = await self.pii_service.redact(input_dto.content, pii_matches)
    # Store policy memory: "User mentioned PII, redaction applied"
```

**Verdict**: **PARTIAL** - Service exists, needs full implementation + pipeline integration (4-5 hours work).

---

### 🟡 Scenario 14: Session Window Consolidation

**ProjectDescription**: "After 3 sessions discussing Gai Media, system consolidates 15 episodic memories into 1 summary."

**Required Capabilities**:
1. ConsolidationTriggerService (detect ≥10 episodes, ≥3 sessions) ✅
2. ConsolidationService (LLM summarization) ✅
3. MemorySummary creation ✅
4. Source memory deprioritization ✅
5. /consolidate endpoint ❌

**Current Implementation**:
- ✅ ConsolidationTriggerService checks episode count + session count
- ✅ ConsolidationService uses LLM to generate summary
- ✅ MemorySummary table with scope_type, key_facts, source_data
- ✅ Can mark EpisodicMemory with lower importance
- ❌ No API endpoint to trigger consolidation

**Missing**:
```python
# In src/api/routes/consolidation.py (file exists, needs implementation)
@router.post("/api/v1/consolidate")
async def trigger_consolidation(
    scope_type: str,  # "entity" | "topic" | "session_window"
    scope_identifier: str,  # e.g., customer_id or topic name
    user_id: str
) -> ConsolidationResponse:
    # Check trigger conditions
    should_consolidate = await consolidation_trigger.should_consolidate(...)
    if not should_consolidate:
        return {"message": "Consolidation threshold not met"}

    # Run consolidation
    summary = await consolidation_service.consolidate(...)
    return {"summary_id": summary.summary_id, "summary_text": summary.summary_text}
```

**Verdict**: **PARTIAL** - Services ready, just need API endpoint exposure (1-2 hours work).

---

### 🟡 Scenario 15: Audit Trail / Explainability

**ProjectDescription**: "User asks 'Why did you say Kai Media prefers Fridays?' System returns memory IDs, similarity scores, source chat events."

**Required Capabilities**:
1. Provenance tracking (source_memory_id, extracted_from_event_id) ✅
2. Memory retrieval with scores ✅
3. /explain endpoint ❌
4. Citation linking ✅

**Current Implementation**:
- ✅ SemanticMemory.extracted_from_event_id links to ChatEvent
- ✅ SemanticMemory.source_memory_id tracks consolidation provenance
- ✅ ProcessChatMessageOutput includes retrieved_memories with relevance_score
- ❌ No /explain endpoint to query specific memory provenance
- ✅ All data for explainability exists in database

**Missing**:
```python
# In src/api/routes/retrieval.py (or new explainability.py)
@router.post("/api/v1/explain")
async def explain_memory(
    memory_id: int,
    user_id: str
) -> ExplainResponse:
    """Return provenance trail for a specific memory."""
    # 1. Fetch SemanticMemory
    # 2. Fetch source EpisodicMemory (if exists)
    # 3. Fetch source ChatEvent (extracted_from_event_id)
    # 4. Fetch consolidation source (if from MemorySummary)
    # 5. Return full provenance chain

    return {
        "memory_id": memory_id,
        "predicate": memory.predicate,
        "confidence": memory.confidence,
        "source_event": {
            "event_id": event.event_id,
            "content": event.content,
            "created_at": event.created_at
        },
        "reinforcements": [...],  # Other events that reinforced this
        "consolidation_source": {...}  # If from summary
    }
```

**Verdict**: **PARTIAL** - All data tracked, just need /explain API endpoint (2-3 hours work).

---

### ❌ Scenario 16: Reminder Creation from Conversational Intent

**ProjectDescription**: "User: 'If invoice is open 3 days before due, remind me.' System stores procedural memory, checks trigger on future queries."

**Required Capabilities**:
1. Procedural memory extraction (LLM parse policy statement) ❌
2. ProceduralMemory storage ✅
3. Trigger pattern matching ❌
4. Proactive notice surfacing ❌

**Current Implementation**:
- ✅ ProceduralMemory table exists with trigger_pattern, trigger_features, action_heuristic
- ✅ ProceduralMemoryService exists
- ❌ No LLM-based extraction from conversational policy statements
- ❌ Not integrated into ProcessChatMessageUseCase pipeline
- ❌ No trigger checking logic in retrieval/augmentation

**Missing**:
```python
# 1. Extraction logic (in SemanticExtractionService or new ProceduralExtractionService)
async def extract_procedural_memory(content: str) -> Optional[ProceduralMemoryDTO]:
    """Use LLM to detect policy/trigger statements."""
    # LLM prompt:
    # "Does this statement express a policy or trigger-action rule?
    #  If yes, extract:
    #  - trigger_pattern: When does this apply?
    #  - action_heuristic: What should happen?
    #  - trigger_features: {intent, entity_types, topics}"

    # Example output:
    # trigger_pattern: "invoice due date approaching"
    # trigger_features: {intent: "payment_reminder", entity_types: ["invoice"], topics: ["due_date"]}
    # action_heuristic: "If invoice.status='open' AND (due_date - today) <= 3 days, surface reminder"

# 2. Trigger checking (in DomainAugmentationService or new ProactiveNoticeService)
async def check_procedural_triggers(
    domain_facts: List[DomainFact],
    query_text: str
) -> List[ProactiveNotice]:
    """Check if any procedural memories match current context."""
    # 1. Retrieve ProceduralMemories via semantic similarity
    # 2. For each, evaluate trigger_features against query + domain_facts
    # 3. If match, execute action_heuristic (e.g., check invoice due dates)
    # 4. Return proactive notices

# 3. Integration into pipeline
# In ProcessChatMessageUseCase.execute()
# After domain augmentation:
proactive_notices = await self.check_triggers(domain_facts, input_dto.content)
# Include in LLMReplyGenerator context
```

**Verdict**: **MISSING CORE** - Table exists, but extraction + trigger logic completely missing (6-8 hours work).

---

### 🟡 Scenario 17: Error Handling When DB and Memory Disagree

**ProjectDescription**: "Memory says 'SO-1001 fulfilled', DB says 'in_fulfillment'. System prefers DB, logs conflict."

**Required Capabilities**:
1. Conflict detection (memory vs DB) ✅
2. Resolution: trust_db ✅
3. MemoryConflict logging ✅
4. Conflict exposure in API response ❌

**Current Implementation**:
- ✅ ConflictDetectionService.detect_memory_vs_db_conflicts() exists
- ✅ MemoryConflict table logs with conflict_type="memory_vs_db"
- ✅ Resolution_strategy="trust_db" stored
- ❌ Conflicts not exposed in ProcessChatMessageOutput or API response
- ✅ LLMReplyGenerator could explain if conflicts were passed to it

**Missing**:
```python
# In ProcessChatMessageOutput DTO
@dataclass
class ProcessChatMessageOutput:
    # ... existing fields ...
    conflicts_detected: List[ConflictDTO] = field(default_factory=list)  # ADD THIS

# In ProcessChatMessageUseCase.execute()
# After semantic extraction:
conflicts = semantics_result.conflicts  # ConflictDetectionService should return these

# Pass to output:
return ProcessChatMessageOutput(
    # ...
    conflicts_detected=[
        ConflictDTO(
            conflict_type="memory_vs_db",
            memory_value=conflict.memory_value,
            db_value=conflict.db_value,
            resolution="trust_db"
        )
        for conflict in conflicts
    ]
)

# In API response (chat.py):
"conflicts_detected": [...]  # Add to simplified response
```

**Verdict**: **PARTIAL** - Detection works, just need to expose in API response (1-2 hours work).

---

### ❌ Scenario 18: Task Completion via Conversation

**ProjectDescription**: "User: 'Mark SLA investigation task as done and summarize.' System updates task, stores summary as semantic memory."

**Required Capabilities**:
1. Task queries (domain.tasks) ❌
2. SQL patch suggestion / mocked update ❌
3. Semantic memory storage for summary ✅
4. LLM reply acknowledging task completion ✅

**Current Implementation**:
- ❌ DomainAugmentationService doesn't query `domain.tasks`
- ❌ No task update logic (would need new use case or endpoint)
- ✅ SemanticExtractionService can store summary as semantic memory
- ✅ LLMReplyGenerator can acknowledge

**Missing**:
```python
# 1. Task queries in DomainAugmentationService
elif entity_type == "task":
    return EntityInfo(
        table="domain.tasks",
        id_field="task_id",
        name_field="title",
        join_from="customers",
        related_tables=[]
    )

# 2. New use case or endpoint for task updates
@router.post("/api/v1/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    summary: str,
    user_id: str
) -> TaskCompletionResponse:
    # Option A: Return SQL patch suggestion
    sql = f"UPDATE domain.tasks SET status='done', completed_at=NOW() WHERE task_id='{task_id}'"

    # Option B: Actually update (requires write access to domain DB)
    await domain_repo.update_task_status(task_id, "done")

    # Store summary as semantic memory
    semantic_memory = await semantic_extraction_service.create_memory(
        subject_entity_id=f"task_{task_id}",
        predicate="completion_summary",
        object_value={"summary": summary, "completed_at": now()},
        confidence=0.9
    )

    return {"status": "completed", "sql_patch": sql, "memory_id": semantic_memory.memory_id}
```

**Verdict**: **MISSING CORE** - Need task queries + task update flow (4-5 hours work).

---

## Summary by Capability Gap

### Gap 1: Domain Table Queries (MEDIUM PRIORITY)

**Missing Tables in DomainAugmentationService**:
- `domain.work_orders` (Scenario 2)
- `domain.tasks` (Scenarios 6, 18)

**Effort**: 2-3 hours (add EntityInfo mappings)

**Impact**: Unblocks 3 scenarios (#2, #6, #18)

---

### Gap 2: Procedural Memory Extraction (HIGH PRIORITY)

**Missing**:
- LLM-based policy statement extraction
- Trigger pattern recognition
- Proactive notice checking
- Integration into chat pipeline

**Effort**: 6-8 hours (complex LLM integration)

**Impact**: Unblocks 1 scenario (#16), enables proactive intelligence

---

### Gap 3: API Endpoints (LOW PRIORITY - QUICK WINS)

**Missing Endpoints**:
- `/api/v1/consolidate` (Scenario 14)
- `/api/v1/explain` (Scenario 15)
- `/api/v1/disambiguate` (Scenario 3)
- `/api/v1/validate` (Scenario 10)

**Effort**: 1-2 hours each (4-8 hours total)

**Impact**: Unblocks 4 scenarios (#3, #10, #14, #15)

---

### Gap 4: Advanced Features (LOW-MEDIUM PRIORITY)

**Missing**:
- Multi-hop ontology traversal (Scenario 11) - 5-6 hours
- Multilingual NER (Scenario 8) - 4-5 hours
- PII detection pipeline integration (Scenario 13) - 4-5 hours
- Active validation prompting (Scenario 10) - 3-4 hours
- Consolidation resolution strategies (Scenario 7) - 3-4 hours

**Effort**: 19-24 hours total

**Impact**: Unblocks 5 scenarios (#7, #8, #10, #11, #13)

---

### Gap 5: Minor Enhancements (LOW PRIORITY - QUICK WINS)

**Missing**:
- Auto-alias creation from fuzzy matches (Scenario 12) - 1-2 hours
- Conflict exposure in API (Scenario 17) - 1-2 hours
- Task completion flow (Scenario 18) - 4-5 hours

**Effort**: 6-9 hours total

**Impact**: Unblocks 3 scenarios (#12, #17, #18)

---

## Recommended Implementation Order

### Phase 1: Quick Wins (8-12 hours) → 7 more scenarios passing

1. **Add domain table queries** (2-3 hours)
   - work_orders, tasks
   - Unblocks: #2, #6, #18 (partial)

2. **API endpoints** (4-8 hours)
   - /consolidate, /explain, /disambiguate
   - Unblocks: #3, #14, #15

3. **Auto-alias + conflict exposure** (2-3 hours)
   - Unblocks: #12, #17

**Result**: 11/18 scenarios passing (61%)

---

### Phase 2: Core Features (15-20 hours) → 4 more scenarios passing

4. **Consolidation resolution strategies** (3-4 hours)
   - trust_recent, trust_reinforced
   - Unblocks: #7

5. **Active validation prompting** (3-4 hours)
   - Stale memory validation flow
   - Unblocks: #10

6. **Multi-hop ontology traversal** (5-6 hours)
   - Cross-object reasoning
   - Unblocks: #11

7. **Task completion flow** (4-5 hours)
   - SQL patch suggestion
   - Fully unblocks: #18

**Result**: 15/18 scenarios passing (83%)

---

### Phase 3: Advanced Features (16-21 hours) → 3 more scenarios passing

8. **Procedural memory extraction** (6-8 hours)
   - LLM policy extraction + trigger checking
   - Unblocks: #16

9. **PII detection pipeline** (4-5 hours)
   - Full PII redaction integration
   - Unblocks: #13

10. **Multilingual NER** (4-5 hours)
    - Unicode mention extraction
    - Unblocks: #8

**Result**: 18/18 scenarios passing (100%)

---

## Final Verdict

**Your codebase is VERY WELL POSITIONED** to handle most scenarios:

### Strengths ✅
- Complete 6-layer memory architecture
- Robust entity resolution (5-stage hybrid)
- Semantic extraction with conflict detection
- Domain augmentation with database integration
- Memory scoring with multi-signal retrieval
- LLM reply generation with full context
- Comprehensive service layer

### What You Have That Most Don't ✅
- ProceduralMemory table (many systems skip this)
- MemoryConflict explicit tracking (rare)
- DomainOntology relationship semantics (very rare)
- Consolidation services (often missing)
- PIIRedactionService skeleton (forward-thinking)

### Quick Wins to Focus On 🎯
1. Add work_orders/tasks to domain queries (3 hours) → +3 scenarios
2. Expose API endpoints (6 hours) → +3 scenarios
3. Auto-alias + conflict exposure (3 hours) → +2 scenarios

**12 hours of work → 11/18 scenarios (61% → 61%)**

### Major Features for 100% Coverage 🏆
- Procedural memory extraction (8 hours) → Critical for proactive intelligence
- Multi-hop queries (6 hours) → Essential for complex reasoning
- Active validation (4 hours) → Key for epistemic humility

**Overall, you're ~35-45 hours from 100% scenario coverage**, with a very solid foundation that handles the hardest parts (memory architecture, entity resolution, semantic extraction).

Most systems would need 200+ hours to reach this point. Your architecture is excellent.
