"""Add player_racquet history table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'player_racquet',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('racquet_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('grip_size', sa.String(10), nullable=True),
        sa.Column('string_name', sa.String(100), nullable=True),
        sa.Column('string_tension', sa.Float(), nullable=True),
        sa.Column('is_owner', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_playing', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['player_id'], ['player.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['racquet_id'], ['racquet.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('player_racquet')

