#!/usr/bin/env python
"""
Comprehensive E2E Test Runner for Photo Upload Flow V3

This script executes a REAL end-to-end test against the running system:
1. Creates test data in database (warehouse, location, user, products, densities)
2. Submits photo via HTTP POST to /api/v1/stock/photo
3. Monitors Celery task execution
4. Verifies database state after completion
5. Generates comprehensive report

Requirements:
- Docker services running (db, api, celery_cpu, celery_io, redis, flower)
- Test image at /tmp/test_image.jpg
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, Polygon
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent))

from app.models.density_parameter import DensityParameter
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.product_family import ProductFamily
from app.models.storage_area import StorageArea
from app.models.storage_location import StorageLocation
from app.models.storage_location_config import StorageLocationConfig
from app.models.user import User
from app.models.warehouse import Warehouse

DATABASE_URL = "postgresql+asyncpg://demeter:demeter_dev_password@localhost:5432/demeterai"
API_BASE_URL = "http://localhost:8000"
FLOWER_URL = "http://localhost:5555"
TEST_IMAGE_PATH = "/tmp/test_image.jpg"


class Colors:
    """Terminal color codes."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(message: str):
    """Print formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}\n")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def print_info(message: str):
    """Print info message."""
    print(f"  {message}")


async def setup_test_data():
    """Create complete test data in database."""
    print_header("STEP 1: Creating Test Data")

    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with AsyncSession(engine) as session:
            # 1. Create warehouse
            wh_polygon = Polygon(
                [(-70.75, -33.55), (-70.55, -33.55), (-70.55, -33.35), (-70.75, -33.35), (-70.75, -33.55)]
            )
            warehouse = Warehouse(
                code="WH-E2E-TEST",
                name="E2E Test Warehouse",
                warehouse_type="greenhouse",
                geojson_coordinates=from_shape(wh_polygon, srid=4326),
                active=True,
            )
            session.add(warehouse)
            await session.flush()
            print_success(f"Created warehouse: {warehouse.code} (ID={warehouse.warehouse_id})")

            # 2. Create storage area
            sa_polygon = Polygon(
                [(-70.70, -33.50), (-70.60, -33.50), (-70.60, -33.40), (-70.70, -33.40), (-70.70, -33.50)]
            )
            storage_area = StorageArea(
                warehouse_id=warehouse.warehouse_id,
                code="SA-E2E-TEST",
                name="E2E Test Area",
                position="C",
                geojson_coordinates=from_shape(sa_polygon, srid=4326),
                active=True,
            )
            session.add(storage_area)
            await session.flush()
            print_success(f"Created storage area: {storage_area.code} (ID={storage_area.storage_area_id})")

            # 3. Create storage location (INSIDE area polygon)
            loc_point = Point(-70.650, -33.450)  # lon, lat (inside SA polygon)
            storage_location = StorageLocation(
                storage_area_id=storage_area.storage_area_id,
                code="LOC-E2E-TEST",
                qr_code="QR-LOC-E2E-TEST",
                name="E2E Test Location",
                description="E2E test storage location",
                coordinates=from_shape(loc_point, srid=4326),
                active=True,
            )
            session.add(storage_location)
            await session.flush()
            print_success(f"Created storage location: {storage_location.code} (ID={storage_location.location_id})")
            print_info(f"  GPS coordinates: longitude={-70.650}, latitude={-33.450}")

            # 4. Create user
            user = User(
                email="e2e.test@demeterai.com",
                password_hash="$2b$12$testhashdummy",  # dummy hash
                first_name="E2E",
                last_name="Test User",
                role="worker",
                active=True,
            )
            session.add(user)
            await session.flush()
            print_success(f"Created user: {user.email} (ID={user.id})")

            # 5. Create product taxonomy (category → family → product)
            category = ProductCategory(
                code="CAT-E2E-TEST",
                name="E2E Test Category",
                description="Test category for E2E testing",
            )
            session.add(category)
            await session.flush()
            print_success(f"Created product category: {category.code} (ID={category.category_id})")

            family = ProductFamily(
                category_id=category.category_id,
                code="FAM-E2E-TEST",
                name="E2E Test Family",
                description="Test family for E2E testing",
            )
            session.add(family)
            await session.flush()
            print_success(f"Created product family: {family.code} (ID={family.family_id})")

            product = Product(
                family_id=family.family_id,
                sku="PROD-E2E-TEST",
                common_name="Test Product",
                scientific_name="Testus Productus",
                description="Test product for E2E testing",
            )
            session.add(product)
            await session.flush()
            print_success(f"Created product: {product.sku} (ID={product.id})")

            # 6. Create density parameter
            density_param = DensityParameter(
                product_id=product.id,
                min_density_per_m2=10.0,
                max_density_per_m2=50.0,
                optimal_density_per_m2=30.0,
            )
            session.add(density_param)
            await session.flush()
            print_success(f"Created density parameter (ID={density_param.id})")

            # 7. Create storage location config
            config = StorageLocationConfig(
                storage_location_id=storage_location.location_id,
                product_id=product.id,
                expected_density_per_m2=30.0,
                threshold_min_density=10.0,
                threshold_max_density=50.0,
            )
            session.add(config)
            await session.flush()
            print_success(f"Created storage location config (ID={config.id})")

            await session.commit()

            return {
                "warehouse_id": warehouse.warehouse_id,
                "storage_area_id": storage_area.storage_area_id,
                "storage_location_id": storage_location.location_id,
                "user_id": user.id,
                "product_id": product.id,
                "gps_longitude": -70.650,
                "gps_latitude": -33.450,
            }

    finally:
        await engine.dispose()


async def submit_photo(test_data: dict):
    """Submit photo via HTTP POST to API."""
    print_header("STEP 2: Submitting Photo via HTTP POST")

    # Check if test image exists
    if not Path(TEST_IMAGE_PATH).exists():
        print_error(f"Test image not found at {TEST_IMAGE_PATH}")
        return None

    print_info(f"Using test image: {TEST_IMAGE_PATH}")
    print_info(f"Image size: {Path(TEST_IMAGE_PATH).stat().st_size / 1024 / 1024:.2f} MB")
    print_info(f"GPS: longitude={test_data['gps_longitude']}, latitude={test_data['gps_latitude']}")
    print_info(f"User ID: {test_data['user_id']}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(TEST_IMAGE_PATH, "rb") as f:
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/stock/photo",
                    files={"file": ("test_image.jpg", f, "image/jpeg")},
                    data={
                        "longitude": str(test_data["gps_longitude"]),
                        "latitude": str(test_data["gps_latitude"]),
                        "user_id": str(test_data["user_id"]),
                    },
                )

        print_info(f"Response status: {response.status_code}")

        if response.status_code == 202:
            response_data = response.json()
            print_success("Photo submitted successfully!")
            print_info(f"  Task ID: {response_data.get('task_id')}")
            print_info(f"  Session ID: {response_data.get('session_id')}")
            print_info(f"  Status: {response_data.get('status')}")
            print_info(f"  Poll URL: {response_data.get('poll_url')}")
            return response_data
        else:
            print_error(f"API returned status {response.status_code}")
            print_error(f"Response: {response.text}")
            return None

    except Exception as e:
        print_error(f"Failed to submit photo: {str(e)}")
        return None


async def monitor_celery_task(task_id: str, timeout: int = 60):
    """Monitor Celery task via Flower API."""
    print_header("STEP 3: Monitoring Celery Task Execution")

    print_info(f"Task ID: {task_id}")
    print_info(f"Flower URL: {FLOWER_URL}")
    print_info(f"Timeout: {timeout} seconds")

    start_time = time.time()
    last_state = None

    try:
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get(f"{FLOWER_URL}/api/task/info/{task_id}")
                    if response.status_code == 200:
                        task_info = response.json()
                        current_state = task_info.get("state")

                        if current_state != last_state:
                            print_info(f"  Task state: {current_state}")
                            last_state = current_state

                        if current_state in ["SUCCESS", "FAILURE"]:
                            if current_state == "SUCCESS":
                                print_success("Celery task completed successfully!")
                                return True
                            else:
                                print_error(f"Celery task failed: {task_info.get('result')}")
                                return False

                except httpx.RequestError:
                    print_warning("Flower API not accessible, continuing...")

                await asyncio.sleep(2)

            print_warning(f"Task monitoring timed out after {timeout} seconds")
            return None

    except Exception as e:
        print_error(f"Error monitoring task: {str(e)}")
        return None


async def verify_database_state(test_data: dict, session_id: int):
    """Verify database state after ML processing."""
    print_header("STEP 4: Verifying Database State")

    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with AsyncSession(engine) as session:
            # 1. Check photo_processing_sessions
            result = await session.execute(
                text("SELECT id, status, total_images FROM photo_processing_sessions WHERE id = :session_id"),
                {"session_id": session_id},
            )
            row = result.first()
            if row:
                print_success(f"Photo processing session found (ID={row[0]})")
                print_info(f"  Status: {row[1]}")
                print_info(f"  Total images: {row[2]}")
            else:
                print_error("Photo processing session NOT FOUND")

            # 2. Check s3_images
            result = await session.execute(
                text(
                    """
                    SELECT id, status, file_size_bytes, s3_key_original, s3_key_thumbnail
                    FROM s3_images
                    WHERE session_id = :session_id
                    """
                ),
                {"session_id": session_id},
            )
            rows = result.fetchall()
            if rows:
                print_success(f"Found {len(rows)} S3 image(s)")
                for row in rows:
                    print_info(f"  Image ID={row[0]}, status={row[1]}, size={row[2]} bytes")
                    print_info(f"    S3 original: {row[3]}")
                    print_info(f"    S3 thumbnail: {row[4]}")
            else:
                print_error("No S3 images found")

            # 3. Check detections
            result = await session.execute(
                text(
                    """
                    SELECT COUNT(*), MIN(confidence_score), MAX(confidence_score)
                    FROM detections
                    WHERE session_id = :session_id
                    """
                ),
                {"session_id": session_id},
            )
            row = result.first()
            if row and row[0] > 0:
                print_success(f"Found {row[0]} detection(s)")
                print_info(f"  Confidence range: {row[1]:.2f} - {row[2]:.2f}")
            else:
                print_warning("No detections found (this may be normal if no objects detected)")

            # 4. Check estimations
            result = await session.execute(
                text(
                    """
                    SELECT COUNT(*), SUM(estimated_count)
                    FROM estimations
                    WHERE session_id = :session_id
                    """
                ),
                {"session_id": session_id},
            )
            row = result.first()
            if row and row[0] > 0:
                print_success(f"Found {row[0]} estimation(s)")
                print_info(f"  Total estimated count: {row[1]}")
            else:
                print_warning("No estimations found")

            # 5. Check stock_batches
            result = await session.execute(
                text(
                    """
                    SELECT batch_code, quantity_current, product_id, storage_location_id
                    FROM stock_batches
                    WHERE storage_location_id = :location_id
                    ORDER BY created_at DESC
                    LIMIT 5
                    """
                ),
                {"location_id": test_data["storage_location_id"]},
            )
            rows = result.fetchall()
            if rows:
                print_success(f"Found {len(rows)} stock batch(es)")
                for row in rows:
                    print_info(f"  Batch: {row[0]}, quantity={row[1]}, product_id={row[2]}")
            else:
                print_warning("No stock batches found")

            return True

    finally:
        await engine.dispose()


async def main():
    """Run complete E2E test."""
    print_header("DemeterAI v2.0 - Photo Upload Flow V3 - Complete E2E Test")

    try:
        # Step 1: Setup test data
        test_data = await setup_test_data()

        # Step 2: Submit photo
        response_data = await submit_photo(test_data)
        if not response_data:
            print_error("FAILED: Photo submission failed")
            sys.exit(1)

        # Step 3: Monitor Celery task
        task_id = response_data.get("task_id")
        session_id = response_data.get("session_id")

        if task_id:
            task_success = await monitor_celery_task(task_id, timeout=120)
            if task_success is False:
                print_error("FAILED: Celery task failed")
            elif task_success is None:
                print_warning("WARNING: Could not verify task completion via Flower")
        else:
            print_error("No task_id in response")

        # Give ML processing time to complete
        print_info("\nWaiting 30 seconds for ML processing to complete...")
        await asyncio.sleep(30)

        # Step 4: Verify database state
        await verify_database_state(test_data, session_id)

        # Final report
        print_header("E2E TEST COMPLETED")
        print_success("Test execution finished!")
        print_info("\nManual verification steps:")
        print_info(f"1. Check Flower dashboard: {FLOWER_URL}")
        print_info(f"2. Check S3 bucket for uploaded images")
        print_info(f"3. Verify database records for session_id={session_id}")
        print_info(f"4. Check API logs: docker logs demeterai-api")
        print_info(f"5. Check Celery logs: docker logs demeterai-celery-cpu")

    except Exception as e:
        print_error(f"E2E test failed with exception: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
