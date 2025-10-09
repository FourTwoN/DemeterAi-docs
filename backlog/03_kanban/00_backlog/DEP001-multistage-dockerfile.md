# [DEP001] Multi-stage Dockerfile

## Metadata
- **Epic**: epic-011-deployment
- **Sprint**: Sprint-02
- **Priority**: `critical` ⚡
- **Complexity**: M (5 points)
- **Dependencies**: Blocks [DEP002, DEP003], Blocked by [F002]

## Description
Create optimized multi-stage Dockerfile for production: builder stage (compile dependencies) + runtime stage (slim image).

## Acceptance Criteria
- [ ] Multi-stage build (builder + runtime)
- [ ] Base image: python:3.12-slim
- [ ] Final image size <500MB (without ML models)
- [ ] Non-root user for security
- [ ] Health check included
- [ ] Optimized layer caching (COPY requirements first)

## Implementation
```dockerfile
# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 demeter
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/demeter/.local
ENV PATH=/home/demeter/.local/bin:$PATH

# Copy application code
COPY --chown=demeter:demeter app/ app/

# Switch to non-root user
USER demeter

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Testing
- Build image: `docker build -t demeterai:latest .`
- Verify image size <500MB
- Test health check works
- Run container and test /health endpoint

---
**Card Created**: 2025-10-09
