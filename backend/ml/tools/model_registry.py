"""
Model Registry for ML Pipeline

Tracks trained models, their metrics, and deployment status.
Supports model versioning and rollback.

Usage:
    # Register a new model
    python -m ml.tools.model_registry register \
        --name detector \
        --version v1.0 \
        --path runs/detector/best/weights/best.pt \
        --metrics '{"recall": 0.98, "map50": 0.96}'

    # List models
    python -m ml.tools.model_registry list --name detector

    # Deploy a model version
    python -m ml.tools.model_registry deploy --name detector --version v1.0

    # Rollback to previous version
    python -m ml.tools.model_registry rollback --name detector
"""

import argparse
import hashlib
import json
import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default registry location
REGISTRY_PATH = Path("ml/models/registry.json")
MODELS_PATH = Path("ml/models")


class ModelRegistry:
    """Registry for tracking ML models."""

    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or REGISTRY_PATH
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict:
        """Load registry from disk."""
        if self.registry_path.exists():
            with open(self.registry_path) as f:
                return json.load(f)
        return {"models": {}, "deployments": {}}

    def _save_registry(self):
        """Save registry to disk."""
        with open(self.registry_path, "w") as f:
            json.dump(self.registry, f, indent=2, default=str)

    def _compute_hash(self, path: Path) -> str:
        """Compute SHA256 hash of model file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]

    def register(
        self,
        name: str,
        version: str,
        path: str,
        metrics: Optional[Dict] = None,
        dataset_hash: Optional[str] = None,
        config_path: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict:
        """
        Register a new model version.

        Args:
            name: Model name (e.g., "detector", "classifier")
            version: Version string (e.g., "v1.0", "v1.1-beta")
            path: Path to model weights
            metrics: Training/validation metrics
            dataset_hash: Hash of training dataset (for reproducibility)
            config_path: Path to training config used
            notes: Optional notes about this version

        Returns:
            Model entry dict
        """
        model_path = Path(path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        # Initialize model entries if needed
        if name not in self.registry["models"]:
            self.registry["models"][name] = {"versions": {}}

        # Check if version already exists
        if version in self.registry["models"][name]["versions"]:
            raise ValueError(f"Version {version} already exists for {name}")

        # Compute model hash
        model_hash = self._compute_hash(model_path)

        # Copy model to registry storage
        dest_dir = MODELS_PATH / name / version
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / model_path.name
        shutil.copy2(model_path, dest_path)

        # Copy config if provided
        if config_path:
            config_src = Path(config_path)
            if config_src.exists():
                shutil.copy2(config_src, dest_dir / "config.yaml")

        # Create entry
        entry = {
            "version": version,
            "path": str(dest_path),
            "original_path": str(model_path),
            "hash": model_hash,
            "size_mb": round(model_path.stat().st_size / (1024 * 1024), 2),
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics or {},
            "dataset_hash": dataset_hash,
            "config_path": str(dest_dir / "config.yaml") if config_path else None,
            "notes": notes,
            "deployed": False,
        }

        self.registry["models"][name]["versions"][version] = entry
        self._save_registry()

        logger.info(f"Registered {name} {version} (hash: {model_hash})")
        return entry

    def list_models(self, name: Optional[str] = None) -> Dict:
        """List all registered models or versions of a specific model."""
        if name:
            if name not in self.registry["models"]:
                return {"error": f"Model {name} not found"}
            return self.registry["models"][name]
        return self.registry["models"]

    def get_model(self, name: str, version: str) -> Optional[Dict]:
        """Get specific model version."""
        if name not in self.registry["models"]:
            return None
        return self.registry["models"][name]["versions"].get(version)

    def get_deployed_version(self, name: str) -> Optional[str]:
        """Get currently deployed version for a model."""
        return self.registry["deployments"].get(name)

    def deploy(self, name: str, version: str) -> Dict:
        """
        Deploy a model version.

        Creates symlinks to the deployed model in the standard location.
        """
        if name not in self.registry["models"]:
            raise ValueError(f"Model {name} not found")

        if version not in self.registry["models"][name]["versions"]:
            raise ValueError(f"Version {version} not found for {name}")

        entry = self.registry["models"][name]["versions"][version]

        # Update deployment record
        previous = self.registry["deployments"].get(name)
        self.registry["deployments"][name] = version

        # Mark as deployed
        for v, e in self.registry["models"][name]["versions"].items():
            e["deployed"] = (v == version)

        # Create symlink to deployed model
        model_path = Path(entry["path"])
        deploy_dir = MODELS_PATH / name
        deploy_link = deploy_dir / f"deployed{model_path.suffix}"

        if deploy_link.exists() or deploy_link.is_symlink():
            deploy_link.unlink()
        deploy_link.symlink_to(model_path.absolute())

        self._save_registry()

        result = {
            "name": name,
            "version": version,
            "previous_version": previous,
            "deployed_path": str(deploy_link),
            "deployed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Deployed {name} {version}")
        return result

    def rollback(self, name: str) -> Dict:
        """Rollback to previous deployed version."""
        if name not in self.registry["models"]:
            raise ValueError(f"Model {name} not found")

        versions = self.registry["models"][name]["versions"]
        current = self.registry["deployments"].get(name)

        if not current:
            raise ValueError(f"No deployment found for {name}")

        # Find previous version by registration date
        sorted_versions = sorted(
            versions.items(),
            key=lambda x: x[1]["registered_at"],
            reverse=True
        )

        previous = None
        found_current = False
        for v, _ in sorted_versions:
            if found_current:
                previous = v
                break
            if v == current:
                found_current = True

        if not previous:
            raise ValueError(f"No previous version to rollback to for {name}")

        return self.deploy(name, previous)

    def delete_version(self, name: str, version: str, force: bool = False) -> bool:
        """Delete a model version."""
        if name not in self.registry["models"]:
            raise ValueError(f"Model {name} not found")

        if version not in self.registry["models"][name]["versions"]:
            raise ValueError(f"Version {version} not found")

        entry = self.registry["models"][name]["versions"][version]

        if entry["deployed"] and not force:
            raise ValueError(f"Cannot delete deployed version. Use --force or deploy another version first.")

        # Delete files
        model_path = Path(entry["path"])
        if model_path.exists():
            model_path.unlink()
        if model_path.parent.exists() and not any(model_path.parent.iterdir()):
            model_path.parent.rmdir()

        # Remove from registry
        del self.registry["models"][name]["versions"][version]
        if self.registry["deployments"].get(name) == version:
            del self.registry["deployments"][name]

        self._save_registry()
        logger.info(f"Deleted {name} {version}")
        return True

    def compare_versions(self, name: str, v1: str, v2: str) -> Dict:
        """Compare metrics between two versions."""
        if name not in self.registry["models"]:
            raise ValueError(f"Model {name} not found")

        versions = self.registry["models"][name]["versions"]
        if v1 not in versions or v2 not in versions:
            raise ValueError(f"Version not found")

        m1 = versions[v1]["metrics"]
        m2 = versions[v2]["metrics"]

        comparison = {
            "version_1": v1,
            "version_2": v2,
            "metrics": {},
        }

        all_metrics = set(m1.keys()) | set(m2.keys())
        for metric in all_metrics:
            val1 = m1.get(metric)
            val2 = m2.get(metric)
            diff = None
            if val1 is not None and val2 is not None:
                try:
                    diff = float(val2) - float(val1)
                except (TypeError, ValueError):
                    pass

            comparison["metrics"][metric] = {
                "v1": val1,
                "v2": val2,
                "diff": diff,
            }

        return comparison


def main():
    parser = argparse.ArgumentParser(description="ML Model Registry")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Register command
    register_parser = subparsers.add_parser("register", help="Register a new model")
    register_parser.add_argument("--name", required=True, help="Model name")
    register_parser.add_argument("--version", required=True, help="Version string")
    register_parser.add_argument("--path", required=True, help="Path to model file")
    register_parser.add_argument("--metrics", help="Metrics as JSON string")
    register_parser.add_argument("--dataset-hash", help="Dataset hash for reproducibility")
    register_parser.add_argument("--config", help="Path to training config")
    register_parser.add_argument("--notes", help="Notes about this version")

    # List command
    list_parser = subparsers.add_parser("list", help="List registered models")
    list_parser.add_argument("--name", help="Model name (optional)")

    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy a model version")
    deploy_parser.add_argument("--name", required=True, help="Model name")
    deploy_parser.add_argument("--version", required=True, help="Version to deploy")

    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback to previous version")
    rollback_parser.add_argument("--name", required=True, help="Model name")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a model version")
    delete_parser.add_argument("--name", required=True, help="Model name")
    delete_parser.add_argument("--version", required=True, help="Version to delete")
    delete_parser.add_argument("--force", action="store_true", help="Force delete even if deployed")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two versions")
    compare_parser.add_argument("--name", required=True, help="Model name")
    compare_parser.add_argument("--v1", required=True, help="First version")
    compare_parser.add_argument("--v2", required=True, help="Second version")

    args = parser.parse_args()
    registry = ModelRegistry()

    if args.command == "register":
        metrics = None
        if args.metrics:
            metrics = json.loads(args.metrics)

        entry = registry.register(
            name=args.name,
            version=args.version,
            path=args.path,
            metrics=metrics,
            dataset_hash=args.dataset_hash,
            config_path=args.config,
            notes=args.notes,
        )
        print(json.dumps(entry, indent=2))

    elif args.command == "list":
        result = registry.list_models(args.name)
        print(json.dumps(result, indent=2))

    elif args.command == "deploy":
        result = registry.deploy(args.name, args.version)
        print(json.dumps(result, indent=2))

    elif args.command == "rollback":
        result = registry.rollback(args.name)
        print(json.dumps(result, indent=2))

    elif args.command == "delete":
        registry.delete_version(args.name, args.version, args.force)
        print(f"Deleted {args.name} {args.version}")

    elif args.command == "compare":
        result = registry.compare_versions(args.name, args.v1, args.v2)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
