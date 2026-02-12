"""
YOLO Detection Service for Bar Item Detection.

Uses YOLOv8 to detect bar items (bottles, cans, glasses, garnishes) before
product recognition. Returns is_bar_item=False if no valid bar items detected.
"""

import io
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path

import numpy as np
from PIL import Image, ExifTags

logger = logging.getLogger(__name__)


def fix_image_orientation(image: Image.Image) -> Image.Image:
    """Fix image orientation based on EXIF data."""
    try:
        # Get EXIF orientation tag
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break

        exif = image._getexif()
        if exif is not None:
            orientation_value = exif.get(orientation)
            if orientation_value == 3:
                image = image.rotate(180, expand=True)
            elif orientation_value == 6:
                image = image.rotate(270, expand=True)
            elif orientation_value == 8:
                image = image.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError):
        # No EXIF data or orientation tag
        pass
    return image


# Bar item classes for detection
BAR_ITEM_CLASSES = {
    "bottle": 0,
    "can": 1,
    "glass": 2,
    "garnish": 3,
    "shaker": 4,
    "tap_handle": 5,
}

# Classes that should trigger product recognition
RECOGNIZABLE_CLASSES = {"bottle", "can", "glass"}

# COCO class mapping for pre-trained model (fallback)
COCO_CLASS_NAMES = {
    39: "bottle",      # COCO bottle class
    40: "glass",       # COCO wine glass
    41: "glass",       # COCO cup
    76: "glass",       # COCO vase (sometimes cans)
}

# Valid COCO classes for bar items
COCO_BAR_CLASSES = {39, 40, 41}

# Classes that should definitely REJECT (not bar items)
# If we detect these with high confidence, it's NOT a bar item
NON_BAR_CLASSES = {
    0,   # person
    1,   # bicycle
    2,   # car
    3,   # motorcycle
    5,   # bus
    7,   # truck
    14,  # bird
    15,  # cat
    16,  # dog
    17,  # horse
    24,  # backpack
    26,  # handbag
    63,  # laptop
    64,  # mouse
    65,  # remote
    67,  # cell phone
}


@dataclass
class Detection:
    """Single object detection result."""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    is_bar_item: bool

    def to_dict(self):
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": list(self.bbox),
            "is_bar_item": self.is_bar_item,
        }


class YOLODetectionService:
    """YOLO-based bar item detection service."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.15,  # Lower threshold to catch more detections
        use_custom_model: bool = False,
    ):
        """
        Initialize YOLO detection service.

        Args:
            model_path: Path to custom YOLO model. If None, uses pre-trained.
            confidence_threshold: Minimum confidence for detections.
            use_custom_model: Whether to use custom bar-trained model.
        """
        self.confidence_threshold = confidence_threshold
        self.use_custom_model = use_custom_model
        self.model = None
        self.model_path = model_path

        # Lazy load model on first use
        self._model_loaded = False

    def _load_model(self):
        """Lazy load YOLO model."""
        if self._model_loaded:
            return

        try:
            from ultralytics import YOLO

            if self.use_custom_model and self.model_path and Path(self.model_path).exists():
                logger.info(f"Loading custom YOLO model from {self.model_path}")
                self.model = YOLO(self.model_path)
            else:
                # Use pre-trained YOLOv8 nano (fastest)
                logger.info("Loading pre-trained YOLOv8n model")
                self.model = YOLO("yolov8n.pt")

            self._model_loaded = True
            logger.info("YOLO model loaded successfully")

        except ImportError:
            logger.warning("ultralytics not installed, YOLO detection disabled")
            self.model = None
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.model = None

    def detect(self, image_data: bytes) -> List[Detection]:
        """
        Detect bar items in an image.

        Args:
            image_data: Image bytes (JPEG, PNG, etc.)

        Returns:
            List of Detection objects for bar items found.
        """
        self._load_model()

        if self.model is None:
            logger.warning("YOLO model not available, skipping detection")
            return []

        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            # Fix EXIF orientation (important for phone photos)
            image = fix_image_orientation(image)
            if image.mode != "RGB":
                image = image.convert("RGB")
            # Run YOLO inference
            results = self.model(image, verbose=False)

            detections = []
            for result in results:
                if result.boxes is None:
                    continue

                for box in result.boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])

                    # Skip low confidence detections
                    if confidence < self.confidence_threshold:
                        continue

                    # Map COCO class to bar item class
                    class_name = result.names.get(class_id, "unknown")

                    if self.use_custom_model:
                        # Custom model - use class names directly
                        is_bar = class_name in RECOGNIZABLE_CLASSES
                    else:
                        # Pre-trained COCO model - check if bar item
                        if class_id in COCO_BAR_CLASSES:
                            class_name = COCO_CLASS_NAMES.get(class_id, class_name)
                            is_bar = True
                        elif class_id in NON_BAR_CLASSES:
                            # Track non-bar items for rejection logic
                            is_bar = False
                        else:
                            # Unknown class - skip
                            continue

                    # Get bounding box
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    bbox = (int(x1), int(y1), int(x2), int(y2))

                    detections.append(Detection(
                        class_id=class_id,
                        class_name=class_name,
                        confidence=confidence,
                        bbox=bbox,
                        is_bar_item=is_bar,
                    ))

            # Sort by confidence (highest first)
            detections.sort(key=lambda d: d.confidence, reverse=True)

            logger.info(f"YOLO detected {len(detections)} bar items")
            return detections

        except Exception as e:
            logger.error(f"YOLO detection failed: {e}")
            return []

    def has_bar_item(self, detections: List[Detection]) -> bool:
        """Check if any detection is a recognizable bar item."""
        return any(d.is_bar_item for d in detections)

    def get_best_detection(self, detections: List[Detection]) -> Optional[Detection]:
        """Get the best (highest confidence) bar item detection."""
        bar_detections = [d for d in detections if d.is_bar_item]
        if bar_detections:
            return bar_detections[0]  # Already sorted by confidence
        return None

    def has_non_bar_item(self, detections: List[Detection]) -> bool:
        """Check if we detected something that's definitely NOT a bar item."""
        # Only return True if we have high-confidence detection of non-bar items
        for d in detections:
            if not d.is_bar_item and d.confidence > 0.5:
                # Check if class is in our "definitely not bar" list
                if d.class_id in NON_BAR_CLASSES:
                    return True
        return False

    def crop_to_detection(
        self,
        image_data: bytes,
        detection: Detection,
        padding: float = 0.1,
    ) -> bytes:
        """
        Crop image to detection bounding box with padding.

        Args:
            image_data: Original image bytes.
            detection: Detection with bbox.
            padding: Padding ratio (0.1 = 10% extra on each side).

        Returns:
            Cropped image bytes (JPEG).
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            if image.mode != "RGB":
                image = image.convert("RGB")

            img_width, img_height = image.size
            x1, y1, x2, y2 = detection.bbox

            # Add padding
            box_width = x2 - x1
            box_height = y2 - y1
            pad_x = int(box_width * padding)
            pad_y = int(box_height * padding)

            # Ensure within bounds
            x1 = max(0, x1 - pad_x)
            y1 = max(0, y1 - pad_y)
            x2 = min(img_width, x2 + pad_x)
            y2 = min(img_height, y2 + pad_y)

            # Crop
            cropped = image.crop((x1, y1, x2, y2))

            # Convert back to bytes
            buffer = io.BytesIO()
            cropped.save(buffer, format="JPEG", quality=95)
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Failed to crop image: {e}")
            return image_data  # Return original on error


# Global singleton instance
_detection_service: Optional[YOLODetectionService] = None


def get_detection_service() -> YOLODetectionService:
    """Get or create the global YOLO detection service."""
    global _detection_service
    if _detection_service is None:
        _detection_service = YOLODetectionService()
    return _detection_service


def detect_bar_items(image_data: bytes) -> List[Detection]:
    """
    Convenience function to detect bar items in an image.

    Args:
        image_data: Image bytes.

    Returns:
        List of Detection objects.
    """
    service = get_detection_service()
    return service.detect(image_data)


def is_bar_item_image(image_data: bytes) -> Tuple[bool, Optional[Detection], bool]:
    """
    Check if an image contains a bar item.

    Args:
        image_data: Image bytes.

    Returns:
        Tuple of (is_bar_item, best_detection, is_definitely_not_bar).
        - is_bar_item: True if bar item detected
        - best_detection: The detection object if found
        - is_definitely_not_bar: True only if we detected something clearly NOT a bar item
    """
    service = get_detection_service()
    detections = service.detect(image_data)

    # Check if we detected a bar item
    if detections and service.has_bar_item(detections):
        return True, service.get_best_detection(detections), False

    # Check if we detected something that's definitely NOT a bar item
    # (person, car, laptop, etc. with high confidence)
    is_definitely_not_bar = service.has_non_bar_item(detections)

    # If nothing detected OR only non-bar items detected
    return False, None, is_definitely_not_bar
