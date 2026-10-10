# ABS Sync — Claude Code Context & Handoff Guide

## Project Overview
**ABS Sync (Sync ABS)** is a multi-marketplace dropshipping synchronization, catalog aggregation, and order fulfillment platform. It connects wholesale distributors directly to retail marketplace channels.

- **Wholesale Suppliers Supported:** Ingram Micro (Production REST/OAuth 2.0), D&H Distributing (**Production** Axway REST API as of 2026-10-09 — was test env earlier in the project, credentials were rotated to production `DANDH_CLIENT_ID`/`SECRET` in `backend/.env`), TD SYNNEX (Production REST Partner API / cis-partner-api, Account 813367), and Mock Supplier (deterministic development/testing).
- **Marketplace Sales Channels:** eBay (Live Production OAuth, Sell Fulfillment/Inventory API), Walmart (Live Production OAuth 2.0, direct merchant credentials, real order ingestion, inventory/price sync, tracking updates via Marketplace API v3), Amazon (SP-API adapter exists but order methods are explicit `NotImplementedError` stubs, not wired to real orders), Shopify (Admin REST API adapter, same order-method caveat as Amazon), plus mock adapters for all four.
- **Core Operations:**
  - Catalog sync with UPC/EAN normalization, per-branch warehouse stock, and image resolution (supplier photo → UPC lookup → curated brand/category stock photo fallback).
  - Dynamic repricing with tiered markups, marketplace commission deductions, and minimum margin safeguards.
  - Multi-supplier inventory allocation, physical stock pooling, and automatic out-of-stock zeroing/delisting.
  - **Order Operations:** Order ingestion (eBay and Walmart live; Amazon/Shopify honestly unimplemented), supplier routing (with real Ingram Micro freight-cost estimate and TD SYNNEX base shipping rules at routing time), purchase order generation, real order submission to D&H, Ingram Micro, and TD SYNNEX, automatic tracking discovery and push back to marketplace channels.
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
│   │   │   │   ├── live_walmart.py         # Real OAuth2, order fetch, tracking, inventory, price sync via Marketplace API v3
│   │   │   │   ├── live_amazon.py          # Listing/inventory only — order methods NOT overridden (raise)
│   │   │   │   ├── live_shopify.py         # Listing/inventory only — order methods NOT overridden (raise)
│   │   │   │   └── mock_*.py               # Mock adapters (eBay, Amazon, Shopify, Walmart)
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
    │   ├── orders/page.tsx             # Order management: route/create-po/tracking/cancel/live-submit.
    │   │                               #   Critical actions (Cancel, Place Order Live) go through an
    │   │                               #   in-app `confirmModal` state + styled dialog, not window.confirm().
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
- **eBay & Walmart:** full live production sales channels:
  - **eBay:** live OAuth listing publish + real order ingestion/tracking/acknowledge via the Sell Fulfillment API.
  - **Walmart:** live production OAuth 2.0 with direct merchant keys ("My API Key"), real catalog item verification, order ingestion via `/v3/orders`, inventory updates via `/v3/inventory`, pricing updates via `/v3/prices`, and shipping confirmation via `/v3/orders/{id}/shipping`.
- **Order routing:** items with no catalog match, no supplier stock, or a deleted product get an honest `UNROUTABLE` status with a specific `routing_note` — never silently stuck or falsely reported as routed.
- **Real purchase order submission (D&H, Ingram Micro, and TD SYNNEX):** `POST /purchase-orders/{id}/submit-live` auto-detects which supplier the PO belongs to and calls the matching adapter's `submit_order()`:
  - D&H: Customer Order Management API (**production** as of 2026-10-09).
  - Ingram Micro: Order Create v7 (`api.ingrammicro.com/resellers/v7/orders`) (production env).
  - TD SYNNEX: Partner API `POST /api/v1/webservice/json/SubmitPO` (production env).
- **Automatic tracking discovery:** `tracking_sync_task` (every 10 min) polls submitted POs via each supplier's real tracking endpoint:
  - D&H: real tracking status API.
  - Ingram Micro: Search Orders v7 → Get Order Details v7.
  - TD SYNNEX: `GET /api/v1/webservice/json/GetOrderStatus/orderNo/{orderNo}`.
- **Real shipping cost & rules:**
  - Ingram Micro: calls Freight Estimate v6 API (`POST /resellers/v6/freightestimate`).
  - TD SYNNEX: calls real `POST /api/v1/webservice/json/GetFreightQuote` (v2.1) first; falls back to the configurable Rules-page flat rate only if the live call fails. Account `813367` now has the "JFQ" service enabled (confirmed live). Real responses include non-customer internal codes (observed: "LABS" at $0.00) which are excluded, and a genuine `ShipMethodDescription` containing "Ground" is preferred over cheaper non-ground options when available. Some individual SKUs still return `Client.InvalidWarehouseNumber` from TD SYNNEX (no resolvable ship-from warehouse for that specific item) and fall back to the flat rate — this is a real per-SKU condition on TD SYNNEX's side, not a bug.
  - D&H: default flat rate or weight-based estimate.
- **Analytics:** real net profit (`revenue − supplier_cost − marketplace_fees − shipping_cost`), gross margin, supplier scoring, catalog missing-data rate.
- **RBAC:** login/JWT auth, `admin`/`operator` roles gating credential and destructive actions.
- **Product disable toggle:** persisted via `Product.is_enabled`.
- **Dashboard:** order KPIs, pricing-changes widget, supplier inventory mix breakdown, async "Update Everything Now".
- **Catalog filters:** brand, category, supplier, in-stock, min/max price, marketplace.

### TD SYNNEX tracking lookup fixed from real docs (2026-10-09)
`check_shipment_status()` (`GetOrderStatus`) was rewritten after the user pasted TD SYNNEX's real API reference. Real findings:
- Tracking numbers live nested at `lines[].subLines[].tracking[]` — never at the top level or directly on a line, which is all the previous version ever checked. It would have found real tracking on essentially zero real orders.
- **The previous version defaulted the carrier to a fabricated `"UPS"` when none was found** — a direct violation of this project's "never fabricate" rule, since the real carrier/ship-method could be anything. Fixed to surface the real `shippingMethod` code or an empty string, never a guess.
- There is no `shippedDate` field; the old code fell back to `orderPlacedDate`, which misreports an order's *placement* time as its *ship* time. Fixed to use `subLines[].shipDate` (real ship date, populated for `inputType=PO-v2` lookups) or `subLines[].estimatedToShip`, else nothing.
- Removed an undocumented `customerNo` query param — customer context is resolved from the OAuth bearer token itself, confirmed by the real docs ("there is no credential block in the request body").
See `test_td_synnex_adapter.py` (4 tests covering the nested-tracking path, the no-fabrication guarantee, and the not-found-error case).

**Ingram Micro and D&H tracking lookups independently verified, no changes needed.** Ingram Micro's `check_shipment_status()` (Search Orders v7 → Get Order Details v7, real nested `shipmentDetails[].carrierDetails[].trackingDetails`) was already confirmed earlier this session against Ingram's real "Get Order Details V7" doc; now also covered by `test_ingram_micro_tracking.py`. D&H's `check_shipment_status()` (`shipments[].manifests[].trackingNumber/carrier/shipmentDate`) was checked directly against the full OAS 3.0 spec the user pasted and matched exactly — now covered by `test_dandh_submit_order.py`. With this, **every real supplier's both order-submission and tracking-lookup path has been checked against actual vendor documentation** (not inferred, not guessed) at least once this session.

### Image search: root cause is Bing anti-scraping, not our code (2026-10-10)
Definitively proven, not guessed: sent the exact same narrow B2B query to the scraped `BingWebImageSearchProvider` endpoint 3 times in a row — got 3 completely different, unrelated results each time (random decoy content: a student award page, a TikTok comment, wife quotes). The identical query typed into a real browser on bing.com returns consistent, correct results every time. This is Bing detecting non-browser/automated traffic and serving randomized filler instead of its real ranked results for exactly the kind of structured SKU/part-number query this app needs most — an anti-scraping countermeasure, not a bug reachable by better queries, higher `max_results`, or a smarter relevance filter (the filter was already correctly rejecting 100% of the decoy content — the problem is the real data never reaches us at all).
- `max_results` was also raised earlier the same day from 10-12 (arbitrary) to 35 (the natural ceiling of one already-fetched Bing HTML page) — real fix for a *separate* issue (throwing away good results Bing did return), confirmed working for well-indexed products (3M filters, Vertiv UPS units) both before and unaffected by the anti-scraping issue above.
- **Real fix added**: `BingImageSearchAPIProvider` — the official, non-scraped Bing Image Search API (Azure Cognitive Services / Bing Search v7, `https://api.bing.microsoft.com/v7.0/images/search`). Same underlying Bing index a browser sees, fetched through Bing's own sanctioned channel, not subject to the scraping countermeasure. Fully coded and tested (`test_bing_image_search_api.py`), selected via `IMAGE_SEARCH_PROVIDER=bing_api` + a real `BING_IMAGE_SEARCH_API_KEY` in `backend/.env` — **not set yet, needs a real Azure/Bing Search subscription key from the user to activate**. Until then, the free scraped `BingWebImageSearchProvider` remains the default and will continue to occasionally return decoy content for narrow queries — this is inherent to scraping, not something further code changes can fix.
- `SerperImageSearchProvider` was fully removed from the codebase 2026-10-10 at the user's request (no API key available, so it was dead code).

### Walmart matchability gate now fails closed (2026-10-09)
`ListingService.publish_product_to_marketplace()`'s Walmart matchability pre-check used to fail OPEN in two real cases: a product with no UPC/EAN skipped the check entirely (the old `and (product.upc or product.ean)` condition), and a live-check failure (network blip, Walmart API error) was caught, logged as a warning, and let the publish proceed "anyway". Both let an unverified/unmatchable product reach a real `MP_ITEM_MATCH` submission. Fixed to fail closed in every case — no UPC, or the check itself erroring, both now block the publish with a clear `ValueError` instead of assuming it's fine. See `test_walmart_publish_guards.py`.

### Image search relevance filter added (2026-10-09)
Real incident: the manual "Search Web for Photos" picker showed an actor's photo and a movie poster as suggestions for ordinary cable/dongle products. Root cause, live-confirmed (not assumed): Bing Image Search, scraped directly (`BingWebImageSearchProvider`, no API key, free), returns images with **zero topical connection** to the query for narrow/low-indexed B2B product titles — confirmed by live-testing the exact failing query against real Bing and finding all 12 results were about an unrelated actor, while a generic query ("apple iphone") against the same live endpoint returned genuinely relevant results. This is an inherent limitation of scraping Bing without its official API — its fallback ranking for obscure queries is not reliable, and this can vary day to day as Bing's own ranking/anti-scraping behavior shifts (explains "it was fine yesterday").
- Added `_is_relevant()`: requires at least one real shared token between the query and a candidate's title/page URL before showing it as a suggestion. Applied inside `search_web_images()`, so it protects every caller (manual search box, the automatic UPC-tiered pipeline) uniformly. Proven against the actual real captured Bing response that caused the incident (`test_image_search_relevance.py`) — correctly rejects all 12 original bad results, keeps genuinely relevant ones.
- This filter makes bad suggestions far rarer, but can't guarantee "always good" — if Bing has no real relevant indexed content for a SKU, the honest outcome is now **zero suggestions** (never a wrong photo), not a fabricated-looking one.
- **The real fix for consistently good results**: `SerperImageSearchProvider` (real Google Images results via Serper.dev, not Bing) already existed partially in this codebase but was missing a `search_web_images()` method for the manual picker and the new relevance filter — both added. It's fully wired and ready; **it just needs a real `IMAGE_SEARCH_API_KEY` (Serper.dev) and `IMAGE_SEARCH_PROVIDER=serper` set in `backend/.env`** to actually take over from Bing. Not set yet — this is the same class of "needs real credentials from the user" item as the Ingram `RESELLER_*` fields.

### Full endpoint test coverage reached (2026-10-09)
All 80 API endpoints now have at least one direct HTTP-level test (`tests/integration/test_remaining_endpoints.py` + `test_session_fixes_endpoints.py` cover the last 23, all previously code-reviewed with no bugs found but untested at the HTTP layer). Writing these tests caught one more real gap: `PUT /marketplaces/{id}/fee-schedule` was still missing its admin-role gate despite being flagged and "fixed" earlier this session — the fix was never actually applied, only the eBay OAuth endpoint's was. Now genuinely fixed and verified by test. **223/223 backend tests pass.**

### Status vs. the original spec (`sync_project_development_specification.pdf`)
The spec's V1 scope was narrower than what's actually built; the app has grown beyond V1 into most of the spec's "Future Expansion" list (order routing, PO generation, tracking sync, analytics) because the user explicitly asked for those over the course of the project — that's a deliberate, approved expansion, not scope creep to flag as a bug. What's genuinely still a gap against the spec itself:
- **Suppliers:** spec lists 5 (D&H, Ingram Micro, TD SYNNEX, Ma Labs, VoiceComm). Only 3 real + Mock are implemented. `ma_labs.py`/`voicecomm.py` adapter source files existed at some point (their compiled `.pyc` remains in `__pycache__`) and were deliberately removed later — `seed.py` still has a comment documenting the cleanup ("Clean up any removed suppliers (TD SYNNEX, Ma Labs, VoiceComm)"). Re-adding them would need real credentials/API docs from those two distributors.
- **Marketplaces:** spec lists 5 (Amazon, eBay, Walmart, Shopify, Newegg). Newegg was also removed the same way (`mock_newegg.cpython-*.pyc` exists, source doesn't; `seed.py` cleans up "extra unmaintained marketplaces (e.g. Newegg)"). Amazon/Shopify are connected but their *order* methods are honest `NotImplementedError` stubs (listing/inventory/price sync works for both).
- **Elasticsearch:** spec calls for it for large-catalog search; not present anywhere (no service in `docker-compose.yml`, no client code). Catalog search currently runs as a plain PostgreSQL `ILIKE`/indexed query, which is fine at current catalog size but won't scale to "hundreds of thousands of products" the way the spec describes.
- **Celery Flower, Sentry, Slack webhook alerts:** none integrated. Email alerts exist; Slack does not. No Celery task monitoring UI, no error tracking service.
- **Redis distributed locks:** only present in `listing_service.py`, not applied uniformly to every marketplace-write path the spec implies.
- **Nginx / HTTPS / Let's Encrypt:** not set up for local Docker Compose (expected — that's a deployment concern, now scaffolded separately for Azure Container Apps in `infra/`, which gets HTTPS from the platform ingress instead of a hand-rolled Nginx+Certbot setup).
- **`/api/products/search`** as a distinct route doesn't exist; search is a query param (`?search=`) on the existing paginated `/api/products` list endpoint — functionally equivalent to the spec's intent, just a different URL shape.

Everything else in the spec (adapter abstraction, normalized product schema, pricing engine formulas, safety-buffer/OOS logic, dashboard KPI cards, error-status taxonomy, JWT auth, encrypted credentials, mock-before-real adapter pattern, retry/backoff, paginated list endpoints) matches the spec closely or exactly — verified by direct code read, not assumed.

### Real-money launch readiness (as of 2026-10-09)
Before `DRY_RUN=False` is ever set, the following were found and fixed by direct code/doc review (not guessed) — all now covered by tests:
- **CRITICAL — fixed:** `submit_purchase_order_live()` filtered for order items with `status == "ROUTED"`, but `create_purchase_orders()` (the mandatory prior step) sets item status to `"ORDERED"`. This meant **every real order submission, for every supplier, would have failed 100% of the time** with "No routed items" — completely invisible because `DRY_RUN=True`'s simulated path returns before ever reaching that line. Fixed to filter on `"ORDERED"`. See `test_dandh_branch_selection.py`.
- **CRITICAL — fixed:** `IngramMicroAdapter.submit_order()` was missing the `resellerInfo`/`endUserInfo` objects Ingram's real Order Create v7 API requires (confirmed against Ingram's official API reference, pasted 2026-10-09). Now built from new `RESELLER_*` settings (this business's own identity — **must be filled in `backend/.env`, currently blank placeholders**) + the real order's buyer/shipping data; the adapter refuses to submit rather than send an incomplete payload. See `test_ingram_micro_submit_order.py`.
- **Fixed:** D&H's `submit_order()` always defaulted `branch="BR01"` regardless of which branch's real stock (`WarehouseStock` table) the routing engine actually found. Now resolves a branch that genuinely has enough stock for every line on the PO, and refuses (raises `ValueError`, never guesses) if no single branch can cover the whole order. See `test_dandh_branch_selection.py`.
- **Confirmed by test, not just code-read:** if a real supplier API call fails for any reason, the PO is left exactly as `DRAFT` — `po.status`/`supplier_order_id` are only ever written after `adapter.submit_order()` returns successfully, so a thrown exception never lets the order silently "advance" to the next step. (`test_submit_live_leaves_po_as_draft_when_real_adapter_call_fails`.)
- **D&H payload fully confirmed against the real OAS 3.0 spec (2026-10-09):** user pasted the complete raw OpenAPI spec for Customer Order Management API 2.0.1. This resolved every remaining D&H uncertainty with certainty, not inference:
  - `shipments[].lines[].item` — confirmed exactly correct (was previously a high-confidence inference from the response schema; the request schema itself now confirms it). Real constraint: exactly one of `item`/`customerItemNumber` plus `orderQuantity`, matching what's sent.
  - `shipments[].branch` is **optional** — "D&H will select the best warehouse if one is not entered." The adapter previously defaulted to `branch="BR01"` unconditionally (the original bug), then was fixed to *require* a single branch with provably sufficient stock or else refuse the order — that refusal was itself overcorrected. Now: `branch` defaults to `None` and is only included in the payload when the caller has a confident single-branch answer; otherwise it's omitted entirely and D&H's own system auto-routes it, which is the documented correct behavior. `order_service.py`'s D&H branch-resolution logic no longer raises when no single branch covers the whole order — it just omits `branch`.
  - `shipping.serviceType`'s real enum is **lowercase** (`"ground"`, `"pickup"`, `"nextDay"`, ...). The adapter defaulted to `"Ground"` (capital G), which doesn't match the enum and would likely have been rejected — fixed to `"ground"`.
  - `unitPrice` is optional for D&H (unlike TD SYNNEX, where it's required) — correctly not sent.
  See `test_dandh_submit_order.py` and `test_dandh_branch_selection.py`.
- **TD SYNNEX `submit_order()` was entirely wrong — rewritten from real docs (2026-10-09):** user pasted TD SYNNEX's real Partner API `SubmitPO` reference. The previous payload used wrong field names/casing throughout (`poNumber`/`shipTo`/`lines` instead of the real `PONumber`/`Shipment.ShipTo`/`Items.Item[]`), was missing the required `DropShipFlag`, and — most seriously — **never sent `UnitPrice` at all**, despite it being a required field on every line per TD SYNNEX's own schema. This would have failed validation on literally every real submission; invisible until now for the same reason as the other two bugs (never exercised with real credentials). Rewritten to match the real schema exactly, including TD SYNNEX's own error-decision order (top-level `errorMessage` → `OrderResponse.ErrorMessage` → per-line `Code=="rejected"`) and the fact that each line can get its own distinct `OrderNumber` (one PO can become multiple TD SYNNEX sales orders). `order_service.py`'s shared `line_items` builder now includes `unitPrice` (from `SupplierProduct.cost`) for all three suppliers so TD SYNNEX has what it needs. See `test_td_synnex_submit_order.py`. All three real supplier adapters (Ingram Micro, D&H, TD SYNNEX) have now had their `submit_order()` payload verified against real vendor documentation this session — none were purely guessed anymore, though D&H's exact line-item field name (`"item"`) is still an inference, not literally shown in a request example.
- **Order status-transition gaps — fixed:** `mark_delivered()`/`complete_order()` had no validation at all (any order, in any status, could jump straight to DELIVERED/COMPLETED, corrupting analytics that key off status). Now `mark_delivered()` requires `SHIPPED`, `complete_order()` requires `DELIVERED`.
- **Orphaned live listings on product delete — fixed:** `DELETE /products/{id}` used to cascade-delete every attached `Listing` row with no attempt to retire/withdraw it on the real marketplace first (same bug class as the real 00TF99 incident, already fixed for `DELETE /listings/{id}`). Both endpoints now share `ListingService.retire_or_withdraw_listing()`.
- **RBAC gaps — fixed:** `PUT /marketplaces/{id}/fee-schedule` and `POST /marketplaces/ebay/exchange-code` (overwrites live eBay OAuth tokens) had no `require_role("admin")`, unlike every other credential/config-sensitive route in the same file. Both now gated.
- **Input validation — fixed:** `POST /products/{id}/walmart-create-new-item` had no `gt=0` on `price`/`weight_lbs`, so a `$0` or negative-weight item could be submitted to Walmart's real catalog.
- **Buyer verification:** there is no separate "is this a real person" check in this app, and there doesn't need to be — orders only ever reach this system via each marketplace's real Orders API (`fetch_orders()`), which only returns orders the marketplace has already captured real payment for. eBay/Walmart/Amazon/Shopify's own KYC and payment processing *is* the fraud check; this app's job is to ship to the address the marketplace already validated. Walmart orders already capture real buyer phone (`ship_info.phone`) and email (`customerEmailId`) in `shipping_address`/`buyer_username`; eBay orders currently capture name/address only (eBay also deliberately masks the buyer's real email behind an anonymized relay address — that's eBay's own privacy policy, not a gap here) — adding eBay phone capture from `shipTo.primaryPhone` would be a small future improvement, not done yet.
- **Not yet audited this session:** TD SYNNEX `submit_order()`'s exact field-level correctness, and the full ~20-endpoint sweep's remaining LOW-severity findings (minor N+1 query patterns on `/errors` and `/sync-logs` list endpoints — fine at current scale, not fixed).

### Explicitly NOT Implemented (raises, never fabricates)
- **Amazon / Shopify order integration:** `fetch_orders()`, `update_tracking()`, `acknowledge_order()` are not overridden by `LiveAmazonAdapter`/`LiveShopifyAdapter`, so they raise `NotImplementedError` (caught and logged per-marketplace by calling tasks).
- **Order completion lifecycle:** `OrderService.mark_delivered()` / `complete_order()` exist but are not scheduled; orders currently sit at `SHIPPED`.
- **Non-physical Ingram Micro SKUs** (software licenses, support contracts): return sentinel quantity (e.g. `9999999`) instead of physical stock count.
- **Additional connectors** (TikTok Shop, Etsy): explicitly out of scope per current direction.

---

## Important Technical Notes & Credentials
- **Credentials actually live in TWO files, both gitignored, and this matters** (discovered 2026-10-10 — the earlier "all credentials live in `backend/.env`" note here was wrong): `docker-compose.yml`'s `backend`/`celery_worker`/`celery_beat` services declare `env_file: - .env`, a path relative to the compose file's location — i.e. the **project-root** `.env` (`Sync ABS/.env`), not `backend/.env`. That root file is what docker-compose injects as real OS environment variables into each container. `backend/.env` is *also* read, separately, because `./backend` is bind-mounted to `/app` and Pydantic Settings' own `env_file=(".env", "../.env")` config resolves `.env` to `/app/.env` = `backend/.env`. Real OS env vars (from the root file, via compose) take precedence over Pydantic's own `.env`-file parsing for any key present in both — so **a value only updated in `backend/.env` is silently ignored if that same key already exists in the root `.env`**, and only takes effect for keys the root `.env` doesn't set at all (confirmed empirically: `RESELLER_*` worked when only added to `backend/.env`, precisely because the root file had zero `RESELLER_*` lines). As of 2026-10-10 the two files were manually verified in sync for every credential that exists in both (`DANDH_*`, `INGRAM_MICRO_*`, `TDSYNNEX_*`, `DATABASE_URL`, etc.) and the new `RESELLER_*` block was added to both. **Going forward: always update both files together**, and prefer checking the actual running value (`docker exec sync_backend python -c "from app.core.config import settings; print(settings.WHATEVER)"`) over trusting either file alone when it matters.
- **Walmart Marketplace API:** `WALMART_ENVIRONMENT=production` — registered via Walmart Developer Portal using direct merchant keys ("My API Key"). OAuth 2.0 token endpoint `POST https://marketplace.walmartapis.com/v3/token` issuing 15-minute Bearer tokens, with automated refresh and secure Fernet credential storage.
- **Ingram Micro API:** `INGRAM_MICRO_ENVIRONMENT=production` — live production account. Catalog caps at page 200 (50 items/page, max 10,000 items per search); page 201 returns 404 Record not found, handled by resetting cursor to page 1. Orders: Order Create v7.
- **D&H Distributing API:** `DANDH_ENVIRONMENT=production` (switched from test 2026-10-09). ScrollId cursor pagination (up to 100 items per request). Real catalog sync, inventory, and `submit_order()` now hit D&H's live production endpoints — `submit_purchase_order_live()` is still safe to click because of the `DRY_RUN` guard below, but once `DRY_RUN=False` a D&H submit-live is a real, live, production order exactly like Ingram Micro/TD SYNNEX.
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
- **DRY_RUN sandbox guard (`backend/app/core/config.py`, `settings.DRY_RUN`, default `True`):** sits in front of `OrderService.submit_purchase_order_live()` and short-circuits **before** any supplier is identified — so it protects Ingram Micro, D&H, and TD SYNNEX equally regardless of which of them is in production. While `True` (current state — nothing in `.env`/`docker-compose.yml` overrides it), clicking "Place Order (Live)" never calls a real supplier API; it generates a fake `SANDBOX-<SUPPLIER>-<hex>` confirmation number and marks the PO `SUBMITTED` locally. A hard guard (`SandboxViolationError`) additionally blocks any code path that tries to force a real transaction while `DRY_RUN=True`. **Flipping `DRY_RUN=False` in `.env` is the single switch that makes all three suppliers' order submission genuinely real — do this only when intentionally going live**, and restart `sync_backend` after.
- **Free end-to-end routing test fixtures:** 4 inactive marketplace rows exist for sandbox testing without ever touching real eBay/Amazon/Shopify/Walmart credentials — `eBay (Test Sandbox)` (`MockEBayAdapter`), `Amazon (Test Sandbox)` (`MockAmazonAdapter`), `Shopify (Test Sandbox)` (`MockShopifyAdapter`), `Walmart (Test Sandbox)` (`MockWalmartAdapter`, aliased to `MockEBayAdapter` in the registry). All `is_active=False` so Celery's 2-min ingestion sweep never touches them. `backend/scripts/seed_test_routing_orders.py` creates test `Order`/`OrderItem`/`Listing` rows against real catalog/supplier data on these marketplaces — re-runnable anytime for free routing tests across all 3 real suppliers.
