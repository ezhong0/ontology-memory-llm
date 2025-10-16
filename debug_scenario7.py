"""Debug script for Scenario 7 retrieval issue.

This script simulates the Scenario 7 flow and inspects the database state
to understand why memories aren't being retrieved.
"""

import asyncio
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import necessary components
from src.config.settings import Settings
from src.infrastructure.database.models import SemanticMemory as SemanticMemoryModel
from src.infrastructure.database.repositories.semantic_memory_repository import SemanticMemoryRepository
from src.infrastructure.services.openai_embedding_service import OpenAIEmbeddingService

settings = Settings()


async def main():
    """Debug Scenario 7 retrieval."""
    # Create database connection
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Initialize services
        embedding_service = OpenAIEmbeddingService(api_key=settings.openai_api_key)
        semantic_repo = SemanticMemoryRepository(session)

        print("=" * 80)
        print("SCENARIO 7 DEBUG: Memory Retrieval Investigation")
        print("=" * 80)

        # Query 1: Check all semantic memories in database
        print("\n1. Querying all semantic memories for user 'ops_manager'...")
        stmt = select(SemanticMemoryModel).where(
            SemanticMemoryModel.user_id == "ops_manager"
        )
        result = await session.execute(stmt)
        all_memories = result.scalars().all()

        print(f"   Found {len(all_memories)} memories")
        for mem in all_memories:
            print(f"   - Memory {mem.memory_id}: {mem.subject_entity_id} | {mem.predicate} | {mem.object_value}")
            print(f"     Status: {mem.status}, Confidence: {mem.confidence:.2f}")
            print(f"     Has embedding: {mem.embedding is not None}")

        # Query 2: Check memories with delivery_preference predicate
        print("\n2. Checking memories with 'delivery_preference' predicate...")
        stmt = select(SemanticMemoryModel).where(
            SemanticMemoryModel.user_id == "ops_manager",
            SemanticMemoryModel.predicate == "delivery_preference"
        )
        result = await session.execute(stmt)
        delivery_memories = result.scalars().all()

        print(f"   Found {len(delivery_memories)} delivery preference memories")
        for mem in delivery_memories:
            print(f"   - Memory {mem.memory_id}:")
            print(f"     Subject: {mem.subject_entity_id}")
            print(f"     Object: {mem.object_value}")
            print(f"     Status: {mem.status}")
            print(f"     Confidence: {mem.confidence:.2f}")
            print(f"     Has embedding: {mem.embedding is not None}")
            if mem.embedding:
                print(f"     Embedding length: {len(mem.embedding)}")

        # Query 3: Test vector similarity search
        print("\n3. Testing vector similarity search with query...")
        query_text = "What day should we deliver to Kai Media?"
        print(f"   Query: '{query_text}'")

        query_embedding = await embedding_service.generate_embedding(query_text)
        print(f"   Query embedding generated: {len(query_embedding)} dimensions")

        # Use repository's find_similar method
        similar_memories = await semantic_repo.find_similar(
            query_embedding=query_embedding,
            user_id="ops_manager",
            limit=50,
            min_confidence=0.3
        )

        print(f"   Vector search returned {len(similar_memories)} memories")
        for mem, similarity in similar_memories:
            print(f"   - Memory {mem.memory_id}: {mem.predicate} = {mem.object_value}")
            print(f"     Similarity: {similarity:.4f}, Confidence: {mem.confidence:.2f}")

        # Query 4: Check what the embedding text was for delivery memories
        print("\n4. Reconstructing embedding text for delivery memories...")
        for mem in delivery_memories:
            # This is how embeddings are created in extract_semantics.py
            embedding_text = f"{mem.subject_entity_id} {mem.predicate} {mem.object_value}"
            print(f"   Memory {mem.memory_id} embedding text:")
            print(f"   '{embedding_text}'")

        # Query 5: Generate embedding for a more natural representation
        print("\n5. Testing alternative embedding strategies...")
        if delivery_memories:
            mem = delivery_memories[0]
            obj_value = mem.object_value.get("value", str(mem.object_value))

            # Current strategy (structured)
            structured_text = f"{mem.subject_entity_id} {mem.predicate} {mem.object_value}"
            structured_embedding = await embedding_service.generate_embedding(structured_text)

            # Alternative strategy (natural language)
            natural_text = f"delivery preference is {obj_value}"
            natural_embedding = await embedding_service.generate_embedding(natural_text)

            # Calculate similarity with query
            import numpy as np

            query_emb = np.array(query_embedding)
            structured_emb = np.array(structured_embedding)
            natural_emb = np.array(natural_embedding)

            def cosine_similarity(a, b):
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

            structured_sim = cosine_similarity(query_emb, structured_emb)
            natural_sim = cosine_similarity(query_emb, natural_emb)

            print(f"   Structured text: '{structured_text}'")
            print(f"   Similarity to query: {structured_sim:.4f}")
            print(f"   Natural text: '{natural_text}'")
            print(f"   Similarity to query: {natural_sim:.4f}")
            print(f"   Improvement: {(natural_sim - structured_sim):.4f}")

        print("\n" + "=" * 80)
        print("DIAGNOSIS:")
        print("=" * 80)

        if len(all_memories) == 0:
            print("❌ No memories found - memories are not being created")
        elif len(delivery_memories) == 0:
            print("❌ No delivery_preference memories - semantic extraction failing")
        elif not all(m.embedding is not None for m in delivery_memories):
            print("❌ Some memories missing embeddings - embedding generation failing")
        elif len(similar_memories) == 0:
            print("❌ Vector search returns no results - embedding similarity too low")
            print("   ROOT CAUSE: Structured embedding text is not semantically similar to natural language query")
        else:
            print("✅ Memories are being retrieved correctly")

        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
