# [DEP008] Container Orchestration (Docker Swarm/K8s)

## Metadata
- **Epic**: epic-011-deployment
- **Sprint**: Sprint-08
- **Priority**: `medium`
- **Complexity**: L (8 points)
- **Dependencies**: Blocked by [DEP002, DEP004]

## Description
Deploy to production orchestration platform: Docker Swarm (simpler) or Kubernetes (enterprise-grade).

## Acceptance Criteria
- [ ] Choose orchestration: Docker Swarm OR Kubernetes
- [ ] Multi-node cluster (min 3 nodes)
- [ ] API replicas: 2-4 instances
- [ ] GPU workers: 1 per GPU (pool=solo)
- [ ] Auto-restart on failure
- [ ] Rolling updates (zero downtime)
- [ ] Resource limits (CPU, memory)

## Implementation

**Option A: Docker Swarm (simpler)**
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml demeterai

# Scale API
docker service scale demeterai_api=4
```

**docker-compose.yml additions:**
```yaml
services:
  api:
    deploy:
      replicas: 4
      update_config:
        parallelism: 2
        delay: 10s
      restart_policy:
        condition: on-failure
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

**Option B: Kubernetes (production-grade)**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demeterai-api
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: api
        image: demeterai:latest
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
          requests:
            cpu: "1"
            memory: "1Gi"
```

## Testing
- Deploy to cluster
- Test API accessible via load balancer
- Test rolling update (no downtime)
- Test pod auto-restart on failure
- Test resource limits enforced

---
**Card Created**: 2025-10-09
