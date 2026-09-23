from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.api.v1.endpoints import (
    auth,
    suppliers,
    products,
    sync_logs,
    errors,
    dashboard,
    listings,
    rules,
    marketplaces,
    orders,
    analytics
)

api_router = APIRouter()

# Every router except /auth requires a valid logged-in user (Phase 5: staff
# roles/permissions). /auth stays open since that's how a user gets a token
# in the first place. Role-specific restrictions (admin-only actions like
# deleting a supplier or editing credentials) are applied per-endpoint on
# top of this baseline via Depends(require_role(...)).
authenticated = [Depends(get_current_user)]

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Suppliers"], dependencies=authenticated)
api_router.include_router(products.router, prefix="/products", tags=["Central Catalog"], dependencies=authenticated)
api_router.include_router(marketplaces.router, prefix="/marketplaces", tags=["Marketplaces"], dependencies=authenticated)
api_router.include_router(listings.router, prefix="/listings", tags=["Marketplace Listings"], dependencies=authenticated)
api_router.include_router(orders.router, prefix="/orders", tags=["Orders & Fulfillment"], dependencies=authenticated)
api_router.include_router(rules.router, prefix="/rules", tags=["Rules Engine"], dependencies=authenticated)
api_router.include_router(sync_logs.router, prefix="/sync-logs", tags=["Sync Logs"], dependencies=authenticated)
api_router.include_router(errors.router, prefix="/errors", tags=["Errors & Alerts"], dependencies=authenticated)
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"], dependencies=authenticated)
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"], dependencies=authenticated)


