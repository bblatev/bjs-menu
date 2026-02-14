"""OCR Text Recognition Service for Bottle Labels - Enhanced Version.

This module provides:
- Text extraction from bottle labels using EasyOCR
- Multi-language support (EN, FR, ES, DE, PT, IT, RU)
- GPU acceleration (configurable)
- Fuzzy matching for OCR error tolerance
- Image preprocessing with deskewing and adaptive thresholding
- OCR result caching by image hash
- Semantic matching with sentence embeddings
- Comprehensive brand database
"""

import io
import os
import re
import hashlib
import logging
from typing import Optional, List, Dict, Tuple, Any, Set
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
from collections import OrderedDict
import numpy as np
from PIL import Image, ImageOps
from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration from environment
# ============================================================================

OCR_GPU_ENABLED = os.getenv("OCR_GPU_ENABLED", "false").lower() == "true"
OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "en").split(",")
OCR_CONFIDENCE_THRESHOLD = float(settings.ocr_confidence_threshold)
OCR_CACHE_SIZE = int(os.getenv("OCR_CACHE_SIZE", "500"))
SEMANTIC_MATCHING_ENABLED = os.getenv("SEMANTIC_MATCHING_ENABLED", "true").lower() == "true"

# ============================================================================
# Lazy-loaded dependencies
# ============================================================================

_OCR_READER = None
_OCR_AVAILABLE = False
_SENTENCE_MODEL = None
_SENTENCE_MODEL_AVAILABLE = False

try:
    import easyocr
    _OCR_AVAILABLE = True
    logger.info("EasyOCR available")
except ImportError:
    logger.warning("EasyOCR not available - text recognition disabled")

try:
    if SEMANTIC_MATCHING_ENABLED:
        from sentence_transformers import SentenceTransformer
        _SENTENCE_MODEL_AVAILABLE = True
        logger.info("SentenceTransformers available for semantic matching")
except (ImportError, ValueError, Exception) as e:
    logger.info(f"SentenceTransformers not available - using basic matching: {e}")


# ============================================================================
# OCR Result Cache (LRU with image hash keys)
# ============================================================================

class OCRCache:
    """LRU cache for OCR results keyed by image hash."""

    def __init__(self, maxsize: int = 500):
        self.cache: OrderedDict = OrderedDict()
        self.maxsize = maxsize
        self.hits = 0
        self.misses = 0

    def _hash_image(self, image_data: bytes) -> str:
        """Create hash of image data."""
        return hashlib.md5(image_data).hexdigest()

    def get(self, image_data: bytes) -> Optional['LabelInfo']:
        """Get cached result if available."""
        key = self._hash_image(image_data)
        if key in self.cache:
            self.hits += 1
            self.cache.move_to_end(key)
            return self.cache[key]
        self.misses += 1
        return None

    def set(self, image_data: bytes, result: 'LabelInfo'):
        """Cache OCR result."""
        key = self._hash_image(image_data)
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.maxsize:
                self.cache.popitem(last=False)
            self.cache[key] = result

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        return {
            "size": len(self.cache),
            "maxsize": self.maxsize,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0.0
        }

    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0


_OCR_CACHE = OCRCache(maxsize=OCR_CACHE_SIZE)


# ============================================================================
# Fuzzy Matching / Edit Distance
# ============================================================================

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def fuzzy_match(text1: str, text2: str, threshold: float = 0.8) -> Tuple[bool, float]:
    """Check if two strings match with fuzzy tolerance.

    Handles common OCR errors:
    - I/l/1 confusion
    - O/0 confusion
    - Character substitutions

    Returns:
        Tuple of (is_match, similarity_score)
    """
    if not text1 or not text2:
        return False, 0.0

    t1 = text1.lower().strip()
    t2 = text2.lower().strip()

    # Exact match
    if t1 == t2:
        return True, 1.0

    # Normalize common OCR confusions
    ocr_normalizations = [
        ('1', 'l'), ('l', 'i'), ('0', 'o'), ('rn', 'm'),
        ('vv', 'w'), ('cl', 'd'), ('ii', 'u'), ('nn', 'm'),
    ]

    t1_norm = t1
    t2_norm = t2
    for old, new in ocr_normalizations:
        t1_norm = t1_norm.replace(old, new)
        t2_norm = t2_norm.replace(old, new)

    if t1_norm == t2_norm:
        return True, 0.95

    # Calculate similarity based on edit distance
    max_len = max(len(t1), len(t2))
    if max_len == 0:
        return False, 0.0

    distance = levenshtein_distance(t1_norm, t2_norm)
    similarity = 1.0 - (distance / max_len)

    # Also check sequence matcher
    seq_sim = SequenceMatcher(None, t1_norm, t2_norm).ratio()

    # Use the better score
    final_sim = max(similarity, seq_sim)

    return final_sim >= threshold, final_sim


def find_best_fuzzy_match(query: str, candidates: List[str], threshold: float = 0.7) -> Optional[Tuple[str, float]]:
    """Find the best fuzzy match from a list of candidates.

    Returns:
        Tuple of (best_match, score) or None if no match above threshold
    """
    best_match = None
    best_score = threshold

    for candidate in candidates:
        _, score = fuzzy_match(query, candidate)
        if score > best_score:
            best_score = score
            best_match = candidate

    return (best_match, best_score) if best_match else None


# ============================================================================
# Comprehensive Brand Database
# ============================================================================

BRAND_DATABASE = {
    # Vodka
    "vodka": [
        "absolut", "smirnoff", "grey goose", "belvedere", "ketel one",
        "stolichnaya", "stoli", "titos", "tito's", "ciroc", "skyy",
        "pinnacle", "new amsterdam", "svedka", "finlandia", "russian standard",
        "chopin", "żubrówka", "zubrowka", "wyborowa", "luksusowa",
        "reyka", "hangar 1", "crystal head", "three olives", "deep eddy",
        "savoy", "nemiroff", "khortytsa", "parliament"
    ],
    # Whiskey/Whisky
    "whiskey": [
        "jack daniels", "jack daniel's", "johnnie walker", "jameson",
        "makers mark", "maker's mark", "jim beam", "wild turkey", "evan williams",
        "bulleit", "woodford reserve", "knob creek", "basil hayden",
        "buffalo trace", "eagle rare", "blantons", "blanton's", "pappy van winkle",
        "crown royal", "canadian club", "seagrams", "seagram's",
        "glenfiddich", "glenlivet", "macallan", "laphroaig", "lagavulin",
        "talisker", "oban", "dalmore", "balvenie", "aberlour", "highland park",
        "chivas regal", "dewars", "dewar's", "famous grouse", "j&b", "cutty sark",
        "bushmills", "redbreast", "green spot", "powers", "tullamore dew",
        "nikka", "suntory", "yamazaki", "hibiki", "hakushu"
    ],
    # Rum
    "rum": [
        "bacardi", "captain morgan", "havana club", "mount gay", "appleton estate",
        "malibu", "kraken", "diplomatico", "diplomatico", "ron zacapa",
        "plantation", "flor de cana", "brugal", "don q", "sailor jerry",
        "myers", "goslings", "pyrat", "bumbu", "angostura"
    ],
    # Tequila/Mezcal
    "tequila": [
        "jose cuervo", "patron", "don julio", "herradura", "casamigos",
        "espolon", "olmeca", "sauza", "el jimador", "hornitos", "milagro",
        "corralejo", "casa noble", "clase azul", "avion", "teremana",
        "1800", "tres generaciones", "cazadores", "tapatio",
        "del maguey", "illegal mezcal", "montelobos", "vida mezcal"
    ],
    # Gin
    "gin": [
        "bombay", "bombay sapphire", "tanqueray", "hendricks", "hendrick's",
        "beefeater", "gordons", "gordon's", "sipsmith", "botanist",
        "aviation", "roku", "monkey 47", "nolets", "nolet's", "bulldog",
        "bloom", "caorunn", "plymouth", "brokers", "haymans", "hayman's"
    ],
    # Cognac/Brandy
    "cognac": [
        "hennessy", "remy martin", "rémy martin", "courvoisier", "martell",
        "camus", "hine", "delamain", "hardy", "frapin", "pierre ferrand",
        "gautier", "a.e. dor", "paul giraud"
    ],
    # Liqueurs
    "liqueur": [
        "kahlua", "baileys", "amaretto", "jagermeister", "jägermeister",
        "cointreau", "grand marnier", "frangelico", "chambord", "midori",
        "disaronno", "sambuca", "drambuie", "benedictine", "chartreuse",
        "campari", "aperol", "st germain", "pimms", "pimm's",
        "southern comfort", "fireball", "rumchata", "licor 43"
    ],
    # Beer
    "beer": [
        "corona", "heineken", "budweiser", "stella", "stella artois", "guinness",
        "modelo", "pacifico", "dos equis", "tecate", "negra modelo",
        "peroni", "moretti", "amstel", "beck's", "becks", "carlsberg",
        "kronenbourg", "hoegaarden", "leffe", "duvel", "chimay",
        "pilsner urquell", "staropramen", "tyskie", "zywiec",
        "asahi", "sapporo", "kirin", "tsingtao", "tiger", "singha"
    ],
    # Wine
    "wine": [
        "barefoot", "yellowtail", "yellow tail", "jacob's creek", "jacobs creek",
        "robert mondavi", "kendall jackson", "sutter home", "woodbridge",
        "beringer", "clos du bois", "louis jadot", "nicolas feuillatte",
        "veuve clicquot", "moet", "moët", "dom perignon", "cristal",
        "chateau", "château"
    ],
    # Vermouth/Aperitifs
    "vermouth": [
        "martini", "cinzano", "noilly prat", "dolin", "cocchi",
        "lillet", "punt e mes", "antica formula"
    ],
    # Bitters
    "bitters": [
        "angostura", "peychauds", "peychaud's", "orange bitters", "fee brothers"
    ]
}

# Flatten brand list for quick lookup
ALL_BRANDS: Set[str] = set()
BRAND_TO_CATEGORY: Dict[str, str] = {}
for category, brands in BRAND_DATABASE.items():
    for brand in brands:
        ALL_BRANDS.add(brand.lower())
        BRAND_TO_CATEGORY[brand.lower()] = category

# Brand variants and common misspellings
BRAND_VARIANTS = {
    "jack daniel's": ["jack daniels", "jd", "jackdaniels"],
    "johnnie walker": ["johnny walker", "jonnie walker"],
    "maker's mark": ["makers mark", "makersmark"],
    "grey goose": ["gray goose", "greygoose"],
    "jägermeister": ["jagermeister", "jager", "jaeger"],
    "rémy martin": ["remy martin", "remymartin"],
    "hendrick's": ["hendricks", "hendrick"],
    "tito's": ["titos", "tito"],
    "bailey's": ["baileys", "bailey"],
    "gordon's": ["gordons", "gordon"],
}

# Distinguishing words for product variants
DISTINGUISHING_WORDS = {
    "colors": ["gold", "silver", "black", "red", "blue", "green", "white", "pink", "platinum", "amber"],
    "ages": ["12", "15", "18", "21", "25", "year", "years", "aged", "old", "yo"],
    "types": ["single", "double", "triple", "blended", "single malt", "reserve", "special", "limited",
              "rare", "vintage", "extra", "premium", "select", "deluxe", "grand", "royal"],
    "flavors": ["vanilla", "honey", "apple", "cherry", "peach", "mango", "citrus", "lime", "lemon",
                "orange", "raspberry", "strawberry", "coconut", "caramel", "cinnamon", "spiced"],
    "finishes": ["cask", "barrel", "sherry", "bourbon", "port", "wine", "rum", "finished"],
}


# ============================================================================
# Multi-language Support
# ============================================================================

SUPPORTED_LANGUAGES = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "pt": "Portuguese",
    "it": "Italian",
    "ru": "Russian",
    "nl": "Dutch",
    "pl": "Polish",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
}

# Language-specific stopwords
STOPWORDS = {
    "en": {"the", "and", "for", "with", "from", "est", "vol", "alc", "abv", "ltd", "inc", "co"},
    "fr": {"le", "la", "les", "de", "du", "des", "et", "pour", "avec"},
    "es": {"el", "la", "los", "las", "de", "del", "y", "para", "con"},
    "de": {"der", "die", "das", "und", "für", "mit", "von", "aus"},
    "pt": {"o", "a", "os", "as", "de", "do", "da", "e", "para", "com"},
    "it": {"il", "la", "lo", "gli", "le", "di", "del", "e", "per", "con"},
}


def _get_ocr_reader():
    """Lazy load OCR reader with configured languages and GPU setting."""
    global _OCR_READER

    if not _OCR_AVAILABLE:
        return None

    if _OCR_READER is None:
        try:
            # Map language codes
            languages = []
            for lang in OCR_LANGUAGES:
                lang = lang.strip().lower()
                if lang in SUPPORTED_LANGUAGES:
                    languages.append(lang)

            if not languages:
                languages = ['en']

            logger.info(f"Initializing EasyOCR with languages: {languages}, GPU: {OCR_GPU_ENABLED}")
            _OCR_READER = easyocr.Reader(languages, gpu=OCR_GPU_ENABLED, verbose=False)
            logger.info("EasyOCR reader initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            return None

    return _OCR_READER


def _get_sentence_model():
    """Lazy load sentence transformer model for semantic matching."""
    global _SENTENCE_MODEL

    if not _SENTENCE_MODEL_AVAILABLE:
        return None

    if _SENTENCE_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Use a lightweight model for speed
            _SENTENCE_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence transformer model loaded for semantic matching")
        except Exception as e:
            logger.warning(f"Failed to load sentence transformer: {e}")
            return None

    return _SENTENCE_MODEL


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TextRegion:
    """A detected text region."""
    text: str
    confidence: float
    bbox: List[List[int]]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    language: str = "en"


@dataclass
class LabelInfo:
    """Extracted label information."""
    raw_text: str  # All detected text concatenated
    brand: Optional[str] = None
    brand_category: Optional[str] = None
    product_name: Optional[str] = None
    volume: Optional[str] = None
    alcohol_percentage: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    distinguishing_words: List[str] = field(default_factory=list)
    text_regions: List[TextRegion] = field(default_factory=list)
    confidence: float = 0.0
    detected_language: str = "en"
    from_cache: bool = False
    semantic_embedding: Optional[np.ndarray] = None


# ============================================================================
# Image Preprocessing
# ============================================================================

def enhance_for_ocr(image: Image.Image, aggressive: bool = False) -> Image.Image:
    """Enhanced image preprocessing for better OCR results.

    Features:
    - Upscaling small images
    - Contrast enhancement
    - Sharpening
    - Noise reduction
    - Optional deskewing
    - Adaptive thresholding for difficult images
    """
    from PIL import ImageEnhance, ImageFilter

    original_mode = image.mode

    # Convert to RGB for processing
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Resize if too small
    min_dim = min(image.size)
    if min_dim < 500:
        scale = 500 / min_dim
        new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5 if not aggressive else 2.0)

    # Enhance brightness slightly
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(1.1)

    # Sharpen
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0 if not aggressive else 2.5)

    # Denoise using median filter
    image = image.filter(ImageFilter.MedianFilter(size=3))

    if aggressive:
        # Additional edge enhancement for difficult images
        image = image.filter(ImageFilter.EDGE_ENHANCE)

        # Unsharp mask for clearer text
        image = image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    return image


def deskew_image(image: Image.Image) -> Image.Image:
    """Attempt to deskew a tilted image for better OCR.

    Uses Hough transform to detect dominant lines and correct rotation.
    """
    try:
        import cv2

        # Convert to numpy array
        img_array = np.array(image)

        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Detect lines using Hough transform
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)

        if lines is not None and len(lines) > 0:
            # Calculate average angle
            angles = []
            for line in lines[:20]:  # Use top 20 lines
                rho, theta = line[0]
                angle = np.degrees(theta) - 90
                if abs(angle) < 45:  # Only consider reasonable angles
                    angles.append(angle)

            if angles:
                avg_angle = np.median(angles)

                # Only rotate if angle is significant
                if abs(avg_angle) > 0.5:
                    # Rotate image
                    (h, w) = img_array.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, avg_angle, 1.0)
                    rotated = cv2.warpAffine(img_array, M, (w, h),
                                            flags=cv2.INTER_CUBIC,
                                            borderMode=cv2.BORDER_REPLICATE)
                    return Image.fromarray(rotated)

        return image

    except ImportError:
        logger.debug("OpenCV not available for deskewing")
        return image
    except Exception as e:
        logger.debug(f"Deskewing failed: {e}")
        return image


def adaptive_threshold_image(image: Image.Image) -> Image.Image:
    """Apply adaptive thresholding for difficult images with uneven lighting."""
    try:
        import cv2

        img_array = np.array(image)

        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Convert back to RGB for EasyOCR
        rgb = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)

        return Image.fromarray(rgb)

    except ImportError:
        return image
    except Exception as e:
        logger.debug(f"Adaptive threshold failed: {e}")
        return image


# ============================================================================
# Volume and Alcohol Patterns
# ============================================================================

VOLUME_PATTERNS = [
    r'(\d+(?:[.,]\d+)?)\s*(ml|ML|mL|cl|CL|cL|l|L|liter|litre|oz|OZ|fl\.?\s*oz)',
    r'(\d+(?:[.,]\d+)?)\s*(?:fluid\s+)?ounces?',
]

ALCOHOL_PATTERNS = [
    r'(\d+(?:[.,]\d+)?)\s*%\s*(?:alc|vol|abv|alcohol)?',
    r'(\d+(?:[.,]\d+)?)\s*proof',
    r'ABV\s*:?\s*(\d+(?:[.,]\d+)?)\s*%?',
    r'ALC\s*:?\s*(\d+(?:[.,]\d+)?)\s*%?',
]


# ============================================================================
# Main OCR Functions
# ============================================================================

def extract_text_from_image(
    image_data: bytes,
    use_cache: bool = True,
    aggressive_preprocessing: bool = False,
    try_deskew: bool = True,
    compute_embedding: bool = True
) -> LabelInfo:
    """Extract text from an image using OCR with all enhancements.

    Args:
        image_data: Raw image bytes
        use_cache: Whether to use/store cached results
        aggressive_preprocessing: Apply more aggressive image enhancement
        try_deskew: Attempt to correct image rotation
        compute_embedding: Generate semantic embedding for the text

    Returns:
        LabelInfo with extracted text and parsed information
    """
    # Check cache first
    if use_cache:
        cached = _OCR_CACHE.get(image_data)
        if cached:
            cached.from_cache = True
            return cached

    reader = _get_ocr_reader()

    if reader is None:
        return LabelInfo(raw_text="", confidence=0.0)

    try:
        # Load and preprocess image
        image = Image.open(io.BytesIO(image_data))
        image = ImageOps.exif_transpose(image)

        if image.mode != "RGB":
            image = image.convert("RGB")

        # Try deskewing first
        if try_deskew:
            image = deskew_image(image)

        # Enhance image for OCR
        image = enhance_for_ocr(image, aggressive=aggressive_preprocessing)

        # Convert to numpy array for EasyOCR
        img_array = np.array(image)

        # Run OCR
        results = reader.readtext(img_array)

        # If poor results, try with adaptive thresholding
        if not results or all(r[2] < 0.4 for r in results):
            logger.debug("Retrying with adaptive thresholding")
            threshold_image = adaptive_threshold_image(image)
            img_array = np.array(threshold_image)
            results_threshold = reader.readtext(img_array)

            # Use threshold results if better
            if results_threshold and (not results or
                sum(r[2] for r in results_threshold) > sum(r[2] for r in results)):
                results = results_threshold

        if not results:
            empty_result = LabelInfo(raw_text="", confidence=0.0)
            if use_cache:
                _OCR_CACHE.set(image_data, empty_result)
            return empty_result

        # Parse results
        text_regions = []
        all_text = []
        total_confidence = 0.0

        for bbox, text, conf in results:
            if conf > OCR_CONFIDENCE_THRESHOLD:
                text_regions.append(TextRegion(
                    text=text,
                    confidence=conf,
                    bbox=[[int(p[0]), int(p[1])] for p in bbox]
                ))
                all_text.append(text)
                total_confidence += conf

        raw_text = " ".join(all_text)
        avg_confidence = total_confidence / len(text_regions) if text_regions else 0.0

        # Extract structured information
        label_info = parse_label_text(raw_text, text_regions)
        label_info.confidence = avg_confidence

        # Compute semantic embedding if requested
        if compute_embedding and raw_text:
            label_info.semantic_embedding = compute_semantic_embedding(raw_text)

        # Cache result
        if use_cache:
            _OCR_CACHE.set(image_data, label_info)

        return label_info

    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return LabelInfo(raw_text="", confidence=0.0)


def parse_label_text(raw_text: str, regions: List[TextRegion]) -> LabelInfo:
    """Parse raw OCR text to extract structured information with fuzzy matching."""

    label_info = LabelInfo(
        raw_text=raw_text,
        text_regions=regions
    )

    text_lower = raw_text.lower()

    # Extract volume
    for pattern in VOLUME_PATTERNS:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            label_info.volume = match.group(0)
            break

    # Extract alcohol percentage
    for pattern in ALCOHOL_PATTERNS:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            label_info.alcohol_percentage = match.group(0)
            break

    # Try to identify brand using fuzzy matching
    words = text_lower.split()

    # Check for multi-word brands first
    for brand in ALL_BRANDS:
        if ' ' in brand:  # Multi-word brand
            is_match, score = fuzzy_match(text_lower, brand, threshold=0.7)
            if brand in text_lower or is_match:
                label_info.brand = brand.title()
                label_info.brand_category = BRAND_TO_CATEGORY.get(brand)
                break

    # Check single-word brands
    if not label_info.brand:
        for word in words:
            # Exact check first
            if word in ALL_BRANDS:
                label_info.brand = word.title()
                label_info.brand_category = BRAND_TO_CATEGORY.get(word)
                break

            # Fuzzy match
            match = find_best_fuzzy_match(word, list(ALL_BRANDS), threshold=0.8)
            if match:
                label_info.brand = match[0].title()
                label_info.brand_category = BRAND_TO_CATEGORY.get(match[0])
                break

    # Check brand variants
    if not label_info.brand:
        for canonical, variants in BRAND_VARIANTS.items():
            for variant in variants:
                if variant in text_lower:
                    label_info.brand = canonical.title()
                    label_info.brand_category = BRAND_TO_CATEGORY.get(canonical.lower())
                    break
            if label_info.brand:
                break

    # Extract distinguishing words
    for category, words_list in DISTINGUISHING_WORDS.items():
        for word in words_list:
            if word.lower() in text_lower:
                label_info.distinguishing_words.append(word.lower())

    # Extract keywords (significant words)
    word_pattern = re.findall(r'\b[a-zA-Z]{3,}\b', raw_text)
    keywords = []

    # Get stopwords for detected language (default to English)
    lang_stopwords = STOPWORDS.get("en", set())
    for lang in OCR_LANGUAGES:
        if lang in STOPWORDS:
            lang_stopwords = lang_stopwords | STOPWORDS[lang]

    for word in word_pattern:
        word_lower = word.lower()
        if word_lower not in lang_stopwords and len(word) > 2:
            keywords.append(word_lower)

    # Remove duplicates while preserving order
    seen = set()
    label_info.keywords = [k for k in keywords if not (k in seen or seen.add(k))][:20]

    # Try to extract product name (largest/most prominent text regions)
    if regions:
        # Sort by text length and confidence
        sorted_regions = sorted(
            regions,
            key=lambda r: (len(r.text) * r.confidence),
            reverse=True
        )
        for region in sorted_regions[:5]:
            text = region.text.strip()
            # Skip if it's just a number, volume, or alcohol percentage
            if not re.match(r'^[\d\s%\.]+$', text) and len(text) > 3:
                # Skip if it's the brand we already found
                if label_info.brand and label_info.brand.lower() in text.lower():
                    continue
                if not label_info.product_name:
                    label_info.product_name = text
                    break

    return label_info


# ============================================================================
# Semantic Matching with NLP Embeddings
# ============================================================================

def compute_semantic_embedding(text: str) -> Optional[np.ndarray]:
    """Compute semantic embedding for text using sentence transformers."""
    model = _get_sentence_model()

    if model is None:
        return None

    try:
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding
    except Exception as e:
        logger.debug(f"Failed to compute embedding: {e}")
        return None


def semantic_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings."""
    if embedding1 is None or embedding2 is None:
        return 0.0

    dot_product = np.dot(embedding1, embedding2)
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))


def compute_semantic_text_similarity(text1: str, text2: str) -> float:
    """Compute semantic similarity between two texts using embeddings."""
    emb1 = compute_semantic_embedding(text1)
    emb2 = compute_semantic_embedding(text2)

    return semantic_similarity(emb1, emb2)


# ============================================================================
# Text Similarity Functions
# ============================================================================

def compute_text_similarity(text1: str, text2: str, use_semantic: bool = True) -> float:
    """Compute similarity between two text strings.

    Uses combination of:
    - Fuzzy matching (for OCR error tolerance)
    - Sequence matching (for similar spellings)
    - Keyword overlap (for semantic similarity)
    - Semantic embeddings (if available)
    """
    if not text1 or not text2:
        return 0.0

    text1_lower = text1.lower().strip()
    text2_lower = text2.lower().strip()

    # Exact match
    if text1_lower == text2_lower:
        return 1.0

    # Fuzzy match (handles OCR errors)
    _, fuzzy_sim = fuzzy_match(text1_lower, text2_lower)

    # Sequence similarity
    seq_sim = SequenceMatcher(None, text1_lower, text2_lower).ratio()

    # Keyword overlap
    words1 = set(re.findall(r'\b[a-zA-Z]{3,}\b', text1_lower))
    words2 = set(re.findall(r'\b[a-zA-Z]{3,}\b', text2_lower))

    if words1 and words2:
        overlap = len(words1 & words2)
        total = len(words1 | words2)
        keyword_sim = overlap / total if total > 0 else 0.0
    else:
        keyword_sim = 0.0

    # Semantic similarity (if available)
    semantic_sim = 0.0
    if use_semantic and _SENTENCE_MODEL_AVAILABLE:
        semantic_sim = compute_semantic_text_similarity(text1, text2)

    # Weighted combination
    if semantic_sim > 0:
        # With semantic matching
        return fuzzy_sim * 0.25 + seq_sim * 0.25 + keyword_sim * 0.2 + semantic_sim * 0.3
    else:
        # Without semantic matching
        return fuzzy_sim * 0.4 + seq_sim * 0.35 + keyword_sim * 0.25


def compute_label_similarity(label1: LabelInfo, label2: LabelInfo, use_semantic: bool = True) -> float:
    """Compute similarity between two label extractions."""

    if not label1.raw_text and not label2.raw_text:
        return 0.0

    scores = []
    weights = []

    # Brand similarity (high weight if both have brands)
    if label1.brand and label2.brand:
        _, brand_sim = fuzzy_match(label1.brand.lower(), label2.brand.lower())
        scores.append(brand_sim)
        weights.append(0.35)

    # Product name similarity
    if label1.product_name and label2.product_name:
        name_sim = compute_text_similarity(label1.product_name, label2.product_name, use_semantic)
        scores.append(name_sim)
        weights.append(0.30)

    # Keyword overlap
    if label1.keywords and label2.keywords:
        kw1 = set(label1.keywords)
        kw2 = set(label2.keywords)
        overlap = len(kw1 & kw2)
        total = len(kw1 | kw2)
        keyword_sim = overlap / total if total > 0 else 0.0
        scores.append(keyword_sim)
        weights.append(0.20)

    # Distinguishing words match (important for variants)
    if label1.distinguishing_words or label2.distinguishing_words:
        dw1 = set(label1.distinguishing_words)
        dw2 = set(label2.distinguishing_words)
        if dw1 and dw2:
            dw_overlap = len(dw1 & dw2)
            dw_total = len(dw1 | dw2)
            dw_sim = dw_overlap / dw_total if dw_total > 0 else 0.0
            scores.append(dw_sim)
            weights.append(0.10)

    # Semantic embedding similarity
    if use_semantic and label1.semantic_embedding is not None and label2.semantic_embedding is not None:
        sem_sim = semantic_similarity(label1.semantic_embedding, label2.semantic_embedding)
        scores.append(sem_sim)
        weights.append(0.15)

    # Raw text similarity (fallback)
    raw_sim = compute_text_similarity(label1.raw_text, label2.raw_text, use_semantic=False)
    scores.append(raw_sim)
    weights.append(0.05)

    # Weighted average
    if not weights:
        return 0.0

    total_weight = sum(weights)
    weighted_sum = sum(s * w for s, w in zip(scores, weights))

    return weighted_sum / total_weight if total_weight > 0 else 0.0


# ============================================================================
# Feature Vector Functions
# ============================================================================

def extract_text_features_vector(label_info: LabelInfo) -> np.ndarray:
    """Convert label info to a feature vector for ML matching.

    Creates a fixed-size vector encoding the text information.
    """
    # Feature vector components:
    # - Character frequency distribution (26 dims for a-z)
    # - Word count features (5 dims)
    # - Has brand, has volume, has alcohol (3 dims)
    # - Keyword hash features (32 dims)

    vector = np.zeros(66, dtype=np.float32)

    if not label_info.raw_text:
        return vector

    text = label_info.raw_text.lower()

    # Character frequency (26 dims)
    char_counts = np.zeros(26)
    for c in text:
        if 'a' <= c <= 'z':
            char_counts[ord(c) - ord('a')] += 1

    total_chars = char_counts.sum()
    if total_chars > 0:
        vector[:26] = char_counts / total_chars

    # Word count features (5 dims)
    words = text.split()
    vector[26] = min(len(words) / 20.0, 1.0)  # Normalized word count
    vector[27] = min(len(text) / 200.0, 1.0)  # Normalized char count
    vector[28] = len(label_info.keywords) / 20.0 if label_info.keywords else 0.0
    vector[29] = 1.0 if label_info.brand else 0.0
    vector[30] = 1.0 if label_info.volume else 0.0

    # Distinguishing words presence (2 dims)
    vector[31] = min(len(label_info.distinguishing_words) / 5.0, 1.0)
    vector[32] = 1.0 if label_info.brand_category else 0.0

    # Keyword hash features (32 dims) - simple hash-based encoding
    for keyword in label_info.keywords[:10]:
        # Use hash to distribute keywords across 32 bins
        h = hash(keyword) % 32
        vector[34 + h] = min(vector[34 + h] + 0.2, 1.0)

    # Normalize
    norm = np.linalg.norm(vector)
    if norm > 1e-7:
        vector = vector / norm

    return vector


# ============================================================================
# Utility Functions
# ============================================================================

def get_ocr_status() -> Dict[str, Any]:
    """Get OCR service status."""
    return {
        "ocr_available": _OCR_AVAILABLE,
        "reader_loaded": _OCR_READER is not None,
        "gpu_enabled": OCR_GPU_ENABLED,
        "languages": OCR_LANGUAGES,
        "confidence_threshold": OCR_CONFIDENCE_THRESHOLD,
        "semantic_matching_available": _SENTENCE_MODEL_AVAILABLE,
        "semantic_model_loaded": _SENTENCE_MODEL is not None,
        "cache_stats": _OCR_CACHE.stats(),
        "brand_count": len(ALL_BRANDS),
    }


def clear_ocr_cache():
    """Clear the OCR cache."""
    _OCR_CACHE.clear()
    logger.info("OCR cache cleared")


def get_brand_info(brand_name: str) -> Optional[Dict[str, Any]]:
    """Get information about a brand."""
    brand_lower = brand_name.lower()

    # Exact match
    if brand_lower in ALL_BRANDS:
        return {
            "brand": brand_name,
            "category": BRAND_TO_CATEGORY.get(brand_lower),
            "match_type": "exact"
        }

    # Fuzzy match
    match = find_best_fuzzy_match(brand_lower, list(ALL_BRANDS), threshold=0.7)
    if match:
        return {
            "brand": match[0].title(),
            "category": BRAND_TO_CATEGORY.get(match[0]),
            "match_type": "fuzzy",
            "similarity": match[1]
        }

    return None


def extract_text_simple(image_data: bytes) -> str:
    """Simple text extraction - returns just the raw text."""
    label_info = extract_text_from_image(image_data)
    return label_info.raw_text
