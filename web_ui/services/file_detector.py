"""
Unified File Type Detector

Provides consistent file type detection across all upload endpoints.
Uses magic bytes (file signatures) as primary detection method,
with extension fallback for ambiguous cases.

SaaS-FIRST: This detector is format-agnostic. It determines file TYPE,
not file CONTENT. A CSV might be bank transactions, inventory, or anything else.
Classification happens separately.
"""

import os
import logging
from enum import Enum
from typing import Optional, Tuple, BinaryIO
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class FileType(Enum):
    """Supported file types for ingestion"""
    CSV = "csv"
    PDF = "pdf"
    XLS = "xls"
    XLSX = "xlsx"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    TIFF = "tiff"
    HEIC = "heic"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"
    UNKNOWN = "unknown"


@dataclass
class FileDetectionResult:
    """Result of file type detection"""
    file_type: FileType
    mime_type: str
    confidence: str  # "high" (magic bytes) or "medium" (extension only)
    extension: str
    is_supported: bool
    error: Optional[str] = None


# Magic byte signatures for common file types
# Format: (bytes_to_read, offset, signature_bytes, file_type)
MAGIC_SIGNATURES = [
    # PDF: %PDF
    (4, 0, b'%PDF', FileType.PDF),

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    (8, 0, b'\x89PNG\r\n\x1a\n', FileType.PNG),

    # JPEG: FF D8 FF
    (3, 0, b'\xff\xd8\xff', FileType.JPG),

    # TIFF: 49 49 2A 00 (little endian) or 4D 4D 00 2A (big endian)
    (4, 0, b'II*\x00', FileType.TIFF),
    (4, 0, b'MM\x00*', FileType.TIFF),

    # XLSX/DOCX (ZIP-based Office formats): 50 4B 03 04
    (4, 0, b'PK\x03\x04', FileType.XLSX),  # Will differentiate by extension

    # XLS (OLE Compound): D0 CF 11 E0 A1 B1 1A E1
    (8, 0, b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', FileType.XLS),

    # HEIC/HEIF: Various signatures
    (12, 4, b'ftypheic', FileType.HEIC),
    (12, 4, b'ftypmif1', FileType.HEIC),
    (12, 4, b'ftypheix', FileType.HEIC),
]

# MIME types for each file type
MIME_TYPES = {
    FileType.CSV: "text/csv",
    FileType.PDF: "application/pdf",
    FileType.XLS: "application/vnd.ms-excel",
    FileType.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    FileType.PNG: "image/png",
    FileType.JPG: "image/jpeg",
    FileType.JPEG: "image/jpeg",
    FileType.TIFF: "image/tiff",
    FileType.HEIC: "image/heic",
    FileType.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    FileType.DOC: "application/msword",
    FileType.TXT: "text/plain",
    FileType.UNKNOWN: "application/octet-stream",
}

# Supported file types for transaction ingestion
TRANSACTION_SUPPORTED_TYPES = {
    FileType.CSV,
    FileType.PDF,
    FileType.XLS,
    FileType.XLSX,
    FileType.PNG,
    FileType.JPG,
    FileType.JPEG,
    FileType.TIFF,
    FileType.HEIC,
}

# Extension to FileType mapping
EXTENSION_MAP = {
    '.csv': FileType.CSV,
    '.pdf': FileType.PDF,
    '.xls': FileType.XLS,
    '.xlsx': FileType.XLSX,
    '.png': FileType.PNG,
    '.jpg': FileType.JPG,
    '.jpeg': FileType.JPEG,
    '.tiff': FileType.TIFF,
    '.tif': FileType.TIFF,
    '.heic': FileType.HEIC,
    '.heif': FileType.HEIC,
    '.docx': FileType.DOCX,
    '.doc': FileType.DOC,
    '.txt': FileType.TXT,
}


def detect_file_type(
    file_path: Optional[str] = None,
    file_obj: Optional[BinaryIO] = None,
    filename: Optional[str] = None
) -> FileDetectionResult:
    """
    Detect file type using magic bytes and extension.

    Args:
        file_path: Path to file on disk
        file_obj: File-like object (must support read() and seek())
        filename: Original filename (used for extension detection)

    Returns:
        FileDetectionResult with detected type and metadata

    At least one of file_path or file_obj must be provided.
    """
    if not file_path and not file_obj:
        return FileDetectionResult(
            file_type=FileType.UNKNOWN,
            mime_type=MIME_TYPES[FileType.UNKNOWN],
            confidence="none",
            extension="",
            is_supported=False,
            error="No file provided"
        )

    # Get extension from filename or file_path
    if filename:
        ext = os.path.splitext(filename)[1].lower()
    elif file_path:
        ext = os.path.splitext(file_path)[1].lower()
    else:
        ext = ""

    # Try magic byte detection first
    magic_result = _detect_by_magic_bytes(file_path, file_obj)

    if magic_result and magic_result != FileType.UNKNOWN:
        # Special handling for ZIP-based formats (XLSX vs DOCX)
        if magic_result == FileType.XLSX:
            if ext == '.docx':
                magic_result = FileType.DOCX
            elif ext == '.doc':
                # .doc with ZIP signature is unusual, trust the magic bytes
                pass

        return FileDetectionResult(
            file_type=magic_result,
            mime_type=MIME_TYPES.get(magic_result, MIME_TYPES[FileType.UNKNOWN]),
            confidence="high",
            extension=ext,
            is_supported=magic_result in TRANSACTION_SUPPORTED_TYPES
        )

    # Fall back to extension detection
    ext_result = EXTENSION_MAP.get(ext, FileType.UNKNOWN)

    # Special case: CSV files have no magic bytes
    if ext_result == FileType.CSV:
        # Validate it looks like text/CSV
        if _looks_like_csv(file_path, file_obj):
            return FileDetectionResult(
                file_type=FileType.CSV,
                mime_type=MIME_TYPES[FileType.CSV],
                confidence="high",
                extension=ext,
                is_supported=True
            )

    # Special case: TXT files
    if ext_result == FileType.TXT:
        if _looks_like_text(file_path, file_obj):
            return FileDetectionResult(
                file_type=FileType.TXT,
                mime_type=MIME_TYPES[FileType.TXT],
                confidence="high",
                extension=ext,
                is_supported=False  # TXT not for transactions, but valid
            )

    if ext_result != FileType.UNKNOWN:
        return FileDetectionResult(
            file_type=ext_result,
            mime_type=MIME_TYPES.get(ext_result, MIME_TYPES[FileType.UNKNOWN]),
            confidence="medium",
            extension=ext,
            is_supported=ext_result in TRANSACTION_SUPPORTED_TYPES
        )

    # Unknown file type
    return FileDetectionResult(
        file_type=FileType.UNKNOWN,
        mime_type=MIME_TYPES[FileType.UNKNOWN],
        confidence="none",
        extension=ext,
        is_supported=False,
        error=f"Unrecognized file type for extension: {ext}"
    )


def _detect_by_magic_bytes(
    file_path: Optional[str],
    file_obj: Optional[BinaryIO]
) -> Optional[FileType]:
    """Detect file type by reading magic bytes"""
    try:
        # Read first 16 bytes for signature detection
        if file_path:
            with open(file_path, 'rb') as f:
                header = f.read(16)
        elif file_obj:
            current_pos = file_obj.tell()
            file_obj.seek(0)
            header = file_obj.read(16)
            file_obj.seek(current_pos)  # Reset position
        else:
            return None

        if len(header) < 4:
            return None

        # Check each signature
        for bytes_needed, offset, signature, file_type in MAGIC_SIGNATURES:
            if len(header) >= offset + len(signature):
                if header[offset:offset + len(signature)] == signature:
                    return file_type

        return FileType.UNKNOWN

    except Exception as e:
        logger.warning(f"Error reading magic bytes: {e}")
        return None


def _looks_like_csv(
    file_path: Optional[str],
    file_obj: Optional[BinaryIO]
) -> bool:
    """Check if file content looks like CSV (text with commas or tabs)"""
    try:
        if file_path:
            with open(file_path, 'rb') as f:
                sample = f.read(4096)
        elif file_obj:
            current_pos = file_obj.tell()
            file_obj.seek(0)
            sample = file_obj.read(4096)
            file_obj.seek(current_pos)
        else:
            return False

        # Try to decode as text
        try:
            text = sample.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = sample.decode('latin-1')
            except UnicodeDecodeError:
                return False

        # Check for CSV characteristics
        lines = text.split('\n')
        if len(lines) < 2:
            return False

        # Check for consistent delimiter usage
        delimiters = [',', '\t', ';', '|']
        for delim in delimiters:
            counts = [line.count(delim) for line in lines[:5] if line.strip()]
            if counts and min(counts) > 0 and max(counts) - min(counts) <= 2:
                return True

        return False

    except Exception as e:
        logger.warning(f"Error checking CSV format: {e}")
        return False


def _looks_like_text(
    file_path: Optional[str],
    file_obj: Optional[BinaryIO]
) -> bool:
    """Check if file content looks like plain text"""
    try:
        if file_path:
            with open(file_path, 'rb') as f:
                sample = f.read(4096)
        elif file_obj:
            current_pos = file_obj.tell()
            file_obj.seek(0)
            sample = file_obj.read(4096)
            file_obj.seek(current_pos)
        else:
            return False

        # Try to decode as text
        try:
            sample.decode('utf-8')
            return True
        except UnicodeDecodeError:
            try:
                sample.decode('latin-1')
                return True
            except UnicodeDecodeError:
                return False

    except Exception as e:
        logger.warning(f"Error checking text format: {e}")
        return False


def get_supported_extensions() -> list:
    """Get list of supported file extensions for transaction ingestion"""
    return [
        ext for ext, file_type in EXTENSION_MAP.items()
        if file_type in TRANSACTION_SUPPORTED_TYPES
    ]


def is_supported_for_transactions(file_type: FileType) -> bool:
    """Check if file type is supported for transaction ingestion"""
    return file_type in TRANSACTION_SUPPORTED_TYPES


def get_mime_type(file_type: FileType) -> str:
    """Get MIME type for a FileType"""
    return MIME_TYPES.get(file_type, MIME_TYPES[FileType.UNKNOWN])
