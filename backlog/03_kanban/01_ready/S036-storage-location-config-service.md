# S036: StorageLocationConfigService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `CRITICAL`
- **Complexity**: L (5 story points)
- **Area**: `services/config`
- **Dependencies**:
    - Blocks: [S007, S018, C032]
    - Blocked by: [R036, S003, S021, S027]

## Description

**What**: Service for storage_location_configs management (expected product/packaging configuration
for manual initialization validation).

**Why**: CRITICAL for manual stock initialization. Validates that user input matches expected
configuration.

**Context**: Application Layer. Called by S007 (StockMovementService) to validate manual init. Calls
S003 (location), S021 (product), S027 (packaging).

## Acceptance Criteria

- [ ] **AC1**: Create config with validation (location, product, packaging must exist):

```python
class StorageLocationConfigService:
    def __init__(
        self,
        config_repo: StorageLocationConfigRepository,
        location_service: StorageLocationService,
        product_service: ProductService,
        packaging_service: PackagingCatalogService
    ):
        self.config_repo = config_repo
        self.location_service = location_service
        self.product_service = product_service
        self.packaging_service = packaging_service

    async def create_config(
        self,
        request: StorageLocationConfigCreateRequest
    ) -> StorageLocationConfigResponse:
        """Create configuration with cross-service validation"""
        # Validate location exists
        location = await self.location_service.get_storage_location_by_id(
            request.storage_location_id
        )
        if not location:
            raise StorageLocationNotFoundException(request.storage_location_id)

        # Validate product exists
        product = await self.product_service.get_product_by_id(request.product_id)
        if not product:
            raise ProductNotFoundException(request.product_id)

        # Validate packaging exists
        packaging = await self.packaging_service.get_packaging_by_id(
            request.packaging_catalog_id
        )
        if not packaging:
            raise PackagingNotFoundException(request.packaging_catalog_id)

        # Create config
        config = await self.config_repo.create(request.model_dump())
        return StorageLocationConfigResponse.from_model(config)
```

- [ ] **AC2**: Get config by location (for manual init validation)
- [ ] **AC3**: Update config (change expected product/packaging)
- [ ] **AC4**: Validate manual init against config (called by S007)
- [ ] **AC5**: Unit tests ≥90% coverage (CRITICAL service)

## Technical Notes

- CRITICAL for manual initialization workflow
- One config per location (unique constraint)
- Used by S007 to validate manual stock init

## Handover Briefing

**Context**: CRITICAL SERVICE for manual initialization. Validates user input against expected
configuration.

**Key decisions**:

- One config per location (1:1 relationship)
- Validation via services (NOT repositories)
- Config mandatory for manual init (no config = manual init fails)

## Time Tracking

- **Estimated**: 5 story points (~10 hours)

---
**Card Created**: 2025-10-09
