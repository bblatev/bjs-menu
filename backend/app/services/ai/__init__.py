# AI module

from app.services.ai.clip_service import (
    is_clip_available,
    recognize_with_clip,
    get_clip_embedding,
    match_product_to_database,
)

from app.services.ai.training_pipeline import (
    DataAugmentation,
    FeatureAggregator,
    AccuracyTracker,
    TrainingPipeline,
    run_full_training_pipeline,
)

__all__ = [
    # CLIP service
    "is_clip_available",
    "recognize_with_clip",
    "get_clip_embedding",
    "match_product_to_database",
    # Training pipeline
    "DataAugmentation",
    "FeatureAggregator",
    "AccuracyTracker",
    "TrainingPipeline",
    "run_full_training_pipeline",
]
