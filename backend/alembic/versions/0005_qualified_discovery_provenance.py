"""add qualified discovery provenance fields

Revision ID: 0005_qualified_discovery_provenance
Revises: 0004_nullable_opportunity_fields
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_qualified_discovery_provenance"
down_revision = "0004_nullable_opportunity_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "opportunities",
        sa.Column("canonical_source_url", sa.String(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("discovery_source_url", sa.String(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("source_quality", sa.String(), nullable=False, server_default="DEMO"),
    )
    op.add_column(
        "opportunities",
        sa.Column("is_first_party", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "opportunities",
        sa.Column("verification_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("opportunities", "last_checked_at")
    op.drop_column("opportunities", "verification_notes")
    op.drop_column("opportunities", "is_first_party")
    op.drop_column("opportunities", "source_quality")
    op.drop_column("opportunities", "discovery_source_url")
    op.drop_column("opportunities", "canonical_source_url")
