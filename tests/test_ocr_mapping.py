"""Tests for OCR-driven word replacements in image-heavy PDFs."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PyPDF2 import PdfReader

from glyph_mapper.pdf_processor import OCR_AVAILABLE, apply_image_ocr_mapping


pytestmark = pytest.mark.skipif(
    not OCR_AVAILABLE, reason="pytesseract and Pillow are required for OCR tests"
)


FIXTURE_DIR = Path("tests")


def _extract_all_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_backpropagation_slide_replacement(tmp_path) -> None:
    source = (FIXTURE_DIR / "L20_Backpropagation.pdf").read_bytes()
    result = apply_image_ocr_mapping(
        source,
        {
            "Backpropagation": "Frontpropagation",
            "Rectified": "LECTIFIED",
        },
    )

    output_path = tmp_path / "backprop_ocr.pdf"
    output_path.write_bytes(result)

    combined_text = _extract_all_text(output_path.read_bytes())

    assert "Frontpropagation" in combined_text
    assert "LECTIFIED" in combined_text
    assert "Backpropagation" not in combined_text
    assert "Rectified" not in combined_text
    assert "\x00" not in combined_text


def test_attention_slide_title(tmp_path) -> None:
    source = (FIXTURE_DIR / "CSE_576_Attention.pdf").read_bytes()
    result = apply_image_ocr_mapping(source, {"Vivek": "Anish"})

    output_path = tmp_path / "attention_ocr.pdf"
    output_path.write_bytes(result)

    combined_text = _extract_all_text(output_path.read_bytes())

    assert "Anish" in combined_text
    assert "Vivek" not in combined_text
