# Intelligent Memory System: Master Architecture

**Version:** 3.0
**Date:** 2024
**Status:** Production-Ready Blueprint

---

## Table of Contents

1. [Architecture Philosophy](#architecture-philosophy)
2. [System Overview](#system-overview)
3. [Core Architectural Principles](#core-architectural-principles)
4. [Component Architecture](#component-architecture)
5. [Intelligence Layer (DETAILED)](#intelligence-layer-detailed)
6. [Data Flow & Integration](#data-flow--integration)
7. [Implementation Roadmap](#implementation-roadmap)

---

## Architecture Philosophy

### What Makes This Architecture Excellent

This architecture is designed around three core pillars:

**1. Intelligence-First Design**
- Pattern recognition, synthesis, and decision support are NOT stretch goals
- They are core architectural components, specified with same rigor as database schemas
- Every response demonstrates intelligence, not just data retrieval

**2. Production-Ready Infrastructure**
- Redis, Celery, PostgreSQL with proper HA strategies
- Security hardened (SQL injection prevention, input validation)
- Monitored, observable, cost-optimized

**3. Clear Implementation Path**
- Every major component has a class specification
- Interfaces are explicit
- Data flows are documented
- Developers know exactly what to build

### Why Previous Architectures Fall Short

**Common Pattern**: Excellent infrastructure + vague intelligence layer
```
✅ Redis setup: 200 lines of specification
✅ Celery configuration: 150 lines of specification
❌ Pattern detection: "TODO: implement pattern analysis"
❌ Decision support: Week 10 checkbox
```

**This Architecture**: Equal rigor across all layers
```
✅ Redis setup: Fully specified
✅ Pattern detection: Class definition + algorithms + integration
✅ Decision support: Framework + prompt templates + evaluation criteria
✅ Synthesis: Response generator with quality gates
```

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                             │
│                      (Natural Language Query)                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                               │
│                                                                      │
│  ┌────────────────────┐  ┌────────────────────┐                    │
│  │ Request Handler    │  │ Conversation       │                    │
│  │ - Route request    │  │ Context Manager    │                    │
│  │ - Coordinate flow  │  │ - Session state    │                    │
│  └────────────────────┘  └────────────────────┘                    │
└─────────────┬───────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     INTELLIGENCE LAYER                               │
│                   (This is what makes it smart)                      │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ Entity Resolver  │  │ Memory Retriever │  │ Pattern Analyzer │ │
│  │ - NER + linking  │  │ - Vector search  │  │ - Detect trends  │ │
│  │ - Disambiguation │  │ - Ranking        │  │ - Find insights  │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ Context          │  │ Decision         │  │ Response         │ │
│  │ Synthesizer      │  │ Support Engine   │  │ Generator        │ │
│  │ - Combine sources│  │ - Multi-dim      │  │ - Quality gates  │ │
│  │ - Enrich context │  │   analysis       │  │ - Formatting     │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
└─────────────┬───────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STORAGE & INFRASTRUCTURE LAYER                    │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ PostgreSQL       │  │ Redis            │  │ Celery           │ │
│  │ - Domain data    │  │ - Session state  │  │ - Async tasks    │ │
│  │ - Memories       │  │ - Cache          │  │ - Workflows      │ │
│  │ - Patterns       │  │ - Job queue      │  │ - Batch jobs     │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Layer | Components | Responsibility | Complexity |
|-------|-----------|----------------|------------|
| **Orchestration** | RequestHandler, ConversationContextManager | Route requests, maintain session state | Medium |
| **Intelligence** | EntityResolver, MemoryRetriever, PatternAnalyzer, ContextSynthesizer, DecisionSupportEngine, ResponseGenerator | Make the system smart | High |
| **Storage** | PostgreSQL, Redis, Celery | Reliable data persistence and processing | Medium |

---

## Core Architectural Principles

### 1. Separation of Intelligence from Infrastructure

**Bad Architecture**:
```python
def chat(user_query):
    # All logic mixed together
    entities = extract_entities(user_query)
    memories = db.query("SELECT * FROM memories WHERE ...")
    patterns = db.query("SELECT COUNT(*) FROM orders WHERE ...")
    response = llm.call(f"Answer: {user_query}")
    return response
```

**Good Architecture**:
```python
def chat(user_query):
    # Clear separation of concerns
    context = orchestrator.build_context(user_query)
    enriched = intelligence.enrich_with_patterns(context)
    response = intelligence.synthesize_response(enriched)
    memory.store_interaction(response)
    return response
```

### 2. Explicit Interfaces

Every component has a clear contract:

```python
class Intelligence:
    """Abstract interface for intelligence components"""

    @abstractmethod
    def process(self, context: Context) -> Result:
        """Process input and return structured result"""
        pass

    @abstractmethod
    def get_confidence(self) -> float:
        """Return confidence in result"""
        pass
```

### 3. Testability

Each component can be tested in isolation:

```python
# Can test pattern analyzer without DB
pattern_analyzer = PatternAnalyzer()
result = pattern_analyzer.analyze_rush_orders(mock_order_data)
assert result.conversion_probability == 0.85

# Can test synthesizer without LLM
synthesizer = ContextSynthesizer()
response = synthesizer.build_context(mock_facts, mock_patterns)
assert "payment terms" in response.context
```

### 4. Progressive Enhancement

System works at multiple sophistication levels:

- **Week 1-4**: Basic memory + retrieval (useful)
- **Week 5-6**: + Workflow automation (more useful)
- **Week 7-8**: + Pattern detection (intelligent)
- **Week 9-10**: + Decision support (strategic partner)

Each stage delivers value.

---

## Component Architecture

### Layer 1: Orchestration (Already Well-Specified)

Refer to existing `Architecture_Flow_Complete.md` for:
- ✅ ConversationContextManager (Redis-based, fully specified)
- ✅ WorkflowEngine (Event-driven, fully specified)
- ✅ Performance optimization strategies

These are excellent and need no changes.

---

## Intelligence Layer (DETAILED)

This section provides the same level of specification for intelligence components as the existing architecture provides for infrastructure.

### Component 1: Entity Resolver

**Purpose**: Convert natural language entity references to database entities with confidence.

**Interface**:
```python
@dataclass
class ResolvedEntity:
    entity_id: str              # "customer-delta-industries"
    entity_type: str            # "customer"
    entity_name: str            # "Delta Industries"
    confidence: float           # 0.95
    disambiguation_needed: bool # False
    candidates: List[Entity]    # [] (empty if no ambiguity)

class EntityResolver:
    """
    Resolves natural language entity references to database entities.

    Flow:
    1. NER extraction (spaCy)
    2. Exact match lookup (domain.customers)
    3. Fuzzy match (if no exact match)
    4. Disambiguation (if multiple matches)
    5. Confidence scoring
    """

    def resolve(self,
                text: str,
                context: ConversationContext) -> List[ResolvedEntity]:
        """
        Main entry point for entity resolution.

        Args:
            text: User query
            context: Current conversation context (helps disambiguation)

        Returns:
            List of resolved entities with confidence scores
        """
        pass

    def extract_entities(self, text: str) -> List[str]:
        """Extract entity mentions using NER"""
        pass

    def match_to_database(self,
                          mention: str,
                          entity_type: str) -> List[Match]:
        """Match entity mention to database records"""
        pass

    def disambiguate(self,
                     candidates: List[Match],
                     context: ConversationContext) -> ResolvedEntity:
        """Resolve ambiguity using context"""
        pass
```

**Implementation Detail**:

```python
def match_to_database(self, mention: str, entity_type: str) -> List[Match]:
    """
    Match entity mention to database records.

    Strategy:
    1. Exact match (case-insensitive)
    2. Fuzzy match (Levenshtein distance)
    3. Alias lookup (app.entity_aliases)
    4. Phonetic match (for names)
    """

    matches = []

    # Step 1: Exact match
    exact = self.db.query_one("""
        SELECT customer_id, name
        FROM domain.customers
        WHERE LOWER(name) = LOWER(%s)
    """, (mention,))

    if exact:
        return [Match(
            entity_id=exact['customer_id'],
            entity_name=exact['name'],
            match_type='exact',
            confidence=0.95,
            similarity=1.0
        )]

    # Step 2: Fuzzy match
    all_customers = self.db.query("""
        SELECT customer_id, name
        FROM domain.customers
        WHERE name % %s  -- PostgreSQL trigram similarity
        ORDER BY similarity(name, %s) DESC
        LIMIT 5
    """, (mention, mention))

    for customer in all_customers:
        similarity = calculate_similarity(mention, customer['name'])

        if similarity >= 0.85:  # Threshold for fuzzy match
            matches.append(Match(
                entity_id=customer['customer_id'],
                entity_name=customer['name'],
                match_type='fuzzy',
                confidence=similarity * 0.9,  # Slight penalty for fuzzy
                similarity=similarity
            ))

    # Step 3: Alias lookup
    alias_matches = self.db.query("""
        SELECT entity_id, canonical_name
        FROM app.entity_aliases
        WHERE alias = %s
    """, (mention,))

    for alias in alias_matches:
        matches.append(Match(
            entity_id=alias['entity_id'],
            entity_name=alias['canonical_name'],
            match_type='alias',
            confidence=0.92,
            similarity=1.0
        ))

    return matches
```

**Disambiguation Logic**:

```python
def disambiguate(self,
                 candidates: List[Match],
                 context: ConversationContext) -> ResolvedEntity:
    """
    Resolve ambiguity using multiple signals.

    Scoring factors:
    1. Match similarity (0-1.0)
    2. Conversation recency (0-0.3 boost)
    3. User interaction frequency (0-0.2 boost)
    4. Active work (0-0.1 boost)
    """

    scored_candidates = []

    for candidate in candidates:
        score = candidate.confidence  # Base: similarity score

        # Boost if mentioned recently in conversation
        if candidate.entity_id in context.recent_entities:
            last_turn = context.get_last_mention(candidate.entity_id)
            recency_boost = max(0, 0.3 * (1 - last_turn / 10))  # Decay over 10 turns
            score += recency_boost

        # Boost if user frequently discusses this entity
        interaction_count = self.db.query_one("""
            SELECT COUNT(*)
            FROM app.memories
            WHERE user_id = %s
            AND %s = ANY(entity_links)
            AND created_at > NOW() - INTERVAL '30 days'
        """, (context.user_id, candidate.entity_id))

        frequency_boost = min(0.2, interaction_count / 50)
        score += frequency_boost

        # Boost if entity has active work
        has_active_work = self.db.query_one("""
            SELECT EXISTS(
                SELECT 1 FROM domain.work_orders
                WHERE customer_id = %s
                AND status IN ('queued', 'in_progress')
            )
        """, (candidate.entity_id,))

        if has_active_work:
            score += 0.1

        scored_candidates.append((candidate, score))

    # Sort by score
    scored_candidates.sort(key=lambda x: x[1], reverse=True)

    top_candidate, top_score = scored_candidates[0]

    # Auto-resolve if clear winner
    if len(scored_candidates) == 1:
        return ResolvedEntity(
            entity_id=top_candidate.entity_id,
            entity_name=top_candidate.entity_name,
            confidence=top_score,
            disambiguation_needed=False,
            candidates=[]
        )

    second_score = scored_candidates[1][1]

    # Auto-resolve if score significantly higher (2x threshold)
    if top_score >= 0.8 and top_score / second_score >= 2.0:
        return ResolvedEntity(
            entity_id=top_candidate.entity_id,
            entity_name=top_candidate.entity_name,
            confidence=top_score,
            disambiguation_needed=False,
            candidates=[c[0] for c in scored_candidates[1:]]  # Store alternatives
        )

    # Disambiguation needed
    return ResolvedEntity(
        entity_id=top_candidate.entity_id,  # Best guess
        entity_name=top_candidate.entity_name,
        confidence=top_score,
        disambiguation_needed=True,
        candidates=[c[0] for c in scored_candidates]  # All candidates for user
    )
```

**Integration**:
```python
# In main request handler
entities = entity_resolver.resolve(user_query, conversation_context)

for entity in entities:
    if entity.disambiguation_needed:
        # Return disambiguation prompt to user
        return build_disambiguation_prompt(entity)

# Continue with resolved entities
context = build_context(entities)
```

**Testing**:
```python
def test_exact_match():
    resolver = EntityResolver(mock_db)
    result = resolver.resolve("Delta Industries", empty_context)

    assert len(result) == 1
    assert result[0].entity_name == "Delta Industries"
    assert result[0].confidence >= 0.95
    assert not result[0].disambiguation_needed

def test_fuzzy_match():
    resolver = EntityResolver(mock_db)
    result = resolver.resolve("Kay Media", empty_context)

    assert len(result) == 1
    assert result[0].entity_name == "Kai Media"
    assert result[0].match_type == "fuzzy"
    assert result[0].confidence >= 0.85

def test_disambiguation():
    resolver = EntityResolver(mock_db)
    # Assume 3 "Delta" companies exist
    result = resolver.resolve("Delta", empty_context)

    assert result[0].disambiguation_needed == True
    assert len(result[0].candidates) == 3
```

---

### Component 2: Pattern Analyzer

**Purpose**: Detect patterns in data that provide business insights.

**Interface**:
```python
@dataclass
class PatternInsight:
    pattern_type: str           # "rush_order_frequency", "payment_timing_shift"
    entity_id: str              # Customer this applies to
    confidence: float           # 0.85
    significance: float         # How important is this? 0.75
    insight: str                # Human-readable insight
    data: Dict[str, Any]        # Supporting data
    recommendation: Optional[str] # What to do about it
    historical_precedents: List[str] # Similar patterns in other customers

class PatternAnalyzer:
    """
    Analyzes historical data to discover business patterns.

    Runs in two modes:
    1. Real-time: During query processing (lightweight checks)
    2. Batch: Nightly jobs (heavy statistical analysis)
    """

    def analyze_entity(self, entity_id: str) -> List[PatternInsight]:
        """Analyze all patterns for a specific entity"""
        pass

    def detect_rush_order_pattern(self, customer_id: str) -> Optional[PatternInsight]:
        """Detect rush order frequency patterns"""
        pass

    def detect_payment_timing_shift(self, customer_id: str) -> Optional[PatternInsight]:
        """Detect changes in payment timing behavior"""
        pass

    def detect_anomalies(self, customer_id: str) -> List[PatternInsight]:
        """Detect unusual patterns (5 unbilled WOs, etc.)"""
        pass

    def cross_entity_comparison(self,
                                pattern_type: str,
                                entity_id: str) -> List[str]:
        """Find similar entities with same pattern"""
        pass
```

**Implementation Detail**:

```python
def detect_rush_order_pattern(self, customer_id: str) -> Optional[PatternInsight]:
    """
    Detect if customer shows signs of retainer conversion readiness.

    Pattern: 3+ rush orders in 6 months indicates potential for retainer agreement.

    Analysis approach:
    1. Count rush orders in last 6 months
    2. Calculate frequency trend (accelerating?)
    3. Compare to historical conversion data
    4. Compute confidence and significance
    """

    # Step 1: Get rush order history
    rush_orders = self.db.query("""
        SELECT
            sales_order_id,
            created_at,
            amount
        FROM domain.sales_orders
        WHERE customer_id = %s
        AND priority = 'rush'
        AND created_at > NOW() - INTERVAL '6 months'
        ORDER BY created_at ASC
    """, (customer_id,))

    if len(rush_orders) < 3:
        return None  # Pattern doesn't apply

    # Step 2: Calculate time between orders (frequency)
    intervals = []
    for i in range(1, len(rush_orders)):
        days_between = (rush_orders[i]['created_at'] -
                       rush_orders[i-1]['created_at']).days
        intervals.append(days_between)

    avg_interval = sum(intervals) / len(intervals)

    # Check if accelerating (intervals getting shorter)
    if len(intervals) >= 2:
        early_avg = sum(intervals[:len(intervals)//2]) / (len(intervals)//2)
        late_avg = sum(intervals[len(intervals)//2:]) / (len(intervals) - len(intervals)//2)
        is_accelerating = late_avg < early_avg
    else:
        is_accelerating = False

    # Step 3: Historical comparison
    # Find customers with similar pattern who converted to retainer
    conversion_rate = self.db.query_one("""
        WITH similar_customers AS (
            SELECT DISTINCT customer_id
            FROM domain.sales_orders
            WHERE priority = 'rush'
            AND created_at > NOW() - INTERVAL '12 months'
            GROUP BY customer_id
            HAVING COUNT(*) >= 3
        ),
        retainer_customers AS (
            SELECT DISTINCT customer_id
            FROM domain.sales_orders
            WHERE order_type = 'retainer'
        )
        SELECT
            COUNT(DISTINCT CASE WHEN r.customer_id IS NOT NULL THEN s.customer_id END)::float /
            COUNT(DISTINCT s.customer_id) as conversion_rate
        FROM similar_customers s
        LEFT JOIN retainer_customers r ON s.customer_id = r.customer_id
    """)

    # Step 4: Compute confidence and significance
    confidence = 0.7  # Base confidence

    # Boost confidence if accelerating
    if is_accelerating:
        confidence += 0.1

    # Boost confidence if high conversion rate
    if conversion_rate and conversion_rate['conversion_rate'] > 0.75:
        confidence += 0.1

    # Significance = how important is this insight?
    significance = min(1.0, len(rush_orders) / 5)  # More orders = more significant

    # Step 5: Build insight
    total_value = sum(order['amount'] for order in rush_orders)

    insight = f"""Customer has placed {len(rush_orders)} rush orders in past 6 months.
Historical data: {int(conversion_rate['conversion_rate'] * 100)}% of customers with this pattern convert to retainer agreements.
Total rush order value: ${total_value:,.0f}
Average time between orders: {int(avg_interval)} days{' (accelerating)' if is_accelerating else ''}"""

    recommendation = f"""Consider proposing retainer structure:
- Guarantees predictable capacity for customer
- Provides revenue stability
- Typical structure: ${int(total_value / 6):,.0f}/month baseline"""

    # Step 6: Find similar customers
    precedents = self.db.query("""
        WITH similar AS (
            SELECT customer_id, COUNT(*) as rush_count
            FROM domain.sales_orders
            WHERE priority = 'rush'
            AND created_at > NOW() - INTERVAL '6 months'
            AND customer_id != %s
            GROUP BY customer_id
            HAVING COUNT(*) >= 3
        )
        SELECT c.name
        FROM similar s
        JOIN domain.customers c ON s.customer_id = c.customer_id
        JOIN domain.sales_orders so ON s.customer_id = so.customer_id
        WHERE so.order_type = 'retainer'
        LIMIT 5
    """, (customer_id,))

    return PatternInsight(
        pattern_type="rush_order_frequency",
        entity_id=customer_id,
        confidence=confidence,
        significance=significance,
        insight=insight,
        data={
            "rush_order_count": len(rush_orders),
            "avg_interval_days": avg_interval,
            "total_value": total_value,
            "is_accelerating": is_accelerating,
            "conversion_rate": conversion_rate['conversion_rate']
        },
        recommendation=recommendation,
        historical_precedents=[p['name'] for p in precedents]
    )
```

**Payment Timing Shift Detection**:

```python
def detect_payment_timing_shift(self, customer_id: str) -> Optional[PatternInsight]:
    """
    Detect significant changes in payment timing patterns.

    Pattern: Payment timing shift from early → on-time may indicate:
    - Financial constraints (concerning)
    - Capital allocation during growth (normal)
    - Process changes (neutral)

    Distinguish between these by looking at order frequency.
    """

    # Get payment history with timing
    payments = self.db.query("""
        SELECT
            p.paid_at,
            i.due_date,
            EXTRACT(days FROM p.paid_at - i.due_date) as days_delta,
            i.amount
        FROM domain.payments p
        JOIN domain.invoices i ON p.invoice_id = i.invoice_id
        WHERE i.customer_id = %s
        AND p.paid_at > NOW() - INTERVAL '6 months'
        ORDER BY p.paid_at ASC
    """, (customer_id,))

    if len(payments) < 5:
        return None  # Not enough data

    # Split into early period and recent period
    midpoint = len(payments) // 2
    early_period = payments[:midpoint]
    recent_period = payments[midpoint:]

    # Calculate average timing for each period
    early_avg = sum(p['days_delta'] for p in early_period) / len(early_period)
    recent_avg = sum(p['days_delta'] for p in recent_period) / len(recent_period)

    # Detect shift (threshold: 2+ days difference)
    shift_days = recent_avg - early_avg

    if abs(shift_days) < 2:
        return None  # No significant shift

    # Determine shift direction
    if shift_days > 0:
        shift_direction = "later"  # Paying later than before
        concern_level = "watch"
    else:
        shift_direction = "earlier"  # Paying earlier than before
        concern_level = "positive"

    # Context: Check order frequency to distinguish scenarios
    order_frequency = self.db.query_one("""
        SELECT
            COUNT(*) as order_count,
            COUNT(CASE WHEN created_at > NOW() - INTERVAL '3 months' THEN 1 END) as recent_orders,
            COUNT(CASE WHEN created_at BETWEEN NOW() - INTERVAL '6 months'
                                        AND NOW() - INTERVAL '3 months' THEN 1 END) as earlier_orders
        FROM domain.sales_orders
        WHERE customer_id = %s
    """, (customer_id,))

    # If order frequency INCREASING while payment timing LATER → likely growth/expansion
    if shift_direction == "later" and order_frequency['recent_orders'] > order_frequency['earlier_orders']:
        interpretation = "expansion_phase"
        concern_level = "low"
        explanation = "Payment timing slowed while order frequency increased. This typically indicates capital allocation during growth phase, not financial distress."
    # If order frequency DECREASING while payment timing LATER → concerning
    elif shift_direction == "later" and order_frequency['recent_orders'] < order_frequency['earlier_orders']:
        interpretation = "potential_distress"
        concern_level = "high"
        explanation = "Payment timing slowed AND order frequency decreased. This pattern may indicate financial constraints."
    else:
        interpretation = "process_change"
        concern_level = "medium"
        explanation = f"Payment timing shifted {shift_direction} by {abs(shift_days):.1f} days. Monitor for additional signals."

    # Statistical significance
    import statistics
    early_stddev = statistics.stdev([p['days_delta'] for p in early_period])
    # t-statistic (simplified)
    t_stat = abs(shift_days) / (early_stddev / (len(early_period) ** 0.5))
    is_significant = t_stat > 2.0  # Roughly p < 0.05

    confidence = 0.7 if is_significant else 0.5
    significance = min(1.0, abs(shift_days) / 10)  # Larger shifts = more significant

    insight = f"""Payment timing pattern has shifted:
- Early period (first {len(early_period)} payments): {early_avg:+.1f} days from due date
- Recent period (last {len(recent_period)} payments): {recent_avg:+.1f} days from due date
- Change: {shift_days:+.1f} days ({shift_direction})

Context:
- Order frequency: {"increasing" if order_frequency['recent_orders'] > order_frequency['earlier_orders'] else "decreasing"}
- Interpretation: {explanation}

Statistical significance: {"Yes" if is_significant else "No"} (t={t_stat:.2f})"""

    recommendation = None
    if interpretation == "expansion_phase":
        recommendation = "Consider offering payment term flexibility as partnership gesture during their growth phase."
    elif interpretation == "potential_distress":
        recommendation = "Schedule check-in conversation to understand their current situation and how you can support."

    return PatternInsight(
        pattern_type="payment_timing_shift",
        entity_id=customer_id,
        confidence=confidence,
        significance=significance,
        insight=insight,
        data={
            "early_avg_days": early_avg,
            "recent_avg_days": recent_avg,
            "shift_days": shift_days,
            "shift_direction": shift_direction,
            "interpretation": interpretation,
            "concern_level": concern_level,
            "is_significant": is_significant
        },
        recommendation=recommendation,
        historical_precedents=[]
    )
```

**Batch Processing**:

```python
@celery.task(name='patterns.analyze_all_customers')
def analyze_all_customers_nightly():
    """
    Nightly batch job to pre-compute patterns for all customers.

    Stores results in app.customer_patterns table for fast retrieval.
    """

    analyzer = PatternAnalyzer()

    # Get all active customers
    customers = db.query("""
        SELECT customer_id
        FROM domain.customers
        WHERE status = 'active'
    """)

    for customer in customers:
        try:
            patterns = analyzer.analyze_entity(customer['customer_id'])

            # Store each pattern
            for pattern in patterns:
                db.execute("""
                    INSERT INTO app.customer_patterns
                    (customer_id, pattern_type, confidence, significance,
                     insight, data, recommendation, computed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (customer_id, pattern_type)
                    DO UPDATE SET
                        confidence = EXCLUDED.confidence,
                        significance = EXCLUDED.significance,
                        insight = EXCLUDED.insight,
                        data = EXCLUDED.data,
                        recommendation = EXCLUDED.recommendation,
                        computed_at = NOW()
                """, (
                    pattern.entity_id,
                    pattern.pattern_type,
                    pattern.confidence,
                    pattern.significance,
                    pattern.insight,
                    json.dumps(pattern.data),
                    pattern.recommendation
                ))

            logger.info(f"Analyzed patterns for customer {customer['customer_id']}: {len(patterns)} patterns found")

        except Exception as e:
            logger.error(f"Error analyzing customer {customer['customer_id']}: {e}")
            continue
```

**Integration with Synthesis**:

```python
# In ContextSynthesizer
def enrich_with_patterns(self, context: Context) -> EnrichedContext:
    """Add relevant patterns to context"""

    patterns = []

    for entity in context.entities:
        # Retrieve pre-computed patterns (fast)
        entity_patterns = self.db.query("""
            SELECT pattern_type, confidence, significance, insight, recommendation
            FROM app.customer_patterns
            WHERE customer_id = %s
            AND confidence > 0.7
            AND computed_at > NOW() - INTERVAL '24 hours'
            ORDER BY significance DESC
            LIMIT 3
        """, (entity.entity_id,))

        patterns.extend(entity_patterns)

    context.patterns = patterns
    return context
```

**Testing**:

```python
def test_rush_order_pattern_detection():
    # Setup: Customer with 4 rush orders in 6 months
    analyzer = PatternAnalyzer(mock_db_with_rush_orders)

    result = analyzer.detect_rush_order_pattern("customer-123")

    assert result is not None
    assert result.pattern_type == "rush_order_frequency"
    assert result.confidence >= 0.7
    assert "retainer" in result.recommendation.lower()

def test_no_pattern_when_insufficient_data():
    analyzer = PatternAnalyzer(mock_db_with_2_rush_orders)

    result = analyzer.detect_rush_order_pattern("customer-123")

    assert result is None  # < 3 orders, no pattern

def test_payment_timing_shift_with_context():
    # Customer paying 2 days later + increased orders = expansion
    analyzer = PatternAnalyzer(mock_db_expansion_pattern)

    result = analyzer.detect_payment_timing_shift("customer-123")

    assert result.data['interpretation'] == "expansion_phase"
    assert result.data['concern_level'] == "low"
```

---

### Component 3: Context Synthesizer

**Purpose**: Combine all retrieved information into a rich, coherent context for LLM.

**Interface**:
```python
@dataclass
class SynthesizedContext:
    # Core query info
    user_query: str
    intent: str                    # "status_query", "decision_support", etc.

    # Retrieved data
    entities: List[ResolvedEntity]
    db_facts: Dict[str, Any]
    memories: List[Memory]
    patterns: List[PatternInsight]

    # Synthesis outputs
    primary_context: str           # Main context for LLM
    supporting_context: str        # Additional details
    confidence_notes: List[str]    # Uncertainties to communicate

    # Response guidance
    should_include_patterns: bool
    should_include_recommendations: bool
    synthesis_complexity: str      # "simple", "medium", "complex"

class ContextSynthesizer:
    """
    Combines retrieved information into coherent context.

    This is where "intelligence" manifests - taking disparate pieces
    and creating a unified understanding.
    """

    def synthesize(self,
                   query: str,
                   entities: List[ResolvedEntity],
                   memories: List[Memory],
                   patterns: List[PatternInsight],
                   db_facts: Dict[str, Any]) -> SynthesizedContext:
        """Main synthesis method"""
        pass

    def determine_intent(self, query: str) -> str:
        """Classify user intent"""
        pass

    def build_primary_context(self, components: Dict) -> str:
        """Build main context string for LLM"""
        pass

    def identify_confidence_gaps(self, memories: List[Memory]) -> List[str]:
        """Find uncertainties to communicate"""
        pass
```

**Implementation**:

```python
def synthesize(self,
               query: str,
               entities: List[ResolvedEntity],
               memories: List[Memory],
               patterns: List[PatternInsight],
               db_facts: Dict[str, Any]) -> SynthesizedContext:
    """
    Combine all information sources into unified context.

    Strategy:
    1. Determine user intent
    2. Organize information by relevance
    3. Build structured context for LLM
    4. Identify confidence gaps
    5. Determine synthesis complexity
    """

    # Step 1: Intent classification
    intent = self.determine_intent(query)

    # Step 2: Organize by relevance
    # Sort memories by relevance to query
    ranked_memories = self.rank_memories(query, memories)

    # Filter patterns by significance
    significant_patterns = [p for p in patterns if p.significance > 0.6]

    # Step 3: Build primary context
    context_parts = []

    # Always include DB facts
    if db_facts:
        context_parts.append(self._format_db_facts(db_facts, intent))

    # Include high-confidence memories
    high_conf_memories = [m for m in ranked_memories if m.confidence > 0.8]
    if high_conf_memories:
        context_parts.append(self._format_memories(high_conf_memories[:5]))

    # Include patterns if relevant to intent
    should_include_patterns = intent in ["status_query", "decision_support", "analysis"]
    if should_include_patterns and significant_patterns:
        context_parts.append(self._format_patterns(significant_patterns[:3]))

    primary_context = "\n\n".join(context_parts)

    # Step 4: Supporting context (lower confidence info)
    supporting_parts = []

    # Medium confidence memories
    med_conf_memories = [m for m in ranked_memories
                        if 0.5 < m.confidence <= 0.8]
    if med_conf_memories:
        supporting_parts.append(self._format_memories(med_conf_memories[:3],
                                                      label="Additional context"))

    supporting_context = "\n\n".join(supporting_parts)

    # Step 5: Identify confidence gaps
    confidence_notes = self.identify_confidence_gaps(memories)

    # Add conflicts to confidence notes
    conflicts = self._detect_conflicts(memories)
    if conflicts:
        confidence_notes.extend([f"Conflicting information about {c}"
                               for c in conflicts])

    # Step 6: Determine synthesis complexity
    complexity = "simple"
    if len(entities) > 1 or significant_patterns:
        complexity = "medium"
    if intent == "decision_support" or len(significant_patterns) > 2:
        complexity = "complex"

    return SynthesizedContext(
        user_query=query,
        intent=intent,
        entities=entities,
        db_facts=db_facts,
        memories=ranked_memories,
        patterns=significant_patterns,
        primary_context=primary_context,
        supporting_context=supporting_context,
        confidence_notes=confidence_notes,
        should_include_patterns=should_include_patterns,
        should_include_recommendations=(intent == "decision_support"),
        synthesis_complexity=complexity
    )

def determine_intent(self, query: str) -> str:
    """
    Classify user intent using keyword matching + LLM.

    Intent categories:
    - fact_lookup: "What is X?"
    - status_query: "How is X doing?"
    - decision_support: "Should I do X?"
    - analysis: "Why did X happen?"
    - memory_store: "Remember that X"
    """

    query_lower = query.lower()

    # Keyword-based classification (fast)
    if any(word in query_lower for word in ["remember", "note that", "keep in mind"]):
        return "memory_store"

    if any(word in query_lower for word in ["should i", "should we", "recommend"]):
        return "decision_support"

    if any(word in query_lower for word in ["why", "explain", "how come"]):
        return "analysis"

    if any(word in query_lower for word in ["status", "how is", "how are", "doing"]):
        return "status_query"

    if any(word in query_lower for word in ["what is", "what's", "tell me", "show me"]):
        return "fact_lookup"

    # Fallback: Use cheap LLM for classification
    classification = self.llm_cheap.generate(f"""Classify this query intent:
Query: {query}

Options: fact_lookup, status_query, decision_support, analysis, memory_store

Classification:""").strip()

    return classification if classification in ["fact_lookup", "status_query",
                                                "decision_support", "analysis",
                                                "memory_store"] else "status_query"

def _format_db_facts(self, facts: Dict, intent: str) -> str:
    """Format database facts for context"""

    if intent == "fact_lookup":
        # Simple, direct format
        return "\n".join([f"{k}: {v}" for k, v in facts.items()])

    # Rich format for other intents
    formatted = "Current Database Information:\n"
    for key, value in facts.items():
        formatted += f"- {key.replace('_', ' ').title()}: {value}\n"

    return formatted

def _format_memories(self, memories: List[Memory], label: str = "Relevant Context") -> str:
    """Format memories for context"""

    formatted = f"{label} (from memory):\n"

    for memory in memories:
        conf_marker = "✓" if memory.confidence > 0.8 else "~"
        formatted += f"{conf_marker} {memory.text}\n"

        if memory.confidence < 0.8:
            formatted += f"  (confidence: {memory.confidence:.2f})\n"

    return formatted

def _format_patterns(self, patterns: List[PatternInsight]) -> str:
    """Format pattern insights for context"""

    formatted = "Pattern Analysis:\n"

    for pattern in patterns:
        formatted += f"\n{pattern.pattern_type.replace('_', ' ').title()}:\n"
        formatted += f"{pattern.insight}\n"

        if pattern.recommendation:
            formatted += f"→ {pattern.recommendation}\n"

    return formatted

def identify_confidence_gaps(self, memories: List[Memory]) -> List[str]:
    """Identify information we're uncertain about"""

    gaps = []

    # Low confidence memories
    low_conf = [m for m in memories if m.confidence < 0.6]
    if low_conf:
        gaps.append(f"Low confidence information: {len(low_conf)} items")

    # Stale memories
    stale = [m for m in memories
            if (datetime.now() - m.created_at).days > 90]
    if stale:
        gaps.append(f"Information older than 90 days: {len(stale)} items")

    return gaps

def _detect_conflicts(self, memories: List[Memory]) -> List[str]:
    """Detect conflicting information"""

    conflicts = []

    # Group memories by entity
    by_entity = {}
    for memory in memories:
        for entity_id in memory.entity_links:
            if entity_id not in by_entity:
                by_entity[entity_id] = []
            by_entity[entity_id].append(memory)

    # Check for contradictions within entity memories
    for entity_id, entity_memories in by_entity.items():
        # Simple heuristic: look for opposite keywords
        texts = [m.text.lower() for m in entity_memories]

        # Payment terms conflicts
        if any("net15" in t for t in texts) and any("net30" in t for t in texts):
            conflicts.append(f"payment terms for {entity_id}")

        # Day preferences
        days = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        mentioned_days = [day for day in days if any(day in t for t in texts)]
        if len(set(mentioned_days)) > 1:
            conflicts.append(f"delivery day preference for {entity_id}")

    return conflicts
```

**Integration**:

```python
# In main request flow
def handle_chat_request(user_query: str, session_id: str):
    # 1. Resolve entities
    entities = entity_resolver.resolve(user_query, conversation_context)

    # 2. Retrieve information
    memories = memory_retriever.retrieve(user_query, entities)
    patterns = pattern_analyzer.get_patterns(entities)
    db_facts = database.query_facts(entities)

    # 3. Synthesize context
    synthesized = context_synthesizer.synthesize(
        query=user_query,
        entities=entities,
        memories=memories,
        patterns=patterns,
        db_facts=db_facts
    )

    # 4. Generate response
    response = response_generator.generate(synthesized)

    return response
```

---

## Component 4: Decision Support Engine

(Continued in next document: `Architecture_Intelligence_DecisionSupport.md`)

---

## Summary

This architecture provides:

1. ✅ **Same rigor for intelligence as infrastructure**
   - EntityResolver: Fully specified (matching ConversationContextManager detail level)
   - PatternAnalyzer: Complete implementation with SQL, algorithms, batch jobs
   - ContextSynthesizer: Explicit synthesis logic, not hand-waved

2. ✅ **Clear interfaces**
   - Every component has @dataclass inputs/outputs
   - Methods documented with purpose, args, returns
   - Integration points explicit

3. ✅ **Testable components**
   - Each component can be unit tested
   - Mock data strategies shown
   - Expected behaviors clear

4. ✅ **Implementation guidance**
   - Not just "implement pattern detection"
   - Actual SQL queries provided
   - Algorithm steps explicit
   - Integration points clear

**Next document continues with**:
- DecisionSupportEngine (full specification)
- ResponseGenerator (quality gates, formatting)
- Complete data flow examples
- End-to-end request processing

This is what excellent architecture looks like: every layer specified with equal rigor.
