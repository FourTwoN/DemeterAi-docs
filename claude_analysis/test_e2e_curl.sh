#!/bin/bash

echo "===================================="
echo "Flujo Principal V3 - Curl Test"
echo "===================================="

# Step 1: Health check
echo ""
echo "[1/5] API Health Check..."
curl -s http://localhost:8000/health | python3 -m json.tool

# Step 2: Get location GPS from container
echo ""
echo "[2/5] Getting location coordinates..."
GPS=$(docker exec demeterai-db psql -U demeter -d demeterai -t -c "SELECT ST_X(coordinates), ST_Y(coordinates) FROM storage_locations LIMIT 1;" 2>/dev/null)
LON=$(echo "$GPS" | awk '{print $1}')
LAT=$(echo "$GPS" | awk '{print $2}')
echo "GPS: lon=$LON, lat=$LAT"

# Step 3: Upload photo
echo ""
echo "[3/5] Uploading photo..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/stock/photo \
    -F "photos=@/tmp/test_image.jpg" \
    -F "gps_longitude=$LON" \
    -F "gps_latitude=$LAT" \
    -F "user_id=1")

echo "$RESPONSE" | python3 -m json.tool

# Extract session ID and task IDs
SESSION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', ''))" 2>/dev/null || echo "")
TASK_IDS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(','.join(json.load(sys.stdin).get('task_ids', [])))" 2>/dev/null || echo "")

echo ""
echo "Session ID: $SESSION_ID"
echo "Task IDs: $TASK_IDS"

# Step 4: Wait for processing
echo ""
echo "[4/5] Waiting for Celery processing (60s)..."
for i in {1..12}; do
    echo -n "."
    sleep 5
done
echo " Done"

# Step 5: Check DB state
echo ""
echo "[5/5] Database state..."
echo "S3 Images:"
docker exec demeterai-db psql -U demeter -d demeterai -c "SELECT COUNT(*) as count FROM s3_images;" 2>/dev/null

echo "Processing Sessions:"
docker exec demeterai-db psql -U demeter -d demeterai -c "SELECT COUNT(*) as count FROM photo_processing_sessions;" 2>/dev/null

echo "Detections:"
docker exec demeterai-db psql -U demeter -d demeterai -c "SELECT COUNT(*) as count FROM detections;" 2>/dev/null

echo ""
echo "Test completed!"
