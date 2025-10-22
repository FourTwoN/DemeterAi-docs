# [AUTH003] User Authentication Service

## Metadata

- **Epic**: epic-009-auth-security
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `critical` ⚡
- **Complexity**: M (5 story points)
- **Area**: `authentication`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [AUTH006]
    - Blocked by: [AUTH001, AUTH002, DB028, R001]

## Related Documentation

- **Engineering Plan**: ../../engineering_plan/03_architecture_overview.md
- **Database**: ../../database/database.md (users table)

## Description

Create user authentication service handling login, logout, and token refresh. Orchestrates JWT token
generation, password verification, and user lookup.

**What**: Service layer implementing login (email/password) and logout logic, returning JWT tokens
for authenticated sessions.

**Why**: Centralizes authentication business logic, separating it from HTTP concerns (controllers)
and data access (repositories).

**Context**: Works with AUTH001 (JWT), AUTH002 (passwords), and DB028 (user model).

## Acceptance Criteria

- [ ] **AC1**: `UserAuthenticationService` class in
  `app/services/auth/user_authentication_service.py`:
  ```python
  class UserAuthenticationService:
      async def login(self, email: str, password: str) -> LoginResponse
      async def logout(self, user_id: int) -> bool
      async def refresh_token(self, refresh_token: str) -> TokenPair
  ```

- [ ] **AC2**: Login flow:
    1. Look up user by email (via UserRepository)
    2. Verify password (via PasswordHashingService)
    3. Generate access + refresh tokens (via JWTService)
    4. Return LoginResponse with tokens and user data

- [ ] **AC3**: LoginResponse schema:
  ```python
  class LoginResponse(BaseModel):
      access_token: str
      refresh_token: str
      token_type: str = "Bearer"
      expires_in: int = 900  # 15 min in seconds
      user: UserResponse
  ```

- [ ] **AC4**: Error handling:
    - User not found → `UserNotFoundException` (404)
    - Invalid password → `InvalidCredentialsException` (401)
    - Account disabled → `AccountDisabledException` (403)

- [ ] **AC5**: Security features:
    - Failed login attempts logged (for rate limiting future)
    - No indication whether email or password was wrong (security)
    - Timing attack prevention (constant-time comparison)

## Technical Implementation Notes

### Architecture

- Layer: Application (Service)
- Dependencies: UserRepository, JWTService, PasswordHashingService
- Pattern: Service orchestration (calls multiple services)

### Code Hints

**app/services/auth/user_authentication_service.py:**

```python
from app.repositories.user_repository import UserRepository
from app.services.auth.jwt_service import JWTService
from app.services.auth.password_service import PasswordHashingService
from app.schemas.auth_schema import LoginRequest, LoginResponse, TokenPair
from app.core.exceptions import (
    UserNotFoundException,
    InvalidCredentialsException,
    AccountDisabledException
)
import logging

logger = logging.getLogger(__name__)

class UserAuthenticationService:
    def __init__(
        self,
        user_repo: UserRepository,
        jwt_service: JWTService,
        password_service: PasswordHashingService
    ):
        self.user_repo = user_repo
        self.jwt_service = jwt_service
        self.password_service = password_service

    async def login(self, email: str, password: str) -> LoginResponse:
        """
        Authenticate user and generate JWT tokens.

        Args:
            email: User email
            password: Plain text password

        Returns:
            LoginResponse with tokens and user data

        Raises:
            InvalidCredentialsException: Email or password incorrect
            AccountDisabledException: User account disabled
        """
        # 1. Look up user by email
        user = await self.user_repo.get_by_email(email)
        if not user:
            logger.warning(f"Login attempt for non-existent email: {email}")
            raise InvalidCredentialsException("Invalid email or password")

        # 2. Check if account is active
        if not user.is_active:
            logger.warning(f"Login attempt for disabled account: {email}")
            raise AccountDisabledException("Account is disabled")

        # 3. Verify password
        if not self.password_service.verify_password(password, user.hashed_password):
            logger.warning(f"Invalid password for user: {email}")
            raise InvalidCredentialsException("Invalid email or password")

        # 4. Generate tokens
        access_token = self.jwt_service.encode_access_token(
            user_id=user.id,
            role=user.role,
            email=user.email
        )
        refresh_token = self.jwt_service.encode_refresh_token(user_id=user.id)

        logger.info(f"User logged in successfully: {email}")

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=900,  # 15 minutes
            user=UserResponse.from_orm(user)
        )

    async def logout(self, user_id: int) -> bool:
        """
        Logout user (stateless JWT - no server-side action needed).

        Note: With stateless JWT, logout is client-side (delete tokens).
        This method exists for future blacklist/revocation features.

        Args:
            user_id: User identifier

        Returns:
            True (always succeeds)
        """
        logger.info(f"User logged out: {user_id}")
        return True

    async def refresh_token(self, refresh_token: str) -> TokenPair:
        """
        Generate new access token from refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            TokenPair with new access token

        Raises:
            JWTExpiredException: Refresh token expired
            JWTException: Invalid refresh token
        """
        # Decode refresh token
        payload = self.jwt_service.decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise JWTException("Not a refresh token")

        user_id = payload["sub"]

        # Look up user (ensure still active)
        user = await self.user_repo.get(user_id)
        if not user or not user.is_active:
            raise InvalidCredentialsException("User account not found or disabled")

        # Generate new access token
        access_token = self.jwt_service.encode_access_token(
            user_id=user.id,
            role=user.role,
            email=user.email
        )

        return TokenPair(
            access_token=access_token,
            token_type="Bearer",
            expires_in=900
        )
```

**app/schemas/auth_schema.py:**

```python
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenPair(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int

class LoginResponse(TokenPair):
    refresh_token: str
    user: UserResponse
```

### Testing Requirements

**Unit Tests** (`tests/services/auth/test_user_authentication_service.py`):

- [ ] Test successful login returns tokens
- [ ] Test invalid email raises InvalidCredentialsException
- [ ] Test invalid password raises InvalidCredentialsException
- [ ] Test disabled account raises AccountDisabledException
- [ ] Test refresh_token generates new access token
- [ ] Test expired refresh token raises exception
- [ ] Test logout always succeeds

**Test Example**:

```python
import pytest
from app.services.auth.user_authentication_service import UserAuthenticationService
from app.core.exceptions import InvalidCredentialsException

@pytest.fixture
async def auth_service(mock_user_repo, jwt_service, password_service):
    return UserAuthenticationService(
        user_repo=mock_user_repo,
        jwt_service=jwt_service,
        password_service=password_service
    )

async def test_successful_login(auth_service, mock_user_repo):
    # Mock user with correct password hash
    mock_user_repo.get_by_email.return_value = User(
        id=123,
        email="test@example.com",
        hashed_password="$2b$12$...",  # Hash of "password123"
        role="admin",
        is_active=True
    )

    response = await auth_service.login("test@example.com", "password123")

    assert response.access_token is not None
    assert response.refresh_token is not None
    assert response.user.email == "test@example.com"

async def test_invalid_email(auth_service, mock_user_repo):
    mock_user_repo.get_by_email.return_value = None

    with pytest.raises(InvalidCredentialsException):
        await auth_service.login("wrong@example.com", "password123")

async def test_invalid_password(auth_service, mock_user_repo):
    mock_user_repo.get_by_email.return_value = User(
        id=123,
        email="test@example.com",
        hashed_password="$2b$12$...",
        is_active=True
    )

    with pytest.raises(InvalidCredentialsException):
        await auth_service.login("test@example.com", "wrongpassword")
```

### Performance Expectations

- Login: <500ms (including bcrypt verification ~300ms)
- Refresh token: <50ms
- Logout: <10ms

## Handover Briefing

**For the next developer:**

- **Context**: Service layer orchestrates multiple services (JWT, password, user repo)
- **Key decisions**:
    - Generic error message for security (don't reveal if email or password wrong)
    - Logout is no-op with stateless JWT (client deletes tokens)
    - Refresh token flow generates NEW access token from refresh token
- **Security considerations**:
    - Log failed login attempts (future: rate limiting)
    - Check user.is_active before granting tokens
    - Don't return different errors for email vs password (timing attacks)
- **Next steps after this card**:
    - AUTH004: Authorization middleware (protect routes)
    - AUTH006: Login/logout endpoints (controller layer)

## Definition of Done Checklist

- [ ] Code passes all unit tests (pytest)
- [ ] Login flow works end-to-end
- [ ] Refresh token generates new access token
- [ ] All error cases handled correctly
- [ ] Failed logins logged (security audit trail)
- [ ] Test coverage >85%
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated
- [ ] No passwords logged in plaintext

## Time Tracking

- **Estimated**: 5 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
