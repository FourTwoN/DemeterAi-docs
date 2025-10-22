# S003: StorageLocationService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: L (5 story points)
- **Area**: `services/location`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [S004, S006, S007, S036, C003]
    - Blocked by: [R003, S001, S002]

## Related Documentation

- **Engineering Plan
  **: [../../engineering_plan/backend/service_layer.md](../../engineering_plan/backend/service_layer.md)
- **Architecture
  **: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)
- **Workflows
  **: [../../engineering_plan/workflows/README.md](../../engineering_plan/workflows/README.md)

## Description

**What**: Implement `StorageLocationService` for storage location business logic, **GPS → full
location hierarchy lookup**, and configuration management integration.

**Why**: Storage locations are level 3 of the hierarchy and the **primary unit for stock tracking**.
This service is CRITICAL for photo localization (GPS → warehouse → area → location) and integrates
with StorageLocationConfigService for expected product validation.

**Context**: Clean Architecture Application Layer. StorageLocationService orchestrates GPS-based
hierarchy traversal (calls WarehouseService → StorageAreaService) and validates configurations. This
is the **most complex location service** due to GPS lookup orchestration.

## Acceptance Criteria

- [ ] **AC1**: GPS-based full hierarchy lookup (CRITICAL for photo localization):
  ```python
  from app.services.warehouse_service import WarehouseService
  from app.services.storage_area_service import StorageAreaService
  from app.repositories.storage_location_repository import StorageLocationRepository

  class StorageLocationService:
      """Business logic for storage locations (level 3)"""

      def __init__(
          self,
          location_repo: StorageLocationRepository,
          warehouse_service: WarehouseService,
          area_service: StorageAreaService
      ):
          self.location_repo = location_repo
          self.warehouse_service = warehouse_service
          self.area_service = area_service

      async def get_location_by_gps(
          self,
          longitude: float,
          latitude: float
      ) -> Optional[StorageLocationResponse]:
          """
          GPS → full hierarchy lookup (warehouse → area → location)
          CRITICAL for photo localization
          """
          # 1. Find warehouse containing GPS point
          warehouse = await self.warehouse_service.get_warehouse_by_gps(
              longitude, latitude
          )
          if not warehouse:
              return None

          # 2. Find storage area within warehouse
          area = await self.area_service.get_storage_area_by_gps(
              longitude, latitude, warehouse_id=warehouse.warehouse_id
          )
          if not area:
              return None

          # 3. Find storage location within area
          location = await self.location_repo.get_by_gps_point(
              longitude, latitude, storage_area_id=area.storage_area_id
          )
          if not location:
              return None

          return StorageLocationResponse.from_model(location)
  ```

- [ ] **AC2**: Create location with parent validation:
  ```python
  async def create_storage_location(
      self,
      request: StorageLocationCreateRequest
  ) -> StorageLocationResponse:
      """Create storage location with parent area validation"""
      # 1. Validate parent storage area exists
      area = await self.area_service.get_storage_area_by_id(request.storage_area_id)
      if not area:
          raise StorageAreaNotFoundException(request.storage_area_id)

      # 2. Validate geometry within parent bounds
      await self._validate_within_parent(request.geojson_coordinates, area)

      # 3. Check code uniqueness within area
      existing = await self.location_repo.get_by_code_in_area(
          request.code, request.storage_area_id
      )
      if existing:
          raise DuplicateCodeException(
              f"Location code '{request.code}' already exists in area {area.code}"
          )

      # 4. Create location
      location = await self.location_repo.create(request.model_dump())

      return StorageLocationResponse.from_model(location)
  ```

- [ ] **AC3**: Get locations with configuration data:
  ```python
  async def get_locations_with_config(
      self,
      storage_area_id: int,
      active_only: bool = True
  ) -> List[StorageLocationWithConfigResponse]:
      """Get locations with expected product configuration"""
      locations = await self.location_repo.get_by_storage_area(
          storage_area_id,
          active_only=active_only,
          with_config=True  # Eager load storage_location_configs
      )

      return [
          StorageLocationWithConfigResponse.from_model(loc)
          for loc in locations
      ]
  ```

- [ ] **AC4**: Bulk GPS lookup (optimization for multi-photo processing):
  ```python
  async def bulk_gps_lookup(
      self,
      gps_points: List[tuple[float, float]]
  ) -> Dict[tuple[float, float], Optional[StorageLocationResponse]]:
      """
      Batch GPS lookups for multiple photos
      Optimization: Single PostGIS query with UNION ALL
      """
      results = await self.location_repo.bulk_get_by_gps_points(gps_points)

      return {
          (point[0], point[1]): StorageLocationResponse.from_model(loc)
          if loc else None
          for point, loc in zip(gps_points, results)
      }
  ```

- [ ] **AC5**: Location utilization with stock integration:
  ```python
  async def calculate_location_utilization(
      self,
      location_id: int
  ) -> LocationUtilizationResponse:
      """
      Calculate storage location utilization
      Requires integration with stock_batches (future)
      """
      location = await self.location_repo.get(location_id)
      if not location:
          raise StorageLocationNotFoundException(location_id)

      # Get current stock batches for location
      # NOTE: Requires StockBatchService (S008) - placeholder for now
      current_stock = 0  # TODO: await stock_batch_service.get_total_for_location(location_id)

      # Get expected capacity from configuration
      config = location.storage_location_configs[0] if location.storage_location_configs else None
      expected_capacity = config.expected_quantity if config else None

      utilization = (current_stock / expected_capacity * 100) if expected_capacity else None

      return LocationUtilizationResponse(
          location_id=location_id,
          current_stock=current_stock,
          expected_capacity=expected_capacity,
          utilization_percentage=utilization
      )
  ```

- [ ] **AC6**: Schema with nested hierarchy:
  ```python
  # In app/schemas/storage_location_schema.py
  class StorageLocationResponse(BaseModel):
      storage_location_id: int
      storage_area_id: int
      code: str
      name: str
      location_type: str
      geojson_coordinates: dict
      area_m2: Optional[float]
      active: bool

      # Optional nested hierarchy
      storage_area: Optional["StorageAreaResponse"] = None
      warehouse: Optional["WarehouseResponse"] = None

      @classmethod
      def from_model(
          cls,
          location: StorageLocation,
          include_hierarchy: bool = False
      ) -> "StorageLocationResponse":
          """Transform with optional parent data"""
          from geoalchemy2.shape import to_shape

          response = cls(
              storage_location_id=location.storage_location_id,
              storage_area_id=location.storage_area_id,
              code=location.code,
              name=location.name,
              location_type=location.location_type,
              geojson_coordinates=to_shape(location.geojson_coordinates).__geo_interface__,
              area_m2=location.area_m2,
              active=location.active
          )

          if include_hierarchy:
              if location.storage_area:
                  response.storage_area = StorageAreaResponse.from_model(
                      location.storage_area, include_warehouse=True
                  )
                  response.warehouse = response.storage_area.warehouse

          return response
  ```

- [ ] **AC7**: Unit tests achieve ≥85% coverage

## Technical Implementation Notes

### Architecture

- **Layer**: Application (Service)
- **Dependencies**: R003 (StorageLocationRepository), S001 (WarehouseService), S002 (
  StorageAreaService)
- **Design Pattern**: **Orchestration service** - coordinates GPS hierarchy traversal
- **Critical for**: Photo localization ML pipeline

### Code Hints

**GPS hierarchy traversal optimization:**

```python
# Cache hierarchy lookups for repeated GPS queries
from functools import lru_cache

@lru_cache(maxsize=1000)
async def _cached_gps_lookup(longitude: float, latitude: float):
    """Cache GPS lookups (useful for repeated photo processing)"""
    # Round coordinates to 6 decimals (~10cm precision)
    lon_key = round(longitude, 6)
    lat_key = round(latitude, 6)
    return await self.get_location_by_gps(lon_key, lat_key)
```

**Bulk GPS query (PostGIS optimization):**

```sql
-- In repository layer
WITH gps_points AS (
  SELECT
    ST_SetSRID(ST_MakePoint(lon, lat), 4326) AS point,
    lon, lat
  FROM UNNEST(ARRAY[...]) AS coords(lon, lat)
)
SELECT
  gp.lon, gp.lat,
  sl.*
FROM gps_points gp
LEFT JOIN storage_locations sl ON ST_Contains(sl.geojson_coordinates, gp.point)
WHERE sl.active = true;
```

### Testing Requirements

**Unit Tests**:

```python
@pytest.mark.asyncio
async def test_gps_hierarchy_lookup():
    """Test GPS → warehouse → area → location traversal"""
    location_repo = AsyncMock()
    warehouse_service = AsyncMock()
    area_service = AsyncMock()

    # Mock hierarchy
    warehouse_service.get_warehouse_by_gps.return_value = Mock(warehouse_id=1)
    area_service.get_storage_area_by_gps.return_value = Mock(storage_area_id=1)
    location_repo.get_by_gps_point.return_value = Mock(storage_location_id=1)

    service = StorageLocationService(location_repo, warehouse_service, area_service)
    result = await service.get_location_by_gps(-70.648, -33.449)

    assert result is not None
    # Verify service call chain
    warehouse_service.get_warehouse_by_gps.assert_called_once_with(-70.648, -33.449)
    area_service.get_storage_area_by_gps.assert_called_once()

@pytest.mark.asyncio
async def test_gps_lookup_no_warehouse():
    """Test GPS lookup fails gracefully when no warehouse found"""
    warehouse_service = AsyncMock()
    warehouse_service.get_warehouse_by_gps.return_value = None  # No warehouse

    service = StorageLocationService(AsyncMock(), warehouse_service, AsyncMock())
    result = await service.get_location_by_gps(-70.648, -33.449)

    assert result is None
    # Should not call area_service (short-circuit)

@pytest.mark.asyncio
async def test_bulk_gps_lookup():
    """Test batch GPS processing for multiple photos"""
    location_repo = AsyncMock()
    gps_points = [(-70.648, -33.449), (-70.649, -33.450)]

    location_repo.bulk_get_by_gps_points.return_value = [
        Mock(storage_location_id=1),
        Mock(storage_location_id=2)
    ]

    service = StorageLocationService(location_repo, AsyncMock(), AsyncMock())
    results = await service.bulk_gps_lookup(gps_points)

    assert len(results) == 2
    location_repo.bulk_get_by_gps_points.assert_called_once_with(gps_points)
```

**Coverage Target**: ≥85%

### Performance Expectations

- `get_location_by_gps`: <150ms (3 sequential queries - warehouse, area, location)
- `bulk_gps_lookup`: <200ms for 10 GPS points (single query with UNION ALL)
- `create_storage_location`: <40ms
- Cached GPS lookup: <5ms (LRU cache hit)

## Handover Briefing

**For the next developer:**

**Context**: StorageLocationService is the **MOST CRITICAL service for photo localization**. The GPS
hierarchy traversal (warehouse → area → location) is the core of the ML pipeline's location
discovery.

**Key decisions made**:

1. **Orchestrated GPS lookup**: Calls WarehouseService → StorageAreaService → own repository (
   3-level traversal)
2. **Bulk optimization**: Single PostGIS query for multiple GPS points (photo batches)
3. **Configuration integration**: Eager loads `storage_location_configs` for expected product
   validation
4. **Short-circuit on failure**: If warehouse not found, don't query areas/locations
5. **LRU cache opportunity**: GPS coordinates can be cached (10cm precision rounding)

**Known limitations**:

- GPS hierarchy lookup is sequential (3 queries) - can't parallelize without duplication
- Utilization calculation requires StockBatchService integration (S008)
- Cache invalidation needed if location geometries change

**Next steps**:

- S004: StorageBinService (level 4 of hierarchy, similar pattern)
- S006: LocationHierarchyService (aggregates all location services)
- S036: StorageLocationConfigService (expected product management)

**Questions to validate**:

- Should bulk GPS lookup be limited (max 100 points per call)?
- How to handle GPS points on location boundaries (edge cases)?
- Is 10cm GPS precision sufficient for caching?

## Definition of Done Checklist

- [ ] Service code with GPS hierarchy traversal
- [ ] Orchestration via WarehouseService and StorageAreaService (NOT repositories)
- [ ] Bulk GPS lookup optimization implemented
- [ ] Unit tests pass (≥85% coverage)
- [ ] Integration tests with full hierarchy
- [ ] Performance benchmarks documented
- [ ] Type hints validated
- [ ] PR reviewed (2+ approvals)

## Time Tracking

- **Estimated**: 5 story points (~10 hours)
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
