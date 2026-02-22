"""
YOLOv8 Bottle Detector Training Script
Stage 1 of 2-stage ML pipeline

Target metrics:
- Recall >= 0.98
- mAP50 >= 0.95

Usage:
    python -m ml.training.train_detector --config ml/configs/detector.yaml
    python -m ml.training.train_detector --resume runs/detect/train/weights/last.pt
"""

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DetectorTrainer:
    """YOLOv8 bottle detector trainer with validation against hard targets."""

    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.run_dir = None
        self.model = None

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from {config_path}")
        return config

    def _check_ultralytics(self):
        """Check if ultralytics is installed."""
        try:
            from ultralytics import YOLO
            return True
        except ImportError:
            logger.error(
                "ultralytics not installed. Install with: pip install ultralytics"
            )
            return False

    def _prepare_data_yaml(self) -> str:
        """Create data.yaml for YOLO training."""
        data_config = self.config["data"]

        data_yaml = {
            "path": str(Path(data_config["train_path"]).parent),
            "train": "train/images",
            "val": "val/images",
            "test": "test/images" if data_config.get("test_path") else None,
            "names": {i: name for i, name in enumerate(data_config["classes"])},
            "nc": len(data_config["classes"]),
        }

        # Remove None values
        data_yaml = {k: v for k, v in data_yaml.items() if v is not None}

        # Write to temp file
        yaml_path = Path("ml/data/detector_data.yaml")
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        with open(yaml_path, "w") as f:
            yaml.dump(data_yaml, f, default_flow_style=False)

        logger.info(f"Created data.yaml at {yaml_path}")
        return str(yaml_path)

    def train(self, resume: Optional[str] = None) -> Dict:
        """
        Train the detector model.

        Args:
            resume: Path to checkpoint to resume from

        Returns:
            Dict with training results and metrics
        """
        if not self._check_ultralytics():
            raise ImportError("ultralytics package required")

        from ultralytics import YOLO

        model_cfg = self.config["model"]
        train_cfg = self.config["training"]
        aug_cfg = train_cfg.get("augment", {})

        # Initialize model
        if resume:
            logger.info(f"Resuming from checkpoint: {resume}")
            self.model = YOLO(resume)
        else:
            logger.info(f"Loading pretrained model: {model_cfg['pretrained']}")
            self.model = YOLO(model_cfg["pretrained"])

        # Prepare data config
        data_yaml = self._prepare_data_yaml()

        # Create run directory
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(f"runs/detector/{timestamp}")
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Save config for reproducibility
        with open(self.run_dir / "config.yaml", "w") as f:
            yaml.dump(self.config, f)

        logger.info(f"Starting training. Run directory: {self.run_dir}")

        # Train
        results = self.model.train(
            data=data_yaml,
            epochs=train_cfg["epochs"],
            patience=train_cfg["patience"],
            batch=self.config["data"]["batch_size"],
            imgsz=self.config["data"]["image_size"],
            optimizer=train_cfg["optimizer"],
            lr0=train_cfg["lr0"],
            lrf=train_cfg["lrf"],
            momentum=train_cfg["momentum"],
            weight_decay=train_cfg["weight_decay"],
            warmup_epochs=train_cfg["warmup_epochs"],
            # Augmentation
            hsv_h=aug_cfg.get("hsv_h", 0.015),
            hsv_s=aug_cfg.get("hsv_s", 0.7),
            hsv_v=aug_cfg.get("hsv_v", 0.4),
            degrees=aug_cfg.get("degrees", 0.0),
            translate=aug_cfg.get("translate", 0.1),
            scale=aug_cfg.get("scale", 0.5),
            shear=aug_cfg.get("shear", 0.0),
            perspective=aug_cfg.get("perspective", 0.0),
            flipud=aug_cfg.get("flipud", 0.0),
            fliplr=aug_cfg.get("fliplr", 0.5),
            mosaic=aug_cfg.get("mosaic", 1.0),
            mixup=aug_cfg.get("mixup", 0.0),
            copy_paste=aug_cfg.get("copy_paste", 0.0),
            # Output
            project=str(self.run_dir.parent),
            name=self.run_dir.name,
            exist_ok=True,
            verbose=True,
        )

        return self._process_results(results)

    def _process_results(self, results) -> Dict:
        """Process training results and check against targets."""
        targets = self.config.get("targets", {})

        # Extract metrics from results
        metrics = {
            "mAP50": float(results.results_dict.get("metrics/mAP50(B)", 0)),
            "mAP50-95": float(results.results_dict.get("metrics/mAP50-95(B)", 0)),
            "precision": float(results.results_dict.get("metrics/precision(B)", 0)),
            "recall": float(results.results_dict.get("metrics/recall(B)", 0)),
        }

        # Check against hard targets
        target_met = {
            "recall": metrics["recall"] >= targets.get("recall_min", 0.98),
            "mAP50": metrics["mAP50"] >= targets.get("map50_min", 0.95),
        }

        all_targets_met = all(target_met.values())

        result = {
            "metrics": metrics,
            "targets": targets,
            "target_met": target_met,
            "all_targets_met": all_targets_met,
            "run_dir": str(self.run_dir),
            "best_weights": str(self.run_dir / "weights" / "best.pt"),
        }

        # Log results
        logger.info("=" * 60)
        logger.info("TRAINING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Recall:  {metrics['recall']:.4f} (target: {targets.get('recall_min', 0.98)})")
        logger.info(f"mAP50:   {metrics['mAP50']:.4f} (target: {targets.get('map50_min', 0.95)})")
        logger.info(f"mAP50-95: {metrics['mAP50-95']:.4f}")
        logger.info(f"Precision: {metrics['precision']:.4f}")
        logger.info("-" * 60)

        if all_targets_met:
            logger.info("ALL TARGETS MET - Model ready for deployment")
        else:
            failed = [k for k, v in target_met.items() if not v]
            logger.warning(f"TARGETS NOT MET: {failed}")
            logger.warning("Model needs more training or data")

        # Save results
        with open(self.run_dir / "final_results.json", "w") as f:
            json.dump(result, f, indent=2)

        return result

    def validate(self, weights_path: str, data_path: Optional[str] = None) -> Dict:
        """
        Validate model on test set.

        Args:
            weights_path: Path to model weights
            data_path: Optional path to validation data

        Returns:
            Validation metrics
        """
        if not self._check_ultralytics():
            raise ImportError("ultralytics package required")

        from ultralytics import YOLO

        logger.info(f"Validating model: {weights_path}")

        model = YOLO(weights_path)
        val_cfg = self.config.get("validation", {})

        data_yaml = data_path or self._prepare_data_yaml()

        results = model.val(
            data=data_yaml,
            conf=val_cfg.get("conf_threshold", 0.25),
            iou=val_cfg.get("iou_threshold", 0.45),
            max_det=val_cfg.get("max_det", 300),
            verbose=True,
        )

        metrics = {
            "mAP50": float(results.results_dict.get("metrics/mAP50(B)", 0)),
            "mAP50-95": float(results.results_dict.get("metrics/mAP50-95(B)", 0)),
            "precision": float(results.results_dict.get("metrics/precision(B)", 0)),
            "recall": float(results.results_dict.get("metrics/recall(B)", 0)),
        }

        logger.info(f"Validation metrics: {metrics}")
        return metrics

    def export(self, weights_path: str, output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Export model to multiple formats.

        Args:
            weights_path: Path to model weights
            output_dir: Directory to save exported models

        Returns:
            Dict mapping format to output path
        """
        if not self._check_ultralytics():
            raise ImportError("ultralytics package required")

        from ultralytics import YOLO

        logger.info(f"Exporting model: {weights_path}")

        model = YOLO(weights_path)
        export_cfg = self.config.get("export", {})
        formats = export_cfg.get("formats", ["onnx"])

        output_dir = Path(output_dir or self.run_dir or "models/detector")
        output_dir.mkdir(parents=True, exist_ok=True)

        exported = {}

        for fmt in formats:
            logger.info(f"Exporting to {fmt}...")
            try:
                result = model.export(
                    format=fmt,
                    opset=export_cfg.get("opset", 12),
                    simplify=export_cfg.get("simplify", True),
                    dynamic=export_cfg.get("dynamic", False),
                    int8=export_cfg.get("int8", False),
                )
                exported[fmt] = str(result)
                logger.info(f"Exported {fmt}: {result}")
            except Exception as e:
                logger.error(f"Failed to export {fmt}: {e}")

        return exported


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8 bottle detector")
    parser.add_argument(
        "--config",
        type=str,
        default="ml/configs/detector.yaml",
        help="Path to config file",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to checkpoint to resume from",
    )
    parser.add_argument(
        "--validate",
        type=str,
        default=None,
        help="Path to weights to validate (skip training)",
    )
    parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Path to weights to export (skip training)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for exported models",
    )

    args = parser.parse_args()

    trainer = DetectorTrainer(args.config)

    if args.validate:
        # Validation only
        metrics = trainer.validate(args.validate)
        print(json.dumps(metrics, indent=2))

    elif args.export:
        # Export only
        exported = trainer.export(args.export, args.output_dir)
        print(json.dumps(exported, indent=2))

    else:
        # Full training
        results = trainer.train(resume=args.resume)

        if results["all_targets_met"]:
            # Auto-export if targets met
            logger.info("Auto-exporting best model...")
            trainer.export(
                results["best_weights"],
                args.output_dir or "models/detector"
            )


if __name__ == "__main__":
    main()
