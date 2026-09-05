from decimal import Decimal
import pytest
from app.models.product import Product
from app.models.marketplace import Marketplace
from app.models.supplier import Supplier

def test_rules_api_crud_and_preview(client, admin_auth_headers, db_session):
    # Setup baseline data
    product = Product(sku="TEST-RULE-PROD", title="Smart Hub Rule Tester")
    db_session.add(product)
    supplier = Supplier(name="Test Ingram", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add(supplier)
    marketplace = Marketplace(name="eBay Rules Test", adapter_class="MockEBayAdapter", is_active=True)
    db_session.add(marketplace)
    db_session.commit()

    # 1. Test Pricing Rule CRUD
    # Create
    pricing_payload = {
        "product_id": product.id,
        "marketplace_id": marketplace.id,
        "rule_type": "PERCENTAGE_MARKUP",
        "percentage": 18.5,
        "notes": "Premium markup for smart hub"
    }
    resp = client.post("/api/v1/rules/pricing", json=pricing_payload, headers=admin_auth_headers)
    assert resp.status_code == 201, resp.text
    pricing_data = resp.json()
    rule_id = pricing_data["id"]
    assert pricing_data["rule_type"] == "PERCENTAGE_MARKUP"
    assert float(pricing_data["percentage"]) == 18.5

    # List
    list_resp = client.get("/api/v1/rules/pricing", headers=admin_auth_headers)
    assert list_resp.status_code == 200
    assert any(r["id"] == rule_id for r in list_resp.json())

    # Update
    update_resp = client.put(f"/api/v1/rules/pricing/{rule_id}", json={"percentage": 22.0}, headers=admin_auth_headers)
    assert update_resp.status_code == 200
    assert float(update_resp.json()["percentage"]) == 22.0

    # 2. Test Inventory Rule CRUD
    inv_payload = {
        "product_id": product.id,
        "safety_buffer": 3,
        "out_of_stock_action": "DISABLE_LISTING"
    }
    resp = client.post("/api/v1/rules/inventory", json=inv_payload, headers=admin_auth_headers)
    assert resp.status_code == 201, resp.text
    inv_data = resp.json()
    inv_id = inv_data["id"]
    assert inv_data["safety_buffer"] == 3
    assert inv_data["out_of_stock_action"] == "DISABLE_LISTING"

    # List
    inv_list = client.get(f"/api/v1/rules/inventory?product_id={product.id}", headers=admin_auth_headers)
    assert inv_list.status_code == 200
    assert len(inv_list.json()) == 1

    # 3. Test Supplier Priority CRUD
    supp_priority_payload = {
        "product_id": product.id,
        "supplier_id": supplier.id,
        "priority_rank": 1,
        "selection_rule": "PRIORITY_RANK"
    }
    resp = client.post("/api/v1/rules/supplier-priority", json=supp_priority_payload, headers=admin_auth_headers)
    assert resp.status_code == 201, resp.text
    priority_data = resp.json()
    p_id = priority_data["id"]
    assert priority_data["priority_rank"] == 1

    # 4. Test Preview Endpoint
    preview_resp = client.get(f"/api/v1/rules/preview/{product.id}?marketplace_id={marketplace.id}", headers=admin_auth_headers)
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["product_sku"] == "TEST-RULE-PROD"
    assert preview["inventory"]["safety_buffer_applied"] == 3
    assert preview["inventory"]["out_of_stock_action"] == "DISABLE_LISTING"

    # Clean up via DELETE
    assert client.delete(f"/api/v1/rules/pricing/{rule_id}", headers=admin_auth_headers).status_code == 204
    assert client.delete(f"/api/v1/rules/inventory/{inv_id}", headers=admin_auth_headers).status_code == 204
    assert client.delete(f"/api/v1/rules/supplier-priority/{p_id}", headers=admin_auth_headers).status_code == 204
