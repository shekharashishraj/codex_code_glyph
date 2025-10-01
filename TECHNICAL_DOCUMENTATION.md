# PDF Glyph Remapping: Technical Documentation

## Overview

This document provides a detailed technical explanation of how the PDF glyph remapping system works. The system allows users to substitute words in PDF documents while preserving the visual appearance and layout through a sophisticated glyph overlay technique.

## Architecture Overview

The system consists of three main components:

1. **Web Interface (Flask)** - Handles file uploads and user interactions
2. **PDF Processing Engine** - Core logic for text extraction and manipulation
3. **Glyph Overlay System** - Visual preservation during text replacement

## Detailed Component Analysis

### 1. Web Interface (`app.py`)

The Flask application provides three main routes:

#### Route: `/` (Upload)
- Renders the upload form
- Accepts PDF files up to 16MB
- Validates file type and size

#### Route: `/analyze` (POST)
- Processes uploaded PDF for text analysis
- Extracts text preview using PyMuPDF
- Generates word frequency statistics
- Renders mapping interface with suggested words

#### Route: `/remap` (POST)
- Applies user-defined word mappings
- Returns modified PDF as downloadable file
- Handles mapping validation and error cases

### 2. PDF Processing Engine (`glyph_mapper/pdf_processor.py`)

This is the core of the system, handling all PDF manipulation operations.

#### 2.1 Text Extraction Pipeline

```python
def extract_text_preview(pdf_bytes: bytes, *, max_chars: int = 4000) -> str:
```

**Purpose**: Extract readable text from PDF for user preview

**Process**:
1. Opens PDF using PyMuPDF (`fitz.open()`)
2. Iterates through pages sequentially
3. Extracts text using `page.get_text("text")`
4. Concatenates pages until `max_chars` limit reached
5. Returns trimmed, clean text preview

**Key Details**:
- Uses PyMuPDF for reliable text extraction
- Handles multi-page documents efficiently
- Memory-conscious with character limits
- Preserves text structure and spacing

#### 2.2 Word Occurrence Analysis

```python
def generate_word_occurrences(pdf_bytes: bytes) -> Dict[str, List[Dict[str, object]]]:
```

**Purpose**: Create an index of every word and its locations in the PDF

**Process**:
1. Opens PDF with PyMuPDF
2. For each page, extracts words with coordinates using `page.get_text("words")`
3. Builds dictionary mapping each unique word to list of locations
4. Each location contains page number and bounding rectangle

**Data Structure**:
```python
{
    "word": [
        {"page": 0, "rect": (x0, y0, x1, y1)},
        {"page": 1, "rect": (x0, y0, x1, y1)},
        # ... more occurrences
    ]
}
```

**Use Cases**:
- Frequency analysis for UI suggestions
- Position tracking for glyph overlays
- Validation of mapping targets

#### 2.3 Word Mapping Application

This is the most complex part of the system, involving multiple sophisticated techniques.

```python
def apply_word_mapping(pdf_bytes: bytes, mapping: Dict[str, str]) -> bytes:
```

**High-Level Process**:
1. Clean and normalize input mappings
2. Generate glyph overlays for visual preservation
3. Modify PDF content streams for text replacement
4. Apply overlays to final document
5. Return modified PDF bytes

#### 2.4 Glyph Overlay System

**Problem**: When we replace text in PDF content streams, the visual appearance changes because:
- Different fonts may render differently
- Character spacing and kerning are affected
- Visual layout can break

**Solution**: Glyph Overlay Technique

```python
def _collect_overlay_targets(pdf_bytes: bytes, mapping: Dict[str, str], mapping_cf: Dict[str, str]) -> Tuple[List[OverlayTarget], Dict[str, str]]:
```

**Process**:
1. **Identify Target Words**: Find all words that will be replaced
2. **Capture Original Glyphs**: For each target word:
   - Get precise bounding rectangle
   - Render that rectangle as high-DPI image (220 DPI)
   - Store as PNG bytes
3. **Create Overlay Targets**: Build list of images to overlay later

**Key Insight**: By capturing the original visual appearance before text replacement, we can overlay the original glyphs on top of the replaced text, maintaining perfect visual fidelity.

#### 2.5 PDF Content Stream Manipulation

**Background**: PDFs store text using operators in content streams:
- `Tj` - Simple text string
- `TJ` - Text with kerning adjustments (arrays)

```python
# Example PDF content stream operations:
# Tj operator: [(TextStringObject("Hello")], b"Tj")
# TJ operator: [ArrayObject([TextStringObject("H"), -120, TextStringObject("ello")])], b"TJ")
```

**Text Replacement Logic**:

```python
for operands, operator in content.operations:
    if operator == b"Tj":
        # Handle simple text strings
        text_obj = operands[0]
        rewritten = _rewrite_text(str(text_obj), pattern, effective_mapping, mapping_cf)
        if rewritten:
            new_ops.append(([TextStringObject(rewritten)], b"Tj"))
    
    elif operator == b"TJ":
        # Handle kerning arrays - MORE COMPLEX
        array_obj = operands[0]
        new_array = ArrayObject()
        for item in array_obj:
            if isinstance(item, TextStringObject):
                # Rewrite text elements
                rewritten = _rewrite_text(str(item), pattern, effective_mapping, mapping_cf)
                new_array.append(TextStringObject(rewritten) if rewritten else item)
            else:
                # Preserve numbers (kerning adjustments)
                new_array.append(item)
```

**Critical Design Decision**: Process TJ arrays element-by-element rather than combining into single string. This preserves:
- Kerning adjustments (negative numbers)
- Character spacing
- Text positioning accuracy

#### 2.6 Pattern Matching and Case Handling

```python
def _build_pattern(words: Iterable[str], *, ignore_case: bool = False) -> Optional[Pattern[str]]:
```

**Regex Construction**:
1. Sort words by length (longest first) to prevent partial matches
2. Escape special regex characters
3. Join with `|` (OR operator)
4. Compile with optional case-insensitive flag

**Case Resolution System**:
```python
def _resolve_replacement(token: str, mapping: Dict[str, str], mapping_cf: Dict[str, str]) -> Optional[str]:
```

1. **Exact Match**: Check original mapping dictionary first
2. **Case-Folded Match**: Check case-insensitive mapping as fallback
3. **Return Replacement**: Use appropriate replacement value

This dual-layer approach allows:
- Exact case matches when available
- Graceful fallback for case variations
- Maintains user intent for case-sensitive mappings

#### 2.7 Text Segmentation and Reconstruction

```python
def _segment_text(text: str, pattern: Pattern[str], mapping: Dict[str, str], mapping_cf: Dict[str, str]) -> Optional[List[Tuple[str, Optional[str]]]]:
```

**Process**:
1. **Find Matches**: Use regex to find all replacement targets in text
2. **Segment**: Split text into alternating segments:
   - Unchanged text (no replacement)
   - Matched text (with replacement)
3. **Build Tuples**: `(text_segment, replacement_or_none)`

**Reconstruction**:
```python
def _rewrite_text(text: str, pattern: Pattern[str], mapping: Dict[str, str], mapping_cf: Dict[str, str]) -> Optional[str]:
```

1. Get segments from `_segment_text`
2. Rebuild string using replacements where available
3. Return `None` if no changes needed (optimization)

### 3. Advanced PDF Considerations

#### 3.1 Coordinate Systems
- PDF uses bottom-left origin (mathematical coordinates)
- PyMuPDF handles coordinate conversion automatically
- Glyph overlays use precise floating-point rectangles

#### 3.2 Font and Encoding Handling
- System works with any PDF fonts/encodings
- PyMuPDF handles text extraction regardless of font
- Glyph overlays preserve original font rendering

#### 3.3 Memory Management
- All processing done in-memory (no temporary files)
- Large PDFs handled through streaming where possible
- BytesIO used for PDF manipulation pipeline

## Error Handling and Edge Cases

### 1. Case Sensitivity Issues
**Problem**: User maps "word" but PDF contains "Word"
**Detection**: Zero matches found during processing
**Solution**: Case-insensitive fallback mapping system

### 2. Complex Text Layouts
**Problem**: Text split across multiple operators
**Handling**: Process each operator independently, rely on overlays for visual consistency

### 3. Large Documents
**Problem**: Memory usage for huge PDFs
**Mitigation**: Character limits on text preview, streaming where possible

### 4. Font Rendering
**Problem**: Replacement text looks different from original
**Solution**: Glyph overlay system preserves original appearance

## Performance Characteristics

### Time Complexity
- Text extraction: O(n) where n = document size
- Word indexing: O(w) where w = unique words
- Pattern matching: O(t) where t = total text length
- Glyph capture: O(m) where m = mapped words

### Space Complexity
- Word index: O(w × o) where o = average occurrences per word
- Glyph overlays: O(m × i) where i = average image size
- Modified PDF: Similar to original PDF size

### Bottlenecks
1. **Glyph Capture**: High-DPI rendering can be slow for many words
2. **Content Stream Parsing**: PyPDF2 parsing overhead
3. **Memory Usage**: Overlays stored as PNG images in memory

## Security Considerations

### 1. File Upload Safety
- File size limits (16MB)
- MIME type validation
- No file persistence on server

### 2. Memory Safety
- Character limits prevent excessive memory usage
- BytesIO prevents filesystem attacks
- No user-controlled file paths

### 3. Input Validation
- Mapping dictionary sanitization
- PDF structure validation by PyPDF2
- Error handling for malformed inputs

## Future Enhancement Opportunities

### 1. Case Detection Automation
- Auto-suggest correct case variations
- Fuzzy matching for close matches
- Case normalization options

### 2. Performance Optimization
- Parallel glyph capture for large mappings
- Incremental PDF processing
- Caching for repeated operations

### 3. Advanced Features
- Regular expression patterns in mappings
- Font-aware replacements
- Batch processing capabilities

## Debugging and Diagnostics

The codebase includes several debugging utilities:

### 1. Text Extraction Verification
```python
# Check what text PyMuPDF extracts
text = extract_text_preview(pdf_bytes)
```

### 2. Word Occurrence Analysis
```python
# Verify word detection
occurrences = generate_word_occurrences(pdf_bytes)
```

### 3. Pattern Testing
```python
# Test regex patterns
pattern = _build_pattern(words, ignore_case=True)
matches = pattern.findall(test_text)
```

### 4. Content Stream Inspection
```python
# Examine PDF operators
content = ContentStream(page.get_contents(), reader)
for operands, operator in content.operations:
    # Analyze structure
```

## Conclusion

The PDF glyph remapping system demonstrates sophisticated PDF manipulation techniques, combining:

- **Accurate Text Processing**: Reliable extraction and pattern matching
- **Visual Preservation**: Glyph overlay technique maintains appearance
- **Robust Architecture**: Handles complex PDF structures and edge cases
- **Performance Optimization**: Memory-conscious design for large documents

The system's key innovation is the glyph overlay approach, which solves the fundamental challenge of maintaining visual fidelity while modifying PDF text content. This technique could be applied to other PDF modification scenarios beyond simple word replacement.