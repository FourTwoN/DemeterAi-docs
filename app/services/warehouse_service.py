"""Warehouse business logic service.

This module implements the service layer for warehouse operations following
Clean Architecture principles. Services orchestrate business logic and coordinate
repository operations.

Key Features:
- GPS-based warehouse lookup (critical for photo localization)
- Geometry validation with Shapely (fail fast)
- Duplicate code detection
- Soft delete pattern (preserve historical data)
- Schema transformations (PostGIS ↔ GeoJSON)

Architecture:
    Layer: Application (Service)
    Pattern: Service Layer with Dependency Injection
    Dependencies: WarehouseRepository (ONLY - no cross-repository access)
    Used by: WarehouseController (future), ML pipeline

Design Decisions:
    1. Geometry validation BEFORE database insert (fail fast, ~10-20ms overhead)
    2. GPS lookup assumes non-overlapping warehouse polygons
    3. Soft delete only (active=False, preserves historical data)
    4. PostGIS → GeoJSON transformation in response schemas
    5. No repository access except self.warehouse_repo (Clean Architecture)

Example:
    ```python
    # Dependency injection (FastAPI)
    from app.dependencies import get_warehouse_service

    @router.post("/warehouses")
    async def create_warehouse(
        request: WarehouseCreateRequest,
        service: WarehouseService = Depends(get_warehouse_service)
    ):
        return await service.create_warehouse(request)
    ```

See:
    - Task: backlog/03_kanban/01_ready/S001-warehouse-service.md
    - Repository: app/repositories/warehouse_repository.py
    - Schemas: app/schemas/warehouse_schema.py
    - Model: app/models/warehouse.py
"""

from app.core.exceptions import DuplicateCodeException, WarehouseNotFoundException
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.warehouse_schema import (
    WarehouseCreateRequest,
    WarehouseResponse,
    WarehouseUpdateRequest,
    WarehouseWithAreasResponse,
)


class WarehouseService:
    """Business logic service for warehouse operations.

    This service handles all warehouse-related business logic:
    - CRUD operations with validation
    - GPS-based warehouse discovery
    - Geometry validation (Shapely)
    - Schema transformations (PostGIS ↔ GeoJSON)

    Service Layer Pattern:
        - Services call repositories for data access
        - Services call other services for cross-domain operations
        - Controllers/endpoints call services (NOT repositories directly)
        - NO direct access to other repositories (violates Clean Architecture)

    Attributes:
        warehouse_repo: Repository for warehouse data access (injected)
    """

    def __init__(self, warehouse_repo: WarehouseRepository) -> None:
        """Initialize service with repository dependency.

        Args:
            warehouse_repo: Warehouse repository instance (injected)

        Example:
            ```python
            # Via FastAPI dependency injection
            def get_warehouse_service(session: AsyncSession = Depends(get_db_session)):
                repo = WarehouseRepository(session)
                return WarehouseService(repo)
            ```
        """
        self.warehouse_repo = warehouse_repo

    async def create_warehouse(self, request: WarehouseCreateRequest) -> WarehouseResponse:
        """Create new warehouse with business validation.

        Workflow:
            1. Check code uniqueness (duplicate detection)
            2. Validate geometry (Shapely: polygon, closed, ≥3 vertices)
            3. Create warehouse in database
            4. Transform to response schema (PostGIS → GeoJSON)

        Args:
            request: Warehouse creation request with validated fields

        Returns:
            WarehouseResponse with generated ID and GeoJSON geometry

        Raises:
            DuplicateCodeException: If warehouse code already exists (409)
            ValueError: If geometry validation fails (400)

        Performance:
            ~30-50ms total (includes geometry validation ~10-20ms)

        Example:
            ```python
            request = WarehouseCreateRequest(
                code="GH-001",
                name="Main Greenhouse",
                warehouse_type="greenhouse",
                geojson_coordinates={...}
            )
            warehouse = await service.create_warehouse(request)
            # warehouse.warehouse_id -> auto-generated ID
            ```
        """
        # 1. Check code uniqueness (business rule: codes must be unique)
        existing = await self.warehouse_repo.get_by_code(request.code)
        if existing:
            raise DuplicateCodeException(code=request.code)

        # 2. Validate geometry before database insert (fail fast)
        self._validate_geometry(request.geojson_coordinates)

        # 3. Convert GeoJSON to PostGIS geometry and create warehouse
        warehouse_data = request.model_dump()

        # Convert GeoJSON dict to PostGIS geometry
        from geoalchemy2.shape import from_shape
        from shapely.geometry import shape

        polygon = shape(warehouse_data["geojson_coordinates"])
        warehouse_data["geojson_coordinates"] = from_shape(polygon, srid=4326)

        # Create in database
        warehouse = await self.warehouse_repo.create(warehouse_data)

        # 4. Transform to response schema (PostGIS → GeoJSON)
        return WarehouseResponse.from_model(warehouse)

    async def get_warehouse_by_id(self, warehouse_id: int) -> WarehouseResponse:
        """Get warehouse by ID.

        Args:
            warehouse_id: Primary key

        Returns:
            WarehouseResponse with GeoJSON geometry

        Raises:
            WarehouseNotFoundException: If warehouse_id not found (404)

        Example:
            ```python
            warehouse = await service.get_warehouse_by_id(123)
            ```
        """
        warehouse = await self.warehouse_repo.get(warehouse_id)
        if not warehouse:
            raise WarehouseNotFoundException(warehouse_id=warehouse_id)

        return WarehouseResponse.from_model(warehouse)

    async def get_warehouse_by_gps(
        self, longitude: float, latitude: float
    ) -> WarehouseResponse | None:
        """Find warehouse containing GPS coordinates (photo localization).

        Uses PostGIS ST_Contains for point-in-polygon spatial query.
        Critical for ML pipeline: determine which warehouse a photo belongs to.

        Args:
            longitude: GPS longitude (WGS84, e.g., -70.648)
            latitude: GPS latitude (WGS84, e.g., -33.449)

        Returns:
            WarehouseResponse if point is inside a warehouse polygon, None otherwise

        Performance:
            ~30-50ms with GIST index on geojson_coordinates

        Example:
            ```python
            # Photo taken at these coordinates
            warehouse = await service.get_warehouse_by_gps(-70.648, -33.449)
            if warehouse:
                # Photo belongs to this warehouse
            else:
                # Photo is outside all warehouses
            ```

        Note:
            Assumes non-overlapping warehouse polygons.
            Returns first match if polygons overlap (undefined behavior).
        """
        warehouse = await self.warehouse_repo.get_by_gps_point(longitude, latitude)
        if not warehouse:
            return None

        return WarehouseResponse.from_model(warehouse)

    async def get_active_warehouses(
        self, include_areas: bool = False
    ) -> list[WarehouseResponse] | list[WarehouseWithAreasResponse]:
        """Get all active warehouses (soft delete filter).

        Optionally includes storage_areas relationship for hierarchical views.

        Args:
            include_areas: If True, include storage areas in response

        Returns:
            List of WarehouseResponse (or WarehouseWithAreasResponse if include_areas=True)

        Performance:
            - Without areas: ~10-20ms for 50 warehouses
            - With areas: ~30-50ms (includes JOIN)

        Example:
            ```python
            # Get warehouses only
            warehouses = await service.get_active_warehouses()

            # Get warehouses with storage areas
            warehouses = await service.get_active_warehouses(include_areas=True)
            for wh in warehouses:
            ```
        """
        warehouses = await self.warehouse_repo.get_active_warehouses(with_areas=include_areas)

        if include_areas:
            return [WarehouseWithAreasResponse.from_model(wh) for wh in warehouses]

        return [WarehouseResponse.from_model(wh) for wh in warehouses]

    async def update_warehouse(
        self, warehouse_id: int, request: WarehouseUpdateRequest
    ) -> WarehouseResponse:
        """Update warehouse with geometry validation.

        Supports partial updates (only provided fields are modified).

        Workflow:
            1. Check warehouse exists
            2. Validate new geometry if provided
            3. Update warehouse in database
            4. Transform to response schema

        Args:
            warehouse_id: Warehouse ID to update
            request: Update request (partial fields supported)

        Returns:
            Updated WarehouseResponse

        Raises:
            WarehouseNotFoundException: If warehouse_id not found (404)
            ValueError: If new geometry is invalid (400)

        Example:
            ```python
            # Partial update (only name)
            request = WarehouseUpdateRequest(name="New Name")
            updated = await service.update_warehouse(123, request)

            # Update with new geometry
            request = WarehouseUpdateRequest(
                name="New Name",
                geojson_coordinates={...}
            )
            updated = await service.update_warehouse(123, request)
            ```
        """
        # 1. Check warehouse exists
        warehouse = await self.warehouse_repo.get(warehouse_id)
        if not warehouse:
            raise WarehouseNotFoundException(warehouse_id=warehouse_id)

        # 2. Validate new geometry if provided
        update_data = request.model_dump(exclude_unset=True)

        if "geojson_coordinates" in update_data:
            self._validate_geometry(update_data["geojson_coordinates"])

            # Convert GeoJSON to PostGIS geometry
            from geoalchemy2.shape import from_shape
            from shapely.geometry import shape

            polygon = shape(update_data["geojson_coordinates"])
            update_data["geojson_coordinates"] = from_shape(polygon, srid=4326)

        # 3. Update warehouse
        updated = await self.warehouse_repo.update(warehouse_id, update_data)

        # 4. Transform to response
        return WarehouseResponse.from_model(updated)  # type: ignore

    async def delete_warehouse(self, warehouse_id: int) -> bool:
        """Soft delete warehouse (set active=False).

        Preserves historical data for audit trails.
        Does NOT cascade to child entities (manual cleanup required).

        Args:
            warehouse_id: Warehouse ID to delete

        Returns:
            True if deleted successfully

        Raises:
            WarehouseNotFoundException: If warehouse_id not found (404)

        Example:
            ```python
            deleted = await service.delete_warehouse(123)
            # warehouse.active = False (still in database)
            ```

        Note:
            This is a SOFT delete. Warehouse remains in database with active=False.
            Child entities (storage areas) are NOT automatically deactivated.
        """
        # Check warehouse exists
        warehouse = await self.warehouse_repo.get(warehouse_id)
        if not warehouse:
            raise WarehouseNotFoundException(warehouse_id=warehouse_id)

        # Soft delete (set active=False)
        await self.warehouse_repo.update(warehouse_id, {"active": False})
        return True

    def _validate_geometry(self, geojson: dict) -> None:
        """Validate warehouse boundary geometry (private helper).

        Uses Shapely for geometry validation before database insert.
        Ensures polygon is valid, closed, and has ≥3 vertices.

        Args:
            geojson: GeoJSON Polygon dictionary

        Raises:
            ValueError: If geometry is invalid with descriptive error message

        Performance:
            ~10-20ms (Shapely validation is synchronous)

        Validation Rules:
            1. Must be Polygon (not Point, LineString, etc.)
            2. Must be closed (first point = last point) - CHECKED BEFORE Shapely
            3. Must have ≥3 vertices (4 with closing point)
            4. Must be valid (no self-intersections, bow-ties, etc.)

        Example:
            ```python
            # Valid polygon
            geojson = {
                "type": "Polygon",
                "coordinates": [[
                    [-70.648, -33.449], [-70.647, -33.449],
                    [-70.647, -33.450], [-70.648, -33.450],
                    [-70.648, -33.449]  # Closed
                ]]
            }
            self._validate_geometry(geojson)  # OK

            # Invalid: not closed
            geojson = {
                "type": "Polygon",
                "coordinates": [[
                    [-70.648, -33.449], [-70.647, -33.449],
                    [-70.647, -33.450]  # Missing closing point
                ]]
            }
            self._validate_geometry(geojson)  # Raises ValueError
            ```
        """
        from shapely.geometry import shape
        from shapely.validation import explain_validity

        # Rule 1: Must have type Polygon (check GeoJSON structure)
        if geojson.get("type") != "Polygon":
            raise ValueError(
                f"Expected Polygon geometry, got {geojson.get('type')}. "
                "Warehouses must have polygon boundaries."
            )

        # Rule 2: Must be closed (BEFORE Shapely, since Shapely auto-closes)
        # Check the raw GeoJSON coordinates
        if "coordinates" not in geojson or not geojson["coordinates"]:
            raise ValueError("GeoJSON must have 'coordinates' field with at least one ring")

        coords = geojson["coordinates"][0]  # Outer ring

        # Check minimum length first (need at least 1 point to check closure)
        if len(coords) < 1:
            raise ValueError("Polygon coordinates cannot be empty")

        # Check if polygon is closed (first == last) - do this BEFORE checking vertex count
        # This gives more specific error messages
        if coords[0] != coords[-1]:
            raise ValueError(
                "Polygon must be closed (first point must equal last point). "
                f"First: {coords[0]}, "
                f"Last: {coords[-1]}"
            )

        # Now check vertex count (must have ≥4 coordinates with closing point)
        if len(coords) < 4:
            raise ValueError(
                f"Polygon must have at least 3 vertices (4 with closing point). "
                f"Got {len(coords)} coordinate(s)."
            )

        # Rule 3: Convert to Shapely for advanced validation
        polygon = shape(geojson)

        # Rule 4: Must be valid (no self-intersections, etc.)
        if not polygon.is_valid:
            reason = explain_validity(polygon)
            raise ValueError(f"Invalid polygon geometry: {reason}")
