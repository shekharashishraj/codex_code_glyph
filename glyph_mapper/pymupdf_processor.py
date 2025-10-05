"""PyMuPDF-based PDF text processing for reliable text extraction and replacement."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Pattern, Tuple

import io

import fitz  # PyMuPDF
from PIL import Image

from .logger import get_logger


class PyMuPDFProcessor:
    """PDF text processor using PyMuPDF for reliable text handling."""

    def __init__(self, pattern: Pattern[str], clean_mapping: Dict[str, str], mapping_cf: Dict[str, str]):
        self.pattern = pattern
        self.clean_mapping = clean_mapping
        self.mapping_cf = mapping_cf
        self.logger = get_logger()
        self._font_cache: Dict[str, Tuple[str, Optional[bytes]]] = {}

    def process_pdf_overlay_mode(self, pdf_bytes: bytes) -> bytes:
        """
        Process PDF using PyMuPDF with overlay approach.

        1. Extract text blocks with positions using PyMuPDF
        2. Find and replace text using regex
        3. Create overlays to preserve original appearance
        4. Return modified PDF
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        overlays = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_overlays = self._process_page_overlay(page, page_num)
            overlays.extend(page_overlays)

        if overlays:
            self.logger.logger.info(f"Created {len(overlays)} overlays across {len(doc)} pages")
            # Apply overlays to preserve original appearance
            modified_pdf = self._apply_overlays_pymupdf(doc, overlays)
        else:
            self.logger.logger.info("No text replacements made")
            modified_pdf = doc.tobytes()

        doc.close()
        return modified_pdf

    def process_pdf_font_mode(self, pdf_bytes: bytes) -> bytes:
        """
        Process PDF using PyMuPDF with font replacement approach.

        1. Extract and analyze fonts
        2. Create character mappings
        3. Replace text directly
        4. Return modified PDF
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # Apply direct text replacement
        replacements_made = 0
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_replacements = self._process_page_direct_replacement(page, page_num)
            replacements_made += page_replacements

        if replacements_made > 0:
            self.logger.logger.info(f"Made {replacements_made} direct text replacements")
            modified_pdf = doc.tobytes()
        else:
            self.logger.logger.info("No text replacements made")
            modified_pdf = doc.tobytes()

        doc.close()
        return modified_pdf

    def _process_page_overlay(self, page: fitz.Page, page_num: int) -> List[Dict]:
        """Process a single page for overlay mode - capture original text appearance."""
        overlays = []

        # Get text blocks with position information
        blocks = page.get_text("rawdict")

        for block in blocks["blocks"]:
            if "lines" not in block:
                continue  # Skip image blocks

            for line in block["lines"]:
                spans = []
                line_changed = False
                line_bbox = list(line.get("bbox", (float("inf"), float("inf"), float("-inf"), float("-inf"))))

                for span in line["spans"]:
                    chars = span.get("chars", [])
                    if not chars:
                        continue

                    text = "".join(char["c"] for char in chars)
                    new_text = self._apply_text_replacements(text)

                    span_x0 = min(char["bbox"][0] for char in chars)
                    span_y0 = min(char["bbox"][1] for char in chars)
                    span_x1 = max(char["bbox"][2] for char in chars)
                    span_y1 = max(char["bbox"][3] for char in chars)

                    if line_bbox[0] == float("inf"):
                        line_bbox = [span_x0, span_y0, span_x1, span_y1]
                    else:
                        line_bbox[0] = min(line_bbox[0], span_x0)
                        line_bbox[1] = min(line_bbox[1], span_y0)
                        line_bbox[2] = max(line_bbox[2], span_x1)
                        line_bbox[3] = max(line_bbox[3], span_y1)

                    spans.append({
                        "original_text": text,
                        "new_text": new_text,
                        "font": span.get("font", ""),
                        "size": span.get("size", 12),
                        "flags": span.get("flags", 0),
                        "color": span.get("color", 0),
                        "origin": chars[0].get("origin", (span_x0, span_y1)),
                        "bbox": (span_x0, span_y0, span_x1, span_y1),
                    })

                    if new_text != text:
                        line_changed = True

                if not spans or not line_changed:
                    continue

                bbox_tuple = self._expand_bbox(tuple(line_bbox), page.rect)
                overlays.append({
                    "page": page_num,
                    "bbox": bbox_tuple,
                    "spans": spans,
                })

                original_line = "".join(span["original_text"] for span in spans)
                new_line = "".join(span["new_text"] for span in spans)
                self.logger.logger.info(
                    f"Page {page_num + 1}: '{original_line}' → '{new_line}' at {bbox_tuple}"
                )

        return overlays

    def _process_page_direct_replacement(self, page: fitz.Page, page_num: int) -> int:
        """Process a single page for font mode - direct text replacement."""
        replacements_made = 0

        # Get text blocks
        blocks = page.get_text("dict")

        # Find text to replace
        text_instances = []
        for block in blocks["blocks"]:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"]
                    if not text.strip():
                        continue

                    matches = list(self.pattern.finditer(text))
                    if matches:
                        text_instances.append({
                            "bbox": span["bbox"],
                            "text": text,
                            "font_info": {
                                "font": span.get("font", ""),
                                "size": span.get("size", 12),
                                "flags": span.get("flags", 0),
                                "color": span.get("color", 0)
                            }
                        })

        # Apply replacements
        for instance in text_instances:
            new_text = self._apply_text_replacements(instance["text"])
            if new_text != instance["text"]:
                # Remove original text
                page.add_redact_annot(instance["bbox"])
                page.apply_redactions()

                # Add new text using the original font when available.
                font_alias = self._ensure_font(page.parent, page, instance["font_info"].get("font", ""))
                page.insert_text(
                    instance["bbox"][:2],  # (x, y) - top-left corner
                    new_text,
                    fontsize=instance["font_info"].get("size", 12),
                    fontname=font_alias,
                    color=self._color_to_rgb(instance["font_info"].get("color", 0)),
                )

                replacements_made += 1
                self.logger.logger.info(
                    f"Page {page_num + 1}: Direct replacement '{instance['text']}' → '{new_text}'"
                )

        return replacements_made

    def _apply_text_replacements(self, text: str) -> str:
        """Apply regex-based text replacements."""
        def replace_func(match):
            matched_text = match.group()
            # Try case-sensitive first, then case-insensitive
            if matched_text in self.clean_mapping:
                replacement = self.clean_mapping[matched_text]
            else:
                replacement = self.mapping_cf.get(matched_text.casefold(), matched_text)

            self.logger.logger.debug(f"Replacing '{matched_text}' with '{replacement}'")
            return replacement

        return self.pattern.sub(replace_func, text)

    def _apply_overlays_pymupdf(self, doc: fitz.Document, overlays: List[Dict]) -> bytes:
        """Apply overlays to preserve original text appearance."""
        for overlay in overlays:
            try:
                page = doc[overlay["page"]]
                bbox = overlay["bbox"]

                clip_rect = fitz.Rect(*bbox)

                # Remove the original glyphs within this region before redrawing.
                page.add_redact_annot(clip_rect, fill=(1, 1, 1))
                page.apply_redactions()

                for span_info in overlay["spans"]:
                    baseline = span_info.get("origin")
                    if not baseline or len(baseline) != 2:
                        bbox_span = span_info.get("bbox", bbox)
                        baseline = (bbox_span[0], bbox_span[1] + span_info["size"])

                    font_alias = self._ensure_font(doc, page, span_info.get("font", ""))
                    page.insert_text(
                        baseline,
                        span_info["new_text"],
                        fontsize=span_info["size"],
                        fontname=font_alias,
                        color=self._color_to_rgb(span_info.get("color", 0)),
                    )

                self.logger.logger.debug(f"Redrew overlay spans on page {overlay['page'] + 1}")

            except Exception as e:
                self.logger.log_error(e, f"apply_overlay_page_{overlay['page']}")
                continue

        return doc.tobytes()

    def _color_to_rgb(self, value: int) -> Tuple[float, float, float]:
        """Convert an integer PDF color to an RGB triple for PyMuPDF."""
        if value is None:
            return 0.0, 0.0, 0.0

        if value == 0:
            return 0.0, 0.0, 0.0

        r = ((value >> 16) & 0xFF) / 255.0
        g = ((value >> 8) & 0xFF) / 255.0
        b = (value & 0xFF) / 255.0
        return r, g, b

    def _expand_bbox(self, bbox: Tuple[float, float, float, float], page_rect: fitz.Rect, padding: float = 1.0) -> Tuple[float, float, float, float]:
        """Add a small ``padding`` around the bounding box and clamp it to the page."""
        x0, y0, x1, y1 = bbox
        if x0 == float("inf") or y0 == float("inf"):
            return bbox

        expanded = (
            max(page_rect.x0, x0 - padding),
            max(page_rect.y0, y0 - padding),
            min(page_rect.x1, x1 + padding),
            min(page_rect.y1, y1 + padding),
        )
        return expanded

    def _ensure_font(self, doc: fitz.Document, page: fitz.Page, font_name: str) -> str:
        """Register the original font in the document so new text uses consistent glyphs."""
        clean_name = font_name or "helv"
        cached = self._font_cache.get(clean_name)
        if cached:
            alias, font_bytes = cached
            try:
                if font_bytes:
                    page.insert_font(fontname=alias, fontbuffer=font_bytes)
                else:
                    page.insert_font(fontname=alias)
            except ValueError:
                # If the alias already exists for the page, silently ignore.
                pass
            return alias

        font_bytes = self._extract_font_bytes(doc, page, clean_name)
        if not font_bytes:
            self.logger.logger.warning(
                f"Falling back to Helvetica for overlay text because font '{clean_name}' was not embedded."
            )
            self._font_cache[clean_name] = ("helv", None)
            return "helv"

        alias = f"overlay_font_{len(self._font_cache)}"
        page.insert_font(fontname=alias, fontbuffer=font_bytes)
        self._font_cache[clean_name] = (alias, font_bytes)
        return alias

    def _extract_font_bytes(self, doc: fitz.Document, page: fitz.Page, font_name: str) -> Optional[bytes]:
        """Extract the embedded font bytes that correspond to ``font_name``."""
        for font_entry in page.get_fonts(full=True):
            xref, _, _, embedded_name, *_ = font_entry
            clean_embedded = embedded_name.split("+")[-1]
            if clean_embedded == font_name:
                try:
                    extracted = doc.extract_font(xref)
                except Exception as exc:  # pragma: no cover - defensive
                    self.logger.log_error(exc, f"extract_font_{font_name}")
                    return None
                # extract_font returns (name, type, subtype, data)
                if extracted and len(extracted) >= 4:
                    return extracted[3]
        return None


def process_pdf_with_pymupdf(pdf_bytes: bytes, clean_mapping: Dict[str, str], mode: str = "overlay") -> bytes:
    """
    Main entry point for PyMuPDF-based PDF processing.

    Args:
        pdf_bytes: Input PDF as bytes
        clean_mapping: Dictionary of word mappings
        mode: "overlay" or "font"

    Returns:
        Modified PDF as bytes
    """
    logger = get_logger()

    if not clean_mapping:
        logger.logger.warning("No mappings provided")
        return pdf_bytes

    # Build regex pattern
    words = sorted(clean_mapping.keys(), key=len, reverse=True)
    escaped_words = [re.escape(word) for word in words]
    pattern = re.compile('|'.join(escaped_words), re.IGNORECASE)

    # Create case-folded mapping for case-insensitive matching
    mapping_cf = {key.casefold(): value for key, value in clean_mapping.items()}

    logger.logger.info(f"Processing PDF with PyMuPDF in {mode} mode")
    logger.logger.info(f"Pattern: {pattern.pattern}")

    # Create processor
    processor = PyMuPDFProcessor(pattern, clean_mapping, mapping_cf)

    if mode == "overlay":
        return processor.process_pdf_overlay_mode(pdf_bytes)
    elif mode == "font":
        return processor.process_pdf_font_mode(pdf_bytes)
    else:
        logger.logger.error(f"Unknown mode: {mode}")
        return pdf_bytes
