# [AUTH001] JWT Token Service

## Metadata

- **Epic**: epic-009-auth-security
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `critical` ⚡
- **Complexity**: M (5 story points)
- **Area**: `authentication`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [AUTH003, AUTH004, AUTH005, AUTH006]
    - Blocked by: [F002, F005]

## Related Documentation

- **Engineering Plan**: ../../engineering_plan/02_technology_stack.md (Authentication section)
- **Architecture**: ../../engineering_plan/03_architecture_overview.md

## Description

Create JWT (JSON Web Token) token service for secure authentication using
`python-jose[cryptography]` library. Support both HS256 (symmetric) and RS256 (asymmetric) signing
algorithms with configurable token expiration.

**What**: Service for encoding/decoding JWT tokens with user claims (user_id, role, email), token
expiration handling, and signature verification.

**Why**: Stateless authentication is essential for scalable APIs. JWT eliminates need for session
storage and enables horizontal scaling of API servers.

**Context**: This is the foundation for all authentication features. Access tokens expire in 15
minutes, refresh tokens in 7 days (AUTH005).

## Acceptance Criteria

- [ ] **AC1**: `JWTService` class in `app/services/auth/jwt_service.py`:
  ```python
  class JWTService:
      def encode_token(self, user_id: int, role: str, email: str) -> str
      def decode_token(self, token: str) -> dict
      def verify_token(self, token: str) -> bool
  ```

- [ ] **AC2**: Token payload structure:
  ```python
  {
      "sub": user_id,           # subject (user identifier)
      "role": "admin",          # user role
      "email": "user@example.com",
      "iat": 1696800000,        # issued at (Unix timestamp)
      "exp": 1696800900,        # expiration (15 min later)
      "type": "access"          # token type (access|refresh)
  }
  ```

- [ ] **AC3**: Configuration via environment variables:
  ```env
  JWT_SECRET_KEY=your_secret_key_min_32_chars
  JWT_ALGORITHM=HS256              # or RS256
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
  JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
  ```

- [ ] **AC4**: Support both algorithms:
    - **HS256** (symmetric): Single secret key (default for development)
    - **RS256** (asymmetric): Public/private key pair (production recommended)

- [ ] **AC5**: Error handling for:
    - Invalid signature → `JWTInvalidSignatureException`
    - Expired token → `JWTExpiredException`
    - Malformed token → `JWTDecodeException`

## Technical Implementation Notes

### Architecture

- Layer: Application (Service)
- Pattern: Singleton service (single instance per app)
- Dependencies: python-jose==3.3.0

### Code Hints

**app/services/auth/jwt_service.py:**

```python
from datetime import datetime, timedelta
from jose import jwt, JWTError, ExpiredSignatureError
from app.core.config import settings
from app.core.exceptions import JWTException, JWTExpiredException

class JWTService:
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    def encode_access_token(self, user_id: int, role: str, email: str) -> str:
        """Generate access token (15 min expiration)"""
        payload = {
            "sub": user_id,
            "role": role,
            "email": email,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=self.access_token_expire),
            "type": "access"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def encode_refresh_token(self, user_id: int) -> str:
        """Generate refresh token (7 day expiration)"""
        payload = {
            "sub": user_id,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(days=self.refresh_token_expire_days),
            "type": "refresh"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict:
        """Decode and verify token"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except ExpiredSignatureError:
            raise JWTExpiredException("Token has expired")
        except JWTError as e:
            raise JWTException(f"Invalid token: {str(e)}")

    def verify_token(self, token: str) -> bool:
        """Verify token without raising exceptions"""
        try:
            self.decode_token(token)
            return True
        except:
            return False
```

**app/core/config.py additions:**

```python
class Settings(BaseSettings):
    # JWT Configuration
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"
```

### Testing Requirements

**Unit Tests** (`tests/services/auth/test_jwt_service.py`):

- [ ] Test encode_access_token creates valid token
- [ ] Test decode_token extracts correct payload
- [ ] Test expired token raises JWTExpiredException
- [ ] Test invalid signature raises exception
- [ ] Test malformed token raises exception
- [ ] Test refresh token has longer expiration
- [ ] Test token type field ("access" vs "refresh")

**Test Example**:

```python
import pytest
from datetime import datetime, timedelta
from app.services.auth.jwt_service import JWTService
from app.core.exceptions import JWTExpiredException

def test_encode_decode_access_token():
    jwt_service = JWTService()
    token = jwt_service.encode_access_token(
        user_id=123,
        role="admin",
        email="test@example.com"
    )

    payload = jwt_service.decode_token(token)
    assert payload["sub"] == 123
    assert payload["role"] == "admin"
    assert payload["email"] == "test@example.com"
    assert payload["type"] == "access"

def test_expired_token_raises_exception(monkeypatch):
    jwt_service = JWTService()
    # Force immediate expiration
    monkeypatch.setattr(jwt_service, "access_token_expire", 0)

    token = jwt_service.encode_access_token(123, "admin", "test@example.com")

    with pytest.raises(JWTExpiredException):
        jwt_service.decode_token(token)
```

### Performance Expectations

- Token encoding: <5ms
- Token decoding: <3ms
- Token verification: <3ms

## Handover Briefing

**For the next developer:**

- **Context**: JWT enables stateless authentication (no session storage needed)
- **Key decisions**:
    - Using HS256 by default (simpler for development)
    - RS256 support for production (separate public/private keys)
    - 15-minute access tokens (security best practice)
    - 7-day refresh tokens (user convenience)
- **Known limitations**:
    - No token revocation (stateless = can't invalidate before expiration)
    - Solution: Keep access token expiration short (15 min)
- **Security considerations**:
    - Secret key MUST be 32+ characters
    - Never commit JWT_SECRET_KEY to git
    - Rotate secret every 90 days in production
- **Next steps after this card**:
    - AUTH002: Password hashing
    - AUTH003: User authentication service (login)
    - AUTH004: Authorization middleware (role checks)

## Definition of Done Checklist

- [ ] Code passes all unit tests (pytest)
- [ ] JWT token encoding/decoding works correctly
- [ ] All three algorithms supported (HS256, RS256)
- [ ] Error handling for expired/invalid tokens
- [ ] Configuration loaded from environment variables
- [ ] Test coverage >80%
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated (docstrings for all methods)
- [ ] No hardcoded secrets in code

## Time Tracking

- **Estimated**: 5 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
