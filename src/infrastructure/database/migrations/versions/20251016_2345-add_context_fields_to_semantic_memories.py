"""add_context_fields_to_semantic_memories

Revision ID: 7f8e9a1b2c3d
Revises: bc58b75ebbeb
Create Date: 2025-10-16 23:45:00.000000

Add hybrid structured + natural language fields to semantic_memories table:
- original_text: Normalized triple as natural language (e.g., "Gai Media prefers Friday deliveries")
- source_text: Original chat message that created this memory
- related_entities: Array of all entity IDs mentioned (for multi-entity retrieval boosting)

These fields enable:
1. Human-readable memory display (original_text)
2. Full context preservation (source_text for explainability)
3. Better embeddings (natural language > structured triples)
4. Multi-entity retrieval (related_entities for entity overlap scoring)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7f8e9a1b2c3d'
down_revision: Union[str, None] = 'bc58b75ebbeb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add context fields to semantic_memories table.

    These fields complement the existing structured triple (subject-predicate-object)
    with natural language representations and source context.

    All fields are nullable to support existing records.
    """
    # Add original_text column (normalized natural language representation)
    op.add_column(
        'semantic_memories',
        sa.Column('original_text', sa.Text(), nullable=True),
        schema='app'
    )

    # Add source_text column (original chat message)
    op.add_column(
        'semantic_memories',
        sa.Column('source_text', sa.Text(), nullable=True),
        schema='app'
    )

    # Add related_entities column (array of entity IDs for multi-entity retrieval)
    op.add_column(
        'semantic_memories',
        sa.Column('related_entities', postgresql.ARRAY(sa.Text()), nullable=True),
        schema='app'
    )


def downgrade() -> None:
    """Remove context fields from semantic_memories table."""
    op.drop_column('semantic_memories', 'related_entities', schema='app')
    op.drop_column('semantic_memories', 'source_text', schema='app')
    op.drop_column('semantic_memories', 'original_text', schema='app')
