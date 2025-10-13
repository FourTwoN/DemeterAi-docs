"""SQLAlchemy database models.

This module exports all database models for easy importing throughout the application.
Models are organized by domain and follow the 4-tier geospatial location hierarchy.

Location Hierarchy:
    Warehouse (DB001) → StorageArea (DB002) → StorageLocation (DB003) → StorageBin (DB004)

Available Models:
    - Warehouse: Root level geospatial container (greenhouses, shadehouses, etc.)
    - StorageArea: Level 2 logical zones within warehouses (North, South, etc.)
    - (More models will be added in Sprint 01 cards DB003-DB035)

Usage:
    ```python
    from app.models import Warehouse, StorageArea

    warehouse = Warehouse(code="GH-001", name="Main Greenhouse", ...)
    area = StorageArea(warehouse_id=1, code="GH-001-NORTH", name="North Wing", ...)
    ```
"""

from app.models.storage_area import PositionEnum, StorageArea
from app.models.warehouse import Warehouse, WarehouseTypeEnum

__all__ = [
    "Warehouse",
    "WarehouseTypeEnum",
    "StorageArea",
    "PositionEnum",
]
