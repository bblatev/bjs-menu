"""
Dataset Split Freezing Tool

Creates and freezes reproducible train/val/test splits.
Ensures consistent evaluation across experiments.

Usage:
    # Create new split
    python -m ml.tools.freeze_split data/all_images --output splits/v1.json --train 0.7 --val 0.15 --test 0.15

    # Apply existing split
    python -m ml.tools.freeze_split data/all_images --apply splits/v1.json --output-dir data/split_v1

    # Stratified split by class
    python -m ml.tools.freeze_split data/classifier --stratify --output splits/classifier_v1.json
"""

import argparse
import hashlib
import json
import logging
import os
import random
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_file_hash(filepath: Path) -> str:
    """Get short hash for a file (for reproducibility verification)."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        sha256.update(f.read(8192))  # Only hash first 8KB for speed
    return sha256.hexdigest()[:8]


def discover_images(
    data_dir: Path,
    extensions: Optional[List[str]] = None,
) -> List[Path]:
    """Discover all image files in directory."""
    if extensions is None:
        extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]

    files = []
    for ext in extensions:
        files.extend(data_dir.rglob(f"*{ext}"))
        files.extend(data_dir.rglob(f"*{ext.upper()}"))

    return sorted(set(files))


def discover_classes(data_dir: Path) -> Dict[str, List[Path]]:
    """
    Discover classes from directory structure.
    Assumes structure: data_dir/class_name/image.jpg
    """
    classes = defaultdict(list)

    for subdir in sorted(data_dir.iterdir()):
        if subdir.is_dir():
            class_name = subdir.name
            images = discover_images(subdir)
            if images:
                classes[class_name] = images

    return dict(classes)


def create_split(
    files: List[Path],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> Dict[str, List[Path]]:
    """
    Create random split of files.

    Args:
        files: List of file paths
        train_ratio: Fraction for training
        val_ratio: Fraction for validation
        test_ratio: Fraction for test
        seed: Random seed for reproducibility

    Returns:
        Dict with train/val/test file lists
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 0.01, "Ratios must sum to 1.0"

    # Shuffle with seed
    random.seed(seed)
    shuffled = files.copy()
    random.shuffle(shuffled)

    n = len(shuffled)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    return {
        "train": shuffled[:n_train],
        "val": shuffled[n_train:n_train + n_val],
        "test": shuffled[n_train + n_val:],
    }


def create_stratified_split(
    classes: Dict[str, List[Path]],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    min_samples_per_class: int = 3,
) -> Dict[str, Dict[str, List[Path]]]:
    """
    Create stratified split maintaining class distribution.

    Returns:
        Dict with train/val/test, each containing class -> files mapping
    """
    result = {
        "train": defaultdict(list),
        "val": defaultdict(list),
        "test": defaultdict(list),
    }

    for class_name, files in classes.items():
        if len(files) < min_samples_per_class:
            logger.warning(
                f"Class '{class_name}' has only {len(files)} samples, "
                f"minimum is {min_samples_per_class}. Skipping."
            )
            continue

        split = create_split(files, train_ratio, val_ratio, test_ratio, seed)

        for split_name, split_files in split.items():
            result[split_name][class_name] = split_files

    return {k: dict(v) for k, v in result.items()}


def freeze_split(
    data_dir: str,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    stratify: bool = False,
) -> Dict:
    """
    Create and freeze a dataset split.

    Returns:
        Split specification as dict
    """
    data_path = Path(data_dir)

    if stratify:
        classes = discover_classes(data_path)
        if not classes:
            raise ValueError(f"No class directories found in {data_dir}")

        split = create_stratified_split(classes, train_ratio, val_ratio, test_ratio, seed)

        # Convert to serializable format
        split_spec = {
            "type": "stratified",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "seed": seed,
            "ratios": {"train": train_ratio, "val": val_ratio, "test": test_ratio},
            "source_dir": str(data_path.absolute()),
            "classes": list(classes.keys()),
            "splits": {},
        }

        for split_name, class_files in split.items():
            split_spec["splits"][split_name] = {}
            for class_name, files in class_files.items():
                split_spec["splits"][split_name][class_name] = [
                    {
                        "path": str(f.relative_to(data_path)),
                        "hash": get_file_hash(f),
                    }
                    for f in files
                ]

        # Statistics
        split_spec["statistics"] = {
            "total_classes": len(classes),
            "total_files": sum(len(f) for f in classes.values()),
            "per_split": {
                name: sum(len(files) for files in class_files.values())
                for name, class_files in split.items()
            },
        }

    else:
        files = discover_images(data_path)
        if not files:
            raise ValueError(f"No images found in {data_dir}")

        split = create_split(files, train_ratio, val_ratio, test_ratio, seed)

        split_spec = {
            "type": "random",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "seed": seed,
            "ratios": {"train": train_ratio, "val": val_ratio, "test": test_ratio},
            "source_dir": str(data_path.absolute()),
            "splits": {},
        }

        for split_name, split_files in split.items():
            split_spec["splits"][split_name] = [
                {
                    "path": str(f.relative_to(data_path)),
                    "hash": get_file_hash(f),
                }
                for f in split_files
            ]

        split_spec["statistics"] = {
            "total_files": len(files),
            "per_split": {name: len(files) for name, files in split.items()},
        }

    return split_spec


def apply_split(
    split_spec: Dict,
    source_dir: str,
    output_dir: str,
    copy: bool = True,
    verify: bool = True,
) -> Dict[str, int]:
    """
    Apply a frozen split to create train/val/test directories.

    Args:
        split_spec: Split specification dict
        source_dir: Source data directory
        output_dir: Output directory for split data
        copy: If True, copy files. If False, create symlinks
        verify: Verify file hashes match

    Returns:
        Dict with counts per split
    """
    source_path = Path(source_dir)
    output_path = Path(output_dir)

    counts = {}

    if split_spec["type"] == "stratified":
        for split_name, class_files in split_spec["splits"].items():
            counts[split_name] = 0
            for class_name, files in class_files.items():
                dest_dir = output_path / split_name / class_name
                dest_dir.mkdir(parents=True, exist_ok=True)

                for file_info in files:
                    src = source_path / file_info["path"]

                    if verify:
                        actual_hash = get_file_hash(src)
                        if actual_hash != file_info["hash"]:
                            logger.warning(
                                f"Hash mismatch for {file_info['path']}: "
                                f"expected {file_info['hash']}, got {actual_hash}"
                            )

                    dest = dest_dir / src.name
                    if copy:
                        shutil.copy2(src, dest)
                    else:
                        if dest.exists():
                            dest.unlink()
                        dest.symlink_to(src.absolute())

                    counts[split_name] += 1

    else:
        for split_name, files in split_spec["splits"].items():
            dest_dir = output_path / split_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            counts[split_name] = 0

            for file_info in files:
                src = source_path / file_info["path"]

                if verify:
                    actual_hash = get_file_hash(src)
                    if actual_hash != file_info["hash"]:
                        logger.warning(
                            f"Hash mismatch for {file_info['path']}: "
                            f"expected {file_info['hash']}, got {actual_hash}"
                        )

                dest = dest_dir / src.name
                if copy:
                    shutil.copy2(src, dest)
                else:
                    if dest.exists():
                        dest.unlink()
                    dest.symlink_to(src.absolute())

                counts[split_name] += 1

    return counts


def main():
    parser = argparse.ArgumentParser(description="Create and apply dataset splits")
    parser.add_argument(
        "data_dir",
        type=str,
        help="Path to source data directory",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save split specification JSON",
    )
    parser.add_argument(
        "--apply",
        type=str,
        help="Path to split JSON to apply",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory when applying split",
    )
    parser.add_argument(
        "--train",
        type=float,
        default=0.7,
        help="Training set ratio (default: 0.7)",
    )
    parser.add_argument(
        "--val",
        type=float,
        default=0.15,
        help="Validation set ratio (default: 0.15)",
    )
    parser.add_argument(
        "--test",
        type=float,
        default=0.15,
        help="Test set ratio (default: 0.15)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--stratify",
        action="store_true",
        help="Create stratified split (requires class subdirectories)",
    )
    parser.add_argument(
        "--symlink",
        action="store_true",
        help="Create symlinks instead of copying files",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip hash verification when applying",
    )

    args = parser.parse_args()

    if args.apply:
        # Apply existing split
        if not args.output_dir:
            parser.error("--output-dir required when using --apply")

        with open(args.apply) as f:
            split_spec = json.load(f)

        logger.info(f"Applying split from {args.apply}")
        counts = apply_split(
            split_spec,
            args.data_dir,
            args.output_dir,
            copy=not args.symlink,
            verify=not args.no_verify,
        )

        print("\nApplied split:")
        for split_name, count in counts.items():
            print(f"  {split_name}: {count} files")

    else:
        # Create new split
        logger.info(f"Creating split for {args.data_dir}")
        split_spec = freeze_split(
            args.data_dir,
            train_ratio=args.train,
            val_ratio=args.val,
            test_ratio=args.test,
            seed=args.seed,
            stratify=args.stratify,
        )

        print("\n" + "=" * 60)
        print("SPLIT CREATED")
        print("=" * 60)
        print(f"Type: {split_spec['type']}")
        print(f"Seed: {split_spec['seed']}")
        print(f"Ratios: train={args.train}, val={args.val}, test={args.test}")
        print(f"\nStatistics:")
        for key, value in split_spec["statistics"].items():
            print(f"  {key}: {value}")

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(split_spec, f, indent=2)
            logger.info(f"Saved split to: {args.output}")
        else:
            print("\nUse --output to save split specification")


if __name__ == "__main__":
    main()
