# Epic 005: Controllers & API Endpoints

**Status**: Ready
**Sprint**: Sprint-04 (Week 9-10)
**Priority**: high (user-facing interface)
**Total Story Points**: 130
**Total Cards**: 26 (C001-C026)

---

## Goal

Implement complete FastAPI REST API with all endpoints for stock management, locations, analytics, configuration, authentication, and photo operations, following OpenAPI standards.

---

## Success Criteria

- [ ] All 26 controllers implemented following REST conventions
- [ ] OpenAPI docs auto-generated at `/docs`
- [ ] All endpoints return consistent error responses
- [ ] Dependency injection used for database sessions and services
- [ ] All endpoints have request/response schema validation (Pydantic)
- [ ] API versioning implemented (v1 baseline)
- [ ] Rate limiting configured (future-ready)

---

## Cards List (26 cards, 130 points)

### Stock Controllers (25 points)
- **C001**: POST /api/stock/photo - Photo upload (5pts)
- **C002**: POST /api/stock/manual - Manual initialization (5pts)
- **C003**: GET /api/stock/tasks/status - Task status polling (3pts)
- **C004**: POST /api/stock/movements - Create movement (5pts)
- **C005**: GET /api/stock/batches - List batches (3pts)
- **C006**: GET /api/stock/batches/{id} - Batch detail (2pts)
- **C007**: GET /api/stock/history - Movement history (2pts)

### Location Controllers (20 points)
- **C008**: GET /api/locations/warehouses - List warehouses (3pts)
- **C009**: GET /api/locations/warehouses/{id} - Warehouse detail (3pts)
- **C010**: GET /api/locations/areas - List areas (3pts)
- **C011**: GET /api/locations/locations - List storage locations (5pts)
- **C012**: GET /api/locations/locations/{id} - Location detail (3pts)
- **C013**: GET /api/locations/map-view - Map data (GeoJSON) (3pts)

### Analytics Controllers (20 points)
- **C014**: POST /api/analytics/report - Generate custom report (8pts)
- **C015**: GET /api/analytics/export - Export to Excel/CSV (5pts)
- **C016**: POST /api/analytics/comparison - Month comparison (5pts)
- **C017**: GET /api/analytics/dashboard - Dashboard data (2pts)

### Configuration Controllers (15 points)
- **C018**: POST /api/config/storage-location - Create location config (5pts)
- **C019**: GET /api/config/storage-location/{id} - Get config (3pts)
- **C020**: PUT /api/config/storage-location/{id} - Update config (5pts)
- **C021**: DELETE /api/config/storage-location/{id} - Delete config (2pts)

### Auth Controllers (15 points)
- **C022**: POST /api/auth/login - JWT login (5pts)
- **C023**: POST /api/auth/refresh - Refresh token (3pts)
- **C024**: GET /api/auth/me - Current user (2pts)
- **C025**: POST /api/auth/logout - Logout (2pts)
- **C026**: POST /api/auth/change-password - Change password (3pts)

### Health & Meta Controllers (10 points)
- **C027**: GET /health - Health check (2pts)
- **C028**: GET /metrics - Prometheus metrics (3pts)
- **C029**: GET /version - API version info (1pt)

---

## Dependencies

**Blocked By**: S001-S042 (services), SCH001-SCH020 (schemas)
**Blocks**: Frontend development, API documentation

---

## Technical Approach

**Controller Pattern (HTTP ONLY)**:
```python
# ✅ CORRECT: Controller handles HTTP, calls service
@router.post("/stock/manual", status_code=201)
async def manual_init(
    request: ManualStockInitRequest,  # Pydantic validation
    service: StockMovementService = Depends(get_stock_service)
):
    result = await service.create_manual_initialization(request)
    return result  # Auto-serialized to JSON

# ❌ INCORRECT: Business logic in controller
@router.post("/stock/manual")
async def manual_init(request: ManualStockInitRequest, db: Session = Depends()):
    # Validation logic here ❌
    # Database queries here ❌
    # Complex calculations here ❌
```

**Key Patterns**:
- Dependency injection for services (`Depends()`)
- Pydantic request/response schemas
- HTTP status codes (200, 201, 400, 404, 500)
- Global exception handlers (from F005)
- Correlation IDs in headers
- OpenAPI documentation tags

**API Versioning**:
```python
# v1 baseline (stable)
router = APIRouter(prefix="/api/v1")

# v2 future (backward compatible)
router_v2 = APIRouter(prefix="/api/v2")
```

---

**Epic Owner**: API Lead
**Created**: 2025-10-09
