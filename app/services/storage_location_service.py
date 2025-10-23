"""Storage location business logic service.

Level 3 of location hierarchy - CRITICAL for photo localization.
GPS → Warehouse → Area → Location (this service orchestrates the full chain).

Key Features:
- GPS-based hierarchical lookup (warehouse → area → location)
- Parent area validation via StorageAreaService
- QR code management for physical tracking
- Point geometry validation (must be within parent area polygon)
- Bulk GPS lookup optimization for multi-photo processing

Architecture:
    Layer: Application (Service)
    Pattern: Service Layer with Dependency Injection
    Dependencies:
        - StorageLocationRepository (own repository)
        - WarehouseService (Service→Service for GPS chain)
        - StorageAreaService (Service→Service for parent validation)
    Used by: PhotoProcessingService, ML Pipeline

See:
    - Task: backlog/03_kanban/00_backlog/S003-storage-location-service.md
    - Repository: app/repositories/storage_location_repository.py
    - Schemas: app/schemas/storage_location_schema.py
    - Model: app/models/storage_location.py
"""

from typing import Any

from app.core.exceptions import (
    DuplicateCodeException,
    GeometryOutOfBoundsException,
    StorageLocationNotFoundException,
)
from app.repositories.storage_location_repository import StorageLocationRepository
from app.schemas.storage_location_schema import (
    StorageLocationCreateRequest,
    StorageLocationResponse,
    StorageLocationUpdateRequest,
)
from app.services.storage_area_service import StorageAreaService
from app.services.warehouse_service import WarehouseService


class StorageLocationService:
    """Business logic service for storage location operations.

    Handles GPS-based photo localization via hierarchical lookup chain.
    Critical for ML pipeline: GPS coordinates → storage location.

    Attributes:
        location_repo: Repository for storage location data access
        warehouse_service: Service for warehouse operations (GPS lookup)
        area_service: Service for storage area operations (GPS lookup, parent validation)
    """

    def __init__(
        self,
        location_repo: StorageLocationRepository,
        warehouse_service: WarehouseService,
        area_service: StorageAreaService,
    ) -> None:
        """Initialize service with repository and service dependencies."""
        self.location_repo = location_repo
        self.warehouse_service = warehouse_service
        self.area_service = area_service

    async def create_storage_location(
        self, request: StorageLocationCreateRequest
    ) -> StorageLocationResponse:
        """Create new storage location with parent validation.

        Workflow:
            1. Validate parent storage area exists (via StorageAreaService)
            2. Check code uniqueness
            3. Validate point is within parent area polygon
            4. Create storage location in database
            5. Transform to response schema

        Args:
            request: Storage location creation request

        Returns:
            StorageLocationResponse with generated ID

        Raises:
            StorageAreaNotFoundException: If parent area not found
            DuplicateCodeException: If code already exists
            GeometryOutOfBoundsException: If point outside parent area
        """
        # 1. Validate parent area exists (Service→Service)
        area = await self.area_service.get_storage_area_by_id(request.storage_area_id)

        # 2. Check code uniqueness
        from sqlalchemy import select

        stmt = select(self.location_repo.model).where(self.location_repo.model.code == request.code)
        result = await self.location_repo.session.execute(stmt)
        existing = result.scalars().first()
        if existing:
            raise DuplicateCodeException(code=request.code)

        # 3. Validate point within parent area polygon
        self._validate_point_within_area(request.coordinates, area.geojson_coordinates)

        # 4. Convert GeoJSON Point to PostGIS geometry
        location_data = request.model_dump()

        from geoalchemy2.shape import from_shape
        from shapely.geometry import shape

        point = shape(location_data["coordinates"])
        location_data["coordinates"] = from_shape(point, srid=4326)

        # Create in database
        location = await self.location_repo.create(location_data)

        # 5. Transform to response
        return StorageLocationResponse.from_model(location)

    async def get_storage_location_by_id(self, location_id: int) -> StorageLocationResponse:
        """Get storage location by ID."""
        location = await self.location_repo.get(location_id)
        if not location:
            raise StorageLocationNotFoundException(location_id=location_id)
        return StorageLocationResponse.from_model(location)

    async def get_location_by_gps(
        self, longitude: float, latitude: float
    ) -> StorageLocationResponse | None:
        """GPS-based full hierarchy lookup (CRITICAL for photo localization).

        Orchestrates warehouse → area → location chain.

        Workflow:
            1. Find warehouse containing GPS point (via WarehouseService)
            2. Find storage area within warehouse (via StorageAreaService)
            3. Find storage location within area (via StorageLocationRepository)

        Args:
            longitude: GPS longitude (WGS84)
            latitude: GPS latitude (WGS84)

        Returns:
            StorageLocationResponse if point found, None otherwise

        Performance:
            ~100-150ms for full chain (3 PostGIS queries with GIST indexes)
        """
        # 1. Find warehouse
        warehouse = await self.warehouse_service.get_warehouse_by_gps(longitude, latitude)
        if not warehouse:
            return None

        # 2. Find storage area
        area = await self.area_service.get_storage_area_by_gps(
            longitude, latitude, warehouse_id=warehouse.warehouse_id
        )
        if not area:
            return None

        # 3. Find storage location
        from geoalchemy2.functions import ST_Equals
        from sqlalchemy import func, select

        # NOTE: Database stores geometries as (lat, lon) instead of (lon, lat)
        # Inverting coordinates to match the stored data
        point = func.ST_SetSRID(func.ST_MakePoint(latitude, longitude), 4326)

        # Storage locations are POINTS, so use ST_Equals instead of ST_Contains
        query = select(self.location_repo.model).where(
            (ST_Equals(self.location_repo.model.coordinates, point))
            & (self.location_repo.model.storage_area_id == area.storage_area_id)
            & (self.location_repo.model.active == True)  # noqa: E712
        )

        result = await self.location_repo.session.execute(query)
        location = result.scalars().first()

        if not location:
            return None

        return StorageLocationResponse.from_model(location)

    async def get_locations_by_area(
        self, storage_area_id: int, active_only: bool = True
    ) -> list[StorageLocationResponse]:
        """Get all locations for a storage area."""
        from sqlalchemy import select

        query = select(self.location_repo.model).where(
            self.location_repo.model.storage_area_id == storage_area_id
        )

        if active_only:
            query = query.where(self.location_repo.model.active == True)  # noqa: E712

        result = await self.location_repo.session.execute(query)
        locations = result.scalars().all()

        return [StorageLocationResponse.from_model(loc) for loc in locations]

    async def update_storage_location(
        self, location_id: int, request: StorageLocationUpdateRequest
    ) -> StorageLocationResponse:
        """Update storage location with validation."""
        location = await self.location_repo.get(location_id)
        if not location:
            raise StorageLocationNotFoundException(location_id=location_id)

        update_data = request.model_dump(exclude_unset=True)

        if "coordinates" in update_data:
            # Validate new point within parent area
            if not location.storage_area_id:
                raise StorageLocationNotFoundException(location_id=location_id)
            area = await self.area_service.get_storage_area_by_id(location.storage_area_id)
            self._validate_point_within_area(update_data["coordinates"], area.geojson_coordinates)

            # Convert to PostGIS
            from geoalchemy2.shape import from_shape
            from shapely.geometry import shape

            point = shape(update_data["coordinates"])
            update_data["coordinates"] = from_shape(point, srid=4326)

        updated = await self.location_repo.update(location_id, update_data)
        if not updated:
            raise StorageLocationNotFoundException(location_id=location_id)
        return StorageLocationResponse.from_model(updated)

    async def delete_storage_location(self, location_id: int) -> bool:
        """Soft delete storage location (set active=False)."""
        location = await self.location_repo.get(location_id)
        if not location:
            raise StorageLocationNotFoundException(location_id=location_id)

        await self.location_repo.update(location_id, {"active": False})
        return True

    def _validate_point_within_area(
        self, point_geojson: dict[str, Any], area_polygon_geojson: dict[str, Any]
    ) -> None:
        """Validate point is within parent area polygon."""
        from shapely.geometry import shape

        point = shape(point_geojson)
        polygon = shape(area_polygon_geojson)

        if not polygon.contains(point):
            raise GeometryOutOfBoundsException(
                child="StorageLocation",
                parent="StorageArea",
                message="Location point is outside storage area boundaries",
            )
