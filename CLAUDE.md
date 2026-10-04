# ABS Sync — Claude Code Context & Handoff Guide

## Project Overview
**ABS Sync (Sync ABS)** is a multi-marketplace dropshipping synchronization, catalog aggregation, and order fulfillment platform. It connects wholesale distributors directly to retail marketplace channels.

- **Wholesale Suppliers Supported:** Ingram Micro (Production REST/OAuth 2.0), D&H Distributing (Axway REST API), TD SYNNEX (Production REST Partner API / cis-partner-api, Account 813367), and Mock Supplier (deterministic development/testing).
- **Marketplace Sales Channels:** eBay (Live Production OAuth, Sell Fulfillment/Inventory API — the only channel with real order ingestion/tracking today), Amazon (SP-API adapter exists but order methods are explicit `NotImplementedError` stubs, not wired to real orders), Shopify (Admin REST API adapter, same order-method caveat as Amazon), plus mock adapters for all three.
- **Core Operations:**
  - Catalog sync with UPC/EAN normalization, per-branch warehouse stock, and image resolution (supplier photo → UPC lookup → curated brand/category stock photo fallback).
  - Dynamic repricing with tiered markups, marketplace commission deductions, and minimum margin safeguards.
  - Multi-supplier inventory allocation, physical stock pooling, and automatic out-of-stock zeroing/delisting.
  - **Order Operations:** Order ingestion (eBay live; Amazon/Shopify honestly unimplemented), supplier routing (with real Ingram Micro freight-cost estimate and TD SYNNEX base shipping rules at routing time), purchase order generation, real order submission to D&H, Ingram Micro, and TD SYNNEX, automatic tracking discovery and push back to marketplace channels.
  - **Analytics:** Real profitability (revenue/cost/fees/shipping → net profit), supplier scoring, catalog data-quality metrics — never fabricated placeholder numbers.
  - **RBAC:** Staff accounts with `admin`/`operator` roles gating destructive or credential-sensitive actions.

---

## Tech Stack & Runtime Environment

| Layer | Technology | Details |
|---|---|---|
| **Backend Framework** | Python 3.12 / FastAPI | RESTful API, Pydantic v2 validation |
| **ORM & Database** | SQLAlchemy 2.0 / PostgreSQL 16 | Relational persistence, Alembic migrations |
| **Task Queue & Async** | Celery 5.x / RabbitMQ / Redis 7 | Periodic sync tasks, background worker & beat scheduler |
| **Frontend** | Next.js 14 (App Router) / TypeScript | Tailwind CSS, Lucide icons |
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

## Design System
The frontend identity is **"The Dispatch Desk"** — documented in `DESIGN.md` (colors, typography, elevation, components) and `PRODUCT.md` (brand personality, anti-references, register). Read those before making any visual change; don't reintroduce the earlier generic violet/indigo "AI-SaaS" look that was deliberately replaced. Key facts: hazard-orange/steel/ink/paper palette, Bebas Neue display font (used once per screen) + Scheherazade New for Arabic wordmark text, border-first elevation (no default drop shadows), radius hierarchy (tags 4px / buttons 6px / containers 8px).

---

## Key Project Architecture & File Paths

```
Sync ABS/
├── backend/
│   ├── alembic/versions/           # 12 migrations (001 initial schema → 012 supplier default shipping)
│   ├── app/
│   │   ├── adapters/
│   │   │   ├── marketplaces/
│   │   │   │   ├── base.py                 # Abstract MarketplaceAdapter. fetch_orders/update_tracking/
│   │   │   │   │                           #   acknowledge_order default to raising NotImplementedError —
│   │   │   │   │                           #   never a fabricated success/empty-result fallback.
│   │   │   │   ├── live_ebay.py            # Real order fetch/tracking/acknowledge via Sell Fulfillment API
│   │   │   │   ├── live_amazon.py          # Listing/inventory only — order methods NOT overridden (raise)
│   │   │   │   ├── live_shopify.py         # Listing/inventory only — order methods NOT overridden (raise)
│   │   │   │   └── mock_*.py               # Mock eBay/Amazon/Shopify, including simulated orders
│   │   │   └── suppliers/
│   │   │       ├── ingram_micro.py         # Live OAuth2 + resumable page-cursor catalog pagination (caps at 200);
│   │   │       │                           #   real submit_order() (Order Create v7) and
│   │   │       │                           #   check_shipment_status() (Search + Get Order Details v7) — production
│   │   │       ├── d_and_h.py              # Live bearer/OAuth2 + resumable scrollId pagination,
│   │   │       │                           #   real submit_order()/check_shipment_status() against
│   │   │       │                           #   D&H Customer Order Management API — test env only
│   │   │       ├── td_synnex.py            # Live REST Partner API (cis-partner-api) with candidate MPN matching
│   │   │       │                           #   via GetPriceAvailability, live stock GetAvailability, base shipping charge
│   │   │       │                           #   rules, live SubmitPO, and GetOrderStatus tracking polling — production
│   │   │       ├── mock_supplier.py        # Local mock supplier generator
│   │   │       └── image_resolver.py       # supplier photo → UPC lookup → brand/category stock photo
│   │   ├── api/v1/endpoints/
│   │   │   ├── orders.py                   # Order list/detail/route/create-po/tracking/cancel +
│   │   │   │                               #   POST /purchase-orders/{id}/submit-live (real order via
│   │   │   │                               #   D&H, Ingram Micro, or TD SYNNEX, auto-detected from supplier)
│   │   │   ├── analytics.py                # Profitability summary, supplier scoring
│   │   │   ├── auth.py                     # Login/token issuance, current-user
│   │   │   ├── dashboard.py                # KPIs incl. pricing-changes widget, async reconcile-all
│   │   │   ├── suppliers.py, products.py, listings.py, rules.py, marketplaces.py, sync_logs.py
│   │   ├── models/
│   │   │   ├── order.py / order_item.py / purchase_order.py / order_event.py
│   │   │   ├── product.py / supplier_product.py / supplier.py (+ catalog_sync_cursor,
│   │   │   │   catalog_sync_exhausted_at for resumable pagination) / listing.py / marketplace.py
│   │   │   ├── pricing_rule.py / inventory_rule.py / sync_log.py
│   │   │   ├── user.py                     # RBAC: email/password + role ("admin"/"operator")
│   │   │   ├── product_restriction.py      # Marketplace publish blocks (hazmat, brand-gated, etc.)
│   │   │   ├── marketplace_fee_schedule.py # Per-marketplace default commission %
│   │   │   └── warehouse.py                # Per-branch physical stock (D&H branches; Ingram & TD are
│   │   │                                   #   aggregate-only, no Warehouse rows)
│   │   ├── services/
│   │   │   ├── order_service.py            # Ingestion, routing, PO generation, live PO submission
│   │   │   │                               #   (D&H + Ingram Micro + TD SYNNEX), poll_supplier_tracking() (auto-
│   │   │   │                               #   discovers real tracking, called by tracking_sync_task)
│   │   │   ├── analytics_service.py        # Real net-profit/margin/supplier-scoring, no fabricated numbers
│   │   │   ├── restriction_service.py      # Product/category/brand marketplace publish-block checks
│   │   │   ├── catalog_service.py          # Ingestion, normalization, price/marketplace/supplier filters
│   │   │   ├── inventory_service.py, pricing_service.py, listing_service.py, sync_service.py
│   │   │   └── supplier_selection_service.py
│   │   └── tasks/
│   │       ├── celery_app.py               # Beat schedule (5 periodic tasks — see below)
│   │       └── sync_tasks.py
│   └── tests/{unit,integration}/           # 120 passing tests
└── frontend/src/
    ├── app/
    │   ├── page.tsx                    # Dashboard (manifest ledger, pricing-changes panel, supplier mix)
    │   ├── catalog/page.tsx            # Catalog: brand/category/supplier/price-range/in-stock filters
    │   ├── orders/page.tsx             # Order management: route/create-po/tracking/cancel/live-submit
    │   ├── analytics/page.tsx          # Profitability & supplier-scoring dashboard
    │   ├── listings/page.tsx, marketplaces/page.tsx, suppliers/page.tsx, rules/page.tsx, logs/page.tsx
    │   └── login/page.tsx              # Two-panel Dispatch Desk login (see DESIGN.md)
    └── components/Sidebar.tsx, Navbar.tsx, Donut.tsx, Sparkline.tsx
```

---

## Essential Developer Commands

```bash
# Check Docker container status
docker ps

# Run database migration (inside backend container)
docker exec sync_backend alembic upgrade head

# Run unit + integration tests
docker exec sync_backend pytest tests/unit tests/integration -v

# View logs for any service
docker logs -f sync_backend
docker logs -f sync_celery_worker
docker logs -f sync_celery_beat
docker logs -f sync_frontend

# Restart services when modifying Celery tasks, models, or .env
docker restart sync_backend sync_celery_worker sync_celery_beat
```

### Celery Beat Schedule
| Task | Interval | Purpose |
|---|---|---|
| `sync_all_suppliers_task` | every 5 min | Resumable catalog page-through per supplier (Ingram Micro, D&H, TD SYNNEX) |
| `out_of_stock_monitor_task` | every 5 min | Zero/delist out-of-stock listings |
| `order_ingestion_task` | every 2 min | Poll active marketplaces for new orders |
| `tracking_sync_task` | every 10 min | Poll D&H/Ingram/TD SYNNEX for real tracking, then push it to marketplaces |
| `catalog_reconcile_task` | daily 2am | Full reconciliation pass |

---

## Detailed Project Status

### Fully Working End-to-End
- **Catalog sync (Ingram Micro, D&H, and TD SYNNEX):**
  - **Ingram Micro:** Live pricing/stock, resumable pagination up to 200 pages (10,000 items). Page 201 404 response cleanly marks catalog exhausted and cycles back to page 1.
  - **D&H Distributing:** ScrollId cursor pagination across 29,000+ items.
  - **TD SYNNEX Partner API (`cis-partner-api`):** Candidate MPN query batches via `POST /api/v1/webservice/json/GetPriceAvailability`. Automatically matches dealer costs, warehouse stock, and internal `synnexSKU`s. Paginates candidate pools across sync runs with persistent cursor.
  - **Automated Background Scheduling:** Celery Beat dispatches `sync_all_suppliers_task` every 5 minutes, querying all 3 distributors in parallel and updating inventory/costs without manual intervention.
- **Product imagery:** 4-tier resolution (supplier photo → UPC lookup → brand-specific stock photo → category-generic stock photo). The stock-photo pools were fully audited — removed several photos that were miscategorized or wrong-brand, and two dead 404 URLs.
- **Pricing & inventory rules:** markups, marketplace fee modeling, minimum margin/MAP protection, multi-supplier allocation, safety stock, auto-delisting.
- **Multi-supplier comparison:** Aggregates offers across distributors for identical products (e.g., HP EliteDesk, Lenovo Pro 14), automatically routing orders to the lowest landed cost supplier.
- **eBay:** full live OAuth listing publish + real order ingestion/tracking/acknowledge via the Sell Fulfillment API.
- **Order routing:** items with no catalog match, no supplier stock, or a deleted product get an honest `UNROUTABLE` status with a specific `routing_note` — never silently stuck or falsely reported as routed.
- **Real purchase order submission (D&H, Ingram Micro, and TD SYNNEX):** `POST /purchase-orders/{id}/submit-live` auto-detects which supplier the PO belongs to and calls the matching adapter's `submit_order()`:
  - D&H: Customer Order Management API (test env).
  - Ingram Micro: Order Create v7 (`api.ingrammicro.com/resellers/v7/orders`) (production env).
  - TD SYNNEX: Partner API `POST /api/v1/webservice/json/SubmitPO` (production env).
- **Automatic tracking discovery:** `tracking_sync_task` (every 10 min) polls submitted POs via each supplier's real tracking endpoint:
  - D&H: real tracking status API.
  - Ingram Micro: Search Orders v7 → Get Order Details v7.
  - TD SYNNEX: `GET /api/v1/webservice/json/GetOrderStatus/orderNo/{orderNo}`.
- **Real shipping cost & rules:**
  - Ingram Micro: calls Freight Estimate v6 API (`POST /resellers/v6/freightestimate`).
  - TD SYNNEX: configurable base shipping flat rate via Rules page, with `POST /api/v1/webservice/json/GetFreightQuote` integration.
  - D&H: default flat rate or weight-based estimate.
- **Analytics:** real net profit (`revenue − supplier_cost − marketplace_fees − shipping_cost`), gross margin, supplier scoring, catalog missing-data rate.
- **RBAC:** login/JWT auth, `admin`/`operator` roles gating credential and destructive actions.
- **Product disable toggle:** persisted via `Product.is_enabled`.
- **Dashboard:** order KPIs, pricing-changes widget, supplier inventory mix breakdown, async "Update Everything Now".
- **Catalog filters:** brand, category, supplier, in-stock, min/max price, marketplace.

### Explicitly NOT Implemented (raises, never fabricates)
- **Amazon / Shopify order integration:** `fetch_orders()`, `update_tracking()`, `acknowledge_order()` are not overridden by `LiveAmazonAdapter`/`LiveShopifyAdapter`, so they raise `NotImplementedError` (caught and logged per-marketplace by calling tasks).
- **D&H production order submission:** current `DANDH_CLIENT_ID`/`SECRET` are sandbox credentials. Real production submission requires registering a separate application in D&H Axway portal.
- **Order completion lifecycle:** `OrderService.mark_delivered()` / `complete_order()` exist but are not scheduled; orders currently sit at `SHIPPED`.
- **Non-physical Ingram Micro SKUs** (software licenses, support contracts): return sentinel quantity (e.g. `9999999`) instead of physical stock count.
- **Additional connectors** (Walmart, TikTok Shop, Etsy): explicitly out of scope per current direction.

---

## Important Technical Notes & Credentials
- **All credentials live in `backend/.env`** (gitignored — never commit real secrets). Includes: eBay OAuth token, `INGRAM_MICRO_*`, `DANDH_*`, `TDSYNNEX_*`.
- **Ingram Micro API:** `INGRAM_MICRO_ENVIRONMENT=production` — live production account. Catalog caps at page 200 (50 items/page, max 10,000 items per search); page 201 returns 404 Record not found, handled by resetting cursor to page 1. Orders: Order Create v7.
- **D&H Distributing API:** `DANDH_ENVIRONMENT=test` — test environment (`test.api.dandh.com`). ScrollId cursor pagination (up to 100 items per request).
- **TD SYNNEX Partner API:** `TDSYNNEX_ENVIRONMENT=production` — registered via TD SYNNEX Developer Portal under Default Application US (`813367`).
  - Base URL: `https://api.us.tdsynnex.com`
  - Authentication: `x-api-key: sk-3629aa28...`, `Authorization: Bearer sk-4ff7e520...`, `customerNo: 813367`.
  - Price & Availability: `POST /api/v1/webservice/json/GetPriceAvailability` (candidate MPN batches of 50).
  - Stock Check: `POST /api/v1/webservice/json/GetAvailability`.
  - Purchase Orders: `POST /api/v1/webservice/json/SubmitPO`.
  - Order Tracking: `GET /api/v1/webservice/json/GetOrderStatus/orderNo/{orderNo}`.
  - Automated Sync: Automatically polled every 5 minutes by Celery Beat (`sync_all_suppliers_task`).
  - Worker Reload Requirement: Whenever modifying supplier adapters or sync tasks, restart both worker and beat containers (`docker restart sync_celery_worker sync_celery_beat`) so Python code changes reload in Celery worker processes.
- **Registry safety invariant:** `app/adapters/registry.py` raises on an unrecognized `adapter_class` rather than silently defaulting to `MockSupplierAdapter`. All live supplier adapters raise `ConnectionError` (never fabricate catalog data) when credentials are missing or invalid.
- **Database Migrations:** Never execute Alembic directly on the host machine; always `docker exec sync_backend alembic upgrade head`.
