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


# Ensure training images directory exists
TRAINING_DIR = Path(settings.ai_training_images_path)
TRAINING_DIR.mkdir(parents=True, exist_ok=True)


# Allowed image MIME types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

