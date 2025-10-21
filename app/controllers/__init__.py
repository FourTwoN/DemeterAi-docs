"""FastAPI route controllers - Sprint 04.

This module exports all API routers for registration with FastAPI app.

Controllers:
    - stock_controller: Stock management (7 endpoints)
    - location_controller: Location hierarchy (6 endpoints)
    - product_controller: Product management (7 endpoints)
    - config_controller: Configuration (3 endpoints)
    - analytics_controller: Analytics and reporting (3 endpoints)

Total: 26 endpoints (C001-C026)
"""

from app.controllers.analytics_controller import router as analytics_router
from app.controllers.config_controller import router as config_router
from app.controllers.location_controller import router as location_router
from app.controllers.product_controller import router as product_router
from app.controllers.stock_controller import router as stock_router

__all__ = [
    "stock_router",
    "location_router",
    "product_router",
    "config_router",
    "analytics_router",
]
