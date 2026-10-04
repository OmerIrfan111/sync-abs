"""Resumable catalog sync cursor per supplier.

A real supplier catalog (Ingram Micro: ~14,000+ SKUs, D&H: unknown but large)
takes far longer to fully page through than one sync run's time budget
allows. Previously every run re-fetched the same first page-or-so and called
that a complete sync, so only a small, effectively arbitrary slice of each
supplier's real catalog was ever seen. This persists a resume cursor so
successive runs walk forward through the whole catalog instead of restarting
from page 1 every time.

Revision ID: 010_supplier_catalog_cursor
Revises: 009_order_item_shipping_cost
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa

revision = '010_supplier_catalog_cursor'
down_revision = '009_order_item_shipping_cost'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('suppliers', sa.Column('catalog_sync_cursor', sa.Text(), nullable=True))
    op.add_column('suppliers', sa.Column('catalog_sync_exhausted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('suppliers', 'catalog_sync_exhausted_at')
    op.drop_column('suppliers', 'catalog_sync_cursor')
