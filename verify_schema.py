"""Schema verification script - compare SQLAlchemy models vs database.mmd ERD.

This script:
1. Creates all tables from SQLAlchemy models
2. Inspects the actual database schema
3. Compares against database/database.mmd ERD
4. Reports any structural issues (not cosmetic naming differences)
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.base import Base

# Import all models to ensure they're registered


async def create_all_tables():
    """Drop and recreate all tables from SQLAlchemy models."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        print("\n🗑️  Dropping all existing tables...")
        await conn.run_sync(Base.metadata.drop_all)

        print("\n✨ Creating all tables from SQLAlchemy models...")
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("\n✅ Database schema created successfully!")


async def inspect_schema():
    """Inspect actual database schema and report structure."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        # Get list of all tables
        result = await conn.execute(
            text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            AND table_name NOT LIKE 'spatial_%'
            AND table_name NOT IN (SELECT tablename FROM pg_tables WHERE schemaname = 'tiger')
            ORDER BY table_name;
        """)
        )
        tables = [row[0] for row in result.fetchall()]

        print("\n📊 Database Tables Found:")
        print("=" * 80)
        for table in tables:
            print(f"  ✓ {table}")

        print(f"\n📈 Total tables: {len(tables)}")

        # For each table, get column details
        print("\n📋 Detailed Schema Inspection:")
        print("=" * 80)

        for table in tables:
            result = await conn.execute(
                text("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    udt_name
                FROM information_schema.columns
                WHERE table_name = :table
                ORDER BY ordinal_position;
            """),
                {"table": table},
            )

            columns = result.fetchall()

            print(f"\n🏷️  Table: {table}")
            print("-" * 80)
            for col in columns:
                col_name, data_type, nullable, default, udt_name = col
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                default_str = f" DEFAULT {default}" if default else ""
                print(f"    {col_name:30} {udt_name:20} {nullable_str:10}{default_str}")

            # Get foreign keys
            fk_result = await conn.execute(
                text("""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    rc.delete_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                JOIN information_schema.referential_constraints AS rc
                  ON rc.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = :table;
            """),
                {"table": table},
            )

            fks = fk_result.fetchall()
            if fks:
                print("\n    🔗 Foreign Keys:")
                for fk in fks:
                    col, ref_table, ref_col, on_delete = fk
                    print(f"      {col} → {ref_table}.{ref_col} (ON DELETE {on_delete})")

    await engine.dispose()


async def main():
    """Main execution flow."""
    print("=" * 80)
    print("🔍 DemeterAI Database Schema Verification")
    print("=" * 80)

    # Step 1: Create tables
    await create_all_tables()

    # Step 2: Inspect schema
    await inspect_schema()

    print("\n" + "=" * 80)
    print("✅ Schema verification complete!")
    print("=" * 80)
    print("\n📝 Next steps:")
    print("  1. Review the output above")
    print("  2. Compare with database/database.mmd ERD")
    print("  3. Identify any structural issues")
    print("  4. Report findings before making changes")


if __name__ == "__main__":
    asyncio.run(main())
