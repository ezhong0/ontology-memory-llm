# Development Guide

**Project**: Ontology-Aware Memory System
**Architecture**: See `ARCHITECTURE.md` for detailed architecture and code philosophy

This guide provides practical setup instructions, development workflows, and best practices for contributors.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Development Workflow](#development-workflow)
4. [Testing Guide](#testing-guide)
5. [Code Style and Standards](#code-style-and-standards)
6. [Common Tasks](#common-tasks)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.11+ | Application runtime |
| **Poetry** | 1.6+ | Dependency management |
| **Docker** | 20.10+ | Local PostgreSQL/Redis |
| **Docker Compose** | 2.0+ | Multi-container orchestration |
| **Git** | 2.30+ | Version control |
| **Make** | Any | Task automation (optional) |

### Recommended Tools

| Tool | Purpose |
|------|---------|
| **VS Code** or **PyCharm** | IDE with Python support |
| **PostgreSQL client** (psql, pgAdmin, DBeaver) | Database inspection |
| **Postman** or **HTTPie** | API testing |
| **jq** | JSON parsing in terminal |

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/memory-system.git
cd memory-system
```

### 2. Install Python Dependencies

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# Activate virtual environment
poetry shell
```

**Verify installation**:
```bash
python --version  # Should be 3.11+
poetry --version  # Should be 1.6+
```

### 3. Set Up Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Required environment variables**:
```bash
# .env
DATABASE_URL=postgresql+asyncpg://memoryuser:memorypass@localhost:5432/memorydb
OPENAI_API_KEY=sk-...your-key-here...
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

### 4. Start Infrastructure Services

```bash
# Start PostgreSQL with pgvector
docker-compose up -d postgres

# Verify PostgreSQL is running
docker-compose ps
```

**Wait for PostgreSQL to be ready** (check logs):
```bash
docker-compose logs -f postgres
# Wait for: "database system is ready to accept connections"
```

### 5. Initialize Database

```bash
# Run migrations
poetry run alembic upgrade head

# Verify tables created
poetry run python -c "
from src.infrastructure.database.session import engine
from sqlalchemy import inspect
inspector = inspect(engine)
print('Tables:', inspector.get_table_names())
"
```

### 6. Seed Test Data (Optional)

```bash
# Load sample entities and memories
poetry run python scripts/seed_data.py

# Verify data
poetry run python scripts/check_data.py
```

### 7. Start Development Server

```bash
# Start FastAPI with auto-reload
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Verify API is running**:
```bash
# Health check
curl http://localhost:8000/api/v1/health

# OpenAPI docs
open http://localhost:8000/docs
```

---

## Development Workflow

### Daily Development Flow

```bash
# 1. Pull latest changes
git checkout develop
git pull origin develop

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes
# ... edit code ...

# 4. Run tests locally
poetry run pytest

# 5. Run type checking
poetry run mypy src/

# 6. Run linting
poetry run ruff check src/

# 7. Format code
poetry run ruff format src/

# 8. Commit changes
git add .
git commit -m "feat(scope): your commit message"

# 9. Push and create PR
git push origin feature/your-feature-name
# Create PR on GitHub targeting 'develop' branch
```

### Using Makefile (Shortcut)

Create a `Makefile` for common tasks:

```makefile
# Makefile
.PHONY: install test lint format typecheck run clean

install:
	poetry install

test:
	poetry run pytest -v --cov=src --cov-report=term-missing

test-watch:
	poetry run ptw -- -v

lint:
	poetry run ruff check src/ tests/

format:
	poetry run ruff format src/ tests/

typecheck:
	poetry run mypy src/

run:
	poetry run uvicorn src.api.main:app --reload

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

db-migrate:
	poetry run alembic upgrade head

db-rollback:
	poetry run alembic downgrade -1

db-reset:
	docker-compose down -v
	docker-compose up -d postgres
	sleep 5
	poetry run alembic upgrade head
	poetry run python scripts/seed_data.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache
```

**Usage**:
```bash
make install     # Install dependencies
make test        # Run tests
make lint        # Lint code
make format      # Format code
make typecheck   # Type check
make run         # Start dev server
```

---

## Testing Guide

### Running Tests

**Run all tests**:
```bash
poetry run pytest
```

**Run specific test file**:
```bash
poetry run pytest tests/unit/domain/test_entity_resolver.py
```

**Run specific test function**:
```bash
poetry run pytest tests/unit/domain/test_entity_resolver.py::test_exact_match
```

**Run tests with coverage**:
```bash
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

**Run tests in watch mode** (re-run on file changes):
```bash
poetry run ptw  # Requires pytest-watch
```

**Run only unit tests** (fast):
```bash
poetry run pytest tests/unit/
```

**Run integration tests** (requires DB):
```bash
docker-compose up -d postgres
poetry run pytest tests/integration/
```

**Run E2E tests** (slowest):
```bash
poetry run pytest tests/e2e/
```

### Test Markers

Use pytest markers to categorize tests:

```python
# tests/conftest.py
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests (fast, no I/O)")
    config.addinivalue_line("markers", "integration: Integration tests (DB, external services)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (full API)")
    config.addinivalue_line("markers", "slow: Slow tests (>1s)")

# Usage in test file
@pytest.mark.unit
def test_confidence_decay():
    ...

@pytest.mark.integration
async def test_entity_repository():
    ...

@pytest.mark.e2e
async def test_chat_flow():
    ...
```

**Run only unit tests**:
```bash
poetry run pytest -m unit
```

**Run all except slow tests**:
```bash
poetry run pytest -m "not slow"
```

### Writing Tests

**Example unit test** (domain logic):
```python
# tests/unit/domain/test_lifecycle_manager.py
import pytest
from datetime import datetime, timedelta
from domain.services.lifecycle_manager import LifecycleManager
from domain.entities import SemanticMemory
from config.heuristics import DECAY_RATE_PER_DAY

@pytest.mark.unit
def test_compute_effective_confidence_applies_decay():
    # Arrange
    manager = LifecycleManager()
    memory = SemanticMemory(
        memory_id="semantic:123",
        confidence=0.9,
        last_validated_at=datetime.utcnow() - timedelta(days=30),
        status="active"
    )

    # Act
    effective_confidence = manager.compute_effective_confidence(memory)

    # Assert
    expected = 0.9 * math.exp(-30 * DECAY_RATE_PER_DAY)
    assert abs(effective_confidence - expected) < 0.001
    assert effective_confidence < 0.9  # Decayed
```

**Example integration test** (repository):
```python
# tests/integration/test_memory_repository.py
import pytest
from infrastructure.database.repositories import PostgresMemoryRepository
from tests.fixtures.factories import MemoryFactory

@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_by_entity_returns_relevant_memories(test_db_session):
    # Arrange
    repo = PostgresMemoryRepository(test_db_session)

    memory1 = MemoryFactory.create_semantic_memory(
        subject_entity_id="customer:acme_123",
        predicate="ordered"
    )
    memory2 = MemoryFactory.create_semantic_memory(
        subject_entity_id="customer:initech_456",
        predicate="ordered"
    )

    await repo.create(memory1)
    await repo.create(memory2)

    # Act
    results = await repo.find_by_entity(entity_id="customer:acme_123")

    # Assert
    assert len(results) == 1
    assert results[0].subject_entity_id == "customer:acme_123"
```

**Example E2E test** (API):
```python
# tests/e2e/test_entity_resolution_flow.py
import pytest
from httpx import AsyncClient

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_entity_disambiguation_flow(api_client: AsyncClient):
    # Step 1: Resolve ambiguous entity
    response = await api_client.post(
        "/api/v1/entities/resolve",
        json={
            "mention": "Acme",
            "user_id": "user_123",
            "context": {"session_id": "session_456"}
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["requires_disambiguation"] is True
    assert len(data["alternatives"]) >= 2

    # Step 2: User chooses entity
    chosen_entity = data["alternatives"][0]["entity_id"]
    response2 = await api_client.post(
        "/api/v1/entities/disambiguate",
        json={
            "mention": "Acme",
            "chosen_entity_id": chosen_entity,
            "user_id": "user_123",
            "context": {"session_id": "session_456"}
        }
    )

    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["alias_created"] is True

    # Step 3: Resolve again - should not require disambiguation
    response3 = await api_client.post(
        "/api/v1/entities/resolve",
        json={
            "mention": "Acme",
            "user_id": "user_123",
            "context": {"session_id": "session_456"}
        }
    )

    data3 = response3.json()
    assert data3["requires_disambiguation"] is False
    assert data3["canonical_entity"]["entity_id"] == chosen_entity
```

### Test Fixtures

**Shared fixtures** in `tests/conftest.py`:
```python
# tests/conftest.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from src.api.main import app
from src.infrastructure.database.models import Base

@pytest.fixture
async def test_db_engine():
    """Test database engine."""
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost:5432/testdb")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def test_db_session(test_db_engine):
    """Test database session with transaction rollback."""
    async with AsyncSession(test_db_engine) as session:
        async with session.begin():
            yield session
            await session.rollback()

@pytest.fixture
async def api_client():
    """Async HTTP client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

---

## Code Style and Standards

### Type Hints (Required)

**All public functions must have type hints**:
```python
# Good
def compute_score(value: float, weight: float) -> float:
    return value * weight

# Bad (missing type hints)
def compute_score(value, weight):
    return value * weight
```

**Use `typing` module** for complex types:
```python
from typing import List, Dict, Optional, Union, Literal

def process_entities(
    entity_ids: List[str],
    metadata: Optional[Dict[str, Any]] = None,
    mode: Literal["strict", "lenient"] = "strict"
) -> Union[List[Entity], None]:
    ...
```

### Docstrings (Required for Public APIs)

**Use Google-style docstrings**:
```python
def resolve_entity(mention: str, context: ResolutionContext) -> ResolutionResult:
    """
    Resolve textual mention to canonical entity using five-stage algorithm.

    Implements the algorithm from docs/design/ENTITY_RESOLUTION_DESIGN.md.
    Stages: Exact → User-specific → Fuzzy → Coreference → Disambiguation.

    Args:
        mention: Text mention to resolve (e.g., "Acme", "they")
        context: Resolution context with user ID, session, recent entities

    Returns:
        ResolutionResult with entity_id, confidence, and resolution method

    Raises:
        EntityNotFoundError: If no entities match and no domain DB fallback
        AmbiguousEntityError: If multiple entities match with similar confidence

    Examples:
        >>> context = ResolutionContext(user_id="user_1", ...)
        >>> result = resolve_entity("Acme Corporation", context)
        >>> assert result.confidence == 1.0  # Exact match
    """
    ...
```

### Code Formatting

**Use Ruff** for formatting (replaces Black + isort):
```bash
# Format all code
poetry run ruff format src/ tests/

# Check formatting without changing files
poetry run ruff format --check src/
```

**Ruff configuration** in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "A",   # flake8-builtins
    "C4",  # flake8-comprehensions
    "DTZ", # flake8-datetimez
    "T10", # flake8-debugger
    "RUF", # Ruff-specific rules
]
ignore = [
    "E501",  # Line too long (handled by formatter)
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"]  # Allow assert in tests
```

### Linting

**Run Ruff linter**:
```bash
# Check for linting errors
poetry run ruff check src/

# Auto-fix linting errors where possible
poetry run ruff check --fix src/
```

### Type Checking

**Run Mypy** in strict mode:
```bash
poetry run mypy src/
```

**Mypy configuration** in `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
disallow_subclassing_any = true
disallow_untyped_calls = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

---

## Common Tasks

### Database Migrations

**Create new migration**:
```bash
poetry run alembic revision --autogenerate -m "Add new field to semantic_memories"
```

**Review generated migration** in `src/infrastructure/database/migrations/versions/`:
```python
# Always review autogenerated migrations before applying!
# Check:
# - Column types are correct
# - Indexes are appropriate
# - Data migrations handled (if renaming/removing columns)
```

**Apply migration**:
```bash
poetry run alembic upgrade head
```

**Rollback migration**:
```bash
poetry run alembic downgrade -1  # Rollback one version
```

**View migration history**:
```bash
poetry run alembic history
poetry run alembic current
```

### Adding New Dependencies

**Add production dependency**:
```bash
poetry add <package-name>

# Example
poetry add httpx
```

**Add development dependency**:
```bash
poetry add --group dev <package-name>

# Example
poetry add --group dev pytest-watch
```

**Update dependencies**:
```bash
poetry update  # Update all dependencies
poetry update <package-name>  # Update specific package
```

**Lock dependencies** (commit `poetry.lock`):
```bash
poetry lock
git add poetry.lock
git commit -m "chore: update dependency lock file"
```

### API Testing with HTTPie

**Install HTTPie**:
```bash
brew install httpie  # macOS
# or
pip install httpx[cli]
```

**Example requests**:
```bash
# Health check
http GET localhost:8000/api/v1/health

# Chat request
http POST localhost:8000/api/v1/chat \
  message="What did Acme order last month?" \
  user_id="user_123" \
  session_id="session_456"

# Entity resolution
http POST localhost:8000/api/v1/entities/resolve \
  mention="Acme" \
  user_id="user_123" \
  context:='{"session_id": "session_456"}'
```

### Performance Profiling

**Use `py-spy` for production profiling** (no code changes needed):
```bash
# Install py-spy
pip install py-spy

# Profile running process
py-spy top --pid <process-id>

# Generate flamegraph
py-spy record -o profile.svg -- python -m uvicorn src.api.main:app
```

**Use `pytest-benchmark` for microbenchmarks**:
```python
# tests/benchmarks/test_retrieval_performance.py
import pytest

def test_retrieval_performance(benchmark):
    # Arrange
    retriever = MemoryRetriever(...)
    query = "test query"

    # Act & Assert
    result = benchmark(retriever.retrieve, query)
    assert result is not None

# Run benchmarks
poetry run pytest tests/benchmarks/ --benchmark-only
```

---

## Troubleshooting

### PostgreSQL Connection Issues

**Problem**: `sqlalchemy.exc.OperationalError: could not connect to server`

**Solution**:
```bash
# Check PostgreSQL is running
docker-compose ps

# Check PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# Verify connection
docker exec -it memory-system-postgres-1 psql -U memoryuser -d memorydb
```

### Migration Issues

**Problem**: `alembic.util.exc.CommandError: Target database is not up to date`

**Solution**:
```bash
# Check current version
poetry run alembic current

# Check pending migrations
poetry run alembic history

# Apply all pending migrations
poetry run alembic upgrade head

# If stuck, reset database (⚠️ destroys data)
poetry run alembic downgrade base
poetry run alembic upgrade head
```

### Type Checking Errors

**Problem**: `mypy` reports errors in third-party libraries

**Solution**:
```toml
# pyproject.toml
[[tool.mypy.overrides]]
module = "third_party_library.*"
ignore_missing_imports = true
```

### Test Database Cleanup

**Problem**: Tests failing due to leftover data

**Solution**:
```bash
# Drop and recreate test database
docker exec memory-system-postgres-1 psql -U postgres -c "DROP DATABASE IF EXISTS testdb;"
docker exec memory-system-postgres-1 psql -U postgres -c "CREATE DATABASE testdb;"

# Or use test fixtures with proper teardown
# See tests/conftest.py for transaction rollback pattern
```

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
# Ensure virtual environment is activated
poetry shell

# Verify PYTHONPATH (should include project root)
echo $PYTHONPATH

# If needed, add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/memory-system"

# Or use pytest with proper path
poetry run pytest
```

---

## Additional Resources

### Documentation

- **Architecture**: `ARCHITECTURE.md` - System architecture and code philosophy
- **API Docs**: `docs/design/API_DESIGN.md` - API contracts and endpoints
- **Design Docs**: `docs/design/` - Subsystem designs
- **Heuristics**: `docs/reference/HEURISTICS_CALIBRATION.md` - All configuration parameters

### External Resources

- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy (async)**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **PostgreSQL + pgvector**: https://github.com/pgvector/pgvector
- **Pytest**: https://docs.pytest.org/
- **Ruff**: https://docs.astral.sh/ruff/

### Getting Help

1. **Check documentation** in `docs/` folder
2. **Search existing issues** on GitHub
3. **Ask in team chat** (Slack/Discord)
4. **Create issue** with:
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)

---

## Quick Reference

### Essential Commands

```bash
# Setup
make install              # Install dependencies
make docker-up            # Start PostgreSQL
make db-migrate           # Run migrations

# Development
make run                  # Start dev server
make test                 # Run all tests
make lint                 # Lint code
make format               # Format code
make typecheck            # Type check

# Database
make db-reset             # Reset database (⚠️ destroys data)
poetry run alembic upgrade head       # Apply migrations
poetry run alembic revision -m "msg"  # Create migration

# Testing
poetry run pytest -v      # Run all tests (verbose)
poetry run pytest -m unit # Run unit tests only
poetry run pytest --cov   # Run with coverage

# Quality
poetry run mypy src/      # Type check
poetry run ruff check src/ # Lint
poetry run ruff format src/ # Format
```

### File Locations

```
src/api/routes/          # API endpoints
src/domain/services/     # Business logic
src/infrastructure/      # External adapters
src/config/heuristics.py # Configuration parameters
tests/unit/              # Unit tests
tests/integration/       # Integration tests
tests/e2e/               # End-to-end tests
docs/design/             # Design documents
```

### Environment Variables

```bash
DATABASE_URL             # PostgreSQL connection string
OPENAI_API_KEY           # OpenAI API key for embeddings
LOG_LEVEL                # Logging level (DEBUG/INFO/WARNING/ERROR)
ENVIRONMENT              # Environment (development/staging/production)
```

---

**Questions?** Check `docs/README.md` or create an issue on GitHub.
