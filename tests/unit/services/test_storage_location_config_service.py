"""Unit tests for StorageLocationConfigService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock for StorageLocationConfigRepository.

Coverage target: ≥85%

Test categories:
- create: success, all required fields, validation
- get_by_id: success, not found
- get_all: empty, multiple records, limit
- update: success, not found, partial updates
- delete: success, not found

See:
    - Service: app/services/storage_location_config_service.py
    - Model: app/models/storage_location_config.py
    - Schema: app/schemas/storage_location_config_schema.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.storage_location_config import StorageLocationConfig
from app.schemas.storage_location_config_schema import (
    StorageLocationConfigCreateRequest,
    StorageLocationConfigResponse,
    StorageLocationConfigUpdateRequest,
)
from app.services.storage_location_config_service import StorageLocationConfigService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repo():
    """Create mock StorageLocationConfigRepository for testing."""
    return AsyncMock()


@pytest.fixture
def config_service(mock_repo):
    """Create StorageLocationConfigService with mocked repository."""
    return StorageLocationConfigService(repo=mock_repo)


@pytest.fixture
def mock_config():
    """Create mock StorageLocationConfig model instance."""
    config = Mock(spec=StorageLocationConfig)
    config.id = 1
    config.storage_location_id = 100
    config.product_id = 45
    config.packaging_catalog_id = 12
    config.expected_product_state_id = 3
    config.area_cm2 = 5000.0
    config.active = True
    config.notes = None
    config.created_at = datetime(2025, 10, 20, 14, 30, 0)
    config.updated_at = None
    return config


# ============================================================================
# Test Create
# ============================================================================


@pytest.mark.asyncio
async def test_create_success(config_service, mock_repo, mock_config):
    """Test successful storage location config creation."""
    # Arrange
    # Update mock_config to match the request
    mock_config.area_cm2 = 1500

    request = StorageLocationConfigCreateRequest(
        storage_location_id=100,
        product_id=45,
        packaging_catalog_id=12,
        expected_product_state_id=3,
        area_cm2=1500,
    )

    mock_repo.create.return_value = mock_config

    # Act
    response = await config_service.create(request)

    # Assert
    assert isinstance(response, StorageLocationConfigResponse)
    assert response.id == 1
    assert response.storage_location_id == 100
    assert response.product_id == 45
    assert response.packaging_catalog_id == 12
    assert response.expected_product_state_id == 3
    assert response.area_cm2 == 1500
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_with_positive_area(config_service, mock_repo):
    """Test creating config with positive area (area_cm2 must be > 0 per schema)."""
    # Arrange
    request = StorageLocationConfigCreateRequest(
        storage_location_id=101,
        product_id=46,
        packaging_catalog_id=13,
        expected_product_state_id=3,
        area_cm2=1200,  # Must be positive (gt=0)
    )

    mock_zero = Mock(spec=StorageLocationConfig)
    mock_zero.id = 2
    mock_zero.storage_location_id = 101
    mock_zero.product_id = 46
    mock_zero.packaging_catalog_id = 13
    mock_zero.expected_product_state_id = 3
    mock_zero.area_cm2 = 1200
    mock_zero.active = True
    mock_zero.notes = None
    mock_zero.created_at = datetime(2025, 10, 20, 15, 0, 0)
    mock_zero.updated_at = None

    mock_repo.create.return_value = mock_zero

    # Act
    response = await config_service.create(request)

    # Assert
    assert response.area_cm2 == 1200


@pytest.mark.asyncio
async def test_create_different_location(config_service, mock_repo):
    """Test creating config for different storage location."""
    # Arrange
    request = StorageLocationConfigCreateRequest(
        storage_location_id=200,
        product_id=50,
        packaging_catalog_id=15,
        expected_product_state_id=4,
        area_cm2=2000,
    )

    mock_config2 = Mock(spec=StorageLocationConfig)
    mock_config2.id = 3
    mock_config2.storage_location_id = 200
    mock_config2.product_id = 50
    mock_config2.packaging_catalog_id = 15
    mock_config2.expected_product_state_id = 4
    mock_config2.area_cm2 = 2000
    mock_config2.active = True
    mock_config2.notes = None
    mock_config2.created_at = datetime(2025, 10, 20, 15, 30, 0)
    mock_config2.updated_at = None

    mock_repo.create.return_value = mock_config2

    # Act
    response = await config_service.create(request)

    # Assert
    assert response.storage_location_id == 200
    assert response.area_cm2 == 2000


# ============================================================================
# Test Get By ID
# ============================================================================


@pytest.mark.asyncio
async def test_get_by_id_success(config_service, mock_repo, mock_config):
    """Test getting storage location config by ID successfully."""
    # Arrange
    # Update mock_config to match expected values
    mock_config.area_cm2 = 1500
    mock_repo.get.return_value = mock_config

    # Act
    response = await config_service.get_by_id(1)

    # Assert
    assert response.id == 1
    assert response.storage_location_id == 100
    assert response.product_id == 45
    assert response.area_cm2 == 1500
    mock_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_by_id_not_found(config_service, mock_repo):
    """Test getting non-existent config raises ValueError."""
    # Arrange
    mock_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="StorageLocationConfig"):
        await config_service.get_by_id(999)


# ============================================================================
# Test Get All
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_success(config_service, mock_repo):
    """Test getting all storage location configs."""
    # Arrange
    mock_config1 = Mock(spec=StorageLocationConfig)
    mock_config1.id = 1
    mock_config1.storage_location_id = 100
    mock_config1.product_id = 45
    mock_config1.packaging_catalog_id = 12
    mock_config1.expected_product_state_id = 3
    mock_config1.area_cm2 = 1500
    mock_config1.active = True
    mock_config1.notes = None
    mock_config1.created_at = datetime(2025, 10, 20, 14, 0, 0)
    mock_config1.updated_at = None

    mock_config2 = Mock(spec=StorageLocationConfig)
    mock_config2.id = 2
    mock_config2.storage_location_id = 101
    mock_config2.product_id = 46
    mock_config2.packaging_catalog_id = 13
    mock_config2.expected_product_state_id = 3
    mock_config2.area_cm2 = 2000
    mock_config2.active = True
    mock_config2.notes = None
    mock_config2.created_at = datetime(2025, 10, 20, 14, 30, 0)
    mock_config2.updated_at = None

    mock_repo.get_multi.return_value = [mock_config1, mock_config2]

    # Act
    response = await config_service.get_all()

    # Assert
    assert len(response) == 2
    assert response[0].storage_location_id == 100
    assert response[1].storage_location_id == 101
    mock_repo.get_multi.assert_called_once_with(limit=100)


@pytest.mark.asyncio
async def test_get_all_empty(config_service, mock_repo):
    """Test getting configs when none exist."""
    # Arrange
    mock_repo.get_multi.return_value = []

    # Act
    response = await config_service.get_all()

    # Assert
    assert len(response) == 0


@pytest.mark.asyncio
async def test_get_all_with_custom_limit(config_service, mock_repo):
    """Test getting configs with custom limit."""
    # Arrange
    mock_repo.get_multi.return_value = []

    # Act
    await config_service.get_all(limit=50)

    # Assert
    mock_repo.get_multi.assert_called_once_with(limit=50)


# ============================================================================
# Test Update
# ============================================================================


@pytest.mark.asyncio
async def test_update_success(config_service, mock_repo, mock_config):
    """Test updating storage location config successfully."""
    # Arrange
    request = StorageLocationConfigUpdateRequest(
        product_id=47, packaging_catalog_id=14, area_cm2=1800
    )

    updated_mock = Mock(spec=StorageLocationConfig)
    updated_mock.id = 1
    updated_mock.storage_location_id = 100  # Unchanged
    updated_mock.product_id = 47
    updated_mock.packaging_catalog_id = 14
    updated_mock.expected_product_state_id = 3  # Unchanged
    updated_mock.area_cm2 = 1800
    updated_mock.active = True
    updated_mock.notes = None
    updated_mock.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_mock.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_repo.get.return_value = mock_config
    mock_repo.update.return_value = updated_mock

    # Act
    response = await config_service.update(1, request)

    # Assert
    assert response.product_id == 47
    assert response.packaging_catalog_id == 14
    assert response.area_cm2 == 1800
    assert response.updated_at is not None
    mock_repo.get.assert_called_once_with(1)
    mock_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_not_found(config_service, mock_repo):
    """Test updating non-existent config raises ValueError."""
    # Arrange
    request = StorageLocationConfigUpdateRequest(product_id=50)
    mock_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="StorageLocationConfig"):
        await config_service.update(999, request)


@pytest.mark.asyncio
async def test_update_partial_product_only(config_service, mock_repo, mock_config):
    """Test partial update (only product_id, others unchanged)."""
    # Arrange
    request = StorageLocationConfigUpdateRequest(product_id=48)

    updated_mock = Mock(spec=StorageLocationConfig)
    updated_mock.id = 1
    updated_mock.storage_location_id = 100
    updated_mock.product_id = 48
    updated_mock.packaging_catalog_id = 12  # Unchanged
    updated_mock.expected_product_state_id = 3  # Unchanged
    updated_mock.area_cm2 = 1500  # Unchanged
    updated_mock.active = True
    updated_mock.notes = None
    updated_mock.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_mock.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_repo.get.return_value = mock_config
    mock_repo.update.return_value = updated_mock

    # Act
    response = await config_service.update(1, request)

    # Assert
    assert response.product_id == 48
    assert response.packaging_catalog_id == 12  # Unchanged
    assert response.area_cm2 == 1500  # Unchanged
    call_args = mock_repo.update.call_args
    assert "product_id" in call_args[0][1]


@pytest.mark.asyncio
async def test_update_partial_quantity_only(config_service, mock_repo, mock_config):
    """Test partial update (only area_cm2, others unchanged)."""
    # Arrange
    request = StorageLocationConfigUpdateRequest(area_cm2=2500)

    updated_mock = Mock(spec=StorageLocationConfig)
    updated_mock.id = 1
    updated_mock.storage_location_id = 100
    updated_mock.product_id = 45  # Unchanged
    updated_mock.packaging_catalog_id = 12  # Unchanged
    updated_mock.expected_product_state_id = 3  # Unchanged
    updated_mock.area_cm2 = 2500
    updated_mock.active = True
    updated_mock.notes = None
    updated_mock.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_mock.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_repo.get.return_value = mock_config
    mock_repo.update.return_value = updated_mock

    # Act
    response = await config_service.update(1, request)

    # Assert
    assert response.product_id == 45  # Unchanged
    assert response.area_cm2 == 2500
    call_args = mock_repo.update.call_args
    assert "area_cm2" in call_args[0][1]


@pytest.mark.asyncio
async def test_update_partial_multiple_fields(config_service, mock_repo, mock_config):
    """Test partial update with multiple fields."""
    # Arrange
    request = StorageLocationConfigUpdateRequest(
        packaging_catalog_id=15, expected_product_state_id=4, area_cm2=3000
    )

    updated_mock = Mock(spec=StorageLocationConfig)
    updated_mock.id = 1
    updated_mock.storage_location_id = 100
    updated_mock.product_id = 45  # Unchanged
    updated_mock.packaging_catalog_id = 15
    updated_mock.expected_product_state_id = 4
    updated_mock.area_cm2 = 3000
    updated_mock.active = True
    updated_mock.notes = None
    updated_mock.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_mock.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_repo.get.return_value = mock_config
    mock_repo.update.return_value = updated_mock

    # Act
    response = await config_service.update(1, request)

    # Assert
    assert response.product_id == 45  # Unchanged
    assert response.packaging_catalog_id == 15
    assert response.expected_product_state_id == 4
    assert response.area_cm2 == 3000
    call_args = mock_repo.update.call_args
    update_data = call_args[0][1]
    assert "packaging_catalog_id" in update_data
    assert "expected_product_state_id" in update_data
    assert "area_cm2" in update_data


# ============================================================================
# Test Delete
# ============================================================================


@pytest.mark.asyncio
async def test_delete_success(config_service, mock_repo, mock_config):
    """Test deleting storage location config successfully."""
    # Arrange
    mock_repo.get.return_value = mock_config
    mock_repo.delete.return_value = None

    # Act
    await config_service.delete(1)

    # Assert
    mock_repo.get.assert_called_once_with(1)
    mock_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_not_found(config_service, mock_repo):
    """Test deleting non-existent config raises ValueError."""
    # Arrange
    mock_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="StorageLocationConfig"):
        await config_service.delete(999)
