"""CLIP + YOLOv8 Integration for Enhanced Bottle Recognition.

This module combines:
- CLIP: For semantic feature extraction and text-guided similarity
- YOLOv8: For object detection to isolate bottles before feature extraction

Together they provide more robust recognition than CNN features alone.
"""

import io
import logging
import pickle
from app.core.safe_pickle import safe_loads
from typing import Optional, List, Tuple, Dict, Any
import numpy as np
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Lazy-loaded models
_CLIP_MODEL = None
_CLIP_PREPROCESS = None
_YOLO_MODEL = None
_CLIP_AVAILABLE = False
_YOLO_AVAILABLE = False

# Try to import CLIP
try:
    import clip
    import torch
    _CLIP_AVAILABLE = True
    logger.info("CLIP available for semantic features")
except ImportError as e:
    logger.warning(f"CLIP not available: {e}")

# Try to import YOLOv8
try:
    from ultralytics import YOLO
    _YOLO_AVAILABLE = True
    logger.info("YOLOv8 available for object detection")
except ImportError as e:
    logger.warning(f"YOLOv8 not available: {e}")


def _get_clip_model():
    """Lazy load CLIP model."""
    global _CLIP_MODEL, _CLIP_PREPROCESS

    if not _CLIP_AVAILABLE:
        return None, None

    if _CLIP_MODEL is None:
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            # Use ViT-B/32 for good balance of speed and accuracy
            _CLIP_MODEL, _CLIP_PREPROCESS = clip.load("ViT-B/32", device=device)
            _CLIP_MODEL.eval()
            logger.info(f"CLIP model loaded on {device}")
        except Exception as e:
            logger.error(f"Failed to load CLIP: {e}")
            return None, None

    return _CLIP_MODEL, _CLIP_PREPROCESS


def _get_yolo_model():
    """Lazy load YOLOv8 model."""
    global _YOLO_MODEL

    if not _YOLO_AVAILABLE:
        return None

    if _YOLO_MODEL is None:
        try:
            # Use YOLOv8 nano for speed - can detect bottles in 'bottle' class
            _YOLO_MODEL = YOLO('yolov8n.pt')
            logger.info("YOLOv8 model loaded")
        except Exception as e:
            logger.error(f"Failed to load YOLOv8: {e}")
            return None

    return _YOLO_MODEL


def detect_bottles(
    image_data: bytes,
    conf_threshold: float = 0.3,
    iou_threshold: float = 0.4,
    max_detections: int = 100,
    agnostic_nms: bool = True,
) -> List[Dict[str, Any]]:
    """Detect bottles in an image using YOLOv8 with tunable NMS.

    Args:
        image_data: Raw image bytes
        conf_threshold: Minimum confidence threshold (lower = more detections)
        iou_threshold: IoU threshold for NMS (lower = fewer overlapping boxes)
        max_detections: Maximum number of detections to return
        agnostic_nms: If True, NMS is class-agnostic (better for similar objects)

    Returns:
        List of detected bottles with bounding boxes and confidence
    """
    model = _get_yolo_model()
    if model is None:
        return []

    try:
        image = Image.open(io.BytesIO(image_data))
        image = ImageOps.exif_transpose(image)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Run detection with tuned NMS parameters
        results = model(
            image,
            verbose=False,
            conf=conf_threshold,
            iou=iou_threshold,
            max_det=max_detections,
            agnostic_nms=agnostic_nms,
            classes=[39, 40, 41],  # bottle, wine glass, cup
        )

        detections = []
        for result in results:
            boxes = result.boxes
            for i, box in enumerate(boxes):
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                # Filter very small detections (likely noise)
                width = x2 - x1
                height = y2 - y1
                if width < 20 or height < 30:
                    continue

                detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'confidence': conf,
                    'class_id': cls_id,
                    'class_name': model.names[cls_id]
                })

        # Sort by confidence
        detections.sort(key=lambda x: x['confidence'], reverse=True)
        return detections[:max_detections]

    except Exception as e:
        logger.error(f"YOLO detection failed: {e}")
        return []


def crop_to_detection(image_data: bytes, bbox: List[int], padding: float = 0.1) -> bytes:
    """Crop image to a detection bounding box with padding.

    Args:
        image_data: Raw image bytes
        bbox: [x1, y1, x2, y2] bounding box
        padding: Percentage of padding to add around the box

    Returns:
        Cropped image bytes
    """
    try:
        image = Image.open(io.BytesIO(image_data))
        image = ImageOps.exif_transpose(image)
        if image.mode != "RGB":
            image = image.convert("RGB")

        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1

        # Add padding
        pad_w = int(width * padding)
        pad_h = int(height * padding)

        x1 = max(0, x1 - pad_w)
        y1 = max(0, y1 - pad_h)
        x2 = min(image.width, x2 + pad_w)
        y2 = min(image.height, y2 + pad_h)

        cropped = image.crop((x1, y1, x2, y2))

        buffer = io.BytesIO()
        cropped.save(buffer, format="JPEG", quality=95)
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"Crop failed: {e}")
        return image_data


def extract_clip_features(image_data: bytes) -> Optional[np.ndarray]:
    """Extract CLIP image features.

    Returns 512-dimensional semantic feature vector.
    """
    model, preprocess = _get_clip_model()
    if model is None:
        return None

    try:
        import torch

        image = Image.open(io.BytesIO(image_data))
        image = ImageOps.exif_transpose(image)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Preprocess for CLIP
        device = next(model.parameters()).device
        image_input = preprocess(image).unsqueeze(0).to(device)

        # Extract features
        with torch.no_grad():
            image_features = model.encode_image(image_input)

        # Normalize
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        return image_features.cpu().numpy().flatten().astype(np.float32)

    except Exception as e:
        logger.error(f"CLIP feature extraction failed: {e}")
        return None


def extract_clip_features_batch(image_data_list: List[bytes], batch_size: int = 16) -> List[Optional[np.ndarray]]:
    """Extract CLIP features for multiple images in batches (much faster).

    Args:
        image_data_list: List of image bytes
        batch_size: Number of images to process at once

    Returns:
        List of 512-dimensional feature vectors (None if extraction failed)
    """
    model, preprocess = _get_clip_model()
    if model is None:
        return [None] * len(image_data_list)

    results = [None] * len(image_data_list)

    try:
        import torch

        device = next(model.parameters()).device

        # Preprocess all images
        preprocessed = []
        valid_indices = []

        for idx, image_data in enumerate(image_data_list):
            try:
                image = Image.open(io.BytesIO(image_data))
                image = ImageOps.exif_transpose(image)
                if image.mode != "RGB":
                    image = image.convert("RGB")
                preprocessed.append(preprocess(image))
                valid_indices.append(idx)
            except Exception as e:
                logger.debug(f"Failed to preprocess image {idx}: {e}")
                continue

        if not preprocessed:
            return results

        # Process in batches
        for batch_start in range(0, len(preprocessed), batch_size):
            batch_end = min(batch_start + batch_size, len(preprocessed))
            batch_images = preprocessed[batch_start:batch_end]
            batch_indices = valid_indices[batch_start:batch_end]

            # Stack into batch tensor
            image_batch = torch.stack(batch_images).to(device)

            # Extract features
            with torch.no_grad():
                batch_features = model.encode_image(image_batch)

            # Normalize
            batch_features = batch_features / batch_features.norm(dim=-1, keepdim=True)
            batch_features = batch_features.cpu().numpy().astype(np.float32)

            # Store results
            for i, orig_idx in enumerate(batch_indices):
                results[orig_idx] = batch_features[i]

        return results

    except Exception as e:
        logger.error(f"Batch CLIP extraction failed: {e}")
        return results


def extract_clip_text_similarity(image_data: bytes, labels: List[str]) -> Dict[str, float]:
    """Compute similarity between image and text labels using CLIP.

    This enables zero-shot recognition based on product names/descriptions.

    Args:
        image_data: Raw image bytes
        labels: List of text labels to compare against

    Returns:
        Dict mapping label to similarity score
    """
    model, preprocess = _get_clip_model()
    if model is None or not labels:
        return {}

    try:
        import torch

        image = Image.open(io.BytesIO(image_data))
        image = ImageOps.exif_transpose(image)
        if image.mode != "RGB":
            image = image.convert("RGB")

        device = next(model.parameters()).device

        # Prepare image
        image_input = preprocess(image).unsqueeze(0).to(device)

        # Prepare text - add context for better matching
        text_prompts = [f"a photo of {label}" for label in labels]
        text_tokens = clip.tokenize(text_prompts).to(device)

        # Compute features
        with torch.no_grad():
            image_features = model.encode_image(image_input)
            text_features = model.encode_text(text_tokens)

        # Normalize
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        # Compute similarity
        similarity = (image_features @ text_features.T).squeeze(0)

        # Convert to probabilities using softmax with temperature
        probs = (similarity * 100).softmax(dim=0)

        return {label: float(prob) for label, prob in zip(labels, probs)}

    except Exception as e:
        logger.error(f"CLIP text similarity failed: {e}")
        return {}


def extract_enhanced_features(
    image_data: bytes,
    use_yolo_crop: bool = True,
    use_clip: bool = True,
) -> bytes:
    """Extract enhanced features using CLIP + YOLO.

    Pipeline:
    1. Use YOLO to detect bottle region (if enabled)
    2. Crop to bottle (improves feature quality)
    3. Extract CLIP features (semantic understanding)
    4. Combine into feature vector

    Args:
        image_data: Raw image bytes
        use_yolo_crop: Whether to use YOLO to crop to bottle
        use_clip: Whether to use CLIP features

    Returns:
        Pickled feature vector
    """
    processed_image = image_data

    # Step 1: YOLO detection and cropping
    if use_yolo_crop and _YOLO_AVAILABLE:
        detections = detect_bottles(image_data)
        if detections:
            # Use the most confident detection
            best_detection = detections[0]
            processed_image = crop_to_detection(image_data, best_detection['bbox'])
            logger.debug(f"Cropped to bottle: {best_detection['class_name']} ({best_detection['confidence']:.2f})")

    # Step 2: Extract CLIP features
    clip_features = None
    if use_clip and _CLIP_AVAILABLE:
        clip_features = extract_clip_features(processed_image)

    # Step 3: Combine features
    if clip_features is not None:
        # CLIP gives 512-dimensional features
        features = clip_features
    else:
        # Fallback: extract basic features
        from app.services.ai.feature_extraction import extract_combined_features
        return extract_combined_features(processed_image)

    # Normalize
    features = features / (np.linalg.norm(features) + 1e-7)

    return pickle.dumps(features.astype(np.float32))


def compute_clip_similarity(features1: bytes, features2: bytes) -> float:
    """Compute cosine similarity between CLIP feature vectors."""
    try:
        vec1 = safe_loads(features1)
        vec2 = safe_loads(features2)

        # Handle different lengths (shouldn't happen with pure CLIP)
        min_len = min(len(vec1), len(vec2))
        vec1 = vec1[:min_len]
        vec2 = vec2[:min_len]

        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 < 1e-7 or norm2 < 1e-7:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(max(0.0, min(1.0, similarity)))

    except Exception as e:
        logger.error(f"Similarity computation failed: {e}")
        return 0.0


def recognize_with_clip_text(
    image_data: bytes,
    product_labels: Dict[int, str],
    threshold: float = 0.1
) -> List[Tuple[int, str, float]]:
    """Zero-shot recognition using CLIP text matching.

    This doesn't require any training images - it matches based on product names.

    Args:
        image_data: Image to recognize
        product_labels: Dict mapping product_id to product name
        threshold: Minimum probability threshold

    Returns:
        List of (product_id, product_name, probability) sorted by probability
    """
    if not product_labels:
        return []

    # Detect and crop bottle first
    if _YOLO_AVAILABLE:
        detections = detect_bottles(image_data)
        if detections:
            image_data = crop_to_detection(image_data, detections[0]['bbox'])

    # Get CLIP text similarities
    labels = list(product_labels.values())
    similarities = extract_clip_text_similarity(image_data, labels)

    # Map back to product IDs
    results = []
    for product_id, product_name in product_labels.items():
        prob = similarities.get(product_name, 0.0)
        if prob >= threshold:
            results.append((product_id, product_name, prob))

    # Sort by probability descending
    results.sort(key=lambda x: x[2], reverse=True)

    return results


def hybrid_recognition(
    image_data: bytes,
    training_features: List[Tuple[int, str, bytes]],
    product_labels: Dict[int, str],
    clip_weight: float = 0.4,
    feature_weight: float = 0.6,
    threshold: float = 0.5
) -> List[Tuple[int, str, float]]:
    """Hybrid recognition combining trained features + CLIP zero-shot.

    This provides the best of both worlds:
    - Feature matching works well when you have good training data
    - CLIP zero-shot works well for products with descriptive names

    Args:
        image_data: Image to recognize
        training_features: List of (product_id, product_name, feature_bytes)
        product_labels: Dict mapping product_id to product name
        clip_weight: Weight for CLIP zero-shot scores
        feature_weight: Weight for feature matching scores
        threshold: Minimum score threshold

    Returns:
        List of (product_id, product_name, score) sorted by score
    """
    # Detect and crop bottle
    processed_image = image_data
    if _YOLO_AVAILABLE:
        detections = detect_bottles(image_data)
        if detections:
            processed_image = crop_to_detection(image_data, detections[0]['bbox'])

    scores: Dict[int, Tuple[str, float, float]] = {}  # product_id -> (name, feature_score, clip_score)

    # 1. Feature-based matching
    if training_features:
        query_features = extract_enhanced_features(processed_image, use_yolo_crop=False)

        for product_id, product_name, feat_bytes in training_features:
            if feat_bytes:
                sim = compute_clip_similarity(query_features, feat_bytes)
                scores[product_id] = (product_name, sim, 0.0)

    # 2. CLIP zero-shot matching
    if product_labels and _CLIP_AVAILABLE:
        clip_results = recognize_with_clip_text(processed_image, product_labels, threshold=0.01)

        for product_id, product_name, prob in clip_results:
            if product_id in scores:
                name, feat_score, _ = scores[product_id]
                scores[product_id] = (name, feat_score, prob)
            else:
                scores[product_id] = (product_name, 0.0, prob)

    # 3. Combine scores
    results = []
    for product_id, (name, feat_score, clip_score) in scores.items():
        combined_score = feat_score * feature_weight + clip_score * clip_weight
        if combined_score >= threshold:
            results.append((product_id, name, combined_score))

    # Sort by combined score
    results.sort(key=lambda x: x[2], reverse=True)

    return results


# Status function for debugging
def get_status() -> Dict[str, Any]:
    """Get status of CLIP and YOLO availability."""
    status = {
        "clip_available": _CLIP_AVAILABLE,
        "yolo_available": _YOLO_AVAILABLE,
        "clip_loaded": _CLIP_MODEL is not None,
        "yolo_loaded": _YOLO_MODEL is not None,
    }

    if _CLIP_AVAILABLE:
        try:
            import torch
            status["device"] = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception as e:
            logger.warning(f"Failed to detect CLIP device type: {e}")
            status["device"] = "unknown"

    return status
