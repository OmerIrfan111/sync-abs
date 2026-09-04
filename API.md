# سync REST API Reference

The backend exposes a standardized REST API rooted at `/api/v1` with JSON request/response bodies, Pydantic validation, and JWT Bearer token authentication.

## Authentication
- `POST /api/v1/auth/login` - Authenticate with email & password, returns JWT bearer token.
- `GET /api/v1/auth/me` - Retrieve authenticated admin profile.

## Suppliers
- `GET /api/v1/suppliers` - List configured suppliers with status & last sync.
- `POST /api/v1/suppliers` - Register a new supplier connection.
- `GET /api/v1/suppliers/{id}` - Get supplier details.
- `PUT /api/v1/suppliers/{id}` - Update supplier configuration.
- `DELETE /api/v1/suppliers/{id}` - Remove a supplier.
- `POST /api/v1/suppliers/{id}/test` - Test supplier API connectivity.
- `POST /api/v1/suppliers/{id}/sync` - Trigger catalog and inventory sync.

## Central Catalog & Products
- `GET /api/v1/products` - List products with pagination (`page`, `page_size`), search (`q`), and filters (`supplier_id`, `brand`, `category`, `in_stock`).
- `GET /api/v1/products/{id}` - Get product details, linked supplier sources, listings, and pricing history.
- `POST /api/v1/products` - Manually create or import a product.
- `PUT /api/v1/products/{id}` - Update product attributes.
- `DELETE /api/v1/products/{id}` - Soft-delete or remove a product.

## Sync Logs & Errors
- `GET /api/v1/sync-logs` - Query field-level change history with pagination.
- `GET /api/v1/errors` - Query structured error logs with filters by type, severity, and resolution status.
- `POST /api/v1/errors/{id}/resolve` - Mark an error as resolved.

## Dashboard
- `GET /api/v1/dashboard/summary` - Aggregate metrics for KPI cards (Total Products, Active Listings, In Stock, Out of Stock, Needs Attention) and connection statuses.
