# [C025] List Users - GET /api/users

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: S (1 story point)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [SCH018]
  - Blocked by: [SVC012-user-service, DB028-users-model]

## Description

List users for admin management (admin-only endpoint).

## Acceptance Criteria

- [ ] **AC1**: Admin-only (role check)
- [ ] **AC2**: Return all users with roles
- [ ] **AC3**: Filter by active/inactive

```python
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    active_only: bool = True,
    current_user: User = Depends(get_current_admin),
    service: UserService = Depends()
):
    """List users (admin only)."""
    return await service.list_users(active_only)
```

**Coverage Target**: ≥80%

## Time Tracking
- **Estimated**: 1 story point

---

**Card Created**: 2025-10-09
