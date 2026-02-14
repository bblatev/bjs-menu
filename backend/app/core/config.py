"""Application configuration using pydantic-settings.

All environment variables should be accessed through the settings object
rather than using os.getenv() directly. This ensures:
1. Type validation at startup
2. Centralized configuration
3. Documentation of available settings
4. Proper defaults
"""

from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import field_validator, model_validator, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All sensitive configuration should be defined here rather than
    accessed via os.getenv() throughout the codebase.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars
    )

    # Database - defaults to relative path for Docker, override via env for local dev
    database_url: str = "sqlite:///./data/bjsbar.db"

    # Redis - optional, used for caching and session storage
    redis_url: Optional[str] = None

    # Security
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 240  # 4 hours

    # CORS - comma-separated origins or "*" for development only
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # ==========================================================================
    # Email/SMTP Configuration (centralized from scattered os.getenv calls)
    # ==========================================================================
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "BJS Menu System"
    smtp_use_tls: bool = True

    # ==========================================================================
    # External POS Integration
    # ==========================================================================
    external_pos_db_url: Optional[str] = None
    external_pos_mapping: Optional[str] = None

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str, info) -> str:
        """Warn if localhost origins are used in production."""
        # We'll check debug mode after all fields are loaded via model_validator
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v == "change-me-in-production":
            import warnings
            warnings.warn(
                "Using default SECRET_KEY is insecure! Set SECRET_KEY environment variable.",
                UserWarning,
                stacklevel=2,
            )
        if len(v) < 32:
            import warnings
            warnings.warn(
                "SECRET_KEY should be at least 32 characters for security.",
                UserWarning,
                stacklevel=2,
            )
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate settings for production safety."""
        import warnings

        # In production mode, enforce secure settings
        if not self.debug:
            # Fail if using default or weak secret key
            if self.secret_key == "change-me-in-production":
                raise ValueError(
                    "FATAL: Cannot start in production mode with default SECRET_KEY. "
                    "Set a secure SECRET_KEY environment variable (minimum 32 characters)."
                )
            if len(self.secret_key) < 32:
                raise ValueError(
                    f"FATAL: SECRET_KEY must be at least 32 characters in production mode "
                    f"(current length: {len(self.secret_key)}). Generate a secure key with: "
                    "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )

            # Warn about localhost in CORS
            localhost_patterns = ["localhost", "127.0.0.1", "0.0.0.0"]
            origins = [o.strip() for o in self.cors_origins.split(",")]
            localhost_origins = [o for o in origins if any(p in o for p in localhost_patterns)]
            if localhost_origins:
                warnings.warn(
                    f"CORS origins contain localhost URLs in production mode: {localhost_origins}. "
                    "Remove localhost origins for production by setting CORS_ORIGINS environment variable.",
                    UserWarning,
                    stacklevel=2,
                )

        return self

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list, filtering localhost in production."""
        if self.cors_origins == "*":
            return ["*"]

        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

        # Filter out localhost origins in production mode
        if not self.debug:
            localhost_patterns = ["localhost", "127.0.0.1", "0.0.0.0"]
            origins = [o for o in origins if not any(p in o for p in localhost_patterns)]

        return origins

    # Timezone
    timezone: str = "Europe/Sofia"

    # File upload limits
    max_upload_size_mb: int = 10  # Maximum file upload size in MB

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

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100  # requests per window
    rate_limit_window: int = 60  # window in seconds


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
