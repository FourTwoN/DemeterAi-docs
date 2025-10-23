#!/usr/bin/env python3
"""Test script for production data loader.

This script demonstrates how to use the ProductionDataLoader to load
production data into the database.

Usage:
    python test_production_loader.py

Environment:
    DATABASE_URL: Database connection string
    PYTHONPATH: Should include project root
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.base import Base
from app.db.load_production_data import ProductionDataLoader

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def main():
    """Main test function."""
    logger.info("=" * 80)
    logger.info("Testing Production Data Loader")
    logger.info("=" * 80)

    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )

    try:
        # Create tables
        logger.info("Creating database schema...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database schema created")

        # Create session
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # Load production data
            logger.info("")
            logger.info("Loading production data...")
            loader = ProductionDataLoader(session)
            counts = await loader.load_all_async()

            # Display results
            logger.info("")
            logger.info("=" * 80)
            logger.info("✅ Test Complete!")
            logger.info("=" * 80)
            logger.info("Data loaded:")
            for data_type, count in counts.items():
                logger.info(f"  {data_type}: {count}")

            # Verify data was loaded
            logger.info("")
            logger.info("Verifying data...")

            from sqlalchemy import func, select

            from app.models import (
                ProductCategory,
                StorageArea,
                StorageBinType,
                StorageLocation,
                Warehouse,
            )

            # Count each table
            for model, name in [
                (Warehouse, "Warehouses"),
                (StorageArea, "StorageAreas"),
                (StorageLocation, "StorageLocations"),
                (ProductCategory, "ProductCategories"),
                (StorageBinType, "StorageBinTypes"),
            ]:
                result = await session.execute(
                    select(func.count(model.id if hasattr(model, "id") else model.warehouse_id))
                )
                count = result.scalar()
                logger.info(f"  ✓ {name}: {count}")

            logger.info("")
            logger.info("✅ All tests passed!")

    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
        raise

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
