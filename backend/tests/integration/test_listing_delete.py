from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.models.product import Product
from app.models.marketplace import Marketplace
from app.models.listing import Listing
from app.services.listing_service import ListingService


def test_delete_pending_listing_still_attempts_real_withdraw(client, db_session):
    """
    Real incident (2026-10-07, product 00TF99): a Walmart MP_ITEM_MATCH feed
    can go genuinely live within seconds while our local status still says
    PENDING (reconciliation only catches up every 10 minutes). Deleting it
    while the local status was still PENDING used to skip the real withdraw
    entirely, leaving the item live and purchasable on Walmart's side with
    no local record left to manage it. The delete endpoint must attempt a
    live withdraw whenever a real external_listing_id exists, regardless of
    local status.
    """
    product = Product(sku="PENDING-DEL-TEST", title="Test Product", is_enabled=True)
    db_session.add(product)
    marketplace = Marketplace(name="Walmart", adapter_class="LiveWalmartAdapter")
    db_session.add(marketplace)
    db_session.commit()
    db_session.refresh(product)
    db_session.refresh(marketplace)

    listing = Listing(
        product_id=product.id, marketplace_id=marketplace.id,
        external_listing_id=product.sku, status="PENDING",
        selling_price=10, listed_qty=3, last_updated_at=datetime.now(timezone.utc),
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)

    # No retire_item on this adapter (spec-restricted) -> falls back to the
    # zero-stock withdraw path, same as any marketplace with no real delete.
    mock_adapter = MagicMock(spec=["withdraw_listing", "update_inventory", "update_price"])
    with patch.object(ListingService, "get_adapter_for_marketplace", return_value=mock_adapter):
        res = client.delete(f"/api/v1/listings/{listing.id}")

    assert res.status_code == 200
    mock_adapter.withdraw_listing.assert_called_once()
    assert db_session.query(Listing).filter(Listing.id == listing.id).first() is None


def test_delete_listing_uses_real_retirement_when_adapter_supports_it(client, db_session):
    """
    User feedback 2026-10-08: zero-stock alone isn't "removed" — it just
    hides the item from being purchasable while it likely still stays
    visible in Walmart's own search/browse (Walmart's own buyer-facing
    behavior, not something this app controls). "Remove" must mean actually
    gone from the marketplace's catalog when the marketplace supports a real
    delete — confirmed via Walmart's own "Retire an item" reference
    (DELETE /v3/items/{sku}).
    """
    product = Product(sku="RETIRE-DEL-TEST", title="Test Product", is_enabled=True)
    db_session.add(product)
    marketplace = Marketplace(name="Walmart", adapter_class="LiveWalmartAdapter")
    db_session.add(marketplace)
    db_session.commit()
    db_session.refresh(product)
    db_session.refresh(marketplace)

    listing = Listing(
        product_id=product.id, marketplace_id=marketplace.id,
        external_listing_id=product.sku, status="ACTIVE",
        selling_price=10, listed_qty=3, last_updated_at=datetime.now(timezone.utc),
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)

    mock_adapter = MagicMock(spec=["retire_item", "withdraw_listing"])
    with patch.object(ListingService, "get_adapter_for_marketplace", return_value=mock_adapter):
        res = client.delete(f"/api/v1/listings/{listing.id}")

    assert res.status_code == 200
    mock_adapter.retire_item.assert_called_once_with(product.sku)
    mock_adapter.withdraw_listing.assert_not_called()
    assert res.json()["marketplace_cleanup"] == "retired"
