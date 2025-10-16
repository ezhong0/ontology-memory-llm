"""Tests for E2E test fixtures.

Verifies that DomainSeeder and MemoryFactory work correctly.
"""
import pytest
from datetime import datetime, timezone, date


@pytest.mark.integration
@pytest.mark.asyncio
async def test_domain_seeder_creates_customer(domain_seeder, test_db_session):
    """Test that DomainSeeder can create customers."""

    # ARRANGE & ACT
    ids = await domain_seeder.seed({
        "customers": [
            {
                "name": "Test Corporation",
                "industry": "Technology",
                "id": "test_corp_123"
            }
        ]
    })

    # ASSERT: Friendly ID was mapped
    assert "test_corp_123" in ids
    assert ids["test_corp_123"] is not None

    # ASSERT: Customer was created in database
    from sqlalchemy import text
    result = await test_db_session.execute(
        text("SELECT name, industry FROM domain.customers WHERE customer_id = :id"),
        {"id": ids["test_corp_123"]}
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == "Test Corporation"
    assert row[1] == "Technology"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_domain_seeder_creates_invoice_with_foreign_key(domain_seeder, test_db_session):
    """Test that DomainSeeder resolves foreign key references."""

    # ARRANGE & ACT: Create customer, SO, and invoice (using unique test IDs to avoid conflicts)
    ids = await domain_seeder.seed({
        "customers": [
            {"name": "Fixture Test Customer", "industry": "Entertainment", "id": "fixture_cust_123"}
        ],
        "sales_orders": [
            {
                "customer": "fixture_cust_123",  # Friendly ID reference
                "so_number": "SO-FIXTURE-001",  # Unique to avoid demo scenario conflicts
                "title": "Fixture Test Order",
                "status": "in_fulfillment",
                "id": "fixture_so_001"
            }
        ],
        "invoices": [
            {
                "sales_order": "fixture_so_001",  # Friendly ID reference
                "invoice_number": "INV-FIXTURE-001",  # Unique to avoid demo scenario conflicts
                "amount": 999.99,
                "due_date": date(2025, 9, 30),
                "status": "open",
                "id": "fixture_inv_001"
            }
        ]
    })

    # ASSERT: All IDs mapped
    assert "fixture_cust_123" in ids
    assert "fixture_so_001" in ids
    assert "fixture_inv_001" in ids

    # ASSERT: Foreign keys resolved correctly
    from sqlalchemy import text
    result = await test_db_session.execute(
        text("""
            SELECT i.invoice_number, i.amount, s.so_number, c.name
            FROM domain.invoices i
            JOIN domain.sales_orders s ON i.so_id = s.so_id
            JOIN domain.customers c ON s.customer_id = c.customer_id
            WHERE i.invoice_id = :invoice_id
        """),
        {"invoice_id": ids["fixture_inv_001"]}
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == "INV-FIXTURE-001"
    assert float(row[1]) == 999.99
    assert row[2] == "SO-FIXTURE-001"
    assert row[3] == "Fixture Test Customer"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_factory_creates_semantic_memory(memory_factory, test_db_session):
    """Test that MemoryFactory can create semantic memories."""

    # ARRANGE: Create canonical entity first
    await memory_factory.create_canonical_entity(
        entity_id="customer:test_123",
        entity_type="customer",
        canonical_name="Test Corporation",
        external_ref={"table": "domain.customers", "id": "test_123"},
        properties={"industry": "Technology"}
    )

    # ACT: Create semantic memory
    memory = await memory_factory.create_semantic_memory(
        user_id="test_user",
        subject_entity_id="customer:test_123",
        predicate="prefers_delivery_day",
        object_value={"day": "Friday"},
        confidence=0.8
    )

    # ASSERT: Memory created with correct attributes
    assert memory.memory_id is not None
    assert memory.user_id == "test_user"
    assert memory.subject_entity_id == "customer:test_123"
    assert memory.predicate == "prefers_delivery_day"
    assert memory.object_value == {"day": "Friday"}
    assert memory.confidence == 0.8
    assert memory.status == "active"
    assert memory.embedding is not None
    assert len(memory.embedding) == 1536  # OpenAI embedding dimension


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_factory_creates_episodic_memory(memory_factory, test_db_session):
    """Test that MemoryFactory can create episodic memories."""

    # ARRANGE
    import uuid
    session_id = uuid.uuid4()

    # ACT
    memory_id = await memory_factory.create_episodic_memory(
        user_id="test_user",
        session_id=str(session_id),
        summary="User asked about invoice status for Test Corporation",
        event_type="question",
        entities=[
            {
                "id": "customer:test_123",
                "name": "Test Corporation",
                "type": "customer"
            }
        ],
        importance=0.7,
        source_event_ids=[1, 2]
    )

    # ASSERT
    assert memory_id is not None
    assert isinstance(memory_id, int)

    # Verify in database
    from sqlalchemy import text
    result = await test_db_session.execute(
        text("SELECT user_id, summary, event_type, importance FROM app.episodic_memories WHERE memory_id = :id"),
        {"id": memory_id}
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == "test_user"
    assert row[1] == "User asked about invoice status for Test Corporation"
    assert row[2] == "question"
    assert row[3] == 0.7


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_factory_creates_procedural_memory(memory_factory, test_db_session):
    """Test that MemoryFactory can create procedural memories."""

    # ACT
    memory_id = await memory_factory.create_procedural_memory(
        user_id="test_user",
        trigger_pattern="When user asks about payments",
        action_heuristic="Also retrieve invoice information",
        trigger_features={
            "intent": "query",
            "entity_types": ["payment"],
            "topics": ["finance"]
        },
        observed_count=5,
        confidence=0.75
    )

    # ASSERT
    assert memory_id is not None
    assert isinstance(memory_id, int)

    # Verify in database
    from sqlalchemy import text
    result = await test_db_session.execute(
        text("SELECT user_id, trigger_pattern, action_heuristic, observed_count, confidence FROM app.procedural_memories WHERE memory_id = :id"),
        {"id": memory_id}
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == "test_user"
    assert row[1] == "When user asks about payments"
    assert row[2] == "Also retrieve invoice information"
    assert row[3] == 5
    assert row[4] == 0.75


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fixtures_work_together(domain_seeder, memory_factory, test_db_session):
    """Test that domain_seeder and memory_factory work together."""

    # ARRANGE: Seed domain database
    ids = await domain_seeder.seed({
        "customers": [
            {"name": "Integration Test Corp", "industry": "Testing", "id": "integ_123"}
        ]
    })

    customer_uuid = ids["integ_123"]

    # ACT: Create canonical entity referencing domain customer
    entity_id = await memory_factory.create_canonical_entity(
        entity_id=f"customer:{customer_uuid}",
        entity_type="customer",
        canonical_name="Integration Test Corp",
        external_ref={"table": "domain.customers", "id": str(customer_uuid)},  # Convert UUID to string for JSONB
        properties={"industry": "Testing"}
    )

    # ACT: Create semantic memory about this customer
    memory = await memory_factory.create_semantic_memory(
        user_id="test_user",
        subject_entity_id=entity_id,
        predicate="test_predicate",
        object_value={"value": "test_value"}  # Must be dict, not string
    )

    # ASSERT: Full integration works
    assert memory.subject_entity_id == f"customer:{customer_uuid}"

    # Flush all changes to database to ensure they're visible in the query
    await test_db_session.flush()

    # Debug: Check what's in each table
    from sqlalchemy import text

    # Check customer exists
    cust_result = await test_db_session.execute(
        text("SELECT customer_id, name FROM domain.customers WHERE customer_id = :id"),
        {"id": customer_uuid}
    )
    cust_row = cust_result.fetchone()
    assert cust_row is not None, f"Customer not found for UUID: {customer_uuid}"

    # Check canonical entity exists
    entity_result = await test_db_session.execute(
        text("SELECT entity_id, canonical_name, external_ref FROM app.canonical_entities WHERE entity_id = :id"),
        {"id": entity_id}
    )
    entity_row = entity_result.fetchone()
    assert entity_row is not None, f"Canonical entity not found for entity_id: {entity_id}"
    print(f"DEBUG: external_ref = {entity_row[2]}")

    # Check semantic memory exists
    mem_result = await test_db_session.execute(
        text("SELECT memory_id, subject_entity_id, predicate FROM app.semantic_memories WHERE subject_entity_id = :id"),
        {"id": entity_id}
    )
    mem_row = mem_result.fetchone()
    assert mem_row is not None, f"Semantic memory not found for subject_entity_id: {entity_id}"

    # ASSERT: Can query across domain and memory tables
    result = await test_db_session.execute(
        text("""
            SELECT c.name, e.canonical_name, sm.predicate, sm.object_value
            FROM domain.customers c
            JOIN app.canonical_entities e ON e.external_ref->>'primary_value' = c.customer_id::text
            JOIN app.semantic_memories sm ON sm.subject_entity_id = e.entity_id
            WHERE c.customer_id = :customer_id
        """),
        {"customer_id": customer_uuid}
    )
    row = result.fetchone()
    assert row is not None, f"Join query failed - customer_uuid: {customer_uuid}, entity_id: {entity_id}"
    assert row[0] == "Integration Test Corp"  # domain.customers.name
    assert row[1] == "Integration Test Corp"  # canonical_entities.canonical_name
    assert row[2] == "test_predicate"  # semantic_memories.predicate
    assert row[3] == {"value": "test_value"}  # semantic_memories.object_value
