# [ML008] Mask Generation Service

## Metadata
- **Epic**: epic-007
- **Sprint**: Sprint-02
- **Priority**: `medium`
- **Complexity**: S (3 points)
- **Dependencies**: Blocks [ML009], Blocked by [ML003]

## Description
Generate soft circular masks around each detection for visualization and residual calculation.

## Acceptance Criteria
- [ ] Create binary mask per detection (circular, radius = 85% of bbox)
- [ ] Gaussian blur for soft edges (kernel=15)
- [ ] Union mask (all detections combined)
- [ ] Return as numpy array

## Implementation
```python
class MaskGenerationService:
    def create_detection_masks(self, detections, image_shape):
        mask = np.zeros(image_shape[:2], dtype=np.uint8)
        for det in detections:
            radius = int(max(det['width_px'], det['height_px']) * 0.85)
            cv2.circle(mask, (int(det['center_x_px']), int(det['center_y_px'])), radius, 255, -1)
        return cv2.GaussianBlur(mask, (15, 15), 0)
```

## Testing
- Verify mask dimensions match image
- Check soft edges (no hard circles)

---
**Card Created**: 2025-10-09
