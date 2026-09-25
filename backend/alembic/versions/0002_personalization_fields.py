"""Add explicit project evidence and opportunity field restriction."""
from alembic import op
import sqlalchemy as sa
revision='0002_personalization_fields'; down_revision='0001'; branch_labels=None; depends_on=None
def upgrade():
 columns=lambda table:{c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}
 if 'projects' not in columns('profiles'): op.add_column('profiles',sa.Column('projects',sa.Text(),nullable=False,server_default=''))
 if 'field_restriction' not in columns('opportunities'): op.add_column('opportunities',sa.Column('field_restriction',sa.Boolean(),nullable=False,server_default=sa.false()))
def downgrade():
 columns=lambda table:{c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}
 if 'field_restriction' in columns('opportunities'): op.drop_column('opportunities','field_restriction')
 if 'projects' in columns('profiles'): op.drop_column('profiles','projects')
