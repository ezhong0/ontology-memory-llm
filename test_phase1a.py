"""Quick test script for Phase 1A implementation.

Tests the entity resolution flow with sample data.
"""
import asyncio
import uuid
from datetime import datetime, timezone

from src.config.settings import Settings
from src.domain.entities import CanonicalEntity
from src.domain.value_objects import EntityReference
from src.infrastructure.database.repositories import EntityRepository
from src.infrastructure.database.session import get_db_session, init_db


async def setup_test_data():
    """Create some test entities in the database."""
    settings = Settings()
    init_db(settings)

    async with get_db_session() as session:
        repo = EntityRepository(session)

        # Create Acme Corp entity
        acme = CanonicalEntity(
            entity_id="company_acme_123",
            entity_type="company",
            canonical_name="Acme Corporation",
            external_ref=EntityReference(
                table="companies",
                primary_key="company_id",
                primary_value="acme_123",
                display_name="Acme Corporation",
                properties={"industry": "Technology"},
            ),
            properties={"tier": "enterprise", "status": "active"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await repo.create(acme)
        print(f"✅ Created entity: {acme.canonical_name} (ID: {acme.entity_id})")

        # Create some aliases
        from src.domain.entities import EntityAlias

        alias1 = EntityAlias(
            canonical_entity_id="company_acme_123",
            alias_text="Acme Corp",
            alias_source="user_stated",
            confidence=0.9,
            user_id=None,  # Global alias
        )
        await repo.create_alias(alias1)
        print(f"✅ Created alias: '{alias1.alias_text}' -> {acme.canonical_name}")

        alias2 = EntityAlias(
            canonical_entity_id="company_acme_123",
            alias_text="ACME",
            alias_source="user_stated",
            confidence=0.85,
            user_id="test-user-123",  # User-specific alias
        )
        await repo.create_alias(alias2)
        print(f"✅ Created user alias: '{alias2.alias_text}' -> {acme.canonical_name}")

        await session.commit()
        print("\n✨ Test data setup complete!")
        print("\nNow test with:")
        print('curl -X POST http://localhost:8000/api/v1/chat/message \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -H "X-User-Id: test-user-123" \\')
        print('  -d \'{"session_id": "550e8400-e29b-41d4-a716-446655440000", "content": "I met with Acme Corp today", "role": "user"}\'')


if __name__ == "__main__":
    asyncio.run(setup_test_data())
