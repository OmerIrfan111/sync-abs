"""Shipping charges tracking, historical audit, and marketplace UPC listing registry.

Revision ID: 011_shipping_and_upc_registry
Revises: 010_supplier_catalog_cursor
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
from app.core.upc_utils import normalize_upc

revision = '011_shipping_and_upc_registry'
down_revision = '010_supplier_catalog_cursor'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()
    sp_cols = [c['name'] for c in insp.get_columns('supplier_products')]

    # 1. SupplierProduct shipping fields
    if 'base_shipping_charge' not in sp_cols:
        op.add_column('supplier_products', sa.Column('base_shipping_charge', sa.Numeric(10, 2), nullable=True))
    if 'shipping_source' not in sp_cols:
        op.add_column('supplier_products', sa.Column('shipping_source', sa.String(length=50), nullable=True))
    if 'shipping_status' not in sp_cols:
        op.add_column('supplier_products', sa.Column('shipping_status', sa.String(length=50), server_default='valid', nullable=False))
    if 'shipping_updated_at' not in sp_cols:
        op.add_column('supplier_products', sa.Column('shipping_updated_at', sa.DateTime(), nullable=True))

    # 2. Product Shipping History Table
    if 'product_shipping_history' not in existing_tables:
        op.create_table(
            'product_shipping_history',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('supplier_id', sa.Integer(), nullable=False),
            sa.Column('supplier_product_id', sa.Integer(), nullable=True),
            sa.Column('shipping_charge', sa.Numeric(10, 2), nullable=False),
            sa.Column('source', sa.String(length=50), nullable=False),
            sa.Column('destination_zip', sa.String(length=20), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['supplier_product_id'], ['supplier_products.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_product_shipping_history_id'), 'product_shipping_history', ['id'], unique=False)
        op.create_index(op.f('ix_product_shipping_history_product_id'), 'product_shipping_history', ['product_id'], unique=False)
        op.create_index(op.f('ix_product_shipping_history_supplier_id'), 'product_shipping_history', ['supplier_id'], unique=False)
        op.create_index(op.f('ix_product_shipping_history_supplier_product_id'), 'product_shipping_history', ['supplier_product_id'], unique=False)

    # 3. Listing Registry Table
    if 'listing_registry' not in existing_tables:
        op.create_table(
            'listing_registry',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('normalized_upc', sa.String(length=50), nullable=False),
            sa.Column('marketplace', sa.String(length=100), nullable=False),
            sa.Column('marketplace_listing_id', sa.String(length=100), nullable=True),
            sa.Column('sku', sa.String(length=100), nullable=True),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=500), nullable=False),
            sa.Column('brand', sa.String(length=255), nullable=True),
            sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('marketplace', 'normalized_upc', name='uq_listing_registry_mkt_upc')
        )
        op.create_index(op.f('ix_listing_registry_id'), 'listing_registry', ['id'], unique=False)
        op.create_index(op.f('ix_listing_registry_normalized_upc'), 'listing_registry', ['normalized_upc'], unique=False)
        op.create_index(op.f('ix_listing_registry_marketplace'), 'listing_registry', ['marketplace'], unique=False)
        op.create_index(op.f('ix_listing_registry_product_id'), 'listing_registry', ['product_id'], unique=False)

    # 4. Backfill from existing products & listings
    bind = op.get_bind()
    rows = bind.execute(text("""
        SELECT l.id AS listing_id, l.marketplace_id, l.external_listing_id, l.status, l.created_at,
               m.name AS marketplace_name,
               p.id AS product_id, p.sku, p.upc, p.ean, p.title, p.brand
        FROM listings l
        JOIN marketplaces m ON l.marketplace_id = m.id
        JOIN products p ON l.product_id = p.id
    """)).fetchall()

    seen_mkt_upc = set()
    conflicts_found = []

    for row in rows:
        raw_code = row.upc or row.ean
        if not raw_code:
            continue
        try:
            norm = normalize_upc(raw_code)
        except Exception:
            continue

        mkt = (row.marketplace_name or "unknown").strip().lower()
        key = (mkt, norm)

        if key in seen_mkt_upc:
            conflicts_found.append({
                "marketplace": mkt,
                "normalized_upc": norm,
                "product_id": row.product_id,
                "title": row.title,
                "listing_id": row.listing_id,
            })
            continue

        seen_mkt_upc.add(key)
        bind.execute(text("""
            INSERT INTO listing_registry (normalized_upc, marketplace, marketplace_listing_id, sku, product_id, title, brand, status, created_at, updated_at)
            VALUES (:normalized_upc, :marketplace, :marketplace_listing_id, :sku, :product_id, :title, :brand, :status, :created_at, :updated_at)
        """), {
            "normalized_upc": norm,
            "marketplace": mkt,
            "marketplace_listing_id": row.external_listing_id,
            "sku": row.sku,
            "product_id": row.product_id,
            "title": row.title or "Untitled",
            "brand": row.brand,
            "status": row.status or "ACTIVE",
            "created_at": row.created_at or sa.func.now(),
            "updated_at": sa.func.now()
        })

    if conflicts_found:
        print("\n=======================================================")
        print("MIGRATION REPORT: Pre-existing duplicate UPCs detected in database:")
        for c in conflicts_found:
            print(f"  [CONFLICT] Marketplace: {c['marketplace']} | UPC: {c['normalized_upc']} | Product #{c['product_id']} '{c['title']}'")
        print("Pre-existing conflicting records were NOT deleted or modified.")
        print("=======================================================\n")


def downgrade() -> None:
    op.drop_table('listing_registry')
    op.drop_table('product_shipping_history')
    op.drop_column('supplier_products', 'shipping_updated_at')
    op.drop_column('supplier_products', 'shipping_status')
    op.drop_column('supplier_products', 'shipping_source')
    op.drop_column('supplier_products', 'base_shipping_charge')
