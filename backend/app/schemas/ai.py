"""AI shelf scanning schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field


class Detection(BaseModel):
    """A single detection from AI shelf scan."""

    product_id: Optional[int] = None  # Mapped product ID, None if not in catalog
    label: str  # Detected label/class name
    count: int = Field(ge=1)
    confidence: Decimal = Field(ge=0, le=1)
    bbox: Optional[List[float]] = None  # [x1, y1, x2, y2] if available


class ShelfScanRequest(BaseModel):
    """Request for shelf scan (image sent as multipart form data)."""

    session_id: Optional[int] = None  # Optional inventory session to associate with
    store_photo: bool = False  # Whether to persist the photo


class ShelfScanResponse(BaseModel):
    """Response from shelf scan endpoint."""

    detections: List[Detection]
    meta: dict  # {"model": "...", "ts": "...", "inference_time_ms": ...}
    photo_id: Optional[int] = None  # If photo was stored


class ShelfScanReviewRequest(BaseModel):
    """Request to confirm/edit AI detections before adding to session."""

    session_id: int
    detections: List[Detection]  # User-reviewed detections
    photo_id: Optional[int] = None


class TrainingImageCreate(BaseModel):
    """Request to add a training image."""

    product_id: int


class TrainingImageResponse(BaseModel):
    """Response after creating a training image."""

    id: int
    product_id: int
    product_name: str
    created_at: datetime
    is_verified: bool = False


class TrainingStatsResponse(BaseModel):
    """Training statistics."""

    total_images: int
    products_trained: int
    images_per_product: dict  # {product_id: count}


class RecognitionResult(BaseModel):
    """Result of bottle recognition."""

    product_id: Optional[int] = None
    product_name: Optional[str] = None
    confidence: float
    is_match: bool = False

    # Score breakdown from combined recognition
    clip_score: Optional[float] = None
    ocr_score: Optional[float] = None
    text_match_score: Optional[float] = None

    # OCR info
    detected_brand: Optional[str] = None


class RecognitionResponse(BaseModel):
    """Response from recognition endpoint."""

    results: List[RecognitionResult]
    inference_time_ms: float
    session_id: Optional[str] = None  # For confirming/feedback to enable active learning
    is_bar_item: bool = True  # False if YOLO detection found no bar items
    detected_class: Optional[str] = None  # What YOLO detected (bottle, can, wine glass, etc.)
    detection_confidence: Optional[float] = None  # YOLO detection confidence

    # OCR info from query image
    ocr_text: Optional[str] = None  # Raw text extracted from label
    ocr_brand: Optional[str] = None  # Detected brand name
    ocr_product_name: Optional[str] = None  # Detected product name


class RecognitionConfirmRequest(BaseModel):
    """Request to confirm a recognition result for active learning."""

    session_id: str  # From recognition response
    product_id: int  # Confirmed product ID
    is_correct: bool = True  # Whether the recognition was correct


class RecognitionConfirmResponse(BaseModel):
    """Response after confirming recognition."""

    success: bool
    message: str
    training_image_id: Optional[int] = None  # ID of new training image if created


# ============= Multi-Recognition Schemas =============

class DetectedItem(BaseModel):
    """A single detected item with its recognition result."""

    detection_id: int  # Index of detection
    bbox: List[float]  # [x1, y1, x2, y2]
    detected_class: str  # bottle, cup, wine glass, etc.
    detection_confidence: float

    # Recognition result for this item
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    recognition_confidence: float = 0.0
    is_match: bool = False

    # OCR info for this item
    ocr_text: Optional[str] = None


class ProductCount(BaseModel):
    """Count of a recognized product."""

    product_id: int
    product_name: str
    count: int
    avg_confidence: float
    detections: List[int]  # List of detection_ids


class MultiRecognitionResponse(BaseModel):
    """Response from multi-recognition endpoint."""

    total_detections: int  # Total items detected by YOLO
    recognized_count: int  # Items successfully recognized
    unrecognized_count: int  # Items not recognized (confidence too low)

    # Counts per product
    product_counts: List[ProductCount]

    # Individual detections with details
    detections: List[DetectedItem]

    # Processing info
    inference_time_ms: float
    yolo_time_ms: float
    recognition_time_ms: float

    # OCR summary
    ocr_texts: List[str]  # All OCR texts found
