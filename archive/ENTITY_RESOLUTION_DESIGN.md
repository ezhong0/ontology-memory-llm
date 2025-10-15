# Entity Resolution and Linking System

## Vision Alignment

From VISION.md:
> "The system must understand that 'the customer' in one context might be 'Acme Corp' but in another context might be 'Initech'. It must track these references not just as strings but as pointers to business entities with rich relationships."

Entity resolution is not a technical detail—it's fundamental to the system's ability to understand business context. Without it, the system cannot:
- Know what "the customer" means
- Understand coreference chains ("they ordered X, their invoice...")
- Build semantic memories about specific entities
- Traverse ontological relationships

## The Entity Resolution Problem

### Three Fundamental Challenges

**1. Ambiguity**: One phrase, multiple possible entities
```
User: "What did the customer order?"
System: Which customer? (There are 47 active customers)
```

**2. Variation**: Multiple phrases, one entity
```
"Acme Corporation" = "ACME Corp" = "Acme" = "the customer" (in context)
```

**3. Evolution**: Entities and their properties change over time
```
T0: "John's company" → customer:123 (confidence: 0.9)
T1: John leaves the company
T2: "John's company" → ??? (previous resolution now invalid)
```

## Core Architecture

### Two-Layer Design

```
┌─────────────────────────────────────────┐
│  Layer 1: Canonical Entity Layer        │
│  (Source of truth, linked to domain DB) │
└─────────────────────────────────────────┘
                  ↑
                  │ references
                  │
┌─────────────────────────────────────────┐
│  Layer 2: Alias Layer                   │
│  (Multiple names, per-user context)     │
└─────────────────────────────────────────┘
```

**Why this separation?**
- Vision principle: Distinction between correspondence truth (canonical) and contextual truth (aliases)
- Canonical entities are facts about the domain database
- Aliases are facts about language and user context
- One changes rarely (canonical), other changes frequently (aliases)

## Canonical Entities: The Truth Layer

```sql
CREATE TABLE app.canonical_entities (
  entity_id TEXT PRIMARY KEY,           -- "customer:a1b2c3d4"
  entity_type TEXT NOT NULL,            -- "customer"
  canonical_name TEXT NOT NULL,         -- "Acme Corporation"
  external_ref JSONB NOT NULL,          -- {"customer_id": "a1b2c3d4"}
  properties JSONB,                     -- {"industry": "tech", ...}
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);
```

### Design Decisions

**Q: Why TEXT for entity_id instead of UUID?**

A: Semantic structure. `"customer:a1b2c3d4"` is self-documenting:
- The type is visible in the ID itself
- Debugging is easier ("oh, that's a customer")
- Matches domain database reference pattern
- Avoids join to get type in most queries

**Q: What goes in external_ref vs properties?**

A: **external_ref** = how to query domain database (required, stable)
```json
{"customer_id": "a1b2c3d4"}  // Required to JOIN to domain.customers
```

**properties** = discovered facts about entity (optional, evolving)
```json
{
  "industry": "technology",
  "last_order_date": "2024-01-15",
  "preferred_payment_terms": "NET30"
}
```

**Q: Why allow properties to evolve in JSONB?**

A: Vision principle: "graceful evolution." We discover entity properties over time. Starting with rigid schema would require migrations for every discovered property type. JSONB allows the ontology to emerge from usage.

### Canonical Entity Lifecycle

```
┌──────────┐
│ Domain   │  1. Chat mentions "Acme Corporation"
│ Database │     System queries: SELECT * FROM domain.customers WHERE name ILIKE '%acme%'
└────┬─────┘     Finds customer_id = 'a1b2c3d4'
     │
     ↓
┌──────────────────────────────────────┐
│ 2. Create Canonical Entity           │
│    entity_id: "customer:a1b2c3d4"    │
│    entity_type: "customer"           │
│    canonical_name: "Acme Corporation"│
│    external_ref: {"customer_id": ..} │
└──────────────────────────────────────┘
```

**Idempotency**: Use `(entity_type, external_ref)` as natural key. If entity already exists, reuse it.

## Entity Aliases: The Context Layer

```sql
CREATE TABLE app.entity_aliases (
  alias_id BIGSERIAL PRIMARY KEY,
  canonical_entity_id TEXT NOT NULL REFERENCES app.canonical_entities(entity_id),
  alias_text TEXT NOT NULL,
  alias_source TEXT NOT NULL,          -- 'user_input', 'llm_extraction', 'domain_db'
  user_id TEXT,                        -- NULL = global alias
  confidence REAL NOT NULL DEFAULT 1.0,
  use_count INT NOT NULL DEFAULT 1,
  metadata JSONB,                      -- disambiguation context, etc.
  created_at TIMESTAMPTZ NOT NULL,
  UNIQUE(alias_text, user_id, canonical_entity_id)
);
```

### Design Decisions

**Q: Why per-user aliases (user_id nullable)?**

A: Three levels of alias scope:

1. **Global aliases** (user_id = NULL): "Acme Corporation" → customer:a1b2c3d4
   - From domain database canonical name
   - High confidence, works for all users

2. **User-specific aliases** (user_id set): "my main customer" → customer:a1b2c3d4
   - From user's language patterns
   - Only valid for that user
   - Handles personalization

3. **Disambiguated aliases** (metadata contains disambiguation_context):
   - "the customer" → customer:a1b2c3d4 (when discussing Order #12345)
   - Same alias_text, different metadata

**Q: Why track use_count?**

A: Confidence boosting. If user says "Acme" 47 times and it always means customer:a1b2c3d4, confidence should increase. But if suddenly one mention is ambiguous, that matters more.

Formula:
```
effective_confidence = base_confidence * (1 + log(1 + use_count) * 0.1)
```

More usage → higher confidence, but logarithmic (diminishing returns).

**Q: Why store confidence per alias?**

A: Different aliases have different ambiguity levels:
- "Acme Corporation" (confidence: 0.95) - distinctive, unlikely to be wrong
- "Acme" (confidence: 0.75) - could be other companies
- "the customer" (confidence: 0.60) - highly context-dependent
- "they" (confidence: 0.40) - pronoun, needs recency coreference

### Alias Sources and Confidence

```python
alias_source → base_confidence:
  'domain_db'         → 0.95  # From canonical name in database
  'llm_extraction'    → 0.70  # LLM identified entity mention
  'user_explicit'     → 0.90  # User explicitly stated "X is Y"
  'coreference'       → 0.60  # Inferred from coreference chain
  'disambiguation'    → 0.85  # User chose from ambiguous options
```

## The Resolution Algorithm

### Input
```
mention_text: str          # e.g., "Acme"
context: ResolutionContext # containing user_id, conversation entities, recency
```

### Output
```python
@dataclass
class ResolutionResult:
    canonical_entity_id: str | None      # "customer:a1b2c3d4" or None
    confidence: float                     # 0.0 to 1.0
    candidates: List[Candidate]           # Alternative possibilities
    requires_disambiguation: bool         # Should we ask user?
    resolution_explanation: str           # For debugging/explanation
```

### Five-Stage Algorithm

#### Stage 1: Exact Match (High Confidence)

```sql
-- Find exact global aliases
SELECT canonical_entity_id, confidence, use_count
FROM app.entity_aliases
WHERE alias_text = $mention_text
  AND user_id IS NULL
ORDER BY confidence * (1 + log(1 + use_count) * 0.1) DESC
LIMIT 1;
```

**If found with confidence > 0.85**: Return immediately. "Acme Corporation" almost certainly means the official customer.

#### Stage 2: User-Specific Match

```sql
-- Find user-specific aliases
SELECT canonical_entity_id, confidence, use_count, metadata
FROM app.entity_aliases
WHERE alias_text = $mention_text
  AND user_id = $user_id
ORDER BY confidence * (1 + log(1 + use_count) * 0.1) DESC
LIMIT 1;
```

**If found**: Check if context matches metadata.disambiguation_context:
```python
if alias.metadata.get('disambiguation_context'):
    # e.g., "the customer" only valid when discussing order_id:12345
    if current_context.matches(alias.metadata['disambiguation_context']):
        return ResolutionResult(
            canonical_entity_id=alias.canonical_entity_id,
            confidence=alias.confidence,
            candidates=[],
            requires_disambiguation=False
        )
```

#### Stage 3: Fuzzy Match with Semantic Similarity

```sql
-- Find similar aliases (fuzzy text + embedding similarity)
WITH fuzzy_matches AS (
  SELECT
    canonical_entity_id,
    alias_text,
    confidence,
    use_count,
    similarity(alias_text, $mention_text) AS text_similarity
  FROM app.entity_aliases
  WHERE similarity(alias_text, $mention_text) > 0.7  -- pg_trgm extension
    AND (user_id = $user_id OR user_id IS NULL)
)
SELECT
  fm.*,
  ce.canonical_name,
  ce.properties
FROM fuzzy_matches fm
JOIN app.canonical_entities ce ON ce.entity_id = fm.canonical_entity_id
ORDER BY
  text_similarity * fm.confidence DESC
LIMIT 5;
```

**Check semantic similarity** using entity properties:
```python
# If mention_text contains context clues
# "the tech customer" → check properties.industry = "tech"
# "the customer who ordered yesterday" → check last_order_date

for candidate in fuzzy_matches:
    semantic_score = compute_semantic_match(
        mention_text=mention_text,
        entity_properties=candidate.properties,
        conversation_context=context
    )
    candidate.final_score = (
        candidate.text_similarity * 0.4 +
        candidate.confidence * 0.3 +
        semantic_score * 0.3
    ) * (1 + log(1 + candidate.use_count) * 0.1)
```

#### Stage 4: Conversational Context (Coreference)

If mention is a pronoun or definite reference:
- "they" / "them" / "their"
- "the customer" / "the company" / "that order"

```python
def resolve_via_coreference(mention_text: str, context: ResolutionContext):
    """
    Look at recent conversation entities to resolve pronouns.
    """
    # Get entities from last N messages in session
    recent_entities = get_recent_entities(
        session_id=context.session_id,
        limit=10  # Last 10 messages
    )

    # Filter by entity type matching mention
    if "customer" in mention_text.lower():
        candidates = [e for e in recent_entities if e.entity_type == "customer"]
    elif mention_text.lower() in ["they", "them", "their", "it"]:
        # Use most recent entity of any type
        candidates = recent_entities[:1]

    # Score by recency (exponential decay)
    for i, candidate in enumerate(candidates):
        recency_score = exp(-0.5 * i)  # Most recent = 1.0, decay quickly
        candidate.score = candidate.base_confidence * recency_score

    return sorted(candidates, key=lambda c: c.score, reverse=True)
```

**Confidence adjustment**: Coreference is context-dependent, so max confidence = 0.70.

#### Stage 5: Disambiguation Required

If we reach here:
- No high-confidence match found
- Multiple candidates with similar scores
- Or no candidates at all

```python
if not candidates:
    # Attempt domain database search
    candidates = search_domain_database(mention_text)
    if not candidates:
        return ResolutionResult(
            canonical_entity_id=None,
            confidence=0.0,
            candidates=[],
            requires_disambiguation=True,
            resolution_explanation="No matching entities found in memory or domain database"
        )

if len(candidates) == 1 and candidates[0].score > 0.6:
    return ResolutionResult(
        canonical_entity_id=candidates[0].entity_id,
        confidence=candidates[0].score,
        candidates=candidates[1:],
        requires_disambiguation=False
    )
else:
    return ResolutionResult(
        canonical_entity_id=candidates[0].entity_id if candidates else None,
        confidence=candidates[0].score if candidates else 0.0,
        candidates=candidates,
        requires_disambiguation=True,
        resolution_explanation=f"Found {len(candidates)} possible matches"
    )
```

## Disambiguation Strategies

### When to Disambiguate?

**Ask user when:**
- Multiple candidates with similar scores (difference < 0.15)
- Highest confidence < 0.65
- High-stakes context (e.g., "issue refund to the customer")

**Assume best match when:**
- Clear winner (confidence > 0.80, or > 0.20 better than second place)
- Low-stakes context (e.g., "tell me about the customer")
- Can recover if wrong (not making database changes)

### Disambiguation UI Pattern

```
User: "What did the customer order?"

System: I found multiple customers in recent context. Which one do you mean?
  1. Acme Corporation (last mentioned 2 messages ago)
  2. Initech Inc (last mentioned 5 messages ago)
  3. None of these / search for different customer
```

**After user choice:**
```python
# Create disambiguation alias
await create_entity_alias(
    canonical_entity_id="customer:a1b2c3d4",  # User chose #1
    alias_text="the customer",
    alias_source="disambiguation",
    user_id=current_user_id,
    confidence=0.85,  # High confidence - user explicitly chose
    metadata={
        "disambiguation_context": {
            "session_id": current_session_id,
            "disambiguated_at": now(),
            "alternative_candidates": ["customer:x7y8z9", "customer:p9q8r7"],
            "scope": "session"  # Only valid within this session
        }
    }
)
```

### Learning from Disambiguation

Track patterns:
```sql
-- After N disambiguations, detect patterns
-- If user always chooses customer:a1b2c3d4 when "the customer" appears
-- after discussing orders, boost that pattern

INSERT INTO app.entity_aliases (
  canonical_entity_id,
  alias_text,
  alias_source,
  user_id,
  confidence,
  use_count,
  metadata
) VALUES (
  'customer:a1b2c3d4',
  'the customer',
  'learned_pattern',
  $user_id,
  0.75,  -- Learned patterns start moderate confidence
  1,
  jsonb_build_object(
    'pattern', 'appears after order discussion',
    'learned_from_disambiguations', 5
  )
)
ON CONFLICT (alias_text, user_id, canonical_entity_id) DO UPDATE SET
  use_count = app.entity_aliases.use_count + 1,
  confidence = LEAST(0.90, app.entity_aliases.confidence + 0.05);
```

## Integration with Episodic Memories

### Coreference Chains in Context

When creating episodic memories, store the full coreference chain:

```json
{
  "entities": [
    {
      "canonical_id": "customer:a1b2c3d4",
      "mentions": [
        {
          "text": "Acme Corporation",
          "position": "message:0",
          "confidence": 0.95
        },
        {
          "text": "they",
          "position": "message:1",
          "confidence": 0.70,
          "resolved_via": "coreference_to_previous"
        },
        {
          "text": "the customer",
          "position": "message:2",
          "confidence": 0.65,
          "resolved_via": "coreference_to_previous"
        }
      ]
    },
    {
      "canonical_id": "order:12345",
      "mentions": [
        {
          "text": "order #12345",
          "position": "message:1",
          "confidence": 0.98
        },
        {
          "text": "it",
          "position": "message:3",
          "confidence": 0.60,
          "resolved_via": "coreference_to_previous"
        }
      ]
    }
  ]
}
```

**Why store mentions inline in episodic memory?**
- Coreference is episodic context (vision: episodic vs semantic distinction)
- Query pattern: "What entities were discussed in this episode?" reads one record
- Separate table would require join for every episodic memory access

**Vision alignment**: Episodic memories are contextualized, temporal records. Coreference chains are part of that context.

## Domain Database Integration

### On-Demand Entity Discovery

```python
async def discover_entity_from_domain_db(
    mention_text: str,
    entity_type_hint: str | None = None
) -> List[CanonicalEntity]:
    """
    Search domain database for entities matching mention.
    Create canonical entities if found.
    """
    candidates = []

    # If type is known, search that table
    if entity_type_hint == "customer":
        results = await db.execute("""
            SELECT customer_id, name, industry, created_at
            FROM domain.customers
            WHERE name ILIKE $1 OR name % $1  -- ILIKE for substring, % for similarity
            ORDER BY similarity(name, $1) DESC
            LIMIT 5
        """, f"%{mention_text}%")

        for row in results:
            # Create or get canonical entity
            entity = await ensure_canonical_entity(
                entity_type="customer",
                external_ref={"customer_id": row.customer_id},
                canonical_name=row.name,
                properties={"industry": row.industry, "created_at": row.created_at}
            )
            candidates.append(entity)

    # If type unknown, search all tables (using domain ontology)
    else:
        entity_types = await get_all_entity_types()
        for entity_type in entity_types:
            results = await search_entity_type(entity_type, mention_text)
            candidates.extend(results)

    return candidates
```

### Lazy Entity Creation

**Philosophy**: Don't pre-import all domain database entities. Create canonical entities on-demand when:
1. User mentions them in conversation
2. They appear in a query result that's surfaced to user
3. They're needed to complete a semantic triple

**Why lazy?**
- Vision principle: relevance. Most domain entities will never be discussed.
- Reduces storage: Only track entities that have memory associations
- Simplifies initial setup: No bulk import needed

**When does an entity get imported?**
```
User: "Tell me about Acme Corporation's recent orders"
  ↓
1. Resolve "Acme Corporation" → Not in canonical_entities yet
2. Search domain.customers → Find customer_id: a1b2c3d4
3. Create canonical_entities record for customer:a1b2c3d4
4. Create entity_aliases record: "Acme Corporation" → customer:a1b2c3d4
5. Query domain.orders for customer:a1b2c3d4
6. Return results to user
7. Create episodic memory with entity reference
```

## Confidence Decay and Validation

### When Should Confidence Decay?

Aliases can become stale:
```
T0: "John's company" → customer:a1b2c3d4 (confidence: 0.85)
T1: +30 days, no mention
T2: "John's company" is mentioned again
    But John changed jobs!
    Confidence should have decayed due to staleness
```

**Decay formula**:
```python
def compute_current_confidence(alias: EntityAlias, now: datetime) -> float:
    """
    Decay confidence based on time since last use.
    """
    days_since_created = (now - alias.created_at).days
    days_since_last_used = (now - alias.last_used_at).days  # Would need this field

    # Base confidence
    conf = alias.confidence

    # Decay based on staleness (only for context-dependent aliases)
    if alias.metadata.get('context_dependent'):
        # Context-dependent aliases decay faster
        decay_rate = 0.02  # 2% per day
        conf *= exp(-decay_rate * days_since_last_used)
    else:
        # Stable aliases decay slower
        decay_rate = 0.002  # 0.2% per day
        conf *= exp(-decay_rate * days_since_last_used)

    # Usage boost (more usage = more reliable)
    usage_boost = log(1 + alias.use_count) * 0.1
    conf *= (1 + usage_boost)

    return min(1.0, conf)
```

**Implementation choice**: Compute decay on-demand (passive) vs pre-compute (active).

Per design philosophy: **Passive computation preferred** for simple formulas.

```sql
-- On-demand decay in query
SELECT
  alias_text,
  canonical_entity_id,
  confidence * EXP(-0.02 * EXTRACT(EPOCH FROM (now() - created_at)) / 86400)
    AS current_confidence
FROM app.entity_aliases
WHERE alias_text = $mention_text
  AND confidence * EXP(-0.02 * EXTRACT(EPOCH FROM (now() - created_at)) / 86400) > 0.3
ORDER BY current_confidence DESC;
```

### Validation Triggers

Proactively validate aliases when:
1. **Contradiction detected**: Semantic memory conflicts with expected entity property
2. **Long-term staleness**: Alias unused for > 90 days but still in system
3. **Low confidence with high stakes**: About to use 0.65 confidence alias to make database change

```python
async def validate_entity_resolution(
    canonical_entity_id: str,
    validation_reason: str
) -> ValidationResult:
    """
    Re-check that canonical entity still matches domain database.
    """
    entity = await get_canonical_entity(canonical_entity_id)

    # Query domain database
    domain_record = await db.execute("""
        SELECT * FROM domain.{entity.entity_type}s
        WHERE {pk_column} = $1
    """, entity.external_ref[f"{entity.entity_type}_id"])

    if not domain_record:
        # Entity deleted from domain database!
        return ValidationResult(
            valid=False,
            reason="Entity no longer exists in domain database",
            action="mark_inactive"
        )

    # Check if properties significantly changed
    if domain_record.name != entity.canonical_name:
        # Name changed - update canonical entity
        return ValidationResult(
            valid=True,
            reason="Name changed in domain database",
            action="update_canonical_name",
            new_name=domain_record.name
        )

    return ValidationResult(valid=True, reason="Validated against domain database")
```

## Edge Cases and Error Handling

### Circular Coreference

**Problem**: "They ordered product X" (no prior entity mention)

**Solution**: Depth limit + disambiguation request
```python
def resolve_coreference(mention, context, depth=0):
    if depth > 5:  # Prevent infinite recursion
        return request_disambiguation("Unclear reference - which entity do you mean?")
    # ... resolution logic
```

### Entity Type Ambiguity

**Problem**: "Apple" → customer or product?

**Solution**: Use recent context + ontology
```python
context_entities = get_recent_entities(session_id, limit=5)
if any(e.entity_type in ["order", "invoice"] for e in context_entities):
    # Orders relate to customers, prefer customer interpretation
    prefer_types = ["customer"]
else:
    # No context, use most common type for this name
    prefer_types = get_most_common_type("Apple")
```

### Merged Entities (Phase 2)

**Deferred**: Handle domain DB entity merges when they occur. For Phase 1, if entity not found in domain DB, mark as inactive and request clarification.

## Performance Considerations

### Critical Query Patterns

1. **Exact alias lookup** (hottest path):
```sql
CREATE INDEX idx_aliases_lookup ON app.entity_aliases(alias_text, user_id, confidence);
-- Supports: WHERE alias_text = X AND (user_id = Y OR user_id IS NULL)
```

2. **Fuzzy text search**:
```sql
CREATE INDEX idx_aliases_trigram ON app.entity_aliases USING gin(alias_text gin_trgm_ops);
-- Supports: WHERE similarity(alias_text, X) > 0.7
```

3. **Recent entities for coreference**:
```sql
CREATE INDEX idx_episodic_recency ON app.episodic_memories(session_id, created_at DESC);
-- Supports: Recent entities in session for coreference resolution
```

### Expected Load

Resolution per message: 2-5 entity mentions average
- 80% resolved in Stage 1/2 (exact match) - 10ms per resolution
- 15% resolved in Stage 3 (fuzzy) - 50ms per resolution
- 5% require disambiguation - 100ms + user interaction

## Metrics and Monitoring (Phase 2)

**Deferred**: Track resolution quality metrics once system has operational data:
- Resolution success rate by stage
- Disambiguation frequency
- Confidence calibration (do 0.8 confidence resolutions work 80% of the time?)
- Most ambiguous entity types/names

---

## Summary: Entity Resolution Design

**Core Architecture**: Two-layer system (canonical entities + aliases) enabling flexible, context-aware entity resolution.

**Resolution Algorithm**: Five stages with escalating complexity:
1. **Exact match** (0.95 confidence) - "Acme Corporation" → direct alias lookup
2. **User-specific** (0.85 confidence) - "my customer" → user's learned aliases
3. **Fuzzy + semantic** (0.70 confidence) - "Acme" → fuzzy text + property matching
4. **Coreference** (0.60 confidence) - "they" → recent conversation entities
5. **Disambiguation** - Multiple candidates → ask user

**Key Principles**:
- **Passive computation**: Confidence decay computed on-demand
- **Lazy creation**: Entities discovered from domain DB as needed
- **User learning**: Aliases strengthen with repeated use
- **Epistemic humility**: Low confidence → disambiguation request

**Phase 1 Essential**:
- Two-layer architecture (canonical entities + aliases)
- Five-stage resolution algorithm
- Lazy entity discovery from domain DB
- Coreference resolution (recent context)

**Phase 2 Enhancements**:
- Confidence decay with validation triggers
- Resolution metrics and analytics
- Learned disambiguation patterns
- Entity merge handling

---

**Vision Alignment**:
- ✅ Epistemic humility: Confidence tracking, disambiguation when uncertain
- ✅ Context as constitutive: User-specific and context-dependent aliases
- ✅ Graceful evolution: JSONB properties emerge over time
- ✅ Business ontology awareness: Entity types from domain schema
- ✅ Dual truth: Canonical (correspondence) vs Alias (contextual)
