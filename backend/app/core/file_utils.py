"""File upload security utilities."""

import os
import re
import uuid
from pathlib import Path
from typing import Optional, Set

# Allowed file extensions by category
ALLOWED_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
ALLOWED_DOCUMENT_EXTENSIONS: Set[str] = {".pdf", ".csv", ".xlsx", ".xls", ".doc", ".docx"}
ALLOWED_VIDEO_EXTENSIONS: Set[str] = {".mp4", ".mov", ".avi", ".webm"}

# Characters that are safe in filenames
SAFE_FILENAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and injection attacks.

    - Removes path components (directory traversal)
    - Replaces unsafe characters
    - Limits length
    - Preserves extension

    Args:
        filename: Original filename from upload

    Returns:
        Sanitized filename safe for storage and display
    """
    if not filename:
        return "unnamed"

    # Get just the filename, removing any path components
    filename = os.path.basename(filename)

    # Remove null bytes and other dangerous characters
    filename = filename.replace("\x00", "").replace("\n", "").replace("\r", "")

    # Split into name and extension
    name, ext = os.path.splitext(filename)

    # Sanitize the name part - replace unsafe chars with underscore
    name = SAFE_FILENAME_PATTERN.sub("_", name)

    # Remove leading/trailing underscores and dots
    name = name.strip("_.")

    # Ensure name is not empty
    if not name:
        name = "file"

    # Limit name length (leave room for extension)
    max_name_length = 200
    if len(name) > max_name_length:
        name = name[:max_name_length]

    # Sanitize extension (lowercase, remove unsafe chars)
    ext = ext.lower()
    ext = SAFE_FILENAME_PATTERN.sub("", ext)
    if ext and not ext.startswith("."):
        ext = "." + ext

    return name + ext


def generate_secure_filename(original_filename: str, prefix: str = "") -> str:
    """
    Generate a secure filename using UUID while preserving the original extension.

    This is the recommended approach for storing uploaded files.

    Args:
        original_filename: Original filename from upload
        prefix: Optional prefix for organizing files

    Returns:
        UUID-based filename with original extension
    """
    # Get sanitized extension
    ext = ""
    if original_filename:
        _, ext = os.path.splitext(original_filename)
        ext = ext.lower()
        # Validate extension contains only safe characters
        if ext and not re.match(r"^\.[a-zA-Z0-9]+$", ext):
            ext = ""

    # Generate UUID-based filename
    unique_id = uuid.uuid4().hex

    if prefix:
        prefix = SAFE_FILENAME_PATTERN.sub("_", prefix).strip("_.")
        return f"{prefix}_{unique_id}{ext}"

    return f"{unique_id}{ext}"


def validate_file_extension(
    filename: str,
    allowed_extensions: Set[str],
    error_message: Optional[str] = None
) -> bool:
    """
    Validate that a filename has an allowed extension.

    Args:
        filename: Filename to validate
        allowed_extensions: Set of allowed extensions (e.g., {".jpg", ".png"})
        error_message: Optional custom error message

    Returns:
        True if extension is allowed

    Raises:
        ValueError if extension is not allowed
    """
    if not filename:
        raise ValueError(error_message or "Filename is required")

    _, ext = os.path.splitext(filename.lower())

    if ext not in allowed_extensions:
        if error_message:
            raise ValueError(error_message)
        raise ValueError(
            f"File type '{ext}' is not allowed. "
            f"Allowed types: {', '.join(sorted(allowed_extensions))}"
        )

    return True


def is_safe_path(base_path: str, target_path: str) -> bool:
    """
    Check if a target path is safely within the base path.

    Prevents path traversal attacks when constructing file paths.

    Args:
        base_path: The base directory that should contain the file
        target_path: The full path to validate

    Returns:
        True if target_path is safely within base_path
    """
    base = Path(base_path).resolve()
    target = Path(target_path).resolve()

    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


def get_safe_upload_path(
    base_dir: str,
    filename: str,
    create_dirs: bool = True
) -> str:
    """
    Generate a safe upload path for a file.

    Args:
        base_dir: Base directory for uploads
        filename: Original filename (will be made secure)
        create_dirs: Whether to create the directory if it doesn't exist

    Returns:
        Full path that's safe for file storage
    """
    secure_name = generate_secure_filename(filename)
    base = Path(base_dir)

    if create_dirs:
        base.mkdir(parents=True, exist_ok=True)

    full_path = base / secure_name

    # Verify the path is within base_dir (defense in depth)
    if not is_safe_path(str(base), str(full_path)):
        raise ValueError("Invalid file path")

    return str(full_path)
