# Conflict Resolution: Epistemic Humility in Practice

> How the system handles disagreements between memory and reality

---

## TL;DR

When memory and database disagree:
1. **Trust Database** (source of truth)
2. **Expose Conflict** (don't hide it)
3. **Mark Memory for Decay** (self-correction)
4. **Inform User** (transparency)

**Key Principle**: Never silently prefer one source over another. Transparency builds trust.

---

## The Problem

### Scenario

```
Monday: User says "Gai Media's order status is fulfilled"
        → System stores: (Gai, status, fulfilled, confidence: 0.85)

Tuesday: Database updated to "shipped" (external system)

Wednesday: User asks "What's Gai's status?"
          → Memory says: "fulfilled"
          → Database says: "shipped"
          → What should system do?
```

### Naive Approaches (All Wrong)

#### ❌ Option 1: Silently trust memory
```python
return memory.object_value  # "fulfilled"
```
**Problem**: User gets wrong information

#### ❌ Option 2: Silently trust database
```python
return db_result  # "shipped"
```
**Problem**: User doesn't know memory is outdated

#### ❌ Option 3: Ignore conflict
```python
if memory exists:
    return memory.object_value
else:
    return db_result
```
**Problem**: Memory never self-corrects

---

## Our Approach: Dual Truth + Transparency

```python
# 1. Detect conflict
if memory.object_value != db_result:
    conflict = MemoryConflict(
        type="memory_vs_db",
        existing_value=memory.object_value,  # "fulfilled"
        new_value=db_result,                 # "shipped"
        resolution="trust_db"
    )

    # 2. Mark memory for decay
    memory.mark_as_conflicted()
    memory.apply_decay()  # Reduce confidence

    # 3. Inform user
    return {
        "response": f"Status is {db_result} (previously {memory.object_value})",
        "conflicts_detected": [conflict]
    }
```

**Benefits**:
- ✅ User gets correct answer (DB)
- ✅ User knows memory was outdated
- ✅ Memory self-corrects over time
- ✅ Transparency (epistemic humility)

---

## Types of Conflicts

### 1. Memory vs Database

**When**: Database has updated since memory was created

```
Memory: (Gai, status, in_fulfillment, confidence: 0.85)
DB:     (Gai, status, shipped)

Conflict Type: memory_vs_db
Resolution: trust_db
```

**Detection**:
```python
db_status = await domain_db.query_status(entity_id)
memory_status = await memory_repo.find_semantic(
    subject=entity_id,
    predicate="status"
)

if db_status != memory_status.object_value:
    # Conflict detected
    conflicts.append(MemoryConflict(...))
```

**Resolution Strategy**: Always trust database (correspondence truth)

---

### 2. Memory vs Memory (Value Mismatch)

**When**: Two memories contradict each other

```
Memory A: (Gai, delivery_pref, Friday, confidence: 0.85, created: Oct 1)
Memory B: (Gai, delivery_pref, Monday, confidence: 0.80, created: Oct 10)

Conflict Type: value_mismatch
Resolution: keep_newest
```

**Detection**:
```python
existing_memory = await memory_repo.find_semantic(
    subject=entity_id,
    predicate="delivery_pref"
)

new_memory = SemanticMemory(
    subject=entity_id,
    predicate="delivery_pref",
    object_value="Monday"
)

if existing_memory.object_value != new_memory.object_value:
    # Conflict detected
    resolution = determine_resolution(existing_memory, new_memory)
```

**Resolution Strategy**: Multiple rules (see below)

---

### 3. Temporal Conflict

**When**: Values changed over time (not conflicting, just outdated)

```
Memory: (Gai, delivery_pref, Friday, created: 60 days ago)
User:   "Gai now prefers Monday"

Conflict Type: temporal
Resolution: supersede_old
```

**Detection**:
```python
age_days = (now - memory.created_at).days

if age_days > CONFLICT_TEMPORAL_THRESHOLD_DAYS:
    # Old memory, not necessarily conflict
    memory.status = "superseded"
```

**Resolution Strategy**: Mark old memory as superseded

---

## Resolution Strategies

### Strategy 1: Trust Database (memory_vs_db)

```python
def resolve_memory_vs_db(memory, db_value):
    # Database = authoritative (source of truth)
    memory.mark_as_conflicted()
    memory.confidence *= 0.5  # Decay confidence
    memory.status = "conflicted"

    return ConflictResolution(
        chosen_value=db_value,
        rationale="Database is source of truth",
        action="decay_memory"
    )
```

**When to use**: Any memory vs database conflict

---

### Strategy 2: Keep Newest (value_mismatch)

```python
def resolve_value_mismatch(memory_a, memory_b):
    # Prefer more recent information
    if memory_b.created_at > memory_a.created_at:
        memory_a.status = "superseded"
        return ConflictResolution(
            chosen_value=memory_b.object_value,
            rationale="More recent information",
            action="supersede_old"
        )
```

**When to use**: Two memories with different values, clear time difference

---

### Strategy 3: Keep Highest Confidence

```python
def resolve_by_confidence(memory_a, memory_b):
    confidence_gap = abs(memory_a.confidence - memory_b.confidence)

    if confidence_gap > CONFLICT_CONFIDENCE_THRESHOLD:  # 0.2
        winner = max(memory_a, memory_b, key=lambda m: m.confidence)
        loser = min(memory_a, memory_b, key=lambda m: m.confidence)

        loser.status = "conflicted"
        loser.confidence *= 0.8  # Decay

        return ConflictResolution(
            chosen_value=winner.object_value,
            rationale=f"Higher confidence ({winner.confidence:.2f} vs {loser.confidence:.2f})",
            action="decay_lower"
        )
```

**When to use**: Confidence gap > 0.2, no clear temporal order

---

### Strategy 4: Keep Most Reinforced

```python
def resolve_by_reinforcement(memory_a, memory_b):
    reinforcement_gap = abs(
        memory_a.reinforcement_count - memory_b.reinforcement_count
    )

    if reinforcement_gap >= CONFLICT_REINFORCEMENT_THRESHOLD:  # 3
        winner = max(memory_a, memory_b, key=lambda m: m.reinforcement_count)
        loser = min(memory_a, memory_b, key=lambda m: m.reinforcement_count)

        loser.status = "conflicted"

        return ConflictResolution(
            chosen_value=winner.object_value,
            rationale=f"More reinforced ({winner.reinforcement_count} vs {loser.reinforcement_count})",
            action="decay_lower"
        )
```

**When to use**: One memory validated multiple times

---

### Strategy 5: Ask User (ambiguous)

```python
def resolve_ambiguous(memory_a, memory_b):
    # Cannot determine automatically
    return ConflictResolution(
        chosen_value=None,
        rationale="Ambiguous conflict - need user input",
        action="ask_user",
        prompt=f"We have conflicting information: '{memory_a.object_value}' vs '{memory_b.object_value}'. Which is correct?"
    )
```

**When to use**: Similar confidence, similar reinforcement, similar age

---

## Decision Tree

```
Conflict Detected
  ↓
Is it memory_vs_db?
  ├─ Yes → Trust DB (Strategy 1)
  └─ No → Continue
      ↓
Is temporal gap > 30 days?
  ├─ Yes → Keep Newest (Strategy 2)
  └─ No → Continue
      ↓
Is confidence gap > 0.2?
  ├─ Yes → Keep Highest Confidence (Strategy 3)
  └─ No → Continue
      ↓
Is reinforcement gap ≥ 3?
  ├─ Yes → Keep Most Reinforced (Strategy 4)
  └─ No → Ask User (Strategy 5)
```

---

## Examples

### Example 1: Memory vs Database

```python
# Setup
memory = SemanticMemory(
    subject="sales_order_so_1001",
    predicate="status",
    object_value="in_fulfillment",
    confidence=0.85,
    created_at=datetime(2024, 10, 1)
)

db_status = domain_db.query("SELECT status FROM sales_orders WHERE id = 'so_1001'")
# → "shipped"

# Detection
if memory.object_value != db_status:
    conflict = detect_conflict(memory, db_status)

# Resolution
resolution = resolve_memory_vs_db(memory, db_status)

# Result
assert resolution.chosen_value == "shipped"
assert resolution.action == "decay_memory"
assert memory.status == "conflicted"
assert memory.confidence == 0.425  # 0.85 × 0.5

# Response to user
response = f"Status is {db_status} (previously {memory.object_value})"
# "Status is shipped (previously in_fulfillment)"
```

---

### Example 2: Conflicting Preferences

```python
# Setup
memory_1 = SemanticMemory(
    subject="customer_gai_123",
    predicate="delivery_pref",
    object_value="Thursday",
    confidence=0.75,
    reinforcement_count=1,
    created_at=datetime(2024, 10, 1)
)

memory_2 = SemanticMemory(
    subject="customer_gai_123",
    predicate="delivery_pref",
    object_value="Friday",
    confidence=0.85,
    reinforcement_count=2,
    created_at=datetime(2024, 10, 10)
)

# Detection
conflict = detect_value_mismatch(memory_1, memory_2)

# Resolution (newest + higher confidence + more reinforced)
resolution = resolve_value_mismatch(memory_1, memory_2)

# Result
assert resolution.chosen_value == "Friday"
assert resolution.action == "supersede_old"
assert memory_1.status == "superseded"

# Response to user
response = "Gai Media prefers Friday deliveries (recently updated from Thursday)"
```

---

### Example 3: Ambiguous Conflict

```python
# Setup: Similar confidence, similar reinforcement, similar age
memory_1 = SemanticMemory(
    predicate="delivery_pref",
    object_value="Thursday",
    confidence=0.80,
    reinforcement_count=2,
    created_at=datetime(2024, 10, 5)
)

memory_2 = SemanticMemory(
    predicate="delivery_pref",
    object_value="Friday",
    confidence=0.82,  # Only 0.02 difference
    reinforcement_count=2,  # Same reinforcement
    created_at=datetime(2024, 10, 8)  # Only 3 days apart
)

# Detection
conflict = detect_value_mismatch(memory_1, memory_2)

# Resolution
resolution = resolve_ambiguous(memory_1, memory_2)

# Result
assert resolution.action == "ask_user"

# Response to user
response = {
    "response": "I have conflicting information about delivery preference. Which is correct?",
    "disambiguation_required": True,
    "options": ["Thursday", "Friday"],
    "context": {
        "thursday_confidence": 0.80,
        "friday_confidence": 0.82,
        "note": "Both recent, similar confidence"
    }
}
```

---

## User Experience

### Transparent Conflict Reporting

```json
{
  "response": "Status is shipped (previously recorded as in_fulfillment)",
  "conflicts_detected": [
    {
      "conflict_type": "memory_vs_db",
      "subject": "sales_order_so_1001",
      "predicate": "status",
      "existing_value": "in_fulfillment",
      "new_value": "shipped",
      "existing_confidence": 0.85,
      "new_confidence": 1.0,
      "resolution_strategy": "trust_db",
      "explanation": "Database is the authoritative source of truth. Memory has been marked for decay."
    }
  ]
}
```

**Benefits**:
- ✅ User knows there was a conflict
- ✅ User knows which value is used
- ✅ User understands why
- ✅ Builds trust through transparency

---

## Configuration

### Tunable Parameters

```python
# src/config/heuristics.py

# Conflict Detection
CONFLICT_TEMPORAL_THRESHOLD_DAYS = 30  # Days apart for temporal resolution
CONFLICT_CONFIDENCE_THRESHOLD = 0.2    # Confidence gap to flag conflict
CONFLICT_REINFORCEMENT_THRESHOLD = 3   # Reinforcement count difference
MIN_CONFIDENCE_FOR_CONFLICT = 0.4      # Below this, just replace

# Decay on Conflict
CONFLICT_DECAY_FACTOR = 0.5            # confidence *= 0.5 on conflict
```

### Tuning Guide

**Aggressive conflict detection** (catch more conflicts):
```python
CONFLICT_CONFIDENCE_THRESHOLD = 0.1  # Lower threshold
MIN_CONFIDENCE_FOR_CONFLICT = 0.5    # Higher minimum
```

**Conservative conflict detection** (fewer false positives):
```python
CONFLICT_CONFIDENCE_THRESHOLD = 0.3  # Higher threshold
MIN_CONFIDENCE_FOR_CONFLICT = 0.3    # Lower minimum
```

---

## Testing Conflicts

```python
# tests/e2e/test_scenarios.py

@pytest.mark.e2e
async def test_scenario_17_memory_vs_db_conflict():
    """Test memory vs database conflict resolution."""

    # ARRANGE: Create outdated memory
    memory = await memory_repo.create(SemanticMemory(
        subject="sales_order_so_1001",
        predicate="status",
        object_value="fulfilled",  # Outdated
        confidence=0.70
    ))

    # ACT: Query (DB says "in_fulfillment")
    response = await client.post("/api/v1/chat", json={
        "user_id": "ops_manager",
        "message": "Is SO-1001 complete?"
    })

    # ASSERT: Reports current DB state
    assert "in_fulfillment" in response.json()["response"]

    # ASSERT: Conflict logged
    assert "conflicts_detected" in response.json()
    conflict = response.json()["conflicts_detected"][0]
    assert conflict["conflict_type"] == "memory_vs_db"
    assert conflict["resolution_strategy"] == "trust_db"
```

---

## Summary

### Core Principles

1. **Dual Truth**: Database = facts, Memory = context
2. **Transparency**: Expose conflicts, don't hide them
3. **Epistemic Humility**: Never 100% certain
4. **Self-Correction**: Memories decay when conflicted
5. **User-Centric**: Let user resolve ambiguous conflicts

### Resolution Priority

```
1. Trust Database (if memory_vs_db)
2. Trust Newest (if temporal gap > 30 days)
3. Trust Highest Confidence (if gap > 0.2)
4. Trust Most Reinforced (if gap ≥ 3 validations)
5. Ask User (if ambiguous)
```

### Key Takeaway

**Don't hide conflicts**. Transparency builds trust. The system says:
- "I found conflicting information"
- "Here's what I have: X vs Y"
- "I'm using Y because [rationale]"
- "You can correct me if I'm wrong"

This is **epistemic humility** in practice.

---

**Next**: [Architecture Overview](./architecture_overview.md) | [Cost Optimization](./cost_optimization.md)
