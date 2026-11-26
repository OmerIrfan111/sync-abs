import json
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.marketplace import Marketplace
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.sync_log import SyncLog
from app.models.user import User
from app.services.backup_service import export_database, restore_database


def _engine(tmp_path, name):
    engine = create_engine(f"sqlite:///{tmp_path / name}")
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def source(tmp_path):
    engine = _engine(tmp_path, "source.db")
    with Session(engine) as db:
        db.add(User(email="u@x.pk", hashed_password="hash", role="operator"))
        sup = Supplier(name="Ingram Micro", adapter_class="IngramMicroAdapter", credentials_encrypted="gAAAA-secret-blob")
        mp = Marketplace(name="eBay", adapter_class="LiveEBayAdapter", credentials_encrypted="gAAAA-ebay-blob")
        prod = Product(sku="P1", title="Wall Mount", images=["https://img/a.jpg"], specs_json={"image_status": "icecat", "n": [1, 2]})
        db.add_all([sup, mp, prod])
        db.flush()
        db.add(SupplierProduct(product_id=prod.id, supplier_id=sup.id, supplier_sku="S1", cost=Decimal("89.99"),
                               qty_available=7, availability_status="ACTIVE", shipping_info={"weight_lbs": 1.5}))
        order = Order(marketplace_id=mp.id, marketplace_order_id="MO-1", order_total=Decimal("150.50"),
                      marketplace_fees=Decimal("15.05"), shipping_address={"city": "Dallas"}, status="PENDING_ROUTING")
        db.add(order)
        db.flush()
        db.add(OrderItem(order_id=order.id, product_id=prod.id, sku="P1", title="Wall Mount", quantity=2,
                         unit_price=Decimal("75.25"), status="PENDING"))
        db.add(SyncLog(product_id=prod.id, field_changed="cost", old_value="1", new_value="2"))
        db.commit()
    return engine


def test_round_trip_restores_every_table_exactly(source, tmp_path):
    path = str(tmp_path / "backup.jsonl.gz")
    manifest = export_database(source, path)
    assert manifest["counts"]["users"] == 1 and manifest["counts"]["orders"] == 1

    target = _engine(tmp_path, "target.db")
    restored = restore_database(target, path, manifest)
    assert restored["supplier_products"] == 1 and restored["order_items"] == 1

    with Session(target) as db:
        assert db.query(Supplier).one().credentials_encrypted == "gAAAA-secret-blob"
        assert db.query(Marketplace).one().credentials_encrypted == "gAAAA-ebay-blob"
        sp = db.query(SupplierProduct).one()
        assert sp.cost == Decimal("89.99") and sp.shipping_info == {"weight_lbs": 1.5}
        prod = db.query(Product).one()
        assert prod.images == ["https://img/a.jpg"] and prod.specs_json == {"image_status": "icecat", "n": [1, 2]}
        order = db.query(Order).one()
        assert order.order_total == Decimal("150.50") and order.shipping_address == {"city": "Dallas"}
        assert order.created_at is not None
        assert db.query(OrderItem).one().unit_price == Decimal("75.25")


def test_noisy_history_tables_are_not_backed_up(source, tmp_path):
    path = str(tmp_path / "backup.jsonl.gz")
    manifest = export_database(source, path)
    assert "sync_logs" not in manifest["counts"]


def test_restore_refuses_to_overwrite_a_database_that_has_data(source, tmp_path):
    path = str(tmp_path / "backup.jsonl.gz")
    export_database(source, path)
    with pytest.raises(RuntimeError, match="already has data"):
        restore_database(source, path)  # the live database itself
    with Session(source) as db:
        assert db.execute(select(func.count()).select_from(User)).scalar() == 1  # untouched


def test_restore_detects_a_backup_that_does_not_match_its_manifest(source, tmp_path):
    path = str(tmp_path / "backup.jsonl.gz")
    manifest = export_database(source, path)
    manifest["counts"]["products"] += 5
    target = _engine(tmp_path, "target2.db")
    with pytest.raises(RuntimeError, match="verification failed"):
        restore_database(target, path, manifest)


def test_restore_never_reports_success_when_nothing_was_restored(tmp_path):
    """Real bug found 2026-11-26: a restore that loaded no table definitions printed 'OK: 0 rows'."""
    empty_file = tmp_path / "empty.jsonl.gz"
    import gzip
    with gzip.open(empty_file, "wt") as f:
        f.write(json.dumps({"t": "no_such_table", "r": {"id": 1}}) + "\n")
    target = _engine(tmp_path, "target3.db")
    with pytest.raises(RuntimeError, match="nothing was restored"):
        restore_database(target, str(empty_file))
