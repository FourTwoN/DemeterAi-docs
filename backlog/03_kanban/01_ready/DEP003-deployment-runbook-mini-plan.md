# Mini-Plan F: Comprehensive Deployment Runbook

**Created**: 2025-10-21
**Team Leader**: Orchestration Agent
**Epic**: sprint-05-deployment
**Priority**: HIGH (documentation critical for handoff)
**Complexity**: 5 points (Low - mostly documentation)

---

## Task Overview

Create comprehensive deployment guide documenting all environment variables, setup procedures,
testing steps, and operational procedures for DemeterAI v2.0.

---

## Current State Analysis

**Existing Documentation**:

- `.env.example` with basic configuration
- README files in various directories
- Engineering plan documentation
- Sprint summaries

**Missing**:

- Complete deployment runbook
- Environment variable reference
- Step-by-step setup guide
- Troubleshooting guide
- Operational procedures (backup, monitoring, scaling)

---

## Architecture

**Layer**: Documentation
**Pattern**: Comprehensive runbook covering: Environment Setup → Installation → Configuration →
Testing → Operations

**Files to Create/Modify**:

- [ ] `DEPLOYMENT_GUIDE.md` (create - comprehensive deployment guide)
- [ ] `OPERATIONS_RUNBOOK.md` (create - day-to-day operations)
- [ ] `TROUBLESHOOTING.md` (create - common issues and solutions)
- [ ] `README.md` (update - add deployment links)
- [ ] `.env.example` (verify completeness)

---

## Implementation Strategy

### Phase 1: Create DEPLOYMENT_GUIDE.md

**Structure**:

```markdown
# DemeterAI v2.0 - Deployment Guide

## Table of Contents
1. Prerequisites
2. Environment Variables Reference
3. Local Development Setup
4. Docker Deployment
5. Production Deployment
6. Database Setup
7. Auth0 Configuration
8. OpenTelemetry Setup
9. S3 Configuration
10. Testing the Deployment
11. Next Steps

## 1. Prerequisites

**System Requirements**:
- Python 3.12+
- Docker 24.0+ and Docker Compose 2.20+
- PostgreSQL 15+ with PostGIS 3.3+ (or use Docker)
- Redis 7+ (or use Docker)
- Git

**External Services** (for production):
- Auth0 account (free tier)
- AWS account (S3 buckets)
- OTLP receiver (for observability)

**Development Tools**:
- curl or Postman (API testing)
- psql (PostgreSQL client)
- redis-cli (Redis client)

## 2. Environment Variables Reference

### Core Application
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `DEBUG`: Debug mode (true/false)

### Database
- `DATABASE_URL`: Async PostgreSQL connection (asyncpg)
- `DATABASE_URL_SYNC`: Sync PostgreSQL connection (psycopg2)
- `DB_POOL_SIZE`: Connection pool size (default: 20)
- `DB_MAX_OVERFLOW`: Max overflow connections (default: 10)
- `DB_ECHO_SQL`: Log SQL queries (true/false)

### Redis & Celery
- `REDIS_URL`: Redis connection URL
- `CELERY_BROKER_URL`: Celery broker (Redis)
- `CELERY_RESULT_BACKEND`: Celery result backend (Redis)

### AWS S3
- `AWS_REGION`: AWS region (e.g., us-east-1)
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `S3_BUCKET_ORIGINAL`: Original photos bucket
- `S3_BUCKET_VISUALIZATION`: Processed photos bucket
- `S3_PRESIGNED_URL_EXPIRY_HOURS`: URL expiry (default: 24)

### Authentication (Auth0)
- `AUTH0_DOMAIN`: Auth0 domain
- `AUTH0_API_AUDIENCE`: API audience/identifier
- `AUTH0_ALGORITHMS`: JWT algorithms (default: ["RS256"])
- `AUTH0_ISSUER`: Issuer URL
- `JWT_SECRET_KEY`: Local JWT secret (fallback)
- `JWT_ALGORITHM`: Local JWT algorithm
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiry

### OpenTelemetry
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint
- `OTEL_SERVICE_NAME`: Service name
- `OTEL_ENABLED`: Enable OTEL (true/false)
- `APP_ENV`: Environment (development/staging/production)

### Metrics
- `ENABLE_METRICS`: Enable Prometheus metrics (true/false)

## 3. Local Development Setup

Step-by-step guide...

## 4. Docker Deployment

Step-by-step guide...

... (continue with all sections)
```

### Phase 2: Create OPERATIONS_RUNBOOK.md

**Structure**:

```markdown
# DemeterAI v2.0 - Operations Runbook

## Daily Operations

### Starting the Application
...

### Stopping the Application
...

### Checking Health
...

### Viewing Logs
...

## Monitoring

### Metrics (Prometheus)
...

### Traces (OpenTelemetry)
...

### Logs (Structured JSON)
...

## Maintenance

### Database Backups
...

### Database Migrations
...

### Clearing Redis Cache
...

## Scaling

### Horizontal Scaling (Multiple API Instances)
...

### Celery Worker Scaling
...

## Security

### Rotating Secrets
...

### Updating Dependencies
...

### Security Scanning
...
```

### Phase 3: Create TROUBLESHOOTING.md

**Common Issues and Solutions**:

```markdown
# DemeterAI v2.0 - Troubleshooting Guide

## Application Won't Start

**Issue**: `uvicorn` fails with import errors

**Solution**:
1. Verify Python version: `python --version` (must be 3.12+)
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Check database connection
4. Review logs for specific errors

## Database Connection Errors

**Issue**: `asyncpg.exceptions.InvalidAuthorizationSpecificationError`

**Solution**:
1. Verify DATABASE_URL in .env
2. Check PostgreSQL is running: `docker ps | grep postgres`
3. Test connection: `psql -U demeter -d demeterai -h localhost`
4. Verify password matches

## OTLP Exporter Failures

**Issue**: `OpenTelemetry exporter failed to export spans`

**Solution**:
1. Verify OTLP endpoint is reachable
2. Check OTEL_EXPORTER_OTLP_ENDPOINT in .env
3. Temporarily disable: Set OTEL_ENABLED=false
4. Check OTLP receiver logs

... (continue with more issues)
```

### Phase 4: Update README.md

**Add deployment section**:

```markdown
## Deployment

For complete deployment instructions, see:
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Full deployment guide
- [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md) - Daily operations
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues

**Quick Start** (Docker):
```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit .env with your credentials

# 3. Start services
docker-compose up -d

# 4. Run migrations
docker exec demeterai-api alembic upgrade head

# 5. Verify health
curl http://localhost:8000/health
```

```

---

## Acceptance Criteria

- [ ] `DEPLOYMENT_GUIDE.md` created with complete setup instructions
- [ ] `OPERATIONS_RUNBOOK.md` created with operational procedures
- [ ] `TROUBLESHOOTING.md` created with common issues and solutions
- [ ] `README.md` updated with deployment links
- [ ] All environment variables documented
- [ ] Step-by-step instructions for:
  - [ ] Local development setup
  - [ ] Docker deployment
  - [ ] Production deployment
  - [ ] Database setup and migrations
  - [ ] Auth0 configuration
  - [ ] OpenTelemetry setup
  - [ ] S3 bucket configuration
  - [ ] Testing procedures
- [ ] Screenshots or diagrams included (optional)
- [ ] Troubleshooting section covers common issues
- [ ] Operations section covers daily tasks

---

## Content Outline

### DEPLOYMENT_GUIDE.md

**Section 1: Prerequisites**
- System requirements
- External services needed
- Development tools

**Section 2: Environment Variables Reference**
- Complete list of all variables
- Purpose of each variable
- Default values
- Production vs development differences

**Section 3: Local Development Setup**
- Clone repository
- Create virtual environment
- Install dependencies
- Configure .env
- Start PostgreSQL and Redis locally
- Run migrations
- Start application
- Test endpoints

**Section 4: Docker Deployment**
- Build Docker image
- Configure docker-compose.yml
- Start services with docker-compose
- Run migrations in container
- Verify health checks
- View logs
- Stop services

**Section 5: Production Deployment**
- Use docker-compose.prod.yml
- Environment variable security
- Resource limits
- Log rotation
- Health checks
- Restart policies

**Section 6: Database Setup**
- PostgreSQL installation (if not using Docker)
- PostGIS extension
- User creation
- Database creation
- Running Alembic migrations
- Seeding initial data
- Backup procedures

**Section 7: Auth0 Configuration**
- Create Auth0 account
- Create API
- Configure RBAC
- Define roles and permissions
- Get credentials
- Test authentication

**Section 8: OpenTelemetry Setup**
- Configure OTLP endpoint
- Start LGTM stack (if needed)
- Verify traces in Grafana
- Configure alerts

**Section 9: S3 Configuration**
- Create S3 buckets
- Configure IAM user
- Set bucket policies
- Get access keys
- Test upload/download

**Section 10: Testing the Deployment**
- Health check
- API endpoint tests
- Database connectivity
- Auth0 authentication
- OTLP export verification
- Prometheus metrics verification
- S3 upload test

**Section 11: Next Steps**
- Frontend integration notes
- Production monitoring setup
- Scaling considerations
- Security hardening

---

## Testing Procedure

**Verification Steps**:
1. Follow DEPLOYMENT_GUIDE.md step-by-step
2. Verify each section is clear and actionable
3. Test all commands work as documented
4. Verify troubleshooting steps resolve issues
5. Get feedback from team member (fresh eyes)

---

## Performance Expectations

- Guide should be completable in <2 hours (experienced developer)
- Each step should be verifiable
- No assumptions about prior knowledge

---

## Dependencies

**Blocked By**: Mini-Plans A, B, C, D, E (need to document what was implemented)
**Blocks**: None (documentation)

---

## Notes

- Keep language clear and concise
- Use code blocks for commands
- Include expected output where helpful
- Add warnings for destructive operations
- Provide both Docker and native installation paths
- Include links to external documentation (Auth0, AWS, etc.)
- Add table of contents for easy navigation
- Consider adding diagrams (architecture, deployment flow)

---

## Template Structure

**DEPLOYMENT_GUIDE.md** sections:
1. Introduction
2. Prerequisites (what you need)
3. Quick Start (TL;DR version)
4. Detailed Setup (step-by-step)
5. Configuration (environment variables)
6. Testing (verification steps)
7. Troubleshooting (common issues)
8. Next Steps (production considerations)

**OPERATIONS_RUNBOOK.md** sections:
1. Daily Operations (start, stop, health checks)
2. Monitoring (metrics, logs, traces)
3. Maintenance (backups, migrations, updates)
4. Scaling (horizontal, vertical)
5. Security (secrets, updates, scans)
6. Incident Response (what to do when things break)

**TROUBLESHOOTING.md** sections:
1. Application Issues
2. Database Issues
3. Authentication Issues
4. Observability Issues
5. Performance Issues
6. Network Issues
7. Docker Issues

---

## Example Entry (Troubleshooting)

```markdown
## Issue: Database Migration Fails

**Error Message**:
```

sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "warehouses" does not
exist

```

**Cause**: Alembic migrations have not been run or failed partially.

**Solution**:
1. Check current migration version:
   ```bash
   alembic current
   ```

2. If no version shown, database is empty. Run all migrations:
   ```bash
   alembic upgrade head
   ```

3. If version shown but migrations failed, check logs:
   ```bash
   alembic history
   alembic upgrade head --sql  # See SQL without executing
   ```

4. If issue persists, reset database (DEVELOPMENT ONLY):
   ```bash
   alembic downgrade base
   alembic upgrade head
   ```

**Prevention**: Always run migrations in staging environment first.

```
