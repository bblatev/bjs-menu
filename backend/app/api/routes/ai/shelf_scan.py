"""AI shelf scanning & review"""
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

