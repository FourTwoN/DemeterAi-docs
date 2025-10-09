# R017: Stock Movement Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `critical`
- **Complexity**: L (5 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [S014]
  - Blocked by: [F006, F007, DB007, R016, R018]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L178-L194)

## Description

**What**: Implement repository class for `stock_movements` table with CRUD operations, movement_id UUID lookup, and movement history queries.

**Why**: Stock movements track all inventory transactions (plantings, deaths, transfers, sales, photos, manual adjustments). Repository provides transaction history, audit trail, and monthly reconciliation queries.

**Context**: Immutable audit log of all stock changes. movement_id is UUID for distributed system support. Links to batches, users, and photo sessions.

## Acceptance Criteria

- [ ] **AC1**: `StockMovementRepository` class inherits from `AsyncRepository[StockMovement]`
- [ ] **AC2**: Implements `get_by_movement_id(movement_id: UUID)` method (unique constraint)
- [ ] **AC3**: Implements `get_by_batch_id(batch_id: int, limit: int)` for movement history
- [ ] **AC4**: Implements `get_by_session_id(session_id: int)` for photo-generated movements
- [ ] **AC5**: Implements `get_movements_by_type(movement_type: str, start_date, end_date)` for analytics
- [ ] **AC6**: Implements `get_monthly_reconciliation(year: int, month: int)` for sales calculation
- [ ] **AC7**: Includes eager loading for batch, user, source/destination bins
- [ ] **AC8**: Query performance: UUID lookup <10ms, history queries <50ms

## Technical Implementation Notes

**Code hints**: get_by_movement_id (UUID index), get_by_batch_id (with LIMIT for pagination), get_by_session_id (photo-generated movements), get_movements_by_type (with date range), get_monthly_reconciliation (GROUP BY for sales calculation).

**Performance**: UUID index critical, date range indexed, batch_id indexed for history queries.

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] UUID lookup tested
- [ ] Movement history pagination tested
- [ ] Monthly reconciliation tested
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 5 story points (~10 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
