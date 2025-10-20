# S005: StorageBinTypeService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: S (1 story point)
- **Area**: `services/location`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [S004, C005]
  - Blocked by: [R005]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/service_layer.md](../../engineering_plan/backend/service_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd)

## Description

**What**: Implement `StorageBinTypeService` for bin type catalog management (tray types, pot types, container dimensions).

**Why**: Storage bin types define standardized container dimensions (width, length, height) used for capacity calculations. This is a simple CRUD service with no complex business logic.

**Context**: Clean Architecture Application Layer. Simple catalog service - no inter-service dependencies. Used by StorageBinService to validate bin types.

## Acceptance Criteria

- [ ] **AC1**: Basic CRUD operations:
  ```python
  from app.repositories.storage_bin_type_repository import StorageBinTypeRepository
  from app.schemas.storage_bin_type_schema import (
      StorageBinTypeCreateRequest,
      StorageBinTypeResponse
  )

  class StorageBinTypeService:
      """Business logic for storage bin type catalog"""

      def __init__(self, bin_type_repo: StorageBinTypeRepository):
          self.bin_type_repo = bin_type_repo

      async def create_bin_type(
          self,
          request: StorageBinTypeCreateRequest
      ) -> StorageBinTypeResponse:
          """Create new bin type"""
          # Check code uniqueness
          existing = await self.bin_type_repo.get_by_code(request.code)
          if existing:
              raise DuplicateCodeException(f"Bin type '{request.code}' already exists")

          bin_type = await self.bin_type_repo.create(request.model_dump())
          return StorageBinTypeResponse.from_model(bin_type)

      async def get_bin_type_by_id(self, bin_type_id: int) -> Optional[StorageBinTypeResponse]:
          """Get bin type by ID"""
          bin_type = await self.bin_type_repo.get(bin_type_id)
          return StorageBinTypeResponse.from_model(bin_type) if bin_type else None

      async def get_all_bin_types(self, active_only: bool = True) -> List[StorageBinTypeResponse]:
          """Get all bin types"""
          bin_types = await self.bin_type_repo.get_all(active_only=active_only)
          return [StorageBinTypeResponse.from_model(bt) for bt in bin_types]
  ```

- [ ] **AC2**: Volume calculation helper:
  ```python
  def calculate_volume(
      self,
      width_cm: float,
      length_cm: float,
      height_cm: float
  ) -> float:
      """Calculate bin volume in cm³"""
      return width_cm * length_cm * height_cm
  ```

- [ ] **AC3**: Schema transformation:
  ```python
  # In app/schemas/storage_bin_type_schema.py
  class StorageBinTypeResponse(BaseModel):
      storage_bin_type_id: int
      code: str
      name: str
      width_cm: Optional[float]
      length_cm: Optional[float]
      height_cm: Optional[float]
      volume_cm3: Optional[float]  # Calculated field
      active: bool

      @classmethod
      def from_model(cls, bin_type: StorageBinType) -> "StorageBinTypeResponse":
          """Transform model → schema with calculated volume"""
          volume = None
          if all([bin_type.width_cm, bin_type.length_cm, bin_type.height_cm]):
              volume = bin_type.width_cm * bin_type.length_cm * bin_type.height_cm

          return cls(
              storage_bin_type_id=bin_type.storage_bin_type_id,
              code=bin_type.code,
              name=bin_type.name,
              width_cm=bin_type.width_cm,
              length_cm=bin_type.length_cm,
              height_cm=bin_type.height_cm,
              volume_cm3=volume,
              active=bin_type.active
          )
  ```

- [ ] **AC4**: Unit tests achieve ≥80% coverage

## Technical Implementation Notes

### Architecture
- **Layer**: Application (Service)
- **Dependencies**: R005 (StorageBinTypeRepository)
- **Design Pattern**: Simple CRUD service (catalog management)

### Testing Requirements

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_create_bin_type():
    """Test bin type creation"""
    repo = AsyncMock()
    repo.get_by_code.return_value = None
    repo.create.return_value = Mock(
        storage_bin_type_id=1,
        code="TRAY-50x30",
        width_cm=50.0,
        length_cm=30.0,
        height_cm=10.0
    )

    service = StorageBinTypeService(repo)
    request = StorageBinTypeCreateRequest(
        code="TRAY-50x30",
        name="Standard Tray 50x30cm",
        width_cm=50.0,
        length_cm=30.0,
        height_cm=10.0
    )

    result = await service.create_bin_type(request)
    assert result.code == "TRAY-50x30"
    assert result.volume_cm3 == 15000.0  # 50 * 30 * 10

@pytest.mark.asyncio
async def test_volume_calculation():
    """Test volume calculation helper"""
    service = StorageBinTypeService(AsyncMock())
    volume = service.calculate_volume(50.0, 30.0, 10.0)
    assert volume == 15000.0
```

**Coverage Target**: ≥80%

### Performance Expectations
- `create_bin_type`: <20ms
- `get_all_bin_types`: <30ms for 20 types

## Handover Briefing

**Context**: Simple catalog service. No complex business logic.

**Key decisions**:
- Volume auto-calculated in schema transformation
- Used by StorageBinService for bin metadata

**Next steps**: S004 (StorageBinService) uses this service

## Definition of Done Checklist

- [ ] Service code written
- [ ] Volume calculation working
- [ ] Unit tests pass (≥80% coverage)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 1 story point (~2 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
