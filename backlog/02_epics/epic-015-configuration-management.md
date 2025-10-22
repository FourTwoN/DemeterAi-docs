# Epic 015: Configuration Management

**Status**: Ready
**Sprint**: Sprint-03 (Week 7-8)
**Priority**: high (enables ML pipeline)
**Total Story Points**: 35
**Total Cards**: 7

---

## Goal

Implement storage location configuration system with product/packaging assignment, density parameter
auto-calibration, and validation rules for manual initialization.

---

## Success Criteria

- [ ] Storage location config CRUD operations
- [ ] Product/packaging assignment per location
- [ ] Configuration validation (prevents mismatches)
- [ ] Density parameters auto-calibration from ML results
- [ ] Bulk config import from Excel
- [ ] Config history tracking (audit trail)

---

## Cards List (7 cards, 35 points)

### Config CRUD (15 points)

- **CONFIG001**: Create location config (5pts)
- **CONFIG002**: Update location config (3pts)
- **CONFIG003**: Get config by location (2pts)
- **CONFIG004**: Delete config (2pts)
- **CONFIG005**: List all configs (filtered) (3pts)

### Density Parameters (12 points)

- **CONFIG006**: Density param CRUD (3pts)
- **CONFIG007**: Auto-calibration from ML results (5pts)
- **CONFIG008**: Manual calibration (3pts)
- **CONFIG009**: Param history tracking (1pt)

### Bulk Operations (8 points)

- **CONFIG010**: Bulk import from Excel (5pts)
- **CONFIG011**: Config validation rules (3pts)

---

## Dependencies

**Blocked By**: DB012-DB013 (config models), S028-S030 (config services)
**Blocks**: Manual initialization (S003), ML pipeline (classification)

---

## Technical Approach

**Configuration Validation**:

```python
async def validate_config(location_id: int, product_id: int):
    config = await config_repo.get_by_location(location_id)

    if not config:
        raise ConfigNotFoundException(location_id)

    if config.product_id != product_id:
        raise ProductMismatchException(
            expected=config.product_id,
            actual=product_id
        )
```

**Auto-Calibration** (from ML detections):

```python
# After 10+ photos processed for a location
detections = await detection_repo.get_recent(location_id, limit=100)

avg_area_per_plant = sum(d.area_px for d in detections) / len(detections)
plants_per_m2 = calculate_density(avg_area_per_plant, location.area_m2)

await density_params_repo.create({
    "location_id": location_id,
    "plants_per_m2": plants_per_m2,
    "auto_calibrated": True
})
```

---

**Epic Owner**: Backend Lead
**Created**: 2025-10-09
