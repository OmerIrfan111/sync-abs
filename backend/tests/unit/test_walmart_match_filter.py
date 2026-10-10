from app.models.product import Product
from app.services.catalog_service import CatalogService


def _make_product(db, sku, walmart_match_status=None):
    specs = {"walmart_match_status": walmart_match_status} if walmart_match_status else {}
    p = Product(sku=sku, title=f"Test {sku}", is_enabled=True, specs_json=specs)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_walmart_match_status_filter(db_session):
    _make_product(db_session, "WM-MATCH-1", "matchable")
    _make_product(db_session, "WM-MATCH-2", "not_matchable")
    _make_product(db_session, "WM-MATCH-3", None)

    service = CatalogService(db_session)

    matchable, total_m = service.get_products(skip=0, limit=10, walmart_match_status="matchable")
    assert total_m == 1
    assert matchable[0].sku == "WM-MATCH-1"

    not_matchable, total_nm = service.get_products(skip=0, limit=10, walmart_match_status="not_matchable")
    assert total_nm == 1
    assert not_matchable[0].sku == "WM-MATCH-2"

    unchecked, total_u = service.get_products(skip=0, limit=10, walmart_match_status="unchecked")
    assert total_u == 1
    assert unchecked[0].sku == "WM-MATCH-3"
