"""Key/value app settings (automatic-ordering switch)

Revision ID: 015_app_settings
Revises: 014_order_auto_fulfillment
Create Date: 2026-11-25
"""
from alembic import op
import sqlalchemy as sa

revision = '015_app_settings'
down_revision = '014_order_auto_fulfillment'
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if 'app_settings' not in insp.get_table_names():
        op.create_table(
            'app_settings',
            sa.Column('key', sa.String(100), primary_key=True),
            sa.Column('value', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table('app_settings')
