# Epic 006: Schemas & Validation

**Status**: Ready
**Sprint**: Sprint-04 (Week 9-10) - parallel with Controllers
**Priority**: high (API contract)
**Total Story Points**: 60
**Total Cards**: 20 (SCH001-SCH020)

---

## Goal

Implement all Pydantic 2.10.0 request/response schemas with comprehensive validation rules, transformers, and serialization for type-safe API contracts.

---

## Success Criteria

- [ ] All 20 schema groups implemented
- [ ] All schemas have comprehensive validation (min/max, regex, custom validators)
- [ ] Request schemas validate input before reaching services
- [ ] Response schemas serialize SQLAlchemy models correctly
- [ ] Enum schemas for all categorical fields
- [ ] Schema inheritance used to reduce duplication
- [ ] All schemas pass Pydantic validation tests

---

## Cards List (20 cards, 60 points)

### Core Base Schemas (8 points)
- **SCH001**: Base schemas (BaseRequest, BaseResponse, Pagination) (3pts)
- **SCH002**: Error response schemas (ErrorResponse, ValidationError) (2pts)
- **SCH003**: Enum schemas (MovementType, WarehouseType, ProductState) (3pts)

### Stock Schemas (12 points)
- **SCH004**: StockMovement request/response (3pts)
- **SCH005**: ManualInitialization request (3pts)
- **SCH006**: StockBatch response (2pts)
- **SCH007**: ReconciliationReport response (2pts)
- **SCH008**: StockHistory response (2pts)

### Location Schemas (9 points)
- **SCH009**: Warehouse request/response (2pts)
- **SCH010**: StorageArea request/response (2pts)
- **SCH011**: StorageLocation request/response (3pts)
- **SCH012**: MapView GeoJSON response (2pts)

### Product & Packaging Schemas (9 points)
- **SCH013**: Product request/response (3pts)
- **SCH014**: Packaging request/response (2pts)
- **SCH015**: PriceList request/response (2pts)
- **SCH016**: Classification response (2pts)

### Photo & ML Schemas (10 points)
- **SCH017**: PhotoUpload request (multipart) (3pts)
- **SCH018**: TaskStatus response (Celery polling) (2pts)
- **SCH019**: PhotoSession response (3pts)
- **SCH020**: MLResults response (detections + estimations) (2pts)

### Analytics Schemas (6 points)
- **SCH021**: ReportRequest (filters, grouping) (3pts)
- **SCH022**: ReportResponse (data + totals) (2pts)
- **SCH023**: ExportRequest (format, date range) (1pt)

### Config Schemas (3 points)
- **SCH024**: StorageLocationConfig request/response (2pts)
- **SCH025**: DensityParameters request/response (1pt)

### Auth Schemas (3 points)
- **SCH026**: LoginRequest/Response (JWT tokens) (2pts)
- **SCH027**: UserResponse (safe user data) (1pt)

---

## Dependencies

**Blocked By**: DB001-DB035 (models - need to know fields)
**Blocks**: C001-C026 (controllers - need schemas for validation)

---

## Technical Approach

**Schema Patterns**:
```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

# Request schema (validation)
class ManualStockInitRequest(BaseModel):
    storage_location_id: int = Field(..., gt=0)
    product_id: int = Field(..., gt=0)
    packaging_catalog_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=1000000)
    planting_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        if v < 0:
            raise ValueError('Quantity must be positive')
        return v

# Response schema (serialization)
class StockMovementResponse(BaseModel):
    id: int
    movement_id: str  # UUID
    movement_type: str
    quantity: int
    created_at: datetime
    batch_code: Optional[str]

    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode)
```

**Validation Rules**:
- All IDs: `gt=0` (positive integers)
- Quantities: `gt=0` (no zero or negative)
- Codes: `regex='^[A-Z0-9-]+$'`
- Emails: `EmailStr` type
- Dates: Past dates only for historical data
- Enums: Validated against allowed values

**Schema Inheritance**:
```python
# Base (shared fields)
class BaseProduct(BaseModel):
    sku: str
    name: str
    description: Optional[str]

# Request (for creation)
class ProductCreateRequest(BaseProduct):
    family_id: int

# Response (includes generated fields)
class ProductResponse(BaseProduct):
    id: int
    family_id: int
    created_at: datetime
```

---

**Epic Owner**: API Lead
**Created**: 2025-10-09
