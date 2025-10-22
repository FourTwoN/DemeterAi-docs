# S001: WarehouseService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `services/location`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [S002, S003, S006, C001]
    - Blocked by: [R001]

## Related Documentation

- **Engineering Plan
  **: [../../engineering_plan/backend/service_layer.md](../../engineering_plan/backend/service_layer.md)
- **Architecture
  **: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd)

## Description

**What**: Implement `WarehouseService` for warehouse business logic, GPS-based warehouse lookup, and
schema transformations.

**Why**: Services layer orchestrates business logic and coordinates repository operations.
WarehouseService provides GPS → warehouse mapping (critical for photo localization), warehouse CRUD
with validation, and Pydantic schema ↔ SQLAlchemy model transformations.

**Context**: Clean Architecture Application Layer. Services call repositories for data access and
other services for inter-domain operations. NO direct repository calls to other domains.
WarehouseService is the entry point for all warehouse-related operations and GPS-based location
discovery.

## Acceptance Criteria

- [ ] **AC1**: `WarehouseService` class created in `app/services/warehouse_service.py`:
  ```python
  from typing import Optional, List
  from app.repositories.warehouse_repository import WarehouseRepository
  from app.schemas.warehouse_schema import (
      WarehouseCreateRequest,
      WarehouseUpdateRequest,
      WarehouseResponse,
      WarehouseWithAreasResponse
  )
  from app.models.warehouse import Warehouse
  from app.exceptions import WarehouseNotFoundException, DuplicateCodeException

  class WarehouseService:
      """Business logic for warehouse operations"""

      def __init__(self, warehouse_repo: WarehouseRepository):
          self.warehouse_repo = warehouse_repo

      async def create_warehouse(
          self,
          request: WarehouseCreateRequest
      ) -> WarehouseResponse:
          """Create new warehouse with business validation"""
          # 1. Check code uniqueness
          existing = await self.warehouse_repo.get_by_code(request.code)
          if existing:
              raise DuplicateCodeException(f"Warehouse code '{request.code}' already exists")

          # 2. Validate geometry (polygon must be closed, ≥3 points)
          self._validate_geometry(request.geojson_coordinates)

          # 3. Create warehouse
          warehouse = await self.warehouse_repo.create(request.model_dump())

          return WarehouseResponse.from_model(warehouse)

      async def get_warehouse_by_gps(
          self,
          longitude: float,
          latitude: float
      ) -> Optional[WarehouseResponse]:
          """Find warehouse containing GPS point (photo localization)"""
          warehouse = await self.warehouse_repo.get_by_gps_point(longitude, latitude)
          if not warehouse:
              return None
          return WarehouseResponse.from_model(warehouse)

      async def get_active_warehouses(
          self,
          include_areas: bool = False
      ) -> List[WarehouseResponse]:
          """Get all active warehouses, optionally with storage areas"""
          warehouses = await self.warehouse_repo.get_active_warehouses(
              with_areas=include_areas
          )
          if include_areas:
              return [WarehouseWithAreasResponse.from_model(wh) for wh in warehouses]
          return [WarehouseResponse.from_model(wh) for wh in warehouses]
  ```

- [ ] **AC2**: Geometry validation method:
  ```python
  def _validate_geometry(self, geojson: dict) -> None:
      """Validate polygon geometry"""
      from shapely.geometry import shape
      from shapely.validation import explain_validity

      polygon = shape(geojson)

      # Must be polygon
      if polygon.geom_type != 'Polygon':
          raise ValueError(f"Expected Polygon, got {polygon.geom_type}")

      # Must be valid
      if not polygon.is_valid:
          raise ValueError(f"Invalid geometry: {explain_validity(polygon)}")

      # Must have ≥3 points (4 with closing point)
      if len(polygon.exterior.coords) < 4:
          raise ValueError("Polygon must have at least 3 vertices")

      # Must be closed
      if polygon.exterior.coords[0] != polygon.exterior.coords[-1]:
          raise ValueError("Polygon must be closed (first point = last point)")
  ```

- [ ] **AC3**: Update warehouse with geometry change detection:
  ```python
  async def update_warehouse(
      self,
      warehouse_id: int,
      request: WarehouseUpdateRequest
  ) -> WarehouseResponse:
      """Update warehouse with geometry validation"""
      warehouse = await self.warehouse_repo.get(warehouse_id)
      if not warehouse:
          raise WarehouseNotFoundException(warehouse_id)

      # Validate new geometry if provided
      if request.geojson_coordinates:
          self._validate_geometry(request.geojson_coordinates)

      updated = await self.warehouse_repo.update(
          warehouse_id,
          request.model_dump(exclude_unset=True)
      )

      return WarehouseResponse.from_model(updated)
  ```

- [ ] **AC4**: Delete warehouse with cascade protection:
  ```python
  async def delete_warehouse(self, warehouse_id: int) -> bool:
      """Soft delete warehouse (set active=False)"""
      warehouse = await self.warehouse_repo.get(warehouse_id)
      if not warehouse:
          raise WarehouseNotFoundException(warehouse_id)

      # Soft delete only (preserve historical data)
      await self.warehouse_repo.update(warehouse_id, {"active": False})
      return True
  ```

- [ ] **AC5**: Schema transformation helpers:
  ```python
  # In app/schemas/warehouse_schema.py
  from pydantic import BaseModel, Field, field_validator
  from typing import Optional, List
  from datetime import datetime

  class WarehouseResponse(BaseModel):
      warehouse_id: int
      code: str
      name: str
      warehouse_type: str
      geojson_coordinates: dict
      centroid: Optional[dict]
      area_m2: Optional[float]
      active: bool
      created_at: datetime
      updated_at: Optional[datetime]

      @classmethod
      def from_model(cls, warehouse: Warehouse) -> "WarehouseResponse":
          """Transform SQLAlchemy model → Pydantic schema"""
          from geoalchemy2.shape import to_shape

          # Convert PostGIS geometry to GeoJSON
          geojson = to_shape(warehouse.geojson_coordinates).__geo_interface__
          centroid = to_shape(warehouse.centroid).__geo_interface__ if warehouse.centroid else None

          return cls(
              warehouse_id=warehouse.warehouse_id,
              code=warehouse.code,
              name=warehouse.name,
              warehouse_type=warehouse.warehouse_type,
              geojson_coordinates=geojson,
              centroid=centroid,
              area_m2=warehouse.area_m2,
              active=warehouse.active,
              created_at=warehouse.created_at,
              updated_at=warehouse.updated_at
          )
  ```

- [ ] **AC6**: Custom exceptions defined:
  ```python
  # In app/exceptions/warehouse_exceptions.py
  class WarehouseNotFoundException(AppBaseException):
      def __init__(self, warehouse_id: int):
          super().__init__(
              technical_message=f"Warehouse ID {warehouse_id} not found",
              user_message="The requested warehouse does not exist",
              code=404
          )

  class DuplicateCodeException(AppBaseException):
      def __init__(self, message: str):
          super().__init__(
              technical_message=message,
              user_message="A warehouse with this code already exists",
              code=409
          )
  ```

- [ ] **AC7**: Unit tests achieve ≥85% coverage

## Technical Implementation Notes

### Architecture

- **Layer**: Application (Service)
- **Dependencies**: R001 (WarehouseRepository)
- **Design Pattern**: Service layer with dependency injection
- **Transaction Boundary**: Services manage transactions (via repository session)

### Code Hints

**Dependency injection setup:**

```python
# In app/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.repositories.warehouse_repository import WarehouseRepository
from app.services.warehouse_service import WarehouseService

async def get_warehouse_service(
    session: AsyncSession = Depends(get_db_session)
) -> WarehouseService:
    """Dependency injection for WarehouseService"""
    repo = WarehouseRepository(session)
    return WarehouseService(repo)
```

**Controller usage example:**

```python
# In app/controllers/warehouse_controller.py
from fastapi import APIRouter, Depends, status
from app.services.warehouse_service import WarehouseService
from app.dependencies import get_warehouse_service

router = APIRouter(prefix="/warehouses", tags=["warehouses"])

@router.get("/gps")
async def find_warehouse_by_gps(
    longitude: float,
    latitude: float,
    service: WarehouseService = Depends(get_warehouse_service)
):
    """Find warehouse containing GPS coordinates"""
    warehouse = await service.get_warehouse_by_gps(longitude, latitude)
    if not warehouse:
        raise HTTPException(404, "No warehouse found at these coordinates")
    return warehouse
```

### Testing Requirements

**Unit Tests** (`tests/services/test_warehouse_service.py`):

```python
import pytest
from unittest.mock import AsyncMock, Mock
from app.services.warehouse_service import WarehouseService
from app.schemas.warehouse_schema import WarehouseCreateRequest
from app.exceptions import DuplicateCodeException

@pytest.mark.asyncio
async def test_create_warehouse_success():
    """Test successful warehouse creation"""
    repo = AsyncMock()
    repo.get_by_code.return_value = None  # No duplicate
    repo.create.return_value = Mock(
        warehouse_id=1,
        code="WH001",
        name="Main Greenhouse",
        active=True
    )

    service = WarehouseService(repo)
    request = WarehouseCreateRequest(
        code="WH001",
        name="Main Greenhouse",
        warehouse_type="greenhouse",
        geojson_coordinates={
            "type": "Polygon",
            "coordinates": [[
                [-70.648, -33.449], [-70.647, -33.449],
                [-70.647, -33.450], [-70.648, -33.450],
                [-70.648, -33.449]
            ]]
        }
    )

    result = await service.create_warehouse(request)
    assert result.code == "WH001"
    repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_create_warehouse_duplicate_code():
    """Test duplicate code rejection"""
    repo = AsyncMock()
    repo.get_by_code.return_value = Mock(code="WH001")  # Duplicate exists

    service = WarehouseService(repo)
    request = WarehouseCreateRequest(code="WH001", ...)

    with pytest.raises(DuplicateCodeException):
        await service.create_warehouse(request)

@pytest.mark.asyncio
async def test_get_warehouse_by_gps():
    """Test GPS-based warehouse lookup"""
    repo = AsyncMock()
    repo.get_by_gps_point.return_value = Mock(warehouse_id=1, code="WH001")

    service = WarehouseService(repo)
    result = await service.get_warehouse_by_gps(-70.648, -33.449)

    assert result is not None
    assert result.warehouse_id == 1
    repo.get_by_gps_point.assert_called_once_with(-70.648, -33.449)

@pytest.mark.asyncio
async def test_validate_geometry_invalid_polygon():
    """Test geometry validation rejects invalid polygons"""
    service = WarehouseService(AsyncMock())

    # Non-closed polygon
    invalid_geojson = {
        "type": "Polygon",
        "coordinates": [[
            [-70.648, -33.449], [-70.647, -33.449],
            [-70.647, -33.450]  # Missing closing point
        ]]
    }

    with pytest.raises(ValueError, match="must be closed"):
        service._validate_geometry(invalid_geojson)
```

**Integration Tests** (`tests/integration/test_warehouse_service_integration.py`):

```python
@pytest.mark.asyncio
async def test_warehouse_service_full_lifecycle(db_session):
    """Test create → read → update → delete cycle"""
    repo = WarehouseRepository(db_session)
    service = WarehouseService(repo)

    # Create
    create_request = WarehouseCreateRequest(
        code="INT01",
        name="Integration Test Warehouse",
        warehouse_type="greenhouse",
        geojson_coordinates={...}
    )
    created = await service.create_warehouse(create_request)
    assert created.warehouse_id is not None

    # Read by GPS
    warehouse = await service.get_warehouse_by_gps(-70.648, -33.449)
    assert warehouse.code == "INT01"

    # Update
    update_request = WarehouseUpdateRequest(name="Updated Name")
    updated = await service.update_warehouse(created.warehouse_id, update_request)
    assert updated.name == "Updated Name"

    # Delete (soft)
    deleted = await service.delete_warehouse(created.warehouse_id)
    assert deleted is True

    # Verify soft delete
    active_warehouses = await service.get_active_warehouses()
    assert not any(wh.warehouse_id == created.warehouse_id for wh in active_warehouses)
```

**Coverage Target**: ≥85%

### Performance Expectations

- `create_warehouse`: <30ms (includes geometry validation)
- `get_warehouse_by_gps`: <50ms (PostGIS query)
- `get_active_warehouses`: <20ms for 50 warehouses
- Schema transformation (model → Pydantic): <5ms per warehouse

## Handover Briefing

**For the next developer:**

**Context**: WarehouseService is the **first service in the location hierarchy**. Sets the pattern
for all other location services (StorageAreaService, StorageLocationService, etc.).

**Key decisions made**:

1. **GPS lookup method**: Critical for photo localization - returns first match (warehouses should
   not overlap)
2. **Soft delete only**: Preserve historical data, set `active=False` instead of hard delete
3. **Geometry validation**: Shapely validates polygons before database insert (fail fast)
4. **Schema transformations**: PostGIS geometry → GeoJSON in response schemas
5. **Service-only repository access**: Controllers NEVER call repositories directly

**Known limitations**:

- GPS lookup assumes non-overlapping warehouse polygons (undefined behavior if overlap)
- Geometry validation uses Shapely (sync operation, ~10-20ms overhead)
- Soft delete doesn't cascade to child entities (manual cleanup required)

**Next steps after this card**:

- S002: StorageAreaService (similar pattern, calls WarehouseService for parent validation)
- S003: StorageLocationService (GPS lookup delegates to WarehouseService)
- C001: WarehouseController (HTTP layer, uses WarehouseService)

**Questions to validate**:

- Does GPS lookup handle edge cases (point exactly on boundary)?
- Are PostGIS → GeoJSON transformations consistent across all schemas?
- Should we add warehouse capacity calculations (total area vs used area)?

## Definition of Done Checklist

- [ ] Service code written in `app/services/warehouse_service.py`
- [ ] Schema definitions in `app/schemas/warehouse_schema.py`
- [ ] Custom exceptions in `app/exceptions/warehouse_exceptions.py`
- [ ] Dependency injection configured in `app/dependencies.py`
- [ ] Unit tests pass (≥85% coverage)
- [ ] Integration tests with real database pass
- [ ] Type hints validated (mypy)
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)
- [ ] Documentation strings (docstrings) complete

## Time Tracking

- **Estimated**: 3 story points (~6 hours)
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
