"""
Unit tests for Stock Movement schemas.

Tests cover:
- ManualStockInitRequest validation
- StockMovementRequest validation
- Field constraints (positive numbers, max length, enums)
- Error messages and Pydantic error handling
"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.stock_movement_schema import (
    ManualStockInitRequest,
    StockMovementRequest,
)


class TestManualStockInitRequest:
    """Tests for ManualStockInitRequest schema."""

    def test_valid_request_all_fields(self):
        """Test creating request with all valid fields."""
        request = ManualStockInitRequest(
            storage_location_id=1,
            product_id=45,
            packaging_catalog_id=12,
            product_size_id=3,
            quantity=1500,
            planting_date=date(2025, 9, 15),
            notes="Initial stock count for location 1",
        )

        assert request.storage_location_id == 1
        assert request.product_id == 45
        assert request.packaging_catalog_id == 12
        assert request.product_size_id == 3
        assert request.quantity == 1500
        assert request.planting_date == date(2025, 9, 15)
        assert request.notes == "Initial stock count for location 1"

    def test_valid_request_minimal_fields(self):
        """Test creating request with only required fields."""
        request = ManualStockInitRequest(
            storage_location_id=1,
            product_id=45,
            packaging_catalog_id=12,
            product_size_id=3,
            quantity=1500,
            planting_date=date(2025, 9, 15),
        )

        assert request.storage_location_id == 1
        assert request.product_id == 45
        assert request.quantity == 1500
        assert request.notes is None

    def test_valid_request_max_quantity(self):
        """Test request with very large quantity."""
        request = ManualStockInitRequest(
            storage_location_id=1,
            product_id=45,
            packaging_catalog_id=12,
            product_size_id=3,
            quantity=999999,
            planting_date=date(2025, 9, 15),
        )

        assert request.quantity == 999999

    def test_valid_request_notes_at_max_length(self):
        """Test request with notes at maximum length."""
        max_notes = "x" * 500
        request = ManualStockInitRequest(
            storage_location_id=1,
            product_id=45,
            packaging_catalog_id=12,
            product_size_id=3,
            quantity=1500,
            planting_date=date(2025, 9, 15),
            notes=max_notes,
        )

        assert len(request.notes) == 500

    def test_valid_request_empty_notes(self):
        """Test request with empty string notes."""
        request = ManualStockInitRequest(
            storage_location_id=1,
            product_id=45,
            packaging_catalog_id=12,
            product_size_id=3,
            quantity=1500,
            planting_date=date(2025, 9, 15),
            notes="",
        )

        assert request.notes == ""

    def test_invalid_storage_location_id_zero(self):
        """Test that storage_location_id cannot be zero."""
        with pytest.raises(ValidationError) as exc_info:
            ManualStockInitRequest(
                storage_location_id=0,
                product_id=45,
                packaging_catalog_id=12,
                product_size_id=3,
                quantity=1500,
                planting_date=date(2025, 9, 15),
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("storage_location_id",) for err in errors)
        assert any("greater than 0" in str(err["msg"]).lower() for err in errors)

    def test_invalid_storage_location_id_negative(self):
        """Test that storage_location_id cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            ManualStockInitRequest(
                storage_location_id=-1,
                product_id=45,
                packaging_catalog_id=12,
                product_size_id=3,
                quantity=1500,
                planting_date=date(2025, 9, 15),
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("storage_location_id",) for err in errors)

    def test_invalid_product_id_zero(self):
        """Test that product_id cannot be zero."""
        with pytest.raises(ValidationError) as exc_info:
            ManualStockInitRequest(
                storage_location_id=1,
                product_id=0,
                packaging_catalog_id=12,
                product_size_id=3,
                quantity=1500,
                planting_date=date(2025, 9, 15),
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("product_id",) for err in errors)

    def test_invalid_packaging_catalog_id_negative(self):
        """Test that packaging_catalog_id cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            ManualStockInitRequest(
                storage_location_id=1,
                product_id=45,
                packaging_catalog_id=-5,
                product_size_id=3,
                quantity=1500,
                planting_date=date(2025, 9, 15),
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("packaging_catalog_id",) for err in errors)

    def test_invalid_product_size_id_zero(self):
        """Test that product_size_id cannot be zero."""
        with pytest.raises(ValidationError) as exc_info:
            ManualStockInitRequest(
                storage_location_id=1,
                product_id=45,
                packaging_catalog_id=12,
                product_size_id=0,
                quantity=1500,
                planting_date=date(2025, 9, 15),
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("product_size_id",) for err in errors)

    def test_invalid_quantity_zero(self):
        """Test that quantity cannot be zero."""
        with pytest.raises(ValidationError) as exc_info:
            ManualStockInitRequest(
                storage_location_id=1,
                product_id=45,
                packaging_catalog_id=12,
                product_size_id=3,
                quantity=0,
                planting_date=date(2025, 9, 15),
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("quantity",) for err in errors)
        # Should trigger both Field constraint and custom validator
        assert any("greater than 0" in str(err["msg"]).lower() for err in errors)

    def test_invalid_quantity_negative(self):
        """Test that quantity cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            ManualStockInitRequest(
                storage_location_id=1,
                product_id=45,
                packaging_catalog_id=12,
                product_size_id=3,
                quantity=-100,
                planting_date=date(2025, 9, 15),
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("quantity",) for err in errors)

    def test_invalid_notes_too_long(self):
        """Test that notes cannot exceed 500 characters."""
        with pytest.raises(ValidationError) as exc_info:
            ManualStockInitRequest(
                storage_location_id=1,
                product_id=45,
                packaging_catalog_id=12,
                product_size_id=3,
                quantity=1500,
                planting_date=date(2025, 9, 15),
                notes="x" * 501,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("notes",) for err in errors)
        assert any("500" in str(err["msg"]) for err in errors)

    def test_invalid_planting_date_string(self):
        """Test that planting_date must be a date object."""
        with pytest.raises(ValidationError) as exc_info:
            ManualStockInitRequest(
                storage_location_id=1,
                product_id=45,
                packaging_catalog_id=12,
                product_size_id=3,
                quantity=1500,
                planting_date="not-a-date",
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("planting_date",) for err in errors)

    def test_missing_required_field_storage_location_id(self):
        """Test that storage_location_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ManualStockInitRequest(
                product_id=45,
                packaging_catalog_id=12,
                product_size_id=3,
                quantity=1500,
                planting_date=date(2025, 9, 15),
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("storage_location_id",) for err in errors)
        assert any(
            "missing" in str(err["msg"]).lower() or "required" in str(err["msg"]).lower()
            for err in errors
        )

    def test_missing_required_field_quantity(self):
        """Test that quantity is required."""
        with pytest.raises(ValidationError) as exc_info:
            ManualStockInitRequest(
                storage_location_id=1,
                product_id=45,
                packaging_catalog_id=12,
                product_size_id=3,
                planting_date=date(2025, 9, 15),
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("quantity",) for err in errors)

    def test_model_dump(self):
        """Test serializing request to dict."""
        request = ManualStockInitRequest(
            storage_location_id=1,
            product_id=45,
            packaging_catalog_id=12,
            product_size_id=3,
            quantity=1500,
            planting_date=date(2025, 9, 15),
            notes="Test notes",
        )

        data = request.model_dump()
        assert data["storage_location_id"] == 1
        assert data["product_id"] == 45
        assert data["quantity"] == 1500
        assert data["planting_date"] == date(2025, 9, 15)
        assert data["notes"] == "Test notes"

    def test_model_dump_json(self):
        """Test serializing request to JSON."""
        request = ManualStockInitRequest(
            storage_location_id=1,
            product_id=45,
            packaging_catalog_id=12,
            product_size_id=3,
            quantity=1500,
            planting_date=date(2025, 9, 15),
        )

        json_str = request.model_dump_json()
        assert '"storage_location_id":1' in json_str
        assert '"quantity":1500' in json_str
        assert '"planting_date":"2025-09-15"' in json_str


class TestStockMovementRequest:
    """Tests for StockMovementRequest schema."""

    def test_valid_request_plantado(self):
        """Test creating request with plantado movement type."""
        request = StockMovementRequest(
            storage_batch_id=1,
            movement_type="plantado",
            quantity=-50,
            notes="Moving plants to greenhouse",
        )

        assert request.storage_batch_id == 1
        assert request.movement_type == "plantado"
        assert request.quantity == -50
        assert request.notes == "Moving plants to greenhouse"

    def test_valid_request_muerte(self):
        """Test creating request with muerte movement type."""
        request = StockMovementRequest(storage_batch_id=1, movement_type="muerte", quantity=-10)

        assert request.movement_type == "muerte"
        assert request.quantity == -10
        assert request.notes is None

    def test_valid_request_trasplante(self):
        """Test creating request with trasplante movement type."""
        request = StockMovementRequest(storage_batch_id=1, movement_type="trasplante", quantity=25)

        assert request.movement_type == "trasplante"

    def test_valid_request_ventas(self):
        """Test creating request with ventas movement type."""
        request = StockMovementRequest(storage_batch_id=1, movement_type="ventas", quantity=-100)

        assert request.movement_type == "ventas"

    def test_valid_request_ajuste(self):
        """Test creating request with ajuste movement type."""
        request = StockMovementRequest(storage_batch_id=1, movement_type="ajuste", quantity=5)

        assert request.movement_type == "ajuste"

    def test_valid_request_positive_quantity(self):
        """Test request with positive quantity."""
        request = StockMovementRequest(storage_batch_id=1, movement_type="ajuste", quantity=1000)

        assert request.quantity == 1000

    def test_valid_request_negative_quantity(self):
        """Test request with negative quantity."""
        request = StockMovementRequest(storage_batch_id=1, movement_type="muerte", quantity=-500)

        assert request.quantity == -500

    def test_valid_request_zero_quantity(self):
        """Test request with zero quantity (allowed in schema, service layer validates)."""
        request = StockMovementRequest(storage_batch_id=1, movement_type="ajuste", quantity=0)

        assert request.quantity == 0

    def test_valid_request_notes_at_max_length(self):
        """Test request with notes at maximum length."""
        max_notes = "x" * 500
        request = StockMovementRequest(
            storage_batch_id=1, movement_type="ajuste", quantity=10, notes=max_notes
        )

        assert len(request.notes) == 500

    def test_invalid_storage_batch_id_zero(self):
        """Test that storage_batch_id cannot be zero."""
        with pytest.raises(ValidationError) as exc_info:
            StockMovementRequest(storage_batch_id=0, movement_type="ajuste", quantity=10)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("storage_batch_id",) for err in errors)

    def test_invalid_storage_batch_id_negative(self):
        """Test that storage_batch_id cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            StockMovementRequest(storage_batch_id=-1, movement_type="ajuste", quantity=10)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("storage_batch_id",) for err in errors)

    def test_invalid_movement_type_empty(self):
        """Test that movement_type cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            StockMovementRequest(storage_batch_id=1, movement_type="", quantity=10)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("movement_type",) for err in errors)

    def test_invalid_movement_type_wrong_value(self):
        """Test that movement_type must be one of allowed values."""
        with pytest.raises(ValidationError) as exc_info:
            StockMovementRequest(storage_batch_id=1, movement_type="invalid_type", quantity=10)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("movement_type",) for err in errors)
        assert any("plantado" in str(err["msg"]) for err in errors)

    def test_invalid_movement_type_case_sensitive(self):
        """Test that movement_type is case-sensitive."""
        with pytest.raises(ValidationError) as exc_info:
            StockMovementRequest(storage_batch_id=1, movement_type="PLANTADO", quantity=10)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("movement_type",) for err in errors)

    def test_invalid_notes_too_long(self):
        """Test that notes cannot exceed 500 characters."""
        with pytest.raises(ValidationError) as exc_info:
            StockMovementRequest(
                storage_batch_id=1, movement_type="ajuste", quantity=10, notes="x" * 501
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("notes",) for err in errors)
        assert any("500" in str(err["msg"]) for err in errors)

    def test_missing_required_field_storage_batch_id(self):
        """Test that storage_batch_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            StockMovementRequest(movement_type="ajuste", quantity=10)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("storage_batch_id",) for err in errors)

    def test_missing_required_field_movement_type(self):
        """Test that movement_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            StockMovementRequest(storage_batch_id=1, quantity=10)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("movement_type",) for err in errors)

    def test_missing_required_field_quantity(self):
        """Test that quantity is required."""
        with pytest.raises(ValidationError) as exc_info:
            StockMovementRequest(storage_batch_id=1, movement_type="ajuste")

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("quantity",) for err in errors)

    def test_model_dump(self):
        """Test serializing request to dict."""
        request = StockMovementRequest(
            storage_batch_id=1, movement_type="plantado", quantity=-50, notes="Test"
        )

        data = request.model_dump()
        assert data["storage_batch_id"] == 1
        assert data["movement_type"] == "plantado"
        assert data["quantity"] == -50
        assert data["notes"] == "Test"

    def test_model_dump_json(self):
        """Test serializing request to JSON."""
        request = StockMovementRequest(storage_batch_id=1, movement_type="muerte", quantity=-10)

        json_str = request.model_dump_json()
        assert '"storage_batch_id":1' in json_str
        assert '"movement_type":"muerte"' in json_str
        assert '"quantity":-10' in json_str
