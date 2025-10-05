"""TrueType font remapping pipeline implementing the malicious font method."""

from __future__ import annotations

import io
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import (
    ArrayObject,
    ContentStream,
    DecodedStreamObject,
    NameObject,
    NumberObject,
    TextStringObject,
)
from fontTools.ttLib import TTFont

from .logger import get_logger
from .pdf_processor import _array_to_text, _build_pattern, _segment_text


CharMapping = Dict[str, str]
FontCharMappings = Dict[str, CharMapping]


class TFontError(RuntimeError):
    """Raised when the T-font pipeline cannot safely apply replacements."""


def _remap_font_bytes(font_bytes: bytes, char_mappings: CharMapping) -> bytes:
    """Return new font bytes with cmap entries remapped."""
    if not char_mappings:
        return font_bytes

    font = TTFont(io.BytesIO(font_bytes))
    cmap = font.get("cmap")
    if cmap is None:
        raise TFontError("Font lacks cmap table")

    target_tables = [
        table for table in cmap.tables if table.platformID == 3 and table.platEncID in (1, 10)
    ]
    if not target_tables:
        raise TFontError("Font does not expose a Unicode cmap for remapping")

    for replacement_char, original_char in char_mappings.items():
        if len(replacement_char) != 1 or len(original_char) != 1:
            raise TFontError("Only single-character mappings are supported")
        original_code = ord(original_char)
        replacement_code = ord(replacement_char)

        mapped = False
        for table in target_tables:
            glyph_name = table.cmap.get(original_code)
            if not glyph_name:
                continue
            table.cmap[replacement_code] = glyph_name
            mapped = True
        if not mapped:
            raise TFontError(
                f"Glyph for original character {repr(original_char)} not present in font"
            )

    output = io.BytesIO()
    font.save(output)
    return output.getvalue()


def _register_char_mappings(
    font_maps: FontCharMappings,
    font_name: str,
    originals: str,
    replacements: str,
) -> None:
    """Record per-character mappings for a font, ensuring consistency."""
    if len(originals) != len(replacements):
        raise TFontError("Replacement tokens must preserve length for T-font mode")

    mapping = font_maps.setdefault(font_name, {})
    for original_char, replacement_char in zip(originals, replacements):
        existing = mapping.get(replacement_char)
        if existing and existing != original_char:
            raise TFontError(
                f"Conflicting mapping for character {repr(replacement_char)}:"
                f" {repr(existing)} vs {repr(original_char)}"
            )
        mapping[replacement_char] = original_char


def _update_page_content(
    page,
    reader: PdfReader,
    pattern,
    mapping: Dict[str, str],
    mapping_cf: Dict[str, str],
    font_maps: FontCharMappings,
) -> bool:
    """Rewrite text operators on a page and capture char mappings."""
    logger = get_logger()
    if "/Contents" not in page:
        return False

    content = ContentStream(page[NameObject("/Contents")].get_object(), reader)
    new_operations: List[Tuple[List, bytes]] = []
    current_font: Optional[str] = None
    modified = False

    for operands, operator in content.operations:
        if operator == b"Tf" and operands:
            font_operand = operands[0]
            current_font = str(font_operand) if isinstance(font_operand, NameObject) else None
            new_operations.append((operands, operator))
            continue

        if operator == b"Tj" and operands:
            text_obj = operands[0]
            original_text = str(text_obj)
            segments = _segment_text(original_text, pattern, mapping, mapping_cf)
            if not segments:
                new_operations.append((operands, operator))
                continue

            replacement_parts: List[str] = []
            try:
                for segment_text, replacement in segments:
                    if not segment_text:
                        continue
                    if replacement is None:
                        replacement_parts.append(segment_text)
                        continue
                    replacement_parts.append(replacement)
                    if current_font is None:
                        raise TFontError("Text replacement occurs outside of a font context")
                    _register_char_mappings(font_maps, current_font, segment_text, replacement)
            except TFontError:
                # Propagate upwards to trigger fallback
                raise

            rewritten_text = "".join(replacement_parts)
            if rewritten_text != original_text:
                new_operations.append(([TextStringObject(rewritten_text)], operator))
                modified = True
            else:
                new_operations.append((operands, operator))
            continue

        if operator == b"TJ" and operands:
            array_obj = operands[0]
            if not isinstance(array_obj, ArrayObject):
                new_operations.append((operands, operator))
                continue

            combined = _array_to_text(array_obj)
            segments = _segment_text(combined, pattern, mapping, mapping_cf)
            if not segments:
                new_operations.append((operands, operator))
                continue

            try:
                rewritten_combined: List[str] = []
                for segment_text, replacement in segments:
                    if not segment_text:
                        continue
                    if replacement is None:
                        rewritten_combined.append(segment_text)
                        continue
                    rewritten_combined.append(replacement)
                    if current_font is None:
                        raise TFontError("Text replacement occurs outside of a font context")
                    _register_char_mappings(font_maps, current_font, segment_text, replacement)

                rewritten_text = "".join(rewritten_combined)
            except TFontError:
                raise

            if rewritten_text == combined:
                new_operations.append((operands, operator))
                continue

            # Rebuild the array by replacing text objects inline while preserving numbers
            new_array = ArrayObject()
            text_cursor = 0
            for item in array_obj:
                if isinstance(item, TextStringObject):
                    segment = str(item)
                    length = len(segment)
                    replacement_slice = rewritten_text[text_cursor : text_cursor + length]
                    text_cursor += length
                    new_array.append(TextStringObject(replacement_slice))
                else:
                    new_array.append(item)
            new_operations.append(([new_array], operator))
            modified = True
            continue

        new_operations.append((operands, operator))

    if modified:
        new_content = ContentStream(None, reader)
        new_content.operations = new_operations
        page[NameObject("/Contents")] = new_content
        logger.logger.info("Updated content stream with malicious font mappings")

    return modified


def _materialise(font_maps: FontCharMappings, reader: PdfReader) -> None:
    """Apply recorded char mappings to embedded fonts in the PDF."""
    logger = get_logger()
    if not font_maps:
        return

    for page in reader.pages:
        res_obj = page.get(NameObject("/Resources"))
        resources = res_obj.get_object() if hasattr(res_obj, 'get_object') else res_obj
        if not resources or NameObject("/Font") not in resources:
            continue

        fonts_ref = resources[NameObject("/Font")]
        fonts_dict = fonts_ref.get_object() if hasattr(fonts_ref, 'get_object') else fonts_ref

        for font_name_obj, font_ref in fonts_dict.items():
            font_name = str(font_name_obj)
            if font_name not in font_maps:
                continue

            font_obj = font_ref.get_object() if hasattr(font_ref, 'get_object') else font_ref
            descriptor_ref = font_obj.get(NameObject("/FontDescriptor")) if font_obj else None
            descriptor = descriptor_ref.get_object() if hasattr(descriptor_ref, 'get_object') else descriptor_ref
            if not descriptor:
                raise TFontError(f"Font {font_name} lacks a descriptor for embedding")

            storage_key = None
            for key in (NameObject("/FontFile2"), NameObject("/FontFile")):
                if key in descriptor:
                    storage_key = key
                    break
            if storage_key is None or storage_key == NameObject("/FontFile"):
                raise TFontError(f"Font {font_name} is not a TrueType font and cannot be remapped")

            font_stream_ref = descriptor[storage_key]
            font_stream = font_stream_ref.get_object() if hasattr(font_stream_ref, 'get_object') else font_stream_ref
            font_bytes = font_stream.get_data()
            remapped_bytes = _remap_font_bytes(font_bytes, font_maps[font_name])

            new_stream = DecodedStreamObject()
            new_stream.set_data(remapped_bytes)
            new_stream.update({NameObject("/Length"): NumberObject(len(remapped_bytes))})
            descriptor[storage_key] = new_stream
            logger.logger.info(
                "Applied malicious cmap remapping to font %s (%d entries)",
                font_name,
                len(font_maps[font_name]),
            )



def apply_tfont_mapping(pdf_bytes: bytes, mapping: Dict[str, str]) -> bytes:
    """Apply the malicious font technique across the PDF."""
    logger = get_logger()
    if not mapping:
        return pdf_bytes

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pattern = _build_pattern(mapping.keys(), ignore_case=True)
    if pattern is None:
        return pdf_bytes

    mapping_cf = {key.casefold(): value for key, value in mapping.items()}
    font_maps: FontCharMappings = defaultdict(dict)
    any_modified = False

    try:
        for page_number, page in enumerate(reader.pages):
            page_modified = _update_page_content(
                page,
                reader,
                pattern,
                mapping,
                mapping_cf,
                font_maps,
            )
            if page_modified:
                any_modified = True
                logger.logger.info("Page %d updated for T-font mode", page_number + 1)

        if not any_modified:
            logger.logger.info("No applicable text found for T-font remapping")
            return pdf_bytes

        _materialise(font_maps, reader)

    except TFontError as exc:
        logger.log_error(exc, "apply_tfont_mapping")
        raise

    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
