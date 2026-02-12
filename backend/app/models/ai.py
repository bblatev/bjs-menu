"""AI-related models for inventory system.

Includes:
- AIPhoto: Shelf scan photos
- TrainingImage: Bottle recognition training data

Note: Uses stock_item_id to reference main V99 database stock_items table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, LargeBinary, Float, Integer, Boolean, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inventory import InventoryLine
    from app.models.stock_item import StockItem


class AIPhoto(Base):
    """Photo taken for AI shelf scanning (optional persistence)."""

    __tablename__ = "ai_photos"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )
    storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TrainingImage(Base):
    """Training image for bottle recognition.

    Stores both the image file path and extracted feature vectors.
    Supports augmented features for more robust matching.
    Uses stock_item_id to reference main V99 stock_items table.
    """

    __tablename__ = "training_images"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_item_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # Feature vectors
    # Primary feature vector from original image (serialized numpy array)
    feature_vector: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    # Aggregated features from augmented versions (more robust for matching)
    augmented_features: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    # Color histogram for fallback/legacy matching (serialized as bytes)
    color_histogram: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)

    # OCR extracted text from label for text-based matching
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # OCR brand name if detected
    ocr_brand: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # OCR product name if detected
    ocr_product_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Image metadata
    # MD5 hash for duplicate detection
    image_hash: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    # Original image dimensions
    image_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Quality and verification
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Feature extraction metadata
    feature_version: Mapped[Optional[str]] = mapped_column(String(20), default="v2", nullable=True)
    extraction_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships - use explicit foreign_keys since we're referencing main V99 database
    stock_item: Mapped["StockItem"] = relationship(
        "StockItem",
        back_populates="training_images",
        foreign_keys=[stock_item_id],
        primaryjoin="TrainingImage.stock_item_id == StockItem.id"
    )

    @property
    def product_id(self) -> int:
        """Compatibility property for code expecting product_id."""
        return self.stock_item_id

    @property
    def product(self):
        """Compatibility property for code expecting .product relationship."""
        return self.stock_item


class ProductFeatureCache(Base):
    """Cached aggregated features for a stock item.

    Pre-computed aggregated features from all training images
    for faster recognition lookups.
    """

    __tablename__ = "product_feature_cache"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_item_id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, index=True
    )

    @property
    def product_id(self) -> int:
        """Compatibility property for code expecting product_id."""
        return self.stock_item_id

    # Aggregated feature vector from all training images
    aggregated_features: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    # Number of training images used
    image_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Feature version used for aggregation
    feature_version: Mapped[Optional[str]] = mapped_column(String(20), default="v2", nullable=True)

    # Timestamps
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )


class RecognitionLog(Base):
    """Log of recognition attempts for analytics and debugging."""

    __tablename__ = "recognition_logs"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)

    # Result
    matched_product_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_match: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Metadata
    inference_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top_5_results: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string

    # Request info
    image_hash: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "mobile", "web", "api"
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # User feedback
    user_confirmed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    user_correction_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
