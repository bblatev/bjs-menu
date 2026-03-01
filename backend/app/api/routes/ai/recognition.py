"""AI bottle recognition & stock items"""
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
