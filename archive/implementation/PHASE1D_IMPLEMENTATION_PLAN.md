# Phase 1D Implementation Plan: Learning Layer

**Date**: 2025-10-15
**Phase**: Learning (Week 7-8)
**Milestone**: Consolidation + Procedural patterns operational

---

## Executive Summary

Phase 1D adds the **Learning Layer** - the system's ability to consolidate memories into summaries and detect procedural patterns from repeated interactions. This completes the full vision implementation.

### Vision Principles Served

1. **Learning from patterns** - Procedural memory captures "When X, also Y" heuristics
2. **Graceful forgetting** - Consolidation compresses detail into essence
3. **Continuous improvement** - Each conversation makes future ones better

### What Phase 1D Delivers

1. ✅ **ConsolidationService** (Layer 4→6 transition)
   - LLM synthesis of episodic + semantic → summaries
   - Confidence boosting for validated facts
   - Supersedes old summaries

2. ✅ **ProceduralMemoryService** (Layer 3→5 transition)
   - Pattern detection from episodic memories
   - Query pattern learning
   - Action heuristic extraction

3. ✅ **Complete API**
   - POST /api/v1/consolidate
   - GET /api/v1/summaries/{scope_type}/{scope_identifier}
   - Enhanced POST /api/v1/chat with full pipeline

4. ✅ **Comprehensive Tests**
   - Unit tests for all services
   - Integration tests (end-to-end)
   - Performance benchmarks

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              PHASE 1D: LEARNING LAYER                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Episodic Memories (Layer 3)                            │
│         ↓                           ↓                   │
│         ↓                           ↓                   │
│  Pattern Detection           LLM Synthesis              │
│         ↓                           ↓                   │
│         ↓                           ↓                   │
│  Procedural Memories      Memory Summaries              │
│  (Layer 5)                (Layer 6)                     │
│         ↓                           ↓                   │
│         ↓                           ↓                   │
│  Query augmentation        Context compression          │
│  ("When X, also Y")        ("50 episodes → 1 summary")  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Component 1: ConsolidationService

### Purpose
Consolidate episodic and semantic memories into coherent summaries using LLM synthesis.

### Design Philosophy

**Why LLM Essential**: Reading 20+ memories and synthesizing coherent summary is exactly what LLMs excel at. This is NOT a place for deterministic rules.

**Vision**: "Replace many specific memories with one abstract summary" - graceful forgetting through compression.

### Architecture

```
ConsolidationService
├─ Input: (user_id, scope: ConsolidationScope)
├─ Fetch: episodic_memories + semantic_memories in scope
├─ LLM: Synthesize summary (gpt-4o for quality)
├─ Extract: Key facts, interaction patterns, validation needs
├─ Boost: Confidence of confirmed facts
└─ Output: MemorySummary with provenance
```

### Consolidation Scopes

1. **Entity Scope**: All memories about a specific entity
   - Example: "Gai Media profile (3 sessions, Sept 1-15)"
   - Trigger: N+ episodic memories about entity

2. **Topic Scope**: All memories about a topic
   - Example: "Delivery preferences across customers"
   - Trigger: M+ semantic memories with same predicate pattern

3. **Session Window Scope**: Recent sessions for a user
   - Example: "Last 5 sessions summary"
   - Trigger: After N sessions

### LLM Prompt Structure

```python
async def synthesize_summary_llm(
    episodic: List[EpisodicMemory],
    semantic: List[SemanticMemory],
    scope: ConsolidationScope
) -> SummaryData:
    """
    Use LLM for synthesis - reading and synthesizing is what LLMs do best.

    Cost: $0.005 per consolidation (periodic, not per-request)
    """

    prompt = f"""
Synthesize a consolidated summary from these memories.

**Scope**: {scope.type} - {scope.identifier}

**Episodic memories** ({len(episodic)} events):
{format_episodic_memories(episodic)}

**Semantic memories** ({len(semantic)} facts):
{format_semantic_memories(semantic)}

**Task**: Create a coherent summary that:
1. Highlights confirmed facts (mentioned multiple times with high confidence)
2. Notes patterns in interactions
3. Captures key preferences and policies
4. Identifies facts that need validation (low confidence or aged)

**Output** (JSON):
{{
  "summary_text": "Concise narrative summary (2-3 sentences)",
  "key_facts": {{
    "fact_name": {{
      "value": "...",
      "confidence": 0.95,
      "reinforced": 3,
      "source_memory_ids": [1, 5, 12]
    }}
  }},
  "interaction_patterns": ["Pattern 1", "Pattern 2"],
  "needs_validation": ["Fact that hasn't been seen in 90+ days"],
  "confirmed_memory_ids": [1, 5, 12]  // High-confidence facts to boost
}}
"""

    response = await llm.generate(
        prompt=prompt,
        model="gpt-4o",  # Quality matters for synthesis
        temperature=0.3,  # Some creativity for natural summary
        response_format="json"
    )

    return SummaryData.parse(response)
```

### Consolidation Triggers

From `heuristics.py`:
- `CONSOLIDATION_MIN_EPISODIC = 10` - Min episodic memories to consolidate
- `CONSOLIDATION_MIN_SESSIONS = 3` - Min sessions in window
- `CONSOLIDATION_SESSION_WINDOW_DEFAULT = 5` - Last N sessions

### Confidence Boosting

When consolidation confirms a fact (appears in summary with high confidence):
```python
await db.execute("""
    UPDATE semantic_memories
    SET confidence = LEAST(0.95, confidence + 0.1),
        last_validated_at = now()
    WHERE memory_id = ANY($1)
""", confirmed_memory_ids)
```

### Implementation Files

1. **Domain Service**: `src/domain/services/consolidation_service.py`
2. **Repository Port**: `src/domain/ports/summary_repository.py` (already exists)
3. **Repository Impl**: `src/infrastructure/database/repositories/summary_repository.py` (already exists, needs create method)
4. **Value Objects**: `src/domain/value_objects/consolidation.py`
5. **Tests**: `tests/unit/domain/test_consolidation_service.py`

---

## Component 2: ProceduralMemoryService

### Purpose
Detect repeated query patterns and extract action heuristics.

### Design Philosophy

**Basic Implementation** (Phase 1): Simple frequency analysis
- Detect repeated (intent, entities, topics) sequences
- Create heuristic: "When user asks X about Y, also retrieve Z"

**Future** (Phase 2+): ML-based pattern detection using operational data

### Architecture

```
ProceduralMemoryService
├─ Input: user_id (analyze all their episodic memories)
├─ Analyze: Recent 100 episodic memories
├─ Detect: Common patterns (frequency > threshold)
├─ Extract: Trigger pattern + Action heuristic
└─ Output: ProceduralMemory (stored for retrieval augmentation)
```

### Pattern Types (Phase 1)

1. **Query Co-occurrence**: "User asks about delivery → also asks about invoices"
   ```json
   {
     "trigger_pattern": "Query about delivery timing",
     "trigger_features": {
       "intent": "question",
       "entity_types": ["customer"],
       "topics": ["delivery", "shipping"]
     },
     "action_heuristic": "Augment retrieval: also fetch open invoices",
     "action_structure": {
       "augment_retrieval": [
         {"predicate_pattern": "delivery_.*_preference", "entity": "{customer}"},
         {"domain_query": "invoices", "filter": {"status": "open"}}
       ]
     }
   }
   ```

2. **Entity Co-reference**: "User mentions customer → often follows with orders"
   ```json
   {
     "trigger_pattern": "Entity type: customer",
     "action_heuristic": "Preload related orders and work_orders",
     "observed_count": 15
   }
   ```

### Detection Algorithm (Simplified)

```python
class PatternDetector:
    async def detect_query_patterns(self, user_id: str) -> List[ProceduralMemory]:
        """
        Basic frequency analysis for Phase 1.
        Phase 2+: Use ML for more sophisticated detection.
        """
        # Fetch recent episodic memories
        episodes = await self.episodic_repo.get_recent(user_id, limit=100)

        # Extract features from each episode
        features = [self._extract_features(ep) for ep in episodes]

        # Find frequent sequences (sliding window)
        patterns = self._find_frequent_sequences(features, min_support=3)

        # Convert to procedural memories
        procedural_memories = []
        for pattern in patterns:
            if pattern.confidence > 0.7:
                pm = await self._create_procedural_memory(pattern, user_id)
                procedural_memories.append(pm)

        return procedural_memories

    def _extract_features(self, episode: EpisodicMemory) -> Dict:
        """Extract features for pattern matching."""
        return {
            "event_type": episode.event_type,
            "entity_types": [e["type"] for e in episode.entities],
            "intent": self._classify_intent(episode.summary),
            # In Phase 2+: use embeddings for semantic clustering
        }

    def _find_frequent_sequences(
        self,
        features: List[Dict],
        min_support: int
    ) -> List[Pattern]:
        """Find frequent feature sequences (simple frequency counting)."""
        from collections import Counter

        # Sliding window of size 2
        sequences = []
        for i in range(len(features) - 1):
            seq = (
                features[i]["intent"],
                tuple(sorted(features[i]["entity_types"])),
                features[i+1]["intent"],
                tuple(sorted(features[i+1]["entity_types"]))
            )
            sequences.append(seq)

        # Count occurrences
        counts = Counter(sequences)

        # Convert to Pattern objects
        patterns = []
        for seq, count in counts.items():
            if count >= min_support:
                patterns.append(Pattern(
                    sequence=seq,
                    count=count,
                    confidence=count / len(features)
                ))

        return patterns
```

### Implementation Files

1. **Domain Service**: `src/domain/services/procedural_memory_service.py`
2. **Repository Port**: `src/domain/ports/procedural_memory_repository.py`
3. **Repository Impl**: `src/infrastructure/database/repositories/procedural_memory_repository.py`
4. **Value Objects**: `src/domain/value_objects/procedural_memory.py`
5. **Tests**: `tests/unit/domain/test_procedural_memory_service.py`

---

## Component 3: API Endpoints

### Endpoint 1: POST /api/v1/consolidate

**Purpose**: Manually trigger consolidation for a scope

**Request**:
```json
{
  "scope_type": "entity",  // entity|topic|session_window
  "scope_identifier": "customer_gai_123",
  "force": false  // Force even if below thresholds
}
```

**Response**:
```json
{
  "summary_id": 42,
  "summary_text": "Gai Media profile: Friday deliveries (confirmed 3x), NET30 terms...",
  "key_facts": {
    "delivery_preference": {
      "value": "Friday",
      "confidence": 0.95,
      "reinforced": 3
    }
  },
  "source_data": {
    "episodic_count": 12,
    "semantic_count": 8,
    "session_ids": ["uuid1", "uuid2"],
    "time_range": "2025-09-01 to 2025-10-15"
  },
  "confidence": 0.88,
  "created_at": "2025-10-15T14:30:00Z"
}
```

### Endpoint 2: GET /api/v1/summaries/{scope_type}/{scope_identifier}

**Purpose**: Retrieve summary for a scope

**Response**: Same as consolidate response

### Endpoint 3: Enhanced POST /api/v1/chat

**Current**: Only entity resolution
**Enhanced**: Full pipeline with consolidation + procedural hints

**Pipeline**:
```python
@router.post("/api/v1/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Full conversation pipeline with learning.
    """
    # 1. Store event
    event = await chat_service.store_event(...)

    # 2. Entity resolution
    resolved_entities = await resolver.resolve_all(...)

    # 3. Domain database query
    domain_results = await domain_service.query(...)

    # 4. Create episodic memory
    episodic = await episodic_service.create_from_event(...)

    # 5. Extract semantic memories
    semantic_memories = await semantic_service.extract_from_episodic(...)

    # 6. Retrieve relevant memories (with procedural augmentation)
    retrieved_memories = await retriever.retrieve(...)

    # 7. Check consolidation triggers
    if should_consolidate(user_id):
        await consolidation_service.consolidate_async(user_id, scope)

    # 8. Format context for LLM
    memory_context = context_formatter.format(...)

    # 9. Generate response
    llm_response = await llm_service.generate_response(...)

    # 10. Store assistant response
    assistant_event = await chat_service.store_event(...)

    return ChatResponse(...)
```

### Implementation Files

1. **Routes**: `src/api/routes/consolidation.py`
2. **Models**: `src/api/models/consolidation.py`
3. **Enhanced Chat**: Update `src/api/routes/chat.py`

---

## Component 4: Integration Tests

### Test Scenarios

**Scenario 1: End-to-End Memory Lifecycle**
```python
async def test_full_memory_lifecycle():
    """
    Test: Raw event → Episodic → Semantic → Consolidation → Summary
    """
    # 1. Store 10+ chat events about "Gai Media"
    for i in range(10):
        event = await store_event(f"Gai Media prefers Friday delivery (mention {i})")

    # 2. Create episodic memories
    for event in events:
        episodic = await create_episodic(event)

    # 3. Extract semantic memories (should reinforce)
    for episodic in episodic_memories:
        semantics = await extract_semantic(episodic)

    # 4. Consolidate
    summary = await consolidate(user_id, scope="entity:customer_gai_123")

    # 5. Verify
    assert summary.key_facts["delivery_preference"]["value"] == "Friday"
    assert summary.key_facts["delivery_preference"]["confidence"] > 0.9
    assert summary.key_facts["delivery_preference"]["reinforced"] >= 3
```

**Scenario 2: Retrieval with Procedural Augmentation**
```python
async def test_retrieval_with_procedural_hints():
    """
    Test: Procedural patterns enhance retrieval
    """
    # 1. Create pattern: "delivery query → also fetch invoices"
    pattern = await create_procedural_pattern(
        trigger="delivery query",
        action="augment with invoices"
    )

    # 2. Query "When is the delivery for Gai Media?"
    result = await retriever.retrieve(
        query="When is the delivery for Gai Media?",
        user_id=user_id
    )

    # 3. Verify procedural pattern influenced retrieval
    # (Would fetch invoice-related memories even if not semantically similar)
```

**Scenario 3: Consolidation Boosts Confidence**
```python
async def test_consolidation_boosts_confidence():
    """
    Test: Consolidation validates and boosts confidence
    """
    # 1. Create semantic memory with medium confidence
    memory = await create_semantic(
        subject="customer_gai_123",
        predicate="delivery_preference",
        value="Friday",
        confidence=0.7
    )

    # 2. Consolidate (summary confirms the fact)
    summary = await consolidate(user_id, scope="entity:customer_gai_123")

    # 3. Verify confidence boost
    updated_memory = await get_semantic(memory.memory_id)
    assert updated_memory.confidence >= 0.8  # Boosted by consolidation
```

### Performance Benchmarks

**Target**: All operations within Phase 1 performance budgets

1. **Consolidation**: < 2s (LLM synthesis is inherently slower)
2. **Pattern Detection**: < 500ms (frequency analysis)
3. **Full Chat Pipeline**: < 1.5s P95 (including LLM response generation)

### Implementation Files

1. **Integration Tests**: `tests/integration/test_full_pipeline.py`
2. **Performance Tests**: `tests/performance/test_phase1d_latency.py`

---

## Implementation Order

### Week 7: Core Services (Days 1-5)

**Day 1: Consolidation Value Objects**
- `src/domain/value_objects/consolidation.py` (ConsolidationScope, SummaryData)
- Define data structures

**Day 2-3: ConsolidationService**
- `src/domain/services/consolidation_service.py`
- LLM synthesis logic
- Confidence boosting
- Unit tests

**Day 4: Procedural Value Objects**
- `src/domain/value_objects/procedural_memory.py` (Pattern, ProceduralMemory)

**Day 5: ProceduralMemoryService**
- `src/domain/services/procedural_memory_service.py`
- Basic frequency analysis
- Unit tests

### Week 8: API + Integration (Days 6-10)

**Day 6: Repository Implementations**
- `src/infrastructure/database/repositories/summary_repository.py` (add create method)
- `src/infrastructure/database/repositories/procedural_memory_repository.py` (full CRUD)

**Day 7: API Endpoints**
- `src/api/routes/consolidation.py` (consolidate, get summary)
- `src/api/models/consolidation.py` (request/response models)
- Enhance `src/api/routes/chat.py` with full pipeline

**Day 8-9: Integration Tests**
- `tests/integration/test_full_pipeline.py` (3 scenarios)
- `tests/integration/test_consolidation.py`
- `tests/integration/test_procedural_memory.py`

**Day 10: Documentation + Final Review**
- Update API documentation
- Performance benchmarks
- Final code review
- Phase 1 completion summary

---

## Code Quality Standards

### Architecture
- **Hexagonal**: Domain services have NO infrastructure imports
- **Dependency Injection**: All dependencies via constructor
- **Ports & Adapters**: Define repository ports before implementations
- **Single Responsibility**: Each service does ONE thing well

### Code Standards
- **Type hints**: 100% coverage (mypy strict mode)
- **Docstrings**: Every public method with examples
- **Error handling**: Domain exceptions, structured errors
- **Logging**: Structured logging with context
- **Immutability**: Dataclasses with `frozen=True`

### Testing
- **Unit test coverage**: 90%+ for domain services
- **Integration tests**: Full pipeline, database included
- **Performance tests**: Latency targets verified
- **LLM mocking**: Mock LLM responses in unit tests, use real in integration

---

## LLM Usage Summary (Phase 1D)

| Component | LLM Usage | Cost per Use | Frequency |
|-----------|-----------|--------------|-----------|
| **Consolidation** | LLM synthesis (100%) | $0.005 | Periodic (after N sessions) |
| **Pattern Detection** | NO LLM (100% deterministic) | $0 | Background/async |

**Total Phase 1D Cost**:
- Per consolidation: $0.005
- Per conversation: $0 (consolidation is async/background)
- At scale: ~$50/month for 10,000 consolidations

**Still surgical**: LLM only where it genuinely adds value (synthesis)

---

## Success Criteria

### Functional Requirements
- [ ] ConsolidationService creates summaries from 10+ episodic memories
- [ ] Consolidation boosts confidence of confirmed facts
- [ ] ProceduralMemoryService detects repeated patterns (frequency > 3)
- [ ] Procedural patterns stored with trigger + action structure
- [ ] POST /api/v1/consolidate endpoint working
- [ ] GET /api/v1/summaries/{scope}/{id} endpoint working
- [ ] Enhanced POST /api/v1/chat includes consolidation triggers
- [ ] Integration tests pass (3 scenarios)
- [ ] Performance benchmarks met (consolidation < 2s, pattern detection < 500ms)

### Quality Requirements
- [ ] 90%+ unit test coverage for new services
- [ ] All integration tests passing
- [ ] API documentation updated
- [ ] No critical bugs
- [ ] Code review approved

### Vision Alignment
- [ ] Consolidation demonstrates "graceful forgetting"
- [ ] Procedural memory shows "learning from patterns"
- [ ] System improves with each conversation
- [ ] User never restates known preferences

---

## Risk Mitigation

**Risk 1: LLM Synthesis Quality**
- **Mitigation**: Extensive prompt engineering, test with real data, validate JSON output
- **Fallback**: Manual consolidation if LLM fails

**Risk 2: Pattern Detection False Positives**
- **Mitigation**: High threshold (min_support=3), confidence scoring
- **Fallback**: Disable procedural augmentation if patterns are noisy

**Risk 3: Performance of Consolidation**
- **Mitigation**: Async/background consolidation, don't block main chat flow
- **Fallback**: Increase consolidation threshold if too frequent

---

## Phase 1 Completion Checklist

After Phase 1D, Phase 1 is **COMPLETE**. Verify:

- [ ] All 10 database tables operational
- [ ] All 6 memory layers functional (0-6)
- [ ] Entity resolution working (5-stage hybrid)
- [ ] Semantic extraction working (LLM triple extraction)
- [ ] Memory lifecycle working (reinforcement, decay, conflicts)
- [ ] Retrieval working (multi-signal scoring)
- [ ] Consolidation working (LLM synthesis)
- [ ] Procedural memory working (pattern detection)
- [ ] All API endpoints implemented
- [ ] Integration tests passing
- [ ] Performance targets met
- [ ] Documentation complete

---

## Next Steps After Phase 1

**Phase 2: Calibration (1-2 months)**
- Collect operational data (retrieval events, corrections, patterns)
- Calibrate all 43 heuristic parameters using real data
- Tune retrieval strategy weights per user
- Improve pattern detection using ML

**Phase 3: Advanced Learning (2-3 months)**
- Meta-memory (learn decay rates per fact type)
- Adaptive signal weights (per-user optimization)
- Advanced procedural patterns (ML-based)
- Cross-user knowledge transfer

---

**Implementation Date**: 2025-10-15
**Plan Status**: ✅ READY FOR REVIEW & ITERATION
