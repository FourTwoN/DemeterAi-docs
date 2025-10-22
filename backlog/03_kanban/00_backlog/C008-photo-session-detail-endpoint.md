# [C008] Photo Session Detail - GET /api/photos/sessions/{id}

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-03
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (1 story point)
- **Area**: `backend/controllers`
- **Assignee**: TBD

## Description

Retrieve detailed information for a single photo processing session including detections,
estimations, and processing status.

## Acceptance Criteria

- [ ] **AC1**: Path parameter: session_id
- [ ] **AC2**: Return 404 if not found
- [ ] **AC3**: Include related data: detections count, estimations count, batches created

```python
@router.get("/sessions/{session_id}", response_model=PhotoSessionResponse)
async def get_photo_session(
    session_id: int,
    service: PhotoService = Depends()
):
    """Get photo session detail."""
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session
```

**Coverage Target**: ≥85%

## Time Tracking

- **Estimated**: 1 story point

---

**Card Created**: 2025-10-09
