"""enable_pg_trgm_extension

Revision ID: d624b2e7ef1f
Revises: 7b1104998645
Create Date: 2025-10-16 17:08:48.996384

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd624b2e7ef1f'
down_revision: Union[str, None] = '7b1104998645'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable pg_trgm extension for fuzzy matching.

    The pg_trgm extension provides trigram-based text similarity functions:
    - similarity(text, text) → float: Returns similarity score [0.0, 1.0]
    - word_similarity(text, text) → float: Word-based similarity
    - show_limit(): Current similarity threshold

    This enables fuzzy entity resolution for typos like "Kay Media" → "Kai Media".
    """
    # Enable pg_trgm extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Add GIN index on canonical_name for efficient trigram searches
    # This significantly speeds up similarity() queries
    op.create_index(
        "idx_entities_name_trgm",
        "canonical_entities",
        ["canonical_name"],
        unique=False,
        schema="app",
        postgresql_using="gin",
        postgresql_ops={"canonical_name": "gin_trgm_ops"}
    )


def downgrade() -> None:
    """Remove pg_trgm extension."""
    # Drop the GIN index
    op.drop_index("idx_entities_name_trgm", table_name="canonical_entities", schema="app")

    # Drop pg_trgm extension
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
