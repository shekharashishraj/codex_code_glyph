"""Font-level glyph mapping utilities using fontTools."""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from PyPDF2 import PdfReader
from PyPDF2.generic import DictionaryObject, NameObject, StreamObject

from .logger import get_logger


def create_remapped_font(font_path: str, char_mappings: Dict[str, str]) -> bytes:
    """
    Create a new font with remapped character glyphs.
    
    Args:
        font_path: Path to the source TTF font file
        char_mappings: Dictionary mapping original characters to replacement characters
        
    Returns:
        Modified font as bytes
    """
    font = TTFont(font_path)
    
    # Get the character map table
    cmap = font['cmap']
    
    # Find the Unicode BMP subtable (Platform ID 3, Encoding ID 1)
    unicode_cmap = None
    for table in cmap.tables:
        if table.platformID == 3 and table.platEncID == 1:
            unicode_cmap = table
            break
    
    if unicode_cmap is None:
        raise ValueError("No Unicode BMP character map found in font")
    
    # Create mappings between Unicode code points
    code_point_mappings = {}
    for orig_char, repl_char in char_mappings.items():
        if len(orig_char) == 1 and len(repl_char) == 1:
            orig_code = ord(orig_char)
            repl_code = ord(repl_char)
            code_point_mappings[orig_code] = repl_code
    
    # Get glyph names for the characters we want to swap
    glyph_swaps = {}
    for orig_code, repl_code in code_point_mappings.items():
        orig_glyph = unicode_cmap.cmap.get(orig_code)
        repl_glyph = unicode_cmap.cmap.get(repl_code)
        
        if orig_glyph and repl_glyph:
            glyph_swaps[orig_code] = repl_glyph
    
    # Apply the glyph swaps to the character map
    for orig_code, new_glyph in glyph_swaps.items():
        unicode_cmap.cmap[orig_code] = new_glyph
    
    # Save the modified font to bytes
    output = io.BytesIO()
    font.save(output)
    return output.getvalue()


def analyze_font_characters(font_path: str, characters: Set[str]) -> Dict[str, bool]:
    """
    Analyze which characters are available in the font.
    
    Args:
        font_path: Path to the TTF font file
        characters: Set of characters to check
        
    Returns:
        Dictionary mapping characters to their availability in the font
    """
    font = TTFont(font_path)
    
    # Get the character map table
    cmap = font['cmap']
    
    # Find the Unicode BMP subtable
    unicode_cmap = None
    for table in cmap.tables:
        if table.platformID == 3 and table.platEncID == 1:
            unicode_cmap = table
            break
    
    if unicode_cmap is None:
        return {char: False for char in characters}
    
    # Check availability of each character
    availability = {}
    for char in characters:
        if len(char) == 1:
            code_point = ord(char)
            availability[char] = code_point in unicode_cmap.cmap
        else:
            availability[char] = False
    
    return availability


def get_available_fonts() -> Dict[str, str]:
    """
    Get a dictionary of available fonts with their paths.
    Returns fonts in priority order: DejaVuSans, Arial, Times New Roman, fallback.
    """
    fonts = {}

    # Project fonts
    project_fonts_dir = Path(__file__).parent.parent / "fonts"
    if (project_fonts_dir / "DejaVuSans.ttf").exists():
        fonts['DejaVuSans'] = str(project_fonts_dir / "DejaVuSans.ttf")

    # System fonts
    system_fonts = {
        'Arial': "/System/Library/Fonts/Supplemental/Arial.ttf",
        'TimesNewRoman': "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        'Helvetica': "/System/Library/Fonts/Helvetica.ttc",
        'Geneva': "/System/Library/Fonts/Geneva.ttf"
    }

    for name, path in system_fonts.items():
        if os.path.exists(path):
            fonts[name] = path

    return fonts


def extract_font_info_from_pdf(pdf_bytes: bytes) -> Dict[str, any]:
    """
    Extract font information from PDF to understand what fonts are used.

    Returns:
        Dictionary with font information including names and types
    """
    logger = get_logger()
    reader = PdfReader(io.BytesIO(pdf_bytes))

    font_info = {
        'fonts': [],
        'has_embedded_fonts': False,
        'font_names': set()
    }

    try:
        for page in reader.pages:
            if '/Resources' in page and '/Font' in page['/Resources']:
                fonts_dict = page['/Resources']['/Font']

                for font_key, font_obj in fonts_dict.items():
                    if isinstance(font_obj, DictionaryObject):
                        font_data = {
                            'key': str(font_key),
                            'subtype': str(font_obj.get('/Subtype', '')),
                            'basefont': str(font_obj.get('/BaseFont', ''))
                        }

                        # Check if font is embedded
                        if '/FontDescriptor' in font_obj:
                            font_data['embedded'] = True
                            font_info['has_embedded_fonts'] = True

                        font_info['fonts'].append(font_data)
                        font_info['font_names'].add(font_data['basefont'])

                break  # Only check first page for performance

        logger.logger.info(f"Found {len(font_info['fonts'])} fonts in PDF: {font_info['font_names']}")
    except Exception as e:
        logger.log_error(e, "extract_font_info_from_pdf")

    return font_info


def select_best_font_for_pdf(pdf_bytes: bytes) -> str:
    """
    Select the best font to use for remapping based on PDF analysis.
    Priority: DejaVuSans > Arial > Times New Roman > Geneva (fallback)

    Returns:
        Path to the selected font file
    """
    logger = get_logger()
    available_fonts = get_available_fonts()

    # Extract font info from PDF
    pdf_font_info = extract_font_info_from_pdf(pdf_bytes)

    # Priority order
    priority_order = ['DejaVuSans', 'Arial', 'TimesNewRoman', 'Helvetica', 'Geneva']

    # Try to match PDF fonts with available fonts
    pdf_font_names_lower = {name.lower() for name in pdf_font_info['font_names']}
    for pdf_font in pdf_font_names_lower:
        for available_name, available_path in available_fonts.items():
            if available_name.lower() in pdf_font or pdf_font in available_name.lower():
                logger.logger.info(f"Matched PDF font '{pdf_font}' with '{available_name}'")
                return available_path

    # Fall back to priority order
    for font_name in priority_order:
        if font_name in available_fonts:
            logger.logger.info(f"Using fallback font: {font_name}")
            return available_fonts[font_name]

    # Ultimate fallback
    if available_fonts:
        fallback = list(available_fonts.values())[0]
        logger.logger.warning(f"Using ultimate fallback font: {fallback}")
        return fallback

    raise RuntimeError("No suitable fonts found on system")


def create_character_mapping_from_words(word_mappings: Dict[str, str]) -> Dict[str, str]:
    """
    Convert word mappings to character mappings by analyzing character frequency.
    Uses intelligent heuristics to handle different-length words.

    Args:
        word_mappings: Dictionary mapping original words to replacement words

    Returns:
        Dictionary mapping individual characters that need to be swapped
    """
    logger = get_logger()
    char_mappings = {}

    for original, replacement in word_mappings.items():
        orig_lower = original.lower()
        repl_lower = replacement.lower()

        if len(original) == len(replacement):
            # Same length: direct character mapping
            for orig_char, repl_char in zip(original, replacement):
                if orig_char != repl_char:
                    # Avoid conflicts: only map if not already mapped
                    if orig_char not in char_mappings:
                        char_mappings[orig_char] = repl_char
                    elif char_mappings[orig_char] != repl_char:
                        logger.logger.warning(
                            f"Conflicting mapping for '{orig_char}': "
                            f"'{char_mappings[orig_char]}' vs '{repl_char}'"
                        )
        else:
            # Different lengths: find character substitutions using simple heuristic
            # Map unique characters that appear in original but not in replacement
            orig_chars = set(original)
            repl_chars = set(replacement)

            # Find characters that only appear in one word
            only_in_orig = orig_chars - repl_chars
            only_in_repl = repl_chars - orig_chars

            # Create mappings for unique characters if counts match
            if len(only_in_orig) == len(only_in_repl) and len(only_in_orig) > 0:
                for orig_char, repl_char in zip(sorted(only_in_orig), sorted(only_in_repl)):
                    if orig_char not in char_mappings:
                        char_mappings[orig_char] = repl_char
                        logger.logger.debug(f"Inferred mapping: '{orig_char}' → '{repl_char}'")

    logger.logger.info(f"Created {len(char_mappings)} character mappings from {len(word_mappings)} word mappings")
    return char_mappings


def create_font_descriptor(font_path: str, font_name: str) -> DictionaryObject:
    """
    Create a font descriptor dictionary for PDF font embedding.

    Args:
        font_path: Path to the TTF font file
        font_name: Name for the font

    Returns:
        DictionaryObject containing font descriptor
    """
    from PyPDF2.generic import NumberObject, ArrayObject

    # Load font to extract metrics
    font = TTFont(font_path)

    # Get font metrics from head and OS/2 tables
    head_table = font['head']
    os2_table = font.get('OS/2')
    post_table = font.get('post')

    # Font bounding box
    bbox = [
        int(head_table.xMin),
        int(head_table.yMin),
        int(head_table.xMax),
        int(head_table.yMax)
    ]

    # Create font descriptor
    descriptor = DictionaryObject({
        NameObject("/Type"): NameObject("/FontDescriptor"),
        NameObject("/FontName"): NameObject(f"/{font_name}"),
        NameObject("/Flags"): NumberObject(32),  # Symbolic font
        NameObject("/FontBBox"): ArrayObject([NumberObject(x) for x in bbox]),
        NameObject("/ItalicAngle"): NumberObject(int(post_table.italicAngle) if post_table else 0),
        NameObject("/Ascent"): NumberObject(int(os2_table.sTypoAscender) if os2_table else 1000),
        NameObject("/Descent"): NumberObject(int(os2_table.sTypoDescender) if os2_table else -200),
        NameObject("/CapHeight"): NumberObject(int(os2_table.sCapHeight) if os2_table and hasattr(os2_table, 'sCapHeight') else 700),
        NameObject("/StemV"): NumberObject(80),  # Approximate stem width
    })

    return descriptor


def embed_font_in_pdf(pdf_bytes: bytes, remapped_font_path: str, char_mappings: Dict[str, str]) -> bytes:
    """
    Embed a custom remapped font into PDF and replace original fonts.
    Preserves all non-text content including images, annotations, etc.

    Args:
        pdf_bytes: Original PDF bytes
        remapped_font_path: Path to the remapped TTF font file
        char_mappings: Character mappings that were applied

    Returns:
        Modified PDF with embedded remapped font
    """
    from PyPDF2 import PdfReader, PdfWriter
    from PyPDF2.generic import (
        ArrayObject,
        DictionaryObject,
        NumberObject,
        StreamObject
    )

    logger = get_logger()
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    # Read font file
    with open(remapped_font_path, 'rb') as f:
        font_file_bytes = f.read()

    font_name = "RemappedFont"

    logger.logger.info(f"Embedding font '{font_name}' into PDF")

    # Create font file stream
    font_stream = StreamObject()
    font_stream._data = font_file_bytes
    font_stream.update({
        NameObject("/Length"): NumberObject(len(font_file_bytes)),
        NameObject("/Length1"): NumberObject(len(font_file_bytes)),
    })

    # Create font descriptor
    descriptor = create_font_descriptor(remapped_font_path, font_name)
    descriptor[NameObject("/FontFile2")] = font_stream

    # Create font dictionary
    font_dict = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/TrueType"),
        NameObject("/BaseFont"): NameObject(f"/{font_name}"),
        NameObject("/FontDescriptor"): descriptor,
        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    })

    # Process each page, preserving ALL content
    for page_num, page in enumerate(reader.pages):
        # Ensure resources exist
        if "/Resources" not in page:
            page[NameObject("/Resources")] = DictionaryObject()

        resources = page["/Resources"]

        # Ensure Font resources exist
        if "/Font" not in resources:
            resources[NameObject("/Font")] = DictionaryObject()

        # Replace ALL fonts with our remapped font
        # This ensures uniform rendering with the character mappings applied
        font_resources = resources["/Font"]

        # Get existing font keys
        existing_fonts = list(font_resources.keys())

        # Replace first font or add new one
        if existing_fonts:
            # Replace the first font (usually F1 or similar)
            primary_font_key = existing_fonts[0]
            font_resources[primary_font_key] = font_dict
            logger.logger.debug(f"Page {page_num + 1}: Replaced font '{primary_font_key}' with remapped font")
        else:
            # No existing fonts, add as F1
            font_resources[NameObject("/F1")] = font_dict
            logger.logger.debug(f"Page {page_num + 1}: Added remapped font as /F1")

        # Preserve ALL page content: images, annotations, metadata, etc.
        # PyPDF2 automatically preserves these when we add the page
        writer.add_page(page)

    # Write output
    output = io.BytesIO()
    writer.write(output)
    logger.logger.info(f"Successfully embedded font into PDF ({len(output.getvalue())} bytes)")
    return output.getvalue()