"""Product Management API Controllers.

This module provides HTTP endpoints for product operations:
- 3-level product taxonomy (Category → Family → Product)
- Product CRUD operations
- Auto-SKU generation
- Product size management

Architecture:
    Layer: Controller Layer (HTTP only)
    Dependencies: Service layer only (NO business logic here)
    Pattern: Thin controllers - delegate to services

Endpoints:
    GET /api/v1/products/categories - List categories (C014)
    POST /api/v1/products/categories - Create category (C015)
    GET /api/v1/products/families - List families (C016)
    POST /api/v1/products/families - Create family (C017)
    GET /api/v1/products - List products (C018)
    POST /api/v1/products - Create product with auto-SKU (C019)
    GET /api/v1/products/{sku} - Get product by SKU (C020)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.factories.service_factory import ServiceFactory
from app.schemas.product_category_schema import (
    ProductCategoryCreateRequest,
    ProductCategoryResponse,
)
from app.schemas.product_family_schema import (
    ProductFamilyCreateRequest,
    ProductFamilyResponse,
)
from app.schemas.product_schema import ProductCreateRequest, ProductResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/products", tags=["products"])


# =============================================================================
# Dependency Injection Helpers
# =============================================================================


def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
    """Dependency injection for ServiceFactory."""
    return ServiceFactory(session)


# =============================================================================
# API Endpoints - Product Categories
# =============================================================================


@router.get(
    "/categories",
    response_model=list[ProductCategoryResponse],
    summary="List product categories",
)
async def list_product_categories(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    factory: ServiceFactory = Depends(get_factory),
) -> list[ProductCategoryResponse]:
    """List all product categories with pagination (C014).

    Args:
        skip: Offset (default 0)
        limit: Max results (default 100, max 1000)

    Returns:
        List of ProductCategoryResponse

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/products/categories?skip=0&limit=50"
        ```
    """
    try:
        logger.info("Listing product categories", extra={"skip": skip, "limit": limit})

        service = factory.get_product_category_service()
        categories = await service.get_all(skip=skip, limit=limit)

        logger.info("Product categories retrieved", extra={"count": len(categories)})

        return categories

    except Exception as e:
        logger.error("Failed to list categories", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list product categories.",
        )


@router.post(
    "/categories",
    response_model=ProductCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product category",
)
async def create_product_category(
    request: ProductCategoryCreateRequest,
    factory: ServiceFactory = Depends(get_factory),
) -> ProductCategoryResponse:
    """Create a new product category (C015).

    Args:
        request: Product category creation data

    Returns:
        ProductCategoryResponse with created category

    Raises:
        HTTPException 400: Validation error (duplicate name, etc.)
        HTTPException 500: Database error

    Example:
        ```json
        {
          "name": "Vegetables",
          "description": "Fresh vegetables and greens"
        }
        ```
    """
    try:
        logger.info("Creating product category", extra={"name": request.name})

        service = factory.get_product_category_service()
        category = await service.create(request)

        logger.info(
            "Product category created",
            extra={"category_id": category.category_id, "name": category.name},
        )

        return category

    except ValidationException as e:
        logger.warning("Category validation failed", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        logger.error("Failed to create category", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product category.",
        )


# =============================================================================
# API Endpoints - Product Families
# =============================================================================


@router.get(
    "/families",
    response_model=list[ProductFamilyResponse],
    summary="List product families",
)
async def list_product_families(
    category_id: int | None = Query(None, description="Filter by category ID"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    factory: ServiceFactory = Depends(get_factory),
) -> list[ProductFamilyResponse]:
    """List product families with optional category filter (C016).

    Args:
        category_id: Optional category ID filter
        skip: Offset (default 0)
        limit: Max results (default 100, max 1000)

    Returns:
        List of ProductFamilyResponse

    Example:
        ```bash
        # All families
        curl "http://localhost:8000/api/v1/products/families?skip=0&limit=50"

        # Filter by category
        curl "http://localhost:8000/api/v1/products/families?category_id=1"
        ```
    """
    try:
        logger.info(
            "Listing product families",
            extra={"category_id": category_id, "skip": skip, "limit": limit},
        )

        service = factory.get_product_family_service()
        if category_id:
            families = await service.get_by_category(category_id)
        else:
            families = await service.get_all(skip=skip, limit=limit)

        logger.info("Product families retrieved", extra={"count": len(families)})

        return families

    except ResourceNotFoundException as e:
        logger.warning("Category not found", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.error("Failed to list families", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list product families.",
        )


@router.post(
    "/families",
    response_model=ProductFamilyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product family",
)
async def create_product_family(
    request: ProductFamilyCreateRequest,
    factory: ServiceFactory = Depends(get_factory),
) -> ProductFamilyResponse:
    """Create a new product family (C017).

    Args:
        request: Product family creation data

    Returns:
        ProductFamilyResponse with created family

    Raises:
        HTTPException 400: Validation error
        HTTPException 404: Category not found
        HTTPException 500: Database error

    Example:
        ```json
        {
          "category_id": 1,
          "name": "Tomatoes",
          "description": "All tomato varieties"
        }
        ```
    """
    try:
        logger.info(
            "Creating product family",
            extra={"name": request.name, "category_id": request.category_id},
        )

        service = factory.get_product_family_service()
        family = await service.create(request)

        logger.info(
            "Product family created",
            extra={"family_id": family.family_id, "name": family.name},
        )

        return family

    except ValidationException as e:
        logger.warning("Family validation failed", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning("Category not found", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.error("Failed to create family", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product family.",
        )


# =============================================================================
# API Endpoints - Products
# =============================================================================


@router.get(
    "/",
    response_model=list[ProductResponse],
    summary="List products",
)
async def list_products(
    category_id: int | None = Query(None, description="Filter by category ID"),
    family_id: int | None = Query(None, description="Filter by family ID"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    factory: ServiceFactory = Depends(get_factory),
) -> list[ProductResponse]:
    """List products with optional filters (C018).

    Args:
        category_id: Optional category ID filter
        family_id: Optional family ID filter
        skip: Offset (default 0)
        limit: Max results (default 100, max 1000)

    Returns:
        List of ProductResponse

    Example:
        ```bash
        # All products
        curl "http://localhost:8000/api/v1/products?skip=0&limit=50"

        # Filter by category
        curl "http://localhost:8000/api/v1/products?category_id=1"

        # Filter by family
        curl "http://localhost:8000/api/v1/products?family_id=5"
        ```
    """
    try:
        logger.info(
            "Listing products",
            extra={
                "category_id": category_id,
                "family_id": family_id,
                "skip": skip,
                "limit": limit,
            },
        )

        service = factory.get_product_service()
        if category_id and family_id:
            products = await service.get_by_category_and_family(category_id, family_id)
        elif family_id:
            products = await service.get_by_family(family_id)
        else:
            products = await service.get_all(skip=skip, limit=limit)

        logger.info("Products retrieved", extra={"count": len(products)})

        return products

    except ResourceNotFoundException as e:
        logger.warning("Resource not found", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.error("Failed to list products", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list products.",
        )


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product with auto-SKU",
)
async def create_product(
    request: ProductCreateRequest,
    factory: ServiceFactory = Depends(get_factory),
) -> ProductResponse:
    """Create a new product with automatic SKU generation (C019).

    SKU Format: {CATEGORY_CODE}-{FAMILY_CODE}-{PRODUCT_ID}
    Example: VEG-TOM-001

    Args:
        request: Product creation data

    Returns:
        ProductResponse with created product and auto-generated SKU

    Raises:
        HTTPException 400: Validation error
        HTTPException 404: Category or family not found
        HTTPException 500: Database error

    Example:
        ```json
        {
          "category_id": 1,
          "family_id": 5,
          "name": "Cherry Tomato",
          "description": "Sweet cherry tomatoes",
          "scientific_name": "Solanum lycopersicum var. cerasiforme"
        }
        ```

    Response:
        ```json
        {
          "product_id": 10,
          "sku": "VEG-TOM-010",
          "category_id": 1,
          "family_id": 5,
          "name": "Cherry Tomato",
          ...
        }
        ```
    """
    try:
        logger.info(
            "Creating product",
            extra={
                "name": request.name,
                "category_id": request.category_id,
                "family_id": request.family_id,
            },
        )

        service = factory.get_product_service()
        product = await service.create(request)

        logger.info(
            "Product created",
            extra={
                "product_id": product.product_id,
                "sku": product.sku,
                "name": product.name,
            },
        )

        return product

    except ValidationException as e:
        logger.warning("Product validation failed", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning("Resource not found", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.error("Failed to create product", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product.",
        )


@router.get(
    "/{sku}",
    response_model=ProductResponse,
    summary="Get product by SKU",
)
async def get_product_by_sku(
    sku: str,
    factory: ServiceFactory = Depends(get_factory),
) -> ProductResponse:
    """Get product details by SKU (C020).

    Args:
        sku: Product SKU (e.g., "VEG-TOM-010")

    Returns:
        ProductResponse with product details

    Raises:
        HTTPException 404: Product not found

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/products/VEG-TOM-010"
        ```
    """
    try:
        logger.info("Getting product by SKU", extra={"sku": sku})

        service = factory.get_product_service()
        product = await service.get_by_sku(sku)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with SKU '{sku}' not found",
            )

        logger.info(
            "Product retrieved",
            extra={"product_id": product.product_id, "sku": product.sku},
        )

        return product

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Failed to get product", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get product.",
        )
