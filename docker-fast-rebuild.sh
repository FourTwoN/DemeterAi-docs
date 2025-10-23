#!/bin/bash
# Fast Docker rebuild script for DemeterAI v2.0
# This script optimizes rebuild times for development

set -e

echo "🚀 DemeterAI Fast Rebuild"
echo "=========================="

# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Check what changed to decide rebuild strategy
if git diff --quiet HEAD -- requirements.txt; then
    echo "✅ Requirements unchanged - using cached dependencies"
    CACHE_STRATEGY="--build"
else
    echo "⚠️  Requirements changed - full rebuild needed"
    CACHE_STRATEGY="--build --no-cache"
fi

# Check if only app code changed (fastest rebuild)
if git diff --quiet HEAD -- app/ alembic/ && [ "$CACHE_STRATEGY" == "--build" ]; then
    echo "📦 Only non-code files changed - super fast rebuild"
    docker compose up -d --build --no-deps api celery_cpu celery_gpu celery_io flower
else
    echo "🔨 Rebuilding with cache optimization..."
    docker compose up -d $CACHE_STRATEGY
fi

echo ""
echo "✅ Rebuild complete!"
echo ""
echo "📊 Quick status check:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
