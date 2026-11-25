"""Automatic fulfillment outcome on orders

Revision ID: 014_order_auto_fulfillment
Revises: 013_strip_placeholder_images
Create Date: 2026-11-25
"""
from alembic import op
import sqlalchemy as sa

revision = '014_order_auto_fulfillment'
down_revision = '013_strip_placeholder_images'
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = [c['name'] for c in insp.get_columns('orders')]
    if 'auto_order_status' not in cols:
        op.add_column('orders', sa.Column('auto_order_status', sa.String(30), nullable=True))
        op.create_index('ix_orders_auto_order_status', 'orders', ['auto_order_status'])
    if 'auto_order_note' not in cols:
        op.add_column('orders', sa.Column('auto_order_note', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_index('ix_orders_auto_order_status', table_name='orders')
    op.drop_column('orders', 'auto_order_note')
    op.drop_column('orders', 'auto_order_status')
