# Deployment & Operations

**Version:** 1.0
**Last Updated:** 2025-10-08

---

## Overview

DemeterAI deployment strategy uses **Docker Compose** for development and testing, with plans for production deployment on cloud infrastructure.

---

## Docker Compose Architecture

### Services

| Service | Purpose | Pool Type | Replicas |
|---------|---------|-----------|----------|
| **api** | FastAPI web server | - | 2-4 |
| **celery_gpu_0** | ML worker (GPU 0) | solo | 1 |
| **celery_gpu_1** | ML worker (GPU 1) | solo | 1 |
| **celery_cpu** | CPU worker (aggregation) | prefork | 1 (concurrency=16) |
| **celery_io** | I/O worker (S3, DB) | gevent | 1 (concurrency=50) |
| **db** | PostgreSQL + PostGIS | - | 1 |
| **redis** | Celery broker/backend | - | 1 |
| **flower** | Celery monitoring | - | 1 |
| **prometheus** | Metrics collection | - | 1 |
| **grafana** | Metrics visualization | - | 1 |

---

## Celery Worker Configuration

### GPU Workers (CRITICAL)

**MANDATORY: pool=solo, concurrency=1 per GPU**

```bash
# GPU Worker 0
CUDA_VISIBLE_DEVICES=0 celery -A app worker \
  --pool=solo \
  --concurrency=1 \
  --queues=gpu_queue_0 \
  --max-tasks-per-child=50 \
  --max-memory-per-child=8000000  # 8GB limit
```

**Why pool=solo:**
- prefork causes CUDA context conflicts
- Model singleton pattern requires isolated GPU memory
- Industry best practice for GPU workloads

**Recycling:**
- `--max-tasks-per-child=50`: Recycle worker after 50 tasks (prevent memory leaks)
- `--max-memory-per-child=8GB`: Hard memory limit

### CPU Workers

```bash
celery -A app worker \
  --pool=prefork \
  --concurrency=16 \
  --queues=cpu_queue \
  --max-tasks-per-child=200
```

**Purpose:** Aggregation, batch creation, non-ML operations

### I/O Workers

```bash
celery -A app worker \
  --pool=gevent \
  --concurrency=50 \
  --queues=io_queue
```

**Purpose:** S3 uploads, database writes (non-blocking I/O)

---

## Environment Configuration

### Development (.env)

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/demeterai
DATABASE_URL_SYNC=postgresql+psycopg2://user:pass@db:5432/demeterai

# Redis
REDIS_URL=redis://redis:6379/0

# AWS S3
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=demeterai-photos
AWS_REGION=us-east-1

# JWT
JWT_SECRET_KEY=your_secret_key_change_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=15

# ML Models
YOLO_SEGMENTATION_MODEL=yolov11m-seg.pt
YOLO_DETECTION_MODEL=yolov11m.pt

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# App
DEBUG=true
LOG_LEVEL=DEBUG
```

### Production (.env.prod)

```env
DEBUG=false
LOG_LEVEL=INFO

# Use AWS Secrets Manager for sensitive values
DATABASE_URL=postgresql+asyncpg://user:${DB_PASSWORD}@rds-endpoint/demeterai
JWT_SECRET_KEY=${JWT_SECRET_FROM_SECRETS_MANAGER}
```

---

## Database Initialization

### Alembic Migrations

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "initial schema"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Seed Data (Optional)

```bash
# Load initial data (products, packaging, users)
python scripts/seed_data.py
```

---

## Monitoring & Observability

### Flower (Celery Monitoring)

**URL:** `http://localhost:5555`

**Features:**
- Real-time task monitoring
- Worker status
- Task history
- Rate graphs

### Prometheus + Grafana

**Prometheus:** `http://localhost:9090`
**Grafana:** `http://localhost:3000` (admin/admin)

**Metrics:**
- API latency (p50, p95, p99)
- ML inference time
- GPU utilization
- Cache hit rate
- Database connection pool

**Dashboards:**
- API Performance
- ML Pipeline Metrics
- Database Health
- Celery Workers

---

## Backup Strategy

### Database Backups

**Daily automated backups:**
```bash
# Backup script (runs via cron)
pg_dump -h localhost -U user demeterai | gzip > backups/demeterai_$(date +%Y%m%d).sql.gz

# Retention: Keep 30 days, then monthly for 1 year
```

**Point-in-Time Recovery (PITR):**
- WAL archiving to S3
- RPO: 5 minutes
- RTO: 30-60 minutes

### S3 Lifecycle Policies

**Original photos:**
- Delete after 90 days (keep processed images)

**Processed images:**
- Delete after 365 days

---

## Scaling Strategy

### Horizontal Scaling

**API Servers:**
- Scale on CPU > 70% or request queue > 100
- Target: 2-4 replicas for 1000 concurrent users

**GPU Workers:**
- Fixed count (4× A100 for production)
- No auto-scaling (GPU hardware is fixed)

**CPU Workers:**
- Scale on queue depth > 50 tasks
- Target: 1-4 workers depending on load

**I/O Workers:**
- Scale on S3 upload queue > 200 tasks

---

## Security Considerations

### Secrets Management

**Development:** `.env` file (NOT committed to git)
**Production:** AWS Secrets Manager

### S3 Security

- Server-side encryption (AES-256)
- Bucket policy: Private (no public access)
- IAM roles for EC2 instances

### Database Security

- SSL required
- Certificate validation enabled
- Private subnet (no public internet access)

### API Security

- JWT authentication (15min expiration)
- CORS configured for specific origins
- Rate limiting (planned)

---

## Health Checks

### API Health Endpoint

```bash
GET /health

Response:
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "celery_workers": {
    "gpu_queue_0": "active",
    "gpu_queue_1": "active",
    "cpu_queue": "active"
  }
}
```

### Database Health

```sql
SELECT 1;  -- Simple connection test
```

### Redis Health

```bash
redis-cli ping
# Expected: PONG
```

---

## Troubleshooting

### Common Issues

**GPU Worker Fails:**
- Check CUDA drivers: `nvidia-smi`
- Verify `pool=solo` (NOT prefork)
- Check model paths exist

**S3 Upload Fails:**
- Verify AWS credentials
- Check bucket permissions
- Review circuit breaker status (Flower)

**High Database Load:**
- Check slow query log
- Review `pg_stat_activity`
- Consider adding indexes

---

## Next Steps

- **Backend Services:** See [../backend/README.md](../backend/README.md)
- **API Endpoints:** See [../api/README.md](../api/README.md)
- **Development Guide:** See [../development/README.md](../development/README.md)

---

**Document Owner:** DemeterAI Engineering Team
**Last Reviewed:** 2025-10-08
