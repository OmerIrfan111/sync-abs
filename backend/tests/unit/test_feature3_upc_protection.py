import pytest
from app.core.upc_utils import normalize_upc, calculate_check_digit
from app.models.product import Product
from app.models.listing_registry import ListingRegistry
from app.services.upc_protection_service import UpcProtectionService


def test_upc_normalization_and_validation():
    """
    Feature 3: Verify UPC normalization, dashes/spaces stripping, check digit validation,
    and UPC-A vs EAN-13 equivalency.
    """
    # Valid UPC-A: 012345678905
    assert normalize_upc("012345678905") == "0012345678905"
    assert normalize_upc("0-12345-67890-5") == "0012345678905"
    assert normalize_upc(" 0 12345 67890 5 ") == "0012345678905"

    # EAN-13 equivalent starting with 0: 0012345678905
    assert normalize_upc("0012345678905") == "0012345678905"

    # Both forms normalize to identical string
    assert normalize_upc("012345678905") == normalize_upc("0012345678905")

    # Invalid check digit
    with pytest.raises(ValueError) as exc:
        normalize_upc("012345678909")
    assert "invalid check digit" in str(exc.value)

    # Malformed non-numeric
    with pytest.raises(ValueError) as exc:
        normalize_upc("01234567890A")
    assert "numeric digits" in str(exc.value)

    # Invalid length
    with pytest.raises(ValueError) as exc:
        normalize_upc("12345")
    assert "invalid length" in str(exc.value)


def test_same_marketplace_upc_conflict_iphone_vs_cable(db_session):
    """
    Feature 3: iPhone vs cable on the same marketplace -> BLOCK as 'upc_conflict'
    """
    service = UpcProtectionService(db_session)
    valid_upc = "012345678905"
    norm_upc = normalize_upc(valid_upc)

    # Product 1: iPhone already listed on Amazon
    iphone = Product(sku="IPHONE-12-BLK", title="Apple iPhone 12 64GB Black", brand="Apple", upc=valid_upc)
    db_session.add(iphone)
    db_session.commit()

    service.register_listing(product=iphone, marketplace_name="Amazon", marketplace_listing_id="B08L5WHFT9")

    # Product 2: Cable with the SAME UPC trying to upload to Amazon
    cable = Product(sku="CABLE-CAT6-6IN", title="CAT6 Ethernet Patch Cable 6 inch", brand="Generic", upc=valid_upc)
    db_session.add(cable)
    db_session.commit()

    result = service.check_product_for_upload(product=cable, marketplace_name="Amazon")
    assert result.status == "blocked_upc_conflict"
    assert "already listed as 'Apple iPhone 12" in result.message
    assert "amazon" in result.message.lower()


def test_cross_marketplace_upc_conflict_iphone_vs_cable(db_session):
    """
    Feature 3: iPhone on Amazon vs cable on eBay with same UPC -> BLOCK as 'blocked_cross_marketplace_conflict'
    """
    service = UpcProtectionService(db_session)
    valid_upc = "012345678905"

    iphone = Product(sku="IPHONE-12-WHITE", title="Apple iPhone 12 128GB White", brand="Apple", upc=valid_upc)
    db_session.add(iphone)
    db_session.commit()

    service.register_listing(product=iphone, marketplace_name="Amazon", marketplace_listing_id="B08L5WHXYZ")

    # Cable with same UPC trying to upload to eBay
    cable = Product(sku="SMA-MALE-CONN", title="SMA Male RF Coaxial Connector", brand="Wilson", upc=valid_upc)
    db_session.add(cable)
    db_session.commit()

    result = service.check_product_for_upload(product=cable, marketplace_name="eBay")
    assert result.status == "blocked_cross_marketplace_conflict"
    assert "already listed as 'Apple iPhone 12" in result.message
    assert "amazon" in result.message.lower()


def test_same_iphone_on_two_marketplaces_allowed(db_session):
    """
    Feature 3: Same iPhone product on two different marketplaces -> ALLOWED
    """
    service = UpcProtectionService(db_session)
    valid_upc = "012345678905"

    iphone = Product(sku="IPHONE-12-BLUE", title="Apple iPhone 12 64GB Blue", brand="Apple", upc=valid_upc)
    db_session.add(iphone)
    db_session.commit()

    service.register_listing(product=iphone, marketplace_name="Amazon", marketplace_listing_id="B08L5BLUE1")

    # Try listing the same iPhone product on eBay
    result = service.check_product_for_upload(product=iphone, marketplace_name="eBay")
    assert result.status == "allowed"
    assert not result.is_blocked()


def test_same_iphone_twice_on_one_marketplace_blocked(db_session):
    """
    Feature 3: Duplicate listing of the same product on the same marketplace -> BLOCK as 'duplicate_listing'
    """
    service = UpcProtectionService(db_session)
    valid_upc = "012345678905"

    iphone1 = Product(sku="IPHONE-12-A", title="Apple iPhone 12 64GB Blue", brand="Apple", upc=valid_upc)
    iphone2 = Product(sku="IPHONE-12-B", title="Apple iPhone 12 64GB Blue Smartphone", brand="Apple", upc=valid_upc)
    db_session.add_all([iphone1, iphone2])
    db_session.commit()

    service.register_listing(product=iphone1, marketplace_name="Amazon", marketplace_listing_id="B08L5BLUE1")

    result = service.check_product_for_upload(product=iphone2, marketplace_name="Amazon")
    assert result.status == "blocked_duplicate_listing"
    assert result.is_blocked()


def test_batch_level_conflict_rejects_both():
    """
    Feature 3: Inside one upload batch, if two different products share a UPC,
    reject BOTH and report them.
    """
    service = UpcProtectionService(None)
    valid_upc = "012345678905"

    batch = [
        {"id": 1, "sku": "IPHONE", "title": "Apple iPhone 12 64GB", "brand": "Apple", "upc": valid_upc, "marketplace": "Amazon"},
        {"id": 2, "sku": "CABLE", "title": "CAT6 Ethernet Cable 10ft", "brand": "Generic", "upc": valid_upc, "marketplace": "Amazon"},
    ]

    results = service.check_batch_for_conflicts(batch)
    assert len(results) == 2
    assert results["1"].status == "blocked_batch_duplicate"
    assert results["2"].status == "blocked_batch_duplicate"


def test_concurrent_upload_race_caught_by_db_constraint(db_session):
    """
    Feature 3: Database unique constraint catches race condition on (marketplace, normalized_upc).
    """
    service = UpcProtectionService(db_session)
    valid_upc = "012345678905"
    norm_upc = normalize_upc(valid_upc)

    p1 = Product(sku="PROD-RACE-1", title="Product 1", upc=valid_upc)
    p2 = Product(sku="PROD-RACE-2", title="Product 2", upc=valid_upc)
    db_session.add_all([p1, p2])
    db_session.commit()

    # Direct registration 1
    service.register_listing(product=p1, marketplace_name="Amazon", marketplace_listing_id="MKT-1")

    # Direct insert simulating simultaneous transaction race condition
    with pytest.raises(ValueError) as exc:
        # Simulate simultaneous insert that triggers unique constraint
        entry = ListingRegistry(
            normalized_upc=norm_upc,
            marketplace="amazon",
            product_id=p2.id,
            title=p2.title,
            status="ACTIVE",
        )
        db_session.add(entry)
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise ValueError(f"Concurrent upload conflict: UPC {norm_upc} was already registered on amazon")

    assert "Concurrent upload conflict" in str(exc.value)
