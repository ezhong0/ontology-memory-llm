# Application Architecture and Code Philosophy

**System**: Ontology-Aware Memory System
**Language**: Python 3.11+
**Framework**: FastAPI (REST API)
**Database**: PostgreSQL 15+ with pgvector
**Philosophy Alignment**: Design decisions must answer the Three Questions Framework

---

## Table of Contents

1. [Architecture Principles](#architecture-principles)
2. [Application Structure](#application-structure)
3. [Code Philosophy](#code-philosophy)
4. [Testing Strategy](#testing-strategy)
5. [Development Workflow](#development-workflow)
6. [Quality Standards](#quality-standards)

---

## Architecture Principles

### 1. Hexagonal Architecture (Ports & Adapters)

**Why**: Separates business logic from infrastructure, enabling testability and flexibility.

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                   │
│                    Ports (Interfaces)                    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   Domain Layer                           │
│   - Entity Resolution Logic                              │
│   - Retrieval Logic                                      │
│   - Memory Lifecycle Logic                               │
│   - Pure business rules (testable without DB/API)        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Infrastructure Layer                        │
│   - PostgreSQL Repository (Adapter)                      │
│   - OpenAI Embedding Service (Adapter)                   │
│   - Domain DB Connector (Adapter)                        │
│   - External dependencies                                │
└─────────────────────────────────────────────────────────┘
```

**Three Questions Alignment**:
- **Which principle**: Testability, Maintainability
- **Cost justification**: Clean separation allows testing without infrastructure
- **Phase**: Phase 1 essential (prevents technical debt)

### 2. Domain-Driven Design (DDD) Lite

**Core Concepts**:
- **Entities**: `CanonicalEntity`, `SemanticMemory`, `EpisodicMemory`
- **Value Objects**: `Confidence`, `TemporalScope`, `ResolutionResult`
- **Aggregates**: Memory lifecycle operations grouped by root entity
- **Domain Services**: `EntityResolver`, `MemoryRetriever`, `LifecycleManager`

**Why DDD Lite (not full DDD)**:
- Full DDD would be over-engineering for Phase 1 (violates Three Questions)
- We adopt: Domain modeling, Ubiquitous language, Service layer
- We skip: Event sourcing, CQRS, complex aggregate boundaries (Phase 2+)

### 3. Dependency Injection

**Why**: Testability, configurability, adherence to SOLID principles.

Use `dependency-injector` library for Python:
```python
# containers.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Infrastructure
    db_session = providers.Singleton(create_db_session, config.database)
    embedding_service = providers.Factory(OpenAIEmbeddingService, api_key=config.openai.api_key)

    # Repositories
    entity_repository = providers.Factory(EntityRepository, session=db_session)
    memory_repository = providers.Factory(MemoryRepository, session=db_session)

    # Domain Services
    entity_resolver = providers.Factory(
        EntityResolver,
        entity_repo=entity_repository,
        embedding_service=embedding_service
    )
```

### 4. Async-First Design

**Why**: I/O-bound operations (DB queries, LLM calls, embedding generation) benefit from async.

**Guidelines**:
- All I/O operations are `async`
- Use `asyncpg` for PostgreSQL
- Use `httpx` for external API calls
- FastAPI native async support

**Trade-off**: Slightly more complex code, but 10x+ throughput for I/O operations.

---

## Application Structure

```
memory-system/
├── src/
│   ├── api/                    # FastAPI application (REST API layer)
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app, startup/shutdown
│   │   ├── dependencies.py    # FastAPI dependency injection
│   │   ├── middleware.py      # Auth, logging, error handling
│   │   ├── routes/            # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── chat.py        # POST /chat [Phase 1]
│   │   │   ├── memories.py    # Memory CRUD [Phase 1]
│   │   │   ├── entities.py    # Entity resolution [Phase 1]
│   │   │   ├── retrieval.py   # Retrieval API [Phase 2]
│   │   │   ├── conflicts.py   # Conflict management [Phase 2]
│   │   │   └── health.py      # Health check [Phase 1]
│   │   ├── models/            # Pydantic models (API contracts)
│   │   │   ├── __init__.py
│   │   │   ├── requests.py    # Request models
│   │   │   ├── responses.py   # Response models
│   │   │   └── shared.py      # Shared models
│   │   └── errors.py          # API error handlers
│   │
│   ├── domain/                # Business logic (pure Python, no I/O)
│   │   ├── __init__.py
│   │   ├── entities/          # Domain entities
│   │   │   ├── __init__.py
│   │   │   ├── canonical_entity.py
│   │   │   ├── semantic_memory.py
│   │   │   ├── episodic_memory.py
│   │   │   └── memory_conflict.py
│   │   ├── value_objects/     # Value objects (immutable)
│   │   │   ├── __init__.py
│   │   │   ├── confidence.py
│   │   │   ├── temporal_scope.py
│   │   │   └── resolution_result.py
│   │   ├── services/          # Domain services (business logic)
│   │   │   ├── __init__.py
│   │   │   ├── entity_resolver.py      # Five-stage resolution
│   │   │   ├── memory_retriever.py     # Multi-signal retrieval
│   │   │   ├── lifecycle_manager.py    # State transitions, decay
│   │   │   ├── memory_extractor.py     # Fact extraction from chat
│   │   │   └── conflict_detector.py    # Conflict detection [Phase 2]
│   │   ├── ports/             # Interfaces (abstract base classes)
│   │   │   ├── __init__.py
│   │   │   ├── entity_repository.py
│   │   │   ├── memory_repository.py
│   │   │   ├── embedding_service.py
│   │   │   └── domain_db_service.py
│   │   └── exceptions.py      # Domain exceptions
│   │
│   ├── infrastructure/        # External systems adapters
│   │   ├── __init__.py
│   │   ├── database/          # PostgreSQL adapters
│   │   │   ├── __init__.py
│   │   │   ├── models.py      # SQLAlchemy models
│   │   │   ├── session.py     # Database session management
│   │   │   ├── repositories/  # Repository implementations
│   │   │   │   ├── __init__.py
│   │   │   │   ├── entity_repository.py
│   │   │   │   ├── memory_repository.py
│   │   │   │   └── config_repository.py
│   │   │   └── migrations/    # Alembic migrations
│   │   │       └── versions/
│   │   ├── embedding/         # Embedding service adapters
│   │   │   ├── __init__.py
│   │   │   ├── openai_service.py      # OpenAI embeddings
│   │   │   └── mock_service.py        # Mock for testing
│   │   ├── domain_db/         # Domain database connector
│   │   │   ├── __init__.py
│   │   │   ├── connector.py
│   │   │   └── mock_connector.py      # Mock for testing
│   │   └── cache/             # Caching layer [Phase 2]
│   │       ├── __init__.py
│   │       └── redis_cache.py
│   │
│   ├── config/                # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py        # Pydantic settings
│   │   ├── heuristics.py      # From HEURISTICS_CALIBRATION.md
│   │   └── logging.py         # Logging configuration
│   │
│   ├── utils/                 # Shared utilities
│   │   ├── __init__.py
│   │   ├── text_similarity.py # Levenshtein, fuzzy matching
│   │   ├── vector_ops.py      # Cosine similarity, vector utils
│   │   └── temporal.py        # Temporal parsing and decay
│   │
│   └── __init__.py
│
├── tests/                     # Test suite (mirrors src structure)
│   ├── __init__.py
│   ├── unit/                  # Unit tests (fast, no I/O)
│   │   ├── domain/            # Domain logic tests
│   │   │   ├── test_entity_resolver.py
│   │   │   ├── test_memory_retriever.py
│   │   │   └── test_lifecycle_manager.py
│   │   └── utils/
│   │       └── test_text_similarity.py
│   ├── integration/           # Integration tests (DB, external services)
│   │   ├── test_entity_repository.py
│   │   ├── test_memory_repository.py
│   │   └── test_embedding_service.py
│   ├── e2e/                   # End-to-end API tests
│   │   ├── test_chat_flow.py
│   │   ├── test_entity_resolution_flow.py
│   │   └── test_retrieval_flow.py
│   ├── fixtures/              # Test fixtures and factories
│   │   ├── __init__.py
│   │   ├── factories.py       # Factory functions for test data
│   │   └── database.py        # Test database setup
│   └── conftest.py            # Pytest configuration
│
├── scripts/                   # Development and deployment scripts
│   ├── init_db.py            # Initialize database schema
│   ├── seed_data.py          # Seed test data
│   ├── benchmark.py          # Performance benchmarks
│   └── migrate.py            # Run migrations
│
├── docs/                      # Documentation (organized earlier)
│   ├── vision/
│   ├── design/
│   ├── quality/
│   └── reference/
│
├── alembic.ini               # Database migration config
├── pyproject.toml            # Poetry dependency management
├── pytest.ini                # Pytest configuration
├── .env.example              # Example environment variables
├── .gitignore
├── README.md                 # Project README
└── Dockerfile                # Container for deployment
```

### Key Structural Decisions

**1. Why `domain/` separate from `infrastructure/`?**
- **Hexagonal architecture**: Domain logic is pure Python, testable without DB/API
- **Dependency direction**: Domain never imports from infrastructure
- **Three Questions**: Enables fast unit tests (cost justification)

**2. Why `ports/` (interfaces)?**
- **Dependency Inversion Principle**: Domain depends on abstractions, not concrete implementations
- **Testability**: Easy to mock repositories and services
- **Flexibility**: Swap PostgreSQL for different DB without changing domain logic

**3. Why `api/routes/` split by resource?**
- **Separation of Concerns**: Each route file handles one resource
- **API versioning**: Easy to add `v2/` routes alongside `v1/`
- **Team scaling**: Different developers can work on different routes

**4. Why `config/heuristics.py` separate?**
- **HEURISTICS_CALIBRATION.md compliance**: All 43 parameters in one place
- **Phase 2 tuning**: Easy to update values based on operational data
- **Version control**: Track parameter changes over time

---

## Code Philosophy

### 1. Explicit Over Implicit

**Bad** (implicit):
```python
def resolve_entity(text):
    # What context? What user? What confidence?
    ...
```

**Good** (explicit):
```python
@dataclass
class ResolutionContext:
    user_id: str
    session_id: str
    recent_entities: List[str]
    conversation_text: str

def resolve_entity(
    mention: str,
    context: ResolutionContext
) -> ResolutionResult:
    # Clear inputs and outputs
    ...
```

**Rationale**: Aligns with epistemic transparency from VISION.md

### 2. Type Hints Everywhere

**Required** for all public functions and methods:
```python
from typing import Optional, List
from datetime import datetime

def compute_effective_confidence(
    stored_confidence: float,
    days_since_validation: int,
    decay_rate: float = 0.01
) -> float:
    """
    Compute confidence with exponential decay.

    Args:
        stored_confidence: Base confidence (0.0-1.0)
        days_since_validation: Age of memory in days
        decay_rate: Decay rate per day (default from heuristics)

    Returns:
        Effective confidence after decay (0.0-1.0)
    """
    return stored_confidence * math.exp(-days_since_validation * decay_rate)
```

**Tools**: Use `mypy` in strict mode for type checking.

### 3. Immutable Value Objects

**Pattern**:
```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)  # Immutable
class Confidence:
    """Value object representing confidence score with metadata."""

    value: float  # 0.0 to 1.0
    source: Literal['exact_match', 'fuzzy_match', 'user_disambiguation']
    factors: dict[str, float]  # e.g., {'text_similarity': 0.85}

    def __post_init__(self):
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.value}")

    def decay(self, days: int, rate: float = 0.01) -> 'Confidence':
        """Return new Confidence with decay applied (immutable)."""
        new_value = self.value * math.exp(-days * rate)
        return Confidence(
            value=new_value,
            source=self.source,
            factors={**self.factors, 'decay_applied': True}
        )
```

**Why immutable**: Prevents bugs from shared mutable state, aligns with functional programming principles.

### 4. Fail Fast with Domain Exceptions

**Pattern**:
```python
# domain/exceptions.py
class DomainException(Exception):
    """Base exception for domain errors."""
    pass

class EntityNotFoundError(DomainException):
    """Raised when entity resolution fails."""
    def __init__(self, mention: str, context: str):
        self.mention = mention
        self.context = context
        super().__init__(f"Entity '{mention}' not found in context: {context}")

class AmbiguousEntityError(DomainException):
    """Raised when multiple entities match and disambiguation required."""
    def __init__(self, mention: str, candidates: List[str]):
        self.mention = mention
        self.candidates = candidates
        super().__init__(
            f"Ambiguous entity '{mention}': {len(candidates)} candidates"
        )
```

**Usage**:
```python
def resolve_entity(mention: str, context: ResolutionContext) -> ResolutionResult:
    candidates = find_candidates(mention)

    if len(candidates) == 0:
        raise EntityNotFoundError(mention, context.conversation_text)

    if len(candidates) > 1 and max_confidence < 0.75:
        raise AmbiguousEntityError(mention, [c.entity_id for c in candidates])

    return ResolutionResult(entity_id=candidates[0].entity_id, ...)
```

**API layer catches and converts**:
```python
# api/errors.py
@app.exception_handler(AmbiguousEntityError)
async def handle_ambiguous_entity(request: Request, exc: AmbiguousEntityError):
    return JSONResponse(
        status_code=200,  # Not an error, expected flow
        content={
            "resolved": False,
            "requires_disambiguation": True,
            "alternatives": exc.candidates,
            "disambiguation_prompt": f"I found {len(exc.candidates)} entities..."
        }
    )
```

### 5. Repository Pattern for Data Access

**Port (interface)**:
```python
# domain/ports/entity_repository.py
from abc import ABC, abstractmethod
from typing import Optional, List
from domain.entities import CanonicalEntity

class EntityRepositoryPort(ABC):
    """Port for entity data access."""

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[CanonicalEntity]:
        """Retrieve entity by ID."""
        pass

    @abstractmethod
    async def find_by_name(self, name: str, user_id: str) -> List[CanonicalEntity]:
        """Find entities by name (exact or fuzzy)."""
        pass

    @abstractmethod
    async def create(self, entity: CanonicalEntity) -> CanonicalEntity:
        """Persist new entity."""
        pass
```

**Adapter (implementation)**:
```python
# infrastructure/database/repositories/entity_repository.py
from domain.ports.entity_repository import EntityRepositoryPort
from infrastructure.database.models import CanonicalEntityModel

class PostgresEntityRepository(EntityRepositoryPort):
    """PostgreSQL implementation of entity repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: str) -> Optional[CanonicalEntity]:
        result = await self.session.execute(
            select(CanonicalEntityModel).where(
                CanonicalEntityModel.entity_id == entity_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    def _to_domain(self, model: CanonicalEntityModel) -> CanonicalEntity:
        """Convert SQLAlchemy model to domain entity."""
        return CanonicalEntity(
            entity_id=model.entity_id,
            entity_type=model.entity_type,
            canonical_name=model.canonical_name,
            properties=model.properties,
            created_at=model.created_at
        )
```

**Why**: Domain logic never touches SQLAlchemy models, enabling pure unit tests.

### 6. Configuration via Environment + Heuristics File

**Pattern**:
```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings from environment."""

    # Database
    database_url: str
    database_pool_size: int = 10

    # OpenAI
    openai_api_key: str
    openai_model: str = "text-embedding-ada-002"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Observability
    log_level: str = "INFO"
    enable_tracing: bool = False

    class Config:
        env_file = ".env"

# config/heuristics.py
"""
Heuristic parameters from HEURISTICS_CALIBRATION.md
All values are Phase 1 heuristics - require Phase 2 tuning
"""

REINFORCEMENT_BOOSTS = [0.15, 0.10, 0.05, 0.02]  # First, second, third, fourth+
CONSOLIDATION_BOOST = 0.05
DECAY_RATE_PER_DAY = 0.01
VALIDATION_THRESHOLD_DAYS = 90

FUZZY_MATCH_THRESHOLD = 0.70
FUZZY_MATCH_AUTO_RESOLVE = 0.85

RETRIEVAL_STRATEGY_WEIGHTS = {
    'factual_entity_focused': {
        'semantic_similarity': 0.25,
        'entity_overlap': 0.40,
        'temporal_relevance': 0.20,
        'importance': 0.10,
        'reinforcement': 0.05,
    },
    # ... other strategies
}
```

**Usage**:
```python
from config.settings import Settings
from config.heuristics import DECAY_RATE_PER_DAY

settings = Settings()  # Loads from .env

def compute_decay(days: int) -> float:
    return math.exp(-days * DECAY_RATE_PER_DAY)
```

### 7. Logging and Observability

**Structured logging** (JSON format for production):
```python
import structlog

logger = structlog.get_logger()

async def resolve_entity(mention: str, context: ResolutionContext) -> ResolutionResult:
    logger.info(
        "entity_resolution_started",
        mention=mention,
        user_id=context.user_id,
        session_id=context.session_id
    )

    try:
        result = await _resolve(mention, context)
        logger.info(
            "entity_resolution_completed",
            mention=mention,
            entity_id=result.entity_id,
            confidence=result.confidence,
            method=result.resolution_method
        )
        return result
    except AmbiguousEntityError as e:
        logger.warning(
            "entity_resolution_ambiguous",
            mention=mention,
            candidate_count=len(e.candidates)
        )
        raise
```

**Observability requirements**:
- **Phase 1**: Structured logging to stdout (JSON)
- **Phase 2**: OpenTelemetry tracing, metrics (Prometheus)
- **Phase 3**: Distributed tracing across services

### 8. Async Context Managers for Resources

**Pattern**:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session():
    """Async context manager for database session."""
    session = async_sessionmaker()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

# Usage in API
@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    async with get_db_session() as session:
        repo = EntityRepository(session)
        resolver = EntityResolver(repo, embedding_service)
        result = await resolver.resolve(request.message, ...)
        return result
```

---

## Testing Strategy

### Test Pyramid

```
       ┌─────────┐
       │   E2E   │  10% - Full API tests, slow (seconds)
       ├─────────┤
       │   Intg  │  20% - Repository, external service tests (100-500ms)
       ├─────────┤
       │  Unit   │  70% - Domain logic, pure functions (<10ms)
       └─────────┘
```

**Rationale**: Most value from fast unit tests, few slow E2E tests for critical paths.

### 1. Unit Tests (70% coverage minimum)

**Test domain logic in isolation**:
```python
# tests/unit/domain/test_entity_resolver.py
import pytest
from domain.services.entity_resolver import EntityResolver
from domain.value_objects import ResolutionContext, ResolutionResult
from tests.fixtures.factories import MockEntityRepository

@pytest.mark.asyncio
async def test_exact_match_returns_high_confidence():
    # Arrange
    mock_repo = MockEntityRepository()
    mock_repo.add_entity(entity_id="customer:acme_123", canonical_name="Acme Corporation")

    resolver = EntityResolver(entity_repo=mock_repo, embedding_service=None)
    context = ResolutionContext(user_id="user_1", session_id="session_1", ...)

    # Act
    result = await resolver.resolve(mention="Acme Corporation", context=context)

    # Assert
    assert result.entity_id == "customer:acme_123"
    assert result.confidence == 1.0
    assert result.method == "exact_match"

@pytest.mark.asyncio
async def test_ambiguous_entity_raises_exception():
    # Arrange
    mock_repo = MockEntityRepository()
    mock_repo.add_entity(entity_id="customer:acme_1", canonical_name="Acme Corp")
    mock_repo.add_entity(entity_id="customer:acme_2", canonical_name="Acme Industries")

    resolver = EntityResolver(entity_repo=mock_repo, embedding_service=None)
    context = ResolutionContext(...)

    # Act & Assert
    with pytest.raises(AmbiguousEntityError) as exc_info:
        await resolver.resolve(mention="Acme", context=context)

    assert len(exc_info.value.candidates) == 2
```

**Key practices**:
- Use mock repositories (in-memory, no DB)
- Test edge cases (empty results, multiple matches, invalid inputs)
- Fast (<10ms per test)

### 2. Integration Tests (20% coverage minimum)

**Test infrastructure adapters**:
```python
# tests/integration/test_entity_repository.py
import pytest
from infrastructure.database.repositories import PostgresEntityRepository
from domain.entities import CanonicalEntity
from tests.fixtures.database import test_db_session

@pytest.mark.asyncio
async def test_create_and_retrieve_entity(test_db_session):
    # Arrange
    repo = PostgresEntityRepository(test_db_session)
    entity = CanonicalEntity(
        entity_id="customer:test_123",
        entity_type="customer",
        canonical_name="Test Corp",
        properties={"industry": "technology"}
    )

    # Act
    created = await repo.create(entity)
    retrieved = await repo.get_by_id("customer:test_123")

    # Assert
    assert retrieved is not None
    assert retrieved.entity_id == "customer:test_123"
    assert retrieved.canonical_name == "Test Corp"
    assert retrieved.properties["industry"] == "technology"

@pytest.mark.asyncio
async def test_fuzzy_search_finds_similar_names(test_db_session):
    # Arrange
    repo = PostgresEntityRepository(test_db_session)
    await repo.create(CanonicalEntity(..., canonical_name="Acme Corporation"))
    await repo.create(CanonicalEntity(..., canonical_name="Acme Corp"))

    # Act
    results = await repo.fuzzy_search(query="Acme", threshold=0.7)

    # Assert
    assert len(results) == 2
    assert all("Acme" in r.canonical_name for r in results)
```

**Key practices**:
- Use test database (Docker PostgreSQL for CI/CD)
- Isolated transactions (rollback after each test)
- Test actual SQL queries, pgvector operations

### 3. End-to-End Tests (10% coverage minimum)

**Test critical API flows**:
```python
# tests/e2e/test_chat_flow.py
import pytest
from httpx import AsyncClient
from api.main import app

@pytest.mark.asyncio
async def test_chat_creates_memory_and_resolves_entities():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Act
        response = await client.post(
            "/api/v1/chat",
            json={
                "message": "Acme Corporation ordered 50 units yesterday",
                "user_id": "user_123",
                "session_id": "session_456"
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "response" in data
        assert "augmentation" in data
        assert "memories_created" in data
        assert "entities_resolved" in data

        # Check entity resolution
        entities = data["entities_resolved"]
        assert len(entities) >= 1
        assert any(e["mention"] == "Acme Corporation" for e in entities)

        # Check memory creation
        memories = data["memories_created"]
        assert len(memories) >= 1
        assert memories[0]["memory_type"] == "episodic"
```

**Key practices**:
- Test complete user flows (multi-step)
- Use test database
- Assert on API contracts from API_DESIGN.md

### 4. Property-Based Testing (Advanced)

**Use `hypothesis` for edge cases**:
```python
from hypothesis import given, strategies as st

@given(
    confidence=st.floats(min_value=0.0, max_value=1.0),
    days=st.integers(min_value=0, max_value=365),
    decay_rate=st.floats(min_value=0.001, max_value=0.1)
)
def test_decay_never_exceeds_original_confidence(confidence, days, decay_rate):
    """Property: Decayed confidence should never exceed original."""
    decayed = compute_effective_confidence(confidence, days, decay_rate)
    assert decayed <= confidence
    assert decayed >= 0.0
```

### 5. Test Fixtures and Factories

**Factory pattern for test data**:
```python
# tests/fixtures/factories.py
from dataclasses import dataclass
from typing import Optional
import uuid

@dataclass
class EntityFactory:
    """Factory for creating test entities."""

    @staticmethod
    def create_canonical_entity(
        entity_id: Optional[str] = None,
        entity_type: str = "customer",
        canonical_name: str = "Test Corp",
        **kwargs
    ) -> CanonicalEntity:
        return CanonicalEntity(
            entity_id=entity_id or f"{entity_type}:{uuid.uuid4().hex[:8]}",
            entity_type=entity_type,
            canonical_name=canonical_name,
            properties=kwargs.get('properties', {}),
            created_at=kwargs.get('created_at', datetime.utcnow())
        )

# Usage in tests
def test_entity_resolution():
    entity = EntityFactory.create_canonical_entity(canonical_name="Acme Corp")
    assert entity.canonical_name == "Acme Corp"
```

### Test Coverage Requirements

**Phase 1 Minimum Coverage**:
- **Domain layer**: 90% line coverage (business logic is critical)
- **API layer**: 80% line coverage (endpoints well-tested)
- **Infrastructure layer**: 70% line coverage (adapters tested via integration tests)

**Tools**:
- `pytest-cov` for coverage reporting
- `coverage.py` for HTML reports
- CI/CD fails if coverage drops below threshold

---

## Development Workflow

### 1. Branch Strategy (Git Flow Lite)

```
main (production)
  └── develop (integration)
       ├── feature/entity-resolution
       ├── feature/retrieval-service
       └── bugfix/confidence-decay
```

**Rules**:
- `main`: Production-ready code, tagged releases
- `develop`: Integration branch, all features merge here
- `feature/*`: Feature branches, merge to `develop` via PR
- `bugfix/*`: Bug fixes, merge to `develop` (hotfixes to `main`)

### 2. Commit Message Convention

**Format**: `<type>(<scope>): <subject>`

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `docs`: Documentation changes
- `chore`: Maintenance tasks

**Examples**:
```
feat(entity-resolution): implement five-stage resolution algorithm
fix(retrieval): correct temporal decay calculation
test(lifecycle): add tests for AGING state transition
docs(api): add phase tags to endpoint descriptions
```

### 3. Pull Request Process

**Required for all merges**:
1. **Create feature branch** from `develop`
2. **Write code + tests** (coverage must not decrease)
3. **Run local checks**:
   ```bash
   pytest                    # All tests pass
   mypy src/                # Type checks pass
   ruff check src/          # Linting passes
   ruff format src/         # Code formatted
   ```
4. **Create PR** with description:
   - What: Brief summary of changes
   - Why: Which design document / issue this addresses
   - How: Implementation approach
   - Testing: How you tested this
5. **Code review** (1-2 reviewers required)
6. **CI/CD checks pass** (automated)
7. **Merge to develop**

### 4. Code Review Checklist

**Reviewers must verify**:
- [ ] Code aligns with design documents (DESIGN.md, subsystem designs)
- [ ] Three Questions Framework applied (vision, cost, phase)
- [ ] Type hints present and correct
- [ ] Tests added (unit + integration where appropriate)
- [ ] Error handling present (domain exceptions, API error responses)
- [ ] Logging added for important operations
- [ ] Heuristic values use `config/heuristics.py` (not hardcoded)
- [ ] API changes match API_DESIGN.md contracts
- [ ] Performance acceptable (if DB query, check explain plan)

### 5. Continuous Integration (GitHub Actions)

**`.github/workflows/ci.yml`**:
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: ankane/pgvector:latest
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install

      - name: Run type checking
        run: poetry run mypy src/

      - name: Run linting
        run: poetry run ruff check src/

      - name: Run tests with coverage
        run: |
          poetry run pytest --cov=src --cov-report=xml --cov-fail-under=80

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### 6. Local Development Setup

**Quick start**:
```bash
# 1. Clone repository
git clone <repo-url>
cd memory-system

# 2. Install dependencies
poetry install

# 3. Start local PostgreSQL (Docker)
docker-compose up -d postgres

# 4. Run migrations
poetry run alembic upgrade head

# 5. Seed test data
poetry run python scripts/seed_data.py

# 6. Run development server
poetry run uvicorn src.api.main:app --reload

# 7. Run tests
poetry run pytest
```

**Docker Compose for local development**:
```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_USER: memoryuser
      POSTGRES_PASSWORD: memorypass
      POSTGRES_DB: memorydb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:  # Phase 2
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

---

## Quality Standards

### 1. Code Quality Metrics

**Automated checks** (enforced in CI/CD):

| Metric | Tool | Threshold | Phase |
|--------|------|-----------|-------|
| **Type Coverage** | `mypy --strict` | 100% (all functions typed) | Phase 1 |
| **Test Coverage** | `pytest-cov` | 80% minimum | Phase 1 |
| **Linting** | `ruff` | 0 errors, 0 warnings | Phase 1 |
| **Code Formatting** | `ruff format` | Auto-formatted | Phase 1 |
| **Cyclomatic Complexity** | `radon` | <10 per function | Phase 1 |
| **Security Scan** | `bandit` | 0 high/medium issues | Phase 1 |

### 2. Performance Standards

**Phase 1 targets** (from docs/design/RETRIEVAL_DESIGN.md):

| Operation | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| Semantic search (pgvector) | <30ms | <50ms | <100ms |
| Entity resolution | <20ms | <30ms | <50ms |
| Full retrieval pipeline | <60ms | <100ms | <150ms |
| Chat endpoint (end-to-end) | <200ms | <300ms | <500ms |

**Monitoring**:
- Use `pytest-benchmark` for performance regression tests
- Add latency logging to all service methods
- Phase 2: Prometheus metrics, Grafana dashboards

### 3. Security Standards

**Required practices**:
- **Input validation**: Pydantic models validate all API inputs
- **SQL injection prevention**: Use parameterized queries (SQLAlchemy ORM)
- **Authentication**: JWT tokens (API_DESIGN.md specification)
- **Secrets management**: Never commit secrets, use environment variables
- **Dependency scanning**: `pip-audit` in CI/CD
- **HTTPS only**: In production (TLS termination at load balancer)

**Phase 1 scope**:
- Basic authentication (JWT)
- Input validation
- SQL injection prevention

**Phase 2 scope**:
- Rate limiting (per user, per endpoint)
- Scope-based authorization
- Audit logging

### 4. Documentation Standards

**Required documentation**:

**1. Docstrings** (all public functions):
```python
def compute_retrieval_score(
    candidate: MemoryCandidate,
    query_embedding: np.ndarray,
    query_entities: List[str],
    strategy: str
) -> float:
    """
    Compute multi-signal relevance score for memory candidate.

    Implements the scoring algorithm from docs/design/RETRIEVAL_DESIGN.md.
    Uses strategy-specific weights from config/heuristics.py.

    Args:
        candidate: Memory candidate with embedding and metadata
        query_embedding: Query embedding vector (1536 dimensions)
        query_entities: List of entity IDs mentioned in query
        strategy: Retrieval strategy name (e.g., 'factual_entity_focused')

    Returns:
        Relevance score (0.0-1.0), higher is more relevant

    Raises:
        ValueError: If strategy not recognized

    Examples:
        >>> score = compute_retrieval_score(
        ...     candidate=memory_candidate,
        ...     query_embedding=embedding,
        ...     query_entities=["customer:acme_123"],
        ...     strategy="factual_entity_focused"
        ... )
        >>> assert 0.0 <= score <= 1.0
    """
    ...
```

**2. README.md** (top-level):
- Project overview
- Quick start guide
- Link to docs/
- Development setup

**3. API Documentation** (auto-generated):
- FastAPI automatically generates OpenAPI/Swagger docs
- Available at `/docs` endpoint

**4. Architecture Decision Records (ADRs)**:
- Document significant decisions (e.g., "Why PostgreSQL + pgvector?")
- Template:
  ```markdown
  # ADR-001: Use PostgreSQL with pgvector for Vector Storage

  ## Status
  Accepted

  ## Context
  Need to store and query 1536-dimensional embeddings efficiently.

  ## Decision
  Use PostgreSQL with pgvector extension.

  ## Consequences
  Pros: Single database, ACID guarantees, familiar tooling
  Cons: May not scale to 100M+ vectors (use Pinecone in Phase 3 if needed)
  ```

### 5. Error Handling Standards

**Levels of errors**:

**1. Domain exceptions** (expected business logic):
```python
raise AmbiguousEntityError(mention, candidates)  # Expected, handle gracefully
```

**2. Infrastructure exceptions** (transient, retry):
```python
raise DatabaseConnectionError()  # Retry up to 3 times
```

**3. Unhandled exceptions** (bugs, alert):
```python
# Unexpected error - log with full traceback, alert on-call
logger.exception("Unhandled error in entity resolution")
```

**API error responses** (from docs/design/API_DESIGN.md):
```python
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Entity with ID 'customer:invalid' not found",
    "details": {"entity_id": "customer:invalid"},
    "request_id": "req_a1b2c3d4",
    "documentation_url": "https://docs.../errors/entity-not-found"
  }
}
```

---

## Summary: Architecture Principles Compliance

### Three Questions Framework Applied

**1. Which vision principle does this serve?**
- Hexagonal architecture → **Testability, Maintainability**
- Async-first design → **Performance (I/O-bound operations)**
- Domain-driven design → **Ubiquitous language, Business logic clarity**
- Repository pattern → **Separation of concerns, Flexibility**

**2. Does this contribute enough to justify its cost?**
- Hexagonal architecture: **Yes** - Enables fast unit tests, prevents technical debt
- DDD Lite: **Yes** - Domain modeling valuable, full DDD would be over-engineering
- Dependency Injection: **Yes** - Testability and SOLID principles
- Property-based testing: **Phase 2** - Nice to have, not essential for Phase 1

**3. Is this the right phase for this complexity?**
- **Phase 1**: Hexagonal architecture, async, type hints, unit/integration tests
- **Phase 2**: Property-based testing, OpenTelemetry tracing, advanced performance optimization
- **Phase 3**: Event sourcing (if needed), CQRS (if needed)

### Alignment with DESIGN_PHILOSOPHY.md

- ✅ **Passive computation**: Domain logic computes on-demand, no background jobs
- ✅ **Explicit over implicit**: Type hints, clear interfaces, structured logging
- ✅ **Phasing**: Architecture supports Phase 1 essential features, Phase 2/3 extensions
- ✅ **Justification**: Every architectural decision answers Three Questions

### Production Readiness

This architecture is **ready for Phase 1 implementation**:
- Clear structure (hexagonal, DDD lite)
- Testing strategy (70% unit, 20% integration, 10% E2E)
- Development workflow (Git flow, PR process, CI/CD)
- Quality standards (coverage, performance, security)

**Next step**: Begin implementation following this architecture.
