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


WordRect = Tuple[float, float, float, float]


@dataclasses.dataclass
class OverlayTarget:
    page: int
    rect: WordRect
    image: bytes


_SPACE_THRESHOLD = -120  # TJ adjustments more negative than this approximate a space.


def extract_text_preview(pdf_bytes: bytes, *, max_chars: int = 4000) -> str:
    """Return a concatenated text preview limited to ``max_chars`` characters."""

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
        return "".join(chunks).strip()
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
    ordered = [re.escape(word) for word in sorted(set(words), key=len, reverse=True)]
    if not ordered:
        return None
    flags = re.IGNORECASE if ignore_case else 0
    return re.compile("|".join(ordered), flags)


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
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    segments: List[Tuple[str, Optional[str]]] = []
    last_idx = 0
    for match in matches:
        start, end = match.span()
        if start > last_idx:
            segments.append((text[last_idx:start], None))
        original = match.group(0)
        replacement = _resolve_replacement(original, mapping, mapping_cf)
        segments.append((original, replacement))
        last_idx = end
    if last_idx < len(text):
        segments.append((text[last_idx:], None))
    return segments


def _rewrite_text(
    text: str,
    pattern: Pattern[str],
    mapping: Dict[str, str],
    mapping_cf: Dict[str, str],
) -> Optional[str]:
    segments = _segment_text(text, pattern, mapping, mapping_cf)
    if not segments:
        return None
    rebuilt: List[str] = []
    for segment_text, replacement in segments:
        if not segment_text:
            continue
        rebuilt.append(replacement if replacement is not None else segment_text)
    return "".join(rebuilt)


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
                pix = page.get_pixmap(clip=fitz.Rect(*rect), dpi=220, alpha=False)
                targets.append(OverlayTarget(page_number, rect, pix.tobytes("png")))
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


def apply_word_mapping(pdf_bytes: bytes, mapping: Dict[str, str]) -> bytes:
    """Apply the provided ``mapping`` and return the modified PDF bytes."""

    clean_mapping = {
        original.strip(): replacement.strip()
        for original, replacement in mapping.items()
        if original.strip() and replacement.strip()
    }
    if not clean_mapping:
        return pdf_bytes

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

    for page in reader.pages:
        content = ContentStream(page.get_contents(), reader)
        new_ops: List[Tuple[List[object], bytes]] = []
        modified = False

        for operands, operator in content.operations:
            if operator == b"Tj" and operands:
                text_obj = operands[0]
                if isinstance(text_obj, TextStringObject):
                    rewritten = _rewrite_text(str(text_obj), pattern, effective_mapping, mapping_cf)
                    if rewritten is not None:
                        modified = True
                        new_ops.append(([TextStringObject(rewritten)], b"Tj"))
                        continue

            if operator == b"TJ" and operands:
                array_obj = operands[0]
                if isinstance(array_obj, ArrayObject):
                    combined = _array_to_text(array_obj)
                    rewritten_full = _rewrite_text(combined, pattern, effective_mapping, mapping_cf)
                    if rewritten_full is not None:
                        modified = True
                        new_ops.append(([ArrayObject([TextStringObject(rewritten_full)])], b"TJ"))
                        continue
            new_ops.append((operands, operator))

        if modified:
            content.operations = new_ops
            page[NameObject("/Contents")] = content
        writer.add_page(page)

    remapped_bytes = io.BytesIO()
    writer.write(remapped_bytes)

    return _apply_overlays(remapped_bytes.getvalue(), overlays)
