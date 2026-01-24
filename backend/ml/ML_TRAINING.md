# ML Training Guide

## Overview

This document describes the 2-stage ML pipeline for shelf recognition:

1. **Stage 1 - Detection**: YOLOv8 bottle/can detector
2. **Stage 2 - Classification**: EfficientNet + ArcFace SKU classifier

## Hard Performance Targets

| Metric | Target | Description |
|--------|--------|-------------|
| Detection Recall | >= 0.98 | Must detect 98%+ of bottles |
| mAP@50 | >= 0.95 | Detection accuracy at IoU=0.5 |
| SKU Top-1 Accuracy | >= 93% | Correct SKU identification |
| Count MAE | <= 0.30 | Mean absolute error per SKU |

## Installation

```bash
# Install ML dependencies
pip install -e ".[ml]"

# Or install individually
pip install ultralytics timm faiss-cpu albumentations
```

## Directory Structure

```
ml/
├── configs/           # Training configurations
├── training/          # Training scripts
├── inference/         # Inference pipeline
├── eval/              # Evaluation scripts
├── tools/             # Dataset utilities
├── data/              # Training data (not in git)
└── models/            # Trained models (not in git)
```

## Quick Start

### 1. Prepare Dataset

```bash
# Create dataset structure
mkdir -p ml/data/detector/{train,val,test}/images
mkdir -p ml/data/detector/{train,val,test}/labels
mkdir -p ml/data/classifier/{train,val,test}

# Hash dataset for versioning
python -m ml.tools.hash_dataset ml/data/detector --output ml/data/versions/detector_v1.json

# Create reproducible splits
python -m ml.tools.freeze_split ml/data/classifier --stratify --output ml/data/splits/classifier_v1.json
```

### 2. Train Detector (Stage 1)

```bash
# Train YOLOv8 bottle detector
python -m ml.training.train_detector --config ml/configs/detector.yaml

# Resume training
python -m ml.training.train_detector --resume runs/detector/latest/weights/last.pt

# Validate model
python -m ml.training.train_detector --validate runs/detector/latest/weights/best.pt

# Export to ONNX/TFLite
python -m ml.training.train_detector --export runs/detector/latest/weights/best.pt
```

### 3. Train Classifier (Stage 2)

```bash
# Train SKU classifier with ArcFace
python -m ml.training.train_classifier --config ml/configs/classifier.yaml

# Export embeddings for all SKUs
python -m ml.training.train_classifier \
    --export-embeddings \
    --weights runs/classifier/latest/best.pt \
    --data-path ml/data/classifier/train \
    --output-dir models/classifier

# Export to ONNX
python -m ml.training.train_classifier \
    --export-onnx \
    --weights runs/classifier/latest/best.pt
```

### 4. Evaluate Pipeline

```bash
# Run full evaluation
python -m ml.eval.eval_shelf_counts \
    --pipeline-config ml/configs/pipeline.yaml \
    --test-dir ml/data/test \
    --output results/eval_v1.json

# Evaluate from saved predictions
python -m ml.eval.eval_shelf_counts \
    --predictions predictions.json \
    --ground-truth ground_truth.json
```

### 5. Run Inference

```bash
# Test pipeline on single image
python -m ml.inference.pipeline_v2 test_image.jpg \
    --config ml/configs/pipeline.yaml \
    --output annotated_output.jpg
```

## Training Data Requirements

### Detector Data (YOLO Format)

```
data/detector/
├── train/
│   ├── images/
│   │   ├── img001.jpg
│   │   └── ...
│   └── labels/
│       ├── img001.txt    # YOLO format: class x_center y_center width height
│       └── ...
├── val/
└── test/
```

Label format (normalized coordinates):
```
0 0.5 0.5 0.2 0.4   # class=bottle, center=(0.5,0.5), size=(0.2,0.4)
1 0.3 0.7 0.15 0.3  # class=can
```

Classes:
- 0: bottle
- 1: can
- 2: glass
- 3: unknown_container

### Classifier Data (ImageFolder Format)

```
data/classifier/
├── train/
│   ├── sku_001_absolut_vodka/
│   │   ├── img001.jpg
│   │   ├── img002.jpg
│   │   └── ...
│   ├── sku_002_jagermeister/
│   └── ...
├── val/
└── test/
```

**Requirements:**
- Minimum 300 images per SKU
- Images should be cropped bottles (from detection stage)
- Various angles, lighting conditions, shelf positions

## Configuration Files

### detector.yaml

Key settings:
```yaml
model:
  architecture: "yolov8m"  # s/m/l/x

training:
  epochs: 100
  batch_size: 16

targets:
  recall_min: 0.98
  map50_min: 0.95
```

### classifier.yaml

Key settings:
```yaml
model:
  backbone: "efficientnet_b2"
  embedding_dim: 512
  metric_head:
    type: "arcface"
    margin: 0.5
    scale: 64

data:
  min_images_per_sku: 300
  hard_negative_mining:
    enabled: true

targets:
  top1_accuracy_min: 0.93
```

## Dataset Versioning

Always version your datasets before training:

```bash
# Create hash of current dataset
python -m ml.tools.hash_dataset ml/data/classifier \
    --output ml/data/versions/classifier_$(date +%Y%m%d).json

# Compare with previous version
python -m ml.tools.hash_dataset ml/data/classifier \
    --compare ml/data/versions/classifier_v1.json
```

## Model Export

### Export for Server (ONNX)

```bash
# Detector
python -m ml.training.train_detector \
    --export runs/detector/best/weights/best.pt \
    --output-dir models/detector

# Classifier
python -m ml.training.train_classifier \
    --export-onnx \
    --weights runs/classifier/best/best.pt \
    --output-dir models/classifier
```

### Export for Mobile (TFLite)

```bash
# Detector (via ultralytics)
yolo export model=runs/detector/best/weights/best.pt format=tflite

# Classifier (manual conversion)
python -c "
import torch
import onnx
from onnx_tf.backend import prepare
import tensorflow as tf

# Load ONNX
onnx_model = onnx.load('models/classifier/classifier.onnx')
tf_rep = prepare(onnx_model)
tf_rep.export_graph('models/classifier/classifier_tf')

# Convert to TFLite
converter = tf.lite.TFLiteConverter.from_saved_model('models/classifier/classifier_tf')
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()
with open('models/classifier/classifier.tflite', 'wb') as f:
    f.write(tflite_model)
"
```

## Active Learning

The pipeline automatically queues low-confidence predictions for human review:

```bash
# View queue via API
curl http://localhost:8000/api/v1/ai/v2/active-learning-queue

# Label an item
curl -X POST "http://localhost:8000/api/v1/ai/v2/active-learning/label?item_id=abc123&sku_id=42"
```

Queue location: `data/active_learning_queue/`

## Troubleshooting

### Low Detection Recall

1. Check training data quality - ensure all bottles are labeled
2. Lower confidence threshold in config
3. Add more training images with difficult angles/lighting
4. Try larger model (yolov8l instead of yolov8m)

### Low Classification Accuracy

1. Ensure minimum 300 images per SKU
2. Enable hard negative mining for similar bottles
3. Increase ArcFace margin for better class separation
4. Check for mislabeled training data

### High Count MAE

1. Detection recall is likely the issue - fix detection first
2. Check for duplicate detections (adjust NMS threshold)
3. Ensure consistent image resolution

## API Integration

Enable V2 pipeline in your environment:

```bash
export AI_V2_ENABLED=true
export AI_V2_PIPELINE_CONFIG=ml/configs/pipeline.yaml
```

Or in `.env`:
```
AI_V2_ENABLED=true
AI_V2_PIPELINE_CONFIG=ml/configs/pipeline.yaml
AI_V2_DETECTOR_MODEL=models/detector/best.onnx
AI_V2_CLASSIFIER_MODEL=models/classifier/best.onnx
AI_V2_EMBEDDINGS_PATH=models/classifier/embeddings.npy
```

Test endpoint:
```bash
curl -X POST http://localhost:8000/api/v1/ai/v2/recognize \
    -F "image=@shelf_photo.jpg"
```
