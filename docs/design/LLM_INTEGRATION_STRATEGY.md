# LLM Integration Strategy: Surgical Application, Not Blanket Replacement

> **SUPERSEDED**: This document has been superseded by **DESIGN.md v2.0** (Section: Where LLMs Are Used).
> See `ARCHIVE_DESIGN_EVOLUTION.md` for the evolution history.
> Retained for reference on LLM integration decision-making process.

**Date**: 2025-10-15
**Status**: Superseded by DESIGN.md v2.0
**Principle**: Use LLMs for **semantic understanding** and **reasoning**, not for **lookup** or **pattern matching**

---

## Core Philosophy: The Right Tool for the Right Job

**LLMs excel at**:
- Semantic understanding (interpreting meaning)
- Contextual reasoning (using conversation history)
- Ambiguity resolution (weighing multiple factors)
- Natural language generation (synthesis, summarization)

**Deterministic systems excel at**:
- Exact lookups (SQL queries)
- Pattern matching (regex, pg_trgm)
- Fast scoring (mathematical formulas)
- Consistency (same input → same output)

**The mistake**: Assuming LLMs are better at everything.

**The insight**: Use each tool where it has a clear advantage.

---

## Area-by-Area Analysis

### 1. Entity Resolution: Strategic LLM Use

#### What to Keep Deterministic

**✅ Exact match** (70% of cases):
```python
# Perfect for SQL - instant, free, deterministic
SELECT canonical_entity_id FROM entity_aliases
WHERE alias_text = 'Acme Corporation' AND user_id IS NULL
```
**Why not LLM**: No semantic understanding needed. It's an exact lookup.

**✅ User-specific aliases** (15% of cases):
```python
# Perfect for SQL - learned user preferences
SELECT canonical_entity_id FROM entity_aliases
WHERE alias_text = 'my customer' AND user_id = 'user_123'
```
**Why not LLM**: User explicitly taught this mapping. Just look it up.

**✅ Fuzzy matching** (10% of cases):
```python
# pg_trgm is EXCELLENT at fuzzy text matching
SELECT canonical_entity_id, similarity(alias_text, 'ACME Corp') as score
FROM entity_aliases
WHERE similarity(alias_text, 'ACME Corp') > 0.70
ORDER BY score DESC
```
**Why not LLM**:
- pg_trgm handles typos, case, punctuation perfectly
- 10ms vs 300ms (30x faster)
- Free vs $0.003
- Deterministic (same similarity score every time)

**When pg_trgm is enough**: "ACME Corp" → "Acme Corporation" (0.85 similarity)

#### Where LLM Adds Clear Value

**✅ Coreference resolution** (3-5% of cases):
```python
# User: "What did Acme order?"
# Assistant: "Order #1001 for $5,000"
# User: "When will they get it?" ← "they" = Acme or Order?

# Deterministic heuristic: "they" = most recent entity
recent_entities = ["order:1001", "customer:acme"]
return recent_entities[0]  # ❌ Returns order (wrong!)

# LLM with context:
prompt = """
User said "they" in: "When will they get it?"
Recent entities: Acme (customer), Order #1001
Which does "they" refer to?
"""
# ✅ Returns Acme (correct - customers receive orders)
```

**Why LLM**: Requires understanding:
- Semantic roles (customers receive, orders are received)
- Conversation flow (question about delivery → entity receiving delivery)
- Pragmatic reasoning (orders don't "get" things, customers do)

**Cost-benefit**: $0.003 for 3-5% of cases = $0.00015 average cost → Worth it for accuracy.

**✅ Ambiguity with context clues**:
```python
# User: "What did Apple order last quarter?"
# Candidates: Apple Inc (customer:apple_tech), Apple Farm Supply (customer:apple_farm)

# Recent context: Discussion about B2B software licenses

# LLM reasoning:
"Given context about B2B software, 'Apple' likely refers to Apple Inc (tech company)
rather than Apple Farm Supply."
```

**Why LLM**: Semantic understanding of context relevance.

#### Recommended Architecture

```python
async def resolve_entity(mention: str, context: Context) -> Resolution:
    # Stage 1: Exact match (70%)
    if exact := await exact_match(mention):
        return exact  # 5ms, $0

    # Stage 2: User alias (15%)
    if user_alias := await user_alias_match(mention, context.user_id):
        return user_alias  # 5ms, $0

    # Stage 3: Fuzzy match (10%)
    fuzzy_candidates = await fuzzy_match(mention, threshold=0.70)
    if len(fuzzy_candidates) == 1 and fuzzy_candidates[0].score > 0.85:
        return fuzzy_candidates[0]  # 15ms, $0

    # Stage 4: LLM for hard cases (3-5%)
    # Only when:
    # - Pronoun/coreference ("they", "the customer")
    # - Multiple fuzzy matches need context ranking
    # - No good fuzzy match but need entity discovery

    if is_coreference(mention) or len(fuzzy_candidates) > 1:
        return await llm_resolve(mention, fuzzy_candidates, context)  # 300ms, $0.003

    # Stage 5: Search domain DB (lazy entity creation)
    domain_matches = await search_domain_db(mention)
    if domain_matches:
        return create_and_resolve(domain_matches[0])

    return None  # No match
```

**Result**: 95% deterministic (fast, free), 5% LLM (smart, costly)

---

### 2. Memory Extraction: LLM for Semantic Parsing

#### What to Keep Deterministic

**✅ Event type classification** (simple patterns):
```python
# These patterns are reliable:
if "?" in message:
    event_type = "question"
elif message.lower().startswith(("actually", "no,", "that's wrong")):
    event_type = "correction"
elif re.search(r"(remember|note that|keep in mind)", message.lower()):
    event_type = "statement"
```

**Why not LLM**: Simple, fast, deterministic. No semantic ambiguity.

**✅ Entity mention detection** (NER patterns):
```python
# Capitalized words, @ mentions, IDs
entity_mentions = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', message)
entity_mentions += re.findall(r'SO-\d+|INV-\d+|CUST-\d+', message)
```

**Why not LLM**: Pattern matching is sufficient for mention detection.

#### Where LLM Adds Clear Value

**✅ Triple extraction** (semantic parsing):
```python
# User: "Acme prefers Friday deliveries and NET30 payment terms"

# Pattern matching attempt:
# ❌ Hard to parse: multiple facts, complex structure
# ❌ "prefers" could apply to what? Friday? NET30? Both?

# LLM extraction:
"""
Extract subject-predicate-object triples:

Input: "Acme prefers Friday deliveries and NET30 payment terms"
Entities: [Acme Corporation (customer:acme)]

Output:
[
  {subject: "Acme Corporation", predicate: "delivery_day_preference", object: "Friday"},
  {subject: "Acme Corporation", predicate: "payment_terms", object: "NET30"}
]
"""
```

**Why LLM**:
- Understands compound statements
- Maps natural language predicates to schema predicates
- Handles implicit subjects ("...and NET30" inherits "Acme")

**✅ Confidence assessment**:
```python
# User: "I think they might prefer Thursday, but I'm not sure"

# LLM extracts:
{
  "fact": {subject: "customer:X", predicate: "delivery_day", object: "Thursday"},
  "confidence": 0.45,  # ← LLM detects uncertainty from "I think", "might", "not sure"
  "reasoning": "User expressed uncertainty with qualifiers"
}
```

**Why LLM**: Detecting epistemic modality ("might", "probably", "definitely") is semantic understanding.

#### Recommended Architecture

```python
async def extract_memories(message: str, context: Context) -> Extraction:
    # Deterministic pre-processing
    event_type = classify_event_type(message)  # Patterns
    mentions = extract_entity_mentions(message)  # NER/patterns

    # Resolve entities (hybrid from Area 1)
    entities = [await resolve_entity(m, context) for m in mentions]

    # LLM for semantic extraction
    if should_extract_facts(event_type):  # Only for statements, corrections
        facts = await llm_extract_facts(
            message=message,
            entities=entities,
            conversation_context=context.recent_messages
        )
        return Extraction(event_type, entities, facts)

    return Extraction(event_type, entities, facts=[])
```

**When to skip LLM**: Questions, simple acknowledgments ("ok", "thanks") don't need fact extraction.

---

### 3. Query Understanding: Hybrid Pattern + LLM

#### What to Keep Deterministic

**✅ Common query patterns** (90% of cases):
```python
# Very reliable patterns:
if re.search(r"what (did|does|is|are)", query.lower()):
    return QueryType(category="factual", ...)

if re.search(r"how (do|did|to|can) (I|we)", query.lower()):
    return QueryType(category="procedural", ...)

if re.search(r"(last|recent|yesterday|this) (week|month|quarter)", query.lower()):
    return QueryType(time_focused=True, ...)
```

**Why not LLM**: These patterns work 95%+ of the time. Fast, free, deterministic.

**✅ Entity detection**: Already covered in Area 1 (hybrid approach)

#### Where LLM Adds Value

**✅ Complex/compound queries** (10% of cases):
```python
# Query: "How did Acme usually pay over the last quarter, and should I offer them a discount?"

# Pattern matching:
# ✅ Detects "how" → procedural (wrong - it's asking about past behavior = factual)
# ✅ Detects "last quarter" → time_focused (correct)
# ❌ Misses compound nature (two questions: past behavior + recommendation)

# LLM classification:
{
  "primary_intent": "factual_entity_focused",  # ← Asking about Acme's past behavior
  "secondary_intent": "analytical",  # ← Wants recommendation based on patterns
  "entity_focused": true,
  "time_focused": true,
  "retrieval_strategy": "factual_entity_focused",
  "reasoning": "Primary question is about historical payment patterns for Acme"
}
```

**Why LLM**: Compound queries, nuanced intent, context-dependent classification.

#### Recommended Architecture

```python
async def understand_query(query: str, context: Context) -> QueryUnderstanding:
    # Try deterministic patterns first
    if pattern_result := classify_with_patterns(query):
        if pattern_result.confidence > 0.90:
            return pattern_result  # 90% of cases, <5ms

    # Fall back to LLM for complex cases
    return await llm_classify_query(query, context)  # 10% of cases, 200ms, $0.001
```

**Cost**: $0.0001 average (10% × $0.001)

---

### 4. Retrieval Scoring: Keep Deterministic

#### Why NOT LLM

```python
# Current multi-signal scoring:
score = (
    semantic_similarity * 0.25 +
    entity_overlap * 0.40 +
    temporal_relevance * 0.20 +
    importance * 0.10 +
    reinforcement * 0.05
)

# Latency: 10-20ms for 100 candidates (in-memory computation)
# Cost: $0
# Determinism: Same query → same scores
```

**If we used LLM**:
```python
# LLM scoring 100 candidates:
# Latency: 100 × 200ms = 20,000ms (20 seconds!) ← UNACCEPTABLE
# Or batch: 1 call, 500ms ← Still too slow
# Cost: $0.01 per retrieval ← 10x more expensive than entire chat request
```

**Verdict**: ❌ **DO NOT use LLM for scoring**. Multi-signal formula is perfect.

**Exception**: LLM could help *learn* optimal weights in Phase 2 (offline analysis), but not for runtime scoring.

---

### 5. Conflict Detection: Hybrid with Smart Triggers

#### What to Keep Deterministic

**✅ Pre-filtering** (99% of cases):
```python
# Fast checks before expensive LLM call:

# Check 1: Different predicates? → No conflict possible
if new.predicate != existing.predicate:
    return NoConflict()  # 99% of cases

# Check 2: Same predicate, check exact value match
if new.predicate == existing.predicate:
    if normalize(new.object_value) == normalize(existing.object_value):
        return Reinforcement()  # Same fact, reinforce
```

**Normalization** (deterministic):
```python
def normalize(value):
    # Handle formatting variations:
    # "NET30" → "net-30"
    # "Friday" → "friday"
    # "$1,000" → "1000.00"
    return value.lower().replace(" ", "-").strip("$,")
```

**Why not LLM**: Exact matching and normalization are deterministic operations.

#### Where LLM Adds Value

**✅ Semantic conflict detection** (1% of cases):
```python
# After pre-filtering, only these remain:
# - Same subject + predicate
# - Different values AFTER normalization
# - Need semantic understanding

# Example:
# Existing: "Acme prefers email communication"
# New: "Acme hates phone calls"
#
# Different predicates ("prefers email" vs "hates phone")
# But semantically compatible (both about communication preferences)

# LLM check:
prompt = """
Do these facts conflict?
Fact 1: Acme prefers email communication
Fact 2: Acme hates phone calls

Conflict types:
- Direct contradiction: Same property, incompatible values
- Semantic compatibility: Different properties, compatible meanings
- No conflict: Compatible facts

Output: {conflict: false, reasoning: "Both facts describe communication preferences, compatible"}
"""
```

**Why LLM**: Understanding semantic relationships between different predicates.

#### Recommended Architecture

```python
async def detect_conflict(new_fact: Fact, existing_facts: List[Fact]) -> Conflict:
    # Stage 1: Pre-filter (99%)
    same_predicate_facts = [f for f in existing_facts
                            if f.predicate == new_fact.predicate]

    if not same_predicate_facts:
        return NoConflict()  # Different predicates, no conflict

    # Stage 2: Exact/normalized match (90% of same-predicate)
    for existing in same_predicate_facts:
        if normalize(existing.object_value) == normalize(new_fact.object_value):
            return Reinforcement()  # Same fact

    # Stage 3: LLM semantic check (1% of total)
    # Only for same predicate, different normalized values
    return await llm_semantic_conflict_check(new_fact, same_predicate_facts)
```

**Cost**: $0.002 × 1% = $0.00002 average

---

### 6. Consolidation: LLM is Perfect (Keep as-is)

```python
# Input: 20 episodic memories + 10 semantic facts about "Acme Corporation"
# Output: Coherent natural language summary + structured key facts

# This is EXACTLY what LLMs are good at:
# - Reading multiple documents
# - Extracting patterns
# - Synthesizing coherent narrative
# - Structuring information
```

**✅ Keep current design**. LLM consolidation is correct.

---

## Summary: Surgical LLM Integration

| Component | Strategy | LLM Usage | Cost Impact | Accuracy Gain |
|-----------|----------|-----------|-------------|---------------|
| **Entity Resolution** | Hybrid | 5% (coreference only) | $0.00015 | +15% on pronouns |
| **Memory Extraction** | LLM for parsing | 100% of statements | $0.002 | +25% on complex facts |
| **Query Understanding** | Hybrid | 10% (complex queries) | $0.0001 | +10% on compounds |
| **Retrieval Scoring** | ❌ No LLM | 0% | $0 | N/A (would be slower) |
| **Conflict Detection** | Hybrid | 1% (semantic conflicts) | $0.00002 | +20% on semantics |
| **Consolidation** | ✅ LLM | 100% (async) | $0.003 | N/A (LLM is best tool) |

**Total cost per chat request**: ~$0.0024 (vs $0.026 in "replace everything" approach)

**Code complexity**: ~1,400 lines (vs ~3,000 original, ~1,200 "replace everything")

**Implementation time**: 8-9 weeks (vs 10-12 original, 6-8 "replace everything")

---

## Decision Criteria: When to Use LLM

Use LLM when **ALL** of these are true:

1. ✅ **Semantic understanding required** (not just pattern matching or lookup)
2. ✅ **Deterministic approaches demonstrably fail** (not just "LLM might be better")
3. ✅ **Cost justified by accuracy gain** (measure improvement, not assume)
4. ✅ **Latency acceptable** (can afford 200-500ms, or can run async)

Examples:

**✅ Use LLM**: Coreference ("they" could mean multiple entities)
- Semantic: Yes (understanding roles and context)
- Deterministic fails: Yes (recency heuristic only 60% accurate)
- Cost justified: Yes (+30% accuracy for $0.003)
- Latency: Acceptable (300ms for 5% of requests)

**❌ Don't use LLM**: Fuzzy text matching
- Semantic: No (just character similarity)
- Deterministic fails: No (pg_trgm is 95%+ accurate)
- Cost justified: No (no accuracy gain, 30x slower)
- Latency: Not acceptable (300ms vs 10ms)

---

## Revised Architecture Recommendation

**Principle**: Deterministic first, LLM for genuinely hard problems.

**Phase 1 Implementation** (8-9 weeks):

```python
Week 1-2: Core pipeline
✅ Deterministic event classification
✅ Hybrid entity resolution (exact/alias/fuzzy → LLM for coreference)
✅ LLM fact extraction (semantic parsing)
✅ Deterministic retrieval scoring

Week 3-4: Query understanding + conflict detection
✅ Pattern-based query classification (LLM fallback for complex)
✅ Deterministic conflict pre-filtering (LLM for semantic)

Week 5-6: Memory transformations
✅ LLM consolidation (synthesis)
✅ Deterministic lifecycle state machine

Week 7-8: Testing + optimization
✅ Measure LLM vs deterministic accuracy
✅ Optimize LLM prompt efficiency
✅ Fast path optimization (increase hit rate)

Week 9: Polish
✅ Error handling
✅ Monitoring
✅ Documentation
```

This is a **balanced approach**: Use LLMs where they shine, keep deterministic systems where they excel.
