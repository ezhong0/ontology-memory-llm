# CLAUDE.md

> **Philosophy**: Understand deeply before acting. Build comprehensive solutions, not quick fixes. Every line matters.

---

## Core Principles

### 1. Understanding First
**INVESTIGATE THOROUGHLY BEFORE IMPLEMENTING.**
- Read design docs → check code → run tests → trace flow
- Ask questions when uncertain (better to ask than assume wrong)
- Propose approach before coding (let human correct early)
- Fix root causes, not symptoms

**Value thorough solutions over speed.** A 1000-token investigation beats a 100-token band-aid.

### 2. Vision-Driven
Every decision answers: **Which vision principle does this serve?**

The Vision: System behaves like an **experienced colleague** (perfect recall, deep business knowledge, learns preferences, admits uncertainty, explains reasoning, improves over time).

### 3. Three Questions Framework
Before adding ANY complexity:
1. Which vision principle does this serve?
2. Does contribution justify cost (schema/maintenance burden)?
3. Right phase? (Phase 1: essential now | Phase 2: needs usage data | Phase 3: needs patterns)

---

## Architecture (Non-Negotiable)

**Hexagonal (Ports & Adapters)**
```
API → Domain (pure Python) → Infrastructure (DB/LLM)
```

**Rules:**
- Domain NEVER imports infrastructure
- All I/O through repository ports (ABC interfaces)
- Domain exceptions (not HTTP)
- Value objects immutable (`@dataclass(frozen=True)`)
- 100% type annotations
- Async all I/O

**Pattern:** Port (ABC) in `domain/ports/`, adapter in `infrastructure/*/repositories/`

---

## Code Standards

1. **Type Everything**: `def func(x: str, y: int) -> Result:` not `def func(x, y):`
2. **Immutable Values**: `@dataclass(frozen=True)` with `__post_init__` validation
3. **Domain Exceptions**: `AmbiguousEntityError(mention, candidates)` not `HTTPException`
4. **No Magic Numbers**: `get_config('decay.rate')` not `0.01`
5. **Test Coverage**: 90% domain, 80% API, 70% infra (70% unit, 20% integration, 10% E2E)
6. **Structured Logs**: `logger.info("entity_resolved", entity_id=x, confidence=y)`
7. **Async I/O**: All DB/API calls async

---

## Essential References

- `docs/vision/VISION.md` - Philosophy (START HERE)
- `docs/design/DESIGN.md` - Complete spec (1,509 lines)
- `docs/ARCHITECTURE.md` - Patterns
- `src/config/heuristics.py` - All tunable parameters

---

## Commands

```bash
# Daily
make run                # Dev server
make test-watch         # TDD mode

# Quality
make check-all          # Lint + typecheck + coverage (run before commit)

# DB
make db-migrate         # Apply
make db-reset           # ⚠️ Destroy all
```

---

## Key Decisions

1. **Surgical LLM**: 95% deterministic (pg_trgm), 5% LLM (coreference) → $0.002/turn vs $0.03 pure-LLM
2. **Passive Computation**: Calculate on-demand (Phase 1), pre-compute later (Phase 2)
3. **Epistemic Humility**: Max confidence = 0.95 (never 100%)
4. **Dual Truth**: Domain DB (authoritative facts) + Memory system (contextual understanding)

---

## Common Pitfalls

1. Importing infrastructure in domain
2. Hardcoded heuristics
3. Missing type hints
4. Mutable domain objects
5. Quick fixes without tests
6. Features without vision justification
7. Silently ignoring conflicts
8. LLM when deterministic works
9. Real DB in unit tests (use mocks)
10. Creating docs for trivial changes

---

## Decision Guides

**When Starting Task:**
1. Read relevant design docs
2. Identify vision principle served
3. Plan tests first
4. Ask if design unclear

**When Uncertain:** Ask "Which principle?", "Which phase?", "Established pattern?", "Edge cases?", "How test?"

**When Tests Fail:**
1. Read test assertion
2. Check design doc expectation
3. Determine if test or implementation wrong
4. Fix root cause
5. Add edge case tests

**Commit Format:** `type(scope): subject` where type = `feat|fix|refactor|test|docs|chore`

---

## Current Status

**Phase 1A+1B**: 95% done (entity resolution, semantic extraction working)
**Issues**: 9/130 tests failing (formula mismatch)
**Next**: Phase 1C (retrieval, domain integration, conflicts)

---

**Remember**: Production-grade system for agentic intelligence. Build something worthy of being called a colleague.
