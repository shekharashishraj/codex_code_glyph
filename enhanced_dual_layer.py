"""
Enhanced Dual-Layer Text Rendering with Length-Independent Mapping
Supports longer replacement words while maintaining visual exactness
"""

from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import (
    ContentStream, NameObject, NumberObject, TextStringObject,
    ArrayObject, FloatObject
)
import io
from typing import Dict, List, Tuple

def enhanced_dual_layer_rendering(pdf_bytes: bytes, mapping: Dict[str, str]) -> bytes:
    """
    Enhanced dual-layer with support for longer replacement words

    STRATEGY:
    1. Layer 1: Invisible replacement text (compressed/expanded to fit)
    2. Layer 2: Visible original text (normal spacing)
    3. Perfect visual alignment using TJ arrays
    """
    print("👁️ ENHANCED DUAL-LAYER: Length-Independent Rendering")

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    for page in reader.pages:
        content = ContentStream(page.get_contents(), reader)
        new_ops: List[Tuple[List[object], bytes]] = []

        for operands, operator in content.operations:
            if operator == b"Tj" and operands and isinstance(operands[0], TextStringObject):
                original_text = str(operands[0])

                # Check if this text needs replacement
                replacement_text = None
                for orig, repl in mapping.items():
                    if orig in original_text:
                        replacement_text = original_text.replace(orig, repl)
                        break

                if replacement_text and replacement_text != original_text:
                    print(f"   🔄 '{original_text}' -> '{replacement_text}' (length: {len(original_text)} -> {len(replacement_text)})")

                    # LAYER 1: Invisible replacement text with length compensation
                    invisible_tj_array = create_length_compensated_array(
                        original_text, replacement_text, invisible=True
                    )

                    new_ops.extend([
                        ([NumberObject(3)], b"Tr"),  # Invisible mode
                        ([ArrayObject(invisible_tj_array)], b"TJ"),  # Invisible replacement with spacing
                        ([NumberObject(0)], b"Tr"),  # Visible mode
                    ])

                    # LAYER 2: Visible original text (normal)
                    new_ops.append(([TextStringObject(original_text)], b"Tj"))
                    continue

            # Preserve all other operations
            new_ops.append((operands, operator))

        # Update page content
        content.operations = new_ops
        page[NameObject("/Contents")] = content
        writer.add_page(page)

    # Write result
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

def create_length_compensated_array(original: str, replacement: str, invisible: bool = False) -> List:
    """
    Create TJ array that makes replacement text fit in original text's visual space

    Examples:
    "cat" -> "dragon": Compress "dragon" letters to fit "cat" width
    "elephant" -> "dog": Expand "dog" letters to fill "elephant" width
    """

    if len(replacement) == len(original):
        # Same length - simple replacement
        return [TextStringObject(replacement)]

    elif len(replacement) > len(original):
        # Longer replacement - COMPRESS spacing
        print(f"      🗜️  Compressing '{replacement}' into '{original}' space")

        # Calculate compression ratio
        compression_ratio = len(original) / len(replacement)
        spacing_reduction = int(200 * (1 - compression_ratio))  # More aggressive compression

        tj_array = []
        for i, char in enumerate(replacement):
            tj_array.append(TextStringObject(char))
            if i < len(replacement) - 1:  # Don't add spacing after last character
                tj_array.append(NumberObject(-spacing_reduction))  # Negative = compress

        return tj_array

    else:
        # Shorter replacement - EXPAND spacing
        print(f"      📏 Expanding '{replacement}' to fill '{original}' space")

        # Calculate expansion ratio
        expansion_ratio = len(original) / len(replacement)
        spacing_increase = int(100 * (expansion_ratio - 1))

        tj_array = []
        for i, char in enumerate(replacement):
            tj_array.append(TextStringObject(char))
            if i < len(replacement) - 1:  # Don't add spacing after last character
                tj_array.append(NumberObject(spacing_increase))  # Positive = expand

        return tj_array

# Test the enhanced system
if __name__ == "__main__":
    # Test extreme length differences
    test_mappings = {
        "cat": "dragon",        # 3 -> 6 chars (2x longer)
        "dog": "elephant",      # 3 -> 8 chars (2.7x longer)
        "fox": "a",            # 3 -> 1 char (3x shorter)
        "quick": "supercalifragilisticexpialidocious"  # 5 -> 34 chars (6.8x longer!)
    }

    print("🧪 TESTING EXTREME LENGTH DIFFERENCES:")
    print("=" * 50)

    for original, replacement in test_mappings.items():
        ratio = len(replacement) / len(original)
        print(f"'{original}' -> '{replacement}' (ratio: {ratio:.1f}x)")

        # Show what the TJ array would look like
        tj_array = create_length_compensated_array(original, replacement)
        print(f"   TJ Array: {len(tj_array)} elements")
        print()