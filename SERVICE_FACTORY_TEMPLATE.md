# ServiceFactory Implementation Template
## For Python Expert

**File**: `/home/lucasg/proyectos/DemeterDocs/app/factories/service_factory.py`

---

## Complete Implementation

```python
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

from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

# Repository imports
from app.repositories.warehouse_repository import WarehouseRepository
from app.repositories.storage_area_repository import StorageAreaRepository
from app.repositories.storage_location_repository import StorageLocationRepository
from app.repositories.storage_bin_repository import StorageBinRepository
from app.repositories.storage_bin_type_repository import StorageBinTypeRepository
from app.repositories.storage_location_config_repository import StorageLocationConfigRepository
from app.repositories.product_category_repository import ProductCategoryRepository
from app.repositories.product_family_repository import ProductFamilyRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.product_size_repository import ProductSizeRepository
from app.repositories.product_state_repository import ProductStateRepository
from app.repositories.stock_batch_repository import StockBatchRepository
from app.repositories.stock_movement_repository import StockMovementRepository
from app.repositories.density_parameter_repository import DensityParameterRepository
from app.repositories.packaging_type_repository import PackagingTypeRepository
from app.repositories.packaging_color_repository import PackagingColorRepository
from app.repositories.packaging_material_repository import PackagingMaterialRepository
from app.repositories.packaging_catalog_repository import PackagingCatalogRepository
from app.repositories.price_list_repository import PriceListRepository
from app.repositories.photo_processing_session_repository import PhotoProcessingSessionRepository
from app.repositories.s3_image_repository import S3ImageRepository
from app.repositories.detection_repository import DetectionRepository
from app.repositories.estimation_repository import EstimationRepository

# Service imports
from app.services.warehouse_service import WarehouseService
from app.services.storage_area_service import StorageAreaService
from app.services.storage_location_service import StorageLocationService
from app.services.storage_bin_service import StorageBinService
from app.services.storage_bin_type_service import StorageBinTypeService
from app.services.storage_location_config_service import StorageLocationConfigService
from app.services.product_category_service import ProductCategoryService
from app.services.product_family_service import ProductFamilyService
from app.services.product_service import ProductService
from app.services.product_size_service import ProductSizeService
from app.services.product_state_service import ProductStateService
from app.services.stock_batch_service import StockBatchService
from app.services.stock_movement_service import StockMovementService
from app.services.density_parameter_service import DensityParameterService
from app.services.packaging_type_service import PackagingTypeService
from app.services.packaging_color_service import PackagingColorService
from app.services.packaging_material_service import PackagingMaterialService
from app.services.packaging_catalog_service import PackagingCatalogService
from app.services.price_list_service import PriceListService
from app.services.location_hierarchy_service import LocationHierarchyService
from app.services.batch_lifecycle_service import BatchLifecycleService
from app.services.movement_validation_service import MovementValidationService
from app.services.analytics_service import AnalyticsService
from app.services.photo.photo_upload_service import PhotoUploadService
from app.services.photo.photo_processing_session_service import PhotoProcessingSessionService
from app.services.photo.s3_image_service import S3ImageService
from app.services.photo.detection_service import DetectionService
from app.services.photo.estimation_service import EstimationService


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
        self._services: Dict[str, object] = {}

    # =============================================================================
    # Level 1: Simple Services (Repository only, no service dependencies)
    # =============================================================================

    def get_warehouse_service(self) -> WarehouseService:
        """Get WarehouseService instance."""
        if "warehouse" not in self._services:
            repo = WarehouseRepository(self.session)
            self._services["warehouse"] = WarehouseService(repo)
        return self._services["warehouse"]

    def get_storage_bin_type_service(self) -> StorageBinTypeService:
        """Get StorageBinTypeService instance."""
        if "storage_bin_type" not in self._services:
            repo = StorageBinTypeRepository(self.session)
            self._services["storage_bin_type"] = StorageBinTypeService(repo)
        return self._services["storage_bin_type"]

    def get_product_category_service(self) -> ProductCategoryService:
        """Get ProductCategoryService instance."""
        if "product_category" not in self._services:
            repo = ProductCategoryRepository(self.session)
            self._services["product_category"] = ProductCategoryService(repo)
        return self._services["product_category"]

    def get_product_size_service(self) -> ProductSizeService:
        """Get ProductSizeService instance."""
        if "product_size" not in self._services:
            repo = ProductSizeRepository(self.session)
            self._services["product_size"] = ProductSizeService(repo)
        return self._services["product_size"]

    def get_product_state_service(self) -> ProductStateService:
        """Get ProductStateService instance."""
        if "product_state" not in self._services:
            repo = ProductStateRepository(self.session)
            self._services["product_state"] = ProductStateService(repo)
        return self._services["product_state"]

    def get_stock_movement_service(self) -> StockMovementService:
        """Get StockMovementService instance."""
        if "stock_movement" not in self._services:
            repo = StockMovementRepository(self.session)
            self._services["stock_movement"] = StockMovementService(repo)
        return self._services["stock_movement"]

    def get_storage_location_config_service(self) -> StorageLocationConfigService:
        """Get StorageLocationConfigService instance."""
        if "storage_location_config" not in self._services:
            repo = StorageLocationConfigRepository(self.session)
            self._services["storage_location_config"] = StorageLocationConfigService(repo)
        return self._services["storage_location_config"]

    def get_density_parameter_service(self) -> DensityParameterService:
        """Get DensityParameterService instance."""
        if "density_parameter" not in self._services:
            repo = DensityParameterRepository(self.session)
            self._services["density_parameter"] = DensityParameterService(repo)
        return self._services["density_parameter"]

    def get_packaging_type_service(self) -> PackagingTypeService:
        """Get PackagingTypeService instance."""
        if "packaging_type" not in self._services:
            repo = PackagingTypeRepository(self.session)
            self._services["packaging_type"] = PackagingTypeService(repo)
        return self._services["packaging_type"]

    def get_packaging_color_service(self) -> PackagingColorService:
        """Get PackagingColorService instance."""
        if "packaging_color" not in self._services:
            repo = PackagingColorRepository(self.session)
            self._services["packaging_color"] = PackagingColorService(repo)
        return self._services["packaging_color"]

    def get_packaging_material_service(self) -> PackagingMaterialService:
        """Get PackagingMaterialService instance."""
        if "packaging_material" not in self._services:
            repo = PackagingMaterialRepository(self.session)
            self._services["packaging_material"] = PackagingMaterialService(repo)
        return self._services["packaging_material"]

    def get_price_list_service(self) -> PriceListService:
        """Get PriceListService instance."""
        if "price_list" not in self._services:
            repo = PriceListRepository(self.session)
            self._services["price_list"] = PriceListService(repo)
        return self._services["price_list"]

    def get_photo_processing_session_service(self) -> PhotoProcessingSessionService:
        """Get PhotoProcessingSessionService instance."""
        if "photo_processing_session" not in self._services:
            repo = PhotoProcessingSessionRepository(self.session)
            self._services["photo_processing_session"] = PhotoProcessingSessionService(repo)
        return self._services["photo_processing_session"]

    def get_s3_image_service(self) -> S3ImageService:
        """Get S3ImageService instance."""
        if "s3_image" not in self._services:
            repo = S3ImageRepository(self.session)
            self._services["s3_image"] = S3ImageService(repo)
        return self._services["s3_image"]

    def get_detection_service(self) -> DetectionService:
        """Get DetectionService instance."""
        if "detection" not in self._services:
            repo = DetectionRepository(self.session)
            self._services["detection"] = DetectionService(repo)
        return self._services["detection"]

    def get_estimation_service(self) -> EstimationService:
        """Get EstimationService instance."""
        if "estimation" not in self._services:
            repo = EstimationRepository(self.session)
            self._services["estimation"] = EstimationService(repo)
        return self._services["estimation"]

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
        return self._services["storage_area"]

    def get_storage_location_service(self) -> StorageLocationService:
        """Get StorageLocationService instance.

        Dependencies:
            - StorageAreaService (for parent validation)
        """
        if "storage_location" not in self._services:
            repo = StorageLocationRepository(self.session)
            area_service = self.get_storage_area_service()
            self._services["storage_location"] = StorageLocationService(repo, area_service)
        return self._services["storage_location"]

    def get_storage_bin_service(self) -> StorageBinService:
        """Get StorageBinService instance.

        Dependencies:
            - StorageLocationService (for parent validation)
        """
        if "storage_bin" not in self._services:
            repo = StorageBinRepository(self.session)
            location_service = self.get_storage_location_service()
            self._services["storage_bin"] = StorageBinService(repo, location_service)
        return self._services["storage_bin"]

    def get_product_family_service(self) -> ProductFamilyService:
        """Get ProductFamilyService instance.

        Dependencies:
            - ProductCategoryService (for category validation)
        """
        if "product_family" not in self._services:
            repo = ProductFamilyRepository(self.session)
            category_service = self.get_product_category_service()
            self._services["product_family"] = ProductFamilyService(repo, category_service)
        return self._services["product_family"]

    def get_product_service(self) -> ProductService:
        """Get ProductService instance.

        Dependencies:
            - ProductCategoryService (for SKU generation)
            - ProductFamilyService (for SKU generation)
        """
        if "product" not in self._services:
            repo = ProductRepository(self.session)
            category_service = self.get_product_category_service()
            family_service = self.get_product_family_service()
            self._services["product"] = ProductService(
                repo, category_service, family_service
            )
        return self._services["product"]

    def get_packaging_catalog_service(self) -> PackagingCatalogService:
        """Get PackagingCatalogService instance.

        Dependencies:
            - PackagingTypeService
            - PackagingColorService
            - PackagingMaterialService
        """
        if "packaging_catalog" not in self._services:
            repo = PackagingCatalogRepository(self.session)
            type_service = self.get_packaging_type_service()
            color_service = self.get_packaging_color_service()
            material_service = self.get_packaging_material_service()
            self._services["packaging_catalog"] = PackagingCatalogService(
                repo, type_service, color_service, material_service
            )
        return self._services["packaging_catalog"]

    def get_stock_batch_service(self) -> StockBatchService:
        """Get StockBatchService instance.

        Dependencies:
            - StorageLocationConfigService (for configuration validation)
        """
        if "stock_batch" not in self._services:
            repo = StockBatchRepository(self.session)
            config_service = self.get_storage_location_config_service()
            self._services["stock_batch"] = StockBatchService(repo, config_service)
        return self._services["stock_batch"]

    def get_analytics_service(self) -> AnalyticsService:
        """Get AnalyticsService instance.

        Dependencies:
            - StockBatchRepository (for inventory queries)
        """
        if "analytics" not in self._services:
            batch_repo = StockBatchRepository(self.session)
            self._services["analytics"] = AnalyticsService(batch_repo)
        return self._services["analytics"]

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
        return self._services["location_hierarchy"]

    def get_batch_lifecycle_service(self) -> BatchLifecycleService:
        """Get BatchLifecycleService instance.

        Dependencies:
            - StockBatchService
            - StockMovementService
            - StorageLocationConfigService
        """
        if "batch_lifecycle" not in self._services:
            self._services["batch_lifecycle"] = BatchLifecycleService(
                batch_service=self.get_stock_batch_service(),
                movement_service=self.get_stock_movement_service(),
                config_service=self.get_storage_location_config_service(),
            )
        return self._services["batch_lifecycle"]

    def get_movement_validation_service(self) -> MovementValidationService:
        """Get MovementValidationService instance.

        Dependencies:
            - StockBatchService
            - StorageLocationService
        """
        if "movement_validation" not in self._services:
            self._services["movement_validation"] = MovementValidationService(
                batch_service=self.get_stock_batch_service(),
                location_service=self.get_storage_location_service(),
            )
        return self._services["movement_validation"]

    def get_photo_upload_service(self) -> PhotoUploadService:
        """Get PhotoUploadService instance.

        Dependencies:
            - PhotoProcessingSessionService
            - S3ImageService
            - LocationHierarchyService
        """
        if "photo_upload" not in self._services:
            self._services["photo_upload"] = PhotoUploadService(
                session_service=self.get_photo_processing_session_service(),
                s3_service=self.get_s3_image_service(),
                location_service=self.get_location_hierarchy_service(),
            )
        return self._services["photo_upload"]
```

---

## __init__.py File

**File**: `/home/lucasg/proyectos/DemeterDocs/app/factories/__init__.py`

```python
"""Dependency injection factories."""

from app.factories.service_factory import ServiceFactory

__all__ = ["ServiceFactory"]
```

---

## Usage Examples

### In Controllers (AFTER refactoring)

```python
# stock_controller.py
from app.factories.service_factory import ServiceFactory

def get_factory(
    session: AsyncSession = Depends(get_db_session)
) -> ServiceFactory:
    """Get ServiceFactory instance."""
    return ServiceFactory(session)

@router.post("/photo")
async def upload_photo_for_stock_count(
    file: UploadFile,
    longitude: float,
    latitude: float,
    user_id: int,
    factory: ServiceFactory = Depends(get_factory),  # ✅ Use factory
) -> PhotoUploadResponse:
    # ✅ No repository knowledge, just get service from factory
    service = factory.get_photo_upload_service()
    return await service.upload_photo(file, longitude, latitude, user_id)
```

---

## Testing

```python
# tests/unit/factories/test_service_factory.py
import pytest
from unittest.mock import Mock
from app.factories.service_factory import ServiceFactory

@pytest.fixture
def mock_session():
    return Mock()

def test_service_factory_creates_warehouse_service(mock_session):
    factory = ServiceFactory(mock_session)
    service = factory.get_warehouse_service()
    assert service is not None
    assert isinstance(service, WarehouseService)

def test_service_factory_caches_services(mock_session):
    factory = ServiceFactory(mock_session)
    service1 = factory.get_warehouse_service()
    service2 = factory.get_warehouse_service()
    assert service1 is service2  # Same instance (cached)

def test_service_factory_creates_product_service_with_dependencies(mock_session):
    factory = ServiceFactory(mock_session)
    service = factory.get_product_service()
    assert service is not None
    # ProductService should have category_service and family_service
    assert hasattr(service, 'category_service')
    assert hasattr(service, 'family_service')
```

---

## Verification Commands

```bash
# Create factory directory
mkdir -p /home/lucasg/proyectos/DemeterDocs/app/factories

# Create __init__.py
touch /home/lucasg/proyectos/DemeterDocs/app/factories/__init__.py

# Verify imports work
python -c "from app.factories.service_factory import ServiceFactory; print('✅ Factory OK')"

# Test factory instantiation
python -c "
from app.factories.service_factory import ServiceFactory
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Test with mock session
from unittest.mock import Mock
session = Mock()
factory = ServiceFactory(session)
print('✅ Factory instantiation OK')

# Test service creation
service = factory.get_warehouse_service()
print(f'✅ Service creation OK: {type(service).__name__}')
"
```

---

## Next Steps

1. Create `/home/lucasg/proyectos/DemeterDocs/app/factories/` directory
2. Copy this template to `service_factory.py`
3. Verify imports work
4. Run basic tests
5. Move to Phase 2 (controller refactoring)

---

**Python Expert**: Use this exact template to create the ServiceFactory.
**Do NOT modify** the service instantiation patterns - they match the existing service signatures.
