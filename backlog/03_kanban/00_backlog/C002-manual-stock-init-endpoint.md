# [C002] Manual Stock Initialization Endpoint - POST /api/stock/manual

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02 (Week 5-6)
- **Status**: `backlog`
- **Priority**: `high` (secondary initialization method)
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [SCH001]
    - Blocked
      by: [SVC003-stock-movement-service, DB007-stock-movements-model, DB024-storage-location-config]

## Related Documentation

- **Engineering Plan**: ../../engineering_plan/api/README.md (lines 58-92)
- **Architecture**: ../../engineering_plan/03_architecture_overview.md (lines 317-359)
- **Workflow**: ../../engineering_plan/workflows/manual_initialization.md

## Description

Create the **secondary stock initialization endpoint** for manual entry when photo-based counting is
unavailable.

**What**: FastAPI endpoint for manual stock initialization:

- Accepts complete stock count (location, product, packaging, size, quantity)
- Validates against storage_location_config (critical validation)
- Creates stock_movement (type: "manual_init") + stock_batch
- Returns HTTP 201 (Created) with batch details

**Why**:

- **Fallback method**: When photos unavailable or user prefers manual entry
- **Pre-existing inventory**: Initialize system with existing counts
- **Validation**: Ensures manual entries match configured location settings
- **Trust user input**: No ML processing, direct database insert

**Context**: This endpoint bypasses ML pipeline entirely. It's faster but requires careful
validation to prevent data inconsistencies.

## Acceptance Criteria

- [ ] **AC1**: FastAPI route defined:
  ```python
  from fastapi import APIRouter, Depends, HTTPException, status
  from app.services.stock_movement_service import StockMovementService
  from app.schemas.stock_schema import ManualStockInitRequest, StockMovementResponse
  from app.dependencies.auth import get_current_user
  from app.exceptions.business_exceptions import (
      ProductMismatchException,
      PackagingMismatchException,
      ConfigNotFoundException
  )

  @router.post(
      "/manual",
      response_model=StockMovementResponse,
      status_code=status.HTTP_201_CREATED,
      summary="Manual stock initialization (no photo)",
      description="""
      Initialize stock manually without photo upload.

      **Validation**:
      - storage_location_config must exist
      - product_id must match configured product
      - packaging_catalog_id must match configured packaging
      - quantity must be > 0

      **Creates**:
      - stock_movement (type: manual_init)
      - stock_batch (with generated batch_code)

      **Use cases**:
      - Pre-existing inventory import
      - Photo system unavailable
      - Quick manual adjustments
      """
  )
  async def initialize_stock_manually(
      request: ManualStockInitRequest,
      current_user: User = Depends(get_current_user),
      service: StockMovementService = Depends()
  ) -> StockMovementResponse:
      """
      Manual stock initialization (business logic in service).
      """
      try:
          result = await service.create_manual_initialization(
              request=request,
              user_id=current_user.id
          )

          logger.info(
              f"Manual stock init: location={request.storage_location_id}, "
              f"quantity={request.quantity}, user={current_user.id}"
          )

          return result

      except ProductMismatchException as e:
          raise HTTPException(status_code=400, detail=str(e))
      except PackagingMismatchException as e:
          raise HTTPException(status_code=400, detail=str(e))
      except ConfigNotFoundException as e:
          raise HTTPException(status_code=404, detail=str(e))
      except Exception as e:
          logger.error(f"Manual init failed: {str(e)}", exc_info=True)
          raise HTTPException(status_code=500, detail="Internal server error")
  ```

- [ ] **AC2**: Request validation (Pydantic):
    - storage_location_id: required, int > 0
    - product_id: required, int > 0
    - packaging_catalog_id: required, int > 0
    - product_size_id: required, int > 0
    - quantity: required, int > 0
    - planting_date: optional, date format
    - notes: optional, string max 500 chars

- [ ] **AC3**: Error handling:
    - Product mismatch → HTTP 400 with user-friendly message
    - Packaging mismatch → HTTP 400
    - Config not found → HTTP 404
    - Invalid quantity (≤0) → HTTP 422
    - Database error → HTTP 500

- [ ] **AC4**: Response includes:
    - stock_movement_id (UUID)
    - stock_batch_id (serial)
    - batch_code (generated)
    - quantity confirmed
    - created_at timestamp

- [ ] **AC5**: OpenAPI documentation with examples

## Technical Implementation Notes

### Code Hints

**Business exception mapping:**

```python
from app.exceptions.business_exceptions import ProductMismatchException

try:
    result = await service.create_manual_initialization(request)
except ProductMismatchException as e:
    # Convert business exception to HTTP response
    raise HTTPException(
        status_code=400,
        detail=e.user_message  # User-friendly message
    )
```

### Testing Requirements

```python
def test_manual_init_success(client, auth_headers, mock_service):
    """Valid manual init returns 201"""
    request = {
        "storage_location_id": 123,
        "product_id": 45,
        "packaging_catalog_id": 12,
        "product_size_id": 3,
        "quantity": 1500,
        "planting_date": "2025-09-15"
    }

    response = client.post("/api/stock/manual", json=request, headers=auth_headers)

    assert response.status_code == 201
    assert response.json()["quantity"] == 1500

def test_manual_init_product_mismatch(client, auth_headers):
    """Product mismatch returns 400"""
    # Service will raise ProductMismatchException
    response = client.post("/api/stock/manual", json=request, headers=auth_headers)
    assert response.status_code == 400
    assert "mismatch" in response.json()["detail"].lower()
```

**Coverage Target**: ≥85%

### Performance Expectations

- Response time: <200ms (synchronous, no ML)
- Database inserts: 2 (movement + batch)
- Validation queries: 1 (config lookup)

## Handover Briefing

**Key decisions**:

1. **Synchronous**: HTTP 201 immediate (no background task)
2. **Critical validation**: Product/packaging must match config
3. **Trust user input**: No photo verification, assumes accuracy
4. **Batch code auto-generated**: Format: LOC{id}-PROD{id}-{date}-{seq}

**Next steps**: SCH001 (ManualStockInitRequest schema)

## Definition of Done Checklist

- [ ] Route defined in stock_controller.py
- [ ] Error handling for business exceptions
- [ ] OpenAPI docs complete
- [ ] Unit tests ≥85% coverage
- [ ] Integration test with database
- [ ] PR reviewed and approved

## Time Tracking

- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
