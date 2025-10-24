# ML Visualization Quick Guide

## Detection Colors

The ML pipeline now uses **confidence-based color coding** for detections:

| Confidence Level | Color | Description |
|-----------------|-------|-------------|
| ≥ 80% | **Cyan** | High confidence - reliable detection |
| 50-79% | **Yellow** | Medium confidence - review recommended |
| < 50% | **Red** | Low confidence - verify manually |

## Visual Elements

### Bounding Boxes
- **Rectangle**: Outlines the exact detection area
- **Thickness**: 2px for clear visibility
- **Semi-transparent**: Preserves underlying image details

### Center Dots
- **3px filled circle** at detection center
- **Same color** as bounding box
- **Purpose**: Precise location reference for measurements

### Legend (Top-Left Corner)
```
Detected: [count]
Estimated: [count]
Confidence: [percentage]

Detection Colors:
High conf (cyan)     ← displayed in cyan
Med conf (yellow)    ← displayed in yellow
Low conf (red)       ← displayed in red
```

## Reading the Visualization

### Example Scenarios

**Scenario 1: High-Quality Detection**
```
✓ Cyan bounding box
✓ Confidence ≥80%
→ Action: Trust detection, proceed normally
```

**Scenario 2: Medium-Quality Detection**
```
⚠ Yellow bounding box
⚠ Confidence 50-79%
→ Action: Review if critical measurement
```

**Scenario 3: Low-Quality Detection**
```
✗ Red bounding box
✗ Confidence <50%
→ Action: Manual verification required
```

## Transparency Settings

- **Original image**: 60% visibility
- **Overlay**: 40% visibility
- **Result**: Clear boxes without obscuring details

## Code Location

**File**: `app/tasks/ml_tasks.py`
**Function**: `create_visualization_with_detections_and_estimations_task()`
**Lines**: 1333-1377 (detection drawing)

## Configuration

Current thresholds (hardcoded):
- High: `confidence >= 0.8`
- Medium: `confidence >= 0.5`
- Low: `confidence < 0.5`

To modify, edit lines 1358-1363 in `app/tasks/ml_tasks.py`.

---

**Last Updated**: 2025-10-24
