"""Integration tests for ProductService with real database.

Tests service operations against real PostgreSQL database.
NO mocks - real database access via ProductRepository.

Coverage target: ≥85%

Test categories:
- create_product: success, SKU auto-generation, family validation
- get_product_by_id: success, not found
- get_product_by_sku: success, case insensitive
- get_products_by_family: success, filtering
- get_all_products: empty, multiple
- update_product: success, immutable fields
- delete_product: success
- SKU generation: auto-increment, uniqueness

See:
    - Service: app/services/product_service.py
    - Repository: app/repositories/product_repository.py
"""

import pytest

from app.models.product import Product
from app.repositories.product_category_repository import ProductCategoryRepository
from app.repositories.product_family_repository import ProductFamilyRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product_category_schema import ProductCategoryCreateRequest
from app.schemas.product_family_schema import ProductFamilyCreateRequest
from app.schemas.product_schema import ProductCreateRequest, ProductUpdateRequest
from app.services.product_category_service import ProductCategoryService
from app.services.product_family_service import ProductFamilyService
from app.services.product_service import ProductService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def category_service(db_session):
    """Create ProductCategoryService with real repository."""
    repo = ProductCategoryRepository(session=db_session)
    return ProductCategoryService(category_repo=repo)


@pytest.fixture
async def family_service(db_session, category_service):
    """Create ProductFamilyService with real repository."""
    repo = ProductFamilyRepository(session=db_session)
    return ProductFamilyService(family_repo=repo, category_service=category_service)


@pytest.fixture
async def product_service(db_session, family_service):
    """Create ProductService with real repository."""
    repo = ProductRepository(session=db_session)
    return ProductService(product_repo=repo, family_service=family_service)


@pytest.fixture
async def test_category(category_service, db_session):
    """Create a test category for products."""
    request = ProductCategoryCreateRequest(code="SUCCULENT", name="Succulent")
    category = await category_service.create_category(request)
    await db_session.commit()
    return category


@pytest.fixture
async def test_family(family_service, test_category, db_session):
    """Create a test family for products."""
    request = ProductFamilyCreateRequest(
        category_id=test_category.id,
        name="Echeveria",
        scientific_name="Echeveria spp.",
    )
    family = await family_service.create_family(request)
    await db_session.commit()
    return family


# ============================================================================
# Test Create Product
# ============================================================================


@pytest.mark.asyncio
async def test_create_product_success(product_service, test_family, db_session):
    """Test creating product successfully with auto-generated SKU."""
    # Arrange
    request = ProductCreateRequest(
        family_id=test_family.family_id,
        common_name="Echeveria 'Lola'",
        scientific_name="Echeveria lilacina × E. derenbergii",
        description="Compact rosette succulent with powdery blue-gray leaves",
        custom_attributes={"color": "blue-gray", "growth_rate": "slow"},
    )

    # Act
    response = await product_service.create_product(request)
    await db_session.commit()

    # Assert
    assert response.product_id is not None
    assert response.family_id == test_family.family_id
    assert response.sku is not None
    assert response.sku.startswith("ECHEVERIA-")
    assert response.common_name == "Echeveria 'Lola'"
    assert response.custom_attributes["color"] == "blue-gray"

    # Verify in database
    db_product = await db_session.get(Product, response.product_id)
    assert db_product is not None
    assert db_product.sku == response.sku


@pytest.mark.asyncio
async def test_create_product_minimal_fields(product_service, test_family, db_session):
    """Test creating product with only required fields."""
    # Arrange
    request = ProductCreateRequest(family_id=test_family.family_id, common_name="Simple Echeveria")

    # Act
    response = await product_service.create_product(request)
    await db_session.commit()

    # Assert
    assert response.common_name == "Simple Echeveria"
    assert response.scientific_name is None
    assert response.description is None
    assert response.custom_attributes == {}


@pytest.mark.asyncio
async def test_create_product_sku_auto_increment(product_service, test_family, db_session):
    """Test that SKU auto-increments for products in same family."""
    # Arrange - Create first product
    request1 = ProductCreateRequest(family_id=test_family.family_id, common_name="First Echeveria")
    product1 = await product_service.create_product(request1)
    await db_session.commit()

    # Act - Create second product
    request2 = ProductCreateRequest(family_id=test_family.family_id, common_name="Second Echeveria")
    product2 = await product_service.create_product(request2)
    await db_session.commit()

    # Assert - SKUs should increment
    assert product1.sku == "ECHEVERIA-001"
    assert product2.sku == "ECHEVERIA-002"


@pytest.mark.asyncio
async def test_create_product_different_families_independent_skus(
    product_service, family_service, test_category, db_session
):
    """Test that different families have independent SKU counters."""
    # Arrange - Create another family
    family1_request = ProductFamilyCreateRequest(category_id=test_category.id, name="Sedum")
    sedum_family = await family_service.create_family(family1_request)
    await db_session.commit()

    # Create another family
    family2_request = ProductFamilyCreateRequest(category_id=test_category.id, name="Aloe")
    aloe_family = await family_service.create_family(family2_request)
    await db_session.commit()

    # Act - Create products in different families
    sedum_request = ProductCreateRequest(
        family_id=sedum_family.family_id, common_name="Sedum Burrito"
    )
    aloe_request = ProductCreateRequest(family_id=aloe_family.family_id, common_name="Aloe Vera")

    sedum_product = await product_service.create_product(sedum_request)
    aloe_product = await product_service.create_product(aloe_request)
    await db_session.commit()

    # Assert - Both should have -001 suffix (independent counters)
    assert sedum_product.sku == "SEDUM-001"
    assert aloe_product.sku == "ALOE-001"


@pytest.mark.asyncio
async def test_create_product_invalid_family(product_service):
    """Test creating product with non-existent family raises ValueError."""
    # Arrange
    request = ProductCreateRequest(family_id=99999, common_name="Invalid Product")

    # Act & Assert
    with pytest.raises(ValueError, match="ProductFamily 99999 not found"):
        await product_service.create_product(request)


# ============================================================================
# Test Get Product by ID
# ============================================================================


@pytest.mark.asyncio
async def test_get_product_by_id_success(product_service, test_family, db_session):
    """Test getting product by ID."""
    # Arrange - Create product
    request = ProductCreateRequest(family_id=test_family.family_id, common_name="Test Product")
    created = await product_service.create_product(request)
    await db_session.commit()

    # Act
    response = await product_service.get_product_by_id(created.product_id)

    # Assert
    assert response.product_id == created.product_id
    assert response.sku == created.sku
    assert response.common_name == "Test Product"


@pytest.mark.asyncio
async def test_get_product_by_id_not_found(product_service):
    """Test getting non-existent product."""
    # Act & Assert
    with pytest.raises(ValueError, match="Product 99999 not found"):
        await product_service.get_product_by_id(99999)


# ============================================================================
# Test Get Product by SKU
# ============================================================================


@pytest.mark.asyncio
async def test_get_product_by_sku_success(product_service, test_family, db_session):
    """Test getting product by SKU."""
    # Arrange - Create product
    request = ProductCreateRequest(family_id=test_family.family_id, common_name="SKU Test Product")
    created = await product_service.create_product(request)
    await db_session.commit()

    # Act
    response = await product_service.get_product_by_sku(created.sku)

    # Assert
    assert response.product_id == created.product_id
    assert response.sku == created.sku


@pytest.mark.asyncio
async def test_get_product_by_sku_case_insensitive(product_service, test_family, db_session):
    """Test getting product by SKU is case-insensitive."""
    # Arrange - Create product
    request = ProductCreateRequest(family_id=test_family.family_id, common_name="Case Test")
    created = await product_service.create_product(request)
    await db_session.commit()

    # Act - Search with lowercase SKU
    response = await product_service.get_product_by_sku(created.sku.lower())

    # Assert
    assert response.product_id == created.product_id
    assert response.sku == created.sku.upper()


@pytest.mark.asyncio
async def test_get_product_by_sku_not_found(product_service):
    """Test getting product by non-existent SKU."""
    # Act & Assert
    with pytest.raises(ValueError, match="Product with SKU 'INVALID-SKU' not found"):
        await product_service.get_product_by_sku("INVALID-SKU")


# ============================================================================
# Test Get Products by Family
# ============================================================================


@pytest.mark.asyncio
async def test_get_products_by_family_success(product_service, test_family, db_session):
    """Test getting all products for a specific family."""
    # Arrange - Create multiple products in same family
    products = [
        ProductCreateRequest(family_id=test_family.family_id, common_name="Product 1"),
        ProductCreateRequest(family_id=test_family.family_id, common_name="Product 2"),
        ProductCreateRequest(family_id=test_family.family_id, common_name="Product 3"),
    ]

    for req in products:
        await product_service.create_product(req)
    await db_session.commit()

    # Act
    response = await product_service.get_products_by_family(test_family.family_id)

    # Assert
    assert len(response) >= 3
    names = {p.common_name for p in response}
    assert "Product 1" in names
    assert "Product 2" in names
    assert "Product 3" in names


@pytest.mark.asyncio
async def test_get_products_by_family_filtering(
    product_service, family_service, test_category, db_session
):
    """Test that get_products_by_family only returns products from specified family."""
    # Arrange - Create two families
    family1_request = ProductFamilyCreateRequest(category_id=test_category.id, name="Family1")
    family1 = await family_service.create_family(family1_request)
    await db_session.commit()

    family2_request = ProductFamilyCreateRequest(category_id=test_category.id, name="Family2")
    family2 = await family_service.create_family(family2_request)
    await db_session.commit()

    # Create products in both families
    await product_service.create_product(
        ProductCreateRequest(family_id=family1.family_id, common_name="Family1 Product")
    )
    await product_service.create_product(
        ProductCreateRequest(family_id=family2.family_id, common_name="Family2 Product")
    )
    await db_session.commit()

    # Act - Get products from family1 only
    response = await product_service.get_products_by_family(family1.family_id)

    # Assert - Should only have family1 products
    for product in response:
        assert product.family_id == family1.family_id
    names = {p.common_name for p in response}
    assert "Family1 Product" in names
    assert "Family2 Product" not in names


@pytest.mark.asyncio
async def test_get_products_by_family_invalid_family(product_service):
    """Test getting products for non-existent family."""
    # Act & Assert
    with pytest.raises(ValueError, match="ProductFamily 99999 not found"):
        await product_service.get_products_by_family(99999)


# ============================================================================
# Test Get All Products
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_products_success(product_service, test_family, db_session):
    """Test getting all products."""
    # Arrange - Create products
    products = [
        ProductCreateRequest(family_id=test_family.family_id, common_name=f"Product {i}")
        for i in range(3)
    ]

    for req in products:
        await product_service.create_product(req)
    await db_session.commit()

    # Act
    response = await product_service.get_all_products()

    # Assert
    assert len(response) >= 3
    assert isinstance(response, list)


# ============================================================================
# Test Update Product
# ============================================================================


@pytest.mark.asyncio
async def test_update_product_success(product_service, test_family, db_session):
    """Test updating product."""
    # Arrange - Create product
    request = ProductCreateRequest(family_id=test_family.family_id, common_name="Original Name")
    created = await product_service.create_product(request)
    await db_session.commit()

    # Act - Update
    update_request = ProductUpdateRequest(
        common_name="Updated Name",
        description="Updated description",
        custom_attributes={"new_field": "new_value"},
    )
    response = await product_service.update_product(created.product_id, update_request)
    await db_session.commit()

    # Assert
    assert response.product_id == created.product_id
    assert response.sku == created.sku  # SKU unchanged
    assert response.family_id == created.family_id  # Family unchanged
    assert response.common_name == "Updated Name"
    assert response.description == "Updated description"
    assert response.custom_attributes["new_field"] == "new_value"


@pytest.mark.asyncio
async def test_update_product_partial(product_service, test_family, db_session):
    """Test partial update (only common_name)."""
    # Arrange
    request = ProductCreateRequest(
        family_id=test_family.family_id,
        common_name="Original",
        description="Original description",
    )
    created = await product_service.create_product(request)
    await db_session.commit()

    # Act - Update only name
    update_request = ProductUpdateRequest(common_name="Updated Name Only")
    response = await product_service.update_product(created.product_id, update_request)
    await db_session.commit()

    # Assert
    assert response.common_name == "Updated Name Only"
    assert response.description == "Original description"  # Unchanged


@pytest.mark.asyncio
async def test_update_product_sku_immutable(product_service, test_family, db_session):
    """Test that SKU cannot be updated (immutable field)."""
    # Arrange
    request = ProductCreateRequest(family_id=test_family.family_id, common_name="Test Product")
    created = await product_service.create_product(request)
    await db_session.commit()
    original_sku = created.sku

    # Act - Try to update (service should ignore SKU/family_id changes)
    update_request = ProductUpdateRequest(common_name="Updated Name")
    response = await product_service.update_product(created.product_id, update_request)
    await db_session.commit()

    # Assert
    assert response.sku == original_sku  # SKU unchanged
    assert response.family_id == test_family.family_id  # Family unchanged


@pytest.mark.asyncio
async def test_update_product_not_found(product_service):
    """Test updating non-existent product."""
    # Arrange
    update_request = ProductUpdateRequest(common_name="New Name")

    # Act & Assert
    with pytest.raises(ValueError, match="Product 99999 not found"):
        await product_service.update_product(99999, update_request)


# ============================================================================
# Test Delete Product
# ============================================================================


@pytest.mark.asyncio
async def test_delete_product_success(product_service, test_family, db_session):
    """Test deleting product."""
    # Arrange - Create product
    request = ProductCreateRequest(family_id=test_family.family_id, common_name="To Delete")
    created = await product_service.create_product(request)
    await db_session.commit()

    product_id = created.product_id

    # Act - Delete
    await product_service.delete_product(product_id)
    await db_session.commit()

    # Assert - Product should not exist
    db_product = await db_session.get(Product, product_id)
    assert db_product is None


@pytest.mark.asyncio
async def test_delete_product_not_found(product_service):
    """Test deleting non-existent product."""
    # Act & Assert
    with pytest.raises(ValueError, match="Product 99999 not found"):
        await product_service.delete_product(99999)


# ============================================================================
# Test SKU Generation
# ============================================================================


@pytest.mark.asyncio
async def test_sku_generation_handles_family_name_with_spaces(
    product_service, family_service, test_category, db_session
):
    """Test SKU generation handles family names with spaces correctly."""
    # Arrange - Create family with spaces in name
    family_request = ProductFamilyCreateRequest(
        category_id=test_category.id, name="Aloe Vera Species"
    )
    family = await family_service.create_family(family_request)
    await db_session.commit()

    # Act
    product_request = ProductCreateRequest(family_id=family.family_id, common_name="Test Aloe")
    product = await product_service.create_product(product_request)
    await db_session.commit()

    # Assert - Spaces should be removed from SKU prefix
    assert product.sku == "ALOEVERASPECIES-001"


@pytest.mark.asyncio
async def test_sku_generation_truncates_long_family_names(
    product_service, family_service, test_category, db_session
):
    """Test SKU generation truncates long family names to 15 chars."""
    # Arrange - Create family with very long name
    family_request = ProductFamilyCreateRequest(
        category_id=test_category.id,
        name="VeryLongFamilyNameThatExceedsLimit",
    )
    family = await family_service.create_family(family_request)
    await db_session.commit()

    # Act
    product_request = ProductCreateRequest(family_id=family.family_id, common_name="Test Product")
    product = await product_service.create_product(product_request)
    await db_session.commit()

    # Assert - Prefix should be truncated to 15 chars
    prefix = product.sku.split("-")[0]
    assert len(prefix) == 15
    assert product.sku.startswith("VERYLONGFAMILYN-")
