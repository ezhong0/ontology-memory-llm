"""refactor_triples_to_entities

Revision ID: a1b2c3d4e5f6
Revises: 7f8e9a1b2c3d
Create Date: 2025-10-17 00:00:00.000000

Major refactor: Transform semantic memories from structured triples (SPO)
to entity-tagged natural language with importance scoring.

Changes:
- Remove: subject_entity_id, predicate, predicate_type, object_value,
  reinforcement_count, last_validated_at, original_text, related_entities
- Add: content, entities, metadata, last_accessed_at
- Update: importance calculation, indexes

Data Migration:
- Preserves all existing memories
- Converts triple structure to natural language
- Stores original predicate info in metadata for audit trail
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '7f8e9a1b2c3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Refactor semantic memories from triples to entity-tagged natural language."""

    # Step 1: Add new columns (nullable initially for migration)
    op.add_column(
        'semantic_memories',
        sa.Column('content', sa.Text(), nullable=True),
        schema='app'
    )

    op.add_column(
        'semantic_memories',
        sa.Column('entities', postgresql.ARRAY(sa.Text()), nullable=True),
        schema='app'
    )

    op.add_column(
        'semantic_memories',
        sa.Column('memory_metadata', postgresql.JSONB(), nullable=True),
        schema='app'
    )

    op.add_column(
        'semantic_memories',
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        schema='app'
    )

    # Step 2: Migrate existing data
    # Convert triple structure to natural language + entities
    op.execute(text("""
        UPDATE app.semantic_memories
        SET
            -- Content: Construct from triple (original_text doesn't exist in current schema)
            content = subject_entity_id || ' ' || predicate || ': ' ||
                COALESCE(object_value->>'value', object_value::text),

            -- Entities: Convert subject_entity_id to array (related_entities doesn't exist)
            entities = ARRAY[subject_entity_id],

            -- Metadata: Store confirmation count + original triple info for audit trail
            memory_metadata = jsonb_build_object(
                'confirmation_count', COALESCE(reinforcement_count - 1, 0),
                'migrated_from_triple', true,
                'original_predicate', predicate,
                'original_predicate_type', predicate_type,
                'original_object_value', object_value
            ),

            -- Last accessed: Use last_validated_at if available, else updated_at
            last_accessed_at = COALESCE(last_validated_at, updated_at),

            -- Importance: Calculate from confidence (Phase 1 formula: 0.3 + confidence * 0.6)
            importance = GREATEST(0.3, LEAST(1.0, 0.3 + (confidence * 0.6)))

        WHERE content IS NULL;
    """))

    # Step 3: Make new columns NOT NULL now that data is migrated
    op.alter_column(
        'semantic_memories',
        'content',
        nullable=False,
        schema='app'
    )

    op.alter_column(
        'semantic_memories',
        'entities',
        nullable=False,
        schema='app'
    )

    op.alter_column(
        'semantic_memories',
        'last_accessed_at',
        nullable=False,
        schema='app'
    )

    # Step 4: Drop old predicate-based indexes BEFORE dropping columns
    # (dropping columns will auto-drop indexes, so we do this first to avoid errors)
    try:
        op.drop_index('idx_semantic_entity_pred', table_name='semantic_memories', schema='app')
    except Exception:
        pass  # Index might not exist or already dropped

    try:
        op.drop_index('idx_semantic_memories_entity_pred_user', table_name='semantic_memories', schema='app')
    except Exception:
        pass  # Index might not exist

    try:
        op.drop_index('idx_semantic_memories_user_subject', table_name='semantic_memories', schema='app')
    except Exception:
        pass  # Index might not exist

    # Step 5: Drop old triple-based columns
    op.drop_column('semantic_memories', 'subject_entity_id', schema='app')
    op.drop_column('semantic_memories', 'predicate', schema='app')
    op.drop_column('semantic_memories', 'predicate_type', schema='app')
    op.drop_column('semantic_memories', 'object_value', schema='app')
    op.drop_column('semantic_memories', 'reinforcement_count', schema='app')
    op.drop_column('semantic_memories', 'confidence_factors', schema='app')
    op.drop_column('semantic_memories', 'last_validated_at', schema='app')
    op.drop_column('semantic_memories', 'original_text', schema='app')
    op.drop_column('semantic_memories', 'related_entities', schema='app')

    # Step 6: Add new entity-based indexes
    op.create_index(
        'idx_semantic_entities_gin',
        'semantic_memories',
        ['entities'],
        unique=False,
        postgresql_using='gin',
        schema='app'
    )

    op.create_index(
        'idx_semantic_user_importance',
        'semantic_memories',
        ['user_id', text('importance DESC')],
        unique=False,
        schema='app'
    )

    # Step 7: Add importance constraint
    op.create_check_constraint(
        'valid_importance',
        'semantic_memories',
        'importance >= 0 AND importance <= 1',
        schema='app'
    )


def downgrade() -> None:
    """Reverse migration: Entity-tagged back to triples (lossy)."""

    # Note: This downgrade is lossy - we can't perfectly reconstruct triples
    # but we preserve what we can from metadata

    # Step 1: Add back old columns
    op.add_column(
        'semantic_memories',
        sa.Column('subject_entity_id', sa.Text(), nullable=True),
        schema='app'
    )

    op.add_column(
        'semantic_memories',
        sa.Column('predicate', sa.Text(), nullable=True),
        schema='app'
    )

    op.add_column(
        'semantic_memories',
        sa.Column('predicate_type', sa.Text(), nullable=True),
        schema='app'
    )

    op.add_column(
        'semantic_memories',
        sa.Column('object_value', postgresql.JSONB(), nullable=True),
        schema='app'
    )

    op.add_column(
        'semantic_memories',
        sa.Column('reinforcement_count', sa.Integer(), nullable=True),
        schema='app'
    )

    op.add_column(
        'semantic_memories',
        sa.Column('confidence_factors', postgresql.JSONB(), nullable=True),
        schema='app'
    )

    op.add_column(
        'semantic_memories',
        sa.Column('last_validated_at', sa.DateTime(timezone=True), nullable=True),
        schema='app'
    )

    op.add_column(
        'semantic_memories',
        sa.Column('original_text', sa.Text(), nullable=True),
        schema='app'
    )

    op.add_column(
        'semantic_memories',
        sa.Column('related_entities', postgresql.ARRAY(sa.Text()), nullable=True),
        schema='app'
    )

    # Step 2: Restore data from metadata where possible
    op.execute(text("""
        UPDATE app.semantic_memories
        SET
            subject_entity_id = entities[1],  -- Take first entity as subject
            predicate = COALESCE(memory_metadata->>'original_predicate', 'unknown'),
            predicate_type = COALESCE(memory_metadata->>'original_predicate_type', 'attribute'),
            object_value = COALESCE(
                (memory_metadata->'original_object_value')::jsonb,
                jsonb_build_object('value', content)
            ),
            reinforcement_count = COALESCE((memory_metadata->>'confirmation_count')::int + 1, 1),
            last_validated_at = last_accessed_at
        WHERE subject_entity_id IS NULL;
    """))

    # Step 3: Make old columns NOT NULL
    op.alter_column('semantic_memories', 'subject_entity_id', nullable=False, schema='app')
    op.alter_column('semantic_memories', 'predicate', nullable=False, schema='app')
    op.alter_column('semantic_memories', 'predicate_type', nullable=False, schema='app')
    op.alter_column('semantic_memories', 'object_value', nullable=False, schema='app')
    op.alter_column('semantic_memories', 'reinforcement_count', nullable=False, schema='app')

    # Step 4: Drop new columns
    op.drop_column('semantic_memories', 'content', schema='app')
    op.drop_column('semantic_memories', 'entities', schema='app')
    op.drop_column('semantic_memories', 'memory_metadata', schema='app')
    op.drop_column('semantic_memories', 'last_accessed_at', schema='app')

    # Step 5: Restore old indexes
    op.drop_index('idx_semantic_entities_gin', table_name='semantic_memories', schema='app')
    op.drop_index('idx_semantic_user_importance', table_name='semantic_memories', schema='app')
    op.drop_constraint('valid_importance', 'semantic_memories', schema='app')

    op.create_index(
        'idx_semantic_entity_pred',
        'semantic_memories',
        ['subject_entity_id', 'predicate'],
        unique=False,
        schema='app'
    )
