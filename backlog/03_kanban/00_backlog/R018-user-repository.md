# R018: User Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R017, S015]
  - Blocked by: [F006, F007, DB028]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L195-L206)

## Description

**What**: Implement repository class for `users` table with CRUD operations, email lookup, password hash validation, and role filtering.

**Why**: Users represent system actors (admin, supervisor, worker, viewer). Repository provides authentication, authorization, and activity tracking.

**Context**: Authentication/authorization foundation. Email is unique identifier. Password hash stored (never plaintext). Role-based access control.

## Acceptance Criteria

- [ ] **AC1**: `UserRepository` class inherits from `AsyncRepository[User]`
- [ ] **AC2**: Implements `get_by_email(email: str)` method (unique constraint, for login)
- [ ] **AC3**: Implements `get_by_role(role: str)` for role-based filtering
- [ ] **AC4**: Implements `get_active_users()` filtering by active flag
- [ ] **AC5**: Implements `update_last_login(user_id: int)` for activity tracking
- [ ] **AC6**: NEVER returns password_hash in standard queries (security)
- [ ] **AC7**: Query performance: email lookup <10ms

## Technical Implementation Notes

**Code hints**: get_by_email (for authentication), get_by_role (admin/supervisor/worker/viewer), get_active_users (active=true), update_last_login (timestamp update).

**Security**: Never include password_hash in default options(). Only load for authentication.

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Email lookup tested
- [ ] Password hash security verified (not exposed)
- [ ] Role filtering tested
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 3 story points (~6 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
