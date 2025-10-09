# S015: S3ImageService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `services/photo`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [S013, ML001, C014]
  - Blocked by: [F008-s3-connection]

## Description

**What**: S3 operations service (upload original, upload visualizations, download, generate presigned URLs, lifecycle management).

**Why**: Centralizes S3 interactions. Implements circuit breaker pattern for resilience.

**Context**: Application Layer. Wraps boto3 S3 client with error handling and circuit breaker.

## Acceptance Criteria

- [ ] **AC1**: Upload original photo to S3 (bucket: demeter-photos-original)
- [ ] **AC2**: Upload visualization images (bucket: demeter-photos-viz)
- [ ] **AC3**: Generate presigned URLs (24-hour expiry)
- [ ] **AC4**: Download image from S3
- [ ] **AC5**: Circuit breaker for S3 failures (pybreaker, fail_max=5, timeout=60s)
- [ ] **AC6**: Unit tests ≥85% coverage

## Technical Notes
- Circuit breaker prevents cascading S3 failures
- Presigned URLs for secure browser access
- S3 key format: `{session_id}/{filename}`

## Time Tracking
- **Estimated**: 3 story points (~6 hours)

---
**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
