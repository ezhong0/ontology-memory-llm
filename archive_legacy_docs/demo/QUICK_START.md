# Demo Development Quick Start

## TL;DR: You're Protected

The demo is **architecturally isolated** from production code. You can work on demo fearlessly.

---

## The Safety Guarantee

✅ **Production code never knows demo exists** (one-way dependency)
✅ **Demo can be deleted without breaking anything** (just delete `src/demo/`)
✅ **Production tests pass independently** (don't need demo)
✅ **Automated checks prevent contamination** (CI enforced)

---

## Where Demo Code Lives

```
src/
├── demo/              # ✅ ALL demo code goes here
│   ├── api/          # Demo API routes (/demo/*)
│   ├── services/     # Demo-specific services
│   └── models/       # Demo API models

├── domain/            # ❌ Never touch for demo
├── infrastructure/    # ❌ Only add domain_models.py (separate file)
└── api/              # ❌ Never touch for demo

tests/
└── demo/             # ✅ ALL demo tests go here
```

---

## Safe Operations

### ✅ You CAN Do This

```python
# Import FROM production (read-only)
from src.domain.services.entity_resolution_service import EntityResolver
from src.infrastructure.database.repositories.customer_repository import CustomerRepository

# Call domain services
class ScenarioLoaderService:
    def __init__(self, entity_resolver: EntityResolver):
        self.resolver = entity_resolver  # ✅ Using production service

    async def load_scenario(self):
        entity = await self.resolver.resolve("Kai Media")  # ✅ Safe!
```

### ❌ You CANNOT Do This

```python
# ❌ Production code importing demo
# src/domain/services/some_service.py
from src.demo.services.scenario_loader import ScenarioLoader  # FORBIDDEN!

# ❌ Modifying production models
# src/infrastructure/database/models.py
class SemanticMemory(Base):
    is_demo_data = Column(Boolean)  # FORBIDDEN! No demo fields in production models

# ❌ Demo logic in domain services
# src/domain/services/entity_resolution_service.py
class EntityResolver:
    def resolve(self, mention: str):
        if settings.DEMO_MODE_ENABLED:  # FORBIDDEN! Domain shouldn't know about demo
            ...
```

---

## Development Commands

### Before You Start
```bash
# Verify production tests pass (baseline)
make test-prod
```

### While Developing Demo
```bash
# Run demo tests
make test-demo

# Check isolation rules
make check-demo-isolation

# Run all demo safety checks
make check-demo
```

### Before Committing
```bash
# Full safety check: isolation + production tests + demo tests
make check-demo
```

---

## The Rules (Enforced Automatically)

### Rule 1: One-Way Imports
```
Demo → Production (✅ Allowed)
Production → Demo (❌ Forbidden, CI will fail)
```

### Rule 2: Demo Code Only in src/demo/
All demo implementation in `src/demo/`, all demo tests in `tests/demo/`.

### Rule 3: Production Tests Must Pass Without Demo
```bash
DEMO_MODE_ENABLED=false make test-prod  # Must pass
```

### Rule 4: No Demo Fields in Production Models
Production models in `src/infrastructure/database/models.py` must remain demo-agnostic.

---

## What If I Break the Rules?

### Automated Safety Net

**Pre-commit** (local):
- Checks for demo imports in production
- Warns if modifying production models in demo commit

**CI Pipeline** (GitHub Actions):
- `make check-demo-isolation` - Fails if boundaries violated
- `make test-prod` - Fails if production tests broken
- `make test-demo` - Fails if demo tests broken

### Manual Check
```bash
# Run before pushing
make check-demo
```

If this passes, you're good to push!

---

## Common Questions

### Q: Can I modify domain services for demo needs?
**A:** No. Create a demo wrapper service that uses the production service.

**Example**:
```python
# ❌ Wrong: Modifying production service
class EntityResolver:
    def resolve(self, mention: str):
        if DEMO_MODE:  # Don't do this!
            ...

# ✅ Right: Demo wrapper
class DemoEntityResolver:
    def __init__(self, base: EntityResolver):
        self.base = base

    async def resolve_with_trace(self, mention: str):
        start = time.time()
        result = await self.base.resolve(mention)  # Use production
        duration = time.time() - start
        return result, duration  # Add demo-specific tracing
```

### Q: Can I add a new database table for demo data?
**A:** Yes, but in the **domain schema**, not app schema.

```python
# ✅ Right: New file src/infrastructure/database/domain_models.py
class DomainCustomer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "domain"}  # Separate schema!

# ❌ Wrong: Adding to src/infrastructure/database/models.py (production models)
```

### Q: Can I share utilities between production and demo?
**A:** Yes, put shared utilities in `src/common/` or `src/lib/`.

```
src/
├── common/         # ✅ Shared utilities (used by both)
│   └── utils.py
├── demo/          # Demo-specific code
└── domain/        # Production code
```

### Q: What if I need demo-specific configuration?
**A:** Use the `DEMO_MODE_ENABLED` flag:

```python
# src/config/settings.py
class Settings(BaseSettings):
    DEMO_MODE_ENABLED: bool = False  # Default: disabled

# src/demo/services/scenario_loader.py
if not settings.DEMO_MODE_ENABLED:
    raise RuntimeError("Demo mode disabled")
```

---

## Quick Reference: File Locations

| What | Where | Why |
|------|-------|-----|
| Demo API routes | `src/demo/api/*.py` | Isolated endpoints `/demo/*` |
| Scenario definitions | `src/demo/services/scenario_registry.py` | Configuration, not logic |
| Demo services | `src/demo/services/*.py` | Demo-specific orchestration |
| Demo tests | `tests/demo/*.py` | Isolated test suite |
| Domain data models | `src/infrastructure/database/domain_models.py` | New file, separate from production |
| Production models | `src/infrastructure/database/models.py` | **Never modify for demo** |

---

## Summary Checklist

Before committing demo code:
- [ ] All demo code in `src/demo/`
- [ ] All demo tests in `tests/demo/`
- [ ] No imports of `src.demo` in production code
- [ ] No demo fields added to production models
- [ ] `make check-demo` passes
- [ ] Production tests still pass: `make test-prod`

**If all checked: You're safe to commit!** ✅

---

## Need Help?

- **Full Architecture**: See `docs/demo/DEMO_ARCHITECTURE.md`
- **Isolation Guarantees**: See `docs/demo/DEMO_ISOLATION_GUARANTEES.md`
- **Production System**: See `CLAUDE.md`
