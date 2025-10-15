# Heuristics Calibration Document

**Version**: 1.0 (Phase 1 Initial Heuristics)
**Status**: All values are Phase 1 heuristics requiring Phase 2 calibration
**Philosophy Alignment**: DESIGN_PHILOSOPHY.md - "Useful later = improves quality with real usage data"

---

## Purpose

This document consolidates all numeric parameters, weights, thresholds, and confidence values used across the memory system. These values are **Phase 1 heuristics** chosen based on first principles and common practice, but they **MUST be tuned in Phase 2** using real operational data.

**Key Principle**: Every numeric value below should be treated as a hypothesis to be validated, not as a permanent constant.

---

## 1. Confidence and Decay Parameters

**Source**: LIFECYCLE_DESIGN.md

### 1.1 Reinforcement Confidence Boosts

When a memory is reinforced through validation or repeated occurrence:

| Event | Confidence Boost | Justification | Phase 2 Tuning Required |
|-------|-----------------|---------------|------------------------|
| **First Reinforcement** | +0.15 | Strong signal of importance | Yes - analyze correction rate by boost level |
| **Second Reinforcement** | +0.10 | Diminishing returns principle | Yes - measure impact on retrieval quality |
| **Third Reinforcement** | +0.05 | Further diminishing returns | Yes - may be noise at this point |
| **Fourth+ Reinforcement** | +0.02 | Marginal continued validation | Yes - consider cap or removal |

**Maximum Cap**: 0.95 (never 100% certain - epistemic humility principle)

**Phase 1 Rationale**:
- Logarithmic-style diminishing returns
- Based on information theory: first confirmation is most valuable
- Cap at 0.95 to maintain epistemic humility

**Phase 2 Data Requirements**:
- Minimum 100+ semantic memories with reinforcement events
- Track correction rate by reinforcement count
- Measure retrieval precision by confidence level
- **Expected Tuning**: Likely need different boosts for different fact types

**Tuning Metrics**:
```python
# Phase 2: Measure these to calibrate boosts
precision_by_confidence = {
    0.80: 0.XX,  # % of memories with conf 0.80 that were correct
    0.85: 0.XX,
    0.90: 0.XX,
    0.95: 0.XX,
}

correction_rate_by_reinforcement = {
    1: 0.XX,  # % of once-reinforced memories later corrected
    2: 0.XX,
    3: 0.XX,
}
```

### 1.2 Consolidation Confidence Boost

When multiple episodic memories consolidate into a semantic memory:

| Parameter | Value | Justification | Phase 2 Tuning Required |
|-----------|-------|---------------|------------------------|
| **Consolidation Boost** | +0.05 | Multiple sources provide corroboration | Yes - highly uncertain without data |

**Phase 1 Rationale**:
- Multiple independent observations increase confidence
- Conservative boost to avoid over-confidence

**Phase 2 Data Requirements**:
- Minimum 50+ consolidation events
- Track correction rate for consolidated vs non-consolidated memories
- **Expected Finding**: May need variable boost based on episodic source diversity

**Critical Question for Phase 2**: Is consolidation from 3 identical phrasings the same as 3 different phrasings?

### 1.3 Decay Rates

Exponential confidence decay over time:

| Parameter | Value | Justification | Phase 2 Tuning Required |
|-----------|-------|---------------|------------------------|
| **Default Decay Rate** | 0.01 per day | ~1% confidence loss per day, ~25% after 90 days | Yes - likely needs per-domain tuning |
| **Validation Threshold** | 90 days | Transition to AGING state if unvalidated | Yes - may vary by fact importance |
| **Minimum Reinforcements to Avoid Aging** | 2 | Well-reinforced facts decay slower | Yes - arbitrary threshold |

**Phase 1 Rationale**:
- Exponential decay formula: `confidence * exp(-days * 0.01)`
- At day 90: confidence reduced to ~40% of original
- Matches typical "quarterly review" cadence in knowledge management

**Phase 2 Data Requirements**:
- Minimum 200+ memories spanning 90+ days lifecycle
- Track correction rate by age
- Measure user query patterns by memory age
- **Expected Tuning**: Different decay rates for different fact types:
  - Stable facts (company names): 0.001/day
  - Volatile facts (prices, statuses): 0.05/day
  - Procedural knowledge: 0.005/day

**Tuning Metrics**:
```python
# Phase 2: Measure actual decay patterns
correction_rate_by_age = {
    '0-30 days': 0.XX,
    '31-60 days': 0.XX,
    '61-90 days': 0.XX,
    '91-180 days': 0.XX,
}
```

---

## 2. Entity Resolution Confidence Scores

**Source**: ENTITY_RESOLUTION_DESIGN.md

### 2.1 Five-Stage Resolution Confidence

| Stage | Confidence | Justification | Phase 2 Tuning Required |
|-------|-----------|---------------|------------------------|
| **Stage 1: Exact Match** | 1.0 | Perfect string match on canonical name | No - justified |
| **Stage 2: Known Alias** | 0.95 | Previously learned alias | Yes - track disambiguation errors |
| **Stage 3: Fuzzy Match** | 0.70-0.85 | Levenshtein similarity | Yes - calibrate threshold |
| **Stage 4: Coreference** | 0.60 | Contextual pronoun resolution | Yes - highly uncertain |
| **Stage 5: User Disambiguation** | 0.85 | User explicitly chose | Yes - track override rate |

**Phase 1 Rationale**:
- Higher confidence for deterministic matches
- Lower confidence for probabilistic methods
- User input valued highly (0.85) but not perfect (user errors possible)

**Phase 2 Data Requirements**:
- Minimum 100+ entity resolution events
- Track disambiguation error rate by stage
- Measure user override frequency
- **Expected Tuning**: Stage 4 (coreference) likely needs refinement based on context quality

**Tuning Metrics**:
```python
# Phase 2: Measure resolution quality
resolution_accuracy_by_stage = {
    'exact_match': 1.00,
    'known_alias': 0.XX,  # % correct
    'fuzzy_match': 0.XX,
    'coreference': 0.XX,
    'user_disambiguation': 0.XX,
}
```

### 2.2 Fuzzy Match Thresholds

| Parameter | Value | Justification | Phase 2 Tuning Required |
|-----------|-------|---------------|------------------------|
| **Fuzzy Match Threshold** | 0.70 | 70% Levenshtein similarity minimum | Yes - track false positive rate |
| **High Confidence Threshold** | 0.85 | Auto-resolve if single match above this | Yes - balance precision vs recall |
| **Multi-Match Fallback** | Disambiguation prompt | Multiple candidates above threshold | Yes - may auto-resolve if one >> others |

**Phase 1 Rationale**:
- 0.70 catches common typos ("Acme Corp" vs "Acme Corporation")
- 0.85 requires strong similarity for auto-resolution
- Conservative approach: ask user when ambiguous

**Phase 2 Data Requirements**:
- Minimum 50+ fuzzy match events
- Track false positive rate at different thresholds
- Measure user frustration with disambiguation prompts
- **Expected Tuning**: May need domain-specific thresholds (person names vs company names)

### 2.3 Fuzzy Scoring Weights

Formula: `text_similarity * 0.4 + confidence * 0.3 + semantic_score * 0.3`

| Weight Component | Value | Justification | Phase 2 Tuning Required |
|-----------------|-------|---------------|------------------------|
| **Text Similarity** | 0.4 | Primary signal | Yes - completely heuristic |
| **Historical Confidence** | 0.3 | Entity use frequency | Yes - unclear if important |
| **Semantic Similarity** | 0.3 | Embedding-based match | Yes - may be more important than text |

**Phase 1 Rationale**:
- Text similarity weighted highest (string match is most reliable)
- Confidence and semantic similarity balanced equally
- **Highly uncertain** - these weights are educated guesses

**Phase 2 Data Requirements**:
- Minimum 100+ fuzzy resolution events with ground truth
- A/B test different weight combinations
- **Expected Finding**: Semantic similarity may deserve higher weight for synonyms

---

## 3. Retrieval Scoring Weights

**Source**: RETRIEVAL_DESIGN.md

### 3.1 Strategy-Based Weight Distributions

Four different retrieval strategies with different signal weights:

#### Strategy 1: Factual Entity-Focused

| Signal | Weight | Justification | Phase 2 Tuning Required |
|--------|--------|---------------|------------------------|
| **Semantic Similarity** | 0.25 | Important but not dominant | Yes - optimize per query type |
| **Entity Overlap** | 0.40 | PRIMARY signal for factual queries | Yes - measure precision improvement |
| **Temporal Relevance** | 0.20 | Recent facts often more relevant | Yes - domain-dependent |
| **Importance** | 0.10 | User-flagged critical facts | Yes - unclear weight needed |
| **Reinforcement** | 0.05 | Well-validated facts slightly boosted | Yes - marginal utility uncertain |

**Phase 1 Rationale**:
- Entity overlap highest (0.40) because query like "What did Acme order?" needs Acme entity
- Semantic similarity lower than expected (not keyword match, so entities matter more)
- Temporal relevance valued (recent orders more relevant)

**Phase 2 Data Requirements**:
- Minimum 100+ factual queries with relevance judgments
- **Expected Tuning**: Entity overlap may need 0.50+, semantic similarity may drop to 0.15

#### Strategy 2: Temporal-Focused

| Signal | Weight | Justification | Phase 2 Tuning Required |
|--------|--------|---------------|------------------------|
| **Semantic Similarity** | 0.30 | Still important for relevance | Yes |
| **Entity Overlap** | 0.15 | Less critical for time-based queries | Yes |
| **Temporal Relevance** | 0.40 | PRIMARY signal | Yes |
| **Importance** | 0.10 | Consistent across strategies | Yes |
| **Reinforcement** | 0.05 | Consistent across strategies | Yes |

**Phase 1 Rationale**:
- For queries like "What happened last week?", time is primary signal
- Entity overlap reduced (query may not mention specific entities)

#### Strategy 3: Conceptual-Focused

| Signal | Weight | Justification | Phase 2 Tuning Required |
|--------|--------|---------------|------------------------|
| **Semantic Similarity** | 0.50 | PRIMARY signal for abstract queries | Yes |
| **Entity Overlap** | 0.10 | Minimal importance | Yes |
| **Temporal Relevance** | 0.15 | Less critical | Yes |
| **Importance** | 0.15 | Valued for conceptual queries | Yes |
| **Reinforcement** | 0.10 | Well-validated concepts preferred | Yes |

**Phase 1 Rationale**:
- For queries like "Tell me about procurement workflows", semantic meaning dominates
- Entity overlap low (query is abstract)

#### Strategy 4: Balanced (Default)

| Signal | Weight | Justification | Phase 2 Tuning Required |
|--------|--------|---------------|------------------------|
| **Semantic Similarity** | 0.35 | Moderate importance | Yes |
| **Entity Overlap** | 0.25 | Moderate importance | Yes |
| **Temporal Relevance** | 0.20 | Moderate importance | Yes |
| **Importance** | 0.15 | Slightly elevated | Yes |
| **Reinforcement** | 0.05 | Consistent | Yes |

**Phase 1 Rationale**: When query type is unclear, balance all signals

**CRITICAL PHASE 2 REQUIREMENT**:
- Minimum 500+ retrieval events (100+ per strategy)
- User relevance feedback on top-k results
- **Expected Finding**: These weights will change significantly. Consider machine learning approaches (LambdaMART, neural reranking).

### 3.2 Temporal Decay for Retrieval

| Parameter | Value | Justification | Phase 2 Tuning Required |
|-----------|-------|---------------|------------------------|
| **Temporal Decay Rate** | 0.01 per day | Same as confidence decay | Yes - may differ from confidence decay |
| **Formula** | `exp(-0.01 * age_days)` | Exponential decay | Yes - linear may be better for some queries |

**Phase 1 Rationale**: Reuse confidence decay rate for consistency

**Phase 2 Expected Tuning**:
- Temporal decay for retrieval may be different from confidence decay
- Example: Recent memories may be more relevant (faster decay), even if confidence unchanged

### 3.3 Importance Score Thresholds

| Threshold | Value | Justification | Phase 2 Tuning Required |
|-----------|-------|---------------|------------------------|
| **High Importance** | 0.8+ | User-flagged or high-impact facts | Yes - calibrate against user flags |
| **Medium Importance** | 0.5-0.8 | Normal facts | Yes |
| **Low Importance** | <0.5 | Routine observations | Yes |

**Phase 1 Rationale**: Arbitrary linear scale

**Phase 2 Expected Tuning**:
- Importance may be categorical, not continuous
- May need learning from user implicit feedback (which memories did user act on?)

### 3.4 Retrieval Limits

| Parameter | Value | Justification | Phase 2 Tuning Required |
|-----------|-------|---------------|------------------------|
| **Top K Results** | 10 | Balance recall vs context length | Yes - optimize for LLM context usage |
| **Minimum Score Threshold** | 0.3 | Avoid irrelevant results | Yes - calibrate precision/recall |
| **Ontology Expansion Depth** | 1 | Immediate neighbors only | Yes - measure benefit vs cost |

**Phase 1 Rationale**:
- 10 results fits most LLM contexts without overwhelming
- 0.3 threshold is permissive (recall-focused)
- Depth=1 avoids exponential explosion

**Phase 2 Expected Tuning**:
- K may vary by query complexity
- Threshold may vary by strategy
- Depth may increase for sparse knowledge domains

---

## 4. Learning Thresholds (Phase 2/3)

**Source**: LEARNING_DESIGN.md

These are **not implemented in Phase 1**, but documented here for future reference.

### 4.1 Minimum Sample Requirements

| Learning Dimension | Minimum Samples | Justification |
|-------------------|----------------|---------------|
| **Extraction Quality** | 50+ memories with corrections | Statistical significance |
| **Retrieval Relevance** | 100+ retrieval events with feedback | Pattern detection |
| **Entity Disambiguation** | 20+ disambiguation events | Per-entity learning |
| **Importance Calibration** | 100+ memories with user actions | Implicit feedback signals |
| **Confidence Tuning** | 50+ corrections per fact type | Type-specific decay rates |
| **Procedural Generalization** | 10+ similar procedures | Pattern abstraction |

**Rationale**: Based on statistical power analysis and common ML practice

**Phase 2 Tuning**: May discover patterns earlier or require more data than expected

### 4.2 Exploration Rates

| Parameter | Value | Justification |
|-----------|-------|---------------|
| **Epsilon-Greedy Exploration** | 0.1 | 10% exploration, 90% exploitation |
| **Minimum Exploration Count** | 5 per option | Ensure all options tried |

**Rationale**: Standard reinforcement learning practice

---

## 5. System Configuration Defaults

**Source**: DESIGN.md (system_config table)

### 5.1 Embedding Configuration

| Parameter | Value | Justification | Phase 2 Tuning Required |
|-----------|-------|---------------|------------------------|
| **Embedding Model** | text-embedding-ada-002 | OpenAI standard | Yes - evaluate newer models |
| **Embedding Dimensions** | 1536 | Model default | No - tied to model |
| **Similarity Threshold** | 0.7 | Minimum cosine similarity | Yes - calibrate precision/recall |

### 5.2 Performance Targets

| Metric | Target | Justification | Phase 2 Tuning Required |
|--------|--------|---------------|------------------------|
| **Semantic Search Latency** | <50ms | P95 for pgvector query | Yes - may need to relax |
| **Entity Retrieval Latency** | <30ms | P95 for entity lookup | Yes - measure actual |
| **Total Retrieval Latency** | <100ms | End-to-end for top-10 | Yes - optimize critical path |

**Phase 1 Rationale**: Based on typical PostgreSQL + pgvector benchmarks

**Phase 2 Tuning**: Measure actual latencies, may need caching or indexing optimizations

---

## 6. Cross-Cutting Calibration Strategy

### Phase 2 Calibration Process

When sufficient data is collected (see sample requirements above):

1. **Data Collection** (Phase 1):
   - Log all operations with timestamps
   - Log user corrections and overrides
   - Log retrieval events with feedback
   - Log disambiguation choices

2. **Analysis** (Phase 2 Start):
   - Calculate precision/recall by parameter value
   - A/B test alternative values
   - Measure user satisfaction metrics

3. **Tuning** (Phase 2 Iteration):
   - Adjust one parameter category at a time
   - Validate against held-out test set
   - Document changes and rationale

4. **Monitoring** (Phase 2 Ongoing):
   - Track calibration drift over time
   - Re-tune periodically as domain evolves
   - Alert on significant distribution shifts

### Global Principles for All Heuristics

1. **Conservative Defaults**: Prefer values that err on the side of:
   - Lower confidence (epistemic humility)
   - Higher recall (don't miss relevant memories)
   - Simpler models (avoid overfitting)

2. **Justification Burden**: Every value should either be:
   - Derived from first principles, OR
   - Marked for Phase 2 calibration

3. **Documentation**: When changing any value, document:
   - Old value
   - New value
   - Data-driven rationale
   - Expected impact

4. **Versioning**: Track heuristic versions in system_config table:
   ```json
   {
     "version": "1.0",
     "last_calibrated": "2024-01-15",
     "calibration_data_size": 1234,
     "decay_rate": 0.01,
     "rationale": "Initial Phase 1 heuristic"
   }
   ```

---

## 7. Critical Unknowns

These questions **cannot be answered** without operational data:

### 7.1 Confidence Calibration
- Q: Is +0.15 for first reinforcement the right boost?
- **Answer Requires**: 100+ memories with corrections, measure precision by boost level

### 7.2 Decay Rates
- Q: Is 0.01/day the right decay rate?
- **Answer Requires**: 200+ memories spanning 90+ days, measure correction rate by age
- **Expected Finding**: Different rates for different fact types

### 7.3 Retrieval Weights
- Q: Are entity-focused weights (0.4 entity, 0.25 semantic) optimal?
- **Answer Requires**: 500+ queries with relevance judgments
- **Expected Finding**: May need machine learning approach instead of hand-tuned weights

### 7.4 Entity Resolution
- Q: Is 0.70 the right fuzzy match threshold?
- **Answer Requires**: 100+ resolution events, measure false positive/negative rates
- **Expected Finding**: Domain-specific thresholds (person names vs company names)

### 7.5 Consolidation Boost
- Q: Should consolidation from multiple episodic memories boost confidence?
- **Answer Requires**: 50+ consolidation events, measure correction rate
- **Expected Finding**: Boost should depend on episodic source diversity, not just count

---

## 8. Heuristic Change Log

### Version 1.0 - Phase 1 Initial Values (Current)
- All values set based on first principles and common practice
- No operational data available
- All values marked for Phase 2 calibration

### Future Versions
- Document all changes here with data-driven rationale
- Example format:
  ```
  Version 1.1 - Phase 2 Calibration Round 1 (2024-XX-XX)
  - Changed decay_rate: 0.01 → 0.008
  - Rationale: Analysis of 234 memories showed correction rate plateau at 112 days
  - Data: correction_rate_by_age graph attached
  - Impact: +12% precision, -3% recall
  ```

---

## 9. Appendix: Formulas Reference

### Confidence Decay Formula
```python
def compute_effective_confidence(stored_conf, days_since_validation, decay_rate=0.01):
    return stored_conf * exp(-days_since_validation * decay_rate)
```

### Reinforcement Boost Formula
```python
def compute_reinforcement_boost(reinforcement_count):
    boosts = [0.15, 0.10, 0.05, 0.02]
    if reinforcement_count == 0:
        return 0
    index = min(reinforcement_count - 1, len(boosts) - 1)
    return boosts[index]
```

### Retrieval Score Formula
```python
def compute_retrieval_score(signals, strategy_weights):
    return sum(signals[sig] * strategy_weights[sig] for sig in signals)
```

### Fuzzy Match Score Formula
```python
def compute_fuzzy_score(text_sim, confidence, semantic_sim, use_count):
    base_score = text_sim * 0.4 + confidence * 0.3 + semantic_sim * 0.3
    popularity_boost = log(1 + use_count) * 0.1
    return base_score * (1 + popularity_boost)
```

### Temporal Relevance Formula
```python
def compute_temporal_relevance(age_days, decay_rate=0.01):
    return exp(-decay_rate * age_days)
```

---

## Summary

This document consolidates **43 numeric parameters** across the memory system.

**Phase 1 Status**: All values are educated guesses based on first principles.

**Phase 2 Requirement**: All values must be validated and tuned using real operational data.

**Minimum Data Requirements for Phase 2 Calibration**:
- 100+ semantic memories with lifecycle events
- 500+ retrieval events with feedback
- 100+ entity resolution events
- 50+ consolidation events

**Expected Outcome**: Significant changes to most heuristic values, with domain-specific and user-specific tuning replacing global constants.

**Philosophy Alignment**: "Useful later = improves quality with real usage data" - these heuristics enable Phase 1 to function, but will be improved in Phase 2 with empirical evidence.
