# Entity Resolution: Multi-Step Algorithm vs LLM-Based Approach

**Date**: 2025-10-15
**Status**: Architectural Analysis
**Decision**: Pending

---

## The Question

Should we use a **5-stage deterministic algorithm** (Exact → Alias → Fuzzy → Coreference → Disambiguation) or a **simpler LLM-based resolver** that gets context and resolves entities with confidence?

---

## Approach 1: Current Multi-Step Design (5-Stage Algorithm)

### Architecture

```python
# Stage 1: Exact Match
SELECT * FROM entity_aliases WHERE alias_text = 'Acme Corporation' AND user_id IS NULL
→ Confidence: 1.0 (deterministic)
→ Latency: ~5ms (indexed lookup)
→ Cost: $0

# Stage 2: User-Specific Alias
SELECT * FROM entity_aliases WHERE alias_text = 'my customer' AND user_id = 'user_123'
→ Confidence: 0.95 (learned)
→ Latency: ~5ms
→ Cost: $0

# Stage 3: Fuzzy Match + Semantic
SELECT * FROM entity_aliases WHERE similarity(alias_text, 'Acme') > 0.7
→ Confidence: 0.70-0.85 (depends on similarity score)
→ Latency: ~30ms (trigram index + scoring)
→ Cost: $0

# Stage 4: Coreference Resolution
recent_entities = get_recent_entities(session_id, limit=10)
→ Confidence: 0.60 (contextual, decays with recency)
→ Latency: ~10ms
→ Cost: $0

# Stage 5: Disambiguation
if no high_confidence_match:
    ask_user(candidates)
→ Confidence: 0.85 after user selection
→ Latency: ~100ms + user time
→ Cost: $0
```

### Performance Profile

| Metric | Stage 1-2 (80% of cases) | Stage 3 (15%) | Stage 4-5 (5%) |
|--------|-------------------------|--------------|---------------|
| **Latency** | 5-10ms | 30-50ms | 100ms + user |
| **API Cost** | $0 | $0 | $0 |
| **Confidence** | 0.95-1.0 | 0.70-0.85 | 0.60-0.85 |
| **Deterministic?** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Debuggable?** | ✅ High | ✅ High | ✅ High |

**Average per-resolution**:
- Latency: ~15ms (weighted average)
- Cost: $0

### Code Complexity

```python
# Estimated implementation size
entity_resolver.py:          ~500 lines
entity_repository.py:        ~300 lines
coreference_resolver.py:     ~200 lines
fuzzy_matcher.py:            ~150 lines
disambiguation_handler.py:   ~100 lines
───────────────────────────────────
Total:                       ~1250 lines

# Number of database queries per resolution
Stage 1: 1 query (alias lookup)
Stage 2: 1 query (user alias lookup)
Stage 3: 2 queries (fuzzy match + entity properties)
Stage 4: 1 query (recent entities from episodic memories)
Stage 5: 1-N queries (domain DB search)

Average: 2-3 queries per resolution
```

### Maintenance Burden

**Requires tuning**:
- `FUZZY_MATCH_THRESHOLD = 0.70` (in heuristics.py)
- `DISAMBIGUATION_MIN_CONFIDENCE_GAP = 0.15`
- `COREFERENCE_WINDOW = 10` messages
- Confidence formulas for each stage

**Requires database extensions**:
- `pg_trgm` for fuzzy text matching (trigram similarity)
- Multiple indexes (exact, trigram, GIN for JSONB)

**Testing complexity**:
- Need test data for each stage
- Need mocks for database queries
- Need fuzzy matching edge cases
- Integration tests for end-to-end flow

---

## Approach 2: Pure LLM-Based Resolution

### Architecture

```python
async def resolve_entity_llm(
    mention_text: str,
    context: ResolutionContext
) -> ResolutionResult:
    """
    Single LLM call to resolve entity mention.
    """
    prompt = f"""
You are an entity resolver for a business intelligence system.

**Task**: Resolve the entity mention "{mention_text}" to a canonical entity ID.

**Available Entities**:
{json.dumps(context.candidate_entities, indent=2)}

**Conversation Context**:
Recent messages:
{format_recent_messages(context.session_history)}

Recent entities mentioned:
{format_recent_entities(context.recent_entities)}

**Instructions**:
1. Determine which canonical entity (if any) the mention refers to
2. Provide confidence score (0.0 to 1.0)
3. If ambiguous, list alternative candidates
4. Explain your reasoning

**Output Format** (JSON):
{{
  "canonical_entity_id": "customer:xxx" or null,
  "confidence": 0.85,
  "alternative_candidates": ["customer:yyy", "customer:zzz"],
  "requires_disambiguation": false,
  "reasoning": "The mention 'Acme' most likely refers to..."
}}
"""

    response = await llm.generate(
        prompt=prompt,
        model="gpt-4-turbo",  # or claude-3-5-sonnet
        temperature=0.0,  # Deterministic as possible
        response_format="json"
    )

    return ResolutionResult.parse(response)
```

### Performance Profile

| Metric | Value |
|--------|-------|
| **Latency** | 200-500ms (LLM API call) |
| **API Cost** | $0.002-0.005 per resolution (GPT-4 Turbo) |
| **Confidence** | 0.0-1.0 (model-generated, needs calibration) |
| **Deterministic?** | ❌ No (even with temperature=0, minor variance) |
| **Debuggable?** | ⚠️ Medium (black box, but has "reasoning" field) |

**Average per-resolution**:
- Latency: ~300ms
- Cost: ~$0.003

**Cost analysis** (at scale):
- 100 messages/day/user × 3 entities/message × $0.003 = **$0.90/user/day**
- 1,000 users = **$900/day** = **$27,000/month** for entity resolution alone

### Code Complexity

```python
# Estimated implementation size
llm_entity_resolver.py:       ~150 lines (including prompt)
prompt_templates.py:          ~50 lines
llm_response_parser.py:       ~100 lines
───────────────────────────────────
Total:                        ~300 lines

# Much simpler!

# Number of operations per resolution
1. Fetch candidate entities (1 query)
2. Format context (in-memory)
3. Call LLM API (1 HTTP request)
4. Parse JSON response

Average: 1 database query, 1 API call
```

### Maintenance Burden

**Requires tuning**:
- Prompt engineering (iterative refinement)
- Confidence calibration (model says 0.8, but actual accuracy is 0.65?)
- Token budget management (context can grow large)

**No database extensions needed**:
- Just standard lookups for candidate entities

**Testing complexity**:
- Need LLM mocking (use recorded responses)
- Prompt regression tests (did prompt change break resolution?)
- Confidence calibration tests

---

## Approach 3: Hybrid (Deterministic Fast Path + LLM Fallback)

### Architecture

```python
async def resolve_entity_hybrid(
    mention_text: str,
    context: ResolutionContext
) -> ResolutionResult:
    """
    Best of both worlds: deterministic fast path, LLM for hard cases.
    """

    # FAST PATH: Exact match (Stage 1)
    exact_match = await db.execute("""
        SELECT canonical_entity_id, confidence
        FROM entity_aliases
        WHERE alias_text = $1 AND user_id IS NULL
        ORDER BY confidence DESC
        LIMIT 1
    """, mention_text)

    if exact_match and exact_match.confidence > 0.90:
        return ResolutionResult(
            canonical_entity_id=exact_match.canonical_entity_id,
            confidence=exact_match.confidence,
            method="exact_match",
            latency_ms=5
        )

    # FAST PATH: User-specific alias (Stage 2)
    user_alias = await db.execute("""
        SELECT canonical_entity_id, confidence
        FROM entity_aliases
        WHERE alias_text = $1 AND user_id = $2
        ORDER BY confidence DESC
        LIMIT 1
    """, mention_text, context.user_id)

    if user_alias and user_alias.confidence > 0.85:
        return ResolutionResult(
            canonical_entity_id=user_alias.canonical_entity_id,
            confidence=user_alias.confidence,
            method="user_alias",
            latency_ms=10
        )

    # SLOW PATH: LLM resolution for everything else
    # (handles fuzzy matching, coreference, context, ambiguity)

    # Fetch candidate entities from domain DB
    candidates = await fetch_candidate_entities(
        mention_text=mention_text,
        entity_types=context.expected_types,
        user_id=context.user_id
    )

    # Add recent entities for coreference
    candidates.extend(context.recent_entities)

    # Let LLM resolve
    llm_result = await resolve_entity_llm(
        mention_text=mention_text,
        candidates=candidates,
        context=context
    )

    # Learn from LLM decision (create alias for future fast path)
    if llm_result.confidence > 0.80 and llm_result.canonical_entity_id:
        await create_or_update_alias(
            alias_text=mention_text,
            canonical_entity_id=llm_result.canonical_entity_id,
            user_id=context.user_id,
            confidence=min(0.85, llm_result.confidence),
            source="llm_learned"
        )

    return ResolutionResult(
        canonical_entity_id=llm_result.canonical_entity_id,
        confidence=llm_result.confidence,
        method="llm_resolution",
        latency_ms=llm_result.latency_ms
    )
```

### Performance Profile

**Fast path (80-90% of cases)**:
- Latency: 5-10ms
- Cost: $0
- Confidence: 0.90-1.0

**LLM path (10-20% of cases)**:
- Latency: 200-500ms
- Cost: $0.003
- Confidence: 0.0-1.0 (model-dependent)

**Weighted average**:
- Latency: ~50ms (0.85 × 10ms + 0.15 × 300ms)
- Cost: ~$0.0005 per resolution (0.85 × $0 + 0.15 × $0.003)
- Cost at scale: 1,000 users × 300 resolutions/day = **$150/day** = **$4,500/month**

### Code Complexity

```python
# Estimated implementation size
hybrid_resolver.py:          ~200 lines
fast_path_matcher.py:        ~100 lines
llm_resolver.py:             ~150 lines
alias_learner.py:            ~100 lines
───────────────────────────────────
Total:                       ~550 lines

# Moderate complexity, best trade-off
```

---

## Comparative Analysis

### 1. Latency

| Approach | P50 | P95 | P99 |
|----------|-----|-----|-----|
| **Multi-Step** | 10ms | 50ms | 200ms (disambiguation) |
| **Pure LLM** | 300ms | 500ms | 800ms |
| **Hybrid** | 10ms | 300ms | 500ms |

**Winner**: Multi-Step (fast) or Hybrid (good balance)

### 2. Cost

| Approach | Per Resolution | 1000 users/month | Notes |
|----------|---------------|------------------|-------|
| **Multi-Step** | $0 | $0 | Infrastructure only |
| **Pure LLM** | $0.003 | $27,000 | At 300 resolutions/user/day |
| **Hybrid** | $0.0005 | $4,500 | 15% hit LLM path |

**Winner**: Multi-Step (free) or Hybrid (manageable cost)

### 3. Accuracy

| Approach | Exact Match | Fuzzy | Coreference | Ambiguous |
|----------|------------|-------|-------------|-----------|
| **Multi-Step** | 100% | 85%* | 75%* | 90% (user disambig) |
| **Pure LLM** | 98%** | 95%** | 90%** | 85%** |
| **Hybrid** | 100% | 95% | 90% | 90% |

\* Depends on heuristic tuning
\*\* Depends on model capability and prompt quality

**Winner**: Hybrid (gets best of both)

### 4. Development Complexity

| Aspect | Multi-Step | Pure LLM | Hybrid |
|--------|-----------|----------|--------|
| **Initial implementation** | 1250 lines | 300 lines | 550 lines |
| **Database setup** | pg_trgm + indexes | Basic indexes | Basic indexes |
| **Prompt engineering** | None | High effort | Medium effort |
| **Heuristic tuning** | 5-6 parameters | Confidence calibration | 2-3 parameters |
| **Testing complexity** | High | Medium | Medium |

**Winner**: Pure LLM (simplest) or Hybrid (good balance)

### 5. Debuggability

| Approach | Explainability | Determinism | Reproducibility |
|----------|---------------|-------------|-----------------|
| **Multi-Step** | ✅ Excellent (stage + confidence) | ✅ Fully deterministic | ✅ 100% reproducible |
| **Pure LLM** | ⚠️ Good (reasoning field) | ❌ Non-deterministic | ⚠️ ~95% with temp=0 |
| **Hybrid** | ✅ Excellent (method field) | ⚠️ Fast path deterministic | ✅ Fast path 100%, LLM ~95% |

**Winner**: Multi-Step or Hybrid

### 6. Maintainability

**Multi-Step requires**:
- Tuning fuzzy match thresholds
- Calibrating confidence by stage
- Maintaining coreference logic
- Managing database indexes

**Pure LLM requires**:
- Prompt versioning
- Confidence calibration
- Managing token budgets
- LLM provider changes

**Hybrid requires**:
- Fast path maintenance (simpler than full multi-step)
- LLM prompt maintenance
- Alias learning logic

**Winner**: Pure LLM (fewer moving parts) or Hybrid

### 7. Evolution & Learning

| Capability | Multi-Step | Pure LLM | Hybrid |
|-----------|-----------|----------|--------|
| **Learn from user corrections** | ✅ Create aliases | ✅ In-context examples | ✅ Both |
| **Adapt to new entity types** | ❌ Requires code changes | ✅ Just update prompt | ✅ Just update prompt |
| **Handle typos** | ⚠️ Fuzzy match (limited) | ✅ Natural language understanding | ✅ LLM handles it |
| **Multi-language** | ❌ Requires i18n | ✅ Native capability | ✅ Native capability |

**Winner**: Pure LLM or Hybrid

---

## Real-World Scenarios

### Scenario 1: "What did Acme Corporation order last month?"

**Multi-Step**:
1. Stage 1: Exact match "Acme Corporation" → customer:xxx (5ms, $0, confidence: 1.0)
2. ✅ Total: 5ms, $0

**Pure LLM**:
1. Fetch candidates from domain.customers (10ms)
2. Call LLM with context (300ms, $0.003)
3. ✅ Total: 310ms, $0.003

**Hybrid**:
1. Fast path: Exact match → customer:xxx (5ms, $0)
2. ✅ Total: 5ms, $0

**Winner**: Multi-Step or Hybrid (20x faster, free)

---

### Scenario 2: "What did they order?" (pronoun coreference)

**Multi-Step**:
1. Stages 1-3: No match
2. Stage 4: Coreference → recent_entities[0] (10ms, $0, confidence: 0.60)
3. ✅ Total: 15ms, $0
4. Accuracy: 75% (may pick wrong entity)

**Pure LLM**:
1. Fetch recent entities (5ms)
2. Call LLM with conversation context (300ms, $0.003)
3. LLM understands "they" refers to most recent customer
4. ✅ Total: 305ms, $0.003
5. Accuracy: ~90% (better context understanding)

**Hybrid**:
1. Fast path: No match
2. LLM path: Same as Pure LLM
3. ✅ Total: 305ms, $0.003
4. Accuracy: ~90%

**Winner**: LLM or Hybrid (higher accuracy, acceptable latency for complex case)

---

### Scenario 3: "Tell me about Apple" (ambiguous: customer vs product?)

**Multi-Step**:
1. Stage 1-2: Finds alias "Apple" → [customer:xxx, product:yyy]
2. Use recent context heuristic: Last entity was an order → prefer customer
3. ✅ Total: 20ms, $0, confidence: 0.65
4. Accuracy: ~70% (heuristic-based)

**Pure LLM**:
1. Fetch candidates: customer:xxx, product:yyy (10ms)
2. Call LLM with context (300ms, $0.003)
3. LLM reasons about conversation topic
4. ✅ Total: 310ms, $0.003
5. Accuracy: ~85% (better reasoning)

**Hybrid**:
1. Fast path: No high-confidence match
2. LLM path: Same as Pure LLM
3. ✅ Total: 310ms, $0.003
4. Accuracy: ~85%

**Winner**: LLM or Hybrid (better accuracy on ambiguous cases)

---

### Scenario 4: "Check the status of SO-1001" (exact match)

**Multi-Step**:
1. Stage 1: Exact match "SO-1001" → order:1001 (5ms, $0, confidence: 1.0)
2. ✅ Total: 5ms, $0

**Pure LLM**:
1. Fetch candidates (5ms)
2. Call LLM (300ms, $0.003)
3. ✅ Total: 305ms, $0.003

**Hybrid**:
1. Fast path: Exact match → order:1001 (5ms, $0)
2. ✅ Total: 5ms, $0

**Winner**: Multi-Step or Hybrid (60x faster, free)

---

## Recommendation

### 🏆 **Hybrid Approach** (Deterministic Fast Path + LLM Fallback)

**Rationale**:

1. **Performance**: Fast path handles 80-90% of cases in <10ms with $0 cost
2. **Accuracy**: LLM handles complex cases (coreference, ambiguity, typos) with 90%+ accuracy
3. **Cost**: ~$4,500/month at 1,000 users (vs $27,000 for pure LLM)
4. **Simplicity**: ~550 lines (vs 1,250 for full multi-step)
5. **Learning**: LLM decisions create aliases, moving cases to fast path over time
6. **Debuggability**: Method field shows which path was used
7. **Evolution**: Easy to adapt to new entity types (just update prompt)

### Implementation Strategy

**Phase 1: MVP** (Weeks 3-4)
```python
# Implement hybrid resolver
✅ Fast path: Exact + user alias lookup (stages 1-2)
✅ LLM path: For everything else
✅ Alias learning: Store LLM decisions for future fast path
✅ Basic prompt with confidence scoring
```

**Phase 2: Optimization** (Weeks 5-6)
```python
# Tune fast path coverage
✅ Track fast path hit rate (target: 85%+)
✅ Add common patterns to aliases (e.g., "SO-XXXX" → order)
✅ Confidence calibration for LLM path
```

**Phase 3: Advanced Features** (Phase 2 of roadmap)
```python
# Enhanced LLM capabilities
✅ Multi-turn disambiguation ("Did you mean X or Y?")
✅ Learned patterns from LLM reasoning
✅ Confidence decay and validation
```

### Code Structure

```python
# src/domain/services/entity_resolver.py
class HybridEntityResolver:
    def __init__(
        self,
        alias_repository: EntityAliasRepository,
        llm_service: LLMService,
        learning_service: AliasLearningService
    ):
        self.fast_path = FastPathResolver(alias_repository)
        self.llm_path = LLMEntityResolver(llm_service)
        self.learner = learning_service

    async def resolve(
        self,
        mention: str,
        context: ResolutionContext
    ) -> ResolutionResult:
        # Try fast path first
        result = await self.fast_path.resolve(mention, context)

        if result.confidence > 0.85:
            return result  # High confidence, done!

        # Fall back to LLM
        llm_result = await self.llm_path.resolve(mention, context)

        # Learn from LLM decision
        if llm_result.confidence > 0.80:
            await self.learner.create_alias_from_llm(
                mention, llm_result, context
            )

        return llm_result
```

### Cost-Benefit Analysis

| Metric | Multi-Step | Hybrid | Pure LLM |
|--------|-----------|--------|----------|
| **Development time** | 3 weeks | 1.5 weeks | 1 week |
| **Code complexity** | High (1250 lines) | Medium (550 lines) | Low (300 lines) |
| **Monthly cost (1K users)** | $0 | $4,500 | $27,000 |
| **P95 latency** | 50ms | 300ms | 500ms |
| **Accuracy (complex cases)** | 75% | 90% | 90% |
| **Maintainability** | Medium | Medium-High | High |
| **Adaptability** | Low | High | High |

**Break-even**: At current LLM pricing, hybrid approach is worth it if:
- Development time saved > $4,500/month in engineering costs
- Higher accuracy on complex cases improves user experience
- Adaptability matters for evolving entity types

**Verdict**: ✅ **Hybrid is the pragmatic choice for Phase 1**

---

## Migration Path (If Starting Fresh)

**Week 1**: Implement pure LLM approach (fastest to MVP)
- Get working end-to-end
- Measure LLM path performance and cost
- Collect resolution examples

**Week 2**: Add fast path for common cases
- Analyze most common entity mentions
- Implement exact + user alias lookups
- Measure fast path hit rate

**Week 3**: Add learning
- Store LLM decisions as aliases
- Watch fast path hit rate increase over time
- Target: 85%+ hit rate by end of month

**Result**: You've essentially built the hybrid approach incrementally, validating each step.

---

## Conclusion

The **hybrid approach** combines the best of both worlds:

✅ **Fast** for common cases (exact matches, learned aliases)
✅ **Smart** for hard cases (LLM handles context, ambiguity, typos)
✅ **Cost-effective** (only pay for LLM on 10-20% of cases)
✅ **Self-improving** (LLM decisions become future fast path entries)
✅ **Maintainable** (~550 lines vs 1,250 for full multi-step)
✅ **Debuggable** (method field shows which path was used)

The pure LLM approach is simpler initially but becomes expensive at scale. The full multi-step approach is faster and free but complex to maintain and less adaptable.

**Recommendation**: Start with hybrid approach in Phase 1. It's the pragmatic middle ground.
