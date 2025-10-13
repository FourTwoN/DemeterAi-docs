# [F011] Dockerfile - Multi-stage Build for FastAPI

## Metadata
- **Epic**: epic-001-foundation.md
- **Sprint**: Sprint-00 (Week 1-2)
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: L (8 story points)
- **Area**: `foundation`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [F012, DEP001-DEP012]
  - Blocked by: [F001, F002]

## Related Documentation
- **Deployment**: ../../engineering_plan/deployment/README.md
- **Tech Stack**: ../../backlog/00_foundation/tech-stack.md#deployment--containers

## Description

Create production-ready Dockerfile with multi-stage build pattern, optimized layer caching, non-root user execution, and support for both CPU and GPU environments.

**What**: Implement Dockerfile with builder stage (dependencies), runtime stage (minimal image), health check, and proper signal handling. Support Python 3.12, FastAPI, and optional CUDA for GPU workers.

**Why**: Multi-stage builds reduce final image size (70% smaller). Layer caching speeds up builds (only rebuild changed layers). Non-root user improves security. Health checks enable container orchestration.

**Context**: DemeterAI needs separate images for API server (no GPU) and ML workers (optional GPU). Multi-stage build shares base layers. Production image must be <500MB for fast deployment.

## Acceptance Criteria

- [ ] **AC1**: Multi-stage Dockerfile created with builder and runtime stages:
  ```dockerfile
  # Stage 1: Builder
  FROM python:3.12-slim AS builder
  # Install dependencies only

  # Stage 2: Runtime
  FROM python:3.12-slim
  COPY --from=builder ...
  # Minimal runtime image
  ```

- [ ] **AC2**: Non-root user configured:
  ```dockerfile
  RUN groupadd -r appuser && useradd -r -g appuser appuser
  USER appuser
  ```

- [ ] **AC3**: Health check configured:
  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
  ```

- [ ] **AC4**: Environment-specific builds:
  - **Base (CPU)**: ~300MB, no CUDA dependencies
  - **GPU**: ~1.5GB, includes CUDA 12.1 runtime

- [ ] **AC5**: Build arguments for customization:
  ```dockerfile
  ARG PYTHON_VERSION=3.12
  ARG ENABLE_GPU=false
  ARG APP_ENV=production
  ```

- [ ] **AC6**: Image builds successfully:
  ```bash
  # CPU version
  docker build -t demeterai-api:latest .

  # GPU version
  docker build --build-arg ENABLE_GPU=true -t demeterai-ml:latest .
  ```

- [ ] **AC7**: Image runs successfully:
  ```bash
  docker run -p 8000:8000 demeterai-api:latest
  curl http://localhost:8000/health
  # Expected: {"status": "healthy"}
  ```

## Technical Implementation Notes

### Architecture
- Layer: Foundation (Containerization)
- Dependencies: Python 3.12, Docker 24+
- Design pattern: Multi-stage build, immutable infrastructure

### Code Hints

**Dockerfile structure (CPU version):**
```dockerfile
# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml README.md ./
COPY app/ app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e .

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && \
    useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser app/ app/
COPY --chown=appuser:appuser alembic/ alembic/
COPY --chown=appuser:appuser alembic.ini .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Dockerfile.gpu (GPU version):**
```dockerfile
# Base on NVIDIA CUDA runtime
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 AS builder

# Install Python 3.12
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3-pip \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ... rest similar to CPU version
# Plus: Install CUDA-enabled PyTorch
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Runtime stage
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# ... rest similar to CPU runtime
# Plus: CUDA environment variables
ENV CUDA_VISIBLE_DEVICES=0
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

CMD ["celery", "-A", "app.celery_app", "worker", "--pool=solo", "--concurrency=1"]
```

**.dockerignore:**
```
.git
.venv
venv
__pycache__
*.pyc
.pytest_cache
.coverage
htmlcov
.env
.env.*
!.env.example
*.log
logs/
uploads/
processed_images/
.DS_Store
README.md
docs/
tests/
```

### Testing Requirements

**Unit Tests**: N/A (Docker configuration)

**Integration Tests**:
- [ ] Test image builds:
  ```bash
  docker build -t demeterai-test:latest .
  # Expected: Build succeeds, no errors
  ```

- [ ] Test image size:
  ```bash
  docker images demeterai-test:latest
  # Expected: SIZE < 500MB for CPU version
  ```

- [ ] Test container runs:
  ```bash
  docker run -d -p 8000:8000 --name test-api demeterai-test:latest
  sleep 5
  curl http://localhost:8000/health
  docker stop test-api
  # Expected: Health endpoint responds
  ```

- [ ] Test health check:
  ```bash
  docker run -d demeterai-test:latest
  docker inspect --format='{{.State.Health.Status}}' <container_id>
  # Expected: "healthy" after 40s
  ```

- [ ] Test non-root user:
  ```bash
  docker run demeterai-test:latest whoami
  # Expected: "appuser" (not root)
  ```

**Test Command**:
```bash
# Build and test
docker build -t demeterai-test:latest .
docker run -p 8000:8000 demeterai-test:latest
```

### Performance Expectations
- Build time (clean): <5 minutes
- Build time (cached): <30 seconds
- Image size (CPU): <500MB
- Image size (GPU): <1.5GB
- Container startup: <10 seconds
- Health check response: <3 seconds

## Handover Briefing

**For the next developer:**
- **Context**: This is the foundation for deployment - all services run in these containers
- **Key decisions**:
  - Multi-stage build (smaller image, faster deployments)
  - Non-root user (security best practice, required by many K8s clusters)
  - Health check (enables automatic restart in docker-compose/K8s)
  - Separate Dockerfile.gpu (CUDA dependencies add 1GB+)
  - .dockerignore (prevents copying unnecessary files, faster builds)
  - Python 3.12-slim (smaller than full Python image)
- **Known limitations**:
  - GPU image requires NVIDIA Container Toolkit on host
  - Health check requires curl in image (adds 5MB)
  - Multi-stage build doesn't share layers between images (separate pulls)
- **Next steps after this card**:
  - F012: docker-compose.yml (orchestrates multiple containers)
  - DEP001-DEP012: CI/CD builds and pushes images
  - Production: Push images to registry (ECR, Docker Hub)
- **Questions to ask**:
  - Should we use alpine instead of slim? (smaller but compatibility issues)
  - Should we add distroless for security? (no shell, harder debugging)
  - Should we build ARM images for M1/M2 Macs? (multi-platform build)

## Definition of Done Checklist

- [ ] Code passes all tests (pytest)
- [ ] Dockerfile builds successfully
- [ ] Image size meets targets (<500MB CPU, <1.5GB GPU)
- [ ] Container runs and health check passes
- [ ] Non-root user verified
- [ ] .dockerignore created
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated (README.md with Docker commands)
- [ ] Sample docker run command works

## Time Tracking
- **Estimated**: 8 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
