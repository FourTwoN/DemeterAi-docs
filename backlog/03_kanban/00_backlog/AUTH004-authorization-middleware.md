# [AUTH004] Authorization Middleware

## Metadata
- **Epic**: epic-009-auth-security
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `critical` ⚡
- **Complexity**: M (5 story points)
- **Area**: `authentication`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [AUTH006, all protected API endpoints]
  - Blocked by: [AUTH001]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/03_architecture_overview.md
- **FastAPI Docs**: https://fastapi.tiangolo.com/tutorial/dependencies/

## Description

Create FastAPI dependency for protecting routes with JWT authentication and role-based authorization. Validates tokens and enforces role requirements.

**What**: Middleware (FastAPI Depends) that extracts JWT from Authorization header, validates it, and checks user roles.

**Why**: Protect API endpoints from unauthorized access. Enforce role-based permissions (admin, operator, viewer).

**Context**: Used across all protected API routes. Integrates with AUTH001 (JWT service).

## Acceptance Criteria

- [ ] **AC1**: Authorization dependencies in `app/core/auth_middleware.py`:
  ```python
  async def get_current_user(token: str = Depends(oauth2_scheme)) -> User
  async def require_admin(user: User = Depends(get_current_user)) -> User
  async def require_operator(user: User = Depends(get_current_user)) -> User
  ```

- [ ] **AC2**: JWT token extraction from Authorization header:
  ```
  Authorization: Bearer <jwt_token>
  ```

- [ ] **AC3**: Token validation flow:
  1. Extract token from header
  2. Decode and verify JWT
  3. Look up user by ID from token payload
  4. Check user is_active
  5. Return User object

- [ ] **AC4**: Role hierarchy:
  - **admin**: Full access (all operations)
  - **operator**: Read + Write (no user management)
  - **viewer**: Read-only

- [ ] **AC5**: Error responses:
  - Missing token → 401 Unauthorized
  - Invalid token → 401 Unauthorized
  - Expired token → 401 Unauthorized with "Token expired" message
  - Insufficient permissions → 403 Forbidden

## Technical Implementation Notes

### Architecture
- Layer: Presentation (Middleware)
- Pattern: Dependency injection
- Integration: FastAPI OAuth2PasswordBearer

### Code Hints

**app/core/auth_middleware.py:**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.services.auth.jwt_service import JWTService
from app.repositories.user_repository import UserRepository
from app.db.session import get_db_session
from app.core.exceptions import JWTExpiredException, JWTException
from sqlalchemy.ext.asyncio import AsyncSession

# OAuth2 scheme (extracts token from Authorization header)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Extract and validate JWT token, return current user.

    Raises:
        HTTPException 401: Invalid or expired token
        HTTPException 403: User account disabled
    """
    jwt_service = JWTService()

    try:
        # Decode token
        payload = jwt_service.decode_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Look up user
        user_repo = UserRepository(User, session)
        user = await user_repo.get(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account disabled"
            )

        return user

    except JWTExpiredException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except JWTException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def require_admin(
    user: User = Depends(get_current_user)
) -> User:
    """
    Ensure current user has admin role.

    Raises:
        HTTPException 403: User is not admin
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

async def require_operator(
    user: User = Depends(get_current_user)
) -> User:
    """
    Ensure current user has operator or admin role.

    Raises:
        HTTPException 403: User is not operator or admin
    """
    if user.role not in ["operator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin access required"
        )
    return user

async def require_viewer(
    user: User = Depends(get_current_user)
) -> User:
    """
    Ensure current user has any valid role (viewer, operator, admin).
    This is equivalent to get_current_user (authenticated user).
    """
    return user
```

**Usage in controllers:**
```python
from fastapi import APIRouter, Depends
from app.core.auth_middleware import get_current_user, require_admin

router = APIRouter()

@router.get("/api/stock/summary")
async def get_stock_summary(
    user: User = Depends(get_current_user)  # Any authenticated user
):
    return {"message": f"Hello {user.email}"}

@router.delete("/api/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin)  # Admin only
):
    return {"message": f"User {user_id} deleted by admin {current_user.email}"}
```

### Testing Requirements

**Unit Tests** (`tests/core/test_auth_middleware.py`):
- [ ] Test valid token returns user
- [ ] Test missing token raises 401
- [ ] Test invalid token raises 401
- [ ] Test expired token raises 401 with correct message
- [ ] Test disabled user raises 403
- [ ] Test require_admin allows admin, blocks others
- [ ] Test require_operator allows operator and admin, blocks viewer

**Integration Tests** (`tests/api/test_protected_routes.py`):
- [ ] Test protected route without token returns 401
- [ ] Test protected route with valid token returns 200
- [ ] Test admin-only route with non-admin returns 403

**Test Example**:
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_protected_route_without_token():
    response = client.get("/api/stock/summary")
    assert response.status_code == 401

def test_protected_route_with_valid_token(valid_token):
    headers = {"Authorization": f"Bearer {valid_token}"}
    response = client.get("/api/stock/summary", headers=headers)
    assert response.status_code == 200

def test_admin_route_with_non_admin(operator_token):
    headers = {"Authorization": f"Bearer {operator_token}"}
    response = client.delete("/api/users/123", headers=headers)
    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]
```

### Performance Expectations
- Token validation: <10ms
- User lookup: <20ms (cached in future)
- Total middleware overhead: <30ms per request

## Handover Briefing

**For the next developer:**
- **Context**: FastAPI dependency system makes this elegant (just add Depends())
- **Key decisions**:
  - OAuth2PasswordBearer extracts token from Authorization header
  - Role hierarchy: admin > operator > viewer
  - 401 for auth issues, 403 for permission issues
- **Security considerations**:
  - Always check user.is_active (prevent deleted users)
  - Don't reveal if user exists in error messages
  - Log unauthorized access attempts (future: rate limiting)
- **Performance optimization (future)**:
  - Cache user lookups in Redis (30 sec TTL)
  - Avoids DB query on every request
- **Next steps after this card**:
  - AUTH006: Login/logout endpoints
  - Apply to all API routes that need protection

## Definition of Done Checklist

- [ ] Code passes all unit tests
- [ ] Integration tests with real FastAPI routes
- [ ] Token extraction works from Authorization header
- [ ] Role-based authorization enforced
- [ ] All error cases return correct HTTP status
- [ ] Test coverage >85%
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated with usage examples

## Time Tracking
- **Estimated**: 5 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
