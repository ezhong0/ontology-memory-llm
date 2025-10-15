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
    """Test database URL (isolated from production)"""
    return "postgresql+asyncpg://test:test@localhost:5432/memory_test"


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

    Each test gets a clean database via transaction rollback.
    """
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        # Begin transaction
        async with session.begin():
            yield session
            # Rollback happens automatically after yield


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
# API Client Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def api_client(test_db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client for E2E API testing.

    Uses test database session for isolation.
    """
    # from src.api.main import app

    # Override database dependency
    # async def override_get_db():
    #     yield test_db_session
    #
    # app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(base_url="http://test") as client:
        yield client

    # Cleanup
    # app.dependency_overrides.clear()


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
# Assertion Helpers
# ============================================================================

@pytest.fixture
def assert_confidence_in_range():
    """Helper to assert confidence is in valid range"""
    def _assert(confidence: float, min_val: float = 0.0, max_val: float = 0.95):
        assert min_val <= confidence <= max_val, \
            f"Confidence {confidence} not in range [{min_val}, {max_val}]"
    return _assert


@pytest.fixture
def assert_valid_entity_id():
    """Helper to assert entity_id follows format"""
    import re

    def _assert(entity_id: str):
        pattern = r'^[a-z_]+:[a-zA-Z0-9_-]+$'
        assert re.match(pattern, entity_id), \
            f"Invalid entity_id format: {entity_id} (expected: 'type:identifier')"
    return _assert


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
