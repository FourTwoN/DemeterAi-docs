# Technology Stack - DemeterAI v2.0

**Document Version:** 1.0
**Last Updated:** 2025-10-08

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Language](#language)
3. [Backend Framework & API](#backend-framework--api)
4. [Database Layer](#database-layer)
5. [Async Processing](#async-processing)
6. [Machine Learning (CPU-First Approach)](#machine-learning-cpu-first-approach)
7. [Image Processing](#image-processing)
8. [Storage](#storage)
9. [Authentication & Security](#authentication--security)
10. [Testing & Quality](#testing--quality)
11. [Deployment & Containers](#deployment--containers)
12. [Monitoring & Observability](#monitoring--observability)
13. [Complete Dependency List](#complete-dependency-list)

---

## Core Principles

### Technology Selection Criteria

1. **Production-Ready:** No experimental or beta libraries
2. **Async-First:** Embrace Python async/await for concurrency
3. **Type-Safe:** Strong typing with Pydantic + SQLAlchemy 2.0
4. **CPU-First:** System must work without GPU (GPU optional for speedup)
5. **Open Source:** Prefer battle-tested, well-maintained OSS
6. **Performance:** Prioritize fast libraries (asyncpg, SAHI, Redis)

---

## Language

### Python 3.12

**Version:** 3.12.x (latest stable)

**Why Python 3.12:**
- ✅ Latest stable release with async/await improvements
- ✅ Type hints improvements (PEP 695 generic syntax)
- ✅ 25% faster than Python 3.11 (CPython optimizations)
- ✅ Native support for all ML libraries (YOLO, OpenCV, SAHI)
- ✅ Excellent ecosystem for data science and ML

**Alternatives Considered:**
- ❌ Go: Poor ML library support, no async ORM comparable to SQLAlchemy
- ❌ Rust: Steep learning curve, immature ML ecosystem
- ❌ Node.js: Weak ML/CV libraries, async patterns less mature

---

## Backend Framework & API

### FastAPI 0.118.0

**Version:** 0.118.0 (released September 2025)
**Updated from:** 0.109.0 → 0.118.0

**Why FastAPI:**
- ✅ **Async-first:** Built on Starlette, fully async/await compatible
- ✅ **Auto OpenAPI docs:** Interactive docs at `/docs` out of the box
- ✅ **Pydantic integration:** Type-safe request/response validation
- ✅ **Performance:** One of the fastest Python frameworks (comparable to Node/Go)
- ✅ **Developer experience:** Intuitive API, excellent error messages

**Key Features We Use:**
- Background tasks (Celery integration)
- Dependency injection (database sessions, auth)
- WebSocket support (future: real-time updates)
- File uploads (multipart form data for photos)
- Query parameter validation

**2025 Best Practices:**
- Use `async def` for all I/O-bound operations (DB, S3, Redis)
- Use `def` for CPU-bound ops (FastAPI runs them in thread pool)
- Avoid blocking the event loop (no sync DB calls in async routes)

**Example:**
```python
from fastapi import FastAPI, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

@app.post("/stock/photo")
async def upload_photo(
    file: UploadFile,
    session: AsyncSession = Depends(get_db_session)
):
    # Async I/O - does not block event loop
    photo = await session.execute(select(PhotoSession).where(...))
    return {"status": "processing"}
```

---

## Database Layer

### PostgreSQL 15+

**Version:** PostgreSQL 15.x (with PostGIS 3.3+)

**Why PostgreSQL:**
- ✅ **ACID compliance:** Transactional integrity for inventory data
- ✅ **PostGIS:** Best-in-class geospatial queries (point-in-polygon for GPS)
- ✅ **Partitioning:** Native table partitioning for detections/estimations
- ✅ **JSONB:** Efficient storage for flexible metadata
- ✅ **Performance:** Excellent query planner, mature indexing

**PostGIS 3.3+ for Geospatial:**
- SP-GiST indexes for non-overlapping polygons (warehouse hierarchy)
- ST_Contains for GPS → storage_location lookup
- Centroid generation, area calculations

**Partitioning Strategy:**
- Daily partitions for `detections` and `estimations` (high volume)
- Partition pruning: 10-100× faster queries when filtering by date
- Auto-maintenance with pg_partman extension

### SQLAlchemy 2.0.43

**Version:** 2.0.43 (released August 2025)
**Updated from:** 2.0.25 → 2.0.43

**Why SQLAlchemy 2.0:**
- ✅ **Async support:** First-class asyncio integration (no longer beta)
- ✅ **Type-safe:** Improved type hints, mypy compatible
- ✅ **Performance:** 20-30% faster than 1.4 for complex queries
- ✅ **Modern API:** `select()` construct, better eager loading

**Async Driver: asyncpg**

**Why asyncpg:**
- ✅ **350× faster bulk inserts** than ORM (714k rows/sec vs 2k rows/sec)
- ✅ **COPY protocol:** Native PostgreSQL bulk load
- ✅ **Connection pooling:** Built-in efficient pool management

**Usage Pattern:**
- ORM for CRUD operations (repository pattern)
- asyncpg COPY for bulk inserts (detections/estimations after ML processing)

**Example:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import selectinload

# Async engine
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/demeterai",
    pool_size=20,
    max_overflow=10,
    echo=False
)

# Async query with eager loading (prevent N+1)
async with AsyncSession(engine) as session:
    result = await session.execute(
        select(PhotoSession)
        .options(
            joinedload(PhotoSession.storage_location),
            selectinload(PhotoSession.detections)
        )
    )
    sessions = result.unique().scalars().all()
```

---

## Async Processing

### Celery 5.3+

**Version:** Celery 5.3.6+

**Why Celery:**
- ✅ **Chord pattern:** Parent task → multiple child tasks → callback
- ✅ **DLQ support:** Dead letter queue for failed tasks
- ✅ **Retry mechanisms:** Exponential backoff, max retries
- ✅ **Monitoring:** Integration with Flower, Prometheus

**Critical Configuration for GPU Workers:**
```python
# MANDATORY: pool=solo, concurrency=1 per GPU
# Reason: CUDA context conflicts with prefork/gevent
CUDA_VISIBLE_DEVICES=0 celery -A app worker \
  --pool=solo \
  --concurrency=1 \
  --queues=gpu_queue_0 \
  --max-tasks-per-child=50  # Recycle to prevent memory leaks
```

**Worker Types:**
1. **GPU Workers** (`pool=solo`): ML inference (segmentation, detection)
2. **CPU Workers** (`pool=prefork`): Aggregation, batch creation
3. **I/O Workers** (`pool=gevent`): S3 uploads, database writes

### Redis 7+

**Version:** Redis 7.x

**Why Redis:**
- ✅ **Low latency:** <1ms for task coordination
- ✅ **Persistence:** RDB + AOF for durability
- ✅ **Pub/Sub:** Task status updates
- ✅ **Caching:** Used for storage_location_config, density_parameters

**Usage:**
- Celery broker (task queue)
- Celery result backend (task state)
- Application cache (cache-aside pattern)

---

## Machine Learning (CPU-First Approach)

### ⚡ CRITICAL: CPU-First Design

**DemeterAI is designed to run on CPU by default. GPU is optional for 3-5× speedup, NOT required.**

**Why CPU-First:**
- ✅ **Accessibility:** No expensive GPU hardware required
- ✅ **Cost:** Cloud CPU instances 10× cheaper than GPU
- ✅ **Reliability:** No CUDA driver issues, easier deployment
- ✅ **Scalability:** Horizontal scaling easier with CPU workers

**Performance:**
- **CPU:** 5-10 minutes per photo (acceptable for batch processing)
- **GPU:** 1-3 minutes per photo (3-5× speedup)
- **Target:** Process 600k photos in 8-14 hours (4× A100 GPUs) or 40-80 hours (CPU cluster)

### Ultralytics YOLO v11

**Version:** YOLO v11 (latest from Ultralytics)

**Why YOLO v11:**
- ✅ **22% fewer parameters** than YOLOv8 (faster on CPU)
- ✅ **25% faster inference** than YOLOv8
- ✅ **Segmentation + Detection:** Both models in one framework
- ✅ **CPU-optimized:** Works well on CPU with ONNX/OpenVINO export
- ✅ **Active development:** Ultralytics maintains excellent docs

**Models We Use:**
- `yolov11m-seg.pt`: Segmentation (find containers: plugs, boxes, segments)
- `yolov11m.pt`: Detection (count individual plants)

**Optimization for CPU:**
```python
from ultralytics import YOLO

model = YOLO('yolov11m-seg.pt')

# Export to ONNX for CPU optimization
model.export(format='onnx', opset=12, simplify=True)

# Inference on CPU
results = model.predict(
    'photo.jpg',
    imgsz=1024,
    conf=0.30,
    device='cpu',  # CPU mode
    half=False     # FP32 for CPU (FP16 only on GPU)
)
```

### SAHI (Slicing Aided Hyper Inference)

**Version:** Latest stable

**Why SAHI:**
- ✅ **+6.8% AP improvement** for high-resolution images
- ✅ **Handles 4000×3000 photos:** Slices into 640×640 tiles
- ✅ **Automatic NMS:** Merges overlapping detections across slices
- ✅ **Easy integration:** Wraps YOLO models seamlessly

**Usage:**
```python
from sahi.predict import get_sliced_prediction
from sahi import AutoDetectionModel

detector = AutoDetectionModel.from_pretrained(
    model_type='ultralytics',
    model_path='yolov11m.pt',
    confidence_threshold=0.25,
    device='cpu'  # CPU mode
)

result = get_sliced_prediction(
    image_path,
    detector,
    slice_height=640,
    slice_width=640,
    overlap_height_ratio=0.2,
    overlap_width_ratio=0.2
)
```

---

## Image Processing

### OpenCV 4.9+

**Version:** opencv-python-headless 4.9.0.80

**Why OpenCV:**
- ✅ **Industry standard:** Most battle-tested CV library
- ✅ **Headless:** No GUI dependencies (smaller Docker images)
- ✅ **Performance:** Optimized C++ core, Python bindings
- ✅ **Complete toolset:** Image filters, morphology, color space conversion

**Usage:**
- Mask smoothing (morphological operations)
- HSV vegetation filtering (remove bare soil)
- Image resizing, cropping, format conversion

### Pillow 10.2+

**Version:** Pillow 10.2.0

**Why Pillow:**
- ✅ **EXIF extraction:** GPS coordinates, timestamp, camera info
- ✅ **Format support:** JPEG, PNG, AVIF, WebP
- ✅ **Thumbnail generation:** 400×400 previews

---

## Storage

### AWS S3 (with boto3)

**Why S3:**
- ✅ **Scalability:** Unlimited storage
- ✅ **Durability:** 99.999999999% (11 nines)
- ✅ **Lifecycle policies:** Auto-delete old originals after 90 days
- ✅ **Versioning:** Keep previous versions if needed

**Storage Strategy:**
- **Original photos:** `original/{YYYY}/{MM}/{DD}/{uuid}.jpg` (90-day retention)
- **Processed photos:** `processed/{YYYY}/{MM}/{DD}/{uuid}_viz.avif` (365-day retention)
- **Compression:** AVIF format (50% smaller than JPEG, same quality)

**Circuit Breaker:**
```python
import pybreaker

s3_breaker = pybreaker.CircuitBreaker(
    fail_max=5,              # Open after 5 failures
    reset_timeout=60,        # Try recovery after 60s
    success_threshold=3      # Require 3 successes to close
)

@s3_breaker
def upload_to_s3(file, bucket, key):
    return s3_client.upload_file(file, bucket, key)
```

---

## Authentication & Security

### JWT Tokens (python-jose)

**Version:** python-jose[cryptography] 3.3.0

**Why JWT:**
- ✅ **Stateless:** No session storage needed
- ✅ **Secure:** Cryptographic signing (RS256 or HS256)
- ✅ **Standard:** Industry-standard format

**Configuration:**
- Token expiration: 15 minutes (access), 7 days (refresh)
- Algorithm: HS256 (symmetric) or RS256 (asymmetric)
- Rotation: Secret rotation every 90 days

### Password Hashing (passlib + bcrypt)

**Version:** passlib[bcrypt] 1.7.4

**Why bcrypt:**
- ✅ **Adaptive:** Configurable work factor (prevents brute force)
- ✅ **Industry standard:** Used by GitHub, Heroku, etc.
- ✅ **Salt included:** Automatic salt generation

---

## Testing & Quality

### pytest 8.0+

**Version:** pytest 8.0.0

**Why pytest:**
- ✅ **Simple API:** Cleaner than unittest
- ✅ **Fixtures:** Reusable test setup
- ✅ **Async support:** pytest-asyncio for async tests
- ✅ **Coverage:** pytest-cov integration

**Testing Strategy:**
- Unit tests: 80%+ coverage target
- Integration tests: Full pipeline with test photos
- Mocking: pytest-mock for external services

### Ruff 0.1.14

**Version:** Ruff 0.1.14

**Why Ruff:**
- ✅ **Fast:** 10-100× faster than Flake8 + Black
- ✅ **All-in-one:** Linter + formatter
- ✅ **Compatible:** Drop-in replacement for Flake8, isort, Black

**Configuration:**
```toml
[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line too long (let formatter handle)
```

---

## Deployment & Containers

### Docker + Docker Compose

**Version:** Docker 24+, Compose 2.x

**Why Docker:**
- ✅ **Consistency:** Same environment dev → staging → prod
- ✅ **Isolation:** Dependencies contained
- ✅ **Scalability:** Easy horizontal scaling

**Multi-stage build:**
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

### Prometheus + Grafana

**Why Prometheus:**
- ✅ **Time-series DB:** Ideal for metrics
- ✅ **Pull model:** No client-side buffering
- ✅ **PromQL:** Powerful query language

**Metrics We Track:**
- API latency (p50, p95, p99)
- ML inference time
- GPU utilization
- Cache hit rate
- Database connection pool

### OpenTelemetry (Future)

**Why OpenTelemetry:**
- ✅ **Distributed tracing:** See full request flow (API → Celery → DB)
- ✅ **Vendor-neutral:** Export to Jaeger, Zipkin, or commercial APMs
- ✅ **Auto-instrumentation:** FastAPI + Celery plugins

---

## Complete Dependency List

### Core Dependencies (requirements.txt)

```txt
# Web Framework
fastapi==0.118.0
uvicorn[standard]==0.34.0
pydantic==2.10.0
pydantic-settings==2.6.0

# Database
sqlalchemy==2.0.43
asyncpg==0.30.0
psycopg2-binary==2.9.10
alembic==1.14.0

# Async Tasks
celery==5.4.0
redis==5.2.0

# Machine Learning (CPU-First)
ultralytics==8.3.0
opencv-python-headless==4.10.0
numpy==2.0.0
pillow==11.0.0
torch==2.4.0  # CPU version by default
torchvision==0.19.0
sahi==0.11.18

# Image Processing
scikit-image==0.24.0

# Geolocation
shapely==2.0.6

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Excel/CSV
openpyxl==3.1.2
pandas==2.2.3

# Storage
boto3==1.35.0

# Circuit Breaker
pybreaker==1.2.0

# Testing
pytest==8.3.0
pytest-asyncio==0.24.0
pytest-cov==6.0.0
pytest-mock==3.14.0
httpx==0.27.0

# Code Quality
ruff==0.7.0

# Utilities
python-dateutil==2.9.0
pyyaml==6.0.1
```

---

## Version Update Summary (2025-10-08)

| Dependency | Old Version | New Version | Notes |
|-----------|-------------|-------------|-------|
| **FastAPI** | 0.109.0 | **0.118.0** | Latest async improvements |
| **SQLAlchemy** | 2.0.25 | **2.0.43** | Async no longer beta |
| **Pydantic** | 2.5.3 | **2.10.0** | Performance improvements |
| **Celery** | 5.3.6 | **5.4.0** | Stability fixes |
| **Redis** | 5.0.1 | **5.2.0** | Async client improvements |
| **Ultralytics** | 8.1.20 | **8.3.0** | YOLO v11 support |
| **OpenCV** | 4.9.0 | **4.10.0** | Bug fixes |
| **NumPy** | 1.26.3 | **2.0.0** | Major release |
| **pytest** | 8.0.0 | **8.3.0** | Async test improvements |
| **Ruff** | 0.1.14 | **0.7.0** | Faster linting |

---

## Next Steps

- **Read:** [Architecture Overview](./03_architecture_overview.md) to understand system structure
- **Dive Deeper:** [Backend ML Pipeline](./backend/ml_pipeline.md) for CPU-first implementation details

---

**Document Owner:** DemeterAI Engineering Team
**Review Cycle:** Quarterly (verify latest stable versions)
**Last Verified:** 2025-10-08
