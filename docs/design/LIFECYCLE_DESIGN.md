# Memory Lifecycle & Transformation Pipeline Design

## Overview

This document details the **dynamic processes** that govern how memories are created, evolve, reinforce, decay, and consolidate over time. Each transformation is a decision point guided by clear criteria rooted in the vision's philosophical principles.

**Vision Principles Served**:
- **Memory Transformation**: Episodic → Semantic → Procedural (Layer 3 → 4 → 5 transformation)
- **Graceful Forgetting**: Decay + consolidation + active validation
- **Epistemic Humility**: Confidence tracking, knowing what we don't know
- **Explainability**: Complete provenance for every transformation

---

## Part 1: Memory States and State Machines

### Semantic Memory State Machine

Semantic memories represent learned facts that evolve. They require a lifecycle that supports **graceful forgetting** (vision principle).

```
                    ┌─────────────────────┐
                    │    CREATED (t=0)    │
                    │  confidence: 0.7    │
                    └──────────┬──────────┘
                               │
                               ↓
                    ┌─────────────────────┐
                    │      ACTIVE         │◄──── Reinforcement
                    │  Used in retrieval  │      increases confidence
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ↓              ↓              ↓
      ┌─────────────┐  ┌─────────────┐  ┌──────────────┐
      │   AGING     │  │ SUPERSEDED  │  │ INVALIDATED  │
      │  (old, no   │  │ (replaced)  │  │  (incorrect) │
      │   reinforce)│  │             │  │              │
      └──────┬──────┘  └──────────────┘  └──────────────┘
             │
             ↓
     ┌───────────────┐
     │ User validates│
     │  or corrects  │
     └───────┬───────┘
             │
      ┌──────┴──────┐
      ↓             ↓
  ┌────────┐  ┌───────────┐
  │ ACTIVE │  │INVALIDATED│
  │(reset) │  │(corrected)│
  └────────┘  └───────────┘
```

**State Definitions**:

1. **ACTIVE**: Current belief, confidence ≥ 0.3, recently validated or reinforced
   - Used in retrieval
   - Contributes to responses
   - Subject to passive decay (computed on-demand)

2. **AGING**: Still believed but needs validation
   - Triggers: `(now() - last_validated_at) > validation_threshold` AND `reinforcement_count < 2`
   - Still retrieved but flagged for validation
   - System proactively asks: "Is this still accurate?"
   - **Why essential**: Vision's "active validation" principle—system questions old information

3. **SUPERSEDED**: Replaced by newer information
   - Not used in retrieval (unless exploring history)
   - Kept for explainability ("I previously thought X, but now Y")
   - Links to superseding memory via `superseded_by_memory_id`
   - **Why essential**: Vision's "living memory vs historical record" distinction

4. **INVALIDATED**: Marked as incorrect
   - User explicitly corrected OR conflict with authoritative DB
   - Not used in retrieval
   - Kept for learning (improve extraction patterns in Phase 3)
   - **Why essential**: Vision's "epistemic humility" + future learning capability

**Transition Criteria**:

| From State | To State | Trigger | Action |
|------------|----------|---------|--------|
| ACTIVE | AGING | `(now() - last_validated_at) > validation_threshold` AND `reinforcement_count < 2` | Set status=aging, include validation prompt in next retrieval |
| ACTIVE | SUPERSEDED | User states contradicting fact OR new memory replaces | Set status=superseded, link to new memory |
| ACTIVE | INVALIDATED | User correction "That's wrong" OR DB conflict detected | Set status=invalidated, log reason |
| AGING | ACTIVE | User confirms accuracy | Reset last_validated_at, apply confidence boost |
| AGING | INVALIDATED | User corrects or denies | Set status=invalidated, create corrected memory |

**Implementation: Passive State Transitions**

```python
def get_semantic_memory_state(memory):
    """
    Compute state on-demand (no background jobs needed)
    """
    # Stored state takes precedence for superseded/invalidated
    if memory.status in ('superseded', 'invalidated'):
        return memory.status

    # Check if should transition to AGING
    days_since_validation = (now() - (memory.last_validated_at or memory.created_at)).days
    validation_threshold = get_config('decay')['validation_threshold_days']  # 90

    if (days_since_validation > validation_threshold and
        memory.reinforcement_count < 2):
        # Don't UPDATE database - just flag for validation prompt
        return 'aging'

    return 'active'
```

**Why This Approach**:
- ✅ No background jobs to transition states
- ✅ State computed when needed (retrieval time)
- ✅ Database only stores explicit transitions (superseded/invalidated)
- ✅ Simple to implement, aligned with vision

### Episodic Memory Lifecycle

Simpler lifecycle - episodic memories are historical events.

```
    ┌─────────────┐
    │   CREATED   │
    └──────┬──────┘
           │
           ↓
    ┌─────────────┐
    │   ACTIVE    │
    │ (retrievable)│
    └──────┬──────┘
           │
           ↓ (after consolidation)
    ┌─────────────┐
    │CONSOLIDATED │
    │(subsumed by │
    │  summary)   │
    └─────────────┘
```

**Key Principle**: Episodic memories don't become invalid (events happened), but they can be subsumed by summaries for efficiency (vision's "graceful forgetting").

**Retrieval Priority**: Recent episodic > consolidated > distant episodic

---

## Part 2: Transformation Pipeline

### Stage 1: Raw Event → Episodic Memory

**Trigger**: User sends message

**Process**:
```
1. Store raw event (immutable) in chat_events
   ↓
2. LLM extraction: intent, entities, event_type
   ↓
3. Entity resolution (text → canonical entity IDs)
   ↓
4. Domain DB queries (if entities identified)
   ↓
5. Create episodic memory:
   - Distilled summary of interaction
   - Resolved entities with coreference
   - Domain facts referenced (for provenance)
   - Event type (question|statement|command|correction|confirmation)
   ↓
6. Compute importance score
   ↓
7. Async: Generate embedding
```

**Decision: When to create episodic memory?**

Always create for user messages. Optionally create for assistant responses if they contain commitments or decisions.

**Importance Scoring** (pragmatic heuristic):

```python
def compute_episodic_importance(event):
    """
    Importance determines retrieval priority and consolidation likelihood
    Vision alignment: "Learn what matters" - not all events are equal
    """
    base_importance = {
        'question': 0.4,       # questions provide context
        'statement': 0.6,      # statements might contain facts
        'command': 0.7,        # commands are commitments
        'correction': 0.9,     # corrections are high signal
        'confirmation': 0.8    # confirmations validate existing memories
    }[event.event_type]

    # Boost if involves entities (grounded in domain)
    entity_boost = min(0.2, len(event.entities) * 0.05)

    # Boost if queried domain DB (concrete grounding)
    db_boost = 0.1 if event.domain_facts_referenced else 0.0

    importance = base_importance + entity_boost + db_boost
    return max(0.0, min(1.0, importance))
```

### Stage 2: Episodic → Semantic Memory

**Trigger**: Episodic memory contains extractable fact

**Vision Alignment**: Layer 4 transformation - distilling events into abstracted facts that persist across sessions.

**Decision: When to extract semantic memory?**

```python
def should_extract_semantic(episodic):
    """
    Determine if episodic memory warrants semantic extraction
    """
    # 1. Explicit memory statements ("Remember that...", "Note that...")
    if has_memory_trigger(episodic.content):
        return True, {'reason': 'explicit', 'base_confidence': 0.7}

    # 2. Preference/policy statements ("They prefer X", "Always do Y")
    if matches_preference_pattern(episodic.content):
        return True, {'reason': 'preference', 'base_confidence': 0.6}

    # 3. Corrections (high signal - user is actively teaching)
    if episodic.event_type == 'correction':
        return True, {'reason': 'correction', 'base_confidence': 0.85}

    # 4. Confirmations → Reinforcement flow (don't create new memory)
    if episodic.event_type == 'confirmation':
        return False, {'reason': 'trigger_reinforcement'}

    # 5. Inferred patterns (conservative - Phase 2 enhancement)
    # For now, only extract explicit statements

    return False, {'reason': 'no_extractable_fact'}
```

**Extraction Process**:
```
1. Parse episodic content into subject-predicate-object triple
   ↓
2. Resolve subject to canonical entity ID
   ↓
3. Check for existing semantic memory (subject + predicate)
   ↓
4a. IF EXISTS AND values compatible → Reinforcement (Stage 3)
4b. IF EXISTS AND values conflict → Conflict resolution (Stage 4)
4c. IF NEW → Create semantic memory
   ↓
5. Compute initial confidence (based on source)
   ↓
6. Link to source episodic memory (provenance)
   ↓
7. Async: Generate embedding
```

**Example Extraction**:

```
Episodic: "User stated that Gai Media prefers Friday deliveries"

Extracted semantic memory:
{
  "subject_entity_id": "customer:gai-media-uuid",
  "predicate": "delivery_day_preference",
  "predicate_type": "preference",
  "object_value": {"type": "string", "value": "Friday"},
  "confidence": 0.7,  // explicit statement
  "source_type": "episodic",
  "source_memory_id": 12345,
  "reinforcement_count": 1
}
```

### Stage 3: Reinforcement vs New Memory

**Critical Decision Point**: When extracting a fact that already exists

**Vision Alignment**: "Reinforcement strengthens stable patterns" - repeatedly confirmed facts gain confidence.

**Matching Logic**:

```python
def find_matching_semantic_memory(subject, predicate, object_value):
    """
    Find existing memory that matches this fact
    """
    # Query active memories for subject + predicate
    candidates = query("""
        SELECT * FROM app.semantic_memories
        WHERE subject_entity_id = ? AND predicate = ?
          AND status IN ('active', 'aging')
        ORDER BY confidence DESC
    """, subject, predicate)

    if not candidates:
        return None, 'no_match'

    # Check object value compatibility
    for candidate in candidates:
        if values_compatible(candidate.object_value, object_value):
            return candidate, 'reinforcement'

    # Same predicate, different value = conflict
    return candidates[0], 'conflict'

def values_compatible(existing, new):
    """
    Determine if values represent same fact
    Pragmatic approach: exact match or semantic equivalence
    """
    # Exact match
    if existing == new:
        return True

    # Semantic equivalence (e.g., "Friday" == "Fridays", "NET30" == "NET 30")
    if semantic_equivalent(existing.get('value'), new.get('value')):
        return True

    return False
```

**Reinforcement Flow**:

```
Matching memory found with compatible value
    ↓
1. Increment reinforcement_count
    ↓
2. Update confidence (diminishing returns):
   new_confidence = min(0.95, old_confidence + reinforcement_boost)
    ↓
3. Reset last_validated_at = now() (implicit validation)
    ↓
4. If status was 'aging', transition to 'active'
    ↓
5. Update confidence_factors (for explainability)
```

**Reinforcement Boost Formula** (diminishing returns):

```python
def compute_reinforcement_boost(reinforcement_count):
    """
    Diminishing returns: each reinforcement adds less confidence
    Vision: Asymptotic approach to 0.95 (never 100% certain)
    """
    if reinforcement_count == 1:
        return 0.15  # First reinforcement: significant boost
    elif reinforcement_count == 2:
        return 0.10  # Second: still meaningful
    elif reinforcement_count == 3:
        return 0.05  # Third: smaller boost
    else:
        return 0.02  # Further: minimal boost
```

### Stage 4: Conflict Resolution

**Vision Alignment**: "Make conflicts explicit" (epistemic humility) - don't silently choose, show both sources.

**Conflict Types**:

1. **Memory vs Memory**: Same subject+predicate, different object values
2. **Memory vs DB**: Semantic memory contradicts authoritative database
3. **User Correction**: User explicitly states "That's wrong"

**Resolution Strategy** (pragmatic hierarchy):

```python
def resolve_conflict(existing_memory, new_memory, conflict_type):
    """
    Vision: "Truth hierarchy" - DB > Recent explicit > Highly reinforced
    """
    # 1. DB is authoritative (always wins)
    if conflict_type == 'memory_vs_db':
        return {
            'strategy': 'trust_db',
            'action': 'supersede',
            'winner': new_memory,  # new memory has DB value
            'loser': existing_memory
        }

    # 2. User explicit correction (high confidence)
    if new_memory.source_type == 'correction':
        return {
            'strategy': 'trust_correction',
            'action': 'supersede',
            'winner': new_memory,
            'loser': existing_memory
        }

    # 3. Confidence-based (significant difference)
    if abs(existing_memory.confidence - new_memory.confidence) > 0.3:
        winner = existing_memory if existing_memory.confidence > new_memory.confidence else new_memory
        loser = new_memory if winner == existing_memory else existing_memory
        return {
            'strategy': 'trust_higher_confidence',
            'action': 'supersede',
            'winner': winner,
            'loser': loser
        }

    # 4. Recency wins (recent explicit overrides old)
    if (now() - new_memory.created_at).days < 7:
        return {
            'strategy': 'trust_recent',
            'action': 'supersede',
            'winner': new_memory,
            'loser': existing_memory
        }

    # 5. Ambiguous - log conflict, present both to user
    return {
        'strategy': 'ask_user',
        'action': 'log_conflict',
        'present_both': True
    }
```

**Resolution Actions**:

```python
def apply_resolution(resolution, conflict_id):
    """Apply conflict resolution and log for explainability"""
    with transaction():
        # Log in memory_conflicts table
        insert_conflict(conflict_id, resolution)

        if resolution['action'] == 'supersede':
            # Mark loser as superseded
            update("""
                UPDATE app.semantic_memories
                SET status = 'superseded',
                    superseded_by_memory_id = ?
                WHERE memory_id = ?
            """, resolution['winner'].memory_id, resolution['loser'].memory_id)

        elif resolution['action'] == 'log_conflict':
            # Don't auto-resolve - present to user in next response
            # "I have conflicting information: memory says X (conf: 0.8), but recent note says Y (conf: 0.7)"
            pass
```

### Stage 5: Correction Flow

**Trigger**: User explicitly corrects a fact

Example: "Actually, they prefer Thursday, not Friday"

**Vision Alignment**: User corrections are high-signal teaching moments (confidence 0.85).

**Correction Detection** (pattern matching):

```python
def detect_correction(message):
    """Identify correction intent"""
    correction_patterns = [
        "actually",
        "no,",
        "that's wrong",
        "I meant",
        "correction:"
    ]
    return matches_any_pattern(message, correction_patterns)
```

**Correction Process**:

```
1. LLM extracts: old value + corrected value + subject/predicate
   ↓
2. Find existing memory being corrected (subject + predicate)
   ↓
3. Mark old memory as 'superseded'
   ↓
4. Create new semantic memory:
   - confidence: 0.85 (high - explicit correction)
   - source_type: 'correction'
   - supersedes_memory_id: <old_memory_id>
   ↓
5. Log in memory_conflicts (for future learning)
```

**Example**:

```
Before:
{
  "memory_id": 100,
  "predicate": "delivery_day_preference",
  "object_value": {"value": "Friday"},
  "confidence": 0.8,
  "status": "active"
}

User: "Actually, they prefer Thursday, not Friday"

After:
Old memory 100: status → 'superseded', superseded_by_memory_id → 101
New memory 101: {
  "predicate": "delivery_day_preference",
  "object_value": {"value": "Thursday"},
  "confidence": 0.85,
  "source_type": "correction",
  "supersedes_memory_id": 100
}
```

### Stage 6: Decay Process

**Vision Alignment**: "Graceful forgetting" - unreinforced memories fade over time.

**Design Philosophy**: **Passive decay** - compute on-demand, don't store or pre-compute.

**Implementation**:

```python
def compute_effective_confidence(memory):
    """
    Apply exponential decay to stored confidence
    No database update - computed at retrieval time
    """
    days_since_validation = (now() - (memory.last_validated_at or memory.created_at)).days
    decay_rate = get_config('decay')['default_rate_per_day']  # 0.01

    # Exponential decay
    decay_multiplier = exp(-days_since_validation * decay_rate)
    effective_conf = memory.confidence * decay_multiplier

    return effective_conf
```

**Triggering Validation** (transition to AGING state):

```python
def check_if_aging(memory):
    """
    Determine if memory should transition to AGING state
    Vision: "Active validation" - proactively verify old memories
    """
    days_since_validation = (now() - (memory.last_validated_at or memory.created_at)).days
    validation_threshold = get_config('decay')['validation_threshold_days']  # 90

    # Transition to AGING if:
    # - Old (> 90 days since validation)
    # - Low reinforcement (< 3 confirmations)
    if days_since_validation > validation_threshold and memory.reinforcement_count < 3:
        return True

    return False
```

**Validation Process**:

```
Aging memory retrieved
    ↓
LLM includes validation prompt in response:
"I have a note from [date] that they prefer Friday—is that still accurate?"
    ↓
User response:
├─→ "Yes" → UPDATE last_validated_at=now(), status='active'
└─→ "No, Thursday" → Correction flow
```

### Stage 7: Consolidation (Episodic + Semantic → Summary)

**Vision Alignment**: Layer 6 transformation - "Forgetting is essential to intelligence" (compression).

**Trigger Criteria** (pragmatic):

```python
def should_consolidate(entity_id, user_id):
    """Determine if consolidation is needed"""
    session_count = count_sessions_mentioning(entity_id, user_id)
    episodic_count = count_episodic_memories(entity_id, user_id)

    # Trigger: 3+ sessions or 20+ episodic memories
    return session_count >= 3 or episodic_count >= 20
```

**Consolidation Process**:

```
1. Gather source memories (entity-scoped)
   - Episodic memories mentioning entity
   - Semantic memories for entity
   - Previous summary (if exists)
   ↓
2. LLM synthesis
   - Input: Episodic summaries + Semantic facts
   - Output: Natural language summary + Structured key_facts
   ↓
3. Create memory_summaries record
   - Store text + key_facts + source_data
   - If supersedes previous, link via supersedes_summary_id
   ↓
4. Boost confidence of confirmed semantic memories (+0.05)
   ↓
5. Async: Generate embedding
```

**Example Summary Output**:

```json
{
  "summary_text": "Gai Media (Entertainment) profile: Prefers Friday deliveries (confirmed 3x). Typically checks order status weekly. Current: SO-1001 in fulfillment.",
  "key_facts": {
    "delivery_day_preference": {"value": "Friday", "confidence": 0.95},
    "interaction_cadence": {"value": "weekly", "confidence": 0.7}
  },
  "scope_type": "entity",
  "scope_identifier": "customer:gai-media-uuid"
}
```

---

## Part 3: Procedural Memory Emergence

**Vision Alignment**: Layer 5 transformation - "Procedural memory captures patterns" emerges from episodic observation.

**Deferred to Phase 2/3**: Pattern detection requires significant episodic data to identify repeated sequences.

**Essential Concept** (for future implementation):

```python
def detect_procedural_pattern(user_id):
    """
    Analyze episodic memories to find repeated query patterns
    Example: User asks about "delivery" → often asks about "invoices" next
    """
    episodes = query_recent_episodic_memories(user_id, lookback_days=60)

    # Find sequences: topic A followed by topic B (3+ occurrences)
    sequences = identify_common_sequences(episodes, min_occurrences=3)

    for seq in sequences:
        create_procedural_memory({
            'trigger_pattern': f"When user asks about {seq.topic_a}",
            'trigger_features': {'topics': [seq.topic_a]},
            'action_heuristic': f"Also retrieve {seq.topic_b}",
            'action_structure': {'augment_retrieval': seq.topic_b},
            'observed_count': seq.occurrences,
            'confidence': min(0.9, seq.occurrences / 10)
        })
```

**Why Deferred**: Requires 50+ episodic memories per user to detect meaningful patterns. Build after core transformations work.

---

## Part 4: Meta-Memory Learning

**Vision Alignment**: "Learn decay rates per fact type" based on observed change patterns.

**Deferred to Phase 3**: Requires observing corrections across different predicate types (needs 1000+ semantic memories with corrections).

**Essential Concept** (for future):

```python
def learn_decay_rates_per_predicate_type():
    """
    Analyze how long different fact types stay valid
    Example:
    - contact_person: changes frequently (decay_rate: 0.03/day)
    - payment_terms: rarely changes (decay_rate: 0.005/day)
    """
    observations = analyze_corrections_by_predicate_type()

    for pred_type, stats in observations.items():
        avg_change_frequency = mean(stats['days_until_correction'])
        decay_rate = 0.916 / avg_change_frequency  # Target: 0.4 confidence at expected change time
        validation_threshold = avg_change_frequency * 0.5

        store_meta_memory(pred_type, decay_rate, validation_threshold)
```

**Why Deferred**: Can't tune without data. Start with default decay rate (0.01/day), add per-type rates in Phase 3.

---

## Part 5: Lifecycle Event Timeline

**Example Timeline**: User discusses customer "Gai Media" over 3 sessions

### Session 1 (Day 0)

**T+0min**: User: "What's the status of Gai Media's order?"

```
[Store Event]
└─> chat_events: event_id=1, content="What's the status...", role=user

[Entity Resolution]
└─> Extract "Gai Media" → fuzzy match → customer:xxx
└─> Create/update canonical_entities: customer:xxx
└─> Create alias: "Gai Media" → customer:xxx

[Domain Query]
└─> Query domain.sales_orders WHERE customer_id = xxx
└─> Found: SO-1001, status=in_fulfillment

[Create Episodic]
└─> episodic_memories:
    memory_id=1,
    summary="User asked about Gai Media order status",
    event_type=question,
    entities_involved=[customer:xxx, order:SO-1001],
    domain_facts_referenced={queries: [...]}
    importance=0.5
```

**T+2min**: User: "Remember, they prefer Friday deliveries"

```
[Store Event]
└─> chat_events: event_id=2, content="Remember, they prefer..."

[Create Episodic]
└─> episodic_memories: memory_id=2, event_type=statement

[Semantic Extraction]
└─> Detect: Explicit memory trigger ("Remember")
└─> Parse: subject=customer:xxx, predicate=delivery_day_preference, value="Friday"
└─> Check existing: None found
└─> Create semantic_memories:
    memory_id=1,
    subject_entity_id=customer:xxx,
    predicate=delivery_day_preference,
    object_value={type: "string", value: "Friday"},
    confidence=0.7 (explicit statement),
    reinforcement_count=1,
    status=active,
    source_type=episodic,
    source_memory_id=2
```

### Session 2 (Day 7)

**T+7days**: User: "Schedule delivery for Gai Media next week"

```
[Store Event + Episodic]
└─> chat_events: event_id=10
└─> episodic_memories: memory_id=10, event_type=command

[Retrieval]
└─> Retrieve semantic memories for customer:xxx
└─> Found: memory_id=1 (Friday preference), confidence=0.7, age=7days
└─> Effective confidence: 0.7 * exp(-7 * 0.01) ≈ 0.65
└─> Include in context: "Gai Media prefers Friday deliveries (confidence: medium)"

[Domain Query]
└─> Query orders, work orders, invoices

[Assistant Response]
└─> "I can schedule delivery for Gai Media. They prefer Friday deliveries. Next Friday is [date]..."

[Implicit Reinforcement]
└─> Friday preference was retrieved and used → access_count++
└─> Not explicit confirmation, so no reinforcement yet
```

**T+7days+5min**: User: "Yes, Friday works"

```
[Store Event + Episodic]
└─> event_type=confirmation

[Reinforcement]
└─> Detect: Confirmation of Friday preference
└─> Find memory: memory_id=1
└─> Update:
    reinforcement_count: 1 → 2
    confidence: 0.7 → 0.85 (boost: 0.15)
    last_validated_at: now()
└─> Log state transition: (active → active, reason=reinforced)
```

### Session 3 (Day 60)

**T+60days**: User: "What's Gai Media's delivery preference?"

```
[Retrieval]
└─> Retrieve semantic memory_id=1
└─> Age: 60 days since creation, 53 days since last validation
└─> Effective confidence: 0.85 * exp(-53 * 0.01) ≈ 0.50 (decayed significantly)
└─> Check: should_validate_memory? → No (reinforcement_count=2, still above threshold)
└─> Include in context

[Assistant Response]
└─> "Based on our records, Gai Media prefers Friday deliveries (confirmed [date])."
```

### Background Process (Day 70)

**Consolidation Trigger**: 3 sessions discussing Gai Media

```
[Consolidation]
└─> Identify scope: entity=customer:xxx
└─> Gather memories:
    - Episodic: memory_ids=[1, 2, 10, ...]
    - Semantic: memory_ids=[1]
└─> LLM synthesis:
    summary="Gai Media (Entertainment) profile based on 3 sessions (Day 0-60):
            Preferences: Friday deliveries (confirmed 2x, high confidence).
            Patterns: User checks order status regularly.
            Recent: Order SO-1001 in fulfillment."
    key_facts={
      "preferences": {
        "delivery_day": {"value": "Friday", "confidence": 0.9}
      }
    }
└─> Create memory_summaries: summary_id=1
└─> Boost semantic memory confidence: 0.85 → 0.90 (consolidation validation)
```

### Session 4 (Day 150) - Aging

**T+150days**: User: "Schedule delivery for Gai Media"

```
[Retrieval]
└─> Retrieve semantic memory_id=1
└─> Age: 150 days, last_validated: Day 7 (143 days ago)
└─> Check: should_validate_memory? → YES (143 days > 90 day threshold)
└─> Mark for validation

[Update Status]
└─> memory_id=1: status=active → aging
└─> Log transition: reason=age_threshold_exceeded

[Assistant Response]
└─> "I can schedule delivery for Gai Media. I have a note from [date] that they prefer Friday deliveries - is that still accurate?"

[User Response: "Yes, that's correct"]
└─> Validation confirmation
└─> Update memory_id=1:
    status: aging → active
    last_validated_at: now()
    confidence: 0.90 → 0.92 (validation boost)
    reinforcement_count: 2 → 3
```

### Session 5 (Day 155) - Correction

**T+155days**: User: "Actually, they switched to Thursday deliveries last month"

```
[Correction Detection]
└─> Detect: "Actually" = correction pattern
└─> Extract: old_value="Friday", new_value="Thursday"
└─> Find: memory_id=1 (Friday preference)

[Correction Flow]
└─> Supersede old memory:
    memory_id=1: status=active → superseded
    superseded_by_memory_id=2
└─> Create new memory:
    memory_id=2,
    predicate=delivery_day_preference,
    object_value={value: "Thursday"},
    confidence=0.85 (explicit correction),
    source_type=correction,
    supersedes_memory_id=1
└─> Log transitions

[Extraction Pattern Learning]
└─> Analyze: What led to outdated memory?
└─> Note: Memory was validated Day 150 but had already changed
└─> Learning: Validation doesn't catch changes that happened after last interaction
```

---

This completes the memory lifecycle and transformation pipeline design. Every transformation has clear criteria and explicit decision points.
