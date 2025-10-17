"""
Pytest configuration and global fixtures.

This file contains shared fixtures used across all test types:
- Database session management
- Mock services
- Test data factories
- API client setup
"""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient

# Import application components (will exist after implementation)
# from src.api.main import app
# from src.infrastructure.database.session import Base
# from src.config.settings import Settings


# ============================================================================
# Test Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no I/O)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (DB, external services)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (full API scenarios)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (may use real LLM API)"
    )
    config.addinivalue_line(
        "markers", "benchmark: Performance benchmark tests"
    )
    config.addinivalue_line(
        "markers", "philosophy: Vision principle validation tests"
    )


# ============================================================================
# Async Event Loop Fixture
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Test database URL (uses dedicated test database for complete isolation)"""
    # Use dedicated test database (port 5433) to avoid interference with demo/dev database
    # Tests run in transactions with rollback, but separate DB provides additional isolation
    return "postgresql+asyncpg://testuser:testpass@localhost:5433/testdb"


@pytest_asyncio.fixture(scope="function")
async def test_db_engine(test_database_url):
    """Create test database engine"""
    engine = create_async_engine(
        test_database_url,
        echo=False,
        pool_pre_ping=True
    )

    # Create all tables
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create isolated database session for each test.

    Uses TRUNCATE for cleanup since we're on a dedicated test database.
    This is simpler and more reliable than transaction rollbacks for E2E tests.
    """
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        # Clean up before test
        await session.execute(text("TRUNCATE TABLE domain.payments, domain.invoices, domain.work_orders, domain.sales_orders, domain.tasks, domain.customers CASCADE"))
        await session.execute(text("TRUNCATE TABLE app.episodic_memories, app.semantic_memories, app.entity_aliases, app.canonical_entities CASCADE"))
        await session.commit()

        yield session

        # Clean up after test
        await session.execute(text("TRUNCATE TABLE domain.payments, domain.invoices, domain.work_orders, domain.sales_orders, domain.tasks, domain.customers CASCADE"))
        await session.execute(text("TRUNCATE TABLE app.episodic_memories, app.semantic_memories, app.entity_aliases, app.canonical_entities CASCADE"))
        await session.commit()


@pytest_asyncio.fixture(scope="function")
async def test_db_with_seed_data(test_db_session):
    """Database with common seed data for testing"""
    # Seed system_config
    await test_db_session.execute("""
        INSERT INTO app.system_config (config_key, config_value) VALUES
        ('multi_signal_weights', '{"semantic": 0.4, "entity": 0.25, "recency": 0.2, "importance": 0.1, "reinforcement": 0.05}'),
        ('decay', '{"default_rate_per_day": 0.01, "validation_threshold_days": 90}'),
        ('confidence_thresholds', '{"high": 0.85, "medium": 0.6, "low": 0.4}')
    """)

    # Seed test entities
    await test_db_session.execute("""
        INSERT INTO app.canonical_entities (entity_id, entity_type, canonical_name, external_ref, properties) VALUES
        ('customer:gai_123', 'customer', 'Gai Media', '{"table": "domain.customers", "id": "gai_123"}', '{"industry": "Entertainment"}'),
        ('customer:tc_456', 'customer', 'TC Boiler', '{"table": "domain.customers", "id": "tc_456"}', '{"industry": "Industrial"}')
    """)

    await test_db_session.commit()

    return test_db_session


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_entity_repository():
    """In-memory entity repository for fast unit tests"""
    from tests.fixtures.mock_services import MockEntityRepository
    return MockEntityRepository()


@pytest.fixture
def mock_llm_service():
    """Mock LLM service with deterministic responses"""
    from tests.fixtures.mock_services import MockLLMService
    return MockLLMService()


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing"""
    from tests.fixtures.mock_services import MockEmbeddingService
    return MockEmbeddingService()


@pytest.fixture
def mock_domain_db_service():
    """Mock domain database service"""
    from tests.fixtures.mock_services import MockDomainDBService
    return MockDomainDBService()


# ============================================================================
# E2E Test Fixtures (NEW - for scenario testing)
# ============================================================================

@pytest_asyncio.fixture
async def scenario_loader(test_db_session) -> "ScenarioLoaderService":
    """
    Demo scenario loader for E2E tests.

    IMPORTANT: E2E tests should use this instead of domain_seeder to ensure
    tests validate the SAME code path that demo scenarios use.

    Usage:
        await scenario_loader.load_scenario(scenario_id=1)
        # Now test behavior with scenario data loaded

    Benefits:
    - ✅ Tests passing = demo scenarios work
    - ✅ Single source of truth (ScenarioRegistry)
    - ✅ No duplication between tests and demo data
    - ✅ ScenarioLoaderService gets test coverage
    """
    from src.demo.services.scenario_loader import ScenarioLoaderService
    return ScenarioLoaderService(test_db_session, user_id="demo-user")


@pytest_asyncio.fixture
async def domain_seeder(test_db_session) -> "DomainSeeder":
    """
    Domain database seeder for E2E tests.

    DEPRECATED: Use `scenario_loader` fixture instead for E2E tests.
    This ensures tests validate the same code path as demo scenarios.

    Only use this for:
    - Unit tests that need specific edge cases
    - Tests that don't correspond to demo scenarios

    Provides helper to populate domain.* tables with test data.

    Usage:
        await domain_seeder.seed({
            "customers": [{"name": "Kai Media", "industry": "Entertainment"}],
            "invoices": [{"invoice_number": "INV-1009", "amount": 1200.00}]
        })
    """
    from tests.fixtures.domain_seeder import DomainSeeder
    return DomainSeeder(test_db_session)


@pytest_asyncio.fixture
async def memory_factory(test_db_session) -> "MemoryFactory":
    """
    Memory factory for E2E tests.

    Provides helpers to create memories programmatically (bypass chat pipeline).

    Usage:
        await memory_factory.create_semantic_memory(
            user_id="test_user",
            subject_entity_id="customer:kai_123",
            predicate="prefers_delivery_day",
            object_value={"day": "Friday"}
        )
    """
    from tests.fixtures.memory_factory import MemoryFactory
    return MemoryFactory(test_db_session)


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def api_client(test_db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client for E2E API testing.

    Uses test database session for isolation.
    """
    from src.api.main import app
    from src.api.dependencies import get_db

    # Override database dependency to use test session
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_chat_event():
    """Sample chat event for testing"""
    return {
        "session_id": "session_123",
        "user_id": "test_user",
        "role": "user",
        "content": "What's the status of Gai Media's order?",
        "content_hash": "abc123",
        "created_at": datetime.utcnow()
    }


@pytest.fixture
def sample_canonical_entity():
    """Sample canonical entity"""
    return {
        "entity_id": "customer:test_123",
        "entity_type": "customer",
        "canonical_name": "Test Corporation",
        "external_ref": {"table": "domain.customers", "id": "test_123"},
        "properties": {"industry": "Technology"},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


@pytest.fixture
def sample_semantic_memory():
    """Sample semantic memory"""
    return {
        "user_id": "test_user",
        "subject_entity_id": "customer:test_123",
        "predicate": "delivery_preference",
        "predicate_type": "preference",
        "object_value": {"type": "day_of_week", "value": "Friday"},
        "confidence": 0.75,
        "confidence_factors": {"base": 0.7, "reinforcement": 0.05},
        "reinforcement_count": 2,
        "last_validated_at": datetime.utcnow() - timedelta(days=10),
        "source_type": "episodic",
        "status": "active",
        "importance": 0.6,
        "created_at": datetime.utcnow() - timedelta(days=30),
        "updated_at": datetime.utcnow()
    }


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def test_db_with_1000_memories(test_db_session):
    """
    Database with 1000 memories for performance testing.

    Used to test pgvector search performance at realistic scale.
    """
    import numpy as np

    for i in range(1000):
        embedding = np.random.rand(1536).tolist()

        await test_db_session.execute("""
            INSERT INTO app.semantic_memories
            (user_id, subject_entity_id, predicate, predicate_type, object_value,
             confidence, status, importance, embedding)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
            "test_user",
            f"customer:test_{i % 100}",
            "test_predicate",
            "test",
            f'{{"value": "test_{i}"}}',
            0.7,
            "active",
            0.5,
            embedding
        )

    await test_db_session.commit()
    return test_db_session


# ============================================================================
# Time Manipulation Fixtures
# ============================================================================

@pytest.fixture
def freeze_time(monkeypatch):
    """
    Freeze time for testing temporal behavior.

    Usage:
        def test_something(freeze_time):
            freeze_time(datetime(2025, 9, 15, 12, 0, 0))
            # All datetime.utcnow() calls return frozen time
    """
    from datetime import datetime

    frozen_time = None

    def _freeze(dt: datetime):
        nonlocal frozen_time
        frozen_time = dt

        def mock_utcnow():
            return frozen_time

        monkeypatch.setattr("datetime.datetime.utcnow", mock_utcnow)

    return _freeze


# ============================================================================
# Assertion Helpers (from test_helpers.py)
# ============================================================================

@pytest.fixture
def assert_confidence_in_range():
    """Helper to assert confidence is in valid range"""
    from tests.fixtures.test_helpers import assert_confidence_in_range
    return assert_confidence_in_range


@pytest.fixture
def assert_valid_entity_id():
    """Helper to assert entity_id follows format"""
    from tests.fixtures.test_helpers import assert_valid_entity_id
    return assert_valid_entity_id


@pytest.fixture
def api_response_validator():
    """Validator for API response structure"""
    from tests.fixtures.test_helpers import APIResponseValidator
    return APIResponseValidator()


@pytest.fixture
def time_helper():
    """Helper for time-related operations"""
    from tests.fixtures.test_helpers import TimeHelper
    return TimeHelper()


# ============================================================================
# Cleanup Helpers
# ============================================================================

@pytest.fixture(autouse=True)
async def cleanup_test_artifacts():
    """
    Automatically cleanup test artifacts after each test.

    Ensures tests don't leave behind temporary files, connections, etc.
    """
    yield

    # Cleanup code runs after test completes
    # e.g., close file handles, clear caches
    pass
