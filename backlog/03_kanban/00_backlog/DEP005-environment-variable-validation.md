# [DEP005] Environment Variable Validation

## Metadata

- **Epic**: epic-011-deployment
- **Sprint**: Sprint-01
- **Priority**: `high`
- **Complexity**: S (3 points)
- **Dependencies**: Blocked by [F002]

## Description

Use pydantic-settings for environment variable validation. App fails fast on startup if required
config missing.

## Acceptance Criteria

- [ ] All config in `app/core/config.py` using pydantic-settings
- [ ] Required fields validated (e.g., DATABASE_URL, JWT_SECRET_KEY)
- [ ] Type validation (int, bool, URL)
- [ ] Default values for optional config
- [ ] Clear error messages for missing/invalid config

## Implementation

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Database (required)
    DATABASE_URL: PostgresDsn
    DATABASE_URL_SYNC: PostgresDsn

    # Redis (required)
    REDIS_URL: RedisDsn

    # JWT (required, min 32 chars)
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"

    # AWS S3 (required)
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_S3_BUCKET: str

    # Optional with defaults
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    WORKERS: int = 4

settings = Settings()
```

## Testing

- Test missing DATABASE_URL raises ValidationError
- Test invalid REDIS_URL format raises error
- Test JWT_SECRET_KEY <32 chars raises error
- Test default values applied correctly

---
**Card Created**: 2025-10-09
