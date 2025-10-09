# S008: StockBatchService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-03
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: L (5 story points)
- **Area**: `services/stock`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [S007, S010, S012, C008]
  - Blocked by: [R008]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/workflows/README.md](../../engineering_plan/workflows/README.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd)

## Description

**What**: Implement `StockBatchService` for stock batch creation, aggregation, and lifecycle management (grouping movements by product/packaging/size/location).

**Why**: Stock batches aggregate individual movements for inventory queries. Essential for current stock calculations and batch tracking (planting date → transplant → sales).

**Context**: Clean Architecture Application Layer. Called by S007 (StockMovementService) to create batches from movements. Aggregates stock by product/packaging/size combinations.

## Acceptance Criteria

- [ ] **AC1**: Create batch from movement:
  ```python
  from app.repositories.stock_batch_repository import StockBatchRepository

  class StockBatchService:
      def __init__(self, batch_repo: StockBatchRepository):
          self.batch_repo = batch_repo

      async def create_from_movement(
          self,
          movement: StockMovement
      ) -> StockBatchResponse:
          """Create stock batch from movement"""
          # Find existing batch or create new
          existing = await self.batch_repo.get_active_batch(
              storage_location_id=movement.storage_location_id,
              product_id=movement.product_id,
              packaging_catalog_id=movement.packaging_catalog_id,
              product_size=movement.product_size
          )

          if existing:
              # Update existing batch
              updated = await self.batch_repo.update(existing.stock_batch_id, {
                  "quantity": existing.quantity + movement.quantity
              })
              return StockBatchResponse.from_model(updated)

          # Create new batch
          batch = await self.batch_repo.create({
              "storage_location_id": movement.storage_location_id,
              "product_id": movement.product_id,
              "packaging_catalog_id": movement.packaging_catalog_id,
              "product_size": movement.product_size,
              "quantity": movement.quantity,
              "batch_status": "active",
              "planting_date": movement.timestamp
          })

          return StockBatchResponse.from_model(batch)
  ```

- [ ] **AC2**: Get current stock for location:
  ```python
  async def get_total_stock_for_location(
      self,
      storage_location_id: int
  ) -> int:
      """Sum all active batches for location"""
      batches = await self.batch_repo.get_by_location(
          storage_location_id, active_only=True
      )
      return sum(b.quantity for b in batches)
  ```

- [ ] **AC3**: Batch lifecycle operations:
  ```python
  async def update_from_movement(self, movement: StockMovement) -> StockBatchResponse:
      """Update batch based on movement type"""
      pass

  async def decrement_from_movement(self, movement: StockMovement) -> None:
      """Decrement batch for deaths"""
      pass

  async def reverse_movement(
      self,
      original: StockMovement,
      reverse: StockMovement
  ) -> None:
      """Reverse batch changes"""
      pass
  ```

- [ ] **AC4**: Unit tests achieve ≥85% coverage

## Technical Implementation Notes

### Architecture
- **Layer**: Application (Service)
- **Dependencies**: R008 (StockBatchRepository)
- **Design Pattern**: Aggregation service

### Testing Requirements
**Coverage Target**: ≥85%

### Performance Expectations
- `create_from_movement`: <50ms
- `get_total_stock_for_location`: <100ms

## Handover Briefing

**Context**: Aggregates movements into batches. Called by StockMovementService.

**Key decisions**:
- Batches grouped by product/packaging/size/location
- Active batches updated, inactive ones archived

**Next steps**: S010 (BatchLifecycleService)

## Definition of Done Checklist

- [ ] Service code written
- [ ] Batch aggregation logic working
- [ ] Unit tests pass (≥85% coverage)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 5 story points (~10 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
