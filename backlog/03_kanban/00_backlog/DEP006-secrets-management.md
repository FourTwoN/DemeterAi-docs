# [DEP006] Secrets Management

## Metadata
- **Epic**: epic-011-deployment
- **Sprint**: Sprint-07
- **Priority**: `critical` ⚡
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [DEP005]

## Description
Implement secure secrets management using Docker secrets (Swarm) or Kubernetes secrets. Never commit secrets to git.

## Acceptance Criteria
- [ ] .env excluded from git (.gitignore)
- [ ] .env.example template (safe values)
- [ ] Docker secrets integration (Docker Swarm)
- [ ] Kubernetes secrets integration (K8s)
- [ ] AWS Secrets Manager integration (production)
- [ ] Secrets rotated every 90 days (documented process)

## Implementation
**Docker Secrets (docker-compose.yml):**
```yaml
secrets:
  db_password:
    external: true
  jwt_secret:
    external: true

services:
  api:
    secrets:
      - db_password
      - jwt_secret
    environment:
      DATABASE_PASSWORD_FILE: /run/secrets/db_password
      JWT_SECRET_FILE: /run/secrets/jwt_secret
```

**Kubernetes Secrets:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: demeterai-secrets
type: Opaque
data:
  db-password: <base64>
  jwt-secret: <base64>
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: api
        env:
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: demeterai-secrets
              key: db-password
```

**AWS Secrets Manager (production):**
```python
import boto3

def load_secrets():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='demeterai/production')
    secrets = json.loads(response['SecretString'])
    return secrets
```

## Testing
- Verify secrets not in git history
- Test app reads Docker secrets correctly
- Test Kubernetes secrets mounted as env vars
- Test AWS Secrets Manager integration

---
**Card Created**: 2025-10-09
