# [DEP012] Production Deployment Guide (Runbook)

## Metadata

- **Epic**: epic-011-deployment
- **Sprint**: Sprint-08
- **Priority**: `medium`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [DEP001-DEP011]

## Description

Create comprehensive deployment runbook: step-by-step production deployment, rollback procedures,
troubleshooting guide.

## Acceptance Criteria

- [ ] **Deployment checklist** (pre-deployment)
- [ ] **Step-by-step deployment** procedure
- [ ] **Rollback procedure** (for failed deployments)
- [ ] **Smoke tests** (verify critical paths work)
- [ ] **Troubleshooting guide** (common issues + solutions)
- [ ] **Emergency contacts** (on-call rotation)

## Implementation

**docs/deployment/RUNBOOK.md:**

```markdown
# Production Deployment Runbook

## Pre-Deployment Checklist
- [ ] All tests passing in CI
- [ ] Database migrations reviewed
- [ ] Backup verified (<24h old)
- [ ] Monitoring dashboards green
- [ ] Stakeholders notified (maintenance window if needed)

## Deployment Steps

### 1. Backup Database
```bash
./scripts/backup_db.sh
aws s3 ls s3://demeterai-backups/database/ | tail -1  # Verify upload
```

### 2. Run Database Migrations

```bash
kubectl apply -f k8s/db-migrate-job.yaml
kubectl logs -f job/db-migrate  # Watch migration logs
```

### 3. Deploy New Version

```bash
kubectl set image deployment/demeterai-api api=demeterai:v2.1.0
kubectl rollout status deployment/demeterai-api  # Wait for rollout
```

### 4. Smoke Tests

```bash
# Test health endpoint
curl https://api.demeterai.com/health

# Test authentication
curl -X POST https://api.demeterai.com/api/auth/login \
  -d '{"email":"admin@demeterai.com","password":"..."}'

# Test photo upload (critical path)
curl -X POST https://api.demeterai.com/api/stock/photo \
  -H "Authorization: Bearer ..." \
  -F "file=@test_photo.jpg"
```

### 5. Monitor Metrics

- Check Grafana dashboards (error rate, latency)
- Check Celery queue depth
- Check database connections
- Watch logs in Grafana Loki

## Rollback Procedure

If deployment fails or critical issues detected:

### 1. Rollback Deployment

```bash
kubectl rollout undo deployment/demeterai-api
kubectl rollout status deployment/demeterai-api
```

### 2. Rollback Database (if needed)

```bash
# Restore from backup
aws s3 cp s3://demeterai-backups/database/latest.sql.gz .
gunzip latest.sql.gz
psql -h $DB_HOST -U $DB_USER demeterai < latest.sql

# OR rollback migration
kubectl apply -f k8s/db-rollback-job.yaml
```

### 3. Verify Rollback

- Run smoke tests again
- Check error rate returned to normal
- Notify stakeholders

## Troubleshooting

### Issue: Pods not starting

**Symptoms:** Pods in CrashLoopBackOff
**Check:**

```bash
kubectl describe pod demeterai-api-xxx
kubectl logs demeterai-api-xxx
```

**Common causes:**

- Database connection failed (check DATABASE_URL secret)
- Missing environment variables
- Health check failing

**Solution:**

```bash
kubectl get secret demeterai-secrets -o yaml  # Verify secrets
kubectl exec -it demeterai-api-xxx -- env      # Check env vars
```

### Issue: High error rate

**Symptoms:** 5xx errors in Grafana
**Check:**

- Database connection pool exhausted
- Celery queue backed up
- Memory/CPU limits reached

**Solution:**

```bash
# Scale up API replicas
kubectl scale deployment/demeterai-api --replicas=6

# Check database
kubectl exec -it postgres-0 -- psql -U demeter -c "SELECT count(*) FROM pg_stat_activity;"

# Check Celery queue
redis-cli -h redis LLEN celery
```

### Issue: Slow API responses

**Symptoms:** p95 latency >2s
**Check:**

- Database slow queries
- Celery tasks blocking API
- Cache hit rate low

**Solution:**

- Check slow query log
- Scale Celery workers
- Warm up cache

## Emergency Contacts

- **On-call DevOps:** +1-555-DEVOPS
- **Database Admin:** +1-555-DBADMIN
- **Product Owner:** +1-555-PRODUCT
- **Slack:** #demeterai-incidents

```

## Testing
- Practice deployment in staging
- Practice rollback procedure
- Verify runbook accuracy
- Update after each deployment (lessons learned)

---
**Card Created**: 2025-10-09
