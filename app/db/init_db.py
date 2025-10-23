"""Database initialization - Drop and recreate schema on startup.

This module provides automatic database schema recreation to ensure
SQLAlchemy models are always in sync with the database.

Two modes are available:

1. Development mode (default): Drop and recreate schema on every startup
   - WARNING: This DROPS ALL TABLES!
   - Only use in development

2. Production data mode: Create schema once and load production data
   - Creates tables if they don't exist
   - Loads GPS coordinates, product categories, pricing data
   - Idempotent - safe to run multiple times

Architecture:
    Layer: Database / Initialization (Infrastructure Layer)
    Dependencies: SQLAlchemy async, GeoAlchemy2
"""

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import Base
from app.db.load_production_data import ProductionDataLoader

logger = get_logger(__name__)


async def init_database(load_production_data: bool = False) -> None:
    """Initialize database with optional production data loading.

    Two modes:

    1. Development (load_production_data=False, default):
       - DROP all existing tables
       - CREATE all tables from models
       - WARNING: Destroys all data!

    2. Production (load_production_data=True):
       - CREATE tables if they don't exist
       - LOAD production data (GeoJSON + CSV)
       - Idempotent - safe to run multiple times

    Args:
        load_production_data: If True, load production data instead of dropping tables

    Raises:
        Exception: If database initialization fails
    """
    logger.info("=" * 80)
    logger.info("🔄 Starting database initialization...")
    if load_production_data:
        logger.info("Mode: PRODUCTION DATA LOADING (data preserved)")
    else:
        logger.info("Mode: DEVELOPMENT (DROP + RECREATE)")
    logger.info("=" * 80)

    # Create async engine for initialization
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO_SQL,
    )

    try:
        async with engine.begin() as conn:
            if load_production_data:
                # Production mode: Create tables if they don't exist
                logger.info("✨ Creating tables if they don't exist...")

                # Check if tables exist using run_sync (required for AsyncConnection)
                def check_tables(sync_conn):
                    inspector = inspect(sync_conn)
                    all_tables = inspector.get_table_names()
                    # Only count our tables (from Base.metadata)
                    our_tables = [t for t in all_tables if t in Base.metadata.tables]
                    return len(our_tables), len(all_tables)

                our_table_count, all_table_count = await conn.run_sync(check_tables)

                if our_table_count == 0:
                    # Our tables don't exist, create them
                    logger.info(
                        f"  No app tables found. Found {all_table_count} total tables. Creating all tables from models..."
                    )
                    await conn.run_sync(Base.metadata.create_all)
                    logger.info("✅ All app tables created successfully")
                else:
                    logger.info(
                        f"  App tables already exist ({our_table_count} found from {all_table_count} total tables)"
                    )

            else:
                # Development mode: Drop and recreate
                logger.warning("🗑️  Dropping ALL existing tables...")
                await conn.run_sync(Base.metadata.drop_all)
                logger.info("✅ All tables dropped successfully")

                logger.info("✨ Creating all tables from SQLAlchemy models...")
                await conn.run_sync(Base.metadata.create_all)
                logger.info("✅ All tables created successfully")

        # Log table count
        table_count = len(Base.metadata.tables)
        logger.info("=" * 80)
        logger.info(f"✅ Database schema ready! {table_count} tables")
        logger.info("=" * 80)

        # Load production data if requested
        if load_production_data:
            logger.info("")
            logger.info("=" * 80)
            logger.info("Loading production data...")
            logger.info("=" * 80)

            from sqlalchemy.ext.asyncio import AsyncSession

            async with AsyncSession(engine) as session:
                loader = ProductionDataLoader(session)
                counts = await loader.load_all_async()

                logger.info("")
                logger.info("=" * 80)
                logger.info("Production data summary:")
                for data_type, count in counts.items():
                    logger.info(f"  {data_type}: {count}")
                logger.info("=" * 80)

    except Exception as e:
        logger.error(
            "❌ Database initialization failed",
            error=str(e),
            exc_info=True,
        )
        raise

    finally:
        await engine.dispose()
        logger.info("🔒 Database connection closed")
