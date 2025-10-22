# S018: ClassificationService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (3 story points)
- **Area**: `services/photo`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [C017, ML004]
    - Blocked by: [S017, S036]

## Description

**What**: Service for assigning product/packaging classifications to ML estimations (links
estimations to product catalog).

**Why**: Connects ML results to product catalog. Essential for stock movement creation from photo
processing.

**Context**: Application Layer. Reads storage_location_config to determine expected
product/packaging, assigns to estimations.

## Acceptance Criteria

- [ ] **AC1**: Assign classification from config (auto-assign expected product/packaging)
- [ ] **AC2**: Manual classification override (user correction if config wrong)
- [ ] **AC3**: Validate classification (product + packaging must exist in catalog)
- [ ] **AC4**: Create stock movement from classified estimation
- [ ] **AC5**: Unit tests ≥85% coverage

## Technical Notes

- Reads storage_location_configs for expected product/packaging
- Manual override for misclassifications
- Creates stock_movements (type: "foto") after classification

## Time Tracking

- **Estimated**: 3 story points (~6 hours)

---
**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
