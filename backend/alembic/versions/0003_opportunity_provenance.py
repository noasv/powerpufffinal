"""Add qualified-discovery provenance to opportunities."""
from alembic import op
import sqlalchemy as sa
revision='0003_opportunity_provenance';down_revision='0002_personalization_fields';branch_labels=None;depends_on=None
def upgrade():
 columns={c['name'] for c in sa.inspect(op.get_bind()).get_columns('opportunities')}
 additions=[('source_type',sa.String(),False,'DEMO'),('source_domain',sa.String(),True,None),('canonical_source_url',sa.String(),True,None),('discovery_source_url',sa.String(),True,None),('source_quality',sa.String(),False,'DEMO'),('is_first_party',sa.Boolean(),False,sa.false()),('verification_notes',sa.Text(),True,None),('last_checked_at',sa.DateTime(),True,None)]
 for name,typ,nullable,default in additions:
  if name not in columns:op.add_column('opportunities',sa.Column(name,typ,nullable=nullable,server_default=default))
 with op.batch_alter_table('opportunities') as batch:
  batch.alter_column('funding_amount_text',existing_type=sa.String(),nullable=True)
  batch.alter_column('cost_text',existing_type=sa.String(),nullable=True)
  batch.alter_column('language_requirements',existing_type=sa.String(),nullable=True)
def downgrade():
 columns={c['name'] for c in sa.inspect(op.get_bind()).get_columns('opportunities')}
 with op.batch_alter_table('opportunities') as batch:
  for name in ('last_checked_at','verification_notes','is_first_party','source_quality','discovery_source_url','canonical_source_url','source_domain','source_type'):
   if name in columns:batch.drop_column(name)
  batch.alter_column('funding_amount_text',existing_type=sa.String(),nullable=False,server_default='Varies')
  batch.alter_column('cost_text',existing_type=sa.String(),nullable=False,server_default='Free')
  batch.alter_column('language_requirements',existing_type=sa.String(),nullable=False,server_default='English')
