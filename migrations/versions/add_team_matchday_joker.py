"""Add team_matchday_joker table

Revision ID: a1b2c3d4e5f6
Revises: 5a8740a3a9dc
Create Date: 2026-03-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '5a8740a3a9dc'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'team_matchday_joker',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('team.id', ondelete='CASCADE'), nullable=False),
        sa.Column('matchday_id', sa.Integer(), sa.ForeignKey('matchday.id', ondelete='CASCADE'), nullable=False),
        sa.Column('player_id', sa.Integer(), sa.ForeignKey('player.id', ondelete='SET NULL'), nullable=True),
        sa.UniqueConstraint('team_id', 'matchday_id', name='uq_team_matchday_joker'),
    )


def downgrade():
    op.drop_table('team_matchday_joker')

