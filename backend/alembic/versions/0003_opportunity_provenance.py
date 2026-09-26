"""Add discovery provenance and verification state."""
from alembic import op
import sqlalchemy as sa

revision = "0003_opportunity_provenance"
down_revision = "0002_personalization_fields"
branch_labels = None
depends_on = None


def upgrade():
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("opportunities")}
    columns = [
        sa.Column("source_url", sa.String(), nullable=False, server_default=""),
        sa.Column("source_domain", sa.String(), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(), nullable=False, server_default="DEMO"),
        sa.Column("verification_status", sa.String(), nullable=False, server_default="DEMO"),
        sa.Column("discovered_at", sa.DateTime(), nullable=True),
    ]
    for column in columns:
        if column.name not in existing:
            op.add_column("opportunities", column)
    op.create_index("ix_opportunities_source_url", "opportunities", ["source_url"], unique=False)
    op.create_index("ix_opportunities_verification_status", "opportunities", ["verification_status"], unique=False)
    op.execute("UPDATE opportunities SET source_label='Pathly Demo Dataset', source_type='DEMO', verification_status='DEMO' WHERE source_label IN ('Demo dataset', 'Pathly Demo Dataset')")


def downgrade():
    op.drop_index("ix_opportunities_verification_status", table_name="opportunities")
    op.drop_index("ix_opportunities_source_url", table_name="opportunities")
    for name in ("discovered_at", "verification_status", "source_type", "source_domain", "source_url"):
        op.drop_column("opportunities", name)
