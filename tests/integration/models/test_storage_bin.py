"""Integration tests for StorageBin model with database operations.

These tests require a database connection and test:
- CASCADE delete from storage_location (bins deleted when location deleted)
- CASCADE delete chains (warehouse → area → location → bins)
- RESTRICT delete from storage_bin_type (cannot delete type with bins)
- JSONB queries (filter by confidence, container_type, ml_model_version)
- Code uniqueness constraints
- Foreign key integrity

Unit tests with validation logic (no DB) are in tests/unit/models/
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# Import models
pytest.importorskip("app.models.storage_bin", reason="StorageBin model not yet implemented")

from app.models.storage_bin import StorageBin  # noqa: E402


class TestStorageBinCascadeDelete:
    """Test CASCADE delete behavior from parent storage_location."""

    @pytest.mark.asyncio
    async def test_cascade_delete_from_location(self, db_session, storage_location_factory):
        """Delete storage_location → bins CASCADE deleted."""
        # Create location with bins
        location = await storage_location_factory(code="WH-AREA-LOC1")

        # Create 3 bins in this location
        bin1 = StorageBin(
            code="WH-AREA-LOC1-SEG001",
            label="Segmento 1",
            storage_location_id=location.location_id,
        )
        bin2 = StorageBin(
            code="WH-AREA-LOC1-SEG002",
            label="Segmento 2",
            storage_location_id=location.location_id,
        )
        bin3 = StorageBin(
            code="WH-AREA-LOC1-CAJ01",
            label="Cajon 1",
            storage_location_id=location.location_id,
        )

        db_session.add_all([bin1, bin2, bin3])
        await db_session.commit()

        # Verify bins exist
        result = await db_session.execute(
            select(StorageBin).where(StorageBin.storage_location_id == location.location_id)
        )
        bins_before = result.scalars().all()
        assert len(bins_before) == 3

        # Delete location
        await db_session.delete(location)
        await db_session.commit()

        # Verify bins CASCADE deleted
        result = await db_session.execute(
            select(StorageBin).where(StorageBin.storage_location_id == location.location_id)
        )
        bins_after = result.scalars().all()
        assert len(bins_after) == 0

    @pytest.mark.asyncio
    async def test_cascade_delete_from_area(self, db_session, storage_area_factory):
        """Delete storage_area → locations + bins CASCADE deleted."""
        # Create area with location with bins
        area = await storage_area_factory(code="WH-AREA-01")

        # Create location in area
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point

        from app.models.storage_location import StorageLocation

        location = StorageLocation(
            code="WH-AREA-01-LOC1",
            name="Location 1",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-CASCADE-01",
            geojson_coordinates=from_shape(Point(-70.64825, -33.44925), srid=4326),
        )
        db_session.add(location)
        await db_session.commit()
        await db_session.refresh(location)

        # Create bins in location
        bin1 = StorageBin(
            code="WH-AREA-01-LOC1-SEG001",
            label="Segmento 1",
            storage_location_id=location.location_id,
        )
        bin2 = StorageBin(
            code="WH-AREA-01-LOC1-SEG002",
            label="Segmento 2",
            storage_location_id=location.location_id,
        )

        db_session.add_all([bin1, bin2])
        await db_session.commit()

        # Verify bins exist
        result = await db_session.execute(select(StorageBin))
        bins_before = result.scalars().all()
        assert len(bins_before) == 2

        # Delete area (should cascade to location, then to bins)
        await db_session.delete(area)
        await db_session.commit()

        # Verify bins CASCADE deleted
        result = await db_session.execute(select(StorageBin))
        bins_after = result.scalars().all()
        assert len(bins_after) == 0

    @pytest.mark.asyncio
    async def test_cascade_delete_from_warehouse(self, db_session, warehouse_factory):
        """Delete warehouse → areas + locations + bins CASCADE deleted."""
        # Create warehouse → area → location → bins
        warehouse = await warehouse_factory(code="WH-CASCADE")

        # Create area in warehouse
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point, Polygon

        from app.models.storage_area import StorageArea
        from app.models.storage_location import StorageLocation

        area = StorageArea(
            code="WH-CASCADE-AREA",
            name="Test Area",
            warehouse_id=warehouse.warehouse_id,
            position="N",
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)

        # Create location in area
        location = StorageLocation(
            code="WH-CASCADE-AREA-LOC1",
            name="Location 1",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-WH-CASCADE-01",
            geojson_coordinates=from_shape(Point(-70.64825, -33.44925), srid=4326),
        )
        db_session.add(location)
        await db_session.commit()
        await db_session.refresh(location)

        # Create bin in location
        bin_obj = StorageBin(
            code="WH-CASCADE-AREA-LOC1-SEG001",
            label="Segmento 1",
            storage_location_id=location.location_id,
        )
        db_session.add(bin_obj)
        await db_session.commit()

        # Verify bin exists
        result = await db_session.execute(select(StorageBin))
        bins_before = result.scalars().all()
        assert len(bins_before) == 1

        # Delete warehouse (should cascade through area → location → bins)
        await db_session.delete(warehouse)
        await db_session.commit()

        # Verify bin CASCADE deleted
        result = await db_session.execute(select(StorageBin))
        bins_after = result.scalars().all()
        assert len(bins_after) == 0


class TestStorageBinRestrictDelete:
    """Test RESTRICT delete behavior from storage_bin_type."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="StorageBinType model not yet implemented (DB005)")
    async def test_restrict_delete_bin_type_with_bins(self, db_session, storage_location_factory):
        """Delete storage_bin_type with bins → FAILS (RESTRICT)."""
        # Note: This test will be enabled after DB005 (StorageBinType) is implemented
        from app.models.storage_bin_type import StorageBinType

        # Create location
        location = await storage_location_factory(code="WH-AREA-LOC1")

        # Create bin type
        bin_type = StorageBinType(
            name="Segmento Standard",
            capacity=1000,
            dimensions_cm={"width": 60, "length": 40, "height": 15},
        )
        db_session.add(bin_type)
        await db_session.commit()
        await db_session.refresh(bin_type)

        # Create bin with this type
        bin_obj = StorageBin(
            code="WH-AREA-LOC1-SEG001",
            label="Segmento 1",
            storage_location_id=location.location_id,
            storage_bin_type_id=bin_type.storage_bin_type_id,
        )
        db_session.add(bin_obj)
        await db_session.commit()

        # Try to delete bin_type → should FAIL (RESTRICT)
        with pytest.raises(IntegrityError):
            await db_session.delete(bin_type)
            await db_session.commit()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="StorageBinType model not yet implemented (DB005)")
    async def test_restrict_delete_bin_type_without_bins(self, db_session):
        """Delete storage_bin_type without bins → SUCCESS."""
        from app.models.storage_bin_type import StorageBinType

        # Create bin type (no bins)
        bin_type = StorageBinType(
            name="Unused Bin Type",
            capacity=500,
        )
        db_session.add(bin_type)
        await db_session.commit()

        # Delete should succeed (no bins reference it)
        await db_session.delete(bin_type)
        await db_session.commit()

        # Verify deleted
        result = await db_session.execute(select(StorageBinType))
        types_after = result.scalars().all()
        assert len(types_after) == 0


class TestStorageBinJsonbQueries:
    """Test JSONB position_metadata queries."""

    @pytest.mark.asyncio
    async def test_filter_by_confidence_high(self, db_session, storage_location_factory):
        """Filter bins with confidence > 0.9."""
        location = await storage_location_factory(code="WH-AREA-LOC1")

        # Create bins with different confidence levels
        bin_high1 = StorageBin(
            code="WH-AREA-LOC1-SEG001",
            label="High Confidence 1",
            storage_location_id=location.location_id,
            position_metadata={"confidence": 0.95, "container_type": "segmento"},
        )
        bin_high2 = StorageBin(
            code="WH-AREA-LOC1-SEG002",
            label="High Confidence 2",
            storage_location_id=location.location_id,
            position_metadata={"confidence": 0.92, "container_type": "segmento"},
        )
        bin_low = StorageBin(
            code="WH-AREA-LOC1-SEG003",
            label="Low Confidence",
            storage_location_id=location.location_id,
            position_metadata={"confidence": 0.65, "container_type": "segmento"},
        )

        db_session.add_all([bin_high1, bin_high2, bin_low])
        await db_session.commit()

        # Query bins with confidence > 0.9
        result = await db_session.execute(
            select(StorageBin).where(StorageBin.position_metadata["confidence"].as_float() > 0.9)
        )
        high_confidence_bins = result.scalars().all()

        assert len(high_confidence_bins) == 2
        assert all(
            bin_obj.position_metadata["confidence"] > 0.9 for bin_obj in high_confidence_bins
        )

    @pytest.mark.asyncio
    async def test_filter_by_confidence_low(self, db_session, storage_location_factory):
        """Filter bins with confidence < 0.7."""
        location = await storage_location_factory(code="WH-AREA-LOC1")

        # Create bins with different confidence levels
        bin_low1 = StorageBin(
            code="WH-AREA-LOC1-SEG001",
            label="Low Confidence 1",
            storage_location_id=location.location_id,
            position_metadata={"confidence": 0.65, "container_type": "segmento"},
        )
        bin_low2 = StorageBin(
            code="WH-AREA-LOC1-SEG002",
            label="Low Confidence 2",
            storage_location_id=location.location_id,
            position_metadata={"confidence": 0.58, "container_type": "segmento"},
        )
        bin_high = StorageBin(
            code="WH-AREA-LOC1-SEG003",
            label="High Confidence",
            storage_location_id=location.location_id,
            position_metadata={"confidence": 0.95, "container_type": "segmento"},
        )

        db_session.add_all([bin_low1, bin_low2, bin_high])
        await db_session.commit()

        # Query bins with confidence < 0.7
        result = await db_session.execute(
            select(StorageBin).where(StorageBin.position_metadata["confidence"].as_float() < 0.7)
        )
        low_confidence_bins = result.scalars().all()

        assert len(low_confidence_bins) == 2
        assert all(bin_obj.position_metadata["confidence"] < 0.7 for bin_obj in low_confidence_bins)

    @pytest.mark.asyncio
    async def test_filter_by_container_type(self, db_session, storage_location_factory):
        """Filter bins by container_type = 'segmento'."""
        location = await storage_location_factory(code="WH-AREA-LOC1")

        # Create bins with different container types
        seg1 = StorageBin(
            code="WH-AREA-LOC1-SEG001",
            label="Segmento 1",
            storage_location_id=location.location_id,
            position_metadata={"confidence": 0.92, "container_type": "segmento"},
        )
        seg2 = StorageBin(
            code="WH-AREA-LOC1-SEG002",
            label="Segmento 2",
            storage_location_id=location.location_id,
            position_metadata={"confidence": 0.88, "container_type": "segmento"},
        )
        cajon = StorageBin(
            code="WH-AREA-LOC1-CAJ01",
            label="Cajon 1",
            storage_location_id=location.location_id,
            position_metadata={"confidence": 0.90, "container_type": "cajon"},
        )

        db_session.add_all([seg1, seg2, cajon])
        await db_session.commit()

        # Query bins with container_type = 'segmento'
        result = await db_session.execute(
            select(StorageBin).where(
                StorageBin.position_metadata["container_type"].as_string() == "segmento"
            )
        )
        segmentos = result.scalars().all()

        assert len(segmentos) == 2
        assert all(
            bin_obj.position_metadata["container_type"] == "segmento" for bin_obj in segmentos
        )

    @pytest.mark.asyncio
    async def test_filter_by_ml_model_version(self, db_session, storage_location_factory):
        """Filter bins by ml_model_version."""
        location = await storage_location_factory(code="WH-AREA-LOC1")

        # Create bins with different ML model versions
        bin_v2_3 = StorageBin(
            code="WH-AREA-LOC1-SEG001",
            label="ML v2.3",
            storage_location_id=location.location_id,
            position_metadata={
                "confidence": 0.92,
                "container_type": "segmento",
                "ml_model_version": "yolov11-seg-v2.3",
            },
        )
        bin_v2_4 = StorageBin(
            code="WH-AREA-LOC1-SEG002",
            label="ML v2.4",
            storage_location_id=location.location_id,
            position_metadata={
                "confidence": 0.95,
                "container_type": "segmento",
                "ml_model_version": "yolov11-seg-v2.4",
            },
        )

        db_session.add_all([bin_v2_3, bin_v2_4])
        await db_session.commit()

        # Query bins with ml_model_version = 'yolov11-seg-v2.3'
        result = await db_session.execute(
            select(StorageBin).where(
                StorageBin.position_metadata["ml_model_version"].as_string() == "yolov11-seg-v2.3"
            )
        )
        bins_v2_3 = result.scalars().all()

        assert len(bins_v2_3) == 1
        assert bins_v2_3[0].position_metadata["ml_model_version"] == "yolov11-seg-v2.3"


class TestStorageBinCodeUniqueness:
    """Test code uniqueness constraint."""

    @pytest.mark.asyncio
    async def test_code_uniqueness_enforced(self, db_session, storage_location_factory):
        """Duplicate code → IntegrityError."""
        location = await storage_location_factory(code="WH-AREA-LOC1")

        # Create first bin
        bin1 = StorageBin(
            code="WH-AREA-LOC1-SEG001",
            label="First Bin",
            storage_location_id=location.location_id,
        )
        db_session.add(bin1)
        await db_session.commit()

        # Try to create second bin with same code → should FAIL
        bin2 = StorageBin(
            code="WH-AREA-LOC1-SEG001",  # Duplicate!
            label="Second Bin",
            storage_location_id=location.location_id,
        )
        db_session.add(bin2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_different_codes_allowed(self, db_session, storage_location_factory):
        """Different codes → SUCCESS."""
        location = await storage_location_factory(code="WH-AREA-LOC1")

        # Create bins with different codes
        bin1 = StorageBin(
            code="WH-AREA-LOC1-SEG001",
            label="Segmento 1",
            storage_location_id=location.location_id,
        )
        bin2 = StorageBin(
            code="WH-AREA-LOC1-SEG002",  # Different code
            label="Segmento 2",
            storage_location_id=location.location_id,
        )
        bin3 = StorageBin(
            code="WH-AREA-LOC1-CAJ01",  # Different code
            label="Cajon 1",
            storage_location_id=location.location_id,
        )

        db_session.add_all([bin1, bin2, bin3])
        await db_session.commit()

        # Verify all created
        result = await db_session.execute(
            select(StorageBin).where(StorageBin.storage_location_id == location.location_id)
        )
        bins = result.scalars().all()
        assert len(bins) == 3


class TestStorageBinForeignKeyIntegrity:
    """Test foreign key integrity constraints."""

    @pytest.mark.asyncio
    async def test_invalid_storage_location_id(self, db_session):
        """Non-existent storage_location_id → ForeignKeyError."""
        # Try to create bin with non-existent location
        bin_obj = StorageBin(
            code="WH-AREA-LOC1-SEG001",
            label="Invalid FK",
            storage_location_id=99999,  # Does not exist
        )
        db_session.add(bin_obj)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_null_storage_location_id(self, db_session):
        """NULL storage_location_id → NotNullError."""
        # Try to create bin with NULL location_id
        bin_obj = StorageBin(
            code="WH-AREA-LOC1-SEG001",
            label="Null FK",
            storage_location_id=None,  # NULL not allowed
        )
        db_session.add(bin_obj)

        with pytest.raises((IntegrityError, TypeError, ValueError)):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_null_storage_bin_type_id(self, db_session, storage_location_factory):
        """NULL storage_bin_type_id → SUCCESS (NULLABLE)."""
        location = await storage_location_factory(code="WH-AREA-LOC1")

        # Create bin with NULL bin_type_id (should succeed)
        bin_obj = StorageBin(
            code="WH-AREA-LOC1-SEG001",
            label="No Type",
            storage_location_id=location.location_id,
            storage_bin_type_id=None,  # NULL allowed
        )
        db_session.add(bin_obj)
        await db_session.commit()

        # Verify created
        result = await db_session.execute(
            select(StorageBin).where(StorageBin.code == "WH-AREA-LOC1-SEG001")
        )
        created_bin = result.scalar_one()
        assert created_bin.storage_bin_type_id is None
