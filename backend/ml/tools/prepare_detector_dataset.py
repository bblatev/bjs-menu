#!/usr/bin/env python3
"""
Auto-annotate Training Images for YOLO Detector

Uses pre-trained YOLO to generate bounding box annotations for bar items
(bottle, can, glass) from existing product training images.

Usage:
    python -m ml.tools.prepare_detector_dataset --input data/training_images --output data/detector

This will:
1. Run YOLOv8 on each image to detect bottles/cans/glasses
2. Generate YOLO format annotation files (.txt)
3. Split into train/val/test sets
4. Create data.yaml for training
"""

import argparse
import json
import logging
import os
import random
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# COCO class IDs for bar items
COCO_BAR_CLASSES = {
    39: "bottle",
    40: "wine glass",
    41: "cup",
    # Add can if using custom model
}

# Map to our class IDs
OUR_CLASSES = {
    "bottle": 0,
    "wine glass": 1,
    "glass": 1,
    "cup": 2,
    "can": 3,
}

CLASS_NAMES = ["bottle", "glass", "cup", "can"]


def check_ultralytics():
    """Check if ultralytics is installed."""
    try:
        from ultralytics import YOLO
        return True
    except ImportError:
        return False


def auto_annotate_image(
    model,
    image_path: Path,
    conf_threshold: float = 0.25,
) -> List[Tuple[int, float, float, float, float]]:
    """
    Auto-annotate a single image using YOLO.

    Returns list of (class_id, x_center, y_center, width, height) in YOLO format.
    All coordinates are normalized 0-1.
    """
    results = model(str(image_path), verbose=False)
    annotations = []

    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue

        for box in boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])

            if conf < conf_threshold:
                continue

            # Get class name from COCO
            cls_name = result.names.get(cls_id, "")

            # Map to our classes
            our_cls_id = None
            for key, value in OUR_CLASSES.items():
                if key.lower() in cls_name.lower():
                    our_cls_id = value
                    break

            if our_cls_id is None:
                continue

            # Get normalized bbox (YOLO format: x_center, y_center, width, height)
            xywhn = box.xywhn[0].tolist()
            annotations.append((our_cls_id, *xywhn))

    return annotations


def write_annotation(annotations: List[Tuple], output_path: Path):
    """Write annotations in YOLO format."""
    with open(output_path, "w") as f:
        for ann in annotations:
            cls_id, x, y, w, h = ann
            f.write(f"{cls_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")


def prepare_dataset(
    input_dir: Path,
    output_dir: Path,
    train_ratio: float = 0.8,
    val_ratio: float = 0.15,
    conf_threshold: float = 0.25,
    model_name: str = "yolov8n.pt",
):
    """
    Prepare YOLO detector dataset from training images.

    Args:
        input_dir: Directory with training images
        output_dir: Output directory for dataset
        train_ratio: Fraction for training set
        val_ratio: Fraction for validation set
        conf_threshold: Minimum confidence for auto-annotations
        model_name: Pre-trained YOLO model to use
    """
    if not check_ultralytics():
        logger.error("ultralytics not installed. Run: pip install ultralytics")
        return

    from ultralytics import YOLO

    # Load pre-trained model
    logger.info(f"Loading {model_name}...")
    model = YOLO(model_name)

    # Find all images
    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    images = []
    for ext in image_extensions:
        images.extend(input_dir.glob(f"*{ext}"))
        images.extend(input_dir.glob(f"*{ext.upper()}"))

    if not images:
        logger.error(f"No images found in {input_dir}")
        return

    logger.info(f"Found {len(images)} images")

    # Create output directories
    for split in ["train", "val", "test"]:
        (output_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (output_dir / split / "labels").mkdir(parents=True, exist_ok=True)

    # Shuffle and split
    random.shuffle(images)
    n_train = int(len(images) * train_ratio)
    n_val = int(len(images) * val_ratio)

    splits = {
        "train": images[:n_train],
        "val": images[n_train:n_train + n_val],
        "test": images[n_train + n_val:],
    }

    # Process images
    stats = {"total": 0, "annotated": 0, "empty": 0, "by_class": {c: 0 for c in CLASS_NAMES}}

    for split_name, split_images in splits.items():
        logger.info(f"\nProcessing {split_name} set ({len(split_images)} images)...")

        for img_path in split_images:
            stats["total"] += 1

            # Auto-annotate
            annotations = auto_annotate_image(model, img_path, conf_threshold)

            if annotations:
                stats["annotated"] += 1
                for ann in annotations:
                    cls_id = ann[0]
                    if cls_id < len(CLASS_NAMES):
                        stats["by_class"][CLASS_NAMES[cls_id]] += 1
            else:
                stats["empty"] += 1

            # Copy image
            dst_img = output_dir / split_name / "images" / img_path.name
            shutil.copy2(img_path, dst_img)

            # Write annotation
            label_name = img_path.stem + ".txt"
            dst_label = output_dir / split_name / "labels" / label_name
            write_annotation(annotations, dst_label)

    # Create data.yaml
    data_yaml = {
        "path": str(output_dir.absolute()),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "names": {i: name for i, name in enumerate(CLASS_NAMES)},
        "nc": len(CLASS_NAMES),
    }

    yaml_path = output_dir / "data.yaml"
    import yaml
    with open(yaml_path, "w") as f:
        yaml.dump(data_yaml, f, default_flow_style=False)

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("DATASET PREPARATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Total images: {stats['total']}")
    logger.info(f"With annotations: {stats['annotated']}")
    logger.info(f"Empty (no detections): {stats['empty']}")
    logger.info(f"\nSplit sizes:")
    logger.info(f"  Train: {len(splits['train'])}")
    logger.info(f"  Val: {len(splits['val'])}")
    logger.info(f"  Test: {len(splits['test'])}")
    logger.info(f"\nDetections by class:")
    for cls_name, count in stats["by_class"].items():
        logger.info(f"  {cls_name}: {count}")
    logger.info(f"\nData config: {yaml_path}")
    logger.info("=" * 60)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Prepare YOLO detector dataset")
    parser.add_argument(
        "--input",
        type=str,
        default="training_images",
        help="Input directory with training images",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/detector",
        help="Output directory for dataset",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.8,
        help="Training set ratio",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.15,
        help="Validation set ratio",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Confidence threshold for auto-annotation",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n.pt",
        help="Pre-trained YOLO model to use",
    )

    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return

    prepare_dataset(
        input_dir=input_dir,
        output_dir=output_dir,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        conf_threshold=args.conf,
        model_name=args.model,
    )


if __name__ == "__main__":
    main()
