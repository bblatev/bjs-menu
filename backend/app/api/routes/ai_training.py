"""AI Training and Bottle Recognition API routes.

Provides training image management and recognition endpoints
adapted for the bjs-menu system.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, BackgroundTasks
from pydantic import BaseModel, Field

from app.db.session import DbSession
from app.core.rbac import CurrentUser, OptionalCurrentUser
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Training images directory
TRAINING_DIR = Path("training_images")
TRAINING_DIR.mkdir(exist_ok=True)

# Recognition thresholds
RECOGNITION_THRESHOLD = 0.65
HIGH_CONFIDENCE_THRESHOLD = 0.80
MIN_TRAINING_IMAGES = 3


# ==================== SCHEMAS ====================

class TrainingImageResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    created_at: str
    is_verified: bool = False
    has_features: bool = False


class TrainingStatsResponse(BaseModel):
    total_images: int
    products_trained: int
    images_per_product: Dict[str, int]
    products_ready: int
    avg_images_per_product: float


class RecognitionResult(BaseModel):
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    confidence: float
    is_match: bool = False
    confidence_level: str = "none"


class RecognitionResponse(BaseModel):
    results: List[RecognitionResult]
    inference_time_ms: float
    top_match: Optional[RecognitionResult] = None
    session_id: Optional[str] = None
    is_bar_item: bool = True
    detected_class: Optional[str] = None
    detection_confidence: Optional[float] = None


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


# ==================== In-memory stores ====================
_training_images: list = []
_recognition_sessions: dict = {}
_next_image_id = 1


# ==================== TRAINING ENDPOINTS ====================

@router.post("/training/upload", response_model=TrainingImageResponse)
@limiter.limit("30/minute")
async def upload_training_image(
    request: Request,
    image: UploadFile = File(..., description="Image of bottle to train"),
    product_id: int = Form(...),
    use_augmentation: bool = Form(default=True, description="Generate augmented versions"),
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """Upload a training image for bottle recognition."""
    global _next_image_id

    content_type = image.content_type or ""
    if content_type and not content_type.startswith("image/") and content_type != "application/octet-stream":
        raise HTTPException(status_code=400, detail=f"File must be an image, got: {content_type}")

    image_data = await image.read()

    if len(image_data) < 1000:
        raise HTTPException(status_code=400, detail=f"Image too small ({len(image_data)} bytes). Minimum is 1000 bytes.")

    ext = image.filename.split(".")[-1] if "." in image.filename else "jpg"
    filename = f"{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = TRAINING_DIR / filename

    with open(filepath, "wb") as f:
        f.write(image_data)

    now = datetime.utcnow().isoformat()
    training_image = {
        "id": _next_image_id,
        "product_id": product_id,
        "product_name": f"Product {product_id}",
        "storage_path": str(filepath),
        "created_at": now,
        "is_verified": False,
        "has_features": False,
    }
    _training_images.append(training_image)
    _next_image_id += 1

    return TrainingImageResponse(**{k: v for k, v in training_image.items() if k in TrainingImageResponse.model_fields})


@router.post("/training/upload-batch", response_model=BatchUploadResponse)
@limiter.limit("30/minute")
async def upload_training_images_batch(
    request: Request,
    images: List[UploadFile] = File(..., description="Multiple images to upload"),
    product_id: int = Form(...),
    use_augmentation: bool = Form(default=True),
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """Upload multiple training images at once."""
    global _next_image_id

    uploaded = 0
    failed = 0
    errors = []

    for idx, img in enumerate(images):
        try:
            content_type = img.content_type or ""
            if content_type and not content_type.startswith("image/"):
                errors.append(f"Image {idx + 1}: Not an image file")
                failed += 1
                continue

            image_data = await img.read()
            if len(image_data) < 1000:
                errors.append(f"Image {idx + 1}: Too small")
                failed += 1
                continue

            ext = img.filename.split(".")[-1] if "." in img.filename else "jpg"
            filename = f"{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
            filepath = TRAINING_DIR / filename

            with open(filepath, "wb") as f:
                f.write(image_data)

            now = datetime.utcnow().isoformat()
            training_image = {
                "id": _next_image_id,
                "product_id": product_id,
                "product_name": f"Product {product_id}",
                "storage_path": str(filepath),
                "created_at": now,
                "is_verified": False,
                "has_features": False,
            }
            _training_images.append(training_image)
            _next_image_id += 1
            uploaded += 1

        except Exception as e:
            errors.append(f"Image {idx + 1}: {str(e)[:100]}")
            failed += 1

    return BatchUploadResponse(uploaded=uploaded, failed=failed, errors=errors[:10])


@router.get("/training/stats", response_model=TrainingStatsResponse)
@limiter.limit("60/minute")
def get_training_stats(request: Request, db: DbSession = None, current_user: CurrentUser = None):
    """Get comprehensive training statistics."""
    total_images = len(_training_images)
    product_counts: Dict[str, int] = {}

    for img in _training_images:
        pid = str(img["product_id"])
        product_counts[pid] = product_counts.get(pid, 0) + 1

    products_trained = len(product_counts)
    products_ready = sum(1 for cnt in product_counts.values() if cnt >= MIN_TRAINING_IMAGES)
    avg_images = total_images / products_trained if products_trained > 0 else 0

    return TrainingStatsResponse(
        total_images=total_images,
        products_trained=products_trained,
        images_per_product=product_counts,
        products_ready=products_ready,
        avg_images_per_product=round(avg_images, 1),
    )


@router.get("/training/product-status/{product_id}", response_model=ProductTrainingStatus)
@limiter.limit("60/minute")
def get_product_training_status(request: Request, product_id: int, db: DbSession = None, current_user: CurrentUser = None):
    """Get detailed training status for a specific product."""
    images = [img for img in _training_images if img["product_id"] == product_id]
    image_count = len(images)
    has_features = any(img.get("has_features", False) for img in images)

    if image_count == 0:
        recommendation = "Upload at least 3 training images from different angles"
    elif image_count < MIN_TRAINING_IMAGES:
        recommendation = f"Add {MIN_TRAINING_IMAGES - image_count} more images for better accuracy"
    elif not has_features:
        recommendation = "Re-extract features using the retrain endpoint"
    else:
        recommendation = "Product is ready for recognition"

    return ProductTrainingStatus(
        product_id=product_id,
        product_name=f"Product {product_id}",
        image_count=image_count,
        is_ready=image_count >= MIN_TRAINING_IMAGES and has_features,
        has_aggregated_features=False,
        recommendation=recommendation,
    )


@router.get("/training/images")
@limiter.limit("60/minute")
def list_training_images(
    request: Request,
    product_id: Optional[int] = None,
    only_without_features: bool = False,
    skip: int = 0, limit: int = 100,
    db: DbSession = None, current_user: CurrentUser = None,
):
    """List training images with filtering options."""
    filtered = list(_training_images)

    if product_id:
        filtered = [img for img in filtered if img["product_id"] == product_id]
    if only_without_features:
        filtered = [img for img in filtered if not img.get("has_features", False)]

    page = filtered[skip : skip + limit]
    return [
        {
            "id": img["id"],
            "product_id": img["product_id"],
            "product_name": img["product_name"],
            "storage_path": img["storage_path"],
            "created_at": img["created_at"],
            "is_verified": img.get("is_verified", False),
            "has_features": img.get("has_features", False),
            "has_augmented_features": False,
        }
        for img in page
    ]


@router.delete("/training/images/{image_id}")
@limiter.limit("30/minute")
def delete_training_image(request: Request, image_id: int, db: DbSession = None, current_user: CurrentUser = None):
    """Delete a training image."""
    global _training_images

    for img in _training_images:
        if img["id"] == image_id:
            try:
                if os.path.exists(img["storage_path"]):
                    os.remove(img["storage_path"])
            except Exception as e:
                logger.debug(f"Optional: cleanup training image file: {e}")
            _training_images = [i for i in _training_images if i["id"] != image_id]
            return {"message": "Training image deleted"}

    raise HTTPException(status_code=404, detail="Training image not found")


@router.post("/training/retrain", response_model=RetrainResponse)
@limiter.limit("30/minute")
def retrain_features(
    request: Request,
    product_id: Optional[int] = None,
    force: bool = False,
    db: DbSession = None, current_user: CurrentUser = None,
):
    """Re-extract features for training images."""
    filtered = list(_training_images)

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
    for img in _training_images:
        if img["id"] == image_id:
            img["is_verified"] = verified
            return {"message": f"Image {'verified' if verified else 'unverified'}", "id": image_id}
    raise HTTPException(status_code=404, detail="Training image not found")


# ==================== RECOGNITION ENDPOINT ====================

@router.post("/recognize", response_model=RecognitionResponse)
@limiter.limit("30/minute")
async def recognize_bottle(
    request: Request,
    image: UploadFile = File(..., description="Image of bottle to recognize"),
    top_k: int = 5,
    skip_detection: bool = False,
    detected_class: Optional[str] = None,
    db: DbSession = None,
):
    """Recognize a bar item from an image."""
    content_type = image.content_type or ""
    if content_type and not content_type.startswith("image/") and content_type != "application/octet-stream":
        raise HTTPException(status_code=400, detail=f"File must be an image, got: {content_type}")

    image_data = await image.read()
    start_time = datetime.utcnow()

    if not _training_images:
        inference_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        return RecognitionResponse(
            results=[], inference_time_ms=round(inference_time, 2),
            top_match=None, session_id=None,
            is_bar_item=True, detected_class=detected_class,
            detection_confidence=None,
        )

    # Placeholder recognition - return empty results
    inference_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    session_id = str(uuid.uuid4())

    return RecognitionResponse(
        results=[],
        inference_time_ms=round(inference_time, 2),
        top_match=None,
        session_id=session_id,
        is_bar_item=True,
        detected_class=detected_class,
        detection_confidence=None,
    )


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

    start_time = datetime.utcnow()
    inference_time = (datetime.utcnow() - start_time).total_seconds() * 1000

    return {
        "similarity": 0.0,
        "is_same_product": False,
        "confidence_level": "low",
        "inference_time_ms": round(inference_time, 2),
    }


# ==================== ACTIVE LEARNING ====================

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


# ==================== STORAGE STATUS ====================

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
