# S006: LocationHierarchyService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: L (5 story points)
- **Area**: `services/location`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [C006, S013]
  - Blocked by: [S001, S002, S003, S004]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/service_layer.md](../../engineering_plan/backend/service_layer.md)
- **Architecture**: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)
- **Workflows**: [../../engineering_plan/workflows/README.md](../../engineering_plan/workflows/README.md)

## Description

**What**: Implement `LocationHierarchyService` as an **aggregation service** that provides unified access to all 4 levels of the location hierarchy (warehouse → storage_area → storage_location → storage_bin).

**Why**: Controllers and ML pipeline need a single entry point for location operations without knowing internal service dependencies. This service **orchestrates** S001-S004 and provides hierarchy-wide operations (tree navigation, breadcrumb paths, bulk operations).

**Context**: Clean Architecture Application Layer. **Aggregation pattern** - wraps S001-S004 services to provide high-level operations. Critical for photo localization ML pipeline and location management UI.

## Acceptance Criteria

- [ ] **AC1**: Unified GPS lookup (all 4 levels):
  ```python
  from app.services.warehouse_service import WarehouseService
  from app.services.storage_area_service import StorageAreaService
  from app.services.storage_location_service import StorageLocationService
  from app.services.storage_bin_service import StorageBinService

  class LocationHierarchyService:
      """
      Aggregation service for location hierarchy operations
      Orchestrates S001-S004 services
      """

      def __init__(
          self,
          warehouse_service: WarehouseService,
          area_service: StorageAreaService,
          location_service: StorageLocationService,
          bin_service: StorageBinService
      ):
          self.warehouse_service = warehouse_service
          self.area_service = area_service
          self.location_service = location_service
          self.bin_service = bin_service

      async def get_full_hierarchy_by_gps(
          self,
          longitude: float,
          latitude: float
      ) -> Optional[LocationHierarchyResponse]:
          """
          GPS → full 4-level hierarchy lookup
          CRITICAL for photo localization in ML pipeline
          """
          # 1. Get storage_location (includes warehouse + area traversal)
          location = await self.location_service.get_location_by_gps(longitude, latitude)
          if not location:
              return None

          # 2. Get bins within location (optional - bins might not exist)
          bins = await self.bin_service.get_bins_by_location(
              location.storage_location_id,
              active_only=True
          )

          # 3. Build hierarchy response
          return LocationHierarchyResponse(
              warehouse=location.warehouse,
              storage_area=location.storage_area,
              storage_location=location,
              storage_bins=bins if bins else []
          )
  ```

- [ ] **AC2**: Breadcrumb path generation:
  ```python
  async def get_breadcrumb_path(
      self,
      level: str,  # "warehouse", "area", "location", "bin"
      entity_id: int
  ) -> LocationBreadcrumbResponse:
      """
      Generate breadcrumb path for UI navigation
      Example: Warehouse WH001 → Area A1 → Location L01 → Bin B001
      """
      if level == "bin":
          bin_obj = await self.bin_service.get_storage_bin_by_id(entity_id)
          location = await self.location_service.get_storage_location_by_id(
              bin_obj.storage_location_id
          )
          area = await self.area_service.get_storage_area_by_id(
              location.storage_area_id
          )
          warehouse = await self.warehouse_service.get_warehouse_by_id(
              area.warehouse_id
          )

          return LocationBreadcrumbResponse(
              path=[
                  {"level": "warehouse", "id": warehouse.warehouse_id, "name": warehouse.name},
                  {"level": "area", "id": area.storage_area_id, "name": area.name},
                  {"level": "location", "id": location.storage_location_id, "name": location.name},
                  {"level": "bin", "id": bin_obj.storage_bin_id, "name": bin_obj.name}
              ]
          )

      # Similar for other levels (location, area, warehouse)
      # ...
  ```

- [ ] **AC3**: Tree structure generation for UI:
  ```python
  async def get_hierarchy_tree(
      self,
      warehouse_id: Optional[int] = None
  ) -> List[LocationTreeNode]:
      """
      Generate full tree structure for location picker UI
      Optionally filter by warehouse
      """
      warehouses = (
          [await self.warehouse_service.get_warehouse_by_id(warehouse_id)]
          if warehouse_id
          else await self.warehouse_service.get_active_warehouses(include_areas=True)
      )

      tree = []
      for warehouse in warehouses:
          warehouse_node = LocationTreeNode(
              level="warehouse",
              id=warehouse.warehouse_id,
              code=warehouse.code,
              name=warehouse.name,
              children=[]
          )

          # Get storage areas
          areas = await self.area_service.get_areas_by_warehouse(
              warehouse.warehouse_id,
              include_locations=True
          )

          for area in areas:
              area_node = LocationTreeNode(
                  level="area",
                  id=area.storage_area_id,
                  code=area.code,
                  name=area.name,
                  children=[]
              )

              # Get storage locations
              locations = await self.location_service.get_locations_by_area(
                  area.storage_area_id,
                  include_bins=True
              )

              for location in locations:
                  location_node = LocationTreeNode(
                      level="location",
                      id=location.storage_location_id,
                      code=location.code,
                      name=location.name,
                      children=[]
                  )

                  # Get bins
                  bins = await self.bin_service.get_bins_by_location(
                      location.storage_location_id
                  )

                  for bin_obj in bins:
                      bin_node = LocationTreeNode(
                          level="bin",
                          id=bin_obj.storage_bin_id,
                          code=bin_obj.code,
                          name=bin_obj.name,
                          children=[]
                      )
                      location_node.children.append(bin_node)

                  area_node.children.append(location_node)

              warehouse_node.children.append(area_node)

          tree.append(warehouse_node)

      return tree
  ```

- [ ] **AC4**: Validation helper (check hierarchy integrity):
  ```python
  async def validate_hierarchy(
      self,
      warehouse_id: Optional[int] = None,
      area_id: Optional[int] = None,
      location_id: Optional[int] = None,
      bin_id: Optional[int] = None
  ) -> HierarchyValidationResponse:
      """
      Validate that hierarchy IDs are consistent
      Example: Ensure location belongs to area, area belongs to warehouse
      """
      errors = []

      if bin_id and location_id:
          bin_obj = await self.bin_service.get_storage_bin_by_id(bin_id)
          if bin_obj.storage_location_id != location_id:
              errors.append(f"Bin {bin_id} does not belong to location {location_id}")

      if location_id and area_id:
          location = await self.location_service.get_storage_location_by_id(location_id)
          if location.storage_area_id != area_id:
              errors.append(f"Location {location_id} does not belong to area {area_id}")

      if area_id and warehouse_id:
          area = await self.area_service.get_storage_area_by_id(area_id)
          if area.warehouse_id != warehouse_id:
              errors.append(f"Area {area_id} does not belong to warehouse {warehouse_id}")

      return HierarchyValidationResponse(
          valid=len(errors) == 0,
          errors=errors
      )
  ```

- [ ] **AC5**: Batch operations (create full location hierarchy at once):
  ```python
  async def create_full_location_hierarchy(
      self,
      request: CreateHierarchyRequest
  ) -> LocationHierarchyResponse:
      """
      Create warehouse → area → location → bins in one transaction
      Useful for initial setup
      """
      # 1. Create warehouse
      warehouse = await self.warehouse_service.create_warehouse(request.warehouse)

      # 2. Create storage area
      area_request = request.storage_area
      area_request.warehouse_id = warehouse.warehouse_id
      area = await self.area_service.create_storage_area(area_request)

      # 3. Create storage location
      location_request = request.storage_location
      location_request.storage_area_id = area.storage_area_id
      location = await self.location_service.create_storage_location(location_request)

      # 4. Bulk create bins (if specified)
      bins = []
      if request.bins_quantity:
          bins = await self.bin_service.bulk_create_bins(
              storage_location_id=location.storage_location_id,
              bin_type_id=request.bin_type_id,
              quantity=request.bins_quantity,
              code_prefix=request.bin_code_prefix or "BIN"
          )

      return LocationHierarchyResponse(
          warehouse=warehouse,
          storage_area=area,
          storage_location=location,
          storage_bins=bins
      )
  ```

- [ ] **AC6**: Schema for aggregated responses:
  ```python
  # In app/schemas/location_hierarchy_schema.py
  class LocationHierarchyResponse(BaseModel):
      """Full 4-level hierarchy"""
      warehouse: WarehouseResponse
      storage_area: StorageAreaResponse
      storage_location: StorageLocationResponse
      storage_bins: List[StorageBinResponse]

  class LocationTreeNode(BaseModel):
      """Recursive tree structure for UI"""
      level: str  # "warehouse", "area", "location", "bin"
      id: int
      code: str
      name: str
      children: List["LocationTreeNode"]

  class LocationBreadcrumbResponse(BaseModel):
      """Breadcrumb navigation path"""
      path: List[dict]  # [{"level": "warehouse", "id": 1, "name": "WH001"}, ...]

  class HierarchyValidationResponse(BaseModel):
      """Validation result"""
      valid: bool
      errors: List[str]
  ```

- [ ] **AC7**: Unit tests achieve ≥85% coverage

## Technical Implementation Notes

### Architecture
- **Layer**: Application (Service)
- **Dependencies**: S001, S002, S003, S004 (ALL location services)
- **Design Pattern**: **Aggregation / Facade pattern** - unified interface to complex subsystem
- **Critical for**: ML pipeline photo localization, location management UI

### Code Hints

**Caching opportunity:**
```python
from functools import lru_cache

@lru_cache(maxsize=100)
async def _cached_hierarchy_tree(warehouse_id: Optional[int]):
    """Cache tree structure (invalidate on location updates)"""
    return await self.get_hierarchy_tree(warehouse_id)
```

**N+1 query optimization:**
```python
# In tree generation, use eager loading
warehouses = await self.warehouse_service.get_active_warehouses(include_areas=True)
# This loads warehouses + areas in 2 queries (not N+1)
```

### Testing Requirements

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_full_hierarchy_gps_lookup():
    """Test GPS → full 4-level hierarchy"""
    warehouse_svc = AsyncMock()
    area_svc = AsyncMock()
    location_svc = AsyncMock()
    bin_svc = AsyncMock()

    # Mock location with nested data
    location_svc.get_location_by_gps.return_value = Mock(
        storage_location_id=1,
        warehouse=Mock(warehouse_id=1),
        storage_area=Mock(storage_area_id=1)
    )
    bin_svc.get_bins_by_location.return_value = [Mock(storage_bin_id=1)]

    service = LocationHierarchyService(warehouse_svc, area_svc, location_svc, bin_svc)
    result = await service.get_full_hierarchy_by_gps(-70.648, -33.449)

    assert result is not None
    assert result.storage_location.storage_location_id == 1
    assert len(result.storage_bins) == 1

@pytest.mark.asyncio
async def test_breadcrumb_generation():
    """Test breadcrumb path for bin"""
    # Mock services to return hierarchy
    service = LocationHierarchyService(...)
    breadcrumb = await service.get_breadcrumb_path("bin", bin_id=1)

    assert len(breadcrumb.path) == 4  # warehouse, area, location, bin
    assert breadcrumb.path[0]["level"] == "warehouse"
    assert breadcrumb.path[3]["level"] == "bin"

@pytest.mark.asyncio
async def test_hierarchy_validation():
    """Test hierarchy consistency validation"""
    service = LocationHierarchyService(...)

    # Valid hierarchy
    result = await service.validate_hierarchy(
        warehouse_id=1, area_id=1, location_id=1, bin_id=1
    )
    assert result.valid is True

    # Invalid (bin doesn't belong to location)
    result = await service.validate_hierarchy(
        location_id=1, bin_id=999  # Wrong bin
    )
    assert result.valid is False
    assert len(result.errors) > 0
```

**Coverage Target**: ≥85%

### Performance Expectations
- `get_full_hierarchy_by_gps`: <200ms (sequential service calls)
- `get_hierarchy_tree` (1 warehouse): <500ms for 10 areas × 20 locations × 50 bins
- `validate_hierarchy`: <100ms (3-4 sequential lookups)
- Cached tree: <10ms (LRU cache hit)

## Handover Briefing

**For the next developer:**

**Context**: LocationHierarchyService is an **aggregation service** (Facade pattern). It wraps S001-S004 to provide unified location operations. CRITICAL for ML pipeline and UI.

**Key decisions made**:
1. **GPS lookup aggregation**: Single call returns all 4 levels (warehouse → area → location → bins)
2. **Tree generation**: Recursive structure for location picker UI
3. **Breadcrumb paths**: Navigation helper for UI
4. **Hierarchy validation**: Ensures referential integrity across levels
5. **Bulk operations**: Create full hierarchy in one transaction

**Known limitations**:
- Tree generation can be slow for large hierarchies (consider pagination)
- No caching by default (implement Redis for production)
- GPS lookup is sequential (can't parallelize hierarchy traversal)

**Next steps**:
- C006: LocationHierarchyController (uses this service)
- S013: PhotoUploadService (calls `get_full_hierarchy_by_gps()`)
- ML Pipeline: Uses GPS lookup for photo localization

**Questions to validate**:
- Should tree generation be paginated (lazy loading)?
- Cache invalidation strategy for hierarchy changes?
- Should breadcrumb include GPS coordinates?

## Definition of Done Checklist

- [ ] Service code written
- [ ] All aggregation methods implemented
- [ ] GPS lookup tested with full hierarchy
- [ ] Tree generation working
- [ ] Unit tests pass (≥85% coverage)
- [ ] Integration tests with all 4 services
- [ ] Performance benchmarks documented
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 5 story points (~10 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
