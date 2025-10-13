# ============================================
# Multi-stage Dockerfile for DemeterAI v2.0
# Production-ready FastAPI application
# CPU-optimized (default), GPU-enabled (optional)
# ============================================

# Build arguments
ARG PYTHON_VERSION=3.12
ARG APP_ENV=production
ARG ENABLE_GPU=false

# ============================================
# Stage 1: Builder - Install dependencies
# ============================================
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /build

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt .
COPY pyproject.toml .

# Install Python dependencies
# Use --no-cache-dir to reduce image size
# Install in user site to avoid permission issues
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: Runtime - Minimal production image
# ============================================
FROM python:${PYTHON_VERSION}-slim

# Set build argument as environment variable
ARG APP_ENV
ENV APP_ENV=${APP_ENV}

WORKDIR /app

# Install runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && \
    useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app

# Copy installed Python packages from builder stage
# Note: Python 3.12 path is /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

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

# Set Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run FastAPI with uvicorn
# --host 0.0.0.0: Listen on all interfaces (required for Docker)
# --port 8000: Default FastAPI port
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
