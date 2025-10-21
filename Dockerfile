# ============================================
# Multi-stage Dockerfile for DemeterAI v2.0
# Production-ready FastAPI application
# Optimized for size (<500MB) and security
# ============================================

# Build arguments
ARG PYTHON_VERSION=3.12
ARG APP_ENV=production

# ============================================
# Stage 1: Builder - Install dependencies
# ============================================
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /build

# Install system dependencies for building Python packages
# Keep layer count minimal by chaining commands
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy only dependency files first (better layer caching)
COPY requirements.txt .

# Install Python dependencies to a virtual environment
# Using venv allows us to copy only installed packages to runtime
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    # Remove unnecessary files to reduce size
    find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + || true && \
    find /opt/venv -type f -name "*.pyc" -delete || true && \
    find /opt/venv -type f -name "*.pyo" -delete || true

# ============================================
# Stage 2: Runtime - Minimal production image
# ============================================
FROM python:${PYTHON_VERSION}-slim

# Set build argument as environment variable
ARG APP_ENV
ENV APP_ENV=${APP_ENV}

WORKDIR /app

# Install runtime dependencies only (no build tools)
# Single RUN command reduces layers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
# Using UID/GID that won't conflict with host systems
RUN groupadd -r -g 1000 appuser && \
    useradd -r -u 1000 -g appuser -s /sbin/nologin -c "App User" appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment to use the virtual environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random

# Copy application code with proper ownership
COPY --chown=appuser:appuser app/ app/
COPY --chown=appuser:appuser alembic/ alembic/
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser .env.example .env.example

# Switch to non-root user
USER appuser

# Health check - verify FastAPI is responding
# Interval: Check every 30s
# Timeout: Wait max 3s for response
# Start period: Give 40s for application to start
# Retries: Mark unhealthy after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose FastAPI port
EXPOSE 8000

# Use tini as init process for proper signal handling
# This ensures graceful shutdown on SIGTERM
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run FastAPI with uvicorn (exec form for proper signal handling)
# --host 0.0.0.0: Listen on all interfaces (required for Docker)
# --port 8000: Default FastAPI port
# --workers 1: Single worker (scale with container orchestration)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
