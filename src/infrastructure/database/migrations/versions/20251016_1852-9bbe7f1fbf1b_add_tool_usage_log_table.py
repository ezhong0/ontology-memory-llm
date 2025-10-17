"""add_tool_usage_log_table

Revision ID: 9bbe7f1fbf1b
Revises: d624b2e7ef1f
Create Date: 2025-10-16 18:52:52.154331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9bbe7f1fbf1b'
down_revision: Union[str, None] = 'd624b2e7ef1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tool_usage_log table for tracking LLM tool calling patterns.

    Vision Alignment:
    - Learning from usage (track what works)
    - Feedback loop infrastructure
    - Phase 2: Analyze patterns, optimize tool selection
    """
    # Create tool_usage_log table in app schema
    op.create_table(
        "tool_usage_log",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("conversation_id", sa.String(length=255), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column(
            "tools_called",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            comment="Array of {tool, arguments, iteration}",
        ),
        sa.Column("facts_count", sa.Integer(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "outcome_satisfaction",
            sa.Integer(),
            nullable=True,
            comment="NULL=unknown, 1=satisfied, 0=not satisfied",
        ),
        sa.Column("outcome_feedback", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="app",
        comment="Track which tool patterns work for learning",
    )

    # Create indexes for Phase 2 analysis
    op.create_index(
        "idx_tool_usage_conversation",
        "tool_usage_log",
        ["conversation_id"],
        unique=False,
        schema="app",
    )
    op.create_index(
        "idx_tool_usage_timestamp",
        "tool_usage_log",
        ["timestamp"],
        unique=False,
        schema="app",
    )
    # GIN index for JSONB queries on tool combinations
    op.create_index(
        "idx_tool_usage_tools_called",
        "tool_usage_log",
        ["tools_called"],
        unique=False,
        schema="app",
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Remove tool_usage_log table."""
    op.drop_index("idx_tool_usage_tools_called", table_name="tool_usage_log", schema="app")
    op.drop_index("idx_tool_usage_timestamp", table_name="tool_usage_log", schema="app")
    op.drop_index("idx_tool_usage_conversation", table_name="tool_usage_log", schema="app")
    op.drop_table("tool_usage_log", schema="app")
