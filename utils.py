"""
PDF Extraction and Text Sanitization Utilities
AI Resume Screening System — Phase 2
"""

import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union
import pypdf
from pypdf.errors import PdfReadError


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
                return PDFParseResult(
                    success=False,
                    text="",
                    page_count=0,
                    word_count=0,
                    char_count=0,
                    error=f"File not found: {file_path}",
                )
            content_bytes = file_path.read_bytes()
            stream = io.BytesIO(content_bytes)
        else:
            return PDFParseResult(
                success=False,
                text="",
                page_count=0,
                word_count=0,
                char_count=0,
                error=f"Unsupported file source type: {type(source).__name__}",
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
                    error="File signature mismatch: File does not appear to be a valid PDF format.",
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
                extracted_pages.append(f"\n[Warning: Could not extract text from page {page_idx + 1}: {page_err}]\n")

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
                    "No selectable text found. This document appears to be an image-only scan or empty document. "
                    "Please upload a text-selectable PDF."
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
        return PDFParseResult(
            success=False,
            text="",
            page_count=0,
            word_count=0,
            char_count=0,
            error=f"Corrupted or unreadable PDF: {str(pe)}",
        )
    except Exception as e:
        return PDFParseResult(
            success=False,
            text="",
            page_count=0,
            word_count=0,
            char_count=0,
            error=f"Unexpected error while parsing PDF: {str(e)}",
        )
