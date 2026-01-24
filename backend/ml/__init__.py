"""
ML Module for Shelf Recognition Pipeline V2

2-Stage Architecture:
- Stage 1: YOLOv8 bottle/can detection
- Stage 2: EfficientNet + ArcFace SKU classification

Target Metrics:
- Detection Recall >= 0.98
- mAP50 >= 0.95
- SKU Top-1 Accuracy >= 93%
- Count MAE <= 0.30 per SKU
"""

from ml.inference.pipeline_v2 import (
    PipelineV2,
    PipelineResult,
    ShelfItem,
    Detection,
    Classification,
    create_pipeline,
)

__all__ = [
    "PipelineV2",
    "PipelineResult",
    "ShelfItem",
    "Detection",
    "Classification",
    "create_pipeline",
]

__version__ = "2.0.0"
