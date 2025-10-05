"""Unit tests for high-level processing mode routing."""

from __future__ import annotations

from types import SimpleNamespace

from glyph_mapper.pdf_processor import OverlayTarget

import glyph_mapper.pdf_processor as pdf_processor


class DummyLogger:
    """Minimal stand-in for ``PDFProcessingLogger`` during unit tests."""

    def __init__(self) -> None:
        noop = lambda *args, **kwargs: None
        self.logger = SimpleNamespace(info=noop, warning=noop, error=noop)
        self.mode = None
        self.mappings = []
        self.input_bytes = None
        self.output_bytes = None
        self.finalized = False

    def log_input_pdf(self, pdf_bytes: bytes, filename: str = "input.pdf") -> None:  # noqa: D401
        self.input_bytes = pdf_bytes

    def log_mode_selection(self, mode: str) -> None:
        self.mode = mode

    def log_mappings(self, mapping):
        self.mappings.append(dict(mapping))

    def log_output_pdf(self, pdf_bytes: bytes, filename: str = "output.pdf") -> None:
        self.output_bytes = pdf_bytes

    def log_error(self, error: Exception, context: str) -> None:
        self.logger.error(error, context)

    def finalize_run(self) -> None:
        self.finalized = True


def test_apply_word_mapping_routes_to_ocr(monkeypatch) -> None:
    """Ensure ``mode='ocr'`` delegates to the OCR helper with cleaned mappings."""

    dummy_logger = DummyLogger()
    monkeypatch.setattr(pdf_processor, "get_logger", lambda: dummy_logger)

    captured = {}

    def fake_ocr(pdf_bytes, mapping, *, dpi=220, min_confidence=60):  # type: ignore[override]
        captured["args"] = (pdf_bytes, mapping, dpi, min_confidence)
        return b"%PDF-ocr-output"

    monkeypatch.setattr(pdf_processor, "apply_image_ocr_mapping", fake_ocr)

    result = pdf_processor.apply_word_mapping(
        b"%PDF-1.7\n",
        {" Vivek ": " Anish "},
        mode="ocr",
    )

    assert result == b"%PDF-ocr-output"
    assert captured["args"][1] == {"Vivek": "Anish"}
    assert captured["args"][2:] == (220, 60)
    assert dummy_logger.mode == "ocr"
    assert dummy_logger.finalized is True


def test_overlay_mode_applies_captured_overlays(monkeypatch) -> None:
    """Overlay mode should restore original glyph appearance after rewrites."""

    dummy_logger = DummyLogger()
    monkeypatch.setattr(pdf_processor, "get_logger", lambda: dummy_logger)

    target = OverlayTarget(page=0, rect=(0.0, 0.0, 10.0, 10.0), image=b"img")

    monkeypatch.setattr(pdf_processor, "_expand_mapping_variants", lambda mapping: mapping)
    monkeypatch.setattr(
        pdf_processor,
        "_collect_overlay_targets",
        lambda pdf_bytes, mapping, mapping_cf: ([target], mapping),
    )
    monkeypatch.setattr(
        pdf_processor,
        "_apply_content_stream_mapping",
        lambda pdf_bytes, clean_mapping: b"%PDF-rewritten",
    )
    monkeypatch.setattr(pdf_processor, "_sanitize_text_layer", lambda data: b"sanitized")

    captured = {}

    def fake_apply_overlays(pdf_bytes, overlays):
        captured["args"] = (pdf_bytes, overlays)
        return b"%PDF-overlaid"

    monkeypatch.setattr(pdf_processor, "_apply_overlays", fake_apply_overlays)

    result = pdf_processor._apply_overlay_mode_mapping(b"%PDF-1.7\n", {"Hello": "World"})

    assert result == b"%PDF-overlaid"
    assert captured["args"][0] == b"sanitized"
    assert captured["args"][1] == [target]
