"""Core PDF processing utilities to support glyph remapping."""

from __future__ import annotations

import dataclasses
import io
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Optional, Pattern, Tuple

import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import ArrayObject, ContentStream, NameObject, NumberObject, TextStringObject

from .logger import get_logger
from .cross_array_processor import process_content_stream_with_cross_array_support

try:  # Optional OCR dependencies
    import pytesseract
    from pytesseract import Output as _TESS_OUTPUT
except ImportError:  # pragma: no cover - optional dependency not installed
    pytesseract = None
    _TESS_OUTPUT = None

try:  # Pillow is required for pytesseract image handling
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency not installed
    Image = None


OCR_AVAILABLE: bool = pytesseract is not None and Image is not None


WordRect = Tuple[float, float, float, float]


@dataclasses.dataclass
class OverlayTarget:
    page: int
    rect: WordRect
    image: bytes


@dataclasses.dataclass
class OCRWord:
    text: str
    norm: str
    rect: fitz.Rect
    height: float


@dataclasses.dataclass
class OCRMatch:
    rect: fitz.Rect
    replacement: str
    font_size: float


_SPACE_THRESHOLD = -120  # TJ adjustments more negative than this approximate a space.


def extract_text_preview(pdf_bytes: bytes, *, max_chars: int = 4000) -> str:
    """Return a concatenated text preview limited to ``max_chars`` characters."""
    logger = get_logger()
    
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        chunks: List[str] = []
        remaining = max_chars
        for page in doc:
            page_text = page.get_text("text")
            if not page_text:
                continue
            if len(page_text) > remaining:
                chunks.append(page_text[:remaining])
                break
            chunks.append(page_text)
            remaining -= len(page_text)
            if remaining <= 0:
                break
        
        full_text = "".join(chunks).strip()
        logger.log_text_extraction(full_text)
        return full_text
    finally:
        doc.close()


def generate_word_occurrences(pdf_bytes: bytes) -> Dict[str, List[Dict[str, object]]]:
    """Collect rectangles for each distinct word in the PDF."""

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        index: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        for page_number, page in enumerate(doc):
            for x0, y0, x1, y1, word, *_ in page.get_text("words"):
                token = word.strip()
                if not token:
                    continue
                rect: WordRect = (float(x0), float(y0), float(x1), float(y1))
                index[token].append({"page": page_number, "rect": rect})
        return index
    finally:
        doc.close()


def summarise_vocabulary(word_index: Dict[str, Iterable[Dict[str, object]]], *, top_n: int = 50) -> List[Tuple[str, int]]:
    """Return the ``top_n`` most frequent words for quick UI suggestions."""

    frequency = Counter({word: len(list(locations)) for word, locations in word_index.items()})
    return frequency.most_common(top_n)


def _build_pattern(words: Iterable[str], *, ignore_case: bool = False) -> Optional[Pattern[str]]:
    logger = get_logger()
    
    ordered = [re.escape(word) for word in sorted(set(words), key=len, reverse=True)]
    if not ordered:
        logger.log_pattern_building([], "", ignore_case)
        return None
    
    flags = re.IGNORECASE if ignore_case else 0
    pattern = re.compile("|".join(ordered), flags)
    
    logger.log_pattern_building(list(words), pattern.pattern, ignore_case)
    return pattern


def _resolve_replacement(token: str, mapping: Dict[str, str], mapping_cf: Dict[str, str]) -> Optional[str]:
    replacement = mapping.get(token)
    if replacement is not None:
        return replacement
    return mapping_cf.get(token.casefold())


def _segment_text(
    text: str,
    pattern: Pattern[str],
    mapping: Dict[str, str],
    mapping_cf: Dict[str, str],
) -> Optional[List[Tuple[str, Optional[str]]]]:
    logger = get_logger()
    
    matches = list(pattern.finditer(text))
    if not matches:
        logger.log_text_segment_analysis(text, None, "", "")
        return None
    
    segments: List[Tuple[str, Optional[str]]] = []
    last_idx = 0
    found_replacements = []
    
    for match in matches:
        start, end = match.span()
        if start > last_idx:
            segments.append((text[last_idx:start], None))
        original = match.group(0)
        replacement = _resolve_replacement(original, mapping, mapping_cf)
        segments.append((original, replacement))
        if replacement:
            found_replacements.append(f"{original}→{replacement}")
        last_idx = end
    if last_idx < len(text):
        segments.append((text[last_idx:], None))
    
    # Log detailed analysis
    if found_replacements:
        logger.log_text_segment_analysis(text, segments, "", "")
        logger.logger.info(f"Found {len(found_replacements)} replacements in text segment: {found_replacements}")
    
    return segments


def _rewrite_text(
    text: str,
    pattern: Pattern[str],
    mapping: Dict[str, str],
    mapping_cf: Dict[str, str],
) -> Optional[str]:
    logger = get_logger()
    
    segments = _segment_text(text, pattern, mapping, mapping_cf)
    if not segments:
        logger.log_replacement_attempt(text, pattern.pattern, mapping, None)
        return None
    
    rebuilt: List[str] = []
    for segment_text, replacement in segments:
        if not segment_text:
            continue
        rebuilt.append(replacement if replacement is not None else segment_text)
    
    result = "".join(rebuilt)
    logger.log_replacement_attempt(text, pattern.pattern, mapping, result)
    return result


def _array_to_text(array: ArrayObject) -> str:
    pieces: List[str] = []
    for item in array:
        if isinstance(item, TextStringObject):
            pieces.append(str(item))
        elif isinstance(item, NumberObject):
            if float(item) <= _SPACE_THRESHOLD:
                pieces.append(" ")
    return "".join(pieces)


def _collect_overlay_targets(
    pdf_bytes: bytes,
    mapping: Dict[str, str],
    mapping_cf: Dict[str, str],
) -> Tuple[List[OverlayTarget], Dict[str, str]]:
    if not mapping:
        return [], {}

    targets: List[OverlayTarget] = []
    discovered: Dict[str, str] = {}

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        for page_number, page in enumerate(doc):
            for x0, y0, x1, y1, word, *_ in page.get_text("words"):
                token = word.strip()
                if not token:
                    continue
                replacement = _resolve_replacement(token, mapping, mapping_cf)
                if replacement is None:
                    continue
                rect = (float(x0), float(y0), float(x1), float(y1))

                # Capture the ORIGINAL text as it appears in the PDF - perfect size matching
                pix = page.get_pixmap(clip=fitz.Rect(*rect), dpi=220, alpha=False)
                original_image = pix.tobytes("png")
                targets.append(OverlayTarget(page_number, rect, original_image))
                discovered.setdefault(token, replacement)
    finally:
        doc.close()

    return targets, discovered



def _apply_overlays(pdf_bytes: bytes, overlays: List[OverlayTarget]) -> bytes:
    if not overlays:
        return pdf_bytes

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        by_page: Dict[int, List[OverlayTarget]] = defaultdict(list)
        for target in overlays:
            by_page[target.page].append(target)
        for page_number, items in by_page.items():
            page = doc[page_number]
            for target in items:
                rect = fitz.Rect(*target.rect)
                page.insert_image(rect, stream=target.image, keep_proportion=False, overlay=True)
        output = io.BytesIO()
        doc.save(output, garbage=4, deflate=True)
        return output.getvalue()
    finally:
        doc.close()



def apply_word_mapping(pdf_bytes: bytes, mapping: Dict[str, str], mode: str = "overlay") -> bytes:
    """Apply the provided ``mapping`` and return the modified PDF bytes.

    Args:
        pdf_bytes: Original PDF content
        mapping: Dictionary of word mappings
        mode: Processing mode - "overlay", "font", or "ocr"
    """
    logger = get_logger()
    
    # Log input
    logger.log_input_pdf(pdf_bytes)
    logger.log_mode_selection(mode)
    logger.log_mappings(mapping)

    clean_mapping = {
        original.strip(): replacement.strip()
        for original, replacement in mapping.items()
        if original.strip() and replacement.strip()
    }
    if not clean_mapping:
        logger.logger.warning("No valid mappings provided after cleaning")
        return pdf_bytes

    logger.log_mappings(clean_mapping)

    # Route to appropriate processing mode
    try:
        if mode == "font":
            result = _apply_font_mode_mapping(pdf_bytes, clean_mapping)
        elif mode == "ocr":
            result = apply_image_ocr_mapping(pdf_bytes, clean_mapping)
        else:
            result = _apply_overlay_mode_mapping(pdf_bytes, clean_mapping)
        
        logger.log_output_pdf(result)
        logger.finalize_run()
        return result
        
    except Exception as e:
        logger.log_error(e, f"apply_word_mapping({mode})")
        logger.finalize_run()
        raise


def apply_image_overlay_mapping(pdf_bytes: bytes, mapping: Dict[str, str]) -> bytes:
    """Convenience wrapper that forces the overlay pipeline for image-heavy PDFs."""
    from .pymupdf_processor import process_pdf_with_pymupdf

    return process_pdf_with_pymupdf(pdf_bytes, mapping, mode="overlay")




def apply_image_ocr_mapping(
    pdf_bytes: bytes,
    mapping: Dict[str, str],
    *,
    dpi: int = 220,
    min_confidence: int = 60,
) -> bytes:
    """Perform OCR-driven replacements for raster-centric PDFs."""

    _ensure_ocr_dependencies()

    if not mapping:
        return pdf_bytes

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        scale = dpi / 72.0
        replacements_applied = 0

        prepared = _prepare_ocr_mappings(mapping)
        if not prepared:
            return pdf_bytes

        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            words = _extract_ocr_words(image, page.rect, scale, min_confidence)
            if not words:
                continue

            matches = _match_ocr_words(words, prepared)
            if not matches:
                continue

            for match in matches:
                page.insert_textbox(
                    match.rect,
                    match.replacement,
                    fontsize=match.font_size,
                    fontname="helv",
                    render_mode=3,
                    color=(0, 0, 0),
                    overlay=True,
                )
                replacements_applied += 1

        if replacements_applied == 0:
            return pdf_bytes

        buffer = io.BytesIO()
        doc.save(buffer, garbage=4, deflate=True)
        return buffer.getvalue()
    finally:
        doc.close()


def _ensure_ocr_dependencies() -> None:
    if not OCR_AVAILABLE:
        raise RuntimeError("pytesseract and Pillow are required for OCR-based mapping")


def _normalize_ocr_token(token: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "", token).casefold()


def _tokenize_mapping_key(key: str) -> List[str]:
    tokens = [t for t in re.findall(r"[0-9A-Za-z]+", key)]
    cleaned = [_normalize_ocr_token(t) for t in tokens if _normalize_ocr_token(t)]
    if not cleaned:
        fallback = _normalize_ocr_token(key)
        if fallback:
            cleaned = [fallback]
    return cleaned


def _prepare_ocr_mappings(mapping: Dict[str, str]) -> List[Tuple[List[str], str]]:
    prepared: List[Tuple[List[str], str]] = []
    for original, replacement in mapping.items():
        tokens = _tokenize_mapping_key(original)
        if tokens:
            prepared.append((tokens, replacement))
    return prepared


def _extract_ocr_words(image: "Image.Image", page_rect: fitz.Rect, scale: float, min_confidence: int) -> List[OCRWord]:
    if not OCR_AVAILABLE:
        return []
    data = pytesseract.image_to_data(image, output_type=_TESS_OUTPUT.DICT)  # type: ignore[arg-type]
    words: List[OCRWord] = []
    n_items = len(data.get("text", []))
    for idx in range(n_items):
        raw = data["text"][idx].strip()
        if not raw:
            continue
        try:
            conf = float(data["conf"][idx])
        except (KeyError, ValueError):
            conf = -1
        if conf < min_confidence:
            continue
        norm = _normalize_ocr_token(raw)
        if not norm:
            continue
        left = float(data["left"][idx])
        top = float(data["top"][idx])
        width = float(data["width"][idx])
        height = float(data["height"][idx])
        x0 = left / scale
        y0 = top / scale
        x1 = (left + width) / scale
        y1 = (top + height) / scale
        rect = fitz.Rect(x0, y0, x1, y1)
        rect = fitz.Rect(
            max(page_rect.x0, rect.x0),
            max(page_rect.y0, rect.y0),
            min(page_rect.x1, rect.x1),
            min(page_rect.y1, rect.y1),
        )
        words.append(
            OCRWord(
                text=raw,
                norm=norm,
                rect=rect,
                height=height / scale,
            )
        )
    return words


def _match_ocr_words(words: List[OCRWord], prepared: List[Tuple[List[str], str]]) -> List[OCRMatch]:
    matches: List[OCRMatch] = []
    used: Set[int] = set()
    norms = [word.norm for word in words]
    for tokens, replacement in prepared:
        span = len(tokens)
        if span == 0 or span > len(words):
            continue
        i = 0
        while i <= len(words) - span:
            if any(idx in used for idx in range(i, i + span)):
                i += 1
                continue
            window = norms[i : i + span]
            if window == tokens:
                rects = [words[i + offset].rect for offset in range(span)]
                union = fitz.Rect(
                    min(r.x0 for r in rects),
                    min(r.y0 for r in rects),
                    max(r.x1 for r in rects),
                    max(r.y1 for r in rects),
                )
                union = fitz.Rect(
                    union.x0 - 0.8,
                    union.y0 - 0.8,
                    union.x1 + 0.8,
                    union.y1 + 0.8,
                )
                font_size = max(8.0, sum(words[i + offset].height for offset in range(span)) / span)
                matches.append(OCRMatch(rect=union, replacement=replacement, font_size=font_size))
                used.update(range(i, i + span))
                i += span
            else:
                i += 1
    return matches


def _apply_overlay_mode_mapping(
    pdf_bytes: bytes,
    clean_mapping: Dict[str, str],
    *,
    sanitize: bool = True,
) -> bytes:
    """Apply word mapping prioritising text-layer rewrites before raster fallbacks."""

    logger = get_logger()

    overlay_mapping = _expand_mapping_variants(clean_mapping)
    mapping_cf = {key.casefold(): value for key, value in overlay_mapping.items()}
    overlays, discovered = _collect_overlay_targets(pdf_bytes, overlay_mapping, mapping_cf)
    if overlays:
        logger.logger.info("Captured %d overlay targets", len(overlays))

    rewritten = _apply_content_stream_mapping(pdf_bytes, clean_mapping)
    if rewritten is not None:
        logger.logger.info("Content stream rewrite succeeded")
        processed = _sanitize_text_layer(rewritten) if sanitize else rewritten
        if overlays:
            logger.logger.info("Re-applying %d overlays to preserve visual appearance", len(overlays))
            processed = _apply_overlays(processed, overlays)
        return processed

    logger.logger.warning("Content stream rewrite unavailable; falling back to PyMuPDF font mode")
    from .pymupdf_processor import process_pdf_with_pymupdf

    font_bytes = process_pdf_with_pymupdf(pdf_bytes, clean_mapping, mode="font")
    return _sanitize_text_layer(font_bytes) if sanitize else font_bytes


def _expand_mapping_variants(clean_mapping: Dict[str, str]) -> Dict[str, str]:
    """Return mapping augmented with space-punctuated variants for split glyph cases."""
    if not clean_mapping:
        return {}

    expanded = dict(clean_mapping)
    punctuations = [",", ";", ":", "."]
    for original, replacement in clean_mapping.items():
        for punct in punctuations:
            if punct in original:
                spaced_original = original.replace(punct, f" {punct}")
                spaced_replacement = replacement.replace(punct, f" {punct}")
                expanded.setdefault(spaced_original, spaced_replacement)
    return expanded


def _apply_content_stream_mapping(pdf_bytes: bytes, clean_mapping: Dict[str, str]) -> Optional[bytes]:
    """Attempt in-place text replacement using PyPDF2 content stream rewriting."""
    if not clean_mapping:
        return None

    logger = get_logger()
    reader = PdfReader(io.BytesIO(pdf_bytes))

    effective_mapping = _expand_mapping_variants(clean_mapping)
    pattern = _build_pattern(effective_mapping.keys(), ignore_case=True)
    if pattern is None:
        return None

    mapping_cf = {key.casefold(): value for key, value in effective_mapping.items()}

    any_modified = False
    for page_number, page in enumerate(reader.pages):
        if NameObject("/Contents") not in page:
            continue

        content = ContentStream(page[NameObject("/Contents")].get_object(), reader)
        modified_ops, page_modified = process_content_stream_with_cross_array_support(
            content.operations,
            pattern,
            effective_mapping,
            mapping_cf,
        )

        if not page_modified:
            continue

        new_stream = ContentStream(None, reader)
        new_stream.operations = modified_ops
        if hasattr(content, "forced_encoding"):
            new_stream.forced_encoding = content.forced_encoding
        page[NameObject("/Contents")] = new_stream
        any_modified = True
        logger.logger.info("Page %d updated via content stream rewrite", page_number + 1)

    if not any_modified:
        logger.logger.info("Content stream rewrite produced no changes; fallback to overlay pipeline")
        return None

    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    output = io.BytesIO()
    writer.write(output)
    logger.logger.info("Successfully applied content stream replacements without overlays")
    return output.getvalue()


def _sanitize_text_layer(pdf_bytes: bytes) -> bytes:
    """Remove null glyph placeholders and normalize text encoding."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    modified = False

    for page in reader.pages:
        if NameObject("/Contents") not in page:
            continue

        content = ContentStream(page[NameObject("/Contents")].get_object(), reader)
        new_operations = []
        page_modified = False

        for operands, operator in content.operations:
            if operator == b"Tj" and operands:
                text_obj = operands[0]
                if isinstance(text_obj, TextStringObject):
                    raw_bytes = getattr(text_obj, "original_bytes", b"")
                    if raw_bytes and set(raw_bytes) <= {0}:
                        page_modified = True
                        continue  # Drop null-only text object
            elif operator == b"TJ" and operands:
                array_obj = operands[0]
                if isinstance(array_obj, ArrayObject):
                    sanitized_array = ArrayObject()
                    array_modified = False
                    for item in array_obj:
                        if isinstance(item, TextStringObject):
                            raw_bytes = getattr(item, "original_bytes", b"")
                            if raw_bytes and set(raw_bytes) <= {0}:
                                array_modified = True
                                continue
                        sanitized_array.append(item)
                    if sanitized_array:
                        if array_modified:
                            page_modified = True
                            new_operations.append(([sanitized_array], operator))
                        else:
                            new_operations.append((operands, operator))
                        continue
                    page_modified = True
                    continue

            new_operations.append((operands, operator))

        if page_modified:
            modified = True
            sanitized_stream = ContentStream(None, reader)
            sanitized_stream.operations = new_operations
            if hasattr(content, "forced_encoding"):
                sanitized_stream.forced_encoding = content.forced_encoding
            page[NameObject("/Contents")] = sanitized_stream

    if not modified:
        return pdf_bytes

    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _apply_font_mode_mapping(pdf_bytes: bytes, clean_mapping: Dict[str, str]) -> bytes:
    """Apply word mapping using the malicious T-font pipeline with overlay fallback."""
    logger = get_logger()
    logger.logger.info("Using T-font malicious font remapping")

    try:
        from .tfont_processor import TFontError, apply_tfont_mapping

        return apply_tfont_mapping(pdf_bytes, clean_mapping)
    except Exception as e:
        logger.log_error(e, "font_mode_mapping")
        logger.logger.warning("T-font pipeline failed, reverting to overlay mode")
        return _apply_overlay_mode_mapping(pdf_bytes, clean_mapping)
