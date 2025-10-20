"""Unit tests for MovementValidationService.

Tests business logic for validating stock movements.
No database access - pure validation logic.

TESTING STRATEGY:
- Test validation rules for movement data
- Test quantity validation (zero, positive, negative)
- Test inbound/outbound consistency
- Test required fields validation
- Test error message formatting

Coverage target: ≥80%

Test categories:
- validate_movement_request: success, various failure scenarios
- Quantity validation: zero, positive inbound, negative outbound
- Field validation: missing movement_type

See:
    - Service: app/services/movement_validation_service.py
"""

import pytest

from app.services.movement_validation_service import MovementValidationService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def validation_service():
    """Create MovementValidationService instance."""
    return MovementValidationService()


# ============================================================================
# validate_movement_request - Success cases
# ============================================================================


@pytest.mark.asyncio
async def test_validate_movement_request_inbound_success(validation_service):
    """Test validation passes for valid inbound movement."""
    # Arrange
    movement_data = {
        "quantity": 100,
        "is_inbound": True,
        "movement_type": "manual_init",
        "batch_id": 5,
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is True
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_validate_movement_request_outbound_success(validation_service):
    """Test validation passes for valid outbound movement."""
    # Arrange
    movement_data = {
        "quantity": -50,
        "is_inbound": False,
        "movement_type": "ventas",
        "batch_id": 5,
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is True
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_validate_movement_request_positive_outbound_success(validation_service):
    """Test validation passes for outbound with positive quantity (gets negated later)."""
    # Arrange - Some systems pass positive quantity and rely on is_inbound flag
    movement_data = {
        "quantity": 30,
        "is_inbound": False,
        "movement_type": "muerte",
        "batch_id": 5,
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    # This should FAIL according to the validation rules
    assert result["valid"] is False
    assert "Outbound movements must have negative quantity" in result["errors"]


# ============================================================================
# validate_movement_request - Quantity validation failures
# ============================================================================


@pytest.mark.asyncio
async def test_validate_movement_request_zero_quantity(validation_service):
    """Test validation fails when quantity is zero."""
    # Arrange
    movement_data = {
        "quantity": 0,
        "is_inbound": True,
        "movement_type": "ajuste",
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is False
    assert "Quantity cannot be zero" in result["errors"]


@pytest.mark.asyncio
async def test_validate_movement_request_inbound_negative_quantity(validation_service):
    """Test validation fails when inbound movement has negative quantity."""
    # Arrange
    movement_data = {
        "quantity": -50,
        "is_inbound": True,
        "movement_type": "manual_init",
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is False
    assert "Inbound movements must have positive quantity" in result["errors"]


@pytest.mark.asyncio
async def test_validate_movement_request_outbound_positive_quantity(validation_service):
    """Test validation fails when outbound movement has positive quantity."""
    # Arrange
    movement_data = {
        "quantity": 50,
        "is_inbound": False,
        "movement_type": "ventas",
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is False
    assert "Outbound movements must have negative quantity" in result["errors"]


# ============================================================================
# validate_movement_request - Required field validation
# ============================================================================


@pytest.mark.asyncio
async def test_validate_movement_request_missing_movement_type(validation_service):
    """Test validation fails when movement_type is missing."""
    # Arrange
    movement_data = {
        "quantity": 100,
        "is_inbound": True,
        # movement_type missing
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is False
    assert "Movement type is required" in result["errors"]


@pytest.mark.asyncio
async def test_validate_movement_request_empty_movement_type(validation_service):
    """Test validation fails when movement_type is empty string."""
    # Arrange
    movement_data = {
        "quantity": 100,
        "is_inbound": True,
        "movement_type": "",  # Empty string
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is False
    assert "Movement type is required" in result["errors"]


@pytest.mark.asyncio
async def test_validate_movement_request_none_movement_type(validation_service):
    """Test validation fails when movement_type is None."""
    # Arrange
    movement_data = {
        "quantity": 100,
        "is_inbound": True,
        "movement_type": None,
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is False
    assert "Movement type is required" in result["errors"]


# ============================================================================
# validate_movement_request - Multiple errors
# ============================================================================


@pytest.mark.asyncio
async def test_validate_movement_request_multiple_errors(validation_service):
    """Test validation returns all errors when multiple rules are violated."""
    # Arrange
    movement_data = {
        "quantity": 0,  # Error 1: Zero quantity
        "is_inbound": True,
        # movement_type missing - Error 2
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is False
    assert len(result["errors"]) == 2
    assert "Quantity cannot be zero" in result["errors"]
    assert "Movement type is required" in result["errors"]


@pytest.mark.asyncio
async def test_validate_movement_request_all_errors(validation_service):
    """Test validation with all possible errors."""
    # Arrange
    movement_data = {
        "quantity": 0,  # Error 1
        "is_inbound": True,
        # movement_type missing - Error 2
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is False
    assert len(result["errors"]) >= 2


@pytest.mark.asyncio
async def test_validate_movement_request_inbound_negative_and_zero(validation_service):
    """Test zero quantity takes precedence over sign validation."""
    # Arrange
    movement_data = {
        "quantity": 0,
        "is_inbound": True,
        "movement_type": "manual_init",
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is False
    # Zero check happens first
    assert "Quantity cannot be zero" in result["errors"]


# ============================================================================
# Edge cases
# ============================================================================


@pytest.mark.asyncio
async def test_validate_movement_request_default_quantity_zero(validation_service):
    """Test validation when quantity defaults to zero."""
    # Arrange
    movement_data = {
        # quantity not provided - defaults to 0
        "is_inbound": True,
        "movement_type": "ajuste",
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is False
    assert "Quantity cannot be zero" in result["errors"]


@pytest.mark.asyncio
async def test_validate_movement_request_default_is_inbound_false(validation_service):
    """Test validation when is_inbound defaults to False."""
    # Arrange
    movement_data = {
        "quantity": 50,  # Positive
        # is_inbound not provided - defaults to False
        "movement_type": "ventas",
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is False
    assert "Outbound movements must have negative quantity" in result["errors"]


@pytest.mark.asyncio
async def test_validate_movement_request_large_positive_quantity(validation_service):
    """Test validation with large positive quantity."""
    # Arrange
    movement_data = {
        "quantity": 1_000_000,
        "is_inbound": True,
        "movement_type": "manual_init",
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is True
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_validate_movement_request_large_negative_quantity(validation_service):
    """Test validation with large negative quantity."""
    # Arrange
    movement_data = {
        "quantity": -1_000_000,
        "is_inbound": False,
        "movement_type": "ventas",
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is True
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_validate_movement_request_various_movement_types(validation_service):
    """Test validation accepts various movement types."""
    # Arrange
    movement_types = ["manual_init", "ventas", "muerte", "ajuste", "transfer", "detection_update"]

    for m_type in movement_types:
        movement_data = {
            "quantity": 10,
            "is_inbound": True,
            "movement_type": m_type,
        }

        # Act
        result = await validation_service.validate_movement_request(movement_data)

        # Assert
        assert result["valid"] is True, f"Failed for movement_type: {m_type}"
        assert result["errors"] == []


# ============================================================================
# Return structure validation
# ============================================================================


@pytest.mark.asyncio
async def test_validate_movement_request_return_structure_valid(validation_service):
    """Test return structure for valid movement."""
    # Arrange
    movement_data = {
        "quantity": 100,
        "is_inbound": True,
        "movement_type": "manual_init",
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert isinstance(result, dict)
    assert "valid" in result
    assert "errors" in result
    assert isinstance(result["valid"], bool)
    assert isinstance(result["errors"], list)


@pytest.mark.asyncio
async def test_validate_movement_request_return_structure_invalid(validation_service):
    """Test return structure for invalid movement."""
    # Arrange
    movement_data = {
        "quantity": 0,
        "is_inbound": True,
        "movement_type": "manual_init",
    }

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert isinstance(result, dict)
    assert "valid" in result
    assert "errors" in result
    assert isinstance(result["valid"], bool)
    assert isinstance(result["errors"], list)
    assert len(result["errors"]) > 0
    assert all(isinstance(error, str) for error in result["errors"])


@pytest.mark.asyncio
async def test_validate_movement_request_empty_dict(validation_service):
    """Test validation with empty movement data."""
    # Arrange
    movement_data = {}

    # Act
    result = await validation_service.validate_movement_request(movement_data)

    # Assert
    assert result["valid"] is False
    assert "Quantity cannot be zero" in result["errors"]
    assert "Movement type is required" in result["errors"]
