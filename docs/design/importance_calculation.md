# Importance Calculation Design

## Overview

**Importance** replaces `reinforcement_count` as a dynamic 0..1 score representing how much this memory matters to the user.

Unlike reinforcement_count (discrete counter), importance is **continuous and decays**, requiring active validation to maintain high scores.

---

## Calculation Formula

```python
importance = base_importance × recency_factor × confirmation_factor

# Constrained to [0.0, 1.0]
importance = min(1.0, max(0.0, importance))
```

---

## 1. Base Importance (0.3 - 0.9)

Determined at **memory creation** based on:

### A. Source Signal Strength

| Signal | Base Importance | Example |
|--------|----------------|---------|
| **Explicit "remember"** | 0.9 | "Remember: Gai prefers Friday" |
| **Strong preference** | 0.8 | "I always want NET30 terms" |
| **Observed pattern** | 0.6 | User mentions Friday 3x in conversation |
| **Casual mention** | 0.4 | "Yeah, they like Friday deliveries" |
| **Inferred/weak** | 0.3 | Inferred from context |

### B. Confidence Mapping

For Phase 1 (simple mapping):
```python
base_importance = 0.3 + (confidence × 0.6)

# Examples:
# confidence=1.0 → importance=0.9
# confidence=0.7 → importance=0.72
# confidence=0.5 → importance=0.6
# confidence=0.3 → importance=0.48
```

---

## 2. Recency Factor (0.5 - 1.0)

Memories **decay over time** unless accessed:

```python
days_since_last_access = (now - last_accessed_at).days
recency_factor = max(0.5, exp(-DECAY_RATE × days_since_last_access))

# Configuration (src/config/heuristics.py):
DECAY_RATE = 0.01  # Half-life ≈ 69 days

# Examples:
# 0 days   → factor = 1.0   (fresh)
# 30 days  → factor = 0.74  (slight decay)
# 69 days  → factor = 0.50  (half importance)
# 138 days → factor = 0.25  (fading)
```

**Key insight**: Memories naturally fade unless they remain relevant (accessed/confirmed).

---

## 3. Confirmation Factor (1.0 - 1.5)

Tracks **reinforcement history** via metadata:

```python
confirmation_count = metadata.get("confirmation_count", 0)
confirmation_factor = min(1.5, 1.0 + 0.1 × confirmation_count)

# Examples:
# 0 confirmations → factor = 1.0  (no boost)
# 1 confirmation  → factor = 1.1  (10% boost)
# 3 confirmations → factor = 1.3  (30% boost)
# 5+ confirmations → factor = 1.5 (50% boost, capped)
```

**Storage**: Store in `object_value` metadata:
```json
{
  "text": "Gai Media prefers Friday deliveries",
  "metadata": {
    "confirmation_count": 3,
    "last_confirmed_at": "2025-10-16T10:00:00Z",
    "confirmation_sources": [101, 205, 312]  // event_ids
  }
}
```

---

## 4. Dynamic Updates

### When to Recalculate Importance

1. **On retrieval** (passive decay):
   - Recalculate recency_factor
   - Update `last_accessed_at` timestamp
   - Persist updated importance

2. **On confirmation** (reinforcement):
   - Increment `confirmation_count`
   - Recalculate with new confirmation_factor
   - Reset recency (last_accessed_at = now)
   - Persist

3. **On conflict** (invalidation):
   - Set importance = 0.1 (mark as invalidated but keep for audit)
   - Or delete if desired

---

## 5. Phase 1 Implementation (Simplified)

For initial implementation, **skip recency/confirmation factors**:

```python
# At creation:
importance = 0.3 + (confidence × 0.6)

# On confirmation (when same info mentioned again):
importance = min(1.0, importance + 0.05)

# On invalidation (conflict detected):
importance = 0.1
```

**Rationale**:
- Simpler to implement and test
- Can add decay/confirmation in Phase 2
- Still provides meaningful ordering (high confidence = high importance)

---

## 6. Usage in Retrieval

### Ranking Formula (Multi-Signal)

```python
relevance_score = (
    0.35 × semantic_similarity     # Vector cosine
  + 0.25 × entity_overlap          # Shared entities
  + 0.20 × importance              # NEW: Replace recency
  + 0.15 × recency                 # Separate recency signal
  + 0.05 × temporal_coherence      # Session continuity
)
```

**Key change**: `importance` replaces raw `reinforcement_count` as a normalized 0..1 signal.

### Filtering

```python
# Only retrieve memories with minimum importance
memories = await repo.find_similar(
    embedding=query_embedding,
    min_importance=0.3  # Filter out low-importance memories
)
```

---

## 7. Examples

### Example 1: Explicit Statement
```
User: "Remember: Gai Media always wants NET30 payment terms"

→ confidence = 0.95 (explicit)
→ base_importance = 0.3 + (0.95 × 0.6) = 0.87
→ importance = 0.87 (Phase 1 simple)
```

### Example 2: Casual Mention
```
User: "Yeah, they mentioned they prefer Friday once"

→ confidence = 0.6 (casual)
→ base_importance = 0.3 + (0.6 × 0.6) = 0.66
→ importance = 0.66
```

### Example 3: Reinforcement
```
Day 1: importance = 0.87
Day 30: User confirms again → importance = min(1.0, 0.87 + 0.05) = 0.92
Day 60: User confirms again → importance = min(1.0, 0.92 + 0.05) = 0.97
```

### Example 4: Decay (Phase 2)
```
Day 1: importance = 0.87
Day 69 (no access):
  → recency_factor = 0.5
  → importance = 0.87 × 0.5 = 0.435 (faded)
```

---

## 8. Migration Path

### Phase 1 (Current)
- Simple importance = f(confidence)
- No decay, minimal reinforcement

### Phase 2 (Future)
- Add recency_factor (time decay)
- Track confirmation_count in metadata
- Recalculate on retrieval

### Phase 3 (Advanced)
- User feedback signals (thumbs up/down)
- Usage-based importance (how often retrieved)
- Entity centrality (popular entities → higher importance)

---

## Summary

**Key Design Decisions**:

1. ✅ **Importance replaces reinforcement_count** as a continuous 0..1 score
2. ✅ **Base importance from confidence** (simple Phase 1 mapping)
3. ✅ **Stored directly** in `importance` column (not calculated on-the-fly)
4. ✅ **Decays over time** (Phase 2) unless accessed/confirmed
5. ✅ **Used in ranking** as a normalized signal (replaces raw count)
6. ✅ **Metadata tracks confirmations** for transparency

**Philosophy**: Memory importance reflects **current relevance**, not just **how many times mentioned**. Inactive memories fade, active ones stay prominent.
