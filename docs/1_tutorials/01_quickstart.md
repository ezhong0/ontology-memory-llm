# Quickstart: Your First Memory-Aware Agent

**Goal**: Get the system running and understand the core workflow in 15 minutes.

**Prerequisites**:
- Python 3.11+
- Docker Desktop running
- 2GB free RAM
- Terminal/command line

## What You'll Learn

By the end of this tutorial, you'll:
1. ✅ Start the memory system locally
2. ✅ Send your first chat message
3. ✅ See entity resolution in action (5-stage hybrid algorithm)
4. ✅ Query domain data (sales orders, invoices, work orders)
5. ✅ Create and retrieve contextual memories
6. ✅ Understand the complete data flow

---

## Step 1: Setup (5 minutes)

### Clone and Install

```bash
# Clone repository
git clone <repo-url>
cd adenAssessment2

# One-command setup (installs deps, starts DB, runs migrations, seeds data)
make setup
```

**What just happened?**
- ✅ Installed ~43 Python packages via Poetry
- ✅ Started PostgreSQL container with pgvector extension
- ✅ Created 16 database tables (10 memory system + 6 domain)
- ✅ Applied 12 Alembic migrations
- ✅ Ready to run!

<details>
<summary>Troubleshooting: setup fails</summary>

**Problem**: `poetry not found`
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
```

**Problem**: Port 5432 already in use
```bash
# Option 1: Stop existing PostgreSQL
brew services stop postgresql

# Option 2: Change port in docker-compose.yml
# Edit: "5432:5432" → "5433:5432"
```

**Problem**: Permission denied on Docker
```bash
# Start Docker Desktop first, then retry
make docker-up
```
</details>

---

## Step 2: Start the API Server (2 minutes)

Open a **new terminal** and run:

```bash
cd adenAssessment2
make run
```

**Expected output**:
```
Starting development server...
API will be available at: http://localhost:8000
OpenAPI docs: http://localhost:8000/docs
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Verify**: Visit http://localhost:8000/docs to see auto-generated API documentation.

---

## Step 3: Your First Chat Message (3 minutes)

Open a **third terminal** (keep server running) and send your first request:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "message": "Remember: Kai Media prefers Friday deliveries and NET30 payment terms."
  }'
```

**Expected Response** (simplified):
```json
{
  "response": "I've recorded that Kai Media prefers Friday deliveries and NET30 payment terms.",
  "augmentation": {
    "entities_resolved": [
      {
        "mention": "Kai Media",
        "entity_id": "customer_kai_123",
        "canonical_name": "Kai Media",
        "confidence": 1.0,
        "method": "domain_bootstrap"
      }
    ],
    "domain_facts": [],
    "memories_retrieved": []
  },
  "memories_created": [
    {
      "memory_type": "semantic",
      "subject_entity_id": "customer_kai_123",
      "predicate": "delivery_preference",
      "object_value": {type: "day_of_week", "value": "Friday"},
      "confidence": 0.85
    },
    {
      "memory_type": "semantic",
      "subject_entity_id": "customer_kai_123",
      "predicate": "payment_terms",
      "object_value": {"type": "payment_term", "value": "NET30"},
      "confidence": 0.85
    },
    {
      "memory_type": "episodic",
      "summary": "User said: Remember: Kai Media prefers Friday..."
    }
  ]
}
```

**What happened?**

```
User Input: "Remember: Kai Media prefers Friday deliveries and NET30 payment terms."
    ↓
┌─────────────────────────────────────────────┐
│ Phase 1: Entity Resolution (5-stage)       │
│ "Kai Media" → 5-stage algorithm:           │
│  Stage 1: Exact match ❌                    │
│  Stage 2: User alias ❌                     │
│  Stage 3: Fuzzy match ❌                    │
│  Stage 4: LLM coreference ❌                │
│  Stage 5: Domain bootstrap ✅               │
│  Result: customer_kai_123 (0.90 confidence)│
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Phase 2: Semantic Extraction (LLM)         │
│ LLM call to extract facts:                 │
│   "Kai Media prefers Friday deliveries"    │
│   → (Kai, delivery_preference, Friday)     │
│                                             │
│   "NET30 payment terms"                    │
│   → (Kai, payment_terms, NET30)            │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Phase 3: Domain Augmentation                │
│ Query domain.customers, sales_orders, etc.  │
│ (No results for new entity)                │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Phase 4: Memory Storage                     │
│ Store 2 semantic memories:                  │
│  - delivery_preference: Friday             │
│  - payment_terms: NET30                    │
│ Store 1 episodic memory (conversation)     │
└─────────────────────────────────────────────┘
    ↓
Response: "I've recorded that Kai Media..."
```

**Key Observations**:
- ✅ **Stage 5 (Domain Bootstrap)**: System didn't have "Kai Media" in memory, but might exist in domain DB. Creates canonical entity on-the-fly.
- ✅ **LLM Extraction**: Parsed conversational text into structured triples
- ✅ **Confidence = 0.85**: Not 1.0 (max 0.95) – epistemic humility principle
- ✅ **Memory Types**: Semantic (facts) + Episodic (events)

---

## Step 4: Test Memory Persistence (3 minutes)

Now query the system using the memory you just created:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "message": "When should we deliver to Kai Media?"
  }'
```

**Expected Response**:
```json
{
  "response": "Based on my records, Kai Media prefers Friday deliveries.",
  "augmentation": {
    "entities_resolved": [
      {
        "mention": "Kai Media",
        "entity_id": "customer_kai_123",
        "canonical_name": "Kai Media",
        "confidence": 1.0,
        "method": "exact_match"
      }
    ],
    "domain_facts": [],
    "memories_retrieved": [
      {
        "memory_id": 1,
        "memory_type": "semantic",
        "predicate": "delivery_preference",
        "object_value": {"type": "day_of_week", "value": "Friday"},
        "confidence": 0.85,
        "relevance_score": 0.94
      }
    ]
  },
  "provenance": {
    "memory_ids": [1],
    "similarity_scores": [0.94],
    "memory_count": 1,
    "source_types": ["semantic"]
  }
}
```

**What happened?**

```
User Input: "When should we deliver to Kai Media?"
    ↓
┌─────────────────────────────────────────────┐
│ Phase 1: Entity Resolution                  │
│ "Kai Media" → Stage 1 (Exact Match) ✅      │
│ Result: customer_kai_123 (1.0 confidence)  │
│ Time: 20ms, Cost: $0                       │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Phase 2: Semantic Extraction                │
│ Extract: (user, inquires_about, delivery)  │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Phase 3: Multi-Signal Retrieval             │
│ 1. Generate query embedding (1536-dim)     │
│ 2. pgvector search → top 100 candidates    │
│ 3. Score each candidate:                   │
│    0.40 × semantic_similarity (0.92)       │
│    0.25 × entity_overlap (1.0)             │
│    0.20 × recency (0.95)                   │
│    0.10 × temporal_coherence (1.0)         │
│    0.05 × importance (0.50)                │
│    = 0.94 relevance score                  │
│ 4. Return top 5 memories                   │
│ Time: 60ms, Cost: $0                       │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Phase 4: LLM Reply Generation               │
│ System prompt includes:                     │
│  - Resolved entities: [Kai Media]          │
│  - Retrieved memories: [Friday delivery]   │
│  - Domain facts: []                        │
│ LLM generates natural language response    │
└─────────────────────────────────────────────┘
    ↓
Response: "Based on my records, Kai Media prefers Friday deliveries."
```

**Key Observations**:
- ✅ **Exact Match (Stage 1)**: Now "Kai Media" resolves instantly (<20ms)
- ✅ **Memory Retrieved**: System recalled Friday preference from previous turn
- ✅ **Provenance Tracking**: Response includes memory IDs, similarity scores
- ✅ **Multi-Signal Scoring**: 5 signals (not just vector similarity)

---

## Step 5: Query Domain Database (3 minutes)

Now let's test domain database integration. The system bridges **conversational mentions** to **structured business data**.

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "message": "What invoices does Kai Media have?"
  }'
```

**Expected Response** (if domain seeded):
```json
{
  "response": "Based on the current data, Kai Media has one unpaid invoice (INV-1009) for $1,200, which was due on September 30, 2024. Since this is past due and they typically use NET30 payment terms, you may want to send a payment reminder.",
  "augmentation": {
    "entities_resolved": [
      {
        "mention": "Kai Media",
        "entity_id": "customer_kai_123",
        "canonical_name": "Kai Media",
        "confidence": 1.0,
        "method": "exact_match"
      }
    ],
    "domain_facts": [
      {
        "fact_type": "invoice",
        "entity_id": "customer_kai_123",
        "table": "domain.invoices",
        "content": "INV-1009: $1,200, open, due 2024-09-30",
        "metadata": {
          "invoice_id": "inv_1009",
          "amount": 1200.00,
          "status": "open",
          "due_date": "2024-09-30"
        }
      }
    ],
    "memories_retrieved": [
      {
        "memory_id": 2,
        "predicate": "payment_terms",
        "object_value": {"value": "NET30"},
        "confidence": 0.85,
        "relevance_score": 0.89
      }
    ]
  }
}
```

**What happened?**

```
User Input: "What invoices does Kai Media have?"
    ↓
┌─────────────────────────────────────────────┐
│ Phase 1: Entity Resolution                  │
│ Result: customer_kai_123                   │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Phase 2: Domain Augmentation (NEW!)        │
│ 1. Detect: entity_type = "customer"        │
│ 2. Query domain database:                  │
│    SELECT * FROM domain.invoices            │
│    WHERE customer_id = 'kai_123'           │
│ 3. Return: INV-1009 ($1,200, open)         │
│ Time: 40ms, Cost: $0                       │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Phase 3: Memory Retrieval                   │
│ Retrieve: payment_terms = NET30            │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Phase 4: LLM Reply Generation               │
│ Combines:                                   │
│  - Domain fact: invoice INV-1009           │
│  - Memory: NET30 terms                     │
│  - Business logic: Past due → reminder     │
└─────────────────────────────────────────────┘
    ↓
Response: Natural language combining DB + memory
```

**Key Observations**:
- ✅ **Dual Truth System**: Database = authoritative facts (invoice exists), Memory = context (NET30 preference)
- ✅ **Proactive Intelligence**: System inferred "send reminder" from past-due date
- ✅ **Structured + Unstructured**: SQL query results + vector search results

---

## Step 6: Test Conflict Detection (2 minutes)

Let's see what happens when memory and database disagree:

```bash
# Turn 1: Create a memory about order status
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "message": "Kai Medias order SO-1001 is fulfilled."
  }'

# Turn 2: Query status (database says "in_fulfillment", memory says "fulfilled")
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "message": "What is the status of SO-1001?"
  }'
```

**Expected Response (Turn 2)**:
```json
{
  "response": "According to the current database, SO-1001 is in_fulfillment (not yet complete). Note: Our memory previously indicated it was fulfilled, but the database shows otherwise.",
  "augmentation": {
    "domain_facts": [
      {
        "fact_type": "sales_order",
        "content": "SO-1001: in_fulfillment",
        "metadata": {"status": "in_fulfillment"}
      }
    ],
    "memories_retrieved": [
      {
        "predicate": "status",
        "object_value": {"value": "fulfilled"},
        "confidence": 0.70
      }
    ]
  },
  "conflicts_detected": [
    {
      "conflict_type": "memory_vs_db",
      "subject": "sales_order_so_1001",
      "predicate": "status",
      "existing_value": "fulfilled",
      "new_value": "in_fulfillment",
      "existing_confidence": 0.70,
      "new_confidence": 1.0,
      "resolution_strategy": "trust_db"
    }
  ]
}
```

**Key Observations**:
- ✅ **Epistemic Humility**: System **exposes conflict** rather than hiding it
- ✅ **Trust Database**: Domain DB = source of truth (correspondence truth)
- ✅ **Memory Decay**: Conflicted memory marked for decay
- ✅ **Transparency**: Conflict details included in response

---

## Step 7: Understanding the Architecture (2 minutes)

### 6-Layer Memory Architecture

Your memories are stored in specialized layers:

```
┌────────────────────────────────────────────────┐
│ Layer 6: Summaries                             │
│ "Kai Media: NET30, Friday delivery, 3 orders" │
│ (Cross-session consolidations)                 │
└────────────────────────────────────────────────┘
                    ↑ consolidates
┌────────────────────────────────────────────────┐
│ Layer 5: Procedural                            │
│ "When invoice mentioned → check domain.invoices"│
│ (Learned heuristics)                           │
└────────────────────────────────────────────────┘
                    ↑ derives
┌────────────────────────────────────────────────┐
│ Layer 4: Semantic                              │
│ (Kai, delivery_preference, Friday)             │
│ (Kai, payment_terms, NET30)                    │
│ (Structured facts as SPO triples)              │
└────────────────────────────────────────────────┘
                    ↑ extracts
┌────────────────────────────────────────────────┐
│ Layer 3: Episodic                              │
│ "User asked about Kai's delivery on 2024-10-15"│
│ (Conversation events with context)             │
└────────────────────────────────────────────────┘
                    ↑ identifies
┌────────────────────────────────────────────────┐
│ Layer 2: Entities                              │
│ customer_kai_123 → "Kai Media Productions"    │
│ (Canonical entity resolution)                  │
└────────────────────────────────────────────────┘
                    ↑ mentions
┌────────────────────────────────────────────────┐
│ Layer 1: Chat Events                           │
│ "Remember: Kai Media prefers Friday..."       │
│ (Immutable audit trail)                        │
└────────────────────────────────────────────────┘
```

### 5-Stage Entity Resolution

```python
# Stage 1: Exact match (70% of cases) - <20ms, $0
"Kai Media" → Check canonical_entities table → ✅ Found

# Stage 2: User alias (15% of cases) - <25ms, $0
"Kay Media" → Check entity_aliases → "Kay" → "Kai Media"

# Stage 3: Fuzzy match (10% of cases) - <50ms, $0
"Kai Meda" → pg_trgm similarity > 0.7 → "Kai Media"

# Stage 4: LLM coreference (5% of cases) - <300ms, $0.03
"they" (in context) → LLM: "they" refers to "Kai Media"

# Stage 5: Domain bootstrap (<1% of cases) - <40ms, $0
"New Customer Inc" → Query domain.customers → Create entity
```

**Cost Comparison**:
- **This system**: $0.002/turn (95% deterministic)
- **Pure LLM**: $0.03/turn (100% LLM for entity resolution)
- **15x cheaper!**

---

## Step 8: Explore the OpenAPI Docs (Optional)

Visit http://localhost:8000/docs to see:

### Available Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/chat` | Main chat endpoint (simplified) |
| `POST /api/v1/chat/message` | Structured chat with full resolution |
| `POST /api/v1/chat/message/enhanced` | Chat + memory retrieval |
| `POST /api/v1/consolidate` | Consolidate memories into summaries |
| `GET /api/v1/procedural` | Retrieve learned procedural patterns |
| `POST /api/v1/conflicts` | Manage memory conflicts |
| `GET /api/v1/health` | Health check |

Try the **interactive API docs**:
1. Click on `POST /api/v1/chat`
2. Click "Try it out"
3. Enter request body:
   ```json
   {
     "user_id": "demo_user",
     "message": "Test message"
   }
   ```
4. Click "Execute"
5. See response inline

---

## Next Steps

### Learn More

- **[Architecture Deep Dive](../3_explanation/architecture_overview.md)** - Understand hexagonal architecture, data flow
- **[API Reference](../4_reference/api_reference.md)** - Complete endpoint specifications
- **[Configuration Guide](../4_reference/configuration_reference.md)** - 43 tunable parameters
- **[Testing Strategy](../3_explanation/testing_strategy.md)** - 130+ tests (unit, integration, E2E)

### Try Advanced Features

#### 1. Test Disambiguation

```bash
# Create two similar entities
curl -X POST http://localhost:8000/api/v1/chat \
  -d '{"user_id": "demo", "message": "Apple Inc is a tech company"}'

curl -X POST http://localhost:8000/api/v1/chat \
  -d '{"user_id": "demo", "message": "Apple Farm Supply is an agriculture company"}'

# Ambiguous query
curl -X POST http://localhost:8000/api/v1/chat \
  -d '{"user_id": "demo", "message": "What'\''s Apple'\''s status?"}'

# Response will ask you to choose between the two
```

#### 2. Test PII Redaction

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -d '{
    "user_id": "demo",
    "message": "Remember my phone: 415-555-0199 for urgent alerts"
  }'

# System will redact PII before storage
```

#### 3. Test Memory Decay

```bash
# Create a memory, then check after 60 days (simulated)
# In production: confidence decays exponentially
# Reaches 0.5 confidence in ~60 days
```

#### 4. Run Tests

```bash
# Run all 130+ tests
make test

# Run only E2E tests (18 real-world scenarios)
make test-e2e

# Run in watch mode (TDD)
make test-watch
```

#### 5. Check Code Quality

```bash
# Run all quality checks
make check-all
# → Lint (ruff)
# → Type check (mypy strict)
# → Test coverage (80% minimum)
```

---

## Common Commands Cheat Sheet

```bash
# Infrastructure
make docker-up          # Start PostgreSQL
make docker-down        # Stop services
make docker-clean       # ⚠️  Destroy all data

# Database
make db-migrate         # Apply migrations
make db-rollback        # Undo last migration
make db-reset           # ⚠️  Reset database
make db-shell           # Open psql shell

# Development
make run                # Start API server
make test-watch         # TDD mode
make format             # Auto-format code
make check-all          # Pre-commit checks

# Testing
make test               # All tests
make test-unit          # Unit tests only (fast)
make test-integration   # Integration tests (requires DB)
make test-e2e           # End-to-end tests
make test-cov           # Coverage report

# Cleanup
make clean              # Remove caches
make clean-all          # Deep clean (Docker + caches)
```

---

## Troubleshooting

### API Server Won't Start

**Problem**: `Address already in use`
```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use different port
poetry run uvicorn src.api.main:app --port 8001
```

### Database Connection Failed

**Problem**: `FATAL: database "memorydb" does not exist`
```bash
# Reset database
make db-reset
```

### Tests Failing

**Problem**: `pytest: command not found`
```bash
# Activate Poetry environment
poetry shell

# Or prefix with poetry run
poetry run pytest
```

### Memory Retrieval Returns Nothing

**Problem**: Memories not retrieved despite being created

**Debug**:
```bash
# Check if memories exist
make db-shell
# In psql:
SELECT * FROM app.semantic_memories;
```

Possible causes:
1. **Entity mismatch**: Memory stored for different entity ID
2. **Confidence too low**: Adjust `MEMORY_MIN_CONFIDENCE` in heuristics.py
3. **Embedding issue**: Check if embeddings are generated

---

## Key Takeaways

After completing this quickstart, you should understand:

1. ✅ **5-Stage Entity Resolution**: 95% resolved without LLM (cost-efficient)
2. ✅ **6-Layer Memory Architecture**: Specialized storage for different query patterns
3. ✅ **Dual Truth System**: Database = facts, Memory = context
4. ✅ **Multi-Signal Scoring**: 5 signals (not just vector similarity)
5. ✅ **Epistemic Humility**: Max confidence 0.95, expose conflicts
6. ✅ **Provenance Tracking**: Every response cites sources
7. ✅ **Domain Integration**: Bridge conversations to structured business data

**Performance Metrics** (from this quickstart):
- Entity resolution: <50ms average (Stage 1-3)
- Memory retrieval: <60ms for 100 candidates
- Full chat with LLM: <800ms P95

**Cost** (per turn):
- Entity resolution: $0.00075 average
- Semantic extraction: $0.024
- Memory retrieval: $0 (deterministic)
- Reply generation: $0.03
- **Total**: ~$0.055 (vs $0.67 pure LLM approach)

---

## What's Next?

### Deep Dives
- [Architecture Overview](../3_explanation/architecture_overview.md) - Why these design choices?
- [Cost Optimization](../3_explanation/cost_optimization.md) - Surgical LLM usage explained
- [Conflict Resolution](../3_explanation/conflict_resolution.md) - Memory vs DB conflicts

### How-To Guides
- [Tune Scoring Weights](../2_how-to-guides/tune_scoring_weights.md) - Adjust multi-signal weights
- [Add Custom Entity Type](../2_how-to-guides/add_custom_entity_type.md) - Extend the entity system

### Reference
- [API Endpoints](../4_reference/api_reference.md) - Complete specifications
- [Database Schema](../4_reference/database_schema.md) - Table definitions + ERD
- [Configuration Options](../4_reference/configuration_reference.md) - All 43 heuristics

---

**Congratulations!** You've completed the quickstart and understand the core workflow. The system is now running locally and you can start building memory-aware agents.

**Questions?** Check the [troubleshooting section](#troubleshooting) or open an issue on GitHub.
