# Vision Alignment Guide: Building the Experienced Colleague

**Purpose**: Transform implementation from rule-based system to cognitive entity that embodies vision principles.

**Philosophy**: The vision isn't a feature list—it's a way of being. Every architectural decision should answer: "Does this make the system more like an experienced colleague?"

---

## Table of Contents

1. [Core Identity: What Are We Building?](#core-identity)
2. [The 8 Fundamental Principles](#principles)
3. [Architectural Patterns for Vision Alignment](#patterns)
4. [System-Wide Alignment Strategy](#strategy)
5. [Implementation Checklist by Component](#checklist)
6. [Anti-Patterns and How to Avoid Them](#antipatterns)
7. [Measurement: Are We Vision-Aligned?](#measurement)

---

## Core Identity: What Are We Building? {#core-identity}

### The North Star (Vision lines 683-694)

> This system should feel like talking to an **experienced colleague** who:
> - Never forgets what matters
> - Knows the business deeply
> - Learns your way of working
> - Admits uncertainty
> - Explains their thinking
> - Gets smarter over time
> - Handles mistakes gracefully
> - Respects your time

### The Central Thesis (Vision lines 21-22)

> An intelligent agent requires **both correspondence truth (database) and contextual truth (memory)** in dynamic equilibrium.

### What This Means

We're not building:
- ❌ A chatbot with database access
- ❌ A fancy SQL generator
- ❌ A keyword-matching wrapper

We're building:
- ✅ A **cognitive entity** with genuine understanding
- ✅ A **knowledge-grounded reasoning partner**
- ✅ A **semantic memory layer** that transforms data into wisdom

**The difference is fundamental**, not incremental.

---

## The 8 Fundamental Principles {#principles}

### 1. Context as Constitutive of Meaning

**Vision Statement** (lines 145-170):
> "Meaning is always contextual... Retrieval is reconstructing the minimal context necessary for meaning to emerge."

**What It Means**:
- "Is this ready?" has no meaning without context
- Same words + different context = different meaning
- System must understand situational semantics, not just word matching

**Current Violations**:
```python
# ❌ VIOLATION: Context-free keyword matching
if "invoice" in query:
    return "financial"

# ❌ VIOLATION: Ignores who, what, when
# "Invoice status?" (checking existing)
# "Invoice them?" (creating new)
# Both match "invoice" but need different responses
```

**Vision-Aligned Approach**:
```python
# ✅ ALIGNED: LLM understands context
tools = [
    {
        "name": "get_invoice_status",
        "description": "Check existing invoice status"
    },
    {
        "name": "check_invoicing_readiness",
        "description": "Determine if we can create new invoice"
    }
]

# LLM chooses based on context:
# "Invoice status?" → calls get_invoice_status()
# "Can we invoice?" → calls check_invoicing_readiness()
```

**Implementation Guidance**:
- Use LLM tool calling for query planning (context-aware)
- Pass rich context to retrieval (entities, session, user preferences)
- Multi-signal scoring (not just text similarity)
- Intent derived from question + entities + history, not keywords

---

### 2. Epistemic Humility

**Vision Statement** (lines 386-421):
> "A profound principle: The system should know what it doesn't know... Max confidence = 0.95 (never 100% certain)"

**What It Means**:
- Never claim absolute certainty
- Confidence reflects epistemic justification
- Low confidence triggers validation
- Uncertainty is explicit and actionable

**Current Violations**:
```python
# ❌ VIOLATION: Claims perfect certainty
CONFIDENCE_EXACT_MATCH = 1.0
new_confidence = 1.0  # DB is authoritative

# ❌ VIOLATION: No uncertainty expression
if fuzzy_match_score > 0.85:
    return entity  # What if there are 2 similar entities?
```

**Vision-Aligned Approach**:
```python
# ✅ ALIGNED: Max confidence is 0.95
CONFIDENCE_EXACT_MATCH = 0.95  # Even exact matches can have errors
MAX_CONFIDENCE = 0.95  # Epistemic humility principle

# ✅ ALIGNED: Calibrated confidence
confidence = self._calibrate_confidence(
    predicted=0.85,
    historical_accuracy=0.78,  # Actually achieved accuracy
)
# Returns: 0.78 (honest assessment)

# ✅ ALIGNED: Express uncertainty
if confidence < 0.6:
    return {
        "answer": "I'm uncertain, here's why...",
        "confidence": confidence,
        "suggestion": "Would you like me to validate this?"
    }
```

**Implementation Guidance**:
- Replace ALL `confidence=1.0` with `MAX_CONFIDENCE` (0.95)
- Calibrate confidence scores against actual accuracy
- Low confidence → hedge language + cite sources
- Aged memories → prompt validation
- Conflicts → show both sources with confidence levels
- Make uncertainty visible in responses

**Confidence Tiers** (Vision lines 229-243):
```python
CONFIDENCE_TIERS = {
    (0.0, 0.5):   "uncertain",      # "Based on limited information..."
    (0.5, 0.8):   "moderate",       # "According to [source]..."
    (0.8, 0.95):  "high",           # "Confirmed: [fact]"
}

def generate_with_confidence(fact: str, confidence: float) -> str:
    tier = get_tier(confidence)

    if tier == "uncertain":
        return f"Based on limited information, {fact.lower()}. I recommend validating this."
    elif tier == "moderate":
        return f"According to our records, {fact}. (Confidence: {confidence:.0%})"
    else:
        return f"Confirmed: {fact}"
```

---

### 3. Learning from Usage

**Vision Statement** (lines 507-522):
> "The system adapts to its user and domain... This adaptation happens **automatically through usage patterns** - no explicit configuration needed."

**What It Means**:
- Track what works
- Learn from interactions
- Patterns emerge from usage data
- System improves without code changes

**Current Violations**:
```python
# ❌ VIOLATION: Hardcoded patterns
FINANCIAL_KEYWORDS = ["invoice", "payment", "owe"]
INTENT_MAPPINGS = {
    "financial": ["get_invoices", "get_payments"],
}

# ❌ VIOLATION: No usage tracking
def classify_intent(query):
    if any(kw in query for kw in FINANCIAL_KEYWORDS):
        return "financial"  # No learning, static forever
```

**Vision-Aligned Approach**:
```python
# ✅ ALIGNED: Track usage patterns
class UsageTracker:
    async def log_query(self, query: str, intent: str, tools_used: List[str]):
        """Log what happened."""
        await self.db.insert({
            "query": query,
            "predicted_intent": intent,
            "tools_called": tools_used,
            "timestamp": now(),
        })

    async def log_outcome(self, query_id: int, user_satisfaction: str):
        """Log if it worked."""
        await self.db.update(query_id, {
            "satisfaction": user_satisfaction,  # "helpful" | "not_helpful"
        })

# ✅ ALIGNED: Learn classifier from data
class LearnedIntentClassifier:
    async def train(self):
        """Train from logged usage."""
        data = await self.usage_tracker.get_training_data()
        # Queries where user was satisfied = positive examples
        # Queries where user corrected = negative examples

        self.model.fit(data.queries, data.intents)

    async def classify(self, query: str) -> Tuple[str, float]:
        intent = self.model.predict(query)
        confidence = self.model.predict_proba(query).max()
        return (intent, confidence)
```

**Implementation Guidance**:
- Log predictions + outcomes for every query
- Build training datasets from real usage
- Replace heuristics with learned models when data sufficient
- Track which memories prove useful (weight future retrieval)
- Learn aliases from successful fuzzy matches
- Discover new intent categories automatically
- Measure before/after accuracy to validate learning

**Learning Loop**:
```
1. Bootstrap: Use heuristics (marked as temporary)
2. Track: Log predictions + user satisfaction
3. Learn: Train model when ≥500 examples
4. A/B Test: Compare heuristic vs learned
5. Replace: Switch to learned when accuracy >90%
6. Repeat: Continuous improvement
```

---

### 4. Graceful Forgetting

**Vision Statement** (lines 69-85):
> "Forgetting is not a bug in memory; it's essential to intelligence... The system implements graceful forgetting: decay, consolidation, correction, active validation."

**What It Means**:
- Not all information is equally important
- Unreinforced memories fade (not deleted, deprioritized)
- Abstract details into summaries
- Mark outdated memories as superseded
- Proactively verify aged memories

**Current Violations**:
```python
# ❌ VIOLATION: All memories treated equally
memories = await retrieve_all(user_id)
# 1000+ memories, no prioritization, context overwhelm

# ❌ VIOLATION: No decay
# Memory from 6 months ago has same weight as yesterday
```

**Vision-Aligned Approach**:
```python
# ✅ ALIGNED: Temporal decay (Vision lines 106-109)
EPISODIC_HALF_LIFE_DAYS = 30
SEMANTIC_HALF_LIFE_DAYS = 90

def calculate_temporal_weight(memory: Memory, now: datetime) -> float:
    """Apply decay based on memory type."""
    days_old = (now - memory.created_at).days

    if memory.type == "episodic":
        half_life = EPISODIC_HALF_LIFE_DAYS
    else:
        half_life = SEMANTIC_HALF_LIFE_DAYS

    # Exponential decay
    decay_factor = 0.5 ** (days_old / half_life)

    # Reinforcement counteracts decay
    reinforcement_boost = 1 + (0.1 * memory.reinforcement_count)

    return decay_factor * reinforcement_boost

# ✅ ALIGNED: Consolidation (Vision lines 263-285)
class ConsolidationService:
    async def consolidate(self, entity_id: str, session_window: int = 5):
        """Replace N memories with 1 summary."""

        # Get recent episodic memories
        episodes = await self.repo.get_episodic(
            entity_id=entity_id,
            last_n_sessions=session_window,
        )

        if len(episodes) < 10:
            return None  # Not enough to consolidate

        # LLM creates summary
        summary = await self.llm.summarize(episodes)

        # Store summary memory
        summary_memory = await self.repo.create_summary(
            entity_id=entity_id,
            summary_text=summary,
            source_memory_ids=[e.id for e in episodes],
            confidence=0.8,  # Summaries have good confidence
        )

        # Mark episodes as consolidated (not deleted!)
        for episode in episodes:
            episode.status = "consolidated"
            episode.superseded_by = summary_memory.id
            await self.repo.update(episode)

        logger.info(
            "memories_consolidated",
            episode_count=len(episodes),
            summary_id=summary_memory.id,
        )

        return summary_memory

# ✅ ALIGNED: Active validation (Vision lines 362-365)
class ValidationService:
    async def check_for_stale_memories(self, memories: List[Memory]) -> List[Memory]:
        """Identify memories needing validation."""
        stale = []

        for mem in memories:
            days_since_validation = (now() - mem.last_validated_at).days

            if days_since_validation > 90 and mem.confidence < 0.7:
                stale.append(mem)

        return stale

    async def prompt_validation(self, memory: Memory) -> str:
        """Generate validation prompt for LLM."""
        return f"""
        We have this information on record: "{memory.content}"
        This was last validated {memory.days_old} days ago.
        Is this still accurate? If so, I'll update my confidence.
        """
```

**Implementation Guidance**:
- Apply temporal decay to all memories
- Different decay rates for different types (episodic faster than semantic)
- Consolidate after ≥10 episodes or ≥3 sessions
- Never delete memories—mark as superseded
- Validate memories >90 days old before using
- Retrieval prioritizes: recent + reinforced + high confidence

---

### 5. Ontology-Aware Reasoning

**Vision Statement** (lines 89-139):
> "The database isn't a flat collection of tables - it's a **graph of meaningful relationships** through which reasoning can flow."

**What It Means**:
- Relationships have semantic meaning ("fulfills", "obligates")
- Multi-hop reasoning across entities
- Graph traversal for answers
- Schema awareness enables intelligent querying

**Current Violations**:
```python
# ❌ VIOLATION: Flat query dispatch
if intent == "financial":
    queries = ["invoices"]  # Only one table

# ❌ VIOLATION: No relationship traversal
# "Can we invoice Gai Media?" needs:
# customer → sales_order → work_order → invoice (3 hops!)
# But system only looks at invoices table
```

**Vision-Aligned Approach**:
```python
# ✅ ALIGNED: LLM sees schema and traverses graph
tools = [
    {
        "name": "traverse_order_chain",
        "description": """
        Follow relationships: customer → sales_order → work_order → invoice.

        Relationships:
        - customer HAS_MANY sales_orders
        - sales_order FULFILLED_BY work_orders
        - sales_order GENERATES invoices

        Use this to answer questions about order status, invoicing readiness,
        completion state, or payment status.
        """,
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "include_completed": {"type": "boolean"}
            }
        }
    }
]

# ✅ ALIGNED: Multi-hop reasoning
# User: "Can we invoice Gai Media?"
# LLM thinks: "Need to check if work is done (WO) and invoice doesn't exist"
# LLM calls: traverse_order_chain(customer_id="abc", include_completed=False)
# Returns: {
#   "sales_orders": [{"so_id": "SO-1001", "status": "active"}],
#   "work_orders": [{"wo_id": "WO-5002", "status": "done"}],
#   "invoices": []
# }
# LLM: "Yes, work is done and no invoice exists yet."

# ✅ ALIGNED: Semantic relationships in schema
class OntologyService:
    async def get_schema_for_llm(self) -> Dict[str, Any]:
        """Provide schema with semantic relationships."""
        return {
            "tables": {
                "customers": {
                    "description": "Customer master data",
                    "key_fields": ["customer_id", "name", "payment_terms"]
                },
                "sales_orders": {
                    "description": "Sales orders from customers",
                    "key_fields": ["so_id", "customer_id", "status"]
                },
                "work_orders": {
                    "description": "Work fulfilling sales orders",
                    "key_fields": ["wo_id", "so_id", "status"]
                },
                "invoices": {
                    "description": "Customer invoices",
                    "key_fields": ["invoice_id", "customer_id", "status"]
                }
            },
            "relationships": [
                {
                    "from": "customers",
                    "to": "sales_orders",
                    "type": "HAS_MANY",
                    "semantic_meaning": "Customer places sales orders",
                    "join": "customers.customer_id = sales_orders.customer_id"
                },
                {
                    "from": "sales_orders",
                    "to": "work_orders",
                    "type": "FULFILLED_BY",
                    "semantic_meaning": "Sales order is fulfilled by work orders",
                    "join": "sales_orders.so_id = work_orders.so_id"
                },
                {
                    "from": "sales_orders",
                    "to": "invoices",
                    "type": "GENERATES",
                    "semantic_meaning": "Sales order generates invoice after fulfillment",
                    "join": "sales_orders.so_id = invoices.so_id"
                }
            ]
        }
```

**Implementation Guidance**:
- Provide full schema to LLM for query planning
- Include semantic meanings of relationships
- Tools should support multi-hop queries
- Graph traversal methods in domain DB port
- Entity resolution considers relationships
- Memory retrieval follows entity graph

---

### 6. Multi-Dimensional Relevance

**Vision Statement** (lines 172-184):
> "Text similarity is one dimension. But relevance is multi-dimensional: semantic similarity, entity overlap, temporal relevance, importance, reinforcement, usage patterns, intent alignment."

**What It Means**:
- Retrieval uses multiple signals, not just vector similarity
- Different query types need different signals
- Combine signals with learned weights
- Relevance is contextual

**Current Violations**:
```python
# ❌ VIOLATION: Single-signal retrieval
memories = await vector_db.similarity_search(
    query_embedding=query_vec,
    top_k=10
)
# Only uses semantic similarity, ignores all other signals

# ❌ VIOLATION: Fixed weights
final_score = 0.5 * semantic + 0.3 * entity + 0.2 * temporal
# Same weights for all queries (wrong!)
```

**Vision-Aligned Approach**:
```python
# ✅ ALIGNED: Multi-signal scoring (Vision lines 60-95 in heuristics.py)
RETRIEVAL_STRATEGY_WEIGHTS = {
    "factual_entity_focused": {
        "semantic_similarity": 0.25,
        "entity_overlap": 0.40,      # Entity mentions matter most
        "temporal_relevance": 0.20,
        "importance": 0.10,
        "reinforcement": 0.05,
    },
    "procedural": {
        "semantic_similarity": 0.45,
        "entity_overlap": 0.05,
        "temporal_relevance": 0.05,
        "importance": 0.15,
        "reinforcement": 0.30,        # Proven patterns matter most
    },
    "temporal": {
        "semantic_similarity": 0.20,
        "entity_overlap": 0.20,
        "temporal_relevance": 0.40,  # Recency matters most
        "importance": 0.15,
        "reinforcement": 0.05,
    },
}

class MultiSignalScorer:
    async def score(
        self,
        candidates: List[Memory],
        query: str,
        query_embedding: List[float],
        entities: List[str],
        strategy: str,
    ) -> List[Tuple[Memory, float, ScoreBreakdown]]:
        """Score using multiple signals with strategy-specific weights."""

        weights = RETRIEVAL_STRATEGY_WEIGHTS[strategy]
        scored = []

        for memory in candidates:
            # Calculate each signal
            semantic_sim = cosine_similarity(query_embedding, memory.embedding)
            entity_overlap = jaccard(entities, memory.entities)
            temporal_rel = self._temporal_relevance(memory.created_at)
            importance = memory.importance_score
            reinforcement = memory.reinforcement_count / 10.0  # Normalize

            # Weighted combination
            final_score = (
                weights["semantic_similarity"] * semantic_sim +
                weights["entity_overlap"] * entity_overlap +
                weights["temporal_relevance"] * temporal_rel +
                weights["importance"] * importance +
                weights["reinforcement"] * reinforcement
            )

            breakdown = ScoreBreakdown(
                semantic=semantic_sim,
                entity=entity_overlap,
                temporal=temporal_rel,
                importance=importance,
                reinforcement=reinforcement,
                weights=weights,
            )

            scored.append((memory, final_score, breakdown))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored

# ✅ ALIGNED: Strategy selection based on query intent
def select_strategy(query: str, entities: List[str]) -> str:
    """Choose retrieval strategy based on query characteristics."""

    query_lower = query.lower()

    # Temporal queries
    if any(word in query_lower for word in ["when", "recent", "latest", "yesterday"]):
        return "temporal"

    # Procedural queries
    if any(word in query_lower for word in ["how", "process", "steps", "workflow"]):
        return "procedural"

    # Factual queries (default)
    return "factual_entity_focused"
```

**Implementation Guidance**:
- Multi-signal scorer with breakdown visibility
- Strategy-specific weights (not one-size-fits-all)
- Learn optimal weights from usage patterns
- Explainable scores (show which signals contributed)
- Adaptive: adjust weights based on query type

---

### 7. Transparency and Explainability

**Vision Statement** (lines 422-460):
> "Transparency as Trust: Users trust what they understand. Explainability is not a feature; it's a requirement for adoption."

**What It Means**:
- Every fact citable to source
- Every retrieval traceable to scoring logic
- Every response shows reasoning chain
- Users can audit system's thinking

**Current Violations**:
```python
# ❌ VIOLATION: Black box response
response = await llm.generate(query)
return {"answer": response}  # No provenance, no scores, no reasoning

# ❌ VIOLATION: Hidden retrieval
memories = await retrieve(query)  # How were these selected? What scores?
```

**Vision-Aligned Approach**:
```python
# ✅ ALIGNED: Full provenance in response
response = {
    "answer": "Gai Media has invoice INV-1009 due Jan 15...",

    "provenance": {
        "memories_retrieved": [
            {
                "memory_id": 123,
                "content": "Gai Media prefers Friday deliveries",
                "confidence": 0.85,
                "source": "chat_event_456",
                "created_at": "2025-01-10",
                "relevance_score": 0.78,
                "score_breakdown": {
                    "semantic_similarity": 0.65,
                    "entity_overlap": 0.90,
                    "temporal_relevance": 0.85,
                }
            }
        ],
        "domain_facts": [
            {
                "fact_type": "invoice_status",
                "entity_id": "customer_abc",
                "content": {"invoice_number": "INV-1009", "status": "open"},
                "source_table": "domain.invoices",
                "source_row_id": 789,
            }
        ],
        "reasoning_chain": [
            "1. Resolved 'Gai Media' to customer_abc123",
            "2. Called get_invoices(customer_abc123)",
            "3. Retrieved memory about delivery preferences (relevance: 0.78)",
            "4. Synthesized response combining DB facts + memory context"
        ]
    },

    "metadata": {
        "memory_count": 3,
        "domain_fact_count": 2,
        "retrieval_strategy": "factual_entity_focused",
        "confidence": 0.87,
        "llm_model": "claude-haiku-4-5",
        "tokens_used": 2456,
    }
}

# ✅ ALIGNED: Audit trail API
@router.get("/api/v1/audit/{session_id}")
async def get_audit_trail(session_id: str):
    """Get full audit trail for a conversation."""
    return {
        "session_id": session_id,
        "turns": [
            {
                "turn_number": 1,
                "user_query": "What's the status for Gai Media?",
                "entities_resolved": [
                    {"mention": "Gai Media", "entity_id": "customer_abc", "method": "exact_match"}
                ],
                "memories_retrieved": [...],
                "domain_queries_executed": [
                    {"table": "invoices", "filters": {"customer_id": "abc"}}
                ],
                "response": "...",
                "reasoning": "..."
            }
        ]
    }
```

**Implementation Guidance**:
- Return provenance with every response
- Include memory IDs + similarity scores
- Include DB table + row IDs for facts
- Show reasoning chain (what system did)
- Expose retrieval strategy used
- API endpoint for full audit trail
- Log everything for debugging/analysis

---

### 8. Emergent Intelligence

**Vision Statement** (lines 467-485):
> "Intelligence isn't programmed - it emerges from interaction of simple mechanisms: Extract → Store → Decay → Retrieve → Augment → Consolidate → Learn."

**What It Means**:
- Complex behavior from simple rules
- No hardcoded intelligence
- Patterns emerge from usage
- System becomes more than sum of parts

**Current Violations**:
```python
# ❌ VIOLATION: Programmed intelligence
INTENT_MAPPINGS = {
    "financial": ["get_invoices", "get_payments"],
    "operational": ["get_work_orders", "get_tasks"],
}
# Developer encoded all patterns (static, doesn't improve)

# ❌ VIOLATION: No emergence
# System does exactly what we programmed, nothing more
```

**Vision-Aligned Approach**:
```python
# ✅ ALIGNED: Simple mechanisms that enable emergence

# Mechanism 1: Extract entities and facts
entities = await extract_entities(message)
facts = await extract_facts(message, entities)

# Mechanism 2: Store with embeddings + confidence
for fact in facts:
    memory = await create_memory(fact)
    await store_memory(memory)

# Mechanism 3: Decay based on age + reinforcement
for memory in memories:
    memory.confidence *= decay_factor(memory.age)
    memory.confidence *= (1 + 0.1 * memory.reinforcement_count)

# Mechanism 4: Retrieve using multi-signal scoring
candidates = await vector_search(query_embedding)
scored = await multi_signal_score(candidates, query, entities)
top_memories = scored[:10]

# Mechanism 5: Augment with domain facts
domain_facts = await llm_tool_calling(query, entities, schema)

# Mechanism 6: Consolidate periodically
if session_count >= 3 and episode_count >= 10:
    summary = await consolidate(entity_id)

# Mechanism 7: Learn from usage
await track_query(query, intent, tools_used, user_satisfaction)
if training_examples >= 500:
    await train_classifier()

# ✅ EMERGENT BEHAVIORS (not programmed, they emerge):
# - System remembers what matters (via importance + reinforcement)
# - Gets more confident about stable facts (via reinforcement)
# - Questions aged information (via decay)
# - Learns entity aliases (via fuzzy match → alias creation)
# - Surfaces relevant context automatically (via multi-signal retrieval)
# - Improves disambiguation (via alias use tracking)
# - Builds domain understanding (via consolidation)
# - Adapts to new domains (via LLM tool calling + schema)
```

**Implementation Guidance**:
- Design simple, composable mechanisms
- Avoid hardcoding patterns
- Track everything for learning
- Let intelligence emerge from usage
- Measure emergent properties (accuracy, recall, adaptation)
- Trust the process—complexity emerges from simplicity

---

## Architectural Patterns for Vision Alignment {#patterns}

### Pattern 1: LLM as Reasoning Engine

**Problem**: Hardcoded rules don't capture semantic understanding

**Solution**: LLM with tool calling for dynamic query planning

```python
class VisionAlignedOrchestrator:
    """Orchestrator using LLM as reasoning engine."""

    async def process(self, query: str, entities: List[Entity]) -> Response:
        # Phase 1: Entity resolution (deterministic, fast)
        resolved = await self.resolve_entities(query)

        # Phase 2: LLM decides what data to fetch (tool calling)
        response = await self.llm.chat_with_tools(
            query=query,
            entities=resolved,
            tools=self.define_domain_tools(),
            system_prompt=self.build_prompt_with_schema(),
        )

        # Phase 3: LLM synthesizes response with fetched data
        # (happens automatically during tool calling)

        return response
```

**Benefits**:
- Context-aware (not keyword-based)
- Adaptive (new tools = automatic usage)
- Ontology-aware (sees schema)
- Emergent (intelligent behavior from LLM + tools)

---

### Pattern 2: Confidence-Driven Behavior

**Problem**: System acts with same certainty regardless of evidence quality

**Solution**: Confidence determines system behavior

```python
class ConfidenceDrivenService:
    """Service that adapts behavior based on confidence."""

    async def act_on_memory(self, memory: Memory) -> Action:
        confidence = self.calibrate_confidence(memory)

        if confidence >= 0.90:
            # High confidence: Act without qualification
            return DirectAction(memory.content)

        elif confidence >= 0.60:
            # Medium confidence: Act but cite source
            return QualifiedAction(
                memory.content,
                citation=f"According to {memory.source} from {memory.created_at}",
                confidence=confidence,
            )

        else:
            # Low confidence: Validate before using
            return ValidationRequest(
                memory.content,
                reason=f"This information is {memory.days_old} days old",
                suggested_validation="Is this still accurate?",
            )
```

---

### Pattern 3: Learning Loop

**Problem**: System doesn't improve from usage

**Solution**: Track → Measure → Learn → Replace

```python
class LearningLoop:
    """Continuous improvement from usage patterns."""

    async def track(self, query: str, prediction: str, tools_used: List[str]):
        """Track what system did."""
        await self.tracker.log_query(query, prediction, tools_used)

    async def measure(self, query_id: int, user_satisfied: bool):
        """Measure if it worked."""
        await self.tracker.log_outcome(query_id, user_satisfied)

    async def learn(self):
        """Learn from tracked data."""
        data = await self.tracker.get_training_data(min_examples=500)

        if len(data) >= 500:
            model = await self.trainer.train(data)
            accuracy = await self.validator.test(model)

            if accuracy > 0.90:
                logger.info("learned_model_ready", accuracy=accuracy)
                return model

        return None

    async def replace(self, new_model):
        """Replace heuristic with learned model."""
        self.active_model = new_model
        logger.info("heuristic_replaced_with_learned_model")
```

---

### Pattern 4: Graph-Aware Retrieval

**Problem**: Retrieval ignores relationships between entities

**Solution**: Traverse entity graph during retrieval

```python
class GraphAwareRetriever:
    """Retrieve memories by following entity relationships."""

    async def retrieve(
        self,
        query: str,
        entities: List[Entity],
        max_hops: int = 2,
    ) -> List[Memory]:
        # Start with direct matches
        direct = await self.vector_search(query, entities)

        # Expand via graph traversal
        related_entities = await self.traverse_graph(entities, max_hops)
        indirect = await self.vector_search(query, related_entities)

        # Combine and re-rank
        all_candidates = direct + indirect
        scored = await self.multi_signal_score(
            all_candidates,
            query,
            entities,
            decay=True,
            boost_related=True,
        )

        return scored[:10]
```

---

### Pattern 5: Provenance-First Design

**Problem**: Can't explain why system said something

**Solution**: Track provenance through entire pipeline

```python
@dataclass
class ProvenanceChain:
    """Track every step of reasoning."""

    query: str
    entities_resolved: List[Tuple[str, str, float]]  # (mention, entity_id, confidence)
    tools_called: List[Tuple[str, Dict, Any]]  # (tool_name, args, result)
    memories_retrieved: List[Tuple[int, float, Dict]]  # (id, score, breakdown)
    domain_facts: List[DomainFact]
    reasoning_steps: List[str]
    final_confidence: float

class ProvenanceAwareService:
    """Service that tracks provenance."""

    async def process(self, query: str) -> Tuple[Response, ProvenanceChain]:
        chain = ProvenanceChain(query=query)

        # Track each step
        entities = await self.resolve_entities(query)
        chain.entities_resolved = [(e.mention, e.entity_id, e.confidence) for e in entities]

        tools_used = await self.llm_tool_calling(query, entities)
        chain.tools_called = tools_used

        memories = await self.retrieve_memories(query, entities)
        chain.memories_retrieved = [(m.id, m.score, m.breakdown) for m in memories]

        response = await self.generate_response(query, tools_used, memories)
        chain.final_confidence = response.confidence

        return (response, chain)
```

---

## System-Wide Alignment Strategy {#strategy}

### Phase 0: Foundation (Week 1)

**Goal**: Fix critical violations

**Actions**:
1. Replace all `confidence=1.0` with `MAX_CONFIDENCE` (0.95)
2. Add provenance tracking to existing responses
3. Implement basic usage logging
4. Run full test suite, ensure no regressions

**Success Criteria**:
- Zero instances of `confidence=1.0`
- All responses include provenance
- Usage data flowing to logs

---

### Phase 1: LLM Tool Use (Weeks 2-3)

**Goal**: Replace keyword intent with LLM reasoning

**Actions**:
1. Add tool calling to `AnthropicLLMService`
2. Define 5-6 core domain tools
3. Update `LLMReplyGenerator` to use tools
4. A/B test: keywords vs tool calling
5. Measure: accuracy, latency, user satisfaction

**Success Criteria**:
- Tool calling works with Haiku 4.5
- Accuracy ≥ keywords (ideally better)
- Latency ≤ 600ms (p95)
- Users prefer tool-based responses

---

### Phase 2: Learning Infrastructure (Month 2)

**Goal**: Enable learning from usage

**Actions**:
1. Structured usage tracking (predictions + outcomes)
2. Training data builder
3. Learned intent classifier (logistic regression)
4. Confidence calibrator
5. Replace keywords when learned accuracy >90%

**Success Criteria**:
- ≥500 tracked queries with outcomes
- Learned classifier accuracy >90%
- Calibrated confidence (predicted ≈ actual)
- Zero keyword lists in production code

---

### Phase 3: Adaptive Behaviors (Month 3+)

**Goal**: Emergent intelligence from usage

**Actions**:
1. Online learning (continuous updates)
2. Active learning (ask when uncertain)
3. Auto-discover new intent categories
4. Adaptive retrieval weights
5. Self-improving consolidation

**Success Criteria**:
- System discovers new patterns without code changes
- Accuracy improves over time automatically
- Adapts to new domains zero-shot
- Emergent behaviors documented

---

## Implementation Checklist by Component {#checklist}

### Entity Resolution Service

- [ ] Max confidence = 0.95 (not 1.0)
- [ ] Auto-create aliases from fuzzy matches
- [ ] Track alias usage for learning
- [ ] Calibrate confidence scores
- [ ] Express uncertainty when ambiguous
- [ ] Provenance: return resolution method + score

### Domain Augmentation Service

- [ ] Replace keyword intent with LLM tool calling
- [ ] Provide full schema to LLM
- [ ] Tools support multi-hop queries
- [ ] Track which tools prove useful
- [ ] Remove hardcoded query mappings
- [ ] Provenance: return tools called + results

### Memory Retrieval Service

- [ ] Multi-signal scoring (not just vectors)
- [ ] Strategy-specific weights
- [ ] Graph-aware retrieval (follow entity relationships)
- [ ] Apply temporal decay
- [ ] Boost reinforced memories
- [ ] Provenance: return score breakdown

### LLM Reply Generator

- [ ] Tool calling integration
- [ ] Confidence-driven language
- [ ] Cite sources for claims
- [ ] Express uncertainty explicitly
- [ ] Validation prompts for aged memories
- [ ] Provenance: return reasoning chain

### Consolidation Service

- [ ] Trigger after ≥10 episodes
- [ ] LLM-generated summaries
- [ ] Mark source memories as consolidated (not deleted)
- [ ] Summaries get confidence boost
- [ ] Track consolidation quality
- [ ] Provenance: return source memory IDs

### Conflict Resolution Service

- [ ] Detect memory-vs-DB conflicts
- [ ] Detect memory-vs-memory conflicts
- [ ] Confidence-based strategies
- [ ] Make conflicts explicit (don't silently choose)
- [ ] Track resolution outcomes
- [ ] Provenance: return both sources + rationale

---

## Anti-Patterns and How to Avoid Them {#antipatterns}

### Anti-Pattern 1: Keyword Overfitting

**Symptom**:
```python
if "invoice" in query:
    intent = "financial"
```

**Why It's Wrong**: Context-free, brittle, doesn't learn

**Fix**: LLM tool calling (context-aware, adaptive)

---

### Anti-Pattern 2: Perfect Certainty

**Symptom**:
```python
confidence = 1.0  # DB is authoritative
```

**Why It's Wrong**: Violates epistemic humility, no room for correction

**Fix**: `MAX_CONFIDENCE = 0.95`, calibration

---

### Anti-Pattern 3: Black Box Responses

**Symptom**:
```python
return {"answer": llm_response}  # No provenance
```

**Why It's Wrong**: Not explainable, can't audit, hard to debug

**Fix**: Return provenance with every response

---

### Anti-Pattern 4: Static Behavior

**Symptom**:
```python
MAPPINGS = {...}  # Hardcoded, never changes
```

**Why It's Wrong**: Doesn't learn, doesn't adapt, requires code changes

**Fix**: Track usage, learn from patterns, replace with models

---

### Anti-Pattern 5: Single-Signal Retrieval

**Symptom**:
```python
memories = vector_db.search(query_embedding)  # Only similarity
```

**Why It's Wrong**: Ignores entity overlap, temporal relevance, importance

**Fix**: Multi-signal scoring with strategy-specific weights

---

### Anti-Pattern 6: Forgetting by Deletion

**Symptom**:
```python
await db.delete(old_memory)  # Lose history
```

**Why It's Wrong**: Can't explain reasoning, can't learn from past

**Fix**: Mark as superseded, keep audit trail

---

### Anti-Pattern 7: Context-Free Meaning

**Symptom**:
```python
# Same query, different context → same result
answer = process(query)  # No user, no session, no entities
```

**Why It's Wrong**: Meaning depends on context

**Fix**: Pass user, session, entities, history to all components

---

## Measurement: Are We Vision-Aligned? {#measurement}

### Quantitative Metrics

#### Correctness (Correspondence Truth)
- DB facts cited: ≥95% accurate
- Entity resolution: ≥95% precision
- Semantic extraction: ≥90% precision

#### Relevance (Contextual Truth)
- Retrieved memories used: ≥90%
- User satisfaction: ≥80% "helpful"
- Preference recall: ≥85% across sessions

#### Efficiency
- p95 latency: ≤800ms
- LLM cost: ≤$0.005 per query
- Memory footprint: ≤50 memories per response

#### Learning
- Classifier accuracy: ≥90% vs baseline
- Confidence calibration: predicted ≈ actual (±5%)
- Adaptation rate: discovers new patterns monthly

#### Consistency
- Entity resolution: ≥95% after disambiguation
- Conflict detection: 100% memory-vs-DB conflicts caught
- Consolidation quality: ≥85% user approval

---

### Qualitative Indicators

#### Feels Like a Colleague
- [ ] Users stop re-stating known preferences
- [ ] Conversations feel continuous across sessions
- [ ] Users trust responses without always verifying
- [ ] Disambiguation requests decrease over time
- [ ] Users proactively correct the system
- [ ] System catches issues before users notice

#### Epistemic Humility
- [ ] System admits uncertainty when appropriate
- [ ] Low confidence → hedge language + sources
- [ ] Aged memories → validation prompts
- [ ] Conflicts → both sources shown
- [ ] Users feel system is honest about limitations

#### Adaptive Intelligence
- [ ] Accuracy improves over time without code changes
- [ ] System handles new domains zero-shot
- [ ] Learns entity aliases automatically
- [ ] Discovers new intent categories from usage
- [ ] Retrieval weights adapt to query patterns

#### Transparency
- [ ] Every response citable to sources
- [ ] Audit trail available for all decisions
- [ ] Users understand why system said something
- [ ] Debugging is straightforward (provenance chain)
- [ ] Errors are traceable to root cause

---

### The Ultimate Test

After extended use, if the system were removed, users would feel like they **lost a knowledgeable colleague**—not just a tool, but a memory layer that had become integrated into their workflow.

**This is the vision.** This is what we're building.

---

## Conclusion: The Path Forward

The vision isn't a feature list. It's a philosophy of what intelligence looks like:

- **Not programmed** → Emergent from simple mechanisms
- **Not static** → Learning continuously from usage
- **Not brittle** → Adaptive to context and domain
- **Not certain** → Epistemically humble about knowledge
- **Not opaque** → Transparent and explainable
- **Not isolated** → Graph-aware and relationship-conscious
- **Not forgetful** → Perfect recall of what matters
- **Not mechanical** → Colleague-like in interaction

Every architectural decision should serve this vision. Every line of code should ask: "Does this make the system more like an experienced colleague?"

**The roadmap**:
1. Fix critical violations (epistemic humility, provenance)
2. Replace keywords with LLM tool calling (context-aware)
3. Build learning infrastructure (track → learn → adapt)
4. Enable emergent intelligence (simple rules → complex behavior)

**The north star**: A cognitive entity that transforms business data from "rows in tables" into "meaningful knowledge in context"—enabling an AI agent to reason with both the **precision of databases** and the **understanding of human memory**.

That is the vision. That is what's possible. That is what we build. 🚀
