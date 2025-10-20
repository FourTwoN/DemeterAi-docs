# Team Leader Mini-Plan: S001 - WarehouseService
**Created**: 2025-10-20 (Sprint 03 - Services Layer)
**Status**: In Planning
**Team Leader**: Claude Code

---

## Task Overview
- **Card**: S001 - WarehouseService
- **Epic**: epic-004 (Service Layer - Location Hierarchy)
- **Priority**: HIGH (critical path - blocks S002, S003, S006, C001)
- **Complexity**: 3 story points (Medium - ~6 hours)
- **Current Status**: backlog → ready (pending move)

## Architecture

### Layer: Application (Service)
**Pattern**: Clean Architecture - Service Layer
**Design**: Repository Pattern + Dependency Injection

### Dependencies
**Direct dependencies**:
- R001 (WarehouseRepository) - EXISTS ✅ (extends AsyncRepository)
- PostgreSQL + PostGIS for geometry operations
- Shapely for geometry validation

**Service dependencies**: NONE (this is the root service)

**Critical Rules**:
- Service → Service communication ONLY (NEVER Service → OtherRepository)
- For S001: No other services exist yet, so no cross-service calls needed
- Future services (S002-S006) will call WarehouseService methods

### Database Access
**Tables involved**:
- `warehouses` (primary - PostGIS geometry)

**Schema verification** (database/database.mmd):
```
warehouses {
  warehouse_id SERIAL PK
  code VARCHAR(50) UNIQUE NOT NULL
  name VARCHAR(200) NOT NULL
  warehouse_type warehouse_type_enum NOT NULL
  geojson_coordinates GEOMETRY(POLYGON, 4326) NOT NULL
  centroid GEOMETRY(POINT, 4326)
  area_m2 NUMERIC(10,2) GENERATED
  active BOOLEAN DEFAULT true
  created_at TIMESTAMP DEFAULT NOW()
  updated_at TIMESTAMP
}
```

**Model verification**: /home/lucasg/proyectos/DemeterDocs/app/models/warehouse.py ✅
- Matches database schema exactly
- PostGIS support via GeoAlchemy2
- Enum: WarehouseTypeEnum (greenhouse, shadehouse, open_field, tunnel)
- Validator: code must be uppercase alphanumeric 2-20 chars
- Relationships: storage_areas (one-to-many)

---

## Files to Create/Modify

### 1. Schemas (NEW)
**File**: `/home/lucasg/proyectos/DemeterDocs/app/schemas/warehouse_schema.py` (~200 lines)
**Purpose**: Pydantic schemas for request/response validation
**Classes**:
- `WarehouseCreateRequest` - create warehouse payload
- `WarehouseUpdateRequest` - update warehouse payload
- `WarehouseResponse` - standard response with geometry as GeoJSON
- `WarehouseWithAreasResponse` - response including storage_areas relationship

### 2. Exceptions (EXTEND EXISTING)
**File**: `/home/lucasg/proyectos/DemeterDocs/app/core/exceptions.py`
**Add**:
- `WarehouseNotFoundException(NotFoundException)` - 404 when warehouse_id not found
- `DuplicateCodeException(AppBaseException)` - 409 when warehouse code already exists

### 3. Repository (EXTEND EXISTING)
**File**: `/home/lucasg/proyectos/DemeterDocs/app/repositories/warehouse_repository.py`
**Current**: Only inherits from AsyncRepository (18 lines)
**Add domain-specific methods**:
- `get_by_code(code: str) -> Warehouse | None` - lookup by unique code
- `get_by_gps_point(longitude: float, latitude: float) -> Warehouse | None` - PostGIS spatial query
- `get_active_warehouses(with_areas: bool = False) -> list[Warehouse]` - active warehouses with optional eager loading

### 4. Service (NEW)
**File**: `/home/lucasg/proyectos/DemeterDocs/app/services/warehouse_service.py` (~150 lines)
**Purpose**: Business logic orchestration
**Methods**:
- `create_warehouse(request: WarehouseCreateRequest) -> WarehouseResponse`
- `get_warehouse_by_gps(longitude: float, latitude: float) -> WarehouseResponse | None`
- `get_active_warehouses(include_areas: bool = False) -> list[WarehouseResponse]`
- `update_warehouse(warehouse_id: int, request: WarehouseUpdateRequest) -> WarehouseResponse`
- `delete_warehouse(warehouse_id: int) -> bool` (soft delete)
- `_validate_geometry(geojson: dict) -> None` (private helper)

### 5. Unit Tests (NEW)
**File**: `/home/lucasg/proyectos/DemeterDocs/tests/unit/services/test_warehouse_service.py` (~250 lines)
**Coverage target**: ≥85%
**Test scenarios**:
- Create warehouse: success case
- Create warehouse: duplicate code (DuplicateCodeException)
- Create warehouse: invalid geometry (ValueError)
- GPS lookup: found
- GPS lookup: not found
- Get active warehouses: with and without areas
- Update warehouse: success
- Update warehouse: not found (WarehouseNotFoundException)
- Delete warehouse: soft delete verification

### 6. Integration Tests (NEW)
**File**: `/home/lucasg/proyectos/DemeterDocs/tests/integration/test_warehouse_service_integration.py` (~200 lines)
**Purpose**: Real database testing (NO MOCKS)
**Test scenarios**:
- Full lifecycle: create → read by GPS → update → soft delete
- PostGIS spatial queries with real coordinates
- Geometry validation with real database constraints
- Transaction management (commit/rollback)

---

## Implementation Strategy

### Phase 1: Foundation (Python Expert)
**Time**: 1 hour
**Deliverables**:
1. Create `warehouse_schema.py` with all Pydantic schemas
2. Add warehouse exceptions to `exceptions.py`
3. Extend `WarehouseRepository` with domain queries

**Verification**:
```bash
# Import check
python -c "from app.schemas.warehouse_schema import WarehouseCreateRequest, WarehouseResponse"
python -c "from app.core.exceptions import WarehouseNotFoundException, DuplicateCodeException"
python -c "from app.repositories.warehouse_repository import WarehouseRepository"
```

### Phase 2: Service Implementation (Python Expert)
**Time**: 2 hours
**Deliverables**:
1. Implement `WarehouseService` class
2. All business logic methods
3. Geometry validation with Shapely
4. Schema transformations (PostGIS → GeoJSON)

**Key implementation notes**:
- Use `from_shape()` and `to_shape()` from geoalchemy2.shape for geometry conversions
- Shapely validation BEFORE database insert (fail fast)
- Soft delete: update active=False (preserve historical data)
- GPS lookup: use ST_Contains PostGIS function

**Verification**:
```bash
# Import check
python -c "from app.services.warehouse_service import WarehouseService"
```

### Phase 3: Testing (Testing Expert - PARALLEL with Phase 2)
**Time**: 2-3 hours
**Deliverables**:
1. Unit tests with AsyncMock for repository
2. Integration tests with real PostgreSQL database
3. Coverage report showing ≥85%

**Testing patterns**:
- Unit tests: Mock WarehouseRepository responses
- Integration tests: Use pytest fixtures from conftest.py (db_session)
- Real database required for PostGIS operations
- NO MOCKS of business logic

**Verification**:
```bash
# Run tests
pytest tests/unit/services/test_warehouse_service.py -v
pytest tests/integration/test_warehouse_service_integration.py -v

# Check coverage
pytest tests/unit/services/test_warehouse_service.py --cov=app.services.warehouse_service --cov-report=term-missing
```

### Phase 4: Quality Gates (Team Leader)
**Time**: 30 minutes
**Checklist**:
- [ ] All tests pass (pytest exit code = 0)
- [ ] Coverage ≥85%
- [ ] Type hints on all methods
- [ ] Docstrings complete
- [ ] No Service → OtherRepository violations
- [ ] Geometry validation working
- [ ] PostGIS queries tested

---

## Acceptance Criteria Tracking

### AC1: WarehouseService class structure ✅ (from task spec)
- [ ] Class created in `app/services/warehouse_service.py`
- [ ] Constructor: `__init__(self, warehouse_repo: WarehouseRepository)`
- [ ] Method: `create_warehouse(request) -> WarehouseResponse`
- [ ] Method: `get_warehouse_by_gps(longitude, latitude) -> WarehouseResponse | None`
- [ ] Method: `get_active_warehouses(include_areas) -> list[WarehouseResponse]`

### AC2: Geometry validation ✅
- [ ] Private method: `_validate_geometry(geojson: dict) -> None`
- [ ] Validates polygon type
- [ ] Validates polygon is closed (first point = last point)
- [ ] Validates ≥3 vertices (4 with closing point)
- [ ] Uses Shapely for validation
- [ ] Raises ValueError with descriptive messages

### AC3: Update warehouse ✅
- [ ] Method: `update_warehouse(warehouse_id, request) -> WarehouseResponse`
- [ ] Checks warehouse exists (raises WarehouseNotFoundException)
- [ ] Validates new geometry if provided
- [ ] Supports partial updates (exclude_unset=True)

### AC4: Delete warehouse (soft delete) ✅
- [ ] Method: `delete_warehouse(warehouse_id) -> bool`
- [ ] Checks warehouse exists
- [ ] Sets active=False (NOT hard delete)
- [ ] Returns True on success

### AC5: Schema transformations ✅
- [ ] WarehouseResponse.from_model() class method
- [ ] Converts PostGIS geometry → GeoJSON
- [ ] Handles centroid conversion (nullable)
- [ ] All fields mapped correctly

### AC6: Custom exceptions ✅
- [ ] WarehouseNotFoundException (404) - inherits from NotFoundException
- [ ] DuplicateCodeException (409) - inherits from AppBaseException

### AC7: Unit tests ≥85% coverage ✅
- [ ] Test create_warehouse success
- [ ] Test create_warehouse duplicate code
- [ ] Test validate_geometry (valid polygon)
- [ ] Test validate_geometry (invalid: not closed)
- [ ] Test validate_geometry (invalid: < 3 vertices)
- [ ] Test get_warehouse_by_gps (found)
- [ ] Test get_warehouse_by_gps (not found)
- [ ] Test get_active_warehouses (with/without areas)
- [ ] Test update_warehouse success
- [ ] Test update_warehouse not found
- [ ] Test delete_warehouse success
- [ ] Coverage report shows ≥85%

---

## Performance Expectations

**Targets** (from task spec):
- `create_warehouse`: <30ms (includes geometry validation)
- `get_warehouse_by_gps`: <50ms (PostGIS spatial query)
- `get_active_warehouses`: <20ms for 50 warehouses
- Schema transformation: <5ms per warehouse

**Monitoring**:
- Integration tests should measure actual performance
- PostGIS GIST indexes required for spatial query performance

---

## Known Issues & Limitations

1. **GPS lookup assumes non-overlapping warehouses**
   - ST_Contains returns first match
   - Undefined behavior if warehouse polygons overlap
   - Future enhancement: detect overlaps, return all matches

2. **Geometry validation is synchronous**
   - Shapely operations are sync (10-20ms overhead)
   - Could impact performance for bulk operations
   - Consider async wrapper if needed

3. **Soft delete doesn't cascade**
   - Setting warehouse.active=False doesn't affect child entities
   - Manual cleanup required (or database CASCADE rules)

4. **No warehouse capacity calculations**
   - Current implementation doesn't calculate used vs total capacity
   - S002-S006 services will need this for stock management

---

## Next Steps After S001

**Immediately unblocked**:
- S002: StorageAreaService (calls WarehouseService for parent validation)
- S003: StorageLocationService (GPS lookup delegates to WarehouseService)
- S006: StorageBinService (indirectly depends on S001)
- C001: WarehouseController (HTTP layer uses WarehouseService)

**Pattern established for**:
- All location hierarchy services (S002-S006)
- GPS-based lookups
- PostGIS geometry handling
- Soft delete pattern
- Schema transformation pattern

---

## Team Coordination

### Python Expert Assignment
**Start immediately**: Phase 1 + Phase 2
**Files to create**:
1. `/home/lucasg/proyectos/DemeterDocs/app/schemas/warehouse_schema.py`
2. `/home/lucasg/proyectos/DemeterDocs/app/services/warehouse_service.py`

**Files to modify**:
1. `/home/lucasg/proyectos/DemeterDocs/app/core/exceptions.py` (add 2 exceptions)
2. `/home/lucasg/proyectos/DemeterDocs/app/repositories/warehouse_repository.py` (add 3 methods)

**Dependencies to install** (verify in environment):
```bash
# Check if shapely is installed
python -c "import shapely; print(shapely.__version__)"

# Check if geoalchemy2 is installed
python -c "import geoalchemy2; print(geoalchemy2.__version__)"
```

**Template reference**: `/home/lucasg/proyectos/DemeterDocs/backlog/04_templates/starter-code/base_service.py` (if exists)

### Testing Expert Assignment
**Start in parallel with Python Expert Phase 2**
**Files to create**:
1. `/home/lucasg/proyectos/DemeterDocs/tests/unit/services/test_warehouse_service.py`
2. `/home/lucasg/proyectos/DemeterDocs/tests/integration/test_warehouse_service_integration.py`

**Test database**:
- Use pytest fixtures from `/home/lucasg/proyectos/DemeterDocs/tests/conftest.py`
- Integration tests require PostgreSQL + PostGIS
- Docker compose: `docker compose up db_test -d`

**Coverage command**:
```bash
pytest tests/unit/services/test_warehouse_service.py \
  --cov=app.services.warehouse_service \
  --cov-report=term-missing \
  --cov-fail-under=85
```

---

## Quality Gate Checklist

Before moving S001 to `05_done/`:

### Gate 1: Code Review ✅
- [ ] Service → Service pattern enforced (no violations)
- [ ] All methods have type hints
- [ ] All methods have docstrings
- [ ] Async/await used correctly
- [ ] No TODO/FIXME in production code
- [ ] Geometry validation implemented correctly
- [ ] PostGIS conversions working

### Gate 2: Tests Pass ✅
```bash
pytest tests/unit/services/test_warehouse_service.py -v
pytest tests/integration/test_warehouse_service_integration.py -v
echo $?  # Must be 0
```

### Gate 3: Coverage ≥85% ✅
```bash
pytest tests/ --cov=app.services.warehouse_service --cov-report=term-missing
# TOTAL line must show ≥85%
```

### Gate 4: No Hallucinations ✅
```bash
# Verify all imports work
python -c "from app.services.warehouse_service import WarehouseService"
python -c "from app.schemas.warehouse_schema import WarehouseCreateRequest, WarehouseResponse"
python -c "from app.core.exceptions import WarehouseNotFoundException, DuplicateCodeException"
```

### Gate 5: Database Schema Match ✅
```bash
# Compare model with service expectations
# Verify geometry columns exist
# Check enum values match
```

---

## Git Commit Template

**After ALL quality gates pass**:

```bash
git add \
  app/schemas/warehouse_schema.py \
  app/services/warehouse_service.py \
  app/core/exceptions.py \
  app/repositories/warehouse_repository.py \
  tests/unit/services/test_warehouse_service.py \
  tests/integration/test_warehouse_service_integration.py

git commit -m "feat(services): implement WarehouseService with PostGIS support

- Add WarehouseService with CRUD operations
- Implement GPS-based warehouse lookup (ST_Contains)
- Add Shapely geometry validation (polygon, closed, ≥3 vertices)
- Create Pydantic schemas with PostGIS → GeoJSON conversion
- Add WarehouseNotFoundException and DuplicateCodeException
- Extend WarehouseRepository with domain-specific queries
- Unit tests: 85%+ coverage, all passing
- Integration tests: real PostGIS queries, all passing

Blocks: S002, S003, S006, C001

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Estimated Timeline

**Total**: 6 hours (3 story points)

| Phase | Duration | Owner |
|-------|----------|-------|
| Planning (this document) | 30 min | Team Leader |
| Phase 1: Foundation | 1 hour | Python Expert |
| Phase 2: Service Implementation | 2 hours | Python Expert |
| Phase 3: Testing (parallel) | 2-3 hours | Testing Expert |
| Phase 4: Quality Gates | 30 min | Team Leader |
| **Total** | **6 hours** | - |

**Start**: 2025-10-20
**Target completion**: 2025-10-20 (same day)

---

**Mini-Plan Status**: READY FOR EXECUTION
**Next Action**: Move S001 to `01_ready/`, spawn Python Expert + Testing Expert
