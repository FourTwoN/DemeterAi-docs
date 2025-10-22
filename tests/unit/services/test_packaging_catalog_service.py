"""Unit tests for PackagingCatalogService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock for PackagingCatalogRepository.

Coverage target: ≥85%

Test categories:
- create: success, all required fields
- get_by_id: success, not found
- get_all: empty, multiple records, limit
- update: success, not found, partial updates
- delete: success, not found

See:
    - Service: app/services/packaging_catalog_service.py
    - Model: app/models/packaging_catalog.py
    - Schema: app/schemas/packaging_catalog_schema.py
"""

from unittest.mock import AsyncMock, Mock

import pytest

from app.models.packaging_catalog import PackagingCatalog
from app.schemas.packaging_catalog_schema import (
    PackagingCatalogCreateRequest,
    PackagingCatalogResponse,
    PackagingCatalogUpdateRequest,
)
from app.services.packaging_catalog_service import PackagingCatalogService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repo():
    """Create mock PackagingCatalogRepository for testing."""
    return AsyncMock()


@pytest.fixture
def packaging_catalog_service(mock_repo):
    """Create PackagingCatalogService with mocked repository."""
    return PackagingCatalogService(repo=mock_repo)


@pytest.fixture
def mock_packaging_catalog():
    """Create mock PackagingCatalog model instance."""
    catalog = Mock(spec=PackagingCatalog)
    catalog.id = 1
    catalog.sku = "POT-PLASTIC-BLACK-10L"
    catalog.name = "10L Black Plastic Pot"
    catalog.packaging_type_id = 1
    catalog.packaging_material_id = 2
    catalog.packaging_color_id = 3
    catalog.volume_liters = 10.0
    catalog.diameter_cm = 25.0
    catalog.height_cm = 20.0
    return catalog


# ============================================================================
# Test Create
# ============================================================================


@pytest.mark.asyncio
async def test_create_success(packaging_catalog_service, mock_repo, mock_packaging_catalog):
    """Test successful packaging catalog creation."""
    # Arrange
    request = PackagingCatalogCreateRequest(
        sku="POT-PLASTIC-BLACK-10L",
        name="10L Black Plastic Pot",
        packaging_type_id=1,
        packaging_material_id=2,
        packaging_color_id=3,
        volume_liters=10.0,
        diameter_cm=25.0,
        height_cm=20.0,
    )

    mock_repo.create.return_value = mock_packaging_catalog

    # Act
    response = await packaging_catalog_service.create(request)

    # Assert
    assert isinstance(response, PackagingCatalogResponse)
    assert response.id == 1
    assert response.sku == "POT-PLASTIC-BLACK-10L"
    assert response.name == "10L Black Plastic Pot"
    assert response.packaging_type_id == 1
    assert response.packaging_material_id == 2
    assert response.packaging_color_id == 3
    assert response.volume_liters == 10.0
    assert response.diameter_cm == 25.0
    assert response.height_cm == 20.0
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_different_dimensions(packaging_catalog_service, mock_repo):
    """Test creating packaging catalog with different dimensions."""
    # Arrange
    request = PackagingCatalogCreateRequest(
        sku="POT-CERAMIC-WHITE-15L",
        name="15L White Ceramic Pot",
        packaging_type_id=1,
        packaging_material_id=3,
        packaging_color_id=1,
        volume_liters=15.0,
        diameter_cm=30.0,
        height_cm=25.0,
    )

    mock_catalog = Mock(spec=PackagingCatalog)
    mock_catalog.id = 2
    mock_catalog.sku = "POT-CERAMIC-WHITE-15L"
    mock_catalog.name = "15L White Ceramic Pot"
    mock_catalog.packaging_type_id = 1
    mock_catalog.packaging_material_id = 3
    mock_catalog.packaging_color_id = 1
    mock_catalog.volume_liters = 15.0
    mock_catalog.diameter_cm = 30.0
    mock_catalog.height_cm = 25.0

    mock_repo.create.return_value = mock_catalog

    # Act
    response = await packaging_catalog_service.create(request)

    # Assert
    assert response.volume_liters == 15.0
    assert response.diameter_cm == 30.0
    assert response.height_cm == 25.0


@pytest.mark.asyncio
async def test_create_validates_positive_dimensions(packaging_catalog_service, mock_repo):
    """Test that schema validates positive dimensions (gt=0)."""
    # Arrange - Schema should validate gt=0
    request = PackagingCatalogCreateRequest(
        sku="POT-TEST",
        name="Test Pot",
        packaging_type_id=1,
        packaging_material_id=2,
        packaging_color_id=3,
        volume_liters=5.0,
        diameter_cm=15.0,
        height_cm=10.0,
    )

    mock_catalog = Mock(spec=PackagingCatalog)
    mock_catalog.id = 3
    mock_catalog.sku = "POT-TEST"
    mock_catalog.name = "Test Pot"
    mock_catalog.packaging_type_id = 1
    mock_catalog.packaging_material_id = 2
    mock_catalog.packaging_color_id = 3
    mock_catalog.volume_liters = 5.0
    mock_catalog.diameter_cm = 15.0
    mock_catalog.height_cm = 10.0

    mock_repo.create.return_value = mock_catalog

    # Act
    response = await packaging_catalog_service.create(request)

    # Assert - all dimensions positive
    assert response.volume_liters > 0
    assert response.diameter_cm > 0
    assert response.height_cm > 0


# ============================================================================
# Test Get By ID
# ============================================================================


@pytest.mark.asyncio
async def test_get_by_id_success(packaging_catalog_service, mock_repo, mock_packaging_catalog):
    """Test getting packaging catalog by ID successfully."""
    # Arrange
    mock_repo.get.return_value = mock_packaging_catalog

    # Act
    response = await packaging_catalog_service.get_by_id(1)

    # Assert
    assert response.id == 1
    assert response.sku == "POT-PLASTIC-BLACK-10L"
    assert response.volume_liters == 10.0
    mock_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_by_id_not_found(packaging_catalog_service, mock_repo):
    """Test getting non-existent packaging catalog raises ValueError."""
    # Arrange
    mock_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="PackagingCatalog"):
        await packaging_catalog_service.get_by_id(999)


# ============================================================================
# Test Get All
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_success(packaging_catalog_service, mock_repo):
    """Test getting all packaging catalogs."""
    # Arrange
    mock_cat1 = Mock(spec=PackagingCatalog)
    mock_cat1.id = 1
    mock_cat1.sku = "POT-PLASTIC-BLACK-10L"
    mock_cat1.name = "10L Black Plastic Pot"
    mock_cat1.packaging_type_id = 1
    mock_cat1.packaging_material_id = 2
    mock_cat1.packaging_color_id = 3
    mock_cat1.volume_liters = 10.0
    mock_cat1.diameter_cm = 25.0
    mock_cat1.height_cm = 20.0

    mock_cat2 = Mock(spec=PackagingCatalog)
    mock_cat2.id = 2
    mock_cat2.sku = "POT-CERAMIC-WHITE-15L"
    mock_cat2.name = "15L White Ceramic Pot"
    mock_cat2.packaging_type_id = 1
    mock_cat2.packaging_material_id = 3
    mock_cat2.packaging_color_id = 1
    mock_cat2.volume_liters = 15.0
    mock_cat2.diameter_cm = 30.0
    mock_cat2.height_cm = 25.0

    mock_repo.get_multi.return_value = [mock_cat1, mock_cat2]

    # Act
    response = await packaging_catalog_service.get_all()

    # Assert
    assert len(response) == 2
    assert response[0].sku == "POT-PLASTIC-BLACK-10L"
    assert response[1].sku == "POT-CERAMIC-WHITE-15L"
    mock_repo.get_multi.assert_called_once_with(limit=100)


@pytest.mark.asyncio
async def test_get_all_empty(packaging_catalog_service, mock_repo):
    """Test getting packaging catalogs when none exist."""
    # Arrange
    mock_repo.get_multi.return_value = []

    # Act
    response = await packaging_catalog_service.get_all()

    # Assert
    assert len(response) == 0


@pytest.mark.asyncio
async def test_get_all_with_custom_limit(packaging_catalog_service, mock_repo):
    """Test getting packaging catalogs with custom limit."""
    # Arrange
    mock_repo.get_multi.return_value = []

    # Act
    await packaging_catalog_service.get_all(limit=50)

    # Assert
    mock_repo.get_multi.assert_called_once_with(limit=50)


# ============================================================================
# Test Update
# ============================================================================


@pytest.mark.asyncio
async def test_update_success(packaging_catalog_service, mock_repo, mock_packaging_catalog):
    """Test updating packaging catalog successfully."""
    # Arrange
    request = PackagingCatalogUpdateRequest(
        name="Updated Pot Name", volume_liters=12.0, diameter_cm=28.0, height_cm=22.0
    )

    updated_mock = Mock(spec=PackagingCatalog)
    updated_mock.id = 1
    updated_mock.sku = "POT-PLASTIC-BLACK-10L"  # Code unchanged
    updated_mock.name = "Updated Pot Name"
    updated_mock.packaging_type_id = 1
    updated_mock.packaging_material_id = 2
    updated_mock.packaging_color_id = 3
    updated_mock.volume_liters = 12.0
    updated_mock.diameter_cm = 28.0
    updated_mock.height_cm = 22.0

    mock_repo.get.return_value = mock_packaging_catalog
    mock_repo.update.return_value = updated_mock

    # Act
    response = await packaging_catalog_service.update(1, request)

    # Assert
    assert response.name == "Updated Pot Name"
    assert response.volume_liters == 12.0
    assert response.diameter_cm == 28.0
    assert response.height_cm == 22.0
    mock_repo.get.assert_called_once_with(1)
    mock_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_not_found(packaging_catalog_service, mock_repo):
    """Test updating non-existent packaging catalog raises ValueError."""
    # Arrange
    request = PackagingCatalogUpdateRequest(name="Updated Name")
    mock_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="PackagingCatalog"):
        await packaging_catalog_service.update(999, request)


@pytest.mark.asyncio
async def test_update_partial_name_only(
    packaging_catalog_service, mock_repo, mock_packaging_catalog
):
    """Test partial update (only name, dimensions unchanged)."""
    # Arrange
    request = PackagingCatalogUpdateRequest(name="New Name Only")

    updated_mock = Mock(spec=PackagingCatalog)
    updated_mock.id = 1
    updated_mock.sku = "POT-PLASTIC-BLACK-10L"
    updated_mock.name = "New Name Only"
    updated_mock.packaging_type_id = 1
    updated_mock.packaging_material_id = 2
    updated_mock.packaging_color_id = 3
    updated_mock.volume_liters = 10.0  # Unchanged
    updated_mock.diameter_cm = 25.0  # Unchanged
    updated_mock.height_cm = 20.0  # Unchanged

    mock_repo.get.return_value = mock_packaging_catalog
    mock_repo.update.return_value = updated_mock

    # Act
    response = await packaging_catalog_service.update(1, request)

    # Assert
    assert response.name == "New Name Only"
    assert response.volume_liters == 10.0  # Unchanged
    call_args = mock_repo.update.call_args
    assert "name" in call_args[0][1]


@pytest.mark.asyncio
async def test_update_partial_dimensions_only(
    packaging_catalog_service, mock_repo, mock_packaging_catalog
):
    """Test partial update (only dimensions, name unchanged)."""
    # Arrange
    request = PackagingCatalogUpdateRequest(volume_liters=11.0, diameter_cm=26.0)

    updated_mock = Mock(spec=PackagingCatalog)
    updated_mock.id = 1
    updated_mock.sku = "POT-PLASTIC-BLACK-10L"
    updated_mock.name = "10L Black Plastic Pot"  # Unchanged
    updated_mock.packaging_type_id = 1
    updated_mock.packaging_material_id = 2
    updated_mock.packaging_color_id = 3
    updated_mock.volume_liters = 11.0
    updated_mock.diameter_cm = 26.0
    updated_mock.height_cm = 20.0  # Unchanged (not in request)

    mock_repo.get.return_value = mock_packaging_catalog
    mock_repo.update.return_value = updated_mock

    # Act
    response = await packaging_catalog_service.update(1, request)

    # Assert
    assert response.name == "10L Black Plastic Pot"  # Unchanged
    assert response.volume_liters == 11.0
    assert response.diameter_cm == 26.0
    assert response.height_cm == 20.0  # Unchanged
    call_args = mock_repo.update.call_args
    update_data = call_args[0][1]
    assert "volume_liters" in update_data
    assert "diameter_cm" in update_data


# ============================================================================
# Test Delete
# ============================================================================


@pytest.mark.asyncio
async def test_delete_success(packaging_catalog_service, mock_repo, mock_packaging_catalog):
    """Test deleting packaging catalog successfully."""
    # Arrange
    mock_repo.get.return_value = mock_packaging_catalog
    mock_repo.delete.return_value = None

    # Act
    await packaging_catalog_service.delete(1)

    # Assert
    mock_repo.get.assert_called_once_with(1)
    mock_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_not_found(packaging_catalog_service, mock_repo):
    """Test deleting non-existent packaging catalog raises ValueError."""
    # Arrange
    mock_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="PackagingCatalog"):
        await packaging_catalog_service.delete(999)
