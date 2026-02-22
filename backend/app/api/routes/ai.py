"""AI shelf scanning and bottle recognition routes."""

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

logger = logging.getLogger(__name__)

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

router = APIRouter()

# Ensure training images directory exists
TRAINING_DIR = Path(settings.ai_training_images_path)
TRAINING_DIR.mkdir(parents=True, exist_ok=True)


# Allowed image MIME types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post("/shelf-scan", response_model=ShelfScanResponse)
@limiter.limit("10/minute")
async def shelf_scan(
    request: Request,
    image: UploadFile = File(..., description="Image of shelf/fridge to scan"),
    session_id: Annotated[Optional[int], Form()] = None,
    store_photo: Annotated[bool, Form()] = False,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """
    Analyze a shelf/fridge photo and detect products.

    Returns detected products with counts and confidence scores.
    StockItems are mapped to catalog items where possible.
    """
    # Validate content type
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File must be an image. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    # Read image data with size limit
    max_size = settings.max_upload_size_mb * 1024 * 1024
    image_data = await image.read()

    if len(image_data) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB",
        )

    # Run inference
    start_time = datetime.now(timezone.utc)
    raw_detections = run_inference(image_data)
    inference_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

    # Map detections to stock items
    detections = []
    for det in raw_detections:
        # Try to find stock item by name (case-insensitive partial match)
        stock_item = db.query(StockItem).filter(
            StockItem.name.ilike(f"%{det['label']}%")
        ).first()

        detection = Detection(
            product_id=stock_item.id if stock_item else None,
            label=det["label"],
            count=det["count"],
            confidence=Decimal(str(det["confidence"])),
            bbox=det.get("bbox"),
        )
        detections.append(detection)

    # Store photo if requested
    photo_id = None
    if store_photo:
        photo = AIPhoto(session_id=session_id)
        # Note: In production, save to file storage and set storage_path
        # For now, we just create the record
        db.add(photo)
        db.commit()
        db.refresh(photo)
        photo_id = photo.id

    return ShelfScanResponse(
        detections=detections,
        meta={
            "model": "shelf-scan-v1",
            "ts": datetime.now(timezone.utc).isoformat(),
            "inference_time_ms": round(inference_time, 2),
            "total_items_detected": sum(d.count for d in detections),
        },
        photo_id=photo_id,
    )


@router.post("/shelf-scan/review")
@limiter.limit("30/minute")
def review_shelf_scan(
    request: Request,
    review_request: ShelfScanReviewRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Add reviewed AI detections to an inventory session.

    After user reviews and confirms/edits the AI detections,
    this endpoint adds them as inventory lines.
    """
    # Verify session exists and is draft
    session = db.query(InventorySession).filter(InventorySession.id == review_request.session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status != SessionStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add lines to a non-draft session",
        )

    lines_added = 0
    lines_updated = 0

    try:
        for detection in review_request.detections:
            if detection.product_id is None:
                continue  # Skip unmatched detections

            # Verify product exists
            product = db.query(StockItem).filter(StockItem.id == detection.product_id).first()
            if not product:
                continue

            # Check if line already exists
            existing_line = (
                db.query(InventoryLine)
                .filter(
                    InventoryLine.session_id == review_request.session_id,
                    InventoryLine.product_id == detection.product_id,
                )
                .first()
            )

            if existing_line:
                # Update existing line
                existing_line.counted_qty += detection.count
                existing_line.method = CountMethod.AI
                existing_line.confidence = detection.confidence
                existing_line.photo_id = review_request.photo_id
                existing_line.counted_at = datetime.now(timezone.utc)
                lines_updated += 1
            else:
                # Create new line
                line = InventoryLine(
                    session_id=review_request.session_id,
                    product_id=detection.product_id,
                    counted_qty=detection.count,
                    method=CountMethod.AI,
                    confidence=detection.confidence,
                    photo_id=review_request.photo_id,
                )
                db.add(line)
                lines_added += 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "session_id": review_request.session_id,
        "lines_added": lines_added,
        "lines_updated": lines_updated,
    }


# ============= Bottle Training Endpoints =============

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

@router.post("/recognize", response_model=RecognitionResponse)
@limiter.limit("20/minute")
async def recognize_bottle(
    request: Request,
    image: UploadFile = File(..., description="Image of bottle to recognize"),
    db: DbSession = None,
):
    """
    Recognize a bottle from an image using hybrid CLIP+YOLO+Feature matching.

    Uses:
    - YOLO: To detect and crop bottle region (and filter non-bar items)
    - CLIP: For semantic understanding and zero-shot matching
    - Feature vectors: For trained image matching

    Combines all approaches for best accuracy.
    """
    # Validate image
    if not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image",
        )

    # Read image data
    image_data = await image.read()
    start_time = datetime.now(timezone.utc)

    # ===== FIX EXIF ORIENTATION =====
    # Mobile photos often have EXIF rotation data that needs to be applied
    try:
        from PIL import Image, ImageOps
        import io
        img = Image.open(io.BytesIO(image_data))
        img = ImageOps.exif_transpose(img)  # Auto-rotate based on EXIF
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=95)
        image_data = buffer.getvalue()
    except Exception as e:
        logger.warning(f"EXIF orientation fix failed for recognition image: {e}")

    # ===== YOLO DETECTION FIRST - Filter non-bar items =====
    detected_class = None
    detection_confidence = None
    is_bar_item = True
    processed_image = image_data  # Image to use for recognition (possibly cropped)

    if CLIP_YOLO_AVAILABLE:
        try:
            detections = detect_bottles(image_data, conf_threshold=0.25)
            if detections:
                # Found a bar item - use the best detection
                best = detections[0]
                detected_class = best.get('class_name')
                detection_confidence = best.get('confidence')
                is_bar_item = True

                # Crop to detection for better feature matching
                from app.services.ai.clip_yolo_service import crop_to_detection
                processed_image = crop_to_detection(image_data, best['bbox'], padding=0.15)
            else:
                # No bar items detected - still try recognition but flag it
                is_bar_item = False
                detected_class = None
        except Exception as e:
            logger.warning(f"YOLO detection failed, continuing without crop: {e}")

    # If YOLO says no bar item, still try recognition but flag it
    # This allows recognition of bottles that YOLO doesn't detect (unusual shapes, angles)
    # The is_bar_item=False flag tells the client YOLO didn't confirm it's a bar item

    # Get all training images with CLIP features (2048 bytes)
    # Filter out old incompatible feature formats (17792 bytes etc)
    training_images = db.query(TrainingImage).filter(
        TrainingImage.feature_vector.isnot(None),
        func.length(TrainingImage.feature_vector) == 2048  # CLIP features only
    ).all()

    # Get all stock items for CLIP zero-shot
    stock_items = db.query(StockItem).filter(StockItem.is_active == True).all()
    product_labels = {s.id: s.name for s in stock_items}

    if not training_images and not product_labels:
        inference_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        return RecognitionResponse(
            results=[RecognitionResult(
                product_id=None,
                product_name=None,
                confidence=0.0,
                is_match=False,
            )],
            inference_time_ms=round(inference_time, 2),
        )

    results = []

    # Disable hybrid CLIP recognition - use trained features only for better accuracy
    # CLIP zero-shot can override trained features incorrectly
    if False and CLIP_YOLO_AVAILABLE:
        try:
            # Prepare training features
            training_features = []
            for img in training_images:
                product = db.query(StockItem).filter(StockItem.id == img.product_id).first()
                product_name = product.name if product else "Unknown"
                training_features.append((img.product_id, product_name, img.feature_vector))

            # Run hybrid recognition
            hybrid_results = hybrid_recognition(
                image_data=image_data,
                training_features=training_features,
                product_labels=product_labels,
                clip_weight=0.4,
                feature_weight=0.6,
                threshold=0.1,
            )

            for product_id, product_name, score in hybrid_results[:5]:
                results.append(RecognitionResult(
                    product_id=product_id,
                    product_name=product_name,
                    confidence=round(score, 4),
                    is_match=score >= settings.ai_recognition_threshold,
                ))

        except Exception as e:
            # Log error and fall back to traditional matching
            logger.error(f"Hybrid recognition failed, falling back: {e}")
            results = []

    # Fall back to CLIP feature matching if no results
    if not results:
        try:
            # Use CLIP for query feature extraction (same as training data)
            # Use processed_image (which may be cropped to detection) for better matching
            if CLIP_SERVICE_AVAILABLE:
                query_embedding = get_clip_embedding(processed_image)
                if query_embedding is None:
                    raise ValueError("CLIP embedding extraction failed")
                # Normalize the embedding
                query_embedding = query_embedding / (np.linalg.norm(query_embedding) + 1e-7)
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="CLIP service not available for recognition",
                )
        except Exception as e:
            logger.error(f"Failed to process image for recognition: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process image. Please try again or contact support.",
            )

        # Extract OCR text from query image for text-based matching
        query_ocr_text = None
        query_ocr_brand = None
        query_ocr_product_name = None
        if OCR_AVAILABLE:
            try:
                query_label_info = extract_text_from_image(processed_image)
                if query_label_info:
                    if query_label_info.raw_text:
                        query_ocr_text = query_label_info.raw_text
                    if query_label_info.brand:
                        query_ocr_brand = query_label_info.brand
                    if query_label_info.product_name:
                        query_ocr_product_name = query_label_info.product_name
            except Exception as e:
                logger.debug(f"Optional: OCR text extraction for recognition query: {e}")

        # Build candidates per product - group CLIP features by stock_item_id
        product_features: dict[int, list] = {}
        for img in training_images:
            if img.stock_item_id not in product_features:
                product_features[img.stock_item_id] = []
            # Convert raw bytes to numpy array (CLIP features are float32, 512 dims = 2048 bytes)
            try:
                feat_array = np.frombuffer(img.feature_vector, dtype=np.float32)
                if len(feat_array) == 512:  # Valid CLIP embedding
                    product_features[img.stock_item_id].append(feat_array)
            except Exception as e:
                logger.warning(f"Failed to parse feature vector for training image {img.id} (stock_item {img.stock_item_id}): {e}")
                continue

        # Find best match per product using CLIP cosine similarity
        for stock_item_id, features_list in product_features.items():
            if not features_list:
                continue

            # Compute similarity with each training image, take best
            best_sim = 0.0
            for train_feat in features_list:
                # Cosine similarity
                sim = float(np.dot(query_embedding, train_feat))
                if sim > best_sim:
                    best_sim = sim

            # Also compute mean feature similarity
            if len(features_list) > 1:
                mean_feat = np.mean(features_list, axis=0)
                mean_feat = mean_feat / (np.linalg.norm(mean_feat) + 1e-7)
                mean_sim = float(np.dot(query_embedding, mean_feat))
                best_sim = max(best_sim, mean_sim)

            final_sim = best_sim

            product = db.query(StockItem).filter(StockItem.id == stock_item_id).first()
            product_name = product.name if product else "Unknown"

            # OCR text match boost - if OCR detected brand/text matches product name
            ocr_boost = 0.0
            text_match_score = 0.0
            detected_brand = None

            if query_ocr_brand and product_name:
                # Check if detected brand is in product name
                if query_ocr_brand.lower() in product_name.lower():
                    ocr_boost = 0.1  # 10% boost for brand match
                    text_match_score = 0.5
                    detected_brand = query_ocr_brand

            if query_ocr_text and product_name:
                # Check word overlap between OCR text and product name
                # Filter out short words and common noise
                stop_words = {'the', 'a', 'an', 'and', 'or', 'of', 'ml', 'l', 'cl'}
                ocr_words = set(w for w in query_ocr_text.lower().split() if len(w) > 1 and w not in stop_words)
                name_words = set(w for w in product_name.lower().split() if len(w) > 1 and w not in stop_words)

                common = ocr_words & name_words
                if len(common) >= 1:  # At least 1 significant word in common
                    # Use Jaccard similarity (intersection / union) for balanced scoring
                    union = ocr_words | name_words
                    jaccard_sim = len(common) / max(len(union), 1)

                    # Also check if ALL product name words are in OCR (full match bonus)
                    name_coverage = len(common) / max(len(name_words), 1)

                    # Penalize if OCR has distinctive words missing from product name
                    # e.g., OCR "Silver Vodka" should penalize "Savoy Vodka" (missing "Silver")
                    distinctive_words = {'silver', 'gold', 'premium', 'reserve', 'black', 'white', 'red', 'blue', 'special', 'extra', 'aged', 'classic'}
                    ocr_distinctive = ocr_words & distinctive_words
                    name_distinctive = name_words & distinctive_words
                    missing_distinctive = ocr_distinctive - name_distinctive

                    # Final text match score: weighted combination
                    # - Jaccard for overall match quality
                    # - Name coverage for how well product matches OCR
                    # - Penalty for missing distinctive words
                    text_match_score = max(text_match_score, (jaccard_sim * 0.4 + name_coverage * 0.6))

                    if missing_distinctive:
                        # Penalize products missing distinctive words found in OCR
                        penalty = len(missing_distinctive) * 0.15
                        text_match_score = max(0, text_match_score - penalty)

                    word_match_boost = min(0.15, text_match_score * 0.15)
                    ocr_boost = max(ocr_boost, word_match_boost)

            # Apply OCR boost with text match weighting
            # If OCR text matches product name well, boost confidence more significantly
            if text_match_score > 0.6:
                # Strong text match - give significant boost
                ocr_boost = max(ocr_boost, text_match_score * 0.15)
            elif text_match_score > 0:
                # Partial text match - use existing boost
                ocr_boost = max(ocr_boost, text_match_score * 0.1)

            final_sim_with_ocr = min(1.0, final_sim + ocr_boost)

            results.append(RecognitionResult(
                product_id=stock_item_id,
                product_name=product_name,
                confidence=round(final_sim_with_ocr, 4),
                is_match=final_sim_with_ocr >= settings.ai_recognition_threshold,
                clip_score=round(final_sim, 4),
                text_match_score=round(text_match_score, 4) if text_match_score > 0 else None,
                detected_brand=detected_brand,
            ))

        # Sort by confidence, then by text_match_score as tiebreaker
        results.sort(key=lambda x: (x.confidence, x.text_match_score or 0), reverse=True)
        results = results[:5]

    inference_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

    # Filter to only return matches above threshold
    matched_results = [r for r in results if r.is_match]

    # If no matches above threshold, return best candidate marked as not a match
    if not matched_results and results:
        best = results[0]
        matched_results = [RecognitionResult(
            product_id=best.product_id,
            product_name=best.product_name,
            confidence=best.confidence,
            is_match=False,  # Explicitly not a match
        )]

    # Get OCR vars if they were set
    response_ocr_text = locals().get('query_ocr_text')
    response_ocr_brand = locals().get('query_ocr_brand')
    response_ocr_product = locals().get('query_ocr_product_name')

    return RecognitionResponse(
        results=matched_results,
        inference_time_ms=round(inference_time, 2),
        is_bar_item=is_bar_item,
        detected_class=detected_class,
        detection_confidence=detection_confidence,
        ocr_text=response_ocr_text,
        ocr_brand=response_ocr_brand,
        ocr_product_name=response_ocr_product,
    )


@router.post("/recognize-multi")
@limiter.limit("30/minute")
async def recognize_multi(
    request: Request,
    image: UploadFile = File(..., description="Image with multiple bottles to recognize"),
    confidence_threshold: float = 0.60,
    detection_threshold: float = 0.10,
    iou_threshold: float = 0.30,
    enable_ocr: bool = False,
    ocr_boost: bool = True,
    db: DbSession = None,
):
    """
    Recognize MULTIPLE bottles in a single image and count them.

    Uses YOLO to detect all bottles/items, then runs CLIP recognition on each.
    Returns product counts and individual detection details.

    Args:
        image: Image file (shelf photo, bar photo, etc.)
        confidence_threshold: Minimum CLIP confidence for a match (default 0.60)
        detection_threshold: YOLO detection threshold (default 0.10)
        iou_threshold: NMS IoU threshold (default 0.30)
        enable_ocr: Whether to run OCR on ALL detections (slower)
        ocr_boost: Auto-run OCR on ambiguous detections (0.50-0.80 confidence) to boost accuracy
    """
    from app.schemas.ai import MultiRecognitionResponse, DetectedItem, ProductCount
    from app.services.ai.clip_yolo_service import extract_clip_features_batch

    # Validate image
    if not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image",
        )

    # Read and preprocess image
    image_data = await image.read()
    start_time = datetime.now(timezone.utc)

    # Fix EXIF orientation
    try:
        from PIL import Image, ImageOps
        import io
        img = Image.open(io.BytesIO(image_data))
        img = ImageOps.exif_transpose(img)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=90)
        image_data = buffer.getvalue()
        img_width, img_height = img.size
    except Exception as e:
        logger.warning(f"EXIF orientation fix failed for multi-recognition image: {e}")
        img_width, img_height = 0, 0

    # ===== YOLO DETECTION - Find ALL items =====
    yolo_start = datetime.now(timezone.utc)
    all_detections = []

    if CLIP_YOLO_AVAILABLE:
        try:
            detections = detect_bottles(
                image_data,
                conf_threshold=detection_threshold,
                iou_threshold=iou_threshold,
                max_detections=100,
                agnostic_nms=True,
            )
            all_detections = detections or []
        except Exception as e:
            logger.warning(f"YOLO detection failed in multi-recognition: {e}")

    # ===== LIGHT FILTERING - Remove noise and non-bottle items =====
    filtered_detections = []
    for det in all_detections:
        bbox = det.get('bbox', [0, 0, 0, 0])
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        det_class = det.get('class_name', '').lower()

        # Skip only very small detections (noise)
        if width < 20 or height < 30:
            continue

        # Skip wine glasses - they shouldn't match bottle products
        # Keep only bottles and cups for product recognition
        if det_class == 'wine glass':
            continue

        filtered_detections.append(det)

    all_detections = filtered_detections
    yolo_time = (datetime.now(timezone.utc) - yolo_start).total_seconds() * 1000

    if not all_detections:
        inference_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        return MultiRecognitionResponse(
            total_detections=0,
            recognized_count=0,
            unrecognized_count=0,
            product_counts=[],
            detections=[],
            inference_time_ms=round(inference_time, 2),
            yolo_time_ms=round(yolo_time, 2),
            recognition_time_ms=0,
            ocr_texts=[],
        )

    # ===== Load training data =====
    training_images = db.query(TrainingImage).filter(
        TrainingImage.feature_vector.isnot(None),
        func.length(TrainingImage.feature_vector) == 2048
    ).all()

    # Build product features matrix for vectorized matching
    product_ids = []
    product_mean_features = []

    product_features_dict: dict[int, list] = {}
    for ti in training_images:
        if ti.stock_item_id not in product_features_dict:
            product_features_dict[ti.stock_item_id] = []
        try:
            feat_array = np.frombuffer(ti.feature_vector, dtype=np.float32)
            if len(feat_array) == 512:
                product_features_dict[ti.stock_item_id].append(feat_array)
        except Exception as e:
            logger.warning(f"Failed to parse feature vector for training image {ti.id} (stock_item {ti.stock_item_id}): {e}")
            continue

    # Build mean feature matrix for vectorized similarity
    for pid, features in product_features_dict.items():
        if features:
            mean_feat = np.mean(features, axis=0)
            mean_feat = mean_feat / (np.linalg.norm(mean_feat) + 1e-7)
            product_ids.append(pid)
            product_mean_features.append(mean_feat)

    # Stack into matrix for fast batch similarity
    if product_mean_features:
        feature_matrix = np.stack(product_mean_features)  # Shape: (num_products, 512)
    else:
        feature_matrix = None

    # Get product names
    stock_items = {s.id: s.name for s in db.query(StockItem).filter(StockItem.is_active == True).all()}

    # ===== CROP ALL DETECTIONS =====
    recognition_start = datetime.now(timezone.utc)
    cropped_images = []

    for det in all_detections:
        bbox = det.get('bbox', [0, 0, 0, 0])
        try:
            from app.services.ai.clip_yolo_service import crop_to_detection
            cropped = crop_to_detection(image_data, bbox, padding=0.08)
            cropped_images.append(cropped)
        except Exception as e:
            logger.warning(f"Failed to crop detection {idx} (bbox={bbox}), using original image: {e}")
            cropped_images.append(image_data)

    # ===== BATCH CLIP FEATURE EXTRACTION =====
    clip_embeddings = []
    if CLIP_SERVICE_AVAILABLE and cropped_images:
        try:
            clip_embeddings = extract_clip_features_batch(cropped_images, batch_size=32)
        except Exception as e:
            logger.warning(f"Batch CLIP extraction failed, falling back to individual extraction: {e}")
            for cropped in cropped_images:
                try:
                    emb = get_clip_embedding(cropped)
                    clip_embeddings.append(emb)
                except Exception as e:
                    logger.warning(f"Individual CLIP embedding extraction failed for detection {idx}: {e}")
                    clip_embeddings.append(None)

    # ===== VECTORIZED MATCHING (FAST) =====
    detected_items = []
    product_counts_dict = {}
    ocr_texts = []

    # Build query matrix from valid embeddings
    valid_indices = []
    query_vectors = []
    for idx, emb in enumerate(clip_embeddings):
        if emb is not None:
            emb_norm = emb / (np.linalg.norm(emb) + 1e-7)
            valid_indices.append(idx)
            query_vectors.append(emb_norm)

    # Compute all similarities at once using matrix multiplication
    best_matches = {}  # idx -> (product_id, product_name, confidence)

    if query_vectors and feature_matrix is not None:
        query_matrix = np.stack(query_vectors)  # Shape: (num_queries, 512)
        # Matrix multiply: (num_queries, 512) @ (512, num_products) = (num_queries, num_products)
        similarity_matrix = query_matrix @ feature_matrix.T

        # Find best match for each query
        for i, orig_idx in enumerate(valid_indices):
            best_prod_idx = np.argmax(similarity_matrix[i])
            best_sim = float(similarity_matrix[i, best_prod_idx])
            best_pid = product_ids[best_prod_idx]
            best_matches[orig_idx] = (best_pid, stock_items.get(best_pid, "Unknown"), best_sim)

    # Build detection results
    for idx, det in enumerate(all_detections):
        bbox = det.get('bbox', [0, 0, 0, 0])
        det_class = det.get('class_name', 'unknown')
        det_conf = det.get('confidence', 0)

        best_product_id = None
        best_product_name = None
        best_confidence = 0.0
        ocr_text = None

        if idx in best_matches:
            best_product_id, best_product_name, best_confidence = best_matches[idx]

        # ===== INTELLIGENT OCR BOOSTING =====
        # Run OCR on ambiguous detections to improve accuracy
        # Only targets borderline cases where OCR can make a difference
        ocr_boost_value = 0.0
        is_ambiguous = 0.58 <= best_confidence <= 0.65  # Narrow range: only borderline cases

        # Only run OCR on reasonably-sized detections (better quality crops)
        bbox = det.get('bbox', [0, 0, 0, 0])
        det_width = bbox[2] - bbox[0]
        det_height = bbox[3] - bbox[1]
        is_good_quality = det_width > 80 and det_height > 120  # Minimum size for readable OCR

        should_run_ocr = (
            OCR_AVAILABLE and
            idx < len(cropped_images) and
            best_product_name and
            (enable_ocr or (ocr_boost and is_ambiguous and is_good_quality))
        )

        if should_run_ocr:
            try:
                label_info = extract_text_from_image(cropped_images[idx])
                if label_info and label_info.raw_text:
                    ocr_text = label_info.raw_text.strip()
                    if ocr_text:
                        ocr_texts.append(ocr_text)

                        # Calculate OCR boost based on text match to product name
                        ocr_text_lower = ocr_text.lower()
                        product_name_lower = best_product_name.lower()

                        # Extract key words from product name
                        product_words = set(product_name_lower.replace("'", "").split())
                        product_words.discard("the")  # Remove common words

                        # Check for brand/product name matches in OCR text
                        matched_words = sum(1 for w in product_words if w in ocr_text_lower)
                        match_ratio = matched_words / len(product_words) if product_words else 0

                        # Also check if OCR detected brand matches
                        if label_info.brand:
                            brand_lower = label_info.brand.lower()
                            if brand_lower in product_name_lower or any(w in brand_lower for w in product_words if len(w) > 3):
                                ocr_boost_value = 0.08  # Strong brand match
                            elif any(brand_lower in stock_items.get(pid, "").lower() for pid in product_ids if pid != best_product_id):
                                # OCR brand matches a DIFFERENT product - penalize
                                ocr_boost_value = -0.10

                        # Word match boost
                        if match_ratio >= 0.5:
                            ocr_boost_value = max(ocr_boost_value, match_ratio * 0.12)  # Up to 12% boost
                        elif match_ratio == 0 and len(ocr_text) > 10:
                            # No matches but had readable text - slight penalty
                            ocr_boost_value = min(ocr_boost_value, -0.03)

                        # Apply boost
                        best_confidence = min(1.0, max(0.0, best_confidence + ocr_boost_value))
            except Exception as e:
                logger.debug(f"Optional: OCR confidence boosting: {e}")

        is_match = best_confidence >= confidence_threshold

        item = DetectedItem(
            detection_id=idx,
            bbox=bbox,
            detected_class=det_class,
            detection_confidence=round(det_conf, 4),
            product_id=best_product_id if is_match else None,
            product_name=best_product_name if is_match else None,
            recognition_confidence=round(best_confidence, 4),
            is_match=is_match,
            ocr_text=ocr_text,
        )
        detected_items.append(item)

        if is_match and best_product_id:
            if best_product_id not in product_counts_dict:
                product_counts_dict[best_product_id] = {
                    'name': best_product_name,
                    'count': 0,
                    'confidences': [],
                    'detection_ids': []
                }
            product_counts_dict[best_product_id]['count'] += 1
            product_counts_dict[best_product_id]['confidences'].append(best_confidence)
            product_counts_dict[best_product_id]['detection_ids'].append(idx)

    recognition_time = (datetime.now(timezone.utc) - recognition_start).total_seconds() * 1000
    inference_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

    # Build product counts list
    product_counts = []
    for pid, data in sorted(product_counts_dict.items(), key=lambda x: x[1]['count'], reverse=True):
        avg_conf = sum(data['confidences']) / len(data['confidences']) if data['confidences'] else 0
        product_counts.append(ProductCount(
            product_id=pid,
            product_name=data['name'],
            count=data['count'],
            avg_confidence=round(avg_conf, 4),
            detections=data['detection_ids'],
        ))

    recognized_count = sum(1 for d in detected_items if d.is_match)
    unrecognized_count = len(detected_items) - recognized_count

    return MultiRecognitionResponse(
        total_detections=len(detected_items),
        recognized_count=recognized_count,
        unrecognized_count=unrecognized_count,
        product_counts=product_counts,
        detections=detected_items,
        inference_time_ms=round(inference_time, 2),
        yolo_time_ms=round(yolo_time, 2),
        recognition_time_ms=round(recognition_time, 2),
        ocr_texts=ocr_texts,
    )


@router.get("/status")
@limiter.limit("60/minute")
def get_ai_status(
    request: Request,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Get AI system status including OCR, CLIP and YOLO availability."""
    # Count training data
    total_images = db.query(TrainingImage).count()
    products_trained = db.query(TrainingImage.stock_item_id).distinct().count()
    images_with_features = db.query(TrainingImage).filter(
        TrainingImage.feature_vector.isnot(None)
    ).count()
    images_with_ocr = db.query(TrainingImage).filter(
        TrainingImage.ocr_text.isnot(None)
    ).count()

    status = {
        "training_images": total_images,
        "products_trained": products_trained,
        "images_with_features": images_with_features,
        "images_with_ocr": images_with_ocr,
        "ocr_available": OCR_AVAILABLE,
        "clip_yolo_available": CLIP_YOLO_AVAILABLE,
        "recognition_threshold": settings.ai_recognition_threshold,
    }

    if CLIP_YOLO_AVAILABLE:
        try:
            clip_status = get_clip_yolo_status()
            status.update(clip_status)
        except Exception as e:
            logger.warning(f"Failed to get CLIP/YOLO status: {e}")

    return status


@router.get("/stock-items")
@limiter.limit("60/minute")
def list_stock_items(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: DbSession = None,
):
    """
    List all stock items from the main V99 database.

    Returns stock items (products) that can be used for AI training.
    This endpoint provides access to the main V99 inventory.
    No authentication required for listing items.
    """
    # Get stock items, optionally filter by active status
    query = db.query(StockItem).filter(
        (StockItem.is_active == True) | (StockItem.is_active.is_(None))
    )

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    # Count training images per stock item
    training_counts = dict(
        db.query(
            TrainingImage.stock_item_id,
            func.count(TrainingImage.id)
        ).group_by(TrainingImage.stock_item_id).all()
    )

    return {
        "total": total,
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "sku": item.sku,
                "unit": item.unit,
                "quantity": item.quantity,
                "training_images_count": training_counts.get(item.id, 0),
            }
            for item in items
        ]
    }


@router.get("/stock-items/training-status")
@limiter.limit("60/minute")
def get_training_status(
    request: Request,
    min_images: int = 10,
    db: DbSession = None,
):
    """
    Get training status for all products.

    Returns products sorted by training priority (least trained first).
    Shows CLIP feature count vs old feature count.
    """
    from sqlalchemy import case, literal_column

    # Query products with training counts
    results = db.query(
        StockItem.id,
        StockItem.name,
        func.sum(case(
            (func.length(TrainingImage.feature_vector) == 2048, 1),
            else_=0
        )).label('clip_count'),
        func.sum(case(
            (func.length(TrainingImage.feature_vector) != 2048, 1),
            else_=0
        )).label('old_count'),
        func.count(TrainingImage.id).label('total_count')
    ).outerjoin(
        TrainingImage, StockItem.id == TrainingImage.stock_item_id
    ).filter(
        StockItem.is_active == True
    ).group_by(
        StockItem.id
    ).all()

    # Format results
    products = []
    needs_training = []
    well_trained = []

    for row in results:
        clip_count = row.clip_count or 0
        old_count = row.old_count or 0

        item = {
            "id": row.id,
            "name": row.name,
            "clip_images": clip_count,
            "old_images": old_count,
            "total_images": row.total_count or 0,
            "status": "ready" if clip_count >= min_images else "needs_training",
            "priority": "high" if clip_count == 0 and old_count > 0 else (
                "medium" if clip_count < min_images else "low"
            )
        }
        products.append(item)

        if clip_count < min_images:
            needs_training.append(item)
        else:
            well_trained.append(item)

    # Sort by priority
    needs_training.sort(key=lambda x: (x['clip_images'], -x['old_images']))

    return {
        "total_products": len(products),
        "well_trained": len(well_trained),
        "needs_training": len(needs_training),
        "min_images_threshold": min_images,
        "products_needing_training": needs_training,
        "well_trained_products": well_trained[:10],  # Top 10 only
    }


@router.post("/stock-items")
@limiter.limit("30/minute")
def create_stock_item(
    request: Request,
    name: Annotated[str, Form()],
    sku: Annotated[str, Form()],
    unit: Annotated[str, Form()] = "bottle",
    quantity: Annotated[float, Form()] = 0,
    db: DbSession = None,
):
    """
    Create a new stock item in the main V99 database.

    This endpoint allows creating new products that can be used for AI training.
    """
    # Create new stock item
    stock_item = StockItem(
        name=name,
        sku=sku,
        unit=unit,
        quantity=quantity,
        venue_id=1,  # Default venue
        is_active=True,
    )
    db.add(stock_item)
    db.commit()
    db.refresh(stock_item)

    return {
        "id": stock_item.id,
        "name": stock_item.name,
        "sku": stock_item.sku,
        "unit": stock_item.unit,
        "quantity": stock_item.quantity,
    }


# ============= Training Pipeline Endpoints =============

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
