"""V2.2 Phase 5: User roles for staff permissions

Revision ID: 007_user_roles
Revises: 006_product_restrictions
Create Date: 2026-09-23
"""
from alembic import op
import sqlalchemy as sa

revision = '007_user_roles'
down_revision = '006_product_restrictions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='operator'))
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE users SET role = 'admin' WHERE is_superuser = true"))


def downgrade() -> None:
    op.drop_column('users', 'role')
