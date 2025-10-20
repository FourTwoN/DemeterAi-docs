"""Product category business logic service (ROOT taxonomy level)."""

from app.repositories.product_category_repository import ProductCategoryRepository
from app.schemas.product_category_schema import (
    ProductCategoryCreateRequest,
    ProductCategoryResponse,
    ProductCategoryUpdateRequest,
)


class ProductCategoryService:
    """Business logic for product category operations (CRUD + validation)."""

    def __init__(self, category_repo: ProductCategoryRepository) -> None:
        self.category_repo = category_repo

    async def create_category(
        self, request: ProductCategoryCreateRequest
    ) -> ProductCategoryResponse:
        """Create a new product category with code uniqueness validation."""
        category_data = request.model_dump()
        category_model = await self.category_repo.create(category_data)
        return ProductCategoryResponse.from_model(category_model)

    async def get_category_by_id(self, category_id: int) -> ProductCategoryResponse:
        """Get category by ID."""
        category_model = await self.category_repo.get(category_id)
        if not category_model:
            raise ValueError(f"ProductCategory {category_id} not found")
        return ProductCategoryResponse.from_model(category_model)

    async def get_all_categories(self, active_only: bool = True) -> list[ProductCategoryResponse]:
        """Get all categories (active_only filter for future soft delete support)."""
        # Note: active_only parameter reserved for future soft delete implementation
        categories = await self.category_repo.get_multi(limit=100)
        return [ProductCategoryResponse.from_model(c) for c in categories]

    async def update_category(
        self, category_id: int, request: ProductCategoryUpdateRequest
    ) -> ProductCategoryResponse:
        """Update category fields (code is immutable)."""
        category_model = await self.category_repo.get(category_id)
        if not category_model:
            raise ValueError(f"ProductCategory {category_id} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.category_repo.update(category_id, update_data)
        return ProductCategoryResponse.from_model(updated_model)

    async def delete_category(self, category_id: int) -> None:
        """Soft delete category (future implementation)."""
        # Note: This will be soft delete when we implement deleted_at column
        category_model = await self.category_repo.get(category_id)
        if not category_model:
            raise ValueError(f"ProductCategory {category_id} not found")
        await self.category_repo.delete(category_id)
