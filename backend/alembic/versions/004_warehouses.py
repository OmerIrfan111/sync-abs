"""V2.2 Phase 3: Multi-warehouse support

Revision ID: 004_warehouses
Revises: 003_credential_expiry
Create Date: 2026-09-23
"""
from alembic import op
import sqlalchemy as sa

revision = '004_warehouses'
down_revision = '003_credential_expiry'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'warehouses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('supplier_id', sa.Integer(), sa.ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        sa.UniqueConstraint('supplier_id', 'code', name='uq_warehouse_supplier_code'),
    )
    op.create_index('ix_warehouses_id', 'warehouses', ['id'])
    op.create_index('ix_warehouses_supplier_id', 'warehouses', ['supplier_id'])

    op.create_table(
        'warehouse_stock',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('supplier_product_id', sa.Integer(), sa.ForeignKey('supplier_products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('qty_available', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('stock_replenish_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        sa.UniqueConstraint('supplier_product_id', 'warehouse_id', name='uq_warehouse_stock_product_warehouse'),
    )
    op.create_index('ix_warehouse_stock_id', 'warehouse_stock', ['id'])
    op.create_index('ix_warehouse_stock_supplier_product_id', 'warehouse_stock', ['supplier_product_id'])
    op.create_index('ix_warehouse_stock_warehouse_id', 'warehouse_stock', ['warehouse_id'])


def downgrade() -> None:
    op.drop_table('warehouse_stock')
    op.drop_table('warehouses')
