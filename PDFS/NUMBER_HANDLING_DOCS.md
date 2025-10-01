# Number Handling in Cross-Array PDF Processing

## Overview

This document describes the comprehensive approach to handling number substitutions that span multiple TJ (text) operations in PDF content streams.

## Problem Statement

PDF files can split decimal numbers across multiple TJ array operations, making simple text replacement insufficient. For example:

**Input PDF Structure:**
```
TJ Array 1: ['=', '0']
TJ Array 2: ['9:', 'Will', 'gradient', ...]
```

**Expected Pattern:** `0.9:` → `9.0:`

## Solution Architecture

### Multi-Phase Processing

1. **Phase 1: V2 Single-Array Processing**
   - Handles patterns within individual TJ arrays
   - Manages ligature conversion (`\x0c` → `fi`)
   - Applies proportional text distribution

2. **Phase 2: Cross-Array Pattern Detection**
   - Uses sliding window approach across consecutive TJ operations
   - Builds combined text representation from multiple arrays
   - Detects split decimal patterns using regex

3. **Phase 3: Cross-Array Replacement**
   - Modifies multiple TJ arrays to implement the replacement
   - Preserves PDF structure while applying text changes

### Key Components

#### CrossArrayProcessor Class

Located in `glyph_mapper/cross_array_processor.py`

**Primary Methods:**
- `process_content_operations()`: Main entry point for cross-array processing
- `_find_cross_array_matches()`: Detects patterns spanning multiple arrays
- `_apply_cross_array_replacement()`: Implements replacements across arrays

#### Pattern Detection Strategy

```python
# Window text building from multiple TJ operations
def _build_window_text(self, window_operations):
    text_parts = []
    for _, array_obj in window_operations:
        array_text = self._extract_array_text(array_obj)
        if array_text:
            text_parts.append(array_text)
    return ' '.join(text_parts)

# Split decimal pattern detection
split_decimal_patterns = [
    r'(?:=\s*)?(\d)\s+(\d+):',  # Matches "= 0 9:" or "0 9:"
    r'(?:=\s*)?(\d)\s*(\d+):',  # Matches "= 09:" or "09:"
]
```

#### Replacement Implementation

For decimal number patterns like "0.9:" → "9.0:":

1. **First Array Modification:**
   - Replace first digit: "0" → "9"
   - `['=', '0']` → `['=', '9']`

2. **Second Array Modification:**
   - Add decimal point and replace: "9:" → ".0:"
   - `['9:', 'Will']` → `['.0:', 'Will']`

## Test Cases and Results

### Working Cases ✅

1. **Basic Cross-Array Decimal (0.9:)**
   ```
   Input:  ['=', '0'] + ['9:', 'Will']
   Output: ['=', '9'] + ['.0:', 'Will']
   Result: '=9.0:Will' ✅
   ```

2. **Single Array Decimal (Control)**
   ```
   Input:  ['The', 'value', '0.9:', 'shows']
   Output: ['The', 'value', '9.0:', 'shows']
   Result: 'Thevalue9.0:shows' ✅
   ```

### Partial Cases ⚠️

1. **Complex Cross-Array Decimal (1.2:)**
   ```
   Input:  ['If', '∥Wh∥=', '1'] + ['2:', 'Will', 'gradients']
   Output: ['If', '∥Wh∥=', '0'] + ['.2:', 'Will', 'gradients']
   Result: 'If∥Wh∥=0..2:Willgradients' ⚠️
   ```
   *Issue: Double decimal point in output*

### Not Yet Implemented ❌

1. **Three-Way Split Numbers**
   ```
   Input: ['value', '0'] + ['.'] + ['5', 'percent']
   Target: Handle patterns split across 3+ arrays
   ```

## Implementation Integration

### PDF Processor Integration

The cross-array processor is integrated into the main PDF processing pipeline in `glyph_mapper/pdf_processor.py`:

```python
# Use cross-array processor for comprehensive pattern matching
modified_operations, page_modified = process_content_stream_with_cross_array_support(
    content.operations, pattern, effective_mapping, mapping_cf
)
```

### Processing Flow

1. **Input:** PDF with word mappings (e.g., `{'0.9:': '9.0:', '1.2:': '0.2:'}`)
2. **Pattern Compilation:** Build regex patterns from mappings
3. **Page Processing:** For each page's content stream:
   - Apply V2 processor to individual TJ arrays
   - Apply cross-array processor for spanning patterns
   - Update content stream with modifications
4. **Output:** Modified PDF with number substitutions applied

## Performance Considerations

- **Window Size:** Currently set to 3 consecutive TJ operations
- **Pattern Caching:** Regex patterns compiled once per processing run
- **Early Termination:** Skip processing when no patterns are detected

## Known Limitations

1. **Double Decimal Issue:** Some complex cases may produce double decimal points
2. **Three-Array Splits:** Not yet implemented for patterns spanning 3+ arrays
3. **Character Spacing:** May affect fine-tuned character positioning in some cases

## Future Enhancements

1. **Resolve Double Decimal Issue:** Improve replacement logic for complex cases
2. **Extended Window Support:** Handle patterns spanning more than 2 arrays
3. **Spacing Preservation:** Better maintain original character spacing
4. **Pattern Optimization:** More efficient pattern matching for large documents

## Usage Examples

```python
from glyph_mapper.pdf_processor import apply_word_mapping

# Apply number substitutions
pdf_bytes = Path('document.pdf').read_bytes()
remapped = apply_word_mapping(pdf_bytes, {
    '0.9:': '9.0:',
    '1.2:': '0.2:',
    '2.5': '5.2'
})
Path('output.pdf').write_bytes(remapped)
```

## Testing

Run comprehensive tests with:
```bash
python3 test_number_substitutions.py
python3 debug_cross_array.py
```

This implementation successfully handles the majority of cross-array decimal number cases encountered in PDF documents while maintaining the original document structure and formatting.