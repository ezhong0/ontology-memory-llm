# Retrieval and Augmentation System

## Vision Alignment

From VISION.md:
> "Retrieval is not information extraction—it is meaning-making. The system must understand which memories matter in which contexts, just as an experienced colleague knows what to recall when."

The retrieval system is a **relevance intelligence system** that combines:
- **Semantic relevance**: Embedding similarity (what matches conceptually)
- **Entity relevance**: Entity overlap (what's about the same things)
- **Temporal relevance**: Recency/time-range (what's current vs historical)
- **Importance**: Impact weighting (what matters most)
- **Reinforcement**: Proven utility (what's been useful before)

**Design Philosophy Applied**:
- **Passive computation**: Scores computed on-demand, no pre-computed rankings
- **Complexity justified**: Multi-signal scoring serves vision's "context as constitutive" principle
- **Phase distinction**: Core retrieval (Phase 1) vs learned optimization (Phase 2/3)

---

## Phase Roadmap

**Phase 1 (Essential)**: Three-stage retrieval architecture
- Query understanding (entity extraction, query classification)
- Multi-source candidate generation (semantic + entity + temporal)
- Multi-signal ranking and selection
- Context window management

**Phase 2 (Enhancements)**: Retrieval optimization
- Implicit feedback tracking (which memories get used)
- Signal weight tuning per user
- Advanced diversity (MMR algorithm)

**Phase 3 (Learning)**: Adaptive retrieval
- Learned signal weights per query type
- A/B testing different strategies
- Retrieval explanation ("I recalled this because...")

## The Retrieval Problem

### Core Challenge: Multi-Dimensional Relevance

A memory might be relevant because:
1. **Semantic similarity**: Query embedding is close to memory embedding
2. **Entity overlap**: Query mentions same entities as memory
3. **Temporal proximity**: Recent memories for ongoing conversations
4. **Importance**: High-impact memories matter more
5. **Reinforcement**: Frequently recalled memories prove their value
6. **Ontological relationships**: Query about customers should include related orders

**The challenge**: How to weight these signals? Different query types need different weightings.

### Example Scenarios

**Scenario 1: "What did Acme Corporation order last month?"**
- Entity overlap: HIGH weight (must include Acme)
- Temporal: HIGH weight (last month)
- Semantic: MEDIUM weight (order-related concepts)
- Importance: LOW weight (specific factual query)

**Scenario 2: "How do I usually handle rush orders?"**
- Semantic: HIGH weight (rush order procedures)
- Reinforcement: HIGH weight (proven patterns)
- Procedural memory: REQUIRED (this is about process)
- Entity overlap: LOW weight (not entity-specific)

**Scenario 3: "Tell me about my customers"**
- Entity type: HIGH weight (must be customer entities)
- Summary memory: PREFERRED (consolidated view)
- Importance: HIGH weight (focus on key customers)
- Recency: MEDIUM weight (balance current and historical)

## Architecture: Three-Stage Retrieval

```
┌─────────────────────────────────────────────────────────┐
│ Stage 1: Query Understanding                            │
│ - Parse query                                           │
│ - Extract entities                                      │
│ - Classify query type                                   │
│ - Determine retrieval strategy                          │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ Stage 2: Candidate Generation                           │
│ - Semantic search (embedding similarity)                │
│ - Entity-based retrieval                                │
│ - Temporal filtering                                    │
│ - Memory type filtering                                 │
│ → Candidates: 100-200 memories (over-retrieve)          │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ Stage 3: Ranking and Selection                          │
│ - Multi-signal scoring                                  │
│ - Deduplication                                         │
│ - Diversity balancing                                   │
│ - Context window management                             │
│ → Final: 5-15 memories (fit in context)                 │
└─────────────────────────────────────────────────────────┘
```

## Stage 1: Query Understanding

### Query Classification

Every user query falls into one of several types, each requiring different retrieval strategy:

```python
@dataclass
class QueryType:
    """Classification of user query intent."""
    category: str  # 'factual', 'procedural', 'exploratory', 'analytical'
    entity_focused: bool  # Is this about specific entities?
    time_focused: bool  # Does temporal context matter?
    procedural: bool  # Is this about how-to/process?
    requires_domain_db: bool  # Need real-time domain data?

# Examples:
"What did Acme order?" → QueryType(
    category='factual',
    entity_focused=True,
    time_focused=False,
    procedural=False,
    requires_domain_db=True  # Need to query domain.orders
)

"How do I handle rush orders?" → QueryType(
    category='procedural',
    entity_focused=False,
    time_focused=False,
    procedural=True,
    requires_domain_db=False
)

"Tell me about my recent customer interactions" → QueryType(
    category='exploratory',
    entity_focused=True,
    time_focused=True,
    procedural=False,
    requires_domain_db=False
)

"Why are sales down this quarter?" → QueryType(
    category='analytical',
    entity_focused=False,
    time_focused=True,
    procedural=False,
    requires_domain_db=True  # Need current sales data
)
```

### Entity Extraction from Query

Use entity resolution system (from ENTITY_RESOLUTION_DESIGN.md):

```python
async def extract_query_entities(query: str, context: ConversationContext) -> List[ResolvedEntity]:
    """
    Extract and resolve entity mentions from query.
    """
    # Use NER (Named Entity Recognition) or LLM to identify mentions
    mentions = await extract_entity_mentions(query)
    # ["Acme", "last month", "rush orders"]

    resolved_entities = []
    for mention in mentions:
        result = await resolve_entity(mention, context)
        if result.canonical_entity_id:
            resolved_entities.append(ResolvedEntity(
                mention_text=mention,
                canonical_id=result.canonical_entity_id,
                confidence=result.confidence
            ))

    return resolved_entities
```

### Temporal Extraction

Extract time references and convert to date ranges:

```python
def extract_temporal_scope(query: str) -> Optional[TimeRange]:
    """
    Parse temporal references in query.
    """
    # "last month" → (2024-01-01, 2024-01-31)
    # "yesterday" → (2024-02-14, 2024-02-14)
    # "this quarter" → (2024-01-01, 2024-03-31)
    # "recent" → (now - 7 days, now)

    patterns = {
        r'last month': lambda: month_range(offset=-1),
        r'yesterday': lambda: day_range(offset=-1),
        r'recent|recently|lately': lambda: (now() - timedelta(days=7), now()),
        r'this quarter': lambda: current_quarter_range(),
        r'(\d+) days ago': lambda n: day_range(offset=-int(n)),
    }

    for pattern, range_fn in patterns.items():
        if re.search(pattern, query.lower()):
            return range_fn()

    return None  # No temporal constraint
```

### Retrieval Strategy Selection

Based on query type, choose retrieval weights:

```python
STRATEGY_WEIGHTS = {
    'factual_entity_focused': {
        'semantic_similarity': 0.25,
        'entity_overlap': 0.40,  # High: must match entities
        'temporal_relevance': 0.20,
        'importance': 0.10,
        'reinforcement': 0.05,
    },
    'procedural': {
        'semantic_similarity': 0.45,  # High: must match procedure concept
        'entity_overlap': 0.05,  # Low: procedures are general
        'temporal_relevance': 0.05,
        'importance': 0.15,
        'reinforcement': 0.30,  # High: proven patterns matter
    },
    'exploratory': {
        'semantic_similarity': 0.35,
        'entity_overlap': 0.25,
        'temporal_relevance': 0.15,
        'importance': 0.20,  # High: surface important patterns
        'reinforcement': 0.05,
    },
    'analytical': {
        'semantic_similarity': 0.30,
        'entity_overlap': 0.15,
        'temporal_relevance': 0.25,  # High: trends over time
        'importance': 0.25,  # High: focus on impactful patterns
        'reinforcement': 0.05,
    },
}

def select_strategy(query_type: QueryType) -> Dict[str, float]:
    """Select retrieval weights based on query type."""
    if query_type.procedural:
        return STRATEGY_WEIGHTS['procedural']
    elif query_type.entity_focused and query_type.category == 'factual':
        return STRATEGY_WEIGHTS['factual_entity_focused']
    elif query_type.category == 'analytical':
        return STRATEGY_WEIGHTS['analytical']
    else:
        return STRATEGY_WEIGHTS['exploratory']
```

## Stage 2: Candidate Generation

### Multi-Source Retrieval

Generate candidates from multiple sources in parallel:

```python
async def generate_candidates(
    query: str,
    query_embedding: np.ndarray,
    query_entities: List[ResolvedEntity],
    query_type: QueryType,
    time_range: Optional[TimeRange],
    user_id: str
) -> List[MemoryCandidate]:
    """
    Generate retrieval candidates from multiple sources.
    Over-retrieve here; we'll rank and filter in Stage 3.
    """
    candidates = []

    # Source 1: Semantic similarity (vector search)
    semantic_candidates = await retrieve_by_semantic_similarity(
        embedding=query_embedding,
        user_id=user_id,
        limit=50,
        min_similarity=0.5
    )
    candidates.extend(semantic_candidates)

    # Source 2: Entity overlap
    if query_entities:
        entity_candidates = await retrieve_by_entities(
            entities=[e.canonical_id for e in query_entities],
            user_id=user_id,
            limit=30
        )
        candidates.extend(entity_candidates)

    # Source 3: Temporal range
    if time_range:
        temporal_candidates = await retrieve_by_time_range(
            start=time_range.start,
            end=time_range.end,
            user_id=user_id,
            limit=30
        )
        candidates.extend(temporal_candidates)

    # Source 4: Memory type filtering
    if query_type.procedural:
        procedural_candidates = await retrieve_procedural_memories(
            embedding=query_embedding,
            user_id=user_id,
            limit=20
        )
        candidates.extend(procedural_candidates)

    # Source 5: Summaries (always include recent summaries)
    summary_candidates = await retrieve_memory_summaries(
        user_id=user_id,
        scope_type='session' if time_range else 'global',
        limit=5
    )
    candidates.extend(summary_candidates)

    # Deduplicate by memory_id
    unique_candidates = {c.memory_id: c for c in candidates}
    return list(unique_candidates.values())
```

### Semantic Similarity Retrieval

```sql
-- pgvector cosine similarity search
SELECT
  memory_id,
  memory_type,  -- 'episodic', 'semantic', 'procedural', 'summary'
  summary_text,
  entities,
  importance,
  created_at,
  1 - (embedding <=> $query_embedding) AS cosine_similarity
FROM (
  SELECT memory_id, 'episodic' AS memory_type, summary AS summary_text,
         entities, importance, embedding, created_at
  FROM app.episodic_memories
  WHERE user_id = $user_id

  UNION ALL

  SELECT memory_id, 'semantic' AS memory_type,
         subject_entity_id || ' ' || predicate || ' ' || object_value AS summary_text,
         jsonb_build_array(jsonb_build_object('canonical_id', subject_entity_id)) AS entities,
         importance, embedding, created_at
  FROM app.semantic_memories
  WHERE user_id = $user_id AND status = 'active'

  UNION ALL

  SELECT memory_id, 'procedural' AS memory_type,
         trigger_pattern || ': ' || action_heuristic AS summary_text,
         NULL AS entities,
         0.8 AS importance,  -- Procedural memories default high importance
         embedding, created_at
  FROM app.procedural_memories
  WHERE user_id = $user_id

  UNION ALL

  SELECT summary_id AS memory_id, 'summary' AS memory_type, summary_text,
         NULL AS entities, 0.9 AS importance,  -- Summaries very high importance
         embedding, created_at
  FROM app.memory_summaries
  WHERE user_id = $user_id
) AS all_memories
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $query_embedding  -- pgvector index scan
LIMIT 50;
```

**Why UNION ALL across memory types?**
- Vision: All memory types should be retrievable
- User might ask about any type: facts (semantic), events (episodic), processes (procedural)
- Semantic search works across types with same embedding space

### Entity-Based Retrieval

```sql
-- Find memories involving specific entities
WITH target_entities AS (
  SELECT unnest($entity_ids::text[]) AS entity_id
)
SELECT DISTINCT
  em.memory_id,
  'episodic' AS memory_type,
  em.summary AS summary_text,
  em.entities,
  em.importance,
  em.created_at,
  COUNT(DISTINCT te.entity_id) AS entity_match_count
FROM app.episodic_memories em
CROSS JOIN LATERAL jsonb_array_elements(em.entities) AS entity
JOIN target_entities te ON (entity->>'canonical_id') = te.entity_id
WHERE em.user_id = $user_id
GROUP BY em.memory_id, em.summary, em.entities, em.importance, em.created_at

UNION ALL

-- Semantic memories with subject entity match
SELECT
  sm.memory_id,
  'semantic' AS memory_type,
  sm.subject_entity_id || ' ' || sm.predicate || ' ' || sm.object_value AS summary_text,
  jsonb_build_array(jsonb_build_object('canonical_id', sm.subject_entity_id)) AS entities,
  sm.importance,
  sm.created_at,
  1 AS entity_match_count
FROM app.semantic_memories sm
JOIN target_entities te ON sm.subject_entity_id = te.entity_id
WHERE sm.user_id = $user_id AND sm.status = 'active'

ORDER BY entity_match_count DESC, importance DESC, created_at DESC
LIMIT 30;
```

### Ontology-Aware Expansion

Expand entity retrieval using domain ontology:

```python
async def expand_entities_via_ontology(
    entities: List[str],
    max_depth: int = 1
) -> List[str]:
    """
    Given entity IDs, expand to include ontologically related entities.

    Example:
      Input: ["customer:a1b2c3d4"]
      Ontology: customer --[HAS_MANY]--> orders
      Output: ["customer:a1b2c3d4", "order:1", "order:2", ...]

    Use case: Query about a customer should include their orders.
    """
    expanded = set(entities)

    for entity_id in entities:
        entity_type = entity_id.split(':')[0]

        # Find related entity types via ontology
        relations = await db.fetch("""
            SELECT relation_type, to_entity_type, join_spec
            FROM app.domain_ontology
            WHERE from_entity_type = $1
        """, entity_type)

        for rel in relations:
            # Query domain database for related entities
            related_entities = await query_related_entities(
                entity_id=entity_id,
                relation=rel,
                limit=10  # Don't explode context
            )
            expanded.update(related_entities)

    return list(expanded)
```

**Example**:
```
Query: "What did Acme Corporation order?"
Entities: ["customer:a1b2c3d4"]

Ontology expansion:
  customer --[HAS_MANY]--> orders
  Query domain.orders WHERE customer_id = 'a1b2c3d4'
  → Discover: order:12345, order:12346, order:12347

Expanded entities: ["customer:a1b2c3d4", "order:12345", "order:12346", "order:12347"]

Now retrieve memories mentioning ANY of these entities.
```

**Vision alignment**: Ontology-awareness means understanding relationships, not just entities in isolation.

## Stage 3: Ranking and Selection

### Multi-Signal Scoring

Combine all relevance signals into single score:

```python
def compute_memory_score(
    candidate: MemoryCandidate,
    query_embedding: np.ndarray,
    query_entities: List[str],
    time_range: Optional[TimeRange],
    strategy_weights: Dict[str, float],
    now: datetime
) -> float:
    """
    Compute final relevance score using weighted multi-signal approach.
    """
    signals = {}

    # Signal 1: Semantic similarity
    if candidate.embedding is not None:
        signals['semantic_similarity'] = cosine_similarity(
            query_embedding,
            candidate.embedding
        )
    else:
        signals['semantic_similarity'] = 0.0

    # Signal 2: Entity overlap
    candidate_entities = extract_entity_ids(candidate.entities)
    if query_entities and candidate_entities:
        overlap = len(set(query_entities) & set(candidate_entities))
        max_possible = len(query_entities)
        signals['entity_overlap'] = overlap / max_possible
    else:
        signals['entity_overlap'] = 0.0

    # Signal 3: Temporal relevance
    if time_range:
        if time_range.start <= candidate.created_at <= time_range.end:
            signals['temporal_relevance'] = 1.0
        else:
            # Decay based on distance from time range
            distance_days = min(
                abs((candidate.created_at - time_range.start).days),
                abs((candidate.created_at - time_range.end).days)
            )
            signals['temporal_relevance'] = exp(-0.1 * distance_days)
    else:
        # No time constraint: mild recency bias
        age_days = (now - candidate.created_at).days
        signals['temporal_relevance'] = exp(-0.01 * age_days)

    # Signal 4: Importance
    signals['importance'] = candidate.importance  # Already 0.0-1.0

    # Signal 5: Reinforcement
    # (Would need retrieval_log from Phase 2 to compute)
    # For now: Use use_count if available, else default
    signals['reinforcement'] = min(1.0, log(1 + candidate.use_count) / 5.0) if hasattr(candidate, 'use_count') else 0.5

    # Weighted combination
    final_score = sum(
        signals[signal_name] * strategy_weights[signal_name]
        for signal_name in signals
    )

    # Boost for memory type preferences
    if candidate.memory_type == 'summary':
        final_score *= 1.15  # Summaries are dense, prefer them
    elif candidate.memory_type == 'procedural':
        # Already boosted by strategy weights when query is procedural
        pass

    return final_score
```

### Diversity and Deduplication

Avoid returning many similar memories:

```python
def select_diverse_memories(
    scored_candidates: List[Tuple[MemoryCandidate, float]],
    max_memories: int,
    diversity_threshold: float = 0.85
) -> List[MemoryCandidate]:
    """
    Select top-k memories while maintaining diversity.

    Use Maximal Marginal Relevance (MMR) approach:
      MMR = λ * Relevance - (1 - λ) * MaxSimilarity to already selected
    """
    selected = []
    candidates = sorted(scored_candidates, key=lambda x: x[1], reverse=True)

    λ = 0.7  # Balance between relevance and diversity

    for candidate, score in candidates:
        if len(selected) >= max_memories:
            break

        if not selected:
            # First memory: just take highest score
            selected.append(candidate)
            continue

        # Check similarity to already selected memories
        max_similarity = max(
            cosine_similarity(candidate.embedding, s.embedding)
            for s in selected
            if candidate.embedding is not None and s.embedding is not None
        )

        # MMR score
        mmr_score = λ * score - (1 - λ) * max_similarity

        # Only add if diverse enough or very high relevance
        if mmr_score > 0.3 or score > 0.9:
            selected.append(candidate)

    return selected
```

### Context Window Management

Fit memories into available context window:

```python
def fit_to_context_window(
    memories: List[MemoryCandidate],
    max_tokens: int = 3000,
    query_tokens: int = 100
) -> List[MemoryCandidate]:
    """
    Select memories that fit within context window.

    Priority order:
      1. Summaries (most dense information)
      2. Highest scored memories
      3. Prune least relevant if needed
    """
    available_tokens = max_tokens - query_tokens

    # Summaries first (always include if present)
    summaries = [m for m in memories if m.memory_type == 'summary']
    others = [m for m in memories if m.memory_type != 'summary']

    selected = []
    tokens_used = 0

    # Add summaries
    for summary in summaries:
        tokens = estimate_tokens(summary.summary_text)
        if tokens_used + tokens <= available_tokens:
            selected.append(summary)
            tokens_used += tokens

    # Add others until context full
    for memory in others:
        tokens = estimate_tokens(memory.summary_text)
        if tokens_used + tokens <= available_tokens:
            selected.append(memory)
            tokens_used += tokens
        else:
            break  # Context window full

    return selected

def estimate_tokens(text: str) -> int:
    """Rough estimate: 1 token ≈ 4 characters."""
    return len(text) // 4
```

## Augmentation: Presenting Memories to LLM

### Structured Prompt Format

Format retrieved memories for LLM consumption:

```python
def format_augmentation_context(
    memories: List[MemoryCandidate],
    query: str
) -> str:
    """
    Format retrieved memories into structured prompt section.
    """
    sections = []

    # Group by memory type
    by_type = defaultdict(list)
    for m in memories:
        by_type[m.memory_type].append(m)

    # Summaries first (highest level)
    if by_type['summary']:
        sections.append("## Relevant Summaries\n")
        for summary in by_type['summary']:
            sections.append(f"- {summary.summary_text}\n")

    # Procedural memories (how-to patterns)
    if by_type['procedural']:
        sections.append("\n## Relevant Procedures\n")
        for proc in by_type['procedural']:
            sections.append(f"- When: {proc.trigger_pattern}\n")
            sections.append(f"  Then: {proc.action_heuristic}\n")

    # Semantic facts
    if by_type['semantic']:
        sections.append("\n## Relevant Facts\n")
        for sem in by_type['semantic']:
            # Format as natural language triple
            sections.append(f"- {format_semantic_triple(sem)}\n")

    # Episodic memories
    if by_type['episodic']:
        sections.append("\n## Relevant Past Interactions\n")
        for ep in by_type['episodic']:
            sections.append(f"- {ep.summary_text} ({format_time_ago(ep.created_at)})\n")

    prompt = f"""# Retrieved Context

The following information from your memory may be relevant to the query: "{query}"

{"".join(sections)}

Use this context to inform your response, but be clear about what you know vs. what you're inferring.
"""

    return prompt

def format_semantic_triple(semantic_memory) -> str:
    """Format semantic triple as natural language."""
    predicates = {
        'has_property': f"{semantic_memory.subject} has {semantic_memory.object_value}",
        'related_to': f"{semantic_memory.subject} is related to {semantic_memory.object_value}",
        'prefers': f"{semantic_memory.subject} prefers {semantic_memory.object_value}",
        # ... more predicate templates
    }
    return predicates.get(
        semantic_memory.predicate_type,
        f"{semantic_memory.subject} {semantic_memory.predicate} {semantic_memory.object_value}"
    )
```

### Example Augmented Prompt

```
User Query: "What did Acme Corporation order last month?"

# Retrieved Context

The following information from your memory may be relevant to the query: "What did Acme Corporation order last month?"

## Relevant Summaries
- Acme Corporation (customer:a1b2c3d4) is a long-standing customer with frequent large orders, typically in the technology sector.

## Relevant Facts
- Acme Corporation has industry: technology
- Acme Corporation prefers payment terms: NET30
- Acme Corporation has recent order: order:12345 (2024-01-15)

## Relevant Past Interactions
- User asked about Acme's payment status for invoice #789 (2 weeks ago)
- User reviewed Acme's Q4 2023 order history and noted increase in order frequency (1 month ago)

# Domain Database Query Results

[Current orders from domain.orders table for customer_id = a1b2c3d4, date > 2024-01-01]

---

Based on the above context and current data, please respond to the user's query.
```

**Vision alignment**: Presenting memories as structured knowledge, not raw data dumps. LLM can reason over this context.

## Integration with Domain Database

### Hybrid Retrieval: Memory + Real-Time Data

```python
async def augmented_retrieval(
    query: str,
    user_id: str,
    context: ConversationContext
) -> AugmentedContext:
    """
    Combine memory retrieval with domain database queries.
    """
    # Stage 1: Understand query
    query_type = classify_query(query)
    query_entities = await extract_query_entities(query, context)
    query_embedding = await compute_embedding(query)
    time_range = extract_temporal_scope(query)

    # Stage 2 & 3: Retrieve memories
    memories = await retrieve_and_rank_memories(
        query=query,
        query_embedding=query_embedding,
        query_entities=query_entities,
        query_type=query_type,
        time_range=time_range,
        user_id=user_id
    )

    # Parallel: Query domain database if needed
    domain_results = None
    if query_type.requires_domain_db and query_entities:
        domain_results = await query_domain_database(
            query_type=query_type,
            entities=query_entities,
            time_range=time_range
        )

    return AugmentedContext(
        memories=memories,
        domain_results=domain_results,
        query_type=query_type
    )
```

### When to Query Domain DB vs Memory?

**Domain Database**: Current state, transactional data
- "What did Acme order?" → Query domain.orders table
- "What's the balance on invoice #123?" → Query domain.invoices table
- "How many active customers?" → Query domain.customers table

**Memory System**: Learned patterns, context, summarized knowledge
- "What does Acme usually order?" → Retrieve procedural/semantic memories
- "Why did Acme dispute invoice #123?" → Retrieve episodic memory
- "Tell me about my relationship with Acme" → Retrieve memory summaries

**Both**: Rich contextual answers
```python
# Query: "Should I offer Acme a discount?"

# From memory:
# - Acme prefers NET30 payment terms (semantic)
# - Previous discount negotiation was successful (episodic)
# - Pattern: Large customers with >$50k orders get 5% discount (procedural)

# From domain DB:
# - Acme's total orders this year: $120,000
# - Acme's payment history: Always on time
# - Current quote request: $15,000

# Combined answer: Intelligent recommendation based on context + data
```

## Performance and Scaling

### Query Performance Targets

- **Semantic search**: <50ms for 50 candidates (pgvector index)
- **Entity retrieval**: <30ms (B-tree index on entity IDs)
- **Scoring & ranking**: <20ms (in-memory computation)
- **Total retrieval latency**: <100ms end-to-end

### Indexes Required

```sql
-- Semantic similarity (pgvector)
CREATE INDEX idx_episodic_embedding ON app.episodic_memories USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
CREATE INDEX idx_semantic_embedding ON app.semantic_memories USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
CREATE INDEX idx_procedural_embedding ON app.procedural_memories USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
CREATE INDEX idx_summary_embedding ON app.memory_summaries USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Entity retrieval (GIN index for JSONB)
CREATE INDEX idx_episodic_entities ON app.episodic_memories USING gin (entities jsonb_path_ops);

-- Temporal filtering
CREATE INDEX idx_episodic_time_user ON app.episodic_memories(user_id, created_at DESC);
CREATE INDEX idx_semantic_time_user ON app.semantic_memories(user_id, created_at DESC);

-- Importance filtering (for high-importance memories)
CREATE INDEX idx_episodic_importance ON app.episodic_memories(user_id, importance DESC) WHERE importance > 0.7;
```

### Scaling Considerations

**Phase 1** (current design): Single-database, good to ~1M memories per user
- pgvector handles millions of vectors efficiently
- Filtering by user_id partitions data naturally

**Phase 2** (if scaling needed): Partitioning strategies
- Partition by user_id (most queries are per-user)
- Partition episodic_memories by created_at (older memories less frequently accessed)
- Consider separate vector index per user for very large deployments

**Phase 3** (if extreme scale): Specialized vector database
- Move embeddings to dedicated vector DB (Pinecone, Weaviate, etc.)
- Keep structured data (entities, timestamps, metadata) in PostgreSQL
- Join results in application layer

## Feedback and Learning (Phase 2/3)

**Deferred**: Track which retrieved memories prove useful to tune signal weights over time.

**Phase 2 Concept**: Log retrieval events
```python
# After each retrieval
await log_retrieval_event(
    query=query,
    retrieved_memory_ids=[m.memory_id for m in memories],
    used_in_response=[m.memory_id for m in memories if m.used]  # Heuristic detection
)
```

**Phase 3 Concept**: Learn from patterns
- Which memory types most useful per query type?
- Should signal weights adapt per user?
- A/B test different weighting strategies

**Why Deferred**: Need operational data (1000+ retrieval events) to identify meaningful patterns.

---

## Summary: Retrieval System Design

**Core Architecture**: Three-stage pipeline for relevance-aware memory retrieval

**Stage 1 - Query Understanding**:
- Classify query type (factual, procedural, exploratory, analytical)
- Extract and resolve entities
- Extract temporal scope
- Select retrieval strategy (signal weights)

**Stage 2 - Candidate Generation**:
- Semantic similarity search (pgvector)
- Entity-based retrieval (JSONB GIN index)
- Temporal filtering (B-tree index)
- Memory type filtering (summaries, procedural, semantic, episodic)
- → Over-retrieve: 100-200 candidates

**Stage 3 - Ranking & Selection**:
- Multi-signal scoring (semantic + entity + temporal + importance + reinforcement)
- Diversity balancing (avoid redundant memories)
- Context window management (fit within token budget)
- → Final: 5-15 memories

**Key Principles**:
- **Passive computation**: All scores computed on-demand
- **Context-aware strategies**: Different weights for different query types
- **Ontology-aware expansion**: Entity relationships guide retrieval
- **Hybrid approach**: Memory + domain DB for complete answers

**Phase 1 Essential**:
- Three-stage retrieval pipeline
- Multi-signal scoring with configurable weights
- Parallel candidate generation from multiple sources
- Context window management

**Phase 2 Enhancements**:
- Retrieval feedback logging
- Diversity optimization (MMR algorithm)
- Per-user signal weight tuning

**Phase 3 Learning**:
- Adaptive signal weights from usage data
- A/B testing retrieval strategies
- Retrieval explainability

**Performance Targets**:
- Semantic search: <50ms (pgvector)
- Entity retrieval: <30ms (B-tree)
- Ranking: <20ms (in-memory)
- **Total: <100ms end-to-end**

---

**Vision Alignment**:
- ✅ Meaning-based retrieval: Multi-dimensional relevance (not just text match)
- ✅ Context-aware: Different strategies for different query types
- ✅ Ontology-aware: Entity expansion via domain relationships
- ✅ Experienced colleague: Summaries and procedural patterns prioritized
- ✅ Minimal sufficient context: Diversity to avoid redundancy
