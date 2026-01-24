"""
Export CLIP embeddings from database for V2 classifier.

Reads existing training features from the database and exports them
in the format expected by the V2 pipeline.

Usage:
    python -m ml.tools.export_db_embeddings --output-dir models/classifier
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_embeddings(output_dir: str, min_images: int = 1):
    """
    Export CLIP embeddings from database.

    Args:
        output_dir: Directory to save embeddings
        min_images: Minimum images per product to include
    """
    from sqlalchemy import create_engine, text
    from app.core.config import settings

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        # Get all products with training images
        result = conn.execute(text("""
            SELECT
                ti.stock_item_id,
                si.name as product_name,
                si.sku,
                ti.feature_vector
            FROM training_images ti
            JOIN stock_items si ON ti.stock_item_id = si.id
            WHERE ti.feature_vector IS NOT NULL
              AND length(ti.feature_vector) = 2048
            ORDER BY ti.stock_item_id
        """))

        # Group features by product
        product_features = {}
        product_names = {}

        for row in result:
            product_id = row[0]
            product_name = row[1]
            sku = row[2]
            feature_bytes = row[3]

            # Create unique key
            key = f"{product_id}_{sku or product_name}".replace(" ", "_").replace("/", "_")

            if key not in product_features:
                product_features[key] = []
                product_names[key] = {
                    "id": product_id,
                    "name": product_name,
                    "sku": sku,
                }

            # Convert bytes to numpy array
            try:
                embedding = np.frombuffer(feature_bytes, dtype=np.float32)
                if len(embedding) == 512:  # Valid CLIP embedding
                    product_features[key].append(embedding)
            except Exception as e:
                logger.warning(f"Failed to parse embedding for product {product_id}: {e}")

    # Filter by minimum images
    filtered = {
        k: v for k, v in product_features.items()
        if len(v) >= min_images
    }

    logger.info(f"Found {len(filtered)} products with >= {min_images} images")

    # Compute mean embedding per product
    embeddings_dict = {}
    for key, features in filtered.items():
        if features:
            # Average all embeddings for this product
            mean_embedding = np.mean(features, axis=0)
            # Normalize
            mean_embedding = mean_embedding / (np.linalg.norm(mean_embedding) + 1e-7)
            embeddings_dict[key] = mean_embedding

            logger.info(f"  {key}: {len(features)} images -> embedding shape {mean_embedding.shape}")

    # Save embeddings
    embeddings_path = output_path / "embeddings.npy"
    np.save(embeddings_path, embeddings_dict)
    logger.info(f"Saved embeddings to {embeddings_path}")

    # Save SKU mapping
    sku_mapping = {
        k: product_names[k] for k in embeddings_dict.keys()
    }
    mapping_path = output_path / "sku_mapping.json"
    with open(mapping_path, "w") as f:
        json.dump(sku_mapping, f, indent=2)
    logger.info(f"Saved SKU mapping to {mapping_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("EXPORT SUMMARY")
    print("=" * 60)
    print(f"Total products exported: {len(embeddings_dict)}")
    print(f"Embedding dimension: 512 (CLIP)")
    print(f"\nProducts:")
    for key, info in sku_mapping.items():
        count = len(product_features.get(key, []))
        print(f"  {key}: {info['name']} ({count} images)")

    return {
        "embeddings_path": str(embeddings_path),
        "mapping_path": str(mapping_path),
        "num_products": len(embeddings_dict),
    }


def main():
    parser = argparse.ArgumentParser(description="Export DB embeddings for V2 classifier")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models/classifier",
        help="Output directory for embeddings",
    )
    parser.add_argument(
        "--min-images",
        type=int,
        default=1,
        help="Minimum images per product",
    )

    args = parser.parse_args()
    export_embeddings(args.output_dir, args.min_images)


if __name__ == "__main__":
    main()
