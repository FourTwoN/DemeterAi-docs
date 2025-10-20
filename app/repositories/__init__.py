"""Data access layer repositories for DemeterAI v2.0.

This package contains the Repository Pattern implementation for all database
access. All repositories inherit from AsyncRepository[T] base class.

Exports:
    AsyncRepository: Generic base repository for all models
    All specialized repositories (R001-R026)

Architecture:
    Layer: Infrastructure (Repository Pattern)
    Purpose: Abstract database access from business logic
    Pattern: Generic repository with SQLAlchemy 2.0 async API

Usage:
    ```python
    from app.repositories import WarehouseRepository, AsyncRepository
    from sqlalchemy.ext.asyncio import AsyncSession

    # Specialized repository
    warehouse_repo = WarehouseRepository(session)
    warehouse = await warehouse_repo.get(1)
    ```
"""

from app.repositories.base import AsyncRepository
from app.repositories.classification_repository import ClassificationRepository
from app.repositories.density_parameter_repository import DensityParameterRepository
from app.repositories.detection_repository import DetectionRepository
from app.repositories.estimation_repository import EstimationRepository
from app.repositories.packaging_catalog_repository import PackagingCatalogRepository
from app.repositories.packaging_color_repository import PackagingColorRepository
from app.repositories.packaging_material_repository import PackagingMaterialRepository
from app.repositories.packaging_type_repository import PackagingTypeRepository
from app.repositories.photo_processing_session_repository import (
    PhotoProcessingSessionRepository,
)
from app.repositories.price_list_repository import PriceListRepository
from app.repositories.product_category_repository import ProductCategoryRepository
from app.repositories.product_family_repository import ProductFamilyRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.product_sample_image_repository import ProductSampleImageRepository
from app.repositories.product_size_repository import ProductSizeRepository
from app.repositories.product_state_repository import ProductStateRepository
from app.repositories.s3_image_repository import S3ImageRepository
from app.repositories.stock_batch_repository import StockBatchRepository
from app.repositories.stock_movement_repository import StockMovementRepository
from app.repositories.storage_area_repository import StorageAreaRepository
from app.repositories.storage_bin_repository import StorageBinRepository
from app.repositories.storage_bin_type_repository import StorageBinTypeRepository
from app.repositories.storage_location_config_repository import (
    StorageLocationConfigRepository,
)
from app.repositories.storage_location_repository import StorageLocationRepository
from app.repositories.user_repository import UserRepository
from app.repositories.warehouse_repository import WarehouseRepository

__all__ = [
    # Base repository
    "AsyncRepository",
    # Geospatial hierarchy (4 levels)
    "WarehouseRepository",
    "StorageAreaRepository",
    "StorageLocationRepository",
    "StorageBinRepository",
    "StorageBinTypeRepository",
    # Stock management
    "StockBatchRepository",
    "StockMovementRepository",
    "StorageLocationConfigRepository",
    # ML pipeline
    "PhotoProcessingSessionRepository",
    "DetectionRepository",
    "EstimationRepository",
    "ClassificationRepository",
    "DensityParameterRepository",
    # Product taxonomy
    "ProductCategoryRepository",
    "ProductFamilyRepository",
    "ProductRepository",
    "ProductStateRepository",
    "ProductSizeRepository",
    "ProductSampleImageRepository",
    # Packaging catalog
    "PackagingTypeRepository",
    "PackagingMaterialRepository",
    "PackagingColorRepository",
    "PackagingCatalogRepository",
    # Pricing
    "PriceListRepository",
    # Images
    "S3ImageRepository",
    # Authentication
    "UserRepository",
]
