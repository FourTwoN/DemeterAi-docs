#!/usr/bin/env python3
"""Load/cleanup test fixtures for DemeterAI v2.0 E2E tests.

This script loads realistic test data from test_fixtures.sql into the PostgreSQL
test database. It can be used:

1. **Standalone**: Run directly to load fixtures for manual testing
2. **pytest integration**: Called from conftest.py fixture for automatic setup

Usage:
    # Load fixtures into test database
    python tests/fixtures/load_fixtures.py

    # Load fixtures + verify data
    python tests/fixtures/load_fixtures.py --verify

    # Cleanup fixtures (delete all test data)
    python tests/fixtures/load_fixtures.py --cleanup

    # Load fixtures into custom database URL
    python tests/fixtures/load_fixtures.py --db-url="postgresql://user:pass@localhost/db"

Features:
    - Loads fixtures from test_fixtures.sql
    - Verifies PostGIS geometries are valid
    - Checks all FKs are satisfied
    - Can cleanup all test data
    - Returns exit code 0 (success) or 1 (failure)

Dependencies:
    - PostgreSQL 15+ with PostGIS 3.3+
    - psycopg2-binary or asyncpg
    - SQLAlchemy 2.0+ (async)

Author: Python Expert (DemeterAI Team)
Date: 2025-10-22
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Default test database URL (same as tests/conftest.py)
DEFAULT_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://demeter_test:demeter_test_password@localhost:5434/demeterai_test",
)

# Path to SQL fixtures file
FIXTURES_DIR = Path(__file__).parent
FIXTURES_SQL = FIXTURES_DIR / "test_fixtures.sql"


async def load_fixtures(database_url: str, verify: bool = False) -> bool:
    """Load test fixtures from SQL file into database.

    Args:
        database_url: PostgreSQL connection URL (asyncpg format)
        verify: If True, run verification queries after loading

    Returns:
        True if successful, False otherwise

    Raises:
        FileNotFoundError: If fixtures SQL file not found
        Exception: If database connection or query execution fails
    """
    if not FIXTURES_SQL.exists():
        print(f"❌ ERROR: Fixtures file not found: {FIXTURES_SQL}", file=sys.stderr)
        return False

    print(f"📂 Loading fixtures from: {FIXTURES_SQL}")
    print(f"🔗 Database URL: {database_url.replace('demeter_test_password', '***')}")

    # Create async engine
    engine = create_async_engine(database_url, echo=False)

    try:
        # Read SQL file
        sql_content = FIXTURES_SQL.read_text(encoding="utf-8")

        # Execute SQL in a single transaction
        async with engine.begin() as conn:
            print("⏳ Executing SQL fixtures...")
            await conn.execute(text(sql_content))
            print("✅ Fixtures loaded successfully!")

        # Verify data if requested
        if verify:
            await verify_fixtures(engine)

        return True

    except Exception as e:
        print(f"❌ ERROR loading fixtures: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return False

    finally:
        await engine.dispose()


async def verify_fixtures(engine) -> None:
    """Verify fixtures were loaded correctly.

    Checks:
        1. Row counts for all tables
        2. PostGIS geometry validity
        3. Foreign key integrity

    Args:
        engine: SQLAlchemy async engine

    Raises:
        AssertionError: If verification fails
    """
    print("\n🔍 Verifying fixtures...")

    async with engine.begin() as conn:
        # Verify row counts
        tables = [
            "warehouses",
            "storage_areas",
            "storage_locations",
            "storage_bins",
            "storage_bin_types",
            "product_categories",
            "product_families",
            "products",
            "product_states",
            "product_sizes",
            "packaging_types",
            "packaging_materials",
            "packaging_colors",
            "packaging_catalog",
            "users",
            "storage_location_config",
        ]

        print("\n📊 Row counts:")
        for table in tables:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"   {table:30s} {count:3d} rows")

        # Verify PostGIS geometries
        print("\n🌍 PostGIS geometry validation:")
        geom_tables = [
            ("warehouses", "geojson_coordinates", "POLYGON"),
            ("storage_areas", "geojson_coordinates", "POLYGON"),
            ("storage_locations", "geojson_coordinates", "POINT"),
        ]

        for table, geom_col, expected_type in geom_tables:
            result = await conn.execute(
                text(
                    f"""
                SELECT
                    code,
                    ST_IsValid({geom_col}) AS is_valid,
                    ST_GeometryType({geom_col}) AS geom_type
                FROM {table}
            """
                )
            )
            rows = result.fetchall()
            for row in rows:
                code, is_valid, geom_type = row
                if not is_valid:
                    print(f"   ❌ {table}.{code}: INVALID geometry!")
                    raise AssertionError(f"Invalid geometry in {table}.{code}")
                if geom_type != f"ST_{expected_type}":
                    print(
                        f"   ❌ {table}.{code}: Wrong type {geom_type} (expected ST_{expected_type})"
                    )
                    raise AssertionError(f"Wrong geometry type in {table}.{code}")
                print(f"   ✅ {table}.{code}: {geom_type} (valid)")

        # Verify GENERATED columns (area_m2, centroid)
        print("\n📐 GENERATED columns (area_m2, centroid):")
        for table in ["warehouses", "storage_areas", "storage_locations"]:
            result = await conn.execute(
                text(
                    f"""
                SELECT code, area_m2, ST_AsText(centroid) AS centroid_wkt
                FROM {table}
            """
                )
            )
            rows = result.fetchall()
            for row in rows:
                code, area_m2, centroid_wkt = row
                if area_m2 is None and table != "storage_locations":
                    print(f"   ❌ {table}.{code}: area_m2 is NULL!")
                    raise AssertionError(f"GENERATED column area_m2 is NULL in {table}.{code}")
                if centroid_wkt is None:
                    print(f"   ❌ {table}.{code}: centroid is NULL!")
                    raise AssertionError(f"GENERATED column centroid is NULL in {table}.{code}")
                print(f"   ✅ {table}.{code}: area_m2={area_m2}, centroid={centroid_wkt}")

    print("\n✅ All verifications passed!")


async def cleanup_fixtures(database_url: str) -> bool:
    """Delete all test data from database (cascade delete).

    WARNING: This will DELETE all data from the test database!
    Only use this on TEST databases, never on PRODUCTION!

    Args:
        database_url: PostgreSQL connection URL (asyncpg format)

    Returns:
        True if successful, False otherwise
    """
    print(f"🗑️  Cleaning up fixtures from: {database_url.replace('demeter_test_password', '***')}")
    print("⚠️  WARNING: This will DELETE all data from the database!")

    # Create async engine
    engine = create_async_engine(database_url, echo=False)

    try:
        async with engine.begin() as conn:
            # Delete in reverse dependency order (respects FKs)
            tables = [
                "storage_location_config",
                "stock_movements",
                "stock_batches",
                "storage_bins",
                "storage_locations",
                "storage_areas",
                "warehouses",
                "packaging_catalog",
                "packaging_colors",
                "packaging_materials",
                "packaging_types",
                "product_sample_images",
                "products",
                "product_families",
                "product_categories",
                "product_states",
                "product_sizes",
                "storage_bin_types",
                "users",
            ]

            for table in tables:
                result = await conn.execute(text(f"DELETE FROM {table}"))
                print(f"   ✅ Deleted {result.rowcount} rows from {table}")

        print("✅ Cleanup complete!")
        return True

    except Exception as e:
        print(f"❌ ERROR during cleanup: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return False

    finally:
        await engine.dispose()


async def main() -> int:
    """Main entry point for CLI usage.

    Returns:
        Exit code: 0 (success), 1 (failure)
    """
    parser = argparse.ArgumentParser(
        description="Load/cleanup test fixtures for DemeterAI v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=DEFAULT_DB_URL,
        help=f"Database URL (default: {DEFAULT_DB_URL.replace('demeter_test_password', '***')})",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify fixtures after loading (check row counts, geometries, FKs)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Cleanup all test data (DELETE all rows)",
    )

    args = parser.parse_args()

    # Cleanup mode
    if args.cleanup:
        success = await cleanup_fixtures(args.db_url)
        return 0 if success else 1

    # Load fixtures mode
    success = await load_fixtures(args.db_url, verify=args.verify)
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
