# Docker Build and Deployment Guide

## Overview

DemeterAI v2.0 uses multi-stage Docker builds for production deployment. Two Dockerfiles are provided:

- `Dockerfile` - API server (FastAPI + Uvicorn)
- `Dockerfile.gpu` - ML workers (Celery + YOLO with CUDA support)

## Prerequisites

- Docker 24.0+
- Docker Compose 2.20+ (for orchestration)
- NVIDIA Container Toolkit (for GPU workers only)

## Building Images

### CPU Version (API Server)

```bash
# Build with default settings
docker build -t demeterai-api:latest .

# Build with custom Python version
docker build --build-arg PYTHON_VERSION=3.12 -t demeterai-api:latest .

# Build for development
docker build --build-arg APP_ENV=development -t demeterai-api:dev .
```

### GPU Version (ML Workers)

```bash
# Build GPU-enabled image
docker build -f Dockerfile.gpu -t demeterai-ml:latest .

# Build with custom CUDA version
docker build -f Dockerfile.gpu \
  --build-arg CUDA_VERSION=12.1.0 \
  -t demeterai-ml:latest .
```

## Running Containers

### API Server

```bash
# Run API server
docker run -d \
  --name demeterai-api \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/demeter" \
  -e REDIS_URL="redis://redis:6379/0" \
  -e AWS_ACCESS_KEY_ID="your-key" \
  -e AWS_SECRET_ACCESS_KEY="your-secret" \
  demeterai-api:latest

# Check health
curl http://localhost:8000/health
# Expected: {"status": "healthy", "service": "DemeterAI v2.0"}

# View logs
docker logs -f demeterai-api
```

### ML Workers (GPU)

```bash
# Run ML worker with GPU
docker run -d \
  --name demeterai-ml-worker \
  --gpus all \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/demeter" \
  -e REDIS_URL="redis://redis:6379/0" \
  -e CUDA_VISIBLE_DEVICES=0 \
  demeterai-ml:latest

# Check worker status
docker exec demeterai-ml-worker celery -A app.celery_app inspect active

# View logs
docker logs -f demeterai-ml-worker
```

## Image Details

### Multi-Stage Build Benefits

1. **Smaller final image**: Build dependencies removed (70% size reduction)
2. **Faster deployments**: Only runtime dependencies in final image
3. **Layer caching**: Unchanged layers reused (30s rebuild time)
4. **Security**: Non-root user, minimal attack surface

### Security Features

- Non-root user: `appuser` (UID/GID assigned by system)
- Read-only filesystem compatible
- No secrets in image (use environment variables)
- Minimal base image (python:3.12-slim)

### Health Checks

**API Server**:
- Endpoint: `GET /health`
- Interval: 30s
- Timeout: 3s
- Start period: 40s (application startup time)
- Retries: 3

**ML Workers**:
- Check: Process alive (`pgrep -f celery`)
- Interval: 30s
- Start period: 60s (model loading time)

## Performance

### Build Times

| Build Type | Clean Build | Cached Build | Description |
|------------|-------------|--------------|-------------|
| CPU (API) | ~4 min | ~30s | FastAPI dependencies |
| GPU (ML) | ~8 min | ~45s | CUDA + PyTorch + YOLO |

### Image Sizes

| Image | Size | Description |
|-------|------|-------------|
| demeterai-api:latest | ~6GB* | API server with all dependencies |
| demeterai-ml:latest | ~8GB | ML worker with CUDA runtime |

**Note**: Current image sizes include GPU dependencies in requirements.txt. For production, use separate requirements files:
- `requirements-api.txt` - FastAPI, PostgreSQL, Redis (~300MB)
- `requirements-ml.txt` - Above + PyTorch, YOLO, CUDA (~6GB)

### Runtime Performance

| Metric | Value | Description |
|--------|-------|-------------|
| Container startup | <10s | API ready to serve requests |
| Health check response | <3s | /health endpoint latency |
| Memory usage (API) | ~200MB | Base FastAPI + SQLAlchemy |
| Memory usage (ML) | ~4GB | YOLO model loaded in GPU memory |

## Optimization Tips

### Reduce Image Size

1. **Split requirements files**:
```bash
# requirements-api.txt (minimal)
fastapi==0.118.2
uvicorn==0.34.0
sqlalchemy==2.0.43
asyncpg==0.30.0
pydantic==2.10.0
redis==5.2.0
boto3==1.35.0

# requirements-ml.txt (full ML stack)
-r requirements-api.txt
torch==2.4.0
torchvision==0.19.0
ultralytics==8.3.0
opencv-python==4.9.0.80
```

2. **Use build argument for conditional installation**:
```dockerfile
ARG ENABLE_GPU=false
RUN if [ "$ENABLE_GPU" = "true" ]; then \
      pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121; \
    else \
      pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu; \
    fi
```

### Improve Build Speed

1. **Order COPY commands by change frequency**:
```dockerfile
# Rarely changes (cached)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Frequently changes (rebuild only this layer)
COPY app/ app/
```

2. **Use BuildKit features**:
```bash
# Enable BuildKit for parallel builds
DOCKER_BUILDKIT=1 docker build -t demeterai:latest .
```

3. **Use Docker layer caching in CI/CD**:
```yaml
# .github/workflows/build.yml
- uses: docker/build-push-action@v5
  with:
    cache-from: type=registry,ref=demeterai:buildcache
    cache-to: type=registry,ref=demeterai:buildcache,mode=max
```

## Troubleshooting

### Build fails with "COPY failed"

**Problem**: Python version mismatch in COPY path
```
ERROR: "/usr/local/lib/python3.12.12/site-packages": not found
```

**Solution**: Use hardcoded Python 3.12 path
```dockerfile
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
```

### Container exits immediately

**Problem**: Missing required environment variables

**Solution**: Check logs and provide all required variables
```bash
docker logs demeterai-api
# Error: DATABASE_URL environment variable not set

docker run -e DATABASE_URL="..." demeterai-api:latest
```

### Health check always failing

**Problem**: Application not listening on 0.0.0.0

**Solution**: Verify uvicorn host binding
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### GPU not detected in container

**Problem**: NVIDIA Container Toolkit not installed

**Solution**: Install toolkit and verify
```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Verify GPU access
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

## Next Steps

- **F012**: docker-compose.yml for multi-container orchestration
- **DEP001-DEP012**: CI/CD pipeline for automated builds
- **Production**: Push images to container registry (ECR, Docker Hub, GCR)

## References

- [Docker Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker security best practices](https://docs.docker.com/develop/security-best-practices/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker)
- [FastAPI Docker deployment](https://fastapi.tiangolo.com/deployment/docker/)
