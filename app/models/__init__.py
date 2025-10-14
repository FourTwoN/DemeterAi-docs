"""SQLAlchemy database models.

This module exports all database models for easy importing throughout the application.
Models are organized by domain and follow the 4-tier geospatial location hierarchy.

Location Hierarchy (100% COMPLETE):
    Warehouse (DB001) → StorageArea (DB002) → StorageLocation (DB003) → StorageBin (DB004)

Product Catalog (100% COMPLETE):
    - ProductCategory (DB015): ROOT taxonomy (Cactus, Succulent, Bromeliad, etc.)
    - ProductFamily (DB016): LEVEL 2 taxonomy (Echeveria, Aloe, Monstera, etc.)
    - Product (DB017): LEAF products with SKU and JSONB metadata
    - ProductState (DB018): Product lifecycle states (SEED → DEAD)
    - ProductSize (DB019): Product size categories (XS → XXL, CUSTOM)

Authentication (COMPLETE):
    - User (DB028): Internal staff authentication with role-based access control

ML Pipeline (IN PROGRESS):
    - Classification (DB026): ML prediction cache for product/packaging/size inference

Available Models:
    - Warehouse: Root level geospatial container (greenhouses, shadehouses, etc.)
    - StorageArea: Level 2 logical zones within warehouses (North, South, etc.)
    - StorageLocation: Level 3 photo units with QR code tracking
    - StorageBin: Level 4 (LEAF) physical containers where stock exists
    - StorageBinType: Container type catalog (plug trays, boxes, segments, pots)
    - ProductCategory: Product taxonomy ROOT (Category → Family → Product)
    - ProductFamily: Product taxonomy LEVEL 2 (Echeveria, Aloe, Monstera, etc.)
    - Product: LEAF products with SKU and JSONB custom_attributes
    - ProductState: Product lifecycle state catalog (seed, seedling, adult, flowering, etc.)
    - ProductSize: Product size category catalog (XS, S, M, L, XL, XXL, CUSTOM)
    - User: Internal authentication with bcrypt password hashing and 4-level role hierarchy
    - Classification: ML prediction cache linking detections/estimations to products/packaging/sizes

Usage:
    ```python
    from app.models import (
        Warehouse, StorageArea, StorageLocation, StorageBin, StorageBinType,
        ProductCategory, ProductFamily, Product, ProductState, ProductSize,
        Classification
    )

    warehouse = Warehouse(code="GH-001", name="Main Greenhouse", ...)
    area = StorageArea(warehouse_id=1, code="GH-001-NORTH", name="North Wing", ...)
    location = StorageLocation(storage_area_id=1, code="GH-001-NORTH-LOC-001",
                               qr_code="LOC12345-A", ...)
    bin = StorageBin(storage_location_id=1, code="GH-001-NORTH-LOC-001-SEG001",
                     label="Segment 1", status="active", ...)
    bin_type = StorageBinType(code="PLUG_TRAY_288", name="288-Cell Plug Tray", ...)
    category = ProductCategory(code="CACTUS", name="Cactus", description="Cacti family...")
    family = ProductFamily(category_id=1, name="Echeveria", scientific_name="Echeveria", ...)
    state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, ...)
    size = ProductSize(code="M", name="Medium (10-20cm)", min_height_cm=10, ...)
    ```
"""

from app.models.classification import Classification
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.product_family import ProductFamily
from app.models.product_size import ProductSize
from app.models.product_state import ProductState
from app.models.storage_area import PositionEnum, StorageArea
from app.models.storage_bin import StorageBin, StorageBinStatusEnum
from app.models.storage_bin_type import BinCategoryEnum, StorageBinType
from app.models.storage_location import StorageLocation
from app.models.user import User, UserRoleEnum
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
    "ProductCategory",
    "ProductFamily",
    "Product",
    "ProductState",
    "ProductSize",
    "Classification",
    "User",
    "UserRoleEnum",
]
