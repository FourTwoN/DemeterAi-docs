# [AUTH006] Login/Logout Endpoints

## Metadata

- **Epic**: epic-009-auth-security
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `critical` ⚡
- **Complexity**: S (3 story points)
- **Area**: `authentication`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: All protected API endpoints
    - Blocked by: [AUTH001, AUTH002, AUTH003, AUTH004, AUTH005]

## Related Documentation

- **Engineering Plan**: ../../engineering_plan/api/README.md
- **Architecture**: ../../engineering_plan/03_architecture_overview.md (Controllers layer)

## Description

Create FastAPI controller endpoints for login and logout. Thin controller layer that delegates to
UserAuthenticationService.

**What**: REST API endpoints `/api/auth/login` (POST) and `/api/auth/logout` (POST) with proper HTTP
status codes and OpenAPI documentation.

**Why**: Provides HTTP interface for authentication. Controller handles HTTP concerns only (
validation, status codes), business logic in service layer.

**Context**: Final piece of authentication system. Combines AUTH001-AUTH005.

## Acceptance Criteria

- [ ] **AC1**: Login endpoint:
  ```http
  POST /api/auth/login
  Content-Type: application/json

  {
    "email": "user@example.com",
    "password": "SecurePass123!"
  }
  ```

- [ ] **AC2**: Login success response (200):
  ```json
  {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": 123,
      "email": "user@example.com",
      "role": "admin",
      "is_active": true
    }
  }
  ```

- [ ] **AC3**: Login error responses:
    - Invalid credentials → 401 Unauthorized
    - Account disabled → 403 Forbidden
    - Validation error (invalid email) → 422 Unprocessable Entity

- [ ] **AC4**: Logout endpoint (protected):
  ```http
  POST /api/auth/logout
  Authorization: Bearer <access_token>
  ```

- [ ] **AC5**: OpenAPI documentation:
    - Endpoints appear in `/docs`
    - Request/response schemas documented
    - Security scheme defined (Bearer token)

## Technical Implementation Notes

### Architecture

- Layer: Presentation (Controller)
- Pattern: Thin controller (delegates to service)
- Dependencies: UserAuthenticationService

### Code Hints

**app/controllers/auth_controller.py:**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.auth_schema import LoginRequest, LoginResponse
from app.services.auth.user_authentication_service import UserAuthenticationService
from app.core.auth_middleware import get_current_user
from app.core.exceptions import (
    InvalidCredentialsException,
    AccountDisabledException
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    auth_service: UserAuthenticationService = Depends()
):
    """
    Login with email and password.

    Returns JWT tokens (access + refresh) and user data.

    **Error Codes:**
    - 401: Invalid email or password
    - 403: Account disabled
    - 422: Validation error
    """
    try:
        response = await auth_service.login(request.email, request.password)
        return response
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except AccountDisabledException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
    auth_service: UserAuthenticationService = Depends()
):
    """
    Logout current user.

    With stateless JWT, logout is client-side (delete tokens).
    This endpoint exists for future blacklist features.

    **Requires:** Valid access token in Authorization header.
    """
    await auth_service.logout(current_user.id)
    # 204 No Content (success, no body)
    return None

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.

    **Requires:** Valid access token in Authorization header.
    """
    return UserResponse.from_orm(current_user)
```

**app/main.py integration:**

```python
from fastapi import FastAPI
from app.controllers import auth_controller

app = FastAPI(
    title="DemeterAI v2.0",
    version="2.0.0",
    description="ML-powered plant inventory management"
)

# Include auth router
app.include_router(auth_controller.router)

# Security scheme for OpenAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### Testing Requirements

**Integration Tests** (`tests/api/test_auth_endpoints.py`):

- [ ] Test POST /api/auth/login with valid credentials returns 200
- [ ] Test login response includes access_token and refresh_token
- [ ] Test login with invalid email returns 401
- [ ] Test login with invalid password returns 401
- [ ] Test login with invalid email format returns 422
- [ ] Test POST /api/auth/logout requires authentication
- [ ] Test logout with valid token returns 204
- [ ] Test GET /api/auth/me returns current user

**Test Example**:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_success():
    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@demeterai.com",
            "password": "SecurePass123!"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["user"]["email"] == "admin@demeterai.com"

def test_login_invalid_credentials():
    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@demeterai.com",
            "password": "WrongPassword"
        }
    )

    assert response.status_code == 401

def test_logout_requires_auth():
    response = client.post("/api/auth/logout")
    assert response.status_code == 401

def test_logout_success(valid_token):
    headers = {"Authorization": f"Bearer {valid_token}"}
    response = client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 204

def test_get_current_user(valid_token):
    headers = {"Authorization": f"Bearer {valid_token}"}
    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert "role" in data
```

### Performance Expectations

- Login endpoint: <500ms (includes password verification)
- Logout endpoint: <50ms
- GET /me endpoint: <50ms

## Handover Briefing

**For the next developer:**

- **Context**: Final auth card, combines all previous auth work
- **Key decisions**:
    - Controllers are thin (no business logic)
    - All logic delegated to UserAuthenticationService
    - Logout returns 204 No Content (success, no body)
- **OpenAPI integration**:
    - Endpoints automatically documented at /docs
    - Bearer token security scheme defined
    - Test with Swagger UI at http://localhost:8000/docs
- **Next steps after this card**:
    - Apply get_current_user to protected routes
    - Add rate limiting to login endpoint (future)
    - Implement token blacklist for logout (future)

## Definition of Done Checklist

- [ ] Code passes all integration tests
- [ ] Login endpoint returns tokens correctly
- [ ] Logout endpoint requires authentication
- [ ] All error cases return correct HTTP status
- [ ] OpenAPI documentation complete
- [ ] Test coverage >85%
- [ ] PR approved by 2+ reviewers
- [ ] Can test endpoints via Swagger UI at /docs

## Time Tracking

- **Estimated**: 3 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
