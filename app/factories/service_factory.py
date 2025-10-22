"""Service Factory for Centralized Dependency Injection.

This module provides a ServiceFactory class that creates and manages
all service instances for the application. It implements:

1. Dependency Injection: Services get their dependencies via factory
2. Lazy Loading: Services created only when first requested
3. Singleton per Session: One factory instance per database session
4. Type Safety: Full type hints for all service getters

Architecture:
    Pattern: Factory + Singleton (per session)
    Layer: Infrastructure / Dependency Injection
    Lifecycle: One factory per HTTP request (via session)
    Thread Safety: Each async request gets own session + factory

Usage:
    ```python
    # In controller
    def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
        return ServiceFactory(session)

    @router.get("/products")
    async def list_products(factory: ServiceFactory = Depends(get_factory)):
        service = factory.get_product_service()
        return await service.get_all()
    ```
"""

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.density_parameter_repository import DensityParameterRepository
from app.repositories.detection_repository import DetectionRepository
from app.repositories.estimation_repository import EstimationRepository
from app.repositories.packaging_catalog_repository import PackagingCatalogRepository
from app.repositories.packaging_color_repository import PackagingColorRepository
from app.repositories.packaging_material_repository import PackagingMaterialRepository
from app.repositories.packaging_type_repository import PackagingTypeRepository
from app.repositories.photo_processing_session_repository import PhotoProcessingSessionRepository
from app.repositories.price_list_repository import PriceListRepository
from app.repositories.product_category_repository import ProductCategoryRepository
from app.repositories.product_family_repository import ProductFamilyRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.product_size_repository import ProductSizeRepository
from app.repositories.product_state_repository import ProductStateRepository
from app.repositories.s3_image_repository import S3ImageRepository
from app.repositories.stock_batch_repository import StockBatchRepository
from app.repositories.stock_movement_repository import StockMovementRepository
from app.repositories.storage_area_repository import StorageAreaRepository
from app.repositories.storage_bin_repository import StorageBinRepository
from app.repositories.storage_bin_type_repository import StorageBinTypeRepository
from app.repositories.storage_location_config_repository import StorageLocationConfigRepository
from app.repositories.storage_location_repository import StorageLocationRepository

# Repository imports
from app.repositories.warehouse_repository import WarehouseRepository
from app.services.analytics_service import AnalyticsService
from app.services.batch_lifecycle_service import BatchLifecycleService
from app.services.density_parameter_service import DensityParameterService
from app.services.location_hierarchy_service import LocationHierarchyService
from app.services.movement_validation_service import MovementValidationService
from app.services.packaging_catalog_service import PackagingCatalogService
from app.services.packaging_color_service import PackagingColorService
from app.services.packaging_material_service import PackagingMaterialService
from app.services.packaging_type_service import PackagingTypeService
from app.services.photo.detection_service import DetectionService
from app.services.photo.estimation_service import EstimationService
from app.services.photo.photo_processing_session_service import PhotoProcessingSessionService
from app.services.photo.photo_upload_service import PhotoUploadService
from app.services.photo.s3_image_service import S3ImageService
from app.services.price_list_service import PriceListService
from app.services.product_category_service import ProductCategoryService
from app.services.product_family_service import ProductFamilyService
from app.services.product_service import ProductService
from app.services.product_size_service import ProductSizeService
from app.services.product_state_service import ProductStateService
from app.services.stock_batch_service import StockBatchService
from app.services.stock_movement_service import StockMovementService
from app.services.storage_area_service import StorageAreaService
from app.services.storage_bin_service import StorageBinService
from app.services.storage_bin_type_service import StorageBinTypeService
from app.services.storage_location_config_service import StorageLocationConfigService
from app.services.storage_location_service import StorageLocationService

# Service imports
from app.services.warehouse_service import WarehouseService


class ServiceFactory:
    """Centralized service factory for dependency injection.

    This factory creates and manages all service instances for the application.
    Services are lazily created on first access and cached for reuse within
    the same database session.

    Attributes:
        session: SQLAlchemy async database session
        _services: Cache for created service instances

    Example:
        ```python
        factory = ServiceFactory(session)
        product_service = factory.get_product_service()
        products = await product_service.get_all()
        ```
    """

    def __init__(self, session: AsyncSession):
        """Initialize factory with database session.

        Args:
            session: SQLAlchemy async database session
        """
        self.session = session
        self._services: dict[str, object] = {}

    # =============================================================================
    # Level 1: Simple Services (Repository only, no service dependencies)
    # =============================================================================

    def get_warehouse_service(self) -> WarehouseService:
        """Get WarehouseService instance."""
        if "warehouse" not in self._services:
            repo = WarehouseRepository(self.session)
            self._services["warehouse"] = WarehouseService(repo)
        return cast(WarehouseService, self._services["warehouse"])

    def get_storage_bin_type_service(self) -> StorageBinTypeService:
        """Get StorageBinTypeService instance."""
        if "storage_bin_type" not in self._services:
            repo = StorageBinTypeRepository(self.session)
            self._services["storage_bin_type"] = StorageBinTypeService(repo)
        return cast(StorageBinTypeService, self._services["storage_bin_type"])

    def get_product_category_service(self) -> ProductCategoryService:
        """Get ProductCategoryService instance."""
        if "product_category" not in self._services:
            repo = ProductCategoryRepository(self.session)
            self._services["product_category"] = ProductCategoryService(repo)
        return cast(ProductCategoryService, self._services["product_category"])

    def get_product_size_service(self) -> ProductSizeService:
        """Get ProductSizeService instance."""
        if "product_size" not in self._services:
            repo = ProductSizeRepository(self.session)
            self._services["product_size"] = ProductSizeService(repo)
        return cast(ProductSizeService, self._services["product_size"])

    def get_product_state_service(self) -> ProductStateService:
        """Get ProductStateService instance."""
        if "product_state" not in self._services:
            repo = ProductStateRepository(self.session)
            self._services["product_state"] = ProductStateService(repo)
        return cast(ProductStateService, self._services["product_state"])

    def get_stock_movement_service(self) -> StockMovementService:
        """Get StockMovementService instance."""
        if "stock_movement" not in self._services:
            repo = StockMovementRepository(self.session)
            self._services["stock_movement"] = StockMovementService(repo)
        return cast(StockMovementService, self._services["stock_movement"])

    def get_storage_location_config_service(self) -> StorageLocationConfigService:
        """Get StorageLocationConfigService instance."""
        if "storage_location_config" not in self._services:
            repo = StorageLocationConfigRepository(self.session)
            self._services["storage_location_config"] = StorageLocationConfigService(repo)
        return cast(StorageLocationConfigService, self._services["storage_location_config"])

    def get_density_parameter_service(self) -> DensityParameterService:
        """Get DensityParameterService instance."""
        if "density_parameter" not in self._services:
            repo = DensityParameterRepository(self.session)
            self._services["density_parameter"] = DensityParameterService(repo)
        return cast(DensityParameterService, self._services["density_parameter"])

    def get_packaging_type_service(self) -> PackagingTypeService:
        """Get PackagingTypeService instance."""
        if "packaging_type" not in self._services:
            repo = PackagingTypeRepository(self.session)
            self._services["packaging_type"] = PackagingTypeService(repo)
        return cast(PackagingTypeService, self._services["packaging_type"])

    def get_packaging_color_service(self) -> PackagingColorService:
        """Get PackagingColorService instance."""
        if "packaging_color" not in self._services:
            repo = PackagingColorRepository(self.session)
            self._services["packaging_color"] = PackagingColorService(repo)
        return cast(PackagingColorService, self._services["packaging_color"])

    def get_packaging_material_service(self) -> PackagingMaterialService:
        """Get PackagingMaterialService instance."""
        if "packaging_material" not in self._services:
            repo = PackagingMaterialRepository(self.session)
            self._services["packaging_material"] = PackagingMaterialService(repo)
        return cast(PackagingMaterialService, self._services["packaging_material"])

    def get_price_list_service(self) -> PriceListService:
        """Get PriceListService instance."""
        if "price_list" not in self._services:
            repo = PriceListRepository(self.session)
            self._services["price_list"] = PriceListService(repo)
        return cast(PriceListService, self._services["price_list"])

    def get_photo_processing_session_service(self) -> PhotoProcessingSessionService:
        """Get PhotoProcessingSessionService instance."""
        if "photo_processing_session" not in self._services:
            repo = PhotoProcessingSessionRepository(self.session)
            self._services["photo_processing_session"] = PhotoProcessingSessionService(repo)
        return cast(PhotoProcessingSessionService, self._services["photo_processing_session"])

    def get_s3_image_service(self) -> S3ImageService:
        """Get S3ImageService instance."""
        if "s3_image" not in self._services:
            repo = S3ImageRepository(self.session)
            self._services["s3_image"] = S3ImageService(repo)
        return cast(S3ImageService, self._services["s3_image"])

    def get_detection_service(self) -> DetectionService:
        """Get DetectionService instance."""
        if "detection" not in self._services:
            repo = DetectionRepository(self.session)
            self._services["detection"] = DetectionService(repo)
        return cast(DetectionService, self._services["detection"])

    def get_estimation_service(self) -> EstimationService:
        """Get EstimationService instance."""
        if "estimation" not in self._services:
            repo = EstimationRepository(self.session)
            self._services["estimation"] = EstimationService(repo)
        return cast(EstimationService, self._services["estimation"])

    # =============================================================================
    # Level 2: Services with Service Dependencies
    # =============================================================================

    def get_storage_area_service(self) -> StorageAreaService:
        """Get StorageAreaService instance.

        Dependencies:
            - WarehouseService (for parent validation)
        """
        if "storage_area" not in self._services:
            repo = StorageAreaRepository(self.session)
            warehouse_service = self.get_warehouse_service()
            self._services["storage_area"] = StorageAreaService(repo, warehouse_service)
        return cast(StorageAreaService, self._services["storage_area"])

    def get_storage_location_service(self) -> StorageLocationService:
        """Get StorageLocationService instance.

        Dependencies:
            - WarehouseService (for warehouse validation)
            - StorageAreaService (for parent validation)
        """
        if "storage_location" not in self._services:
            repo = StorageLocationRepository(self.session)
            warehouse_service = self.get_warehouse_service()
            area_service = self.get_storage_area_service()
            self._services["storage_location"] = StorageLocationService(
                repo, warehouse_service, area_service
            )
        return cast(StorageLocationService, self._services["storage_location"])

    def get_storage_bin_service(self) -> StorageBinService:
        """Get StorageBinService instance.

        Dependencies:
            - StorageLocationService (for parent validation)
        """
        if "storage_bin" not in self._services:
            repo = StorageBinRepository(self.session)
            location_service = self.get_storage_location_service()
            self._services["storage_bin"] = StorageBinService(repo, location_service)
        return cast(StorageBinService, self._services["storage_bin"])

    def get_product_family_service(self) -> ProductFamilyService:
        """Get ProductFamilyService instance.

        Dependencies:
            - ProductCategoryService (for category validation)
        """
        if "product_family" not in self._services:
            repo = ProductFamilyRepository(self.session)
            category_service = self.get_product_category_service()
            self._services["product_family"] = ProductFamilyService(repo, category_service)
        return cast(ProductFamilyService, self._services["product_family"])

    def get_product_service(self) -> ProductService:
        """Get ProductService instance.

        Dependencies:
            - ProductFamilyService (for SKU generation)
        """
        if "product" not in self._services:
            repo = ProductRepository(self.session)
            family_service = self.get_product_family_service()
            self._services["product"] = ProductService(repo, family_service)
        return cast(ProductService, self._services["product"])

    def get_packaging_catalog_service(self) -> PackagingCatalogService:
        """Get PackagingCatalogService instance.

        Note: Current implementation has no service dependencies
        """
        if "packaging_catalog" not in self._services:
            repo = PackagingCatalogRepository(self.session)
            self._services["packaging_catalog"] = PackagingCatalogService(repo)
        return cast(PackagingCatalogService, self._services["packaging_catalog"])

    def get_stock_batch_service(self) -> StockBatchService:
        """Get StockBatchService instance.

        Note: Current implementation has no service dependencies
        """
        if "stock_batch" not in self._services:
            repo = StockBatchRepository(self.session)
            self._services["stock_batch"] = StockBatchService(repo)
        return cast(StockBatchService, self._services["stock_batch"])

    def get_analytics_service(self) -> AnalyticsService:
        """Get AnalyticsService instance.

        Dependencies:
            - StockBatchService (for inventory queries)
            - StockMovementService (for movement analytics)
        """
        if "analytics" not in self._services:
            batch_service = self.get_stock_batch_service()
            movement_service = self.get_stock_movement_service()
            self._services["analytics"] = AnalyticsService(batch_service, movement_service)
        return cast(AnalyticsService, self._services["analytics"])

    # =============================================================================
    # Level 3: Complex Services (Multiple Dependencies)
    # =============================================================================

    def get_location_hierarchy_service(self) -> LocationHierarchyService:
        """Get LocationHierarchyService instance.

        Dependencies:
            - WarehouseService
            - StorageAreaService
            - StorageLocationService
            - StorageBinService
        """
        if "location_hierarchy" not in self._services:
            self._services["location_hierarchy"] = LocationHierarchyService(
                warehouse_service=self.get_warehouse_service(),
                area_service=self.get_storage_area_service(),
                location_service=self.get_storage_location_service(),
                bin_service=self.get_storage_bin_service(),
            )
        return cast(LocationHierarchyService, self._services["location_hierarchy"])

    def get_batch_lifecycle_service(self) -> BatchLifecycleService:
        """Get BatchLifecycleService instance.

        Note: Current implementation has no dependencies (stateless helper)
        """
        if "batch_lifecycle" not in self._services:
            self._services["batch_lifecycle"] = BatchLifecycleService()
        return cast(BatchLifecycleService, self._services["batch_lifecycle"])

    def get_movement_validation_service(self) -> MovementValidationService:
        """Get MovementValidationService instance.

        Note: Current implementation has no dependencies (stateless validator)
        """
        if "movement_validation" not in self._services:
            self._services["movement_validation"] = MovementValidationService()
        return cast(MovementValidationService, self._services["movement_validation"])

    def get_photo_upload_service(self) -> PhotoUploadService:
        """Get PhotoUploadService instance.

        Dependencies:
            - PhotoProcessingSessionService
            - S3ImageService
            - StorageLocationService (not LocationHierarchyService)
        """
        if "photo_upload" not in self._services:
            self._services["photo_upload"] = PhotoUploadService(
                session_service=self.get_photo_processing_session_service(),
                s3_service=self.get_s3_image_service(),
                location_service=self.get_storage_location_service(),
            )
        return cast(PhotoUploadService, self._services["photo_upload"])
