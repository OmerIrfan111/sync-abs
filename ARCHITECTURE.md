# سync Architecture Overview

سync is a high-throughput, multi-supplier dropshipping and inventory synchronization engine that acts as the single source of truth between wholesale suppliers and ecommerce marketplaces.

## High-Level System Design

```
+-------------------------------------------------------------+
|                      Next.js Admin UI                       |
|           (Products, Suppliers, Pricing, Sync Logs)        |
+------------------------------+------------------------------+
                               | REST / JWT
                               v
+-------------------------------------------------------------+
|                     FastAPI Admin API                       |
|        (Validation, Auth, Services, Triggers, Endpoints)   |
+--------------+---------------+--------------+---------------+
               |               |              |
               v               v              v
      +----------------+ +------------+ +----------------+
      | PostgreSQL 16  | |  Redis 7   | |   RabbitMQ     |
      | Core Catalog & | | Caching &  | | Task Message   |
      | Sync State DB  | | Dist. Lock | |     Broker     |
      +----------------+ +------------+ +-------+--------+
                                                |
                        +-----------------------+
                        |
                        v
        +--------------------------------+
        |  Celery Workers & Celery Beat  |
        +---------------+----------------+
                        |
        +---------------+---------------+
        |                               |
        v                               v
+-----------------------+     +-----------------------+
|   Supplier Adapters   |     | Marketplace Adapters  |
|  - Mock Supplier      |     |  - Mock eBay (Phase2) |
|  - D&H (Phase 4)      |     |  - Amazon (Phase 4)   |
|  - Ingram (Phase 4)   |     |  - Walmart (Phase 4)  |
|  - TD SYNNEX (Phase 4)|     |  - Shopify (Phase 4)  |
+-----------------------+     +-----------------------+
```

## Core Abstractions

### 1. Supplier Adapter Abstraction (`SupplierAdapter`)
Every supplier integration (mock or real) implements:
- `fetch_catalog() -> list[NormalizedProduct]`
- `fetch_inventory(skus: list[str]) -> dict[str, int]`
- `fetch_price_changes() -> dict[str, Decimal]`
- `test_connection() -> bool`

Supplier-specific payload variations are isolated within the adapter layer and stored in `specs_json` or raw payload fields, leaving the central database schema normalized and unpolluted.

### 2. Marketplace Adapter Abstraction (`MarketplaceAdapter`)
Every marketplace integration implements:
- `create_listing(product, price, qty) -> ListingResult`
- `update_listing(external_id, updates) -> ListingResult`
- `update_inventory(external_id, qty) -> bool`
- `update_price(external_id, price) -> bool`
- `withdraw_listing(external_id) -> bool`
- `get_listing(external_id) -> ListingDetails`

### 3. Distributed Concurrency & Locking
To prevent race conditions during parallel Celery tasks updating the same product or marketplace listing, Redis distributed locks (`sync:lock:product:{id}` and `sync:lock:listing:{id}`) are acquired with TTLs and exponential backoff retry.
