"""
Password Security Utilities

Provides password hashing and verification using bcrypt.

Security Features:
- bcrypt with cost factor 12 (2^12 = 4096 iterations)
- Password strength validation
- Constant-time comparison
- No plaintext password storage

Usage:
    from app.core.security import hash_password, verify_password

    # Hash password
    hashed = hash_password("SecurePass123!")

    # Verify password
    is_valid = verify_password("SecurePass123!", hashed)  # True
"""

import re
from typing import TYPE_CHECKING, Any

import bcrypt  # type: ignore[import-not-found]

if TYPE_CHECKING:
    pass

# Password strength requirements
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 72  # bcrypt max byte length
BCRYPT_COST_FACTOR = 12  # 2^12 = 4096 rounds (recommended for 2025)


def is_password_valid(password: str) -> tuple[bool, str | None]:
    """
    Validate password meets strength requirements.

    Requirements:
    - Minimum 12 characters
    - Maximum 72 characters (bcrypt limit)
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character (@$!%*?&#^()_-+=[]{}|\\:";'<>,.~/`)

    Args:
        password: Plain text password to validate

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, "error message") if invalid

    Example:
        >>> is_password_valid("weak")
        (False, "Password must be at least 12 characters long")
        >>> is_password_valid("SecurePass123!")
        (True, None)
    """
    if not password:
        return False, "Password cannot be empty"

    if len(password) < PASSWORD_MIN_LENGTH:
        return (False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")

    if len(password) > PASSWORD_MAX_LENGTH:
        return (False, f"Password must not exceed {PASSWORD_MAX_LENGTH} characters")

    # Check byte length (bcrypt limit is 72 bytes, not characters)
    if len(password.encode("utf-8")) > PASSWORD_MAX_LENGTH:
        return (False, f"Password must not exceed {PASSWORD_MAX_LENGTH} bytes when UTF-8 encoded")

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    if not re.search(r'[@$!%*?&#^()_\-+=\[\]{}|\\:";\'<>,.~/`]', password):
        return False, "Password must contain at least one special character"

    return True, None


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Uses bcrypt with cost factor 12 (4096 rounds) for secure hashing.
    The hash includes salt and algorithm metadata.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string (bcrypt format: $2b$12$...)

    Raises:
        ValueError: If password doesn't meet strength requirements

    Example:
        >>> hashed = hash_password("SecurePass123!")
        >>> hashed.startswith("$2b$12$")
        True
    """
    # Validate password strength
    is_valid, error_msg = is_password_valid(password)
    if not is_valid:
        raise ValueError(f"Invalid password: {error_msg}")

    # Encode password to bytes
    password_bytes = password.encode("utf-8")

    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=BCRYPT_COST_FACTOR)
    hashed: bytes = bcrypt.hashpw(password_bytes, salt)

    # Return as string
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Previously hashed password to compare against

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("SecurePass123!")
        >>> verify_password("SecurePass123!", hashed)
        True
        >>> verify_password("WrongPassword", hashed)
        False
    """
    try:
        # Encode inputs to bytes
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")

        # Verify with constant-time comparison
        result: bool = bcrypt.checkpw(password_bytes, hashed_bytes)
        return result
    except Exception:
        # Invalid hash format or verification error
        return False


def needs_rehash(hashed_password: str, rounds: int = BCRYPT_COST_FACTOR) -> bool:
    """
    Check if a hashed password needs to be rehashed.

    This happens when the hash uses a lower cost factor than specified.

    Args:
        hashed_password: Previously hashed password
        rounds: Desired cost factor (default: 12)

    Returns:
        True if password should be rehashed, False otherwise

    Example:
        >>> hashed = hash_password("SecurePass123!")
        >>> needs_rehash(hashed)
        False
    """
    try:
        # Extract cost factor from hash
        # Format: $2b$12$...
        parts = hashed_password.split("$")
        if len(parts) < 4:
            return True  # Invalid format

        current_rounds = int(parts[2])
        return current_rounds < rounds
    except Exception:
        # Invalid hash format
        return True


def get_password_requirements() -> dict[str, Any]:
    """
    Get password requirements for client-side validation.

    Returns:
        Dictionary with password requirements:
        - min_length: Minimum password length
        - max_length: Maximum password length
        - require_uppercase: Requires uppercase letter
        - require_lowercase: Requires lowercase letter
        - require_digit: Requires digit
        - require_special: Requires special character
        - special_chars: List of allowed special characters

    Example:
        >>> reqs = get_password_requirements()
        >>> reqs['min_length']
        12
    """
    return {
        "min_length": PASSWORD_MIN_LENGTH,
        "max_length": PASSWORD_MAX_LENGTH,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_digit": True,
        "require_special": True,
        "special_chars": "@$!%*?&#^()_-+=[]{}|\\:\";'<>,.~/`",
        "cost_factor": BCRYPT_COST_FACTOR,
    }
