# [C009] Reprocess Failed Photo - POST /api/photos/reprocess

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-03
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD

## Description

Retry ML processing for failed photo sessions (circuit breaker recovery, manual retry).

## Acceptance Criteria

- [ ] **AC1**: Request body: session_id
- [ ] **AC2**: Verify session status is 'failed' or 'warning'
- [ ] **AC3**: Dispatch new Celery task with same photo
- [ ] **AC4**: Return new task_id

```python
@router.post("/reprocess", response_model=PhotoUploadResponse)
async def reprocess_photo(
    session_id: int,
    service: PhotoService = Depends()
):
    """Retry failed photo processing."""
    session = await service.get_session(session_id)
    if session.status not in ['failed', 'warning']:
        raise HTTPException(400, "Only failed/warning sessions can be reprocessed")

    result = await service.reprocess(session_id)
    return result
```

**Coverage Target**: ≥80%

## Time Tracking
- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
