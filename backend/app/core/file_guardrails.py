"""
File Upload Guardrails

Security controls for file uploads to prevent unauthorized
video storage on HQ server.

Policy: HQ stores METADATA ONLY - no video files.
Videos must be processed at edge (terminals) and only
metadata/thumbnails sent to HQ.
"""

from typing import Set, Optional, Callable
from functools import wraps
from fastapi import HTTPException, status, UploadFile

from app.core.feature_flags import is_enabled


# Blocked file extensions (video and other large media)
BLOCKED_VIDEO_EXTENSIONS: Set[str] = {
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv",
    ".webm", ".m4v", ".mpeg", ".mpg", ".3gp", ".3g2",
    ".ogv", ".ts", ".mts", ".m2ts", ".vob"
}

# Blocked MIME types for video
BLOCKED_VIDEO_MIMETYPES: Set[str] = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/x-ms-wmv",
    "video/x-flv",
    "video/webm",
    "video/mpeg",
    "video/3gpp",
    "video/3gpp2",
    "video/ogg",
    "video/mp2t"
}

# Allowed image extensions
ALLOWED_IMAGE_EXTENSIONS: Set[str] = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico"
}

# Allowed image MIME types
ALLOWED_IMAGE_MIMETYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "image/x-icon"
}


def get_file_extension(filename: str) -> str:
    """Extract lowercase file extension from filename."""
    if not filename or "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def is_video_file(file: UploadFile) -> bool:
    """
    Check if an uploaded file is a video file.

    Checks both extension and MIME type for security.
    """
    # Check extension
    ext = get_file_extension(file.filename or "")
    if ext in BLOCKED_VIDEO_EXTENSIONS:
        return True

    # Check MIME type
    if file.content_type and file.content_type.lower() in BLOCKED_VIDEO_MIMETYPES:
        return True

    return False


def is_image_file(file: UploadFile) -> bool:
    """
    Check if an uploaded file is a valid image file.
    """
    # Check extension
    ext = get_file_extension(file.filename or "")
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False

    # Check MIME type if provided
    if file.content_type:
        return file.content_type.lower() in ALLOWED_IMAGE_MIMETYPES

    return True


def validate_no_video(file: UploadFile) -> None:
    """
    Validate that an uploaded file is not a video.

    Raises HTTPException if video upload is attempted
    while VIDEO_STORAGE_BLOCKED flag is enabled.
    """
    if not is_enabled("VIDEO_STORAGE_BLOCKED"):
        # Flag not enabled, allow all uploads (legacy behavior)
        return

    if is_video_file(file):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Video file upload is not permitted on HQ server. "
                "Videos should be processed at terminal level. "
                "Only metadata and thumbnails may be uploaded."
            )
        )


def validate_image_only(file: UploadFile) -> None:
    """
    Validate that an uploaded file is an image.

    Always enforced regardless of feature flags.
    """
    if not is_image_file(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid file type. Only images are allowed. "
                f"Supported formats: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"
            )
        )


def block_video_upload(func: Callable):
    """
    Decorator to block video uploads when VIDEO_STORAGE_BLOCKED is enabled.

    Usage:
        @router.post("/upload")
        @block_video_upload
        async def upload_file(file: UploadFile):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Find the file parameter
        file = kwargs.get("file")
        if file is None:
            for arg in args:
                if isinstance(arg, UploadFile):
                    file = arg
                    break

        if file is not None:
            validate_no_video(file)

        return await func(*args, **kwargs)
    return wrapper


def images_only(func: Callable):
    """
    Decorator to only allow image uploads.

    Usage:
        @router.post("/upload/image")
        @images_only
        async def upload_image(file: UploadFile):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Find the file parameter
        file = kwargs.get("file")
        if file is None:
            for arg in args:
                if isinstance(arg, UploadFile):
                    file = arg
                    break

        if file is not None:
            validate_image_only(file)
            validate_no_video(file)

        return await func(*args, **kwargs)
    return wrapper


class FileGuardrails:
    """
    Centralized file upload policy enforcement.

    Provides methods for validating uploads against
    organizational policies.
    """

    @staticmethod
    def check_upload(
        file: UploadFile,
        allow_video: bool = False,
        require_image: bool = False,
        max_size_mb: int = 10
    ) -> None:
        """
        Check an upload against policy rules.

        Args:
            file: The uploaded file
            allow_video: Whether video is allowed (overridden by feature flag)
            require_image: Whether only images are allowed
            max_size_mb: Maximum file size in megabytes

        Raises:
            HTTPException: If validation fails
        """
        # Always check video policy if flag is enabled
        if is_enabled("VIDEO_STORAGE_BLOCKED") and not allow_video:
            validate_no_video(file)

        # Check image requirement
        if require_image:
            validate_image_only(file)

    @staticmethod
    def is_blocked_globally() -> bool:
        """Check if video storage is blocked globally."""
        return is_enabled("VIDEO_STORAGE_BLOCKED")

    @staticmethod
    def get_policy_status() -> dict:
        """Get current file upload policy status."""
        return {
            "video_storage_blocked": is_enabled("VIDEO_STORAGE_BLOCKED"),
            "allowed_image_types": list(ALLOWED_IMAGE_MIMETYPES),
            "blocked_video_types": list(BLOCKED_VIDEO_MIMETYPES),
            "policy": "HQ stores metadata only. Videos processed at edge."
        }
