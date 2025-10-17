# E2E Scenarios Test Design

## Design Philosophy

Before implementing, design each test thoughtfully:

1. **What infrastructure exists?** - Don't test what isn't built
2. **What should this test validate?** - Focus on one clear concept
3. **How does this differ from other tests?** - Avoid redundancy
4. **What are realistic assertions?** - Match Phase 1 capabilities

## Scenario Mapping to Implementation Status

### ✅ Ready to Implement (Infrastructure Complete)

**Scenario 1: Overdue invoice + preference recall** ✅ DONE
- Tests: Cross-turn retrieval, domain augmentation, memory scoring
- Infrastructure: Phase 1D complete

**Scenario 4: NET terms learning** ✅ DONE
- Tests: Semantic extraction from conversation
- Infrastructure: Phase 1B complete

**Scenario 5: Partial payments and balance**
- Tests: Domain DB joins (invoices + payments), episodic memory creation
- Infrastructure: Domain repository, chat endpoint
- New: Need payments query in domain augmentation

**Scenario 9: Cold-start grounding**
- Tests: Pure DB query without memories, episodic memory creation
- Infrastructure: Domain repository (sales_orders, work_orders)
- Simple: No memory retrieval needed

**Scenario 18: Task completion**
- Tests: Task status query, semantic memory storage
- Infrastructure: Domain repository (tasks table)
- Simplified: Return facts, store memory (not actual DB update)

### ⚠️ Needs Feature Work

**Scenario 2: Work order rescheduling**
- Missing: Work order queries in domain augmentation
- Design: Query WO, extract scheduling preference as semantic memory

**Scenario 3: Ambiguous entity disambiguation**
- Missing: Disambiguation flow/API
- Design: Test fuzzy match, detect ambiguity, handle clarification

**Scenario 6: SLA breach detection**
- Missing: Task age calculation, risk tagging
- Design: Query old tasks, flag risks in response

**Scenario 7: Conflicting memories consolidation**
- Missing: Consolidation rules (trust_recent vs trust_reinforced)
- Design: Create conflicting memories, verify resolution strategy

**Scenario 8: Multilingual alias handling**
- Missing: Multilingual NER
- Design: Non-English input, English canonical storage, alias creation

**Scenario 10: Active recall for stale facts**
- Missing: Validation prompting, memory status transitions
- Design: Create aged memory, prompt for validation, update on confirmation

**Scenario 11: Cross-object reasoning**
- Missing: Chained queries (SO → WO → Invoice)
- Design: Query chain, policy memory extraction

**Scenario 12: Fuzzy match + alias learning**
- Partial: Fuzzy match exists, alias learning needs triggering
- Design: Typo → fuzzy match → alias creation

**Scenario 13: PII redaction**
- Missing: PII detection and redaction
- Design: Detect PII, redact before storage, return masked

**Scenario 14: Session window consolidation**
- Missing: /consolidate endpoint, summary generation
- Design: Multiple sessions → consolidation → summary memory

**Scenario 15: Explainability / audit trail**
- Missing: /explain endpoint
- Design: Query provenance, return memory IDs and sources

**Scenario 16: Reminder creation from intent**
- Missing: Policy memory + proactive checking
- Design: Store policy, trigger on matching queries

**Scenario 17: Memory vs DB conflict**
- Partial: Conflict detection exists
- Design: Create outdated memory, verify DB preference

## Test Design Principles

### 1. One Concept Per Test
Each test validates ONE clear concept:
- Scenario 1: Cross-turn retrieval
- Scenario 4: Semantic extraction
- Scenario 5: DB joins + balance calculation
- Scenario 9: Cold start (DB only)

### 2. Realistic Assertions
Match Phase 1 capabilities:
- ✅ Entity resolution may fail for new entities
- ✅ LLM responses vary (check key facts, not exact phrasing)
- ✅ Augmentation structure is consistent
- ❌ Don't assert on unimplemented features

### 3. Clear Test Structure
```python
# ARRANGE: Seed data
ids = await domain_seeder.seed({...})
await memory_factory.create_canonical_entity(...)

# ACT: User query
response = await api_client.post("/api/v1/chat", json={...})

# ASSERT: Validate response
assert response.status_code == 200
data = response.json()
assert "expected_fact" in data["response"]
assert len(data["augmentation"]["domain_facts"]) > 0
```

### 4. Skip When Appropriate
```python
@pytest.mark.skip(reason="TODO: Work order queries not implemented")
async def test_scenario_02_work_order_rescheduling(...):
    # Full test implementation here
    # Even though skipped, the test is designed and ready
```

## Implementation Order

### Phase 1: Infrastructure-Ready (Now)
1. Scenario 5: Partial payments
2. Scenario 9: Cold-start grounding
3. Scenario 18: Task completion

### Phase 2: Minor Feature Additions
4. Scenario 2: Work order queries
5. Scenario 12: Alias learning trigger
6. Scenario 17: Memory vs DB (enhance existing)

### Phase 3: Major Features
7. Scenario 3: Disambiguation flow
8. Scenario 7: Consolidation rules
9. Scenario 10: Active recall
10. Scenario 11: Cross-object reasoning
11. Scenario 14: Consolidation endpoint

### Phase 4: Advanced Features
12. Scenario 6: SLA/risk tagging
13. Scenario 8: Multilingual
14. Scenario 13: PII redaction
15. Scenario 15: Explainability endpoint
16. Scenario 16: Proactive reminders

## Next Steps

1. Write ALL 18 test implementations
2. Mark 11 as @pytest.mark.skip with reason
3. Run the 7 that should work
4. Fix issues systematically
5. Implement missing features in order
