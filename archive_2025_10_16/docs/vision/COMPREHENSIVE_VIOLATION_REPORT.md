# Comprehensive Vision Violation Report (Deep Analysis)

**Analysis Date**: 2025-10-16
**Codebase**: Ontology-Aware Memory System for LLM Agents
**Vision Document**: `/docs/vision/VISION.md`
**Scope**: Full codebase scan with philosophical alignment analysis

---

## Executive Summary

This report identifies **architectural and philosophical violations** at three levels:

1. **Surface violations** (confidence=1.0, hardcoded keywords)
2. **Architectural violations** (missing feedback loops, static parameters)
3. **Philosophical violations** (programmed vs emergent intelligence)

**Critical Finding**: The codebase has **excellent structure** (hexagonal architecture, typed, async) but implements **programmed intelligence** when the vision calls for **emergent intelligence**.

From VISION.md lines 466-486:
> "Intelligence isn't programmed - it **emerges from interaction of simple mechanisms**... These simple rules, applied consistently, yield **emergent intelligent behavior**"

The system currently violates this by:
- Hardcoding what should be learned
- Missing feedback loops needed for emergence
- No infrastructure for meta-learning
- Static parameters that should adapt

---

## Part I: Critical Violations (Immediate Fixes)

### C1. Epistemic Humility Violations (confidence=1.0)

**Vision Principle Violated**: Lines 386-421
> "MAX_CONFIDENCE = 0.95 (never 100%) - Even exact database matches could be typos or outdated"

**All instances of confidence=1.0 in codebase:**

1. **`src/config/heuristics.py:39`** - ROOT CAUSE
   ```python
   # VIOLATION
   CONFIDENCE_EXACT_MATCH = 1.0  # Should be 0.95
   ```
   - **Impact**: Propagates to all exact entity resolution results
   - **Used by**: `EntityResolutionService._stage1_exact_match()` line 186

2. **`src/application/use_cases/process_chat_message.py:390`**
   ```python
   # VIOLATION - DB facts claiming 100% certainty
   new_confidence = 1.0  # DB is authoritative
   ```
   - **Philosophical issue**: From VISION.md lines 189-199, even DB facts can be stale or have data entry errors
   - **Quote**: "Current database facts - Authoritative, transactional, source of truth for 'what is'" - but line 396 adds "Make confidence explicit... Low confidence → cite source, hedge language"

3. **`src/domain/services/debug_trace_service.py:149`**
   ```python
   confidence=1.0  # Debug traces at 100% certainty
   ```

4. **`src/demo/services/scenario_loader.py:492`**
   ```python
   confidence=1.0  # Demo data claiming perfect certainty
   ```

5. **`src/domain/services/conflict_detection_service.py:374`**
   ```python
   confidence_diff=1.0,  # DB has 100% confidence (authoritative)
   ```
   - **Context**: `detect_memory_vs_db_conflict` method
   - **Issue**: Comment says "authoritative" but code violates epistemic humility

**Philosophical Rationale** (VISION.md lines 386-403):

> "Epistemic Humility: A profound principle: **The system should know what it doesn't know**...
> Many systems fail by **overconfident hallucination** - stating uncertain things with certainty.
> This system makes uncertainty **explicit and actionable**"

Even the most authoritative source (database) can have:
- Data entry errors
- Stale cache/replication lag
- Temporal validity issues ("status=open" may have just changed)
- Semantic ambiguity (what does "complete" mean?)

**Solution**:

```python
# src/config/heuristics.py - Fix the root
CONFIDENCE_EXACT_MATCH = 0.95  # Epistemic humility: never 100% certain

# For ALL database facts
DB_FACT_CONFIDENCE = 0.95  # Authoritative but not infallible

# src/application/use_cases/process_chat_message.py:390
from src.config import heuristics
new_confidence = heuristics.DB_FACT_CONFIDENCE  # Authoritative, not perfect

# Philosophy: MAX_CONFIDENCE = 0.95 enforces "I could be wrong" mindset
# This is not uncertainty - it's epistemic honesty
```

---

### C2. Brittle String Matching (Hard Equality)

**Vision Principle Violated**: Lines 145-170 - "Context as Constitutive of Meaning"
**Also violates**: Lines 386-403 - "Epistemic Humility"

**Violations**:

1. **`src/infrastructure/llm/anthropic_llm_service.py:451`**
2. **`src/infrastructure/llm/openai_llm_service.py:444`**

Both:
```python
# VIOLATION: Assumes exact format
if response_text.upper() == "UNKNOWN":
    return ResolutionResult.failed(...)
```

**Problem**:
- Fails if LLM returns: "unknown", "Unknown", "uncertain", "I don't know", "unclear", "cannot determine", "not sure"
- No semantic understanding
- Brittle assumption about LLM output format

**Deeper Issue - From VISION.md lines 145-155**:
> "Context as Constitutive of Meaning: Here's a deep truth from philosophy of language: **meaning is always contextual**. The question 'Is this ready?' has no meaning without context"

Hard string matching ignores:
- Semantic equivalence ("unknown" = "uncertain" = "can't tell")
- Contextual meaning (LLM might hedge differently)
- Pragmatic communication (LLM expresses uncertainty in various ways)

**Vision-Aligned Solution**:

```python
# Semantic understanding of uncertainty, not exact string match
UNCERTAINTY_INDICATORS = {
    # Direct statements
    "unknown", "unsure", "uncertain", "unclear",
    # Inability expressions
    "cannot determine", "can't tell", "can't say", "don't know",
    # Hedging
    "ambiguous", "unclear referent", "multiple possibilities",
    "not enough context", "insufficient information"
}

# Fuzzy semantic match
def indicates_uncertainty(response: str) -> bool:
    """Check if LLM response indicates inability to resolve."""
    normalized = response.strip().lower()

    # Check for any uncertainty indicator
    if any(indicator in normalized for indicator in UNCERTAINTY_INDICATORS):
        return True

    # Check for null/none responses
    if normalized in {"null", "none", "n/a"}:
        return True

    return False

# Usage
if indicates_uncertainty(response_text):
    return ResolutionResult.failed(
        mention_text=mention.text,
        reason=f"LLM indicated uncertainty: {response_text}"
    )
```

**Better: LLM Structured Output with Confidence**
```python
# Ask LLM for structured response with explicit confidence
response_schema = {
    "entity_id": "string | null",
    "confidence": "float 0-1",
    "reasoning": "string"
}

# LLM returns:
# {"entity_id": null, "confidence": 0.0, "reasoning": "No clear referent in context"}
# OR
# {"entity_id": "customer_123", "confidence": 0.85, "reasoning": "Recent mention matches Gai Media"}

# Now use confidence threshold instead of string matching
```

---

## Part II: High-Priority Architectural Violations

### H1. Static Retrieval Weights (No Per-User Adaptation)

**Vision Principle Violated**: VISION.md lines 507-522 - "Adaptive Behavior"

**Quote from Vision**:
> "The system **adapts to its user and domain**:
> - User A always wants invoice details → prioritize financial memories
> - User B cares about technician names → prioritize operational memories
> - User C asks about payments frequently → proactive payment monitoring
> This adaptation happens **automatically through usage patterns** - no explicit configuration needed."

**Violation**: `src/config/heuristics.py:62-95`

```python
# HARDCODED - Same weights for ALL users!
RETRIEVAL_STRATEGY_WEIGHTS = {
    "factual_entity_focused": {
        "semantic_similarity": 0.25,
        "entity_overlap": 0.40,
        "temporal_relevance": 0.20,
        "importance": 0.10,
        "reinforcement": 0.05,
    },
    # ... more strategies, all static
}
```

**Problem**:
- User A who only cares about finances gets same weights as User B who cares about operations
- No learning from which signals correlated with useful retrievals
- No adaptation based on usage patterns

**Architectural Violation**: Missing the entire feedback loop infrastructure needed for adaptive behavior.

**Vision-Aligned Solution**:

```python
# Phase 1: Add usage tracking infrastructure
class RetrievalFeedbackTracker:
    """Track retrieval outcomes for learning optimal weights.

    Philosophy: Learn what works by observing outcomes.
    """

    async def track_retrieval_outcome(
        self,
        user_id: str,
        query: str,
        strategy: str,
        retrieved_memories: list[ScoredMemory],
        was_useful: bool,  # Did memories contribute to response?
        user_feedback: float | None = None,  # Optional explicit feedback
    ):
        """Track whether retrieved memories were actually useful.

        Usefulness signals:
        - Explicit: User thumbs up/down
        - Implicit: Memories cited in final response
        - Behavioral: User asked follow-up vs abandoned
        """
        await self.repo.log_retrieval_event({
            "user_id": user_id,
            "query_embedding": await self.embed(query),
            "strategy": strategy,
            "signal_scores": {
                mem.candidate.memory_id: mem.signal_breakdown.to_dict()
                for mem in retrieved_memories[:5]  # Top 5
            },
            "was_useful": was_useful,
            "user_feedback": user_feedback,
            "timestamp": datetime.now(UTC)
        })

# Phase 2: Learn per-user weight distributions
async def learn_user_weights(user_id: str) -> dict[str, float]:
    """Learn optimal retrieval weights for specific user.

    Philosophy: Different users care about different signals.
    """
    # Get user's retrieval history
    history = await feedback_tracker.get_user_history(user_id, limit=100)

    # Filter to successful retrievals
    successful = [h for h in history if h["was_useful"]]

    if len(successful) < 20:
        # Not enough data, use defaults
        return heuristics.RETRIEVAL_STRATEGY_WEIGHTS["exploratory"]

    # Analyze which signals correlated with success
    # Example: User A's successful retrievals had high entity_overlap
    # Example: User B's successful retrievals had high recency

    signal_importance = compute_signal_correlations(successful)

    # Normalize to sum to 1.0
    weights = normalize_weights(signal_importance)

    # Blend with defaults (avoid overfitting)
    alpha = min(0.7, len(successful) / 100)  # More data → more personalization
    personalized_weights = blend_weights(weights, default_weights, alpha)

    logger.info(
        "learned_user_weights",
        user_id=user_id,
        sample_size=len(successful),
        weights=personalized_weights
    )

    return personalized_weights

# Usage in MultiSignalScorer
class MultiSignalScorer:
    async def score_candidates(self, candidates, query_context):
        # Get personalized weights for this user
        weights = await self.get_user_weights(query_context.user_id)

        # Score with personalized weights
        scored = [self._score_single_candidate(c, query_context, weights)
                  for c in candidates]

        return sorted(scored, key=lambda x: x.relevance_score, reverse=True)
```

**Emergent Properties**:
- System learns each user's priorities automatically
- No configuration needed
- Adapts as user behavior changes
- Vision-aligned: "Intelligence emerges from simple mechanisms + usage"

---

### H2. Static Decay Rates (No Per-Predicate Learning)

**Vision Principle Violated**: VISION.md lines 517-520

**Quote**:
> "Different facts have different decay rates:
> - Fast decay: Contact persons, project statuses (change frequently)
> - Slow decay: Payment terms, delivery preferences (stable)
> - No decay: Historical facts ('X happened on date Y')
> **The system should learn decay rates per fact type** based on observed change patterns."

**Violation**: `src/config/heuristics.py:16`

```python
# HARDCODED - Same decay rate for ALL fact types!
DECAY_RATE_PER_DAY = 0.01  # 1% per day

# Used for all semantic memories regardless of predicate type
```

**Problem**:
- "contact_person" predicate decays at same rate as "payment_terms" predicate
- Vision explicitly says different fact types should have different decay rates
- No learning from observed change frequency

**Deeper Violation**: From VISION.md lines 256-261:
> "Different facts have different decay rates... The system should **learn decay rates per fact type** based on observed change patterns."

This isn't just a missing feature - it's a philosophical misalignment. The vision says the system should **discover** which facts are stable vs volatile, not be told.

**Vision-Aligned Solution**:

```python
# Phase 1: Track fact mutations
class FactMutationTracker:
    """Track when facts change to learn decay rates.

    Philosophy: Observe reality to learn its patterns.
    """

    async def track_fact_change(
        self,
        predicate: str,
        old_value: dict,
        new_value: dict,
        days_since_last_change: int,
        confidence_in_change: float,
    ):
        """Record when a fact changes value."""
        await self.repo.log_mutation({
            "predicate": predicate,
            "old_value": old_value,
            "new_value": new_value,
            "days_stable": days_since_last_change,
            "change_confidence": confidence_in_change,
            "timestamp": datetime.now(UTC)
        })

# Phase 2: Learn predicate-specific decay rates
async def learn_decay_rates() -> dict[str, float]:
    """Learn how fast different predicate types change.

    Returns decay_rate_per_day for each predicate pattern.
    """
    mutations = await mutation_tracker.get_all_mutations()

    # Group by predicate
    by_predicate = defaultdict(list)
    for mut in mutations:
        by_predicate[mut["predicate"]].append(mut["days_stable"])

    decay_rates = {}
    for predicate, stable_periods in by_predicate.items():
        if len(stable_periods) < 5:
            # Not enough data, use default
            decay_rates[predicate] = heuristics.DECAY_RATE_PER_DAY
            continue

        # Calculate median time to change
        median_stable_days = np.median(stable_periods)

        # Convert to decay rate
        # Logic: If facts typically change after 30 days, decay should be slower
        # If facts typically change after 3 days, decay should be faster

        # Half-life formula: decay_rate = ln(2) / half_life
        half_life = median_stable_days
        decay_rate = math.log(2) / max(half_life, 1)  # Prevent division by zero

        decay_rates[predicate] = decay_rate

        logger.info(
            "learned_decay_rate",
            predicate=predicate,
            median_stable_days=median_stable_days,
            decay_rate_per_day=decay_rate,
            sample_size=len(stable_periods)
        )

    return decay_rates

# Usage in MemoryValidationService
class MemoryValidationService:
    async def calculate_confidence_decay(self, memory: SemanticMemory):
        # Get learned decay rate for this predicate type
        decay_rate = await self.get_predicate_decay_rate(memory.predicate)

        # Apply learned decay rate
        days_elapsed = (datetime.now(UTC) - memory.last_validated_at).days
        decay_factor = math.exp(-decay_rate * days_elapsed)

        return memory.confidence * decay_factor
```

**Meta-Learning**: System learns ABOUT learning
- Discovers which fact types are stable vs volatile
- Adapts decay rates based on observed reality
- No hardcoded assumptions about domain

---

### H3. No Feedback Loop for Conflict Resolution

**Vision Principle Violated**: VISION.md lines 507-522 - "Learning from Usage"

**Current State**: `src/domain/services/conflict_detection_service.py:224-301`

```python
def _recommend_resolution(self, ...):
    """Recommend conflict resolution strategy.

    Resolution priority:  # ← HARDCODED STRATEGY ORDER
    1. Temporal: Most recent wins (>30 days difference)
    2. Confidence: Highest confidence wins (>0.2 difference)
    3. Reinforcement: Most reinforced wins (>3 observations difference)
    """
    if temporal_diff_days >= self._temporal_threshold:
        return ConflictResolution.KEEP_NEWEST

    if confidence_diff >= self._confidence_threshold:
        return ConflictResolution.KEEP_HIGHEST_CONFIDENCE

    # ... hardcoded priority order
```

**Problem**:
- Strategy priority is hardcoded
- No learning from which strategies work best
- Vision says "Learn what matters" but system doesn't track resolution outcomes

**Missing**: The entire feedback loop

```
Conflict Detected → Resolution Applied → ??? → No Learning
                                          ↑
                                   MISSING: Outcome tracking
```

**Vision-Aligned Solution**:

```python
# Add outcome tracking
class ConflictResolutionTracker:
    """Track conflict resolution outcomes to learn optimal strategies.

    Philosophy: Learn which resolution strategies work by observing outcomes.
    """

    async def track_resolution_outcome(
        self,
        conflict: MemoryConflict,
        resolution_applied: ConflictResolution,
        outcome_quality: float,  # 0-1 score of how well it worked
        outcome_signals: dict,  # What happened after resolution
    ):
        """Track whether resolution was effective.

        Outcome signals:
        - Did user correct the resolution? (explicit negative feedback)
        - Was resolved value used successfully? (implicit positive feedback)
        - Did another conflict arise? (resolution may have been wrong)
        - Did subsequent queries work correctly? (resolution enabled correct reasoning)
        """
        await self.repo.log_resolution_event({
            "conflict_type": conflict.conflict_type,
            "resolution_strategy": resolution_applied,
            "confidence_diff": conflict.confidence_diff,
            "temporal_diff_days": conflict.temporal_diff_days,
            "reinforcement_diff": (1 - conflict.metadata.get("existing_reinforcement_count", 0)),
            "predicate": conflict.predicate,
            "outcome_quality": outcome_quality,
            "outcome_signals": outcome_signals,
            "timestamp": datetime.now(UTC)
        })

# Learn optimal strategy per conflict context
async def learn_resolution_strategy(conflict_context: dict) -> ConflictResolution:
    """Learn which resolution strategy works best for this context.

    Philosophy: Different predicates may have different optimal strategies.
    Example: For "current_status", recency matters most
             For "payment_terms", confidence matters most
    """
    # Get historical resolutions for similar conflicts
    similar_conflicts = await tracker.get_similar_conflicts(
        predicate=conflict_context["predicate"],
        conflict_type=conflict_context["conflict_type"]
    )

    # Analyze which strategies had best outcomes
    strategy_performance = defaultdict(list)
    for past in similar_conflicts:
        strategy_performance[past["resolution_strategy"]].append(
            past["outcome_quality"]
        )

    # Choose strategy with best average outcome
    best_strategy = max(
        strategy_performance.items(),
        key=lambda x: np.mean(x[1])  # Average quality
    )[0]

    logger.info(
        "learned_conflict_resolution",
        predicate=conflict_context["predicate"],
        best_strategy=best_strategy,
        avg_quality=np.mean(strategy_performance[best_strategy]),
        sample_size=len(strategy_performance[best_strategy])
    )

    return best_strategy
```

**Emergent Behavior**:
- System learns: "For payment_terms, confidence beats recency"
- System learns: "For project_status, recency beats confidence"
- No need to hardcode domain knowledge - emerges from observation

---

### H4. Hardcoded Intent Classification (No Learning)

**Vision Principle Violated**: Lines 466-486 - "Emergent Intelligence"
**Also violates**: Lines 145-170 - "Context as Constitutive of Meaning"

**Violations**:

1. **`src/domain/services/domain_augmentation_service.py:149-175`**
2. **`src/domain/services/procedural_memory_service.py:218-261`**

Both use hardcoded keyword lists:

```python
# VIOLATION: Keyword-based intent, same for all contexts
if any(word in query_lower for word in ["invoice", "payment", "owe"]):
    return "financial"
elif any(word in query_lower for word in ["work order", "technician"]):
    return "work_orders"
# ... more hardcoded patterns
```

**Problem - Context Insensitivity**:

| Query | Intent (Current) | Intent (Should Be) |
|-------|------------------|-------------------|
| "Can we invoice them?" | financial ✓ | financial ✓ |
| "They sent an invoice" | financial ✗ | notification/update |
| "Invoice format is wrong" | financial ✗ | issue/complaint |
| "We owe them an invoice" | financial ✓ | obligation/task |

Keywords match text, not meaning. Violates "Context as Constitutive of Meaning".

**From VISION.md lines 145-155**:
> "The question 'Is this ready?' has no meaning without context... Retrieval is **reconstructing the minimal context necessary for meaning to emerge**"

**Vision-Aligned Solution - LLM Tool Calling**:

Instead of classifying intent, give LLM tools and let it reason about what data to fetch.

```python
# Phase 2: Replace intent classification with LLM tool calling
# From docs/implementation/SINGLE_SHOT_LLM_APPROACH.md

# Define tools for data access
tools = [
    {
        "name": "get_invoices",
        "description": "Get invoices for a customer with optional status filter",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "status": {"type": "string", "enum": ["open", "paid", "overdue", "all"]}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_work_orders",
        "description": "Get work orders for a customer with optional status filter",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "in_progress", "done", "all"]}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "traverse_order_chain",
        "description": "Follow relationships from customer through sales orders, work orders, to invoices. Returns complete chain with statuses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "include_history": {"type": "boolean", "description": "Include completed orders"}
            },
            "required": ["customer_id"]
        }
    }
    # ... more domain-specific tools
]

# LLM decides what to fetch based on understanding, not keywords
response = await llm.messages.create(
    model="claude-haiku-4-5",  # Fast, supports tool use
    messages=[{
        "role": "user",
        "content": query  # "Can we invoice Gai Media?"
    }],
    tools=tools,
    max_tokens=1024
)

# LLM reasons:
# "To answer if we can invoice, I need to check:
#  1. Active sales orders (get_work_orders)
#  2. Work completion status (in work order response)
#  3. Existing invoices (get_invoices)
# Let me call these tools..."

# LLM calls appropriate tools based on semantic understanding
# NO keywords, NO intent classification
# Pure reasoning about what data is needed
```

**Why This Is Vision-Aligned**:

1. **Context-Aware**: LLM understands "can we invoice" vs "they sent an invoice" are different intents despite keyword overlap

2. **Ontology-Aware**: LLM can see relationship schema and traverse graph (customer → order → work_order → invoice)

3. **Emergent**: Adding new tools automatically makes them available - no code changes needed

4. **Zero Latency Penalty**: Tool calls execute in parallel with LLM processing (~500ms total, same as current approach)

5. **Learning**: Track which tool combinations work for which queries, adjust tool descriptions

---

## Part III: Systemic Architectural Violations

### S1. Missing Feedback Loop Infrastructure (Foundational Issue)

**Vision Principle Violated**: VISION.md lines 466-486, 507-522

**Core Problem**: The vision describes a **learning system**, but the architecture has **no feedback loops**.

From VISION.md lines 466-476:
> "Intelligence isn't programmed - it **emerges from interaction of simple mechanisms**:
> 1. Extract entities and facts
> 2. Store with embeddings, confidence, provenance
> 3. Decay based on age
> 4. Retrieve using multi-signal relevance
> 5. **Augment with authoritative DB facts**
> 6. Consolidate periodically
> 7. **Learn which retrieval patterns work**  ← MISSING IN CODE"

**Step 7 is completely missing**. There's no infrastructure to track:

- Which memories were useful vs useless
- Which queries succeeded vs failed
- Which entity resolutions were correct vs wrong
- Which conflicts were resolved well vs poorly
- Which consolidations improved retrieval vs degraded it

**Architectural Gap**:

```
Current Architecture:
┌─────────────────────────────────────────────────────┐
│ Request → Process → Store → Retrieve → Respond     │
│                         ↓                           │
│                    (no feedback)                    │
└─────────────────────────────────────────────────────┘

Vision Architecture:
┌─────────────────────────────────────────────────────┐
│ Request → Process → Store → Retrieve → Respond     │
│     ↑                                     ↓         │
│     └──────── Feedback Loop ──────────────┘         │
│          (track outcomes, learn, adapt)             │
└─────────────────────────────────────────────────────┘
```

**Vision-Aligned Solution - Add Feedback Infrastructure**:

```python
# New Port: src/domain/ports/feedback_repository.py
class IFeedbackRepository(ABC):
    """Repository for tracking system outcomes for learning.

    Philosophy: Can't learn without observing outcomes.
    """

    @abstractmethod
    async def log_retrieval_outcome(
        self,
        user_id: str,
        query: str,
        strategy: str,
        retrieved_memories: list[dict],
        was_useful: bool,
        usefulness_signals: dict,
    ) -> None:
        """Track whether retrieved memories contributed to response."""
        pass

    @abstractmethod
    async def log_entity_resolution_outcome(
        self,
        mention: str,
        resolved_entity_id: str,
        method: str,
        confidence: float,
        was_correct: bool,  # User confirmed or corrected?
    ) -> None:
        """Track entity resolution accuracy."""
        pass

    @abstractmethod
    async def log_conflict_resolution_outcome(
        self,
        conflict_id: int,
        resolution_strategy: str,
        outcome_quality: float,
    ) -> None:
        """Track conflict resolution effectiveness."""
        pass

    @abstractmethod
    async def log_consolidation_outcome(
        self,
        summary_id: int,
        memories_consolidated: list[int],
        retrieval_improvement: float,  # Did it help future retrievals?
    ) -> None:
        """Track consolidation effectiveness."""
        pass

# New Service: src/domain/services/learning_service.py
class LearningService:
    """Meta-learning service that learns from tracked outcomes.

    Philosophy: System improves by observing what works.
    """

    async def learn_retrieval_weights(self, user_id: str) -> dict[str, float]:
        """Learn optimal retrieval weights for user."""
        # Analyze feedback repository
        # Find correlations between signal weights and useful retrievals
        # Return personalized weights

    async def learn_decay_rates(self) -> dict[str, float]:
        """Learn predicate-specific decay rates."""
        # Analyze mutation history
        # Calculate median stability periods
        # Return learned decay rates per predicate

    async def learn_consolidation_thresholds(self) -> dict[str, int]:
        """Learn when consolidation helps vs hurts."""
        # Analyze consolidation outcomes
        # Find optimal thresholds per scope type
        # Return learned thresholds
```

**Integration Points**:

```python
# In process_chat_message.py - Track entity resolution outcomes
resolved_entities = await entity_resolution_service.resolve_entities(mentions)

# Track outcomes for learning
for entity in resolved_entities:
    await feedback_tracker.log_entity_resolution(
        mention=entity.mention_text,
        resolved_id=entity.entity_id,
        method=entity.method,
        confidence=entity.confidence,
        # Will be updated later if user corrects
    )

# In retrieval pipeline - Track usefulness
retrieved_memories = await retrieval_service.retrieve(query_context)

# Later, after response generation:
memories_used_in_response = [m.memory_id for m in memories if m.cited]

await feedback_tracker.log_retrieval_outcome(
    user_id=user_id,
    query=query,
    strategy=query_context.strategy,
    retrieved_memories=retrieved_memories,
    was_useful=len(memories_used_in_response) > 0,
    usefulness_signals={
        "cited_count": len(memories_used_in_response),
        "top_5_used": memories_used_in_response[:5],
        "user_feedback": explicit_feedback  # if available
    }
)
```

**Emergent Properties with Feedback Loops**:

- System learns which entity resolution methods work best for which types of mentions
- System adapts retrieval weights based on what actually proves useful
- System discovers which predicates are stable vs volatile
- System improves consolidation timing based on retrieval impact
- **Intelligence emerges from feedback, not programming**

---

### S2. No Meta-Learning (Learning About Learning)

**Vision Principle Violated**: VISION.md lines 221-223

**Quote**:
> "↓ [Meta-Learning]
> Domain knowledge: 'Delivery preferences are stable (low change frequency), validate if >90 days old'"

**Problem**: System doesn't learn **about** learning. No tracking of:

- Which learning mechanisms work (Does alias learning help? By how much?)
- Which calibration approaches succeed (Are learned weights better than defaults?)
- Optimal learning rates (How much data before switching to learned model?)
- Meta-parameters (Decay rate for decay rates?)

**Vision-Aligned Solution**:

```python
class MetaLearningService:
    """Learn about the learning process itself.

    Philosophy: Second-order learning - learning how to learn better.
    """

    async def evaluate_learning_mechanism(
        self,
        mechanism: str,  # "alias_learning", "weight_personalization", etc.
        metric: str = "accuracy_improvement"
    ) -> float:
        """Measure effectiveness of a learning mechanism.

        Returns improvement over baseline (e.g., +15% accuracy).
        """
        # Compare periods with/without mechanism
        before_performance = await self.get_baseline_performance(mechanism)
        after_performance = await self.get_current_performance(mechanism)

        improvement = (after_performance - before_performance) / before_performance

        logger.info(
            "learning_mechanism_evaluation",
            mechanism=mechanism,
            before=before_performance,
            after=after_performance,
            improvement_pct=improvement * 100
        )

        return improvement

    async def optimize_learning_thresholds(self) -> dict[str, int]:
        """Learn optimal data thresholds for switching to learned models.

        Example: At what N should we switch from default weights to learned weights?
        """
        thresholds = {}

        for mechanism in ["weight_personalization", "decay_rate_learning"]:
            # Find inflection point where learned model beats default
            sample_sizes = [10, 20, 50, 100, 200, 500]
            performance_by_size = {}

            for size in sample_sizes:
                # Evaluate performance with N samples
                perf = await self.evaluate_at_sample_size(mechanism, size)
                performance_by_size[size] = perf

            # Find minimum N where learned beats default by >10%
            for size, perf in sorted(performance_by_size.items()):
                if perf > baseline * 1.10:  # 10% improvement threshold
                    thresholds[mechanism] = size
                    break

        return thresholds

    async def detect_learning_plateaus(self) -> list[str]:
        """Identify learning mechanisms that have plateaued.

        Returns list of mechanisms to investigate or redesign.
        """
        plateaued = []

        for mechanism in self.active_mechanisms:
            recent_improvements = await self.get_recent_trend(mechanism, days=30)

            # If no improvement in 30 days, mark as plateaued
            if max(recent_improvements) - min(recent_improvements) < 0.01:  # <1% variation
                plateaued.append(mechanism)
                logger.warning(
                    "learning_plateau_detected",
                    mechanism=mechanism,
                    recent_improvements=recent_improvements
                )

        return plateaued
```

**Emergent Meta-Knowledge**:
- "Alias learning helps most for frequently used entities (15% accuracy boost)"
- "Weight personalization requires 50+ queries to beat defaults"
- "Decay rate learning has plateaued - need better mutation tracking"

This is **learning about learning** - the system observes its own learning process and optimizes it.

---

### S3. Hardcoded Consolidation Confidence (No Quality Measurement)

**Vision Principle Violated**: Lines 228-243 - "Confidence as Epistemic State"

**Violation**: `src/domain/services/consolidation_service.py:564, 677`

```python
# Line 564 - ARBITRARY VALUE
confidence=0.8,  # Base confidence for LLM synthesis

# Line 677 - ARBITRARY VALUE
confidence=0.6,  # Lower confidence for fallback
```

**Problem**: Confidence should reflect **actual synthesis quality**, not arbitrary values.

From VISION.md lines 228-243:
> "Confidence isn't arbitrary. Confidence reflects **epistemic justification**... Confidence should be **calibrated** - over time, learn what confidence levels actually predict accuracy."

**Deeper Issue**: No measurement of synthesis quality means no way to calibrate confidence.

**Vision-Aligned Solution**:

```python
class ConsolidationQualityEvaluator:
    """Measure consolidation synthesis quality for confidence calibration.

    Philosophy: Confidence should reflect actual accuracy.
    """

    async def evaluate_synthesis_quality(
        self,
        summary: MemorySummary,
        source_memories: list[MemoryCandidate],
    ) -> float:
        """Calculate quality score for LLM synthesis.

        Returns confidence score [0-1] based on multiple quality signals.
        """
        quality_signals = {}

        # Signal 1: Fact extraction completeness
        # Did summary capture key facts from source memories?
        key_facts_in_summary = len(summary.key_facts)
        high_conf_sources = [m for m in source_memories if m.confidence > 0.7]
        completeness = min(1.0, key_facts_in_summary / max(len(high_conf_sources), 1))
        quality_signals["completeness"] = completeness

        # Signal 2: Consistency check
        # Does summary contradict any source memories?
        contradictions = await self.detect_contradictions(summary, source_memories)
        consistency = 1.0 - (len(contradictions) * 0.1)  # Penalty per contradiction
        quality_signals["consistency"] = max(0.0, consistency)

        # Signal 3: Reinforcement alignment
        # Did summary identify highly reinforced facts?
        reinforced_facts_captured = 0
        for mem in source_memories:
            if mem.reinforcement_count and mem.reinforcement_count >= 3:
                # Check if this fact appears in summary
                if await self.fact_in_summary(mem, summary):
                    reinforced_facts_captured += 1

        reinforcement_alignment = reinforced_facts_captured / max(len([m for m in source_memories if m.reinforcement_count >= 3]), 1)
        quality_signals["reinforcement_alignment"] = reinforcement_alignment

        # Signal 4: Temporal coherence
        # Did summary respect temporal ordering of facts?
        temporal_coherence = await self.check_temporal_coherence(summary, source_memories)
        quality_signals["temporal_coherence"] = temporal_coherence

        # Weighted combination
        weights = {
            "completeness": 0.3,
            "consistency": 0.4,  # Most important - avoid contradictions
            "reinforcement_alignment": 0.2,
            "temporal_coherence": 0.1
        }

        quality_score = sum(
            quality_signals[signal] * weight
            for signal, weight in weights.items()
        )

        # Cap at MAX_CONFIDENCE (epistemic humility)
        quality_score = min(quality_score, heuristics.MAX_CONFIDENCE)

        logger.info(
            "consolidation_quality_evaluated",
            summary_id=summary.summary_id,
            quality_score=quality_score,
            signals=quality_signals
        )

        return quality_score

# Usage in ConsolidationService
async def _store_summary(self, user_id, scope, summary_data):
    summary = MemorySummary(
        user_id=user_id,
        scope_type=scope.type,
        scope_identifier=scope.identifier,
        summary_text=summary_data.summary_text,
        key_facts=summary_data.key_facts,
        # ... other fields

        # CALCULATE confidence from quality, don't hardcode
        confidence=await self.quality_evaluator.evaluate_synthesis_quality(
            summary=summary,
            source_memories=source_memories
        )
    )

    # Now confidence reflects actual synthesis quality
```

**Calibration Loop**:

```python
# Track synthesis confidence vs actual usefulness
await feedback_tracker.log_consolidation_outcome(
    summary_id=summary.summary_id,
    predicted_quality=summary.confidence,
    actual_usefulness=measured_retrieval_improvement,  # Did it help?
)

# Periodically calibrate quality evaluation weights
async def calibrate_quality_evaluator():
    """Learn which quality signals best predict usefulness."""
    outcomes = await feedback_tracker.get_consolidation_outcomes(limit=100)

    # Find which signals correlated with actual usefulness
    signal_correlations = compute_correlations(outcomes)

    # Update quality evaluation weights
    new_weights = optimize_weights_for_prediction(signal_correlations)

    quality_evaluator.update_weights(new_weights)
```

**Now confidence is calibrated**: If consolidations with confidence=0.8 are actually only 60% useful, the calibration process discovers this and adjusts quality evaluation to be more conservative.

---

## Part IV: Philosophical Synthesis

### The Core Misalignment: Programmed vs Emergent Intelligence

**Vision Philosophy** (VISION.md lines 466-486):

> "Intelligence isn't programmed - it **emerges from interaction of simple mechanisms**...
> These simple rules, applied consistently, yield **emergent intelligent behavior**:
> - Remembers what matters, forgets what doesn't
> - Gets more confident about stable facts
> - Questions aged information
> - Learns entity aliases from usage
> - Surfaces relevant context automatically
> - **Improves disambiguation over time**
> - **Builds domain understanding from patterns**
> The system becomes **more than the sum of its parts**."

**Current Implementation**: Intelligence is **programmed**:

- Retrieval weights: programmed (hardcoded in heuristics.py)
- Intent classification: programmed (keyword lists)
- Query dispatch: programmed (if/elif chains)
- Conflict resolution: programmed (fixed priority order)
- Decay rates: programmed (same for all fact types)
- Consolidation timing: programmed (static thresholds)

**The Gap**: Vision says intelligence **emerges from usage**. Code says intelligence is **encoded in constants**.

**Root Cause**: Missing feedback loops. Can't have emergence without:
1. Observation of outcomes
2. Learning from patterns
3. Adaptation based on learning
4. Meta-learning about learning

---

### The Path to Emergence: Three-Phase Transformation

**Phase 0: Critical Fixes** (1-2 hours)
- Fix all `confidence=1.0` → `MAX_CONFIDENCE` (0.95)
- Fix brittle string matching → semantic understanding
- **Philosophy**: Restore epistemic humility

**Phase 1: Add Feedback Infrastructure** (8-12 hours)
- Create `IFeedbackRepository` port
- Implement `FeedbackTracker` service
- Add outcome logging to all decision points:
  - Entity resolution outcomes
  - Retrieval usefulness
  - Conflict resolution effectiveness
  - Consolidation quality
- **Philosophy**: Enable observation (can't learn without data)

**Phase 2: Implement Learning** (16-24 hours)
- Create `LearningService` that analyzes feedback
- Learn per-user retrieval weights
- Learn per-predicate decay rates
- Learn conflict resolution strategies
- Calibrate consolidation quality evaluation
- A/B test learned vs default parameters
- **Philosophy**: Intelligence begins to emerge from patterns

**Phase 3: Meta-Learning & Continuous Improvement** (Future)
- Create `MetaLearningService`
- Evaluate learning mechanisms themselves
- Optimize learning thresholds
- Detect plateaus and investigate
- Automatic model updates in production
- **Philosophy**: System that learns how to learn better

---

## Part V: Detailed Solutions by Component

### Solution 1: Vision-Aligned Retrieval (Adaptive Weights)

**Current**: Static weights for all users
**Vision**: Per-user adaptive weights

```python
# Complete implementation of adaptive retrieval

class AdaptiveRetrievalService:
    """Retrieval service with user-adaptive weighting.

    Philosophy: Learn what each user cares about from usage.
    """

    def __init__(
        self,
        candidate_generator: CandidateGenerator,
        scorer: MultiSignalScorer,
        feedback_tracker: RetrievalFeedbackTracker,
        learning_service: LearningService,
    ):
        self.candidate_generator = candidate_generator
        self.scorer = scorer
        self.feedback_tracker = feedback_tracker
        self.learning_service = learning_service

    async def retrieve(
        self,
        query_context: QueryContext,
    ) -> list[ScoredMemory]:
        """Retrieve memories with user-adaptive weighting."""

        # Get personalized weights for this user
        user_weights = await self.get_user_weights(query_context.user_id)

        # Update query context with personalized weights
        query_context.weights = user_weights

        # Generate candidates
        candidates = await self.candidate_generator.generate_candidates(query_context)

        # Score with personalized weights
        scored = await self.scorer.score_candidates(candidates, query_context)

        # Track for learning
        await self.feedback_tracker.track_retrieval(
            user_id=query_context.user_id,
            query=query_context.query_text,
            weights_used=user_weights,
            retrieved=scored[:10]  # Top 10
        )

        return scored

    async def get_user_weights(self, user_id: str) -> dict[str, float]:
        """Get personalized weights for user.

        Falls back to defaults if insufficient data.
        """
        # Try to load learned weights
        learned = await self.learning_service.get_learned_weights(user_id)

        if learned and learned["confidence"] > 0.7:  # Sufficient data
            logger.info(
                "using_learned_weights",
                user_id=user_id,
                sample_size=learned["sample_size"],
                weights=learned["weights"]
            )
            return learned["weights"]
        else:
            # Fall back to defaults
            logger.debug(
                "using_default_weights",
                user_id=user_id,
                reason="insufficient_data" if learned else "no_learning_yet"
            )
            return heuristics.RETRIEVAL_STRATEGY_WEIGHTS["exploratory"]

    async def provide_feedback(
        self,
        retrieval_id: str,
        was_useful: bool,
        usefulness_signals: dict,
    ):
        """Record feedback on retrieval usefulness.

        Enables learning from outcomes.
        """
        await self.feedback_tracker.record_outcome(
            retrieval_id=retrieval_id,
            was_useful=was_useful,
            usefulness_signals=usefulness_signals
        )

        # Trigger re-learning if enough new data
        await self.learning_service.maybe_update_user_weights(user_id)
```

**Emergence**: After 50+ queries, User A who focuses on finances has weights:
```python
{
    "semantic_similarity": 0.20,
    "entity_overlap": 0.50,  # Higher! User A cares about entity relationships
    "temporal_relevance": 0.10,
    "importance": 0.15,
    "reinforcement": 0.05
}
```

User B who asks about recent events has weights:
```python
{
    "semantic_similarity": 0.25,
    "entity_overlap": 0.15,
    "temporal_relevance": 0.45,  # Higher! User B cares about recency
    "importance": 0.10,
    "reinforcement": 0.05
}
```

**Intelligence emerged** from observing what works for each user.

---

### Solution 2: LLM Tool Calling (Replace Intent Classification)

**Current**: Keywords → Intent → Hardcoded queries
**Vision**: LLM reasoning → Dynamic tool selection

See `docs/implementation/SINGLE_SHOT_LLM_APPROACH.md` for complete implementation.

**Key Advantages**:
1. **Context-aware**: Understands semantic meaning, not keywords
2. **Ontology-aware**: Can traverse relationship graph
3. **Zero latency penalty**: Tools execute in parallel (~500ms total)
4. **Emergent**: Adding tools makes them available automatically
5. **Vision-aligned**: "Intelligence emerges from simple mechanisms" - LLM + tools = emergent query planning

---

### Solution 3: Quality-Based Consolidation Confidence

**Current**: Hardcoded confidence values
**Vision**: Measured quality → Calibrated confidence

```python
# Integration into consolidation service
async def consolidate_entity(self, user_id, entity_id):
    # ... fetch memories, synthesize summary ...

    # Evaluate synthesis quality (NOT hardcoded confidence)
    quality_score = await self.quality_evaluator.evaluate_synthesis_quality(
        summary=summary,
        source_memories=episodic + semantic
    )

    summary.confidence = quality_score  # Reflects actual quality

    # Store
    stored = await self._summary_repo.create(summary)

    # Track for calibration
    await self.feedback_tracker.log_consolidation(
        summary_id=stored.summary_id,
        predicted_quality=quality_score,
        # Will be updated later with actual usefulness
    )

    return stored

# Later, when summary is used in retrieval
async def track_consolidation_usefulness(summary_id, retrieval_improvement):
    """Record whether consolidation actually helped."""
    await feedback_tracker.update_consolidation_outcome(
        summary_id=summary_id,
        actual_usefulness=retrieval_improvement
    )

    # Triggers calibration if enough data
    await calibration_service.maybe_recalibrate_quality_evaluation()
```

---

## Part VI: Measurement & Validation

### How to Verify Vision Alignment

**Principle 1: Epistemic Humility**
- ✅ `grep -r "confidence.*=.*1\.0" src/` returns zero matches
- ✅ MAX_CONFIDENCE = 0.95 enforced everywhere
- ✅ No hard string matching (all use semantic equivalence)
- ✅ Uncertainty made explicit in responses

**Principle 2: Learning from Usage**
- ✅ Feedback repository exists and is populated
- ✅ All decision points log outcomes
- ✅ Learning service analyzes feedback periodically
- ✅ Learned parameters outperform defaults (measure A/B test)

**Principle 3: Emergent Intelligence**
- ✅ User weights adapt based on usage (measure divergence from defaults)
- ✅ Decay rates learned per predicate (measure variance)
- ✅ Conflict strategies learned per context (measure strategy distribution)
- ✅ System performance improves over time (measure trend)

**Principle 4: Context-Aware**
- ✅ LLM tool calling replaces keyword matching
- ✅ Same query → different tools based on context
- ✅ Multi-hop graph traversal enabled

**Principle 5: Explainability**
- ✅ Every decision has provenance
- ✅ Every retrieval shows signal breakdown
- ✅ Every response cites sources

---

## Part VII: Migration Strategy

### Phase 0: Critical Fixes (Day 1)

**Epistemic Humility Restoration**:
```bash
# Fix root constant
sed -i 's/CONFIDENCE_EXACT_MATCH = 1.0/CONFIDENCE_EXACT_MATCH = 0.95/' src/config/heuristics.py

# Fix all uses
sed -i 's/confidence=1\.0/confidence=heuristics.MAX_CONFIDENCE/g' src/**/*.py
sed -i 's/confidence_diff=1\.0/confidence_diff=heuristics.MAX_CONFIDENCE/g' src/**/*.py

# Run tests
poetry run pytest tests/ -v
```

**Brittle String Fix**:
```python
# Update both LLM services
# Replace: if response_text.upper() == "UNKNOWN":
# With: if indicates_uncertainty(response_text):
```

**Verification**:
```bash
grep -r "confidence.*=.*1\.0" src/  # Should return nothing
grep -r "\.upper\(\).*==" src/  # Should return nothing in LLM services
```

---

### Phase 1: Feedback Infrastructure (Week 1)

1. **Create feedback schema** (Day 1)
   - `feedback_events` table
   - Columns: event_type, context, outcome, timestamp

2. **Implement FeedbackRepository** (Day 2)
   - PostgreSQL adapter
   - Write methods for all event types

3. **Add tracking calls** (Days 3-4)
   - Entity resolution outcomes
   - Retrieval usefulness
   - Conflict resolution effectiveness
   - Consolidation quality

4. **Verification** (Day 5)
   - Run system for 24 hours
   - Verify feedback events populating
   - Check data quality

---

### Phase 2: Learning Implementation (Weeks 2-3)

1. **Implement LearningService** (Week 2)
   - Learn user retrieval weights
   - Learn predicate decay rates
   - Learn conflict strategies
   - Calibrate consolidation quality

2. **A/B Testing Framework** (Week 3)
   - 50% users get learned parameters
   - 50% users get defaults
   - Measure: accuracy, usefulness, user satisfaction

3. **Gradual Rollout** (Week 3)
   - If learned params win: 100% rollout
   - If defaults win: investigate and iterate

---

### Phase 3: LLM Tool Calling (Weeks 4-5)

1. **Implement Tool Executor** (Week 4)
   - Define domain tools
   - Implement tool handlers
   - Test with Claude Haiku 4.5

2. **Parallel Running** (Week 4)
   - Log both approaches
   - Compare: accuracy, latency, cost

3. **Cutover** (Week 5)
   - Switch to tool calling if metrics better
   - Remove keyword classification

---

## Part VIII: Success Criteria

### Quantitative Targets

**Phase 0 Success**:
- Zero `confidence=1.0` in codebase
- All LLM responses handled semantically
- Tests pass

**Phase 1 Success**:
- Feedback events logging at 1000+/day
- All decision points tracked
- Data quality >95% (valid, non-null)

**Phase 2 Success**:
- Learned weights outperform defaults by >10%
- Learned decay rates show variance by predicate
- User satisfaction improves (measure via feedback)

**Phase 3 Success**:
- LLM tool calling accuracy >95%
- Latency <800ms p95
- Cost increase <20% (should be ~50% but optimize)

### Qualitative Indicators (Vision-Aligned)

From VISION.md lines 169-180:
> "After extended use, if the system were removed, users would feel like they **lost a knowledgeable colleague**"

Indicators:
- Users stop re-explaining preferences (system remembers)
- Disambiguation requests decrease (system learns)
- Users trust responses (explainability builds confidence)
- Conversations feel continuous (not starting fresh)
- Users correct system comfortably (collaborative refinement)

---

## Conclusion: The Philosophical Essence

The gap between current code and vision isn't about features - it's about **philosophy of intelligence**.

**Current Philosophy**: Intelligence is encoding expert knowledge into rules
**Vision Philosophy**: Intelligence emerges from observation + learning

**Current Approach**: Program what to do in each situation
**Vision Approach**: Provide mechanisms, let patterns emerge from usage

**Current System**: Static, configured
**Vision System**: Adaptive, self-improving

The **good news**: Architecture is sound (hexagonal, typed, testable)

The **work needed**: Add feedback loops so intelligence can emerge

The **transformation**: From database with rules → Learning cognitive partner

**From VISION.md closing** (lines 204-219):
> "Memory is the transformation of experience into understanding...
> An LLM without memory is a pattern matcher - impressive but limited.
> An LLM with memory becomes something qualitatively different: a **cognitive entity** that learns from experience, adapts to context, builds understanding over time...
> This system is about **giving an LLM the foundation of intelligence itself: memory that learns, adapts, and evolves**."

That is the vision. The path is clear. The architecture is ready. Now we add the learning loops that transform programmed rules into emergent intelligence.

---

## Appendix: All Violations Cross-Reference

| ID | File:Line | Violation | Principle | Severity |
|----|-----------|-----------|-----------|----------|
| C1.1 | heuristics.py:39 | confidence=1.0 | Epistemic Humility | Critical |
| C1.2 | process_chat_message.py:390 | confidence=1.0 | Epistemic Humility | Critical |
| C1.3 | debug_trace_service.py:149 | confidence=1.0 | Epistemic Humility | Critical |
| C1.4 | scenario_loader.py:492 | confidence=1.0 | Epistemic Humility | Critical |
| C1.5 | conflict_detection_service.py:374 | confidence=1.0 | Epistemic Humility | Critical |
| C2.1 | anthropic_llm_service.py:451 | Hard string match | Context/Humility | Critical |
| C2.2 | openai_llm_service.py:444 | Hard string match | Context/Humility | Critical |
| H1.1 | heuristics.py:62-95 | Static weights | Learning/Adaptive | High |
| H2.1 | heuristics.py:16 | Static decay rate | Learning/Adaptive | High |
| H3.1 | conflict_detection_service.py:224 | No resolution feedback | Learning | High |
| H4.1 | domain_augmentation_service.py:149 | Hardcoded keywords | Context/Emergent | High |
| H4.2 | procedural_memory_service.py:218 | Hardcoded keywords | Context/Emergent | High |
| S1 | Architecture-wide | No feedback loops | Emergent Intelligence | Systemic |
| S2 | Architecture-wide | No meta-learning | Learning About Learning | Systemic |
| S3.1 | consolidation_service.py:564 | Hardcoded confidence | Confidence Calibration | Medium |
| S3.2 | consolidation_service.py:677 | Hardcoded confidence | Confidence Calibration | Medium |

**Total**: 16 specific violations + 2 systemic gaps

---

**Generated**: 2025-10-16
**Author**: Deep codebase analysis against VISION.md philosophical principles
**Next**: Implement Phase 0 critical fixes, then build feedback infrastructure for emergence
