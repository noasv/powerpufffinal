"""Allow unknown opportunity data to remain NULL."""

from alembic import op
import sqlalchemy as sa

revision = "0004_nullable_opportunity_fields"
down_revision = "0003_opportunity_provenance"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("opportunities") as batch_op:
        batch_op.alter_column(
            "funding_amount_text",
            existing_type=sa.String(),
            nullable=True,
        )
        batch_op.alter_column(
            "cost_text",
            existing_type=sa.String(),
            nullable=True,
        )
        batch_op.alter_column(
            "language_requirements",
            existing_type=sa.String(),
            nullable=True,
        )


def downgrade():
    # Convert NULLs before restoring the old NOT NULL schema.
    op.execute(
        "UPDATE opportunities SET funding_amount_text='' "
        "WHERE funding_amount_text IS NULL"
    )
    op.execute(
        "UPDATE opportunities SET cost_text='' "
        "WHERE cost_text IS NULL"
    )
    op.execute(
        "UPDATE opportunities SET language_requirements='' "
        "WHERE language_requirements IS NULL"
    )

    with op.batch_alter_table("opportunities") as batch_op:
        batch_op.alter_column(
            "funding_amount_text",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            "cost_text",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            "language_requirements",
            existing_type=sa.String(),
            nullable=False,
        )
