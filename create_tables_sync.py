"""Create all tables synchronously without async complexity."""

import sys

from sqlalchemy import create_engine, inspect, text

# Build sync DATABASE_URL from async URL
DATABASE_URL = (
    "postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test"
)

print(f"Connecting to: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL, echo=False)

    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✅ Connected to PostgreSQL: {version[:50]}...")

    # Import Base and all models
    from app.db.base import Base

    print(f"\n📦 Loaded {len(Base.metadata.tables)} models")

    # Drop all tables
    print("\n🗑️  Dropping all existing tables...")
    Base.metadata.drop_all(engine)

    # Create all tables
    print("\n✨ Creating all tables from SQLAlchemy models...")
    Base.metadata.create_all(engine)

    # Inspect what was created
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"\n✅ Created {len(tables)} tables successfully!")
    print("\n📋 Tables created:")
    for table in sorted(tables):
        print(f"  ✓ {table}")

    # Show detailed schema for first few tables
    print("\n" + "=" * 80)
    print("📊 Sample Table Structures:")
    print("=" * 80)

    sample_tables = ["warehouses", "storage_areas", "storage_locations", "storage_bins"]
    for table_name in sample_tables:
        if table_name in tables:
            print(f"\n🏷️  {table_name}:")
            print("-" * 80)

            columns = inspector.get_columns(table_name)
            for col in columns:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                col_type = str(col["type"])
                print(f"  {col['name']:30} {col_type:25} {nullable}")

            # Foreign keys
            fks = inspector.get_foreign_keys(table_name)
            if fks:
                print("\n  🔗 Foreign Keys:")
                for fk in fks:
                    print(
                        f"    {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}"
                    )

    print("\n" + "=" * 80)
    print("✅ Schema creation complete!")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {e}", file=sys.stderr)
    import traceback

    traceback.print_exc()
    sys.exit(1)
