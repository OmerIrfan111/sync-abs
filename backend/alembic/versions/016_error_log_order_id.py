"""Link alerts to the order they are about

Revision ID: 016_error_log_order_id
Revises: 015_app_settings
Create Date: 2026-11-26
"""
from alembic import op
import sqlalchemy as sa

revision = '016_error_log_order_id'
down_revision = '015_app_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if 'order_id' not in [c['name'] for c in insp.get_columns('error_logs')]:
        op.add_column('error_logs', sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True))
        op.create_index('ix_error_logs_order_id', 'error_logs', ['order_id'])


def downgrade() -> None:
    op.drop_index('ix_error_logs_order_id', table_name='error_logs')
    op.drop_column('error_logs', 'order_id')
