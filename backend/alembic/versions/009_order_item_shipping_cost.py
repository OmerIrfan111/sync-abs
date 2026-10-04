"""V2.2: real shipping cost on order items, quoted via Shippo at routing
time. Null means no quote was available (missing weight data, no ship-from
configured, or a failed rate lookup) — never a fabricated estimate.

Revision ID: 009_order_item_shipping_cost
Revises: 008_order_item_routing_note
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = '009_order_item_shipping_cost'
down_revision = '008_order_item_routing_note'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('order_items', sa.Column('shipping_cost', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('order_items', 'shipping_cost')
