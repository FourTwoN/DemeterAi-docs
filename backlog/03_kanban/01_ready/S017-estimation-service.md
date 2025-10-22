# S017: EstimationService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `services/photo`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [S018, ML003, C016]
    - Blocked by: [R017]

## Description

**What**: Service for creating estimations from ML results (band-based + density-based methods).

**Why**: Persists ML estimation results. Supports two estimation methods (band-based for
segmentation, density-based for detection).

**Context**: Application Layer. Called by ML pipeline to store final count estimations.

## Acceptance Criteria

- [ ] **AC1**: Bulk create estimations from ML results
- [ ] **AC2**: Support band-based method (size bands: pequeño, mediano, grande)
- [ ] **AC3**: Support density-based method (detections → total count)
- [ ] **AC4**: Calculate final estimated quantity (sum across bands)
- [ ] **AC5**: Link estimations to photo_processing_session
- [ ] **AC6**: Unit tests ≥85% coverage

## Technical Notes

- Band-based: 3 bands (pequeño, mediano, grande) with individual counts
- Density-based: Single total count from detection density
- Final quantity = sum of all band counts

## Time Tracking

- **Estimated**: 3 story points (~6 hours)

---
**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
