"""SQLAlchemy database models.

This module exports all database models for easy importing throughout the application.
Models are organized by domain and follow the 4-tier geospatial location hierarchy.

Location Hierarchy (100% COMPLETE):
    Warehouse (DB001) → StorageArea (DB002) → StorageLocation (DB003) → StorageBin (DB004)

Available Models:
    - Warehouse: Root level geospatial container (greenhouses, shadehouses, etc.)
    - StorageArea: Level 2 logical zones within warehouses (North, South, etc.)
    - StorageLocation: Level 3 photo units with QR code tracking
    - StorageBin: Level 4 (LEAF) physical containers where stock exists
    - (More models will be added in Sprint 01 cards DB005-DB035)

Usage:
    ```python
    from app.models import Warehouse, StorageArea, StorageLocation, StorageBin

    warehouse = Warehouse(code="GH-001", name="Main Greenhouse", ...)
    area = StorageArea(warehouse_id=1, code="GH-001-NORTH", name="North Wing", ...)
    location = StorageLocation(storage_area_id=1, code="GH-001-NORTH-LOC-001",
                               qr_code="LOC12345-A", ...)
    bin = StorageBin(storage_location_id=1, code="GH-001-NORTH-LOC-001-SEG001",
                     label="Segment 1", status="active", ...)
    ```
"""

from app.models.storage_area import PositionEnum, StorageArea
from app.models.storage_bin import StorageBin, StorageBinStatusEnum
from app.models.storage_bin_type import BinCategoryEnum, StorageBinType
from app.models.storage_location import StorageLocation
from app.models.warehouse import Warehouse, WarehouseTypeEnum

__all__ = [
    "Warehouse",
    "WarehouseTypeEnum",
    "StorageArea",
    "PositionEnum",
    "StorageLocation",
    "StorageBin",
    "StorageBinStatusEnum",
    "StorageBinType",
    "BinCategoryEnum",
]
