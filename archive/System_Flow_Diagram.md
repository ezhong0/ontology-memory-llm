# Intelligent Memory System: Complete Request Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            USER REQUEST                                      │
│               "Should we extend payment terms to Delta?"                     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ENTITY RESOLUTION (Multi-Strategy)                       │
│                              Latency: ~150ms                                 │
│                                                                              │
│  STEP 1: NER Extraction (spaCy)                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ • Extract entity mentions from natural language                        │ │
│  │ • Identify entity types (ORG, PERSON, PRODUCT, etc.)                   │ │
│  │ • Input: "Should we extend payment terms to Delta?"                    │ │
│  │ • Output: [{"mention": "Delta", "type": "ORG"}]                        │ │
│  │ • Latency: ~50ms                                                       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  STEP 2: Database Matching (3-Strategy Approach)                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Strategy 1: Exact Match (case-insensitive)                             │ │
│  │   SELECT customer_id, name FROM domain.customers                       │ │
│  │   WHERE LOWER(name) = LOWER('Delta')                                   │ │
│  │   • Confidence: 0.95 if match found                                    │ │
│  │                                                                        │ │
│  │ Strategy 2: Fuzzy Match (PostgreSQL trigram similarity)                │ │
│  │   SELECT customer_id, name, similarity(name, 'Delta') as score        │ │
│  │   FROM domain.customers                                                │ │
│  │   WHERE name % 'Delta'  -- pg_trgm operator                           │ │
│  │   ORDER BY score DESC LIMIT 5                                          │ │
│  │   • Handles typos: "Dleta" → "Delta" (score: 0.89)                    │ │
│  │   • Partial matches: "Delta Industries" (score: 0.72)                 │ │
│  │                                                                        │ │
│  │ Strategy 3: Alias Lookup                                               │ │
│  │   SELECT entity_id, canonical_name FROM app.entity_aliases             │ │
│  │   WHERE alias = 'Delta'                                                │ │
│  │   • Maps known aliases: "DI" → "Delta Industries"                     │ │
│  │   • Confidence: 0.92                                                   │ │
│  │                                                                        │ │
│  │ Result: 3 candidates found                                             │ │
│  │   1. Delta Industries (customer-delta-industries-123)                  │ │
│  │   2. Delta Shipping Co (customer-delta-shipping-456)                   │ │
│  │   3. Delta Tech Solutions (customer-delta-tech-789)                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  STEP 3: Disambiguation (Context-Based Scoring)                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Scoring Factors:                                                       │ │
│  │  • Base similarity score (0-1.0)                                       │ │
│  │  • Conversation recency boost (+0-0.3)                                 │ │
│  │      → "Delta" mentioned 2 turns ago → Delta Industries               │ │
│  │  • User interaction frequency boost (+0-0.2)                           │ │
│  │      → User discussed Delta Industries 15 times this month             │ │
│  │  • Active work boost (+0.1)                                            │ │
│  │      → Delta Industries has 3 active orders                            │ │
│  │                                                                        │ │
│  │ Final Scores:                                                          │ │
│  │   Delta Industries: 0.93 (winner - auto-resolved)                     │ │
│  │   Delta Shipping: 0.42                                                 │ │
│  │   Delta Tech: 0.38                                                     │ │
│  │                                                                        │ │
│  │ Decision: Auto-resolve (top score > 0.8 AND 2x second place)          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────────────┘
                Resolved: Delta Industries (customer-delta-industries-123)
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│               INFORMATION RETRIEVAL (3 Parallel Streams)                     │
│                         Total Latency: ~100ms                                │
│                       (max of 3 parallel operations)                         │
│                                                                              │
│  ╔═════════════════════╗  ╔═════════════════════╗  ╔════════════════════╗  │
│  ║  STREAM 1:          ║  ║  STREAM 2:          ║  ║  STREAM 3:         ║  │
│  ║  Memory Retrieval   ║  ║  Pattern Analysis   ║  ║  Database Facts    ║  │
│  ║  Latency: ~100ms    ║  ║  Latency: ~50ms     ║  ║  Latency: ~30ms    ║  │
│  ╚═════════════════════╝  ╚═════════════════════╝  ╚════════════════════╝  │
│           │                        │                        │                │
│           ▼                        ▼                        ▼                │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────────┐    │
│  │ Vector Search    │    │ Cache Lookup     │    │ SQL Queries       │    │
│  │                  │    │                  │    │                   │    │
│  │ 1. Embed query   │    │ SELECT * FROM    │    │ Current revenue   │    │
│  │    with OpenAI   │    │ customer_patterns│    │ Payment history   │    │
│  │                  │    │ WHERE customer_id│    │ Active orders     │    │
│  │ 2. pgvector      │    │ AND computed_at  │    │ Invoice status    │    │
│  │    cosine search │    │ > NOW() - 24hrs  │    │                   │    │
│  │                  │    │                  │    │ All indexed for   │    │
│  │ 3. Rank by       │    │ If cache miss:   │    │ fast retrieval    │    │
│  │    relevance +   │    │ → Real-time      │    │                   │    │
│  │    recency       │    │   pattern detect │    │                   │    │
│  │                  │    │   (5s timeout)   │    │                   │    │
│  │ 4. Return top 10 │    │                  │    │                   │    │
│  │    memories      │    │ Graceful degrade │    │                   │    │
│  │                  │    │ if timeout       │    │                   │    │
│  └──────────────────┘    └──────────────────┘    └───────────────────┘    │
│           │                        │                        │                │
│           │                        │                        │                │
│  Results: 10 memories     Results: 2 patterns      Results: DB facts        │
│  • "Delta prefers         • Rush order pattern     • Revenue: $127K/yr      │
│    NET15 terms"             (4 orders in 6 mo)     • Orders: 18 total       │
│    (confidence: 0.95)     • Payment shift            (3 active)             │
│  • "Expanding into          (early → on-time)      • Payments: 15/15        │
│    new markets"           • Confidence: 0.85          on-time               │
│    (confidence: 0.82)     • Significance: 0.75     • Growth: +40% YoY       │
│                                                                              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
         Memories (10)            Patterns (2)             DB Facts
                                       │
                                       └────────────┬───────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTEXT SYNTHESIS (Intelligence Layer)                    │
│                            Latency: ~100ms                                   │
│                                                                              │
│  STEP 1: Intent Classification                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Keyword Analysis: "Should we" → decision_support intent                │ │
│  │                                                                        │ │
│  │ Intent Types:                                                          │ │
│  │  • fact_lookup: "What is X?"                                           │ │
│  │  • status_query: "How is X doing?"                                     │ │
│  │  • decision_support: "Should I do X?" ← MATCHED                        │ │
│  │  • analysis: "Why did X happen?"                                       │ │
│  │  • memory_store: "Remember that X"                                     │ │
│  │                                                                        │ │
│  │ Result: decision_support (triggers multi-dimensional analysis)         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  STEP 2: Context Organization                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ PRIMARY CONTEXT (high confidence, directly relevant):                  │ │
│  │  Database Facts:                                                       │ │
│  │   • Revenue: $127K annually (top 25% customer)                         │ │
│  │   • Payment history: 15/15 invoices paid on-time                       │ │
│  │   • Active orders: 3 totaling $45K                                     │ │
│  │   • Growth: +40% year-over-year                                        │ │
│  │                                                                        │ │
│  │  High-Confidence Memories:                                             │ │
│  │   ✓ "Delta prefers NET15 payment terms" (0.95)                        │ │
│  │   ✓ "Expanding into automotive and aerospace sectors" (0.90)          │ │
│  │                                                                        │ │
│  │  Significant Patterns:                                                 │ │
│  │   • Rush order frequency pattern (85% convert to retainer)            │ │
│  │   • Payment timing stable (always 3-5 days early)                     │ │
│  │                                                                        │ │
│  │ SUPPORTING CONTEXT (medium confidence):                                │ │
│  │  ~ "Working with Sarah Chen as primary contact" (0.78)                │ │
│  │  ~ "Prefer Thursday deliveries for rush orders" (0.72)                │ │
│  │                                                                        │ │
│  │ CONFIDENCE GAPS IDENTIFIED:                                            │ │
│  │  • No conflicting information detected                                 │ │
│  │  • All information < 90 days old                                       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  STEP 3: Determine Synthesis Complexity                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Factors:                                                               │ │
│  │  • Multiple entities? No (just Delta Industries)                       │ │
│  │  • Significant patterns? Yes (2 patterns detected)                     │ │
│  │  • Decision support intent? Yes                                        │ │
│  │                                                                        │ │
│  │ Result: COMPLEX synthesis                                              │ │
│  │   → Triggers multi-dimensional decision analysis                       │ │
│  │   → Structured response format required                                │ │
│  │   → Full reasoning transparency                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              DECISION SUPPORT ENGINE (Multi-Dimensional Analysis)            │
│                            Latency: ~800ms                                   │
│                                                                              │
│  DIMENSION 1: Financial Health Assessment                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Factor 1: Payment History (0-3 points)                                 │ │
│  │   • 15/15 invoices paid on-time                                        │ │
│  │   • 0 late payments, 0 missed payments                                 │ │
│  │   • Score: 3.0/3.0 (Perfect) ✓                                         │ │
│  │                                                                        │ │
│  │ Factor 2: Revenue Contribution (0-2 points)                            │ │
│  │   • $127K annually                                                     │ │
│  │   • Top 25% revenue contributor (75th percentile)                      │ │
│  │   • Score: 1.5/2.0 (High) ✓                                            │ │
│  │                                                                        │ │
│  │ Factor 3: Growth Trajectory (0-2 points)                               │ │
│  │   • +40% year-over-year growth                                         │ │
│  │   • Strong upward trend                                                │ │
│  │   • Score: 1.5/2.0 (Healthy) ✓                                         │ │
│  │                                                                        │ │
│  │ Factor 4: Payment Timing (0-2 points)                                  │ │
│  │   • Average: 3-5 days before due date                                  │ │
│  │   • Recent shift: early → on-time (during expansion)                   │ │
│  │   • Score: 1.0/2.0 (Good) ✓                                            │ │
│  │                                                                        │ │
│  │ Factor 5: Consistency (0-1 point)                                      │ │
│  │   • Low variance in payment timing (stddev < 5 days)                   │ │
│  │   • Score: 1.0/1.0 (Highly consistent) ✓                               │ │
│  │                                                                        │ │
│  │ TOTAL FINANCIAL SCORE: 8.0/10.0 (EXCELLENT)                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  DIMENSION 2: Risk Assessment                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Base Risk Calculation:                                                 │ │
│  │   Base = max(0, 5 - financial_score/2)                                 │ │
│  │   Base = max(0, 5 - 8.0/2) = 1.0 (Low)                                 │ │
│  │                                                                        │ │
│  │ Decision-Specific Risk Factors:                                        │ │
│  │                                                                        │ │
│  │  Risk 1: Recent Payment Delays?                                        │ │
│  │   SQL: SELECT COUNT(*) FROM payments WHERE paid_at > due_date          │ │
│  │   Result: 0 delays in past 3 months                                    │ │
│  │   Impact: +0.0 risk (no concern) ✓                                     │ │
│  │                                                                        │ │
│  │  Risk 2: Declining Order Frequency?                                    │ │
│  │   Recent orders: 8 (last 3 months)                                     │ │
│  │   Earlier orders: 5 (previous 3 months)                                │ │
│  │   Trend: INCREASING (+60%)                                             │ │
│  │   Impact: -0.5 risk (positive signal) ✓                                │ │
│  │                                                                        │ │
│  │  Risk 3: Payment Timing + Order Frequency Context                      │ │
│  │   Payment shift: early → on-time                                       │ │
│  │   Order frequency: INCREASING                                          │ │
│  │   Interpretation: Expansion phase (capital allocation)                 │ │
│  │   NOT financial distress                                               │ │
│  │   Impact: +0.0 risk ✓                                                  │ │
│  │                                                                        │ │
│  │ Historical Precedent Analysis:                                         │ │
│  │   Similar customers with extended terms: 23                            │ │
│  │   Successful outcomes (< 10% late rate): 19                            │ │
│  │   Success rate: 83%                                                    │ │
│  │   Impact: -0.2 risk (strong precedent) ✓                               │ │
│  │                                                                        │ │
│  │ TOTAL RISK SCORE: 0.3/10.0 (VERY LOW)                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  DIMENSION 3: Relationship Value                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ • Top 25% revenue contributor                                          │ │
│  │ • 40% growth trajectory                                                 │ │
│  │ • 4 rush orders in 6 months (high engagement)                          │ │
│  │ • Expanding into new markets (long-term potential)                     │ │
│  │ • Strategic Importance: HIGH                                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  SYNTHESIS: Recommendation Generation                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Decision Logic:                                                        │ │
│  │   IF financial >= 7.0 AND risk < 4.0 → YES                            │ │
│  │   IF financial >= 5.0 AND risk < 6.0 → CONDITIONAL                    │ │
│  │   ELSE → NO or MORE INFO NEEDED                                        │ │
│  │                                                                        │ │
│  │ Current: financial = 8.0, risk = 0.3                                   │ │
│  │                                                                        │ │
│  │ RECOMMENDATION: YES - Extend Payment Terms                             │ │
│  │                                                                        │ │
│  │ Confidence: 87%                                                        │ │
│  │   (high financial + very low risk + strong precedent)                 │ │
│  │                                                                        │ │
│  │ Reasoning:                                                             │ │
│  │  ✓ Excellent financial health (8.0/10)                                 │ │
│  │  ✓ Very low risk profile (0.3/10)                                      │ │
│  │  ✓ Payment timing shift explained by growth (not distress)            │ │
│  │  ✓ Strong historical precedent (83% success rate)                     │ │
│  │  ✓ High strategic relationship value                                   │ │
│  │                                                                        │ │
│  │ Conditions:                                                            │ │
│  │  • Review performance after 6 months                                   │ │
│  │  • Monitor payment timing for further changes                          │ │
│  │                                                                        │ │
│  │ Alternative Options:                                                   │ │
│  │  1. Graduated approach (NET15 → NET20 → NET30 over 6 months)         │ │
│  │  2. Retainer agreement with flexible terms                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RESPONSE GENERATION (Quality-Controlled)                  │
│                            Latency: ~2000ms                                  │
│                                                                              │
│  STEP 1: Prompt Building (Complexity-Based)                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Synthesis Complexity: COMPLEX                                          │ │
│  │ → Use structured decision analysis format                              │ │
│  │                                                                        │ │
│  │ Prompt Structure:                                                      │ │
│  │   System Instructions:                                                 │ │
│  │    • Role: Strategic business advisor                                  │ │
│  │    • Format: Structured decision analysis                              │ │
│  │    • Requirements: Data-backed, transparent reasoning                  │ │
│  │                                                                        │ │
│  │   Context Provided:                                                    │ │
│  │    • Primary context (database facts + high-conf memories)             │ │
│  │    • Pattern insights (rush orders, payment timing)                    │ │
│  │    • Decision analysis (financial, risk, relationship)                 │ │
│  │    • Recommendation with confidence                                    │ │
│  │                                                                        │ │
│  │   Required Sections:                                                   │ │
│  │    1. CURRENT SITUATION (summarize facts)                              │ │
│  │    2. KEY FACTORS (patterns + insights)                                │ │
│  │    3. ANALYSIS (reasoning across dimensions)                           │ │
│  │    4. RECOMMENDATION (YES/NO/CONDITIONAL with confidence)              │ │
│  │    5. NEXT STEPS (actionable items)                                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  STEP 2: LLM Generation with Fallback                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Primary: GPT-4 (max 1000 tokens, temp 0.3)                             │ │
│  │  • Attempt 1: Generate response                                        │ │
│  │  • Latency target: < 10s                                               │ │
│  │  • If timeout or error:                                                │ │
│  │    → Retry with exponential backoff (3 attempts)                       │ │
│  │    → If still fails, fallback to GPT-3.5-turbo                        │ │
│  │                                                                        │ │
│  │ Fallback: GPT-3.5-turbo (faster, cheaper)                              │ │
│  │  • Latency target: < 5s                                                │ │
│  │  • If fails:                                                           │ │
│  │    → Use template-based response (structured data only)               │ │
│  │                                                                        │ │
│  │ Circuit Breaker:                                                       │ │
│  │  • If 5 consecutive LLM failures → open circuit for 60s               │ │
│  │  • Use template responses during circuit open                         │ │
│  │                                                                        │ │
│  │ Rate Limiting:                                                         │ │
│  │  • Token bucket: 60 requests/minute                                    │ │
│  │  • Prevents API rate limit errors                                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  STEP 3: Quality Gates (5 Checks)                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Gate 1: Length Appropriateness                                         │ │
│  │   Expected for COMPLEX: 200-500 words                                  │ │
│  │   Actual: 287 words ✓                                                  │ │
│  │                                                                        │ │
│  │ Gate 2: Query Relevance                                                │ │
│  │   Keywords overlap: 8/10 query terms addressed ✓                      │ │
│  │   Directly answers "should we extend terms?" ✓                        │ │
│  │                                                                        │ │
│  │ Gate 3: Source Citation                                                │ │
│  │   Database facts cited ✓                                               │ │
│  │   Memory references included ✓                                         │ │
│  │   Pattern insights mentioned ✓                                         │ │
│  │                                                                        │ │
│  │ Gate 4: Confidence Communication                                       │ │
│  │   Decision confidence stated (87%) ✓                                   │ │
│  │   Reasoning transparency provided ✓                                    │ │
│  │   Conditions clearly listed ✓                                          │ │
│  │                                                                        │ │
│  │ Gate 5: Pattern Inclusion                                              │ │
│  │   Significant patterns (rush orders, payment timing) mentioned ✓      │ │
│  │                                                                        │ │
│  │ QUALITY SCORE: 0.92/1.00 (PASSED) ✓                                    │ │
│  │   All gates passed, high quality response                             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  STEP 4: Format Response                                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Format as markdown with:                                               │ │
│  │  • Clear section headers                                               │ │
│  │  • Bullet points for key facts                                         │ │
│  │  • Confidence indicators (✓ for strong signals)                       │ │
│  │  • Data citations with values                                          │ │
│  │  • Next steps as actionable checklist                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RETURN RESPONSE TO USER                               │
│                                                                              │
│  Response Summary:                                                           │
│   • Recommendation: YES - Extend payment terms                              │
│   • Confidence: 87%                                                          │
│   • Quality Score: 0.92                                                      │
│   • Sources: Database (current), Memory (5 items), Patterns (2)             │
│                                                                              │
│  Performance:                                                                │
│   • Entity Resolution: 150ms                                                 │
│   • Information Retrieval: 100ms (parallel)                                  │
│   • Context Synthesis: 100ms                                                 │
│   • Decision Support: 800ms                                                  │
│   • Response Generation: 2000ms                                              │
│   ────────────────────────────────                                          │
│   • TOTAL: 3150ms (within p95 target of 10s) ✓                              │
│                                                                              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
                                 [BACKGROUND]
                                       │
┌──────────────────────────────────────┴──────────────────────────────────────┐
│                    MEMORY STORAGE (Asynchronous, Non-Blocking)               │
│                              Latency: ~200ms                                 │
│                         (does not block user response)                       │
│                                                                              │
│  STEP 1: Store Episodic Memory                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ INSERT INTO app.memories (                                             │ │
│  │   memory_id, user_id, session_id, memory_type,                         │ │
│  │   content, embedding, entity_links, created_at                         │ │
│  │ ) VALUES (                                                             │ │
│  │   gen_random_uuid(),                                                   │ │
│  │   'user-123',                                                          │ │
│  │   'session-456',                                                       │ │
│  │   'episodic',                                                          │ │
│  │   'User asked about extending payment terms to Delta Industries...',  │ │
│  │   embedding_vector,  -- 1536-dim OpenAI embedding                     │ │
│  │   ['customer-delta-industries-123'],                                   │ │
│  │   NOW()                                                                │ │
│  │ )                                                                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  STEP 2: Update Conversation Context (Redis)                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ HSET conversation:session-456 {                                        │ │
│  │   "last_entities": ["customer-delta-industries-123"],                  │ │
│  │   "last_intent": "decision_support",                                   │ │
│  │   "last_topics": ["payment_terms", "financial_health"],               │ │
│  │   "turn_count": 5,                                                     │ │
│  │   "updated_at": "2024-01-15T10:30:45Z"                                 │ │
│  │ }                                                                      │ │
│  │ EXPIRE conversation:session-456 3600  -- 1 hour TTL                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  STEP 3: Check Workflow Triggers                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Workflow Engine checks if any workflows should trigger:                │ │
│  │                                                                        │ │
│  │  Example Workflows:                                                    │ │
│  │   • "Payment terms changed" → notify account manager                  │ │
│  │   • "High-value decision" → add to review queue                       │ │
│  │   • "Pattern detected" → create follow-up task                        │ │
│  │                                                                        │ │
│  │  For this request:                                                     │ │
│  │   → "High-value decision" workflow triggered                          │ │
│  │   → Create task: "Review Delta Industries payment term extension"     │ │
│  │   → Assign to: Account Manager (Sarah)                                │ │
│  │   → Due: 2 days from now                                               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  STEP 4: Invalidate Cache (if needed)                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ If decision results in data changes:                                   │ │
│  │  • Invalidate pattern cache for customer                               │ │
│  │    → DEL cache:patterns:customer-delta-industries-123                 │ │
│  │  • Invalidate entity cache                                             │ │
│  │  • Update materialized views (if any)                                  │ │
│  │                                                                        │ │
│  │ For this request:                                                      │ │
│  │  → No data changed yet (recommendation only)                           │ │
│  │  → No cache invalidation needed                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              ▼                                               │
│  STEP 5: Emit Metrics & Logs                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Metrics:                                                               │ │
│  │  • request_handler.requests (counter) +1                               │ │
│  │  • request_handler.duration (histogram) 3150ms                         │ │
│  │  • entity_resolver.duration (histogram) 150ms                          │ │
│  │  • decision_support.recommendation (counter, tags: YES) +1             │ │
│  │  • response_generator.quality_score (histogram) 0.92                   │ │
│  │                                                                        │ │
│  │ Structured Log (JSON):                                                 │ │
│  │  {                                                                     │ │
│  │    "timestamp": "2024-01-15T10:30:45Z",                                │ │
│  │    "level": "info",                                                    │ │
│  │    "event": "request_completed",                                       │ │
│  │    "user_id": "user-123",                                              │ │
│  │    "session_id": "session-456",                                        │ │
│  │    "entity_id": "customer-delta-industries-123",                       │ │
│  │    "intent": "decision_support",                                       │ │
│  │    "recommendation": "YES",                                            │ │
│  │    "confidence": 0.87,                                                 │ │
│  │    "quality_score": 0.92,                                              │ │
│  │    "duration_ms": 3150,                                                │ │
│  │    "patterns_detected": 2                                              │ │
│  │  }                                                                     │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Performance Metrics

| Component | Target p95 | Actual | Status |
|-----------|-----------|---------|--------|
| Entity Resolution | 150ms | 150ms | ✓ |
| Information Retrieval | 200ms | 100ms | ✓✓ |
| Context Synthesis | 300ms | 100ms | ✓✓ |
| Decision Support | 2000ms | 800ms | ✓✓ |
| Response Generation | 8000ms | 2000ms | ✓✓ |
| **Total Request** | **10000ms** | **3150ms** | **✓✓** |

---

## Error Handling & Resilience

### Graceful Degradation Strategy

```
LLM Failure Path:
  GPT-4 timeout (30s)
    ↓
  Retry with backoff (3 attempts)
    ↓
  Fallback to GPT-3.5-turbo
    ↓
  Template-based response
    ↓
  Always provides answer (never fails silently)

Pattern Analysis Timeout Path:
  Real-time detection timeout (5s)
    ↓
  Return cached patterns (< 24h old)
    ↓
  Return empty list (continue without patterns)
    ↓
  Response still generated (without pattern insights)

Database Slow Query Path:
  Query timeout (2s)
    ↓
  Return from L2 cache (Redis)
    ↓
  Return from L1 cache (in-memory)
    ↓
  Return partial results with confidence note
```

---

## Scaling Characteristics

### Horizontal Scaling (Stateless API Layer)
- API servers: 1 → N instances (load balanced)
- Each request independent
- Session state in Redis (shared)

### Vertical Scaling (Database)
- Initial: Single PostgreSQL instance
- Scale up: Increase CPU/RAM
- Scale out: Read replicas for queries

### Caching Strategy (Reduces Load)
- L1 (in-memory): 1ms access, 1000 items
- L2 (Redis): 5ms access, unlimited
- Pattern cache: 24h TTL, pre-computed nightly

### Cost Optimization
- Cache hit rate target: > 70%
- LLM fallback to cheaper models
- Batch pattern computation (nightly)
- Estimated cost: $500-800/month initial

---

## Complete Database Schema

**Required PostgreSQL Extensions:**
- `pgvector` - Vector similarity search
- `pg_trgm` - Trigram fuzzy text matching
- `uuid-ossp` - UUID generation

### Domain Schema (Business Data)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          domain.customers                                   │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ Column                 │ Type           │ Constraints                      │
├────────────────────────┼────────────────┼─────────────────────────────────┤
│ customer_id  🔑        │ UUID           │ PRIMARY KEY, auto-generated      │
│ name                   │ TEXT           │ NOT NULL                         │
│ industry               │ TEXT           │                                  │
│ status                 │ TEXT           │ DEFAULT 'active'                 │
│                        │                │ • active, inactive, suspended    │
│ notes                  │ TEXT           │                                  │
│ created_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
│ updated_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘
            │
            │ 1:N (one customer → many orders)
            ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        domain.sales_orders                                  │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ Column                 │ Type           │ Constraints                      │
├────────────────────────┼────────────────┼─────────────────────────────────┤
│ sales_order_id  🔑     │ UUID           │ PRIMARY KEY, auto-generated      │
│ customer_id  🔗        │ UUID           │ FK → customers, NOT NULL         │
│ so_number              │ TEXT           │ UNIQUE, NOT NULL                 │
│ title                  │ TEXT           │ NOT NULL                         │
│ status                 │ TEXT           │ NOT NULL                         │
│                        │                │ • draft, approved, in_fulfillment│
│                        │                │   fulfilled, cancelled           │
│ priority               │ TEXT           │ • normal, rush                   │
│ order_type             │ TEXT           │ • one_time, retainer             │
│ total_amount           │ NUMERIC(12,2)  │                                  │
│ created_at             │ TIMESTAMPTZ    │ NOT NULL, DEFAULT NOW()          │
│ updated_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘
            │
            ├─────────────────────┐
            │ 1:N                 │ 1:N
            ▼                     ▼
┌────────────────────────┐  ┌────────────────────────────────────────────────┐
│  domain.work_orders    │  │         domain.invoices                        │
├────────────────────────┤  ├────────────────────────┬────────────────┬──────┤
│ wo_id  🔑              │  │ invoice_id  🔑         │ UUID           │ PK   │
│ sales_order_id  🔗     │  │ sales_order_id  🔗     │ UUID           │ FK   │
│ wo_number (UNIQUE)     │  │ invoice_number (UNIQUE)│ TEXT           │      │
│ description            │  │ amount                 │ NUMERIC(12,2)  │      │
│ status                 │  │ due_date               │ DATE           │      │
│ • queued, in_progress  │  │ status                 │ TEXT           │      │
│   blocked, done        │  │ • open, paid, void     │                │      │
│ technician             │  │ issued_at              │ TIMESTAMPTZ    │      │
│ scheduled_for          │  │ created_at             │ TIMESTAMPTZ    │      │
│ created_at             │  └────────────────────────┴────────────────┴──────┘
│ updated_at             │               │
└────────────────────────┘               │ 1:N
                                         ▼
                                 ┌────────────────────────┐
                                 │   domain.payments      │
                                 ├────────────────────────┤
                                 │ payment_id  🔑         │
                                 │ invoice_id  🔗         │
                                 │ amount                 │
                                 │ method                 │
                                 │ paid_at                │
                                 │ created_at             │
                                 └────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                            domain.tasks                                     │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ Column                 │ Type           │ Constraints                      │
├────────────────────────┼────────────────┼─────────────────────────────────┤
│ task_id  🔑            │ UUID           │ PRIMARY KEY, auto-generated      │
│ customer_id  🔗        │ UUID           │ FK → customers (optional)        │
│ title                  │ TEXT           │ NOT NULL                         │
│ body                   │ TEXT           │                                  │
│ status                 │ TEXT           │ NOT NULL                         │
│                        │                │ • todo, doing, done              │
│ created_at             │ TIMESTAMPTZ    │ NOT NULL, DEFAULT NOW()          │
│ updated_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘

Legend: 🔑 Primary Key  |  🔗 Foreign Key  |  1:N One-to-Many Relationship
```

### App Schema (Intelligence & Memory Layer)

#### 1. Chat & Conversation

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           app.chat_events                                   │
│                    Raw conversation message events                          │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ Column                 │ Type           │ Constraints                      │
├────────────────────────┼────────────────┼─────────────────────────────────┤
│ event_id  🔑           │ UUID           │ PRIMARY KEY, auto-generated      │
│ session_id             │ UUID           │ NOT NULL                         │
│ user_id                │ UUID           │ NOT NULL                         │
│ role                   │ VARCHAR(20)    │ NOT NULL                         │
│                        │                │ • user, assistant, system        │
│ content                │ TEXT           │ NOT NULL                         │
│ metadata               │ JSONB          │ Additional context               │
│ created_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘
 Indexes: idx_chat_events_session (session_id, created_at)
          idx_chat_events_user (user_id, created_at)
```

#### 2. Entity Resolution System

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            app.entities                                     │
│            Extracted entities linking text to domain data                   │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ Column                 │ Type           │ Constraints                      │
├────────────────────────┼────────────────┼─────────────────────────────────┤
│ entity_id  🔑          │ UUID           │ PRIMARY KEY, auto-generated      │
│ session_id             │ UUID           │ Session where discovered         │
│ user_id                │ UUID           │ NOT NULL                         │
│ name                   │ VARCHAR(255)   │ NOT NULL, entity name            │
│ type                   │ VARCHAR(50)    │ NOT NULL                         │
│                        │                │ • customer, order, invoice,      │
│                        │                │   person, topic                  │
│ source                 │ VARCHAR(20)    │ NOT NULL                         │
│                        │                │ • message, database, inferred    │
│ external_ref           │ JSONB          │ {"table":"...", "id":"..."}      │
│ mention_count          │ INT            │ DEFAULT 1                        │
│ last_mentioned         │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
│ confidence             │ DECIMAL(3,2)   │ 0-1, DEFAULT 0.80                │
│ created_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘
            │
            │ 1:N (one entity → many aliases)
            ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        app.entity_aliases                                   │
│                  Learned mappings for disambiguation                        │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ Column                 │ Type           │ Constraints                      │
├────────────────────────┼────────────────┼─────────────────────────────────┤
│ alias_id  🔑           │ UUID           │ PRIMARY KEY, auto-generated      │
│ user_id                │ UUID           │ NOT NULL                         │
│ alias_text             │ VARCHAR(255)   │ NOT NULL (e.g., "DI", "Kay")     │
│ entity_id  🔗          │ UUID           │ FK → entities, CASCADE           │
│ confidence             │ DECIMAL(3,2)   │ 0-1, DEFAULT 0.80                │
│ usage_count            │ INT            │ DEFAULT 1                        │
│ user_confirmed         │ BOOLEAN        │ DEFAULT FALSE                    │
│ last_used              │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
│ created_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘
 Indexes: idx_aliases_text (alias_text, user_id)
          idx_aliases_entity (entity_id)
          UNIQUE (user_id, alias_text, entity_id)
```

#### 3. Memory System (Core Intelligence)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            app.memories                                     │
│                 Vectorized knowledge chunks with HNSW index                 │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ Column                 │ Type           │ Constraints                      │
├────────────────────────┼────────────────┼─────────────────────────────────┤
│ memory_id  🔑          │ UUID           │ PRIMARY KEY, auto-generated      │
│ user_id                │ UUID           │ NOT NULL                         │
│ session_id             │ UUID           │ Source session                   │
│ kind                   │ VARCHAR(20)    │ NOT NULL                         │
│                        │                │ • episodic (events)              │
│                        │                │ • semantic (facts)               │
│                        │                │ • procedural (workflows)         │
│                        │                │ • pattern (insights)             │
│ text                   │ TEXT           │ NOT NULL, memory content         │
│ embedding  📊          │ vector(1536)   │ OpenAI embedding for search      │
│ importance             │ DECIMAL(3,2)   │ 0-1, DEFAULT 0.50                │
│ confidence             │ DECIMAL(3,2)   │ 0-1, DEFAULT 0.70                │
│ base_confidence        │ DECIMAL(3,2)   │ Original (before decay)          │
│ reinforcement_count    │ INT            │ DEFAULT 0, access counter        │
│ deprecated             │ BOOLEAN        │ DEFAULT FALSE, soft delete       │
│ superseded_by  🔗      │ UUID           │ FK → memories (self-ref)         │
│ entity_links           │ JSONB          │ Array of linked entity_ids       │
│ ttl_days               │ INT            │ DEFAULT 365, lifespan            │
│ last_accessed          │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
│ created_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
│ updated_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘
 Critical Indexes:
   • HNSW vector index (m=16, ef_construction=64) for cosine similarity search
   • GIN index on entity_links for fast entity-based retrieval
   • Composite (user_id, created_at) for temporal queries
   • Partial index on kind WHERE NOT deprecated

┌────────────────────────────────────────────────────────────────────────────┐
│                       app.memory_summaries                                  │
│              Cross-session consolidated memory summaries                    │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ Column                 │ Type           │ Constraints                      │
├────────────────────────┼────────────────┼─────────────────────────────────┤
│ summary_id  🔑         │ UUID           │ PRIMARY KEY, auto-generated      │
│ user_id                │ UUID           │ NOT NULL                         │
│ entity_id              │ UUID           │ Optional: entity-specific        │
│ session_window         │ INT            │ NOT NULL, # sessions merged      │
│ structured_facts       │ JSONB          │ NOT NULL, fact objects array     │
│ prose_summary          │ TEXT           │ NOT NULL, human-readable         │
│ embedding  📊          │ vector(1536)   │ For retrieval                    │
│ source_memory_ids      │ JSONB          │ NOT NULL, traceability array     │
│ created_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘
 Indexes: HNSW on embedding, (user_id, created_at), entity_id
```

#### 4. Pattern Analysis Cache

```
┌────────────────────────────────────────────────────────────────────────────┐
│                       app.customer_patterns                                 │
│          Pre-computed patterns (24hr cache, nightly computation)            │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ Column                 │ Type           │ Constraints                      │
├────────────────────────┼────────────────┼─────────────────────────────────┤
│ pattern_id  🔑         │ UUID           │ PRIMARY KEY, auto-generated      │
│ customer_id  🔗        │ UUID           │ NOT NULL → domain.customers      │
│ pattern_type           │ VARCHAR(50)    │ NOT NULL                         │
│                        │                │ • rush_order_frequency           │
│                        │                │ • payment_timing_shift           │
│                        │                │ • growth_trajectory              │
│                        │                │ • service_escalation_pattern     │
│ confidence             │ DECIMAL(3,2)   │ NOT NULL, 0-1                    │
│ significance           │ DECIMAL(3,2)   │ NOT NULL, 0-1 (impact score)     │
│ insight                │ TEXT           │ NOT NULL, human description      │
│ data                   │ JSONB          │ NOT NULL, supporting metrics     │
│ recommendation         │ TEXT           │ Actionable next step             │
│ computed_at            │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘
 Constraints: UNIQUE (customer_id, pattern_type) -- one of each type per customer
 Indexes: (customer_id, computed_at DESC)
          (customer_id, confidence DESC) WHERE confidence > 0.6
```

#### 5. Workflow Automation

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          app.workflows                                      │
│            User workflows and AI-learned automation patterns                │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ Column                 │ Type           │ Constraints                      │
├────────────────────────┼────────────────┼─────────────────────────────────┤
│ workflow_id  🔑        │ UUID           │ PRIMARY KEY, auto-generated      │
│ user_id                │ UUID           │ NOT NULL                         │
│ name                   │ VARCHAR(255)   │ NOT NULL, workflow name          │
│ type                   │ VARCHAR(20)    │ NOT NULL                         │
│                        │                │ • implicit (AI-learned)          │
│                        │                │ • explicit (user-defined)        │
│ trigger                │ JSONB          │ NOT NULL, trigger definition     │
│ conditions             │ JSONB          │ DEFAULT '[]', when to run        │
│ actions                │ JSONB          │ DEFAULT '[]', what to do         │
│ confidence             │ DECIMAL(3,2)   │ DEFAULT 0.80 (for implicit)      │
│ user_confirmed         │ BOOLEAN        │ DEFAULT FALSE                    │
│ learned_from           │ JSONB          │ Pattern metadata if implicit     │
│ execution_count        │ INT            │ DEFAULT 0                        │
│ last_executed          │ TIMESTAMPTZ    │                                  │
│ active                 │ BOOLEAN        │ DEFAULT TRUE                     │
│ created_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
│ updated_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘
            │
            │ 1:N
            ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    app.workflow_suggestions                                 │
│              AI-generated workflow suggestions for user                     │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ suggestion_id  🔑      │ UUID           │ PRIMARY KEY, auto-generated      │
│ user_id                │ UUID           │ NOT NULL                         │
│ workflow_id  🔗        │ UUID           │ FK → workflows, CASCADE          │
│ suggestion             │ TEXT           │ NOT NULL, description            │
│ entity_id              │ UUID           │ Optional: related entity         │
│ shown                  │ BOOLEAN        │ DEFAULT FALSE                    │
│ acknowledged           │ BOOLEAN        │ DEFAULT FALSE                    │
│ created_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
│ shown_at               │ TIMESTAMPTZ    │                                  │
│ acknowledged_at        │ TIMESTAMPTZ    │                                  │
└────────────────────────┴────────────────┴─────────────────────────────────┘
 Indexes: (user_id, shown, created_at), workflow_id
```

#### 6. Supporting Tables

```
┌────────────────────────────────────────────────────────────────────────────┐
│               app.conversation_state_backup                                 │
│         PostgreSQL backup of Redis conversation context                     │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ session_id  🔑         │ UUID           │ PRIMARY KEY                      │
│ user_id                │ UUID           │ NOT NULL                         │
│ state_data             │ JSONB          │ NOT NULL, full Redis state       │
│ last_backup            │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                     app.pattern_baselines                                   │
│              Statistical baselines for anomaly detection                    │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ baseline_id  🔑        │ UUID           │ PRIMARY KEY, auto-generated      │
│ user_id                │ UUID           │ NOT NULL                         │
│ pattern_type           │ VARCHAR(50)    │ NOT NULL                         │
│ entity_type            │ VARCHAR(50)    │ Optional type filter             │
│ entity_id              │ UUID           │ Optional specific entity         │
│ baseline_metrics       │ JSONB          │ NOT NULL, statistical data       │
│ sample_size            │ INT            │ NOT NULL                         │
│ confidence_interval    │ DECIMAL(3,2)   │                                  │
│ last_updated           │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
│ created_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘
 Constraint: UNIQUE (user_id, pattern_type, entity_type, entity_id)

┌────────────────────────────────────────────────────────────────────────────┐
│                         app.async_jobs                                      │
│                    Celery task tracking table                               │
├────────────────────────┬────────────────┬─────────────────────────────────┤
│ job_id  🔑             │ UUID           │ PRIMARY KEY (Celery task ID)     │
│ user_id                │ UUID           │ NOT NULL                         │
│ session_id             │ UUID           │ Optional session context         │
│ job_type               │ VARCHAR(50)    │ NOT NULL (task type)             │
│ params                 │ JSONB          │ NOT NULL, task parameters        │
│ priority               │ VARCHAR(20)    │ DEFAULT 'medium'                 │
│                        │                │ • low, medium, high              │
│ status                 │ VARCHAR(20)    │ DEFAULT 'queued'                 │
│                        │                │ • queued, running, completed,    │
│                        │                │   failed, cancelled              │
│ result                 │ JSONB          │ Task output                      │
│ error                  │ TEXT           │ Error message if failed          │
│ created_at             │ TIMESTAMPTZ    │ DEFAULT NOW()                    │
│ started_at             │ TIMESTAMPTZ    │ When execution began             │
│ completed_at           │ TIMESTAMPTZ    │ When finished                    │
└────────────────────────┴────────────────┴─────────────────────────────────┘
 Indexes: (status, priority, created_at), (user_id, created_at), (job_type, status)
```

**Key Features:**
- 📊 Vector embeddings with HNSW indexes for sub-100ms similarity search
- 🔗 Entity resolution with fuzzy matching and learned aliases
- 🧠 Multi-type memory system (episodic, semantic, procedural, pattern)
- ⚡ Pre-computed pattern cache with 24hr TTL for instant insights
- 🔄 Workflow automation with AI-learned implicit workflows
- 💾 Redis state backup in PostgreSQL for disaster recovery

### Performance Indexes (Critical for Production)

#### Domain Schema Indexes

```
┌────────────────────────────────────────────────────────────────────────────┐
│                       ENTITY RESOLUTION INDEXES                             │
├────────────────────────────────────────────────────────────────────────────┤
│ idx_customers_name_trgm                                                     │
│   Table: domain.customers                                                   │
│   Type: GIN (Generalized Inverted Index) with trigram ops                  │
│   Column: name                                                              │
│   Purpose: Fast fuzzy text matching for entity resolution                  │
│   Performance: Enables ~50ms fuzzy search across 100K+ customers           │
│   Query Example:                                                            │
│     SELECT * FROM customers WHERE name % 'Dleta'  -- matches "Delta"       │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                      PATTERN ANALYSIS INDEXES                               │
├────────────────────────────────────────────────────────────────────────────┤
│ idx_sales_orders_customer_priority_created  (Partial Index)                │
│   Table: domain.sales_orders                                                │
│   Columns: (customer_id, priority, created_at)                             │
│   WHERE: priority = 'rush'                                                  │
│   Purpose: Fast rush order pattern detection per customer                  │
│   Performance: 10x faster queries for rush order analysis                  │
│   Size Reduction: 80% smaller than full index (only rush orders)           │
│                                                                             │
│ idx_sales_orders_customer_created                                           │
│   Columns: (customer_id, created_at DESC)                                  │
│   Purpose: Customer order history queries                                  │
│   Performance: Instant retrieval of recent orders per customer             │
│                                                                             │
│ idx_sales_orders_status  (Partial Index)                                   │
│   Columns: status                                                           │
│   WHERE: status != 'cancelled'                                              │
│   Purpose: Active order tracking and status reports                        │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                   PAYMENT TIMING ANALYSIS INDEXES                           │
├────────────────────────────────────────────────────────────────────────────┤
│ idx_payments_invoice_paid                                                   │
│   Table: domain.payments                                                    │
│   Columns: (invoice_id, paid_at)                                           │
│   Purpose: Payment timing pattern detection                                │
│                                                                             │
│ idx_invoices_customer_due                                                   │
│   Table: domain.invoices                                                    │
│   Columns: (customer_id, due_date, created_at)                             │
│   Purpose: Customer payment behavior analysis                              │
│                                                                             │
│ idx_invoices_due_date  (Partial Index)                                     │
│   Columns: (due_date, status)                                               │
│   WHERE: status = 'open'                                                    │
│   Purpose: Open invoice tracking and aging reports                         │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                      WORK ORDER INDEXES                                     │
├────────────────────────────────────────────────────────────────────────────┤
│ idx_work_orders_sales_order                                                 │
│   Columns: (sales_order_id, status)                                        │
│   Purpose: Order fulfillment tracking                                      │
│                                                                             │
│ idx_work_orders_status_date                                                 │
│   Columns: (status, updated_at)                                            │
│   Purpose: Work queue management and SLA monitoring                        │
└────────────────────────────────────────────────────────────────────────────┘
```

#### App Schema Indexes

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY RETRIEVAL INDEXES                            │
├────────────────────────────────────────────────────────────────────────────┤
│ idx_memories_embedding  🚀 CRITICAL PATH                                    │
│   Table: app.memories                                                       │
│   Type: HNSW (Hierarchical Navigable Small World)                          │
│   Column: embedding (vector 1536)                                          │
│   Parameters: m=16, ef_construction=64                                      │
│   Distance: Cosine similarity                                               │
│   Purpose: Fast vector similarity search for memory retrieval              │
│   Performance: Sub-100ms search across 1M+ memory chunks                   │
│   Query Example:                                                            │
│     SELECT * FROM memories                                                  │
│     ORDER BY embedding <=> query_vector LIMIT 10                           │
│                                                                             │
│ idx_memories_entity_links                                                   │
│   Type: GIN (JSONB array index)                                            │
│   Column: entity_links                                                      │
│   Purpose: Fast entity-based memory lookup                                 │
│   Query Example:                                                            │
│     SELECT * FROM memories                                                  │
│     WHERE entity_links @> '["customer-123"]'                               │
│                                                                             │
│ idx_memories_user_created                                                   │
│   Columns: (user_id, created_at DESC)                                      │
│   Purpose: Temporal memory queries (recency bias)                          │
│                                                                             │
│ idx_memories_kind  (Partial Index)                                         │
│   Column: kind                                                              │
│   WHERE: NOT deprecated                                                     │
│   Purpose: Memory type filtering (episodic vs semantic)                    │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                  MEMORY SUMMARIES INDEXES                                   │
├────────────────────────────────────────────────────────────────────────────┤
│ idx_summaries_embedding  🚀 CRITICAL PATH                                   │
│   Type: HNSW vector index (m=16, ef_construction=64)                       │
│   Column: embedding (vector 1536)                                          │
│   Purpose: Consolidated memory similarity search                           │
│                                                                             │
│ idx_summaries_user, idx_summaries_entity                                    │
│   Purpose: User/entity-specific summary retrieval                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                      ENTITY RESOLUTION INDEXES                              │
├────────────────────────────────────────────────────────────────────────────┤
│ idx_entities_name                                                           │
│   Purpose: Fast entity name lookup                                         │
│                                                                             │
│ idx_entities_external_ref                                                   │
│   Type: GIN (JSONB index)                                                  │
│   Purpose: Domain data → entity linking                                    │
│                                                                             │
│ idx_entity_aliases_alias                                                    │
│   Column: alias_text                                                        │
│   Purpose: Alias → canonical entity resolution                             │
│   Query Example: "DI" → "Delta Industries"                                 │
│                                                                             │
│ UNIQUE (user_id, alias_text, entity_id)                                    │
│   Purpose: Prevent duplicate alias mappings                                │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                     PATTERN CACHE INDEXES                                   │
├────────────────────────────────────────────────────────────────────────────┤
│ idx_customer_patterns_computed                                              │
│   Columns: (customer_id, computed_at DESC)                                 │
│   Purpose: Fetch latest patterns with 24hr cache check                     │
│   Query Example:                                                            │
│     SELECT * FROM customer_patterns                                         │
│     WHERE customer_id = $1 AND computed_at > NOW() - INTERVAL '24 hours'  │
│                                                                             │
│ idx_customer_patterns_confidence  (Partial Index)                          │
│   Columns: (customer_id, confidence DESC)                                  │
│   WHERE: confidence > 0.6                                                   │
│   Purpose: Significant pattern filtering (exclude noise)                   │
│   Size: ~60% of full index (only high-confidence patterns)                 │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                    OTHER APP SCHEMA INDEXES                                 │
├────────────────────────────────────────────────────────────────────────────┤
│ idx_chat_events_session, idx_chat_events_user                              │
│   Purpose: Conversation history retrieval                                  │
│                                                                             │
│ idx_workflows_trigger  (GIN index)                                          │
│   Purpose: Fast workflow trigger matching                                  │
│                                                                             │
│ idx_async_jobs_status                                                       │
│   Columns: (status, priority, created_at)                                  │
│   Purpose: Job queue processing (Celery)                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

**Index Build Strategy:**
- Use `CREATE INDEX CONCURRENTLY` to avoid table locks during creation
- Build indexes during off-peak hours for large tables
- Monitor index bloat and rebuild periodically with `REINDEX CONCURRENTLY`
- Estimated total index size: ~30-40% of table size

### Memory Lifecycle Management

#### Garbage Collection Strategy

```
┌────────────────────────────────────────────────────────────────────────────┐
│                      MEMORY LIFECYCLE FLOW                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  NEW MEMORY                                                                 │
│      │                                                                       │
│      ├─ importance: 0.50                                                    │
│      ├─ confidence: 0.70                                                    │
│      ├─ reinforcement_count: 0                                              │
│      ├─ ttl_days: 365                                                       │
│      └─ deprecated: FALSE                                                   │
│      │                                                                       │
│      ▼                                                                       │
│  ACTIVE MEMORY (0-365 days)                                                 │
│      │                                                                       │
│      ├─ Gets accessed → reinforcement_count++                              │
│      │                                                                       │
│      ├─ If reinforcement_count >= 3                                         │
│      │    → PROTECTED from garbage collection                              │
│      │    → Becomes "important" memory                                      │
│      │                                                                       │
│      └─ If never reinforced (count < 3)                                     │
│         → Eligible for deprecation after TTL                               │
│      │                                                                       │
│      ▼                                                                       │
│  SOFT DELETE (deprecated = TRUE)                                            │
│      │                                                                       │
│      ├─ 30-day grace period                                                 │
│      ├─ Still in database                                                   │
│      ├─ Excluded from queries (WHERE NOT deprecated)                       │
│      └─ Can be restored if accessed                                         │
│      │                                                                       │
│      ▼                                                                       │
│  HARD DELETE (after 30 days)                                                │
│      │                                                                       │
│      └─ Permanently removed from database                                   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                 FUNCTION: gc_old_memories()                                 │
│                        Soft Delete Phase                                    │
├────────────────────────────────────────────────────────────────────────────┤
│ Purpose:                                                                    │
│   Mark old, unreinforced memories as deprecated                            │
│                                                                             │
│ Criteria for Deprecation:                                                  │
│   1. Age: created_at + ttl_days < NOW()                                    │
│   2. Low engagement: reinforcement_count < 3                                │
│   3. Not already deprecated                                                 │
│                                                                             │
│ Action:                                                                     │
│   UPDATE app.memories SET deprecated = TRUE                                │
│                                                                             │
│ Returns:                                                                    │
│   Count of deprecated memories                                             │
│                                                                             │
│ Typical Results:                                                            │
│   • Day 1: ~500 memories deprecated (initial cleanup)                      │
│   • Daily: ~20-50 memories deprecated (routine)                            │
│                                                                             │
│ Scheduling:                                                                 │
│   Run daily at 2:00 AM (low traffic period)                                │
│                                                                             │
│ Example Execution:                                                          │
│   SELECT deprecated_count FROM gc_old_memories();                          │
│   Result: 42 memories marked as deprecated                                 │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│           FUNCTION: gc_delete_deprecated_memories()                         │
│                      Hard Delete Phase                                      │
├────────────────────────────────────────────────────────────────────────────┤
│ Purpose:                                                                    │
│   Permanently delete memories that have been deprecated for 30+ days       │
│                                                                             │
│ Criteria for Deletion:                                                     │
│   1. deprecated = TRUE                                                      │
│   2. updated_at < NOW() - INTERVAL '30 days'                               │
│                                                                             │
│ Action:                                                                     │
│   DELETE FROM app.memories (permanent)                                     │
│                                                                             │
│ Returns:                                                                    │
│   Count of deleted memories                                                │
│                                                                             │
│ 30-Day Grace Period Rationale:                                             │
│   • Allows recovery if memory was incorrectly deprecated                   │
│   • User can restore via "I told you about X" queries                      │
│   • Gives time for consolidation process to run                            │
│                                                                             │
│ Typical Results:                                                            │
│   • Weekly: ~100-200 memories permanently deleted                          │
│                                                                             │
│ Scheduling:                                                                 │
│   Run weekly on Sunday at 3:00 AM                                          │
│                                                                             │
│ Example Execution:                                                          │
│   SELECT deleted_count FROM gc_delete_deprecated_memories();               │
│   Result: 156 memories permanently deleted                                 │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                   MEMORY PROTECTION RULES                                   │
├────────────────────────────────────────────────────────────────────────────┤
│ Memories NEVER garbage collected:                                          │
│                                                                             │
│ 1. High Reinforcement: reinforcement_count >= 3                            │
│    → User has accessed this memory multiple times                          │
│    → Indicates importance to user                                          │
│                                                                             │
│ 2. Semantic Memories: kind = 'semantic' AND importance > 0.8               │
│    → Core facts about entities                                             │
│    → Long-term knowledge                                                   │
│                                                                             │
│ 3. Superseding Memories: EXISTS (superseded_by)                            │
│    → Memory has been consolidated into a summary                           │
│    → Keep for traceability                                                 │
│                                                                             │
│ 4. Recent Memories: created_at > NOW() - INTERVAL '7 days'                │
│    → Too new to evaluate usefulness                                        │
│    → Wait for potential reinforcement                                      │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                      MONITORING METRICS                                     │
├────────────────────────────────────────────────────────────────────────────┤
│ Track these metrics for memory health:                                     │
│                                                                             │
│ • Total Memories: ~10K-100K per user                                        │
│ • Deprecated %: Target 10-15% (healthy turnover)                           │
│ • Avg Reinforcement: Target 1.5-2.0 per memory                             │
│ • GC Rate: ~2-5% deprecation rate per month                                │
│                                                                             │
│ Alerts:                                                                     │
│   • Deprecated % > 30% → Too aggressive, increase TTL                      │
│   • Deprecated % < 5% → Too conservative, decrease TTL                     │
│   • Avg Reinforcement < 1.0 → Low engagement, review memory quality        │
└────────────────────────────────────────────────────────────────────────────┘
```

**Cron Schedule (pg_cron or external scheduler):**
```
# Daily soft-delete at 2:00 AM
0 2 * * * SELECT gc_old_memories();

# Weekly hard-delete on Sunday at 3:00 AM
0 3 * * 0 SELECT gc_delete_deprecated_memories();
```

---

## This Flow Handles:

✅ Complex decision support queries
✅ Multi-dimensional analysis (financial, risk, relationship)
✅ Pattern detection and insights
✅ Transparent reasoning with confidence scores
✅ Quality-controlled responses
✅ Graceful degradation on failures
✅ Sub-10s response times (p95)
✅ Comprehensive observability
✅ Asynchronous background operations
