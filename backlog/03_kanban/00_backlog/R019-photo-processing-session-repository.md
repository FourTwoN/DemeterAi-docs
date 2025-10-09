# R019: Photo Processing Session Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `critical`
- **Complexity**: M (3 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R022, R023, S016]
  - Blocked by: [F006, F007, DB012, R020, R003]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L207-L226)

## Description

**What**: Implement repository class for `photo_processing_sessions` table with CRUD operations, session_id UUID lookup, and ML pipeline status tracking.

**Why**: Photo processing sessions track ML pipeline execution (segmentation → detection → estimation). Repository provides session management, status tracking, and validation workflow.

**Context**: Created when photo uploaded → ML pipeline processes → results stored → user validates. session_id is UUID for distributed Celery tasks.

## Acceptance Criteria

- [ ] **AC1**: `PhotoProcessingSessionRepository` class inherits from `AsyncRepository[PhotoProcessingSession]`
- [ ] **AC2**: Implements `get_by_session_id(session_id: UUID)` method (unique constraint)
- [ ] **AC3**: Implements `get_by_storage_location_id(location_id: int)` for location photo history
- [ ] **AC4**: Implements `get_pending_validation()` for validation workflow
- [ ] **AC5**: Implements `get_by_status(status: str, limit: int)` for monitoring
- [ ] **AC6**: Includes eager loading for original_image, processed_image, storage_location
- [ ] **AC7**: Query performance: UUID lookup <10ms, status filtering <30ms

## Technical Implementation Notes

**Code hints**: get_by_session_id (UUID index), get_by_storage_location_id (for location history), get_pending_validation (validated=false), get_by_status (pending/processing/completed/failed), get_failed_sessions_with_errors (for debugging).

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] UUID lookup tested
- [ ] Status filtering tested
- [ ] Validation workflow tested
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 3 story points (~6 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
