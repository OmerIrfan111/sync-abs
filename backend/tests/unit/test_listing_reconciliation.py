from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.models.product import Product
from app.models.marketplace import Marketplace
from app.models.listing import Listing
from app.models.sync_log import SyncLog
from app.services.listing_service import ListingService


def _make_product(db, sku="WM-TEST-1"):
    p = Product(sku=sku, title="Test Product", is_enabled=True)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _make_walmart_marketplace(db):
    m = Marketplace(name="Walmart", adapter_class="LiveWalmartAdapter")
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def test_reconcile_promotes_to_active_on_real_success(db_session):
    product = _make_product(db_session)
    marketplace = _make_walmart_marketplace(db_session)
    listing = Listing(
        product_id=product.id, marketplace_id=marketplace.id,
        external_listing_id=product.sku, status="PENDING",
        selling_price=10, listed_qty=1, last_updated_at=datetime.now(timezone.utc),
    )
    db_session.add(listing)
    db_session.add(SyncLog(product_id=product.id, field_changed="walmart_feed_id", new_value="FEED123"))
    db_session.commit()

    service = ListingService(db_session)
    mock_adapter = MagicMock()
    mock_adapter.get_feed_status.return_value = {
        "feedStatus": "PROCESSED",
        "itemsSucceeded": 1,
        "itemDetails": {"itemIngestionStatus": [{"ingestionStatus": "SUCCESS"}]},
    }
    with patch.object(service, "get_adapter_for_marketplace", return_value=mock_adapter):
        result = service.reconcile_pending_async_listings()

    db_session.refresh(listing)
    assert result["active"] == 1
    assert listing.status == "ACTIVE"
    # MP_ITEM_MATCH has no quantity field — Walmart creates the item with 0
    # stock by default, so the first moment we know it's really live is
    # exactly when a real inventory push needs to happen, or it's listed
    # but unpurchasable (real bug found 2026-10-07 on product 00TF99).
    mock_adapter.update_inventory.assert_called_once_with(product.sku, product.sku, 1)


def test_reconcile_marks_error_on_real_failure(db_session):
    product = _make_product(db_session, sku="WM-TEST-2")
    marketplace = _make_walmart_marketplace(db_session)
    listing = Listing(
        product_id=product.id, marketplace_id=marketplace.id,
        external_listing_id=product.sku, status="PENDING",
        selling_price=10, listed_qty=1, last_updated_at=datetime.now(timezone.utc),
    )
    db_session.add(listing)
    db_session.add(SyncLog(product_id=product.id, field_changed="walmart_feed_id", new_value="FEED456"))
    db_session.commit()

    service = ListingService(db_session)
    mock_adapter = MagicMock()
    mock_adapter.get_feed_status.return_value = {
        "feedStatus": "PROCESSED",
        "itemsSucceeded": 0,
        "itemDetails": {"itemIngestionStatus": [{
            "ingestionStatus": "DATA_ERROR",
            "ingestionErrors": {"ingestionError": [{"code": "ERR_INT_SYS_01010010"}]},
        }]},
    }
    with patch.object(service, "get_adapter_for_marketplace", return_value=mock_adapter):
        result = service.reconcile_pending_async_listings()

    db_session.refresh(listing)
    assert result["failed"] == 1
    assert listing.status == "ERROR"


def test_reconcile_leaves_still_processing_as_pending(db_session):
    product = _make_product(db_session, sku="WM-TEST-3")
    marketplace = _make_walmart_marketplace(db_session)
    listing = Listing(
        product_id=product.id, marketplace_id=marketplace.id,
        external_listing_id=product.sku, status="PENDING",
        selling_price=10, listed_qty=1, last_updated_at=datetime.now(timezone.utc),
    )
    db_session.add(listing)
    db_session.add(SyncLog(product_id=product.id, field_changed="walmart_feed_id", new_value="FEED789"))
    db_session.commit()

    service = ListingService(db_session)
    mock_adapter = MagicMock()
    mock_adapter.get_feed_status.return_value = {
        "feedStatus": "RECEIVED",
        "itemsSucceeded": 0,
        "itemDetails": {"itemIngestionStatus": []},
    }
    with patch.object(service, "get_adapter_for_marketplace", return_value=mock_adapter):
        result = service.reconcile_pending_async_listings()

    db_session.refresh(listing)
    assert result["still_pending"] == 1
    assert listing.status == "PENDING"


def test_reconcile_skips_listing_with_no_feed_id_on_file(db_session):
    product = _make_product(db_session, sku="WM-TEST-4")
    marketplace = _make_walmart_marketplace(db_session)
    listing = Listing(
        product_id=product.id, marketplace_id=marketplace.id,
        external_listing_id=product.sku, status="PENDING",
        selling_price=10, listed_qty=1, last_updated_at=datetime.now(timezone.utc),
    )
    db_session.add(listing)
    db_session.commit()

    service = ListingService(db_session)
    mock_adapter = MagicMock()
    with patch.object(service, "get_adapter_for_marketplace", return_value=mock_adapter):
        result = service.reconcile_pending_async_listings()

    db_session.refresh(listing)
    mock_adapter.get_feed_status.assert_not_called()
    assert listing.status == "PENDING"
    assert result == {"active": 0, "failed": 0, "still_pending": 0}
