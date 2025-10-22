# [DEP003] GPU Worker Docker Image

## Metadata

- **Epic**: epic-011-deployment
- **Sprint**: Sprint-02
- **Priority**: `high`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [DEP001]

## Description

Create specialized Dockerfile for GPU workers with CUDA support. Based on nvidia/cuda base image.

## Acceptance Criteria

- [ ] Base image: nvidia/cuda:12.1.0-runtime-ubuntu22.04
- [ ] CUDA 12.1+ support
- [ ] PyTorch with CUDA support
- [ ] Ultralytics YOLO GPU-enabled
- [ ] Image size <2GB
- [ ] Test with nvidia-smi

## Implementation

```dockerfile
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Install Python 3.12
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install GPU-enabled packages
COPY requirements-gpu.txt .
RUN pip install --no-cache-dir -r requirements-gpu.txt

COPY app/ app/

CMD ["celery", "-A", "app", "worker", "--pool=solo", "--concurrency=1"]
```

**requirements-gpu.txt:**

```
torch==2.4.0+cu121
torchvision==0.19.0+cu121
ultralytics==8.3.0
# ... other deps
```

## Testing

- Build: `docker build -f Dockerfile.gpu -t demeterai-gpu .`
- Test CUDA: `docker run --gpus all demeterai-gpu nvidia-smi`
- Verify PyTorch sees GPU: `python -c "import torch; print(torch.cuda.is_available())"`

---
**Card Created**: 2025-10-09
