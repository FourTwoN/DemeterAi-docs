# [AUTH005] Refresh Token Logic

## Metadata

- **Epic**: epic-009-auth-security
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: S (3 story points)
- **Area**: `authentication`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [AUTH006]
    - Blocked by: [AUTH001, AUTH003]

## Related Documentation

- **Engineering Plan**: ../../engineering_plan/02_technology_stack.md
- **JWT Best Practices**: OAuth2 refresh token pattern

## Description

Implement refresh token rotation logic for extending user sessions without requiring re-login.
Access tokens expire in 15 minutes, refresh tokens in 7 days.

**What**: Endpoint `/api/auth/refresh` that accepts refresh token and returns new access token.
Optionally implements token rotation (issue new refresh token on each use).

**Why**: Short-lived access tokens (15 min) improve security. Refresh tokens allow users to stay
logged in for 7 days without re-entering credentials.

**Context**: Part of AUTH003 (user authentication service) but separated for clarity.

## Acceptance Criteria

- [ ] **AC1**: Refresh token endpoint accepts refresh token:
  ```http
  POST /api/auth/refresh
  Content-Type: application/json

  {
    "refresh_token": "eyJ..."
  }
  ```

- [ ] **AC2**: Response contains new access token:
  ```json
  {
    "access_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 900
  }
  ```

- [ ] **AC3**: Token rotation (security best practice):
    - Option A (simple): Return only new access token
    - Option B (secure): Return new access + new refresh token, invalidate old refresh
    - Implement Option A first (stateless), Option B requires token blacklist

- [ ] **AC4**: Validation rules:
    - Refresh token must not be expired
    - Token type must be "refresh" (not "access")
    - User from token must still be active

- [ ] **AC5**: Error handling:
    - Expired refresh token → 401 "Refresh token expired, please login"
    - Invalid token → 401 "Invalid refresh token"
    - User disabled → 403 "Account disabled"

## Technical Implementation Notes

### Architecture

- Layer: Application (Service) + Presentation (Controller)
- Integration: AUTH001 (JWT), AUTH003 (auth service)
- Pattern: Token refresh flow

### Code Hints

**Already implemented in AUTH003, add to controller:**

```python
# app/controllers/auth_controller.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.auth_schema import RefreshTokenRequest, TokenPair
from app.services.auth.user_authentication_service import UserAuthenticationService

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/refresh", response_model=TokenPair)
async def refresh_access_token(
    request: RefreshTokenRequest,
    auth_service: UserAuthenticationService = Depends()
):
    """
    Generate new access token from refresh token.

    Returns new access token (15 min expiration).
    Does NOT rotate refresh token (stateless approach).
    """
    try:
        token_pair = await auth_service.refresh_token(request.refresh_token)
        return token_pair
    except JWTExpiredException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired, please login again"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
```

**app/schemas/auth_schema.py additions:**

```python
from pydantic import BaseModel

class RefreshTokenRequest(BaseModel):
    refresh_token: str
```

**Future: Token rotation with blacklist (Option B):**

```python
# Requires Redis blacklist or database token table
async def refresh_token_with_rotation(self, old_refresh_token: str) -> LoginResponse:
    """
    Token rotation: Issue new refresh token and blacklist old one.
    """
    # Decode old refresh token
    payload = self.jwt_service.decode_token(old_refresh_token)
    user_id = payload["sub"]

    # Blacklist old refresh token (store in Redis)
    await self.redis_client.set(
        f"blacklist:{old_refresh_token}",
        "revoked",
        ex=7*24*60*60  # 7 days
    )

    # Generate new tokens
    user = await self.user_repo.get(user_id)
    access_token = self.jwt_service.encode_access_token(...)
    new_refresh_token = self.jwt_service.encode_refresh_token(user_id)

    return LoginResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        ...
    )
```

### Testing Requirements

**Integration Tests** (`tests/api/test_auth_endpoints.py`):

- [ ] Test POST /api/auth/refresh with valid refresh token
- [ ] Test returns new access token
- [ ] Test expired refresh token returns 401
- [ ] Test access token (not refresh token) returns 401
- [ ] Test refresh token for disabled user returns 403

**Test Example**:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_refresh_token_success(valid_refresh_token):
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": valid_refresh_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 900

def test_refresh_with_expired_token(expired_refresh_token):
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": expired_refresh_token}
    )

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()

def test_refresh_with_access_token(valid_access_token):
    # Should fail - access tokens can't be used for refresh
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": valid_access_token}
    )

    assert response.status_code == 401
```

### Performance Expectations

- Refresh token endpoint: <50ms
- Token generation: <5ms
- User lookup: <20ms

## Handover Briefing

**For the next developer:**

- **Context**: Refresh tokens extend sessions without re-login
- **Key decisions**:
    - Simple approach: Don't rotate refresh token (stateless)
    - Secure approach: Rotate + blacklist (requires Redis, future feature)
    - Access tokens short-lived (15 min), refresh tokens 7 days
- **Security trade-offs**:
    - Stateless = no revocation (if refresh token stolen, valid until expiry)
    - Solution: Keep refresh token expiry short (7 days)
    - Future: Implement token blacklist in Redis
- **User experience**:
    - Client should refresh access token when it expires
    - If refresh token expired, redirect to login
- **Next steps after this card**:
    - AUTH006: Complete login/logout endpoints
    - Future: Token rotation with Redis blacklist

## Definition of Done Checklist

- [ ] Code passes all integration tests
- [ ] POST /api/auth/refresh endpoint works
- [ ] Returns new access token from valid refresh token
- [ ] Error cases handled correctly
- [ ] Test coverage >80%
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated with refresh flow
- [ ] OpenAPI docs generated automatically

## Time Tracking

- **Estimated**: 3 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
