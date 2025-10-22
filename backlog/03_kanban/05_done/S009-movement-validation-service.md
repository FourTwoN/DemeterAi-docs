# S009: MovementValidationService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-03
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `services/stock`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [S007]
    - Blocked by: None (no repository dependencies)

## Description

**What**: Implement `MovementValidationService` for business rules validation (quantity limits,
movement type rules, date validations).

**Why**: Centralizes business logic validation for stock movements. Prevents invalid operations (
negative stock, future dates, invalid movement types).

**Context**: Clean Architecture Application Layer. Pure business logic service (no repository
dependencies). Called by StockMovementService before creating movements.

## Acceptance Criteria

- [ ] **AC1**: Validate manual initialization:

```python
class MovementValidationService:
    async def validate_manual_init(
        self,
        request: ManualStockInitRequest
    ) -> ValidationResult:
        """Validate manual initialization request"""
        errors = []

        if request.quantity <= 0:
            errors.append("Quantity must be positive")

        if request.quantity > 100000:  # Sanity check
            errors.append("Quantity exceeds maximum (100,000)")

        if request.product_size not in ["pequeño", "mediano", "grande"]:
            errors.append("Invalid product size")

        return ValidationResult(valid=len(errors) == 0, errors=errors)
```

- [ ] **AC2**: Validate movement operations:

```python
async def validate_movement(
    self,
    request: StockMovementCreateRequest
) -> ValidationResult:
    """Validate stock movement"""
    errors = []

    # Date validation
    if request.timestamp and request.timestamp > datetime.utcnow():
        errors.append("Movement date cannot be in the future")

    # Movement type validation
    valid_types = ["plantado", "muerte", "trasplante", "venta", "manual_init"]
    if request.movement_type not in valid_types:
        errors.append(f"Invalid movement type: {request.movement_type}")

    # Quantity validation
    if request.quantity <= 0:
        errors.append("Quantity must be positive")

    return ValidationResult(valid=len(errors) == 0, errors=errors)
```

- [ ] **AC3**: Unit tests achieve ≥90% coverage

## Technical Implementation Notes

### Architecture

- **Layer**: Application (Service)
- **Dependencies**: None (pure business logic)
- **Design Pattern**: Validator pattern

### Testing Requirements

**Coverage Target**: ≥90%

## Definition of Done Checklist

- [ ] Service code written
- [ ] All validation rules implemented
- [ ] Unit tests pass (≥90% coverage)
- [ ] PR reviewed (2+ approvals)

## Time Tracking

- **Estimated**: 3 story points (~6 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
