"""
Dataset Hashing Tool

Creates a reproducible hash of a dataset for versioning.
Ensures training reproducibility by tracking exact data used.

Usage:
    python -m ml.tools.hash_dataset data/classifier/train
    python -m ml.tools.hash_dataset data/detector --output versions/detector_v1.json
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def hash_file(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def hash_dataset(
    data_dir: str,
    extensions: Optional[List[str]] = None,
    include_annotations: bool = True,
) -> Dict:
    """
    Hash all files in a dataset directory.

    Args:
        data_dir: Path to dataset directory
        extensions: File extensions to include (default: images + json)
        include_annotations: Whether to include annotation files

    Returns:
        Dict with dataset metadata and hashes
    """
    data_path = Path(data_dir)

    if not data_path.exists():
        raise ValueError(f"Dataset directory not found: {data_dir}")

    if extensions is None:
        extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
        if include_annotations:
            extensions.extend([".json", ".txt", ".xml", ".yaml"])

    # Collect all files
    files = []
    for ext in extensions:
        files.extend(data_path.rglob(f"*{ext}"))

    files = sorted(files)

    logger.info(f"Found {len(files)} files in {data_dir}")

    # Compute individual hashes
    file_hashes = {}
    for filepath in files:
        rel_path = filepath.relative_to(data_path)
        file_hashes[str(rel_path)] = hash_file(filepath)

    # Compute combined hash
    combined = hashlib.sha256()
    for path in sorted(file_hashes.keys()):
        combined.update(path.encode())
        combined.update(file_hashes[path].encode())

    dataset_hash = combined.hexdigest()

    # Gather statistics
    stats = {
        "total_files": len(files),
        "by_extension": {},
        "by_directory": {},
    }

    for filepath in files:
        ext = filepath.suffix.lower()
        stats["by_extension"][ext] = stats["by_extension"].get(ext, 0) + 1

        parent = filepath.parent.relative_to(data_path)
        parent_str = str(parent) if str(parent) != "." else "root"
        stats["by_directory"][parent_str] = stats["by_directory"].get(parent_str, 0) + 1

    result = {
        "dataset_hash": dataset_hash,
        "dataset_path": str(data_path.absolute()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "statistics": stats,
        "file_hashes": file_hashes,
    }

    return result


def compare_datasets(hash1: Dict, hash2: Dict) -> Dict:
    """
    Compare two dataset hashes.

    Returns:
        Dict with added, removed, and modified files
    """
    files1 = set(hash1.get("file_hashes", {}).keys())
    files2 = set(hash2.get("file_hashes", {}).keys())

    added = files2 - files1
    removed = files1 - files2
    common = files1 & files2

    modified = set()
    for path in common:
        if hash1["file_hashes"][path] != hash2["file_hashes"][path]:
            modified.add(path)

    return {
        "datasets_identical": len(added) == 0 and len(removed) == 0 and len(modified) == 0,
        "hash1": hash1.get("dataset_hash"),
        "hash2": hash2.get("dataset_hash"),
        "added": sorted(added),
        "removed": sorted(removed),
        "modified": sorted(modified),
        "unchanged": len(common) - len(modified),
    }


def main():
    parser = argparse.ArgumentParser(description="Hash dataset for versioning")
    parser.add_argument(
        "data_dir",
        type=str,
        help="Path to dataset directory",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save hash JSON (default: print to stdout)",
    )
    parser.add_argument(
        "--compare",
        type=str,
        help="Path to another hash JSON to compare against",
    )
    parser.add_argument(
        "--no-file-hashes",
        action="store_true",
        help="Exclude individual file hashes from output",
    )

    args = parser.parse_args()

    result = hash_dataset(args.data_dir)

    # Optionally compare
    if args.compare:
        with open(args.compare) as f:
            other = json.load(f)
        comparison = compare_datasets(other, result)

        print("\n" + "=" * 60)
        print("DATASET COMPARISON")
        print("=" * 60)
        print(f"Previous hash: {comparison['hash1'][:16]}...")
        print(f"Current hash:  {comparison['hash2'][:16]}...")
        print(f"Identical: {comparison['datasets_identical']}")
        print(f"Added:     {len(comparison['added'])} files")
        print(f"Removed:   {len(comparison['removed'])} files")
        print(f"Modified:  {len(comparison['modified'])} files")
        print(f"Unchanged: {comparison['unchanged']} files")

        if comparison["added"]:
            print("\nAdded files:")
            for f in comparison["added"][:10]:
                print(f"  + {f}")
            if len(comparison["added"]) > 10:
                print(f"  ... and {len(comparison['added']) - 10} more")

        if comparison["modified"]:
            print("\nModified files:")
            for f in comparison["modified"][:10]:
                print(f"  ~ {f}")
            if len(comparison["modified"]) > 10:
                print(f"  ... and {len(comparison['modified']) - 10} more")

    # Remove file hashes if requested
    if args.no_file_hashes:
        del result["file_hashes"]

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Saved dataset hash to: {args.output}")
        print(f"Dataset hash: {result['dataset_hash'][:16]}...")
    else:
        if not args.compare:
            print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
