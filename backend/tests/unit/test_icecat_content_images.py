from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.suppliers.icecat_provider import (
    ContentMatch, IcecatContentError, IcecatContentProvider, IcecatRestricted, brand_candidates,
)
from app.core.image_status import has_real_image, is_placeholder_url, real_images
from app.models.marketplace import Marketplace
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.services.catalog_service import CatalogService
from app.services.image_matching_service import ImageMatchingService
from app.services.listing_service import ListingService

STOCK = "https://images.unsplash.com/photo-1?w=600"
REAL = "https://images.icecat.biz/img/gallery/abc.jpg"


def _match(**kw):
    return ContentMatch(images=[REAL], title="Real Title", icecat_id="1", matched_by="brand+mpn", **kw)


def test_brand_candidates_normalizes_distributor_spellings():
    assert brand_candidates("HP I")[0] == "HP"
    assert brand_candidates("Cisco Systems")[0] == "Cisco"
    assert brand_candidates("SAMSUNGOEM")[0] == "Samsung"
    assert "Spectrum Industries" in brand_candidates("Spectrum Industries Inc.")
    assert brand_candidates("") == []
    assert len(brand_candidates("Some Long Brand Name Corp")) <= 4


def test_placeholder_detection():
    assert is_placeholder_url(STOCK)
    assert not is_placeholder_url(REAL)
    assert real_images([STOCK, REAL]) == [REAL]
    assert not has_real_image(Product(images=[STOCK]))
    assert has_real_image(Product(images=[STOCK, REAL]))


def test_parse_prefers_high_res_then_gallery_without_duplicates():
    payload = {"data": {
        "GeneralInfo": {"Title": "T", "IcecatId": 7},
        "Image": {"HighPic": REAL},
        "Gallery": [{"Pic": REAL}, {"Pic": "https://images.icecat.biz/img/gallery/b.jpg"}],
    }}
    m = IcecatContentProvider._parse(payload, "gtin", None)
    assert m.images == [REAL, "https://images.icecat.biz/img/gallery/b.jpg"]
    assert m.icecat_id == "7"
    assert IcecatContentProvider._parse({"data": {}}, "gtin", None) is None
    assert IcecatContentProvider._parse(None, "gtin", None) is None


def test_lookup_tries_gtin_then_brand_variants_and_stops_on_first_hit():
    p = IcecatContentProvider()
    calls = []

    def fake_get(params, **kw):
        calls.append(params)
        if params.get("Brand") == "HP":
            return {"data": {"Image": {"HighPic": REAL}, "GeneralInfo": {}}}
        return None

    with patch.object(p, "_get", side_effect=fake_get):
        m = p.lookup("HP I", "CF217A", "012345678905")
    assert m.matched_by == "brand+mpn" and m.brand_used == "HP"
    assert calls[0] == {"GTIN": "012345678905"}
    assert calls[1] == {"Brand": "HP", "ProductCode": "CF217A"}


def test_placeholder_gtin_is_not_queried():
    p = IcecatContentProvider()
    with patch.object(p, "_get", return_value=None) as g:
        assert p.lookup(None, None, "0000000000000") is None
    g.assert_not_called()


def test_transient_error_is_not_recorded_as_a_miss(db_session):
    prod = Product(sku="E1", title="x", brand="HP", mpn="M1", images=[STOCK], specs_json={})
    db_session.add(prod)
    db_session.commit()
    provider = MagicMock()
    provider.lookup_with_status.side_effect = IcecatContentError("rate limited")
    out = ImageMatchingService(db=db_session).resolve_from_content(prod, provider=provider)
    assert out == "error"
    assert "image_content_checked_at" not in (prod.specs_json or {})


def test_definitive_miss_is_remembered_and_not_rechecked(db_session):
    prod = Product(sku="E2", title="x", brand="HP", mpn="M2", images=[STOCK], specs_json={})
    db_session.add(prod)
    db_session.commit()
    svc = ImageMatchingService(db=db_session)
    provider = MagicMock()
    provider.lookup_with_status.return_value = (None, False)
    assert svc.resolve_from_content(prod, provider=provider) == "no_match"
    assert prod.specs_json["image_status"] == "placeholder"
    assert svc.resolve_from_content(prod, provider=provider) == "skipped"
    provider.lookup_with_status.assert_called_once()
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    prod.specs_json = {**prod.specs_json, "image_content_checked_at": old}
    assert svc.needs_content_check(prod)


def test_match_replaces_placeholder_with_real_photo(db_session):
    prod = Product(sku="E3", title="x", brand="HP", mpn="M3", images=[STOCK], specs_json={})
    db_session.add(prod)
    db_session.commit()
    provider = MagicMock()
    provider.lookup_with_status.return_value = (_match(), False)
    assert ImageMatchingService(db=db_session).resolve_from_content(prod, provider=provider) == "icecat"
    assert prod.images[0] == REAL and STOCK not in prod.images
    assert prod.specs_json["image_status"] == "icecat"
    assert prod.specs_json["image_match_info"]["matched_by"] == "brand+mpn"


def test_backfill_serves_in_stock_first_skips_real_and_recent_misses(db_session):
    sup = Supplier(name="BF Sup", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add(sup)
    db_session.flush()
    recent = datetime.now(timezone.utc).isoformat()
    rows = {
        "out": Product(sku="BF-OUT", title="o", brand="HP", mpn="O", images=[STOCK], specs_json={}),
        "stock": Product(sku="BF-STOCK", title="s", brand="HP", mpn="S", images=[STOCK], specs_json={}),
        "real": Product(sku="BF-REAL", title="r", brand="HP", mpn="R", images=[REAL], specs_json={"image_status": "supplier"}),
        "missed": Product(sku="BF-MISS", title="m", brand="HP", mpn="MM", images=[STOCK],
                          specs_json={"image_status": "placeholder", "image_content_checked_at": recent}),
    }
    db_session.add_all(rows.values())
    db_session.flush()
    db_session.add(SupplierProduct(product_id=rows["stock"].id, supplier_id=sup.id, supplier_sku="s", cost=1,
                                   qty_available=5, availability_status="ACTIVE"))
    db_session.commit()

    seen = []

    def fake_lookup(self, brand, mpn, gtin):
        seen.append(mpn)
        return (_match(), False) if mpn == "S" else (None, False)

    with patch("app.adapters.suppliers.icecat_provider.IcecatContentProvider.lookup_with_status", fake_lookup):
        result = CatalogService(db_session).backfill_product_images(limit=50, workers=2)

    assert seen[0] == "S"
    assert set(seen) == {"S", "O"}
    assert result["matched"] == 1 and result["no_match"] == 1 and result["errors"] == 0
    db_session.refresh(rows["stock"])
    assert rows["stock"].images[0] == REAL


def test_publish_to_live_marketplace_blocked_without_real_photo(db_session):
    class LiveFakeAdapter:
        pass

    prod = Product(sku="PUB1", title="RAM", brand="Acme", mpn="X1", images=[STOCK], specs_json={})
    mp = Marketplace(name="Live Test", adapter_class="LiveEBayAdapter", is_active=True)
    db_session.add_all([prod, mp])
    db_session.commit()
    svc = ListingService(db_session)
    with patch.object(svc, "get_adapter_for_marketplace", return_value=LiveFakeAdapter()), \
         patch("app.services.image_matching_service.ImageMatchingService.resolve_from_content", return_value="no_match"):
        with pytest.raises(ValueError, match="no verified product photo"):
            svc.publish_product_to_marketplace(prod.id, mp.id, custom_price=10, custom_qty=1)


def test_403_is_reported_as_restricted_not_as_error_or_plain_miss():
    """Live-confirmed 2026-11-18: HTTP 403 'an app_key is required' means the
    product exists in Icecat but needs a Full Icecat account."""
    p = IcecatContentProvider()
    with patch.object(p, "_get", side_effect=IcecatRestricted("full icecat")):
        match, restricted = p.lookup_with_status("LIAN-LI", "GA2L36PB", None)
    assert match is None and restricted is True


def test_restricted_product_is_rechecked_once_a_full_key_is_configured(db_session):
    prod = Product(sku="E9", title="x", brand="LIAN-LI", mpn="GA2L36PB", images=[STOCK], specs_json={})
    db_session.add(prod)
    db_session.commit()
    svc = ImageMatchingService(db=db_session)
    provider = MagicMock()
    provider.lookup_with_status.return_value = (None, True)
    with patch("app.services.image_matching_service.settings") as st:
        st.ICECAT_APP_KEY = None
        assert svc.resolve_from_content(prod, provider=provider) == "no_match"
        assert prod.specs_json["image_content_status"] == "requires_full_icecat"
        assert not svc.needs_content_check(prod)
        st.ICECAT_APP_KEY = "key-123"
        assert svc.needs_content_check(prod)


# ── Root-cause regression: sync used to overwrite real photos with stock ones ──

def _sync_item(sku, images, upc=None):
    from app.schemas.supplier import NormalizedProduct
    return NormalizedProduct(supplier_sku=sku, title="Wall Mount", brand="Chief", mpn=sku, upc=upc,
                             cost=10, quantity=3, images=images)


def _supplier(db_session):
    sup = Supplier(name="Sync Sup", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add(sup)
    db_session.flush()
    return sup


def test_new_product_never_stores_stock_placeholders(db_session):
    sup = _supplier(db_session)
    with patch("app.services.image_matching_service.ImageMatchingService.resolve_from_content", return_value="no_match"):
        product, _, _ = CatalogService(db_session).upsert_supplier_product(sup, _sync_item("NEW1", [STOCK, STOCK + "2"]))
    assert product.images == []


def test_sync_never_overwrites_a_real_photo_with_stock_photos(db_session):
    """Real incident 2026-11-18: every sync replaced the product's photo with
    the adapter's generic stock photos (a graphics card on a wall mount)."""
    sup = _supplier(db_session)
    prod = Product(sku="KEEP1", title="Wall Mount", brand="Chief", mpn="KEEP1", images=[REAL],
                   specs_json={"image_status": "icecat"})
    db_session.add(prod)
    db_session.commit()
    for _ in range(3):
        CatalogService(db_session).upsert_supplier_product(sup, _sync_item("KEEP1", [STOCK, STOCK + "2", STOCK + "3"]))
    db_session.refresh(prod)
    assert prod.images == [REAL]
    assert prod.specs_json["image_status"] == "icecat"


def test_sync_removes_legacy_placeholders_but_keeps_real(db_session):
    sup = _supplier(db_session)
    prod = Product(sku="LEG1", title="Wall Mount", brand="Chief", mpn="LEG1", images=[STOCK, REAL, STOCK + "2"], specs_json={})
    db_session.add(prod)
    db_session.commit()
    CatalogService(db_session).upsert_supplier_product(sup, _sync_item("LEG1", [STOCK]))
    db_session.refresh(prod)
    assert prod.images == [REAL]


def test_supplier_provided_photo_is_added_and_marked_supplier(db_session):
    sup = _supplier(db_session)
    prod = Product(sku="SUP1", title="Wall Mount", brand="Chief", mpn="SUP1", images=[], specs_json={})
    db_session.add(prod)
    db_session.commit()
    CatalogService(db_session).upsert_supplier_product(sup, _sync_item("SUP1", [REAL, STOCK]))
    db_session.refresh(prod)
    assert prod.images == [REAL]
    assert prod.specs_json["image_status"] == "supplier"


def test_small_renditions_are_captured_and_stored_for_fast_lists(db_session):
    """Icecat originals are ~1 MB (3000x2400); lists must use the ~500px rendition."""
    big, small = "https://images.icecat.biz/img/gallery/big.jpg", "https://images.icecat.biz/img/gallery_mediums/small.jpg"
    payload = {"data": {"GeneralInfo": {"Title": "T"},
                        "Image": {"HighPic": big, "Pic500x500": small},
                        "Gallery": [{"Pic": big, "Pic500x500": small}]}}
    m = IcecatContentProvider._parse(payload, "gtin", None)
    assert m.images == [big] and m.thumbs == {big: small}

    prod = Product(sku="TH1", title="x", brand="HP", mpn="TH1", images=[], specs_json={})
    db_session.add(prod)
    db_session.commit()
    ImageMatchingService(db=db_session).apply_content_match(prod, m)
    assert prod.specs_json["image_thumbs"] == {big: small}
