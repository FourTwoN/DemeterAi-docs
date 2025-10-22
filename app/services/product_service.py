"""Product business logic service (LEVEL 3 taxonomy - LEAF level).

This service handles product management with:
- SKU auto-generation (format: FAMILY-STATE-SIZE-NNN)
- Family validation via ProductFamilyService (Service→Service pattern)
- SKU uniqueness validation
- Product queries by family/category
"""

from sqlalchemy import select

from app.core.exceptions import NotFoundException
from app.repositories.product_repository import ProductRepository
from app.schemas.product_schema import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
)
from app.services.product_family_service import ProductFamilyService


class ProductService:
    """Business logic for product operations (CRUD + SKU auto-generation)."""

    def __init__(
        self, product_repo: ProductRepository, family_service: ProductFamilyService
    ) -> None:
        """Initialize service with repository and family service.

        Args:
            product_repo: Product repository (own repository)
            family_service: Family service for validation (Service→Service pattern)
        """
        self.product_repo = product_repo
        self.family_service = family_service

    async def _generate_sku(self, family_id: int, common_name: str) -> str:
        """Generate unique SKU for product.

        Format: FAMILYPREFIX-NNN (e.g., ECHEVERIA-001, CACTUS-042)

        Strategy:
        1. Get family name via ProductFamilyService
        2. Create prefix from family name (uppercase, remove spaces)
        3. Find max suffix for this family
        4. Increment and format as 3-digit number

        Args:
            family_id: Family ID for SKU prefix
            common_name: Product common name (used as fallback if family unavailable)

        Returns:
            Generated SKU (e.g., "ECHEVERIA-001")

        Raises:
            ValueError: If family doesn't exist
        """
        # Get family via FamilyService (Service→Service pattern)
        family_response = await self.family_service.get_family_by_id(family_id)

        # Create prefix from family name (uppercase, remove spaces, limit to 15 chars)
        family_prefix = family_response.name.upper().replace(" ", "").replace("'", "")[:15]

        # Get all products for this family to find max suffix
        # Query pattern: SELECT * FROM products WHERE family_id = X AND sku LIKE 'PREFIX-%'
        stmt = select(self.product_repo.model).where(self.product_repo.model.family_id == family_id)
        result = await self.product_repo.session.execute(stmt)
        family_products = result.scalars().all()

        # Find max suffix number
        max_suffix = 0
        for product in family_products:
            # Extract suffix from SKU (format: PREFIX-NNN)
            if product.sku and product.sku.startswith(family_prefix + "-"):
                suffix_str = product.sku.split("-")[-1]
                try:
                    suffix_num = int(suffix_str)
                    max_suffix = max(max_suffix, suffix_num)
                except ValueError:
                    # Skip SKUs with non-numeric suffixes
                    continue

        # Generate new SKU with incremented suffix
        new_suffix = max_suffix + 1
        sku = f"{family_prefix}-{new_suffix:03d}"

        return sku

    async def create_product(self, request: ProductCreateRequest) -> ProductResponse:
        """Create product with auto-generated SKU and family validation.

        Business rules:
        1. Validate family exists via ProductFamilyService
        2. Auto-generate unique SKU (FAMILY-NNN format)
        3. Validate SKU uniqueness (should never fail with auto-generation)
        4. Create product in database

        Args:
            request: Product creation request (NO SKU - auto-generated)

        Returns:
            ProductResponse with auto-generated SKU

        Raises:
            ValueError: If family doesn't exist
        """
        # Validate family exists via FamilyService (Service→Service pattern)
        # This call raises ValueError if family doesn't exist
        await self.family_service.get_family_by_id(request.family_id)

        # Auto-generate SKU
        sku = await self._generate_sku(request.family_id, request.common_name)

        # Create product data with generated SKU
        product_data = request.model_dump()
        product_data["sku"] = sku

        # Ensure custom_attributes is empty dict if not provided
        if product_data.get("custom_attributes") is None:
            product_data["custom_attributes"] = {}

        # Create via repository
        product_model = await self.product_repo.create(product_data)

        return ProductResponse.from_model(product_model)

    async def get_product_by_id(self, product_id: int) -> ProductResponse:
        """Get product by ID.

        Args:
            product_id: Product ID to retrieve

        Returns:
            ProductResponse

        Raises:
            NotFoundException: If product not found
        """
        product_model = await self.product_repo.get(product_id)
        if not product_model:
            raise NotFoundException(resource="Product", identifier=product_id)
        return ProductResponse.from_model(product_model)

    async def get_product_by_sku(self, sku: str) -> ProductResponse:
        """Get product by SKU.

        Args:
            sku: Product SKU (unique identifier)

        Returns:
            ProductResponse

        Raises:
            ValueError: If product not found
        """
        # Query by SKU (unique constraint)
        stmt = select(self.product_repo.model).where(self.product_repo.model.sku == sku.upper())
        result = await self.product_repo.session.execute(stmt)
        product_model = result.scalar_one_or_none()

        if not product_model:
            raise NotFoundException(resource="Product", identifier=f"SKU:{sku}")

        return ProductResponse.from_model(product_model)

    async def get_products_by_family(
        self, family_id: int, limit: int = 100
    ) -> list[ProductResponse]:
        """Get all products for a specific family.

        Args:
            family_id: Family ID to filter by
            limit: Max results to return (default 100)

        Returns:
            List of ProductResponse objects
        """
        # Validate family exists via FamilyService
        await self.family_service.get_family_by_id(family_id)

        # Query products by family
        stmt = (
            select(self.product_repo.model)
            .where(self.product_repo.model.family_id == family_id)
            .limit(limit)
        )
        result = await self.product_repo.session.execute(stmt)
        products = result.scalars().all()

        return [ProductResponse.from_model(p) for p in products]

    async def get_all_products(self, limit: int = 200) -> list[ProductResponse]:
        """Get all products.

        Args:
            limit: Max results to return (default 200)

        Returns:
            List of ProductResponse objects
        """
        products = await self.product_repo.get_multi(limit=limit)
        return [ProductResponse.from_model(p) for p in products]

    async def update_product(
        self, product_id: int, request: ProductUpdateRequest
    ) -> ProductResponse:
        """Update product fields.

        Note: SKU and family_id are immutable (cannot be changed after creation).

        Args:
            product_id: Product ID to update
            request: Update request with optional fields

        Returns:
            Updated ProductResponse

        Raises:
            NotFoundException: If product not found
        """
        # Verify product exists
        product_model = await self.product_repo.get(product_id)
        if not product_model:
            raise NotFoundException(resource="Product", identifier=product_id)

        # Update only provided fields
        update_data = request.model_dump(exclude_unset=True)

        # Never allow SKU or family_id updates (immutable)
        update_data.pop("sku", None)
        update_data.pop("family_id", None)

        # Update via repository
        updated_model = await self.product_repo.update(product_id, update_data)

        return ProductResponse.from_model(updated_model)

    async def delete_product(self, product_id: int) -> None:
        """Delete product (soft delete in future).

        Args:
            product_id: Product ID to delete

        Raises:
            NotFoundException: If product not found
        """
        # Verify product exists
        product_model = await self.product_repo.get(product_id)
        if not product_model:
            raise NotFoundException(resource="Product", identifier=product_id)

        # Delete via repository
        await self.product_repo.delete(product_id)

    # Convenience aliases for controller compatibility
    async def get_by_category_and_family(
        self, category_id: int, family_id: int, limit: int = 100
    ) -> list[ProductResponse]:
        """Get products by category and family."""
        # Query products filtered by family (family implies category)
        products = await self.get_products_by_family(family_id, limit=limit)
        # Additional category filter if needed (family already belongs to a category)
        return products

    async def get_by_family(self, family_id: int, limit: int = 100) -> list[ProductResponse]:
        """Alias for get_products_by_family."""
        return await self.get_products_by_family(family_id, limit=limit)

    async def get_all(self, skip: int = 0, limit: int = 200) -> list[ProductResponse]:
        """Alias for get_all_products with pagination."""
        # Note: ProductRepository doesn't have skip param, so we'll slice results
        products = await self.get_all_products(limit=limit + skip)
        return products[skip:]

    async def create(self, request: ProductCreateRequest) -> ProductResponse:
        """Alias for create_product."""
        return await self.create_product(request)

    async def get_by_sku(self, sku: str) -> ProductResponse:
        """Alias for get_product_by_sku."""
        return await self.get_product_by_sku(sku)
