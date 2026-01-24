#!/usr/bin/env python3
"""
Auto-annotate full-frame product images.

For close-up product shots where the bottle/can fills the entire frame,
creates a full-frame bounding box annotation.

Also merges with existing auto-detected annotations.
"""

import json
import shutil
from pathlib import Path
from PIL import Image

# Class definitions
CLASSES = ["bottle", "glass", "cup", "can"]


def create_fullframe_annotation(image_path: Path, class_id: int = 0, margin: float = 0.02):
    """
    Create a full-frame annotation for an image.

    Args:
        image_path: Path to image
        class_id: Class ID (0=bottle, 1=glass, 2=cup, 3=can)
        margin: Margin from edges (as fraction of image size)

    Returns:
        YOLO format annotation string
    """
    # Get image dimensions
    with Image.open(image_path) as img:
        width, height = img.size

    # Create bbox with small margin
    x_center = 0.5
    y_center = 0.5
    box_width = 1.0 - (2 * margin)
    box_height = 1.0 - (2 * margin)

    return f"{class_id} {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}"


def process_images(
    input_dir: Path,
    output_dir: Path,
    auto_annotations_dir: Path = None,
):
    """
    Process images and create annotations.

    - Uses auto-detected annotations if available
    - Creates full-frame annotations for images without detections
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    labels_dir = output_dir / "labels"
    images_dir.mkdir(exist_ok=True)
    labels_dir.mkdir(exist_ok=True)

    # Find all images
    image_files = []
    for ext in [".jpg", ".jpeg", ".png"]:
        image_files.extend(input_dir.glob(f"*{ext}"))
        image_files.extend(input_dir.glob(f"*{ext.upper()}"))

    print(f"Found {len(image_files)} images")

    stats = {"total": 0, "auto": 0, "fullframe": 0}

    for img_path in image_files:
        stats["total"] += 1

        # Check for existing auto-annotation
        auto_ann_path = None
        if auto_annotations_dir:
            auto_ann_path = auto_annotations_dir / (img_path.stem + ".txt")

        # Copy image
        dst_img = images_dir / img_path.name
        shutil.copy2(img_path, dst_img)

        # Create annotation
        dst_label = labels_dir / (img_path.stem + ".txt")

        if auto_ann_path and auto_ann_path.exists():
            # Check if auto-annotation has content
            with open(auto_ann_path) as f:
                content = f.read().strip()

            if content:
                # Use auto-detected annotation
                with open(dst_label, "w") as f:
                    f.write(content)
                stats["auto"] += 1
                print(f"  {img_path.name}: Using auto-detected annotation")
                continue

        # Create full-frame annotation
        annotation = create_fullframe_annotation(img_path, class_id=0)  # Default to bottle
        with open(dst_label, "w") as f:
            f.write(annotation + "\n")
        stats["fullframe"] += 1
        print(f"  {img_path.name}: Created full-frame annotation")

    print(f"\nProcessed {stats['total']} images:")
    print(f"  Auto-detected: {stats['auto']}")
    print(f"  Full-frame: {stats['fullframe']}")

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="data/yolo_training_prep")
    parser.add_argument("--output", type=str, default="data/detector_annotated")
    parser.add_argument("--auto-dir", type=str, default="data/detector/train/labels")

    args = parser.parse_args()

    process_images(
        Path(args.input),
        Path(args.output),
        Path(args.auto_dir) if args.auto_dir else None,
    )


if __name__ == "__main__":
    main()
