# S007: StockMovementService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-03
- **Status**: `backlog`
- **Priority**: `CRITICAL`
- **Complexity**: XL (8 story points)
- **Area**: `services/stock`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [S008, S011, S012, C007]
  - Blocked by: [R007, S003, S008, S009, S036]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/workflows/README.md](../../engineering_plan/workflows/README.md)
- **Architecture**: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)
- **Manual Init Workflow**: [../../flows/manual_stock_initialization/](../../flows/manual_stock_initialization/)

## Description

**What**: Implement `StockMovementService` for **manual stock initialization**, movement tracking (plantado, muerte, trasplante, venta), and reconciliation logic.

**Why**: StockMovementService is the **CORE of the stock management system**. It handles:
1. **Manual stock initialization** (alternative to photo-based init)
2. **Monthly movements** (plantings, deaths, transplants)
3. **Sales calculation** (month-end reconciliation)
4. **Movement validation** (business rules via S009)

**Context**: Clean Architecture Application Layer. **CRITICAL SERVICE** - orchestrates S003 (location validation), S008 (batch creation), S009 (movement validation), and S036 (config validation). This service implements the **monthly reconciliation workflow**.

## Acceptance Criteria

- [ ] **AC1**: Manual stock initialization (PRIMARY workflow):
  ```python
  from app.services.storage_location_service import StorageLocationService
  from app.services.storage_location_config_service import StorageLocationConfigService
  from app.services.stock_batch_service import StockBatchService
  from app.services.movement_validation_service import MovementValidationService
  from app.repositories.stock_movement_repository import StockMovementRepository

  class StockMovementService:
      """
      Business logic for stock movements and reconciliation
      CRITICAL SERVICE for manual initialization and monthly reconciliation
      """

      def __init__(
          self,
          movement_repo: StockMovementRepository,
          location_service: StorageLocationService,
          config_service: StorageLocationConfigService,
          batch_service: StockBatchService,
          validation_service: MovementValidationService
      ):
          self.movement_repo = movement_repo
          self.location_service = location_service
          self.config_service = config_service
          self.batch_service = batch_service
          self.validation_service = validation_service

      async def create_manual_initialization(
          self,
          request: ManualStockInitRequest
      ) -> StockMovementResponse:
          """
          CRITICAL: Manual stock initialization workflow
          Alternative to photo-based initialization
          """
          # 1. Validate storage location exists
          location = await self.location_service.get_storage_location_by_id(
              request.storage_location_id
          )
          if not location:
              raise StorageLocationNotFoundException(request.storage_location_id)

          # 2. Validate configuration exists and matches product/packaging
          config = await self.config_service.get_by_location(
              request.storage_location_id
          )
          if not config:
              raise ConfigNotFoundException(
                  f"No configuration found for location {request.storage_location_id}. "
                  "Manual initialization requires expected product configuration."
              )

          # 3. CRITICAL VALIDATION: Product and packaging must match config
          if config.product_id != request.product_id:
              raise ProductMismatchException(
                  expected=config.product_id,
                  actual=request.product_id,
                  message=f"Expected product {config.product_id}, got {request.product_id}"
              )

          if config.packaging_catalog_id != request.packaging_catalog_id:
              raise PackagingMismatchException(
                  expected=config.packaging_catalog_id,
                  actual=request.packaging_catalog_id
              )

          # 4. Business validation (via MovementValidationService)
          validation_result = await self.validation_service.validate_manual_init(request)
          if not validation_result.valid:
              raise ValidationException(validation_result.errors)

          # 5. Create stock movement (type: "manual_init")
          movement_data = {
              "storage_location_id": request.storage_location_id,
              "movement_type": "manual_init",
              "quantity": request.quantity,
              "product_id": request.product_id,
              "packaging_catalog_id": request.packaging_catalog_id,
              "product_size": request.product_size,
              "source_type": "manual",
              "timestamp": func.now(),
              "notes": request.notes
          }

          movement = await self.movement_repo.create(movement_data)

          # 6. Create stock batch (via StockBatchService)
          batch = await self.batch_service.create_from_movement(movement)

          return StockMovementResponse.from_model(movement)
  ```

- [ ] **AC2**: Movement creation (plantado, muerte, trasplante):
  ```python
  async def create_movement(
      self,
      request: StockMovementCreateRequest
  ) -> StockMovementResponse:
      """
      Create stock movement (planting, death, transplant)
      Used during monthly operations
      """
      # 1. Validate location
      location = await self.location_service.get_storage_location_by_id(
          request.storage_location_id
      )
      if not location:
          raise StorageLocationNotFoundException(request.storage_location_id)

      # 2. Business validation
      validation_result = await self.validation_service.validate_movement(request)
      if not validation_result.valid:
          raise ValidationException(validation_result.errors)

      # 3. For transplants, validate destination location
      if request.movement_type == "trasplante" and request.destination_location_id:
          dest_location = await self.location_service.get_storage_location_by_id(
              request.destination_location_id
          )
          if not dest_location:
              raise StorageLocationNotFoundException(request.destination_location_id)

      # 4. Create movement
      movement = await self.movement_repo.create(request.model_dump())

      # 5. Update stock batches (via BatchService)
      if request.movement_type in ["plantado", "trasplante"]:
          await self.batch_service.update_from_movement(movement)
      elif request.movement_type == "muerte":
          await self.batch_service.decrement_from_movement(movement)

      return StockMovementResponse.from_model(movement)
  ```

- [ ] **AC3**: Sales calculation (month-end reconciliation):
  ```python
  async def calculate_sales(
      self,
      storage_location_id: int,
      start_date: datetime,
      end_date: datetime
  ) -> SalesCalculationResponse:
      """
      Calculate sales for a location (monthly reconciliation)
      Formula: sales = start_count + movements - end_count
      """
      # 1. Get start count (baseline - photo or manual init)
      start_count = await self.movement_repo.get_count_at_date(
          storage_location_id, start_date
      )

      # 2. Get all movements in period
      movements = await self.movement_repo.get_movements_in_period(
          storage_location_id, start_date, end_date
      )

      # Calculate net movement
      net_movement = sum(
          m.quantity if m.movement_type in ["plantado", "trasplante_in"]
          else -m.quantity
          for m in movements
      )

      # 3. Get end count (photo or manual)
      end_count = await self.movement_repo.get_count_at_date(
          storage_location_id, end_date
      )

      # 4. Calculate sales
      calculated_sales = start_count + net_movement - end_count

      return SalesCalculationResponse(
          storage_location_id=storage_location_id,
          period_start=start_date,
          period_end=end_date,
          start_count=start_count,
          net_movement=net_movement,
          end_count=end_count,
          calculated_sales=calculated_sales
      )
  ```

- [ ] **AC4**: Get movements by location and period:
  ```python
  async def get_movements_for_location(
      self,
      storage_location_id: int,
      start_date: Optional[datetime] = None,
      end_date: Optional[datetime] = None,
      movement_types: Optional[List[str]] = None
  ) -> List[StockMovementResponse]:
      """Get movements for a location with filters"""
      movements = await self.movement_repo.get_by_location(
          storage_location_id,
          start_date=start_date,
          end_date=end_date,
          movement_types=movement_types
      )

      return [StockMovementResponse.from_model(m) for m in movements]
  ```

- [ ] **AC5**: Reverse movement (correction):
  ```python
  async def reverse_movement(
      self,
      movement_id: int,
      reason: str
  ) -> StockMovementResponse:
      """
      Reverse a movement (create compensating movement)
      Used for manual corrections
      """
      # 1. Get original movement
      original = await self.movement_repo.get(movement_id)
      if not original:
          raise StockMovementNotFoundException(movement_id)

      # 2. Create reverse movement
      reverse_data = {
          "storage_location_id": original.storage_location_id,
          "movement_type": f"{original.movement_type}_reverse",
          "quantity": -original.quantity,  # Negate quantity
          "product_id": original.product_id,
          "packaging_catalog_id": original.packaging_catalog_id,
          "product_size": original.product_size,
          "source_type": "manual_correction",
          "notes": f"Reversal of movement {movement_id}: {reason}",
          "original_movement_id": movement_id
      }

      reverse_movement = await self.movement_repo.create(reverse_data)

      # 3. Update batches
      await self.batch_service.reverse_movement(original, reverse_movement)

      return StockMovementResponse.from_model(reverse_movement)
  ```

- [ ] **AC6**: Schema transformations:
  ```python
  # In app/schemas/stock_movement_schema.py
  class ManualStockInitRequest(BaseModel):
      """Manual initialization request (alternative to photo)"""
      storage_location_id: int
      product_id: int
      packaging_catalog_id: int
      product_size: str  # "pequeño", "mediano", "grande"
      quantity: int = Field(gt=0)
      notes: Optional[str] = None

      @field_validator('quantity')
      @classmethod
      def quantity_positive(cls, v):
          if v <= 0:
              raise ValueError("Quantity must be positive")
          return v

  class StockMovementResponse(BaseModel):
      stock_movement_id: int
      storage_location_id: int
      movement_type: str
      quantity: int
      product_id: int
      packaging_catalog_id: int
      product_size: str
      source_type: str  # "manual", "foto", "manual_correction"
      timestamp: datetime
      notes: Optional[str]

      # Nested location (optional)
      storage_location: Optional["StorageLocationResponse"] = None

      @classmethod
      def from_model(
          cls,
          movement: StockMovement,
          include_location: bool = False
      ) -> "StockMovementResponse":
          """Transform model → schema"""
          response = cls(
              stock_movement_id=movement.stock_movement_id,
              storage_location_id=movement.storage_location_id,
              movement_type=movement.movement_type,
              quantity=movement.quantity,
              product_id=movement.product_id,
              packaging_catalog_id=movement.packaging_catalog_id,
              product_size=movement.product_size,
              source_type=movement.source_type,
              timestamp=movement.timestamp,
              notes=movement.notes
          )

          if include_location and movement.storage_location:
              from app.schemas.storage_location_schema import StorageLocationResponse
              response.storage_location = StorageLocationResponse.from_model(
                  movement.storage_location
              )

          return response
  ```

- [ ] **AC7**: Unit tests achieve ≥90% coverage (CRITICAL service)

## Technical Implementation Notes

### Architecture
- **Layer**: Application (Service)
- **Dependencies**: R007 (StockMovementRepository), S003, S008, S009, S036
- **Design Pattern**: Orchestration service with transaction boundaries
- **Critical for**: Manual initialization, monthly reconciliation

### Code Hints

**Transaction boundary:**
```python
from sqlalchemy.ext.asyncio import AsyncSession

async def create_manual_initialization(self, request):
    """Transaction spans movement + batch creation"""
    async with self.movement_repo.session.begin():
        movement = await self.movement_repo.create(...)
        batch = await self.batch_service.create_from_movement(movement)
        # Auto-commit on exit (or rollback on exception)
    return movement
```

### Testing Requirements

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_manual_init_with_config_validation():
    """Test manual initialization validates config"""
    movement_repo = AsyncMock()
    location_svc = AsyncMock()
    config_svc = AsyncMock()
    batch_svc = AsyncMock()
    validation_svc = AsyncMock()

    # Mock config exists and matches
    location_svc.get_storage_location_by_id.return_value = Mock(storage_location_id=1)
    config_svc.get_by_location.return_value = Mock(
        product_id=1,
        packaging_catalog_id=1
    )
    validation_svc.validate_manual_init.return_value = Mock(valid=True)

    service = StockMovementService(
        movement_repo, location_svc, config_svc, batch_svc, validation_svc
    )

    request = ManualStockInitRequest(
        storage_location_id=1,
        product_id=1,
        packaging_catalog_id=1,
        product_size="mediano",
        quantity=100
    )

    result = await service.create_manual_initialization(request)

    # Verify service call chain
    config_svc.get_by_location.assert_called_once_with(1)
    validation_svc.validate_manual_init.assert_called_once()
    batch_svc.create_from_movement.assert_called_once()

@pytest.mark.asyncio
async def test_manual_init_product_mismatch():
    """Test rejection when product doesn't match config"""
    config_svc = AsyncMock()
    config_svc.get_by_location.return_value = Mock(
        product_id=1,  # Expected
        packaging_catalog_id=1
    )

    service = StockMovementService(
        AsyncMock(), AsyncMock(), config_svc, AsyncMock(), AsyncMock()
    )
    service.location_service.get_storage_location_by_id = AsyncMock(return_value=Mock())

    request = ManualStockInitRequest(
        storage_location_id=1,
        product_id=999,  # Wrong product
        packaging_catalog_id=1,
        product_size="mediano",
        quantity=100
    )

    with pytest.raises(ProductMismatchException):
        await service.create_manual_initialization(request)

@pytest.mark.asyncio
async def test_calculate_sales():
    """Test sales calculation formula"""
    movement_repo = AsyncMock()
    movement_repo.get_count_at_date.side_effect = [100, 80]  # Start, end
    movement_repo.get_movements_in_period.return_value = [
        Mock(movement_type="plantado", quantity=10),
        Mock(movement_type="muerte", quantity=5)
    ]

    service = StockMovementService(movement_repo, ...)
    result = await service.calculate_sales(1, start_date, end_date)

    # sales = start + movements - end = 100 + (10 - 5) - 80 = 25
    assert result.calculated_sales == 25
```

**Coverage Target**: ≥90%

### Performance Expectations
- `create_manual_initialization`: <100ms (includes validation + batch creation)
- `create_movement`: <50ms
- `calculate_sales`: <200ms (aggregation query)
- `get_movements_for_location`: <100ms for 1000 movements

## Handover Briefing

**For the next developer:**

**Context**: StockMovementService is the **CORE of stock management**. Implements manual initialization (alternative to photo-based) and monthly reconciliation workflow.

**Key decisions made**:
1. **Config validation MANDATORY**: Manual init requires matching product/packaging in config
2. **Transaction boundaries**: Movement + batch creation in single transaction
3. **Sales calculation**: Formula-based (start + movements - end)
4. **Reverse movements**: Compensating entries (not deletes) for audit trail
5. **Service orchestration**: Calls S003, S008, S009, S036 (NOT repositories)

**Known limitations**:
- Sales calculation assumes no concurrent modifications to stock
- Reverse movement creates new entry (doesn't delete original)
- No bulk movement creation (create individually)

**Next steps**:
- S008: StockBatchService (aggregates movements into batches)
- S009: MovementValidationService (business rules)
- S011: ReconciliationService (month-end workflow)

**Questions to validate**:
- Should manual init allow quantity = 0 (empty location)?
- How to handle concurrent movements to same location?
- Should sales calculation detect negative stock?

## Definition of Done Checklist

- [ ] Service code with manual initialization
- [ ] Config validation working (product + packaging match)
- [ ] Sales calculation tested
- [ ] Transaction boundaries verified
- [ ] Unit tests pass (≥90% coverage)
- [ ] Integration tests with all dependencies
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 8 story points (~16 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
