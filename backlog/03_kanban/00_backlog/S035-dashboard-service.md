# S035: DashboardService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `services/analytics`
- **Dependencies**:
  - Blocks: [C031]
  - Blocked by: [S028, S012]

## Description

**What**: Dashboard data aggregation service (KPIs, widgets, summary statistics).

**Why**: Powers main dashboard UI with key metrics.

**Context**: Application Layer. Aggregates data for dashboard widgets.

## Acceptance Criteria

- [ ] **AC1**: Get dashboard KPIs (total stock, total locations, processing rate)
- [ ] **AC2**: Recent activity feed (last 10 movements/photos)
- [ ] **AC3**: Stock alerts (low stock, high stock, anomalies)
- [ ] **AC4**: Photo processing stats (success rate, avg time)
- [ ] **AC5**: Unit tests ≥85% coverage

## Time Tracking
- **Estimated**: 3 story points (~6 hours)

---
**Card Created**: 2025-10-09
