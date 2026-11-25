"""Strip generic stock-photo placeholders from every product's images

Revision ID: 013_strip_placeholder_images
Revises: 012_supplier_default_shipping
Create Date: 2026-11-18

Every sync used to overwrite Product.images with three generic Unsplash stock
photos (a graphics card on a wall mount), clobbering real photos. Placeholders
are never stored now; this removes the ones already there for ALL products and
resets the "photo resolved" markers on products left with no real photo, so
the content backfill picks them up again.
"""
from alembic import op

revision = '013_strip_placeholder_images'
down_revision = '012_supplier_default_shipping'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE products
        SET images = COALESCE(
            (SELECT json_agg(u) FROM json_array_elements_text(images) AS u
             WHERE u NOT LIKE '%images.unsplash.com%'),
            '[]'::json)
        WHERE images::text LIKE '%images.unsplash.com%'
    """)
    op.execute("""
        UPDATE products
        SET specs_json = (specs_json::jsonb
            - 'image_status' - 'image_content_status' - 'image_content_checked_at'
            - 'image_content_key_used' - 'image_match_info')::json
        WHERE json_array_length(images) = 0
          AND specs_json->>'image_status' IN ('icecat', 'verified', 'supplier', 'manual')
    """)


def downgrade() -> None:
    pass
