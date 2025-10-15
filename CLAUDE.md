# CLAUDE.md

**Philosophy**: This project values **exceptional code quality**, **comprehensive solutions**, and **beautiful, elegant architecture** over speed and band-aid fixes.

> "Every line of code is a conversation with the future. Make it worth reading."

## What This Project Is About

This is not a typical CRUD application. This is a **philosophically grounded**, **vision-driven** system that transforms how LLM agents understand and remember business context.

**Current State**: Phase 1A + Phase 1B implementation ~95% complete. Core entity resolution and semantic extraction working. Now moving toward Phase 1C (intelligence) and Phase 1D (learning).

**Code Quality**: 11,864 lines of carefully structured Python. 100% type-annotated. Pure hexagonal architecture. 121/130 unit tests passing. Production-ready foundation.

---

## The First Principle: Understanding Before Execution

> **SEEK TO FULLY UNDERSTAND ANY ISSUE OR REQUEST BEFORE JUMPING INTO EXECUTION. ERR ON THE SIDE OF BEING THOROUGH.**

This is not negotiable. This is the foundation of everything else.

### Why This Matters

**Building the wrong thing quickly is worse than building the right thing slowly.**

A comprehensive solution to a misunderstood problem is worthless. A quick fix to a surface symptom creates technical debt. Understanding IS the work—execution is just the expression of that understanding.

### Value Good Solutions Over Speed

**CRITICAL**: Think deeply about all issues. **Value good solutions over lower token usage or time spent.**

Don't optimize for:
- ❌ Minimal tokens used
- ❌ Fastest response time
- ❌ Shortest conversation
- ❌ Fewest questions asked

**DO optimize for**:
- ✅ **Correct understanding** of the problem
- ✅ **Comprehensive solution** that addresses root cause
- ✅ **Well-reasoned approach** aligned with architecture
- ✅ **Thoughtful consideration** of edge cases and impacts

**Remember**:
- A 1000-token thorough investigation that leads to the right solution is **infinitely more valuable** than a 100-token quick fix that creates technical debt.
- Spending 30 minutes understanding the problem deeply is **better** than spending 5 minutes implementing the wrong solution.
- Asking 10 clarifying questions to get it right is **better** than making 10 assumptions and getting it wrong.

**This project values quality over speed. Always.**

### How to Apply This

**When given a task, bug report, or feature request:**

#### 1. **Investigate Thoroughly**

**DON'T**:
- ❌ Jump straight to coding
- ❌ Assume you understand from a brief description
- ❌ Implement based on the surface-level request
- ❌ Rush to "done" without exploring context

**DO**:
- ✅ Read all relevant design docs
- ✅ Check related code to understand current implementation
- ✅ Run tests to see current behavior
- ✅ Trace through the system to understand data flow
- ✅ Look for similar patterns elsewhere in the codebase
- ✅ Check git history to understand why it was built this way

**Example**:
```
User: "Fix the failing tests in memory_validation_service.py"

❌ BAD approach:
- Look at test, see it expects X, change code to return X
- Tests pass, mark done

✅ GOOD approach:
- Read failing tests to understand what behavior is expected
- Read DESIGN.md to understand what the design specifies
- Read the implementation to understand current logic
- Read LIFECYCLE_DESIGN.md to understand confidence decay formula
- Check if tests are testing the right thing or if implementation is wrong
- Understand WHY the discrepancy exists
- Determine root cause: formula mismatch? Test expectation wrong? Both?
- Fix the ROOT CAUSE with full understanding
- Add additional tests for edge cases discovered during investigation
```

#### 2. **Ask Clarifying Questions Liberally**

**It is ALWAYS better to ask than to assume.**

**Good questions to ask**:
- "I see the tests are failing—should I verify the expected behavior against DESIGN.md first?"
- "The design doc mentions X, but the current implementation does Y. Which is correct?"
- "This request asks for feature X. Looking at the architecture, should this go in domain layer or infrastructure?"
- "I see two possible approaches: A (simpler but less flexible) and B (more complex but scales better). Which aligns with the vision?"
- "Before implementing, I want to check: does this serve a vision principle? Which one?"
- "I found what looks like the issue, but I want to understand the context first. Can I investigate X, Y, and Z before proposing a fix?"

**Questions show thoughtfulness, not weakness.**

An experienced colleague asks questions to avoid wasting time on wrong solutions. You should too.

#### 3. **Propose Before Implementing**

When you've investigated and understood the issue:

**DON'T** immediately write code.

**DO** propose your understanding and approach:

```
"Based on my investigation:

**Understanding**:
- The tests expect confidence decay to use formula X (from DESIGN.md)
- Current implementation uses formula Y (seems to be older approach)
- Root cause: Implementation wasn't updated when design changed in v2.0

**Proposed Solution**:
1. Update calculate_effective_confidence() to match DESIGN.md spec
2. Update related tests to verify edge cases (days=0, days=90, never validated)
3. Add integration test to verify decay in full pipeline

**Questions**:
- Should I also check if other services use this formula correctly?
- Are there any migration concerns if we change how confidence is calculated?

Does this approach align with your expectations?"
```

This lets the human correct misunderstandings BEFORE you spend hours coding the wrong thing.

#### 4. **Err on the Side of Thoroughness**

When uncertain whether to investigate more or start coding:

**Default to: Investigate more.**

**Examples**:
- "Should I check how other services handle this pattern?" → **Yes, check.**
- "Should I read the entire DESIGN.md section or just the relevant part?" → **Read the entire section for context.**
- "Should I verify my understanding matches the tests?" → **Yes, verify.**
- "Should I look for edge cases beyond what's mentioned?" → **Yes, look.**
- "Should I trace through the full flow or just the immediate function?" → **Trace the full flow.**

**Why**: 10 minutes of investigation can save hours of rework.

### What Thoroughness Looks Like

**Scenario**: User reports "entity resolution is returning wrong results for fuzzy matches"

**❌ SURFACE-LEVEL approach** (2 minutes):
- Look at fuzzy match code
- See similarity threshold is 0.7
- Change to 0.8
- Mark done

**✅ THOROUGH approach** (20 minutes):
- Read the error report carefully - which specific entities failed?
- Check DESIGN.md - what's the intended fuzzy match behavior?
- Look at test cases - what scenarios are tested?
- Run tests to reproduce the issue
- Check database - what aliases exist for the failing entities?
- Check HEURISTICS_CALIBRATION.md - what's the rationale for 0.7 threshold?
- Trace through the 5-stage resolution algorithm - where is it failing?
- Check if similar entities resolve correctly - is this an outlier or systematic?
- Investigate: Is threshold wrong? Is pg_trgm similarity calculation wrong? Is the test data unusual?
- Understand the root cause
- Propose fix with rationale
- Implement with comprehensive tests

**Result**: The first approach might "fix" this specific case but miss the underlying issue. The second approach solves the actual problem.

### Balancing Thoroughness and Paralysis

**Thoroughness doesn't mean analysis paralysis.**

There's a balance:
- ✅ Investigate thoroughly enough to understand the problem
- ✅ Ask questions when uncertain
- ✅ Propose approach before implementing
- ❌ Don't spend hours investigating trivial changes
- ❌ Don't research endlessly without making progress

**Rule of thumb**:
- **Simple tasks** (fix typo, update config value): 2-5 minutes investigation
- **Medium tasks** (implement new function, fix bug): 10-30 minutes investigation
- **Complex tasks** (new feature, architectural change): 30-60 minutes investigation

**But always**: Understand before implementing.

### Red Flags That You Haven't Understood Enough

Stop and investigate more if you find yourself:
- ❌ "I'll just try this and see if it works"
- ❌ "I'm not sure why this is failing, but changing X seems to fix it"
- ❌ "The design doc says Y but I'll do X because it's easier"
- ❌ "I don't fully understand the architecture but I'll implement it here"
- ❌ "I'm not sure which approach is right, so I'll pick one"
- ❌ "This seems complicated, I'll simplify it" (without understanding WHY it's complex)

**These are all signs you need to investigate more, read more docs, or ask questions.**

### Success Indicators

You've understood enough when you can:
- ✅ Explain the problem in your own words
- ✅ Trace the issue back to root cause
- ✅ Justify your approach with reference to vision principles and design docs
- ✅ Identify edge cases that need handling
- ✅ Describe how your solution fits into the broader architecture
- ✅ Anticipate potential impacts on other parts of the system

**Only then should you start coding.**

---

## Ground Rules: How We Build Here

### 1. **Vision First, Always**

Every decision—every table, every field, every function—must answer:

> **Which vision principle does this serve?**

If you can't name the principle from `docs/vision/VISION.md`, stop and reconsider. This is not negotiable.

**The Vision**: Build a system that behaves like an **experienced colleague who has worked with this company for years**—someone who:
- Never forgets what matters (perfect recall of relevant context)
- Knows the business deeply (understands data, processes, relationships)
- Learns your way of working (adapts to preferences)
- Admits uncertainty (doesn't pretend to know when unsure)
- Explains their thinking (always traces reasoning to sources)
- Gets smarter over time (each conversation improves future ones)

### 2. **Quality Over Speed, Without Exception**

**We prioritize**:
- ✅ **Comprehensive solutions** that solve the problem completely
- ✅ **Beautiful, elegant architecture** that will age well
- ✅ **Type-safe, well-tested code** with explicit contracts
- ✅ **Thoughtful design** with documented rationale
- ✅ **Patterns that scale** to Phase 2 and beyond

**We reject**:
- ❌ **Quick fixes** that create technical debt
- ❌ **"Good enough for now"** implementations
- ❌ **Shortcuts** that violate architecture
- ❌ **Band-aid solutions** that don't address root causes
- ❌ **Rushing to "done"** without considering edge cases

**Example of our standards**:
```python
# ❌ UNACCEPTABLE
def resolve_entity(name):
    return db.query("SELECT * FROM entities WHERE name LIKE ?", name)[0]

# ✅ ACCEPTABLE - Type-safe, async, comprehensive docstring, error handling
async def resolve_entity(
    mention: str, user_id: str, context: ResolutionContext
) -> ResolutionResult:
    """5-stage hybrid resolution with confidence tracking."""
    # Exact → Alias → Fuzzy → LLM coreference → Domain DB
    ...
```

### 3. **Think Deeply Before Coding**

When given a task:

1. **Read the design docs first** - Don't guess. The architecture is documented.
2. **Understand the vision principle** - Why does this exist?
3. **Consider edge cases** - What could go wrong?
4. **Think about the whole system** - How does this fit?
5. **Ask questions if unclear** - Better to ask than build wrong.

**Before writing any code**, answer:
- Which vision principle am I serving?
- What are the edge cases?
- How will this be tested?
- Does this fit the established patterns?
- Is there a simpler way that doesn't sacrifice quality?

### 4. **Architecture is Sacred**

This system uses **pure hexagonal architecture** (ports & adapters). This is non-negotiable.

```
API Layer (FastAPI)
    ↓ depends on
Domain Layer (Pure Python - NO infrastructure imports)
    ↓ depends on (via interfaces)
Infrastructure Layer (DB, LLM, external systems)
```

**Critical rules**:
- ✅ Domain layer NEVER imports from infrastructure
- ✅ All I/O goes through repository ports (ABC interfaces)
- ✅ Domain exceptions are business concepts, not HTTP errors
- ✅ Value objects are immutable (`@dataclass(frozen=True)`)
- ✅ All public methods are 100% type-annotated

**If you violate these rules, the code will be rejected.**

### 5. **Tests Are Not Optional**

Test pyramid: **70% unit | 20% integration | 10% E2E**

**Before marking any task complete**:
- [ ] Unit tests for domain logic (mocked I/O)
- [ ] Integration tests for repository operations (real DB)
- [ ] Edge cases covered (null, empty, invalid inputs)
- [ ] Error paths tested (what happens when things fail?)
- [ ] Coverage meets minimum: 90% domain, 80% API, 70% infrastructure

**Test quality standards**:
```python
# ❌ UNACCEPTABLE - Vague
def test_entity_resolution():
    result = resolve_entity("Acme")
    assert result is not None

# ✅ ACCEPTABLE - Specific, Given-When-Then, Arrange-Act-Assert
@pytest.mark.unit
@pytest.mark.asyncio
async def test_exact_match_returns_confidence_1_0_with_exact_method():
    """Given: Entity exists. When: Exact match. Then: confidence=1.0, method='exact'"""
    # Arrange
    mock_repo = MockEntityRepository()
    mock_repo.add_entity(entity_id="customer:acme_123", canonical_name="Acme Corporation")
    resolver = EntityResolver(entity_repo=mock_repo)

    # Act
    result = await resolver.resolve("Acme Corporation", "user_1", ResolutionContext())

    # Assert
    assert result.entity_id == "customer:acme_123"
    assert result.confidence == 1.0
    assert result.method == "exact_match"
```

---

## The Core Architecture

### Philosophical Foundation: Dual Truth

The system maintains **two forms of truth in dynamic equilibrium**:

**Correspondence Truth (Database)**: Objective, authoritative facts
- `invoice_id: INV-1009, amount: $1200, status: open`
- Source of truth for "what IS"

**Contextual Truth (Memory)**: Interpretive understanding
- "Customer is sensitive about reminders"
- "They typically pay 2-3 days late"
- Source of meaning for "what it MEANS"

**Neither alone is sufficient.** Database without memory is precise but hollow. Memory without database is meaningful but ungrounded.

### The 6-Layer Memory Architecture

```
Layer 6: SUMMARIES (memory_summaries)
         ↑ Consolidation: "Gai Media profile (3 sessions)..."
Layer 5: PROCEDURAL (procedural_memories)
         ↑ Pattern extraction: "When delivery mentioned, check invoices"
Layer 4: SEMANTIC (semantic_memories)
         ↑ Fact extraction: "Gai Media: delivery_preference = Friday"
Layer 3: EPISODIC (episodic_memories)
         ↑ Event interpretation: "User asked about delivery timing"
Layer 2: ENTITY RESOLUTION (canonical_entities, entity_aliases)
         ↑ Reference grounding: "Gai" → customer:gai_media_123
Layer 1: RAW EVENTS (chat_events)
         ↑ Immutable audit trail: Every message stored
Layer 0: DOMAIN DATABASE (external)
         Authoritative business data
```

**Information flows both ways**:
- **Abstraction (↑)**: Events → Facts → Patterns → Summaries
- **Grounding (↓)**: Queries fetch DB facts, enrich with memory layers

### Database Schema: 10 Essential Tables

Every table serves explicit vision principles. **No table is "nice to have."**

| Layer | Table | Vision Principle |
|-------|-------|------------------|
| 1 | `chat_events` | Provenance, explainability |
| 2 | `canonical_entities` | Problem of reference |
| 2 | `entity_aliases` | Identity across time, learning |
| 3 | `episodic_memories` | Events with meaning |
| 4 | `semantic_memories` | Contextual truth, epistemic humility |
| 5 | `procedural_memories` | Learning from patterns |
| 6 | `memory_summaries` | Graceful forgetting |
| Support | `domain_ontology` | Ontology-awareness |
| Support | `memory_conflicts` | Epistemic humility |
| Support | `system_config` | Tunable parameters |

**See** `src/infrastructure/database/models.py` for complete schema (263 lines, all models defined).

---

## Key Design Decisions (and Why)

### Decision 1: Surgical LLM Integration

**Principle**: Use LLMs where they add clear value, deterministic systems where they excel.

| Component | Approach | Why |
|-----------|----------|-----|
| Entity Resolution | 95% deterministic, 5% LLM | pg_trgm fuzzy matching handles most cases. LLM only for pronouns. |
| Semantic Extraction | 100% LLM | Parsing "Acme prefers Friday deliveries and NET30" into triples genuinely needs LLM. |
| Retrieval Scoring | 0% LLM | Must score 100+ candidates in <100ms. Deterministic formula works. |
| Consolidation | 100% LLM | Reading 20+ memories and synthesizing summary is exactly what LLMs do best. |

**Cost**: ~$0.002 per conversational turn (vs $0.03 for pure LLM approach)

**Accuracy**: 85-90% (vs 90%+ for pure LLM, 60-70% for pure deterministic)

### Decision 2: Passive Computation (No Background Jobs)

**Preferred pattern**:
```python
def calculate_effective_confidence(memory: SemanticMemory) -> float:
    """Compute confidence with decay applied - on demand, not pre-computed."""
    days_since_validation = (now() - memory.last_validated_at).days
    decay_rate = get_config('decay.default_rate_per_day')

    return memory.confidence * exp(-days_since_validation * decay_rate)
```

**Why**:
- Simpler: No background jobs, no staleness issues
- Accurate: Always reflects current state
- Phase 1 appropriate: Pre-computation is Phase 2 optimization

**Exception**: Embeddings are pre-computed (expensive, used frequently)

### Decision 3: JSONB for Context-Specific Data

**Use JSONB when**:
- Variable structure per context
- Rarely queried independently
- Explainability metadata

**Examples**:
- `semantic_memories.confidence_factors` - Evidence varies per memory
- `episodic_memories.entities` - Coreference chains are context-specific
- `entity_aliases.metadata` - Disambiguation context varies

**Use separate tables when**:
- Frequently queried independently
- Foreign key relationships needed
- Fixed schema with lifecycle

**Examples**:
- `canonical_entities` - Queried for resolution
- `semantic_memories` - Has status lifecycle, referenced by conflicts

### Decision 4: Epistemic Humility is Built-In

**The system NEVER claims 100% certainty** (MAX_CONFIDENCE = 0.95).

```python
@dataclass
class SemanticMemory:
    confidence: float  # Range: 0.0 to 0.95

    def reinforce(self, boost: float = 0.05) -> None:
        """Increase confidence from validation (capped at 0.95)."""
        self.confidence = min(0.95, self.confidence + boost)
```

**When conflicts are detected**:
1. Log to `memory_conflicts` table (never silently ignore)
2. Resolve using strategy: trust_db | trust_recent | ask_user
3. Return both values with confidences to user if ambiguous

**This is a philosophical stance**: The system knows what it doesn't know.

---

## Current Implementation Status

### ✅ Phase 1A Complete: Entity Resolution
- 5-stage hybrid resolution (exact/alias/fuzzy/LLM/domain-DB)
- PostgreSQL with pg_trgm, alias learning, lazy entity creation
- **Key**: `src/domain/services/entity_resolution_service.py`

### ✅ Phase 1B Complete: Semantic Extraction
- LLM triple extraction, conflict detection (memory vs memory, memory vs DB)
- Passive decay calculation, reinforcement with diminishing returns
- **Key**: `semantic_extraction_service.py`, `conflict_detection_service.py`, `memory_validation_service.py`

### ⚠️ Current Issues
- **9/130 tests failing**: 8 in `test_memory_validation_service.py` (decay formula mismatch), 1 in `test_semantic_extraction_service.py`
- **API integration incomplete** (Phase 1B services not wired to routes/DI container)

### 🎯 Next: Phase 1C (Intelligence)
Multi-signal retrieval, domain database integration, enhanced conflict detection, ontology traversal

### 🔮 Future: Phase 1D (Learning)
Procedural memory extraction, consolidation, complete lifecycle, full API exposure

---

## Code Conventions (Non-Negotiable)

### 1. Type Hints: 100% Coverage

```python
# ✅ CORRECT
async def resolve_entity(
    mention: str,
    user_id: str,
    context: ResolutionContext
) -> ResolutionResult:
    ...

# ❌ REJECTED - Missing types
async def resolve_entity(mention, user_id, context):
    ...
```

**Enforcement**: `make typecheck` runs mypy in strict mode. Must pass.

### 2. Immutable Value Objects

```python
# ✅ CORRECT
@dataclass(frozen=True)
class Confidence:
    value: float
    source: str
    factors: dict[str, float]

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.value}")

# ❌ REJECTED - Mutable
@dataclass
class Confidence:
    value: float
    source: str
```

### 3. Domain Exceptions (Not HTTP)

```python
# ✅ CORRECT - Domain exception with context
class AmbiguousEntityError(DomainException):
    """Multiple entities match, user clarification required."""
    def __init__(self, mention: str, candidates: List[Entity]):
        self.mention = mention
        self.candidates = candidates
        super().__init__(f"Ambiguous entity: '{mention}'")

# ❌ REJECTED - HTTP exception in domain
from fastapi import HTTPException
raise HTTPException(status_code=422, detail="Ambiguous entity")
```

**API layer converts to HTTP** - see `src/api/errors.py` for exception handlers.

### 4. Repository Pattern (Ports & Adapters)

**Pattern**: Port (ABC interface) in `domain/ports/`, adapter (implementation) in `infrastructure/database/repositories/`

```python
# ✅ Port in domain
class EntityRepositoryPort(ABC):
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[CanonicalEntity]:
        pass

# ✅ Adapter in infrastructure
class PostgresEntityRepository(EntityRepositoryPort):
    async def get_by_id(self, entity_id: str) -> Optional[CanonicalEntity]:
        # Query DB, convert model to domain entity
        return self._to_domain(model) if model else None
```

### 5. Never Hardcode Heuristics

```python
# ✅ CORRECT
from src.config.heuristics import get_config

decay_rate = get_config('decay.default_rate_per_day')
confidence = memory.confidence * exp(-days * decay_rate)

# ❌ REJECTED
confidence = memory.confidence * exp(-days * 0.01)  # Magic number!
```

**All heuristic values** live in `src/config/heuristics.py` (203 lines, 43+ parameters).

### 6. Structured Logging

```python
# ✅ CORRECT
import structlog

logger = structlog.get_logger()

logger.info(
    "entity_resolved",
    method="fuzzy",
    entity_id=result.entity_id,
    confidence=result.confidence,
    user_id=user_id,
)

# ❌ REJECTED
print(f"Resolved {result.entity_id} with confidence {result.confidence}")
```

### 7. Async Everything (I/O)

```python
# ✅ CORRECT
async def resolve_entity(...) -> ResolutionResult:
    exact = await self.entity_repo.get_by_canonical_name(mention)
    ...

# ❌ REJECTED - Blocking I/O
def resolve_entity(...) -> ResolutionResult:
    exact = self.entity_repo.get_by_canonical_name(mention)  # Blocks event loop!
    ...
```

---

## Essential Development Commands

### Daily Workflow

```bash
# Start database
make docker-up

# Run dev server with auto-reload
make run

# Run tests on file changes (TDD workflow)
make test-watch
```

### Before Committing

```bash
# Run ALL quality checks (lint + typecheck + test coverage)
make check-all

# If any fail, fix them. Don't commit broken code.
```

### Testing

```bash
# All tests
make test

# Just unit tests (fast, no DB)
make test-unit

# Just integration tests (requires DB)
make test-integration

# With coverage report (HTML in htmlcov/)
make test-cov

# Single test file
poetry run pytest tests/unit/domain/test_entity_resolver.py

# Single test function
poetry run pytest tests/unit/domain/test_entity_resolver.py::test_exact_match

# All tests matching pattern
poetry run pytest -k "entity"
```

### Database

```bash
# Apply migrations
make db-migrate

# Create new migration (autogenerate from models)
make db-create-migration MSG="add procedural memories table"

# Rollback last migration
make db-rollback

# Reset database (⚠️ destroys data)
make db-reset

# Open psql shell
make db-shell
```

### Code Quality

```bash
# Check style
make lint

# Auto-fix style issues
make lint-fix

# Format code (ruff)
make format

# Type checking (mypy strict)
make typecheck

# Security checks
make security
```

---

## The Three Questions Framework

**Before adding ANY complexity** (table, field, function, dependency), answer:

### 1. Which vision principle does this serve?

From `docs/vision/VISION.md`:
- Perfect recall of relevant context
- Deep business understanding (ontology-awareness)
- Adaptive learning
- Epistemic humility (knows what it doesn't know)
- Explainable reasoning (provenance)
- Continuous improvement

**If you can't name the principle, STOP. Reconsider.**

### 2. Does this contribute enough to justify its cost?

**Cost** = Schema complexity + Query complexity + Maintenance burden

**Contribution** = How much does this advance the vision?

**Example**:
- Procedural memories table: High cost, but essential (in vision Layer 5) → **Keep**
- Access count field: Low cost, but deferred (Phase 3 learning) → **Defer**

### 3. Is this the right phase for this complexity?

- **Phase 1** (now): Essential for core functionality
- **Phase 2** (after deployment): Enhancements that need real usage data
- **Phase 3** (after calibration): Learning features that need patterns

**Example**:
- Confidence decay: Phase 1 (essential for epistemic humility)
- Learned retrieval weights: Phase 2 (need usage data to tune)
- Meta-learning decay rates: Phase 3 (need large dataset of corrections)

---

## Common Pitfalls (AVOID THESE)

### ❌ 1. Importing Infrastructure in Domain

```python
# WRONG - Domain imports infrastructure
from src.infrastructure.database.models import EntityModel

class EntityResolver:
    def resolve(self, mention: str) -> Entity:
        result = session.query(EntityModel).filter(...).first()  # ❌
```

**Why wrong**: Violates hexagonal architecture. Domain should be pure Python.

### ❌ 2. Hardcoded Heuristics

```python
# WRONG
if confidence < 0.7:  # ❌ Magic number
    needs_validation = True
```

**Why wrong**: Heuristics need Phase 2 calibration. Must be configurable.

### ❌ 3. Skipping Type Hints

```python
# WRONG
def resolve_entity(mention, context):  # ❌ No types
    ...
```

**Why wrong**: Violates code quality standards. Will fail mypy strict mode.

### ❌ 4. Mutable Domain Objects

```python
# WRONG
@dataclass
class Confidence:  # ❌ Not frozen
    value: float
```

**Why wrong**: Value objects should be immutable. Prevents accidental mutation.

### ❌ 5. Quick Fixes Without Tests

```python
# WRONG - No tests
def resolve_entity(...):
    try:
        return db.query(...)[0]  # ❌ What if empty? No test coverage.
    except:
        return None  # ❌ Swallowing all exceptions
```

**Why wrong**: No edge case handling, no tests, silent failures.

### ❌ 6. Adding Features Without Vision Justification

```python
# WRONG
class SemanticMemory:
    accessed_count: int  # ❌ Which vision principle does this serve?
```

**Why wrong**: Useful for Phase 3, not essential now. Adds premature complexity.

### ❌ 7. Silently Ignoring Conflicts

```python
# WRONG
if existing_memory.value != new_value:
    return existing_memory  # ❌ Silent preference, no logging
```

**Why wrong**: Epistemic humility requires explicit conflict tracking.

### ❌ 8. Pre-Computing When Passive Works

```python
# WRONG - Background job updating confidence
@celery.task
def update_confidence_with_decay():
    for memory in all_memories:
        memory.confidence *= decay_factor  # ❌ Unnecessary complexity
        db.save(memory)
```

**Why wrong**: Phase 1 uses passive computation. Pre-computation is Phase 2.

### ❌ 9. Using LLM When Deterministic Works

```python
# WRONG
async def fuzzy_match(mention: str, entities: List[Entity]) -> Entity:
    # Use LLM to find fuzzy match
    result = await llm.complete(f"Which entity matches '{mention}'?")  # ❌
```

**Why wrong**: pg_trgm similarity is faster, cheaper, more reliable for fuzzy matching.

### ❌ 10. Testing Infrastructure in Unit Tests

```python
# WRONG
@pytest.mark.unit
async def test_entity_repository():
    repo = PostgresEntityRepository(real_db_session)  # ❌ Real DB in unit test
    entity = await repo.get_by_id("customer:123")
    assert entity is not None
```

**Why wrong**: Unit tests should be fast (no I/O). Use mocks. Real DB = integration test.

---

## Critical Reference Documents

**Always consult these before implementing**:

### Vision & Philosophy
- `docs/vision/VISION.md` (720 lines) - **Start here**. Philosophical foundation.
- `docs/vision/DESIGN_PHILOSOPHY.md` (323 lines) - Three Questions Framework, decision trees.

### Complete Design
- `docs/design/DESIGN.md` (1,509 lines) - **Complete system specification**. All algorithms, all tables, all justifications.

### Implementation Guides
- `docs/quality/PHASE1_ROADMAP.md` - 8-week implementation plan with detailed tasks.
- `docs/reference/HEURISTICS_CALIBRATION.md` - All 43 tunable parameters (in `src/config/heuristics.py`).
- `docs/design/API_DESIGN.md` - Request/response models for all endpoints.
- `docs/design/LIFECYCLE_DESIGN.md` - Memory state transitions, decay, reinforcement.
- `docs/design/RETRIEVAL_DESIGN.md` - Multi-signal scoring formula.

### Architecture
- `docs/ARCHITECTURE.md` - Hexagonal architecture, DDD patterns.
- `docs/DEVELOPMENT_GUIDE.md` - Setup, workflows, troubleshooting.

**If something isn't in the docs, ask before proceeding.**

---

## Working With Claude: Guidelines

### When Starting a New Task

1. **Read the relevant design docs** (don't guess at architecture)
2. **Identify the vision principle** you're serving
3. **Check current implementation status** (what's done, what's next)
4. **Consider edge cases and error paths**
5. **Plan the tests first** (TDD approach)
6. **Ask clarifying questions** if design is ambiguous

### When You're Uncertain

**ASK instead of assuming**. Better questions to ask:

- "Which vision principle does this serve?"
- "Should this be Phase 1, 2, or 3?"
- "Is there an established pattern I should follow?"
- "What are the edge cases I should handle?"
- "How should this be tested?"

**Don't say**: "I'll implement it this way and we can change it later."

### When Tests Fail

**Don't just make tests pass. Understand WHY they're failing.**

1. Read the test carefully - what's it asserting?
2. Understand the expected behavior from design docs
3. Check if implementation or test is wrong
4. Fix the root cause, not just the symptom
5. Add more tests for edge cases you discovered

### When Code Review Feedback Comes

**See feedback as improving the system, not criticism.**

- If architectural violation: Fix immediately, understand why it matters
- If missing edge case: Add tests, thank reviewer
- If unclear design: Ask for design doc clarification
- If disagreement: Discuss with reference to vision principles

---

## Advanced Principles: Mastering the Philosophy

These principles go beyond "how to code" and into "how to think" about building this system.

### 1. Root Cause Thinking (The 5 Whys)

**Never fix symptoms. Always fix root causes.**

When encountering an issue, ask "why" until you reach the fundamental cause:

**Example**:
```
Issue: Tests failing in memory_validation_service.py

Why? → Expected confidence 0.742, got 0.735
Why? → Decay calculation differs from test expectation
Why? → Formula uses different decay rate
Why? → Implementation uses 0.01, test expects 0.0115 (from DESIGN.md)
Why? → Implementation wasn't updated when design changed in v2.0

ROOT CAUSE: Design-implementation drift from v2.0 revision
FIX: Update implementation to match DESIGN.md, add regression test
```

**Surface fix** (wrong): Change expected value in test to 0.735
**Root cause fix** (right): Update formula to match design specification

**Apply this to**:
- Bug fixes (don't patch symptoms, eliminate causes)
- Test failures (understand WHY tests fail, not just how to make them pass)
- Design questions (understand why the design exists before changing it)
- Performance issues (profile and understand bottlenecks, don't blindly optimize)

### 2. Systems Thinking (The Ripple Effect)

**Every change affects multiple parts of the system.**

Before implementing anything, trace the ripples:

**6 Dimensions of Impact**:

1. **Data Flow**: Where does this data come from? Where does it go?
2. **Error Propagation**: What happens when this fails? Who handles the error?
3. **Performance**: Does this add latency? Database queries? LLM calls?
4. **State Management**: Does this change state? How does state persist?
5. **Dependencies**: What depends on this? What does this depend on?
6. **Testing**: How do I test this? What edge cases exist?

**Example**:
```
Task: Add LLM coreference resolution to entity resolver

Systems Thinking Analysis:
1. Data Flow: Needs conversation history → Changes ResolutionContext
2. Error Propagation: LLM can fail → Need fallback strategy, timeout handling
3. Performance: LLM adds 200ms → Make this the LAST stage (fast path first)
4. State Management: LLM results should be learned → Save as aliases
5. Dependencies: Needs LLM service port → Add to EntityResolver constructor
6. Testing: LLM is external → Mock LLM service in unit tests, integration test with real LLM

Result: Comprehensive implementation that fits architecture
```

**Never implement in isolation. Always consider the system.**

### 3. Learn from the Codebase

**The existing code is the best documentation of standards.**

Before writing new code, study similar existing code:

**Pattern Recognition**:
- Writing a new service? Study `EntityResolutionService` and `SemanticExtractionService`
- Writing a new repository? Study `EntityRepository` and `SemanticMemoryRepository`
- Writing a new domain entity? Study `CanonicalEntity` and `SemanticMemory`
- Writing a new test? Study existing test structure in the same directory

**What to observe**:
- Naming conventions (e.g., methods are `create_memory`, not `createMemory`)
- Error handling patterns (domain exceptions, not HTTP exceptions)
- Logging structure (structured logs with context)
- Type annotations (comprehensive, with Union, Optional where appropriate)
- Docstring style (concise summary, then details)
- Test structure (Arrange-Act-Assert, descriptive test names)

**Anti-pattern**: "I'll write this my way and refactor later."
**Good pattern**: "Let me see how EntityResolver does this, then follow that pattern."

### 4. Code as Communication

**You're not writing code for the computer. You're writing it for humans (including future you).**

**Write self-documenting code**:

```python
# ❌ BAD - Needs comments to understand
def calculate_score(m, q):
    # Compute cosine similarity
    s = 1 - cosine(m.e, q.e)
    # Apply entity boost
    e = jaccard(m.ents, q.ents)
    # Decay factor
    d = exp(-age * 0.01)
    return 0.4 * s + 0.25 * e + 0.2 * d

# ✅ GOOD - Self-documenting with good names
def calculate_relevance_score(
    memory: Memory,
    query: Query,
    weights: ScoringWeights
) -> float:
    """
    Multi-signal relevance scoring.

    Combines semantic similarity, entity overlap, and recency decay
    using weighted formula from RETRIEVAL_DESIGN.md.
    """
    semantic_score = 1 - cosine_distance(memory.embedding, query.embedding)
    entity_score = jaccard_similarity(memory.entities, query.entities)
    age_days = (now() - memory.created_at).days
    recency_score = exp(-age_days * get_config('decay.default_rate_per_day'))

    relevance = (
        weights.semantic * semantic_score +
        weights.entity * entity_score +
        weights.recency * recency_score
    )

    return relevance
```

**When to comment**:
- **DON'T** comment WHAT the code does (code should show this)
- **DO** comment WHY you made a design choice
- **DO** comment complex algorithms with references
- **DO** comment rationale for non-obvious values

**Example of good comments**:
```python
# Use exponential decay rather than linear because confidence should
# drop quickly initially but level off (per LIFECYCLE_DESIGN.md)
decay_factor = exp(-age_days * decay_rate)

# Cap at 0.95 (not 1.0) to maintain epistemic humility - system
# never claims 100% certainty (vision principle)
self.confidence = min(0.95, self.confidence + boost)
```

### 5. When to Push Back (Respectfully)

**Not all requests should be implemented as stated.**

Sometimes the right answer is: "I understand what you're asking, but here's why we should do X instead."

**Legitimate reasons to push back**:

1. **Violates core architecture**
   - "This would require domain layer to import infrastructure, which breaks hexagonal architecture. Instead, let's..."

2. **Doesn't serve vision principles**
   - "I can add this field, but I can't identify which vision principle it serves. Can we defer this to Phase 2 when we have usage data?"

3. **Creates technical debt**
   - "A quick fix here would work short-term but make Phase 1C harder. Let me propose a comprehensive solution that sets us up correctly."

4. **Wrong phase for complexity**
   - "This feature requires learning from usage patterns. We don't have data yet. This is a Phase 3 feature. For Phase 1, let's do X instead."

**How to push back effectively**:

```
Template:
"I understand you want [THEIR REQUEST].

However, [CONCERN WITH REFERENCE TO DOCS/PRINCIPLES].

Instead, I propose [ALTERNATIVE APPROACH] because [RATIONALE TIED TO VISION].

This gives us [BENEFITS] while avoiding [COSTS].

Does this align with your intent?"
```

**Example**:
```
"I understand you want to add accessed_count to track memory usage.

However, looking at DESIGN_PHILOSOPHY.md, this seems like a Phase 3
learning feature (requires usage patterns we don't have yet), and
PHASE1_ROADMAP.md doesn't include it as essential.

Instead, I propose we add this to the Phase 3 backlog and focus on
completing Phase 1C (conflict detection, multi-signal retrieval)
which are essential for the core vision.

This keeps Phase 1 scope manageable while ensuring we build learning
features when we have data to learn from.

Does this align with your intent?"
```

### 6. Incremental Perfection (Not Iterative Roughing-In)

**Complete each piece fully before moving to the next.**

**DON'T**: Rough-in approach
```
❌ "I'll implement entity resolution roughly, then semantic extraction
   roughly, then come back and polish both later."

Result: Two half-finished features, unclear what's production-ready
```

**DO**: Incremental perfection
```
✅ "I'll implement entity resolution COMPLETELY (including tests,
   edge cases, error handling, docs), verify it works, THEN move
   to semantic extraction."

Result: One production-ready feature, clear progress
```

**What "complete" means**:
- ✅ Implementation matches design specification
- ✅ All edge cases handled
- ✅ Comprehensive tests (unit + integration)
- ✅ Error handling with appropriate exceptions
- ✅ Logging for observability
- ✅ Type annotations complete
- ✅ Docstrings written
- ✅ Passes all quality checks (lint, typecheck, coverage)

**Progress should be**: 100% → 100% → 100%

**Not**: 60% → 60% → 60% → eventually 100%

### 7. Pattern Recognition and Consistency

**Consistency compounds clarity.**

The codebase has established patterns. Learn them, follow them, perpetuate them.

**Core Patterns**:

1. **Repository Pattern**
   - Port (ABC) in `domain/ports/`
   - Adapter (implementation) in `infrastructure/database/repositories/`
   - Async methods with descriptive names
   - Return domain entities, not DB models

2. **Value Object Pattern**
   - Immutable (`@dataclass(frozen=True)`)
   - Validation in `__post_init__`
   - Type annotations complete
   - Semantic names

3. **Service Pattern**
   - Coordinates between repositories
   - Contains business logic
   - Takes repository ports in constructor (dependency injection)
   - Returns domain entities or raises domain exceptions

4. **Exception Pattern**
   - Domain exceptions inherit from `DomainException`
   - Carry context (not just message)
   - API layer converts to HTTP responses
   - Never raise HTTP exceptions from domain

5. **Logging Pattern**
   - Structured logging with `structlog`
   - Use event names (e.g., "entity_resolved", not "Resolved entity")
   - Include context (user_id, entity_id, confidence, etc.)
   - Log at appropriate levels (info for success, warning for issues)

6. **Configuration Pattern**
   - All heuristics in `src/config/heuristics.py`
   - Access via `get_config('path.to.value')`
   - Never hardcode magic numbers
   - Document rationale in `docs/reference/HEURISTICS_CALIBRATION.md`

**When adding new code, ask**: "Is there already a pattern for this?"

### 8. Documentation as Contract

**Design docs are not suggestions. They're specifications.**

When implementation and docs disagree:

1. **First**: Understand which is correct
   - Check git history - when was each changed?
   - Check conversation history - what was the intention?
   - Check related code - what's consistent?

2. **Then**: Fix the discrepancy
   - If docs are right: Update implementation
   - If implementation is right: Update docs
   - If both are wrong: Fix both

3. **Never**: Ignore the discrepancy
   - ❌ "Docs say X but code does Y, I'll leave it"
   - ❌ "I'll implement Z which differs from both"

**Docs are the source of truth for**:
- Vision principles (`VISION.md`)
- Algorithm specifications (`DESIGN.md`)
- Architecture patterns (`ARCHITECTURE.md`)
- Decision rationale (`DESIGN_PHILOSOPHY.md`)
- Heuristic values (`HEURISTICS_CALIBRATION.md`)

**Code is the source of truth for**:
- Current implementation state
- What actually works
- Performance characteristics
- Edge cases discovered through testing

**When they align: System is healthy.**
**When they diverge: Priority 1 issue.**

### 9. Pride in Craft

**You're building a system that transforms memory into intelligence.**

This is not a throwaway prototype. This is production-grade infrastructure for the foundation of agentic intelligence.

**What this means**:

- Write code you'd be proud to show in 5 years
- Leave the codebase better than you found it
- Think: "Is this production-ready?" not "Is this good enough for now?"
- Take ownership: If you see something wrong, fix it (or at least flag it)
- Sweat the details: Naming, formatting, docstrings, test quality—all matter

**Every line of code is a reflection of your standards.**

Make them high standards.

**Remember the metaphor**: You're building an experienced colleague, not a chatbot. Build something worthy of being called a colleague.

---

## Performance Targets (Phase 1)

| Operation | P95 Latency | Why This Matters |
|-----------|-------------|------------------|
| Entity resolution (fast path) | <50ms | 95% of resolutions use deterministic path |
| Entity resolution (LLM path) | <300ms | 5% of resolutions need coreference |
| Semantic search (pgvector) | <50ms | Retrieval must be near-instant |
| Multi-signal scoring | <100ms | Score 100+ candidates deterministically |
| Full chat endpoint | <800ms | End-to-end including LLM generation |

**If you add code that degrades these targets, optimize or reconsider.**

---

## Environment Setup

Required environment variables (see `.env.example`):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://memoryuser:memorypass@localhost:5432/memorydb

# OpenAI (embeddings + extraction)
OPENAI_API_KEY=sk-...your-key...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # 1536 dimensions
OPENAI_LLM_MODEL=gpt-4o  # Quality matters for extraction

# API
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # json for production, text for development
```

---

## Commit Message Convention

Format: `<type>(<scope>): <subject>`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructure (no behavior change)
- `test`: Add/update tests
- `docs`: Documentation only
- `chore`: Build, dependencies, tooling

Examples:
```
feat(entity-resolution): implement Stage 4 LLM coreference resolution
fix(semantic-memory): correct passive decay calculation per DESIGN.md spec
refactor(repositories): extract common query patterns to base class
test(conflict-detection): add tests for memory vs DB conflicts
docs(architecture): update DESIGN.md with surgical LLM justification
```
