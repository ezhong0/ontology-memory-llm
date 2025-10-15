# Design Evolution Archive

**Date**: 2025-10-15
**Status**: Historical Reference

---

## Purpose of This Document

This archive documents the design evolution process that led to the current **DESIGN.md v2.0** (ground-up redesign). It preserves the exploration and iteration that occurred, showing how the design was refined based on feedback.

---

## Evolution Timeline

### Phase 1: Initial LLM-Heavy Exploration

**Documents Created**:
1. `ENTITY_RESOLUTION_COMPARISON.md` - Detailed comparison of approaches
2. `ENTITY_RESOLUTION_DESIGN_V2.md` - Hybrid entity resolution design
3. `LLM_FIRST_ARCHITECTURE.md` - Aggressive LLM adoption approach

**Approach**: Replace most complex logic with LLMs
- Entity resolution: Stages 3-5 → LLM
- Memory extraction: Full LLM
- Query understanding: Full LLM
- Retrieval: LLM re-ranking

**Outcome**:
- Code reduction: 3,000 lines → 1,200 lines (60%)
- Cost: ~$0.026 per request
- **User feedback**: "Don't just replace everything with LLM. Really think about where it provides value to my system and the best design integration for each aspect."

---

### Phase 2: Surgical LLM Approach

**Document Created**: `LLM_INTEGRATION_STRATEGY.md`

**Revised Approach**: Use LLMs only where they add clear, measurable value

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Entity Resolution | Deterministic (95%) + LLM coreference (5%) | pg_trgm excellent for fuzzy matching |
| Memory Extraction | Pattern detection + LLM semantic parsing | LLM genuinely better at triple extraction |
| Query Understanding | Pattern-based (90%) + LLM fallback (10%) | Simple patterns work most of time |
| Retrieval Scoring | Deterministic formula (100%) | Must be fast (<100ms), LLM too slow |
| Conflict Detection | Deterministic (99%) + LLM semantic (1%) | Most conflicts are obvious |
| Consolidation | LLM synthesis (100%) | This is what LLMs excel at |

**Outcome**:
- Code: ~1,600 lines
- Cost: ~$0.0024 per request
- Accuracy: 85-90%

**Summary Document**: `ARCHITECTURE_RECOMMENDATIONS.md`

---

### Phase 3: Ground-Up Redesign (Current)

**User Request**: "Rethink everything from the ground up again. Review VISION.md and DESIGN_PHILOSOPHY.md and rewrite DESIGN.md"

**Document Created**: `DESIGN.md v2.0`

**Approach**: Start from vision principles, derive architecture

**Key Changes from Phase 2**:
1. **Vision-first derivation**: Every table/algorithm explicitly justified by vision
2. **Complete algorithm specifications**: Detailed pseudocode for all key processes
3. **Integration of surgical LLM approach**: Incorporated Phase 2 learnings into comprehensive design
4. **Information flow diagrams**: Complete memory creation and retrieval pipelines
5. **Implementation roadmap**: Clear 8-week phased approach

**Result**: Comprehensive design document that:
- Grounds every decision in VISION.md principles
- Applies DESIGN_PHILOSOPHY.md's Three Questions Framework
- Integrates the surgical LLM approach where it adds value
- Provides complete specifications for implementation
- Includes detailed algorithms, cost analysis, success metrics

---

## What Was Learned

### Iteration 1 → 2: Over-Eager LLM Adoption

**What we got wrong**:
- Fuzzy matching: Suggested LLM, but pg_trgm is excellent (95%+ accurate, 30x faster)
- Query classification: Suggested always-LLM, but patterns work 90% of time
- All entity resolution: Suggested LLM for stages 3-5, but only coreference needs it

**What we got right**:
- Memory extraction: LLM genuinely better for semantic parsing
- Consolidation: Already LLM-based (correct from start)
- Hybrid principle: Fast path + LLM fallback (but applied too broadly initially)

### Iteration 2 → 3: From Surgical Strategy to Complete Design

**What was missing in Phase 2**:
- Explicit connection to vision principles for every design element
- Complete algorithm specifications (not just high-level descriptions)
- Information flow through entire system
- Integration with supporting tables (ontology, conflicts, config)
- Phased implementation roadmap

**What Phase 3 adds**:
- Vision-grounded justification for every table
- Detailed pseudocode for entity resolution, extraction, retrieval, conflicts, consolidation
- Complete memory creation and retrieval pipelines
- Decision criteria for every design choice
- Clear phase distinctions (essential vs enhancements vs learning)

---

## Decision Criteria: When to Use LLMs

Through this evolution, we refined our criteria:

**Use LLM when ALL of these are true**:
1. ✅ **Semantic understanding required** (not just pattern matching)
2. ✅ **Deterministic approaches demonstrably fail** (measured, not assumed)
3. ✅ **Cost justified by accuracy gain** (quantified improvement)
4. ✅ **Latency acceptable** (can afford 200-500ms or run async)

**Examples**:

✅ **Use LLM**: Coreference resolution
- Needs: Understanding context ("they" = customer who receives, not order)
- Fails: Recency heuristic only 60% accurate
- Gain: +30% accuracy for $0.003
- Latency: 300ms acceptable for 5% of cases

❌ **Don't use LLM**: Fuzzy text matching
- Needs: Character similarity (not semantic understanding)
- Fails: pg_trgm is 95%+ accurate already
- Gain: None (possibly worse, hallucination risk)
- Latency: 300ms vs 10ms (30x slower)

---

## Superseded Documents

The following documents were created during exploration but are now superseded by **DESIGN.md v2.0**:

### 1. ENTITY_RESOLUTION_DESIGN_V2.md
**Status**: Superseded
**Content**: Hybrid entity resolution with fast path + LLM fallback
**Why superseded**: Entity resolution section now fully integrated into DESIGN.md with more detail
**Retain for**: Reference on entity resolution algorithm evolution

### 2. LLM_INTEGRATION_STRATEGY.md
**Status**: Superseded
**Content**: Surgical LLM integration approach with area-by-area analysis
**Why superseded**: All recommendations integrated into DESIGN.md's "Where LLMs Are Used" section
**Retain for**: Reference on decision-making process for LLM integration

### 3. ARCHITECTURE_RECOMMENDATIONS.md
**Status**: Superseded
**Content**: Summary and next steps from Phase 2
**Why superseded**: Decisions made, integrated into DESIGN.md v2.0
**Retain for**: Understanding iteration process

### 4. ENTITY_RESOLUTION_COMPARISON.md
**Status**: Reference
**Content**: Detailed comparison of Multi-Step vs Pure LLM vs Hybrid approaches
**Why retain**: Still valuable for understanding trade-offs
**Status**: Keep as reference document

---

## Current Design Documents (Active)

The following documents represent the current, active design:

### Core Design
1. **DESIGN.md v2.0** - Comprehensive system design (ground-up redesign)
2. **LIFECYCLE_DESIGN.md** - Memory lifecycle and transformation pipeline
3. **RETRIEVAL_DESIGN.md** - Three-stage retrieval architecture
4. **API_DESIGN.md** - API design and interfaces

### Vision & Philosophy
5. **VISION.md** - Philosophical foundation and principles
6. **DESIGN_PHILOSOPHY.md** - Decision framework and phasing strategy

### Reference
7. **ENTITY_RESOLUTION_COMPARISON.md** - Trade-off analysis (historical reference)

---

## Key Takeaways

1. **Start from vision, not from solution**: Phase 3 succeeded because it derived architecture from vision principles, not the other way around.

2. **Surgical over blanket**: Use LLMs where they add clear value, not as a general replacement for deterministic systems.

3. **Justify every piece of complexity**: The Three Questions Framework ensures every design element earns its place.

4. **Iteration is essential**: The exploration (Phases 1-2) was necessary to refine to the final design (Phase 3).

5. **Documentation serves implementation**: Complete algorithms and specifications (Phase 3) are more useful than high-level strategies (Phase 2).

---

## For Future Reference

When evaluating new features or changes:

1. **Check vision alignment**: Which vision principle does this serve?
2. **Apply Three Questions**: Does it justify its cost? Is this the right phase?
3. **Consider alternatives**: Is there a simpler deterministic approach?
4. **Measure, don't assume**: Use LLMs where they demonstrably add value
5. **Phase appropriately**: Essential (P1) → Useful (P2) → Learning (P3)

---

**The journey from exploration to refined design is preserved here for future reference and learning.**
