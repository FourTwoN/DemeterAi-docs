# [OBS008] Readiness Check Endpoint

## Metadata
- **Epic**: epic-010-observability
- **Sprint**: Sprint-06
- **Priority**: `high`
- **Complexity**: S (3 points)
- **Dependencies**: Blocked by [F006, CEL002]

## Description
Implement `/ready` endpoint for readiness checks. Verifies database and Redis connectivity before accepting traffic.

## Acceptance Criteria
- [ ] GET /ready returns 200 if all dependencies healthy
- [ ] Returns 503 if database unreachable
- [ ] Returns 503 if Redis unreachable
- [ ] Checks run in parallel (fast response)
- [ ] Response includes status of each dependency

## Implementation
```python
@router.get("/ready")
async def readiness():
    checks = {
        "database": await check_database(),
        "redis": await check_redis()
    }

    all_healthy = all(checks.values())

    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content={
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks
        }
    )

async def check_database():
    try:
        await session.execute(text("SELECT 1"))
        return True
    except:
        return False
```

**Kubernetes deployment:**
```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

## Testing
- Test /ready returns 200 when healthy
- Test /ready returns 503 when DB down
- Test parallel checks complete in <100ms

---
**Card Created**: 2025-10-09
