"""Debug script to check E2E test response structure."""
import asyncio
import json
from httpx import AsyncClient
from datetime import date
from tests.fixtures.domain_seeder import DomainSeeder
from tests.fixtures.memory_factory import MemoryFactory
from src.infrastructure.database.session import get_db_session

async def debug_test():
    """Run simplified version of Scenario 1 to debug."""
    async with get_db_session() as session:
        # Setup seeder
        seeder = DomainSeeder(session)
        factory = MemoryFactory(session)

        # Seed domain data
        ids = await seeder.seed({
            "customers": [{
                "name": "Kai Media",
                "industry": "Entertainment",
                "id": "kai_123"
            }],
            "sales_orders": [{
                "customer": "kai_123",
                "so_number": "SO-1001",
                "title": "Album Fulfillment",
                "status": "fulfilled",
                "id": "so_1001"
            }],
            "invoices": [{
                "sales_order": "so_1001",
                "invoice_number": "INV-1009",
                "amount": 1200.00,
                "due_date": date(2025, 9, 30),
                "status": "open",
                "id": "inv_1009"
            }]
        })

        await session.commit()

        print("\\n=== Seeder ID Mapping ===")
        print(json.dumps(ids, indent=2))

        # Create entity
        await factory.create_canonical_entity(
            entity_id=f"customer_{ids['kai_123']}",
            entity_type="customer",
            canonical_name="Kai Media",
            external_ref={"table": "domain.customers", "id": ids["kai_123"]},
            properties={"industry": "Entertainment"}
        )
        await session.commit()

    # Make API requests
    async with AsyncClient(base_url="http://localhost:8000", timeout=60) as client:
        # First message - create memory
        resp1 = await client.post("/api/v1/chat", json={
            "user_id": "finance_agent",
            "message": "Remember: Kai Media prefers Friday deliveries"
        })
        print(f"\\n=== First Request Status: {resp1.status_code} ===")

        # Second message - retrieve memory and domain facts
        resp2 = await client.post("/api/v1/chat", json={
            "user_id": "finance_agent",
            "message": "Draft an email for Kai Media about their unpaid invoice and mention their preferred delivery day for the next shipment."
        })

        print(f"\\n=== Second Request Status: {resp2.status_code} ===")

        if resp2.status_code == 200:
            data = resp2.json()

            print("\\n=== Response Structure ===")
            print("Keys:", list(data.keys()))

            if "augmentation" in data:
                print("\\nAugmentation keys:", list(data["augmentation"].keys()))

                if "domain_facts" in data["augmentation"]:
                    facts = data["augmentation"]["domain_facts"]
                    print(f"\\nDomain facts count: {len(facts)}")
                    for i, fact in enumerate(facts):
                        print(f"\\nFact {i+1}:")
                        print(json.dumps(fact, indent=2, default=str))

                if "memories_retrieved" in data["augmentation"]:
                    mems = data["augmentation"]["memories_retrieved"]
                    print(f"\\nMemories retrieved count: {len(mems)}")
                    for i, mem in enumerate(mems):
                        print(f"\\nMemory {i+1}:")
                        print(json.dumps(mem, indent=2, default=str))

            print("\\n=== Response Text ===")
            print(data["response"][:500])

            print("\\n=== Test Assertions Check ===")
            print(f"✓ 'INV-1009' in response: {'INV-1009' in data['response']}")
            print(f"✓ 'Friday' in response: {'Friday' in data['response']}")

            # Check domain facts
            if "domain_facts" in data.get("augmentation", {}):
                for fact in data["augmentation"]["domain_facts"]:
                    if fact.get("table") == "domain.invoices":
                        print(f"\\n✓ Found invoice fact with table='domain.invoices'")
                        print(f"  - invoice_id in fact: {fact.get('invoice_id')}")
                        print(f"  - Expected (seed key): 'inv_1009'")
                        print(f"  - Expected (UUID): '{ids['inv_1009']}'")
                        print(f"  - Match seed key: {fact.get('invoice_id') == 'inv_1009'}")
                        print(f"  - Match UUID: {fact.get('invoice_id') == ids['inv_1009']}")

if __name__ == "__main__":
    asyncio.run(debug_test())
