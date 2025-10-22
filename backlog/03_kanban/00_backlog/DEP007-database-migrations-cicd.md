# [DEP007] Database Migrations CI/CD

## Metadata

- **Epic**: epic-011-deployment
- **Sprint**: Sprint-03
- **Priority**: `high`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [F007, DEP011]

## Description

Automate Alembic migrations in CI/CD pipeline. Run migrations before deploying new code.

## Acceptance Criteria

- [ ] Migrations run automatically on deploy
- [ ] Rollback strategy for failed migrations
- [ ] Dry-run mode for testing migrations
- [ ] Lock mechanism (prevent concurrent migrations)
- [ ] Migration success logged and monitored

## Implementation

**GitHub Actions (.github/workflows/deploy.yml):**

```yaml
- name: Run Database Migrations
  run: |
    alembic upgrade head
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}

- name: Verify Migration Success
  run: |
    alembic current
```

**Kubernetes Job (pre-deployment):**

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
spec:
  template:
    spec:
      containers:
      - name: migrate
        image: demeterai:latest
        command: ["alembic", "upgrade", "head"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: demeterai-secrets
              key: database-url
      restartPolicy: OnFailure
```

**Migration lock (prevent concurrent runs):**

```python
# Use advisory lock in PostgreSQL
SELECT pg_advisory_lock(123456);
# Run migration
SELECT pg_advisory_unlock(123456);
```

## Testing

- Test migration runs successfully in CI
- Test rollback: `alembic downgrade -1`
- Test concurrent migration attempts (lock prevents)
- Test failed migration doesn't deploy new code

---
**Card Created**: 2025-10-09
