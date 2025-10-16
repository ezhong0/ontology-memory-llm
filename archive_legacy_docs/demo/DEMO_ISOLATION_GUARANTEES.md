# Demo Isolation Guarantees

**Purpose**: Ensure demo development cannot contaminate or break production code.

---

## The Iron Rules

### Rule 1: One-Way Import Dependency

```
Demo → Domain/Infrastructure/API (allowed, read-only)
Domain/Infrastructure/API → Demo (FORBIDDEN)
```

**Enforcement**:
```python
# .pylintrc or ruff.toml
[tool.ruff.lint.isort]
known-first-party = ["src"]
sections = ["FUTURE", "STDLIB", "THIRDPARTY", "FIRSTPARTY", "LOCALFOLDER"]

# Enforce: domain/infrastructure/api cannot import from demo
[tool.ruff.lint.flake8-import-conventions]
banned-from = [
    {path = "src.demo", within = ["src.domain", "src.infrastructure", "src.api"]}
]
```

### Rule 2: Demo Code Lives ONLY in src/demo/

```
src/
├── demo/              # ✅ ALL demo code here
│   ├── api/          # Demo API routes
│   ├── services/     # Demo services
│   └── models/       # Demo API models
├── domain/            # ❌ Demo code FORBIDDEN
├── infrastructure/    # ❌ Demo code FORBIDDEN
└── api/              # ❌ Demo code FORBIDDEN
```

**Enforcement**: Code review checklist + automated path checks in CI.

### Rule 3: Demo Cannot Modify Domain Behavior

Demo can:
- ✅ **Call** domain services via their ports
- ✅ **Read** domain entities
- ✅ **Create** domain entities through services

Demo cannot:
- ❌ Modify domain service implementations
- ❌ Bypass domain services to write directly to repositories
- ❌ Change domain entity definitions
- ❌ Add fields to production models

**Why Safe**: Domain services are called through interfaces (ports). Demo is just another consumer.

### Rule 4: Separate Test Directories

```
tests/
├── unit/
│   ├── domain/           # Production domain tests
│   ├── api/             # Production API tests
│   └── infrastructure/   # Production infrastructure tests
├── integration/          # Production integration tests
└── demo/                 # ✅ ALL demo tests here
    ├── test_scenario_loader.py
    ├── test_admin_services.py
    └── test_demo_api.py
```

**Test isolation**:
```bash
# Run ONLY production tests
make test-prod        # Excludes tests/demo/

# Run ONLY demo tests
make test-demo        # Only tests/demo/

# Run all tests
make test-all
```

### Rule 5: Demo Mode Environment Flag

```python
# src/config/settings.py
class Settings(BaseSettings):
    DEMO_MODE_ENABLED: bool = False  # Default: OFF

# src/demo/__init__.py - Fail fast if demo mode disabled
from src.config.settings import settings

if not settings.DEMO_MODE_ENABLED:
    raise RuntimeError(
        "Demo mode is disabled. Set DEMO_MODE_ENABLED=true in .env to enable demo."
    )

# All demo API routes check this flag
from src.demo import *  # Raises if not enabled
```

**Production deployment**:
```bash
# Production .env
DEMO_MODE_ENABLED=false  # Demo code won't even load

# Development .env
DEMO_MODE_ENABLED=true   # Demo available
```

---

## Automated Safeguards

### 1. Import Linting (Enforced in CI)

```bash
# .github/workflows/ci.yml or Makefile
lint-demo-isolation:
	@echo "Checking demo isolation..."
	@! grep -r "from src.demo" src/domain src/infrastructure src/api || \
	  (echo "ERROR: Production code imports from demo!" && exit 1)
	@echo "✅ Demo isolation verified"
```

### 2. Type Checking Isolation

```ini
# mypy.ini
[mypy]
warn_unused_ignores = True
disallow_any_unimported = True

# Ensure domain doesn't depend on demo types
[[tool.mypy.overrides]]
module = "src.domain.*"
disallow_any_expr = false
# Demo types not available in domain context
```

### 3. Test Coverage Separation

```bash
# Run production tests with coverage (demo excluded)
pytest tests/unit tests/integration --cov=src --cov-report=html --ignore=tests/demo

# Verify production coverage meets threshold without demo
pytest --cov=src --cov-fail-under=80 --ignore=tests/demo
```

### 4. Git Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Checking demo isolation..."

# Check for demo imports in production code
if git diff --cached --name-only | grep -q "^src/\(domain\|infrastructure\|api\)/"; then
  if git diff --cached | grep -q "from src.demo"; then
    echo "❌ ERROR: Production code cannot import from demo"
    exit 1
  fi
fi

# Check for production models modified in demo commit
if git diff --cached --name-only | grep -q "^src/demo/"; then
  if git diff --cached --name-only | grep -q "^src/infrastructure/database/models.py"; then
    echo "⚠️  WARNING: Modifying production models in demo commit"
    echo "Are you sure this is intentional? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
      exit 1
    fi
  fi
fi

echo "✅ Demo isolation verified"
```

---

## What Demo CAN Do Safely

### ✅ Use Domain Services (Read-Only from Demo's Perspective)

```python
# src/demo/services/scenario_loader.py
from src.domain.services.entity_resolution_service import EntityResolver
from src.domain.services.semantic_extraction_service import SemanticMemoryCreator

class ScenarioLoaderService:
    def __init__(
        self,
        entity_resolver: EntityResolver,  # ✅ Injected, read-only interface
        memory_creator: SemanticMemoryCreator  # ✅ Injected, read-only interface
    ):
        self.entity_resolver = entity_resolver
        self.memory_creator = memory_creator

    async def load_scenario(self, scenario_id: int):
        # ✅ Call domain services - this is safe!
        entity = await self.entity_resolver.resolve("Kai Media", ...)
        memory = await self.memory_creator.create(...)
```

### ✅ Add New Database Models (Domain Schema Only)

```python
# src/infrastructure/database/domain_models.py (NEW FILE)
"""
Domain schema models (for external business data).
Separate from app schema models (memory system).
"""
from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import UUID

class DomainCustomer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "domain"}  # ✅ Separate schema

    customer_id = Column(UUID, primary_key=True)
    name = Column(Text)
    # ...
```

**Why Safe**: Completely separate schema (`domain.*`), doesn't touch `app.*` schema where production memory models live.

### ✅ Add Demo-Specific API Routes

```python
# src/demo/api/scenarios.py
from fastapi import APIRouter

router = APIRouter(prefix="/demo/scenarios", tags=["demo"])

@router.post("/{scenario_id}/load")  # ✅ /demo/* prefix
async def load_scenario(scenario_id: int):
    # Demo route - isolated from production /chat, /memory, etc.
    ...
```

**Why Safe**: Different URL prefix (`/demo/*`), controlled by `DEMO_MODE_ENABLED` flag.

### ✅ Add Demo-Specific Services

```python
# src/demo/services/admin_database.py
class AdminDatabaseService:
    """Admin CRUD for domain schema - demo only."""

    async def delete_customer(self, customer_id: UUID):
        # ✅ Operates on domain.customers, not app.canonical_entities
        ...
```

**Why Safe**: Only operates on `domain` schema (test data), not `app` schema (production memory).

---

## What Demo CANNOT Do

### ❌ Modify Production Domain Services

```python
# src/domain/services/entity_resolution_service.py

# ❌ FORBIDDEN: Adding demo-specific logic to production service
class EntityResolver:
    async def resolve(self, mention: str, context: ResolutionContext):
        # ❌ Don't add this!
        if settings.DEMO_MODE_ENABLED:
            # Special demo behavior
            ...
```

**Why Forbidden**: Production services should never know about demo mode. Demo-specific logic belongs in demo services.

**Correct Approach**: Create a demo service that wraps the production service:

```python
# src/demo/services/demo_entity_resolver.py
class DemoEntityResolver:
    """Demo wrapper for entity resolution with additional features."""

    def __init__(self, base_resolver: EntityResolver):
        self.base = base_resolver  # ✅ Composition, not modification

    async def resolve_with_tracing(self, mention: str, context: ResolutionContext):
        # Demo-specific tracing
        trace_start = time.time()
        result = await self.base.resolve(mention, context)  # ✅ Delegate to production
        trace_end = time.time()
        # Log trace
        return result, trace
```

### ❌ Modify Production Database Models

```python
# src/infrastructure/database/models.py

# ❌ FORBIDDEN: Adding demo fields to production models
class SemanticMemory(Base):
    __tablename__ = "semantic_memories"
    __table_args__ = {"schema": "app"}

    memory_id = Column(BigInteger, primary_key=True)
    # ...

    # ❌ Don't add this!
    is_demo_data = Column(Boolean, default=False)  # NO!
```

**Why Forbidden**: Production models should never have demo-specific fields.

**Correct Approach**: Track demo data separately:

```python
# src/demo/tracking.py
class DemoDataTracker:
    """Track which data was created by demos."""

    _demo_entities: Set[str] = set()

    @classmethod
    def mark_as_demo(cls, entity_id: str):
        cls._demo_entities.add(entity_id)

    @classmethod
    def is_demo_data(cls, entity_id: str) -> bool:
        return entity_id in cls._demo_entities
```

Or use a separate tracking table:

```python
# src/infrastructure/database/domain_models.py
class DemoDataTracking(Base):
    __tablename__ = "demo_data_tracking"
    __table_args__ = {"schema": "domain"}  # ✅ In domain schema

    id = Column(BigInteger, primary_key=True)
    entity_type = Column(Text)  # customer, sales_order, etc.
    entity_id = Column(UUID)
    scenario_id = Column(Integer)
    created_at = Column(DateTime)
```

### ❌ Import Production Code into Domain Layer

```python
# src/domain/services/entity_resolution_service.py

# ❌ FORBIDDEN
from src.demo.services.scenario_loader import ScenarioLoaderService

# This would create circular dependency and contaminate production
```

**Enforced by**: Import linting (automated in CI).

---

## Code Review Checklist

Before merging demo code, verify:

- [ ] All demo code is in `src/demo/`
- [ ] No imports of `src.demo` in `src/domain/`, `src/infrastructure/`, or `src/api/`
- [ ] No modifications to production models in `src/infrastructure/database/models.py`
- [ ] No demo-specific logic in domain services
- [ ] All demo tests are in `tests/demo/`
- [ ] Demo API routes have `/demo` prefix
- [ ] `DEMO_MODE_ENABLED` check is present
- [ ] New domain schema models are in separate file (`domain_models.py`)
- [ ] CI passes with `make lint-demo-isolation`

---

## CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test-production:
    name: Test Production Code (Isolated)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: poetry install
      - name: Run production tests only
        run: |
          DEMO_MODE_ENABLED=false pytest tests/unit tests/integration --ignore=tests/demo
      - name: Check production coverage
        run: |
          pytest --cov=src --cov-fail-under=80 \
                 --ignore=tests/demo \
                 --ignore=src/demo

  test-demo:
    name: Test Demo (Separate)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: poetry install
      - name: Run demo tests
        run: |
          DEMO_MODE_ENABLED=true pytest tests/demo

  lint-isolation:
    name: Verify Demo Isolation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check no demo imports in production
        run: |
          if grep -r "from src.demo" src/domain src/infrastructure src/api; then
            echo "ERROR: Production code imports from demo!"
            exit 1
          fi
      - name: Check demo stays in demo directory
        run: |
          # Fail if demo code found outside src/demo/
          if find src/domain src/infrastructure src/api -name "*demo*" -type f; then
            echo "ERROR: Demo code found outside src/demo/"
            exit 1
          fi
```

---

## Makefile Commands

```makefile
# Makefile

# Production tests (demo excluded)
.PHONY: test-prod
test-prod:
	DEMO_MODE_ENABLED=false pytest tests/unit tests/integration --ignore=tests/demo -v

# Demo tests only
.PHONY: test-demo
test-demo:
	DEMO_MODE_ENABLED=true pytest tests/demo -v

# Verify demo isolation
.PHONY: check-demo-isolation
check-demo-isolation:
	@echo "Checking demo isolation rules..."
	@# Check for demo imports in production
	@! grep -r "from src.demo" src/domain src/infrastructure src/api || \
	  (echo "❌ ERROR: Production code imports from demo!" && exit 1)
	@# Check for demo files outside demo directory
	@! find src/domain src/infrastructure src/api -name "*demo*" -type f | grep -q . || \
	  (echo "❌ ERROR: Demo code found outside src/demo/" && exit 1)
	@echo "✅ Demo isolation verified!"

# Run all checks before committing demo code
.PHONY: check-demo
check-demo: check-demo-isolation test-prod test-demo
	@echo "✅ All demo safety checks passed!"
```

---

## Summary: You're Safe When...

✅ **Demo code stays in `src/demo/`**
✅ **Demo imports FROM production (never the reverse)**
✅ **Demo uses domain services via ports (interfaces)**
✅ **Demo operates on `domain` schema (test data), not `app` schema (production memory)**
✅ **Demo tests stay in `tests/demo/`**
✅ **CI runs production tests independently** (can pass without demo)
✅ **`DEMO_MODE_ENABLED=false` disables demo completely**

The architecture guarantees that:
1. Production code never knows demo exists
2. Demo is completely optional (can be removed by deleting `src/demo/`)
3. Production tests pass independently
4. Domain services remain pure (no demo logic)
5. Automated checks prevent contamination

**Bottom line**: You can work on demo fearlessly - the boundaries are enforced by code structure, type system, linting, and CI.
