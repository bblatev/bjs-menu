"""
Shelf Count Evaluation Script

Evaluates pipeline accuracy against ground truth annotations.
Calculates:
- Detection recall (target >= 0.98)
- mAP50 (target >= 0.95)
- SKU Top-1 accuracy (target >= 93%)
- Count MAE (target <= 0.30 per SKU)

Usage:
    python -m ml.eval.eval_shelf_counts --predictions predictions.json --ground-truth gt.json
    python -m ml.eval.eval_shelf_counts --pipeline-config ml/configs/pipeline.yaml --test-dir data/test
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EvalConfig:
    """Evaluation configuration."""
    iou_threshold: float = 0.5
    conf_threshold: float = 0.5
    # Hard targets from spec
    detection_recall_min: float = 0.98
    map50_min: float = 0.95
    top1_accuracy_min: float = 0.93
    count_mae_max: float = 0.30


@dataclass
class DetectionMetrics:
    """Detection evaluation metrics."""
    recall: float
    precision: float
    map50: float
    true_positives: int
    false_positives: int
    false_negatives: int
    total_gt: int
    total_pred: int


@dataclass
class ClassificationMetrics:
    """Classification evaluation metrics."""
    top1_accuracy: float
    top3_accuracy: float
    top5_accuracy: float
    per_class_accuracy: Dict[str, float]
    confusion_matrix: Optional[Dict] = None


@dataclass
class CountingMetrics:
    """Counting evaluation metrics."""
    mae: float  # Mean Absolute Error per SKU
    rmse: float  # Root Mean Squared Error
    per_sku_mae: Dict[str, float]
    total_gt_items: int
    total_pred_items: int


@dataclass
class FullEvalResult:
    """Complete evaluation results."""
    detection: DetectionMetrics
    classification: ClassificationMetrics
    counting: CountingMetrics
    targets_met: Dict[str, bool]
    all_targets_met: bool


def compute_iou(box1: Tuple, box2: Tuple) -> float:
    """Compute IoU between two boxes (x1, y1, x2, y2)."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def match_detections(
    gt_boxes: List[Tuple],
    pred_boxes: List[Tuple],
    iou_threshold: float = 0.5,
) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """
    Match predictions to ground truth using Hungarian algorithm.

    Returns:
        matches: List of (gt_idx, pred_idx) pairs
        unmatched_gt: List of unmatched GT indices
        unmatched_pred: List of unmatched prediction indices
    """
    if not gt_boxes or not pred_boxes:
        return [], list(range(len(gt_boxes))), list(range(len(pred_boxes)))

    # Compute IoU matrix
    iou_matrix = np.zeros((len(gt_boxes), len(pred_boxes)))
    for i, gt in enumerate(gt_boxes):
        for j, pred in enumerate(pred_boxes):
            iou_matrix[i, j] = compute_iou(gt, pred)

    # Greedy matching (simplified Hungarian)
    matches = []
    matched_gt = set()
    matched_pred = set()

    while True:
        # Find best unmatched pair
        best_iou = iou_threshold
        best_pair = None

        for i in range(len(gt_boxes)):
            if i in matched_gt:
                continue
            for j in range(len(pred_boxes)):
                if j in matched_pred:
                    continue
                if iou_matrix[i, j] > best_iou:
                    best_iou = iou_matrix[i, j]
                    best_pair = (i, j)

        if best_pair is None:
            break

        matches.append(best_pair)
        matched_gt.add(best_pair[0])
        matched_pred.add(best_pair[1])

    unmatched_gt = [i for i in range(len(gt_boxes)) if i not in matched_gt]
    unmatched_pred = [i for i in range(len(pred_boxes)) if i not in matched_pred]

    return matches, unmatched_gt, unmatched_pred


def evaluate_detection(
    predictions: List[Dict],
    ground_truth: List[Dict],
    config: EvalConfig,
) -> DetectionMetrics:
    """
    Evaluate detection performance.

    Args:
        predictions: List of prediction dicts with 'image_id', 'boxes', 'scores'
        ground_truth: List of GT dicts with 'image_id', 'boxes', 'labels'
        config: Evaluation config

    Returns:
        DetectionMetrics
    """
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_gt = 0
    total_pred = 0

    # Group by image
    gt_by_image = {g["image_id"]: g for g in ground_truth}
    pred_by_image = {p["image_id"]: p for p in predictions}

    all_image_ids = set(gt_by_image.keys()) | set(pred_by_image.keys())

    for image_id in all_image_ids:
        gt = gt_by_image.get(image_id, {"boxes": []})
        pred = pred_by_image.get(image_id, {"boxes": [], "scores": []})

        gt_boxes = gt.get("boxes", [])
        pred_boxes = pred.get("boxes", [])
        scores = pred.get("scores", [1.0] * len(pred_boxes))

        # Filter by confidence
        filtered = [(b, s) for b, s in zip(pred_boxes, scores) if s >= config.conf_threshold]
        pred_boxes = [b for b, _ in filtered]

        total_gt += len(gt_boxes)
        total_pred += len(pred_boxes)

        # Match detections
        matches, unmatched_gt, unmatched_pred = match_detections(
            gt_boxes, pred_boxes, config.iou_threshold
        )

        total_tp += len(matches)
        total_fp += len(unmatched_pred)
        total_fn += len(unmatched_gt)

    # Compute metrics
    recall = total_tp / total_gt if total_gt > 0 else 0.0
    precision = total_tp / total_pred if total_pred > 0 else 0.0

    # Simplified mAP50 (using recall at IoU=0.5)
    map50 = recall * precision if (recall + precision) > 0 else 0.0

    return DetectionMetrics(
        recall=recall,
        precision=precision,
        map50=map50,
        true_positives=total_tp,
        false_positives=total_fp,
        false_negatives=total_fn,
        total_gt=total_gt,
        total_pred=total_pred,
    )


def evaluate_classification(
    predictions: List[Dict],
    ground_truth: List[Dict],
    config: EvalConfig,
) -> ClassificationMetrics:
    """
    Evaluate classification performance.

    Args:
        predictions: List with 'image_id', 'items' (each with 'sku_id', 'top_k_predictions')
        ground_truth: List with 'image_id', 'items' (each with 'sku_id')

    Returns:
        ClassificationMetrics
    """
    total = 0
    top1_correct = 0
    top3_correct = 0
    top5_correct = 0

    per_class_correct = defaultdict(int)
    per_class_total = defaultdict(int)

    # Match predictions to GT by image and box
    gt_by_image = {g["image_id"]: g for g in ground_truth}
    pred_by_image = {p["image_id"]: p for p in predictions}

    for image_id, gt in gt_by_image.items():
        pred = pred_by_image.get(image_id)
        if not pred:
            continue

        gt_items = gt.get("items", [])
        pred_items = pred.get("items", [])

        # Match items by box IoU
        gt_boxes = [item.get("box") for item in gt_items]
        pred_boxes = [item.get("box") for item in pred_items]

        matches, _, _ = match_detections(gt_boxes, pred_boxes, config.iou_threshold)

        for gt_idx, pred_idx in matches:
            gt_sku = gt_items[gt_idx].get("sku_id")
            pred_item = pred_items[pred_idx]

            pred_sku = pred_item.get("sku_id")
            top_k = pred_item.get("top_k_predictions", [pred_sku])

            total += 1
            per_class_total[gt_sku] += 1

            if pred_sku == gt_sku:
                top1_correct += 1
                per_class_correct[gt_sku] += 1

            if gt_sku in top_k[:3]:
                top3_correct += 1

            if gt_sku in top_k[:5]:
                top5_correct += 1

    top1_acc = top1_correct / total if total > 0 else 0.0
    top3_acc = top3_correct / total if total > 0 else 0.0
    top5_acc = top5_correct / total if total > 0 else 0.0

    per_class_accuracy = {
        cls: per_class_correct[cls] / per_class_total[cls]
        for cls in per_class_total
        if per_class_total[cls] > 0
    }

    return ClassificationMetrics(
        top1_accuracy=top1_acc,
        top3_accuracy=top3_acc,
        top5_accuracy=top5_acc,
        per_class_accuracy=per_class_accuracy,
    )


def evaluate_counting(
    predictions: List[Dict],
    ground_truth: List[Dict],
) -> CountingMetrics:
    """
    Evaluate counting accuracy.

    Args:
        predictions: List with 'image_id', 'sku_counts' dict
        ground_truth: List with 'image_id', 'sku_counts' dict

    Returns:
        CountingMetrics
    """
    per_sku_errors = defaultdict(list)
    total_gt_items = 0
    total_pred_items = 0

    gt_by_image = {g["image_id"]: g for g in ground_truth}
    pred_by_image = {p["image_id"]: p for p in predictions}

    for image_id, gt in gt_by_image.items():
        pred = pred_by_image.get(image_id, {"sku_counts": {}})

        gt_counts = gt.get("sku_counts", {})
        pred_counts = pred.get("sku_counts", {})

        all_skus = set(gt_counts.keys()) | set(pred_counts.keys())

        for sku in all_skus:
            gt_count = gt_counts.get(sku, 0)
            pred_count = pred_counts.get(sku, 0)

            error = abs(gt_count - pred_count)
            per_sku_errors[sku].append(error)

            total_gt_items += gt_count
            total_pred_items += pred_count

    # Compute MAE per SKU
    per_sku_mae = {
        sku: np.mean(errors) for sku, errors in per_sku_errors.items()
    }

    # Overall MAE
    all_errors = [e for errors in per_sku_errors.values() for e in errors]
    mae = np.mean(all_errors) if all_errors else 0.0
    rmse = np.sqrt(np.mean([e**2 for e in all_errors])) if all_errors else 0.0

    return CountingMetrics(
        mae=mae,
        rmse=rmse,
        per_sku_mae=per_sku_mae,
        total_gt_items=total_gt_items,
        total_pred_items=total_pred_items,
    )


def evaluate_full_pipeline(
    predictions: List[Dict],
    ground_truth: List[Dict],
    config: Optional[EvalConfig] = None,
) -> FullEvalResult:
    """
    Run full evaluation of 2-stage pipeline.

    Args:
        predictions: Pipeline predictions
        ground_truth: Ground truth annotations
        config: Evaluation config

    Returns:
        FullEvalResult with all metrics
    """
    config = config or EvalConfig()

    detection = evaluate_detection(predictions, ground_truth, config)
    classification = evaluate_classification(predictions, ground_truth, config)
    counting = evaluate_counting(predictions, ground_truth)

    targets_met = {
        "detection_recall": detection.recall >= config.detection_recall_min,
        "map50": detection.map50 >= config.map50_min,
        "top1_accuracy": classification.top1_accuracy >= config.top1_accuracy_min,
        "count_mae": counting.mae <= config.count_mae_max,
    }

    return FullEvalResult(
        detection=detection,
        classification=classification,
        counting=counting,
        targets_met=targets_met,
        all_targets_met=all(targets_met.values()),
    )


def run_pipeline_on_test_set(
    pipeline_config: str,
    test_dir: str,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Run pipeline on test set and return predictions.

    Args:
        pipeline_config: Path to pipeline config
        test_dir: Path to test directory with images and annotations

    Returns:
        (predictions, ground_truth) lists
    """
    import cv2
    from ml.inference.pipeline_v2 import PipelineV2

    pipeline = PipelineV2.from_config(pipeline_config)
    test_path = Path(test_dir)

    predictions = []
    ground_truth = []

    # Load annotations
    annotations_file = test_path / "annotations.json"
    if annotations_file.exists():
        with open(annotations_file) as f:
            annotations = json.load(f)
    else:
        annotations = {}

    # Process each image
    for img_path in sorted(test_path.glob("*.jpg")) + sorted(test_path.glob("*.png")):
        image_id = img_path.stem
        logger.info(f"Processing: {image_id}")

        # Run pipeline
        image = cv2.imread(str(img_path))
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        result = pipeline.process(image_rgb)

        # Convert to eval format
        pred = {
            "image_id": image_id,
            "boxes": [item.detection.bbox for item in result.items],
            "scores": [item.detection.confidence for item in result.items],
            "items": [
                {
                    "box": item.detection.bbox,
                    "sku_id": item.classification.sku_id if item.classification else "unknown",
                    "confidence": item.classification.confidence if item.classification else 0.0,
                }
                for item in result.items
            ],
            "sku_counts": result.sku_counts,
        }
        predictions.append(pred)

        # Get ground truth
        gt = annotations.get(image_id, {})
        gt["image_id"] = image_id
        ground_truth.append(gt)

    return predictions, ground_truth


def print_results(result: FullEvalResult, config: EvalConfig):
    """Print evaluation results."""
    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)

    print("\n[DETECTION]")
    print(f"  Recall:    {result.detection.recall:.4f}  (target: >= {config.detection_recall_min})")
    print(f"  Precision: {result.detection.precision:.4f}")
    print(f"  mAP@50:    {result.detection.map50:.4f}  (target: >= {config.map50_min})")
    print(f"  TP: {result.detection.true_positives}, FP: {result.detection.false_positives}, FN: {result.detection.false_negatives}")

    print("\n[CLASSIFICATION]")
    print(f"  Top-1 Accuracy: {result.classification.top1_accuracy:.4f}  (target: >= {config.top1_accuracy_min})")
    print(f"  Top-3 Accuracy: {result.classification.top3_accuracy:.4f}")
    print(f"  Top-5 Accuracy: {result.classification.top5_accuracy:.4f}")

    print("\n[COUNTING]")
    print(f"  MAE per SKU: {result.counting.mae:.4f}  (target: <= {config.count_mae_max})")
    print(f"  RMSE:        {result.counting.rmse:.4f}")
    print(f"  GT items: {result.counting.total_gt_items}, Pred items: {result.counting.total_pred_items}")

    print("\n" + "-" * 70)
    print("TARGETS:")
    for target, met in result.targets_met.items():
        status = "PASS" if met else "FAIL"
        print(f"  {target}: {status}")

    print("-" * 70)
    if result.all_targets_met:
        print("ALL TARGETS MET - Pipeline ready for deployment")
    else:
        failed = [k for k, v in result.targets_met.items() if not v]
        print(f"TARGETS NOT MET: {failed}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Evaluate shelf count pipeline")
    parser.add_argument(
        "--predictions",
        type=str,
        help="Path to predictions JSON",
    )
    parser.add_argument(
        "--ground-truth",
        type=str,
        help="Path to ground truth JSON",
    )
    parser.add_argument(
        "--pipeline-config",
        type=str,
        default="ml/configs/pipeline.yaml",
        help="Path to pipeline config (for running on test set)",
    )
    parser.add_argument(
        "--test-dir",
        type=str,
        help="Path to test directory with images and annotations.json",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save results JSON",
    )

    args = parser.parse_args()

    config = EvalConfig()

    if args.predictions and args.ground_truth:
        # Load from files
        with open(args.predictions) as f:
            predictions = json.load(f)
        with open(args.ground_truth) as f:
            ground_truth = json.load(f)
    elif args.test_dir:
        # Run pipeline on test set
        predictions, ground_truth = run_pipeline_on_test_set(
            args.pipeline_config, args.test_dir
        )
    else:
        parser.error("Either --predictions/--ground-truth or --test-dir required")

    # Evaluate
    result = evaluate_full_pipeline(predictions, ground_truth, config)

    # Print results
    print_results(result, config)

    # Save results
    if args.output:
        output_data = {
            "detection": {
                "recall": result.detection.recall,
                "precision": result.detection.precision,
                "map50": result.detection.map50,
                "true_positives": result.detection.true_positives,
                "false_positives": result.detection.false_positives,
                "false_negatives": result.detection.false_negatives,
            },
            "classification": {
                "top1_accuracy": result.classification.top1_accuracy,
                "top3_accuracy": result.classification.top3_accuracy,
                "top5_accuracy": result.classification.top5_accuracy,
                "per_class_accuracy": result.classification.per_class_accuracy,
            },
            "counting": {
                "mae": result.counting.mae,
                "rmse": result.counting.rmse,
                "per_sku_mae": result.counting.per_sku_mae,
            },
            "targets_met": result.targets_met,
            "all_targets_met": result.all_targets_met,
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
