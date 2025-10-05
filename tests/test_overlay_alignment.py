"""Utility assertions to ensure overlay crops match original spans."""

from __future__ import annotations

import io
import statistics
from pathlib import Path
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
from PIL import Image, ImageChops

Mapping = Dict[str, str]
LineRecord = Tuple[int, int, str, Tuple[float, float, float, float]]


def _collect_lines(document: fitz.Document, token: str) -> List[LineRecord]:
    """Return (page_index, line_index, text, bbox) for lines containing ``token``."""
    results: List[LineRecord] = []
    for page_index, page in enumerate(document):
        raw = page.get_text("rawdict")
        for block in raw["blocks"]:
            if "lines" not in block:
                continue
            for line_index, line in enumerate(block["lines"]):
                line_text = "".join(
                    "".join(char["c"] for char in span.get("chars", ()))
                    for span in line.get("spans", ())
                )
                if token in line_text:
                    bbox = line.get("bbox")
                    if bbox:
                        results.append((page_index, line_index, line_text, tuple(bbox)))
    return results


def _render_clip(page: fitz.Page, bbox: Tuple[float, float, float, float], *, dpi: int = 300) -> Image.Image:
    pix = page.get_pixmap(clip=fitz.Rect(*bbox), dpi=dpi, alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png")))


def _mean_pixel_delta(img_a: Image.Image, img_b: Image.Image) -> float:
    diff = ImageChops.difference(img_a, img_b).convert("L")
    return statistics.mean(diff.getdata())


def assert_overlay_alignment(
    *,
    original_pdf: Path,
    remapped_pdf: Path,
    mapping: Mapping,
    tolerance_px: int = 2,
    mean_delta_max: float = 15.0,
    dpi: int = 300,
) -> None:
    """Assert that the rendered overlays match the original visuals and text is replaced."""
    orig_doc = fitz.open(original_pdf)
    new_doc = fitz.open(remapped_pdf)

    try:
        all_new_text = "\n".join(page.get_text("text") for page in new_doc)
        for original_token, replacement in mapping.items():
            assert (
                replacement in all_new_text
            ), f"Replacement token '{replacement}' not present in remapped PDF text layer"

            original_lines = _collect_lines(orig_doc, original_token)
            for page_index, line_index, _, orig_bbox in original_lines:
                orig_img = _render_clip(orig_doc[page_index], orig_bbox, dpi=dpi)
                new_img = _render_clip(new_doc[page_index], orig_bbox, dpi=dpi)

                width_diff = abs(orig_img.width - new_img.width)
                height_diff = abs(orig_img.height - new_img.height)
                assert (
                    width_diff <= tolerance_px and height_diff <= tolerance_px
                ), (
                    f"Overlay image dimensions drifted beyond tolerance for page {page_index + 1}, "
                    f"line {line_index + 1}: width diff {width_diff}px, height diff {height_diff}px"
                )

                mean_delta = _mean_pixel_delta(orig_img, new_img)
                assert (
                    mean_delta <= mean_delta_max
                ), (
                    f"Overlay visual delta ({mean_delta:.2f}) exceeded allowable limit for page "
                    f"{page_index + 1}, line {line_index + 1}"
                )
    finally:
        orig_doc.close()
        new_doc.close()


if __name__ == "__main__":
    assert_overlay_alignment(
        original_pdf=Path("runs/20251003_230435_831/input.pdf"),
        remapped_pdf=Path("glyph-remapped-20251004_013227_841-overlay.pdf"),
        mapping={"water?": "aciid?"},
    )
    print("Overlay alignment checks passed.")
