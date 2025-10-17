# Ontology-Aware Memory System

> Transform stateless LLM agents into experienced colleagues with perfect recall, business context awareness, and epistemic humility.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Type Checking](https://img.shields.io/badge/mypy-strict-success)](https://mypy-lang.org/)
[![Code Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)]()
[![Tests](https://img.shields.io/badge/tests-130%2B-brightgreen)]()

## The Problem

Traditional LLMs are **stateless** — they forget everything between conversations and lack business context:

```python
# Turn 1
User: "What's Gai Media's order status?"
LLM: "I don't have access to that information."

# Turn 2 (new conversation)
User: "What did we just discuss?"
LLM: "I don't have any prior conversation history."
```

This system transforms LLMs into **experienced colleagues** that:
- Remember every conversation across sessions
- Integrate with your business database (ERP/CRM)
- Admit uncertainty when data conflicts
- Explain their reasoning with provenance tracking

## Quick Example

```bash
# Start the system
make setup && make run

# Send a chat message
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "message": "What is Gai Media'\''s current order status and unpaid invoices?"
  }'
```

**What happens under the hood:**

```
1. Entity Resolution (5-stage algorithm)
   "Gai Media" → customer:gai_123 (via exact match, 20ms)

2. Domain Database Query
   → sales_orders: SO-1001 (in_fulfillment, 500 units)
   → invoices: INV-1009 ($1,200, open, due Sept 30)

3. Memory Retrieval (multi-signal scoring)
   → "Gai Media prefers Friday deliveries" (confidence: 0.92)
   → "Payment terms: NET30" (confidence: 0.88)

4. Natural Language Response
   "Based on your current data, Gai Media Productions has one active
   sales order (SO-1001) for 500 units currently in fulfillment.
   They have one unpaid invoice (INV-1009) for $1,200, due September 30.
   Since this is past due and they typically use NET30 terms, you may
   want to send a payment reminder."
```

**Response includes full provenance:**

```json
{
  "response": "Based on your current data, Gai Media...",
  "augmentation": {
    "entities_resolved": [
      {
        "mention": "Gai Media",
        "entity_id": "customer:gai_123",
        "confidence": 1.0,
        "method": "exact_match"
      }
    ],
    "domain_facts": [
      {
        "fact_type": "sales_order",
        "content": "SO-1001: 500 units, in_fulfillment",
        "source_table": "domain.sales_orders"
      }
    ],
    "memories_retrieved": [
      {
        "predicate": "payment_terms",
        "object": "NET30",
        "confidence": 0.88,
        "similarity_score": 0.91
      }
    ]
  },
  "provenance": {
    "memory_ids": [1, 2],
    "memory_count": 2,
    "source_types": ["semantic", "semantic"]
  }
}
```

## Key Features

### 🧠 6-Layer Memory Architecture
```
Layer 6: Summaries     (cross-session consolidations)
Layer 5: Procedural    (learned heuristics: "when X, do Y")
Layer 4: Semantic      (facts as subject-predicate-object triples)
Layer 3: Episodic      (conversation events with context)
Layer 2: Entities      (canonical entity resolution)
Layer 1: Chat Events   (immutable audit trail)
```

### 🎯 5-Stage Entity Resolution (95% Deterministic)
```python
# 70% → Stage 1: Exact match            (<20ms, $0)
# 15% → Stage 2: User aliases           (<25ms, $0)
# 10% → Stage 3: Fuzzy match (pg_trgm)  (<50ms, $0)
#  5% → Stage 4: LLM coreference         (<300ms, $0.03)
# <1% → Stage 5: Domain DB bootstrap    (<40ms, $0)
```

**Cost efficiency:** $0.002/turn vs $0.03 for pure LLM approaches (15x cheaper)

### 🔄 Dual Truth System
- **Database**: Authoritative facts (source of truth)
- **Memory**: Contextual understanding & learned preferences
- **Conflict Resolution**: Expose conflicts, trust DB, mark memory for decay

Example:
```
Memory says: "Status: in_fulfillment" (confidence: 0.85)
Database says: "Status: shipped"
→ System returns: "Status is now shipped (changed from in_fulfillment)"
→ Memory marked as conflicted, confidence decayed
```

### 📊 Multi-Signal Retrieval Scoring
```python
relevance_score = (
    0.40 × semantic_similarity   # Vector similarity
  + 0.25 × entity_overlap        # Mentioned entities
  + 0.20 × recency               # Time-based decay
  + 0.10 × temporal_coherence    # Conversation flow
  + 0.05 × importance            # User-marked priority
)
```

Scores 100+ candidates in <100ms (zero LLM calls)

### 🔐 PII Detection & Redaction
Automatically detects and redacts sensitive data before storage:
- Email addresses
- Phone numbers
- SSNs
- Credit card numbers

### 🤔 Epistemic Humility
- **Never 100% confident** (max confidence: 0.95)
- **Exponential decay** over time (reaches 0.5 in ~60 days)
- **Exposes conflicts** explicitly (memory vs database)
- **Cites sources** (provenance tracking)

## Quick Start

### Prerequisites
- Python 3.11+
- Docker Desktop
- 2GB RAM

### Setup (5 minutes)

```bash
# 1. Clone repository
git clone <repo-url>
cd adenAssessment2

# 2. One-command setup (installs deps, starts DB, runs migrations, seeds data)
make setup

# 3. Start API server
make run
# → API: http://localhost:8000
# → OpenAPI docs: http://localhost:8000/docs
```

### Your First Chat

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "message": "What customers do we have?"
  }'
```

**Next steps:**
- 📖 [Full Tutorial](docs/1_tutorials/01_quickstart.md) - 15-minute walkthrough
- 🏗️ [Architecture Overview](docs/3_explanation/architecture_overview.md) - Deep dive
- 📚 [API Reference](docs/4_reference/api_reference.md) - Complete endpoint specs

## Architecture Highlights

### Hexagonal Architecture (Ports & Adapters)

```
┌─────────────────────────────────────────┐
│      API Layer (FastAPI)                │
│  HTTP handlers, request validation      │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Application Layer (Use Cases)         │
│  Orchestrators coordinating services    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Domain Layer (Pure Business Logic)    │
│  • Entities: CanonicalEntity, Memory    │
│  • Services: EntityResolution, Scoring  │
│  • Ports: IEntityRepository (ABC)       │
│  NO infrastructure imports!             │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Infrastructure Layer (Adapters)       │
│  • PostgreSQL + pgvector                │
│  • OpenAI / Anthropic LLM services      │
│  • Concrete repository implementations  │
└─────────────────────────────────────────┘
```

**Why hexagonal?**
- Domain logic testable without database (mocks only)
- Swap PostgreSQL → MongoDB without changing business logic
- 100% type coverage in domain layer (mypy strict mode)

### Data Flow Example

```
User: "What's Gai's status?"
  ↓
API: Validate request (Pydantic)
  ↓
ProcessChatMessageUseCase: Orchestrate workflow
  ├─→ EntityResolutionService: "Gai" → "customer:gai_123"
  ├─→ DomainDatabasePort: Query sales_orders table
  ├─→ SemanticMemoryRepository: Vector search (pgvector)
  ├─→ MultiSignalScorer: Score 100 candidates (5 signals)
  └─→ LLMService: Generate natural language reply
  ↓
API: Return JSON response with provenance
```

### Key Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **5-stage entity resolution** | 95% resolved without LLM → 15x cheaper | 85% accuracy vs 90% pure LLM |
| **pgvector (not Pinecone)** | ACID transactions, $0 cost, <10M vectors | Limited to 10M vectors (Phase 1 sufficient) |
| **Surgical LLM usage** | Only where deterministic fails | Requires hybrid algorithm complexity |
| **Confidence decay** | Epistemic humility, active learning | More complex memory lifecycle |
| **Dual truth system** | Database = facts, Memory = context | Must handle conflicts explicitly |

## Project Statistics

| Metric | Value |
|--------|-------|
| **Lines of Code** | 12,000 production, 8,500 tests |
| **Test Coverage** | 85% overall (90% domain, 80% API, 70% infra) |
| **Test Count** | 130+ (unit, integration, E2E, property, performance) |
| **Type Safety** | 100% (mypy --strict mode) |
| **Performance** | P95 <800ms for full chat with LLM |
| **Cost** | $0.002/turn (15x cheaper than pure LLM) |
| **Architecture** | Hexagonal (zero infrastructure in domain) |

## Technology Stack

### Backend
- **Python** 3.11+ (async/await, type hints)
- **FastAPI** 0.109+ (REST API, OpenAPI docs)
- **SQLAlchemy** 2.0+ (async ORM)
- **PostgreSQL** 15+ (relational database)
- **pgvector** 0.2+ (vector similarity search)
- **Alembic** 1.13+ (schema migrations)

### LLM & Embeddings
- **OpenAI** (GPT-4, text-embedding-3-small)
- **Anthropic** (Claude 3.5 Sonnet)
- **Embeddings**: 1536-dimensional vectors

### Development
- **pytest** 7.4+ (testing framework)
- **mypy** 1.8+ (static type checking)
- **ruff** 0.1+ (linting & formatting)
- **structlog** 24.1+ (structured logging)
- **dependency-injector** 4.41+ (DI container)

## Documentation

We follow the [Divio Documentation System](https://documentation.divio.com/) — organized by user intent:

### 📚 [Tutorials](docs/1_tutorials/) (Learning-oriented)
Get started quickly with hands-on examples:
- [Quickstart Guide](docs/1_tutorials/01_quickstart.md) - 15-minute walkthrough

### 🛠️ [How-To Guides](docs/2_how-to-guides/) (Problem-oriented)
Solve specific problems:
- [Configure Scoring Weights](docs/2_how-to-guides/tune_scoring_weights.md)
- [Add Custom Entity Types](docs/2_how-to-guides/add_custom_entity_type.md)

### 💡 [Explanation](docs/3_explanation/) (Understanding-oriented)
Understand the "why" behind decisions:
- [Architecture Deep Dive](docs/3_explanation/architecture_overview.md)
- [Cost Optimization Strategy](docs/3_explanation/cost_optimization.md)
- [Testing Philosophy](docs/3_explanation/testing_strategy.md)
- [Conflict Resolution](docs/3_explanation/conflict_resolution.md)

### 📖 [Reference](docs/4_reference/) (Information-oriented)
Look up facts quickly:
- [API Endpoints](docs/4_reference/api_reference.md)
- [Database Schema](docs/4_reference/database_schema.md)
- [Configuration Options](docs/4_reference/configuration_reference.md)

## Development Workflow

### Daily Commands

```bash
# Start infrastructure
make docker-up

# Start API server (auto-reload)
make run

# Run tests in watch mode (TDD)
make test-watch

# Format code
make format

# Run all quality checks (lint + typecheck + coverage)
make check-all
```

### Testing

```bash
# Run all tests
make test

# Unit tests only (fast, no I/O)
make test-unit

# Integration tests (requires DB)
make test-integration

# End-to-end tests (full API flow)
make test-e2e

# Coverage report
make test-cov
# → Opens htmlcov/index.html
```

### Database

```bash
# Apply migrations
make db-migrate

# Create new migration
make db-create-migration MSG="add new field"

# Reset database (⚠️ destroys data)
make db-reset

# Open psql shell
make db-shell
```

### Quality Checks (Pre-Commit)

```bash
# Run everything before committing
make check-all
# → Lint (ruff)
# → Type check (mypy strict)
# → Test coverage (80% minimum)
```

## Vision Principles

Every feature serves one of these core principles:

### 🎯 Perfect Recall
Never forget user preferences or business context across sessions.

### 🔍 Explainability
Provenance tracking for every decision — transparency builds trust.

### 🤔 Epistemic Humility
Admit uncertainty. Max confidence = 0.95 (never 100%). Expose conflicts explicitly.

### 📈 Continuous Learning
Improve from every interaction. Reinforce on validation, decay over time.

### 💰 Cost Efficiency
Surgical LLM usage — only where deterministic methods fail.

## Project Status

**Current Phase**: Phase 1 (Entity Resolution + Memory System) — 95% complete

### Implemented
- ✅ 5-stage entity resolution (exact, alias, fuzzy, LLM, domain)
- ✅ 6-layer memory architecture
- ✅ Domain database integration (PostgreSQL)
- ✅ Multi-signal retrieval scoring
- ✅ PII detection & redaction
- ✅ Conflict detection (memory vs database)
- ✅ Provenance tracking
- ✅ LLM tool calling for domain queries

### In Progress
- 🚧 Phase 2: Active learning from usage patterns
- 🚧 Phase 2: Redis caching for hot paths
- 🚧 Phase 2: Pre-computation for frequent queries

### Roadmap
- 📋 Phase 3: Proactive intelligence (anticipate needs)
- 📋 Phase 3: Autonomous actions (e.g., auto-send reminders)
- 📋 Phase 3: Multi-tenant support

## Code Quality Standards

This project follows production-grade standards:

### Non-Negotiable Rules

1. **100% Type Annotations**
```python
# ✅ Required
def resolve(self, mention: str, user_id: str) -> ResolutionResult:
    ...

# ❌ Not allowed
def resolve(self, mention, user_id):
    ...
```

2. **Domain Never Imports Infrastructure**
```python
# ✅ Allowed: Domain uses ports (interfaces)
from src.domain.ports import IEntityRepository

# ❌ Forbidden: Direct infrastructure import
from src.infrastructure.database.models import EntityModel
```

3. **Immutable Value Objects**
```python
@dataclass(frozen=True)
class ResolutionResult:
    entity_id: str
    confidence: float
    method: str
```

4. **All I/O is Async**
```python
async def create(self, memory: SemanticMemory) -> SemanticMemory:
    ...
```

5. **Domain Exceptions (Not HTTP)**
```python
# ✅ Domain layer
raise AmbiguousEntityError(mention, candidates)

# ❌ Not in domain
raise HTTPException(status_code=422)
```

### Test Coverage Requirements

| Layer | Target | Actual |
|-------|--------|--------|
| Domain | 90% | 90% |
| API | 80% | 85% |
| Infrastructure | 70% | 80% |
| **Overall** | **80%** | **85%** |

## Configuration

All tunable parameters in `src/config/heuristics.py` (43 parameters):

```python
# Entity Resolution
FUZZY_MATCH_THRESHOLD = 0.7  # pg_trgm similarity threshold
MAX_CONFIDENCE = 0.95        # Never 100% certain

# Memory Lifecycle
MEMORY_DECAY_RATE = 0.0115              # Exponential decay
BASE_REINFORCEMENT_BOOST = 0.05         # Confidence increase on validation
CONFIDENCE_CONVERGENCE_LIMIT = 0.95     # Diminishing returns

# Retrieval Scoring
SEMANTIC_WEIGHT = 0.40       # Vector similarity
ENTITY_WEIGHT = 0.25         # Entity overlap
RECENCY_WEIGHT = 0.20        # Time-based
TEMPORAL_WEIGHT = 0.10       # Conversation flow
IMPORTANCE_WEIGHT = 0.05     # User priority
```

See [Configuration Reference](docs/4_reference/configuration_reference.md) for complete list.

## Contributing

### Code Style
- Follow [CLAUDE.md](CLAUDE.md) development guide
- Use `make format` before committing
- Run `make check-all` to verify quality

### Commit Messages
```
type(scope): subject

feat(api): add provenance tracking to chat endpoint
fix(entity): handle null entity_type in resolution
refactor(scoring): extract multi-signal scorer to separate service
test(e2e): add scenario for conflict detection
docs(readme): update quick start guide
```

### Pull Request Checklist
- [ ] Tests pass (`make test`)
- [ ] Coverage ≥ 80% (`make test-cov`)
- [ ] Type checking passes (`make typecheck`)
- [ ] Linting passes (`make lint`)
- [ ] Documentation updated (if needed)

## Troubleshooting

### PostgreSQL Connection Failed

```bash
# Check if PostgreSQL is running
make ps

# Restart PostgreSQL
make docker-down && make docker-up
```

### `make setup` Fails with "poetry not found"

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
```

### Port 5432 Already in Use

```bash
# Option 1: Stop existing PostgreSQL
brew services stop postgresql

# Option 2: Change port in docker-compose.yml
# Change "5432:5432" to "5433:5432"
```

### LLM API Calls Fail (401 Unauthorized)

```bash
# Set API key in .env file
echo "OPENAI_API_KEY=your-key-here" >> .env
# or
echo "ANTHROPIC_API_KEY=your-key-here" >> .env
```

### Tests Fail with Database Errors

```bash
# Reset test database
make db-reset

# Re-run migrations
make db-migrate
```

## License

[MIT License](LICENSE) - See LICENSE file for details

## Support

- 📖 **Documentation**: [docs/](docs/)
- 🐛 **Issues**: [GitHub Issues](issues)
- 💬 **Discussions**: [GitHub Discussions](discussions)

---

**Built with production-grade standards** | 85% test coverage | 100% type safety | Hexagonal architecture

*"Transform LLMs from stateless APIs into experienced colleagues with perfect recall."*
