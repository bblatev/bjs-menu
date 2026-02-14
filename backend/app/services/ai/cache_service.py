"""Feature Cache Service for faster recognition.

This service manages the ProductFeatureCache table to store
aggregated feature vectors per product for faster recognition.
"""

import logging
import pickle
from app.core.safe_pickle import safe_loads
from typing import List, Optional, Dict, Tuple, Any
from datetime import datetime, timezone

import numpy as np
from sqlalchemy.orm import Session

from app.models.ai import TrainingImage, ProductFeatureCache
from app.models.product import Product

logger = logging.getLogger(__name__)


def update_product_cache(product_id: int, db: Session) -> Optional[ProductFeatureCache]:
    """Recompute and cache aggregated features for a product.

    This should be called after adding/removing training images.
    """
    # Get all training images for this product
    training_images = db.query(TrainingImage).filter(
        TrainingImage.stock_item_id == product_id
    ).all()

    if not training_images:
        # Remove cache entry if no training images
        db.query(ProductFeatureCache).filter(
            ProductFeatureCache.stock_item_id == product_id
        ).delete()
        db.commit()
        return None

    # Extract feature vectors
    vectors = []
    for img in training_images:
        if img.feature_vector:
            try:
                vec = safe_loads(img.feature_vector)
                vectors.append(vec)
            except Exception as e:
                logger.warning(f"Failed to load features for image {img.id}: {e}")

    if not vectors:
        return None

    # Compute aggregated features
    aggregated = _aggregate_features(vectors)

    # Get or create cache entry
    cache_entry = db.query(ProductFeatureCache).filter(
        ProductFeatureCache.stock_item_id == product_id
    ).first()

    if cache_entry:
        cache_entry.aggregated_features = pickle.dumps(aggregated)
        cache_entry.image_count = len(vectors)
        cache_entry.updated_at = datetime.now(timezone.utc)
    else:
        cache_entry = ProductFeatureCache(
            stock_item_id=product_id,
            aggregated_features=pickle.dumps(aggregated),
            image_count=len(vectors),
        )
        db.add(cache_entry)

    db.commit()
    db.refresh(cache_entry)

    logger.info(f"Updated cache for product {product_id} with {len(vectors)} images")
    return cache_entry


def _aggregate_features(vectors: List[np.ndarray]) -> np.ndarray:
    """Aggregate multiple feature vectors into one.

    Uses mean with outlier removal for robustness.
    """
    if not vectors:
        return np.zeros(1000, dtype=np.float32)

    # Ensure same length
    min_len = min(len(v) for v in vectors)
    vectors = [v[:min_len] for v in vectors]
    vectors = np.array(vectors)

    if len(vectors) == 1:
        result = vectors[0]
    else:
        # Compute mean
        mean_vector = np.mean(vectors, axis=0)

        # Remove outliers (vectors far from mean)
        if len(vectors) > 3:
            distances = np.linalg.norm(vectors - mean_vector, axis=1)
            threshold = np.percentile(distances, 75)
            inliers = vectors[distances <= threshold]

            if len(inliers) > 0:
                mean_vector = np.mean(inliers, axis=0)

        result = mean_vector

    # Normalize
    norm = np.linalg.norm(result)
    if norm > 1e-7:
        result = result / norm

    return result.astype(np.float32)


def get_all_cached_features(db: Session) -> List[Tuple[int, bytes]]:
    """Get all cached features for recognition.

    Returns list of (product_id, feature_bytes) tuples.
    """
    cache_entries = db.query(ProductFeatureCache).all()
    return [(entry.product_id, entry.aggregated_features) for entry in cache_entries]


def rebuild_all_caches(db: Session) -> Dict[str, int]:
    """Rebuild feature cache for all products with training images.

    Returns stats dict with counts.
    """
    # Get all products with training images
    product_ids = db.query(TrainingImage.stock_item_id).distinct().all()
    product_ids = [pid[0] for pid in product_ids]

    updated = 0
    failed = 0

    for product_id in product_ids:
        try:
            cache_entry = update_product_cache(product_id, db)
            if cache_entry:
                updated += 1
        except Exception as e:
            logger.error(f"Failed to update cache for product {product_id}: {e}")
            failed += 1

    return {
        "total_products": len(product_ids),
        "updated": updated,
        "failed": failed,
    }


def invalidate_cache(product_id: int, db: Session) -> bool:
    """Invalidate (delete) cache for a product.

    Call this when training images are modified.
    """
    result = db.query(ProductFeatureCache).filter(
        ProductFeatureCache.stock_item_id == product_id
    ).delete()
    db.commit()
    return result > 0


def get_cache_stats(db: Session) -> Dict[str, Any]:
    """Get cache statistics."""
    from sqlalchemy import func

    total_cached = db.query(func.count(ProductFeatureCache.id)).scalar() or 0
    total_images = db.query(func.sum(ProductFeatureCache.image_count)).scalar() or 0

    # Products with training images but no cache
    products_with_images = db.query(TrainingImage.stock_item_id).distinct().count()
    uncached = products_with_images - total_cached

    return {
        "total_cached_products": total_cached,
        "total_training_images": total_images,
        "uncached_products": uncached,
        "cache_coverage": total_cached / max(products_with_images, 1),
    }
