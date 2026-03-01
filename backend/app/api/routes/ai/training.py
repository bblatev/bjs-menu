"""AI training image upload & management"""
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

@router.post("/training/upload", response_model=TrainingImageResponse)
@limiter.limit("10/minute")
async def upload_training_image(
    request: Request,
    image: UploadFile = File(..., description="Image of bottle to train"),
    product_id: Annotated[int, Form()] = ...,
    db: DbSession = None,
):
    """
    Upload a training image for bottle recognition.

    Associates an image with a product to teach the AI what the bottle looks like.
    """
    # Validate image
    if not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image",
        )

    # Verify product exists
    product = db.query(StockItem).filter(StockItem.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="StockItem not found",
        )

    # Read image data
    image_data = await image.read()

    # Fix EXIF orientation for mobile photos
    try:
        from PIL import Image, ImageOps
        import io
        img = Image.open(io.BytesIO(image_data))
        img = ImageOps.exif_transpose(img)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=95)
        image_data = buffer.getvalue()
    except ImportError:
        logger.debug("PIL not available for EXIF orientation fix")
    except Exception as e:
        logger.warning(f"Failed to process image EXIF orientation: {e}")

    # Extract CLIP features (2048 bytes = 512 float32) for recognition
    # This is the modern approach that works with the /recognize endpoint
    feature_vector = None
    if CLIP_SERVICE_AVAILABLE:
        try:
            import numpy as np
            from app.services.ai.clip_service import get_clip_embedding
            clip_embedding = get_clip_embedding(image_data)
            if clip_embedding is not None:
                # Normalize and convert to bytes
                clip_embedding = clip_embedding / (np.linalg.norm(clip_embedding) + 1e-7)
                feature_vector = clip_embedding.astype(np.float32).tobytes()
        except Exception as e:
            logger.warning(f"CLIP feature extraction failed: {e}")

    # Fallback to old feature extraction if CLIP fails
    if feature_vector is None:
        try:
            feature_vectors = augment_and_extract_features(image_data, n_augments=5)
            feature_vector = aggregate_product_features(feature_vectors) if feature_vectors else None
        except Exception as e:
            logger.debug(f"Augmented feature extraction failed: {e}")
            try:
                feature_vector = extract_combined_features(image_data)
            except Exception as e2:
                logger.warning(f"All feature extraction methods failed: {e2}")
                feature_vector = None

    # Extract OCR text from label
    ocr_text = None
    ocr_brand = None
    ocr_product_name = None
    if OCR_AVAILABLE:
        try:
            label_info = extract_text_from_image(image_data)
            if label_info:
                ocr_text = label_info.raw_text if label_info.raw_text else None
                ocr_brand = label_info.brand
                ocr_product_name = label_info.product_name
        except Exception as e:
            logger.warning(f"OCR text extraction failed: {e}")

    # Create database record - no file saved, only features stored
    training_image = TrainingImage(
        stock_item_id=product_id,
        storage_path="features_only",
        feature_vector=feature_vector,
        ocr_text=ocr_text,
        ocr_brand=ocr_brand,
        ocr_product_name=ocr_product_name,
    )
    db.add(training_image)
    db.commit()
    db.refresh(training_image)

    return TrainingImageResponse(
        id=training_image.id,
        product_id=product_id,
        product_name=product.name,
        created_at=training_image.created_at,
        is_verified=training_image.is_verified,
    )


@router.post("/training/upload-batch")
@limiter.limit("5/minute")
async def upload_training_batch(
    request: Request,
    images: List[UploadFile] = File(..., description="Multiple training images"),
    product_id: Annotated[int, Form()] = ...,
    db: DbSession = None,
):
    """Upload multiple training images for a product in one request. No auth required."""
    # Validate product exists
    product = db.query(StockItem).filter(StockItem.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="StockItem not found",
        )

    results = {
        "successful": 0,
        "failed": 0,
        "errors": [],
    }

    for idx, image in enumerate(images):
        try:
            if not image.content_type.startswith("image/"):
                results["errors"].append({"index": idx, "error": "Not an image"})
                results["failed"] += 1
                continue

            image_data = await image.read()

            # Fix EXIF orientation for mobile photos
            try:
                from PIL import Image, ImageOps
                import io as iolib
                img = Image.open(iolib.BytesIO(image_data))
                img = ImageOps.exif_transpose(img)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                buffer = iolib.BytesIO()
                img.save(buffer, format='JPEG', quality=95)
                image_data = buffer.getvalue()
            except Exception as e:
                logger.debug(f"Optional: image preprocessing with PIL: {e}")

            # Extract CLIP features (preferred) or fallback to old method
            feature_vector = None
            if CLIP_SERVICE_AVAILABLE:
                try:
                    import numpy as np
                    from app.services.ai.clip_service import get_clip_embedding
                    clip_embedding = get_clip_embedding(image_data)
                    if clip_embedding is not None:
                        clip_embedding = clip_embedding / (np.linalg.norm(clip_embedding) + 1e-7)
                        feature_vector = clip_embedding.astype(np.float32).tobytes()
                except Exception as e:
                    logger.warning(f"Failed to extract CLIP features: {e}")

            # Fallback to old feature extraction if CLIP fails
            if feature_vector is None:
                try:
                    feature_vectors = augment_and_extract_features(image_data, n_augments=3)
                    feature_vector = aggregate_product_features(feature_vectors) if feature_vectors else None
                except Exception as e:
                    logger.warning(f"Augmented feature extraction failed for batch image {idx}, product {product_id}: {e}")
                    try:
                        feature_vector = extract_combined_features(image_data)
                    except Exception as e2:
                        logger.warning(f"Combined feature extraction also failed for batch image {idx}, product {product_id}: {e2}")
                        feature_vector = None

            # Create database record - no file saved
            training_image = TrainingImage(
                stock_item_id=product_id,
                storage_path="features_only",
                feature_vector=feature_vector,
            )
            db.add(training_image)
            results["successful"] += 1

        except Exception as e:
            results["errors"].append({"index": idx, "error": str(e)})
            results["failed"] += 1

    db.commit()
    return results


@router.post("/training/upload-video")
@limiter.limit("3/minute")
async def upload_training_video(
    request: Request,
    video: UploadFile = File(..., description="Video of product to train"),
    product_id: Annotated[int, Form()] = ...,
    frames_per_second: Annotated[float, Form()] = 3.0,
    max_frames: Annotated[int, Form()] = 150,
    db: DbSession = None,
):
    """
    Upload a video and extract frames for training.

    Extracts diverse frames with quality filtering and augmentation.

    Args:
        video: Video file (MP4, MOV, AVI, etc.)
        product_id: StockItem to associate frames with
        frames_per_second: How many frames to extract per second (default 3)
        max_frames: Maximum number of frames to extract (default 150)
    """
    import cv2
    import tempfile
    import numpy as np

    # Validate video
    valid_types = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/avi", "video/mov"]
    if not any(video.content_type.startswith(t.split("/")[0]) for t in valid_types):
        if not video.content_type.startswith("video/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File must be a video. Got: {video.content_type}",
            )

    # Verify product exists
    product = db.query(StockItem).filter(StockItem.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="StockItem not found",
        )

    # Read video data
    video_data = await video.read()

    # Save to temp file for OpenCV
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_data)
        tmp_path = tmp.name

    results = {
        "successful": 0,
        "failed": 0,
        "skipped_blur": 0,
        "skipped_similar": 0,
        "total_frames_in_video": 0,
        "frames_extracted": 0,
        "errors": [],
    }

    try:
        # Open video with OpenCV
        cap = cv2.VideoCapture(tmp_path)

        if not cap.isOpened():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not open video file",
            )

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        results["total_frames_in_video"] = total_frames
        results["video_fps"] = fps
        results["video_duration_seconds"] = round(duration, 2)

        # Calculate frame interval
        frame_interval = int(fps / frames_per_second) if frames_per_second > 0 else int(fps)
        frame_interval = max(1, frame_interval)

        frame_count = 0
        extracted_count = 0
        previous_hashes = []

        def compute_frame_hash(frame):
            """Compute perceptual hash for similarity detection"""
            small = cv2.resize(frame, (32, 32))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            avg = np.mean(gray)
            return tuple((gray > avg).flatten().astype(np.uint8))

        def compute_blur_score(frame):
            """Compute Laplacian variance as blur metric (higher = sharper)"""
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return cv2.Laplacian(gray, cv2.CV_64F).var()

        def is_similar_to_previous(current_hash, prev_hashes, threshold=0.85):
            """Check if frame is too similar to any previously extracted frame"""
            if not prev_hashes:
                return False
            current = np.array(current_hash)
            for prev in prev_hashes[-10:]:  # Check last 10 frames
                prev = np.array(prev)
                similarity = np.mean(current == prev)
                if similarity > threshold:
                    return True
            return False

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Extract frame at interval
            if frame_count % frame_interval == 0 and extracted_count < max_frames:
                try:
                    # Check blur - skip blurry frames
                    blur_score = compute_blur_score(frame)
                    if blur_score < 15:  # Too blurry (lowered threshold)
                        results["skipped_blur"] += 1
                        frame_count += 1
                        continue

                    # Check similarity to previous frames
                    current_hash = compute_frame_hash(frame)
                    if is_similar_to_previous(current_hash, previous_hashes):
                        results["skipped_similar"] += 1
                        frame_count += 1
                        continue

                    previous_hashes.append(current_hash)

                    # Enhance frame quality
                    # Denoise
                    denoised = cv2.fastNlMeansDenoisingColored(frame, None, 5, 5, 7, 21)

                    # Apply CLAHE for better contrast
                    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
                    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

                    # Slight sharpening
                    kernel = np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]])
                    enhanced = cv2.filter2D(enhanced, -1, kernel)

                    # Convert frame to JPEG bytes with high quality
                    _, buffer = cv2.imencode('.jpg', enhanced, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    image_data = buffer.tobytes()

                    # Extract features - no file saved, only features stored in DB
                    try:
                        feature_vectors = augment_and_extract_features(image_data, n_augments=2)
                        feature_vector = aggregate_product_features(feature_vectors) if feature_vectors else None
                    except Exception as e:
                        logger.warning(f"Augmented feature extraction failed for video frame {frame_count}, product {product_id}: {e}")
                        try:
                            feature_vector = extract_combined_features(image_data)
                        except Exception as e2:
                            logger.warning(f"Combined feature extraction also failed for video frame {frame_count}, product {product_id}: {e2}")
                            feature_vector = None

                    # Extract OCR text from every 10th frame (OCR is slow)
                    ocr_text = None
                    ocr_brand = None
                    ocr_product_name = None
                    if OCR_AVAILABLE and extracted_count % 10 == 0:
                        try:
                            label_info = extract_text_from_image(image_data)
                            if label_info:
                                ocr_text = label_info.raw_text if label_info.raw_text else None
                                ocr_brand = label_info.brand
                                ocr_product_name = label_info.product_name
                        except Exception as e:
                            logger.debug(f"Optional: OCR text extraction from image: {e}")

                    # Create database record - no file saved
                    training_image = TrainingImage(
                        stock_item_id=product_id,
                        storage_path="features_only",
                        feature_vector=feature_vector,
                        ocr_text=ocr_text,
                        ocr_brand=ocr_brand,
                        ocr_product_name=ocr_product_name,
                    )
                    db.add(training_image)
                    results["successful"] += 1
                    extracted_count += 1

                except Exception as e:
                    results["errors"].append({"frame": frame_count, "error": str(e)})
                    results["failed"] += 1

            frame_count += 1

        cap.release()
        results["frames_extracted"] = extracted_count

        db.commit()

    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Video processing failed. Please try again or contact support.",
        )
    finally:
        # Clean up temp file
        import os as os_module
        try:
            os_module.unlink(tmp_path)
        except OSError as e:
            logger.warning(f"Failed to clean up temp video file {tmp_path}: {e}")

    return results


@router.get("/training/status")
@limiter.limit("60/minute")
def get_training_status(
    request: Request,
    db: DbSession = None,
):
    """Get AI training system status. No auth required."""
    total_images = db.query(TrainingImage).count() if db else 0
    products_trained = db.query(TrainingImage.stock_item_id).distinct().count() if db else 0

    return {
        "status": "ready",
        "model_version": None,
        "last_trained": None,
        "total_training_images": total_images,
        "products_with_training": products_trained,
        "training_in_progress": False,
        "queue_size": 0,
        "capabilities": {
            "yolo_detection": False,
            "clip_classification": False,
            "ocr_refinement": False,
            "hand_crafted_features": True,
        },
    }


@router.get("/training/stats", response_model=TrainingStatsResponse)
@limiter.limit("60/minute")
def get_training_stats(
    request: Request,
    db: DbSession = None,
):
    """Get training statistics. No auth required."""
    total_images = db.query(TrainingImage).count()

    # Count products with training images
    products_trained = db.query(TrainingImage.stock_item_id).distinct().count()

    # Images per product
    counts = db.query(
        TrainingImage.stock_item_id,
        func.count(TrainingImage.id).label("count")
    ).group_by(TrainingImage.stock_item_id).all()

    images_per_product = {str(pid): cnt for pid, cnt in counts}

    return TrainingStatsResponse(
        total_images=total_images,
        products_trained=products_trained,
        images_per_product=images_per_product,
    )


@router.get("/training/images")
@limiter.limit("60/minute")
def list_training_images(
    request: Request,
    product_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: DbSession = None,
):
    """List training images, optionally filtered by product. No auth required."""
    query = db.query(TrainingImage)

    if product_id:
        query = query.filter(TrainingImage.stock_item_id == product_id)

    images = query.offset(skip).limit(limit).all()

    # Get stock item names for display
    stock_item_ids = [img.stock_item_id for img in images]
    stock_items = {}
    if stock_item_ids:
        items = db.query(StockItem).filter(StockItem.id.in_(stock_item_ids)).all()
        stock_items = {item.id: item.name for item in items}

    return [
        {
            "id": img.id,
            "product_id": img.stock_item_id,
            "product_name": stock_items.get(img.stock_item_id, f"Item {img.stock_item_id}"),
            "storage_path": img.storage_path,
            "created_at": img.created_at.isoformat() if img.created_at else None,
            "is_verified": getattr(img, 'is_verified', False),
        }
        for img in images
    ]


@router.delete("/training/images/{image_id}")
@limiter.limit("30/minute")
def delete_training_image(
    request: Request,
    image_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Delete a training image."""
    image = db.query(TrainingImage).filter(TrainingImage.id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training image not found",
        )

    # Delete file if it exists
    try:
        if os.path.exists(image.storage_path):
            os.remove(image.storage_path)
    except Exception as e:
        logger.debug(f"Optional: cleanup training image file: {e}")

    db.delete(image)
    db.commit()

    return {"message": "Training image deleted"}


# ============= Bottle Recognition Endpoint =============

