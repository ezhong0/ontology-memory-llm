# Configuration Reference

Complete guide to all 43+ tunable parameters in `src/config/heuristics.py`.

---

## Quick Reference

```python
from src.config import heuristics

# Access parameters
max_conf = heuristics.MAX_CONFIDENCE  # 0.95
decay_rate = heuristics.DECAY_RATE_PER_DAY  # 0.01
```

---

## Lifecycle Management

### Confidence Limits

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `MAX_CONFIDENCE` | 0.95 | 0.8-0.99 | Epistemic humility (never 100% certain) |
| `MIN_CONFIDENCE_FOR_USE` | 0.3 | 0.2-0.5 | Below this, memory needs validation |

**Example**:
```python
# Memory with confidence < 0.3 triggers active recall
if memory.confidence < heuristics.MIN_CONFIDENCE_FOR_USE:
    return "I'm not certain. Last validated 90 days ago. Still accurate?"
```

### Reinforcement

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `REINFORCEMENT_BOOSTS` | [0.15, 0.10, 0.05, 0.02] | Confidence boost per validation (diminishing returns) |
| `CONSOLIDATION_BOOST` | 0.05 | Boost from consolidation |

**Usage**:
```python
# 1st validation: +0.15
# 2nd validation: +0.10
# 3rd validation: +0.05
# 4th+ validation: +0.02
boost = heuristics.get_reinforcement_boost(validation_count)
memory.confidence = min(memory.confidence + boost, MAX_CONFIDENCE)
```

### Decay

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `DECAY_RATE_PER_DAY` | 0.01 | 0.005-0.02 | Exponential decay (1% per day) |
| `VALIDATION_THRESHOLD_DAYS` | 90 | 30-180 | Days before active recall |

**Formula**:
```python
confidence_t = confidence_0 × e^(-DECAY_RATE × days)

# Examples:
# Day 0: 0.85
# Day 30: 0.85 × e^(-0.01 × 30) = 0.63
# Day 60: 0.85 × e^(-0.01 × 60) = 0.47
# Day 90: 0.85 × e^(-0.01 × 90) = 0.35 → Triggers validation
```

**Tuning Guide**:
- **Faster decay** (0.02): Aggressive validation (60 days → 0.5)
- **Slower decay** (0.005): Conservative validation (120 days → 0.5)

---

## Entity Resolution

### Confidence by Stage

| Parameter | Default | Range | Method |
|-----------|---------|-------|--------|
| `CONFIDENCE_EXACT_MATCH` | 1.0 | 1.0 | Exact match on canonical name |
| `CONFIDENCE_USER_ALIAS` | 0.95 | 0.9-0.98 | User-specific alias |
| `CONFIDENCE_FUZZY_HIGH` | 0.85 | 0.8-0.9 | Strong fuzzy match |
| `CONFIDENCE_FUZZY_LOW` | 0.70 | 0.6-0.8 | Weak fuzzy match |
| `CONFIDENCE_COREFERENCE` | 0.60 | 0.5-0.7 | LLM coreference resolution |
| `CONFIDENCE_DISAMBIGUATION` | 0.85 | 0.8-0.9 | After user selection |

### Fuzzy Matching

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `FUZZY_MATCH_THRESHOLD` | 0.65 | 0.5-0.8 | Minimum similarity (allows "Kay" → "Kai") |
| `FUZZY_MATCH_AUTO_RESOLVE` | 0.85 | 0.8-0.95 | Auto-resolve if above this |

**Example**:
```python
# "Kay Media" vs "Kai Media"
similarity = pg_trgm_similarity("Kay Media", "Kai Media")  # 0.92

if similarity >= FUZZY_MATCH_AUTO_RESOLVE:
    # Auto-resolve (0.92 > 0.85)
    return ResolutionResult(entity_id, confidence=0.85, method="fuzzy")
elif similarity >= FUZZY_MATCH_THRESHOLD:
    # Consider as candidate (0.92 > 0.65)
    candidates.append(entity)
```

**Tuning Guide**:
- **Lower threshold** (0.5): More candidates, more ambiguity
- **Higher threshold** (0.8): Fewer candidates, more "unresolved"

### Disambiguation

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `DISAMBIGUATION_MIN_CONFIDENCE_GAP` | 0.15 | Gap to avoid disambiguation UI |
| `DISAMBIGUATION_MAX_CANDIDATES` | 5 | Max candidates to show user |

**Example**:
```python
# Two candidates:
# "Apple Inc" (0.95)
# "Apple Farm" (0.95)
# Gap = 0.0 < 0.15 → Ask user

# vs:
# "Apple Inc" (0.95)
# "Apple Farm" (0.75)
# Gap = 0.20 > 0.15 → Auto-select "Apple Inc"
```

### Alias Learning

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `ALIAS_CONFIDENCE_BOOST_PER_USE` | 0.02 | 0.01-0.05 | Incremental boost per use (max 0.95) |

---

## Retrieval System

### Strategy Weights

Four strategies based on query type:

#### Factual/Entity-Focused (Default)
```python
RETRIEVAL_STRATEGY_WEIGHTS["factual_entity_focused"] = {
    "semantic_similarity": 0.25,
    "entity_overlap": 0.40,     # ← Prioritize entity match
    "temporal_relevance": 0.20,
    "importance": 0.10,
    "reinforcement": 0.05,
}
```

**Use when**: Query mentions specific entities ("What's Gai's status?")

#### Procedural
```python
RETRIEVAL_STRATEGY_WEIGHTS["procedural"] = {
    "semantic_similarity": 0.45,
    "entity_overlap": 0.05,
    "temporal_relevance": 0.05,
    "importance": 0.15,
    "reinforcement": 0.30,      # ← Prioritize validated patterns
}
```

**Use when**: Query asks "how to" or about processes

#### Exploratory
```python
RETRIEVAL_STRATEGY_WEIGHTS["exploratory"] = {
    "semantic_similarity": 0.35,  # Balanced
    "entity_overlap": 0.25,
    "temporal_relevance": 0.15,
    "importance": 0.20,
    "reinforcement": 0.05,
}
```

**Use when**: Open-ended queries ("Tell me about last week")

#### Temporal
```python
RETRIEVAL_STRATEGY_WEIGHTS["temporal"] = {
    "semantic_similarity": 0.20,
    "entity_overlap": 0.20,
    "temporal_relevance": 0.40,  # ← Prioritize recency
    "importance": 0.15,
    "reinforcement": 0.05,
}
```

**Use when**: Time-specific queries ("What happened yesterday?")

**Usage**:
```python
from src.config.heuristics import get_retrieval_weights

weights = get_retrieval_weights("factual_entity_focused")
score = (
    weights["semantic_similarity"] × semantic_sim
  + weights["entity_overlap"] × entity_overlap
  + ...
)
```

### Retrieval Limits

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `MAX_SEMANTIC_CANDIDATES` | 50 | 20-100 | pgvector top-k |
| `MAX_ENTITY_CANDIDATES` | 30 | 10-50 | Entity-based retrieval |
| `MAX_TEMPORAL_CANDIDATES` | 30 | 10-50 | Recent memories |
| `MAX_SUMMARY_CANDIDATES` | 5 | 3-10 | Consolidated summaries |

### Type Boosts

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `SUMMARY_BOOST` | 1.15 | Summaries get 15% boost (consolidate > individual) |

### Temporal Decay

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `EPISODIC_HALF_LIFE_DAYS` | 30 | 14-60 | Episodic memories decay faster |
| `SEMANTIC_HALF_LIFE_DAYS` | 90 | 60-180 | Semantic facts decay slower |

**Formula**:
```python
recency_score = e^(-ln(2) / HALF_LIFE × age_in_days)

# Example (semantic, HALF_LIFE=90):
# Day 0: 1.0
# Day 45: 0.71
# Day 90: 0.5
# Day 180: 0.25
```

---

## Conflict Detection

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `CONFLICT_TEMPORAL_THRESHOLD_DAYS` | 30 | 7-90 | Days apart for temporal conflict |
| `CONFLICT_CONFIDENCE_THRESHOLD` | 0.2 | 0.1-0.3 | Confidence gap to flag conflict |
| `CONFLICT_REINFORCEMENT_THRESHOLD` | 3 | 2-5 | Reinforcement count gap |
| `MIN_CONFIDENCE_FOR_CONFLICT` | 0.4 | 0.3-0.5 | Below this, just replace |

**Example**:
```python
# Memory A: confidence=0.7, reinforcement=1
# Memory B: confidence=0.5, reinforcement=1
# Gap = 0.2 ≥ CONFLICT_CONFIDENCE_THRESHOLD → Conflict!

# Resolution: Keep A (higher confidence)
```

---

## Consolidation

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `CONSOLIDATION_MIN_EPISODIC` | 10 | 5-20 | Min memories to consolidate |
| `CONSOLIDATION_MIN_SESSIONS` | 3 | 2-5 | Min sessions in window |
| `CONSOLIDATION_SESSION_WINDOW_DEFAULT` | 5 | 3-10 | Last N sessions |

**Example**:
```bash
# Automatic consolidation triggers when:
# - User has 10+ episodic memories in last 5 sessions
# - OR manually via POST /api/v1/consolidate
```

---

## Procedural Memory

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `PROCEDURAL_MIN_CONFIDENCE` | 0.5 | 0.4-0.7 | Min confidence to use pattern |
| `PROCEDURAL_MIN_SUPPORT` | 3 | 2-5 | Min observations to create pattern |
| `PROCEDURAL_LOOKBACK_DAYS` | 30 | 14-90 | Days to analyze |

**Example**:
```python
# Pattern: "invoice mentioned" → "query domain.invoices"
# Observed 5 times in last 30 days
# Success rate: 0.85
# → confidence = 0.85 > 0.5 → Use pattern
```

---

## Semantic Extraction

| Parameter | Default | Range | Source |
|-----------|---------|-------|--------|
| `EXTRACTION_CONFIDENCE["explicit_statement"]` | 0.7 | 0.6-0.8 | "Remember: X prefers Y" |
| `EXTRACTION_CONFIDENCE["inferred"]` | 0.5 | 0.4-0.6 | Inferred from context |
| `EXTRACTION_CONFIDENCE["consolidation"]` | 0.75 | 0.7-0.85 | LLM consolidation |
| `EXTRACTION_CONFIDENCE["correction"]` | 0.85 | 0.8-0.9 | User corrects fact |

---

## Context Window Management

Budget allocation for LLM context:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `CONTEXT_DB_FACTS` | 0.40 | 40% for database facts |
| `CONTEXT_SUMMARIES` | 0.20 | 20% for summaries |
| `CONTEXT_SEMANTIC` | 0.20 | 20% for semantic facts |
| `CONTEXT_EPISODIC` | 0.15 | 15% for episodic |
| `CONTEXT_PROCEDURAL` | 0.05 | 5% for procedural hints |

**Total**: 100% of available context

**Example**:
```python
# If max_context_tokens = 8000:
# DB facts: 3200 tokens
# Summaries: 1600 tokens
# Semantic: 1600 tokens
# Episodic: 1200 tokens
# Procedural: 400 tokens
```

---

## LLM Tool Calling (Phase 1C)

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `TOOL_ORCHESTRATION_MAX_ITERATIONS` | 5 | Max rounds (prevent loops) |
| `TOOL_ORCHESTRATION_MODEL` | `"claude-haiku-4-5"` | Fast, cheap model |

---

## Environment Variables

Set in `.env` file:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/memorydb

# LLM Providers
LLM_PROVIDER=openai  # or "anthropic"
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Logging
LOG_LEVEL=INFO  # DEBUG | INFO | WARNING | ERROR
STRUCTLOG_DEV_MODE=true  # Pretty-print logs in dev

# Demo Mode
DEMO_MODE_ENABLED=false

# Performance
MAX_CONTEXT_TOKENS=8000  # LLM context window
EMBEDDING_DIMENSIONS=1536  # OpenAI text-embedding-3-small
```

---

## Tuning Guide

### Use Case: Aggressive Validation

```python
# Want memories to decay faster and ask for validation sooner
DECAY_RATE_PER_DAY = 0.02  # 2% per day (vs 1%)
VALIDATION_THRESHOLD_DAYS = 60  # 60 days (vs 90)
MIN_CONFIDENCE_FOR_USE = 0.4  # 0.4 (vs 0.3)

# Result: Reaches 0.5 confidence in ~35 days, asks for validation at 60 days
```

### Use Case: Prioritize Exact Matches

```python
# Want fewer fuzzy matches, more "unresolved"
FUZZY_MATCH_THRESHOLD = 0.80  # 0.80 (vs 0.65)
FUZZY_MATCH_AUTO_RESOLVE = 0.90  # 0.90 (vs 0.85)

# Result: Only strong matches pass, more disambiguation UIs
```

### Use Case: Prioritize Recency

```python
# Retrieval strategy: boost temporal relevance
RETRIEVAL_STRATEGY_WEIGHTS["custom"] = {
    "semantic_similarity": 0.25,
    "entity_overlap": 0.20,
    "temporal_relevance": 0.35,  # ← Boosted
    "importance": 0.15,
    "reinforcement": 0.05,
}
```

---

## Validation

Check configuration validity:

```bash
# In Python shell
poetry run python

>>> from src.config import heuristics
>>> heuristics.MAX_CONFIDENCE
0.95

>>> heuristics.get_retrieval_weights("factual")
{'semantic_similarity': 0.25, 'entity_overlap': 0.40, ...}

>>> heuristics.get_reinforcement_boost(3)
0.05  # 3rd validation boost
```

---

## Performance Impact

| Parameter Change | Impact |
|------------------|--------|
| ↑ `FUZZY_MATCH_THRESHOLD` | Fewer fuzzy matches, faster resolution |
| ↑ `MAX_SEMANTIC_CANDIDATES` | Better recall, slower retrieval (linear) |
| ↑ `DECAY_RATE_PER_DAY` | More validation prompts, more user interaction |
| ↑ `ENTITY_OVERLAP` weight | Better entity-focused retrieval, worse exploratory |
| ↑ `TOOL_ORCHESTRATION_MAX_ITERATIONS` | More complex queries, higher cost |

---

**Next**: [API Reference](./api_reference.md) | [Database Schema](./database_schema.md)
