"""V2.0: Orders, Order Items, Purchase Orders, Order Events

Revision ID: 002_v2_orders
Revises: 001_initial_schema
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa

revision = '002_v2_orders'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- orders ---
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('marketplace_id', sa.Integer(), sa.ForeignKey('marketplaces.id', ondelete='SET NULL'), nullable=True),
        sa.Column('marketplace_order_id', sa.String(200), nullable=False, unique=True),
        sa.Column('buyer_username', sa.String(200), nullable=True),
        sa.Column('buyer_name', sa.String(300), nullable=True),
        sa.Column('shipping_address', sa.JSON(), server_default='{}', nullable=False),
        sa.Column('order_total', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('marketplace_fees', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING_ROUTING'),
        sa.Column('ordered_at', sa.DateTime(), nullable=True),
        sa.Column('shipped_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_orders_id', 'orders', ['id'])
    op.create_index('ix_orders_marketplace_id', 'orders', ['marketplace_id'])
    op.create_index('ix_orders_marketplace_order_id', 'orders', ['marketplace_order_id'], unique=True)
    op.create_index('ix_orders_status', 'orders', ['status'])

    # --- order_items ---
    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sa.Column('listing_id', sa.Integer(), sa.ForeignKey('listings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('marketplace_item_id', sa.String(200), nullable=True),
        sa.Column('sku', sa.String(100), nullable=True),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('supplier_cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('supplier_id', sa.Integer(), sa.ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_order_items_id', 'order_items', ['id'])
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])
    op.create_index('ix_order_items_product_id', 'order_items', ['product_id'])
    op.create_index('ix_order_items_listing_id', 'order_items', ['listing_id'])
    op.create_index('ix_order_items_sku', 'order_items', ['sku'])
    op.create_index('ix_order_items_supplier_id', 'order_items', ['supplier_id'])

    # --- purchase_orders ---
    op.create_table(
        'purchase_orders',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('supplier_id', sa.Integer(), sa.ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('po_number', sa.String(100), nullable=False, unique=True),
        sa.Column('supplier_order_id', sa.String(200), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='DRAFT'),
        sa.Column('total_cost', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('tracking_number', sa.String(200), nullable=True),
        sa.Column('carrier', sa.String(100), nullable=True),
        sa.Column('shipping_address', sa.JSON(), server_default='{}', nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('shipped_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_purchase_orders_id', 'purchase_orders', ['id'])
    op.create_index('ix_purchase_orders_order_id', 'purchase_orders', ['order_id'])
    op.create_index('ix_purchase_orders_supplier_id', 'purchase_orders', ['supplier_id'])
    op.create_index('ix_purchase_orders_po_number', 'purchase_orders', ['po_number'], unique=True)
    op.create_index('ix_purchase_orders_status', 'purchase_orders', ['status'])

    # --- order_events ---
    op.create_table(
        'order_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('details', sa.JSON(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_order_events_id', 'order_events', ['id'])
    op.create_index('ix_order_events_order_id', 'order_events', ['order_id'])
    op.create_index('ix_order_events_event_type', 'order_events', ['event_type'])
    op.create_index('ix_order_events_created_at', 'order_events', ['created_at'])


def downgrade() -> None:
    op.drop_table('order_events')
    op.drop_table('purchase_orders')
    op.drop_table('order_items')
    op.drop_table('orders')
