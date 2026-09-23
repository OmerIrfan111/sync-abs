# ABS Sync — Claude Code Context & Handoff Guide

## Project Overview
**ABS Sync (Sync ABS)** is an enterprise-grade multi-marketplace dropshipping synchronization, catalog aggregation, and automated order fulfillment platform. It connects wholesale distributors directly to retail marketplace channels.

- **Wholesale Suppliers Supported:** Ingram Micro (Production REST/OAuth 2.0), D&H Distributing (Axway REST API), and Mock Supplier (deterministic development/testing).
- **Marketplace Sales Channels:** eBay (Live Production OAuth with 18-month token & Sell Fulfillment/Inventory API), Amazon (SP-API), Shopify (Admin REST API), plus mock adapters for all three.
- **Core Operations:**
  - Automated catalog sync with UPC/EAN normalization and manufacturer imagery resolution.
  - Dynamic repricing with tiered markups, marketplace commission deductions, and minimum margin safeguards.
  - Multi-supplier inventory allocation, physical stock pooling, and automatic out-of-stock zeroing/delisting.
  - **V2 Order Operations:** Automated order ingestion, supplier routing engine, purchase order (PO) generation, tracking sync back to marketplace channels.

---

## Tech Stack & Runtime Environment

| Layer | Technology | Details |
|---|---|---|
| **Backend Framework** | Python 3.12 / FastAPI | RESTful API, Pydantic v2 validation |
| **ORM & Database** | SQLAlchemy 2.0 / PostgreSQL 16 | Relational persistence, Alembic migrations |
| **Task Queue & Async** | Celery 5.x / RabbitMQ / Redis 7 | Periodic sync tasks, background worker & beat scheduler |
| **Frontend** | Next.js 14 (App Router) / TypeScript | Tailwind CSS, Lucide icons, Dark/Glassmorphic design |
| **Containerization** | Docker Compose | 7 coordinated services |

### Running Containers (`docker ps`)
- `sync_backend` (Port `8000:8000`) — FastAPI web service
- `sync_frontend` (Port `3000:3000`) — Next.js admin portal
- `sync_celery_worker` — Background task execution worker
- `sync_celery_beat` — Cron schedule trigger
- `sync_postgres` (Port `5432:5432`) — PostgreSQL primary database
- `sync_redis` (Port `6379:6379`) — Cache & task backend
- `sync_rabbitmq` (Port `5672:5672`, Management `15672:15672`) — Message broker

---

## Key Project Architecture & File Paths

```
Sync ABS/
├── backend/
│   ├── alembic/
│   │   └── versions/
│   │       ├── 001_initial_schema.py       # V1 schema (suppliers, products, listings, rules, logs)
│   │       └── 002_v2_orders.py            # [V2] Migration for orders, items, POs, events
│   ├── app/
│   │   ├── adapters/
│   │   │   ├── marketplaces/
│   │   │   │   ├── base.py                 # Abstract MarketplaceAdapter (includes V2 order methods)
│   │   │   │   ├── live_ebay.py            # Live eBay Inventory & Fulfillment API integration
│   │   │   │   ├── live_amazon.py          # Amazon SP-API integration
│   │   │   │   ├── live_shopify.py         # Shopify Admin REST integration
│   │   │   │   ├── mock_ebay.py            # Mock eBay adapter with V2 order mock methods
│   │   │   │   ├── mock_amazon.py          # Mock Amazon adapter with V2 order mock methods
│   │   │   │   └── mock_shopify.py         # Mock Shopify adapter with V2 order mock methods
│   │   │   └── suppliers/
│   │   │       ├── ingram_micro.py         # Live Ingram Micro API integration (production & sandbox)
│   │   │       ├── d_and_h.py              # Live D&H Distributing Axway REST integration
│   │   │       ├── mock_supplier.py        # Local mock supplier generator
│   │   │       └── image_resolver.py       # Dynamic manufacturer UPC photo lookup
│   │   ├── api/v1/
│   │   │   ├── api.py                      # Main router mounting all sub-routers
│   │   │   └── endpoints/
│   │   │       ├── orders.py               # [V2] 8 order management endpoints
│   │   │       ├── dashboard.py            # Executive KPIs & metrics
│   │   │       ├── suppliers.py            # Supplier configurations & credentials
│   │   │       ├── products.py             # Unified catalog browser & sync triggers
│   │   │       ├── listings.py             # Marketplace listing publishing & status
│   │   │       ├── rules.py                # Pricing & inventory rule configuration
│   │   │       ├── marketplaces.py         # Marketplace credentials & health checks
│   │   │       └── sync_logs.py            # Sync history & error audit logs
│   │   ├── models/
│   │   │   ├── __init__.py                 # Exports all models (including V2 order models)
│   │   │   ├── order.py                    # [V2] Customer order model
│   │   │   ├── order_item.py               # [V2] Order line item model with supplier assignment
│   │   │   ├── purchase_order.py           # [V2] Supplier purchase order model with tracking
│   │   │   ├── order_event.py              # [V2] Order audit trail model
│   │   │   ├── product.py                  # Canonical product catalog model
│   │   │   ├── supplier_product.py         # Per-supplier raw product & price data
│   │   │   ├── supplier.py                 # Supplier configuration model
│   │   │   ├── listing.py                  # Marketplace listing model
│   │   │   ├── marketplace.py              # Marketplace credentials & config
│   │   │   ├── pricing_rule.py             # Tiered markup rules
│   │   │   ├── inventory_rule.py           # Stock buffering & threshold rules
│   │   │   └── sync_log.py                 # Sync execution logs
│   │   ├── schemas/
│   │   │   └── order.py                    # [V2] Pydantic request/response schemas for orders
│   │   ├── services/
│   │   │   ├── order_service.py            # [V2] Order ingestion, routing, PO, tracking service
│   │   │   ├── catalog_service.py          # Supplier catalog ingestion & normalization
│   │   │   ├── inventory_service.py        # Stock calculation, buffering, out-of-stock delisting
│   │   │   ├── pricing_service.py          # Dynamic repricing calculation & margin safety
│   │   │   ├── listing_service.py          # Marketplace publishing orchestration
│   │   │   └── supplier_selection_service.py # Routing logic for best supplier selection
│   │   └── tasks/
│   │       ├── celery_app.py               # Celery app & beat schedule configuration
│   │       └── sync_tasks.py               # Background task definitions
│   └── tests/
│       ├── unit/                           # Isolated unit tests
│       └── integration/                    # End-to-end integration tests
└── frontend/
    └── src/
        ├── app/
        │   ├── page.tsx                    # Executive Dashboard
        │   ├── catalog/page.tsx            # Unified Catalog browser
        │   ├── listings/page.tsx           # Marketplace Listings table & sync
        │   ├── marketplaces/page.tsx       # Channels & OAuth connection statuses
        │   ├── suppliers/page.tsx          # Supplier connectors & sync triggers
        │   ├── rules/page.tsx              # Pricing & Inventory rules editor
        │   ├── logs/page.tsx               # Sync history & error audit table
        │   └── orders/page.tsx             # [V2 - PENDING] Order management dashboard
        └── components/
            └── Sidebar.tsx                 # Navigation sidebar
```

---

## Essential Developer Commands

```bash
# Check Docker container status
docker ps

# Run database migration (inside backend container)
docker exec sync_backend alembic upgrade head

# Run unit tests
docker exec sync_backend pytest tests/unit -v

# Run integration tests
docker exec sync_backend pytest tests/integration -v

# View logs for any service
docker logs -f sync_backend
docker logs -f sync_celery_worker
docker logs -f sync_celery_beat
docker logs -f sync_frontend

# Restart services when modifying Celery tasks or models
docker restart sync_backend sync_celery_worker sync_celery_beat
```

---

## Detailed Project Status & Progress Tracker

### V1 — Completed Features (100% Finished)
- [x] **Supplier Connectors:**
  - [x] Ingram Micro API integration (live production & sandbox support, multi-page pagination for 250+ products).
  - [x] D&H Distributing Axway REST integration (live pricing, warehouse stock, part numbers).
  - [x] Mock Supplier adapter for offline development and testing.
  - [x] Dynamic manufacturer UPC photo resolver with category fallbacks.
- [x] **Catalog & Normalization Engine:**
  - [x] Canonical product mapping, SKU and UPC harmonization.
  - [x] Physical warehouse stock aggregation.
  - [x] Real-time cost calculation.
- [x] **Pricing & Repricing Rules:**
  - [x] Fixed dollar markups, percentage markups, tiered price brackets.
  - [x] Marketplace fee modeling (eBay 13.25%, Amazon 15%).
  - [x] Hard minimum margin safeguards and MAP protection.
- [x] **Inventory Allocation & Delisting Engine:**
  - [x] Multi-supplier prioritization (lowest cost, highest stock, priority rankings).
  - [x] Safety stock buffer thresholds.
  - [x] Automatic out-of-stock detection and quantity zeroing/delisting.
- [x] **Marketplace Synchronization & Publishing:**
  - [x] Live eBay OAuth 2.0 token connected (18-month validity).
  - [x] eBay Inventory API integration for publishing, updating inventory, and setting prices.
  - [x] Mock adapters for Amazon and Shopify.
- [x] **Frontend Admin UI:**
  - [x] Next.js 14 responsive admin panel (Dashboard, Catalog, Listings, Suppliers, Channels, Rules, Logs).
  - [x] Manual trigger buttons for immediate supplier sync and marketplace push.
- [x] **Testing & Infrastructure:**
  - [x] Docker Compose orchestrating 7 containers.
  - [x] 62 automated unit and integration tests passing.

---

### V2 — Order Management, Fulfillment Automation & Analytics (IN PROGRESS)

Claude was actively implementing **Phase V2.0 (Order Management Core)** when switching. Here is the exact status of what has been implemented and what remains:

#### V2.0 Completed So Far:
1. **Database Models (`backend/app/models/`):**
   - [x] `Order` (`order.py`): Buyer name, username, shipping address, total, status, marketplace foreign key.
   - [x] `OrderItem` (`order_item.py`): Line items, selling unit price, supplier cost, routed `supplier_id`.
   - [x] `PurchaseOrder` (`purchase_order.py`): PO reference, carrier, tracking number, supplier order reference.
   - [x] `OrderEvent` (`order_event.py`): Audit log for all state changes (`ORDER_RECEIVED`, `SUPPLIER_ROUTED`, etc.).
   - [x] Registered in `backend/app/models/__init__.py`.
2. **Database Migration Script:**
   - [x] Created `backend/alembic/versions/002_v2_orders.py` defining tables `orders`, `order_items`, `purchase_orders`, `order_events`.
3. **Pydantic Schemas:**
   - [x] `backend/app/schemas/order.py`: OrderCreate, OrderOut, OrderItemOut, PurchaseOrderOut, TrackingUpdate, OrderStats.
4. **Service Layer (`backend/app/services/`):**
   - [x] `order_service.py`: Ingests orders, routes items via supplier selection, generates purchase orders, updates tracking, and transitions statuses.
5. **Marketplace Adapters Extended:**
   - [x] `base.py`: Added abstract `fetch_orders()`, `update_tracking()`, and `acknowledge_order()`.
   - [x] `mock_ebay.py`, `mock_amazon.py`, `mock_shopify.py`: Implemented simulated order generation and tracking updates.
   - [x] `live_ebay.py`: Implemented live eBay Sell Fulfillment API calls (`GET /sell/fulfillment/v1/order`, `POST /shipping_fulfillment`).
6. **REST API Router:**
   - [x] `backend/app/api/v1/endpoints/orders.py`: 8 endpoints implemented:
     - `GET /api/v1/orders` (list with filters)
     - `GET /api/v1/orders/stats` (KPIs)
     - `GET /api/v1/orders/{id}` (detail with items and POs)
     - `POST /api/v1/orders/sync` (trigger manual ingestion)
     - `POST /api/v1/orders/{id}/route` (route items to best supplier)
     - `POST /api/v1/orders/{id}/create-po` (generate purchase order)
     - `PUT /api/v1/orders/{id}/tracking` (update tracking & push to marketplace)
     - `PUT /api/v1/orders/{id}/cancel` (cancel order)
   - [x] Registered router in `backend/app/api/v1/api.py`.

---

#### V2.0 Remaining Tasks (IMMEDIATE ACTION ITEMS FOR CLAUDE CODE):

1. **Apply Database Migration in PostgreSQL:**
   ```bash
   docker exec sync_backend alembic upgrade head
   ```
   *Action:* Run this command to create the 4 new tables (`orders`, `order_items`, `purchase_orders`, `order_events`) in the running database.

2. **Extend `SupplierSelectionService` with Order Routing:**
   - *File:* `backend/app/services/supplier_selection_service.py`
   - *Action:* Add `select_best_supplier_for_order_item(self, product_id: int, quantity: int = 1)` to select the optimal supplier based on available physical stock >= quantity, lowest cost, and supplier priority.

3. **Add Celery Background Tasks for Orders:**
   - *File:* `backend/app/tasks/sync_tasks.py`
   - *Action:* Add:
     - `order_ingestion_task()` — Polls all active marketplaces every 2 minutes for new orders.
     - `tracking_sync_task()` — Checks pending POs and synchronizes tracking numbers.
   - *File:* `backend/app/tasks/celery_app.py`
   - *Action:* Add Celery Beat schedule entries:
     - `order-ingestion-every-2-mins` (`schedule: crontab(minute="*/2")`)
     - `tracking-sync-every-10-mins` (`schedule: crontab(minute="*/10")`)
   - *Action:* Restart worker and beat containers: `docker restart sync_backend sync_celery_worker sync_celery_beat`.

4. **Complete Live Amazon & Shopify Adapter Order Stubs:**
   - *Files:* `backend/app/adapters/marketplaces/live_amazon.py` and `live_shopify.py`
   - *Action:* Add empty or fallback implementations of `fetch_orders()`, `update_tracking()`, and `acknowledge_order()` so live calls don't raise `NotImplementedError`.

5. **Create Frontend Orders Management Page:**
   - *File:* `frontend/src/app/orders/page.tsx`
   - *Features needed:*
     - Order summary KPI cards at top (Today's Orders, Pending Routing, Awaiting Shipment, 30d Revenue).
     - Filter controls by Status (`ALL`, `PENDING_ROUTING`, `ROUTED`, `PO_SUBMITTED`, `SHIPPED`, `DELIVERED`, `CANCELLED`) and Marketplace.
     - Orders table with expandable rows showing line items, item unit price, supplier cost, estimated profit, and routed supplier.
     - Action buttons: "Route Order", "Generate PO", "Add Tracking" modal/dialog, "Cancel".
     - "Sync Orders Now" button calling `POST /api/v1/orders/sync`.
   - *File:* `frontend/src/components/Sidebar.tsx`
   - *Action:* Add `{ name: "Orders", href: "/orders", icon: ShoppingCart, hint: "Customer orders & fulfillment" }` to the navigation menu.

6. **Add Order KPIs to Main Dashboard:**
   - *Backend:* `backend/app/api/v1/endpoints/dashboard.py` — include `total_orders_today`, `pending_orders`, and `revenue_30d` in dashboard response.
   - *Frontend:* `frontend/src/app/page.tsx` — render order cards alongside catalog and listing metrics.

7. **Add V2 Automated Tests:**
   - *File:* `backend/tests/unit/test_order_service.py` — test order ingestion, routing, PO creation, tracking update.
   - *File:* `backend/tests/integration/test_orders_api.py` — test all 8 REST endpoints.
   - Verify complete test suite passes without regressions.

---

### V2.1 & V2.2 — Future Planned Phases

#### Phase V2.1 — Profitability Analytics & Supplier Scoring (Next)
- Real-time net profit computation: `net_profit = order_total - supplier_cost - marketplace_fees - shipping_cost`.
- Dedicated Analytics Dashboard (`/analytics`) showing revenue trends, gross margin % by supplier, and top-performing SKUs.
- Supplier performance scoring based on fulfillment lead times, inventory accuracy, and cancellation rates.

#### Phase V2.2 — Advanced Automation & Scale
- Automated electronic Purchase Order dispatch to Ingram Micro and D&H order submission endpoints.
- Competitor repricing integration.
- Multi-account marketplace support (multiple eBay/Amazon seller stores under one dashboard).
- Additional marketplace connectors (Walmart Marketplace, TikTok Shop, Etsy).

---

## Important Technical Notes & Credentials
- **eBay Live Token:** Production OAuth token is stored in the environment (`.env`). The token has 18 months validity (user consent token). Do not commit raw secrets to git.
- **Ingram Micro API:** Production endpoints use `api.ingrammicro.com`. Sandbox uses `sandbox/resellers/v6`.
- **D&H Distributing API:** Uses Axway API Gateway with customer number and API credentials.
- **Database Migrations:** Never execute Alembic directly on the host machine without the container environment; always use `docker exec sync_backend alembic ...`.
