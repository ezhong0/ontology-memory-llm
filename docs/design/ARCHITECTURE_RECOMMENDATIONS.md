# Architecture Recommendations: Summary & Next Steps

> **SUPERSEDED**: This document has been superseded by **DESIGN.md v2.0**.
> See `ARCHIVE_DESIGN_EVOLUTION.md` for the complete evolution history.
> Retained for reference on the iteration process.

**Date**: 2025-10-15
**Status**: Superseded - User approved ground-up redesign (Option C)

---

## What Changed

I initially recommended replacing most complex logic with LLMs ("LLM-first" approach). After reconsidering your feedback to "really think about where it provides value," I've revised to a more surgical approach:

**Principle**: Use deterministic systems where they excel, LLMs only where they add clear value.

---

## Key Recommendations by Area

### 1. Entity Resolution: Hybrid (Revised)

**Original design**: 5-stage deterministic algorithm
**My first suggestion**: Replace stages 3-5 with LLM
**Revised recommendation**: **Deterministic for 95%, LLM only for coreference**

```
✅ Keep deterministic:
- Exact match (70%) - SQL is perfect
- User alias (15%) - SQL is perfect
- Fuzzy match (10%) - pg_trgm is excellent

✅ Use LLM only for:
- Coreference (5%) - "they", "the customer" needs context reasoning
```

**Why**: pg_trgm handles fuzzy matching brilliantly. Only pronouns/coreference need semantic understanding.

**Savings**: 950 lines → 550 lines (42% reduction, not 63%)
**Cost**: $0.00015 per resolution (not $0.00045)

---

### 2. Memory Extraction: LLM for Semantic Parsing

**Original design**: Pattern matching for detection + triple parsing
**Recommendation**: **Keep pattern detection, LLM for triple extraction**

```
✅ Keep deterministic:
- Event type classification (patterns like "?" = question)
- Entity mention detection (NER patterns)

✅ Use LLM for:
- Triple extraction (semantic parsing is hard)
- Confidence assessment (detecting uncertainty)
```

**Why**: Parsing "Acme prefers Friday deliveries and NET30" into structured triples is genuinely hard with patterns. LLM excels here.

**Cost**: $0.002 per extraction (only for statements/corrections, not all messages)

---

### 3. Query Understanding: Hybrid

**Original design**: Pattern-based classification
**Recommendation**: **Patterns first (90%), LLM fallback (10%)**

```
✅ Keep deterministic:
- Simple patterns ("what did", "how do I") work 90% of time

✅ Use LLM for:
- Compound queries ("How did Acme pay AND should I offer discount?")
- Ambiguous intent
```

**Cost**: $0.0001 average (10% × $0.001)

---

### 4. Retrieval Scoring: Keep Deterministic

**Original design**: Multi-signal weighted formula
**Recommendation**: **❌ DO NOT use LLM**

**Why**:
- Needs to be fast (<100ms for 100 candidates)
- LLM would take 20 seconds (unacceptable)
- Formula works well and is deterministic

**No changes needed**.

---

### 5. Conflict Detection: Smart Hybrid

**Original design**: Exact matching
**Recommendation**: **Deterministic pre-filtering (99%), LLM for semantic (1%)**

```
✅ Keep deterministic:
- Check if same predicate (99% filtered out)
- Normalize values ("NET30" = "NET 30")

✅ Use LLM only for:
- Semantic conflicts across different predicates
- "Prefers email" vs "hates phone calls" - compatible or conflicting?
```

**Cost**: $0.00002 average (1% × $0.002)

---

### 6. Consolidation: LLM is Perfect

**Original design**: LLM synthesis
**Recommendation**: **✅ Keep as-is**

**Why**: Reading 20+ memories and synthesizing coherent summary is exactly what LLMs do best.

**No changes needed**.

---

## Comparative Summary

| Aspect | Original | "Replace Everything" | **Revised (Surgical)** |
|--------|----------|----------------------|------------------------|
| **Code complexity** | ~3,000 lines | ~1,200 lines | **~1,600 lines** |
| **Implementation** | 10-12 weeks | 6-8 weeks | **8-9 weeks** |
| **Cost per request** | $0 (no LLM) | $0.026 | **$0.0024** |
| **Accuracy** | 75% on hard cases | 90%+ | **85-90%** |
| **Latency (P95)** | 50ms | 400ms | **100ms** |

**Verdict**: Surgical approach is the sweet spot.

---

## What I Got Wrong Initially

### ❌ Over-eager LLM adoption:

1. **Fuzzy matching**: Suggested LLM, but pg_trgm is excellent
2. **Query classification**: Suggested always-LLM, but patterns work 90% of time
3. **All entity resolution**: Suggested LLM for stages 3-5, but only coreference needs it

### ✅ What I got right:

1. **Memory extraction**: LLM genuinely better for semantic parsing
2. **Consolidation**: Already LLM-based (correct)
3. **Hybrid principle**: Fast path + LLM fallback (but applied too broadly initially)

---

## Core Principle (Refined)

**Use LLM when ALL of these are true**:

1. ✅ **Semantic understanding required** (not just pattern matching)
2. ✅ **Deterministic approaches demonstrably fail** (measured, not assumed)
3. ✅ **Cost justified by accuracy gain** (quantified improvement)
4. ✅ **Latency acceptable** (can afford 200-500ms or run async)

**Examples**:

✅ **Use LLM**: Coreference resolution
- Needs: Understanding roles ("they" = customer who receives, not order)
- Fails: Recency heuristic only 60% accurate
- Gain: +30% accuracy for $0.003
- Latency: 300ms acceptable for 5% of cases

❌ **Don't use LLM**: Fuzzy text matching
- Needs: Character similarity (not semantic)
- Fails: pg_trgm is 95%+ accurate
- Gain: None (possibly worse)
- Latency: 300ms vs 10ms (30x slower)

---

## Recommended Next Steps

### Option A: Approve Surgical Approach

**If you approve this balanced approach**:

1. I'll update all design docs to reflect surgical LLM integration
2. Update PHASE1_ROADMAP to 8-9 weeks
3. Update CLAUDE.md with "when to use LLM" guidance
4. Keep original docs as reference, create V2 versions

**Timeline**: 2-3 hours to update all docs

### Option B: Further Discussion

**If you want to refine further**:

Let's discuss specific subsystems:
- Which LLM uses make sense to you?
- Which seem questionable?
- Are there areas I'm still over/under-using LLMs?

### Option C: Different Direction

**If you have a different vision**:

Tell me your preferred approach and I'll align the architecture.

---

## My Recommendation

**Approve surgical approach (Option A)** because:

1. **Balanced**: Uses LLMs where they add clear value, keeps deterministic where it works
2. **Measurable**: Each LLM use has quantified cost/benefit
3. **Pragmatic**: 8-9 weeks is realistic, not overly optimistic
4. **Maintainable**: ~1,600 lines is manageable, not over-simplified

The key insight: **Don't replace rule-based systems with LLMs. Use LLMs to handle the cases where rules fail.**

---

## Files Created

1. **LLM_FIRST_ARCHITECTURE.md** - Original aggressive approach (overly LLM-heavy)
2. **ENTITY_RESOLUTION_COMPARISON.md** - Detailed comparison (still valid)
3. **ENTITY_RESOLUTION_DESIGN_V2.md** - Hybrid design (needs revision to be less LLM-heavy)
4. **LLM_INTEGRATION_STRATEGY.md** - **Revised surgical approach (current recommendation)**
5. **ARCHITECTURE_RECOMMENDATIONS.md** - This summary

**Next**: Based on your feedback, I'll either:
- Update remaining docs with surgical approach (Option A)
- Continue discussion (Option B)
- Pivot to different direction (Option C)

What's your preference?
