# Entity Resolution: Hybrid Fast Path + LLM Approach

**Version**: 2.0 - LLM-First Architecture
**Date**: 2025-10-15
**Status**: Active Design (replaces complex 5-stage algorithm)

---

## Design Decision

After comparing the original 5-stage deterministic algorithm vs pure LLM vs hybrid approaches (see `ENTITY_RESOLUTION_COMPARISON.md`), we're adopting a **hybrid architecture**:

- **Fast path** (exact + user alias lookups) handles 80-90% of cases in <10ms with $0 cost
- **LLM path** handles hard cases (fuzzy, coreference, ambiguity) in ~300ms with ~$0.003 cost
- **Self-improving**: LLM decisions create aliases, moving cases to fast path over time

**Result**: Best of both worlds - speed + intelligence + cost-effectiveness

---

## Architecture Overview

```python
async def resolve_entity_hybrid(
    mention: str,
    context: ResolutionContext
) -> ResolutionResult:
    """
    Two-path entity resolution: deterministic fast path + LLM fallback.
    """

    # ═══════════════════════════════════════════════════════
    # FAST PATH: Deterministic lookups (80-90% of cases)
    # ═══════════════════════════════════════════════════════

    # Path 1: Exact global alias match
    exact_match = await db.execute("""
        SELECT canonical_entity_id, confidence
        FROM entity_aliases
        WHERE alias_text = $1 AND user_id IS NULL
        ORDER BY confidence DESC
        LIMIT 1
    """, mention)

    if exact_match and exact_match.confidence > 0.90:
        return ResolutionResult(
            canonical_entity_id=exact_match.canonical_entity_id,
            confidence=exact_match.confidence,
            method="exact_match",
            latency_ms=5
        )

    # Path 2: User-specific alias match
    user_alias = await db.execute("""
        SELECT canonical_entity_id, confidence
        FROM entity_aliases
        WHERE alias_text = $1 AND user_id = $2
        ORDER BY confidence DESC
        LIMIT 1
    """, mention, context.user_id)

    if user_alias and user_alias.confidence > 0.85:
        return ResolutionResult(
            canonical_entity_id=user_alias.canonical_entity_id,
            confidence=user_alias.confidence,
            method="user_alias",
            latency_ms=10
        )

    # ═══════════════════════════════════════════════════════
    # LLM PATH: Complex resolution (10-20% of cases)
    # ═══════════════════════════════════════════════════════

    # Fetch candidate entities for LLM to consider
    candidates = await fetch_candidates(
        mention=mention,
        user_id=context.user_id,
        limit=10
    )

    # Let LLM resolve with full context
    llm_result = await resolve_entity_llm(
        mention=mention,
        candidates=candidates,
        context=context
    )

    # Learn from LLM decision (create alias for future fast path)
    if llm_result.confidence > 0.80 and llm_result.canonical_entity_id:
        await create_or_update_alias(
            alias_text=mention,
            canonical_entity_id=llm_result.canonical_entity_id,
            user_id=context.user_id if llm_result.is_user_specific else None,
            confidence=min(0.85, llm_result.confidence),
            source="llm_learned"
        )

    return ResolutionResult(
        canonical_entity_id=llm_result.canonical_entity_id,
        confidence=llm_result.confidence,
        method="llm_resolution",
        latency_ms=llm_result.latency_ms,
        reasoning=llm_result.reasoning
    )
```

---

## LLM Resolution Implementation

### Prompt Design

```python
async def resolve_entity_llm(
    mention: str,
    candidates: List[CanonicalEntity],
    context: ResolutionContext
) -> LLMResolutionResult:
    """
    Use LLM to resolve entity mention with candidates and context.

    Handles:
    - Fuzzy matching ("Acme" → "Acme Corporation")
    - Coreference ("they" → most recent customer entity)
    - Typos/variations ("ACME Corp" → "Acme Corporation")
    - Ambiguity resolution (multiple candidates → pick best or ask user)
    """

    prompt = f"""
You are an entity resolver for a business intelligence system.

**Task**: Resolve the entity mention "{mention}" to a canonical entity ID.

**Candidate Entities** (from database):
{format_candidates(candidates)}

**Conversation Context**:
Recent messages (last 3):
{format_recent_messages(context.recent_messages)}

Recent entities mentioned:
{format_recent_entities(context.recent_entities)}

**Resolution Rules**:
1. If mention matches a candidate name (exact or fuzzy), choose that candidate
2. If mention is a pronoun ("they", "them", "it"), use recent conversation context
3. If multiple candidates match, choose most likely based on context
4. If no good match, set canonical_entity_id = null
5. If ambiguous (multiple equally likely), set requires_disambiguation = true

**Confidence Guidelines**:
- 0.95-1.0: Exact match or unambiguous context
- 0.80-0.94: High confidence fuzzy match or clear coreference
- 0.65-0.79: Reasonable match but some uncertainty
- 0.40-0.64: Weak match, needs disambiguation
- 0.0-0.39: No good match found

**Output Format** (JSON):
{{
  "canonical_entity_id": "customer:xxx" or null,
  "confidence": 0.85,
  "is_user_specific": false,
  "alternative_candidates": ["customer:yyy", "customer:zzz"],
  "requires_disambiguation": false,
  "reasoning": "The mention 'Acme' most likely refers to 'Acme Corporation' based on exact name match and recent discussion about this customer."
}}
"""

    response = await llm.generate(
        prompt=prompt,
        model="gpt-4-turbo",
        temperature=0.0,
        response_format="json",
        max_tokens=500
    )

    return LLMResolutionResult.parse(response)
```

### Candidate Fetching

```python
async def fetch_candidates(
    mention: str,
    user_id: str,
    limit: int = 10
) -> List[CanonicalEntity]:
    """
    Fetch candidate entities for LLM to consider.

    Sources:
    1. Fuzzy text matches (pg_trgm similarity)
    2. Recent entities from conversation
    3. Domain database search
    """
    candidates = []

    # Source 1: Fuzzy matches from existing entities
    fuzzy_matches = await db.fetch("""
        SELECT ce.*, similarity(ea.alias_text, $1) as sim_score
        FROM canonical_entities ce
        JOIN entity_aliases ea ON ea.canonical_entity_id = ce.entity_id
        WHERE similarity(ea.alias_text, $1) > 0.5
        ORDER BY sim_score DESC
        LIMIT 5
    """, mention)
    candidates.extend(fuzzy_matches)

    # Source 2: Recent entities from conversation
    if context.recent_entities:
        recent = await db.fetch("""
            SELECT * FROM canonical_entities
            WHERE entity_id = ANY($1)
        """, context.recent_entities)
        candidates.extend(recent)

    # Source 3: Search domain database (lazy entity creation)
    domain_matches = await search_domain_database(mention, limit=5)
    for match in domain_matches:
        # Create canonical entity if doesn't exist
        entity = await ensure_canonical_entity(
            entity_type=match.entity_type,
            external_ref=match.external_ref,
            canonical_name=match.name,
            properties=match.properties
        )
        candidates.append(entity)

    # Deduplicate by entity_id
    unique_candidates = {c.entity_id: c for c in candidates}
    return list(unique_candidates.values())[:limit]
```

---

## Canonical Entities & Aliases (Database Layer)

### Two-Table Design

```sql
-- Layer 1: Canonical entities (source of truth)
CREATE TABLE app.canonical_entities (
  entity_id TEXT PRIMARY KEY,           -- "customer:a1b2c3d4"
  entity_type TEXT NOT NULL,            -- "customer"
  canonical_name TEXT NOT NULL,         -- "Acme Corporation"
  external_ref JSONB NOT NULL,          -- {"customer_id": "a1b2c3d4"}
  properties JSONB,                     -- {"industry": "tech", ...}
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Layer 2: Entity aliases (multiple names for same entity)
CREATE TABLE app.entity_aliases (
  alias_id BIGSERIAL PRIMARY KEY,
  canonical_entity_id TEXT NOT NULL REFERENCES app.canonical_entities(entity_id),
  alias_text TEXT NOT NULL,
  alias_source TEXT NOT NULL,          -- 'domain_db', 'llm_learned', 'user_explicit'
  user_id TEXT,                        -- NULL = global, not-null = user-specific
  confidence REAL NOT NULL DEFAULT 1.0,
  use_count INT NOT NULL DEFAULT 1,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(alias_text, user_id, canonical_entity_id)
);

CREATE INDEX idx_aliases_lookup ON app.entity_aliases(alias_text, user_id, confidence);
CREATE INDEX idx_aliases_trigram ON app.entity_aliases USING gin(alias_text gin_trgm_ops);
```

**Design principle**: Canonical entities are facts about the domain database. Aliases are facts about language and user context.

### Lazy Entity Creation

```python
async def ensure_canonical_entity(
    entity_type: str,
    external_ref: dict,
    canonical_name: str,
    properties: dict
) -> CanonicalEntity:
    """
    Create canonical entity if doesn't exist, otherwise return existing.

    Idempotency key: (entity_type, external_ref)
    """
    entity_id = f"{entity_type}:{external_ref[f'{entity_type}_id']}"

    # Check if exists
    existing = await db.fetchrow("""
        SELECT * FROM canonical_entities WHERE entity_id = $1
    """, entity_id)

    if existing:
        return CanonicalEntity.from_db(existing)

    # Create new
    created = await db.fetchrow("""
        INSERT INTO canonical_entities (entity_id, entity_type, canonical_name, external_ref, properties)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (entity_id) DO UPDATE SET
          canonical_name = EXCLUDED.canonical_name,
          properties = EXCLUDED.properties,
          updated_at = now()
        RETURNING *
    """, entity_id, entity_type, canonical_name, external_ref, properties)

    # Create global alias for canonical name
    await db.execute("""
        INSERT INTO entity_aliases (canonical_entity_id, alias_text, alias_source, user_id, confidence)
        VALUES ($1, $2, 'domain_db', NULL, 0.95)
        ON CONFLICT (alias_text, user_id, canonical_entity_id) DO NOTHING
    """, entity_id, canonical_name)

    return CanonicalEntity.from_db(created)
```

---

## Self-Improving Alias Learning

### Learning from LLM Decisions

```python
async def create_or_update_alias(
    alias_text: str,
    canonical_entity_id: str,
    user_id: str | None,
    confidence: float,
    source: str
):
    """
    Create new alias or increment use_count if exists.

    Over time, frequently used LLM-learned aliases move to fast path.
    """
    await db.execute("""
        INSERT INTO entity_aliases (
          canonical_entity_id, alias_text, alias_source,
          user_id, confidence, use_count
        )
        VALUES ($1, $2, $3, $4, $5, 1)
        ON CONFLICT (alias_text, user_id, canonical_entity_id) DO UPDATE SET
          use_count = entity_aliases.use_count + 1,
          confidence = LEAST(0.95, entity_aliases.confidence + 0.02)
    """, canonical_entity_id, alias_text, source, user_id, confidence)
```

**Result**: After ~5 uses, an LLM-learned alias reaches confidence > 0.85 and starts hitting fast path.

### Metrics Tracking

```python
# Track resolution path distribution
resolution_metrics = {
    "exact_match": 0.70,      # 70% hit exact match
    "user_alias": 0.15,       # 15% hit user-specific
    "llm_resolution": 0.15    # 15% need LLM (target < 20%)
}

# Goal: Increase fast path hit rate over time
# Week 1: 85% fast path
# Week 4: 90% fast path (as LLM decisions become aliases)
# Week 12: 92% fast path
```

---

## Disambiguation Flow

### When LLM Detects Ambiguity

```python
# LLM returns:
{
  "canonical_entity_id": "customer:acme_a1b2c3d4",  # Best guess
  "confidence": 0.55,  # Low confidence
  "alternative_candidates": ["customer:acme_a1b2", "customer:acme_x9y8"],
  "requires_disambiguation": true,
  "reasoning": "Multiple entities named 'Acme'. Need user to clarify."
}

# System response to user:
"I found multiple entities matching 'Acme'. Which one do you mean?
  1. Acme Corporation (last discussed 2 days ago)
  2. Acme Industries (last discussed 1 month ago)
  3. None of these / search for different entity"

# User selects #1

# Create disambiguation alias:
await create_or_update_alias(
    alias_text="Acme",
    canonical_entity_id="customer:acme_a1b2c3d4",
    user_id=current_user_id,  # User-specific learning
    confidence=0.85,  # High confidence after explicit selection
    source="user_disambiguation"
)

# Next time user says "Acme", fast path hits user-specific alias!
```

---

## Performance Characteristics

### Latency Breakdown

| Path | P50 | P95 | P99 | Frequency |
|------|-----|-----|-----|-----------|
| **Exact match** | 3ms | 5ms | 8ms | 70% |
| **User alias** | 5ms | 8ms | 12ms | 15% |
| **LLM resolution** | 250ms | 350ms | 500ms | 15% |
| **Weighted average** | **40ms** | **70ms** | **350ms** | 100% |

### Cost Analysis

| Path | Cost per Resolution | Frequency | Weighted Cost |
|------|---------------------|-----------|---------------|
| **Fast path** | $0 | 85% | $0 |
| **LLM path** | $0.003 | 15% | $0.00045 |
| **Average cost** | | | **$0.00045** |

**At scale** (1,000 users × 50 requests/day × 3 entities/request):
- 150,000 resolutions/day
- Cost: $67.50/day = **$2,025/month**

---

## Code Complexity Comparison

### Before (5-Stage Algorithm)

```python
# entity_resolver.py: ~500 lines
# fuzzy_matcher.py: ~150 lines
# coreference_resolver.py: ~200 lines
# disambiguation_handler.py: ~100 lines
# Pattern matching, heuristics, scoring logic
Total: ~950 lines
```

### After (Hybrid Approach)

```python
# hybrid_resolver.py: ~200 lines
#   - Fast path: 50 lines (2 SQL queries)
#   - LLM path: 100 lines (prompt + parsing)
#   - Alias learning: 50 lines
# candidate_fetcher.py: ~100 lines
# llm_prompts.py: ~50 lines
Total: ~350 lines (63% reduction!)
```

---

## Testing Strategy

### Fast Path Tests (Unit)

```python
@pytest.mark.asyncio
async def test_exact_match_returns_immediately():
    # Given: Alias exists
    await create_alias(alias="Acme Corporation", entity_id="customer:xxx", user_id=None)

    # When: Resolve exact match
    result = await hybrid_resolver.resolve("Acme Corporation", context)

    # Then: Fast path hit
    assert result.method == "exact_match"
    assert result.latency_ms < 10
    assert result.confidence == 0.95
```

### LLM Path Tests (Integration)

```python
@pytest.mark.asyncio
async def test_llm_handles_fuzzy_match():
    # Given: No exact alias, but fuzzy candidate exists
    await create_entity(entity_id="customer:xxx", canonical_name="Acme Corporation")

    # When: Resolve fuzzy mention
    result = await hybrid_resolver.resolve("ACME Corp", context)

    # Then: LLM path resolves correctly
    assert result.method == "llm_resolution"
    assert result.canonical_entity_id == "customer:xxx"
    assert result.confidence > 0.80
    assert "Acme Corporation" in result.reasoning
```

### Learning Tests

```python
@pytest.mark.asyncio
async def test_llm_decision_creates_alias():
    # When: LLM resolves with high confidence
    result = await hybrid_resolver.resolve("Acme", context)
    assert result.method == "llm_resolution"

    # Then: Alias is created for future
    alias = await db.fetchrow("SELECT * FROM entity_aliases WHERE alias_text = 'Acme'")
    assert alias is not None
    assert alias.source == "llm_learned"

    # And: Next resolution hits fast path
    result2 = await hybrid_resolver.resolve("Acme", context)
    assert result2.method == "user_alias"  # Fast path!
```

---

## Summary

**Hybrid entity resolution** combines deterministic fast path (85% of cases, <10ms, $0) with LLM intelligence (15% of cases, ~300ms, $0.003).

**Key benefits**:
1. **Performance**: 40ms P50 latency (vs 300ms pure LLM)
2. **Cost**: $0.00045 per resolution (vs $0.003 pure LLM)
3. **Accuracy**: 90%+ on complex cases (vs 70% with heuristics)
4. **Simplicity**: 350 lines vs 950 lines (63% reduction)
5. **Self-improving**: LLM decisions become future fast-path entries

**Phase 1 implementation**: ~1.5 weeks (vs 3 weeks for 5-stage algorithm)

See `ENTITY_RESOLUTION_COMPARISON.md` for detailed analysis of alternatives.
