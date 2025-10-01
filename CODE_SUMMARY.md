# PDF Glyph Remapping Tool - Code Summary

## Overview
A Flask web application for remapping words in PDF documents through glyph-level manipulation. The tool supports two processing modes: overlay mode (visual replacement) and font mode (glyph-level character mapping).

## Architecture

### Core Components

#### 1. **Flask Application** (`app.py`)
- **Framework**: Flask 2.3+ web server running on port 5002
- **Routes**:
  - `GET /` - Upload form for PDF files
  - `POST /analyze` - Extracts text and generates word frequency analysis
  - `POST /remap` - Applies word mappings and returns modified PDF
- **Features**:
  - 25 MB file size limit
  - Base64 encoding for in-memory PDF transfer
  - Session-based processing (no file persistence)
  - Comprehensive logging with unique run IDs

#### 2. **PDF Processing Module** (`glyph_mapper/pdf_processor.py`)
Main orchestration layer with two processing modes:

##### **Overlay Mode** (Default)
1. Extracts word bounding boxes using PyMuPDF
2. Captures original glyph images at exact locations
3. Rewrites PDF content streams with replacement text using PyPDF2
4. Overlays captured images to preserve visual appearance
5. Handles case-insensitive mappings

##### **Font Mode** (Experimental)
1. Extracts primary font from PDF
2. Converts word mappings to character-level mappings
3. Creates remapped font with swapped glyphs using fontTools
4. Rewrites content streams with replacement text
5. Embeds modified font back into PDF
6. Falls back to overlay mode if font manipulation fails

**Key Functions**:
- `extract_text_preview()` - Text extraction with 4000 char limit
- `generate_word_occurrences()` - Word frequency analysis
- `apply_word_mapping()` - Main processing entry point
- `_collect_overlay_targets()` - Captures original glyph images
- `_apply_overlays()` - Applies image overlays to PDF

#### 3. **TJ Array Processor V2** (`glyph_mapper/tj_array_processor_v2.py`)
Processes TJ arrays (PDF kerned text arrays) while preserving element boundaries.

**Algorithm**:
1. Extract text segments with ownership mapping to array indices
2. Combine segments into full text, handling ligatures (fi, fl, ff, ffi)
3. Apply regex pattern matching and word replacements
4. Rebuild characters with updated ownership
5. Aggregate characters back to original segments
6. Write updated segments to new array

**Special Handling**:
- Ligature conversion: `\x0c` → `fi`, `\x0b` → `fl`, etc.
- Space threshold: kerning values ≤ -120 treated as spaces
- Preserves special characters in output

#### 4. **Cross-Array Processor** (`glyph_mapper/cross_array_processor.py`)
Handles patterns split across multiple TJ operations (e.g., "0.9:" split as "0" and "9:").

**Processing Phases**:
1. **Phase 1**: Apply V2 processor to individual TJ arrays
2. **Phase 2**: Sliding window cross-array pattern matching
   - Window size: 3 consecutive TJ operations
   - Detects split decimal patterns (e.g., "= 0 : 9:" → "0.9:")
   - Applies coordinated replacements across multiple arrays

**Special Patterns**:
- Split decimals: `(?:=\s*)?(\d)\s*:\s*(\d+):`
- Missing decimal points reconstructed during matching

#### 5. **Font Manipulator** (`glyph_mapper/font_manipulator.py`)
Font-level glyph manipulation using fontTools.

**Functions**:
- `create_remapped_font()` - Swaps glyph mappings in cmap table
- `analyze_font_characters()` - Checks character availability
- `extract_font_from_pdf()` - Extracts embedded fonts (placeholder)
- `create_character_mapping_from_words()` - Converts word mappings to char mappings
- `embed_font_in_pdf()` - Embeds custom font into PDF resources

**Limitations**:
- Only handles same-length word mappings
- Requires all characters available in source font
- Falls back to overlay mode on any failure

#### 6. **Logger** (`glyph_mapper/logger.py`)
Comprehensive logging system with structured metadata.

**Features**:
- Unique run ID for each processing session
- File logs: `logs/pdf_processing_{run_id}.log`
- Run directories: `runs/{run_id}/` containing:
  - `input.pdf` - Original PDF
  - `output.pdf` - Processed PDF
  - `extracted_text.txt` - Full text extraction
  - `run_metadata.json` - Structured metadata
- Logs: text extraction, pattern building, replacements, errors, fallbacks

### Dependencies
```
Flask>=2.3          # Web framework
PyMuPDF>=1.26       # PDF text extraction and image capture
PyPDF2>=3.0         # PDF content stream manipulation
fontTools           # Font glyph manipulation (font mode only)
```

## Data Flow

1. **Upload**: User uploads PDF via web form
2. **Analysis**:
   - Extract text preview (max 4000 chars)
   - Generate word frequency index
   - Display top 60 words
3. **Mapping**: User defines word → replacement mappings
4. **Processing**:
   - Build regex pattern from mappings (longest-first)
   - Create case-insensitive mapping dict
   - Route to overlay or font mode
   - Process content streams with V2 + cross-array processors
   - Apply overlays (overlay mode) or embed font (font mode)
5. **Download**: Return modified PDF with mappings applied

## Key Algorithms

### Pattern Building
- Sort words by length (descending) to prioritize longer matches
- Escape regex special characters
- Compile with case-insensitive flag
- Pattern: `word1|word2|word3|...`

### Text Segmentation
1. Find all pattern matches in text
2. Split text into (text, replacement) tuples
3. Preserve non-matching segments
4. Handle overlapping matches (first match wins)

### Overlay Technique
1. Locate word bounding boxes with PyMuPDF
2. Capture pixmap of original text at 220 DPI
3. Rewrite content stream with replacement text
4. Overlay original pixmap at exact location
5. Result: replacement text underneath, original appearance on top

### Cross-Array Matching
1. Build sliding window of 3 consecutive TJ operations
2. Extract combined text from window
3. Search for patterns including split decimals
4. Apply coordinated replacements across arrays
5. Preserve array structure and kerning

## File Structure
```
├── app.py                              # Flask web application
├── requirements.txt                    # Python dependencies
├── CLAUDE.md                           # Developer instructions
├── glyph_mapper/                       # Core processing module
│   ├── __init__.py                     # Public API exports
│   ├── pdf_processor.py                # Main processing orchestration
│   ├── tj_array_processor_v2.py        # TJ array processor
│   ├── cross_array_processor.py        # Cross-array pattern matching
│   ├── font_manipulator.py             # Font glyph manipulation
│   └── logger.py                       # Comprehensive logging
├── templates/                          # HTML templates
│   ├── base.html                       # Base layout
│   ├── upload.html                     # Upload form
│   └── mapping.html                    # Mapping interface
├── static/js/                          # Frontend JavaScript
│   └── mapping.js                      # Mapping UI logic
├── logs/                               # Processing logs
└── runs/                               # Run artifacts (PDFs, metadata)
```

## Processing Modes

### Overlay Mode
- **Pros**: Reliable, preserves visual appearance perfectly
- **Cons**: Increases file size (embedded images)
- **Use Case**: Default for all PDFs

### Font Mode
- **Pros**: Smaller file size, true text replacement
- **Cons**: Experimental, many edge cases, limited to char-level swaps
- **Use Case**: Same-length words with available glyphs

## Error Handling
- Font mode failures → automatic fallback to overlay mode
- Missing text → flash message, no processing
- Invalid PDF → validation at upload
- Pattern matching failures → logged but non-fatal
- All errors captured in run metadata

## Logging & Debugging
- Each run gets unique ID: `YYYYMMDD_HHMMSS_mmm`
- Detailed logs include:
  - Text extraction preview
  - Pattern compilation
  - Content stream operations
  - Replacement attempts and results
  - Font analysis (font mode)
  - Error stack traces
- Metadata JSON includes:
  - Input/output file paths and sizes
  - Processing mode
  - All mappings applied
  - Processing steps
  - Error details
  - Duration

## Performance Characteristics
- Memory-only processing (no temp files except logs)
- File size limit: 25 MB
- Text preview limit: 4000 chars
- Word frequency limit: Top 60 words
- Overlay DPI: 220 (balance of quality/size)
- Cross-array window: 3 operations

## Limitations
1. No multi-line word matching
2. Font mode limited to same-length words
3. Split decimal patterns require specific format
4. No support for scanned/image-only PDFs
5. Case-insensitive matching may cause unintended replacements
6. No undo/preview functionality
7. Overlays increase file size

## Future Enhancements
- Better font extraction from PDFs
- Multi-line pattern matching
- Variable-length word mappings in font mode
- Preview before applying changes
- Batch processing
- API endpoints for programmatic access
