# Technology Stack - DemeterAI v2.0
## Single Source of Truth for All Versions

**Document Version:** 1.0
**Last Updated:** 2025-10-09
**⚠️ CRITICAL**: This is the ONLY place for technology versions. All cards, docs, and configs reference this file.

---

## Core Principles

1. **Production-Ready**: No experimental or beta libraries
2. **Async-First**: Python async/await for all I/O operations
3. **Type-Safe**: Strong typing with Pydantic + SQLAlchemy 2.0
4. **CPU-First**: ML system works without GPU (GPU = optional 3-5× speedup)
5. **Open Source**: Battle-tested, well-maintained OSS only

---

## Language

### Python 3.12

**Version**: `3.12.x` (latest stable)
**Why**: Latest stable with async improvements, 25% faster than 3.11, native ML library support

**Installation**:
```bash
# Ubuntu/Debian
sudo apt install python3.12 python3.12-venv python3.12-dev

# Verify
python3.12 --version  # Should show 3.12.x
```

---

## Backend Framework & API

### FastAPI 0.118.2

**Version**: `fastapi==0.118.2`
**Released**: September 2025
**Why**: Async-first, auto OpenAPI docs, Pydantic integration, high performance

**Key Dependencies**:
- `uvicorn[standard]==0.34.0` (ASGI server)
- `pydantic==2.10.0` (validation)
- `pydantic-settings==2.6.0` (config management)

**Usage**:
```python
from fastapi import FastAPI, Depends
app = FastAPI(title="DemeterAI v2.0", version="2.0.0")
```

---

## Database

### PostgreSQL 18+

**Version**: `PostgreSQL 18.x`
**⚠️ CRITICAL**: Version **18**, NOT 15 (old docs had 15, now obsolete)
**Why**: Latest stable, improved partitioning, better query planner

**Extensions**:
- **PostGIS 3.3+**: Geospatial queries (4-level hierarchy)
- **pg_partman**: Auto-partition management (daily for detections/estimations)
- **pg_cron**: Schedule partition maintenance
- **pg_stat_statements**: Query performance monitoring

**Installation (Docker)**:
```yaml
# docker-compose.yml
db:
  image: postgis/postgis:18-3.5  # PostgreSQL 18 + PostGIS 3.5
  environment:
    POSTGRES_VERSION: "18"
```

### SQLAlchemy 2.0.43

**Version**: `sqlalchemy==2.0.43`
**Why**: Async no longer beta, 20-30% faster than 1.4, type-safe queries

**Key Features**:
- Async support (`AsyncSession`, `create_async_engine`)
- Type-safe with `select()` construct
- Eager loading (`selectinload`, `joinedload`)

**Driver: asyncpg**

**Version**: `asyncpg==0.30.0`
**Why**: 350× faster bulk inserts than ORM (714k rows/sec vs 2k rows/sec)

**Usage**:
```python
# ORM for CRUD
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/demeterai")

# asyncpg COPY for bulk inserts (1000+ rows)
import asyncpg
pool = await asyncpg.create_pool(DATABASE_URL)
```

---

## Async Processing

### Celery 5.4.0

**Version**: `celery==5.4.0`
**Why**: Chord patterns, DLQ support, retry mechanisms, Flower monitoring

**⚠️ CRITICAL GPU Configuration**:
```bash
# MANDATORY for GPU workers
CUDA_VISIBLE_DEVICES=0 celery -A app worker \
  --pool=solo \              # NOT prefork (causes CUDA conflicts)
  --concurrency=1 \           # 1 task per GPU
  --queues=gpu_queue_0 \
  --max-tasks-per-child=50    # Recycle to prevent memory leaks
```

**Worker Types**:
- **GPU workers**: `pool=solo` (ML inference)
- **CPU workers**: `pool=prefork` (aggregation, batch creation)
- **I/O workers**: `pool=gevent` (S3 uploads, DB writes)

### Redis 7+

**Version**: `redis==5.2.0` (Python client), `redis:7-alpine` (Docker image)
**Why**: Low latency (<1ms), persistence (RDB + AOF), pub/sub

**Usage**:
- Celery broker (task queue)
- Celery result backend (task state)
- Application cache (cache-aside pattern)

---

## Machine Learning (CPU-First)

### ⚡ CRITICAL: CPU-First Design

**DemeterAI runs on CPU by default. GPU is OPTIONAL for 3-5× speedup.**

**Performance**:
- **CPU**: 5-10 minutes per photo (acceptable for batch processing)
- **GPU**: 1-3 minutes per photo (optional speedup)

### Ultralytics YOLO v11

**Version**: `ultralytics==8.3.0`
**Model Version**: YOLO v11 (latest from Ultralytics)
**Why**: 22% fewer params than YOLOv8, 25% faster, CPU-optimized

**Models Used**:
- `yolov11m-seg.pt`: Segmentation (find containers: plugs, boxes, segments)
- `yolov11m.pt`: Detection (count individual plants)

**CPU Optimization**:
```python
from ultralytics import YOLO
model = YOLO('yolov11m-seg.pt')
model.export(format='onnx', opset=12, simplify=True)  # ONNX for CPU
```

### SAHI (Slicing Aided Hyper Inference)

**Version**: `sahi==0.11.18`
**Why**: +6.8% AP improvement for high-res images, handles 4000×3000 photos

**Usage**:
```python
from sahi.predict import get_sliced_prediction
result = get_sliced_prediction(
    image_path,
    detector,
    slice_height=640,
    slice_width=640,
    overlap_height_ratio=0.2,
    overlap_width_ratio=0.2
)
```

### PyTorch

**Version**: `torch==2.4.0` (CPU version by default)
**Installation**:
```bash
# CPU version (default)
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cpu

# GPU version (optional, if CUDA available)
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121
```

---

## Image Processing

### OpenCV 4.10+

**Version**: `opencv-python-headless==4.10.0`
**Why**: Headless = no GUI dependencies (smaller Docker images), optimized C++ core

**Usage**:
- Mask smoothing (morphological operations)
- HSV vegetation filtering
- Image resizing, cropping, format conversion

### Pillow 11.0+

**Version**: `pillow==11.0.0`
**Why**: EXIF extraction (GPS, timestamp), AVIF format support, thumbnail generation

---

## Storage

### AWS S3 (with boto3)

**Version**: `boto3==1.35.0`
**Why**: Unlimited storage, 11 nines durability, lifecycle policies

**Storage Strategy**:
- Original photos: `original/{YYYY}/{MM}/{DD}/{uuid}.jpg` (90-day retention)
- Processed photos: `processed/{YYYY}/{MM}/{DD}/{uuid}_viz.avif` (365-day retention)
- Compression: AVIF format (50% smaller than JPEG)

**Circuit Breaker**:
**Version**: `pybreaker==1.2.0`
```python
import pybreaker
s3_breaker = pybreaker.CircuitBreaker(
    fail_max=5,              # Open after 5 failures
    reset_timeout=60,        # Try recovery after 60s
    success_threshold=3      # Require 3 successes to close
)
```

---

## Authentication & Security

### JWT Tokens

**Version**: `python-jose[cryptography]==3.3.0`
**Why**: Stateless authentication, cryptographic signing

**Configuration**:
- Access token expiration: 15 minutes
- Refresh token expiration: 7 days
- Algorithm: HS256 (symmetric) or RS256 (asymmetric)

### Password Hashing

**Version**: `passlib[bcrypt]==1.7.4`
**Why**: Adaptive work factor, automatic salt generation, industry standard

---

## Testing & Quality

### pytest 8.3+

**Version**: `pytest==8.3.0`
**Why**: Simple API, fixtures, async support

**Key Plugins**:
- `pytest-asyncio==0.24.0` (async test support)
- `pytest-cov==6.0.0` (coverage reporting)
- `pytest-mock==3.14.0` (mocking)
- `httpx==0.27.0` (FastAPI testing client)

**Coverage Target**: ≥80% for all new code

### Ruff 0.7+

**Version**: `ruff==0.7.0`
**Why**: 10-100× faster than Flake8 + Black, all-in-one linter + formatter

**Configuration** (`.ruff.toml`):
```toml
[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line too long (formatter handles)
```

---

## Deployment & Containers

### Docker

**Version**: Docker 24+, Compose 2.x
**Why**: Consistency (dev → staging → prod), isolation, scalability

**Multi-stage build**:
```dockerfile
FROM python:3.12-slim AS builder
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY app/ app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

---

## Monitoring & Observability

### OpenTelemetry

**Version**: `opentelemetry-api==1.25.0`
**Why**: Vendor-neutral distributed tracing, auto-instrumentation

**Key Components**:
- `opentelemetry-instrumentation-fastapi` (FastAPI auto-instrumentation)
- `opentelemetry-instrumentation-celery` (Celery tracing)
- `opentelemetry-exporter-otlp-proto-grpc` (OTLP export)

**Export Target**: Prometheus + Grafana + Tempo/Jaeger stack (external)

### Prometheus Client

**Version**: `prometheus-client==0.20.0`
**Why**: Time-series metrics, pull model, PromQL query language

**Metrics Tracked**:
- API latency (p50, p95, p99)
- ML inference time
- GPU utilization
- Cache hit rate
- Database connection pool

---

## Complete Dependency List

**See**: `04_templates/config-templates/requirements.txt.template` for full list

**Key Versions Summary**:
```txt
# Web Framework
fastapi==0.118.2
uvicorn[standard]==0.34.0
pydantic==2.10.0

# Database
sqlalchemy==2.0.43
asyncpg==0.30.0
alembic==1.14.0

# Async Tasks
celery==5.4.0
redis==5.2.0

# Machine Learning (CPU-First)
ultralytics==8.3.0
opencv-python-headless==4.10.0
torch==2.4.0  # CPU version
sahi==0.11.18

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Storage
boto3==1.35.0

# Testing
pytest==8.3.0
pytest-asyncio==0.24.0
pytest-cov==6.0.0

# Code Quality
ruff==0.7.0
```

---

## Version Update History

| Date | Dependency | Old Version | New Version | Reason |
|------|-----------|-------------|-------------|--------|
| 2025-10-09 | **PostgreSQL** | 15 | **18** | Latest stable, improved partitioning |
| 2025-10-09 | FastAPI | 0.109.0 | **0.118.2** | Latest async improvements |
| 2025-10-09 | SQLAlchemy | 2.0.25 | **0.43** | Async no longer beta |
| 2025-10-09 | Celery | 5.3.6 | **5.4.0** | Stability fixes |

---

## Verification Commands

**Check installed versions**:
```bash
# Python
python3.12 --version

# PostgreSQL
psql --version

# Python packages
pip list | grep -E "(fastapi|sqlalchemy|celery|ultralytics)"

# Docker
docker --version
docker-compose --version
```

---

## References

- **Engineering Plan**: ../../engineering_plan/02_technology_stack.md
- **Past Decisions**: ../../context/past_chats_summary.md (lines 80-95)
- **Requirements Template**: ../../backlog/04_templates/config-templates/requirements.txt.template

---

**Document Owner**: Backend Team Lead
**Update Frequency**: Only on major version changes or new dependencies
**⚠️ Change Protocol**: Update this file FIRST, then propagate to all configs and docs
