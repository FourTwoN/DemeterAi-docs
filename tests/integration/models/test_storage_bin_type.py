"""Integration tests for StorageBinType model.

Tests the StorageBinType model (DB005) with actual database interactions.

Test Coverage:
    - Seed data verification (2 tests)
    - RESTRICT delete tests (2 tests)
    - Relationship tests (2 tests)
    - Code uniqueness tests (2 tests)
    - CHECK constraint at DB level (2 tests)

Target Coverage: ≥70%
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.storage_bin import StorageBin
from app.models.storage_bin_type import BinCategoryEnum, StorageBinType


@pytest.mark.integration
class TestSeedData:
    """Test seed data verification."""

    def test_seed_data_loaded(self, db_session):
        """Verify all seed types exist after migration."""
        result = db_session.execute(select(StorageBinType))
        types = result.scalars().all()

        # Should have at least 7 seed types
        assert len(types) >= 7

        # Verify specific seed types exist
        codes = [t.code for t in types]
        assert "PLUG_TRAY_288" in codes
        assert "PLUG_TRAY_128" in codes
        assert "PLUG_TRAY_72" in codes
        assert "SEEDLING_TRAY_50" in codes
        assert "BOX_STANDARD" in codes
        assert "SEGMENT_STANDARD" in codes
        assert "POT_10CM" in codes

    def test_seed_data_integrity(self, db_session):
        """Verify seed data has correct structure."""
        # Get PLUG_TRAY_288
        result = db_session.execute(
            select(StorageBinType).where(StorageBinType.code == "PLUG_TRAY_288")
        )
        plug_tray = result.scalar_one()

        assert plug_tray.name == "288-Cell Plug Tray"
        assert plug_tray.category == BinCategoryEnum.PLUG
        assert plug_tray.rows == 18
        assert plug_tray.columns == 16
        assert plug_tray.capacity == 288
        assert plug_tray.is_grid is True
        assert plug_tray.length_cm == 54.0
        assert plug_tray.width_cm == 27.5
        assert plug_tray.height_cm == 5.5

        # Get SEGMENT_STANDARD
        result = db_session.execute(
            select(StorageBinType).where(StorageBinType.code == "SEGMENT_STANDARD")
        )
        segment = result.scalar_one()

        assert segment.name == "Individual Segment"
        assert segment.category == BinCategoryEnum.SEGMENT
        assert segment.rows is None
        assert segment.columns is None
        assert segment.capacity is None
        assert segment.is_grid is False
        assert segment.length_cm is None


@pytest.mark.integration
class TestRestrictDelete:
    """Test RESTRICT delete behavior."""

    def test_delete_bin_type_with_storage_bins_fails(
        self, db_session, sample_warehouse, sample_storage_area, sample_storage_location
    ):
        """Test that deleting bin type with storage bins fails (RESTRICT)."""
        # Create bin type
        bin_type = StorageBinType(
            code="TEST_TYPE_DELETE", name="Test Type for Delete", category=BinCategoryEnum.BOX
        )
        db_session.add(bin_type)
        db_session.commit()

        # Create storage bin referencing this type
        storage_bin = StorageBin(
            storage_location_id=sample_storage_location.location_id,
            storage_bin_type_id=bin_type.storage_bin_type_id,
            code="TEST-BIN-001",
            label="Test Bin",
            status="active",
        )
        db_session.add(storage_bin)
        db_session.commit()

        # Try to delete bin type (should fail - RESTRICT)
        with pytest.raises(IntegrityError, match="violates foreign key constraint"):
            db_session.delete(bin_type)
            db_session.commit()

        db_session.rollback()

    def test_delete_bin_type_without_storage_bins_succeeds(self, db_session):
        """Test that deleting bin type without storage bins succeeds."""
        # Create bin type
        bin_type = StorageBinType(
            code="TEST_TYPE_DELETE_OK", name="Test Type for Delete OK", category=BinCategoryEnum.BOX
        )
        db_session.add(bin_type)
        db_session.commit()

        bin_type_id = bin_type.storage_bin_type_id

        # Delete bin type (should succeed - no storage bins)
        db_session.delete(bin_type)
        db_session.commit()

        # Verify bin type is deleted
        result = db_session.execute(
            select(StorageBinType).where(StorageBinType.storage_bin_type_id == bin_type_id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.integration
class TestRelationships:
    """Test model relationships with database."""

    def test_query_storage_bins_from_bin_type(
        self, db_session, sample_warehouse, sample_storage_area, sample_storage_location
    ):
        """Test querying storage_bins from bin_type."""
        # Create bin type
        bin_type = StorageBinType(
            code="TEST_TYPE_REL", name="Test Type for Relationship", category=BinCategoryEnum.BOX
        )
        db_session.add(bin_type)
        db_session.commit()

        # Create 3 storage bins
        bins = []
        for i in range(3):
            storage_bin = StorageBin(
                storage_location_id=sample_storage_location.location_id,
                storage_bin_type_id=bin_type.storage_bin_type_id,
                code=f"TEST-BIN-{i:03d}",
                label=f"Test Bin {i}",
                status="active",
            )
            bins.append(storage_bin)
            db_session.add(storage_bin)

        db_session.commit()

        # Query bins from bin_type
        result = db_session.execute(
            select(StorageBinType).where(
                StorageBinType.storage_bin_type_id == bin_type.storage_bin_type_id
            )
        )
        retrieved_type = result.scalar_one()

        assert len(retrieved_type.storage_bins) == 3
        bin_codes = [b.code for b in retrieved_type.storage_bins]
        assert "TEST-BIN-000" in bin_codes
        assert "TEST-BIN-001" in bin_codes
        assert "TEST-BIN-002" in bin_codes

    def test_fk_integrity_storage_bins_to_bin_type(
        self, db_session, sample_warehouse, sample_storage_area, sample_storage_location
    ):
        """Test FK integrity (storage_bins.storage_bin_type_id → storage_bin_types.storage_bin_type_id)."""
        # Create bin type
        bin_type = StorageBinType(
            code="TEST_TYPE_FK", name="Test Type for FK", category=BinCategoryEnum.SEGMENT
        )
        db_session.add(bin_type)
        db_session.commit()

        # Create storage bin with valid storage_bin_type_id
        storage_bin = StorageBin(
            storage_location_id=sample_storage_location.location_id,
            storage_bin_type_id=bin_type.storage_bin_type_id,
            code="TEST-BIN-FK-001",
            label="Test Bin FK",
            status="active",
        )
        db_session.add(storage_bin)
        db_session.commit()

        # Verify relationship works
        assert storage_bin.storage_bin_type == bin_type
        assert storage_bin.storage_bin_type.code == "TEST_TYPE_FK"


@pytest.mark.integration
class TestCodeUniqueness:
    """Test code uniqueness constraint."""

    def test_create_two_types_with_same_code_fails(self, db_session):
        """Test creating two types with same code fails (UK constraint)."""
        # Create first bin type
        bin_type1 = StorageBinType(
            code="DUPLICATE_CODE", name="First Type", category=BinCategoryEnum.BOX
        )
        db_session.add(bin_type1)
        db_session.commit()

        # Try to create second bin type with same code
        bin_type2 = StorageBinType(
            code="DUPLICATE_CODE", name="Second Type", category=BinCategoryEnum.POT
        )
        db_session.add(bin_type2)

        with pytest.raises(IntegrityError, match="duplicate key value"):
            db_session.commit()

        db_session.rollback()

    def test_create_types_with_different_codes_succeeds(self, db_session):
        """Test creating types with different codes succeeds."""
        # Create first bin type
        bin_type1 = StorageBinType(
            code="UNIQUE_CODE_1", name="First Type", category=BinCategoryEnum.BOX
        )
        db_session.add(bin_type1)

        # Create second bin type with different code
        bin_type2 = StorageBinType(
            code="UNIQUE_CODE_2", name="Second Type", category=BinCategoryEnum.POT
        )
        db_session.add(bin_type2)

        db_session.commit()

        # Verify both types exist
        result = db_session.execute(select(StorageBinType))
        types = result.scalars().all()
        codes = [t.code for t in types]
        assert "UNIQUE_CODE_1" in codes
        assert "UNIQUE_CODE_2" in codes


@pytest.mark.integration
class TestCheckConstraintAtDBLevel:
    """Test CHECK constraint enforcement at database level."""

    def test_grid_type_with_null_rows_fails(self, db_session):
        """Test inserting is_grid=TRUE with NULL rows fails at DB level."""
        # Create bin type with is_grid=TRUE but NULL rows
        bin_type = StorageBinType(
            code="GRID_NO_ROWS",
            name="Grid Without Rows",
            category=BinCategoryEnum.PLUG,
            is_grid=True,
            columns=16,  # columns NOT NULL, but rows NULL
        )
        db_session.add(bin_type)

        # Should fail CHECK constraint at DB level
        with pytest.raises(IntegrityError, match="ck_storage_bin_type_grid_requires_rows_columns"):
            db_session.commit()

        db_session.rollback()

    def test_grid_type_with_null_columns_fails(self, db_session):
        """Test inserting is_grid=TRUE with NULL columns fails at DB level."""
        # Create bin type with is_grid=TRUE but NULL columns
        bin_type = StorageBinType(
            code="GRID_NO_COLUMNS",
            name="Grid Without Columns",
            category=BinCategoryEnum.PLUG,
            is_grid=True,
            rows=18,  # rows NOT NULL, but columns NULL
        )
        db_session.add(bin_type)

        # Should fail CHECK constraint at DB level
        with pytest.raises(IntegrityError, match="ck_storage_bin_type_grid_requires_rows_columns"):
            db_session.commit()

        db_session.rollback()

    def test_non_grid_type_with_null_rows_succeeds(self, db_session):
        """Test inserting is_grid=FALSE with NULL rows succeeds."""
        # Create bin type with is_grid=FALSE and NULL rows/columns
        bin_type = StorageBinType(
            code="NON_GRID_NO_ROWS",
            name="Non-Grid Without Rows",
            category=BinCategoryEnum.SEGMENT,
            is_grid=False,
        )
        db_session.add(bin_type)
        db_session.commit()

        # Verify bin type was created
        result = db_session.execute(
            select(StorageBinType).where(StorageBinType.code == "NON_GRID_NO_ROWS")
        )
        retrieved_type = result.scalar_one()
        assert retrieved_type.is_grid is False
        assert retrieved_type.rows is None
        assert retrieved_type.columns is None

    def test_grid_type_with_rows_and_columns_succeeds(self, db_session):
        """Test inserting is_grid=TRUE with rows AND columns succeeds."""
        # Create bin type with is_grid=TRUE and rows/columns NOT NULL
        bin_type = StorageBinType(
            code="GRID_WITH_ROWS_COLS",
            name="Grid With Rows and Columns",
            category=BinCategoryEnum.PLUG,
            is_grid=True,
            rows=12,
            columns=24,
            capacity=288,
        )
        db_session.add(bin_type)
        db_session.commit()

        # Verify bin type was created
        result = db_session.execute(
            select(StorageBinType).where(StorageBinType.code == "GRID_WITH_ROWS_COLS")
        )
        retrieved_type = result.scalar_one()
        assert retrieved_type.is_grid is True
        assert retrieved_type.rows == 12
        assert retrieved_type.columns == 24
        assert retrieved_type.capacity == 288
