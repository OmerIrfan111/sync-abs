from decimal import Decimal
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest

from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace
from app.models.listing import Listing
from app.services.listing_service import ListingService


def _setup_product_and_supplier(db):
    supplier = Supplier(name="Test Supplier", adapter_class="MockSupplierAdapter", is_active=True)
    db.add(supplier)
    marketplace = Marketplace(name="Walmart", adapter_class="LiveWalmartAdapter", is_active=True)
    db.add(marketplace)
    db.commit()

    product = Product(sku="GATE-TEST-1", title="Gate Test Product", upc="051128788530", is_enabled=True)
    db.add(product)
    db.commit()

    sp = SupplierProduct(
        product_id=product.id, supplier_id=supplier.id, supplier_sku="GT-1",
        cost=Decimal("20.00"), qty_available=10, availability_status="ACTIVE",
        shipping_info={"weight_lbs": 2.0},
    )
    db.add(sp)
    db.commit()
    db.refresh(product)
    db.refresh(marketplace)
    return product, marketplace


def test_publish_blocked_when_not_matchable(db_session):
    product, marketplace = _setup_product_and_supplier(db_session)

    mock_adapter = MagicMock(spec=["search_walmart_catalog_by_gtin", "get_listing", "create_listing"])
    mock_adapter.search_walmart_catalog_by_gtin.return_value = []

    service = ListingService(db_session)
    with patch.object(service, "get_adapter_for_marketplace", return_value=mock_adapter):
        with pytest.raises(ValueError, match="isn't matchable"):
            service.publish_product_to_marketplace(product.id, marketplace.id)

    mock_adapter.create_listing.assert_not_called()
    db_session.refresh(product)
    assert product.specs_json.get("walmart_match_status") == "not_matchable"


def test_publish_proceeds_when_matchable(db_session):
    product, marketplace = _setup_product_and_supplier(db_session)

    mock_adapter = MagicMock(spec=["search_walmart_catalog_by_gtin", "get_listing", "create_listing"])
    mock_adapter.search_walmart_catalog_by_gtin.return_value = [{"itemId": "123"}]
    mock_adapter.get_listing.side_effect = Exception("404 not found")
    mock_adapter.create_listing.return_value = {
        "external_listing_id": product.sku, "status": "PENDING", "metadata": {},
    }

    service = ListingService(db_session)
    with patch.object(service, "get_adapter_for_marketplace", return_value=mock_adapter):
        listing = service.publish_product_to_marketplace(product.id, marketplace.id)

    assert listing.status == "PENDING"
    mock_adapter.create_listing.assert_called_once()


def test_publish_blocked_when_no_upc_on_file(db_session):
    """
    Real bug fixed 2026-10-09: a product with no UPC/EAN skipped the
    matchability check entirely (the old `and (product.upc or product.ean)`
    guard condition) and sailed through to a real MP_ITEM_MATCH submission
    unverified. Must be blocked instead — no GTIN means it can't be
    confirmed matchable at all.
    """
    product, marketplace = _setup_product_and_supplier(db_session)
    product.upc = None
    product.ean = None
    db_session.commit()

    mock_adapter = MagicMock(spec=["search_walmart_catalog_by_gtin", "get_listing", "create_listing"])

    service = ListingService(db_session)
    with patch.object(service, "get_adapter_for_marketplace", return_value=mock_adapter):
        with pytest.raises(ValueError, match="no UPC/EAN on file"):
            service.publish_product_to_marketplace(product.id, marketplace.id)

    mock_adapter.search_walmart_catalog_by_gtin.assert_not_called()
    mock_adapter.create_listing.assert_not_called()


def test_publish_blocked_when_matchability_check_itself_fails(db_session):
    """
    Real bug fixed 2026-10-09: when search_walmart_catalog_by_gtin() itself
    raised (network blip, Walmart API error), the old code caught it,
    logged a warning, and let the publish proceed "anyway" — an unverified
    product reaching a real feed submission. Must block instead: no
    confirmed match, no submission, regardless of why the check failed.
    """
    product, marketplace = _setup_product_and_supplier(db_session)

    mock_adapter = MagicMock(spec=["search_walmart_catalog_by_gtin", "get_listing", "create_listing"])
    mock_adapter.search_walmart_catalog_by_gtin.side_effect = ConnectionError("Walmart API unreachable")

    service = ListingService(db_session)
    with patch.object(service, "get_adapter_for_marketplace", return_value=mock_adapter):
        with pytest.raises(ValueError, match="Could not verify"):
            service.publish_product_to_marketplace(product.id, marketplace.id)

    mock_adapter.create_listing.assert_not_called()


def test_publish_blocked_when_listing_already_pending(db_session):
    product, marketplace = _setup_product_and_supplier(db_session)
    listing = Listing(
        product_id=product.id, marketplace_id=marketplace.id,
        external_listing_id=product.sku, status="PENDING",
        selling_price=10, listed_qty=5, last_updated_at=datetime.now(timezone.utc),
    )
    db_session.add(listing)
    db_session.commit()

    mock_adapter = MagicMock(spec=["search_walmart_catalog_by_gtin", "get_listing", "create_listing", "update_price", "update_inventory"])

    service = ListingService(db_session)
    with patch.object(service, "get_adapter_for_marketplace", return_value=mock_adapter):
        with pytest.raises(ValueError, match="still being processed"):
            service.publish_product_to_marketplace(product.id, marketplace.id)

    mock_adapter.create_listing.assert_not_called()
    mock_adapter.update_price.assert_not_called()
