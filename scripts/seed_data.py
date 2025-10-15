"""Seed database with comprehensive demo data.

This script populates both domain and memory databases with realistic data
for testing and demonstration purposes.

Usage:
    poetry run python scripts/seed_data.py

Features:
- Idempotent (can run multiple times safely)
- Creates domain data (customers, orders, invoices, etc.)
- Creates memory data (entities, episodes, semantic facts, summaries)
- Generates embeddings for vector similarity search
- Realistic business scenarios matching project requirements
"""

import asyncio
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import numpy as np
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import Settings
from src.infrastructure.database.session import get_db_session, init_db
from src.infrastructure.embedding.openai_embedding_service import (
    OpenAIEmbeddingService,
)

logger = structlog.get_logger(__name__)

# ============================================================================
# Configuration
# ============================================================================

DEMO_USER_ID = "demo-user-001"
SESSION_ID = uuid4()

# ============================================================================
# Domain Data (domain.* schema)
# ============================================================================


async def seed_domain_database(session: AsyncSession) -> dict:
    """Seed domain database with business entities.

    Args:
        session: Database session

    Returns:
        Dictionary of created entity IDs for reference
    """
    logger.info("seeding_domain_database")

    entities = {}

    # Create customers (schema: customer_id UUID, name TEXT, industry TEXT, notes TEXT)
    customers = [
        {
            "name": "Acme Corporation",
            "industry": "Manufacturing",
            "notes": "Long-term client, NET30 payment terms, prefers Friday communications",
        },
        {
            "name": "TechStart Inc",
            "industry": "Software",
            "notes": "Fast-growing startup, NET15 payment terms",
        },
        {
            "name": "GlobalMart",
            "industry": "Retail",
            "notes": "Large retail chain, NET45 payment terms",
        },
    ]

    customer_ids = {}
    for customer in customers:
        # Check if exists first
        result = await session.execute(
            text("SELECT customer_id FROM domain.customers WHERE name = :name"),
            {"name": customer["name"]}
        )
        row = result.fetchone()

        if row:
            customer_ids[customer["name"]] = row[0]
            entities[customer["name"]] = str(row[0])
        else:
            result = await session.execute(
                text("""
                    INSERT INTO domain.customers (name, industry, notes)
                    VALUES (:name, :industry, :notes)
                    RETURNING customer_id
                """),
                customer,
            )
            row = result.fetchone()
            if row:
                customer_ids[customer["name"]] = row[0]
                entities[customer["name"]] = str(row[0])

    # Create sales orders (schema: so_id UUID, customer_id UUID FK, so_number TEXT, title TEXT, status TEXT, created_at TIMESTAMP)
    sales_orders = [
        {
            "so_number": "SO-1001",
            "customer_id": customer_ids["Acme Corporation"],
            "title": "Equipment Installation Project",
            "status": "completed",
            "created_at": datetime.now(UTC) - timedelta(days=45),
        },
        {
            "so_number": "SO-1002",
            "customer_id": customer_ids["Acme Corporation"],
            "title": "System Upgrade Phase 2",
            "status": "in_progress",
            "created_at": datetime.now(UTC) - timedelta(days=10),
        },
        {
            "so_number": "SO-1003",
            "customer_id": customer_ids["TechStart Inc"],
            "title": "Office Network Setup",
            "status": "completed",
            "created_at": datetime.now(UTC) - timedelta(days=20),
        },
        {
            "so_number": "SO-1004",
            "customer_id": customer_ids["GlobalMart"],
            "title": "Store POS System Installation",
            "status": "pending",
            "created_at": datetime.now(UTC) - timedelta(days=5),
        },
    ]

    so_ids = {}
    for order in sales_orders:
        # Check if exists
        result = await session.execute(
            text("SELECT so_id FROM domain.sales_orders WHERE so_number = :so_number"),
            {"so_number": order["so_number"]}
        )
        row = result.fetchone()

        if row:
            so_ids[order["so_number"]] = row[0]
        else:
            result = await session.execute(
                text("""
                    INSERT INTO domain.sales_orders (customer_id, so_number, title, status, created_at)
                    VALUES (:customer_id, :so_number, :title, :status, :created_at)
                    RETURNING so_id
                """),
                order,
            )
            row = result.fetchone()
            if row:
                so_ids[order["so_number"]] = row[0]

    # Create work orders (schema: wo_id UUID, so_id UUID FK, description TEXT, status TEXT, technician TEXT, scheduled_for DATE)
    work_orders = [
        {
            "so_id": so_ids["SO-1001"],
            "description": "Equipment installation and configuration",
            "status": "completed",
            "technician": "John Smith",
            "scheduled_for": (datetime.now(UTC) - timedelta(days=30)).date(),
        },
        {
            "so_id": so_ids["SO-1002"],
            "description": "System upgrade and testing",
            "status": "in_progress",
            "technician": "Sarah Johnson",
            "scheduled_for": (datetime.now(UTC) + timedelta(days=5)).date(),
        },
        {
            "so_id": so_ids["SO-1003"],
            "description": "Network infrastructure setup",
            "status": "completed",
            "technician": "Mike Davis",
            "scheduled_for": (datetime.now(UTC) - timedelta(days=10)).date(),
        },
    ]

    wo_ids = {}
    for wo in work_orders:
        result = await session.execute(
            text("""
                INSERT INTO domain.work_orders (so_id, description, status, technician, scheduled_for)
                VALUES (:so_id, :description, :status, :technician, :scheduled_for)
                RETURNING wo_id
            """),
            wo,
        )
        row = result.fetchone()
        if row:
            wo_ids[wo["description"]] = row[0]

    # Create invoices (schema: invoice_id UUID, so_id UUID FK, invoice_number TEXT, amount NUMERIC, due_date DATE, status TEXT, issued_at TIMESTAMP)
    invoices = [
        {
            "invoice_number": "INV-1001",
            "so_id": so_ids["SO-1001"],
            "issued_at": datetime.now(UTC) - timedelta(days=40),
            "due_date": (datetime.now(UTC) - timedelta(days=10)).date(),
            "amount": 15000.00,
            "status": "paid",
        },
        {
            "invoice_number": "INV-1002",
            "so_id": so_ids["SO-1002"],
            "issued_at": datetime.now(UTC) - timedelta(days=8),
            "due_date": (datetime.now(UTC) + timedelta(days=22)).date(),
            "amount": 8500.00,
            "status": "open",
        },
        {
            "invoice_number": "INV-1003",
            "so_id": so_ids["SO-1003"],
            "issued_at": datetime.now(UTC) - timedelta(days=18),
            "due_date": (datetime.now(UTC) + timedelta(days=12)).date(),
            "amount": 12000.00,
            "status": "open",
        },
        {
            "invoice_number": "INV-1004",
            "so_id": so_ids["SO-1004"],
            "issued_at": datetime.now(UTC) - timedelta(days=3),
            "due_date": (datetime.now(UTC) + timedelta(days=27)).date(),
            "amount": 25000.00,
            "status": "open",
        },
    ]

    invoice_ids = {}
    for invoice in invoices:
        # Check if exists
        result = await session.execute(
            text("SELECT invoice_id FROM domain.invoices WHERE invoice_number = :invoice_number"),
            {"invoice_number": invoice["invoice_number"]}
        )
        row = result.fetchone()

        if row:
            invoice_ids[invoice["invoice_number"]] = row[0]
        else:
            result = await session.execute(
                text("""
                    INSERT INTO domain.invoices (so_id, invoice_number, amount, due_date, status, issued_at)
                    VALUES (:so_id, :invoice_number, :amount, :due_date, :status, :issued_at)
                    RETURNING invoice_id
                """),
                invoice,
            )
            row = result.fetchone()
            if row:
                invoice_ids[invoice["invoice_number"]] = row[0]

    # Create payments (schema: payment_id UUID, invoice_id UUID FK, amount NUMERIC, method TEXT, paid_at TIMESTAMP)
    payments = [
        {
            "invoice_id": invoice_ids["INV-1001"],
            "paid_at": datetime.now(UTC) - timedelta(days=12),
            "amount": 15000.00,
            "method": "wire_transfer",
        },
    ]

    for payment in payments:
        await session.execute(
            text("""
                INSERT INTO domain.payments (invoice_id, amount, method, paid_at)
                VALUES (:invoice_id, :amount, :method, :paid_at)
            """),
            payment,
        )

    # Create tasks (schema: task_id UUID, customer_id UUID FK nullable, title TEXT, body TEXT, status TEXT, created_at TIMESTAMP)
    tasks = [
        {
            "customer_id": customer_ids["Acme Corporation"],
            "title": "Follow up on payment confirmation",
            "body": "Contact Acme on Friday to confirm payment receipt for INV-1002",
            "status": "pending",
            "created_at": datetime.now(UTC) - timedelta(days=2),
        },
        {
            "customer_id": customer_ids["TechStart Inc"],
            "title": "Schedule quarterly business review",
            "body": "Arrange Q4 business review meeting with TechStart Inc",
            "status": "pending",
            "created_at": datetime.now(UTC) - timedelta(days=5),
        },
        {
            "customer_id": customer_ids["GlobalMart"],
            "title": "Prepare proposal for expansion",
            "body": "Draft proposal for additional store locations",
            "status": "in_progress",
            "created_at": datetime.now(UTC) - timedelta(days=7),
        },
    ]

    for task in tasks:
        await session.execute(
            text("""
                INSERT INTO domain.tasks (customer_id, title, body, status, created_at)
                VALUES (:customer_id, :title, :body, :status, :created_at)
            """),
            task,
        )

    await session.commit()

    logger.info(
        "domain_database_seeded",
        customers=len(customers),
        orders=len(sales_orders),
        invoices=len(invoices),
        work_orders=len(work_orders),
        tasks=len(tasks),
        payments=len(payments),
    )

    return entities


# ============================================================================
# Memory System Data (app.* schema)
# ============================================================================


async def seed_canonical_entities(
    session: AsyncSession, domain_entities: dict
) -> dict:
    """Create canonical entities from domain entities.

    Args:
        session: Database session
        domain_entities: Dictionary of domain entity names to IDs

    Returns:
        Dictionary mapping names to entity_ids
    """
    logger.info("seeding_canonical_entities")

    entity_map = {}

    # Create canonical entities for customers
    for name, domain_uuid in domain_entities.items():
        # Use customer:<uuid> format for entity_id
        entity_id = f"customer:{domain_uuid}"

        await session.execute(
            text("""
                INSERT INTO app.canonical_entities (
                    entity_id, entity_type, canonical_name, external_ref, properties, created_at, updated_at
                )
                VALUES (
                    :entity_id, :entity_type, :canonical_name, :external_ref, :properties, :created_at, :updated_at
                )
                ON CONFLICT (entity_id) DO NOTHING
            """),
            {
                "entity_id": entity_id,
                "entity_type": "customer",
                "canonical_name": name,
                "external_ref": json.dumps({"table": "domain.customers", "column": "customer_id", "id": domain_uuid}),
                "properties": json.dumps({"verified": True, "source": "domain_db"}),
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )

        entity_map[name] = entity_id

    await session.commit()

    logger.info("canonical_entities_created", count=len(entity_map))

    return entity_map


async def seed_entity_aliases(session: AsyncSession, entity_map: dict) -> None:
    """Create entity aliases for resolution.

    Args:
        session: Database session
        entity_map: Mapping of canonical names to entity IDs
    """
    logger.info("seeding_entity_aliases")

    aliases = [
        # Acme aliases
        ("Acme Corporation", "Acme", "learned", entity_map["Acme Corporation"], 0.95),
        ("Acme Corporation", "Acme Corp", "learned", entity_map["Acme Corporation"], 0.90),
        ("Acme Corporation", "ACME", "learned", entity_map["Acme Corporation"], 0.85),
        # TechStart aliases
        ("TechStart Inc", "TechStart", "learned", entity_map["TechStart Inc"], 0.95),
        ("TechStart Inc", "TS", "learned", entity_map["TechStart Inc"], 0.75),
        # GlobalMart aliases
        ("GlobalMart", "GM", "learned", entity_map["GlobalMart"], 0.80),
    ]

    for canonical_name, alias_text, source, entity_id, confidence in aliases:
        await session.execute(
            text("""
                INSERT INTO app.entity_aliases (
                    canonical_entity_id, alias_text, alias_source, user_id,
                    confidence, use_count, created_at
                )
                VALUES (
                    :entity_id, :alias_text, :source, :user_id,
                    :confidence, :use_count, :created_at
                )
                ON CONFLICT (alias_text, user_id, canonical_entity_id) DO NOTHING
            """),
            {
                "entity_id": entity_id,
                "alias_text": alias_text,
                "source": source,
                "user_id": DEMO_USER_ID,
                "confidence": confidence,
                "use_count": 1,
                "created_at": datetime.now(UTC),
            },
        )

    await session.commit()

    logger.info("entity_aliases_created", count=len(aliases))


async def seed_chat_events(session: AsyncSession) -> list[int]:
    """Create chat events (conversation history).

    Args:
        session: Database session

    Returns:
        List of created event IDs
    """
    logger.info("seeding_chat_events")

    events = [
        {
            "role": "user",
            "content": "What's the status of Acme Corporation's latest invoice?",
            "timestamp": datetime.now(UTC) - timedelta(hours=2),
        },
        {
            "role": "assistant",
            "content": "Acme Corporation has invoice INV-1002 for $8,500, currently open with a due date 22 days from now.",
            "timestamp": datetime.now(UTC) - timedelta(hours=2, minutes=-1),
        },
        {
            "role": "user",
            "content": "When do they usually pay?",
            "timestamp": datetime.now(UTC) - timedelta(hours=2, minutes=-5),
        },
        {
            "role": "assistant",
            "content": "Based on their history, Acme typically pays 2-3 days before the due date. Their payment terms are NET30.",
            "timestamp": datetime.now(UTC) - timedelta(hours=2, minutes=-6),
        },
        {
            "role": "user",
            "content": "Remind me to email them on Friday about payment confirmation.",
            "timestamp": datetime.now(UTC) - timedelta(hours=2, minutes=-10),
        },
        {
            "role": "assistant",
            "content": "I've noted that you prefer to contact Acme on Fridays for payment matters. I'll help you remember that.",
            "timestamp": datetime.now(UTC) - timedelta(hours=2, minutes=-11),
        },
    ]

    event_ids = []

    for event in events:
        content_hash = hashlib.sha256(event["content"].encode()).hexdigest()[:16]

        result = await session.execute(
            text("""
                INSERT INTO app.chat_events (
                    session_id, user_id, role, content, content_hash, created_at
                )
                VALUES (
                    :session_id, :user_id, :role, :content, :content_hash, :created_at
                )
                ON CONFLICT (session_id, content_hash) DO NOTHING
                RETURNING event_id
            """),
            {
                "session_id": SESSION_ID,
                "user_id": DEMO_USER_ID,
                "role": event["role"],
                "content": event["content"],
                "content_hash": content_hash,
                "created_at": event["timestamp"],
            },
        )

        row = result.fetchone()
        if row:
            event_ids.append(row[0])

    await session.commit()

    logger.info("chat_events_created", count=len(event_ids))

    return event_ids


async def seed_episodic_memories(
    session: AsyncSession,
    embedding_service: OpenAIEmbeddingService,
    event_ids: list[int],
    entity_map: dict,
) -> list[int]:
    """Create episodic memories with embeddings.

    Args:
        session: Database session
        embedding_service: Embedding generation service
        event_ids: Chat event IDs to link to
        entity_map: Entity ID mappings

    Returns:
        List of created memory IDs
    """
    logger.info("seeding_episodic_memories")

    memories = [
        {
            "summary": "User asked about Acme Corporation's latest invoice status",
            "event_type": "question",
            "entities": [
                {
                    "id": entity_map["Acme Corporation"],
                    "name": "Acme Corporation",
                    "type": "customer",
                }
            ],
            "importance": 0.7,
            "source_event_ids": event_ids[:1] if event_ids else [1],
        },
        {
            "summary": "User inquired about Acme's typical payment timing patterns",
            "event_type": "question",
            "entities": [
                {
                    "id": entity_map["Acme Corporation"],
                    "name": "Acme Corporation",
                    "type": "customer",
                }
            ],
            "importance": 0.8,
            "source_event_ids": event_ids[2:3] if len(event_ids) > 2 else [3],
        },
        {
            "summary": "User requested reminder to email Acme on Friday about payment confirmation",
            "event_type": "statement",
            "entities": [
                {
                    "id": entity_map["Acme Corporation"],
                    "name": "Acme Corporation",
                    "type": "customer",
                }
            ],
            "importance": 0.9,
            "source_event_ids": event_ids[4:5] if len(event_ids) > 4 else [5],
        },
    ]

    memory_ids = []

    # Generate embeddings in batch
    summaries = [m["summary"] for m in memories]
    embeddings = await embedding_service.generate_embeddings_batch(summaries)

    for memory, embedding in zip(memories, embeddings):
        # Convert embedding to JSON string for pgvector
        embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)

        result = await session.execute(
            text("""
                INSERT INTO app.episodic_memories (
                    user_id, session_id, summary, event_type, source_event_ids,
                    entities, importance, embedding, created_at
                )
                VALUES (
                    :user_id, :session_id, :summary, :event_type, :source_event_ids,
                    :entities, :importance, CAST(:embedding AS vector), :created_at
                )
                RETURNING memory_id
            """),
            {
                "user_id": DEMO_USER_ID,
                "session_id": SESSION_ID,
                "summary": memory["summary"],
                "event_type": memory["event_type"],
                "source_event_ids": memory["source_event_ids"],
                "entities": json.dumps(memory["entities"]),
                "importance": memory["importance"],
                "embedding": json.dumps(embedding_list),
                "created_at": datetime.now(UTC),
            },
        )

        row = result.fetchone()
        if row:
            memory_ids.append(row[0])

    await session.commit()

    logger.info("episodic_memories_created", count=len(memory_ids))

    return memory_ids


async def seed_semantic_memories(
    session: AsyncSession,
    embedding_service: OpenAIEmbeddingService,
    entity_map: dict,
    event_ids: list[int],
) -> list[int]:
    """Create semantic memories (extracted facts).

    Args:
        session: Database session
        embedding_service: Embedding generation service
        entity_map: Entity ID mappings
        event_ids: Chat event IDs to link to

    Returns:
        List of created memory IDs
    """
    logger.info("seeding_semantic_memories")

    acme_id = entity_map["Acme Corporation"]

    memories = [
        {
            "subject_entity_id": acme_id,
            "predicate": "payment_timing_pattern",
            "predicate_type": "observation",
            "object_value": {"pattern": "2-3 days before due date", "consistency": "high"},
            "confidence": 0.85,
            "reinforcement_count": 3,
            "source_type": "episodic",
            "importance": 0.8,
            "text_for_embedding": "Acme Corporation typically pays 2-3 days before due date",
        },
        {
            "subject_entity_id": acme_id,
            "predicate": "contact_preference",
            "predicate_type": "preference",
            "object_value": {
                "day": "Friday",
                "topic": "payment confirmation",
                "method": "email",
            },
            "confidence": 0.90,
            "reinforcement_count": 1,
            "source_type": "episodic",
            "importance": 0.9,
            "text_for_embedding": "Acme Corporation prefers email contact on Fridays for payment confirmation",
        },
        {
            "subject_entity_id": acme_id,
            "predicate": "payment_terms",
            "predicate_type": "attribute",
            "object_value": {"terms": "NET30", "verified": True},
            "confidence": 0.95,
            "reinforcement_count": 5,
            "source_type": "consolidation",
            "importance": 0.7,
            "text_for_embedding": "Acme Corporation has NET30 payment terms",
        },
    ]

    memory_ids = []

    # Generate embeddings
    texts = [m["text_for_embedding"] for m in memories]
    embeddings = await embedding_service.generate_embeddings_batch(texts)

    for memory, embedding in zip(memories, embeddings):
        # Convert embedding to JSON string for pgvector
        embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)

        result = await session.execute(
            text("""
                INSERT INTO app.semantic_memories (
                    user_id, subject_entity_id, predicate, predicate_type, object_value,
                    confidence, confidence_factors, reinforcement_count, last_validated_at,
                    source_type, source_memory_id, extracted_from_event_id,
                    status, embedding, importance, created_at, updated_at
                )
                VALUES (
                    :user_id, :subject_entity_id, :predicate, :predicate_type, :object_value,
                    :confidence, :confidence_factors, :reinforcement_count, :last_validated_at,
                    :source_type, :source_memory_id, :extracted_from_event_id,
                    :status, CAST(:embedding AS vector), :importance, :created_at, :updated_at
                )
                RETURNING memory_id
            """),
            {
                "user_id": DEMO_USER_ID,
                "subject_entity_id": memory["subject_entity_id"],
                "predicate": memory["predicate"],
                "predicate_type": memory["predicate_type"],
                "object_value": json.dumps(memory["object_value"]),
                "confidence": memory["confidence"],
                "confidence_factors": json.dumps({
                    "base": 0.7,
                    "reinforcement": 0.15,
                    "recency": 0.0,
                }),
                "reinforcement_count": memory["reinforcement_count"],
                "last_validated_at": datetime.now(UTC),
                "source_type": memory["source_type"],
                "source_memory_id": None,
                "extracted_from_event_id": event_ids[0] if event_ids else None,
                "status": "active",
                "embedding": json.dumps(embedding_list),
                "importance": memory["importance"],
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )

        row = result.fetchone()
        if row:
            memory_ids.append(row[0])

    await session.commit()

    logger.info("semantic_memories_created", count=len(memory_ids))

    return memory_ids


async def seed_memory_summaries(
    session: AsyncSession,
    embedding_service: OpenAIEmbeddingService,
    entity_map: dict,
    episodic_memory_ids: list[int],
    semantic_memory_ids: list[int],
) -> None:
    """Create memory summaries (consolidated knowledge).

    Args:
        session: Database session
        embedding_service: Embedding generation service
        entity_map: Entity ID mappings
        episodic_memory_ids: Episodic memory IDs to consolidate
        semantic_memory_ids: Semantic memory IDs to consolidate
    """
    logger.info("seeding_memory_summaries")

    acme_id = entity_map["Acme Corporation"]

    summary_text = (
        "Acme Corporation is a reliable customer with NET30 payment terms. "
        "They consistently pay 2-3 days before due dates. "
        "The user prefers to contact them via email on Fridays for payment confirmations."
    )

    # Check if summary already exists
    result = await session.execute(
        text("""
            SELECT summary_id FROM app.memory_summaries
            WHERE user_id = :user_id
              AND scope_type = :scope_type
              AND scope_identifier = :scope_identifier
        """),
        {
            "user_id": DEMO_USER_ID,
            "scope_type": "entity",
            "scope_identifier": acme_id,
        }
    )

    if result.fetchone():
        logger.info("memory_summary_already_exists", scope_identifier=acme_id)
    else:
        embedding = await embedding_service.generate_embedding(summary_text)

        # Convert embedding to JSON string for pgvector
        embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)

        await session.execute(
            text("""
                INSERT INTO app.memory_summaries (
                    user_id, scope_type, scope_identifier, summary_text, key_facts,
                    source_data, confidence, embedding, created_at
                )
                VALUES (
                    :user_id, :scope_type, :scope_identifier, :summary_text, :key_facts,
                    :source_data, :confidence, CAST(:embedding AS vector), :created_at
                )
            """),
        {
            "user_id": DEMO_USER_ID,
            "scope_type": "entity",
            "scope_identifier": acme_id,
            "summary_text": summary_text,
            "key_facts": json.dumps({
                "payment_behavior": {
                    "value": "Consistently pays 2-3 days before due date",
                    "confidence": 0.85,
                    "reinforced": 3,
                    "source_memory_ids": semantic_memory_ids,
                },
                "contact_preference": {
                    "value": "Email on Fridays for payment matters",
                    "confidence": 0.90,
                    "reinforced": 1,
                    "source_memory_ids": semantic_memory_ids,
                },
            }),
            "source_data": json.dumps({
                "episodic_ids": episodic_memory_ids,
                "semantic_ids": semantic_memory_ids,
                "session_ids": [str(SESSION_ID)],
                "time_range": {
                    "start": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
                    "end": datetime.now(UTC).isoformat(),
                },
            }),
            "confidence": 0.85,
            "embedding": json.dumps(embedding_list),
            "created_at": datetime.now(UTC),
        },
    )

    await session.commit()

    logger.info("memory_summaries_created", count=1)


async def seed_procedural_memories(
    session: AsyncSession,
    embedding_service: OpenAIEmbeddingService,
    episodic_memory_ids: list[int],
) -> None:
    """Create procedural memories (learned patterns).

    Args:
        session: Database session
        embedding_service: Embedding generation service
        episodic_memory_ids: Source episodic memories
    """
    logger.info("seeding_procedural_memories")

    trigger_pattern = "When user asks about customer payment status"
    embedding = await embedding_service.generate_embedding(trigger_pattern)

    # Convert embedding to JSON string for pgvector
    embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)

    await session.execute(
        text("""
            INSERT INTO app.procedural_memories (
                user_id, trigger_pattern, trigger_features, action_heuristic,
                action_structure, observed_count, confidence, embedding, created_at, updated_at
            )
            VALUES (
                :user_id, :trigger_pattern, :trigger_features, :action_heuristic,
                :action_structure, :observed_count, :confidence, CAST(:embedding AS vector), :created_at, :updated_at
            )
        """),
        {
            "user_id": DEMO_USER_ID,
            "trigger_pattern": trigger_pattern,
            "trigger_features": json.dumps({
                "intent": "query_payment",
                "entity_types": ["customer", "invoice"],
                "topics": ["payment", "status"],
            }),
            "action_heuristic": "Also retrieve payment history and typical timing patterns",
            "action_structure": json.dumps({
                "action_type": "augment",
                "queries": ["payment_history", "payment_patterns"],
                "predicates": ["payment_timing_pattern", "payment_terms"],
            }),
            "observed_count": 5,
            "confidence": 0.75,
            "embedding": json.dumps(embedding_list),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    )

    await session.commit()

    logger.info("procedural_memories_created", count=1)


async def seed_domain_ontology(session: AsyncSession) -> None:
    """Create domain ontology (entity relationships).

    Args:
        session: Database session
    """
    logger.info("seeding_domain_ontology")

    relations = [
        {
            "from_type": "customer",
            "relation_type": "has",
            "to_type": "sales_order",
            "cardinality": "one_to_many",
            "semantics": "Customer places sales orders",
            "join_spec": {
                "from_table": "domain.customers",
                "to_table": "domain.sales_orders",
                "join_on": "customer_id",
            },
        },
        {
            "from_type": "sales_order",
            "relation_type": "creates",
            "to_type": "work_order",
            "cardinality": "one_to_many",
            "semantics": "Sales order generates work orders",
            "join_spec": {
                "from_table": "domain.sales_orders",
                "to_table": "domain.work_orders",
                "join_on": "sales_order_id",
            },
        },
        {
            "from_type": "sales_order",
            "relation_type": "generates",
            "to_type": "invoice",
            "cardinality": "one_to_many",
            "semantics": "Sales order generates invoices",
            "join_spec": {
                "from_table": "domain.sales_orders",
                "to_table": "domain.invoices",
                "join_on": "sales_order_id",
            },
        },
        {
            "from_type": "invoice",
            "relation_type": "receives",
            "to_type": "payment",
            "cardinality": "one_to_many",
            "semantics": "Invoice receives payments",
            "join_spec": {
                "from_table": "domain.invoices",
                "to_table": "domain.payments",
                "join_on": "invoice_id",
            },
        },
        {
            "from_type": "work_order",
            "relation_type": "contains",
            "to_type": "task",
            "cardinality": "one_to_many",
            "semantics": "Work order contains tasks",
            "join_spec": {
                "from_table": "domain.work_orders",
                "to_table": "domain.tasks",
                "join_on": "work_order_id",
            },
        },
    ]

    for relation in relations:
        await session.execute(
            text("""
                INSERT INTO app.domain_ontology (
                    from_entity_type, relation_type, to_entity_type, cardinality,
                    relation_semantics, join_spec, created_at
                )
                VALUES (
                    :from_type, :relation_type, :to_type, :cardinality,
                    :semantics, :join_spec, :created_at
                )
                ON CONFLICT (from_entity_type, relation_type, to_entity_type) DO NOTHING
            """),
            {
                "from_type": relation["from_type"],
                "relation_type": relation["relation_type"],
                "to_type": relation["to_type"],
                "cardinality": relation["cardinality"],
                "semantics": relation["semantics"],
                "join_spec": json.dumps(relation["join_spec"]),
                "created_at": datetime.now(UTC),
            },
        )

    await session.commit()

    logger.info("domain_ontology_created", count=len(relations))


# ============================================================================
# Main Execution
# ============================================================================


async def seed_all() -> None:
    """Seed all databases with comprehensive demo data."""
    # Load settings
    settings = Settings()

    # Check for OpenAI API key
    if not settings.openai_api_key:
        logger.error("openai_api_key_missing")
        print("\n⚠️  OpenAI API key not found in environment")
        print("Set OPENAI_API_KEY environment variable to generate embeddings")
        print("\nSkipping seed - embeddings are required for vector similarity search\n")
        return

    # Initialize database
    init_db(settings)
    logger.info("database_initialized")

    # Initialize embedding service
    embedding_service = OpenAIEmbeddingService(api_key=settings.openai_api_key)

    # Seed databases
    try:
        async with get_db_session() as session:
            logger.info("starting_seed_process")

            # 1. Domain database
            domain_entities = await seed_domain_database(session)

            # 2. Canonical entities
            entity_map = await seed_canonical_entities(session, domain_entities)

            # 3. Entity aliases
            await seed_entity_aliases(session, entity_map)

            # 4. Chat events
            event_ids = await seed_chat_events(session)

            # 5. Episodic memories
            episodic_memory_ids = await seed_episodic_memories(
                session, embedding_service, event_ids, entity_map
            )

            # 6. Semantic memories
            semantic_memory_ids = await seed_semantic_memories(
                session, embedding_service, entity_map, event_ids
            )

            # 7. Memory summaries
            await seed_memory_summaries(
                session,
                embedding_service,
                entity_map,
                episodic_memory_ids,
                semantic_memory_ids,
            )

            # 8. Procedural memories
            await seed_procedural_memories(
                session, embedding_service, episodic_memory_ids
            )

            # 9. Domain ontology
            await seed_domain_ontology(session)

            logger.info(
                "seed_process_complete",
                embedding_tokens=embedding_service.total_tokens_used,
                estimated_cost=embedding_service.estimated_cost,
            )

            print("\n✅ Seed process complete!")
            print(f"   Embeddings generated: {embedding_service.total_tokens_used} tokens")
            print(f"   Estimated cost: ${embedding_service.estimated_cost:.4f}")
            print(f"   Demo user ID: {DEMO_USER_ID}")
            print(f"   Session ID: {SESSION_ID}\n")

    except Exception as e:
        logger.error("seed_process_failed", error=str(e), error_type=type(e).__name__)
        raise


def main():
    """Entry point for seed script."""
    asyncio.run(seed_all())


if __name__ == "__main__":
    main()
