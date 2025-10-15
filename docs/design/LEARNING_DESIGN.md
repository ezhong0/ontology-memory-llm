# Learning and Adaptation System

## Vision Alignment

From VISION.md:
> "A memory system that doesn't learn is like a filing cabinet—useful for storage, but not for intelligence. The system must recognize patterns, refine its understanding, and adapt to each user's unique context and needs."

The learning system embodies **graceful evolution**: the system improves over time through pattern recognition and adaptation.

**Design Philosophy Applied**:
- **Phasing justified**: "Learning features require data to learn from" (can't optimize what you haven't observed)
- **Phase 1**: Rule-based operations + data collection
- **Phase 2/3**: Pattern recognition and adaptive learning
- **This document is 100% Phase 2/3 features**

---

## The Learning Paradox

**Central tension**: We need data to learn, but we need to function before we have data.

**Resolution**: Three-phase approach

```
Phase 1 (Essential): Rule-Based Foundation
├─ Fixed extraction heuristics
├─ Fixed retrieval weights
├─ Fixed confidence thresholds
└─ DATA COLLECTION: Log all operations for future learning

Phase 2 (Enhancements): Pattern Recognition
├─ Analyze collected data (50-100+ samples)
├─ Learn which patterns work per user
├─ Adjust weights and thresholds
└─ DATA COLLECTION: Log feedback quality

Phase 3 (Advanced): Adaptive Learning
├─ Continuous online learning
├─ Meta-memories (learning about learning)
├─ Cross-user pattern transfer
└─ Unlearning obsolete patterns
```

**This document describes Phase 2/3 architecture** - how to build learning once you have data.

## What Can the System Learn?

### Six Learning Dimensions

1. **Extraction Quality**: Which facts are worth remembering? Which are noise?
2. **Retrieval Relevance**: Which memories are actually useful for which queries?
3. **Entity Resolution**: Which disambiguation patterns work for this user?
4. **Importance Calibration**: What makes a memory important to this user?
5. **Confidence Tuning**: How quickly should confidence decay? When to validate?
6. **Procedural Generalization**: Which action patterns are recurring? Which are one-off?

## Dimension 1: Extraction Quality Learning

### The Problem

Initial extraction (Phase 1) uses heuristics:
```python
# Phase 1: Rule-based
if "always" in utterance or "usually" in utterance:
    extract_as_procedural_memory()
elif has_entity_and_predicate(utterance):
    extract_as_semantic_memory()
```

**Issues with rule-based extraction**:
- ❌ Extracts too much noise: "I always use Chrome browser" → procedural memory (irrelevant)
- ❌ Misses nuanced patterns: "When customers complain, I typically..." → should be procedural
- ❌ Can't adapt to user's domain: "Customer" means different things in different businesses

### Learning Approach: Extraction Pattern Mining

**Data needed** (Phase 2: Start collecting):
```sql
CREATE TABLE app.extraction_feedback (
  feedback_id BIGSERIAL PRIMARY KEY,
  extracted_memory_id BIGINT NOT NULL,
  memory_type TEXT NOT NULL,
  extraction_pattern TEXT NOT NULL,  -- Which rule/heuristic triggered extraction
  was_useful BOOLEAN,  -- Did this memory get retrieved and used?
  user_correction JSONB,  -- Did user correct/delete this memory?
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Learning algorithm** (Phase 3: Apply learning):
```python
async def learn_extraction_patterns(user_id: str, min_samples: int = 50):
    """
    Analyze extraction feedback to improve extraction rules.

    After we have 50+ feedback samples, learn which patterns work.
    """
    # Query feedback data
    pattern_stats = await db.fetch("""
        SELECT
            extraction_pattern,
            memory_type,
            COUNT(*) AS total_extracted,
            SUM(CASE WHEN was_useful THEN 1 ELSE 0 END) AS useful_count,
            SUM(CASE WHEN user_correction IS NOT NULL THEN 1 ELSE 0 END) AS correction_count
        FROM app.extraction_feedback
        WHERE user_id = $1
        GROUP BY extraction_pattern, memory_type
        HAVING COUNT(*) >= 10
    """, user_id)

    learned_patterns = []
    for pattern in pattern_stats:
        precision = pattern.useful_count / pattern.total_extracted
        error_rate = pattern.correction_count / pattern.total_extracted

        # Learn pattern quality
        if precision > 0.7 and error_rate < 0.1:
            # Good pattern: boost confidence
            learned_patterns.append({
                'pattern': pattern.extraction_pattern,
                'memory_type': pattern.memory_type,
                'confidence_multiplier': 1.2,
                'action': 'boost'
            })
        elif precision < 0.3 or error_rate > 0.3:
            # Bad pattern: suppress or require higher threshold
            learned_patterns.append({
                'pattern': pattern.extraction_pattern,
                'memory_type': pattern.memory_type,
                'confidence_multiplier': 0.5,
                'action': 'suppress'
            })

    # Store learned patterns
    await store_extraction_patterns(user_id, learned_patterns)
    return learned_patterns
```

**Feedback collection** (Phase 2):
```python
async def collect_extraction_feedback(memory_id: int, memory_type: str):
    """
    Track whether extracted memories are useful.
    """
    # Implicit feedback 1: Was memory retrieved?
    retrieval_count = await count_memory_retrievals(memory_id)

    # Implicit feedback 2: Was memory used in LLM response?
    usage_count = await count_memory_usage(memory_id)

    # Implicit feedback 3: Did user correct/delete memory?
    user_corrections = await get_user_corrections(memory_id)

    # Compute usefulness
    was_useful = (
        retrieval_count > 0 and
        usage_count > 0 and
        len(user_corrections) == 0
    )

    # Record feedback
    await db.execute("""
        INSERT INTO app.extraction_feedback (
            extracted_memory_id, memory_type, extraction_pattern, was_useful
        ) VALUES ($1, $2, $3, $4)
    """, memory_id, memory_type, get_extraction_pattern(memory_id), was_useful)
```

## Dimension 2: Retrieval Relevance Learning

### The Problem

Phase 1 retrieval uses fixed weights:
```python
STRATEGY_WEIGHTS = {
    'semantic_similarity': 0.25,
    'entity_overlap': 0.40,
    'temporal_relevance': 0.20,
    'importance': 0.10,
    'reinforcement': 0.05,
}
```

**Questions Phase 1 can't answer**:
- Are these the right weights for this user?
- Do different query types need different weights?
- Which signals actually predict useful memories?

### Learning Approach: Retrieval Weight Optimization

**Data needed** (Phase 2):
```sql
CREATE TABLE app.retrieval_log (
  log_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  query TEXT NOT NULL,
  query_type TEXT NOT NULL,
  memory_id BIGINT NOT NULL,
  memory_type TEXT NOT NULL,
  rank INT NOT NULL,  -- Position in retrieved results (1 = top)
  score REAL NOT NULL,
  signal_scores JSONB NOT NULL,  -- Individual signal scores
  was_used_in_response BOOLEAN,
  user_feedback TEXT,  -- 'helpful', 'not_helpful', 'irrelevant'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Learning algorithm** (Phase 3):
```python
async def optimize_retrieval_weights(user_id: str, query_type: str):
    """
    Learn optimal retrieval weights using supervised learning.

    Features: Signal scores (semantic_similarity, entity_overlap, etc.)
    Labels: was_used_in_response (binary classification)
    Model: Logistic regression or gradient boosted trees
    """
    # Fetch training data
    training_data = await db.fetch("""
        SELECT
            signal_scores,
            was_used_in_response AS label
        FROM app.retrieval_log
        WHERE user_id = $1 AND query_type = $2
    """, user_id, query_type)

    if len(training_data) < 100:
        # Not enough data yet, use defaults
        return STRATEGY_WEIGHTS[query_type]

    # Prepare features and labels
    X = np.array([row.signal_scores for row in training_data])
    y = np.array([row.label for row in training_data])

    # Train logistic regression
    from sklearn.linear_model import LogisticRegression
    model = LogisticRegression()
    model.fit(X, y)

    # Extract learned weights (coefficients)
    learned_weights = {
        'semantic_similarity': model.coef_[0][0],
        'entity_overlap': model.coef_[0][1],
        'temporal_relevance': model.coef_[0][2],
        'importance': model.coef_[0][3],
        'reinforcement': model.coef_[0][4],
    }

    # Normalize to sum to 1.0
    total = sum(abs(w) for w in learned_weights.values())
    normalized_weights = {k: abs(v) / total for k, v in learned_weights.items()}

    # Store for this user + query type
    await db.execute("""
        INSERT INTO app.learned_retrieval_weights (user_id, query_type, weights, trained_at)
        VALUES ($1, $2, $3, now())
        ON CONFLICT (user_id, query_type) DO UPDATE SET
            weights = EXCLUDED.weights,
            trained_at = EXCLUDED.trained_at
    """, user_id, query_type, jsonb.dumps(normalized_weights))

    return normalized_weights
```

**Usage** (Phase 3):
```python
async def get_retrieval_strategy(user_id: str, query_type: str):
    """
    Use learned weights if available, otherwise use defaults.
    """
    learned = await db.fetchrow("""
        SELECT weights FROM app.learned_retrieval_weights
        WHERE user_id = $1 AND query_type = $2
        AND trained_at > now() - interval '30 days'  -- Re-train monthly
    """, user_id, query_type)

    if learned:
        return learned.weights
    else:
        return STRATEGY_WEIGHTS.get(query_type, STRATEGY_WEIGHTS['exploratory'])
```

### Continuous Learning: Online Weight Updates

**Approach**: Update weights incrementally with each query, using exponential moving average:

```python
async def update_weights_online(
    user_id: str,
    query_type: str,
    signal_scores: Dict[str, float],
    was_useful: bool,
    learning_rate: float = 0.01
):
    """
    Online learning: Adjust weights based on each query result.

    Uses gradient descent to minimize prediction error.
    """
    current_weights = await get_retrieval_strategy(user_id, query_type)

    # Compute prediction error
    predicted_usefulness = sum(
        current_weights[signal] * signal_scores[signal]
        for signal in signal_scores
    )
    actual_usefulness = 1.0 if was_useful else 0.0
    error = actual_usefulness - predicted_usefulness

    # Gradient descent update
    updated_weights = {}
    for signal in current_weights:
        gradient = error * signal_scores[signal]
        updated_weights[signal] = current_weights[signal] + learning_rate * gradient

    # Normalize
    total = sum(abs(w) for w in updated_weights.values())
    normalized = {k: abs(v) / total for k, v in updated_weights.items()}

    # Store
    await update_user_retrieval_weights(user_id, query_type, normalized)
```

## Dimension 3: Entity Resolution Pattern Learning

### The Problem

User-specific disambiguation patterns:
```
User A: "the customer" usually means Acme Corp (their main account)
User B: "the customer" depends on conversation context (many customers)
User C: "the customer" → always asks for clarification (very cautious)
```

### Learning Approach: Disambiguation Strategy Personalization

**Data needed** (Phase 2):
```sql
CREATE TABLE app.disambiguation_log (
  log_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  mention_text TEXT NOT NULL,
  candidates JSONB NOT NULL,  -- Array of candidate entities with scores
  user_choice TEXT,  -- NULL if user chose "none of these"
  session_context JSONB NOT NULL,  -- Recent entities, conversation topic
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Learning algorithm** (Phase 3):
```python
async def learn_disambiguation_patterns(user_id: str):
    """
    Learn user-specific disambiguation preferences.

    Pattern examples:
    - User always chooses highest-scored candidate → increase confidence threshold
    - User often chooses 2nd or 3rd candidate → reweight signals
    - User has consistent preference for specific entity → create strong alias
    """
    # Analyze disambiguation history
    history = await db.fetch("""
        SELECT
            mention_text,
            candidates,
            user_choice,
            session_context
        FROM app.disambiguation_log
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 100
    """, user_id)

    patterns = {}

    # Pattern 1: Does user trust highest-scored candidate?
    trust_in_scoring = sum(
        1 for h in history
        if h.user_choice == h.candidates[0]['entity_id']
    ) / len(history)

    if trust_in_scoring > 0.8:
        patterns['auto_select_threshold'] = 0.65  # Lower threshold, user trusts system
    elif trust_in_scoring < 0.5:
        patterns['auto_select_threshold'] = 0.85  # Higher threshold, user doesn't trust

    # Pattern 2: Consistent entity preferences for ambiguous terms
    for mention in set(h.mention_text for h in history):
        mention_history = [h for h in history if h.mention_text == mention]
        if len(mention_history) >= 3:
            # Check if user consistently chooses same entity
            choices = [h.user_choice for h in mention_history]
            most_common = max(set(choices), key=choices.count)
            frequency = choices.count(most_common) / len(choices)

            if frequency > 0.7:
                # Create or boost alias
                await create_entity_alias(
                    canonical_entity_id=most_common,
                    alias_text=mention,
                    alias_source='learned_pattern',
                    user_id=user_id,
                    confidence=0.7 + (frequency - 0.7) * 0.5,  # 0.7 to 0.85
                    metadata={'learned_from_disambiguations': len(mention_history)}
                )

    # Pattern 3: Contextual disambiguation rules
    # If user chooses entity X when discussing topic Y, learn that pattern
    for h in history:
        if 'recent_topic' in h.session_context:
            topic = h.session_context['recent_topic']
            # Store pattern: mention + topic → entity choice
            # (Simplified; real implementation would use more sophisticated pattern matching)

    return patterns
```

## Dimension 4: Importance Calibration

### The Problem

Phase 1 uses heuristic importance scoring:
```python
def compute_initial_importance(memory) -> float:
    """Rule-based importance."""
    importance = 0.5  # Base

    if has_multiple_entities(memory):
        importance += 0.1  # Relationships are important

    if contains_preference_words(memory):
        importance += 0.15  # "prefers", "always", "never"

    if contains_strong_sentiment(memory):
        importance += 0.1  # "critical", "urgent", "problem"

    return min(1.0, importance)
```

**Question**: Does this match what the user actually finds important?

### Learning Approach: Importance Score Calibration

**Data needed** (Phase 2):
```sql
-- Implicit importance signals
CREATE TABLE app.memory_engagement (
  memory_id BIGINT NOT NULL,
  engagement_type TEXT NOT NULL,  -- 'retrieved', 'used', 'referenced', 'user_requested'
  context JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Learning algorithm** (Phase 3):
```python
async def calibrate_importance_scores(user_id: str):
    """
    Learn what makes a memory important for this user.

    Signals:
    - High retrieval count → important
    - Referenced in multiple sessions → important
    - User explicitly requested → very important
    - Long time since last access but not forgotten → important
    """
    # For each memory, compute engagement score
    memories_with_engagement = await db.fetch("""
        SELECT
            m.memory_id,
            m.importance AS initial_importance,
            COUNT(CASE WHEN e.engagement_type = 'retrieved' THEN 1 END) AS retrieval_count,
            COUNT(CASE WHEN e.engagement_type = 'used' THEN 1 END) AS usage_count,
            COUNT(CASE WHEN e.engagement_type = 'user_requested' THEN 1 END) AS explicit_requests,
            COUNT(DISTINCT e.session_id) AS session_span,
            MAX(e.created_at) AS last_accessed
        FROM app.episodic_memories m
        LEFT JOIN app.memory_engagement e ON e.memory_id = m.memory_id
        WHERE m.user_id = $1
        GROUP BY m.memory_id, m.importance
    """, user_id)

    # Compute learned importance
    for memory in memories_with_engagement:
        learned_importance = compute_learned_importance(
            retrieval_count=memory.retrieval_count,
            usage_count=memory.usage_count,
            explicit_requests=memory.explicit_requests,
            session_span=memory.session_span,
            time_since_last_access=(now() - memory.last_accessed).days
        )

        # Update importance with moving average
        # Don't fully replace initial importance, blend with learned
        alpha = 0.3  # Weight for learned importance
        new_importance = (
            alpha * learned_importance +
            (1 - alpha) * memory.initial_importance
        )

        await db.execute("""
            UPDATE app.episodic_memories
            SET importance = $1
            WHERE memory_id = $2
        """, new_importance, memory.memory_id)

def compute_learned_importance(
    retrieval_count: int,
    usage_count: int,
    explicit_requests: int,
    session_span: int,
    time_since_last_access: int
) -> float:
    """
    Compute importance from engagement signals.
    """
    importance = 0.3  # Base

    # Signal 1: Retrieval frequency
    importance += min(0.3, log(1 + retrieval_count) * 0.1)

    # Signal 2: Usage in responses (stronger signal than retrieval)
    importance += min(0.3, log(1 + usage_count) * 0.15)

    # Signal 3: Explicit user requests (very strong signal)
    importance += min(0.3, explicit_requests * 0.15)

    # Signal 4: Session span (used across multiple sessions)
    importance += min(0.15, log(1 + session_span) * 0.05)

    # Signal 5: Recency (decay for stale memories)
    if time_since_last_access > 90:
        importance *= 0.8  # 20% penalty for very old

    return min(1.0, importance)
```

## Dimension 5: Confidence Decay Tuning

### The Problem

Phase 1 uses fixed decay rates:
```python
# Context-dependent aliases: 2% per day
# Stable aliases: 0.2% per day
```

**Question**: Are these the right rates? Do they vary by:
- User (some users have more stable contexts)?
- Entity type (customer names change less than project names)?
- Domain (retail vs consulting have different dynamics)?

### Learning Approach: Adaptive Decay Rates

**Data needed** (Phase 2):
```sql
CREATE TABLE app.confidence_corrections (
  correction_id BIGSERIAL PRIMARY KEY,
  entity_alias_id BIGINT NOT NULL,
  original_confidence REAL NOT NULL,
  days_since_creation INT NOT NULL,
  was_correct BOOLEAN NOT NULL,  -- Was the resolution correct?
  correction_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Learning algorithm** (Phase 3):
```python
async def learn_decay_rates(user_id: str):
    """
    Learn optimal confidence decay rates from corrections.

    If aliases stay correct longer than expected, decay too fast (reduce rate).
    If aliases become incorrect sooner than expected, decay too slow (increase rate).
    """
    corrections = await db.fetch("""
        SELECT
            ea.alias_source,
            ea.metadata->>'context_dependent' AS context_dependent,
            cc.days_since_creation,
            cc.was_correct,
            cc.original_confidence
        FROM app.confidence_corrections cc
        JOIN app.entity_aliases ea ON ea.alias_id = cc.entity_alias_id
        WHERE ea.user_id = $1
    """, user_id)

    # Group by alias characteristics
    groups = defaultdict(list)
    for corr in corrections:
        key = (corr.alias_source, corr.context_dependent)
        groups[key].append(corr)

    learned_rates = {}
    for (alias_source, context_dependent), group in groups.items():
        # Fit decay curve to observed correctness over time
        # Simple approach: Find rate that minimizes prediction error

        best_rate = optimize_decay_rate(group)
        learned_rates[(alias_source, context_dependent)] = best_rate

    return learned_rates

def optimize_decay_rate(corrections: List) -> float:
    """
    Find decay rate that best predicts confidence→correctness relationship.
    """
    def prediction_error(decay_rate):
        error = 0
        for corr in corrections:
            # Compute what confidence would be with this decay rate
            predicted_conf = corr.original_confidence * exp(-decay_rate * corr.days_since_creation)
            # Correctness should correlate with confidence
            predicted_correct = predicted_conf > 0.5
            actual_correct = corr.was_correct
            error += (predicted_correct != actual_correct)
        return error

    # Grid search over reasonable decay rates
    rates = [0.001, 0.002, 0.005, 0.01, 0.02, 0.03, 0.05]
    errors = [prediction_error(rate) for rate in rates]
    best_rate = rates[np.argmin(errors)]

    return best_rate
```

## Dimension 6: Procedural Memory Generalization

### The Problem

Initially extract procedural memories literally:
```
"When a customer requests rush shipping, I check if they're a premium customer, then approve if yes."

→ Creates procedural memory specific to "rush shipping" + "premium customer"
```

**Opportunity**: Generalize to pattern:
```
"When [entity type] requests [service upgrade], check [entity property], then approve based on [property value]"
```

### Learning Approach: Procedural Pattern Abstraction

**Data needed** (Phase 2):
```sql
-- Track procedural memory usage
CREATE TABLE app.procedural_memory_applications (
  application_id BIGSERIAL PRIMARY KEY,
  procedural_memory_id BIGINT NOT NULL,
  trigger_context JSONB NOT NULL,
  was_applicable BOOLEAN NOT NULL,
  was_successful BOOLEAN,  -- NULL if not applied
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Learning algorithm** (Phase 3):
```python
async def generalize_procedural_memories(user_id: str):
    """
    Find clusters of similar procedural memories and generalize.

    Example:
      Memory 1: "When customer requests rush shipping, check premium status"
      Memory 2: "When customer requests expedited delivery, check premium status"
      Memory 3: "When customer requests priority service, check premium status"

      → Generalize to: "When customer requests service upgrade, check premium status"
    """
    # Fetch procedural memories
    procedures = await db.fetch("""
        SELECT
            memory_id,
            trigger_pattern,
            trigger_features,
            action_heuristic,
            action_structure,
            observed_count,
            embedding
        FROM app.procedural_memories
        WHERE user_id = $1 AND observed_count >= 2
    """, user_id)

    # Cluster by embedding similarity
    embeddings = np.array([p.embedding for p in procedures])
    from sklearn.cluster import DBSCAN
    clustering = DBSCAN(eps=0.3, min_samples=2).fit(embeddings)

    # For each cluster, attempt generalization
    for cluster_id in set(clustering.labels_):
        if cluster_id == -1:  # Noise
            continue

        cluster_procedures = [
            p for i, p in enumerate(procedures)
            if clustering.labels_[i] == cluster_id
        ]

        if len(cluster_procedures) < 2:
            continue

        # Extract common pattern
        generalized = extract_common_pattern(cluster_procedures)

        if generalized:
            # Create generalized procedural memory
            await create_procedural_memory(
                user_id=user_id,
                trigger_pattern=generalized.trigger_pattern,
                trigger_features=generalized.trigger_features,
                action_heuristic=generalized.action_heuristic,
                action_structure=generalized.action_structure,
                observed_count=sum(p.observed_count for p in cluster_procedures),
                confidence=0.7,  # Start moderate, will increase with usage
                metadata={
                    'generalized_from': [p.memory_id for p in cluster_procedures],
                    'generalization_method': 'clustering'
                }
            )

def extract_common_pattern(procedures: List[ProceduralMemory]) -> GeneralizedPattern:
    """
    Find common pattern across similar procedures.

    Uses LLM to identify commonality and abstraction.
    """
    # Construct prompt for LLM
    prompt = f"""
    I have observed these similar procedures:

    {format_procedures(procedures)}

    What is the common pattern? Express as a generalized procedure using placeholders for variable parts.

    Format:
    Trigger: [generalized trigger pattern]
    Action: [generalized action]
    """

    # Get LLM to abstract
    response = await llm_query(prompt)

    # Parse response into structured pattern
    return parse_generalized_pattern(response)
```

## Meta-Memory: Learning About Learning

### The Concept

**Meta-memory**: Memories about the memory system itself.

Examples:
- "When I asked about customer preferences, the system surfaced the wrong procedural memory"
- "I've noticed the system doesn't remember details about short phone calls"
- "The summarization works well for order discussions but misses key points in problem-solving sessions"

**Vision alignment**: Epistemic humility includes knowing the limits of your own knowledge system.

### Implementation (Phase 3)

```sql
CREATE TABLE app.meta_memories (
  meta_memory_id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  observation TEXT NOT NULL,  -- What pattern was noticed
  memory_system_component TEXT NOT NULL,  -- 'extraction', 'retrieval', 'entity_resolution', etc.
  suggested_improvement TEXT,
  evidence JSONB NOT NULL,  -- References to specific instances
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Collection**:
```python
async def detect_system_patterns(user_id: str):
    """
    Analyze system behavior to detect meta-patterns.
    """
    # Pattern 1: Extraction gaps
    # If user frequently adds manual corrections of same type
    correction_patterns = await analyze_correction_frequency(user_id)
    if correction_patterns:
        await create_meta_memory(
            user_id=user_id,
            observation=f"User frequently corrects {correction_patterns.type}",
            component='extraction',
            suggested_improvement="Improve extraction rules for this pattern",
            evidence=correction_patterns.examples
        )

    # Pattern 2: Retrieval failures
    # If user repeats queries because results weren't good
    repeated_queries = await detect_repeated_queries(user_id)
    if repeated_queries:
        await create_meta_memory(
            user_id=user_id,
            observation="Query pattern repeated, suggesting poor initial results",
            component='retrieval',
            suggested_improvement="Adjust retrieval weights for this query type",
            evidence=repeated_queries
        )

    # Pattern 3: Entity resolution ambiguity hotspots
    # If certain terms always require disambiguation
    ambiguous_terms = await find_frequently_disambiguated_terms(user_id)
    for term in ambiguous_terms:
        await create_meta_memory(
            user_id=user_id,
            observation=f"Term '{term}' frequently requires disambiguation",
            component='entity_resolution',
            suggested_improvement="Learn context-specific aliases or ask user to define preferred entity",
            evidence={'term': term, 'disambiguation_count': term.count}
        )
```

## Feedback Mechanisms

### Explicit Feedback (User-Initiated)

```python
# User can rate retrieved memories
POST /api/memory/{memory_id}/feedback
{
  "rating": "helpful" | "not_helpful" | "incorrect",
  "comment": "This memory was about the wrong customer"
}

# User can request system improvements
POST /api/system/feedback
{
  "component": "extraction" | "retrieval" | "entity_resolution",
  "issue": "The system doesn't remember customer preferences well",
  "examples": [...]
}
```

### Implicit Feedback (Automatic)

```python
class ImplicitFeedbackCollector:
    """Collect signals about system performance without user action."""

    async def collect_retrieval_feedback(self, query, retrieved_memories, llm_response):
        """Did retrieved memories get used?"""
        for memory in retrieved_memories:
            used = self.memory_appears_in_response(memory, llm_response)
            await record_usage(memory.id, used)

    async def collect_extraction_feedback(self, extracted_memory):
        """Was this extraction useful?"""
        # Wait 24 hours, then check if memory was ever retrieved
        await asyncio.sleep(86400)
        retrieval_count = await count_retrievals(extracted_memory.id)
        was_useful = retrieval_count > 0
        await record_extraction_feedback(extracted_memory.id, was_useful)

    async def collect_confidence_feedback(self, entity_resolution):
        """Was the confidence score accurate?"""
        # If high-confidence resolution gets corrected, confidence was miscalibrated
        if entity_resolution.confidence > 0.8 and user_corrected_resolution:
            await record_confidence_overestimate(entity_resolution.id)
```

## Learning Cadence

### When to Trigger Learning?

```python
LEARNING_TRIGGERS = {
    'extraction_patterns': {
        'min_samples': 50,
        'frequency': 'weekly',
        'trigger': 'sample_threshold_or_schedule'
    },
    'retrieval_weights': {
        'min_samples': 100,
        'frequency': 'daily',
        'trigger': 'sample_threshold_or_schedule'
    },
    'entity_resolution': {
        'min_samples': 20,
        'frequency': 'daily',
        'trigger': 'sample_threshold_or_schedule'
    },
    'importance_calibration': {
        'min_samples': 100,
        'frequency': 'weekly',
        'trigger': 'schedule_only'
    },
    'procedural_generalization': {
        'min_samples': 10,  # Per cluster
        'frequency': 'monthly',
        'trigger': 'schedule_only'
    }
}

async def learning_scheduler():
    """Background task to trigger learning algorithms."""
    while True:
        for learning_task, config in LEARNING_TRIGGERS.items():
            # Check if enough data
            sample_count = await get_sample_count(learning_task)

            if sample_count >= config['min_samples']:
                # Trigger learning
                await run_learning_task(learning_task)

        # Sleep until next check
        await asyncio.sleep(3600)  # Check hourly
```

## Preventing Overfitting and Feedback Loops

### Risk: Reinforcement Loops

```
Bad pattern:
  1. System learns user prefers memory type X
  2. System retrieves more of type X
  3. User sees more type X, uses more type X
  4. System learns user prefers type X even more
  → Feedback loop, ignores other useful memory types
```

### Mitigation: Exploration vs Exploitation

```python
def balanced_retrieval_strategy(
    learned_weights: Dict[str, float],
    exploration_rate: float = 0.1
) -> Dict[str, float]:
    """
    With probability epsilon, use random/diverse strategy instead of learned.

    Ensures system occasionally tries different retrieval strategies
    to discover if learned pattern is still optimal.
    """
    if random.random() < exploration_rate:
        # Exploration: Use alternative strategy
        return {
            signal: weight + random.gauss(0, 0.1)
            for signal, weight in learned_weights.items()
        }
    else:
        # Exploitation: Use learned strategy
        return learned_weights
```

### Risk: Overfitting to Noisy Feedback

```
Bad pattern:
  User had one bad day, gave negative feedback on many memories
  → System learns to suppress those memory types
  → Actually they're useful, just bad timing
```

### Mitigation: Smoothing and Confidence Intervals

```python
def update_learned_parameter_with_smoothing(
    current_value: float,
    new_observation: float,
    observation_count: int,
    smoothing_factor: float = 0.1
) -> float:
    """
    Use exponential moving average to smooth updates.

    Don't let single observation drastically change learned parameters.
    """
    # More observations → trust new data more
    alpha = min(0.5, smoothing_factor * log(1 + observation_count))

    updated_value = (1 - alpha) * current_value + alpha * new_observation

    return updated_value
```

## Testing and Validation

### Unit Tests: Learning Algorithms

```python
def test_extraction_pattern_learning():
    """Learning suppresses bad patterns and boosts good ones."""
    # Setup: Create feedback data
    feedback = [
        {'pattern': 'always_keyword', 'was_useful': True},
        {'pattern': 'always_keyword', 'was_useful': True},
        {'pattern': 'always_keyword', 'was_useful': True},
        {'pattern': 'contains_entity', 'was_useful': False},
        {'pattern': 'contains_entity', 'was_useful': False},
    ]

    # Learn
    learned = learn_extraction_patterns(feedback)

    # Assert
    assert learned['always_keyword']['action'] == 'boost'
    assert learned['contains_entity']['action'] == 'suppress'

def test_retrieval_weight_optimization():
    """Learning adjusts weights based on what worked."""
    # Setup: Retrieval log where entity_overlap predicted usefulness
    logs = [
        {'semantic': 0.9, 'entity': 0.2, 'used': False},
        {'semantic': 0.3, 'entity': 0.9, 'used': True},
        {'semantic': 0.5, 'entity': 0.8, 'used': True},
    ]

    # Learn
    learned_weights = optimize_retrieval_weights(logs)

    # Assert: entity_overlap weight increased
    assert learned_weights['entity_overlap'] > learned_weights['semantic_similarity']
```

### A/B Tests: Validate Learning Impact

```python
async def ab_test_learning_system(duration_days: int = 30):
    """
    Compare users with learning enabled vs disabled.

    Metrics:
    - User satisfaction (explicit feedback)
    - Memory usage (implicit feedback: do retrieved memories get used?)
    - Query efficiency (fewer repeated queries)
    - Disambiguation rate (fewer requests for clarification)
    """
    control_group = randomly_select_users(0.5)  # No learning
    treatment_group = remaining_users()  # Learning enabled

    # Run for duration
    await asyncio.sleep(duration_days * 86400)

    # Compare metrics
    control_metrics = await compute_metrics(control_group)
    treatment_metrics = await compute_metrics(treatment_group)

    # Statistical significance test
    improvement = (treatment_metrics - control_metrics) / control_metrics
    p_value = compute_significance(control_metrics, treatment_metrics)

    return {
        'improvement': improvement,
        'significant': p_value < 0.05
    }
```

## Open Questions

1. **Learning infrastructure**: Should learning run as background jobs, or triggered on-demand? Separate service or in-process?

2. **Model complexity**: Start with simple models (logistic regression, rule learning) or use more complex (neural networks, LLMs)?

3. **User control**: Should users see what the system has learned? Should they be able to override learned patterns?

4. **Cross-user learning**: Can we learn patterns across users (anonymized) to bootstrap new users? Or is all learning per-user?

5. **Unlearning**: If a learned pattern becomes obsolete, how do we detect and unlearn it?

6. **Explanation**: Should the system explain why it learned a pattern? "I've noticed you prefer memories about customer relationships, so I'm weighting those higher."

---

---

## Summary: Learning System Design

**Core Principle**: Can't learn without data—Phase 1 collects, Phase 2/3 learns.

**Six Learning Dimensions** (all Phase 2/3):

1. **Extraction Quality**: Learn which facts worth remembering (requires 50+ samples)
2. **Retrieval Relevance**: Learn optimal signal weights per query type (requires 100+ retrievals)
3. **Entity Resolution**: Learn user disambiguation patterns (requires 20+ disambiguations)
4. **Importance Calibration**: Learn what makes memories important to user (requires 100+ memories)
5. **Confidence Tuning**: Learn optimal decay rates per fact type (requires 50+ corrections)
6. **Procedural Generalization**: Abstract patterns from specific procedures (requires 10+ similar procedures)

**Data Collection (Phase 1)**:
- Log all extractions, retrievals, resolutions
- Track implicit feedback (memory usage)
- Record explicit feedback (user corrections)
- Store context for each operation

**Pattern Recognition (Phase 2)**:
- Batch analysis of collected data
- Simple statistical learning (logistic regression, rule mining)
- Per-user pattern identification
- Weight and threshold adjustments

**Adaptive Learning (Phase 3)**:
- Online/continuous learning
- Meta-memories (system awareness of own patterns)
- Exploration vs exploitation (avoid feedback loops)
- Unlearning obsolete patterns

**Key Safeguards**:
- **Exploration rate**: Occasionally try non-learned strategies (avoid reinforcement loops)
- **Smoothing**: Don't overreact to single observations (exponential moving average)
- **Minimum samples**: Don't learn from insufficient data
- **A/B testing**: Validate that learning actually helps

**Implementation Priority**:
- **Phase 1 essential**: Data collection infrastructure only
- **Phase 2 deferred**: Requires 50-100+ samples per dimension
- **Phase 3 deferred**: Requires Phase 2 validation + continuous feedback

---

**Vision Alignment**:
- ✅ Graceful evolution: System improves with use (vision principle)
- ✅ Epistemic humility: Learn from mistakes, acknowledge limits
- ✅ Personalization: Adapt to each user's unique patterns
- ✅ Meta-awareness: Learn about learning (meta-memories)
- ✅ Design Philosophy: "Learning features need data to learn from" (justified deferral)
