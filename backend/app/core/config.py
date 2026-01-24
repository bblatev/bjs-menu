"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database - defaults to relative path for Docker, override via env for local dev
    database_url: str = "sqlite:///./data/bjsbar.db"

    # Security
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Timezone
    timezone: str = "Europe/Sofia"

    # AI/ML - relative paths for Docker deployment
    ai_model_path: str = "./models/shelf_detector.onnx"
    ai_confidence_threshold: float = 0.5
    ai_store_photos: bool = False
    ai_training_images_path: str = "./data/training_images"
    ai_recognition_threshold: float = 0.55  # Lowered for better matching with OCR

    # AI V2 Pipeline (2-stage: YOLO detection + SKU classification)
    ai_v2_enabled: bool = False  # Feature flag for new pipeline
    ai_v2_pipeline_config: str = "ml/configs/pipeline.yaml"
    ai_v2_detector_model: str = "models/detector/best.onnx"
    ai_v2_classifier_model: str = "models/classifier/best.onnx"
    ai_v2_embeddings_path: str = "models/classifier/embeddings.npy"
    ai_v2_detection_threshold: float = 0.5
    ai_v2_classification_threshold: float = 0.65
    ai_v2_active_learning_enabled: bool = True

    # POS Integration
    pos_default_connector: str = "csv"

    # Server
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # API
    api_v1_prefix: str = "/api/v1"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
