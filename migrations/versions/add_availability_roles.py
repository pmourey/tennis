"""Add plays_single plays_double is_substitute to player_matchday_availability

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('player_matchday_availability') as batch_op:
        batch_op.add_column(sa.Column('plays_single',  sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('plays_double',  sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('is_substitute', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('player_matchday_availability') as batch_op:
        batch_op.drop_column('is_substitute')
        batch_op.drop_column('plays_double')
        batch_op.drop_column('plays_single')

