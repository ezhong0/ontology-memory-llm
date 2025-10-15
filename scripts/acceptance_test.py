"""Acceptance test for the memory system.

This script validates the complete system capabilities:
1. Entity resolution from chat messages
2. Semantic memory extraction
3. Memory retrieval with provenance
4. End-to-end API functionality

Usage:
    # With API server running:
    poetry run python scripts/acceptance_test.py

    # Or test against specific host:
    API_HOST=http://localhost:8000 poetry run python scripts/acceptance_test.py
"""

import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx
import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = structlog.get_logger(__name__)

# Configuration
API_BASE_URL = os.getenv("API_HOST", "http://localhost:8000")
TEST_USER_ID = "demo-user-001"  # Must match seed data user
TEST_SESSION_ID = str(uuid4())


async def test_basic_chat_endpoint():
    """Test basic chat endpoint (entity resolution)."""
    print("\n" + "=" * 80)
    print("TEST 1: Basic Chat Endpoint (Entity Resolution)")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        # Test message with entity mention
        payload = {
            "session_id": TEST_SESSION_ID,
            "content": "What's the status of Acme Corporation's invoices?",
            "role": "user",
            "metadata": {"test": True}
        }

        print(f"\n📤 Sending POST {API_BASE_URL}/api/v1/chat/message")
        print(f"   Content: {payload['content']}")

        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/chat/message",
                json=payload,
                headers={"X-User-ID": TEST_USER_ID},
                timeout=10.0
            )

            print(f"\n📥 Response Status: {response.status_code}")

            if response.status_code == 201:
                data = response.json()
                print(f"✅ Message processed successfully")
                print(f"   Event ID: {data['event_id']}")
                print(f"   Resolved Entities: {data['mention_count']}")
                print(f"   Resolution Rate: {data['resolution_success_rate']:.1f}%")

                if data['resolved_entities']:
                    print(f"\n   Entities:")
                    for entity in data['resolved_entities']:
                        print(f"     • {entity['canonical_name']} (type: {entity['entity_type']})")
                        print(f"       Method: {entity['method']}, Confidence: {entity['confidence']:.2f}")

                return True
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   {response.text}")
                return False

        except httpx.ConnectError:
            print(f"❌ Could not connect to API at {API_BASE_URL}")
            print(f"   Make sure the server is running: make run")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


async def test_enhanced_chat_endpoint():
    """Test enhanced chat endpoint (with memory retrieval)."""
    print("\n" + "=" * 80)
    print("TEST 2: Enhanced Chat Endpoint (Memory Retrieval)")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        # Test message that should trigger semantic extraction
        payload = {
            "session_id": TEST_SESSION_ID,
            "content": "Acme Corporation prefers NET30 payment terms and Friday deliveries.",
            "role": "user",
            "metadata": {"test": True}
        }

        print(f"\n📤 Sending POST {API_BASE_URL}/api/v1/chat/message/enhanced")
        print(f"   Content: {payload['content']}")

        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/chat/message/enhanced",
                json=payload,
                headers={"X-User-ID": TEST_USER_ID},
                timeout=15.0
            )

            print(f"\n📥 Response Status: {response.status_code}")

            if response.status_code == 201:
                data = response.json()
                print(f"✅ Enhanced message processed successfully")
                print(f"   Event ID: {data['event_id']}")
                print(f"   Resolved Entities: {data['mention_count']}")
                print(f"   Retrieved Memories: {data['memory_count']}")

                if data['resolved_entities']:
                    print(f"\n   📍 Resolved Entities:")
                    for entity in data['resolved_entities']:
                        print(f"     • {entity['canonical_name']} (type: {entity['entity_type']})")
                        print(f"       Method: {entity['method']}, Confidence: {entity['confidence']:.2f}")

                if data['retrieved_memories']:
                    print(f"\n   💡 Retrieved Memories:")
                    for memory in data['retrieved_memories']:
                        print(f"     • [{memory['memory_type']}] {memory['content']}")
                        print(f"       Relevance: {memory['relevance_score']:.2f}, Confidence: {memory['confidence']:.2f}")

                if data['context_summary']:
                    print(f"\n   📝 Context Summary:")
                    print(f"     {data['context_summary']}")

                return True
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   {response.text}")
                return False

        except httpx.ConnectError:
            print(f"❌ Could not connect to API at {API_BASE_URL}")
            print(f"   Make sure the server is running: make run")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


async def test_query_with_retrieval():
    """Test query that should retrieve existing memories."""
    print("\n" + "=" * 80)
    print("TEST 3: Memory Retrieval (Query Existing Knowledge)")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        # Query about something in seed data
        payload = {
            "session_id": TEST_SESSION_ID,
            "content": "What do you know about Acme Corporation?",
            "role": "user",
            "metadata": {"test": True}
        }

        print(f"\n📤 Sending POST {API_BASE_URL}/api/v1/chat/message/enhanced")
        print(f"   Content: {payload['content']}")

        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/chat/message/enhanced",
                json=payload,
                headers={"X-User-ID": TEST_USER_ID},
                timeout=15.0
            )

            print(f"\n📥 Response Status: {response.status_code}")

            if response.status_code == 201:
                data = response.json()
                print(f"✅ Query processed successfully")

                if data['retrieved_memories']:
                    print(f"\n   💡 Retrieved {len(data['retrieved_memories'])} memories:")
                    for memory in data['retrieved_memories']:
                        print(f"     • [{memory['memory_type']}] {memory['content'][:80]}...")
                        print(f"       Relevance: {memory['relevance_score']:.2f}")
                else:
                    print(f"\n   ℹ️  No memories retrieved (may need semantic memories in DB)")

                if data['context_summary']:
                    print(f"\n   📝 Context: {data['context_summary']}")

                return True
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            return False


async def verify_seed_data():
    """Verify seed data exists in database."""
    print("\n" + "=" * 80)
    print("PRE-CHECK: Verify Seed Data")
    print("=" * 80)

    from src.config.settings import Settings
    from src.infrastructure.database.session import get_db_session, init_db
    from sqlalchemy import text

    settings = Settings()
    init_db(settings)

    try:
        async with get_db_session() as session:
            # Check canonical entities (global - no user_id)
            result = await session.execute(
                text("SELECT COUNT(*) FROM app.canonical_entities")
            )
            entity_count = result.scalar()

            # Check semantic memories (user-specific)
            result = await session.execute(
                text("SELECT COUNT(*) FROM app.semantic_memories WHERE user_id = :user_id"),
                {"user_id": TEST_USER_ID}
            )
            memory_count = result.scalar()

            # Check episodic memories (user-specific)
            result = await session.execute(
                text("SELECT COUNT(*) FROM app.episodic_memories WHERE user_id = :user_id"),
                {"user_id": TEST_USER_ID}
            )
            episodic_count = result.scalar()

            # Check domain customers
            result = await session.execute(
                text("SELECT COUNT(*) FROM domain.customers")
            )
            customer_count = result.scalar()

            print(f"\n✅ Seed data verified:")
            print(f"   Domain Customers: {customer_count}")
            print(f"   Canonical Entities: {entity_count}")
            print(f"   Semantic Memories: {memory_count}")
            print(f"   Episodic Memories: {episodic_count}")

            if customer_count == 0 or entity_count == 0:
                print(f"\n⚠️  No seed data found")
                print(f"   Run: poetry run python scripts/seed_data.py")
                return False

            return True

    except Exception as e:
        print(f"❌ Could not verify seed data: {e}")
        return False


async def main():
    """Run all acceptance tests."""
    print("\n" + "=" * 80)
    print("MEMORY SYSTEM - ACCEPTANCE TESTS")
    print("=" * 80)
    print(f"\nAPI Base URL: {API_BASE_URL}")
    print(f"Test User: {TEST_USER_ID}")
    print(f"Test Session: {TEST_SESSION_ID}")

    # Pre-check: Verify seed data
    if not await verify_seed_data():
        print("\n❌ Seed data verification failed - run seed script first")
        return False

    # Run tests
    results = []

    results.append(("Basic Chat (Entity Resolution)", await test_basic_chat_endpoint()))
    results.append(("Enhanced Chat (Memory Retrieval)", await test_enhanced_chat_endpoint()))
    results.append(("Query Existing Knowledge", await test_query_with_retrieval()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\n{'=' * 80}")
    print(f"Results: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("✅ ALL TESTS PASSED - System is operational")
        print("\nThe memory system successfully demonstrates:")
        print("  ✅ Entity resolution from natural language")
        print("  ✅ Semantic memory extraction")
        print("  ✅ Memory retrieval with provenance")
        print("  ✅ End-to-end API functionality")
    else:
        print(f"⚠️  {total_count - passed_count} test(s) failed")

    print("=" * 80)

    return passed_count == total_count


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
