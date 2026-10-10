"""
One-off seed script: creates Listing + Order + OrderItem rows against the
*_ (Test Sandbox)_ marketplaces (inactive by default, MockXAdapter-backed) so
the real routing/PO pipeline can be exercised end-to-end against real
catalog/supplier data with zero risk of touching a live marketplace API or
spending real money (DRY_RUN=True simulates submit-live regardless).

Run inside the backend container:
    docker exec sync_backend python scripts/seed_test_routing_orders.py
"""
from decimal import Decimal
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.product import Product
from app.models.marketplace import Marketplace
from app.models.listing import Listing
from app.models.order import Order
from app.models.order_item import OrderItem

db = SessionLocal()

SCENARIOS = [
    {
        "marketplace_name": "eBay (Test Sandbox)",
        "sku": "S14863",
        "note": "Multi-supplier: TD SYNNEX ($370.89 delivered) should beat Ingram ($372.73 delivered)",
    },
    {
        "marketplace_name": "Amazon (Test Sandbox)",
        "sku": "JT3771",
        "note": "Multi-supplier: Ingram ($209.99 delivered) should beat TD SYNNEX ($277.52 delivered), and exercises the real Ingram freight-estimate call",
    },
    {
        "marketplace_name": "Shopify (Test Sandbox)",
        "sku": "DH-SAMS-T7-1TB",
        "note": "D&H-exclusive product — exercises the D&H-only routing path",
    },
    {
        "marketplace_name": "Walmart (Test Sandbox)",
        "sku": "DH-COR-DDR5-32G",
        "note": "D&H-exclusive product on the Walmart test channel",
    },
    {
        "marketplace_name": "eBay (Test Sandbox)",
        "sku": "NO-SUCH-SKU-TEST",
        "note": "Deliberately unmatched SKU — should come back UNROUTABLE with an honest routing_note, not silently stuck",
    },
]

created = []

for sc in SCENARIOS:
    marketplace = db.query(Marketplace).filter(Marketplace.name == sc["marketplace_name"]).first()
    if not marketplace:
        print(f"SKIP: marketplace '{sc['marketplace_name']}' not found")
        continue

    product = db.query(Product).filter(Product.sku == sc["sku"]).first()

    listing = None
    if product:
        listing = db.query(Listing).filter(
            Listing.product_id == product.id,
            Listing.marketplace_id == marketplace.id,
        ).first()
        if not listing:
            listing = Listing(
                product_id=product.id,
                marketplace_id=marketplace.id,
                external_listing_id=f"TEST-{marketplace.id}-{product.sku}",
                status="ACTIVE",
                selling_price=Decimal("149.99"),
                listed_qty=5,
                last_updated_at=datetime.now(timezone.utc),
            )
            db.add(listing)
            db.flush()

    order = Order(
        marketplace_id=marketplace.id,
        marketplace_order_id=f"TEST-ROUTING-{sc['sku']}",
        buyer_username="test_buyer",
        buyer_name="Routing Test Buyer",
        shipping_address={
            "name": "Routing Test Buyer", "street": "123 Test St",
            "city": "Dallas", "state": "TX", "zip": "75201", "country": "US",
        },
        order_total=Decimal("149.99"),
        marketplace_fees=Decimal("15.00"),
        currency="USD",
        status="PENDING_ROUTING",
        ordered_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=product.id if product else None,
        listing_id=listing.id if listing else None,
        marketplace_item_id=f"item-{sc['sku']}",
        sku=sc["sku"],
        title=product.title if product else sc["sku"],
        quantity=1,
        unit_price=Decimal("149.99"),
        status="PENDING",
    )
    db.add(item)
    db.commit()

    created.append((order.id, sc["marketplace_name"], sc["sku"], sc["note"]))

db.close()

print("\nCreated test orders:")
for order_id, mkt, sku, note in created:
    print(f"  Order #{order_id} on {mkt} — SKU {sku}")
    print(f"    expect: {note}")
