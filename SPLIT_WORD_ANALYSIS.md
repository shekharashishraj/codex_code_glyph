# TJ Array Split-Word Problem Analysis

## Problem Statement

PDF text is often stored in TJ arrays where individual words can be split across multiple text elements, making word replacement impossible with element-by-element processing.

## Root Cause Analysis

### Example from QZ7_latex.pdf:
```
TJ array texts: ['Ov', 'er\x0ctting']
```

The word "Overfitting" is split into:
- `"Ov"` 
- `"er\x0ctting"` (with form feed character `\x0c`)

### Current Algorithm Limitation:
```python
for item in array_obj:
    if isinstance(item, TextStringObject):
        text_str = str(item)
        rewritten = _rewrite_text(text_str, pattern, mapping, mapping_cf)
        # ❌ Only processes "Ov" and "er\x0ctting" separately
        # ❌ Never sees complete word "Overfitting"
```

## Comprehensive Solution Design

### 1. TJ Array Text Reconstruction
- **Concatenate all text elements** in TJ array to reconstruct complete text
- **Preserve spacing** using number elements (kerning adjustments)
- **Handle special characters** (`\x0c`, `\r`, `\n`, etc.)

### 2. Smart Word Boundary Detection
- **Identify word boundaries** across elements
- **Map replacements back** to original element structure
- **Preserve formatting** and positioning

### 3. Element Structure Preservation
- **Maintain TJ array structure** for proper PDF rendering
- **Keep number elements** (kerning) intact
- **Distribute replacements** across appropriate elements

## Implementation Strategy

### Phase 1: Text Reconstruction
```python
def reconstruct_tj_text(array_obj):
    """Reconstruct complete text from TJ array elements."""
    # Combine text elements with space handling
    # Clean special characters appropriately
    # Return: (full_text, element_mapping)
```

### Phase 2: Word Replacement Mapping
```python
def map_replacements_to_elements(full_text, replacements, element_mapping):
    """Map text replacements back to TJ array elements."""
    # Apply replacements to full text
    # Calculate element-level changes
    # Return: element_replacement_map
```

### Phase 3: Array Reconstruction
```python
def rebuild_tj_array(array_obj, element_replacements):
    """Rebuild TJ array with replacements while preserving structure."""
    # Apply element-level replacements
    # Preserve numbers (kerning)
    # Maintain proper spacing
```

## Test Cases to Implement

### 1. Split Word Cases
- ✅ `['Ov', 'erfitting']` → `['Und', 'erfitting']`
- ✅ `['Over', 'fit', 'ting']` → `['Under', 'fit', 'ting']`
- ✅ `['O', 'v', 'e', 'r', 'fitting']` → `['U', 'n', 'd', 'e', 'r', 'fitting']`

### 2. Special Character Handling
- ✅ `['Ov', 'er\x0ctting']` → `['Und', 'er\x0ctting']`
- ✅ `['Over\r', 'fitting']` → `['Under\r', 'fitting']`
- ✅ `['Over\n', 'fitting']` → `['Under\n', 'fitting']`

### 3. Kerning Preservation
- ✅ `['Over', -120, 'fitting']` → `['Under', -120, 'fitting']`
- ✅ `['O', -50, 'ver', -80, 'fitting']` → `['U', -50, 'nder', -80, 'fitting']`

### 4. Multiple Word Cases
- ✅ `['Over', 'fitting', 'and', 'Under', 'fitting']` → `['Under', 'fitting', 'and', 'Over', 'fitting']`

### 5. Edge Cases
- ✅ Empty elements: `['', 'Overfitting', '']`
- ✅ Single characters: `['O', 'v', 'e', 'r', 'f', 'i', 't', 't', 'i', 'n', 'g']`
- ✅ Mixed content: `['A.', -100, 'Over', 'fitting', -200, 'problem']`

## Success Criteria

1. **Complete Word Recognition**: All words correctly identified across element boundaries
2. **Accurate Replacement**: Text substitutions work regardless of element splitting
3. **Format Preservation**: Spacing, kerning, and special characters maintained
4. **Performance**: Minimal overhead compared to current implementation
5. **Robustness**: Handles all real-world PDF layouts

## Implementation Files

- `glyph_mapper/tj_array_processor.py` - New comprehensive TJ processing
- `test_tj_array_cases.py` - Comprehensive test suite
- `debug_tj_reconstruction.py` - Debugging tools