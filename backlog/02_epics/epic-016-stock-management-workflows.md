# Epic 016: Stock Management Workflows

**Status**: Ready
**Sprint**: Sprint-03 (Week 7-8)
**Priority**: critical (core business logic)
**Total Story Points**: 55
**Total Cards**: 11

---

## Goal

Implement complete stock management workflows including manual initialization, photo initialization,
stock movements, batch management, and monthly reconciliation with automated sales calculation.

---

## Success Criteria

- [ ] Manual initialization workflow complete with validation
- [ ] Photo initialization triggers ML pipeline
- [ ] All stock movement types supported (plantado, muerte, transplante, ventas)
- [ ] Monthly reconciliation calculates sales automatically
- [ ] Stock batch aggregation working
- [ ] Full audit trail for all movements
- [ ] Movement history API with pagination

---

## Cards List (11 cards, 55 points)

### Initialization Workflows (20 points)

- **STOCK001**: Manual initialization workflow (8pts) - **CRITICAL**
- **STOCK002**: Photo initialization workflow (8pts) - **CRITICAL**
- **STOCK003**: Initialization validation (product match) (4pts)

### Stock Movements (20 points)

- **STOCK004**: Plantado (planting) movement (3pts)
- **STOCK005**: Muerte (death) movement (3pts)
- **STOCK006**: Transplante (transfer) movement (5pts)
- **STOCK007**: Ventas (sales) movement (3pts)
- **STOCK008**: Ajuste (adjustment) movement (3pts)
- **STOCK009**: Movement validation rules (3pts)

### Batch Management (10 points)

- **STOCK010**: Batch creation and aggregation (5pts)
- **STOCK011**: Batch lifecycle management (3pts)
- **STOCK012**: Batch code generation (LOC-PROD-DATE-SEQ) (2pts)

### Reconciliation (5 points)

- **STOCK013**: Monthly reconciliation service (5pts)

---

## Dependencies

**Blocked By**: S001-S006 (stock services), DB019-DB020 (stock models)
**Blocks**: Business operations, monthly reporting

---

## Technical Approach

**Manual Initialization Flow**:

```
User submits: location_id, product_id, quantity
   ↓
Validate: config exists for location
   ↓
Validate: product_id matches config.product_id
   ↓
Create: stock_movement (type: "manual_init")
   ↓
Create: stock_batch (aggregated state)
   ↓
Return: movement_id + batch_code
```

**Monthly Reconciliation** (automated sales):

```sql
-- Formula: sales = (baseline + movements_in - movements_out) - new_photo_count
SELECT
    (SELECT quantity FROM stock_movements WHERE type = 'foto' AND created_at = '2025-09-01') +
    (SELECT SUM(quantity) FROM stock_movements WHERE type = 'plantado' AND created_at BETWEEN '2025-09-01' AND '2025-09-30') -
    (SELECT SUM(ABS(quantity)) FROM stock_movements WHERE type IN ('muerte', 'transplante') AND created_at BETWEEN '2025-09-01' AND '2025-09-30') -
    (SELECT quantity FROM stock_movements WHERE type = 'foto' AND created_at = '2025-10-01')
AS calculated_sales;
```

---

**Epic Owner**: Backend Lead
**Created**: 2025-10-09
