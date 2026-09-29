import uuid
import logging
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    @staticmethod
    def _upload_root() -> Path:
        """Returns the resolved, absolute upload root directory."""
        return Path(settings.UPLOAD_DIR).resolve()

    @staticmethod
    def _safe_path(relative_path: str) -> Path:
        """
        Resolves *relative_path* against the upload root and verifies that the
        result is still inside the upload root directory (path-traversal guard).

        Raises ValueError if the resolved path escapes the upload root.
        """
        upload_root = StorageService._upload_root()
        # Resolve without requiring the path to exist yet
        candidate = (upload_root / relative_path).resolve()
        try:
            # Python 3.9+: is_relative_to() is the clearest check
            candidate.relative_to(upload_root)
        except ValueError:
            raise ValueError(
                "Invalid attachment path: path traversal attempt detected."
            )
        return candidate

    @staticmethod
    async def save_file(file: UploadFile, folder: str = "attachments") -> Tuple[str, str, int]:
        """
        Saves an uploaded file securely under UPLOAD_DIR/<folder>/.

        * The original filename is discarded; a UUID-based name is always used.
        * Only the file extension is preserved and sanitised (no path separators).
        * File size is enforced against MAX_FILE_SIZE_MB before writing.
        * The final path is verified to remain inside the upload root.

        Returns:
            (relative_file_path, mime_type, file_size_bytes)
        """
        # Sanitise folder name: strip path separators to prevent injection
        safe_folder = Path(folder).name  # keeps only the final component

        # Extract and sanitise file extension
        original_name = file.filename or ""
        raw_ext = Path(original_name).suffix  # e.g. ".pdf"
        # Allow only simple alphanumeric extensions; reject anything that looks
        # like a path or contains unexpected characters.
        if raw_ext and (len(raw_ext) > 8 or not raw_ext.replace(".", "").isalnum()):
            raw_ext = ""
        file_ext = raw_ext.lower()

        unique_filename = f"{uuid.uuid4()}{file_ext}"

        # Build and verify the target path before touching the filesystem
        relative_path_str = f"{safe_folder}/{unique_filename}"
        target_path = StorageService._safe_path(relative_path_str)

        # Ensure the parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Read content and enforce size limit
        content = await file.read()
        file_size = len(content)

        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise ValueError(
                f"File size ({file_size} bytes) exceeds the maximum allowed "
                f"limit of {settings.MAX_FILE_SIZE_MB} MB."
            )

        target_path.write_bytes(content)
        logger.info("Attachment saved: %s (%d bytes)", relative_path_str, file_size)

        mime_type = file.content_type or "application/octet-stream"
        return relative_path_str, mime_type, file_size

    @staticmethod
    def get_full_file_path(relative_path: str) -> str:
        """
        Returns the absolute filesystem path for an attachment stored under the
        upload root.  Raises ValueError if the path escapes the upload root
        (path-traversal guard applied on every access, not just upload).
        """
        return str(StorageService._safe_path(relative_path))
