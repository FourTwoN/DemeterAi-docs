"""Base Service Layer Template - Clean Architecture Pattern"""

from app.repositories.base import AsyncRepository


class BaseService:
    """
    Base service template following Clean Architecture.

    CRITICAL RULES:
    1. Services call OTHER SERVICES (NOT repositories directly)
    2. Services contain business logic (NOT repositories)
    3. Services are framework-agnostic (NO FastAPI imports)
    4. Services transform Pydantic schemas ↔ SQLAlchemy models
    """

    def __init__(self, repository: AsyncRepository, **service_dependencies):
        """
        Inject repository + other services (NOT other repositories!).

        Example:
            def __init__(
                self,
                repo: StockMovementRepository,
                config_service: StorageLocationConfigService,  # ✅ Service
                batch_service: StockBatchService,              # ✅ Service
            ):
                self.repo = repo
                self.config_service = config_service
                self.batch_service = batch_service
        """
        self.repo = repository

    # Add business logic methods here


# Example: Stock Movement Service
class StockMovementService:
    """Template showing Service→Service communication (Clean Architecture)."""

    def __init__(
        self,
        repo,  # StockMovementRepository
        config_service,  # StorageLocationConfigService  ✅
        batch_service,  # StockBatchService             ✅
        session_service,  # PhotoSessionService           ✅
    ):
        self.repo = repo
        self.config_service = config_service  # ✅ Service
        self.batch_service = batch_service  # ✅ Service
        self.session_service = session_service  # ✅ Service

    async def create_manual_initialization(self, request):
        """
        Business logic: Manual stock initialization with validation.

        Shows CORRECT Service→Service pattern.
        """
        # ✅ CORRECT: Call config_service (NOT config_repo)
        config = await self.config_service.get_by_location(request.location_id)

        # Business rule: Validate product matches config
        if config.product_id != request.product_id:
            raise ProductMismatchException(expected=config.product_id, actual=request.product_id)

        # Create movement via repository
        movement = await self.repo.create(
            {
                "movement_type": "manual_init",
                "quantity": request.quantity,
                "location_id": request.location_id,
            }
        )

        # ✅ CORRECT: Call batch_service (NOT batch_repo)
        batch = await self.batch_service.create_from_movement(movement)

        return movement


# Anti-Pattern Examples (DO NOT DO THIS!)
class BAD_Service_Examples:
    """These violate Clean Architecture."""

    def __init__(
        self,
        repo,
        config_repo,  # ❌ WRONG: Repository (should be service)
        batch_repo,  # ❌ WRONG: Repository (should be service)
    ):
        self.repo = repo
        self.config_repo = config_repo  # ❌ WRONG
        self.batch_repo = batch_repo  # ❌ WRONG

    async def bad_method(self, request):
        # ❌ WRONG: Direct repository access
        config = await self.config_repo.get(request.location_id)

        # ❌ WRONG: Bypasses business logic in ConfigService
        # ❌ WRONG: No validation, no error handling from service

        movement = await self.repo.create({...})

        # ❌ WRONG: Direct repository access
        batch = await self.batch_repo.create({...})
