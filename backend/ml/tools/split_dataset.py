#!/usr/bin/env python3
"""
Split annotated dataset into train/val/test sets for YOLO training.
"""

import random
import shutil
from pathlib import Path
import yaml


def split_dataset(
    input_dir: Path,
    output_dir: Path,
    train_ratio: float = 0.8,
    val_ratio: float = 0.15,
):
    """Split dataset into train/val/test."""
    images_dir = input_dir / "images"
    labels_dir = input_dir / "labels"

    # Find all images with corresponding labels
    image_files = []
    for ext in [".jpg", ".jpeg", ".png"]:
        for img in images_dir.glob(f"*{ext}"):
            label = labels_dir / (img.stem + ".txt")
            if label.exists():
                image_files.append(img)

    print(f"Found {len(image_files)} annotated images")

    # Shuffle and split
    random.shuffle(image_files)
    n_train = int(len(image_files) * train_ratio)
    n_val = int(len(image_files) * val_ratio)

    splits = {
        "train": image_files[:n_train],
        "val": image_files[n_train:n_train + n_val],
        "test": image_files[n_train + n_val:],
    }

    # Create output directories and copy files
    for split_name, files in splits.items():
        split_images = output_dir / split_name / "images"
        split_labels = output_dir / split_name / "labels"
        split_images.mkdir(parents=True, exist_ok=True)
        split_labels.mkdir(parents=True, exist_ok=True)

        for img in files:
            shutil.copy2(img, split_images / img.name)
            label = labels_dir / (img.stem + ".txt")
            shutil.copy2(label, split_labels / (img.stem + ".txt"))

        print(f"  {split_name}: {len(files)} images")

    # Create data.yaml
    data_yaml = {
        "path": str(output_dir.absolute()),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "names": {
            0: "bottle",
            1: "glass",
            2: "cup",
            3: "can",
        },
        "nc": 4,
    }

    yaml_path = output_dir / "data.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(data_yaml, f, default_flow_style=False)

    print(f"\nDataset ready at: {output_dir}")
    print(f"Config: {yaml_path}")

    return splits


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="data/detector_annotated")
    parser.add_argument("--output", type=str, default="data/detector_final")
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.15)

    args = parser.parse_args()

    split_dataset(
        Path(args.input),
        Path(args.output),
        args.train_ratio,
        args.val_ratio,
    )


if __name__ == "__main__":
    main()
