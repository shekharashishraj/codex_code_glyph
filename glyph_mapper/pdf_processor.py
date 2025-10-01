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
from .tj_array_processor_v2 import process_tj_array_with_word_replacement_v2
from .cross_array_processor import process_content_stream_with_cross_array_support


WordRect = Tuple[float, float, float, float]


@dataclasses.dataclass
class OverlayTarget:
    page: int
    rect: WordRect
    image: bytes


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
        mode: Processing mode - "overlay" or "font"
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
        else:
            result = _apply_overlay_mode_mapping(pdf_bytes, clean_mapping)
        
        logger.log_output_pdf(result)
        logger.finalize_run()
        return result
        
    except Exception as e:
        logger.log_error(e, f"apply_word_mapping({mode})")
        logger.finalize_run()
        raise




def _apply_overlay_mode_mapping(pdf_bytes: bytes, clean_mapping: Dict[str, str]) -> bytes:
    """Apply word mapping using the original overlay technique."""
    mapping_cf = {key.casefold(): value for key, value in clean_mapping.items()}
    overlays, discovered_tokens = _collect_overlay_targets(pdf_bytes, clean_mapping, mapping_cf)

    effective_mapping = dict(clean_mapping)
    effective_mapping.update(discovered_tokens)
    mapping_cf.update({key.casefold(): value for key, value in discovered_tokens.items()})

    pattern = _build_pattern(effective_mapping.keys(), ignore_case=True)
    if pattern is None:
        return pdf_bytes

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    logger = get_logger()
    modified = False

    for page_num, page in enumerate(reader.pages):
        content = ContentStream(page.get_contents(), reader)
        
        logger.logger.info(f"Processing page {page_num + 1} with {len(content.operations)} operations")

        # Use cross-array processor to replace text in content stream
        modified_operations, page_modified = process_content_stream_with_cross_array_support(
            content.operations, pattern, effective_mapping, mapping_cf
        )
        
        if page_modified:
            content.operations = modified_operations
            page[NameObject("/Contents")] = content
            modified = True
        
        writer.add_page(page)

    remapped_bytes = io.BytesIO()
    writer.write(remapped_bytes)

    return _apply_overlays(remapped_bytes.getvalue(), overlays)


def _apply_font_mode_mapping(pdf_bytes: bytes, clean_mapping: Dict[str, str]) -> bytes:
    """Apply word mapping using font-level glyph modification."""
    from .font_manipulator import (
        create_character_mapping_from_words,
        create_remapped_font,
        extract_font_from_pdf,
        embed_font_in_pdf,
        analyze_font_characters
    )
    
    # Extract or identify the primary font from the PDF
    font_path = extract_font_from_pdf(pdf_bytes)
    if not font_path:
        # Fallback to overlay mode if no font can be extracted
        return _apply_overlay_mode_mapping(pdf_bytes, clean_mapping)
    
    # Convert word mappings to character mappings
    char_mappings = create_character_mapping_from_words(clean_mapping)
    
    if not char_mappings:
        # If no character-level mappings possible, fallback to overlay mode
        return _apply_overlay_mode_mapping(pdf_bytes, clean_mapping)
    
    # Check if all required characters are available in the font
    all_chars = set(char_mappings.keys()) | set(char_mappings.values())
    char_availability = analyze_font_characters(font_path, all_chars)
    
    missing_chars = [char for char, available in char_availability.items() if not available]
    if missing_chars:
        # Some characters not available in font, fallback to overlay mode
        return _apply_overlay_mode_mapping(pdf_bytes, clean_mapping)
    
    # Create the remapped font
    try:
        remapped_font_bytes = create_remapped_font(font_path, char_mappings)
        
        # Apply text replacement in PDF content streams (same as overlay mode but without overlays)
        mapping_cf = {key.casefold(): value for key, value in clean_mapping.items()}
        pattern = _build_pattern(clean_mapping.keys(), ignore_case=True)
        
        if pattern is None:
            return pdf_bytes
        
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        
        for page in reader.pages:
            content = ContentStream(page.get_contents(), reader)
            
            # Use cross-array processor for comprehensive pattern matching
            modified_operations, page_modified = process_content_stream_with_cross_array_support(
                content.operations, pattern, clean_mapping, mapping_cf
            )
            
            if page_modified:
                content.operations = modified_operations
                page[NameObject("/Contents")] = content
            
            writer.add_page(page)
        
        remapped_bytes = io.BytesIO()
        writer.write(remapped_bytes)
        
        # Embed the custom font into the PDF
        return embed_font_in_pdf(remapped_bytes.getvalue(), remapped_font_bytes)
        
    except Exception:
        # If font manipulation fails, fallback to overlay mode
        return _apply_overlay_mode_mapping(pdf_bytes, clean_mapping)
