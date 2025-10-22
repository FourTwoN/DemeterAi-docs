# S016: DetectionService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `services/photo`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [S017, ML002, C015]
    - Blocked by: [R016]

## Description

**What**: Service for creating detections from ML results (bulk insert, bbox validation, linking to
sessions).

**Why**: Transforms ML pipeline output into database records. Handles bulk inserts for performance.

**Context**: Application Layer. Called by ML pipeline (CEL006) to persist detection results.

## Acceptance Criteria

- [ ] **AC1**: Bulk create detections from ML results
- [ ] **AC2**: Validate bounding box coordinates (0-1 range, xmin < xmax, ymin < ymax)
- [ ] **AC3**: Link detections to photo_processing_session
- [ ] **AC4**: Get detections by session
- [ ] **AC5**: Calculate detection statistics (count, avg confidence)
- [ ] **AC6**: Unit tests ≥85% coverage

## Technical Notes

- Uses bulk_insert_mappings for performance (1000+ detections per photo)
- Bounding boxes normalized (0-1 range)
- Confidence scores: 0.0-1.0

## Time Tracking

- **Estimated**: 3 story points (~6 hours)

---
**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
