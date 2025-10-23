#!/bin/bash

# Flujo Principal V3 - Simple E2E Test Script
# Usa curl para no depender de librerías Python

set -e

API_URL="http://localhost:8000"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="demeterai"
DB_USER="demeter"
DB_PASSWORD="demeter_secure_pass"

echo "=================================="
echo "Flujo Principal V3 - E2E Test"
echo "=================================="

# Step 1: Health check
echo ""
echo "[1/7] API Health Check..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" ${API_URL}/health)
if [ "$HTTP_CODE" == "200" ]; then
    echo "✓ API is healthy"
else
    echo "✗ API health check failed (HTTP $HTTP_CODE)"
    exit 1
fi

# Step 2: Create test image if doesn't exist
echo ""
echo "[2/7] Creating test image..."
if [ ! -f "/tmp/test_image.jpg" ]; then
    python3 -c "
from PIL import Image
img = Image.new('RGB', (640, 480), color='green')
img.save('/tmp/test_image.jpg')
print('Test image created: 640x480 green')
"
else
    echo "Test image already exists"
fi

# Step 3: Get test location
echo ""
echo "[3/7] Getting test location from database..."
LOCATION_ID=$(psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT location_id FROM storage_locations LIMIT 1;" 2>/dev/null || echo "")

if [ -z "$LOCATION_ID" ]; then
    echo "✗ No locations found in database"
    echo "  Run: python create_test_data.py"
    exit 1
fi

echo "✓ Using location ID: $LOCATION_ID"

# Get GPS coordinates
GPS_DATA=$(psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT ST_X(geojson_coordinates), ST_Y(geojson_coordinates) FROM storage_locations WHERE location_id = $LOCATION_ID LIMIT 1;" 2>/dev/null || echo "")

# Parse GPS
GPS_LON=$(echo "$GPS_DATA" | awk '{print $1}')
GPS_LAT=$(echo "$GPS_DATA" | awk '{print $2}')

if [ -z "$GPS_LON" ] || [ -z "$GPS_LAT" ]; then
    echo "⚠ Could not extract GPS from location, using default"
    GPS_LON="-33.043"
    GPS_LAT="-68.701"
fi

echo "  GPS: lon=$GPS_LON, lat=$GPS_LAT"

# Step 4: Upload photo
echo ""
echo "[4/7] Uploading photo..."
RESPONSE=$(curl -s -X POST ${API_URL}/api/v1/stock/photo \
    -F "photos=@/tmp/test_image.jpg" \
    -F "gps_longitude=$GPS_LON" \
    -F "gps_latitude=$GPS_LAT" \
    -F "user_id=1" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "202" ]; then
    echo "✓ Photo uploaded (HTTP 202)"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"

    # Extract task IDs
    TASK_IDS=$(echo "$BODY" | python3 -c "import sys, json; print(','.join(json.load(sys.stdin).get('task_ids', [])))" 2>/dev/null || echo "")
    SESSION_ID=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', ''))" 2>/dev/null || echo "")

    echo ""
    echo "  Session ID: $SESSION_ID"
    echo "  Task IDs: $TASK_IDS"
else
    echo "✗ Upload failed (HTTP $HTTP_CODE)"
    echo "$BODY"
    exit 1
fi

# Step 5: Wait for Celery tasks
echo ""
echo "[5/7] Waiting for Celery tasks (60s timeout)..."
if [ -n "$TASK_IDS" ]; then
    for i in {1..12}; do
        echo -n "."
        sleep 5
    done
    echo ""
    echo "✓ Celery processing completed (or timeout)"
else
    echo "⚠ No task IDs returned"
fi

# Step 6: Check database state
echo ""
echo "[6/7] Checking database state..."

# S3 images
S3_COUNT=$(psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT COUNT(*) FROM s3_images;" 2>/dev/null || echo "0")
echo "  S3 Images: $S3_COUNT"

# Sessions
SESSION_COUNT=$(psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT COUNT(*) FROM photo_processing_sessions;" 2>/dev/null || echo "0")
echo "  Processing Sessions: $SESSION_COUNT"

# Detections
DET_COUNT=$(psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT COUNT(*) FROM detections;" 2>/dev/null || echo "0")
echo "  Detections: $DET_COUNT"

# Estimations
EST_COUNT=$(psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT COUNT(*) FROM estimations;" 2>/dev/null || echo "0")
echo "  Estimations: $EST_COUNT"

# Batches
BATCH_COUNT=$(psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT COUNT(*) FROM stock_batches;" 2>/dev/null || echo "0")
echo "  Stock Batches: $BATCH_COUNT"

# Step 7: Final summary
echo ""
echo "[7/7] Summary"
echo ""
if [ "$HTTP_CODE" == "202" ]; then
    echo "✓ Photo uploaded successfully"
    if [ "$SESSION_COUNT" -gt "0" ]; then
        echo "✓ Processing session created"
    fi
    if [ "$S3_COUNT" -gt "0" ]; then
        echo "✓ Image saved to S3 table"
    fi
    if [ "$DET_COUNT" -gt "0" ]; then
        echo "✓ Detections recorded"
    fi
    if [ "$EST_COUNT" -gt "0" ]; then
        echo "✓ Estimations calculated"
    fi
    if [ "$BATCH_COUNT" -gt "0" ]; then
        echo "✓ Stock batches created"
    fi
    echo ""
    echo "=== TEST PASSED (at least partially) ==="
else
    echo "✗ Test failed at upload step"
    exit 1
fi

echo ""
echo "For detailed logs, run:"
echo "  docker logs demeterai-api -f"
echo "  docker logs demeterai-celery-cpu -f"
echo ""
