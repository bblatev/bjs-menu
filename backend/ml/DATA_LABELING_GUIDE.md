# Data Labeling Guide

## Overview

This guide covers how to label training data for the 2-stage ML pipeline:

1. **Detection Labels**: Bounding boxes around bottles/cans
2. **Classification Labels**: SKU identification for cropped bottles

## Detection Labeling (Stage 1)

### Classes

| ID | Class | Description |
|----|-------|-------------|
| 0 | bottle | Glass or plastic bottles |
| 1 | can | Metal cans (beer, energy drinks) |
| 2 | glass | Drinking glasses (with or without liquid) |
| 3 | unknown_container | Other containers that should be detected |

### YOLO Label Format

Each image requires a corresponding `.txt` file with the same name:

```
<class_id> <x_center> <y_center> <width> <height>
```

All coordinates are normalized (0.0 - 1.0):
- `x_center`: Center X position / image width
- `y_center`: Center Y position / image height
- `width`: Box width / image width
- `height`: Box height / image height

Example (`shelf_001.txt`):
```
0 0.234 0.567 0.089 0.312
0 0.456 0.543 0.092 0.298
1 0.678 0.521 0.045 0.156
```

### Labeling Tools

Recommended tools for YOLO format:
- **LabelImg** - Free, simple, exports YOLO format directly
- **CVAT** - Web-based, supports teams
- **Roboflow** - Cloud-based with augmentation

### Detection Labeling Guidelines

1. **Draw Tight Boxes**
   - Box should tightly fit the bottle/can
   - Include cap/top but not excessive background
   - If partially visible (>50%), still label it

2. **Label All Instances**
   - Label EVERY bottle/can visible in the image
   - Even if blurry or partially occluded
   - Missing labels hurt recall more than imperfect boxes

3. **Handling Occlusion**
   - If >50% visible: Label with visible bounding box
   - If <50% visible: Skip (don't label)
   - Multiple bottles overlapping: Label each separately

4. **Edge Cases**
   - Bottle on its side: Still label as bottle
   - Empty vs full: Same class (bottle)
   - Different sizes: Same class if same type

### Quality Checklist

Before submitting detection labels:
- [ ] Every visible bottle/can is labeled
- [ ] Boxes are tight (no excessive padding)
- [ ] Correct class assigned (bottle vs can)
- [ ] No duplicate boxes on same object
- [ ] Labels saved in YOLO format

## Classification Labeling (Stage 2)

### Folder Structure

Organize cropped bottle images by SKU:

```
data/classifier/
├── train/
│   ├── absolut_vodka_700ml/
│   │   ├── crop_001.jpg
│   │   ├── crop_002.jpg
│   │   └── ...  (300+ images)
│   ├── jagermeister_1l/
│   ├── jack_daniels_700ml/
│   └── ...
├── val/
└── test/
```

### SKU Naming Convention

Use consistent, descriptive folder names:
```
<brand>_<product>_<size>
```

Examples:
- `absolut_vodka_700ml`
- `jagermeister_1l`
- `coca_cola_330ml_can`
- `heineken_500ml_can`

### Image Requirements

1. **Source**: Cropped from detection stage or manual crops
2. **Size**: At least 224x224 pixels
3. **Content**: Single bottle/can, centered
4. **Variety**: Multiple angles, lighting, backgrounds

### Minimum Images Per SKU

| Priority | Images Required |
|----------|-----------------|
| Top 100 SKUs | 300+ images |
| Medium sellers | 150+ images |
| Low sellers | 50+ images |

### Classification Labeling Guidelines

1. **Verify Correct SKU**
   - Check brand name visible on label
   - Verify product variant (original vs flavored)
   - Confirm size if distinguishable

2. **Image Quality**
   - Clear enough to read label (if readable in original)
   - Reasonably centered
   - Not severely cropped

3. **Variety in Training Set**
   - Different angles (front, slight angle, back)
   - Different lighting (bar lighting, flash, natural)
   - Different backgrounds (shelf, counter, hand-held)
   - Different fill levels (full, partial, empty)

4. **Handling Similar Products**
   - Same brand, different products: Separate folders
   - Same product, different sizes: Separate folders
   - Regional variants: Same folder if label identical

### Quality Checklist

Before submitting classification labels:
- [ ] Folder name matches actual product
- [ ] All images in folder show same SKU
- [ ] Minimum 50 images per SKU (300+ for top SKUs)
- [ ] Mix of angles and lighting conditions
- [ ] No severely blurry or unrecognizable images

## Data Collection Tips

### From Existing Photos

1. Run detector on shelf photos to get crops
2. Sort crops into SKU folders
3. Verify and correct any misclassifications

```bash
# Run detection and save crops
python -m ml.inference.pipeline_v2 shelf_photos/*.jpg \
    --save-crops data/crops/
```

### From Video

Use the video upload endpoint to extract frames:

```bash
curl -X POST http://localhost:8000/api/v1/ai/training/upload-video \
    -F "video=@bottle_rotation.mp4" \
    -F "product_id=42" \
    -F "frames_per_second=3"
```

### Manual Photography

For new SKUs, capture:
1. Front label (5+ angles)
2. Back label (3+ angles)
3. On shelf with other bottles
4. In hand/motion
5. Under different lighting

## Active Learning Integration

The system automatically queues uncertain predictions:

1. **Review Queue**: Check `data/active_learning_queue/`
2. **Label via API**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/ai/v2/active-learning/label" \
       -d "item_id=abc123" \
       -d "sku_id=42"
   ```
3. **Skip Unclear Images**: Delete from queue if unrecognizable

## Common Mistakes

### Detection

| Mistake | Impact | Fix |
|---------|--------|-----|
| Missing labels | Low recall | Label ALL visible bottles |
| Loose boxes | Lower mAP | Draw tight boxes |
| Wrong class | Confusion | Double-check bottle vs can |
| Duplicate boxes | False positives | One box per object |

### Classification

| Mistake | Impact | Fix |
|---------|--------|-----|
| Wrong SKU folder | Confusion | Verify brand/product |
| Too few images | Overfitting | Collect 300+ per SKU |
| All same angle | Poor generalization | Add variety |
| Blurry images | Noise in training | Remove low quality |

## Annotation Workflow

### For Detection

1. Collect shelf images
2. Open in labeling tool (LabelImg)
3. Draw boxes around all bottles/cans
4. Assign correct class (0-3)
5. Export in YOLO format
6. Run `python -m ml.tools.hash_dataset` to version

### For Classification

1. Get crops from detection or manual
2. Sort into SKU folders
3. Verify each folder's contents
4. Ensure minimum image count
5. Create train/val/test split:
   ```bash
   python -m ml.tools.freeze_split data/classifier \
       --stratify --train 0.7 --val 0.15 --test 0.15
   ```

## Versioning

Always version your dataset before training:

```bash
# Create dataset snapshot
python -m ml.tools.hash_dataset data/detector \
    --output data/versions/detector_$(date +%Y%m%d).json

python -m ml.tools.hash_dataset data/classifier \
    --output data/versions/classifier_$(date +%Y%m%d).json
```

This ensures reproducibility and tracks data changes over time.
