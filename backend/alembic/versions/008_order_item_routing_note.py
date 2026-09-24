"""V2.2 Phase 6: routing_note on order items, so orders that can't be
routed (no matching supplier catalog entry, or no supplier with stock)
surface a real, visible reason instead of silently sitting at PENDING.

Revision ID: 008_order_item_routing_note
Revises: 007_user_roles
Create Date: 2026-09-24
"""
from alembic import op
import sqlalchemy as sa

revision = '008_order_item_routing_note'
down_revision = '007_user_roles'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('order_items', sa.Column('routing_note', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('order_items', 'routing_note')
