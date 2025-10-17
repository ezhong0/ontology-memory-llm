"""Debug Scenario 12 to see actual failure."""
import asyncio
import httpx
from uuid import uuid4

async def test_scenario_12():
    base_url = "http://localhost:8000"
    session_id = str(uuid4())
    user_id = "ops_manager"

    # First, check if Kai Media entity exists in the database
    async with httpx.AsyncClient() as client:
        # Try to search for entities
        print("=== Checking if Kai Media entity exists ===")
        search_response = await client.get(
            f"{base_url}/api/v1/entities",
            params={"search": "Kai Media"},
            timeout=30.0,
        )
        print(f"Entity search status: {search_response.status_code}")
        if search_response.status_code == 200:
            entities = search_response.json()
            print(f"Found {len(entities)} entities:")
            for e in entities:
                print(f"  - {e.get('canonical_name')} ({e.get('entity_id')})")
        else:
            print(f"Entity search failed or endpoint doesn't exist")

    # Turn 1: Typo "Kay Media" (should fuzzy match to "Kai Media")
    async with httpx.AsyncClient() as client:
        response1 = await client.post(
            f"{base_url}/api/v1/chat",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "message": "Open a WO for Kay Media for packaging.",
            },
            timeout=30.0,
        )
        data1 = response1.json()

        print("=== TURN 1 RESPONSE ===")
        print(f"Status: {response1.status_code}")

        import json
        print(f"\nFull response:")
        print(json.dumps(data1, indent=2))

        print(f"\nResolved Entities:")
        for entity in data1.get("augmentation", {}).get("entities_resolved", []):
            print(f"  - {entity}")

        print(f"\nChecking fuzzy match assertion...")
        entities = data1.get("augmentation", {}).get("entities_resolved", [])

        # This is the assertion that's failing
        fuzzy_match_found = any(
            e.get("mention_text", "").lower() == "kay media" and
            e.get("canonical_name") == "Kai Media" and
            e.get("method") == "fuzzy"
            for e in entities
        )

        print(f"Fuzzy match found: {fuzzy_match_found}")

        if not fuzzy_match_found:
            print("\n❌ ASSERTION WOULD FAIL")
            print("\nActual entities:")
            for e in entities:
                print(f"  mention_text: {e.get('mention_text')}")
                print(f"  canonical_name: {e.get('canonical_name')}")
                print(f"  method: {e.get('method')}")
                print(f"  is_implicit: {e.get('is_implicit', False)}")
                print()
        else:
            print("\n✅ ASSERTION PASSES")

        # Turn 2: Same typo (should use auto-learned alias)
        response2 = await client.post(
            f"{base_url}/api/v1/chat",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "message": "Update the Kay Media WO with priority.",
            },
            timeout=30.0,
        )
        data2 = response2.json()

        print("\n=== TURN 2 RESPONSE ===")
        print(f"Status: {response2.status_code}")
        print(f"\nResolved Entities:")
        for entity in data2.get("augmentation", {}).get("entities_resolved", []):
            print(f"  - {entity}")

        entities2 = data2.get("augmentation", {}).get("entities_resolved", [])
        alias_match_found = any(
            e.get("mention_text", "").lower() == "kay media" and
            e.get("canonical_name") == "Kai Media" and
            e.get("method") == "alias"
            for e in entities2
        )

        print(f"\nAlias match found: {alias_match_found}")

        if not alias_match_found:
            print("\n❌ ASSERTION WOULD FAIL")
            print("\nActual entities:")
            for e in entities2:
                print(f"  mention_text: {e.get('mention_text')}")
                print(f"  canonical_name: {e.get('canonical_name')}")
                print(f"  method: {e.get('method')}")
                print(f"  is_implicit: {e.get('is_implicit', False)}")
                print()
        else:
            print("\n✅ ASSERTION PASSES")

if __name__ == "__main__":
    asyncio.run(test_scenario_12())
