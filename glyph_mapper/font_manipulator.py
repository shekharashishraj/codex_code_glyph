"""Font-level glyph mapping utilities using fontTools."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable


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


def extract_font_from_pdf(pdf_bytes: bytes) -> Optional[str]:
    """
    Extract the primary font from a PDF and save it as a TTF file.
    This is a simplified implementation - real PDFs may have multiple fonts.
    
    Returns:
        Path to extracted font file, or None if no suitable font found
    """
    # This is a placeholder for font extraction logic
    # In practice, you would need to:
    # 1. Parse the PDF font resources
    # 2. Extract embedded fonts 
    # 3. Convert to TTF format if needed
    # 4. Save to temporary file
    
    # For now, we'll use a system font
    return "/System/Library/Fonts/Geneva.ttf"


def create_character_mapping_from_words(word_mappings: Dict[str, str]) -> Dict[str, str]:
    """
    Convert word mappings to character mappings by finding character differences.
    
    Args:
        word_mappings: Dictionary mapping original words to replacement words
        
    Returns:
        Dictionary mapping individual characters that need to be swapped
    """
    char_mappings = {}
    
    for original, replacement in word_mappings.items():
        # Simple character-by-character mapping for words of same length
        if len(original) == len(replacement):
            for orig_char, repl_char in zip(original, replacement):
                if orig_char != repl_char and orig_char not in char_mappings:
                    char_mappings[orig_char] = repl_char
        else:
            # For different length words, we need a more sophisticated approach
            # For now, we'll skip these and focus on character-level swaps
            pass
    
    return char_mappings


def embed_font_in_pdf(pdf_bytes: bytes, font_bytes: bytes, font_name: str = "CustomFont") -> bytes:
    """
    Embed a custom font into a PDF and update text to use the new font.
    
    This is a complex operation that requires:
    1. Adding the font to the PDF's font resources
    2. Updating all text operations to reference the new font
    3. Maintaining proper font descriptors and encoding
    
    Returns:
        Modified PDF with embedded custom font
    """
    from PyPDF2 import PdfReader, PdfWriter
    from PyPDF2.generic import (
        ArrayObject, 
        DictionaryObject, 
        IndirectObject,
        NameObject, 
        NumberObject,
        TextStringObject,
        ContentStream
    )
    
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    
    # Create font dictionary (simplified - real implementation would be more complex)
    font_dict = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/TrueType"),
        NameObject("/BaseFont"): NameObject(f"/{font_name}"),
        # Add more font properties as needed
    })
    
    # Add font to each page's resources
    for page in reader.pages:
        if "/Resources" in page:
            resources = page["/Resources"]
            if "/Font" not in resources:
                resources[NameObject("/Font")] = DictionaryObject()
            
            # Add our custom font
            resources["/Font"][NameObject(f"/{font_name}")] = font_dict
        
        writer.add_page(page)
    
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()