"""Storage area business logic service.

This module implements the service layer for storage area operations following
Clean Architecture principles. Services orchestrate business logic and coordinate
repository operations.

Key Features:
- GPS-based area lookup (photo localization)
- Geometry validation with Shapely (containment within warehouse)
- Parent warehouse validation via WarehouseService (Service→Service pattern)
- Duplicate code detection
- Soft delete pattern (preserve historical data)
- Schema transformations (PostGIS ↔ GeoJSON)

Architecture:
    Layer: Application (Service)
    Pattern: Service Layer with Dependency Injection
    Dependencies:
        - StorageAreaRepository (own repository)
        - WarehouseService (Service→Service, NOT WarehouseRepository directly)
    Used by: StorageAreaController (future), LocationHierarchyService

Design Decisions:
    1. Geometry validation BEFORE database insert (fail fast, ~10-20ms overhead)
    2. Containment check: area MUST be within parent warehouse polygon
    3. Service→Service communication (calls WarehouseService, NOT WarehouseRepository)
    4. GPS lookup assumes non-overlapping area polygons
    5. Soft delete only (active=False, preserves historical data)
    6. PostGIS → GeoJSON transformation in response schemas

Example:
    ```python
    # Dependency injection (FastAPI)
    from app.dependencies import get_storage_area_service

    @router.post("/storage-areas")
    async def create_storage_area(
        request: StorageAreaCreateRequest,
        service: StorageAreaService = Depends(get_storage_area_service)
    ):
        return await service.create_storage_area(request)
    ```

See:
    - Task: backlog/03_kanban/00_backlog/S002-storage-area-service.md
    - Repository: app/repositories/storage_area_repository.py
    - Schemas: app/schemas/storage_area_schema.py
    - Model: app/models/storage_area.py
"""

from typing import Any, Literal, overload

from app.core.exceptions import (
    DuplicateCodeException,
    GeometryOutOfBoundsException,
    StorageAreaNotFoundException,
    WarehouseNotFoundException,
)
from app.repositories.storage_area_repository import StorageAreaRepository
from app.schemas.storage_area_schema import (
    StorageAreaCreateRequest,
    StorageAreaResponse,
    StorageAreaUpdateRequest,
    StorageAreaWithLocationsResponse,
)
from app.services.warehouse_service import WarehouseService


class StorageAreaService:
    """Business logic service for storage area operations.

    This service handles all storage area-related business logic:
    - CRUD operations with validation
    - GPS-based area discovery
    - Geometry containment validation (area within warehouse)
    - Schema transformations (PostGIS ↔ GeoJSON)
    - Parent warehouse validation via WarehouseService

    Service Layer Pattern:
        - Services call repositories for data access
        - Services call other services for cross-domain operations
        - Controllers/endpoints call services (NOT repositories directly)
        - NO direct access to other repositories (violates Clean Architecture)

    Attributes:
        storage_area_repo: Repository for storage area data access (injected)
        warehouse_service: Service for warehouse operations (injected)
    """

    def __init__(
        self,
        storage_area_repo: StorageAreaRepository,
        warehouse_service: WarehouseService,
    ) -> None:
        """Initialize service with repository and service dependencies.

        Args:
            storage_area_repo: StorageArea repository instance (injected)
            warehouse_service: Warehouse service instance (injected)

        Example:
            ```python
            # Via FastAPI dependency injection
            def get_storage_area_service(
                session: AsyncSession = Depends(get_db_session),
                warehouse_service: WarehouseService = Depends(get_warehouse_service)
            ):
                repo = StorageAreaRepository(session)
                return StorageAreaService(repo, warehouse_service)
            ```
        """
        self.storage_area_repo = storage_area_repo
        self.warehouse_service = warehouse_service

    async def create_storage_area(self, request: StorageAreaCreateRequest) -> StorageAreaResponse:
        """Create new storage area with business validation.

        Workflow:
            1. Validate parent warehouse exists (via WarehouseService)
            2. Check code uniqueness (duplicate detection)
            3. Validate geometry containment (area within warehouse)
            4. Create storage area in database
            5. Transform to response schema (PostGIS → GeoJSON)

        Args:
            request: Storage area creation request with validated fields

        Returns:
            StorageAreaResponse with generated ID and GeoJSON geometry

        Raises:
            WarehouseNotFoundException: If parent warehouse not found (404)
            DuplicateCodeException: If area code already exists (409)
            GeometryOutOfBoundsException: If area extends beyond warehouse (400)

        Performance:
            ~40-60ms total (includes parent validation + geometry validation)

        Example:
            ```python
            request = StorageAreaCreateRequest(
                warehouse_id=1,
                code="INV01-NORTH",
                name="North Wing",
                position="N",
                geojson_coordinates={...}
            )
            area = await service.create_storage_area(request)
            # area.storage_area_id -> auto-generated ID
            ```
        """
        # 1. Validate parent warehouse exists (Service→Service communication)
        warehouse = await self.warehouse_service.get_warehouse_by_id(request.warehouse_id)
        if not warehouse:
            raise WarehouseNotFoundException(warehouse_id=request.warehouse_id)

        # 2. Check code uniqueness (business rule: codes must be unique)
        from sqlalchemy import select

        stmt = select(self.storage_area_repo.model).where(
            self.storage_area_repo.model.code == request.code
        )
        result = await self.storage_area_repo.session.execute(stmt)
        existing = result.scalars().first()
        if existing:
            raise DuplicateCodeException(code=request.code)

        # 3. Validate geometry containment (area MUST be within warehouse)
        self._validate_within_parent(request.geojson_coordinates, warehouse.geojson_coordinates)

        # 4. Convert GeoJSON to PostGIS geometry and create area
        area_data = request.model_dump()

        # Convert GeoJSON dict to PostGIS geometry
        from geoalchemy2.shape import from_shape
        from shapely.geometry import shape

        polygon = shape(area_data["geojson_coordinates"])
        area_data["geojson_coordinates"] = from_shape(polygon, srid=4326)

        # Create in database
        area = await self.storage_area_repo.create(area_data)

        # 5. Transform to response schema (PostGIS → GeoJSON)
        return StorageAreaResponse.from_model(area)

    async def get_storage_area_by_id(self, area_id: int) -> StorageAreaResponse:
        """Get storage area by ID.

        Args:
            area_id: Primary key

        Returns:
            StorageAreaResponse with GeoJSON geometry

        Raises:
            StorageAreaNotFoundException: If area_id not found (404)

        Example:
            ```python
            area = await service.get_storage_area_by_id(123)
            ```
        """
        area = await self.storage_area_repo.get(area_id)
        if not area:
            raise StorageAreaNotFoundException(area_id=area_id)

        return StorageAreaResponse.from_model(area)

    async def get_storage_area_by_gps(
        self, longitude: float, latitude: float, warehouse_id: int | None = None
    ) -> StorageAreaResponse | None:
        """Find storage area containing GPS coordinates (photo localization).

        Uses PostGIS ST_Contains for point-in-polygon spatial query.
        Critical for ML pipeline: determine which storage area a photo belongs to.

        Args:
            longitude: GPS longitude (WGS84, e.g., -70.648)
            latitude: GPS latitude (WGS84, e.g., -33.449)
            warehouse_id: Optional warehouse filter to narrow search

        Returns:
            StorageAreaResponse if point is inside an area polygon, None otherwise

        Performance:
            ~30-50ms with GIST index on geojson_coordinates

        Example:
            ```python
            # Photo taken at these coordinates within warehouse 1
            area = await service.get_storage_area_by_gps(-70.648, -33.449, warehouse_id=1)
            if area:
            else:
            ```

        Note:
            Assumes non-overlapping area polygons.
            Returns first match if polygons overlap (undefined behavior).
        """
        # Use repository's GPS lookup method
        from geoalchemy2.functions import ST_Contains
        from sqlalchemy import func, select

        # NOTE: Database stores geometries as (lat, lon) instead of (lon, lat)
        # Inverting coordinates to match the stored data
        point = func.ST_SetSRID(func.ST_MakePoint(latitude, longitude), 4326)

        # Build query
        query = select(self.storage_area_repo.model).where(
            ST_Contains(self.storage_area_repo.model.geojson_coordinates, point)
        )

        # Add warehouse filter if provided
        if warehouse_id is not None:
            query = query.where(self.storage_area_repo.model.warehouse_id == warehouse_id)

        # Add active filter
        query = query.where(self.storage_area_repo.model.active == True)  # noqa: E712

        result = await self.storage_area_repo.session.execute(query)
        area = result.scalars().first()

        if not area:
            return None

        return StorageAreaResponse.from_model(area)

    @overload
    async def get_areas_by_warehouse(
        self, warehouse_id: int, active_only: bool = True, include_locations: Literal[False] = False
    ) -> list[StorageAreaResponse]: ...

    @overload
    async def get_areas_by_warehouse(
        self, warehouse_id: int, active_only: bool = True, include_locations: Literal[True] = True
    ) -> list[StorageAreaWithLocationsResponse]: ...

    async def get_areas_by_warehouse(
        self, warehouse_id: int, active_only: bool = True, include_locations: bool = False
    ) -> list[StorageAreaResponse] | list[StorageAreaWithLocationsResponse]:
        """Get all areas for a warehouse.

        Optionally includes storage_locations relationship for hierarchical views.

        Args:
            warehouse_id: Parent warehouse ID
            active_only: If True, only return active areas (default: True)
            include_locations: If True, include storage locations in response

        Returns:
            List of StorageAreaResponse (or StorageAreaWithLocationsResponse if include_locations=True)

        Performance:
            - Without locations: ~10-20ms for 20 areas
            - With locations: ~30-50ms (includes JOIN)

        Example:
            ```python
            # Get areas only
            areas = await service.get_areas_by_warehouse(1)

            # Get areas with storage locations
            areas = await service.get_areas_by_warehouse(1, include_locations=True)
            for area in areas:
            ```
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Build query
        query = select(self.storage_area_repo.model).where(
            self.storage_area_repo.model.warehouse_id == warehouse_id
        )

        # Add active filter
        if active_only:
            query = query.where(self.storage_area_repo.model.active == True)  # noqa: E712

        # Eager load storage_locations if requested
        if include_locations:
            query = query.options(selectinload(self.storage_area_repo.model.storage_locations))

        result = await self.storage_area_repo.session.execute(query)
        areas = result.scalars().all()

        if include_locations:
            return [StorageAreaWithLocationsResponse.from_model(area) for area in areas]

        return [StorageAreaResponse.from_model(area) for area in areas]

    async def calculate_utilization(self, area_id: int) -> float:
        """Calculate storage area utilization percentage.

        Calculates what % of the storage area is occupied by active storage_locations.

        Args:
            area_id: Storage area ID

        Returns:
            Utilization percentage (0.0 - 100.0)

        Raises:
            StorageAreaNotFoundException: If area_id not found

        Performance:
            ~50-100ms for 50 storage_locations (aggregates area_m2)

        Example:
            ```python
            utilization = await service.calculate_utilization(123)
            ```
        """
        area = await self.storage_area_repo.get(area_id)
        if not area or not area.area_m2:
            raise StorageAreaNotFoundException(area_id=area_id)

        # Sum area of all active storage_locations
        from sqlalchemy import func, select

        from app.models.storage_location import StorageLocation

        query = select(func.sum(StorageLocation.area_m2)).where(
            (StorageLocation.storage_area_id == area_id) & (StorageLocation.active == True)  # noqa: E712
        )

        result = await self.storage_area_repo.session.execute(query)
        used_area = result.scalar() or 0.0

        return (float(used_area) / float(area.area_m2)) * 100 if area.area_m2 > 0 else 0.0

    async def update_storage_area(
        self, area_id: int, request: StorageAreaUpdateRequest
    ) -> StorageAreaResponse:
        """Update storage area with geometry validation.

        Supports partial updates (only provided fields are modified).

        Workflow:
            1. Check storage area exists
            2. Validate new geometry containment if provided
            3. Update storage area in database
            4. Transform to response schema

        Args:
            area_id: Storage area ID to update
            request: Update request (partial fields supported)

        Returns:
            Updated StorageAreaResponse

        Raises:
            StorageAreaNotFoundException: If area_id not found (404)
            GeometryOutOfBoundsException: If new geometry extends beyond warehouse (400)

        Example:
            ```python
            # Partial update (only name)
            request = StorageAreaUpdateRequest(name="Updated Name")
            updated = await service.update_storage_area(123, request)

            # Update with new geometry
            request = StorageAreaUpdateRequest(
                name="New Name",
                geojson_coordinates={...}
            )
            updated = await service.update_storage_area(123, request)
            ```
        """
        # 1. Check storage area exists
        area = await self.storage_area_repo.get(area_id)
        if not area:
            raise StorageAreaNotFoundException(area_id=area_id)

        # 2. Validate new geometry containment if provided
        update_data = request.model_dump(exclude_unset=True)

        if "geojson_coordinates" in update_data:
            # Get parent warehouse to validate containment
            if not area.warehouse_id:
                raise StorageAreaNotFoundException(area_id=area_id)
            warehouse = await self.warehouse_service.get_warehouse_by_id(area.warehouse_id)
            self._validate_within_parent(
                update_data["geojson_coordinates"], warehouse.geojson_coordinates
            )

            # Convert GeoJSON to PostGIS geometry
            from geoalchemy2.shape import from_shape
            from shapely.geometry import shape

            polygon = shape(update_data["geojson_coordinates"])
            update_data["geojson_coordinates"] = from_shape(polygon, srid=4326)

        # 3. Update storage area
        updated = await self.storage_area_repo.update(area_id, update_data)
        if not updated:
            raise StorageAreaNotFoundException(area_id=area_id)

        # 4. Transform to response
        return StorageAreaResponse.from_model(updated)

    async def delete_storage_area(self, area_id: int) -> bool:
        """Soft delete storage area (set active=False).

        Preserves historical data for audit trails.
        Does NOT cascade to child entities (manual cleanup required).

        Args:
            area_id: Storage area ID to delete

        Returns:
            True if deleted successfully

        Raises:
            StorageAreaNotFoundException: If area_id not found (404)

        Example:
            ```python
            deleted = await service.delete_storage_area(123)
            # area.active = False (still in database)
            ```

        Note:
            This is a SOFT delete. Area remains in database with active=False.
            Child entities (storage locations) are NOT automatically deactivated.
        """
        # Check storage area exists
        area = await self.storage_area_repo.get(area_id)
        if not area:
            raise StorageAreaNotFoundException(area_id=area_id)

        # Soft delete (set active=False)
        await self.storage_area_repo.update(area_id, {"active": False})
        return True

    def _validate_within_parent(
        self, child_geojson: dict[str, Any], parent_geojson: dict[str, Any]
    ) -> None:
        """Validate child geometry is fully within parent boundaries (private helper).

        Uses Shapely for geometry containment check before database insert.
        Ensures storage area polygon is completely within warehouse polygon.

        Args:
            child_geojson: Storage area GeoJSON Polygon dictionary
            parent_geojson: Parent warehouse GeoJSON Polygon dictionary

        Raises:
            GeometryOutOfBoundsException: If child extends beyond parent

        Performance:
            ~10-20ms (Shapely validation is synchronous)

        Validation Rules:
            1. Child polygon must be completely within parent polygon
            2. Touching edges is allowed (boundary intersection OK)
            3. Any part extending outside parent is rejected

        Example:
            ```python
            # Valid: area fully within warehouse
            warehouse_geojson = {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0], [10, 0], [10, 10], [0, 10], [0, 0]
                ]]
            }
            area_geojson = {
                "type": "Polygon",
                "coordinates": [[
                    [2, 2], [8, 2], [8, 8], [2, 8], [2, 2]
                ]]
            }
            self._validate_within_parent(area_geojson, warehouse_geojson)  # OK

            # Invalid: area extends beyond warehouse
            area_geojson = {
                "type": "Polygon",
                "coordinates": [[
                    [5, 5], [15, 5], [15, 15], [5, 15], [5, 5]  # Extends to x=15
                ]]
            }
            self._validate_within_parent(area_geojson, warehouse_geojson)  # Raises
            ```
        """
        from shapely.geometry import shape

        # Convert GeoJSON to Shapely geometries
        child_polygon = shape(child_geojson)
        parent_polygon = shape(parent_geojson)

        # Check containment (child must be within parent)
        if not parent_polygon.contains(child_polygon):
            raise GeometryOutOfBoundsException(
                child="StorageArea",
                parent="Warehouse",
                message="Storage area extends beyond warehouse boundaries",
            )
