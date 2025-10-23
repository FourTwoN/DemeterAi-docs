#!/usr/bin/env python
"""Create minimal test data for E2E testing."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from geoalchemy2.shape import from_shape
from shapely.geometry import Point, Polygon
from sqlalchemy.ext.asyncio import create_async_engine

from app.models.storage_area import StorageArea
from app.models.storage_location import StorageLocation
from app.models.user import User
from app.models.warehouse import Warehouse

DATABASE_URL = "postgresql+asyncpg://demeter:demeter_dev_password@localhost:5432/demeterai"


async def create_test_data():
    """Create minimal test data."""
    engine = create_async_engine(DATABASE_URL, echo=False)

    # Create data
    async def _create():
        from sqlalchemy.ext.asyncio import AsyncSession

        async with AsyncSession(engine) as session:
            # Create warehouse
            wh_polygon = Polygon(
                [(-33.04, -68.71), (-33.04, -68.69), (-33.06, -68.69), (-33.06, -68.71)]
            )
            wh_centroid = wh_polygon.centroid

            warehouse = Warehouse(
                code="WH_TEST",
                name="Test Warehouse",
                warehouse_type="greenhouse",
                geojson_coordinates=from_shape(wh_polygon, srid=4326),
                centroid=from_shape(wh_centroid, srid=4326),
                active=True,
            )
            session.add(warehouse)
            await session.flush()
            print(f"✓ Created warehouse: {warehouse.code}")

            # Create storage area
            sa_polygon = Polygon(
                [(-33.041, -68.705), (-33.041, -68.695), (-33.049, -68.695), (-33.049, -68.705)]
            )
            sa_centroid = sa_polygon.centroid

            storage_area = StorageArea(
                warehouse_id=warehouse.warehouse_id,
                code="SA_TEST",
                name="Test Area",
                position="C",
                geojson_coordinates=from_shape(sa_polygon, srid=4326),
                centroid=from_shape(sa_centroid, srid=4326),
                active=True,
            )
            session.add(storage_area)
            await session.flush()
            print(f"✓ Created storage area: {storage_area.code}")

            # Create storage location (INSIDE the storage area polygon)
            loc_point = Point(-33.043, -68.701)  # Inside SA polygon

            storage_location = StorageLocation(
                storage_area_id=storage_area.storage_area_id,
                code="LOC_TEST",
                qr_code="QR_TEST_001",
                name="Test Location",
                description="Test location for E2E testing",
                coordinates=from_shape(loc_point, srid=4326),
                centroid=from_shape(loc_point, srid=4326),
                active=True,
            )
            session.add(storage_location)
            await session.flush()
            print(f"✓ Created storage location: {storage_location.code}")
            print(f"  GPS: lat={-33.043}, lon={-68.701}")

            # Create test user
            user = User(
                email="test@demeterai.com",
                password_hash="$2b$12$test",  # dummy hash
                first_name="Test",
                last_name="User",
                role="worker",
                active=True,
            )
            session.add(user)
            await session.commit()
            print(f"✓ Created user: {user.email}")

            # Verify
            from sqlalchemy import select

            wh_count = await session.scalar(
                select(
                    len(
                        __import__(
                            "app.models.warehouse", fromlist=["Warehouse"]
                        ).Warehouse.__table__
                    )
                )
            )
            print("\n✓ Test data created successfully!")
            print("  Use GPS: latitude=-33.043, longitude=-68.701")
            print("  Use user_id=1")

    await _create()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_test_data())
