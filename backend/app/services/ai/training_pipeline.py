"""ML Training Pipeline Service.

Provides:
- Data augmentation for training images
- Per-product feature aggregation
- Live accuracy metrics tracking
- Model versioning
"""

import hashlib
import io
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import random

import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai import TrainingImage, ProductFeatureCache, RecognitionLog
from app.models.product import Product

logger = logging.getLogger(__name__)

# Feature vector size for CLIP (openai/clip-vit-base-patch32)
CLIP_FEATURE_SIZE = 512
CLIP_FEATURE_BYTES = CLIP_FEATURE_SIZE * 4  # float32 = 4 bytes = 2048 bytes


class DataAugmentation:
    """Apply data augmentation to training images."""

    def __init__(
        self,
        rotation_range: int = 15,
        brightness_range: Tuple[float, float] = (0.8, 1.2),
        contrast_range: Tuple[float, float] = (0.8, 1.2),
        saturation_range: Tuple[float, float] = (0.8, 1.2),
        flip_horizontal: bool = True,
        blur_probability: float = 0.1,
        noise_probability: float = 0.1,
    ):
        self.rotation_range = rotation_range
        self.brightness_range = brightness_range
        self.contrast_range = contrast_range
        self.saturation_range = saturation_range
        self.flip_horizontal = flip_horizontal
        self.blur_probability = blur_probability
        self.noise_probability = noise_probability

    def augment(self, image: Image.Image, num_augmentations: int = 5) -> List[Image.Image]:
        """Generate augmented versions of an image."""
        augmented = []

        for _ in range(num_augmentations):
            img = image.copy()

            # Random rotation
            if self.rotation_range > 0:
                angle = random.uniform(-self.rotation_range, self.rotation_range)
                img = img.rotate(angle, expand=False, fillcolor=(255, 255, 255))

            # Random horizontal flip
            if self.flip_horizontal and random.random() > 0.5:
                img = ImageOps.mirror(img)

            # Random brightness
            brightness_factor = random.uniform(*self.brightness_range)
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness_factor)

            # Random contrast
            contrast_factor = random.uniform(*self.contrast_range)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast_factor)

            # Random saturation
            saturation_factor = random.uniform(*self.saturation_range)
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(saturation_factor)

            # Random blur
            if random.random() < self.blur_probability:
                img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))

            # Random noise (simulated by reducing quality slightly)
            if random.random() < self.noise_probability:
                # Add noise by saving as JPEG with low quality
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=random.randint(70, 90))
                buffer.seek(0)
                img = Image.open(buffer)

            augmented.append(img)

        return augmented

    def augment_bytes(self, image_bytes: bytes, num_augmentations: int = 5) -> List[bytes]:
        """Augment image from bytes and return list of augmented bytes."""
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        augmented_images = self.augment(image, num_augmentations)

        results = []
        for img in augmented_images:
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            results.append(buffer.getvalue())

        return results


class FeatureAggregator:
    """Aggregate features per product for faster recognition."""

    def __init__(self, db: Session):
        self.db = db

    def compute_product_features(
        self,
        product_id: int,
        feature_version: str = "v2",
    ) -> Optional[np.ndarray]:
        """
        Compute aggregated feature vector for a product.

        Uses average of all training image features.
        """
        # Get all training images with valid CLIP features
        images = (
            self.db.query(TrainingImage)
            .filter(
                TrainingImage.stock_item_id == product_id,
                TrainingImage.feature_vector.isnot(None),
                func.length(TrainingImage.feature_vector) == CLIP_FEATURE_BYTES,
            )
            .all()
        )

        if not images:
            logger.warning(f"No valid features found for product {product_id}")
            return None

        # Stack all feature vectors
        features = []
        for img in images:
            try:
                feat = np.frombuffer(img.feature_vector, dtype=np.float32)
                if len(feat) == CLIP_FEATURE_SIZE:
                    # Normalize
                    feat = feat / (np.linalg.norm(feat) + 1e-7)
                    features.append(feat)
            except Exception as e:
                logger.warning(f"Error processing features for image {img.id}: {e}")

        if not features:
            return None

        # Average all features
        aggregated = np.mean(features, axis=0)

        # Normalize the aggregated vector
        aggregated = aggregated / (np.linalg.norm(aggregated) + 1e-7)

        return aggregated.astype(np.float32)

    def update_product_cache(
        self,
        product_id: int,
        feature_version: str = "v2",
    ) -> Optional[ProductFeatureCache]:
        """Update the feature cache for a product."""
        aggregated = self.compute_product_features(product_id, feature_version)

        if aggregated is None:
            return None

        # Count images
        image_count = (
            self.db.query(func.count(TrainingImage.id))
            .filter(
                TrainingImage.stock_item_id == product_id,
                TrainingImage.feature_vector.isnot(None),
                func.length(TrainingImage.feature_vector) == CLIP_FEATURE_BYTES,
            )
            .scalar()
        )

        # Get or create cache entry
        cache = (
            self.db.query(ProductFeatureCache)
            .filter(ProductFeatureCache.stock_item_id == product_id)
            .first()
        )

        if cache:
            cache.aggregated_features = aggregated.tobytes()
            cache.image_count = image_count
            cache.feature_version = feature_version
            cache.updated_at = datetime.utcnow()
        else:
            cache = ProductFeatureCache(
                stock_item_id=product_id,
                aggregated_features=aggregated.tobytes(),
                image_count=image_count,
                feature_version=feature_version,
            )
            self.db.add(cache)

        self.db.flush()
        return cache

    def update_all_products(
        self,
        feature_version: str = "v2",
    ) -> Dict:
        """Update feature cache for all products with training images."""
        # Get products with training images
        product_ids = (
            self.db.query(TrainingImage.stock_item_id)
            .filter(
                TrainingImage.feature_vector.isnot(None),
                func.length(TrainingImage.feature_vector) == CLIP_FEATURE_BYTES,
            )
            .distinct()
            .all()
        )
        product_ids = [p[0] for p in product_ids]

        updated = 0
        failed = 0

        for product_id in product_ids:
            try:
                result = self.update_product_cache(product_id, feature_version)
                if result:
                    updated += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to update cache for product {product_id}: {e}")
                failed += 1

        self.db.commit()

        return {
            "total_products": len(product_ids),
            "updated": updated,
            "failed": failed,
        }


class AccuracyTracker:
    """Track recognition accuracy metrics."""

    def __init__(self, db: Session):
        self.db = db

    def log_recognition(
        self,
        matched_product_id: Optional[int],
        confidence: float,
        is_match: bool,
        inference_time_ms: Optional[float] = None,
        top_5_results: Optional[List[Dict]] = None,
        image_hash: Optional[str] = None,
        source: str = "api",
        user_id: Optional[int] = None,
    ) -> RecognitionLog:
        """Log a recognition attempt for metrics."""
        log = RecognitionLog(
            matched_product_id=matched_product_id,
            confidence=confidence,
            is_match=is_match,
            inference_time_ms=inference_time_ms,
            top_5_results=json.dumps(top_5_results) if top_5_results else None,
            image_hash=image_hash,
            source=source,
            user_id=user_id,
        )
        self.db.add(log)
        self.db.flush()
        return log

    def record_user_feedback(
        self,
        log_id: int,
        confirmed: bool,
        correction_product_id: Optional[int] = None,
    ):
        """Record user feedback on a recognition result."""
        log = self.db.query(RecognitionLog).filter(RecognitionLog.id == log_id).first()
        if log:
            log.user_confirmed = confirmed
            log.user_correction_id = correction_product_id
            self.db.flush()

    def get_accuracy_metrics(
        self,
        days: int = 30,
        source: Optional[str] = None,
    ) -> Dict:
        """Calculate accuracy metrics for recent recognitions."""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(RecognitionLog).filter(
            RecognitionLog.created_at >= start_date,
            RecognitionLog.user_confirmed.isnot(None),  # Only confirmed results
        )

        if source:
            query = query.filter(RecognitionLog.source == source)

        logs = query.all()

        if not logs:
            return {
                "period_days": days,
                "total_confirmed": 0,
                "accuracy": None,
                "avg_confidence": None,
                "avg_inference_time_ms": None,
            }

        # Calculate metrics
        total = len(logs)
        correct = sum(1 for log in logs if log.user_confirmed)
        confidences = [log.confidence for log in logs if log.confidence]
        inference_times = [log.inference_time_ms for log in logs if log.inference_time_ms]

        return {
            "period_days": days,
            "total_confirmed": total,
            "correct": correct,
            "incorrect": total - correct,
            "accuracy": round(correct / total * 100, 2) if total > 0 else None,
            "avg_confidence": round(sum(confidences) / len(confidences), 4) if confidences else None,
            "avg_inference_time_ms": round(sum(inference_times) / len(inference_times), 2) if inference_times else None,
        }

    def get_product_accuracy(
        self,
        product_id: int,
        days: int = 30,
    ) -> Dict:
        """Get accuracy metrics for a specific product."""
        start_date = datetime.utcnow() - timedelta(days=days)

        logs = (
            self.db.query(RecognitionLog)
            .filter(
                RecognitionLog.created_at >= start_date,
                RecognitionLog.matched_product_id == product_id,
                RecognitionLog.user_confirmed.isnot(None),
            )
            .all()
        )

        if not logs:
            return {
                "product_id": product_id,
                "total_recognitions": 0,
                "accuracy": None,
            }

        total = len(logs)
        correct = sum(1 for log in logs if log.user_confirmed)

        return {
            "product_id": product_id,
            "total_recognitions": total,
            "correct": correct,
            "incorrect": total - correct,
            "accuracy": round(correct / total * 100, 2),
        }

    def get_confusion_matrix(
        self,
        days: int = 30,
        min_samples: int = 5,
    ) -> Dict:
        """Get products that are frequently confused with each other."""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get logs where user provided a correction
        logs = (
            self.db.query(RecognitionLog)
            .filter(
                RecognitionLog.created_at >= start_date,
                RecognitionLog.user_confirmed == False,
                RecognitionLog.user_correction_id.isnot(None),
            )
            .all()
        )

        if not logs:
            return {"confusions": []}

        # Count confusions
        confusion_counts = {}
        for log in logs:
            key = (log.matched_product_id, log.user_correction_id)
            confusion_counts[key] = confusion_counts.get(key, 0) + 1

        # Get product names
        product_ids = set()
        for pred, actual in confusion_counts.keys():
            if pred:
                product_ids.add(pred)
            if actual:
                product_ids.add(actual)

        products = {
            p.id: p.name
            for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()
        }

        # Format results
        confusions = []
        for (pred, actual), count in sorted(
            confusion_counts.items(), key=lambda x: -x[1]
        ):
            if count >= min_samples:
                confusions.append({
                    "predicted_id": pred,
                    "predicted_name": products.get(pred, "Unknown"),
                    "actual_id": actual,
                    "actual_name": products.get(actual, "Unknown"),
                    "count": count,
                })

        return {"confusions": confusions}


class TrainingPipeline:
    """Main training pipeline coordinator."""

    def __init__(self, db: Session):
        self.db = db
        self.augmenter = DataAugmentation()
        self.aggregator = FeatureAggregator(db)
        self.tracker = AccuracyTracker(db)

    def compute_image_hash(self, image_bytes: bytes) -> str:
        """Compute MD5 hash of image for deduplication."""
        return hashlib.md5(image_bytes).hexdigest()

    def is_duplicate_image(self, image_hash: str) -> bool:
        """Check if image already exists in training set."""
        existing = (
            self.db.query(TrainingImage)
            .filter(TrainingImage.image_hash == image_hash)
            .first()
        )
        return existing is not None

    def extract_and_store_features(
        self,
        training_image_id: int,
        include_augmented: bool = True,
        num_augmentations: int = 3,
    ) -> bool:
        """
        Extract features for a training image and optionally augmented versions.
        """
        from app.services.ai.clip_service import get_clip_embedding, is_clip_available

        if not is_clip_available():
            logger.error("CLIP not available for feature extraction")
            return False

        image = self.db.query(TrainingImage).filter(
            TrainingImage.id == training_image_id
        ).first()

        if not image or not image.image_path:
            return False

        try:
            # Read image file
            image_path = Path(image.image_path)
            if not image_path.exists():
                logger.error(f"Image file not found: {image_path}")
                return False

            with open(image_path, 'rb') as f:
                image_bytes = f.read()

            # Get image dimensions
            img = Image.open(io.BytesIO(image_bytes))
            image.image_width = img.width
            image.image_height = img.height

            # Compute hash
            image.image_hash = self.compute_image_hash(image_bytes)

            # Extract main features
            features = get_clip_embedding(image_bytes)
            if features is not None:
                image.feature_vector = features.tobytes()
                image.feature_version = "v2"
            else:
                image.extraction_error = "Failed to extract features"
                self.db.flush()
                return False

            # Extract augmented features
            if include_augmented and num_augmentations > 0:
                augmented_images = self.augmenter.augment_bytes(image_bytes, num_augmentations)
                augmented_features = []

                for aug_bytes in augmented_images:
                    aug_feat = get_clip_embedding(aug_bytes)
                    if aug_feat is not None:
                        # Normalize
                        aug_feat = aug_feat / (np.linalg.norm(aug_feat) + 1e-7)
                        augmented_features.append(aug_feat)

                if augmented_features:
                    # Store concatenated augmented features
                    stacked = np.stack(augmented_features)
                    image.augmented_features = stacked.tobytes()

            image.updated_at = datetime.utcnow()
            image.extraction_error = None
            self.db.flush()

            return True

        except Exception as e:
            logger.error(f"Feature extraction failed for image {training_image_id}: {e}")
            image.extraction_error = str(e)
            self.db.flush()
            return False

    def retrain_product(
        self,
        product_id: int,
        extract_new_features: bool = True,
    ) -> Dict:
        """
        Retrain features for a specific product.

        1. Extract features for any images without them
        2. Update the aggregated product cache
        """
        results = {
            "product_id": product_id,
            "images_processed": 0,
            "features_extracted": 0,
            "cache_updated": False,
        }

        # Get training images for product
        images = (
            self.db.query(TrainingImage)
            .filter(TrainingImage.stock_item_id == product_id)
            .all()
        )

        results["total_images"] = len(images)

        if extract_new_features:
            for image in images:
                # Check if needs feature extraction
                needs_extraction = (
                    image.feature_vector is None or
                    len(image.feature_vector) != CLIP_FEATURE_BYTES
                )

                if needs_extraction:
                    results["images_processed"] += 1
                    if self.extract_and_store_features(image.id):
                        results["features_extracted"] += 1

        # Update aggregated cache
        cache = self.aggregator.update_product_cache(product_id)
        results["cache_updated"] = cache is not None
        if cache:
            results["aggregated_image_count"] = cache.image_count

        self.db.commit()
        return results

    def retrain_all(
        self,
        extract_new_features: bool = True,
    ) -> Dict:
        """Retrain features for all products."""
        # Get all products with training images
        product_ids = (
            self.db.query(TrainingImage.stock_item_id)
            .distinct()
            .all()
        )
        product_ids = [p[0] for p in product_ids if p[0]]

        results = {
            "total_products": len(product_ids),
            "products_processed": 0,
            "total_images": 0,
            "features_extracted": 0,
            "caches_updated": 0,
        }

        for product_id in product_ids:
            try:
                product_results = self.retrain_product(product_id, extract_new_features)
                results["products_processed"] += 1
                results["total_images"] += product_results.get("total_images", 0)
                results["features_extracted"] += product_results.get("features_extracted", 0)
                if product_results.get("cache_updated"):
                    results["caches_updated"] += 1
            except Exception as e:
                logger.error(f"Failed to retrain product {product_id}: {e}")

        self.db.commit()
        return results

    def get_training_stats(self) -> Dict:
        """Get overall training statistics."""
        # Total training images
        total_images = self.db.query(func.count(TrainingImage.id)).scalar()

        # Images with features
        images_with_features = (
            self.db.query(func.count(TrainingImage.id))
            .filter(
                TrainingImage.feature_vector.isnot(None),
                func.length(TrainingImage.feature_vector) == CLIP_FEATURE_BYTES,
            )
            .scalar()
        )

        # Products with training images
        products_trained = (
            self.db.query(func.count(func.distinct(TrainingImage.stock_item_id)))
            .filter(TrainingImage.stock_item_id.isnot(None))
            .scalar()
        )

        # Products with cached features
        products_cached = self.db.query(func.count(ProductFeatureCache.id)).scalar()

        # Images by product
        images_per_product = (
            self.db.query(
                TrainingImage.stock_item_id,
                func.count(TrainingImage.id).label("count")
            )
            .filter(TrainingImage.stock_item_id.isnot(None))
            .group_by(TrainingImage.stock_item_id)
            .all()
        )

        counts = [c for _, c in images_per_product]
        avg_images_per_product = sum(counts) / len(counts) if counts else 0

        return {
            "total_images": total_images,
            "images_with_features": images_with_features,
            "images_pending_extraction": total_images - images_with_features,
            "products_trained": products_trained,
            "products_cached": products_cached,
            "avg_images_per_product": round(avg_images_per_product, 1),
            "min_images_per_product": min(counts) if counts else 0,
            "max_images_per_product": max(counts) if counts else 0,
        }


def run_full_training_pipeline(db: Session) -> Dict:
    """Run the complete training pipeline."""
    pipeline = TrainingPipeline(db)

    logger.info("Starting full training pipeline...")

    # Get initial stats
    initial_stats = pipeline.get_training_stats()

    # Retrain all products
    retrain_results = pipeline.retrain_all(extract_new_features=True)

    # Get final stats
    final_stats = pipeline.get_training_stats()

    # Get accuracy metrics
    accuracy = pipeline.tracker.get_accuracy_metrics(days=30)

    return {
        "initial_stats": initial_stats,
        "retrain_results": retrain_results,
        "final_stats": final_stats,
        "accuracy_metrics": accuracy,
    }
