# [C007] List Photo Sessions - GET /api/photos/sessions

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-03
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (1 story point)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
    - Blocked by: [SVC001-photo-service]

## Description

List all photo processing sessions with filtering and pagination.

## Acceptance Criteria

- [ ] **AC1**: Query parameters: warehouse_id, status, date_from, date_to
- [ ] **AC2**: Pagination: skip, limit (default 50, max 200)
- [ ] **AC3**: Order by created_at DESC

```python
@router.get("/sessions", response_model=List[PhotoSessionResponse])
async def list_photo_sessions(
    warehouse_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
    service: PhotoService = Depends()
):
    """List photo processing sessions."""
    return await service.list_sessions(
        warehouse_id, status, date_from, date_to, skip, limit
    )
```

**Coverage Target**: ≥80%

## Time Tracking

- **Estimated**: 1 story point

---

**Card Created**: 2025-10-09
