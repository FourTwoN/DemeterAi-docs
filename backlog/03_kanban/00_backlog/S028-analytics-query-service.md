# S028: AnalyticsQueryService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: L (5 story points)
- **Area**: `services/analytics`
- **Dependencies**:
  - Blocks: [S029, C025]
  - Blocked by: [S012]

## Description

**What**: Analytics query service with flexible filters (date range, location, product, movement type).

**Why**: Powers analytics dashboard with customizable reports.

**Context**: Application Layer. Aggregates data from stock_movements, stock_batches, and photo_processing_sessions.

## Acceptance Criteria

- [ ] **AC1**: Query stock movements with filters (date, location, product, type)
- [ ] **AC2**: Aggregate stock by warehouse/area/location
- [ ] **AC3**: Photo processing statistics (success rate, avg processing time)
- [ ] **AC4**: Sales trends (daily, weekly, monthly aggregations)
- [ ] **AC5**: Inventory snapshots (stock at specific date)
- [ ] **AC6**: Unit tests ≥85% coverage

## Time Tracking
- **Estimated**: 5 story points (~10 hours)

---
**Card Created**: 2025-10-09
