"""Add default_shipping_charge to suppliers

Revision ID: 012_supplier_default_shipping
Revises: 011_shipping_and_upc_registry
Create Date: 2026-10-03
"""
from alembic import op
import sqlalchemy as sa

revision = '012_supplier_default_shipping'
down_revision = '011_shipping_and_upc_registry'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    sup_cols = [c['name'] for c in insp.get_columns('suppliers')]

    if 'default_shipping_charge' not in sup_cols:
        op.add_column('suppliers', sa.Column('default_shipping_charge', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    sup_cols = [c['name'] for c in insp.get_columns('suppliers')]

    if 'default_shipping_charge' in sup_cols:
        op.drop_column('suppliers', 'default_shipping_charge')
