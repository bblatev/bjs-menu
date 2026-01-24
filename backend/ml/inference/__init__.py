"""Inference pipeline for production deployment."""

from ml.inference.pipeline_v2 import (
    PipelineV2,
    PipelineResult,
    ShelfItem,
    Detection,
    Classification,
    Stage1Detector,
    Stage2Classifier,
    create_pipeline,
)

__all__ = [
    "PipelineV2",
    "PipelineResult",
    "ShelfItem",
    "Detection",
    "Classification",
    "Stage1Detector",
    "Stage2Classifier",
    "create_pipeline",
]
