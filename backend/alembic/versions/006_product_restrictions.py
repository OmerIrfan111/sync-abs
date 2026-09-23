"""V2.2 Phase 4: Product restriction management

Revision ID: 006_product_restrictions
Revises: 005_marketplace_fee_schedules
Create Date: 2026-09-23
"""
from alembic import op
import sqlalchemy as sa

revision = '006_product_restrictions'
down_revision = '005_marketplace_fee_schedules'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'product_restrictions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=True),
        sa.Column('category', sa.String(255), nullable=True),
        sa.Column('brand', sa.String(255), nullable=True),
        sa.Column('marketplace_id', sa.Integer(), sa.ForeignKey('marketplaces.id', ondelete='CASCADE'), nullable=True),
        sa.Column('restriction_type', sa.String(50), nullable=False, server_default='BLOCKED'),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_product_restrictions_id', 'product_restrictions', ['id'])
    op.create_index('ix_product_restrictions_product_id', 'product_restrictions', ['product_id'])
    op.create_index('ix_product_restrictions_category', 'product_restrictions', ['category'])
    op.create_index('ix_product_restrictions_brand', 'product_restrictions', ['brand'])
    op.create_index('ix_product_restrictions_marketplace_id', 'product_restrictions', ['marketplace_id'])


def downgrade() -> None:
    op.drop_table('product_restrictions')
