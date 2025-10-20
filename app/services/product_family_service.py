"""Product family business logic service (LEVEL 2 taxonomy)."""

from app.repositories.product_category_repository import ProductCategoryRepository
from app.repositories.product_family_repository import ProductFamilyRepository
from app.schemas.product_family_schema import (
    ProductFamilyCreateRequest,
    ProductFamilyResponse,
    ProductFamilyUpdateRequest,
)


class ProductFamilyService:
    """Business logic for product family operations (CRUD + category validation)."""

    def __init__(
        self, family_repo: ProductFamilyRepository, category_repo: ProductCategoryRepository
    ) -> None:
        self.family_repo = family_repo
        self.category_repo = category_repo

    async def create_family(self, request: ProductFamilyCreateRequest) -> ProductFamilyResponse:
        """Create product family with parent category validation."""
        # Validate category exists
        category = await self.category_repo.get(request.category_id)
        if not category:
            raise ValueError(f"ProductCategory {request.category_id} not found")

        family_data = request.model_dump()
        family_model = await self.family_repo.create(family_data)
        return ProductFamilyResponse.from_model(family_model)

    async def get_family_by_id(self, family_id: int) -> ProductFamilyResponse:
        """Get family by ID."""
        family_model = await self.family_repo.get(family_id)
        if not family_model:
            raise ValueError(f"ProductFamily {family_id} not found")
        return ProductFamilyResponse.from_model(family_model)

    async def get_families_by_category(self, category_id: int) -> list[ProductFamilyResponse]:
        """Get all families for a specific category."""
        families = await self.family_repo.get_multi(category_id=category_id)
        return [ProductFamilyResponse.from_model(f) for f in families]

    async def get_all_families(self) -> list[ProductFamilyResponse]:
        """Get all families."""
        families = await self.family_repo.get_multi(limit=200)
        return [ProductFamilyResponse.from_model(f) for f in families]

    async def update_family(
        self, family_id: int, request: ProductFamilyUpdateRequest
    ) -> ProductFamilyResponse:
        """Update family fields."""
        family_model = await self.family_repo.get(family_id)
        if not family_model:
            raise ValueError(f"ProductFamily {family_id} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.family_repo.update(family_id, update_data)
        return ProductFamilyResponse.from_model(updated_model)

    async def delete_family(self, family_id: int) -> None:
        """Delete family."""
        family_model = await self.family_repo.get(family_id)
        if not family_model:
            raise ValueError(f"ProductFamily {family_id} not found")
        await self.family_repo.delete(family_id)
