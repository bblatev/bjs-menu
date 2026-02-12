"""
Training Image Storage Service

Handles storage of AI training images in MinIO instead of local filesystem.
Includes migration utilities for moving existing images to MinIO.
"""
import io
import os
import uuid
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)

# Constants
TRAINING_BUCKET = "training-images"
MIN_IMAGE_SIZE = 1000  # Minimum 1KB for valid image
MIN_IMAGE_DIMENSIONS = (50, 50)  # Minimum 50x50 pixels
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # Maximum 50MB


class TrainingImageStorageService:
    """Service for storing training images in MinIO."""

    def __init__(self):
        """Initialize MinIO client."""
        self._client: Optional[Minio] = None
        self._initialized = False
        self._init_client()

    def _init_client(self):
        """Initialize MinIO client and ensure bucket exists."""
        try:
            if not settings.MINIO_ACCESS_KEY or not settings.MINIO_SECRET_KEY:
                logger.warning("MinIO credentials not configured, using local storage fallback")
                return

            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )

            # Ensure bucket exists
            if not self._client.bucket_exists(TRAINING_BUCKET):
                self._client.make_bucket(TRAINING_BUCKET)
                logger.info(f"Created MinIO bucket: {TRAINING_BUCKET}")

            self._initialized = True
            logger.info("TrainingImageStorageService: MinIO initialized")

        except Exception as e:
            logger.error(f"Failed to initialize MinIO: {e}")
            self._client = None

    @property
    def is_minio_available(self) -> bool:
        """Check if MinIO is available."""
        return self._client is not None and self._initialized

    def validate_image(self, image_data: bytes) -> Tuple[bool, str]:
        """
        Validate image data meets minimum requirements.

        Args:
            image_data: Raw image bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check minimum size
        if len(image_data) < MIN_IMAGE_SIZE:
            return False, f"Image too small ({len(image_data)} bytes). Minimum is {MIN_IMAGE_SIZE} bytes."

        # Check maximum size
        if len(image_data) > MAX_IMAGE_SIZE:
            return False, f"Image too large ({len(image_data)} bytes). Maximum is {MAX_IMAGE_SIZE} bytes."

        # Try to open with PIL to verify it's a valid image and check dimensions
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_data))
            width, height = img.size

            if width < MIN_IMAGE_DIMENSIONS[0] or height < MIN_IMAGE_DIMENSIONS[1]:
                return False, f"Image dimensions too small ({width}x{height}). Minimum is {MIN_IMAGE_DIMENSIONS[0]}x{MIN_IMAGE_DIMENSIONS[1]}."

            # Verify the image can be fully loaded (not corrupted)
            img.verify()

        except Exception as e:
            return False, f"Invalid or corrupted image: {str(e)}"

        return True, ""

    def upload_image(
        self,
        image_data: bytes,
        product_id: int,
        filename: Optional[str] = None,
        content_type: str = "image/jpeg"
    ) -> Tuple[bool, str]:
        """
        Upload training image to MinIO.

        Args:
            image_data: Raw image bytes
            product_id: Product ID this image is for
            filename: Optional filename (will be generated if not provided)
            content_type: MIME type of the image

        Returns:
            Tuple of (success, object_name_or_error)
        """
        # Validate first
        is_valid, error = self.validate_image(image_data)
        if not is_valid:
            return False, error

        # Generate object name
        if not filename:
            ext = "jpg" if "jpeg" in content_type else content_type.split("/")[-1]
            filename = f"{uuid.uuid4().hex[:12]}.{ext}"

        object_name = f"product_{product_id}/{filename}"

        if not self.is_minio_available:
            # Fallback to local storage
            return self._save_local(image_data, product_id, filename)

        try:
            self._client.put_object(
                TRAINING_BUCKET,
                object_name,
                io.BytesIO(image_data),
                length=len(image_data),
                content_type=content_type
            )
            logger.info(f"Uploaded training image: {object_name}")
            return True, object_name

        except S3Error as e:
            logger.error(f"MinIO upload error: {e}")
            return False, str(e)

    def _save_local(
        self,
        image_data: bytes,
        product_id: int,
        filename: str
    ) -> Tuple[bool, str]:
        """Fallback to local storage when MinIO unavailable."""
        local_dir = Path("training_images")
        local_dir.mkdir(exist_ok=True)

        local_path = local_dir / f"{product_id}_{filename}"
        try:
            with open(local_path, "wb") as f:
                f.write(image_data)
            return True, str(local_path)
        except Exception as e:
            return False, str(e)

    def get_image(self, object_name: str) -> Optional[bytes]:
        """
        Retrieve image data from MinIO.

        Args:
            object_name: Object path in bucket

        Returns:
            Image bytes or None if not found
        """
        if not self.is_minio_available:
            # Try local fallback
            if os.path.exists(object_name):
                with open(object_name, "rb") as f:
                    return f.read()
            return None

        try:
            response = self._client.get_object(TRAINING_BUCKET, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error:
            return None

    def delete_image(self, object_name: str) -> bool:
        """
        Delete image from MinIO.

        Args:
            object_name: Object path in bucket

        Returns:
            True if deleted successfully
        """
        if not self.is_minio_available:
            # Try local fallback
            if os.path.exists(object_name):
                os.remove(object_name)
            return True

        try:
            self._client.remove_object(TRAINING_BUCKET, object_name)
            return True
        except S3Error as e:
            logger.error(f"MinIO delete error: {e}")
            return False

    def get_presigned_url(self, object_name: str, expires_hours: int = 24) -> Optional[str]:
        """Get presigned URL for image access."""
        if not self.is_minio_available:
            return None

        try:
            from datetime import timedelta
            url = self._client.presigned_get_object(
                TRAINING_BUCKET,
                object_name,
                expires=timedelta(hours=expires_hours)
            )
            return url
        except S3Error:
            return None

    def migrate_local_to_minio(self, local_dir: str = "training_images") -> Dict[str, Any]:
        """
        Migrate existing local training images to MinIO.

        Args:
            local_dir: Path to local training images directory

        Returns:
            Migration statistics
        """
        if not self.is_minio_available:
            return {
                "success": False,
                "error": "MinIO not available",
                "migrated": 0,
                "failed": 0
            }

        local_path = Path(local_dir)
        if not local_path.exists():
            return {
                "success": True,
                "error": None,
                "migrated": 0,
                "failed": 0,
                "message": "No local training images found"
            }

        migrated = 0
        failed = 0
        errors = []

        for img_file in local_path.iterdir():
            if not img_file.is_file():
                continue

            # Skip non-image files
            if img_file.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
                continue

            try:
                # Parse product_id from filename (format: {product_id}_{uuid}.{ext})
                name_parts = img_file.stem.split('_')
                if name_parts[0].isdigit():
                    product_id = int(name_parts[0])
                else:
                    product_id = 0  # Unknown product

                # Read image data
                with open(img_file, "rb") as f:
                    image_data = f.read()

                # Validate
                is_valid, error = self.validate_image(image_data)
                if not is_valid:
                    logger.warning(f"Skipping invalid image {img_file.name}: {error}")
                    failed += 1
                    errors.append(f"{img_file.name}: {error}")
                    continue

                # Upload to MinIO
                object_name = f"product_{product_id}/{img_file.name}"
                content_type = self._guess_content_type(img_file.suffix)

                self._client.put_object(
                    TRAINING_BUCKET,
                    object_name,
                    io.BytesIO(image_data),
                    length=len(image_data),
                    content_type=content_type
                )
                migrated += 1
                logger.info(f"Migrated: {img_file.name} -> {object_name}")

            except Exception as e:
                failed += 1
                errors.append(f"{img_file.name}: {str(e)}")
                logger.error(f"Failed to migrate {img_file.name}: {e}")

        return {
            "success": True,
            "migrated": migrated,
            "failed": failed,
            "errors": errors[:20],  # Limit error list
            "total_files": migrated + failed
        }

    def cleanup_invalid_images(self, local_dir: str = "training_images") -> Dict[str, Any]:
        """
        Find and optionally remove invalid/tiny training images.

        Args:
            local_dir: Path to local training images directory

        Returns:
            Cleanup statistics
        """
        local_path = Path(local_dir)
        if not local_path.exists():
            return {"invalid_images": [], "total_checked": 0}

        invalid = []
        checked = 0

        for img_file in local_path.iterdir():
            if not img_file.is_file():
                continue

            if img_file.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
                continue

            checked += 1

            try:
                with open(img_file, "rb") as f:
                    image_data = f.read()

                is_valid, error = self.validate_image(image_data)
                if not is_valid:
                    invalid.append({
                        "file": str(img_file),
                        "size": len(image_data),
                        "error": error
                    })
            except Exception as e:
                invalid.append({
                    "file": str(img_file),
                    "size": 0,
                    "error": str(e)
                })

        return {
            "invalid_images": invalid,
            "total_checked": checked,
            "valid_count": checked - len(invalid)
        }

    def _guess_content_type(self, suffix: str) -> str:
        """Guess content type from file extension."""
        mapping = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.gif': 'image/gif'
        }
        return mapping.get(suffix.lower(), 'image/jpeg')


# Global instance
_storage_service: Optional[TrainingImageStorageService] = None


def get_training_storage_service() -> TrainingImageStorageService:
    """Get or create the global storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = TrainingImageStorageService()
    return _storage_service
