"""Advanced Image Feature Extraction for Bottle Recognition.

This module provides comprehensive feature extraction:
- CNN features (MobileNetV3 embeddings) - primary
- OCR text features (EasyOCR) - for label text matching
- Color histograms (RGB, HSV)
- HOG (Histogram of Oriented Gradients) descriptors
- Texture features (LBP - Local Binary Patterns)
- Edge features
- Shape features
- Keypoint features (ORB-like)
- Text/label detection features

Also includes:
- Image preprocessing (normalization, resizing)
- Data augmentation for training
- Feature aggregation
- Image quality assessment
- OCR-based text similarity
"""

import io
import pickle
from app.core.safe_pickle import safe_loads
import hashlib
import logging
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, field
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

logger = logging.getLogger(__name__)

# Try to import OCR service
_OCR_AVAILABLE = False
try:
    from app.services.ai.ocr_service import (
        extract_text_from_image, extract_text_features_vector,
        compute_label_similarity, LabelInfo
    )
    _OCR_AVAILABLE = True
    logger.info("OCR service available")
except ImportError:
    logger.warning("OCR service not available")

# Try to import torch for CNN features
_TORCH_AVAILABLE = False
_CNN_MODEL = None
_CNN_TRANSFORM = None

try:
    import torch
    import torch.nn as nn
    from torchvision import models, transforms
    _TORCH_AVAILABLE = True
    logger.info("PyTorch available - CNN features enabled")
except ImportError:
    logger.warning("PyTorch not available - using hand-crafted features only")


def _get_cnn_model():
    """Lazy load CNN model."""
    global _CNN_MODEL, _CNN_TRANSFORM

    if not _TORCH_AVAILABLE:
        return None, None

    if _CNN_MODEL is None:
        try:
            # Use MobileNetV3 Small for efficiency
            _CNN_MODEL = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
            _CNN_MODEL.eval()

            # Remove classifier to get embeddings
            _CNN_MODEL.classifier = nn.Identity()

            # Set up transform
            _CNN_TRANSFORM = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])

            logger.info("CNN model (MobileNetV3) loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load CNN model: {e}")
            return None, None

    return _CNN_MODEL, _CNN_TRANSFORM


@dataclass
class QualityReport:
    """Image quality assessment report."""
    is_acceptable: bool
    overall_score: float  # 0-1
    blur_score: float  # Higher = sharper
    brightness_score: float  # 0-1, 0.5 = ideal
    contrast_score: float  # Higher = better
    issues: List[str] = field(default_factory=list)


@dataclass
class FeatureConfig:
    """Configuration for feature extraction."""
    image_size: Tuple[int, int] = (224, 224)
    color_bins: int = 32
    hog_orientations: int = 9
    hog_pixels_per_cell: Tuple[int, int] = (8, 8)
    hog_cells_per_block: Tuple[int, int] = (2, 2)
    lbp_radius: int = 3
    lbp_points: int = 24
    use_ocr: bool = True  # Use OCR for text extraction
    use_cnn: bool = True  # Use CNN features if available
    cnn_weight: float = 0.50  # Weight for CNN features (reduced to make room for OCR)
    ocr_weight: float = 0.15  # Weight for OCR text features
    feature_weights: Dict[str, float] = None

    def __post_init__(self):
        if self.feature_weights is None:
            self.feature_weights = {
                "color": 0.20,
                "hog": 0.18,
                "texture": 0.12,
                "edge": 0.10,
                "shape": 0.10,
                "keypoints": 0.15,
                "text": 0.05,
                "ocr": 0.10,  # OCR text features
            }


DEFAULT_CONFIG = FeatureConfig()


# ==================== IMAGE PREPROCESSING ====================

def preprocess_image(image_data: bytes, config: FeatureConfig = None) -> Image.Image:
    """Preprocess image for feature extraction."""
    config = config or DEFAULT_CONFIG

    image = Image.open(io.BytesIO(image_data))
    image = ImageOps.exif_transpose(image)

    if image.mode != "RGB":
        image = image.convert("RGB")

    # Normalize
    image = ImageOps.autocontrast(image, cutoff=1)
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.2)

    # Resize and crop
    image = resize_and_crop(image, config.image_size)

    return image


def resize_and_crop(image: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
    """Resize maintaining aspect ratio and center crop."""
    width, height = image.size
    target_w, target_h = target_size

    scale = max(target_w / width, target_h / height)
    new_size = (int(width * scale), int(height * scale))

    image = image.resize(new_size, Image.Resampling.LANCZOS)

    width, height = image.size
    left = (width - target_w) // 2
    top = (height - target_h) // 2

    return image.crop((left, top, left + target_w, top + target_h))


# ==================== IMAGE QUALITY ASSESSMENT ====================

def assess_image_quality(image_data: bytes) -> QualityReport:
    """Assess image quality for training suitability."""
    issues = []

    try:
        image = Image.open(io.BytesIO(image_data))
        image = ImageOps.exif_transpose(image)

        if image.mode != "RGB":
            image = image.convert("RGB")

        img_array = np.array(image)

        # Check minimum size
        width, height = image.size
        if width < 100 or height < 100:
            issues.append(f"Image too small: {width}x{height} (min 100x100)")

        # Blur detection using Laplacian variance
        gray = np.mean(img_array, axis=2)
        laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
        h, w = gray.shape
        blur_response = np.zeros_like(gray)
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                blur_response[y, x] = abs(np.sum(gray[y-1:y+2, x-1:x+2] * laplacian))

        blur_score = np.var(blur_response) / 1000.0  # Normalize
        blur_score = min(1.0, blur_score)

        if blur_score < 0.1:
            issues.append(f"Image is blurry (score: {blur_score:.2f})")

        # Brightness analysis
        brightness = np.mean(img_array) / 255.0
        brightness_score = 1.0 - abs(brightness - 0.5) * 2  # 0.5 = ideal

        if brightness < 0.15:
            issues.append(f"Image too dark (brightness: {brightness:.2f})")
        elif brightness > 0.85:
            issues.append(f"Image too bright (brightness: {brightness:.2f})")

        # Contrast analysis
        contrast_score = np.std(img_array) / 127.5  # Normalize to 0-1
        contrast_score = min(1.0, contrast_score)

        if contrast_score < 0.15:
            issues.append(f"Low contrast (score: {contrast_score:.2f})")

        # Overall score (weighted average)
        overall_score = (
            blur_score * 0.4 +
            brightness_score * 0.3 +
            contrast_score * 0.3
        )

        is_acceptable = len(issues) == 0 and overall_score >= 0.3

        return QualityReport(
            is_acceptable=is_acceptable,
            overall_score=overall_score,
            blur_score=blur_score,
            brightness_score=brightness_score,
            contrast_score=contrast_score,
            issues=issues,
        )

    except Exception as e:
        return QualityReport(
            is_acceptable=False,
            overall_score=0.0,
            blur_score=0.0,
            brightness_score=0.0,
            contrast_score=0.0,
            issues=[f"Failed to analyze image: {str(e)}"],
        )


# ==================== CNN FEATURES ====================

def extract_cnn_features(image: Image.Image) -> Optional[np.ndarray]:
    """Extract CNN embeddings using MobileNetV3.

    Returns 576-dimensional feature vector or None if CNN not available.
    """
    model, transform = _get_cnn_model()

    if model is None or transform is None:
        return None

    try:
        # Ensure RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Transform image
        img_tensor = transform(image).unsqueeze(0)

        # Extract features
        with torch.no_grad():
            features = model(img_tensor)

        # Convert to numpy and flatten
        features = features.squeeze().numpy()

        # L2 normalize
        norm = np.linalg.norm(features)
        if norm > 1e-7:
            features = features / norm

        return features.astype(np.float32)

    except Exception as e:
        logger.error(f"CNN feature extraction failed: {e}")
        return None


# ==================== COLOR FEATURES ====================

def extract_color_histogram_rgb(image: Image.Image, bins: int = 32) -> np.ndarray:
    """Extract RGB color histogram."""
    img_array = np.array(image)

    hist_r = np.histogram(img_array[:, :, 0], bins=bins, range=(0, 256))[0]
    hist_g = np.histogram(img_array[:, :, 1], bins=bins, range=(0, 256))[0]
    hist_b = np.histogram(img_array[:, :, 2], bins=bins, range=(0, 256))[0]

    histogram = np.concatenate([hist_r, hist_g, hist_b]).astype(np.float32)
    histogram = histogram / (histogram.sum() + 1e-7)

    return histogram


def extract_color_histogram_hsv(image: Image.Image, bins: int = 32) -> np.ndarray:
    """Extract HSV color histogram."""
    img_array = np.array(image).astype(np.float32) / 255.0

    r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]

    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    diff = max_c - min_c

    v = max_c
    s = np.where(max_c != 0, diff / max_c, 0)

    h = np.zeros_like(max_c)
    mask = diff != 0

    r_mask = mask & (max_c == r)
    g_mask = mask & (max_c == g)
    b_mask = mask & (max_c == b)

    h[r_mask] = (60 * ((g[r_mask] - b[r_mask]) / diff[r_mask]) + 360) % 360
    h[g_mask] = (60 * ((b[g_mask] - r[g_mask]) / diff[g_mask]) + 120) % 360
    h[b_mask] = (60 * ((r[b_mask] - g[b_mask]) / diff[b_mask]) + 240) % 360

    h = h / 360.0

    hist_h = np.histogram(h.flatten(), bins=bins, range=(0, 1))[0]
    hist_s = np.histogram(s.flatten(), bins=bins, range=(0, 1))[0]
    hist_v = np.histogram(v.flatten(), bins=bins, range=(0, 1))[0]

    histogram = np.concatenate([hist_h, hist_s, hist_v]).astype(np.float32)
    histogram = histogram / (histogram.sum() + 1e-7)

    return histogram


def extract_color_features(image: Image.Image, config: FeatureConfig = None) -> np.ndarray:
    """Extract combined color features."""
    config = config or DEFAULT_CONFIG

    rgb_hist = extract_color_histogram_rgb(image, config.color_bins)
    hsv_hist = extract_color_histogram_hsv(image, config.color_bins)

    return np.concatenate([rgb_hist * 0.5, hsv_hist * 0.5])


# ==================== HOG FEATURES ====================

def extract_hog_features(image: Image.Image, config: FeatureConfig = None) -> np.ndarray:
    """Extract HOG features."""
    config = config or DEFAULT_CONFIG

    gray = image.convert("L")
    gray = gray.resize((64, 128))
    img_array = np.array(gray, dtype=np.float32)

    gx = np.zeros_like(img_array)
    gy = np.zeros_like(img_array)

    gx[:, 1:-1] = img_array[:, 2:] - img_array[:, :-2]
    gy[1:-1, :] = img_array[2:, :] - img_array[:-2, :]

    magnitude = np.sqrt(gx**2 + gy**2)
    orientation = np.arctan2(gy, gx) * (180 / np.pi) % 180

    n_orientations = config.hog_orientations
    cell_size = config.hog_pixels_per_cell
    block_size = config.hog_cells_per_block

    n_cells_y = img_array.shape[0] // cell_size[0]
    n_cells_x = img_array.shape[1] // cell_size[1]

    cell_hists = np.zeros((n_cells_y, n_cells_x, n_orientations))

    for cy in range(n_cells_y):
        for cx in range(n_cells_x):
            y_start = cy * cell_size[0]
            y_end = y_start + cell_size[0]
            x_start = cx * cell_size[1]
            x_end = x_start + cell_size[1]

            cell_mag = magnitude[y_start:y_end, x_start:x_end]
            cell_ori = orientation[y_start:y_end, x_start:x_end]

            bin_width = 180 / n_orientations
            bins = (cell_ori / bin_width).astype(int) % n_orientations

            for b in range(n_orientations):
                cell_hists[cy, cx, b] = np.sum(cell_mag[bins == b])

    n_blocks_y = n_cells_y - block_size[0] + 1
    n_blocks_x = n_cells_x - block_size[1] + 1

    hog_features = []
    for by in range(n_blocks_y):
        for bx in range(n_blocks_x):
            block = cell_hists[by:by+block_size[0], bx:bx+block_size[1], :].flatten()
            norm = np.sqrt(np.sum(block**2) + 1e-7)
            hog_features.extend(block / norm)

    return np.array(hog_features, dtype=np.float32)


# ==================== TEXTURE FEATURES ====================

def extract_lbp_features(image: Image.Image, config: FeatureConfig = None) -> np.ndarray:
    """Extract Local Binary Pattern features."""
    config = config or DEFAULT_CONFIG

    gray = image.convert("L")
    gray = gray.resize((64, 64))
    img_array = np.array(gray, dtype=np.float32)

    radius = config.lbp_radius
    n_points = config.lbp_points

    angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
    sample_x = radius * np.cos(angles)
    sample_y = radius * np.sin(angles)

    height, width = img_array.shape
    lbp = np.zeros((height - 2*radius, width - 2*radius), dtype=np.uint32)

    for i, (dx, dy) in enumerate(zip(sample_x, sample_y)):
        for y in range(radius, height - radius):
            for x in range(radius, width - radius):
                center = img_array[y, x]
                sx = int(round(x + dx))
                sy = int(round(y + dy))

                if 0 <= sx < width and 0 <= sy < height:
                    neighbor = img_array[sy, sx]
                    if neighbor >= center:
                        lbp[y - radius, x - radius] |= (1 << i)

    n_bins = min(n_points + 2, 26)
    hist, _ = np.histogram(lbp.flatten(), bins=n_bins, range=(0, 2**n_points))

    hist = hist.astype(np.float32)
    hist = hist / (hist.sum() + 1e-7)

    return hist


# ==================== EDGE FEATURES ====================

def extract_edge_features(image: Image.Image) -> np.ndarray:
    """Extract edge-based features."""
    gray = image.convert("L")
    gray = gray.resize((64, 64))
    img_array = np.array(gray, dtype=np.float32)

    gx = np.zeros_like(img_array)
    gy = np.zeros_like(img_array)

    gx[:, 1:-1] = img_array[:, 2:] - img_array[:, :-2]
    gy[1:-1, :] = img_array[2:, :] - img_array[:-2, :]

    magnitude = np.sqrt(gx**2 + gy**2)
    direction = np.arctan2(gy, gx)

    hist, _ = np.histogram(direction[magnitude > 20].flatten(), bins=8, range=(-np.pi, np.pi))

    mag_stats = np.array([
        np.mean(magnitude),
        np.std(magnitude),
        np.percentile(magnitude, 90),
    ])

    edge_profile_x = np.mean(magnitude, axis=0)
    edge_profile_y = np.mean(magnitude, axis=1)

    hist = hist.astype(np.float32) / (hist.sum() + 1e-7)
    edge_profile_x = edge_profile_x / (np.linalg.norm(edge_profile_x) + 1e-7)
    edge_profile_y = edge_profile_y / (np.linalg.norm(edge_profile_y) + 1e-7)
    mag_stats = mag_stats / (np.linalg.norm(mag_stats) + 1e-7)

    return np.concatenate([hist, edge_profile_x, edge_profile_y, mag_stats])


# ==================== SHAPE FEATURES ====================

def extract_shape_features(image: Image.Image) -> np.ndarray:
    """Extract shape-based features."""
    gray = image.convert("L")
    gray = gray.resize((64, 64))
    img_array = np.array(gray, dtype=np.float32)

    threshold = np.mean(img_array)
    binary = (img_array < threshold * 0.9).astype(np.uint8)

    m00 = np.sum(binary)

    if m00 == 0:
        return np.zeros(10, dtype=np.float32)

    y_indices, x_indices = np.where(binary > 0)

    cx = np.mean(x_indices)
    cy = np.mean(y_indices)

    mu20 = np.sum((x_indices - cx)**2) / m00
    mu02 = np.sum((y_indices - cy)**2) / m00
    mu11 = np.sum((x_indices - cx) * (y_indices - cy)) / m00

    hu1 = mu20 + mu02
    hu2 = (mu20 - mu02)**2 + 4 * mu11**2

    width = np.max(x_indices) - np.min(x_indices) + 1
    height = np.max(y_indices) - np.min(y_indices) + 1
    aspect_ratio = width / (height + 1e-7)

    extent = m00 / (width * height + 1e-7)
    solidity = extent

    perimeter_approx = 2 * (width + height)
    circularity = 4 * np.pi * m00 / (perimeter_approx**2 + 1e-7)

    features = np.array([
        hu1, np.sqrt(hu2), aspect_ratio, extent, solidity, circularity,
        width / 64.0, height / 64.0, cx / 64.0, cy / 64.0
    ], dtype=np.float32)

    features = features / (np.linalg.norm(features) + 1e-7)

    return features


# ==================== KEYPOINT FEATURES ====================

def extract_keypoint_features(image: Image.Image, max_keypoints: int = 100) -> np.ndarray:
    """Extract keypoint-based features."""
    gray = image.convert("L")
    gray = gray.resize((128, 128))
    img_array = np.array(gray, dtype=np.float32)

    corners = []
    threshold = 20

    for y in range(3, img_array.shape[0] - 3):
        for x in range(3, img_array.shape[1] - 3):
            center = img_array[y, x]

            circle_points = [
                img_array[y-3, x], img_array[y-2, x+2], img_array[y, x+3],
                img_array[y+2, x+2], img_array[y+3, x], img_array[y+2, x-2],
                img_array[y, x-3], img_array[y-2, x-2]
            ]

            brighter = sum(1 for p in circle_points if p > center + threshold)
            darker = sum(1 for p in circle_points if p < center - threshold)

            if brighter >= 6 or darker >= 6:
                patch = img_array[y-1:y+2, x-1:x+2]
                gx = patch[:, 2] - patch[:, 0]
                gy = patch[2, :] - patch[0, :]

                strength = np.sum(gx**2) * np.sum(gy**2) - np.sum(gx * gy)**2
                corners.append((y, x, strength))

    corners.sort(key=lambda c: c[2], reverse=True)
    corners = corners[:max_keypoints]

    if len(corners) == 0:
        return np.zeros(256, dtype=np.float32)

    descriptors = []

    for y, x, _ in corners:
        if y < 8 or y >= img_array.shape[0] - 8 or x < 8 or x >= img_array.shape[1] - 8:
            continue

        patch = img_array[y-8:y+8, x-8:x+8]

        desc = []
        np.random.seed(42)
        for _ in range(32):
            y1, x1 = np.random.randint(0, 16, 2)
            y2, x2 = np.random.randint(0, 16, 2)
            desc.append(1 if patch[y1, x1] > patch[y2, x2] else 0)

        descriptors.append(desc)

    if len(descriptors) == 0:
        return np.zeros(256, dtype=np.float32)

    descriptors = np.array(descriptors)
    desc_values = np.packbits(descriptors, axis=1)

    hist, _ = np.histogram(desc_values.flatten(), bins=256, range=(0, 256))
    hist = hist.astype(np.float32)
    hist = hist / (hist.sum() + 1e-7)

    return hist


# ==================== TEXT FEATURES ====================

def extract_text_features(image: Image.Image) -> np.ndarray:
    """Extract text-presence features."""
    gray = image.convert("L")
    gray = gray.resize((128, 128))
    img_array = np.array(gray, dtype=np.float32)

    laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)

    h, w = img_array.shape
    edges = np.zeros_like(img_array)

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            region = img_array[y-1:y+2, x-1:x+2]
            edges[y, x] = abs(np.sum(region * laplacian))

    features = np.array([
        np.mean(edges),
        np.std(edges),
        np.percentile(edges, 75),
        np.percentile(edges, 90),
        np.sum(edges > 50) / edges.size,
        np.mean(np.abs(np.diff(img_array, axis=1))),
        np.mean(np.abs(np.diff(img_array, axis=0))),
    ], dtype=np.float32)

    features = features / (np.linalg.norm(features) + 1e-7)

    return features


# ==================== COMBINED FEATURES ====================

def extract_combined_features(
    image_data: bytes,
    config: FeatureConfig = None,
    check_quality: bool = False
) -> bytes:
    """Extract all features and combine them.

    Combines multiple feature types:
    - CNN features (MobileNetV3 embeddings) - 50% weight
    - OCR text features (if available) - 15% weight
    - Hand-crafted features - 35% weight

    Args:
        image_data: Raw image bytes
        config: Feature extraction config
        check_quality: If True, raises ValueError for low quality images

    Returns:
        Pickled numpy array of combined features
    """
    config = config or DEFAULT_CONFIG

    try:
        # Optional quality check
        if check_quality:
            quality = assess_image_quality(image_data)
            if not quality.is_acceptable:
                raise ValueError(f"Image quality rejected: {', '.join(quality.issues)}")

        image = preprocess_image(image_data, config)

        # Extract CNN features if available
        cnn_features = None
        if config.use_cnn and _TORCH_AVAILABLE:
            cnn_features = extract_cnn_features(image)
            if cnn_features is not None:
                logger.debug(f"CNN features extracted: {len(cnn_features)} dimensions")

        # Extract OCR text features if available
        ocr_features = None
        if config.use_ocr and _OCR_AVAILABLE:
            try:
                label_info = extract_text_from_image(image_data)
                if label_info and label_info.raw_text:
                    ocr_features = extract_text_features_vector(label_info)
                    logger.debug(f"OCR features extracted: {len(ocr_features)} dimensions, text: {label_info.raw_text[:50]}...")
            except Exception as e:
                logger.warning(f"OCR extraction failed: {e}")
                ocr_features = None

        # Extract hand-crafted features
        hc_features = {
            "color": extract_color_features(image, config),
            "hog": extract_hog_features(image, config),
            "texture": extract_lbp_features(image, config),
            "edge": extract_edge_features(image),
            "shape": extract_shape_features(image),
            "keypoints": extract_keypoint_features(image),
        }

        if config.use_ocr:
            hc_features["text"] = extract_text_features(image)

        # Combine hand-crafted features
        weighted_hc = []
        weights = config.feature_weights

        for name, feat in hc_features.items():
            weight = weights.get(name, 0.1)
            weighted_hc.append(feat * weight)

        hc_combined = np.concatenate(weighted_hc)
        hc_combined = hc_combined / (np.linalg.norm(hc_combined) + 1e-7)

        # Build final combined feature vector
        feature_parts = []

        # CNN features (50% weight)
        if cnn_features is not None:
            feature_parts.append(cnn_features * config.cnn_weight)

        # OCR features (15% weight)
        if ocr_features is not None:
            feature_parts.append(ocr_features * config.ocr_weight)

        # Hand-crafted features (remaining weight)
        remaining_weight = 1.0
        if cnn_features is not None:
            remaining_weight -= config.cnn_weight
        if ocr_features is not None:
            remaining_weight -= config.ocr_weight
        remaining_weight = max(0.1, remaining_weight)  # Minimum 10%

        feature_parts.append(hc_combined * remaining_weight)

        # Concatenate all features
        if feature_parts:
            combined = np.concatenate(feature_parts)
        else:
            combined = hc_combined

        combined = combined / (np.linalg.norm(combined) + 1e-7)

        return pickle.dumps(combined.astype(np.float32))

    except ValueError:
        raise  # Re-raise quality errors
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        raise


def extract_features_with_quality(image_data: bytes, config: FeatureConfig = None) -> Tuple[bytes, QualityReport]:
    """Extract features and return quality report.

    Returns:
        Tuple of (feature_vector_bytes, quality_report)
    """
    config = config or DEFAULT_CONFIG
    quality = assess_image_quality(image_data)
    features = extract_combined_features(image_data, config, check_quality=False)
    return features, quality


# ==================== SIMILARITY ====================

def compute_similarity(features1: bytes, features2: bytes) -> float:
    """Compute cosine similarity between two feature vectors."""
    try:
        vec1 = safe_loads(features1)
        vec2 = safe_loads(features2)

        min_len = min(len(vec1), len(vec2))
        vec1 = vec1[:min_len]
        vec2 = vec2[:min_len]

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


def find_best_match(
    query_features: bytes,
    candidates: List[Tuple[int, bytes]],
    threshold: float = 0.5
) -> Optional[Tuple[int, float]]:
    """Find the best matching product for a query image."""
    best_match = None
    best_similarity = threshold

    for product_id, candidate_features in candidates:
        similarity = compute_similarity(query_features, candidate_features)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = product_id

    if best_match is not None:
        return (best_match, best_similarity)

    return None


# ==================== AGGREGATION ====================

def aggregate_product_features(feature_vectors: List[bytes]) -> bytes:
    """Aggregate multiple training images into a single feature vector."""
    if not feature_vectors:
        return pickle.dumps(np.zeros(1096, dtype=np.float32))

    vectors = []
    for fv in feature_vectors:
        try:
            vectors.append(safe_loads(fv))
        except Exception:
            continue

    if not vectors:
        return pickle.dumps(np.zeros(1096, dtype=np.float32))

    min_len = min(len(v) for v in vectors)
    vectors = [v[:min_len] for v in vectors]
    vectors = np.array(vectors)

    if len(vectors) == 1:
        return pickle.dumps(vectors[0].astype(np.float32))

    mean_vector = np.mean(vectors, axis=0)

    if len(vectors) > 3:
        distances = np.linalg.norm(vectors - mean_vector, axis=1)
        threshold = np.percentile(distances, 75)
        inliers = vectors[distances <= threshold]

        if len(inliers) > 0:
            mean_vector = np.mean(inliers, axis=0)

    mean_vector = mean_vector / (np.linalg.norm(mean_vector) + 1e-7)

    return pickle.dumps(mean_vector.astype(np.float32))


# ==================== DATA AUGMENTATION ====================

def augment_image(image_data: bytes, n_augments: int = 5) -> List[bytes]:
    """Generate augmented versions of an image."""
    image = Image.open(io.BytesIO(image_data))
    image = ImageOps.exif_transpose(image)

    if image.mode != "RGB":
        image = image.convert("RGB")

    augmented = []

    for i in range(n_augments):
        aug_img = image.copy()

        angle = np.random.uniform(-15, 15)
        aug_img = aug_img.rotate(angle, resample=Image.Resampling.BILINEAR, expand=False)

        brightness = np.random.uniform(0.8, 1.2)
        enhancer = ImageEnhance.Brightness(aug_img)
        aug_img = enhancer.enhance(brightness)

        contrast = np.random.uniform(0.8, 1.2)
        enhancer = ImageEnhance.Contrast(aug_img)
        aug_img = enhancer.enhance(contrast)

        if np.random.random() > 0.5:
            aug_img = aug_img.filter(ImageFilter.GaussianBlur(radius=0.5))

        if np.random.random() > 0.7:
            aug_img = ImageOps.mirror(aug_img)

        buffer = io.BytesIO()
        aug_img.save(buffer, format="JPEG", quality=90)
        augmented.append(buffer.getvalue())

    return augmented


def augment_and_extract_features(
    image_data: bytes,
    n_augments: int = 5,
    config: FeatureConfig = None
) -> List[bytes]:
    """Generate augmented images and extract features from each."""
    augmented_images = [image_data] + augment_image(image_data, n_augments)

    features = []
    for img_data in augmented_images:
        try:
            feat = extract_combined_features(img_data, config)
            features.append(feat)
        except Exception as e:
            logger.warning(f"Augmentation feature extraction failed: {e}")
            continue

    return features


# ==================== UTILITIES ====================

def get_image_hash(image_data: bytes) -> str:
    """Get a hash of the image for deduplication."""
    return hashlib.md5(image_data).hexdigest()


def validate_image(image_data: bytes) -> Tuple[bool, str]:
    """Validate that image data is a valid image."""
    try:
        image = Image.open(io.BytesIO(image_data))
        image.verify()

        image = Image.open(io.BytesIO(image_data))

        width, height = image.size
        if width < 50 or height < 50:
            return False, "Image too small (minimum 50x50)"

        if width > 10000 or height > 10000:
            return False, "Image too large (maximum 10000x10000)"

        return True, "OK"

    except Exception as e:
        return False, f"Invalid image: {str(e)}"
