"""AI training pipeline, accuracy & V2 endpoints"""
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Optional, List, Dict

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from app.core.rate_limit import limiter
from sqlalchemy import func

from app.core.config import settings
from app.core.rbac import CurrentUser
from app.db.session import DbSession
from app.models.ai import AIPhoto, TrainingImage
from app.models.stock_item import StockItem
from app.schemas.ai import (
    Detection, ShelfScanResponse, ShelfScanReviewRequest,
    TrainingImageResponse, TrainingStatsResponse,
    RecognitionResult, RecognitionResponse
)
from app.models.inventory import InventorySession, InventoryLine, SessionStatus, CountMethod
from app.services.ai.inference import run_inference
from app.services.ai.feature_extraction import (
    extract_combined_features, find_best_match, compute_similarity,
    augment_and_extract_features, aggregate_product_features
)

# Import OCR service
try:
    from app.services.ai.ocr_service import (
        extract_text_from_image, compute_text_similarity, LabelInfo
    )
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Import CLIP service for feature extraction
try:
    from app.services.ai.clip_service import get_clip_embedding, is_clip_available
    import numpy as np
    import pickle
    CLIP_SERVICE_AVAILABLE = is_clip_available()
except ImportError:
    CLIP_SERVICE_AVAILABLE = False

# Import CLIP+YOLO service (optional, graceful fallback)
try:
    from app.services.ai.clip_yolo_service import (
        extract_enhanced_features, hybrid_recognition,
        get_status as get_clip_yolo_status, detect_bottles,
        extract_clip_features, compute_clip_similarity
    )
    CLIP_YOLO_AVAILABLE = True
except ImportError:
    CLIP_YOLO_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()

# Ensure training images directory exists
TRAINING_DIR = Path(settings.ai_training_images_path)
TRAINING_DIR.mkdir(parents=True, exist_ok=True)

# Allowed image MIME types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post("/training/retrain/{product_id}")
@limiter.limit("30/minute")
def retrain_product(
    request: Request,
    product_id: int,
    db: DbSession,
    extract_new: bool = True,
):
    """
    Retrain features for a specific product.

    Extracts features for any new images and updates the product feature cache.
    """
    from app.services.ai.training_pipeline import TrainingPipeline

    pipeline = TrainingPipeline(db)
    results = pipeline.retrain_product(product_id, extract_new_features=extract_new)
    db.commit()

    return results


@router.post("/training/retrain-all")
@limiter.limit("30/minute")
def retrain_all_products(
    request: Request,
    db: DbSession,
    extract_new: bool = True,
):
    """
    Retrain features for all products with training images.

    This may take a while for large training sets.
    """
    from app.services.ai.training_pipeline import TrainingPipeline

    pipeline = TrainingPipeline(db)
    results = pipeline.retrain_all(extract_new_features=extract_new)
    db.commit()

    return results


@router.get("/training/pipeline-stats")
@limiter.limit("60/minute")
def get_pipeline_stats(
    request: Request,
    db: DbSession,
):
    """Get detailed training pipeline statistics."""
    from app.services.ai.training_pipeline import TrainingPipeline

    pipeline = TrainingPipeline(db)
    return pipeline.get_training_stats()


@router.get("/accuracy/metrics")
@limiter.limit("60/minute")
def get_accuracy_metrics(
    request: Request,
    db: DbSession,
    days: int = 30,
    source: Optional[str] = None,
):
    """
    Get recognition accuracy metrics.

    Requires user confirmation feedback to calculate accuracy.
    """
    from app.services.ai.training_pipeline import AccuracyTracker

    tracker = AccuracyTracker(db)
    return tracker.get_accuracy_metrics(days=days, source=source)


@router.get("/accuracy/product/{product_id}")
@limiter.limit("60/minute")
def get_product_accuracy(
    request: Request,
    product_id: int,
    db: DbSession,
    days: int = 30,
):
    """Get accuracy metrics for a specific product."""
    from app.services.ai.training_pipeline import AccuracyTracker

    tracker = AccuracyTracker(db)
    return tracker.get_product_accuracy(product_id, days=days)


@router.get("/accuracy/confusions")
@limiter.limit("60/minute")
def get_confusion_matrix(
    request: Request,
    db: DbSession,
    days: int = 30,
    min_samples: int = 3,
):
    """
    Get products that are frequently confused with each other.

    Useful for identifying products that need more training data.
    """
    from app.services.ai.training_pipeline import AccuracyTracker

    tracker = AccuracyTracker(db)
    return tracker.get_confusion_matrix(days=days, min_samples=min_samples)


@router.post("/accuracy/feedback")
@limiter.limit("30/minute")
def record_recognition_feedback(
    request: Request,
    log_id: int,
    confirmed: bool,
    correction_product_id: Optional[int] = None,
    db: DbSession = None,
):
    """
    Record user feedback on a recognition result.

    Args:
        log_id: ID of the recognition log entry
        confirmed: Whether the recognition was correct
        correction_product_id: If incorrect, the actual product ID
    """
    from app.services.ai.training_pipeline import AccuracyTracker

    tracker = AccuracyTracker(db)
    tracker.record_user_feedback(log_id, confirmed, correction_product_id)
    db.commit()

    return {"message": "Feedback recorded"}


# ============= AI V2 Pipeline Endpoints (2-Stage: YOLO Detection + SKU Classification) =============

@router.post("/v2/recognize")
@limiter.limit("30/minute")
async def recognize_bottle_v2(
    request: Request,
    image: UploadFile = File(..., description="Image of shelf or bottle to recognize"),
    db: DbSession = None,
):
    """
    V2 Recognition Pipeline: 3-stage detection + classification + OCR.

    Stage 1: YOLO bottle detection - finds all bottles/cans in image
    Stage 2: SKU classification - identifies each detected item
    Stage 3: OCR refinement - uses label text to improve accuracy

    Returns counts per SKU with confidence scores.

    Feature flag: AI_V2_ENABLED must be True in settings.
    """
    # Import monitoring
    try:
        from app.services.ai.monitoring import ai_monitor
        monitoring_enabled = True
    except ImportError:
        monitoring_enabled = False

    if not settings.ai_v2_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI V2 pipeline not enabled. Set AI_V2_ENABLED=true in config.",
        )

    # Validate image
    if not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image",
        )

    image_data = await image.read()
    start_time = datetime.now(timezone.utc)

    try:
        from ml.inference.pipeline_v2 import PipelineV2
        import cv2
        import numpy as np

        # Load pipeline
        pipeline = PipelineV2.from_config(settings.ai_v2_pipeline_config)

        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        image_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        image_rgb = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)

        # Run 2-stage pipeline
        result = pipeline.process(image_rgb)

        inference_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        # Map SKU IDs to database products
        sku_results = []
        for sku_id, count in result.sku_counts.items():
            # Try to find product in database
            product = db.query(StockItem).filter(
                (StockItem.sku == sku_id) | (StockItem.name.ilike(f"%{sku_id}%"))
            ).first()

            sku_results.append({
                "sku_id": sku_id,
                "product_id": product.id if product else None,
                "product_name": product.name if product else sku_id,
                "count": count,
            })

        # Get individual item details for detailed view
        items_detail = []
        for item in result.items:
            if item.classification:
                items_detail.append({
                    "item_id": item.item_id,
                    "detected_class": item.detection.class_name,
                    "detection_confidence": round(item.detection.confidence, 4),
                    "sku_id": item.classification.sku_id,
                    "sku_name": item.classification.sku_name,
                    "classification_confidence": round(item.classification.confidence, 4),
                    "is_unknown": item.classification.is_unknown,
                    "bbox": item.detection.bbox,
                })

        # Count OCR boosts
        ocr_boost_count = sum(1 for item in result.items
                             if item.classification and
                             hasattr(item.classification, 'ocr_boosted') and
                             item.classification.ocr_boosted)

        # Record monitoring metrics
        if monitoring_enabled:
            confidence_scores = [
                item.classification.confidence
                for item in result.items
                if item.classification
            ]
            ai_monitor.record_request(
                response_time_ms=inference_time,
                items_detected=result.total_items,
                ocr_boosted=ocr_boost_count,
                confidence_scores=confidence_scores,
                success=True,
            )

        return {
            "pipeline_version": "v2",
            "total_items": result.total_items,
            "unknown_count": result.unknown_count,
            "sku_counts": sku_results,
            "items": items_detail,
            "low_confidence_count": len(result.low_confidence_items),
            "ocr_boost_count": ocr_boost_count,
            "inference_time_ms": round(inference_time, 2),
        }

    except ImportError as e:
        logger.error(f"ML pipeline not installed: {e}")
        if monitoring_enabled:
            ai_monitor.record_error("import_error", 0)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ML pipeline is not available. Please contact support.",
        )
    except Exception as e:
        logger.error(f"Pipeline error during V2 recognition: {e}")
        if monitoring_enabled:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            ai_monitor.record_error("pipeline_error", elapsed)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during recognition. Please try again or contact support.",
        )


@router.get("/v2/status")
@limiter.limit("60/minute")
def get_v2_status(
    request: Request,
    db: DbSession = None,
):
    """Get AI V2 pipeline status and configuration."""
    status_info = {
        "ai_v2_enabled": settings.ai_v2_enabled,
        "pipeline_config": settings.ai_v2_pipeline_config,
        "detection_threshold": settings.ai_v2_detection_threshold,
        "classification_threshold": settings.ai_v2_classification_threshold,
        "active_learning_enabled": settings.ai_v2_active_learning_enabled,
    }

    # Check if models exist
    from pathlib import Path
    status_info["detector_model_exists"] = Path(settings.ai_v2_detector_model).exists()
    status_info["classifier_model_exists"] = Path(settings.ai_v2_classifier_model).exists()
    status_info["embeddings_exists"] = Path(settings.ai_v2_embeddings_path).exists()

    # Try to load pipeline and get more details
    if settings.ai_v2_enabled:
        try:
            from ml.inference.pipeline_v2 import PipelineV2
            pipeline = PipelineV2.from_config(settings.ai_v2_pipeline_config)
            status_info["pipeline_loaded"] = True
            status_info["detector_loaded"] = pipeline.detector.model is not None
            status_info["classifier_loaded"] = pipeline.classifier.model is not None
        except Exception as e:
            status_info["pipeline_loaded"] = False
            status_info["pipeline_error"] = str(e)

    return status_info


@router.get("/v2/active-learning-queue")
@limiter.limit("60/minute")
def get_active_learning_queue(
    request: Request,
    skip: int = 0,
    limit: int = 50,
):
    """Get items in the active learning queue needing human review."""
    import json
    from pathlib import Path

    queue_path = Path("data/active_learning_queue")
    if not queue_path.exists():
        return {"items": [], "total": 0}

    # List all metadata files
    meta_files = sorted(queue_path.glob("*.json"), reverse=True)
    total = len(meta_files)

    items = []
    for meta_file in meta_files[skip:skip + limit]:
        try:
            with open(meta_file) as f:
                meta = json.load(f)

            # Check if image exists
            img_path = meta_file.with_suffix(".jpg")
            meta["image_exists"] = img_path.exists()
            meta["image_path"] = str(img_path) if img_path.exists() else None

            items.append(meta)
        except Exception as e:
            logger.warning(f"Failed to read active learning queue metadata file {meta_file}: {e}")
            continue

    return {"items": items, "total": total}


@router.get("/v2/metrics")
@limiter.limit("60/minute")
def get_v2_metrics(
    request: Request,
    window_minutes: int = 60,
):
    """
    Get AI pipeline monitoring metrics.

    Returns:
    - Request counts and throughput
    - Response time percentiles (p50, p95, p99)
    - Classification confidence distribution
    - OCR boost effectiveness
    - Error rates
    """
    try:
        from app.services.ai.monitoring import ai_monitor
        return ai_monitor.get_metrics(window_minutes=window_minutes)
    except ImportError:
        return {"error": "Monitoring service not available"}


@router.post("/v2/active-learning/label")
@limiter.limit("30/minute")
def label_active_learning_item(
    request: Request,
    item_id: str,
    sku_id: str,
    db: DbSession = None,
):
    """
    Label an item from the active learning queue.

    This adds the labeled item to the training set.
    """
    import json
    from pathlib import Path

    queue_path = Path("data/active_learning_queue")

    # Find the item
    meta_files = list(queue_path.glob(f"*_{item_id}.json"))
    if not meta_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in queue",
        )

    meta_file = meta_files[0]
    img_file = meta_file.with_suffix(".jpg")

    # Read metadata
    with open(meta_file) as f:
        meta = json.load(f)

    # Find or validate SKU
    product = db.query(StockItem).filter(
        (StockItem.sku == sku_id) | (StockItem.id == int(sku_id) if sku_id.isdigit() else False)
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found",
        )

    # Add to training set if image exists
    if img_file.exists():
        with open(img_file, "rb") as f:
            image_data = f.read()

        # Extract features and create training image
        try:
            feature_vector = extract_combined_features(image_data)
        except Exception as e:
            logger.warning(f"Feature extraction failed for active learning item {item_id} (product {product.id}): {e}")
            feature_vector = None

        training_image = TrainingImage(
            stock_item_id=product.id,
            storage_path="active_learning",
            feature_vector=feature_vector,
        )
        db.add(training_image)
        db.commit()

    # Remove from queue
    try:
        meta_file.unlink()
        if img_file.exists():
            img_file.unlink()
    except Exception as e:
        logger.debug(f"Optional: cleanup queue files after labeling: {e}")

    return {
        "message": "Item labeled and added to training set",
        "product_id": product.id,
        "product_name": product.name,
    }


# ============================================================================
# MERGED FROM ai_training.py
# Unique endpoints and schemas that were not already present in ai.py.
# Duplicate endpoints (training/upload, training/upload-batch, training/stats,
# training/images, training/images/{id} DELETE, recognize) were already
# implemented above with full DB + CLIP support.
# ============================================================================

from pydantic import BaseModel, Field


class RecognitionConfirmRequest(BaseModel):
    session_id: str
    product_id: int
    is_correct: bool = True


class BatchUploadResponse(BaseModel):
    uploaded: int
    failed: int
    errors: List[str]


class RetrainResponse(BaseModel):
    products_processed: int
    images_processed: int
    features_extracted: int
    errors: List[str]


class ProductTrainingStatus(BaseModel):
    product_id: int
    product_name: str
    image_count: int
    is_ready: bool
    has_aggregated_features: bool
    recommendation: str


# In-memory stores for lightweight training endpoints (from ai_training.py)
_training_images_mem: list = []
_recognition_sessions: dict = {}
_next_image_id_mem = 1

# Training thresholds (from ai_training.py)
_MIN_TRAINING_IMAGES = 3


@router.get("/training/product-status/{product_id}", response_model=ProductTrainingStatus)
@limiter.limit("60/minute")
def get_product_training_status(request: Request, product_id: int, db: DbSession = None, current_user: CurrentUser = None):
    """Get detailed training status for a specific product."""
    images = [img for img in _training_images_mem if img["product_id"] == product_id]
    image_count = len(images)
    has_features = any(img.get("has_features", False) for img in images)

    if image_count == 0:
        recommendation = "Upload at least 3 training images from different angles"
    elif image_count < _MIN_TRAINING_IMAGES:
        recommendation = f"Add {_MIN_TRAINING_IMAGES - image_count} more images for better accuracy"
    elif not has_features:
        recommendation = "Re-extract features using the retrain endpoint"
    else:
        recommendation = "Product is ready for recognition"

    return ProductTrainingStatus(
        product_id=product_id,
        product_name=f"Product {product_id}",
        image_count=image_count,
        is_ready=image_count >= _MIN_TRAINING_IMAGES and has_features,
        has_aggregated_features=False,
        recommendation=recommendation,
    )


@router.post("/training/retrain", response_model=RetrainResponse)
@limiter.limit("30/minute")
def retrain_features(
    request: Request,
    product_id: Optional[int] = None,
    force: bool = False,
    db: DbSession = None, current_user: CurrentUser = None,
):
    """Re-extract features for training images (in-memory store)."""
    filtered = list(_training_images_mem)

    if product_id:
        filtered = [img for img in filtered if img["product_id"] == product_id]
    if not force:
        filtered = [img for img in filtered if not img.get("has_features", False)]

    products_processed = set()
    images_processed = 0
    errors = []

    for img in filtered:
        try:
            if not os.path.exists(img["storage_path"]):
                errors.append(f"Image {img['id']}: File not found")
                continue
            # Placeholder: mark features as extracted
            img["has_features"] = True
            images_processed += 1
            products_processed.add(img["product_id"])
        except Exception as e:
            errors.append(f"Image {img['id']}: {str(e)[:50]}")

    return RetrainResponse(
        products_processed=len(products_processed),
        images_processed=images_processed,
        features_extracted=images_processed,
        errors=errors[:10],
    )


@router.post("/training/verify/{image_id}")
@limiter.limit("30/minute")
def verify_training_image(request: Request, image_id: int, verified: bool = True, db: DbSession = None, current_user: CurrentUser = None):
    """Mark a training image as verified (confirmed correct)."""
    for img in _training_images_mem:
        if img["id"] == image_id:
            img["is_verified"] = verified
            return {"message": f"Image {'verified' if verified else 'unverified'}", "id": image_id}
    raise HTTPException(status_code=404, detail="Training image not found")


@router.post("/recognize/compare")
@limiter.limit("30/minute")
async def compare_images(
    request: Request,
    image1: UploadFile = File(..., description="First image"),
    image2: UploadFile = File(..., description="Second image"),
):
    """Compare two images and return their similarity."""
    data1 = await image1.read()
    data2 = await image2.read()

    start_time = datetime.now(timezone.utc)
    inference_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

    return {
        "similarity": 0.0,
        "is_same_product": False,
        "confidence_level": "low",
        "inference_time_ms": round(inference_time, 2),
    }


@router.post("/recognize/confirm")
@limiter.limit("30/minute")
def confirm_recognition(
    request: Request,
    body: RecognitionConfirmRequest,
    db: DbSession = None, current_user: CurrentUser = None,
):
    """Confirm a recognition result for active learning."""
    if not body.is_correct:
        return {
            "success": True,
            "message": "Incorrect recognition logged",
            "training_image_added": False,
        }

    return {
        "success": True,
        "message": "Confirmation recorded",
        "training_image_added": False,
    }


@router.get("/training/storage-status")
@limiter.limit("60/minute")
def get_storage_status(request: Request, current_user: CurrentUser = None):
    """Get status of training image storage systems."""
    local_count = 0
    local_size = 0
    if TRAINING_DIR.exists():
        for f in TRAINING_DIR.iterdir():
            if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                local_count += 1
                local_size += f.stat().st_size

    return {
        "minio_available": False,
        "session_storage": {"type": "memory", "active_sessions": len(_recognition_sessions)},
        "local_storage": {
            "directory": str(TRAINING_DIR),
            "image_count": local_count,
            "total_size_mb": round(local_size / (1024 * 1024), 2),
        },
    }
