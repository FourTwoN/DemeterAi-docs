# [DEP004] Docker & Kubernetes Health Checks

## Metadata
- **Epic**: epic-011-deployment
- **Sprint**: Sprint-06
- **Priority**: `high`
- **Complexity**: S (3 points)
- **Dependencies**: Blocked by [OBS007, OBS008]

## Description
Configure health checks for Docker and Kubernetes: liveness (is process alive?) and readiness (can accept traffic?).

## Acceptance Criteria
- [ ] Docker HEALTHCHECK in Dockerfile
- [ ] Kubernetes liveness probe (GET /health)
- [ ] Kubernetes readiness probe (GET /ready)
- [ ] Unhealthy containers restarted automatically
- [ ] New pods don't receive traffic until ready

## Implementation
**Docker (Dockerfile):**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

**Kubernetes (deployment.yaml):**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3
```

## Testing
- Docker: `docker ps` shows "healthy" status
- Kubernetes: `kubectl get pods` shows "Running" + "1/1 Ready"
- Simulate failure (stop DB) → pod marked NotReady

---
**Card Created**: 2025-10-09
