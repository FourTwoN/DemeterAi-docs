# S011: ReconciliationService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `CRITICAL`
- **Complexity**: XL (8 story points)
- **Area**: `services/stock`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [C010]
  - Blocked by: [S007, S008]

## Description

**What**: Implement `ReconciliationService` for **month-end reconciliation workflow** (automated sales calculation from photo comparison).

**Why**: Core of DemeterAI value proposition - automates monthly inventory reconciliation and calculates sales from photo comparisons.

**Context**: Clean Architecture Application Layer. CRITICAL SERVICE. Orchestrates S007 (movements) and S008 (batches) to perform month-end reconciliation: `sales = start_photo + movements - end_photo`.

## Acceptance Criteria

- [ ] **AC1**: Month-end reconciliation workflow:
```python
class ReconciliationService:
    def __init__(
        self,
        movement_service: StockMovementService,
        batch_service: StockBatchService
    ):
        self.movement_service = movement_service
        self.batch_service = batch_service

    async def reconcile_month(
        self,
        storage_location_id: int,
        month_start: datetime,
        month_end: datetime,
        end_photo_count: int
    ) -> ReconciliationResponse:
        """
        Perform month-end reconciliation
        CRITICAL WORKFLOW: sales = start + movements - end_photo
        """
        # 1. Get start count (baseline photo or manual)
        start_count = await self.movement_service.get_count_at_date(
            storage_location_id, month_start
        )

        # 2. Get movements in period
        movements = await self.movement_service.get_movements_for_location(
            storage_location_id, month_start, month_end
        )

        # 3. Calculate net movement
        net_movement = sum(
            m.quantity if m.movement_type in ["plantado", "trasplante_in"]
            else -m.quantity
            for m in movements
        )

        # 4. Calculate sales (CRITICAL FORMULA)
        calculated_sales = start_count + net_movement - end_photo_count

        # 5. Create sales movement
        if calculated_sales > 0:
            sales_movement = await self.movement_service.create_movement({
                "storage_location_id": storage_location_id,
                "movement_type": "venta",
                "quantity": calculated_sales,
                "source_type": "calculated",
                "timestamp": month_end
            })

        return ReconciliationResponse(
            storage_location_id=storage_location_id,
            period_start=month_start,
            period_end=month_end,
            start_count=start_count,
            net_movement=net_movement,
            end_photo_count=end_photo_count,
            calculated_sales=calculated_sales
        )
```

- [ ] **AC2**: Validate reconciliation (detect discrepancies):
```python
async def validate_reconciliation(
    self,
    reconciliation: ReconciliationResponse,
    actual_sales: Optional[int] = None
) -> ValidationResult:
    """Validate reconciliation results"""
    errors = []

    # Check for negative sales
    if reconciliation.calculated_sales < 0:
        errors.append(
            f"Calculated sales is negative ({reconciliation.calculated_sales}). "
            "Possible counting error or unreported movements."
        )

    # Compare with actual sales (if provided)
    if actual_sales is not None:
        discrepancy = abs(reconciliation.calculated_sales - actual_sales)
        tolerance = 0.05 * actual_sales  # 5% tolerance

        if discrepancy > tolerance:
            errors.append(
                f"Sales discrepancy: calculated {reconciliation.calculated_sales}, "
                f"actual {actual_sales} (diff: {discrepancy})"
            )

    return ValidationResult(valid=len(errors) == 0, errors=errors)
```

- [ ] **AC3**: Unit tests achieve ≥90% coverage

## Technical Implementation Notes

### Architecture
- **Layer**: Application (Service)
- **Dependencies**: S007, S008
- **Design Pattern**: Workflow orchestration

### Performance Expectations
- `reconcile_month`: <500ms (includes movement aggregation)

## Handover Briefing

**Context**: CRITICAL SERVICE for DemeterAI value proposition. Automates monthly reconciliation.

**Key decisions**:
- Formula: `sales = start + movements - end_photo`
- Negative sales indicate errors (flag for review)
- 5% tolerance for actual vs calculated sales

**Next steps**: C010 (ReconciliationController)

## Definition of Done Checklist

- [ ] Service code written
- [ ] Reconciliation formula validated
- [ ] Unit tests pass (≥90% coverage)
- [ ] Integration tests with S007/S008
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 8 story points (~16 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
