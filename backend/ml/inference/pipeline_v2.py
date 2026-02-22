"""
2-Stage ML Pipeline for Shelf Recognition (V2)

Stage 1: YOLO Bottle Detection - find all bottles/cans in image
Stage 2: SKU Classification - identify each detected item

Usage:
    from ml.inference.pipeline_v2 import PipelineV2

    pipeline = PipelineV2.from_config("ml/configs/pipeline.yaml")
    results = pipeline.process(image_bytes)
"""

import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """Single detection from Stage 1."""
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    class_name: str
    confidence: float
    crop: Optional[np.ndarray] = None


@dataclass
class Classification:
    """Single classification result from Stage 2."""
    sku_id: str
    sku_name: str
    confidence: float
    embedding: Optional[np.ndarray] = None
    is_unknown: bool = False
    ocr_text: Optional[str] = None
    ocr_confidence: float = 0.0
    ocr_boosted: bool = False  # True if OCR changed the result


@dataclass
class ShelfItem:
    """Combined detection + classification result."""
    detection: Detection
    classification: Optional[Classification]
    item_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class PipelineResult:
    """Full pipeline output."""
    items: List[ShelfItem]
    sku_counts: Dict[str, int]
    total_items: int
    unknown_count: int
    processing_time_ms: float
    low_confidence_items: List[ShelfItem]  # For active learning


class Stage1Detector:
    """YOLO-based bottle/can detector."""

    def __init__(self, config: Dict):
        self.config = config
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load YOLO model."""
        model_path = self.config.get("model_path")

        if model_path and Path(model_path).exists():
            try:
                # Try ONNX first
                if model_path.endswith(".onnx"):
                    self._load_onnx(model_path)
                else:
                    self._load_ultralytics(model_path)
            except Exception as e:
                logger.warning(f"Failed to load model: {e}")
                self.model = None
        else:
            # Try fallback to pre-trained YOLOv8
            fallback_paths = [
                "yolov8n.pt",  # Current directory
                "models/detector/yolov8n.pt",
                "/Users/zver/Downloads/V99/inventory-system/backend/yolov8n.pt",
            ]
            for fallback in fallback_paths:
                if Path(fallback).exists():
                    logger.info(f"Using pre-trained YOLO: {fallback}")
                    try:
                        self._load_ultralytics(fallback)
                        return
                    except Exception as e:
                        logger.warning(f"Failed to load fallback: {e}")

            logger.warning(f"No YOLO model found, using mock detector")
            self.model = None

    def _load_onnx(self, model_path: str):
        """Load ONNX model for inference."""
        try:
            import onnxruntime as ort

            self.session = ort.InferenceSession(
                model_path,
                providers=["CoreMLExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
            )
            self.model = "onnx"
            logger.info(f"Loaded ONNX model: {model_path}")
        except ImportError:
            logger.warning("onnxruntime not installed")
            raise

    def _load_ultralytics(self, model_path: str):
        """Load model via ultralytics."""
        try:
            from ultralytics import YOLO

            self.model = YOLO(model_path)
            logger.info(f"Loaded YOLO model: {model_path}")
        except ImportError:
            logger.warning("ultralytics not installed")
            raise

    def detect(self, image: np.ndarray) -> List[Detection]:
        """
        Detect bottles/cans in image.

        Args:
            image: RGB image as numpy array (H, W, 3)

        Returns:
            List of Detection objects
        """
        if self.model is None:
            # Mock detection for testing
            return self._mock_detect(image)

        # Apply contrast enhancement for low-contrast images
        enhanced = self._enhance_contrast(image)

        if self.model == "onnx":
            return self._detect_onnx(enhanced)
        else:
            return self._detect_ultralytics(enhanced)

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance image contrast for better detection of low-contrast bottles."""
        import cv2

        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])

        # Convert back to RGB
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

        return enhanced

    def _detect_ultralytics(self, image: np.ndarray) -> List[Detection]:
        """Run detection with ultralytics YOLO."""
        results = self.model(
            image,
            conf=self.config.get("conf_threshold", 0.5),
            iou=self.config.get("iou_threshold", 0.45),
            max_det=self.config.get("max_detections", 50),
            verbose=False,
        )[0]

        detections = []
        process_classes = set(self.config.get("process_classes", ["bottle", "can", "glass"]))

        for box in results.boxes:
            class_id = int(box.cls[0])
            class_name = results.names[class_id]

            if class_name not in process_classes:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0])

            # Crop with padding
            padding = self.config.get("crop_padding", 0.1)
            h, w = image.shape[:2]
            pad_x = int((x2 - x1) * padding)
            pad_y = int((y2 - y1) * padding)

            crop_x1 = max(0, x1 - pad_x)
            crop_y1 = max(0, y1 - pad_y)
            crop_x2 = min(w, x2 + pad_x)
            crop_y2 = min(h, y2 + pad_y)

            crop = image[crop_y1:crop_y2, crop_x1:crop_x2]

            detections.append(Detection(
                bbox=(x1, y1, x2, y2),
                class_name=class_name,
                confidence=conf,
                crop=crop,
            ))

        return detections

    def _detect_onnx(self, image: np.ndarray) -> List[Detection]:
        """Run detection with ONNX model."""
        import cv2

        # Preprocess
        input_size = 640
        h, w = image.shape[:2]
        scale = input_size / max(h, w)
        new_h, new_w = int(h * scale), int(w * scale)

        resized = cv2.resize(image, (new_w, new_h))

        # Pad to square
        padded = np.zeros((input_size, input_size, 3), dtype=np.uint8)
        padded[:new_h, :new_w] = resized

        # Normalize
        input_tensor = padded.astype(np.float32) / 255.0
        input_tensor = input_tensor.transpose(2, 0, 1)[np.newaxis, ...]

        # Run inference
        outputs = self.session.run(None, {"images": input_tensor})[0]

        # Parse YOLO output (simplified)
        detections = []
        conf_threshold = self.config.get("conf_threshold", 0.5)

        # YOLO output format: (batch, num_detections, 4 + num_classes)
        for det in outputs[0]:
            conf = det[4]
            if conf < conf_threshold:
                continue

            # Get class
            class_scores = det[5:]
            class_id = np.argmax(class_scores)
            class_conf = class_scores[class_id]

            if class_conf < conf_threshold:
                continue

            # Bbox (center format to corner)
            cx, cy, bw, bh = det[:4]
            x1 = int((cx - bw / 2) / scale)
            y1 = int((cy - bh / 2) / scale)
            x2 = int((cx + bw / 2) / scale)
            y2 = int((cy + bh / 2) / scale)

            # Clamp
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            class_names = ["bottle", "can", "glass", "unknown_container"]
            class_name = class_names[class_id] if class_id < len(class_names) else "unknown"

            crop = image[y1:y2, x1:x2]

            detections.append(Detection(
                bbox=(x1, y1, x2, y2),
                class_name=class_name,
                confidence=float(conf * class_conf),
                crop=crop,
            ))

        return detections

    def _mock_detect(self, image: np.ndarray) -> List[Detection]:
        """Mock detection for testing without model."""
        h, w = image.shape[:2]

        # Return a mock detection in center of image
        cx, cy = w // 2, h // 2
        size = min(h, w) // 3

        x1, y1 = cx - size // 2, cy - size // 2
        x2, y2 = cx + size // 2, cy + size // 2

        crop = image[y1:y2, x1:x2]

        return [Detection(
            bbox=(x1, y1, x2, y2),
            class_name="bottle",
            confidence=0.95,
            crop=crop,
        )]


class Stage2Classifier:
    """SKU classifier using embeddings."""

    def __init__(self, config: Dict):
        self.config = config
        self.model = None
        self.embeddings = None
        self.sku_mapping = None
        self._load_model()

    def _load_model(self):
        """Load classifier model and embeddings."""
        model_path = self.config.get("model_path")
        embeddings_path = self.config.get("embeddings_path")
        mapping_path = self.config.get("sku_mapping_path")

        # Load embeddings
        if embeddings_path and Path(embeddings_path).exists():
            self.embeddings = np.load(embeddings_path, allow_pickle=True).item()
            logger.info(f"Loaded embeddings for {len(self.embeddings)} SKUs")

        # Load SKU mapping
        if mapping_path and Path(mapping_path).exists():
            with open(mapping_path, "r") as f:
                self.sku_mapping = json.load(f)
            logger.info(f"Loaded SKU mapping")

        # Load ONNX model
        if model_path and Path(model_path).exists():
            try:
                import onnxruntime as ort

                self.session = ort.InferenceSession(
                    model_path,
                    providers=["CoreMLExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
                )
                self.model = "onnx"
                logger.info(f"Loaded classifier ONNX: {model_path}")
            except Exception as e:
                logger.warning(f"Failed to load classifier: {e}")
                self.model = None
        else:
            # Try CLIP fallback if embeddings exist
            if self.embeddings is not None:
                try:
                    from app.services.ai.clip_service import get_clip_embedding, is_clip_available
                    if is_clip_available():
                        self.model = "clip"
                        self._clip_get_embedding = get_clip_embedding
                        logger.info("Using CLIP for classification (no ONNX model)")
                    else:
                        logger.warning("CLIP not available, using mock classifier")
                except ImportError:
                    logger.warning("CLIP service not available, using mock classifier")
            else:
                logger.warning("No embeddings or model, using mock classifier")

    def classify(self, crop: np.ndarray) -> Tuple[Classification, List[Tuple[str, float]]]:
        """
        Classify a cropped bottle/can image.

        Args:
            crop: RGB image crop as numpy array

        Returns:
            Tuple of (Classification result, all candidates with scores)
        """
        if self.embeddings is None:
            return self._mock_classify(), []

        if self.model is None:
            return self._mock_classify(), []

        # Get embedding
        embedding = self._get_embedding(crop)

        # Find nearest SKU
        return self._match_embedding(embedding)

    def _get_embedding(self, crop: np.ndarray) -> np.ndarray:
        """Extract embedding from crop."""
        import cv2

        if self.model == "clip":
            # Use CLIP for embedding extraction
            # Convert numpy array to JPEG bytes
            _, buffer = cv2.imencode('.jpg', cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
            image_bytes = buffer.tobytes()

            embedding = self._clip_get_embedding(image_bytes)
            if embedding is not None:
                embedding = embedding / (np.linalg.norm(embedding) + 1e-7)
                return embedding
            else:
                # Return zero embedding on failure
                return np.zeros(512, dtype=np.float32)

        # ONNX model path
        # Preprocess
        resized = cv2.resize(crop, (224, 224))
        normalized = resized.astype(np.float32) / 255.0

        # ImageNet normalization
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        normalized = (normalized - mean) / std

        # CHW format
        input_tensor = normalized.transpose(2, 0, 1)[np.newaxis, ...].astype(np.float32)

        # Run inference
        embedding = self.session.run(None, {"image": input_tensor})[0][0]

        # Normalize
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def _match_embedding(self, embedding: np.ndarray) -> Tuple[Classification, List[Tuple[str, float]]]:
        """Match embedding to known SKUs.

        Returns:
            Tuple of (Classification, list of (sku_id, similarity) for all candidates)
        """
        sim_config = self.config.get("similarity", {})
        min_conf = sim_config.get("min_confidence", 0.65)
        unknown_thresh = self.config.get("unknown_threshold", 0.50)
        top_k = sim_config.get("top_k", 5)

        # Compute similarities
        similarities = {}
        for sku_name, sku_emb in self.embeddings.items():
            sku_emb = sku_emb / np.linalg.norm(sku_emb)
            sim = float(np.dot(embedding, sku_emb))
            similarities[sku_name] = sim

        # Sort by similarity
        sorted_skus = sorted(similarities.items(), key=lambda x: x[1], reverse=True)

        # Return all candidates for OCR refinement
        all_candidates = [(sku, sim) for sku, sim in sorted_skus]

        if not sorted_skus:
            return Classification(
                sku_id="unknown",
                sku_name="Unknown Product",
                confidence=0.0,
                embedding=embedding,
                is_unknown=True,
            ), all_candidates

        best_sku, best_sim = sorted_skus[0]

        # Check if unknown
        if best_sim < unknown_thresh:
            return Classification(
                sku_id="unknown",
                sku_name="Unknown Product",
                confidence=best_sim,
                embedding=embedding,
                is_unknown=True,
            ), all_candidates

        # Get friendly name from sku_mapping if available
        sku_name = best_sku
        if self.sku_mapping and best_sku in self.sku_mapping:
            mapping_info = self.sku_mapping[best_sku]
            if isinstance(mapping_info, dict):
                sku_name = mapping_info.get("name", best_sku)
            else:
                sku_name = str(mapping_info)

        return Classification(
            sku_id=best_sku,
            sku_name=sku_name,
            confidence=best_sim,
            embedding=embedding,
            is_unknown=False,
        ), all_candidates

    def _mock_classify(self) -> Classification:
        """Mock classification for testing."""
        return Classification(
            sku_id="mock_sku",
            sku_name="Mock Product",
            confidence=0.85,
            is_unknown=False,
        )


class Stage3OCR:
    """OCR-based text recognition for label reading and classification refinement."""

    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.confidence_threshold = config.get("confidence_threshold", 0.70)
        self.boost_threshold = config.get("boost_threshold", 0.05)  # Min diff to boost
        self.ocr_weight = config.get("ocr_weight", 0.3)  # Weight for OCR in final score
        self._ocr_reader = None
        self._ocr_available = False

        if self.enabled:
            self._init_ocr()

    def _init_ocr(self):
        """Initialize OCR reader."""
        try:
            import easyocr
            self._ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            self._ocr_available = True
            logger.info("Stage 3 OCR initialized")
        except Exception as e:
            logger.warning(f"OCR initialization failed: {e}")
            self._ocr_available = False

    def extract_text(self, crop: np.ndarray) -> Tuple[str, float]:
        """Extract text from crop image.

        Returns:
            Tuple of (extracted_text, confidence)
        """
        if not self._ocr_available or self._ocr_reader is None:
            return "", 0.0

        try:
            # Run OCR
            results = self._ocr_reader.readtext(crop)

            if not results:
                return "", 0.0

            # Combine all text with confidence weighting
            texts = []
            total_conf = 0.0
            count = 0

            for bbox, text, conf in results:
                if conf > 0.3 and len(text.strip()) > 1:
                    texts.append(text.strip())
                    total_conf += conf
                    count += 1

            combined_text = " ".join(texts).lower()
            avg_conf = total_conf / count if count > 0 else 0.0

            return combined_text, avg_conf

        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
            return "", 0.0

    def compute_text_similarity(self, ocr_text: str, product_name: str) -> float:
        """Compute similarity between OCR text and product name.

        Uses word matching with emphasis on:
        - Exact word matches (especially distinguishing words like 'silver', 'gold', etc.)
        - Brand name matches
        - Partial matches for longer words
        - CRITICAL: Penalize if OCR has distinguishing words not in product name
        """
        if not ocr_text or not product_name:
            return 0.0

        ocr_lower = ocr_text.lower()
        name_lower = product_name.lower()

        # Check for exact full name match
        if name_lower in ocr_lower:
            return 0.98

        # Check word overlap
        ocr_words = set(ocr_lower.split())
        name_words = set(name_lower.split())

        # Remove common stopwords
        stopwords = {'the', 'and', 'or', 'of', 'with', 'for', 'vol', 'ml', 'cl', 'l', 'vodka', 'gin', 'rum', 'whiskey', 'tequila'}
        ocr_filtered = ocr_words - stopwords
        name_filtered = name_words - stopwords

        if not name_filtered:
            return 0.0

        # Count exact word matches
        exact_matches = 0
        distinguishing_matches = 0
        total_name_words = len(name_filtered)

        # Distinguishing words that differentiate variants (gold, silver, black, red, etc.)
        distinguishing_words = {'silver', 'gold', 'black', 'red', 'blue', 'white', 'green',
                                'premium', 'reserve', 'special', 'original', 'classic',
                                'light', 'dark', 'extra', 'aged', 'double', 'triple'}

        for word in name_filtered:
            if word in ocr_filtered:
                exact_matches += 1
                # Extra weight for distinguishing words
                if word in distinguishing_words:
                    distinguishing_matches += 1
            else:
                # Partial match for longer words (e.g., "savoy" in "8avoy")
                for ocr_word in ocr_filtered:
                    if len(word) > 4 and len(ocr_word) > 4:
                        # Check if >70% of characters match
                        common = sum(1 for c in word if c in ocr_word)
                        if common / len(word) > 0.7:
                            exact_matches += 0.5
                            break

        # Base score from word coverage
        if total_name_words > 0:
            coverage = exact_matches / total_name_words
        else:
            coverage = 0.0

        # Bonus for distinguishing words (critical for variants like Savoy vs Savoy Silver)
        distinguishing_bonus = distinguishing_matches * 0.2

        # Penalty if product has distinguishing word but OCR doesn't match it
        distinguishing_penalty = 0
        for word in name_filtered:
            if word in distinguishing_words and word not in ocr_filtered:
                distinguishing_penalty = 0.3  # Significant penalty
                break

        # CRITICAL: Penalty if OCR has distinguishing word that product name DOESN'T have
        # This helps differentiate "Savoy Vodka" from "Savoy Silver Vodka" when OCR shows "silver"
        ocr_distinguishing_penalty = 0
        for ocr_word in ocr_filtered:
            if ocr_word in distinguishing_words and ocr_word not in name_filtered:
                ocr_distinguishing_penalty = 0.35  # Strong penalty - OCR clearly shows variant word
                break

        final_score = min(coverage + distinguishing_bonus - distinguishing_penalty - ocr_distinguishing_penalty, 1.0)
        return max(final_score, 0.0)

    def refine_classification(
        self,
        crop: np.ndarray,
        classification: Classification,
        all_candidates: List[Tuple[str, float]],  # [(sku_id, visual_sim), ...]
        sku_mapping: Dict,
    ) -> Classification:
        """Refine classification using OCR.

        If OCR text strongly matches a different candidate, boost or switch to it.
        """
        if not self.enabled or not self._ocr_available:
            return classification

        # Extract text from crop
        ocr_text, ocr_conf = self.extract_text(crop)

        if not ocr_text or ocr_conf < 0.3:
            return classification

        # Get current best match name
        current_name = classification.sku_name

        # Compute OCR similarity for top candidates
        ocr_scores = []
        for sku_id, visual_sim in all_candidates[:10]:
            # Get product name from mapping
            product_name = sku_id
            if sku_mapping and sku_id in sku_mapping:
                info = sku_mapping[sku_id]
                if isinstance(info, dict):
                    product_name = info.get("name", sku_id)

            ocr_sim = self.compute_text_similarity(ocr_text, product_name)

            # Combined score: visual + OCR
            combined = visual_sim * (1 - self.ocr_weight) + ocr_sim * self.ocr_weight

            ocr_scores.append({
                'sku_id': sku_id,
                'name': product_name,
                'visual_sim': visual_sim,
                'ocr_sim': ocr_sim,
                'combined': combined,
            })

        # Sort by combined score
        ocr_scores.sort(key=lambda x: x['combined'], reverse=True)

        if not ocr_scores:
            return classification

        best = ocr_scores[0]
        current_score = next(
            (s for s in ocr_scores if s['sku_id'] == classification.sku_id),
            {'combined': classification.confidence}
        )

        # Check if OCR suggests a different product
        ocr_boosted = False
        new_sku_id = classification.sku_id
        new_sku_name = classification.sku_name
        new_confidence = classification.confidence

        # Switch if OCR strongly favors a different product
        if best['sku_id'] != classification.sku_id:
            score_diff = best['combined'] - current_score.get('combined', 0)
            if score_diff > self.boost_threshold and best['ocr_sim'] > 0.5:
                new_sku_id = best['sku_id']
                new_sku_name = best['name']
                new_confidence = best['combined']
                ocr_boosted = True
                logger.info(
                    f"OCR boost: {classification.sku_name} -> {new_sku_name} "
                    f"(text: '{ocr_text[:20]}...', sim: {best['ocr_sim']:.2f})"
                )

        # Update classification with OCR info
        return Classification(
            sku_id=new_sku_id,
            sku_name=new_sku_name,
            confidence=new_confidence,
            embedding=classification.embedding,
            is_unknown=classification.is_unknown if not ocr_boosted else False,
            ocr_text=ocr_text,
            ocr_confidence=ocr_conf,
            ocr_boosted=ocr_boosted,
        )


class ActiveLearningQueue:
    """Queue for low-confidence items needing human review."""

    def __init__(self, config: Dict):
        self.config = config
        self.queue_path = Path(config.get("queue_path", "data/active_learning_queue"))
        self.queue_path.mkdir(parents=True, exist_ok=True)
        self.threshold = config.get("low_confidence_threshold", 0.70)

    def should_queue(self, item: ShelfItem) -> bool:
        """Check if item should be queued for review."""
        if item.classification is None:
            return True
        return item.classification.confidence < self.threshold

    def add(self, item: ShelfItem, image: np.ndarray):
        """Add item to queue for human review."""
        import cv2

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        item_id = item.item_id

        # Save crop
        if item.detection.crop is not None:
            crop_path = self.queue_path / f"{timestamp}_{item_id}.jpg"
            cv2.imwrite(str(crop_path), cv2.cvtColor(item.detection.crop, cv2.COLOR_RGB2BGR))

        # Save metadata
        meta = {
            "item_id": item_id,
            "timestamp": timestamp,
            "detection": {
                "bbox": item.detection.bbox,
                "class_name": item.detection.class_name,
                "confidence": item.detection.confidence,
            },
            "classification": {
                "sku_id": item.classification.sku_id if item.classification else None,
                "sku_name": item.classification.sku_name if item.classification else None,
                "confidence": item.classification.confidence if item.classification else None,
                "is_unknown": item.classification.is_unknown if item.classification else True,
            },
        }

        meta_path = self.queue_path / f"{timestamp}_{item_id}.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Added item to active learning queue: {item_id}")


class PipelineV2:
    """3-stage ML pipeline for shelf recognition."""

    def __init__(self, config: Dict):
        self.config = config
        self.detector = Stage1Detector(config.get("stage1_detector", {}))
        self.classifier = Stage2Classifier(config.get("stage2_classifier", {}))

        # Stage 3: OCR for label text recognition and classification refinement
        ocr_config = config.get("stage3_ocr", {"enabled": True})
        self.ocr = Stage3OCR(ocr_config)

        al_config = config.get("active_learning", {})
        self.active_learning = ActiveLearningQueue(al_config) if al_config.get("enabled") else None

    @classmethod
    def from_config(cls, config_path: str) -> "PipelineV2":
        """Load pipeline from config file."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return cls(config)

    def process(self, image: np.ndarray) -> PipelineResult:
        """
        Process a shelf image through 2-stage pipeline.

        Args:
            image: RGB image as numpy array (H, W, 3)

        Returns:
            PipelineResult with all detections and classifications
        """
        import time

        start_time = time.time()

        # Stage 1: Detection
        detections = self.detector.detect(image)
        logger.info(f"Stage 1: Detected {len(detections)} items")

        # Stage 2: Classification + Stage 3: OCR Refinement
        items = []
        low_confidence_items = []
        ocr_boosts = 0

        for det in detections:
            classification = None
            all_candidates = []

            if det.crop is not None and det.crop.size > 0:
                # Stage 2: Visual classification
                classification, all_candidates = self.classifier.classify(det.crop)

                # Stage 3: OCR refinement (if enabled and we have candidates)
                if classification and all_candidates and self.ocr.enabled:
                    refined = self.ocr.refine_classification(
                        det.crop,
                        classification,
                        all_candidates,
                        self.classifier.sku_mapping or {}
                    )
                    if refined.ocr_boosted:
                        ocr_boosts += 1
                    classification = refined

            item = ShelfItem(detection=det, classification=classification)
            items.append(item)

            # Check for active learning
            if self.active_learning and self.active_learning.should_queue(item):
                low_confidence_items.append(item)
                self.active_learning.add(item, image)

        if ocr_boosts > 0:
            logger.info(f"Stage 3: OCR refined {ocr_boosts} classifications")

        # Aggregate counts
        sku_counts = {}
        unknown_count = 0

        for item in items:
            if item.classification:
                if item.classification.is_unknown:
                    unknown_count += 1
                else:
                    sku_id = item.classification.sku_id
                    sku_counts[sku_id] = sku_counts.get(sku_id, 0) + 1

        processing_time = (time.time() - start_time) * 1000

        logger.info(f"Pipeline complete: {len(items)} items, {len(sku_counts)} unique SKUs, {processing_time:.1f}ms")

        return PipelineResult(
            items=items,
            sku_counts=sku_counts,
            total_items=len(items),
            unknown_count=unknown_count,
            processing_time_ms=processing_time,
            low_confidence_items=low_confidence_items,
        )

    def process_bytes(self, image_bytes: bytes) -> PipelineResult:
        """Process image from bytes."""
        import cv2

        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        return self.process(image)


# Convenience function for API integration
def create_pipeline(config_path: str = "ml/configs/pipeline.yaml") -> PipelineV2:
    """Create pipeline instance."""
    return PipelineV2.from_config(config_path)


if __name__ == "__main__":
    import argparse
    import cv2

    parser = argparse.ArgumentParser(description="Run 2-stage pipeline on image")
    parser.add_argument("image", type=str, help="Path to image")
    parser.add_argument("--config", type=str, default="ml/configs/pipeline.yaml")
    parser.add_argument("--output", type=str, help="Path to save annotated output")

    args = parser.parse_args()

    pipeline = PipelineV2.from_config(args.config)

    # Load image
    image = cv2.imread(args.image)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Process
    result = pipeline.process(image_rgb)

    # Print results
    print(f"\n{'='*60}")
    print(f"PIPELINE RESULTS")
    print(f"{'='*60}")
    print(f"Total items detected: {result.total_items}")
    print(f"Unknown items: {result.unknown_count}")
    print(f"Processing time: {result.processing_time_ms:.1f}ms")
    print(f"\nSKU Counts:")
    for sku, count in sorted(result.sku_counts.items()):
        print(f"  {sku}: {count}")

    # Annotate and save output
    if args.output:
        for item in result.items:
            x1, y1, x2, y2 = item.detection.bbox
            color = (0, 255, 0) if not (item.classification and item.classification.is_unknown) else (0, 0, 255)

            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

            if item.classification:
                label = f"{item.classification.sku_name[:20]} ({item.classification.confidence:.0%})"
                cv2.putText(image, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        cv2.imwrite(args.output, image)
        print(f"\nSaved annotated image to: {args.output}")
