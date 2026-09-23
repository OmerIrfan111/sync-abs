"""V2.2 Phase 4: Marketplace fee schedules

Revision ID: 005_marketplace_fee_schedules
Revises: 004_warehouses
Create Date: 2026-09-23
"""
from alembic import op
import sqlalchemy as sa

revision = '005_marketplace_fee_schedules'
down_revision = '004_warehouses'
branch_labels = None
depends_on = None

# This project's own previously-documented default fee assumptions
# (see CLAUDE.md: "Marketplace fee modeling (eBay 13.25%, Amazon 15%)").
# Formalized here as editable defaults, not fabricated new figures.
KNOWN_DEFAULT_FEES = {
    "eBay": ("13.25", "Standard eBay final value fee (most categories). Verify against your actual category and store subscription tier."),
    "Amazon": ("15.00", "Standard Amazon referral fee (most categories). Verify against your actual category — referral fees range roughly 8-45% by category."),
}


def upgrade() -> None:
    op.create_table(
        'marketplace_fee_schedules',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('marketplace_id', sa.Integer(), sa.ForeignKey('marketplaces.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('fee_percentage', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_marketplace_fee_schedules_id', 'marketplace_fee_schedules', ['id'])
    op.create_index('ix_marketplace_fee_schedules_marketplace_id', 'marketplace_fee_schedules', ['marketplace_id'], unique=True)

    conn = op.get_bind()
    marketplaces = conn.execute(sa.text("SELECT id, name FROM marketplaces")).fetchall()
    for mp_id, mp_name in marketplaces:
        for known_name, (fee, notes) in KNOWN_DEFAULT_FEES.items():
            if known_name.lower() in (mp_name or "").lower():
                conn.execute(
                    sa.text(
                        "INSERT INTO marketplace_fee_schedules (marketplace_id, fee_percentage, notes, created_at) "
                        "VALUES (:mp_id, :fee, :notes, now())"
                    ),
                    {"mp_id": mp_id, "fee": fee, "notes": notes},
                )
                break


def downgrade() -> None:
    op.drop_table('marketplace_fee_schedules')
