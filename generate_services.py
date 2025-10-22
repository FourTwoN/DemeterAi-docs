#!/usr/bin/env python3
"""
Generate all simple CRUD services based on templates.

This script generates services for:
- ProductState, ProductSize (enum services)
- PackagingType, PackagingColor, PackagingMaterial, PackagingCatalog (packaging services)
- DensityParameter, PriceList, StorageLocationConfig (config services)

All follow the same CRUD pattern as ProductCategoryService.
"""

import sys

from app.core.logging import get_logger

logger = get_logger(__name__)

SIMPLE_SERVICES = [
    # (Service Name, Model Name, Repo Name, ID Field, Has Description)
    ("ProductStateService", "ProductState", "ProductStateRepository", "state_id", True),
    ("ProductSizeService", "ProductSize", "ProductSizeRepository", "size_id", True),
    ("PackagingTypeService", "PackagingType", "PackagingTypeRepository", "packaging_type_id", True),
    ("PackagingColorService", "PackagingColor", "PackagingColorRepository", "color_id", True),
    (
        "PackagingMaterialService",
        "PackagingMaterial",
        "PackagingMaterialRepository",
        "material_id",
        True,
    ),
    (
        "PackagingCatalogService",
        "PackagingCatalog",
        "PackagingCatalogRepository",
        "catalog_id",
        False,
    ),
    (
        "DensityParameterService",
        "DensityParameter",
        "DensityParameterRepository",
        "density_id",
        False,
    ),
    ("PriceListService", "PriceList", "PriceListRepository", "price_list_id", False),
    (
        "StorageLocationConfigService",
        "StorageLocationConfig",
        "StorageLocationConfigRepository",
        "config_id",
        False,
    ),
]

SERVICE_TEMPLATE = '''"""{service_doc}"""

from app.repositories.{repo_module} import {repo_name}
from app.schemas.{schema_module} import (
    {model_name}CreateRequest,
    {model_name}Response,
    {model_name}UpdateRequest,
)


class {service_name}:
    """{service_doc_detailed}"""

    def __init__(self, repo: {repo_name}) -> None:
        self.repo = repo

    async def create(self, request: {model_name}CreateRequest) -> {model_name}Response:
        """Create a new {model_lower}."""
        data = request.model_dump()
        model = await self.repo.create(data)
        return {model_name}Response.from_model(model)

    async def get_by_id(self, id: int) -> {model_name}Response:
        """Get {model_lower} by ID."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError(f"{{model_name}} {{{{id}}}} not found")
        return {model_name}Response.from_model(model)

    async def get_all(self, limit: int = 100) -> list[{model_name}Response]:
        """Get all {model_lower}s."""
        models = await self.repo.get_multi(limit=limit)
        return [{model_name}Response.from_model(m) for m in models]

    async def update(self, id: int, request: {model_name}UpdateRequest) -> {model_name}Response:
        """Update {model_lower}."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError(f"{{model_name}} {{{{id}}}} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.repo.update(id, update_data)
        return {model_name}Response.from_model(updated_model)

    async def delete(self, id: int) -> None:
        """Delete {model_lower}."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError(f"{{model_name}} {{{{id}}}} not found")
        await self.repo.delete(id)
'''


def snake_case(name: str) -> str:
    """Convert CamelCase to snake_case."""
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def generate_service(
    service_name: str, model_name: str, repo_name: str, id_field: str, has_description: bool
) -> tuple[str, str]:
    """Generate service code."""
    model_lower = model_name.lower().replace("_", " ")
    repo_module = snake_case(repo_name)
    schema_module = snake_case(model_name) + "_schema"

    service_doc = f"{model_name} business logic service."
    service_doc_detailed = f"Business logic for {model_lower} operations (CRUD)."

    code = SERVICE_TEMPLATE.format(
        service_name=service_name,
        model_name=model_name,
        repo_name=repo_name,
        repo_module=repo_module,
        schema_module=schema_module,
        model_lower=model_lower,
        service_doc=service_doc,
        service_doc_detailed=service_doc_detailed,
        id_field=id_field,
    )

    file_path = f"app/services/{snake_case(service_name)}.py"
    return file_path, code


if __name__ == "__main__":
    logger.info("Starting service generation", count=len(SIMPLE_SERVICES))
    generated_count = 0

    for service_info in SIMPLE_SERVICES:
        service_name, model_name, repo_name, id_field, has_desc = service_info
        file_path, code = generate_service(service_name, model_name, repo_name, id_field, has_desc)
        logger.debug("Generating service", service=service_name, file=file_path)

        try:
            with open(file_path, "w") as f:
                f.write(code)
            logger.info("Service generated successfully", service=service_name, file=file_path)
            generated_count += 1
        except OSError as e:
            logger.error(
                "Failed to generate service", service=service_name, file=file_path, error=str(e)
            )
            sys.exit(1)

    logger.info(
        "Service generation completed", generated=generated_count, total=len(SIMPLE_SERVICES)
    )
