"""
PDF Extraction and Text Sanitization Utilities
AI Resume Screening System — Phase 2
"""

import io
import re
import hashlib
import hmac
import logging
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union
import pypdf
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)


@dataclass
class PDFParseResult:
    """Structured data contract for PDF parsing outcomes."""

    success: bool
    text: str
    page_count: int
    word_count: int
    char_count: int
    error: Optional[str] = None
    is_scanned: bool = False


def sanitize_extracted_text(raw_text: str) -> str:
    """Cleans, normalizes, and prepares raw extracted PDF text for LLM consumption.

    - Normalizes newlines and whitespace.
    - Strips non-printable ASCII control characters.
    - Resolves hyphenated word splits across line breaks.
    - Standardizes diverse bullet point symbols into clean markdown dashes.
    """
    if not raw_text:
        return ""

    # Normalize line endings
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # Filter non-printable ASCII control characters (keeping tab and newline)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Resolve hyphenated line breaks (e.g., 'engi-\nneer' -> 'engineer')
    text = re.sub(r"(\b[A-Za-z]+)-\s*\n\s*([A-Za-z]+\b)", r"\1\2", text)

    # Standardize common resume bullet markers into markdown bullet '-'
    text = re.sub(r"^[ \t]*[•▪*–—·\u2022\u2023\u25E6\u2043\u2219][ \t]*", "- ", text, flags=re.MULTILINE)

    # Replace runs of horizontal whitespace with a single space
    text = re.sub(r"[ \t]+", " ", text)

    # Limit consecutive newlines to at most two (preserve paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip empty lines around content
    return text.strip()


def extract_text_from_pdf(source: Union[io.BytesIO, bytes, Any, str, Path]) -> PDFParseResult:
    """Extracts, validates, and normalizes text from a PDF source.

    Supports:
    - Streamlit UploadedFile objects
    - In-memory BytesIO streams
    - Raw bytes
    - File system paths (str or Path)

    Returns:
        PDFParseResult: Structured result with text, stats, and any diagnostic errors.
        NOTE: Error messages are safe for display to end users — internal paths
        and Python exception details are logged server-side only.
    """
    stream: io.BytesIO

    try:
        # Normalize source into a readable BytesIO stream
        if hasattr(source, "getvalue"):  # Streamlit UploadedFile
            content_bytes = source.getvalue()
            stream = io.BytesIO(content_bytes)
        elif hasattr(source, "read"):  # File-like object
            content_bytes = source.read()
            if isinstance(content_bytes, str):
                content_bytes = content_bytes.encode("utf-8")
            stream = io.BytesIO(content_bytes)
        elif isinstance(source, bytes):
            content_bytes = source
            stream = io.BytesIO(content_bytes)
        elif isinstance(source, (str, Path)):
            file_path = Path(source)
            if not file_path.exists():
                # Log the real path internally; show a generic message to the user.
                logger.warning("PDF source file not found: %s", file_path)
                return PDFParseResult(
                    success=False,
                    text="",
                    page_count=0,
                    word_count=0,
                    char_count=0,
                    error="The resume file could not be found on the server.",
                )
            content_bytes = file_path.read_bytes()
            stream = io.BytesIO(content_bytes)
        else:
            logger.error("Unsupported PDF source type: %s", type(source).__name__)
            return PDFParseResult(
                success=False,
                text="",
                page_count=0,
                word_count=0,
                char_count=0,
                error="An internal error occurred while reading the resume file.",
            )

        # Validate minimum file size and PDF magic bytes
        if len(content_bytes) < 4:
            return PDFParseResult(
                success=False,
                text="",
                page_count=0,
                word_count=0,
                char_count=0,
                error="The uploaded file is empty or too small to be a valid PDF.",
            )

        if not content_bytes.startswith(b"%PDF"):
            # Check if magic bytes appear in first 1024 bytes (some PDFs have leading header bytes)
            if b"%PDF-" not in content_bytes[:1024]:
                return PDFParseResult(
                    success=False,
                    text="",
                    page_count=0,
                    word_count=0,
                    char_count=0,
                    error="The file does not appear to be a valid PDF. Please upload a PDF document.",
                )

        # Initialize pypdf reader
        stream.seek(0)
        reader = pypdf.PdfReader(stream)

        # Check for encryption / password protection
        if reader.is_encrypted:
            try:
                # Try decrypting with empty password
                decrypt_success = reader.decrypt("")
                if decrypt_success == 0:
                    return PDFParseResult(
                        success=False,
                        text="",
                        page_count=len(reader.pages) if reader.pages else 0,
                        word_count=0,
                        char_count=0,
                        error="PDF is password-protected or encrypted. Please upload an unlocked PDF.",
                    )
            except Exception:
                return PDFParseResult(
                    success=False,
                    text="",
                    page_count=0,
                    word_count=0,
                    char_count=0,
                    error="PDF is password-protected or encrypted. Please upload an unlocked PDF.",
                )

        page_count = len(reader.pages)
        if page_count == 0:
            return PDFParseResult(
                success=False,
                text="",
                page_count=0,
                word_count=0,
                char_count=0,
                error="The PDF contains no pages.",
            )

        # Extract text across all pages
        extracted_pages = []
        for page_idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                extracted_pages.append(page_text)
            except Exception as page_err:
                logger.warning("Could not extract text from page %d: %s", page_idx + 1, page_err)
                extracted_pages.append("")  # Skip silently — do not expose error detail in output

        raw_combined = "\n\n".join(extracted_pages)
        clean_text = sanitize_extracted_text(raw_combined)

        char_count = len(clean_text)
        word_count = len(clean_text.split()) if clean_text else 0

        # Check for scanned or image-only documents
        is_scanned = False
        warning_msg = None

        if char_count == 0:
            return PDFParseResult(
                success=False,
                text="",
                page_count=page_count,
                word_count=0,
                char_count=0,
                is_scanned=True,
                error=(
                    "No selectable text found. This document appears to be an image-only scan or "
                    "empty document. Please upload a text-selectable PDF."
                ),
            )
        elif char_count < 50:
            is_scanned = True
            warning_msg = (
                f"Low text density ({char_count} characters detected across {page_count} page(s)). "
                "The PDF may be partially scanned or contains mostly vector graphics/images."
            )

        return PDFParseResult(
            success=True,
            text=clean_text,
            page_count=page_count,
            word_count=word_count,
            char_count=char_count,
            error=warning_msg,
            is_scanned=is_scanned,
        )

    except PdfReadError as pe:
        logger.warning("PdfReadError while parsing resume: %s", pe)
        return PDFParseResult(
            success=False,
            text="",
            page_count=0,
            word_count=0,
            char_count=0,
            error="The uploaded PDF appears to be corrupted or unreadable. Please try re-exporting it.",
        )
    except Exception as e:
        logger.error("Unexpected error while parsing PDF: %s", e)
        return PDFParseResult(
            success=False,
            text="",
            page_count=0,
            word_count=0,
            char_count=0,
            error="An unexpected error occurred while reading the PDF. Please try again or use a different file.",
        )


def get_setting(name: str, default: str = "") -> str:
    """Read a setting from Streamlit Secrets first, then environment variables."""
    try:
        import streamlit as st
        value = st.secrets.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    except Exception:
        pass
    return os.getenv(name, default).strip()


def hash_password(password: str) -> str:
    """Create a PBKDF2-SHA256 password hash in salt$hash format."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Constant-time verification of a PBKDF2 password hash."""
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def verify_recruiter_credentials(user_id: str, password: str) -> bool:
    """Verify recruiter credentials from Streamlit Secrets or environment variables.

    Preferred configuration:
      RECRUITER_USER_ID = "..."
      RECRUITER_PASSWORD_HASH = "salt$hash"

    A plaintext RECRUITER_PASSWORD is supported for local development only.
    """
    expected_user = get_setting("RECRUITER_USER_ID")
    password_hash = get_setting("RECRUITER_PASSWORD_HASH")
    plaintext_password = get_setting("RECRUITER_PASSWORD")

    if not expected_user:
        return False
    if not hmac.compare_digest(user_id.strip(), expected_user):
        return False
    if password_hash:
        return verify_password(password, password_hash)
    if plaintext_password:
        return hmac.compare_digest(password, plaintext_password)
    return False
