"""
Performance Tests: Latency Benchmarks

Tests P95 latency targets from PHASE1_ROADMAP.md:
- Entity resolution (fast path): P95 < 50ms
- Semantic search (pgvector): P95 < 50ms
- Full retrieval: P95 < 100ms
- Chat endpoint: P95 < 800ms

Uses pytest-benchmark for statistical analysis.
"""
import pytest
import asyncio
import time
import numpy as np
from typing import List


# ============================================================================
# Latency Measurement Helpers
# ============================================================================

class LatencyMeasurement:
    """Helper for measuring and analyzing latency."""

    def __init__(self):
        self.measurements: List[float] = []

    def record(self, duration_ms: float):
        """Record a latency measurement in milliseconds."""
        self.measurements.append(duration_ms)

    def get_p95(self) -> float:
        """Get P95 latency."""
        if not self.measurements:
            return 0.0
        return np.percentile(self.measurements, 95)

    def get_p50(self) -> float:
        """Get median (P50) latency."""
        if not self.measurements:
            return 0.0
        return np.percentile(self.measurements, 50)

    def get_p99(self) -> float:
        """Get P99 latency."""
        if not self.measurements:
            return 0.0
        return np.percentile(self.measurements, 99)

    def get_mean(self) -> float:
        """Get mean latency."""
        if not self.measurements:
            return 0.0
        return np.mean(self.measurements)

    def summary(self) -> dict:
        """Get summary statistics."""
        return {
            "count": len(self.measurements),
            "mean": self.get_mean(),
            "p50": self.get_p50(),
            "p95": self.get_p95(),
            "p99": self.get_p99(),
            "min": min(self.measurements) if self.measurements else 0.0,
            "max": max(self.measurements) if self.measurements else 0.0,
        }


async def measure_async_latency(func, *args, **kwargs) -> float:
    """
    Measure latency of async function in milliseconds.

    Args:
        func: Async function to measure
        *args, **kwargs: Arguments to pass to function

    Returns:
        Duration in milliseconds
    """
    start = time.perf_counter()
    await func(*args, **kwargs)
    end = time.perf_counter()
    return (end - start) * 1000  # Convert to ms


# ============================================================================
# Entity Resolution Latency Tests
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.skip(reason="TODO: Implement after entity resolution ready")
class TestEntityResolutionLatency:
    """Test entity resolution latency targets."""

    @pytest.mark.asyncio
    async def test_exact_match_under_50ms_p95(self, mock_entity_repository):
        """
        TARGET: Entity resolution (exact match) P95 < 50ms

        Fast path should be near-instant (database index lookup).
        """
        from tests.fixtures.factories import EntityFactory

        # Setup: Add 100 entities
        for i in range(100):
            entity = EntityFactory.create(canonical_name=f"Company {i}")
            mock_entity_repository.add_entity(entity)

        # Measure latency over 100 iterations
        measurements = LatencyMeasurement()

        for i in range(100):
            # TODO: Replace with actual EntityResolver
            async def mock_resolve():
                await asyncio.sleep(0.001)  # 1ms mock
                return mock_entity_repository.get_by_name(f"Company {i}")

            latency_ms = await measure_async_latency(mock_resolve)
            measurements.record(latency_ms)

        # Assert P95 target
        p95 = measurements.get_p95()
        print(f"\nEntity Resolution (Exact Match) Latency:")
        print(f"  P50: {measurements.get_p50():.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {measurements.get_p99():.2f}ms")

        assert p95 < 50, \
            f"Entity resolution too slow: P95={p95:.2f}ms > 50ms target"

    @pytest.mark.asyncio
    async def test_fuzzy_match_reasonable_latency(self, mock_entity_repository):
        """
        TARGET: Fuzzy match should complete within reasonable time.

        Fuzzy match is slower than exact (requires pg_trgm scan), but should
        still be fast enough for interactive use (< 100ms P95).
        """
        from tests.fixtures.factories import EntityFactory

        # Setup: Add 100 entities
        for i in range(100):
            entity = EntityFactory.create(canonical_name=f"Company {i}")
            mock_entity_repository.add_entity(entity)

        measurements = LatencyMeasurement()

        for i in range(50):  # Fewer iterations (fuzzy is slower)
            async def mock_fuzzy_resolve():
                await asyncio.sleep(0.005)  # 5ms mock
                return await mock_entity_repository.fuzzy_search(f"Compny {i}", 0.7)

            latency_ms = await measure_async_latency(mock_fuzzy_resolve)
            measurements.record(latency_ms)

        p95 = measurements.get_p95()
        print(f"\nEntity Resolution (Fuzzy Match) Latency:")
        print(f"  P95: {p95:.2f}ms")

        assert p95 < 100, \
            f"Fuzzy match too slow: P95={p95:.2f}ms > 100ms target"


# ============================================================================
# Semantic Search Latency Tests
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.integration
@pytest.mark.skip(reason="TODO: Implement after memory repository ready")
class TestSemanticSearchLatency:
    """Test pgvector semantic search latency targets."""

    @pytest.mark.asyncio
    async def test_semantic_search_under_50ms_p95(self, test_db_with_1000_memories):
        """
        TARGET: Semantic search P95 < 50ms at 1000 memories

        Uses pgvector with IVFFlat index for fast approximate nearest neighbor search.
        """
        # TODO: Implement with actual MemoryRepository
        # repo = PostgresMemoryRepository(test_db_with_1000_memories)

        measurements = LatencyMeasurement()

        for i in range(100):
            query_embedding = np.random.rand(1536)

            async def mock_semantic_search():
                await asyncio.sleep(0.02)  # 20ms mock
                # return await repo.semantic_search(query_embedding, limit=50)
                pass

            latency_ms = await measure_async_latency(mock_semantic_search)
            measurements.record(latency_ms)

        p95 = measurements.get_p95()
        print(f"\nSemantic Search Latency (1000 memories):")
        print(f"  P50: {measurements.get_p50():.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {measurements.get_p99():.2f}ms")

        assert p95 < 50, \
            f"Semantic search too slow: P95={p95:.2f}ms > 50ms target"


# ============================================================================
# Full Retrieval Latency Tests
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.skip(reason="TODO: Implement after retrieval service ready")
class TestRetrievalLatency:
    """Test full memory retrieval latency targets."""

    @pytest.mark.asyncio
    async def test_full_retrieval_under_100ms_p95(self):
        """
        TARGET: Full retrieval (multi-signal scoring) P95 < 100ms

        Includes:
        1. Semantic search (50 candidates)
        2. Entity-based retrieval (30 candidates)
        3. Temporal filtering
        4. Multi-signal scoring
        5. Top-k selection
        """
        measurements = LatencyMeasurement()

        for i in range(50):
            async def mock_full_retrieval():
                # Mock: Semantic search (20ms) + entity retrieval (10ms) + scoring (5ms)
                await asyncio.sleep(0.035)  # 35ms mock
                pass

            latency_ms = await measure_async_latency(mock_full_retrieval)
            measurements.record(latency_ms)

        p95 = measurements.get_p95()
        print(f"\nFull Retrieval Latency:")
        print(f"  P95: {p95:.2f}ms")

        assert p95 < 100, \
            f"Full retrieval too slow: P95={p95:.2f}ms > 100ms target"


# ============================================================================
# End-to-End Chat Latency Tests
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.e2e
@pytest.mark.skip(reason="TODO: Implement after chat API ready")
class TestChatEndpointLatency:
    """Test full chat endpoint latency targets."""

    @pytest.mark.asyncio
    async def test_chat_endpoint_under_800ms_p95(self, api_client):
        """
        TARGET: Chat endpoint P95 < 800ms

        Full pipeline:
        1. Entity resolution (50ms)
        2. Domain DB query (50ms)
        3. Memory retrieval (100ms)
        4. LLM generation (500ms - dominates)
        5. Memory creation (50ms)
        Total budget: ~750ms average
        """
        measurements = LatencyMeasurement()

        for i in range(20):  # Fewer iterations (expensive)
            async def mock_chat():
                # Mock full pipeline
                await asyncio.sleep(0.600)  # 600ms mock
                # response = await api_client.post("/api/v1/chat", json={
                #     "user_id": "test_user",
                #     "message": f"Test query {i}"
                # })
                pass

            latency_ms = await measure_async_latency(mock_chat)
            measurements.record(latency_ms)

        p95 = measurements.get_p95()
        print(f"\nChat Endpoint Latency:")
        print(f"  Mean: {measurements.get_mean():.2f}ms")
        print(f"  P50: {measurements.get_p50():.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {measurements.get_p99():.2f}ms")

        assert p95 < 800, \
            f"Chat endpoint too slow: P95={p95:.2f}ms > 800ms target"


# ============================================================================
# Benchmark Comparison Tests
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.skip(reason="TODO: Implement after services ready")
def test_latency_budget_allocation():
    """
    Test that latency budget is correctly allocated across components.

    Chat endpoint budget (800ms P95):
    - Entity resolution: 50ms (6%)
    - Domain DB query: 50ms (6%)
    - Memory retrieval: 100ms (12%)
    - LLM generation: 500ms (62%)
    - Memory creation: 50ms (6%)
    - Buffer: 50ms (6%)
    """
    budget = {
        "entity_resolution": 50,
        "domain_db": 50,
        "retrieval": 100,
        "llm_generation": 500,
        "memory_creation": 50,
        "buffer": 50,
    }

    total_budget = sum(budget.values())
    assert total_budget == 800, f"Budget doesn't sum to target: {total_budget}ms"

    # LLM generation should dominate (>60% of time)
    llm_percentage = (budget["llm_generation"] / total_budget) * 100
    assert llm_percentage > 60, \
        f"LLM should dominate latency budget: {llm_percentage:.1f}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
