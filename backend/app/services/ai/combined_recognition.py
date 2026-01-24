"""Combined OCR + YOLO + CLIP Recognition Service.

This module provides enhanced bottle recognition by combining:
- YOLO: Object detection to locate and crop bottles
- CLIP: Semantic visual features for image matching
- OCR: Text extraction from labels for text-based matching

The combined approach provides:
- Better accuracy through multi-modal matching
- Fallback mechanisms when one method fails
- Confidence boosting when multiple methods agree
"""

import io
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
import numpy as np
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Import services
try:
    from app.services.ai.clip_yolo_service import (
        detect_bottles,
        crop_to_detection,
        extract_clip_features,
        compute_clip_similarity,
        _CLIP_AVAILABLE,
        _YOLO_AVAILABLE,
    )
    CLIP_YOLO_AVAILABLE = _CLIP_AVAILABLE or _YOLO_AVAILABLE
except ImportError:
    CLIP_YOLO_AVAILABLE = False
    logger.warning("CLIP/YOLO service not available")

try:
    from app.services.ai.ocr_service import (
        extract_text_from_image,
        compute_label_similarity,
        fuzzy_match,
        LabelInfo,
        _OCR_AVAILABLE,
    )
    OCR_AVAILABLE = _OCR_AVAILABLE
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR service not available")


@dataclass
class RecognitionCandidate:
    """A candidate product match with scores from different methods."""
    product_id: int
    product_name: str

    # Individual scores
    clip_score: float = 0.0
    ocr_score: float = 0.0
    text_match_score: float = 0.0  # Direct name matching via OCR

    # Combined score
    combined_score: float = 0.0

    # Metadata
    ocr_text: Optional[str] = None
    detected_brand: Optional[str] = None
    detection_class: Optional[str] = None
    detection_confidence: float = 0.0


@dataclass
class CombinedRecognitionResult:
    """Result from combined recognition."""
    candidates: List[RecognitionCandidate] = field(default_factory=list)

    # Detection info
    is_bar_item: bool = True
    detected_class: Optional[str] = None
    detection_confidence: float = 0.0

    # OCR info
    ocr_text: Optional[str] = None
    ocr_brand: Optional[str] = None
    ocr_product_name: Optional[str] = None

    # Processing info
    yolo_used: bool = False
    clip_used: bool = False
    ocr_used: bool = False

    inference_time_ms: float = 0.0


def extract_ocr_from_detection(
    image_data: bytes,
    bbox: Optional[List[int]] = None,
    padding: float = 0.1
) -> Optional[LabelInfo]:
    """Extract OCR from image, optionally cropping to detection first."""
    if not OCR_AVAILABLE:
        return None

    try:
        if bbox:
            # Crop to detection for better OCR
            cropped = crop_to_detection(image_data, bbox, padding=padding)
            return extract_text_from_image(cropped)
        else:
            return extract_text_from_image(image_data)
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return None


def match_ocr_to_products(
    ocr_info: LabelInfo,
    products: List[Dict[str, Any]],
    threshold: float = 0.5
) -> List[Tuple[int, str, float]]:
    """Match OCR text against product names.

    Returns list of (product_id, product_name, score) sorted by score.
    """
    if not ocr_info or not ocr_info.raw_text:
        return []

    matches = []
    ocr_text_lower = ocr_info.raw_text.lower()

    for product in products:
        product_id = product.get('id')
        product_name = product.get('name', '')

        if not product_name:
            continue

        score = 0.0

        # 1. Check brand match (high weight)
        if ocr_info.brand:
            brand_lower = ocr_info.brand.lower()
            name_lower = product_name.lower()

            # Exact brand in product name
            if brand_lower in name_lower:
                score += 0.4
            else:
                # Fuzzy brand match
                is_match, fuzzy_score = fuzzy_match(brand_lower, name_lower, threshold=0.7)
                if is_match:
                    score += 0.3 * fuzzy_score

        # 2. Check product name similarity
        name_lower = product_name.lower()

        # Check if product name words appear in OCR
        name_words = set(name_lower.split())
        ocr_words = set(ocr_text_lower.split())

        common_words = name_words & ocr_words
        if common_words:
            word_overlap = len(common_words) / max(len(name_words), 1)
            score += 0.3 * word_overlap

        # 3. Check distinguishing words match
        if ocr_info.distinguishing_words:
            for dw in ocr_info.distinguishing_words:
                if dw in name_lower:
                    score += 0.1
                    break

        # 4. Fuzzy full name match
        is_match, fuzzy_score = fuzzy_match(ocr_text_lower, name_lower, threshold=0.6)
        if is_match:
            score += 0.2 * fuzzy_score

        if score >= threshold:
            matches.append((product_id, product_name, score))

    # Sort by score descending
    matches.sort(key=lambda x: x[2], reverse=True)
    return matches[:10]  # Top 10


def combined_recognize(
    image_data: bytes,
    training_data: List[Tuple[int, str, bytes, Optional[str]]],  # (id, name, features, ocr_text)
    products: List[Dict[str, Any]],
    clip_weight: float = 0.5,
    ocr_weight: float = 0.3,
    text_match_weight: float = 0.2,
    threshold: float = 0.5,
    use_yolo: bool = True,
    use_ocr: bool = True,
) -> CombinedRecognitionResult:
    """
    Combined recognition using YOLO + CLIP + OCR.

    Pipeline:
    1. YOLO detection - locate and classify bar items
    2. Crop to detection (if found)
    3. CLIP feature extraction and matching
    4. OCR text extraction and matching
    5. Combine scores with weighted average

    Args:
        image_data: Raw image bytes
        training_data: List of (product_id, product_name, feature_vector, ocr_text)
        products: List of product dicts with 'id' and 'name'
        clip_weight: Weight for CLIP similarity scores
        ocr_weight: Weight for OCR-to-OCR similarity
        text_match_weight: Weight for direct OCR-to-product-name matching
        threshold: Minimum combined score threshold
        use_yolo: Whether to use YOLO detection
        use_ocr: Whether to use OCR

    Returns:
        CombinedRecognitionResult with candidates and metadata
    """
    result = CombinedRecognitionResult()

    processed_image = image_data
    detection_bbox = None

    # ===== Step 1: YOLO Detection =====
    if use_yolo and CLIP_YOLO_AVAILABLE:
        try:
            detections = detect_bottles(image_data, conf_threshold=0.25)
            if detections:
                best = detections[0]
                result.is_bar_item = True
                result.detected_class = best.get('class_name')
                result.detection_confidence = best.get('confidence', 0.0)
                detection_bbox = best.get('bbox')

                # Crop for better feature extraction
                processed_image = crop_to_detection(image_data, detection_bbox, padding=0.15)
                result.yolo_used = True
            else:
                # No bar item detected
                result.is_bar_item = False
                return result
        except Exception as e:
            logger.error(f"YOLO detection failed: {e}")

    # ===== Step 2: OCR Extraction =====
    query_ocr: Optional[LabelInfo] = None
    if use_ocr and OCR_AVAILABLE:
        try:
            query_ocr = extract_ocr_from_detection(image_data, detection_bbox)
            if query_ocr and query_ocr.raw_text:
                result.ocr_text = query_ocr.raw_text
                result.ocr_brand = query_ocr.brand
                result.ocr_product_name = query_ocr.product_name
                result.ocr_used = True
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")

    # ===== Step 3: CLIP Feature Extraction =====
    query_clip_features = None
    if CLIP_YOLO_AVAILABLE:
        try:
            query_clip_features = extract_clip_features(processed_image)
            if query_clip_features is not None:
                result.clip_used = True
        except Exception as e:
            logger.error(f"CLIP feature extraction failed: {e}")

    # ===== Step 4: Score Candidates =====
    candidates_map: Dict[int, RecognitionCandidate] = {}

    # Initialize candidates from products
    for product in products:
        pid = product.get('id')
        pname = product.get('name', '')
        if pid and pname:
            candidates_map[pid] = RecognitionCandidate(
                product_id=pid,
                product_name=pname,
                detection_class=result.detected_class,
                detection_confidence=result.detection_confidence,
            )

    # 4a. CLIP similarity scoring
    if query_clip_features is not None and training_data:
        import pickle

        for product_id, product_name, feat_bytes, stored_ocr in training_data:
            if feat_bytes and product_id in candidates_map:
                try:
                    stored_features = pickle.loads(feat_bytes)

                    # Compute cosine similarity
                    dot_product = np.dot(query_clip_features, stored_features)
                    norm1 = np.linalg.norm(query_clip_features)
                    norm2 = np.linalg.norm(stored_features)

                    if norm1 > 1e-7 and norm2 > 1e-7:
                        clip_sim = float(dot_product / (norm1 * norm2))
                        clip_sim = max(0.0, min(1.0, clip_sim))
                        candidates_map[product_id].clip_score = max(
                            candidates_map[product_id].clip_score,
                            clip_sim
                        )
                except Exception as e:
                    logger.debug(f"CLIP similarity failed for product {product_id}: {e}")

    # 4b. OCR similarity scoring (if we have OCR for both query and stored)
    if query_ocr and query_ocr.raw_text and training_data:
        for product_id, product_name, feat_bytes, stored_ocr in training_data:
            if stored_ocr and product_id in candidates_map:
                try:
                    # Create LabelInfo from stored OCR text
                    stored_label = LabelInfo(raw_text=stored_ocr)

                    # Compute OCR similarity
                    ocr_sim = compute_label_similarity(query_ocr, stored_label, use_semantic=False)
                    candidates_map[product_id].ocr_score = max(
                        candidates_map[product_id].ocr_score,
                        ocr_sim
                    )
                except Exception as e:
                    logger.debug(f"OCR similarity failed for product {product_id}: {e}")

    # 4c. Direct text match scoring (OCR text vs product name)
    if query_ocr and query_ocr.raw_text:
        text_matches = match_ocr_to_products(query_ocr, products, threshold=0.2)
        for product_id, product_name, score in text_matches:
            if product_id in candidates_map:
                candidates_map[product_id].text_match_score = score
                candidates_map[product_id].ocr_text = query_ocr.raw_text
                candidates_map[product_id].detected_brand = query_ocr.brand

    # ===== Step 5: Combine Scores =====
    for candidate in candidates_map.values():
        # Weighted combination
        combined = (
            candidate.clip_score * clip_weight +
            candidate.ocr_score * ocr_weight +
            candidate.text_match_score * text_match_weight
        )

        # Boost if multiple methods agree
        methods_agreeing = sum([
            candidate.clip_score > 0.5,
            candidate.ocr_score > 0.5,
            candidate.text_match_score > 0.3,
        ])

        if methods_agreeing >= 2:
            combined *= 1.15  # 15% boost for agreement

        candidate.combined_score = min(1.0, combined)

    # Filter and sort
    result.candidates = [
        c for c in candidates_map.values()
        if c.combined_score >= threshold
    ]
    result.candidates.sort(key=lambda x: x.combined_score, reverse=True)

    # Limit to top 10
    result.candidates = result.candidates[:10]

    return result


def get_combined_status() -> Dict[str, Any]:
    """Get status of combined recognition services."""
    return {
        "clip_yolo_available": CLIP_YOLO_AVAILABLE,
        "ocr_available": OCR_AVAILABLE,
        "combined_available": CLIP_YOLO_AVAILABLE or OCR_AVAILABLE,
    }
