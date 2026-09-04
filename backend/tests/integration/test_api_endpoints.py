from decimal import Decimal
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.supplier_product import SupplierProduct

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_auth_login_flow(client, test_admin_user):
    # Form-data login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testadmin@syncplatform.io", "password": "testpassword123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token is not None

    # Authenticated /me endpoint
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "testadmin@syncplatform.io"

def test_supplier_crud_and_sync(client, db_session):
    # 1. Create supplier
    create_resp = client.post("/api/v1/suppliers", json={
        "name": "Test Supplier Corp",
        "adapter_class": "MockSupplierAdapter",
        "is_active": True,
        "credentials": {"api_key": "test-key-123"}
    })
    assert create_resp.status_code == 201
    supplier_id = create_resp.json()["id"]

    # 2. Test connection
    test_resp = client.post(f"/api/v1/suppliers/{supplier_id}/test")
    assert test_resp.status_code == 200
    assert test_resp.json()["success"] is True

    # 3. Synchronize supplier
    sync_resp = client.post(f"/api/v1/suppliers/{supplier_id}/sync")
    assert sync_resp.status_code == 200
    assert sync_resp.json()["status"] == "SUCCESSFULLY_SYNCHRONIZED"

    # 4. List suppliers
    list_resp = client.get("/api/v1/suppliers")
    assert list_resp.status_code == 200
    assert any(s["name"] == "Test Supplier Corp" for s in list_resp.json())

def test_product_catalog_search_and_pagination(client, db_session):
    # Seed sample products
    p1 = Product(sku="SKU-KEYBOARD-01", title="Wireless Keyboard Logitech", brand="Logitech", category="Accessories")
    p2 = Product(sku="SKU-MOUSE-02", title="Wireless Mouse Razor", brand="Razor", category="Accessories")
    db_session.add_all([p1, p2])
    db_session.commit()

    # Search by keyword
    search_resp = client.get("/api/v1/products?q=Logitech")
    assert search_resp.status_code == 200
    data = search_resp.json()
    assert data["total"] == 1
    assert data["items"][0]["sku"] == "SKU-KEYBOARD-01"

    # Pagination
    page_resp = client.get("/api/v1/products?page=1&page_size=1")
    assert page_resp.status_code == 200
    assert len(page_resp.json()["items"]) == 1
    assert page_resp.json()["total"] >= 2

def test_dashboard_summary(client, db_session):
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_products" in data
    assert "active_listings" in data
    assert "in_stock_products" in data
    assert "out_of_stock_products" in data
    assert "needs_attention" in data
