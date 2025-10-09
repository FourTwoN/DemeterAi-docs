# [C003] Stock Movements Endpoint - POST /api/stock/movements

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02 (Week 5-6)
- **Status**: `backlog`
- **Priority**: `high` (monthly reconciliation workflow)
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [SCH003]
  - Blocked by**: [SVC003-stock-movement-service, DB007-stock-movements-model, DB009-movement-types-enum]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/workflows/README.md
- **Movement Types**: ../../engineering_plan/database/README.md (movement_types_enum)

## Description

Create endpoint for recording stock movements during monthly reconciliation period: plantado (plantings), muerte (deaths), trasplante (transplants).

**What**: FastAPI endpoint for stock movements:
- Accepts movement type (plantado/muerte/trasplante)
- Records quantity change (positive for plantado, negative for muerte)
- Links to storage_batch_id
- Updates stock_batches.current_quantity

**Why**: Monthly reconciliation workflow requires tracking all movements between photo snapshots to calculate sales accurately.

## Acceptance Criteria

- [ ] **AC1**: Route defined:
  ```python
  @router.post(
      "/movements",
      response_model=StockMovementResponse,
      status_code=status.HTTP_201_CREATED,
      summary="Record stock movement (plantado/muerte/trasplante)"
  )
  async def record_stock_movement(
      request: StockMovementRequest,
      current_user: User = Depends(get_current_user),
      service: StockMovementService = Depends()
  ) -> StockMovementResponse:
      """Record manual stock movement."""
      result = await service.create_movement(request, current_user.id)
      return result
  ```

- [ ] **AC2**: Validation:
  - movement_type in ['plantado', 'muerte', 'trasplante']
  - quantity > 0 for plantado, < 0 for muerte
  - storage_batch_id exists
  - Notes optional (max 500 chars)

- [ ] **AC3**: Error handling:
  - Invalid movement type → HTTP 422
  - Batch not found → HTTP 404
  - Insufficient quantity for muerte → HTTP 400

- [ ] **AC4**: Response includes movement_id, updated batch quantity

**Coverage Target**: ≥85%

## Handover Briefing

**Key decisions**:
- **Signed quantities**: Plantado +, muerte -, trasplante updates two batches
- **Batch updates**: service updates stock_batches.current_quantity
- **Audit trail**: All movements permanently recorded

## Definition of Done Checklist

- [ ] Route defined
- [ ] Movement type validation
- [ ] Unit tests ≥85%
- [ ] PR approved

## Time Tracking
- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
