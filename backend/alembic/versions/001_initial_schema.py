"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Suppliers
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('adapter_class', sa.String(length=255), nullable=False),
        sa.Column('credentials_encrypted', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_suppliers_id'), 'suppliers', ['id'], unique=False)

    # Marketplaces
    op.create_table(
        'marketplaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('adapter_class', sa.String(length=255), nullable=False),
        sa.Column('credentials_encrypted', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_marketplaces_id'), 'marketplaces', ['id'], unique=False)

    # Products
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('upc', sa.String(length=50), nullable=True),
        sa.Column('ean', sa.String(length=50), nullable=True),
        sa.Column('mpn', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('brand', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.Column('images', sa.JSON(), nullable=False),
        sa.Column('specs_json', sa.JSON(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=True)
    op.create_index(op.f('ix_products_upc'), 'products', ['upc'], unique=False)
    op.create_index(op.f('ix_products_ean'), 'products', ['ean'], unique=False)
    op.create_index(op.f('ix_products_mpn'), 'products', ['mpn'], unique=False)
    op.create_index(op.f('ix_products_brand'), 'products', ['brand'], unique=False)
    op.create_index(op.f('ix_products_category'), 'products', ['category'], unique=False)
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)

    # Supplier Products
    op.create_table(
        'supplier_products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('supplier_sku', sa.String(length=100), nullable=False),
        sa.Column('cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('qty_available', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('stock_status', sa.String(length=50), nullable=False, server_default='IN_STOCK'),
        sa.Column('availability_status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('shipping_info', sa.JSON(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_supplier_products_id'), 'supplier_products', ['id'], unique=False)
    op.create_index(op.f('ix_supplier_products_product_id'), 'supplier_products', ['product_id'], unique=False)
    op.create_index(op.f('ix_supplier_products_supplier_id'), 'supplier_products', ['supplier_id'], unique=False)
    op.create_index(op.f('ix_supplier_products_supplier_sku'), 'supplier_products', ['supplier_sku'], unique=False)

    # Listings
    op.create_table(
        'listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('marketplace_id', sa.Integer(), nullable=False),
        sa.Column('external_listing_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('selling_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('listed_qty', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['marketplace_id'], ['marketplaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_listings_id'), 'listings', ['id'], unique=False)
    op.create_index(op.f('ix_listings_marketplace_id'), 'listings', ['marketplace_id'], unique=False)
    op.create_index(op.f('ix_listings_product_id'), 'listings', ['product_id'], unique=False)
    op.create_index(op.f('ix_listings_external_listing_id'), 'listings', ['external_listing_id'], unique=False)

    # Pricing Rules
    op.create_table(
        'pricing_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('marketplace_id', sa.Integer(), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('fixed_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('percentage', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('marketplace_fee', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('desired_margin', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['marketplace_id'], ['marketplaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pricing_rules_id'), 'pricing_rules', ['id'], unique=False)
    op.create_index(op.f('ix_pricing_rules_marketplace_id'), 'pricing_rules', ['marketplace_id'], unique=False)
    op.create_index(op.f('ix_pricing_rules_product_id'), 'pricing_rules', ['product_id'], unique=False)

    # Inventory Rules
    op.create_table(
        'inventory_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('safety_buffer', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('out_of_stock_action', sa.String(length=50), nullable=False, server_default='SET_QUANTITY_ZERO'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_rules_id'), 'inventory_rules', ['id'], unique=False)
    op.create_index(op.f('ix_inventory_rules_product_id'), 'inventory_rules', ['product_id'], unique=False)

    # Supplier Priority
    op.create_table(
        'supplier_priorities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('priority_rank', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('selection_rule', sa.String(length=50), nullable=False, server_default='LOWEST_COST'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_supplier_priorities_id'), 'supplier_priorities', ['id'], unique=False)
    op.create_index(op.f('ix_supplier_priorities_product_id'), 'supplier_priorities', ['product_id'], unique=False)
    op.create_index(op.f('ix_supplier_priorities_supplier_id'), 'supplier_priorities', ['supplier_id'], unique=False)

    # Sync Logs
    op.create_table(
        'sync_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('supplier_id', sa.Integer(), nullable=True),
        sa.Column('field_changed', sa.String(length=100), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('synced_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sync_logs_id'), 'sync_logs', ['id'], unique=False)
    op.create_index(op.f('ix_sync_logs_product_id'), 'sync_logs', ['product_id'], unique=False)
    op.create_index(op.f('ix_sync_logs_supplier_id'), 'sync_logs', ['supplier_id'], unique=False)
    op.create_index(op.f('ix_sync_logs_synced_at'), 'sync_logs', ['synced_at'], unique=False)

    # Error Logs
    op.create_table(
        'error_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('error_type', sa.String(length=100), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('marketplace_id', sa.Integer(), nullable=True),
        sa.Column('supplier_id', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['marketplace_id'], ['marketplaces.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_error_logs_id'), 'error_logs', ['id'], unique=False)
    op.create_index(op.f('ix_error_logs_error_type'), 'error_logs', ['error_type'], unique=False)
    op.create_index(op.f('ix_error_logs_product_id'), 'error_logs', ['product_id'], unique=False)
    op.create_index(op.f('ix_error_logs_marketplace_id'), 'error_logs', ['marketplace_id'], unique=False)
    op.create_index(op.f('ix_error_logs_supplier_id'), 'error_logs', ['supplier_id'], unique=False)
    op.create_index(op.f('ix_error_logs_status'), 'error_logs', ['status'], unique=False)
    op.create_index(op.f('ix_error_logs_created_at'), 'error_logs', ['created_at'], unique=False)

def downgrade() -> None:
    op.drop_table('error_logs')
    op.drop_table('sync_logs')
    op.drop_table('supplier_priorities')
    op.drop_table('inventory_rules')
    op.drop_table('pricing_rules')
    op.drop_table('listings')
    op.drop_table('supplier_products')
    op.drop_table('products')
    op.drop_table('marketplaces')
    op.drop_table('suppliers')
    op.drop_table('users')
