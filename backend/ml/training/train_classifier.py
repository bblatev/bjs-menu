"""
SKU Classifier Training Script with ArcFace Metric Learning
Stage 2 of 2-stage ML pipeline

Target metrics:
- Top-1 Accuracy >= 93% for Top 100 SKUs

Usage:
    python -m ml.training.train_classifier --config ml/configs/classifier.yaml
    python -m ml.training.train_classifier --resume checkpoints/classifier/last.pt
"""

import argparse
import json
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ArcFaceHead:
    """ArcFace head for metric learning."""

    def __init__(
        self,
        embedding_dim: int,
        num_classes: int,
        margin: float = 0.5,
        scale: float = 64.0,
    ):
        self.embedding_dim = embedding_dim
        self.num_classes = num_classes
        self.margin = margin
        self.scale = scale
        self.weight = None  # Initialized in PyTorch version

    def forward_pytorch(self, embeddings, labels):
        """PyTorch forward pass."""
        import torch
        import torch.nn.functional as F

        # Normalize embeddings and weights
        embeddings = F.normalize(embeddings, dim=1)
        weight = F.normalize(self.weight, dim=1)

        # Cosine similarity
        cosine = F.linear(embeddings, weight)

        # Convert margin to radians
        theta = torch.acos(torch.clamp(cosine, -1.0 + 1e-7, 1.0 - 1e-7))

        # Add margin to target class
        target_logits = torch.cos(theta + self.margin)

        # One-hot encode labels
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1)

        # Apply margin only to target class
        output = cosine * (1 - one_hot) + target_logits * one_hot
        output *= self.scale

        return output


class HardNegativeMiner:
    """Hard negative mining for improved similar SKU separation."""

    def __init__(self, embeddings: np.ndarray, labels: np.ndarray, k: int = 3):
        self.embeddings = embeddings
        self.labels = labels
        self.k = k
        self._build_index()

    def _build_index(self):
        """Build FAISS index for fast similarity search."""
        try:
            import faiss

            dim = self.embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dim)  # Inner product = cosine for normalized
            normalized = self.embeddings / np.linalg.norm(
                self.embeddings, axis=1, keepdims=True
            )
            self.index.add(normalized.astype(np.float32))
            self.use_faiss = True
        except ImportError:
            logger.warning("FAISS not available, using numpy for similarity search")
            self.use_faiss = False

    def get_hard_negatives(self, query_idx: int) -> List[int]:
        """Get indices of hard negatives for a query sample."""
        query_label = self.labels[query_idx]
        query_embedding = self.embeddings[query_idx]

        if self.use_faiss:
            import faiss

            query_norm = query_embedding / np.linalg.norm(query_embedding)
            D, I = self.index.search(
                query_norm.reshape(1, -1).astype(np.float32),
                self.k * 10  # Get more candidates
            )
            candidates = I[0]
        else:
            # Numpy fallback
            query_norm = query_embedding / np.linalg.norm(query_embedding)
            embeddings_norm = self.embeddings / np.linalg.norm(
                self.embeddings, axis=1, keepdims=True
            )
            similarities = embeddings_norm @ query_norm
            candidates = np.argsort(similarities)[::-1][:self.k * 10]

        # Filter to different class (hard negatives)
        hard_negatives = []
        for idx in candidates:
            if self.labels[idx] != query_label:
                hard_negatives.append(int(idx))
                if len(hard_negatives) >= self.k:
                    break

        return hard_negatives


class ClassifierTrainer:
    """EfficientNet + ArcFace classifier trainer."""

    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.run_dir = None
        self.model = None
        self.device = None

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from {config_path}")
        return config

    def _check_dependencies(self) -> bool:
        """Check required dependencies."""
        missing = []

        try:
            import torch
        except ImportError:
            missing.append("torch")

        try:
            import torchvision
        except ImportError:
            missing.append("torchvision")

        try:
            import timm
        except ImportError:
            missing.append("timm")

        if missing:
            logger.error(f"Missing dependencies: {missing}")
            logger.error("Install with: pip install torch torchvision timm")
            return False

        return True

    def _setup_device(self):
        """Setup compute device."""
        import torch

        if torch.cuda.is_available():
            self.device = torch.device("cuda")
            logger.info(f"Using CUDA: {torch.cuda.get_device_name()}")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
            logger.info("Using Apple MPS")
        else:
            self.device = torch.device("cpu")
            logger.info("Using CPU")

    def _build_model(self, num_classes: int):
        """Build EfficientNet backbone with ArcFace head."""
        import torch
        import torch.nn as nn
        import timm

        model_cfg = self.config["model"]
        backbone_name = model_cfg.get("backbone", "efficientnet_b2")
        embedding_dim = model_cfg.get("embedding_dim", 512)

        logger.info(f"Building model: {backbone_name} with {embedding_dim}D embeddings")

        # Create backbone
        backbone = timm.create_model(
            backbone_name,
            pretrained=True,
            num_classes=0,  # Remove classifier
        )

        # Get backbone output dim
        with torch.no_grad():
            dummy = torch.randn(1, 3, 224, 224)
            backbone_dim = backbone(dummy).shape[1]

        # Build full model
        class SKUClassifier(nn.Module):
            def __init__(self, backbone, backbone_dim, embedding_dim, num_classes, arcface_cfg):
                super().__init__()
                self.backbone = backbone
                self.embedding = nn.Sequential(
                    nn.Linear(backbone_dim, embedding_dim),
                    nn.BatchNorm1d(embedding_dim),
                )
                # ArcFace head
                self.arcface_weight = nn.Parameter(
                    torch.FloatTensor(num_classes, embedding_dim)
                )
                nn.init.xavier_uniform_(self.arcface_weight)

                self.margin = arcface_cfg.get("margin", 0.5)
                self.scale = arcface_cfg.get("scale", 64.0)

            def forward(self, x, labels=None):
                features = self.backbone(x)
                embeddings = self.embedding(features)
                embeddings = nn.functional.normalize(embeddings, dim=1)

                if labels is not None:
                    # Training mode with ArcFace loss
                    return self._arcface_forward(embeddings, labels)
                else:
                    # Inference mode - return embeddings
                    return embeddings

            def _arcface_forward(self, embeddings, labels):
                import torch.nn.functional as F

                weight = F.normalize(self.arcface_weight, dim=1)
                cosine = F.linear(embeddings, weight)

                theta = torch.acos(torch.clamp(cosine, -1.0 + 1e-7, 1.0 - 1e-7))
                target_logits = torch.cos(theta + self.margin)

                one_hot = torch.zeros_like(cosine)
                one_hot.scatter_(1, labels.view(-1, 1), 1)

                output = cosine * (1 - one_hot) + target_logits * one_hot
                output *= self.scale

                return output, embeddings

        arcface_cfg = model_cfg.get("metric_head", {})
        model = SKUClassifier(
            backbone, backbone_dim, embedding_dim, num_classes, arcface_cfg
        )

        return model.to(self.device)

    def _build_dataloaders(self) -> Tuple:
        """Build train/val dataloaders."""
        import torch
        from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
        from torchvision import transforms
        from PIL import Image

        data_cfg = self.config["data"]
        aug_cfg = self.config["training"].get("augment", {})

        # Training transforms
        train_transforms = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.RandomCrop(data_cfg.get("image_size", 224)),
            transforms.RandomHorizontalFlip() if aug_cfg.get("horizontal_flip", True) else transforms.Lambda(lambda x: x),
            transforms.ColorJitter(
                brightness=aug_cfg.get("color_jitter", {}).get("brightness", 0.3),
                contrast=aug_cfg.get("color_jitter", {}).get("contrast", 0.3),
                saturation=aug_cfg.get("color_jitter", {}).get("saturation", 0.3),
                hue=aug_cfg.get("color_jitter", {}).get("hue", 0.1),
            ),
            transforms.RandomRotation(aug_cfg.get("random_rotation", 15)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        # Validation transforms
        val_transforms = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(data_cfg.get("image_size", 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        # Custom dataset
        class SKUDataset(Dataset):
            def __init__(self, root_dir, transform=None):
                self.root_dir = Path(root_dir)
                self.transform = transform
                self.samples = []
                self.class_to_idx = {}

                # Scan directory structure: root/class_name/image.jpg
                for class_idx, class_dir in enumerate(sorted(self.root_dir.iterdir())):
                    if class_dir.is_dir():
                        class_name = class_dir.name
                        self.class_to_idx[class_name] = class_idx
                        for img_path in class_dir.glob("*.jpg"):
                            self.samples.append((str(img_path), class_idx))
                        for img_path in class_dir.glob("*.png"):
                            self.samples.append((str(img_path), class_idx))

                self.idx_to_class = {v: k for k, v in self.class_to_idx.items()}

            def __len__(self):
                return len(self.samples)

            def __getitem__(self, idx):
                img_path, label = self.samples[idx]
                image = Image.open(img_path).convert("RGB")
                if self.transform:
                    image = self.transform(image)
                return image, label

        train_dataset = SKUDataset(data_cfg["train_path"], train_transforms)
        val_dataset = SKUDataset(data_cfg["val_path"], val_transforms)

        logger.info(f"Train samples: {len(train_dataset)}")
        logger.info(f"Val samples: {len(val_dataset)}")
        logger.info(f"Number of classes: {len(train_dataset.class_to_idx)}")

        # Balanced sampling
        if data_cfg.get("sampler") == "balanced":
            labels = [s[1] for s in train_dataset.samples]
            class_counts = np.bincount(labels)
            weights = 1.0 / class_counts[labels]
            sampler = WeightedRandomSampler(weights, len(weights))
            shuffle = False
        else:
            sampler = None
            shuffle = True

        train_loader = DataLoader(
            train_dataset,
            batch_size=data_cfg.get("batch_size", 32),
            shuffle=shuffle,
            sampler=sampler,
            num_workers=data_cfg.get("num_workers", 4),
            pin_memory=True,
        )

        val_loader = DataLoader(
            val_dataset,
            batch_size=data_cfg.get("batch_size", 32),
            shuffle=False,
            num_workers=data_cfg.get("num_workers", 4),
            pin_memory=True,
        )

        return train_loader, val_loader, train_dataset.class_to_idx

    def train(self, resume: Optional[str] = None) -> Dict:
        """
        Train the classifier model.

        Args:
            resume: Path to checkpoint to resume from

        Returns:
            Dict with training results and metrics
        """
        if not self._check_dependencies():
            raise ImportError("Missing required dependencies")

        import torch
        import torch.nn as nn
        from torch.cuda.amp import GradScaler, autocast

        self._setup_device()

        # Build dataloaders
        train_loader, val_loader, class_to_idx = self._build_dataloaders()
        num_classes = len(class_to_idx)

        # Build model
        self.model = self._build_model(num_classes)

        train_cfg = self.config["training"]

        # Optimizer
        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=train_cfg.get("lr", 0.0003),
            weight_decay=train_cfg.get("weight_decay", 0.01),
        )

        # Scheduler
        total_steps = len(train_loader) * train_cfg["epochs"]
        warmup_steps = len(train_loader) * train_cfg.get("warmup_epochs", 5)

        def lr_lambda(step):
            if step < warmup_steps:
                return step / warmup_steps
            else:
                progress = (step - warmup_steps) / (total_steps - warmup_steps)
                return 0.5 * (1 + math.cos(math.pi * progress))

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

        # Loss with label smoothing
        criterion = nn.CrossEntropyLoss(
            label_smoothing=train_cfg.get("label_smoothing", 0.1)
        )

        # Mixed precision
        scaler = GradScaler() if train_cfg.get("amp", True) else None

        # Create run directory
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(f"runs/classifier/{timestamp}")
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Save config and class mapping
        with open(self.run_dir / "config.yaml", "w") as f:
            yaml.dump(self.config, f)
        with open(self.run_dir / "class_to_idx.json", "w") as f:
            json.dump(class_to_idx, f)

        # Resume if specified
        start_epoch = 0
        if resume:
            checkpoint = torch.load(resume, map_location=self.device)
            self.model.load_state_dict(checkpoint["model_state_dict"])
            optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
            start_epoch = checkpoint["epoch"] + 1
            logger.info(f"Resumed from epoch {start_epoch}")

        # Training loop
        best_acc = 0.0
        patience_counter = 0
        patience = train_cfg.get("patience", 30)

        logger.info(f"Starting training. Run directory: {self.run_dir}")

        for epoch in range(start_epoch, train_cfg["epochs"]):
            # Train epoch
            self.model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0

            for batch_idx, (images, labels) in enumerate(train_loader):
                images = images.to(self.device)
                labels = labels.to(self.device)

                optimizer.zero_grad()

                if scaler:
                    with autocast():
                        logits, _ = self.model(images, labels)
                        loss = criterion(logits, labels)

                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    logits, _ = self.model(images, labels)
                    loss = criterion(logits, labels)
                    loss.backward()
                    optimizer.step()

                scheduler.step()

                train_loss += loss.item()
                _, predicted = logits.max(1)
                train_total += labels.size(0)
                train_correct += predicted.eq(labels).sum().item()

                if batch_idx % 50 == 0:
                    logger.info(
                        f"Epoch {epoch} [{batch_idx}/{len(train_loader)}] "
                        f"Loss: {loss.item():.4f} Acc: {100.*train_correct/train_total:.2f}%"
                    )

            train_acc = train_correct / train_total

            # Validation
            val_metrics = self._validate(val_loader)

            logger.info(
                f"Epoch {epoch} - Train Loss: {train_loss/len(train_loader):.4f} "
                f"Train Acc: {100.*train_acc:.2f}% "
                f"Val Top-1: {100.*val_metrics['top1']:.2f}% "
                f"Val Top-3: {100.*val_metrics['top3']:.2f}%"
            )

            # Save checkpoint
            checkpoint = {
                "epoch": epoch,
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_acc": val_metrics["top1"],
            }
            torch.save(checkpoint, self.run_dir / "last.pt")

            # Best model
            if val_metrics["top1"] > best_acc:
                best_acc = val_metrics["top1"]
                torch.save(checkpoint, self.run_dir / "best.pt")
                patience_counter = 0
                logger.info(f"New best model: {100.*best_acc:.2f}%")
            else:
                patience_counter += 1

            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch}")
                break

        return self._finalize_training(best_acc, class_to_idx)

    def _validate(self, val_loader) -> Dict:
        """Run validation and return metrics."""
        import torch

        self.model.eval()
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(self.device)
                embeddings = self.model(images)  # Inference mode returns embeddings

                # For validation, compute cosine similarity with class weights
                weight = torch.nn.functional.normalize(self.model.arcface_weight, dim=1)
                logits = torch.nn.functional.linear(embeddings, weight)

                all_preds.append(logits.cpu())
                all_labels.append(labels)

        all_preds = torch.cat(all_preds)
        all_labels = torch.cat(all_labels)

        # Top-k accuracy
        top_k = self.config["validation"].get("top_k", [1, 3, 5])
        metrics = {}

        for k in top_k:
            _, topk_preds = all_preds.topk(k, dim=1)
            correct = topk_preds.eq(all_labels.view(-1, 1).expand_as(topk_preds))
            metrics[f"top{k}"] = correct.any(dim=1).float().mean().item()

        return metrics

    def _finalize_training(self, best_acc: float, class_to_idx: Dict) -> Dict:
        """Finalize training and check against targets."""
        targets = self.config.get("targets", {})

        target_met = {
            "top1_accuracy": best_acc >= targets.get("top1_accuracy_min", 0.93),
        }

        result = {
            "best_top1_accuracy": best_acc,
            "targets": targets,
            "target_met": target_met,
            "all_targets_met": all(target_met.values()),
            "run_dir": str(self.run_dir),
            "best_weights": str(self.run_dir / "best.pt"),
            "num_classes": len(class_to_idx),
        }

        logger.info("=" * 60)
        logger.info("TRAINING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Top-1 Accuracy: {100.*best_acc:.2f}% (target: {100.*targets.get('top1_accuracy_min', 0.93):.0f}%)")

        if result["all_targets_met"]:
            logger.info("ALL TARGETS MET - Model ready for deployment")
        else:
            logger.warning("TARGETS NOT MET - Model needs improvement")

        with open(self.run_dir / "final_results.json", "w") as f:
            json.dump(result, f, indent=2)

        return result

    def export_embeddings(self, weights_path: str, data_path: str, output_dir: str) -> str:
        """Export embeddings for all SKUs in dataset."""
        import torch
        from torchvision import transforms
        from PIL import Image

        if not self._check_dependencies():
            raise ImportError("Missing dependencies")

        self._setup_device()

        # Load model
        checkpoint = torch.load(weights_path, map_location=self.device)
        num_classes = checkpoint["model_state_dict"]["arcface_weight"].shape[0]
        self.model = self._build_model(num_classes)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

        # Transforms
        transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        # Process each class
        data_path = Path(data_path)
        embeddings_dict = {}

        for class_dir in sorted(data_path.iterdir()):
            if not class_dir.is_dir():
                continue

            class_name = class_dir.name
            class_embeddings = []

            for img_path in list(class_dir.glob("*.jpg")) + list(class_dir.glob("*.png")):
                image = Image.open(img_path).convert("RGB")
                image = transform(image).unsqueeze(0).to(self.device)

                with torch.no_grad():
                    embedding = self.model(image).cpu().numpy()
                    class_embeddings.append(embedding[0])

            if class_embeddings:
                # Average embedding for this class
                embeddings_dict[class_name] = np.mean(class_embeddings, axis=0)
                logger.info(f"Processed {class_name}: {len(class_embeddings)} images")

        # Save embeddings
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        np.save(output_dir / "embeddings.npy", embeddings_dict)
        with open(output_dir / "sku_mapping.json", "w") as f:
            json.dump(list(embeddings_dict.keys()), f)

        logger.info(f"Saved embeddings for {len(embeddings_dict)} SKUs to {output_dir}")
        return str(output_dir / "embeddings.npy")

    def export_onnx(self, weights_path: str, output_path: str):
        """Export model to ONNX format."""
        import torch

        if not self._check_dependencies():
            raise ImportError("Missing dependencies")

        self._setup_device()

        # Load model
        checkpoint = torch.load(weights_path, map_location="cpu")
        num_classes = checkpoint["model_state_dict"]["arcface_weight"].shape[0]

        # Build model for export (without ArcFace head)
        import timm
        import torch.nn as nn

        model_cfg = self.config["model"]
        backbone = timm.create_model(model_cfg["backbone"], pretrained=False, num_classes=0)

        with torch.no_grad():
            dummy = torch.randn(1, 3, 224, 224)
            backbone_dim = backbone(dummy).shape[1]

        class ExportModel(nn.Module):
            def __init__(self, backbone, backbone_dim, embedding_dim):
                super().__init__()
                self.backbone = backbone
                self.embedding = nn.Sequential(
                    nn.Linear(backbone_dim, embedding_dim),
                    nn.BatchNorm1d(embedding_dim),
                )

            def forward(self, x):
                features = self.backbone(x)
                embeddings = self.embedding(features)
                embeddings = nn.functional.normalize(embeddings, dim=1)
                return embeddings

        export_model = ExportModel(
            backbone, backbone_dim, model_cfg.get("embedding_dim", 512)
        )

        # Copy weights (excluding ArcFace)
        state_dict = checkpoint["model_state_dict"]
        export_state = {
            k: v for k, v in state_dict.items()
            if not k.startswith("arcface")
        }
        export_model.load_state_dict(export_state, strict=False)
        export_model.eval()

        # Export
        dummy_input = torch.randn(1, 3, 224, 224)
        torch.onnx.export(
            export_model,
            dummy_input,
            output_path,
            input_names=["image"],
            output_names=["embedding"],
            dynamic_axes={"image": {0: "batch"}, "embedding": {0: "batch"}},
            opset_version=14,
        )

        logger.info(f"Exported ONNX model to {output_path}")
        return output_path


def main():
    parser = argparse.ArgumentParser(description="Train SKU classifier with ArcFace")
    parser.add_argument(
        "--config",
        type=str,
        default="ml/configs/classifier.yaml",
        help="Path to config file",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to checkpoint to resume from",
    )
    parser.add_argument(
        "--export-embeddings",
        action="store_true",
        help="Export embeddings for all SKUs",
    )
    parser.add_argument(
        "--export-onnx",
        action="store_true",
        help="Export model to ONNX",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default=None,
        help="Path to weights for export",
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="Path to data for embedding export",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models/classifier",
        help="Output directory",
    )

    args = parser.parse_args()

    trainer = ClassifierTrainer(args.config)

    if args.export_embeddings:
        if not args.weights or not args.data_path:
            parser.error("--export-embeddings requires --weights and --data-path")
        trainer.export_embeddings(args.weights, args.data_path, args.output_dir)

    elif args.export_onnx:
        if not args.weights:
            parser.error("--export-onnx requires --weights")
        output_path = Path(args.output_dir) / "classifier.onnx"
        trainer.export_onnx(args.weights, str(output_path))

    else:
        results = trainer.train(resume=args.resume)

        if results["all_targets_met"]:
            logger.info("Auto-exporting model...")
            trainer.export_onnx(
                results["best_weights"],
                str(Path(args.output_dir) / "classifier.onnx")
            )


if __name__ == "__main__":
    main()
