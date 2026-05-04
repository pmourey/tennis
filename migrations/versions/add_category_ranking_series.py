"""add max_ranking_id and allowed_series to tournament_category

Revision ID: a1b2c3d4e5f6
Revises: 5a8740a3a9dc
Create Date: 2026-04-20
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '5a8740a3a9dc'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tournament_category') as batch_op:
        batch_op.add_column(sa.Column('max_ranking_id', sa.Integer,
                                      sa.ForeignKey('ranking.id'), nullable=True))
        batch_op.add_column(sa.Column('allowed_series', sa.String(20), nullable=True))


def downgrade():
    with op.batch_alter_table('tournament_category') as batch_op:
        batch_op.drop_column('max_ranking_id')
        batch_op.drop_column('allowed_series')
