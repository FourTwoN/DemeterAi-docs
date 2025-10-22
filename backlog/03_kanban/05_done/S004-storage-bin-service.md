# S004: StorageBinService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (3 story points)
- **Area**: `services/location`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [S006, C004]
    - Blocked by: [R004, S003, S005]

## Related Documentation

- **Engineering Plan
  **: [../../engineering_plan/backend/service_layer.md](../../engineering_plan/backend/service_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd)

## Description

**What**: Implement `StorageBinService` for storage bin business logic (level 4 of hierarchy -
finest granularity).

**Why**: Storage bins are the **lowest level** of the 4-tier hierarchy (warehouse → area →
location → **bin**). Bins represent individual trays, pots, or containers within a location. Service
validates bin types and manages bin-level stock tracking.

**Context**: Clean Architecture Application Layer. StorageBinService calls StorageLocationService
for parent validation and StorageBinTypeService for bin type metadata.

## Acceptance Criteria

- [ ] **AC1**: Create bin with parent location and bin type validation:
  ```python
  from app.services.storage_location_service import StorageLocationService
  from app.services.storage_bin_type_service import StorageBinTypeService
  from app.repositories.storage_bin_repository import StorageBinRepository

  class StorageBinService:
      """Business logic for storage bins (level 4 - finest granularity)"""

      def __init__(
          self,
          bin_repo: StorageBinRepository,
          location_service: StorageLocationService,
          bin_type_service: StorageBinTypeService
      ):
          self.bin_repo = bin_repo
          self.location_service = location_service
          self.bin_type_service = bin_type_service

      async def create_storage_bin(
          self,
          request: StorageBinCreateRequest
      ) -> StorageBinResponse:
          """Create storage bin with parent and type validation"""
          # 1. Validate parent storage location exists
          location = await self.location_service.get_storage_location_by_id(
              request.storage_location_id
          )
          if not location:
              raise StorageLocationNotFoundException(request.storage_location_id)

          # 2. Validate bin type exists
          bin_type = await self.bin_type_service.get_bin_type_by_id(
              request.storage_bin_type_id
          )
          if not bin_type:
              raise StorageBinTypeNotFoundException(request.storage_bin_type_id)

          # 3. Check code uniqueness within location
          existing = await self.bin_repo.get_by_code_in_location(
              request.code, request.storage_location_id
          )
          if existing:
              raise DuplicateCodeException(
                  f"Bin code '{request.code}' already exists in location {location.code}"
              )

          # 4. Create bin
          bin_data = request.model_dump()
          bin_obj = await self.bin_repo.create(bin_data)

          return StorageBinResponse.from_model(bin_obj)
  ```

- [ ] **AC2**: Get bins by location with bin type metadata:
  ```python
  async def get_bins_by_location(
      self,
      storage_location_id: int,
      active_only: bool = True,
      include_bin_type: bool = True
  ) -> List[StorageBinResponse]:
      """Get all bins for a location"""
      bins = await self.bin_repo.get_by_storage_location(
          storage_location_id,
          active_only=active_only,
          with_bin_type=include_bin_type
      )

      return [
          StorageBinResponse.from_model(bin_obj, include_bin_type=include_bin_type)
          for bin_obj in bins
      ]
  ```

- [ ] **AC3**: Bin capacity calculation based on bin type:
  ```python
  async def calculate_bin_capacity(
      self,
      bin_id: int
  ) -> BinCapacityResponse:
      """
      Calculate bin capacity based on bin type dimensions
      Formula: capacity = bin_type.volume_cm3 / product.volume_cm3
      """
      bin_obj = await self.bin_repo.get(bin_id)
      if not bin_obj:
          raise StorageBinNotFoundException(bin_id)

      bin_type = bin_obj.storage_bin_type
      if not bin_type:
          return BinCapacityResponse(bin_id=bin_id, capacity=None)

      # Calculate theoretical capacity from bin type dimensions
      bin_volume_cm3 = (
          bin_type.width_cm * bin_type.length_cm * bin_type.height_cm
          if all([bin_type.width_cm, bin_type.length_cm, bin_type.height_cm])
          else None
      )

      return BinCapacityResponse(
          bin_id=bin_id,
          bin_type_code=bin_type.code,
          volume_cm3=bin_volume_cm3,
          capacity=None  # Requires product integration (future)
      )
  ```

- [ ] **AC4**: Bulk create bins (for location initialization):
  ```python
  async def bulk_create_bins(
      self,
      storage_location_id: int,
      bin_type_id: int,
      quantity: int,
      code_prefix: str = "BIN"
  ) -> List[StorageBinResponse]:
      """
      Create multiple bins at once (e.g., 100 trays in a greenhouse bed)
      Generates sequential codes: BIN-001, BIN-002, ...
      """
      # 1. Validate parent location
      location = await self.location_service.get_storage_location_by_id(
          storage_location_id
      )
      if not location:
          raise StorageLocationNotFoundException(storage_location_id)

      # 2. Validate bin type
      bin_type = await self.bin_type_service.get_bin_type_by_id(bin_type_id)
      if not bin_type:
          raise StorageBinTypeNotFoundException(bin_type_id)

      # 3. Generate bin codes
      bins = []
      for i in range(1, quantity + 1):
          code = f"{code_prefix}-{i:03d}"  # BIN-001, BIN-002, ...
          bin_data = {
              "storage_location_id": storage_location_id,
              "storage_bin_type_id": bin_type_id,
              "code": code,
              "name": f"Bin {code}",
              "active": True
          }
          bin_obj = await self.bin_repo.create(bin_data)
          bins.append(bin_obj)

      return [StorageBinResponse.from_model(b) for b in bins]
  ```

- [ ] **AC5**: Update bin position (row/column/shelf):
  ```python
  async def update_bin_position(
      self,
      bin_id: int,
      row_number: Optional[int],
      column_number: Optional[int],
      shelf_level: Optional[int]
  ) -> StorageBinResponse:
      """Update physical position of bin within location"""
      bin_obj = await self.bin_repo.get(bin_id)
      if not bin_obj:
          raise StorageBinNotFoundException(bin_id)

      updated = await self.bin_repo.update(bin_id, {
          "row_number": row_number,
          "column_number": column_number,
          "shelf_level": shelf_level
      })

      return StorageBinResponse.from_model(updated)
  ```

- [ ] **AC6**: Schema with nested bin type:
  ```python
  # In app/schemas/storage_bin_schema.py
  class StorageBinResponse(BaseModel):
      storage_bin_id: int
      storage_location_id: int
      storage_bin_type_id: int
      code: str
      name: str
      row_number: Optional[int]
      column_number: Optional[int]
      shelf_level: Optional[int]
      active: bool

      # Nested bin type metadata
      bin_type: Optional["StorageBinTypeResponse"] = None

      @classmethod
      def from_model(
          cls,
          bin_obj: StorageBin,
          include_bin_type: bool = False
      ) -> "StorageBinResponse":
          """Transform model → schema"""
          response = cls(
              storage_bin_id=bin_obj.storage_bin_id,
              storage_location_id=bin_obj.storage_location_id,
              storage_bin_type_id=bin_obj.storage_bin_type_id,
              code=bin_obj.code,
              name=bin_obj.name,
              row_number=bin_obj.row_number,
              column_number=bin_obj.column_number,
              shelf_level=bin_obj.shelf_level,
              active=bin_obj.active
          )

          if include_bin_type and bin_obj.storage_bin_type:
              from app.schemas.storage_bin_type_schema import StorageBinTypeResponse
              response.bin_type = StorageBinTypeResponse.from_model(bin_obj.storage_bin_type)

          return response
  ```

- [ ] **AC7**: Unit tests achieve ≥85% coverage

## Technical Implementation Notes

### Architecture

- **Layer**: Application (Service)
- **Dependencies**: R004 (StorageBinRepository), S003 (StorageLocationService), S005 (
  StorageBinTypeService)
- **Design Pattern**: Service-to-service communication for cross-domain validation

### Code Hints

**Bulk insert optimization:**

```python
# In repository layer - use bulk_insert_mappings
async def bulk_create(self, bins: List[dict]) -> List[StorageBin]:
    """Optimized bulk insert for storage bins"""
    self.session.bulk_insert_mappings(StorageBin, bins)
    await self.session.flush()

    # Retrieve created bins
    codes = [b["code"] for b in bins]
    stmt = select(StorageBin).where(StorageBin.code.in_(codes))
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

### Testing Requirements

**Unit Tests**:

```python
@pytest.mark.asyncio
async def test_create_bin_with_parent_validation():
    """Test parent location validation via service"""
    bin_repo = AsyncMock()
    location_service = AsyncMock()
    bin_type_service = AsyncMock()

    location_service.get_storage_location_by_id.return_value = Mock(storage_location_id=1)
    bin_type_service.get_bin_type_by_id.return_value = Mock(storage_bin_type_id=1)

    service = StorageBinService(bin_repo, location_service, bin_type_service)
    request = StorageBinCreateRequest(
        storage_location_id=1,
        storage_bin_type_id=1,
        code="BIN-001"
    )

    result = await service.create_storage_bin(request)

    location_service.get_storage_location_by_id.assert_called_once_with(1)
    bin_type_service.get_bin_type_by_id.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_bulk_create_bins():
    """Test bulk bin creation with sequential codes"""
    bin_repo = AsyncMock()
    bin_repo.create.side_effect = lambda data: Mock(**data, storage_bin_id=1)

    service = StorageBinService(bin_repo, AsyncMock(), AsyncMock())
    # Mock validations
    service.location_service.get_storage_location_by_id = AsyncMock(return_value=Mock())
    service.bin_type_service.get_bin_type_by_id = AsyncMock(return_value=Mock())

    bins = await service.bulk_create_bins(
        storage_location_id=1,
        bin_type_id=1,
        quantity=5,
        code_prefix="TEST"
    )

    assert len(bins) == 5
    assert bins[0].code == "TEST-001"
    assert bins[4].code == "TEST-005"
```

**Coverage Target**: ≥85%

### Performance Expectations

- `create_storage_bin`: <30ms
- `bulk_create_bins` (100 bins): <500ms (use bulk_insert_mappings)
- `get_bins_by_location`: <50ms for 100 bins

## Handover Briefing

**For the next developer:**

**Context**: StorageBinService manages the **finest granularity** in the location hierarchy. Bins
represent individual trays/pots/containers.

**Key decisions made**:

1. **Bulk creation support**: Common to create 50-100 bins per location at once
2. **Sequential code generation**: AUTO-001, AUTO-002... for bulk operations
3. **Position tracking**: Row/column/shelf for physical bin arrangement
4. **Bin type integration**: Links to StorageBinTypeService for capacity calculations

**Next steps**:

- S005: StorageBinTypeService (bin metadata like tray dimensions)
- S006: LocationHierarchyService (aggregates all 4 levels)

## Definition of Done Checklist

- [ ] Service code written
- [ ] Parent validation via services (NOT repositories)
- [ ] Bulk create optimization implemented
- [ ] Unit tests pass (≥85% coverage)
- [ ] PR reviewed (2+ approvals)

## Time Tracking

- **Estimated**: 3 story points (~6 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
