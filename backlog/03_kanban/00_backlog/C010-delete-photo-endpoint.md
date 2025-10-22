# [C010] Delete Photo - DELETE /api/photos/{id}

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-03
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD

## Description

Soft-delete photo session and associated data (detections, estimations).

## Acceptance Criteria

- [ ] **AC1**: Soft delete (set deleted_at, active=false)
- [ ] **AC2**: Delete S3 objects (original + processed)
- [ ] **AC3**: Return HTTP 204 No Content
- [ ] **AC4**: Admin-only endpoint (role check)

```python
@router.delete("/{photo_id}", status_code=204)
async def delete_photo(
    photo_id: int,
    current_user: User = Depends(get_current_admin),
    service: PhotoService = Depends()
):
    """Soft-delete photo session (admin only)."""
    await service.soft_delete(photo_id)
    return None
```

**Coverage Target**: ≥80%

## Time Tracking

- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
