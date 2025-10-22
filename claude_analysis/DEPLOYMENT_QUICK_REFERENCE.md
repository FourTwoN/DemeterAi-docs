# DemeterAI v2.0 - Deployment Quick Reference Card

**Version**: 1.0 | **Sprint**: 05 | **Updated**: 2025-10-21

---

## 🚀 Quick Start (15 Minutes)

```bash
# 1. Clone and setup
git clone https://github.com/YOUR_USERNAME/DemeterDocs.git
cd DemeterDocs
cp .env.example .env

# 2. Edit .env (REQUIRED: set passwords)
vim .env

# 3. Start all services
docker-compose up -d

# 4. Wait for health checks (~30 seconds)
docker-compose ps

# 5. Run database migrations
docker exec demeterai-api alembic upgrade head

# 6. Verify it works
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"DemeterAI v2.0"}

# 7. View API docs
open http://localhost:8000/docs
```

**Success Indicators**:
- ✅ All 3 services show "Up (healthy)"
- ✅ Health endpoint returns 200 OK
- ✅ 28+ tables created in database

---

## 📋 Environment Variables (Critical)

### Must Change (Security)
```bash
# Database passwords
DATABASE_URL=postgresql+asyncpg://demeter:CHANGE_THIS@db:5432/demeterai
DATABASE_URL_SYNC=postgresql+psycopg2://demeter:CHANGE_THIS@db:5432/demeterai
```

### Auth0 (If Using Authentication)
```bash
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_API_AUDIENCE=https://api.demeterai.com
AUTH0_ALGORITHMS=["RS256"]
AUTH0_ISSUER=https://your-tenant.us.auth0.com/
```

### AWS S3 (If Using Photo Storage)
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_ORIGINAL=demeter-photos-original
S3_BUCKET_VISUALIZATION=demeter-photos-viz
```

### OpenTelemetry (If You Have OTLP Stack)
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_ENABLED=true
OTEL_SERVICE_NAME=demeterai-api
APP_ENV=production
```

**Full Reference**: See `SPRINT_05_DEPLOYMENT_GUIDE.md` lines 155-254

---

## 🔑 Auth0 Setup (30 Minutes)

### Step 1: Create Account
1. Go to https://auth0.com/signup
2. Create tenant: `demeterai`
3. Choose region: US/EU/AU

### Step 2: Create API
1. Go to **Applications → APIs**
2. Click **Create API**
3. Name: `DemeterAI v2.0`
4. Identifier: `https://api.demeterai.com` (can be any URI)
5. Signing Algorithm: **RS256**

### Step 3: Define Permissions
Add these 7 permissions in API → Permissions:
- `stock:read` - Read stock data
- `stock:write` - Create/update stock
- `stock:delete` - Delete stock records
- `analytics:read` - View analytics
- `config:read` - Read configuration
- `config:write` - Modify configuration
- `users:manage` - Manage users (admin only)

### Step 4: Create Roles
Go to **User Management → Roles**, create:

| Role | Permissions | Use Case |
|------|-------------|----------|
| **admin** | ALL | System administrators |
| **supervisor** | stock:*, analytics:read, config:read | Floor supervisors |
| **worker** | stock:read, stock:write | Warehouse workers |
| **viewer** | stock:read, analytics:read | Reporting users |

### Step 5: Get Credentials
Copy from Auth0 dashboard:
- **Domain** → `AUTH0_DOMAIN`
- **API Identifier** → `AUTH0_API_AUDIENCE`

Update `.env` and restart:
```bash
docker-compose restart api
```

### Step 6: Test
```bash
# Get token from Auth0 (Method 1: Use API Explorer in dashboard)
# Method 2: Use curl
curl --request POST \
  --url https://your-tenant.us.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{
    "client_id":"YOUR_CLIENT_ID",
    "client_secret":"YOUR_CLIENT_SECRET",
    "audience":"https://api.demeterai.com",
    "grant_type":"client_credentials"
  }'

# Test protected endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/auth/me
```

**Full Guide**: See `SPRINT_05_DEPLOYMENT_GUIDE.md` lines 429-545

---

## 🗄️ Database Commands

```bash
# Connect to database
docker exec -it demeterai-db psql -U demeter -d demeterai

# List tables
\dt

# Count records
SELECT COUNT(*) FROM warehouses;
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM stock_batches;

# Check PostGIS
SELECT PostGIS_Full_Version();

# Exit
\q
```

### Migrations
```bash
# Apply all migrations
docker exec demeterai-api alembic upgrade head

# Check current version
docker exec demeterai-api alembic current

# Rollback one migration
docker exec demeterai-api alembic downgrade -1
```

### Backup & Restore
```bash
# Backup
docker exec demeterai-db pg_dump -U demeter demeterai > backup.sql

# Restore
docker exec -i demeterai-db psql -U demeter -d demeterai < backup.sql
```

---

## 📊 Monitoring & Observability

### Prometheus Metrics
```bash
# View all metrics
curl http://localhost:8000/metrics

# Filter custom metrics
curl http://localhost:8000/metrics | grep "demeter_"
```

**Available Metrics**:
- `http_request_duration_seconds` - API latency
- `http_requests_total` - Total requests
- `demeter_stock_operations_total` - Stock operations
- `demeter_ml_inference_duration_seconds` - ML inference time
- `demeter_active_photo_sessions` - Active sessions

### OpenTelemetry Traces
1. Open Grafana: http://localhost:3000
2. Go to **Explore** → Select **Tempo**
3. Query: `{service.name="demeterai-api"}`
4. View traces

### Logs
```bash
# API logs
docker-compose logs api --tail=100 -f

# All services
docker-compose logs --tail=200 -f

# Database logs
docker-compose logs db --tail=50
```

---

## 🧪 Testing

### Automated Tests
```bash
# Run all tests
docker exec demeterai-api pytest tests/ -v

# Run with coverage
docker exec demeterai-api pytest tests/ --cov=app --cov-report=term-missing

# Run specific test suite
docker exec demeterai-api pytest tests/unit/models/ -v
```

### Manual API Tests
```bash
# Health check
curl http://localhost:8000/health

# Metrics
curl http://localhost:8000/metrics

# API documentation (interactive)
open http://localhost:8000/docs

# Protected endpoint (requires token)
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/stock/batches
```

---

## 🚨 Troubleshooting

### Service Won't Start
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs api --tail=50

# Restart service
docker-compose restart api

# Rebuild and restart
docker-compose up -d --build
```

### Database Connection Fails
```bash
# Verify database is running
docker-compose ps db

# Test connection
docker exec demeterai-db psql -U demeter -d demeterai -c "SELECT 1;"

# Check password in .env matches docker-compose.yml
cat .env | grep DATABASE_URL
cat docker-compose.yml | grep POSTGRES_PASSWORD
```

### Auth0 Token Invalid
```bash
# Verify Auth0 configuration
cat .env | grep AUTH0

# Check JWKS endpoint is accessible
curl https://YOUR_DOMAIN/.well-known/jwks.json

# Decode token to verify claims
# Go to https://jwt.io and paste token
```

### OTLP Export Fails
```bash
# Verify OTLP endpoint
curl http://localhost:4318/v1/traces
# Expected: 405 Method Not Allowed (endpoint exists)

# Temporarily disable OTLP
OTEL_ENABLED=false docker-compose restart api
```

### Docker Image Too Large
```bash
# Check current size
docker images demeterai:latest

# Rebuild with BuildKit
DOCKER_BUILDKIT=1 docker build -t demeterai:latest .

# Check size again
docker images demeterai:latest
```

---

## 🔧 Common Operations

### Stop All Services
```bash
docker-compose down
```

### Stop and Remove Volumes (CAUTION: Deletes Data)
```bash
docker-compose down -v
```

### View Service Status
```bash
docker-compose ps
```

### Restart Single Service
```bash
docker-compose restart api
```

### Scale API Service
```bash
docker-compose up -d --scale api=3
```

### Update After Code Changes
```bash
# Rebuild and restart
docker-compose up -d --build

# Or just restart
docker-compose restart api
```

---

## 📦 Production Checklist

### Before Deployment
- [ ] Change all passwords in `.env`
- [ ] Set `DEBUG=false`
- [ ] Configure Auth0 production tenant
- [ ] Set up AWS S3 buckets with IAM roles
- [ ] Configure HTTPS/TLS (reverse proxy)
- [ ] Set up database backups (automated)
- [ ] Configure OTLP endpoint (Grafana Cloud or self-hosted)
- [ ] Review security settings
- [ ] Test with production-like data

### After Deployment
- [ ] Verify all health checks pass
- [ ] Test authentication flow
- [ ] Verify metrics are visible in Grafana
- [ ] Test S3 photo upload/download
- [ ] Verify database connection pool
- [ ] Monitor error logs for 24 hours
- [ ] Set up alerting rules
- [ ] Document any production-specific configurations

---

## 📚 Documentation Links

**Main Guide**: `/home/lucasg/proyectos/DemeterDocs/SPRINT_05_DEPLOYMENT_GUIDE.md` (1104 lines)

**Sections**:
- Quick Start: Lines 256-303
- Environment Variables: Lines 155-254
- Auth0 Setup: Lines 429-545
- AWS S3 Setup: Lines 629-704
- Testing: Lines 707-811
- Monitoring: Lines 814-886
- Troubleshooting: Lines 889-980
- Production: Lines 983-1055

**Related Docs**:
- Auth Usage Guide: `/home/lucasg/proyectos/DemeterDocs/app/core/AUTH_USAGE_GUIDE.md`
- Database Schema: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd`
- API Documentation: http://localhost:8000/docs (when running)

---

## 🆘 Support

**For Issues**:
1. Check troubleshooting section (lines 889-980 in main guide)
2. Review logs: `docker-compose logs api --tail=100`
3. Verify environment variables: `cat .env`
4. Check service health: `docker-compose ps`

**External Resources**:
- FastAPI Docs: https://fastapi.tiangolo.com/
- Auth0 Docs: https://auth0.com/docs/
- Docker Compose: https://docs.docker.com/compose/
- PostgreSQL: https://www.postgresql.org/docs/

---

**Quick Reference Version**: 1.0
**Last Updated**: 2025-10-21
**Maintained By**: DemeterAI Engineering Team
