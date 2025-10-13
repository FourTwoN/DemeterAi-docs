"""SQLAlchemy database models.

This module exports all database models for easy importing throughout the application.
Models are organized by domain and follow the 4-tier geospatial location hierarchy.

Location Hierarchy:
    Warehouse (DB001) → StorageArea (DB002) → StorageLocation (DB003) → StorageBin (DB004)

Available Models:
    - Warehouse: Root level geospatial container (greenhouses, shadehouses, etc.)
    - (More models will be added in Sprint 01 cards DB002-DB035)

Usage:
    ```python
    from app.models import Warehouse

    warehouse = Warehouse(code="GH-001", name="Main Greenhouse", ...)
    ```
"""

from app.models.warehouse import Warehouse, WarehouseTypeEnum

__all__ = [
    "Warehouse",
    "WarehouseTypeEnum",
]
