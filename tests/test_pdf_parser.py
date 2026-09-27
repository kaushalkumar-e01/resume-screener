"""
Unit Test Suite for Phase 2: PDF Parsing Logic & Text Sanitization
"""

import io
import unittest
import pypdf
import utils
from utils import PDFParseResult, extract_text_from_pdf, sanitize_extracted_text


class TestPDFParser(unittest.TestCase):

    def test_sanitize_extracted_text(self):
        raw = "Full-Stack Soft-\nware Engi-\nneer with \x005+ years experience.\n\n\n• Python\n* Docker\n– FastAPI\n   Lots   of   spaces.   "
        sanitized = sanitize_extracted_text(raw)
        
        # Test de-hyphenation
        self.assertIn("Software", sanitized)
        self.assertIn("Engineer", sanitized)
        
        # Test bullet normalization
        self.assertIn("- Python", sanitized)
        self.assertIn("- Docker", sanitized)
        self.assertIn("- FastAPI", sanitized)
        
        # Test control character removal
        self.assertNotIn("\x00", sanitized)
        
        # Test space normalization
        self.assertNotIn("   ", sanitized)

    def test_corrupt_pdf_detection(self):
        corrupt_data = b"PK\x03\x04This is a zip file, definitely not a PDF"
        result = extract_text_from_pdf(corrupt_data)
        
        self.assertFalse(result.success)
        self.assertIn("File signature mismatch", result.error)

    def test_empty_bytes_handling(self):
        result = extract_text_from_pdf(b"")
        self.assertFalse(result.success)
        self.assertIn("empty", result.error.lower())

    def test_scanned_or_blank_pdf_detection(self):
        # Create a synthetic blank PDF in memory
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=100, height=100)
        buf = io.BytesIO()
        writer.write(buf)
        pdf_bytes = buf.getvalue()

        result = extract_text_from_pdf(pdf_bytes)
        self.assertTrue(result.is_scanned)
        self.assertFalse(result.success)
        self.assertIn("image-only scan or empty", result.error.lower())

    def test_valid_synthetic_pdf_extraction(self):
        # Create a synthetic PDF with text annotations/stream if possible, or verify result contract
        writer = pypdf.PdfWriter()
        page = writer.add_blank_page(width=300, height=300)
        buf = io.BytesIO()
        writer.write(buf)
        pdf_bytes = buf.getvalue()

        result = extract_text_from_pdf(pdf_bytes)
        self.assertEqual(result.page_count, 1)
        self.assertIsInstance(result, PDFParseResult)


if __name__ == "__main__":
    unittest.main()
