# DemeterAI v2.0 - Sprint 5 Deployment Guide

**Version**: 1.0
**Last Updated**: 2025-10-21
**Sprint**: Sprint 05 - Deployment + Observability
**Status**: Implementation Ready

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Prerequisites](#prerequisites)
3. [Architecture Overview](#architecture-overview)
4. [Environment Variables Reference](#environment-variables-reference)
5. [Quick Start (Docker)](#quick-start-docker)
6. [Detailed Setup](#detailed-setup)
7. [Auth0 Configuration](#auth0-configuration)
8. [OpenTelemetry Setup](#opentelemetry-setup)
9. [AWS S3 Configuration](#aws-s3-configuration)
10. [Testing the Deployment](#testing-the-deployment)
11. [Monitoring & Observability](#monitoring--observability)
12. [Troubleshooting](#troubleshooting)
13. [Production Considerations](#production-considerations)

---

## Executive Summary

**What is DemeterAI v2.0?**
Production ML-powered inventory management system for 600,000+ plants using FastAPI,
PostgreSQL/PostGIS, YOLO v11, and Celery.

**What's in Sprint 5?**

- Docker multi-stage build (<500MB)
- OpenTelemetry integration (traces → OTLP stack)
- Prometheus metrics at `/metrics`
- Auth0 JWT authentication with RBAC
- GitHub Actions CI/CD pipeline
- Comprehensive deployment documentation

**Deployment Options**:

1. **Docker Compose** (recommended for development/staging)
2. **Kubernetes** (production - out of scope)
3. **Native Python** (development only)

**Estimated Setup Time**:

- Quick Start (Docker): 15 minutes
- Full Setup (with Auth0/S3): 1-2 hours

---

## Prerequisites

### Required Software

**Core Dependencies**:

- **Python 3.12+** - Application runtime
- **Docker 24.0+** - Container runtime
- **Docker Compose 2.20+** - Multi-container orchestration
- **Git** - Version control
- **curl or Postman** - API testing

**Optional (for native deployment)**:

- **PostgreSQL 15+** with PostGIS 3.3+
- **Redis 7+**
- **psql** (PostgreSQL client)
- **redis-cli** (Redis client)

### External Services (Production)

**Required**:

- **Auth0 Account** (free tier) - https://auth0.com/signup
- **AWS Account** - For S3 buckets (free tier eligible)

**Optional**:

- **OTLP LGTM Stack** - For observability (Grafana/Prometheus/Tempo/Loki)
    - User already has this running (mentioned in context)
    - Default endpoint: http://localhost:4318

### System Requirements

**Minimum** (Development):

- CPU: 2 cores
- RAM: 4GB
- Disk: 10GB free

**Recommended** (Production):

- CPU: 4 cores
- RAM: 8GB
- Disk: 50GB SSD
- Network: 100Mbps

**For ML Inference** (Optional GPU):

- NVIDIA GPU with CUDA 12.1+
- 4GB+ VRAM

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Applications                       │
│                    (Web, Mobile, IoT Devices)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                              │
│                   (Auth0 JWT Validation)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Controllers  │  │   Services   │  │ Repositories │         │
│  │  (26 APIs)   │→│ (30 Services)│→│ (27 Repos)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  Middleware:                                                     │
│  - Correlation ID                                               │
│  - OpenTelemetry                                                │
│  - Prometheus Metrics                                           │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │ Redis Cache  │  │  AWS S3      │
│   + PostGIS  │  │ + Celery     │  │  (Photos)    │
│ (600K records)│  │   Queue      │  │              │
└──────────────┘  └──────────────┘  └──────────────┘

                Observability Stack
         ┌──────────────────────────────┐
         │ OpenTelemetry → OTLP → LGTM │
         │ Prometheus /metrics          │
         │ Structured JSON Logs         │
         └──────────────────────────────┘
```

**Key Components**:

- **FastAPI**: Async REST API (26 endpoints)
- **PostgreSQL**: Primary database with PostGIS for geospatial
- **Redis**: Cache + Celery task queue
- **Celery**: Async task processing (ML inference, photo processing)
- **YOLO v11**: ML models for plant detection/counting
- **Auth0**: JWT authentication with RBAC
- **OpenTelemetry**: Distributed tracing
- **Prometheus**: Metrics collection
- **S3**: Photo storage (original + processed)

---

## Environment Variables Reference

### Core Application

```bash
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Debug mode: true = expose error details, false = production mode
DEBUG=false
```

### Database Configuration

```bash
# Async database connection (asyncpg driver)
# Used by FastAPI for async database operations
DATABASE_URL=postgresql+asyncpg://demeter:password@localhost:5432/demeterai

# Sync database connection (psycopg2 driver)
# Used by Alembic for migrations (migrations are synchronous)
DATABASE_URL_SYNC=postgresql+psycopg2://demeter:password@localhost:5432/demeterai

# Connection pool settings
DB_POOL_SIZE=20           # Base connections
DB_MAX_OVERFLOW=10        # Emergency connections
DB_ECHO_SQL=false         # Log SQL queries (development only)
```

### Redis & Celery

```bash
# Redis connection
REDIS_URL=redis://localhost:6379/0

# Celery task queue
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### AWS S3 Configuration

```bash
# AWS credentials
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# S3 buckets
S3_BUCKET_ORIGINAL=demeter-photos-original
S3_BUCKET_VISUALIZATION=demeter-photos-viz

# Presigned URL expiry (hours)
S3_PRESIGNED_URL_EXPIRY_HOURS=24
```

### Authentication (Auth0)

```bash
# Auth0 domain (from Auth0 dashboard)
AUTH0_DOMAIN=demeterai.us.auth0.com

# API audience/identifier
AUTH0_API_AUDIENCE=https://api.demeterai.com

# JWT algorithms (RS256 for Auth0)
AUTH0_ALGORITHMS=["RS256"]

# Issuer URL
AUTH0_ISSUER=https://demeterai.us.auth0.com/

# Local JWT (fallback for development)
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### OpenTelemetry Configuration

```bash
# OTLP exporter endpoint (your existing LGTM stack)
# gRPC: http://localhost:4317
# HTTP: http://localhost:4318
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# Service identification
OTEL_SERVICE_NAME=demeterai-api
OTEL_ENABLED=true

# Environment tag (for filtering in Grafana)
APP_ENV=development
```

### Prometheus Metrics

```bash
# Enable Prometheus metrics at /metrics
ENABLE_METRICS=true
```

---

## Quick Start (Docker)

**For experienced developers who want to get running fast**:

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/DemeterDocs.git
cd DemeterDocs

# 2. Copy environment file
cp .env.example .env

# 3. Edit .env (REQUIRED: set database passwords)
vim .env
# At minimum, change:
# - Database passwords
# - AWS credentials (if using S3)
# - Auth0 credentials (if using auth)

# 4. Start services (development mode)
docker-compose up -d

# 5. Wait for services to be healthy (~30 seconds)
docker-compose ps

# 6. Run database migrations
docker exec demeterai-api alembic upgrade head

# 7. Verify application is running
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"DemeterAI v2.0"}

# 8. Check metrics endpoint
curl http://localhost:8000/metrics | head -20

# 9. View logs
docker-compose logs api --tail=50

# 10. Stop services
docker-compose down
```

**Production mode**:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## Detailed Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/DemeterDocs.git
cd DemeterDocs

# Verify structure
ls -la
# Should see: app/, alembic/, docker-compose.yml, Dockerfile, etc.
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your favorite editor
vim .env  # or nano, code, etc.
```

**Required Changes**:

```bash
# MUST CHANGE (security):
DATABASE_URL=postgresql+asyncpg://demeter:CHANGE_THIS_PASSWORD@db:5432/demeterai
DATABASE_URL_SYNC=postgresql+psycopg2://demeter:CHANGE_THIS_PASSWORD@db:5432/demeterai

# SHOULD CHANGE (if using Auth0):
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_API_AUDIENCE=https://api.demeterai.com

# SHOULD CHANGE (if using S3):
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
S3_BUCKET_ORIGINAL=your-bucket-original
S3_BUCKET_VISUALIZATION=your-bucket-viz

# OPTIONAL (if you have OTLP stack):
OTEL_EXPORTER_OTLP_ENDPOINT=http://your-otlp-endpoint:4318
OTEL_ENABLED=true
```

### Step 3: Start Services (Docker)

```bash
# Start all services in detached mode
docker-compose up -d

# Expected output:
# Creating network "demeterai-network" ... done
# Creating volume "demeterai_postgres_data" ... done
# Creating demeterai-db ... done
# Creating demeterai-redis ... done
# Creating demeterai-api ... done

# Verify services are healthy
docker-compose ps

# Expected output (all healthy):
# NAME                STATUS              PORTS
# demeterai-api       Up (healthy)        0.0.0.0:8000->8000/tcp
# demeterai-db        Up (healthy)        0.0.0.0:5432->5432/tcp
# demeterai-redis     Up (healthy)        0.0.0.0:6379->6379/tcp
```

### Step 4: Run Database Migrations

```bash
# Run Alembic migrations to create tables
docker exec demeterai-api alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
# INFO  [alembic.runtime.migration] Will assume transactional DDL.
# INFO  [alembic.runtime.migration] Running upgrade  -> abc123, initial schema
# INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456, add indexes
# ...

# Verify tables created
docker exec demeterai-db psql -U demeter -d demeterai -c "\dt"
# Should list 28+ tables
```

### Step 5: Verify Application

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "service": "DemeterAI v2.0"
}

# Test metrics endpoint (Prometheus)
curl http://localhost:8000/metrics

# Expected response:
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
# http_requests_total{handler="/health",method="GET",status="200"} 1.0
# ...

# Test API documentation (OpenAPI)
open http://localhost:8000/docs
# Interactive Swagger UI
```

### Step 6: Seed Database (Optional)

```bash
# If you have seed data script
docker exec demeterai-api python scripts/seed_data.py

# Or manually via SQL
docker exec -i demeterai-db psql -U demeter -d demeterai < seed_data.sql
```

---

## Auth0 Configuration

### Step 1: Create Auth0 Account

1. Go to https://auth0.com/signup
2. Sign up with email or Google
3. Create tenant (e.g., `demeterai`)
4. Choose region (US, EU, AU)

### Step 2: Create API

1. Go to **Applications → APIs**
2. Click **Create API**
3. Fill in:
    - **Name**: DemeterAI v2.0
    - **Identifier**: `https://api.demeterai.com` (any unique URI)
    - **Signing Algorithm**: RS256
4. Click **Create**

### Step 3: Enable RBAC

1. In API settings, go to **Settings** tab
2. Enable:
    - **Enable RBAC**: Yes
    - **Add Permissions in the Access Token**: Yes
3. Click **Save**

### Step 4: Define Permissions

1. In API settings, go to **Permissions** tab
2. Add permissions:
    - `stock:read` - Read stock data
    - `stock:write` - Create/update stock
    - `stock:delete` - Delete stock records
    - `analytics:read` - View analytics
    - `config:read` - Read configuration
    - `config:write` - Modify configuration
    - `users:manage` - Manage users (admin only)

### Step 5: Create Roles

1. Go to **User Management → Roles**
2. Create roles:

**Admin Role**:

- Name: `admin`
- Description: Full system access
- Permissions: ALL (stock:*, analytics:*, config:*, users:manage)

**Supervisor Role**:

- Name: `supervisor`
- Description: Manage stock and view analytics
- Permissions: stock:*, analytics:read, config:read

**Worker Role**:

- Name: `worker`
- Description: Create and update stock
- Permissions: stock:read, stock:write

**Viewer Role**:

- Name: `viewer`
- Description: Read-only access
- Permissions: stock:read, analytics:read

### Step 6: Get Credentials

1. In API settings, copy:
    - **Identifier** → `AUTH0_API_AUDIENCE`
    - **Domain** (from tenant settings) → `AUTH0_DOMAIN`

2. Update `.env`:

```bash
AUTH0_DOMAIN=demeterai.us.auth0.com
AUTH0_API_AUDIENCE=https://api.demeterai.com
AUTH0_ALGORITHMS=["RS256"]
AUTH0_ISSUER=https://demeterai.us.auth0.com/
```

3. Restart API:

```bash
docker-compose restart api
```

### Step 7: Test Authentication

**Get test token** (using Auth0 dashboard):

```bash
# Method 1: Use Auth0 API Explorer
# 1. Go to API → DemeterAI v2.0 → Test
# 2. Copy "Access Token"

# Method 2: Use curl (requires client credentials)
curl --request POST \
  --url https://demeterai.us.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{
    "client_id":"YOUR_CLIENT_ID",
    "client_secret":"YOUR_CLIENT_SECRET",
    "audience":"https://api.demeterai.com",
    "grant_type":"client_credentials"
  }'
```

**Test protected endpoint**:

```bash
# Without token (should fail)
curl http://localhost:8000/api/v1/stock/batches

# Expected: 401 Unauthorized

# With token (should succeed)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/auth/me

# Expected: User claims (sub, email, roles, permissions)
```

---

## OpenTelemetry Setup

**Assuming you have OTLP LGTM stack running** (Grafana + Prometheus + Tempo + Loki)

### Step 1: Verify OTLP Receiver

```bash
# Check if OTLP receiver is running
curl http://localhost:4318/v1/traces
# Should return 405 Method Not Allowed (endpoint exists)

# Or check gRPC endpoint
grpcurl -plaintext localhost:4317 list
# Should list OTLP services
```

### Step 2: Configure Endpoint

```bash
# Edit .env
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318  # HTTP endpoint
# OR
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317  # gRPC endpoint

OTEL_ENABLED=true
OTEL_SERVICE_NAME=demeterai-api
APP_ENV=production
```

### Step 3: Restart API

```bash
docker-compose restart api

# Check logs for OTEL initialization
docker-compose logs api | grep -i "opentelemetry"

# Expected:
# INFO OpenTelemetry initialized successfully
# INFO OTLP exporter configured: http://localhost:4318
```

### Step 4: Generate Test Traffic

```bash
# Generate API requests
for i in {1..10}; do
  curl http://localhost:8000/health
  sleep 1
done

# Generate stock operations
curl -X POST http://localhost:8000/api/v1/stock/batches \
  -H "Content-Type: application/json" \
  -d '{"product_id":1,"quantity":100}'
```

### Step 5: View Traces in Grafana

1. Open Grafana: http://localhost:3000
2. Go to **Explore** → Select **Tempo** datasource
3. Query for service: `demeterai-api`
4. View traces:
    - HTTP request spans
    - Database query spans
    - Service-to-service calls

**Example Trace**:

```
POST /api/v1/stock/batches (200ms)
  ├─ StockService.create_batch (150ms)
  │  ├─ ConfigService.get_by_location (20ms)
  │  │  └─ PostgreSQL SELECT (15ms)
  │  ├─ BatchRepository.create (80ms)
  │  │  └─ PostgreSQL INSERT (75ms)
  │  └─ BatchService.validate (10ms)
  └─ Serialize response (5ms)
```

---

## AWS S3 Configuration

### Step 1: Create S3 Buckets

```bash
# Using AWS CLI
aws s3 mb s3://demeter-photos-original --region us-east-1
aws s3 mb s3://demeter-photos-viz --region us-east-1

# Or via AWS Console:
# 1. Go to S3 → Create bucket
# 2. Name: demeter-photos-original
# 3. Region: us-east-1
# 4. Block public access: Enabled (recommended)
# 5. Create bucket
# 6. Repeat for demeter-photos-viz
```

### Step 2: Create IAM User

```bash
# Via AWS Console:
# 1. Go to IAM → Users → Add user
# 2. Username: demeterai-s3-user
# 3. Access type: Programmatic access
# 4. Permissions: Attach existing policies → AmazonS3FullAccess
# 5. Create user
# 6. Copy Access Key ID and Secret Access Key
```

**Or use AWS CLI**:

```bash
aws iam create-user --user-name demeterai-s3-user

aws iam attach-user-policy \
  --user-name demeterai-s3-user \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam create-access-key --user-name demeterai-s3-user
# Copy AccessKeyId and SecretAccessKey
```

### Step 3: Configure Application

```bash
# Edit .env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_ORIGINAL=demeter-photos-original
S3_BUCKET_VISUALIZATION=demeter-photos-viz
S3_PRESIGNED_URL_EXPIRY_HOURS=24
```

### Step 4: Test S3 Integration

```bash
# Restart API to load new credentials
docker-compose restart api

# Test upload (assuming endpoint exists)
curl -X POST http://localhost:8000/api/v1/photos/upload \
  -F "file=@test_image.jpg" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected response:
{
  "photo_id": "abc-123-def",
  "original_url": "https://s3.amazonaws.com/demeter-photos-original/abc-123-def.jpg",
  "status": "uploaded"
}

# Verify in S3
aws s3 ls s3://demeter-photos-original/
```

---

## Testing the Deployment

### Automated Tests

```bash
# Run all tests
docker exec demeterai-api pytest tests/ -v

# Run specific test suites
docker exec demeterai-api pytest tests/unit/ -v
docker exec demeterai-api pytest tests/integration/ -v

# Run with coverage
docker exec demeterai-api pytest tests/ --cov=app --cov-report=term-missing
```

### Manual API Tests

**1. Health Check**:

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

**2. API Documentation**:

```bash
open http://localhost:8000/docs
# Interactive Swagger UI with all 26 endpoints
```

**3. Stock Endpoints** (requires auth):

```bash
# List stock batches
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/stock/batches

# Create stock batch
curl -X POST http://localhost:8000/api/v1/stock/batches \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "location_id": 1,
    "quantity": 100,
    "batch_code": "BATCH-001"
  }'
```

**4. Metrics Endpoint**:

```bash
curl http://localhost:8000/metrics
# Should return Prometheus-formatted metrics
```

**5. Auth Endpoints**:

```bash
# Get current user info
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/auth/me

# Expected:
{
  "user_id": "auth0|abc123",
  "email": "user@example.com",
  "roles": ["supervisor"],
  "permissions": ["stock:read", "stock:write", "analytics:read"]
}
```

### Database Tests

```bash
# Connect to database
docker exec -it demeterai-db psql -U demeter -d demeterai

# Count records
SELECT COUNT(*) FROM warehouses;
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM stock_batches;

# Check PostGIS
SELECT PostGIS_Full_Version();

# Exit
\q
```

### Redis Tests

```bash
# Connect to Redis
docker exec -it demeterai-redis redis-cli

# Test cache
SET test_key "hello"
GET test_key
DEL test_key

# Check Celery queues
LLEN celery

# Exit
exit
```

---

## Monitoring & Observability

### Prometheus Metrics

**Available Metrics**:

- `http_request_duration_seconds` - API request latency
- `http_requests_total` - Total requests by status code
- `demeter_stock_operations_total` - Stock operations counter
- `demeter_ml_inference_duration_seconds` - ML inference time
- `demeter_active_photo_sessions` - Active processing sessions

**Query Metrics**:

```bash
# View all metrics
curl http://localhost:8000/metrics

# Filter for custom metrics
curl http://localhost:8000/metrics | grep "demeter_"
```

**Prometheus Queries** (in Prometheus UI):

```promql
# Request rate (per second)
rate(http_requests_total[1m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Stock operations by type
sum(rate(demeter_stock_operations_total[5m])) by (operation_type)
```

### OpenTelemetry Traces

**View in Grafana**:

1. Go to Grafana → Explore
2. Select Tempo datasource
3. Query: `{service.name="demeterai-api"}`
4. Explore traces

**Trace Context**:

- Correlation IDs automatically propagated
- Service-to-service calls traced
- Database queries included
- Custom spans for business logic

### Structured Logging

**Log Format** (JSON):

```json
{
  "timestamp": "2025-10-21T14:30:00Z",
  "level": "INFO",
  "message": "Request received",
  "correlation_id": "abc-123-def",
  "method": "POST",
  "path": "/api/v1/stock/batches",
  "user_id": "auth0|123"
}
```

**View Logs**:

```bash
# API logs
docker-compose logs api --tail=100 -f

# Database logs
docker-compose logs db --tail=50

# All logs
docker-compose logs --tail=200 -f
```

---

## Troubleshooting

### Application Won't Start

**Error**: `ImportError: cannot import name 'app'`

**Solution**:

```bash
# Verify Python version
docker exec demeterai-api python --version
# Must be 3.12+

# Reinstall dependencies
docker exec demeterai-api pip install -r requirements.txt

# Check for syntax errors
docker exec demeterai-api python -m py_compile app/main.py
```

### Database Connection Fails

**Error**: `asyncpg.exceptions.InvalidPasswordError`

**Solution**:

```bash
# Verify database is running
docker-compose ps db

# Test connection
docker exec demeterai-db psql -U demeter -d demeterai -c "SELECT 1;"

# Check DATABASE_URL in .env
# Ensure password matches docker-compose.yml
```

### OTLP Export Failures

**Error**: `Failed to export spans to OTLP endpoint`

**Solution**:

```bash
# Verify OTLP endpoint is reachable
curl http://localhost:4318/v1/traces

# Check OTEL_EXPORTER_OTLP_ENDPOINT in .env

# Temporarily disable OTEL
OTEL_ENABLED=false docker-compose restart api

# Check OTLP receiver logs
docker logs YOUR_OTLP_CONTAINER
```

### Auth0 Token Validation Fails

**Error**: `401 Unauthorized - Invalid token`

**Solution**:

```bash
# Verify AUTH0_DOMAIN and AUTH0_API_AUDIENCE
# Must match Auth0 dashboard settings

# Check token expiry
# Decode JWT at https://jwt.io

# Verify JWKS URL is reachable
curl https://YOUR_DOMAIN/.well-known/jwks.json

# Check algorithm matches (RS256)
```

### Docker Image Too Large

**Error**: Image size >500MB

**Solution**:

```bash
# Check current size
docker images demeterai:latest

# Optimize Dockerfile:
# 1. Use --no-cache-dir for pip
# 2. Remove unnecessary packages
# 3. Multi-stage build (already implemented)

# Rebuild with build kit
DOCKER_BUILDKIT=1 docker build -t demeterai:latest .

# Verify size reduction
docker images demeterai:latest
```

---

## Production Considerations

### Security

**✅ Implemented**:

- Non-root user in Docker
- JWT authentication with Auth0
- Environment variable secrets
- Structured logging (no sensitive data)

**🔧 TODO (Operations Team)**:

- Rotate secrets regularly
- Enable TLS/HTTPS (reverse proxy)
- Network segmentation (firewall rules)
- Security scanning (Snyk, Trivy)
- Rate limiting (nginx/traefik)

### Performance

**Database Tuning**:

```sql
-- Increase connection pool (in .env)
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=20

-- Add indexes (already in migrations)
CREATE INDEX idx_stock_batches_product ON stock_batches(product_id);
CREATE INDEX idx_detections_session ON detections(session_id);
```

**Redis Tuning**:

```bash
# In redis.conf or docker-compose
maxmemory 2gb
maxmemory-policy allkeys-lru
```

**API Scaling**:

```bash
# Run multiple API instances
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Add load balancer (nginx/traefik)
```

### Backup & Recovery

**Database Backups**:

```bash
# Manual backup
docker exec demeterai-db pg_dump -U demeter demeterai > backup.sql

# Automated backups (cron)
0 2 * * * docker exec demeterai-db pg_dump -U demeter demeterai | gzip > /backups/demeterai_$(date +\%Y\%m\%d).sql.gz
```

**Restore**:

```bash
docker exec -i demeterai-db psql -U demeter -d demeterai < backup.sql
```

### Disaster Recovery

**RTO (Recovery Time Objective)**: 1 hour
**RPO (Recovery Point Objective)**: 24 hours

**Procedure**:

1. Restore database from latest backup
2. Restore `.env` from secrets manager
3. Deploy application from Docker image
4. Verify health checks
5. Resume traffic

---

## Next Steps

### Immediate (After Sprint 5)

1. **Deploy to Staging** - Use this guide to deploy to staging server
2. **Load Testing** - Test with 600,000+ plant records
3. **Security Audit** - Run penetration tests
4. **Monitor Observability** - Configure Grafana dashboards

### Short-term (Weeks 13-14)

1. **Frontend Integration** - Connect React/Vue frontend
2. **User Training** - Train operations team
3. **Documentation Review** - Update based on feedback
4. **Performance Tuning** - Optimize database queries

### Long-term (Months 4-6)

1. **Kubernetes Migration** - Move to K8s for auto-scaling
2. **Multi-region Deployment** - Deploy to multiple AWS regions
3. **Advanced ML Features** - Implement tracking, forecasting
4. **Mobile App** - Build iOS/Android app

---

## Support & Resources

**Documentation**:

- API Docs: http://localhost:8000/docs
- Engineering Plan: `/home/lucasg/proyectos/DemeterDocs/engineering_plan/`
- Database Schema: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd`

**External Resources**:

- FastAPI: https://fastapi.tiangolo.com/
- Auth0: https://auth0.com/docs/
- OpenTelemetry: https://opentelemetry.io/docs/
- Prometheus: https://prometheus.io/docs/

**Contact**:

- Development Team: dev@demeterai.com
- Operations Team: ops@demeterai.com

---

**Deployment Guide Version**: 1.0
**Last Updated**: 2025-10-21
**Maintained By**: DemeterAI Engineering Team
