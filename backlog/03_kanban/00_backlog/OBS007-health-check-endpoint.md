# [OBS007] Health Check Endpoint

## Metadata
- **Epic**: epic-010-observability
- **Sprint**: Sprint-06
- **Priority**: `critical` ⚡
- **Complexity**: S (2 points)
- **Dependencies**: Blocked by [F001]

## Description
Implement `/health` endpoint for liveness checks (Docker, Kubernetes). Returns 200 if service is running.

## Acceptance Criteria
- [ ] GET /health returns 200 OK
- [ ] Response includes service status, version
- [ ] No authentication required (public endpoint)
- [ ] Response time <50ms

## Implementation
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "demeterai-api",
        "version": "2.0.0"
    }
```

**docker-compose.yml integration:**
```yaml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Testing
- Test GET /health returns 200
- Test Docker healthcheck passes
- Test Kubernetes liveness probe

---
**Card Created**: 2025-10-09
