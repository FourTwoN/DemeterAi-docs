# [C026] Login Endpoint - POST /api/auth/login

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02 (Week 5-6)
- **Status**: `backlog`
- **Priority**: `critical` (authentication foundation)
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [SCH009, SCH019]
    - Blocked by: [SVC012-user-service, DB028-users-model]

## Description

JWT-based login endpoint (email + password).

## Acceptance Criteria

- [ ] **AC1**: Request body: email, password
- [ ] **AC2**: Validate credentials (bcrypt password check)
- [ ] **AC3**: Return JWT access_token + refresh_token
- [ ] **AC4**: Token expiration: 15 min (access), 7 days (refresh)

```python
from app.services.auth_service import AuthService
from app.schemas.auth_schema import LoginRequest, AuthTokenResponse

@router.post("/auth/login", response_model=AuthTokenResponse)
async def login(
    request: LoginRequest,
    service: AuthService = Depends()
):
    """Login with email and password."""
    user = await service.authenticate(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    tokens = await service.create_tokens(user)

    return AuthTokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type="bearer",
        expires_in=900  # 15 minutes
    )
```

**Coverage Target**: ≥90%

## Time Tracking

- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
