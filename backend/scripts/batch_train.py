#!/usr/bin/env python3
"""
Batch Training Script - Import training images and extract CLIP features.

Usage:
    python scripts/batch_train.py --folder /path/to/images --product-id 5
    python scripts/batch_train.py --folder /path/to/images --product-name "Savoy Club Gin"
    python scripts/batch_train.py --auto /path/to/organized/folder

For --auto mode, organize images in folders by product ID:
    /path/to/folder/
        5/          <- product_id
            img1.jpg
            img2.jpg
        6/
            img1.jpg
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from PIL import Image, ImageOps
import io


def get_db_connection():
    """Get SQLite connection to bjsbar.db"""
    import sqlite3
    db_path = Path(__file__).parent.parent.parent.parent / "backend" / "bjsbar.db"
    if not db_path.exists():
        # Try alternate path
        db_path = Path("/Users/zver/Downloads/V99/backend/bjsbar.db")
    return sqlite3.connect(str(db_path))


def get_clip_embedding(image_data: bytes) -> np.ndarray:
    """Extract CLIP embedding from image bytes."""
    try:
        import torch
        import clip
        from PIL import Image
        import io

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)

        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        image_input = preprocess(image).unsqueeze(0).to(device)

        with torch.no_grad():
            image_features = model.encode_image(image_input)
            image_features = image_features.cpu().numpy().flatten()

        return image_features
    except ImportError:
        print("ERROR: CLIP not installed. Run: pip install git+https://github.com/openai/CLIP.git")
        sys.exit(1)


def process_image(image_path: Path) -> tuple:
    """Load and preprocess image, return (image_bytes, width, height)."""
    img = Image.open(image_path)

    # Apply EXIF orientation
    img = ImageOps.exif_transpose(img)

    # Convert to RGB if needed
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Save to bytes
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    image_bytes = buffer.getvalue()

    return image_bytes, img.width, img.height


def import_images_for_product(conn, product_id: int, image_folder: Path, verbose: bool = True):
    """Import all images from folder for a specific product."""
    cursor = conn.cursor()

    # Verify product exists
    cursor.execute("SELECT name FROM stock_items WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    if not row:
        print(f"ERROR: Product ID {product_id} not found")
        return 0

    product_name = row[0]
    if verbose:
        print(f"Training product: {product_name} (ID: {product_id})")

    # Find image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.webp'}
    image_files = [f for f in image_folder.iterdir()
                   if f.is_file() and f.suffix.lower() in image_extensions]

    if not image_files:
        print(f"  No images found in {image_folder}")
        return 0

    if verbose:
        print(f"  Found {len(image_files)} images")

    imported = 0
    for img_path in image_files:
        try:
            # Process image
            image_bytes, width, height = process_image(img_path)

            # Extract CLIP embedding
            embedding = get_clip_embedding(image_bytes)
            embedding = embedding / (np.linalg.norm(embedding) + 1e-7)  # Normalize
            feature_bytes = embedding.astype(np.float32).tobytes()

            # Verify it's 2048 bytes (512 float32)
            if len(feature_bytes) != 2048:
                print(f"  WARNING: {img_path.name} - invalid feature size {len(feature_bytes)}")
                continue

            # Insert into database
            cursor.execute("""
                INSERT INTO training_images
                (stock_item_id, storage_path, feature_vector, confidence, is_verified, image_width, image_height)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (product_id, 'batch_import', feature_bytes, 1.0, True, width, height))

            imported += 1
            if verbose:
                print(f"  ✓ {img_path.name}")

        except Exception as e:
            print(f"  ✗ {img_path.name}: {e}")

    conn.commit()
    if verbose:
        print(f"  Imported {imported}/{len(image_files)} images")

    return imported


def auto_import(conn, base_folder: Path, verbose: bool = True):
    """Auto-import from folder structure organized by product ID."""
    total_imported = 0

    for item in base_folder.iterdir():
        if item.is_dir() and item.name.isdigit():
            product_id = int(item.name)
            imported = import_images_for_product(conn, product_id, item, verbose)
            total_imported += imported

    return total_imported


def list_products_needing_training(conn):
    """List products that need more training."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT si.id, si.name,
               SUM(CASE WHEN LENGTH(ti.feature_vector) = 2048 THEN 1 ELSE 0 END) as clip_count,
               SUM(CASE WHEN LENGTH(ti.feature_vector) <> 2048 THEN 1 ELSE 0 END) as old_count
        FROM stock_items si
        LEFT JOIN training_images ti ON si.id = ti.stock_item_id
        WHERE si.is_active = 1
        GROUP BY si.id
        HAVING clip_count < 10
        ORDER BY clip_count ASC, old_count DESC
    """)

    print("\nProducts needing training (< 10 CLIP images):")
    print("-" * 60)
    print(f"{'ID':<5} {'Name':<35} {'CLIP':<6} {'Old':<6}")
    print("-" * 60)

    for row in cursor.fetchall():
        pid, name, clip_count, old_count = row
        clip_count = clip_count or 0
        old_count = old_count or 0
        status = "⚠️ " if clip_count == 0 else "  "
        print(f"{status}{pid:<5} {name[:33]:<35} {clip_count:<6} {old_count:<6}")


def main():
    parser = argparse.ArgumentParser(description="Batch import training images with CLIP features")
    parser.add_argument('--folder', type=Path, help="Folder containing images")
    parser.add_argument('--product-id', type=int, help="Product ID to train")
    parser.add_argument('--product-name', type=str, help="Product name to train (fuzzy match)")
    parser.add_argument('--auto', type=Path, help="Auto-import from folder organized by product ID")
    parser.add_argument('--list', action='store_true', help="List products needing training")
    parser.add_argument('--quiet', action='store_true', help="Less verbose output")

    args = parser.parse_args()

    conn = get_db_connection()

    if args.list:
        list_products_needing_training(conn)
        return

    if args.auto:
        if not args.auto.exists():
            print(f"ERROR: Folder not found: {args.auto}")
            return
        imported = auto_import(conn, args.auto, verbose=not args.quiet)
        print(f"\nTotal imported: {imported} images")
        return

    if args.folder and (args.product_id or args.product_name):
        if not args.folder.exists():
            print(f"ERROR: Folder not found: {args.folder}")
            return

        product_id = args.product_id
        if args.product_name and not product_id:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM stock_items WHERE name LIKE ? AND is_active = 1",
                (f"%{args.product_name}%",)
            )
            row = cursor.fetchone()
            if row:
                product_id = row[0]
            else:
                print(f"ERROR: Product not found: {args.product_name}")
                return

        imported = import_images_for_product(conn, product_id, args.folder, verbose=not args.quiet)
        print(f"\nImported: {imported} images")
        return

    parser.print_help()
    print("\n\nExamples:")
    print("  python scripts/batch_train.py --list")
    print("  python scripts/batch_train.py --folder ./photos --product-id 5")
    print("  python scripts/batch_train.py --auto ./training_data/")


if __name__ == "__main__":
    main()
