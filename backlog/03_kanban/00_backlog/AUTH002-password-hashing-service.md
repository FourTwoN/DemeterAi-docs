# [AUTH002] Password Hashing Service

## Metadata

- **Epic**: epic-009-auth-security
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `critical` ⚡
- **Complexity**: S (3 story points)
- **Area**: `authentication`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [AUTH003, AUTH006, DB028]
    - Blocked by: [F002]

## Related Documentation

- **Engineering Plan**: ../../engineering_plan/02_technology_stack.md (Authentication section)
- **Security**: Industry standard bcrypt hashing

## Description

Create password hashing service using `passlib[bcrypt]` for secure password storage. Bcrypt is
adaptive (configurable work factor) and includes automatic salt generation.

**What**: Service for hashing passwords on registration and verifying passwords on login using
bcrypt algorithm with configurable rounds.

**Why**: Storing plaintext passwords is a critical security vulnerability. Bcrypt is
industry-standard, used by GitHub, Heroku, and most enterprise applications.

**Context**: Used by user registration (DB028) and login (AUTH003). Bcrypt work factor of 12 rounds
provides good security/performance balance.

## Acceptance Criteria

- [ ] **AC1**: `PasswordHashingService` class in `app/services/auth/password_service.py`:
  ```python
  class PasswordHashingService:
      def hash_password(self, plain_password: str) -> str
      def verify_password(self, plain_password: str, hashed_password: str) -> bool
  ```

- [ ] **AC2**: Bcrypt configuration:
    - Work factor: 12 rounds (default, ~300ms hashing time)
    - Auto-salt generation (built into bcrypt)
    - UTF-8 encoding for international characters

- [ ] **AC3**: Password validation rules:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (@$!%*?&)

- [ ] **AC4**: Password hashing produces unique hashes:
  ```python
  hash1 = service.hash_password("password123")
  hash2 = service.hash_password("password123")
  assert hash1 != hash2  # Different salts
  assert service.verify_password("password123", hash1)  # Both verify
  assert service.verify_password("password123", hash2)
  ```

- [ ] **AC5**: Error handling:
    - Weak password → `WeakPasswordException`
    - Invalid hash format → `InvalidHashException`

## Technical Implementation Notes

### Architecture

- Layer: Application (Service)
- Pattern: Stateless service (no instance state)
- Dependencies: passlib[bcrypt]==1.7.4

### Code Hints

**app/services/auth/password_service.py:**

```python
import re
from passlib.context import CryptContext
from app.core.exceptions import WeakPasswordException, InvalidHashException

class PasswordHashingService:
    def __init__(self):
        # Bcrypt context with 12 rounds (industry standard)
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12
        )

    def hash_password(self, plain_password: str) -> str:
        """
        Hash password using bcrypt.
        Each call produces different hash (different salt).

        Args:
            plain_password: Plain text password

        Returns:
            Bcrypt hash string (starts with $2b$12$...)

        Raises:
            WeakPasswordException: Password doesn't meet requirements
        """
        self._validate_password_strength(plain_password)
        return self.pwd_context.hash(plain_password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against bcrypt hash.

        Args:
            plain_password: Password to verify
            hashed_password: Bcrypt hash from database

        Returns:
            True if password matches, False otherwise
        """
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            raise InvalidHashException(f"Invalid hash format: {str(e)}")

    def _validate_password_strength(self, password: str) -> None:
        """
        Validate password meets security requirements.

        Requirements:
        - Min 8 characters
        - At least one uppercase
        - At least one lowercase
        - At least one digit
        - At least one special character (@$!%*?&)
        """
        if len(password) < 8:
            raise WeakPasswordException(
                "Password must be at least 8 characters"
            )

        if not re.search(r'[A-Z]', password):
            raise WeakPasswordException(
                "Password must contain at least one uppercase letter"
            )

        if not re.search(r'[a-z]', password):
            raise WeakPasswordException(
                "Password must contain at least one lowercase letter"
            )

        if not re.search(r'\d', password):
            raise WeakPasswordException(
                "Password must contain at least one digit"
            )

        if not re.search(r'[@$!%*?&]', password):
            raise WeakPasswordException(
                "Password must contain at least one special character (@$!%*?&)"
            )
```

**app/core/exceptions.py additions:**

```python
class WeakPasswordException(AppBaseException):
    def __init__(self, message: str):
        super().__init__(
            technical_message=message,
            user_message=message,
            code=400
        )

class InvalidHashException(AppBaseException):
    def __init__(self, message: str):
        super().__init__(
            technical_message=message,
            user_message="Invalid password hash format",
            code=500
        )
```

### Testing Requirements

**Unit Tests** (`tests/services/auth/test_password_service.py`):

- [ ] Test hash_password produces valid bcrypt hash
- [ ] Test same password produces different hashes (salting)
- [ ] Test verify_password accepts correct password
- [ ] Test verify_password rejects incorrect password
- [ ] Test weak password validation (each rule)
- [ ] Test invalid hash format raises exception
- [ ] Test unicode password support

**Test Example**:

```python
import pytest
from app.services.auth.password_service import PasswordHashingService
from app.core.exceptions import WeakPasswordException

def test_hash_and_verify_password():
    service = PasswordHashingService()
    plain_password = "SecurePass123!"

    hashed = service.hash_password(plain_password)

    # Hash should start with bcrypt prefix
    assert hashed.startswith("$2b$12$")

    # Correct password verifies
    assert service.verify_password(plain_password, hashed)

    # Wrong password fails
    assert not service.verify_password("WrongPass123!", hashed)

def test_same_password_different_hashes():
    service = PasswordHashingService()
    password = "SecurePass123!"

    hash1 = service.hash_password(password)
    hash2 = service.hash_password(password)

    # Different hashes (different salts)
    assert hash1 != hash2

    # Both verify
    assert service.verify_password(password, hash1)
    assert service.verify_password(password, hash2)

@pytest.mark.parametrize("weak_password", [
    "short",           # Too short
    "nouppercase123!", # No uppercase
    "NOLOWERCASE123!", # No lowercase
    "NoDigits!@#",     # No digit
    "NoSpecial123",    # No special char
])
def test_weak_password_rejected(weak_password):
    service = PasswordHashingService()

    with pytest.raises(WeakPasswordException):
        service.hash_password(weak_password)
```

### Performance Expectations

- Password hashing: ~300ms (bcrypt with 12 rounds)
- Password verification: ~300ms
- Note: Intentionally slow to prevent brute force attacks

## Handover Briefing

**For the next developer:**

- **Context**: Bcrypt is intentionally slow (~300ms) to prevent brute force
- **Key decisions**:
    - 12 rounds work factor (standard, good security/performance balance)
    - Auto-salt generation (bcrypt handles this internally)
    - Strong password validation (8 chars, upper, lower, digit, special)
- **Why not argon2?**:
    - Bcrypt is more widely supported and battle-tested
    - Argon2 is slightly better but adds complexity
- **Security best practices**:
    - Never log passwords (even hashed)
    - Never return password hashes in API responses
    - Force password change after 90 days (optional, future feature)
- **Known limitations**:
    - 72-byte bcrypt password limit (not an issue for normal use)
    - Solution: Pre-hash with SHA256 if storing >72 bytes needed
- **Next steps after this card**:
    - AUTH003: User authentication service (uses this for login)
    - DB028: Users model (stores hashed passwords)

## Definition of Done Checklist

- [ ] Code passes all unit tests (pytest)
- [ ] Password hashing and verification work correctly
- [ ] Same password produces different hashes (salting verified)
- [ ] All password strength rules enforced
- [ ] Bcrypt 12 rounds configuration
- [ ] Test coverage >90%
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated (security best practices)
- [ ] No plaintext passwords in logs or responses

## Time Tracking

- **Estimated**: 3 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
