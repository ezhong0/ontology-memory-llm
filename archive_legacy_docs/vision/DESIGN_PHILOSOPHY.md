# Design Philosophy: Complexity Must Earn Its Keep

## The Core Principle

**Every piece of complexity must be justified against the vision document.**

This is not about simplification for its own sake. Simple systems can fail to achieve their purpose just as badly as over-engineered ones. The question is not "how simple can we make this?" but rather:

> For each piece of complexity: Does it serve a vision principle? Does it contribute enough to justify its existence?

## The Three Questions Framework

When evaluating any design element (table, field, index, relationship), ask:

1. **Which vision principle does this serve?**
   - If none, remove it
   - If "it might be useful later," defer it
   - If multiple principles, it's likely essential

2. **Does this contribute enough to justify its cost?**
   - Cost = schema complexity, query complexity, maintenance burden
   - Contribution = how much does it advance the vision?
   - Sometimes a small contribution justifies a small cost

3. **Is this the right phase for this complexity?**
   - Essential now = directly enables core functionality
   - Useful later = improves quality with real usage data
   - Needs data first = learning features that require observations

## The Normalization Decision Tree

### Use a Separate Table When:
- **Frequently queried independently**: "Show me all canonical entities"
- **Join target**: Other tables need foreign key relationships
- **Lifecycle independent**: Created/updated/deleted on different schedule
- **Fixed schema**: Structure is stable and well-understood

Examples: `canonical_entities`, `semantic_memories`, `chat_events`

### Inline with JSONB When:
- **Context-specific**: Meaning depends on parent record
- **Variable structure**: Schema evolves per use case
- **Query rarely alone**: Almost always accessed via parent
- **Small and bounded**: Won't create huge documents

Examples: `entity_aliases.metadata` (disambiguation context), `episodic_memories.entities` (coreference chains)

### The Anti-Pattern:
Creating a normalized table just because relational databases "should" be normalized. JSONB is powerful. Use it when it serves simplicity without sacrificing query ability.

## Computation Strategy: Passive vs Pre-Computed

### Passive Computation (Preferred):
```sql
-- Compute on-demand when needed
SELECT *,
       base_confidence * EXP(-decay_rate * age_in_days) AS current_confidence
FROM semantic_memories
```

**When to use**: Simple formulas, infrequent computation, or when precision timing matters more than read speed.

**Why**: Avoids background jobs, always accurate, simpler schema.

### Pre-Computed (When Justified):
```sql
-- Store if computation is expensive
CREATE TABLE memory_embeddings (
  memory_id BIGINT PRIMARY KEY,
  embedding vector(1536)  -- Expensive to compute
);
```

**When to use**: Expensive operations (embeddings), high-frequency access, or when index-based filtering is required.

**Why**: Some costs justify pre-computation.

## Phasing: The Right Complexity at the Right Time

### Phase 1: Essential Core
What must exist for the system to function at all?

- Tables that store inputs (`chat_events`)
- Tables that store outputs (`semantic_memories`, `episodic_memories`)
- Tables that enable core vision principles (`domain_ontology`, `canonical_entities`)
- Tables that complete the transformation cycle (`procedural_memories`, `memory_summaries`)

**Justification**: These directly implement the vision's memory transformation layers and ontology-awareness.

### Phase 2: Useful Enhancements
What improves quality with real usage?

- `state_transitions`: Analyze memory lifecycle to tune thresholds
- Validation triggers: Detect contradictions faster
- Retrieval optimization: Better scoring once we see real queries

**Justification**: These need operational data to tune. Build after Phase 1 works.

### Phase 3: Learning & Adaptation
What requires patterns from actual data?

- `meta_memories`: Need to observe what works before learning from it
- `extraction_patterns`: Need to see extraction failures before fixing them
- Adaptive scoring: Need retrieval logs before learning what works

**Justification**: Can't build learning systems without data to learn from.

## Case Studies from This Design

### Case 1: Procedural Memories
**Initial impulse**: Remove to simplify.

**Analysis**: Vision document explicitly describes Layer 5 transformation (Episodic → Semantic → Procedural). This is not optional complexity; it's in the vision.

**Decision**: Keep. Essential. System fails to achieve vision without it.

### Case 2: Disambiguation Preferences
**Initial design**: Separate table `disambiguation_preferences`
```sql
CREATE TABLE disambiguation_preferences (
  user_id TEXT,
  ambiguous_term TEXT,
  chosen_entity_id TEXT,
  context JSONB
);
```

**Analysis**:
- ❌ Never queried independently
- ❌ Context-specific (each preference only meaningful in its context)
- ❌ Variable structure (context varies widely)

**Decision**: Inline into `entity_aliases.metadata.disambiguation_context`. Simpler without losing capability.

### Case 3: Entity Mentions
**Initial design**: Separate table linking events to entities
```sql
CREATE TABLE entity_mentions (
  mention_id BIGSERIAL PRIMARY KEY,
  event_id BIGINT,
  canonical_entity_id TEXT,
  mention_text TEXT,
  mention_context TEXT
);
```

**Analysis**:
- ❓ Enables "find all mentions of entity X" queries
- ❌ But we can do this via episodic_memories.entities JSONB
- ❌ Adds schema complexity for rare query pattern
- ❌ Coreference information is episodic-memory-specific context

**Decision**: Inline into `episodic_memories.entities` as JSONB. If we later discover frequent "all mentions" queries, we can add GIN index on JSONB or materialized view.

### Case 4: Memory Conflicts
**Question**: Is this essential or nice-to-have?

**Analysis**:
- ✅ Vision principle: Epistemic humility
- ✅ Vision explicitly: "knows what it doesn't know with rigorous tracking of confidence and contradiction"
- ✅ Enables critical debugging and trust

**Decision**: Essential. Core to epistemic humility principle. When user asks "why do you believe X?", conflicts table provides the answer.

### Case 5: Redundant Confidence Fields
**Initial design**: `semantic_memories` had many confidence-related fields
```sql
contradiction_count INT,
validation_requested_at TIMESTAMPTZ,
decay_factor REAL,
accessed_count INT
```

**Analysis**:
- ❌ `contradiction_count`: Derivable from `memory_conflicts` table
- ❌ `validation_requested_at`: State management belongs in Phase 2's state_transitions
- ❌ `decay_factor`: Stored in system_config, applied via formula
- ❌ `accessed_count`: Useful for Phase 3 learning, but not now

**Decision**: Remove. Keep single `confidence` field with `confidence_factors` JSONB for explanation. Compute everything else on-demand or defer to later phase.

## Field-Level Philosophy

### Required Fields: The Minimum Viable Set
Every field must answer: "What breaks if this doesn't exist?"

Example from `semantic_memories`:
```sql
memory_id            -- Identity (breaks: can't reference)
user_id              -- Isolation (breaks: data leakage)
predicate            -- Meaning (breaks: can't understand relation)
predicate_type       -- Ontology (breaks: can't traverse semantically)
object_value         -- Meaning (breaks: incomplete triple)
confidence           -- Uncertainty (breaks: epistemic humility)
created_at           -- Time (breaks: can't decay, can't order)
```

Every other field removed unless it serves a specific vision principle.

### Optional Fields: The Clarity Set
Fields that aren't strictly required but significantly improve system quality.

Example:
```sql
importance REAL      -- Improves: retrieval prioritization (vision: relevance)
embedding vector     -- Enables: semantic search (vision: meaning-based retrieval)
status TEXT          -- Enables: lifecycle management (vision: forgetting)
```

### Removed Fields: The Bloat
Fields that seemed useful but don't serve vision:
```sql
accessed_count       -- Nice to have, but defer to Phase 3
tags TEXT[]          -- Generic, not ontology-aware (against vision)
```

## JSON vs Structured: The Pragmatic Balance

### When JSONB is the Right Choice
```sql
-- Variable structure per context
confidence_factors JSONB  -- Different semantic memories have different evidence

-- Context-specific data
metadata JSONB  -- Each alias has unique disambiguation context

-- Flexible evolution
properties JSONB  -- Entity properties vary by domain and discovery
```

### When Structured is the Right Choice
```sql
-- Frequently filtered/sorted
WHERE confidence > 0.7  -- Indexed, fast
WHERE created_at > now() - interval '30 days'

-- Foreign key relationships
REFERENCES canonical_entities(entity_id)

-- Fixed semantics
predicate TEXT NOT NULL
predicate_type TEXT NOT NULL
```

### The Anti-Pattern
```sql
-- ❌ Over-structured: Creates schema rigidity
CREATE TABLE entity_property (
  property_key TEXT,
  property_value TEXT,
  property_type TEXT
);

-- ✅ Right-structured: Allows discovery
properties JSONB  -- { "industry": "tech", "revenue": 1000000, ... }
```

## The Design Review Checklist

Before finalizing any table:

- [ ] **Vision Mapping**: Which vision principle(s) does this serve? (Write it down!)
- [ ] **Essential vs Useful**: Is this Phase 1 essential or Phase 2/3 useful?
- [ ] **Normalization**: Should this be separate or inline? (Use decision tree)
- [ ] **Field Audit**: Can any field be removed, derived, or deferred?
- [ ] **Query Patterns**: What queries does this support? Are they core or edge?
- [ ] **Cost-Benefit**: Does the contribution justify the complexity?

If you can't write a clear "Vision Alignment" statement, the table probably shouldn't exist yet.

## What This Philosophy Rejects

### ❌ "Best Practices" Without Context
Just because normalized schemas are a "best practice" doesn't mean every piece of data needs its own table. Context matters.

### ❌ "We Might Need It Later"
If you can't articulate the current need tied to the vision, defer it. You'll build it better when you have real requirements.

### ❌ "It's Just One More Field"
Death by a thousand cuts. Each field adds cognitive load. Each "just one more" adds up.

### ❌ "Simplification for Aesthetics"
Simple is not the goal. Aligned with vision is the goal. Sometimes that requires complexity.

## What This Philosophy Embraces

### ✅ Complexity That Serves the Vision
Procedural memories add complexity, but they're in the vision. Keep them.

### ✅ Strategic Use of JSONB
Flexible storage for variable contexts isn't a compromise—it's the right tool.

### ✅ Passive Computation
When a simple formula works, don't pre-compute. Simpler is better when cost is low.

### ✅ Phased Complexity
Build what you need now. Build learning features when you have data to learn from.

### ✅ Explicit Justification
Every design element should have a written justification tied to the vision. If you can't write it, reconsider.

## The North Star

When in doubt, return to the vision document's metaphor:

> The system should behave like **an experienced colleague who has worked with this company for years**.

Ask: Would that colleague need this capability to be helpful? If yes, build it. If no, defer it.

That experienced colleague:
- ✅ Remembers procedures (procedural_memories)
- ✅ Summarizes when details overload (memory_summaries)
- ✅ Knows when they're uncertain (memory_conflicts)
- ✅ Understands business relationships (domain_ontology)
- ❌ Doesn't track their own eye movements (accessed_count)
- ❌ Doesn't pre-compute every possible future thought (pre-computed scoring)

Build the system that colleague would need, not the system a perfectionist would imagine.

---

**Final Principle**: Complexity is not the enemy. Unjustified complexity is the enemy. Every piece of this system should earn its place by serving the vision.
