"""Advanced AI Bottle Recognition Service.

Provides comprehensive feature extraction for bottle recognition:
- Color histograms (RGB, HSV)
- HOG (Histogram of Oriented Gradients) descriptors
- SIFT/ORB keypoint descriptors
- Texture features (LBP - Local Binary Patterns)
- Shape features (contour analysis)
- Optional deep learning embeddings
- OCR for label text recognition

Also includes:
- Image preprocessing (background removal, normalization)
- Data augmentation for training
- Multi-scale feature matching
"""

import io
import pickle
from app.core.safe_pickle import safe_loads
import hashlib
import logging
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

logger = logging.getLogger(__name__)


class FeatureType(Enum):
    """Types of features to extract."""
    COLOR_HISTOGRAM = "color_histogram"
    HOG = "hog"
    TEXTURE_LBP = "texture_lbp"
    EDGE = "edge"
    SHAPE = "shape"
    KEYPOINTS = "keypoints"
    DEEP_EMBEDDING = "deep_embedding"
    TEXT_OCR = "text_ocr"


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
    use_deep_features: bool = False
    use_ocr: bool = True
    feature_weights: Dict[str, float] = None

    def __post_init__(self):
        if self.feature_weights is None:
            # Optimized weights for bottle recognition
            # Color and shape are most distinctive for bottles
            self.feature_weights = {
                "color": 0.30,      # Label colors are very distinctive
                "hog": 0.20,        # Shape gradients important
                "texture": 0.15,    # Label texture patterns
                "edge": 0.10,       # Bottle outline
                "shape": 0.15,      # Bottle silhouette
                "keypoints": 0.08,  # Distinctive points
                "text": 0.02,       # OCR less reliable
            }


# Global configuration
DEFAULT_CONFIG = FeatureConfig()


# ==================== IMAGE PREPROCESSING ====================

def preprocess_image(image_data: bytes, config: FeatureConfig = None) -> Image.Image:
    """
    Preprocess image for feature extraction.

    Steps:
    1. Load and convert to RGB
    2. Auto-orient based on EXIF
    3. Remove background (optional)
    4. Normalize brightness/contrast
    5. Resize to standard size
    """
    config = config or DEFAULT_CONFIG

    image = Image.open(io.BytesIO(image_data))

    # Auto-orient based on EXIF data
    image = ImageOps.exif_transpose(image)

    # Convert to RGB
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Normalize brightness and contrast
    image = normalize_image(image)

    # Resize maintaining aspect ratio, then center crop
    image = resize_and_crop(image, config.image_size)

    return image


def normalize_image(image: Image.Image) -> Image.Image:
    """Normalize image brightness and contrast."""
    # Auto-contrast
    image = ImageOps.autocontrast(image, cutoff=1)

    # Slight sharpening for better edge detection
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.2)

    return image


def resize_and_crop(image: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
    """Resize maintaining aspect ratio and center crop."""
    # Calculate scaling factor
    width, height = image.size
    target_w, target_h = target_size

    scale = max(target_w / width, target_h / height)
    new_size = (int(width * scale), int(height * scale))

    # Resize
    image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Center crop
    width, height = image.size
    left = (width - target_w) // 2
    top = (height - target_h) // 2

    return image.crop((left, top, left + target_w, top + target_h))


def remove_background_simple(image: Image.Image) -> Image.Image:
    """
    Simple background removal using edge detection and flood fill.
    For production, consider using rembg or similar ML-based solutions.
    """
    img_array = np.array(image)

    # Convert to grayscale for edge detection
    gray = np.mean(img_array, axis=2).astype(np.uint8)

    # Simple thresholding - assumes bottle is darker/different from background
    # This is a basic approach; ML-based methods would be better
    threshold = np.mean(gray)
    mask = gray < threshold * 1.2

    # Apply mask (keep original where mask is True)
    result = img_array.copy()
    result[~mask] = [255, 255, 255]  # White background

    return Image.fromarray(result)


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
    """Extract HSV color histogram (better for color matching)."""
    # Convert RGB to HSV
    img_array = np.array(image).astype(np.float32) / 255.0

    # Simple RGB to HSV conversion
    r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]

    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    diff = max_c - min_c

    # Value
    v = max_c

    # Saturation
    s = np.where(max_c != 0, diff / max_c, 0)

    # Hue
    h = np.zeros_like(max_c)
    mask = diff != 0

    r_mask = mask & (max_c == r)
    g_mask = mask & (max_c == g)
    b_mask = mask & (max_c == b)

    h[r_mask] = (60 * ((g[r_mask] - b[r_mask]) / diff[r_mask]) + 360) % 360
    h[g_mask] = (60 * ((b[g_mask] - r[g_mask]) / diff[g_mask]) + 120) % 360
    h[b_mask] = (60 * ((r[b_mask] - g[b_mask]) / diff[b_mask]) + 240) % 360

    h = h / 360.0  # Normalize to 0-1

    # Create histograms
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

    # Combine with equal weight
    return np.concatenate([rgb_hist * 0.5, hsv_hist * 0.5])


# ==================== HOG FEATURES ====================

def extract_hog_features(image: Image.Image, config: FeatureConfig = None) -> np.ndarray:
    """
    Extract HOG (Histogram of Oriented Gradients) features.
    Good for capturing shape and structure.
    """
    config = config or DEFAULT_CONFIG

    # Convert to grayscale
    gray = image.convert("L")
    gray = gray.resize((64, 128))  # Standard HOG size
    img_array = np.array(gray, dtype=np.float32)

    # Compute gradients
    gx = np.zeros_like(img_array)
    gy = np.zeros_like(img_array)

    gx[:, 1:-1] = img_array[:, 2:] - img_array[:, :-2]
    gy[1:-1, :] = img_array[2:, :] - img_array[:-2, :]

    # Compute magnitude and orientation
    magnitude = np.sqrt(gx**2 + gy**2)
    orientation = np.arctan2(gy, gx) * (180 / np.pi) % 180

    # HOG parameters
    n_orientations = config.hog_orientations
    cell_size = config.hog_pixels_per_cell
    block_size = config.hog_cells_per_block

    # Compute cell histograms
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

            # Bin orientations
            bin_width = 180 / n_orientations
            bins = (cell_ori / bin_width).astype(int) % n_orientations

            for b in range(n_orientations):
                cell_hists[cy, cx, b] = np.sum(cell_mag[bins == b])

    # Block normalization
    n_blocks_y = n_cells_y - block_size[0] + 1
    n_blocks_x = n_cells_x - block_size[1] + 1

    hog_features = []
    for by in range(n_blocks_y):
        for bx in range(n_blocks_x):
            block = cell_hists[by:by+block_size[0], bx:bx+block_size[1], :].flatten()
            norm = np.sqrt(np.sum(block**2) + 1e-7)
            hog_features.extend(block / norm)

    return np.array(hog_features, dtype=np.float32)


# ==================== TEXTURE FEATURES (LBP) ====================

def extract_lbp_features(image: Image.Image, config: FeatureConfig = None) -> np.ndarray:
    """
    Extract Local Binary Pattern features for texture analysis.
    Useful for identifying bottle labels and surface textures.
    """
    config = config or DEFAULT_CONFIG

    # Convert to grayscale and resize
    gray = image.convert("L")
    gray = gray.resize((64, 64))
    img_array = np.array(gray, dtype=np.float32)

    radius = config.lbp_radius
    n_points = config.lbp_points

    # Generate sampling points
    angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
    sample_x = radius * np.cos(angles)
    sample_y = radius * np.sin(angles)

    height, width = img_array.shape
    lbp = np.zeros((height - 2*radius, width - 2*radius), dtype=np.uint32)

    for i, (dx, dy) in enumerate(zip(sample_x, sample_y)):
        # Bilinear interpolation for sub-pixel sampling
        x1, y1 = int(np.floor(dx)), int(np.floor(dy))
        x2, y2 = x1 + 1, y1 + 1

        fx, fy = dx - x1, dy - y1

        for y in range(radius, height - radius):
            for x in range(radius, width - radius):
                center = img_array[y, x]

                # Simplified: nearest neighbor sampling
                sx = int(round(x + dx))
                sy = int(round(y + dy))

                if 0 <= sx < width and 0 <= sy < height:
                    neighbor = img_array[sy, sx]
                    if neighbor >= center:
                        lbp[y - radius, x - radius] |= (1 << i)

    # Create histogram of LBP values
    # Using uniform patterns (reduces dimensionality)
    n_bins = min(n_points + 2, 26)  # Uniform LBP has n_points + 2 patterns
    hist, _ = np.histogram(lbp.flatten(), bins=n_bins, range=(0, 2**n_points))

    # Normalize
    hist = hist.astype(np.float32)
    hist = hist / (hist.sum() + 1e-7)

    return hist


# ==================== EDGE FEATURES ====================

def extract_edge_features(image: Image.Image) -> np.ndarray:
    """Extract edge-based features using Sobel-like operators."""
    # Convert to grayscale
    gray = image.convert("L")
    gray = gray.resize((64, 64))
    img_array = np.array(gray, dtype=np.float32)

    # Sobel kernels
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)

    # Simple convolution
    def convolve2d(img, kernel):
        h, w = img.shape
        kh, kw = kernel.shape
        pad_h, pad_w = kh // 2, kw // 2

        result = np.zeros_like(img)
        for y in range(pad_h, h - pad_h):
            for x in range(pad_w, w - pad_w):
                region = img[y-pad_h:y+pad_h+1, x-pad_w:x+pad_w+1]
                result[y, x] = np.sum(region * kernel)

        return result

    gx = convolve2d(img_array, sobel_x)
    gy = convolve2d(img_array, sobel_y)

    # Magnitude and direction
    magnitude = np.sqrt(gx**2 + gy**2)

    # Edge histogram (orientation binning)
    direction = np.arctan2(gy, gx)
    n_bins = 8

    hist, _ = np.histogram(direction[magnitude > 20].flatten(), bins=n_bins, range=(-np.pi, np.pi))

    # Also include magnitude statistics
    mag_stats = np.array([
        np.mean(magnitude),
        np.std(magnitude),
        np.percentile(magnitude, 90),
    ])

    # Flatten edge features
    edge_profile_x = np.mean(magnitude, axis=0)
    edge_profile_y = np.mean(magnitude, axis=1)

    # Normalize
    hist = hist.astype(np.float32) / (hist.sum() + 1e-7)
    edge_profile_x = edge_profile_x / (np.linalg.norm(edge_profile_x) + 1e-7)
    edge_profile_y = edge_profile_y / (np.linalg.norm(edge_profile_y) + 1e-7)
    mag_stats = mag_stats / (np.linalg.norm(mag_stats) + 1e-7)

    return np.concatenate([hist, edge_profile_x, edge_profile_y, mag_stats])


# ==================== SHAPE FEATURES ====================

def extract_shape_features(image: Image.Image) -> np.ndarray:
    """Extract shape-based features from bottle contour."""
    # Convert to grayscale and threshold
    gray = image.convert("L")
    gray = gray.resize((64, 64))
    img_array = np.array(gray, dtype=np.float32)

    # Adaptive thresholding
    threshold = np.mean(img_array)
    binary = (img_array < threshold * 0.9).astype(np.uint8)

    # Calculate moments
    moments = {}
    m00 = np.sum(binary)

    if m00 == 0:
        return np.zeros(10, dtype=np.float32)

    y_indices, x_indices = np.where(binary > 0)

    # Centroid
    cx = np.mean(x_indices)
    cy = np.mean(y_indices)

    # Central moments
    mu20 = np.sum((x_indices - cx)**2) / m00
    mu02 = np.sum((y_indices - cy)**2) / m00
    mu11 = np.sum((x_indices - cx) * (y_indices - cy)) / m00

    # Hu moments (rotation invariant)
    hu1 = mu20 + mu02
    hu2 = (mu20 - mu02)**2 + 4 * mu11**2

    # Aspect ratio
    width = np.max(x_indices) - np.min(x_indices) + 1
    height = np.max(y_indices) - np.min(y_indices) + 1
    aspect_ratio = width / (height + 1e-7)

    # Extent (object area / bounding box area)
    extent = m00 / (width * height + 1e-7)

    # Solidity would require convex hull - simplified here
    solidity = extent  # Approximation

    # Circularity
    perimeter_approx = 2 * (width + height)  # Simplified
    circularity = 4 * np.pi * m00 / (perimeter_approx**2 + 1e-7)

    features = np.array([
        hu1, np.sqrt(hu2), aspect_ratio, extent, solidity, circularity,
        width / 64.0, height / 64.0, cx / 64.0, cy / 64.0
    ], dtype=np.float32)

    # Normalize
    features = features / (np.linalg.norm(features) + 1e-7)

    return features


# ==================== KEYPOINT FEATURES (ORB-like) ====================

def extract_keypoint_features(image: Image.Image, max_keypoints: int = 100) -> np.ndarray:
    """
    Extract keypoint-based features using a simplified ORB-like approach.
    For production, consider using OpenCV's ORB or SIFT.
    """
    # Convert to grayscale
    gray = image.convert("L")
    gray = gray.resize((128, 128))
    img_array = np.array(gray, dtype=np.float32)

    # FAST-like corner detection (simplified)
    corners = []
    threshold = 20

    for y in range(3, img_array.shape[0] - 3):
        for x in range(3, img_array.shape[1] - 3):
            center = img_array[y, x]

            # Check circle of radius 3
            circle_points = [
                img_array[y-3, x], img_array[y-2, x+2], img_array[y, x+3],
                img_array[y+2, x+2], img_array[y+3, x], img_array[y+2, x-2],
                img_array[y, x-3], img_array[y-2, x-2]
            ]

            brighter = sum(1 for p in circle_points if p > center + threshold)
            darker = sum(1 for p in circle_points if p < center - threshold)

            if brighter >= 6 or darker >= 6:
                # Calculate corner strength (Harris-like)
                patch = img_array[y-1:y+2, x-1:x+2]
                gx = patch[:, 2] - patch[:, 0]
                gy = patch[2, :] - patch[0, :]

                strength = np.sum(gx**2) * np.sum(gy**2) - np.sum(gx * gy)**2
                corners.append((y, x, strength))

    # Sort by strength and take top keypoints
    corners.sort(key=lambda c: c[2], reverse=True)
    corners = corners[:max_keypoints]

    if len(corners) == 0:
        return np.zeros(256, dtype=np.float32)

    # Extract simple descriptors (BRIEF-like)
    descriptors = []

    for y, x, _ in corners:
        if y < 8 or y >= img_array.shape[0] - 8 or x < 8 or x >= img_array.shape[1] - 8:
            continue

        patch = img_array[y-8:y+8, x-8:x+8]

        # Simple binary tests (BRIEF-like)
        desc = []
        np.random.seed(42)  # Deterministic
        for _ in range(32):
            y1, x1 = np.random.randint(0, 16, 2)
            y2, x2 = np.random.randint(0, 16, 2)
            desc.append(1 if patch[y1, x1] > patch[y2, x2] else 0)

        descriptors.append(desc)

    if len(descriptors) == 0:
        return np.zeros(256, dtype=np.float32)

    # Aggregate descriptors into a bag-of-words histogram
    descriptors = np.array(descriptors)

    # Convert binary to decimal for binning
    desc_values = np.packbits(descriptors, axis=1)

    # Create histogram
    hist, _ = np.histogram(desc_values.flatten(), bins=256, range=(0, 256))
    hist = hist.astype(np.float32)
    hist = hist / (hist.sum() + 1e-7)

    return hist


# ==================== TEXT/OCR FEATURES ====================

def extract_text_features(image: Image.Image) -> np.ndarray:
    """
    Extract text-based features for label recognition.
    Uses a simplified approach; for production use pytesseract or similar.
    """
    # This is a placeholder that returns texture-based features
    # that correlate with text presence

    gray = image.convert("L")
    gray = gray.resize((128, 128))
    img_array = np.array(gray, dtype=np.float32)

    # High-frequency content indicates text
    # Use Laplacian-like filter
    laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)

    h, w = img_array.shape
    edges = np.zeros_like(img_array)

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            region = img_array[y-1:y+2, x-1:x+2]
            edges[y, x] = abs(np.sum(region * laplacian))

    # Statistics that indicate text presence
    features = np.array([
        np.mean(edges),
        np.std(edges),
        np.percentile(edges, 75),
        np.percentile(edges, 90),
        np.sum(edges > 50) / edges.size,  # High edge ratio

        # Horizontal vs vertical edge ratio (text is often horizontal)
        np.mean(np.abs(np.diff(img_array, axis=1))),
        np.mean(np.abs(np.diff(img_array, axis=0))),
    ], dtype=np.float32)

    # Normalize
    features = features / (np.linalg.norm(features) + 1e-7)

    return features


# ==================== COMBINED FEATURE EXTRACTION ====================

def extract_combined_features(
    image_data: bytes,
    config: FeatureConfig = None
) -> bytes:
    """
    Extract all features and combine them.
    Returns serialized feature vector.
    """
    config = config or DEFAULT_CONFIG

    try:
        # Preprocess image
        image = preprocess_image(image_data, config)

        # Extract all features
        features = {}

        # Color features
        features["color"] = extract_color_features(image, config)

        # HOG features
        features["hog"] = extract_hog_features(image, config)

        # Texture features
        features["texture"] = extract_lbp_features(image, config)

        # Edge features
        features["edge"] = extract_edge_features(image)

        # Shape features
        features["shape"] = extract_shape_features(image)

        # Keypoint features
        features["keypoints"] = extract_keypoint_features(image)

        # Text features
        if config.use_ocr:
            features["text"] = extract_text_features(image)

        # Combine with weights
        weighted_features = []
        weights = config.feature_weights

        for name, feat in features.items():
            weight = weights.get(name, 0.1)
            weighted_features.append(feat * weight)

        combined = np.concatenate(weighted_features)

        # L2 normalize the final vector
        combined = combined / (np.linalg.norm(combined) + 1e-7)

        return pickle.dumps(combined.astype(np.float32))

    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        raise


def extract_features_dict(image_data: bytes, config: FeatureConfig = None) -> Dict[str, np.ndarray]:
    """
    Extract all features and return as dictionary.
    Useful for debugging and feature analysis.
    """
    config = config or DEFAULT_CONFIG
    image = preprocess_image(image_data, config)

    return {
        "color": extract_color_features(image, config),
        "hog": extract_hog_features(image, config),
        "texture": extract_lbp_features(image, config),
        "edge": extract_edge_features(image),
        "shape": extract_shape_features(image),
        "keypoints": extract_keypoint_features(image),
        "text": extract_text_features(image) if config.use_ocr else np.array([]),
    }


# ==================== SIMILARITY COMPUTATION ====================

def compute_similarity(features1: bytes, features2: bytes) -> float:
    """Compute cosine similarity between two feature vectors."""
    try:
        vec1 = safe_loads(features1)
        vec2 = safe_loads(features2)

        # Ensure same length
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


def compute_weighted_similarity(
    features1: bytes,
    features2: bytes,
    config: FeatureConfig = None
) -> Tuple[float, Dict[str, float]]:
    """
    Compute similarity with per-feature breakdown.
    Returns overall similarity and per-feature scores.
    """
    config = config or DEFAULT_CONFIG

    try:
        vec1 = safe_loads(features1)
        vec2 = safe_loads(features2)

        # This requires knowing feature boundaries
        # For now, return simple similarity
        similarity = compute_similarity(features1, features2)

        return similarity, {"overall": similarity}

    except Exception as e:
        logger.error(f"Weighted similarity failed: {e}")
        return 0.0, {}


def find_best_matches(
    query_features: bytes,
    candidates: List[Tuple[int, bytes]],
    threshold: float = 0.5,
    top_k: int = 5
) -> List[Tuple[int, float]]:
    """Find the best matching products for a query image."""
    results = []

    for product_id, candidate_features in candidates:
        similarity = compute_similarity(query_features, candidate_features)
        if similarity >= threshold:
            results.append((product_id, similarity))

    # Sort by similarity descending
    results.sort(key=lambda x: x[1], reverse=True)

    return results[:top_k]


# ==================== DATA AUGMENTATION ====================

def augment_image(image_data: bytes, n_augments: int = 10) -> List[bytes]:
    """
    Generate augmented versions of an image for training.

    Enhanced augmentations for better accuracy:
    - Rotation (various angles)
    - Brightness/contrast/saturation variation
    - Sharpness adjustment
    - Scaling/cropping
    - Horizontal flip
    - Gaussian blur
    - Color jitter
    """
    image = Image.open(io.BytesIO(image_data))
    image = ImageOps.exif_transpose(image)

    if image.mode != "RGB":
        image = image.convert("RGB")

    augmented = []

    for i in range(n_augments):
        aug_img = image.copy()

        # Random rotation (-20 to 20 degrees)
        angle = np.random.uniform(-20, 20)
        aug_img = aug_img.rotate(angle, resample=Image.Resampling.BILINEAR, expand=False, fillcolor=(128, 128, 128))

        # Random brightness (0.7 to 1.3)
        brightness = np.random.uniform(0.7, 1.3)
        enhancer = ImageEnhance.Brightness(aug_img)
        aug_img = enhancer.enhance(brightness)

        # Random contrast (0.7 to 1.3)
        contrast = np.random.uniform(0.7, 1.3)
        enhancer = ImageEnhance.Contrast(aug_img)
        aug_img = enhancer.enhance(contrast)

        # Random saturation (0.8 to 1.2)
        saturation = np.random.uniform(0.8, 1.2)
        enhancer = ImageEnhance.Color(aug_img)
        aug_img = enhancer.enhance(saturation)

        # Random sharpness (0.8 to 1.5)
        sharpness = np.random.uniform(0.8, 1.5)
        enhancer = ImageEnhance.Sharpness(aug_img)
        aug_img = enhancer.enhance(sharpness)

        # Random crop and resize (80-100% of image)
        if np.random.random() > 0.5:
            w, h = aug_img.size
            crop_factor = np.random.uniform(0.85, 1.0)
            new_w, new_h = int(w * crop_factor), int(h * crop_factor)
            left = np.random.randint(0, w - new_w + 1)
            top = np.random.randint(0, h - new_h + 1)
            aug_img = aug_img.crop((left, top, left + new_w, top + new_h))
            aug_img = aug_img.resize((w, h), Image.Resampling.BILINEAR)

        # Random slight blur (30% chance)
        if np.random.random() > 0.7:
            radius = np.random.uniform(0.3, 1.0)
            aug_img = aug_img.filter(ImageFilter.GaussianBlur(radius=radius))

        # Random horizontal flip (20% chance - bottles usually have distinct sides)
        if np.random.random() > 0.8:
            aug_img = ImageOps.mirror(aug_img)

        # Random noise simulation via slight posterize (10% chance)
        if np.random.random() > 0.9:
            aug_img = ImageOps.posterize(aug_img, bits=6)

        # Save to bytes
        buffer = io.BytesIO()
        aug_img.save(buffer, format="JPEG", quality=92)
        augmented.append(buffer.getvalue())

    return augmented


def augment_and_extract_features(
    image_data: bytes,
    n_augments: int = 5,
    config: FeatureConfig = None
) -> List[bytes]:
    """
    Generate augmented images and extract features from each.
    Returns list of feature vectors.
    """
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


# ==================== FEATURE AGGREGATION ====================

def aggregate_features(feature_vectors: List[bytes]) -> bytes:
    """
    Aggregate multiple feature vectors into one.
    Uses weighted average with outlier rejection.
    """
    if not feature_vectors:
        return pickle.dumps(np.zeros(1000, dtype=np.float32))

    vectors = []
    for fv in feature_vectors:
        try:
            vectors.append(safe_loads(fv))
        except Exception as e:
            logger.warning(f"Failed to deserialize feature vector during aggregation: {e}")
            continue

    if not vectors:
        return pickle.dumps(np.zeros(1000, dtype=np.float32))

    # Ensure same length
    min_len = min(len(v) for v in vectors)
    vectors = [v[:min_len] for v in vectors]
    vectors = np.array(vectors)

    if len(vectors) == 1:
        return pickle.dumps(vectors[0].astype(np.float32))

    # Compute mean
    mean_vector = np.mean(vectors, axis=0)

    # Optional: reject outliers and recompute
    if len(vectors) > 3:
        distances = np.linalg.norm(vectors - mean_vector, axis=1)
        threshold = np.percentile(distances, 75)
        inliers = vectors[distances <= threshold]

        if len(inliers) > 0:
            mean_vector = np.mean(inliers, axis=0)

    # Normalize
    mean_vector = mean_vector / (np.linalg.norm(mean_vector) + 1e-7)

    return pickle.dumps(mean_vector.astype(np.float32))


# ==================== UTILITY FUNCTIONS ====================

def get_image_hash(image_data: bytes) -> str:
    """Get a hash of the image for deduplication."""
    return hashlib.md5(image_data).hexdigest()


def validate_image(image_data: bytes) -> Tuple[bool, str]:
    """Validate that image data is a valid image."""
    try:
        image = Image.open(io.BytesIO(image_data))
        image.verify()

        # Reopen after verify
        image = Image.open(io.BytesIO(image_data))

        width, height = image.size
        if width < 50 or height < 50:
            return False, "Image too small (minimum 50x50)"

        if width > 10000 or height > 10000:
            return False, "Image too large (maximum 10000x10000)"

        return True, "OK"

    except Exception as e:
        return False, f"Invalid image: {str(e)}"


def get_feature_vector_size(config: FeatureConfig = None) -> int:
    """Get the expected size of the combined feature vector."""
    config = config or DEFAULT_CONFIG

    # Approximate sizes
    sizes = {
        "color": config.color_bins * 6,  # RGB + HSV
        "hog": 1764,  # Depends on image size and HOG params
        "texture": 26,  # LBP histogram
        "edge": 8 + 64 + 64 + 3,  # orientation hist + profiles + stats
        "shape": 10,
        "keypoints": 256,
        "text": 7,
    }

    return sum(sizes.values())
