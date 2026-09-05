from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    suppliers,
    products,
    sync_logs,
    errors,
    dashboard,
    listings,
    rules,
    marketplaces
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Suppliers"])
api_router.include_router(products.router, prefix="/products", tags=["Central Catalog"])
api_router.include_router(marketplaces.router, prefix="/marketplaces", tags=["Marketplaces"])
api_router.include_router(listings.router, prefix="/listings", tags=["Marketplace Listings"])
api_router.include_router(rules.router, prefix="/rules", tags=["Rules Engine"])
api_router.include_router(sync_logs.router, prefix="/sync-logs", tags=["Sync Logs"])
api_router.include_router(errors.router, prefix="/errors", tags=["Errors & Alerts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

