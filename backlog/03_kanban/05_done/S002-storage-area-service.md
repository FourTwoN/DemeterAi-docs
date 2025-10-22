# S002: StorageAreaService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `services/location`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [S003, S006, C002]
    - Blocked by**: [R002, S001]

## Related Documentation

- **Engineering Plan
  **: [../../engineering_plan/backend/service_layer.md](../../engineering_plan/backend/service_layer.md)
- **Architecture
  **: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd)

## Description

**What**: Implement `StorageAreaService` for storage area business logic, hierarchy validation, and
GPS-based area lookup.

**Why**: Storage areas are level 2 of the 4-tier hierarchy (warehouse → storage_area →
storage_location → storage_bin). Service validates parent-child relationships and provides
geospatial queries for area localization.

**Context**: Clean Architecture Application Layer. StorageAreaService calls WarehouseService to
validate parent warehouse existence (service-to-service communication). NO direct repository calls
to WarehouseRepository.

## Acceptance Criteria

- [ ] **AC1**: `StorageAreaService` class with parent validation via WarehouseService:
  ```python
  from app.services.warehouse_service import WarehouseService
  from app.repositories.storage_area_repository import StorageAreaRepository
  from app.schemas.storage_area_schema import (
      StorageAreaCreateRequest,
      StorageAreaResponse
  )
  from app.exceptions import WarehouseNotFoundException, GeometryOutOfBoundsException

  class StorageAreaService:
      """Business logic for storage area operations"""

      def __init__(
          self,
          storage_area_repo: StorageAreaRepository,
          warehouse_service: WarehouseService  # ← Service dependency, NOT repository
      ):
          self.storage_area_repo = storage_area_repo
          self.warehouse_service = warehouse_service

      async def create_storage_area(
          self,
          request: StorageAreaCreateRequest
      ) -> StorageAreaResponse:
          """Create storage area with parent warehouse validation"""
          # 1. Validate parent warehouse exists (via service)
          warehouse = await self.warehouse_service.get_warehouse_by_id(request.warehouse_id)
          if not warehouse:
              raise WarehouseNotFoundException(request.warehouse_id)

          # 2. Validate area geometry is within warehouse bounds
          await self._validate_within_parent(request.geojson_coordinates, warehouse)

          # 3. Create storage area
          area = await self.storage_area_repo.create(request.model_dump())

          return StorageAreaResponse.from_model(area)
  ```

- [ ] **AC2**: Geospatial containment validation:
  ```python
  async def _validate_within_parent(
      self,
      area_geometry: dict,
      warehouse: WarehouseResponse
  ) -> None:
      """Validate storage area is fully within warehouse boundaries"""
      from shapely.geometry import shape

      area_polygon = shape(area_geometry)
      warehouse_polygon = shape(warehouse.geojson_coordinates)

      if not warehouse_polygon.contains(area_polygon):
          raise GeometryOutOfBoundsException(
              f"Storage area extends beyond warehouse {warehouse.code} boundaries"
          )
  ```

- [ ] **AC3**: GPS-based area lookup:
  ```python
  async def get_storage_area_by_gps(
      self,
      longitude: float,
      latitude: float,
      warehouse_id: Optional[int] = None
  ) -> Optional[StorageAreaResponse]:
      """Find storage area containing GPS point"""
      area = await self.storage_area_repo.get_by_gps_point(
          longitude,
          latitude,
          warehouse_id
      )
      if not area:
          return None
      return StorageAreaResponse.from_model(area)
  ```

- [ ] **AC4**: Get areas by warehouse with filtering:
  ```python
  async def get_areas_by_warehouse(
      self,
      warehouse_id: int,
      active_only: bool = True,
      include_locations: bool = False
  ) -> List[StorageAreaResponse]:
      """Get all areas for a warehouse"""
      areas = await self.storage_area_repo.get_by_warehouse(
          warehouse_id,
          active_only=active_only,
          with_locations=include_locations
      )
      return [StorageAreaResponse.from_model(area) for area in areas]
  ```

- [ ] **AC5**: Utilization calculation:
  ```python
  async def calculate_utilization(self, area_id: int) -> float:
      """Calculate storage area utilization percentage"""
      area = await self.storage_area_repo.get(area_id)
      if not area or not area.area_m2:
          return 0.0

      # Sum area of all active storage_locations
      locations = await self.storage_area_repo.get_locations_for_area(area_id)
      used_area = sum(loc.area_m2 or 0 for loc in locations if loc.active)

      return (used_area / area.area_m2) * 100 if area.area_m2 > 0 else 0.0
  ```

- [ ] **AC6**: Schema transformations with nested warehouse data:
  ```python
  # In app/schemas/storage_area_schema.py
  class StorageAreaResponse(BaseModel):
      storage_area_id: int
      warehouse_id: int
      code: str
      name: str
      area_type: str
      geojson_coordinates: dict
      area_m2: Optional[float]
      active: bool
      created_at: datetime

      # Optional nested warehouse
      warehouse: Optional["WarehouseResponse"] = None

      @classmethod
      def from_model(
          cls,
          area: StorageArea,
          include_warehouse: bool = False
      ) -> "StorageAreaResponse":
          """Transform model → schema"""
          from geoalchemy2.shape import to_shape

          response = cls(
              storage_area_id=area.storage_area_id,
              warehouse_id=area.warehouse_id,
              code=area.code,
              name=area.name,
              area_type=area.area_type,
              geojson_coordinates=to_shape(area.geojson_coordinates).__geo_interface__,
              area_m2=area.area_m2,
              active=area.active,
              created_at=area.created_at
          )

          if include_warehouse and area.warehouse:
              from app.schemas.warehouse_schema import WarehouseResponse
              response.warehouse = WarehouseResponse.from_model(area.warehouse)

          return response
  ```

- [ ] **AC7**: Unit tests achieve ≥85% coverage

## Technical Implementation Notes

### Architecture

- **Layer**: Application (Service)
- **Dependencies**: R002 (StorageAreaRepository), S001 (WarehouseService)
- **Design Pattern**: Service-to-service communication (calls WarehouseService, NOT
  WarehouseRepository)
- **Critical Rule**: NO direct repository access to other domains

### Code Hints

**Dependency injection:**

```python
# In app/dependencies.py
async def get_storage_area_service(
    session: AsyncSession = Depends(get_db_session),
    warehouse_service: WarehouseService = Depends(get_warehouse_service)
) -> StorageAreaService:
    """DI for StorageAreaService"""
    repo = StorageAreaRepository(session)
    return StorageAreaService(repo, warehouse_service)
```

**Shapely containment check:**

```python
from shapely.geometry import shape

def is_within(child_geojson: dict, parent_geojson: dict) -> bool:
    """Check if child geometry is fully within parent"""
    child = shape(child_geojson)
    parent = shape(parent_geojson)
    return parent.contains(child)
```

### Testing Requirements

**Unit Tests**:

```python
@pytest.mark.asyncio
async def test_create_area_with_parent_validation():
    """Test parent warehouse validation via service call"""
    area_repo = AsyncMock()
    warehouse_service = AsyncMock()

    # Mock warehouse exists
    warehouse_service.get_warehouse_by_id.return_value = Mock(
        warehouse_id=1,
        code="WH001",
        geojson_coordinates={"type": "Polygon", "coordinates": [...]}
    )

    service = StorageAreaService(area_repo, warehouse_service)
    request = StorageAreaCreateRequest(warehouse_id=1, ...)

    result = await service.create_storage_area(request)

    # Verify service call (NOT repository)
    warehouse_service.get_warehouse_by_id.assert_called_once_with(1)
    area_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_create_area_geometry_out_of_bounds():
    """Test rejection when area extends beyond warehouse"""
    warehouse_service = AsyncMock()
    warehouse_service.get_warehouse_by_id.return_value = Mock(
        geojson_coordinates={
            "type": "Polygon",
            "coordinates": [[
                [0, 0], [10, 0], [10, 10], [0, 10], [0, 0]
            ]]
        }
    )

    service = StorageAreaService(AsyncMock(), warehouse_service)

    # Area extends beyond warehouse
    request = StorageAreaCreateRequest(
        warehouse_id=1,
        geojson_coordinates={
            "type": "Polygon",
            "coordinates": [[
                [5, 5], [15, 5], [15, 15], [5, 15], [5, 5]  # Extends to x=15
            ]]
        },
        ...
    )

    with pytest.raises(GeometryOutOfBoundsException):
        await service.create_storage_area(request)
```

**Coverage Target**: ≥85%

### Performance Expectations

- `create_storage_area`: <40ms (includes parent validation + geometry check)
- `get_storage_area_by_gps`: <50ms (PostGIS query)
- `calculate_utilization`: <100ms for 50 storage_locations

## Handover Briefing

**For the next developer:**

**Context**: StorageAreaService demonstrates **service-to-service communication**. It calls
WarehouseService (NOT WarehouseRepository directly) to validate parent relationships.

**Key decisions made**:

1. **Parent validation via service**: Calls `warehouse_service.get_warehouse_by_id()` (
   encapsulation)
2. **Geometric containment**: Shapely validates areas fit within warehouse boundaries
3. **Utilization calculation**: Aggregates child storage_locations area
4. **Optional nested data**: Schemas can include parent warehouse (avoid N+1 queries)

**Known limitations**:

- Geometry containment check is sync (Shapely) - adds 10-20ms overhead
- Utilization calculation requires separate query to sum locations
- No auto-adjustment if warehouse geometry changes

**Next steps**:

- S003: StorageLocationService (similar pattern, calls StorageAreaService)
- S006: LocationHierarchyService (aggregates S001-S004)

**Questions to validate**:

- Should containment validation allow areas to touch warehouse edges?
- How to handle warehouse geometry updates affecting existing areas?

## Definition of Done Checklist

- [ ] Service code written
- [ ] Parent validation via WarehouseService (NOT repository)
- [ ] Geometry containment validation working
- [ ] Unit tests pass (≥85% coverage)
- [ ] Integration tests pass
- [ ] Type hints validated
- [ ] PR reviewed (2+ approvals)

## Time Tracking

- **Estimated**: 3 story points (~6 hours)
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
