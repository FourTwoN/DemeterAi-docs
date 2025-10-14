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

Packaging (100% COMPLETE):
    - PackagingType (DB007): Container types (pot, tray, box)
    - PackagingMaterial (DB008): Materials (plastic, terracotta, biodegradable)
    - PackagingColor (DB009): Colors with hex codes
    - PackagingCatalog (DB010): Complete packaging specifications

Stock Management (100% COMPLETE):
    - StockBatch (DB016): Physical inventory tracking at bin level
    - StockMovement (DB017): Stock transaction audit trail

ML Pipeline (100% COMPLETE):
    - PhotoProcessingSession (DB012): ML photo processing tracking
    - Classification (DB026): ML prediction cache
    - Detection (DB013): Individual plant detections
    - Estimation (DB014): Dense vegetation estimations

Configuration (100% COMPLETE):
    - StorageLocationConfig (DB023): Location product/packaging config
    - DensityParameter (DB024): Density estimation calibration
    - PriceList (DB025): Product pricing

Reference Images (100% COMPLETE):
    - ProductSampleImage (DB020): Product reference images

Authentication (COMPLETE):
    - User (DB028): Internal staff authentication

S3 Images (COMPLETE):
    - S3Image (DB011): S3 uploaded image metadata

Usage:
    ```python
    from app.models import (
        Warehouse, StorageArea, StorageLocation, StorageBin, StorageBinType,
        ProductCategory, ProductFamily, Product, ProductState, ProductSize,
        PackagingType, PackagingMaterial, PackagingColor, PackagingCatalog,
        StockBatch, StockMovement, PhotoProcessingSession,
        Classification, Detection, Estimation,
        StorageLocationConfig, DensityParameter, PriceList,
        ProductSampleImage, User, S3Image
    )
    ```
"""

from app.models.classification import Classification
from app.models.density_parameter import DensityParameter
from app.models.detection import Detection
from app.models.estimation import CalculationMethodEnum, Estimation
from app.models.packaging_catalog import PackagingCatalog
from app.models.packaging_color import PackagingColor
from app.models.packaging_material import PackagingMaterial
from app.models.packaging_type import PackagingType
from app.models.photo_processing_session import (
    PhotoProcessingSession,
    ProcessingSessionStatusEnum,
)
from app.models.price_list import PriceList
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.product_family import ProductFamily
from app.models.product_sample_image import ProductSampleImage, SampleTypeEnum
from app.models.product_size import ProductSize
from app.models.product_state import ProductState
from app.models.s3_image import (
    ContentTypeEnum,
    ProcessingStatusEnum,
    S3Image,
    UploadSourceEnum,
)
from app.models.stock_batch import StockBatch
from app.models.stock_movement import (
    MovementTypeEnum,
    SourceTypeEnum,
    StockMovement,
)
from app.models.storage_area import PositionEnum, StorageArea
from app.models.storage_bin import StorageBin, StorageBinStatusEnum
from app.models.storage_bin_type import BinCategoryEnum, StorageBinType
from app.models.storage_location import StorageLocation
from app.models.storage_location_config import StorageLocationConfig
from app.models.user import User, UserRoleEnum
from app.models.warehouse import Warehouse, WarehouseTypeEnum

__all__ = [
    # Location Hierarchy
    "Warehouse",
    "WarehouseTypeEnum",
    "StorageArea",
    "PositionEnum",
    "StorageLocation",
    "StorageBin",
    "StorageBinStatusEnum",
    "StorageBinType",
    "BinCategoryEnum",
    # Product Catalog
    "ProductCategory",
    "ProductFamily",
    "Product",
    "ProductState",
    "ProductSize",
    # Packaging
    "PackagingType",
    "PackagingMaterial",
    "PackagingColor",
    "PackagingCatalog",
    # Stock Management
    "StockBatch",
    "StockMovement",
    "MovementTypeEnum",
    "SourceTypeEnum",
    # ML Pipeline
    "PhotoProcessingSession",
    "ProcessingSessionStatusEnum",
    "Classification",
    "Detection",
    "Estimation",
    "CalculationMethodEnum",
    # Configuration
    "StorageLocationConfig",
    "DensityParameter",
    "PriceList",
    # Reference Images
    "ProductSampleImage",
    "SampleTypeEnum",
    # Authentication
    "User",
    "UserRoleEnum",
    # S3 Images
    "S3Image",
    "ContentTypeEnum",
    "UploadSourceEnum",
    "ProcessingStatusEnum",
]
