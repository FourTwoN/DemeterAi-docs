"""SQLAlchemy database models.

This module exports all database models for easy importing throughout the application.
Models are organized by domain and follow the 4-tier geospatial location hierarchy.

Location Hierarchy:
    Warehouse (DB001) → StorageArea (DB002) → StorageLocation (DB003) → StorageBin (DB004)

Available Models:
    - Warehouse: Root level geospatial container (greenhouses, shadehouses, etc.)
    - StorageArea: Level 2 logical zones within warehouses (North, South, etc.)
    - StorageLocation: Level 3 photo units with QR code tracking (DB003)
    - (More models will be added in Sprint 01 cards DB004-DB035)

Usage:
    ```python
    from app.models import Warehouse, StorageArea, StorageLocation

    warehouse = Warehouse(code="GH-001", name="Main Greenhouse", ...)
    area = StorageArea(warehouse_id=1, code="GH-001-NORTH", name="North Wing", ...)
    location = StorageLocation(storage_area_id=1, code="GH-001-NORTH-LOC-001",
                               qr_code="LOC12345-A", ...)
    ```
"""

from app.models.storage_area import PositionEnum, StorageArea
from app.models.storage_location import StorageLocation
from app.models.warehouse import Warehouse, WarehouseTypeEnum

__all__ = [
    "Warehouse",
    "WarehouseTypeEnum",
    "StorageArea",
    "PositionEnum",
    "StorageLocation",
]
