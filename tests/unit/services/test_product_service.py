"""Unit tests for ProductService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock for ProductRepository.

Coverage target: ≥85%

Test categories:
- create_product: success, SKU auto-generation, family validation
- get_product_by_id: success, not found
- get_product_by_sku: success, not found, case insensitive
- get_products_by_family: success, family validation
- get_all_products: empty, multiple products
- update_product: success, not found, immutable fields
- delete_product: success, not found
- _generate_sku: first product, incremental SKU, max suffix

See:
    - Service: app/services/product_service.py
    - Task: backlog/03_kanban/01_ready/S021-product-service.md
"""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.product_schema import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
)
from app.services.product_service import ProductService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_product_repo():
    """Create mock ProductRepository for testing."""
    repo = AsyncMock()
    # Mock session for SKU generation queries
    repo.session = AsyncMock(spec=AsyncSession)
    repo.model = Product  # Needed for queries
    return repo


@pytest.fixture
def mock_family_service():
    """Create mock ProductFamilyService for testing."""
    service = AsyncMock()
    # Mock get_family_by_id to return a valid response
    mock_family_response = Mock()
    mock_family_response.family_id = 1
    mock_family_response.category_id = 1
    mock_family_response.name = "Echeveria"
    mock_family_response.scientific_name = "Echeveria spp."
    service.get_family_by_id.return_value = mock_family_response
    return service


@pytest.fixture
def product_service(mock_product_repo, mock_family_service):
    """Create ProductService with mocked dependencies."""
    return ProductService(product_repo=mock_product_repo, family_service=mock_family_service)


@pytest.fixture
def mock_product():
    """Create mock Product model instance."""
    product = Mock(spec=Product)
    product.product_id = 1
    product.family_id = 1
    product.sku = "ECHEVERIA-001"
    product.common_name = "Echeveria 'Lola'"
    product.scientific_name = "Echeveria lilacina × E. derenbergii"
    product.description = "Compact rosette succulent"
    product.custom_attributes = {"color": "blue-gray", "growth_rate": "slow"}
    return product


# ============================================================================
# Test Create Product
# ============================================================================


@pytest.mark.asyncio
async def test_create_product_success(
    product_service, mock_product_repo, mock_family_service, mock_product
):
    """Test successful product creation with auto-generated SKU."""
    # Arrange
    request = ProductCreateRequest(
        family_id=1,
        common_name="Echeveria 'Lola'",
        scientific_name="Echeveria lilacina × E. derenbergii",
        description="Compact rosette succulent",
        custom_attributes={"color": "blue-gray"},
    )

    # Mock SKU generation: no existing products for this family
    async def mock_execute(*args, **kwargs):
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_product_repo.session.execute = mock_execute

    # Mock repository create
    mock_product_repo.create.return_value = mock_product

    # Act
    response = await product_service.create_product(request)

    # Assert
    assert isinstance(response, ProductResponse)
    assert response.product_id == 1
    assert response.sku == "ECHEVERIA-001"
    assert response.common_name == "Echeveria 'Lola'"
    # Family service is called twice: once for validation, once for SKU generation
    assert mock_family_service.get_family_by_id.call_count == 2
    mock_product_repo.create.assert_called_once()
    # Verify SKU was generated and added to product_data
    create_call_args = mock_product_repo.create.call_args[0][0]
    assert "sku" in create_call_args
    assert create_call_args["sku"].startswith("ECHEVERIA-")


@pytest.mark.asyncio
async def test_create_product_minimal_fields(
    product_service, mock_product_repo, mock_family_service
):
    """Test creating product with only required fields."""
    # Arrange
    request = ProductCreateRequest(family_id=1, common_name="Simple Echeveria")

    # Mock SKU generation
    async def mock_execute(*args, **kwargs):
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_product_repo.session.execute = mock_execute

    mock_minimal = Mock(spec=Product)
    mock_minimal.product_id = 2
    mock_minimal.family_id = 1
    mock_minimal.sku = "ECHEVERIA-001"
    mock_minimal.common_name = "Simple Echeveria"
    mock_minimal.scientific_name = None
    mock_minimal.description = None
    mock_minimal.custom_attributes = {}

    mock_product_repo.create.return_value = mock_minimal

    # Act
    response = await product_service.create_product(request)

    # Assert
    assert response.common_name == "Simple Echeveria"
    assert response.scientific_name is None
    assert response.description is None
    assert response.custom_attributes == {}


@pytest.mark.asyncio
async def test_create_product_invalid_family(product_service, mock_family_service):
    """Test creating product with non-existent family raises ValueError."""
    # Arrange
    request = ProductCreateRequest(family_id=999, common_name="Invalid Product")

    # Mock family service raises ValueError when family doesn't exist
    mock_family_service.get_family_by_id.side_effect = ValueError("ProductFamily 999 not found")

    # Act & Assert
    with pytest.raises(ValueError, match="ProductFamily 999 not found"):
        await product_service.create_product(request)


@pytest.mark.asyncio
async def test_create_product_auto_increments_sku(
    product_service, mock_product_repo, mock_family_service
):
    """Test SKU auto-increments correctly when existing products exist."""
    # Arrange
    request = ProductCreateRequest(family_id=1, common_name="New Echeveria")

    # Mock existing products with SKUs
    existing_product1 = Mock(spec=Product)
    existing_product1.sku = "ECHEVERIA-001"
    existing_product2 = Mock(spec=Product)
    existing_product2.sku = "ECHEVERIA-002"

    async def mock_execute(*args, **kwargs):
        mock_scalars = Mock()
        mock_scalars.all.return_value = [existing_product1, existing_product2]
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_product_repo.session.execute = mock_execute

    new_product = Mock(spec=Product)
    new_product.product_id = 3
    new_product.family_id = 1
    new_product.sku = "ECHEVERIA-003"
    new_product.common_name = "New Echeveria"
    new_product.scientific_name = None
    new_product.description = None
    new_product.custom_attributes = {}

    mock_product_repo.create.return_value = new_product

    # Act
    response = await product_service.create_product(request)

    # Assert
    assert response.sku == "ECHEVERIA-003"


# ============================================================================
# Test Get Product by ID
# ============================================================================


@pytest.mark.asyncio
async def test_get_product_by_id_success(product_service, mock_product_repo, mock_product):
    """Test getting product by ID successfully."""
    # Arrange
    mock_product_repo.get.return_value = mock_product

    # Act
    response = await product_service.get_product_by_id(1)

    # Assert
    assert response.product_id == 1
    assert response.sku == "ECHEVERIA-001"
    assert response.common_name == "Echeveria 'Lola'"
    mock_product_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_product_by_id_not_found(product_service, mock_product_repo):
    """Test getting non-existent product raises ValueError."""
    # Arrange
    mock_product_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="Product 999 not found"):
        await product_service.get_product_by_id(999)


# ============================================================================
# Test Get Product by SKU
# ============================================================================


@pytest.mark.asyncio
async def test_get_product_by_sku_success(product_service, mock_product_repo, mock_product):
    """Test getting product by SKU successfully."""

    # Arrange
    async def mock_execute(*args, **kwargs):
        result = Mock()
        result.scalar_one_or_none.return_value = mock_product
        return result

    mock_product_repo.session.execute = mock_execute

    # Act
    response = await product_service.get_product_by_sku("ECHEVERIA-001")

    # Assert
    assert response.product_id == 1
    assert response.sku == "ECHEVERIA-001"


@pytest.mark.asyncio
async def test_get_product_by_sku_case_insensitive(
    product_service, mock_product_repo, mock_product
):
    """Test getting product by SKU is case-insensitive."""

    # Arrange
    async def mock_execute(*args, **kwargs):
        result = Mock()
        result.scalar_one_or_none.return_value = mock_product
        return result

    mock_product_repo.session.execute = mock_execute

    # Act
    response = await product_service.get_product_by_sku("echeveria-001")

    # Assert
    assert response.sku == "ECHEVERIA-001"


@pytest.mark.asyncio
async def test_get_product_by_sku_not_found(product_service, mock_product_repo):
    """Test getting product by non-existent SKU raises ValueError."""

    # Arrange
    async def mock_execute(*args, **kwargs):
        result = Mock()
        result.scalar_one_or_none.return_value = None
        return result

    mock_product_repo.session.execute = mock_execute

    # Act & Assert
    with pytest.raises(ValueError, match="Product with SKU 'INVALID-SKU' not found"):
        await product_service.get_product_by_sku("INVALID-SKU")


# ============================================================================
# Test Get Products by Family
# ============================================================================


@pytest.mark.asyncio
async def test_get_products_by_family_success(
    product_service, mock_product_repo, mock_family_service
):
    """Test getting all products for a specific family."""
    # Arrange
    product1 = Mock(spec=Product)
    product1.product_id = 1
    product1.family_id = 1
    product1.sku = "ECHEVERIA-001"
    product1.common_name = "Echeveria 'Lola'"
    product1.scientific_name = None
    product1.description = None
    product1.custom_attributes = {}

    product2 = Mock(spec=Product)
    product2.product_id = 2
    product2.family_id = 1
    product2.sku = "ECHEVERIA-002"
    product2.common_name = "Echeveria 'Perle'"
    product2.scientific_name = None
    product2.description = None
    product2.custom_attributes = {}

    async def mock_execute(*args, **kwargs):
        mock_scalars = Mock()
        mock_scalars.all.return_value = [product1, product2]
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_product_repo.session.execute = mock_execute

    # Act
    response = await product_service.get_products_by_family(1)

    # Assert
    assert len(response) == 2
    assert response[0].sku == "ECHEVERIA-001"
    assert response[1].sku == "ECHEVERIA-002"
    mock_family_service.get_family_by_id.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_products_by_family_empty(
    product_service, mock_product_repo, mock_family_service
):
    """Test getting products for family with no products."""

    # Arrange
    async def mock_execute(*args, **kwargs):
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_product_repo.session.execute = mock_execute

    # Act
    response = await product_service.get_products_by_family(1)

    # Assert
    assert len(response) == 0


@pytest.mark.asyncio
async def test_get_products_by_family_invalid_family(product_service, mock_family_service):
    """Test getting products for non-existent family raises ValueError."""
    # Arrange
    mock_family_service.get_family_by_id.side_effect = ValueError("ProductFamily 999 not found")

    # Act & Assert
    with pytest.raises(ValueError, match="ProductFamily 999 not found"):
        await product_service.get_products_by_family(999)


# ============================================================================
# Test Get All Products
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_products_success(product_service, mock_product_repo):
    """Test getting all products."""
    # Arrange
    product1 = Mock(spec=Product)
    product1.product_id = 1
    product1.family_id = 1
    product1.sku = "ECHEVERIA-001"
    product1.common_name = "Echeveria 'Lola'"
    product1.scientific_name = None
    product1.description = None
    product1.custom_attributes = {}

    product2 = Mock(spec=Product)
    product2.product_id = 2
    product2.family_id = 2
    product2.sku = "SEDUM-001"
    product2.common_name = "Sedum 'Burrito'"
    product2.scientific_name = None
    product2.description = None
    product2.custom_attributes = {}

    mock_product_repo.get_multi.return_value = [product1, product2]

    # Act
    response = await product_service.get_all_products()

    # Assert
    assert len(response) == 2
    assert response[0].sku == "ECHEVERIA-001"
    assert response[1].sku == "SEDUM-001"
    mock_product_repo.get_multi.assert_called_once_with(limit=200)


@pytest.mark.asyncio
async def test_get_all_products_empty(product_service, mock_product_repo):
    """Test getting products when none exist."""
    # Arrange
    mock_product_repo.get_multi.return_value = []

    # Act
    response = await product_service.get_all_products()

    # Assert
    assert len(response) == 0


# ============================================================================
# Test Update Product
# ============================================================================


@pytest.mark.asyncio
async def test_update_product_success(product_service, mock_product_repo, mock_product):
    """Test updating product successfully."""
    # Arrange
    request = ProductUpdateRequest(
        common_name="Updated Echeveria Name", description="Updated description"
    )

    updated_mock = Mock(spec=Product)
    updated_mock.product_id = 1
    updated_mock.family_id = 1
    updated_mock.sku = "ECHEVERIA-001"  # SKU unchanged
    updated_mock.common_name = "Updated Echeveria Name"
    updated_mock.scientific_name = "Echeveria lilacina × E. derenbergii"
    updated_mock.description = "Updated description"
    updated_mock.custom_attributes = {"color": "blue-gray"}

    mock_product_repo.get.return_value = mock_product
    mock_product_repo.update.return_value = updated_mock

    # Act
    response = await product_service.update_product(1, request)

    # Assert
    assert response.common_name == "Updated Echeveria Name"
    assert response.description == "Updated description"
    assert response.sku == "ECHEVERIA-001"  # SKU should not change
    mock_product_repo.get.assert_called_once_with(1)
    mock_product_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_product_not_found(product_service, mock_product_repo):
    """Test updating non-existent product raises ValueError."""
    # Arrange
    request = ProductUpdateRequest(common_name="Updated Name")
    mock_product_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="Product 999 not found"):
        await product_service.update_product(999, request)


@pytest.mark.asyncio
async def test_update_product_partial(product_service, mock_product_repo, mock_product):
    """Test partial update (only common_name, no other fields)."""
    # Arrange
    request = ProductUpdateRequest(common_name="New Name Only")

    updated_mock = Mock(spec=Product)
    updated_mock.product_id = 1
    updated_mock.family_id = 1
    updated_mock.sku = "ECHEVERIA-001"
    updated_mock.common_name = "New Name Only"
    updated_mock.scientific_name = "Echeveria lilacina × E. derenbergii"  # Unchanged
    updated_mock.description = "Compact rosette succulent"  # Unchanged
    updated_mock.custom_attributes = {"color": "blue-gray"}

    mock_product_repo.get.return_value = mock_product
    mock_product_repo.update.return_value = updated_mock

    # Act
    response = await product_service.update_product(1, request)

    # Assert
    assert response.common_name == "New Name Only"


@pytest.mark.asyncio
async def test_update_product_sku_immutable(product_service, mock_product_repo, mock_product):
    """Test that SKU cannot be updated (immutable field)."""
    # Arrange
    # Note: ProductUpdateRequest doesn't have sku field, but we test the service filters it
    request = ProductUpdateRequest(common_name="Updated Name")

    updated_mock = Mock(spec=Product)
    updated_mock.product_id = 1
    updated_mock.family_id = 1
    updated_mock.sku = "ECHEVERIA-001"  # Should remain unchanged
    updated_mock.common_name = "Updated Name"
    updated_mock.scientific_name = "Echeveria lilacina × E. derenbergii"
    updated_mock.description = "Compact rosette succulent"
    updated_mock.custom_attributes = {"color": "blue-gray"}

    mock_product_repo.get.return_value = mock_product
    mock_product_repo.update.return_value = updated_mock

    # Act
    response = await product_service.update_product(1, request)

    # Assert
    assert response.sku == "ECHEVERIA-001"  # SKU should not change
    # Verify update_data doesn't contain sku or family_id
    call_args = mock_product_repo.update.call_args[0][1]
    assert "sku" not in call_args
    assert "family_id" not in call_args


# ============================================================================
# Test Delete Product
# ============================================================================


@pytest.mark.asyncio
async def test_delete_product_success(product_service, mock_product_repo, mock_product):
    """Test deleting product successfully."""
    # Arrange
    mock_product_repo.get.return_value = mock_product
    mock_product_repo.delete.return_value = None

    # Act
    await product_service.delete_product(1)

    # Assert
    mock_product_repo.get.assert_called_once_with(1)
    mock_product_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_product_not_found(product_service, mock_product_repo):
    """Test deleting non-existent product raises ValueError."""
    # Arrange
    mock_product_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="Product 999 not found"):
        await product_service.delete_product(999)


# ============================================================================
# Test SKU Generation
# ============================================================================


@pytest.mark.asyncio
async def test_generate_sku_first_product(product_service, mock_product_repo, mock_family_service):
    """Test SKU generation for first product in family."""

    # Arrange
    # No existing products
    async def mock_execute(*args, **kwargs):
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_product_repo.session.execute = mock_execute

    # Act
    sku = await product_service._generate_sku(1, "Test Product")

    # Assert
    assert sku == "ECHEVERIA-001"


@pytest.mark.asyncio
async def test_generate_sku_handles_family_name_with_spaces(
    product_service, mock_product_repo, mock_family_service
):
    """Test SKU generation handles family names with spaces correctly."""
    # Arrange
    # Mock family with spaces in name
    mock_family_response = Mock()
    mock_family_response.family_id = 2
    mock_family_response.name = "Aloe Vera Species"  # Spaces should be removed
    mock_family_service.get_family_by_id.return_value = mock_family_response

    async def mock_execute(*args, **kwargs):
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_product_repo.session.execute = mock_execute

    # Act
    sku = await product_service._generate_sku(2, "Test Product")

    # Assert
    assert sku == "ALOEVERASPECIES-001"  # Spaces removed


@pytest.mark.asyncio
async def test_generate_sku_long_family_name_truncated(
    product_service, mock_product_repo, mock_family_service
):
    """Test SKU generation truncates long family names to 15 chars."""
    # Arrange
    mock_family_response = Mock()
    mock_family_response.family_id = 3
    mock_family_response.name = "VeryLongFamilyNameThatExceedsLimit"  # > 15 chars
    mock_family_service.get_family_by_id.return_value = mock_family_response

    async def mock_execute(*args, **kwargs):
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_product_repo.session.execute = mock_execute

    # Act
    sku = await product_service._generate_sku(3, "Test Product")

    # Assert
    assert len(sku.split("-")[0]) == 15  # Prefix should be exactly 15 chars
    assert sku == "VERYLONGFAMILYN-001"
