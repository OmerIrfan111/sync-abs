# سync — Multi-Supplier Dropshipping & Inventory Synchronization Platform

سync is a high-performance inventory synchronization and automated dropshipping platform designed to sit between wholesale distributors and retail ecommerce marketplaces.

## 🚀 Key Features in V1
- **Central Catalog Management**: Normalized catalog schema holding canonical products linked to one or multiple supplier sources.
- **Modular Adapter Architecture**: Decoupled supplier and marketplace connectors supporting high-fidelity mock testing and extensible real API implementations.
- **Real-Time Inventory & Price Synchronization**: Prevents overselling, enforces safety stock buffers, handles out-of-stock events, and tracks all field changes in immutable audit logs.
- **Enterprise Background Task Pipeline**: Asynchronous sync operations powered by Celery, RabbitMQ, and Redis distributed locks.
- **Executive Operations Dashboard**: Live visibility into product counts, active listings, in-stock/out-of-stock metrics, and supplier/marketplace health.

## 🛠️ Tech Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2
- **Task Queue**: Celery, Celery Beat, RabbitMQ
- **Database & Cache**: PostgreSQL 16, Redis 7
- **Frontend**: Next.js (App Router), React, Tailwind CSS, Lucide Icons
- **DevOps**: Docker, Docker Compose

## ⚡ Quick Start

```bash
# 1. Clone the repository and navigate into it
git clone <repo_url>
cd "Sync ABS"

# 2. Copy the environment variables
cp .env.example .env

# 3. Start the entire application suite with Docker Compose
docker compose up --build -d

# 4. Run database migrations & seed initial mock suppliers
docker compose exec backend alembic upgrade head
docker compose exec backend python app/seed.py
```

Open [http://localhost:3000](http://localhost:3000) in your browser.  
Default Admin Credentials: `admin@syncplatform.io` / `adminpassword123`.

## 📚 Documentation
- [Architecture Overview](ARCHITECTURE.md)
- [API Reference](API.md)
- [Setup & Deployment](SETUP.md)
- [Testing Guide](TESTING.md)
- [Environment & Free API Keys Guide](ENVIRONMENT.md)

---

## 🔍 Prefetch Filters (Feature 2)

Prefetch filters allow sync jobs to filter products **before** fetching or processing data from wholesale suppliers, avoiding unnecessary network traffic and memory overhead:
- **`limit`**: Positive integer specifying the maximum items to fetch (e.g. `limit=50`).
- **`category`**: Case-insensitive substring match pushed to supplier API or filtered in code (e.g. `category=Monitors`).
- **`brand`**: Case-insensitive brand match (e.g. `brand=Logitech`).
- **`supplier`**: Validates that the supplier sync request targets the intended supplier name.

### API Usage Example:
```bash
POST /api/v1/suppliers/1/sync?limit=25&category=Computer%20Accessories&brand=Logitech
```
All parameters are combinable and validated with descriptive 400 Bad Request error messages.

---

## 🧪 Testing Order Routing in Sandbox / Dry-Run Mode (Feature 5)

The platform includes a global **`DRY_RUN / SANDBOX`** mode that defaults to `True` in development and test environments to guarantee that no real money, real supplier purchase orders, or live credit card charges occur:
- Controlled by `DRY_RUN=True` (in `.env`).
- Displays a prominent `[SANDBOX]` log banner across all order routing and simulation steps.
- Hard guard: Raises `SandboxViolationError` immediately if an actual financial or supplier ordering call is attempted when `DRY_RUN=True`.

### Running the Seeded Sandbox Routing Scenarios:
To execute the automated suite of seeded order routing test scenarios:
```bash
# Inside Docker:
docker compose exec backend pytest tests/integration/test_feature5_sandbox_order_routing.py -v

# Or locally with poetry/virtualenv:
pytest backend/tests/integration/test_feature5_sandbox_order_routing.py -v
```

This suite validates all 6 core routing scenarios:
1. **Cheapest Supplier Wins** (lowest delivered cost: base price + ground shipping).
2. **Cheapest Supplier Out of Stock** (graceful fallback to next available supplier with stock).
3. **Delivered Cost Comparison** (a higher base price wins if cheaper ground shipping makes it less expensive overall).
4. **Supplier API Error / Outage** (automatic failover to next responsive supplier).
5. **Duplicate UPC Protection** (blocks upload/routing if mismatched products share UPC).
6. **Cross-Marketplace UPC Conflict** (blocks conflicting product uploads across Amazon, eBay, etc.).

