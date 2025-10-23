#!/usr/bin/env python3
"""
End-to-End Test Script for Flujo Principal V3

This script tests the complete photo upload workflow:
1. API receives photo
2. GPS location lookup
3. S3 upload
4. Session creation
5. Celery task dispatch
6. ML processing (segmentation)
7. Detection and estimation
8. Batch creation

Run with: python test_e2e_flow_v3.py
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuration
API_URL = "http://localhost:8000"
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "demeterai"
DB_USER = "demeter"
DB_PASSWORD = "demeter_secure_pass"
MAX_WAIT_TIME = 60  # seconds to wait for Celery tasks

# Test image path
TEST_IMAGE_PATH = "/tmp/test_image.jpg"

# Colors for output
COLORS = {
    "GREEN": "\033[92m",
    "RED": "\033[91m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "RESET": "\033[0m",
}


def print_header(text: str) -> None:
    """Print section header."""
    print(f"\n{COLORS['BLUE']}{'='*70}")
    print(f"{text.center(70)}")
    print(f"{'='*70}{COLORS['RESET']}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{COLORS['GREEN']}✓ {text}{COLORS['RESET']}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{COLORS['RED']}✗ {text}{COLORS['RESET']}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{COLORS['YELLOW']}⚠ {text}{COLORS['RESET']}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{COLORS['BLUE']}ℹ {text}{COLORS['RESET']}")


def get_db_connection():
    """Get PostgreSQL connection."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        print_success("Connected to PostgreSQL")
        return conn
    except Exception as e:
        print_error(f"Failed to connect to PostgreSQL: {e}")
        sys.exit(1)


async def check_api_health() -> bool:
    """Check if API is healthy."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    print_success("API is healthy")
                    return True
                else:
                    print_error(f"API health check failed with status {resp.status}")
                    return False
    except Exception as e:
        print_error(f"Failed to connect to API: {e}")
        return False


async def upload_photo(
    gps_longitude: float,
    gps_latitude: float,
    user_id: int = 1,
) -> Optional[dict]:
    """Upload photo via API."""
    if not os.path.exists(TEST_IMAGE_PATH):
        print_error(f"Test image not found at {TEST_IMAGE_PATH}")
        return None

    print_info(f"Uploading photo from {TEST_IMAGE_PATH}")
    print_info(f"GPS coordinates: lon={gps_longitude}, lat={gps_latitude}")

    try:
        with open(TEST_IMAGE_PATH, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("photos", f, filename="test_photo.jpg", content_type="image/jpeg")
            data.add_field("gps_longitude", str(gps_longitude))
            data.add_field("gps_latitude", str(gps_latitude))
            data.add_field("user_id", str(user_id))

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{API_URL}/api/v1/stock/photo",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    response_data = await resp.json()

                    if resp.status == 202:
                        print_success(f"Photo uploaded - Status: {resp.status}")
                        print_info(f"Response: {json.dumps(response_data, indent=2)}")
                        return response_data
                    else:
                        print_error(f"Upload failed with status {resp.status}")
                        print_error(f"Response: {json.dumps(response_data, indent=2)}")
                        return None
    except Exception as e:
        print_error(f"Upload request failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def poll_celery_tasks(task_ids: list[str], max_wait: int = MAX_WAIT_TIME) -> dict:
    """Poll Celery tasks for completion."""
    print_info(f"Polling {len(task_ids)} Celery tasks (max wait: {max_wait}s)")

    start_time = time.time()
    results = {}

    while time.time() - start_time < max_wait:
        try:
            async with aiohttp.ClientSession() as session:
                # Prepare task IDs as comma-separated string
                task_ids_str = ",".join(task_ids)

                async with session.get(
                    f"{API_URL}/api/v1/stock/tasks/status",
                    params={"task_ids": task_ids_str},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        response_data = await resp.json()

                        # Check if all tasks are done
                        all_done = all(
                            task.get("status") in ["SUCCESS", "FAILURE"]
                            for task in response_data.get("tasks", [])
                        )

                        if all_done:
                            print_success("All Celery tasks completed")
                            return response_data
                        else:
                            pending = sum(1 for t in response_data.get("tasks", [])
                                        if t.get("status") not in ["SUCCESS", "FAILURE"])
                            print_info(f"Waiting for {pending} tasks...")
                            await asyncio.sleep(5)
                    else:
                        print_warning(f"Status endpoint returned {resp.status}")
        except Exception as e:
            print_warning(f"Polling error (will retry): {e}")
            await asyncio.sleep(5)

    print_warning("Timeout waiting for Celery tasks")
    return results


def query_database(query: str, params: tuple = ()) -> list[dict]:
    """Execute database query."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in results]
    except Exception as e:
        print_error(f"Database query failed: {e}")
        return []


def verify_database_state(image_id: Optional[str] = None) -> bool:
    """Verify the database state after upload."""
    print_header("Database Verification")

    # Check S3 images table
    print_info("Checking s3_images table...")
    s3_images = query_database(
        "SELECT image_id, status, width_px, height_px, file_size_bytes FROM s3_images ORDER BY created_at DESC LIMIT 5"
    )

    if s3_images:
        print_success(f"Found {len(s3_images)} S3 images")
        for img in s3_images:
            status_color = COLORS["GREEN"] if img["status"] == "ready" else COLORS["YELLOW"]
            print(
                f"  {status_color}{img['image_id']}: {img['status']} "
                f"({img['width_px']}x{img['height_px']}) {img['file_size_bytes']} bytes{COLORS['RESET']}"
            )
    else:
        print_warning("No S3 images found in database")

    # Check photo_processing_sessions table
    print_info("Checking photo_processing_sessions table...")
    sessions = query_database(
        "SELECT id, session_id, status, total_detected, total_estimated FROM photo_processing_sessions ORDER BY created_at DESC LIMIT 5"
    )

    if sessions:
        print_success(f"Found {len(sessions)} processing sessions")
        for sess in sessions:
            print(
                f"  Session {sess['session_id']}: {sess['status']} "
                f"(detected: {sess['total_detected']}, estimated: {sess['total_estimated']})"
            )
    else:
        print_warning("No processing sessions found")

    # Check detections table
    print_info("Checking detections table...")
    detections = query_database(
        "SELECT COUNT(*) as count FROM detections"
    )
    if detections and detections[0]["count"] > 0:
        print_success(f"Found {detections[0]['count']} detections")
    else:
        print_warning("No detections found (may not be processed yet)")

    # Check estimations table
    print_info("Checking estimations table...")
    estimations = query_database(
        "SELECT COUNT(*) as count FROM estimations"
    )
    if estimations and estimations[0]["count"] > 0:
        print_success(f"Found {estimations[0]['count']} estimations")
    else:
        print_warning("No estimations found (may not be processed yet)")

    # Check stock_batches table
    print_info("Checking stock_batches table...")
    batches = query_database(
        "SELECT id, batch_code, quantity_current FROM stock_batches ORDER BY created_at DESC LIMIT 5"
    )
    if batches:
        print_success(f"Found {len(batches)} stock batches")
        for batch in batches:
            print(f"  {batch['batch_code']}: qty={batch['quantity_current']}")
    else:
        print_warning("No stock batches found (may not be created yet)")

    return True


async def main() -> None:
    """Main test execution."""
    print_header("Flujo Principal V3 - End-to-End Test")

    # Check if test image exists
    if not os.path.exists(TEST_IMAGE_PATH):
        print_error(f"Test image not found at {TEST_IMAGE_PATH}")
        print_info("Create a test image first:")
        print_info("  python -c \"from PIL import Image; img = Image.new('RGB', (640, 480), color='green'); img.save('/tmp/test_image.jpg')\"")
        sys.exit(1)

    # Step 1: API Health Check
    print_header("Step 1: API Health Check")
    if not await check_api_health():
        print_error("API is not healthy. Cannot continue.")
        sys.exit(1)

    # Step 2: Database Connection
    print_header("Step 2: Database Connection")
    conn = get_db_connection()
    conn.close()

    # Step 3: Get test location
    print_header("Step 3: Find Test Location")
    locations = query_database(
        "SELECT location_id, code, name FROM storage_locations LIMIT 1"
    )

    if not locations:
        print_error("No storage locations found in database")
        print_info("Run create_test_data.py first to populate test data")
        sys.exit(1)

    test_location = locations[0]
    print_success(f"Using location: {test_location['code']} (ID: {test_location['location_id']})")

    # Get GPS coordinates for this location
    gps_data = query_database(
        "SELECT ST_X(geojson_coordinates) as longitude, ST_Y(geojson_coordinates) as latitude FROM storage_locations WHERE location_id = %s",
        (test_location["location_id"],),
    )

    if gps_data:
        gps_lon = gps_data[0]["longitude"]
        gps_lat = gps_data[0]["latitude"]
        print_success(f"GPS Coordinates: lon={gps_lon}, lat={gps_lat}")
    else:
        print_error("Could not extract GPS coordinates from location")
        gps_lon, gps_lat = -33.043, -68.701  # Default test coordinates

    # Step 4: Upload Photo
    print_header("Step 4: Upload Photo")
    upload_response = await upload_photo(gps_lon, gps_lat, user_id=1)

    if not upload_response:
        print_error("Photo upload failed")
        sys.exit(1)

    # Extract task IDs from response
    task_ids = upload_response.get("task_ids", [])
    session_id = upload_response.get("session_id")
    print_success(f"Session ID: {session_id}")
    print_success(f"Task IDs: {task_ids}")

    # Step 5: Poll Celery Tasks
    print_header("Step 5: Wait for Celery Tasks")
    if task_ids:
        celery_results = await poll_celery_tasks(task_ids)
        print_info(f"Celery results: {json.dumps(celery_results, indent=2)}")
    else:
        print_warning("No task IDs returned from API")

    # Step 6: Wait a bit more for DB writes
    print_header("Step 6: Waiting for Database Writes")
    print_info("Waiting 5 seconds for database writes...")
    await asyncio.sleep(5)

    # Step 7: Verify Database State
    verify_database_state(session_id)

    # Final Report
    print_header("Test Complete")
    print_success("End-to-end flow execution completed")
    print_info("Check logs for any errors:")
    print_info("  docker logs demeterai-api | tail -50")
    print_info("  docker logs demeterai-celery-cpu | tail -50")


if __name__ == "__main__":
    # Create test image if it doesn't exist
    if not os.path.exists(TEST_IMAGE_PATH):
        print_info("Creating test image...")
        try:
            from PIL import Image
            img = Image.new("RGB", (640, 480), color="green")
            img.save(TEST_IMAGE_PATH)
            print_success(f"Test image created: {TEST_IMAGE_PATH}")
        except Exception as e:
            print_error(f"Failed to create test image: {e}")

    # Run async main
    asyncio.run(main())
