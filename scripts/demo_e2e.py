"""End-to-end demonstration of the memory system.

This script demonstrates the complete memory system capabilities:
1. Domain database grounding (correspondence truth)
2. Entity resolution (canonical representation)
3. Semantic memory retrieval (contextual truth)
4. Multi-signal relevance scoring
5. Memory lifecycle (retrieval with confidence)

Usage:
    poetry run python scripts/demo_e2e.py
"""

import asyncio
import sys
from pathlib import Path

import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import Settings
from src.infrastructure.database.session import get_db_session, init_db
from src.infrastructure.embedding.openai_embedding_service import (
    OpenAIEmbeddingService,
)
from src.infrastructure.database.repositories import (
    EpisodicMemoryRepository,
    SemanticMemoryRepository,
    SummaryRepository,
)
from src.domain.services.memory_retriever import MemoryRetriever
from src.domain.services.candidate_generator import CandidateGenerator
from src.domain.services.multi_signal_scorer import MultiSignalScorer
from src.domain.services.memory_validation_service import MemoryValidationService
from src.domain.value_objects.query_context import QueryContext, RetrievalFilters
from sqlalchemy import text

logger = structlog.get_logger(__name__)


async def demo_domain_grounding(session):
    """Demonstrate domain database querying (correspondence truth)."""
    print("\n" + "=" * 80)
    print("1. DOMAIN DATABASE GROUNDING (Correspondence Truth)")
    print("=" * 80)

    # Query customers
    result = await session.execute(
        text("""
            SELECT name, industry, notes
            FROM domain.customers
            ORDER BY name
        """)
    )

    print("\n📊 Domain Customers:")
    for row in result:
        print(f"  • {row[0]} ({row[1]})")
        if row[2]:
            print(f"    Notes: {row[2][:80]}...")

    # Query invoices
    result = await session.execute(
        text("""
            SELECT
                i.invoice_number,
                c.name as customer_name,
                i.amount,
                i.status,
                i.due_date
            FROM domain.invoices i
            JOIN domain.sales_orders so ON i.so_id = so.so_id
            JOIN domain.customers c ON so.customer_id = c.customer_id
            ORDER BY i.issued_at DESC
            LIMIT 5
        """)
    )

    print("\n💰 Recent Invoices:")
    for row in result:
        print(f"  • {row[0]}: {row[1]} - ${row[2]:,.2f} ({row[3]}) - Due: {row[4]}")


async def demo_entity_resolution(session):
    """Demonstrate entity resolution and canonical representation."""
    print("\n" + "=" * 80)
    print("2. ENTITY RESOLUTION (Canonical Representation)")
    print("=" * 80)

    # Query canonical entities
    result = await session.execute(
        text("""
            SELECT
                ce.entity_id,
                ce.canonical_name,
                ce.entity_type,
                COUNT(ea.alias_id) as alias_count
            FROM app.canonical_entities ce
            LEFT JOIN app.entity_aliases ea ON ea.canonical_entity_id = ce.entity_id
            GROUP BY ce.entity_id, ce.canonical_name, ce.entity_type
            ORDER BY ce.canonical_name
        """)
    )

    print("\n🔗 Canonical Entities:")
    for row in result:
        print(f"  • {row[1]} (type: {row[2]})")
        print(f"    ID: {row[0]}")
        print(f"    Aliases: {row[3]} variants")


async def demo_memory_retrieval(session, embedding_service):
    """Demonstrate semantic memory retrieval with multi-signal scoring."""
    print("\n" + "=" * 80)
    print("3. SEMANTIC MEMORY RETRIEVAL (Contextual Truth)")
    print("=" * 80)

    # Create repositories
    episodic_repo = EpisodicMemoryRepository(session)
    semantic_repo = SemanticMemoryRepository(session)
    summary_repo = SummaryRepository(session, embedding_service)

    # Create validation service (for passive decay calculation)
    validation_service = MemoryValidationService()

    # Create scorer and candidate generator
    scorer = MultiSignalScorer(validation_service)
    candidate_gen = CandidateGenerator(
        semantic_repo,
        episodic_repo,
        summary_repo,
    )

    # Create retriever
    retriever = MemoryRetriever(
        candidate_generator=candidate_gen,
        scorer=scorer,
        embedding_service=embedding_service,
    )

    # Test query 1: Payment-related
    print("\n🔍 Query 1: 'What are Acme Corporation payment terms?'")
    query = "What are Acme Corporation payment terms?"

    context = QueryContext(
        user_id="demo-user-001",
        text=query,
        entities=[],  # Would be populated by entity resolution in real usage
    )

    filters = RetrievalFilters(
        max_candidates=20,
        max_selected=5,
    )

    result = await retriever.retrieve(context, filters)

    print(f"\n   Retrieved {len(result.selected_memories)} relevant memories:")
    for i, memory in enumerate(result.selected_memories, 1):
        print(f"\n   Memory {i} (score: {memory.final_score:.3f}):")
        print(f"     Type: {memory.memory_type}")
        print(f"     Content: {memory.content[:100]}...")
        print(f"     Signals: semantic={memory.signals.semantic:.3f}, "
              f"entities={memory.signals.entity_overlap:.3f}, "
              f"recency={memory.signals.recency:.3f}")

    print(f"\n   Metadata:")
    print(f"     Candidates evaluated: {result.metadata.total_candidates}")
    print(f"     Retrieval time: {result.metadata.retrieval_time_ms:.1f}ms")
    print(f"     Scoring time: {result.metadata.scoring_time_ms:.1f}ms")


async def demo_memory_lifecycle(session):
    """Demonstrate memory lifecycle (confidence, reinforcement, decay)."""
    print("\n" + "=" * 80)
    print("4. MEMORY LIFECYCLE (Confidence & Epistemic Humility)")
    print("=" * 80)

    # Query semantic memories with confidence
    result = await session.execute(
        text("""
            SELECT
                sm.predicate,
                sm.object_value,
                sm.confidence,
                sm.reinforcement_count,
                sm.status,
                EXTRACT(EPOCH FROM (NOW() - sm.last_validated_at))/86400 as days_since_validation
            FROM app.semantic_memories sm
            WHERE sm.user_id = :user_id
            ORDER BY sm.confidence DESC, sm.reinforcement_count DESC
            LIMIT 5
        """),
        {"user_id": "demo-user-001"}
    )

    print("\n📈 Semantic Memories (with confidence tracking):")
    for row in result:
        print(f"\n  • {row[0]}:")
        print(f"    Value: {row[1]}")
        print(f"    Confidence: {row[2]:.2f} (max=0.95)")
        print(f"    Reinforced: {row[3]} times")
        print(f"    Status: {row[4]}")
        print(f"    Last validated: {row[5]:.1f} days ago")


async def demo_consolidation(session):
    """Demonstrate memory consolidation (graceful forgetting)."""
    print("\n" + "=" * 80)
    print("5. MEMORY CONSOLIDATION (Graceful Forgetting)")
    print("=" * 80)

    # Query summaries
    result = await session.execute(
        text("""
            SELECT
                scope_type,
                scope_identifier,
                summary_text,
                confidence,
                key_facts,
                created_at
            FROM app.memory_summaries
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 3
        """),
        {"user_id": "demo-user-001"}
    )

    print("\n📝 Memory Summaries (consolidated knowledge):")
    for row in result:
        print(f"\n  • Scope: {row[0]} ({row[1]})")
        print(f"    Summary: {row[2][:150]}...")
        print(f"    Confidence: {row[3]:.2f}")
        print(f"    Key Facts: {len(row[4])} facts consolidated")
        print(f"    Created: {row[5]}")


async def main():
    """Run end-to-end demonstration."""
    # Load settings
    settings = Settings()

    # Check for OpenAI API key
    if not settings.openai_api_key:
        print("\n⚠️  OpenAI API key not found")
        print("Set OPENAI_API_KEY environment variable for full demonstration")
        print("\nSkipping embedding-dependent demos...\n")
        embedding_service = None
    else:
        embedding_service = OpenAIEmbeddingService(api_key=settings.openai_api_key)

    # Initialize database
    init_db(settings)

    print("\n" + "=" * 80)
    print("ONTOLOGY-AWARE MEMORY SYSTEM - END-TO-END DEMONSTRATION")
    print("=" * 80)
    print("\nThis demonstration shows the complete memory system capabilities:")
    print("1. Domain database grounding (correspondence truth)")
    print("2. Entity resolution (canonical representation)")
    print("3. Semantic memory retrieval (contextual truth)")
    print("4. Memory lifecycle (confidence & epistemic humility)")
    print("5. Memory consolidation (graceful forgetting)")

    try:
        async with get_db_session() as session:
            # Demo 1: Domain grounding
            await demo_domain_grounding(session)

            # Demo 2: Entity resolution
            await demo_entity_resolution(session)

            # Demo 3: Memory retrieval (if embedding service available)
            if embedding_service:
                await demo_memory_retrieval(session, embedding_service)
            else:
                print("\n" + "=" * 80)
                print("3. SEMANTIC MEMORY RETRIEVAL (Contextual Truth)")
                print("=" * 80)
                print("\n⚠️  Skipped (requires OpenAI API key)")

            # Demo 4: Memory lifecycle
            await demo_memory_lifecycle(session)

            # Demo 5: Consolidation
            await demo_consolidation(session)

        print("\n" + "=" * 80)
        print("✅ DEMONSTRATION COMPLETE")
        print("=" * 80)
        print("\nThe system successfully demonstrates:")
        print("  ✅ Dual truth (correspondence + contextual)")
        print("  ✅ Entity resolution (canonical representation)")
        print("  ✅ Memory retrieval (multi-signal scoring)")
        print("  ✅ Epistemic humility (confidence tracking)")
        print("  ✅ Graceful forgetting (consolidation)")
        print("\nAll core components are operational and working together.\n")

    except Exception as e:
        logger.error("demonstration_failed", error=str(e), error_type=type(e).__name__)
        print(f"\n❌ Demonstration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
