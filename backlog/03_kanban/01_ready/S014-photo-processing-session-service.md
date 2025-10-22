# S014: PhotoProcessingSessionService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `services/photo`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [S013, S016, S017, C013]
    - Blocked by: [R014]

## Description

**What**: Service for photo_processing_sessions lifecycle (status tracking, session CRUD, completion
handling).

**Why**: Tracks ML pipeline progress. Essential for UI status updates and error handling.

**Context**: Application Layer. Manages session state transitions (pending → processing →
completed/failed).

## Acceptance Criteria

- [ ] **AC1**: Session CRUD operations
- [ ] **AC2**: Status transition validation (pending → processing → completed/failed)
- [ ] **AC3**: Get sessions by location/date range
- [ ] **AC4**: Mark session complete (update with results)
- [ ] **AC5**: Unit tests ≥85% coverage

## Technical Notes

- Session statuses: pending, processing, completed, failed, warning
- Includes Celery task_id for progress tracking
- Eager loading of storage_location relationship

## Time Tracking

- **Estimated**: 3 story points (~6 hours)

---
**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
