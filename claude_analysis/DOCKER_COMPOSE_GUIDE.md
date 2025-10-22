# Docker Compose Guide - DemeterAI v2.0

This guide explains how to use Docker Compose to run the complete DemeterAI local development
environment.

## Prerequisites

- Docker 20.10+ installed
- Docker Compose V2 installed
- 8GB+ RAM available
- 20GB+ disk space

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start all services
docker compose up -d

# 3. Wait for health checks (30-60 seconds)
docker compose ps

# 4. Run database migrations
docker compose exec api alembic upgrade head

# 5. Test API
curl http://localhost:8000/health
```

## Services

The docker-compose.yml orchestrates the following services:

### 1. PostgreSQL 18 + PostGIS 3.6 (db)

- **Container**: demeterai-db
- **Port**: 5432
- **Image**: postgis/postgis:18-3.6
- **Credentials**:
    - User: demeter
    - Password: demeter_dev_password
    - Database: demeterai
- **Volume**: postgres_data (persists database)
- **Health Check**: pg_isready every 10s

### 2. Redis 7 (redis)

- **Container**: demeterai-redis
- **Port**: 6379
- **Image**: redis:7-alpine
- **Volume**: redis_data (persists cache)
- **Health Check**: redis-cli ping every 5s

### 3. FastAPI Application (api)

- **Container**: demeterai-api
- **Port**: 8000
- **Build**: From local Dockerfile
- **Depends On**: db (healthy), redis (healthy)
- **Health Check**: curl /health endpoint every 30s
- **Features**:
    - Hot-reload enabled (--reload flag)
    - Structured logging with correlation IDs
    - Exception handlers
    - Async database connection pool

### 4. Celery Workers (Coming in Sprint 02+)

Currently commented out - will be enabled when app/celery_app.py is implemented:

- **celery_cpu**: CPU-intensive tasks (prefork pool)
- **celery_io**: I/O-intensive tasks (gevent pool)
- **flower**: Celery monitoring UI (port 5555)

## Common Commands

### Starting Services

```bash
# Start all services in background
docker compose up -d

# Start with logs visible
docker compose up

# Start specific service
docker compose up -d api
```

### Viewing Status

```bash
# List all services and their status
docker compose ps

# Show service logs
docker compose logs

# Follow logs for specific service
docker compose logs -f api

# Show last 50 lines
docker compose logs --tail=50 api
```

### Stopping Services

```bash
# Stop all services (keeps containers and volumes)
docker compose stop

# Stop and remove containers (keeps volumes)
docker compose down

# Stop and remove containers + volumes (CAUTION: deletes data)
docker compose down -v
```

### Running Commands in Containers

```bash
# Run Alembic migrations
docker compose exec api alembic upgrade head

# Check migration status
docker compose exec api alembic current

# Access PostgreSQL shell
docker compose exec db psql -U demeter demeterai

# Access Redis CLI
docker compose exec redis redis-cli

# Run Python shell
docker compose exec api python

# Run tests (when available)
docker compose exec api pytest
```

### Rebuilding Services

```bash
# Rebuild after code changes
docker compose build api

# Rebuild and restart
docker compose up -d --build api

# Force rebuild (no cache)
docker compose build --no-cache api
```

## Environment Variables

Copy `.env.example` to `.env` and adjust values:

```env
# Database (automatically set in docker-compose.yml)
DATABASE_URL=postgresql+asyncpg://demeter:demeter_dev_password@db:5432/demeterai
DATABASE_URL_SYNC=postgresql+psycopg2://demeter:demeter_dev_password@db:5432/demeterai

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Logging
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR
```

## Health Checks

All services have health checks:

```bash
# Check if API is healthy
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"DemeterAI v2.0"}

# Check database
docker compose exec db pg_isready -U demeter
# Expected: /var/run/postgresql:5432 - accepting connections

# Check Redis
docker compose exec redis redis-cli ping
# Expected: PONG
```

## Troubleshooting

### Services won't start

```bash
# Check logs for errors
docker compose logs

# Check specific service
docker compose logs db
docker compose logs redis
docker compose logs api

# Restart services
docker compose restart
```

### API returns 500 errors

```bash
# Check API logs
docker compose logs api

# Verify database connection
docker compose exec api python -c "from app.db.session import test_connection; import asyncio; asyncio.run(test_connection())"
```

### Database connection refused

```bash
# Verify PostgreSQL is healthy
docker compose ps db

# Check PostgreSQL logs
docker compose logs db

# Try connecting manually
docker compose exec db psql -U demeter demeterai
```

### Port already in use

```bash
# Find process using port
sudo lsof -i :8000  # For API
sudo lsof -i :5432  # For PostgreSQL
sudo lsof -i :6379  # For Redis

# Kill process or change port in docker-compose.yml
```

### Out of disk space

```bash
# Remove unused Docker resources
docker system prune -a

# Remove specific volumes (CAUTION: deletes data)
docker volume rm demeterdocs_postgres_data
docker volume rm demeterdocs_redis_data
```

## Development Workflow

### Typical Development Session

```bash
# 1. Start services
docker compose up -d

# 2. Watch logs while developing
docker compose logs -f api

# 3. Code changes auto-reload (--reload flag enabled)
# Just save your files in app/

# 4. Run migrations after schema changes
docker compose exec api alembic revision --autogenerate -m "description"
docker compose exec api alembic upgrade head

# 5. Stop services when done
docker compose stop
```

### Testing Changes

```bash
# Run tests
docker compose exec api pytest

# Run specific test file
docker compose exec api pytest tests/unit/test_example.py

# Run with coverage
docker compose exec api pytest --cov=app --cov-report=term-missing
```

## Production Notes

This docker-compose.yml is for **local development only**. For production:

- Use docker-compose.prod.yml (Sprint 04+)
- Change default passwords
- Use secrets management (Docker secrets, Vault)
- Add nginx reverse proxy
- Enable SSL/TLS
- Configure resource limits
- Use proper logging drivers
- Add monitoring (Prometheus + Grafana)

## Network Architecture

All services run on the `demeterai-network` Docker network:

```
demeterai-network (bridge)
├── demeterai-db (PostgreSQL 18 + PostGIS 3.6)
│   └── Volume: postgres_data
├── demeterai-redis (Redis 7)
│   └── Volume: redis_data
└── demeterai-api (FastAPI)
    ├── Depends: db (healthy), redis (healthy)
    └── Exposes: 8000
```

## Volumes

Persistent data storage:

- **postgres_data**: Database files (/var/lib/postgresql/data)
- **redis_data**: Redis persistence (/data)

To backup volumes:

```bash
# Backup PostgreSQL
docker compose exec db pg_dump -U demeter demeterai > backup.sql

# Restore PostgreSQL
cat backup.sql | docker compose exec -T db psql -U demeter demeterai
```

## Next Steps

- **Sprint 02**: Enable Celery workers (uncomment in docker-compose.yml)
- **Sprint 04**: Create docker-compose.prod.yml
- **Sprint 05**: Add Prometheus + Grafana monitoring

## Support

For issues or questions:

1. Check logs: `docker compose logs`
2. Review this guide
3. Consult engineering documentation: `engineering_plan/README.md`
