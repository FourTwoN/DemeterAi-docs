# [C004] Query Stock Batches Endpoint - GET /api/stock/batches

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02 (Week 5-6)
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [SCH013]
  - Blocked by: [SVC004-stock-batch-service, DB008-stock-batches-model]

## Description

Query endpoint for stock batches with filtering by location, product, status.

**What**: GET endpoint with query parameters:
- Filter by storage_location_id, product_id, packaging_id
- Filter by batch_status (activo/agotado/vendido)
- Pagination (skip, limit)
- Order by created_at DESC

**Why**: Users need to query current stock for reporting and verification.

## Acceptance Criteria

- [ ] **AC1**: Route defined:
  ```python
  @router.get(
      "/batches",
      response_model=List[StockBatchResponse],
      summary="Query stock batches with filters"
  )
  async def query_stock_batches(
      storage_location_id: Optional[int] = None,
      product_id: Optional[int] = None,
      batch_status: Optional[str] = None,
      skip: int = 0,
      limit: int = 100,
      service: StockBatchService = Depends()
  ) -> List[StockBatchResponse]:
      """Query stock batches."""
      return await service.query_batches(
          location_id=storage_location_id,
          product_id=product_id,
          status=batch_status,
          skip=skip,
          limit=limit
      )
  ```

- [ ] **AC2**: Pagination defaults: skip=0, limit=100 (max 1000)
- [ ] **AC3**: Response includes batch details, current_quantity, batch_code

**Coverage Target**: ≥80%

## Definition of Done Checklist

- [ ] Route with query parameters
- [ ] Pagination working
- [ ] Unit tests ≥80%

## Time Tracking
- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
