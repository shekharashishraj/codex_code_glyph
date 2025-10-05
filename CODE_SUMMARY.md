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

##### **OCR Mode**
1. Rasterizes each page at a configurable DPI (220 by default)
2. Runs Tesseract OCR via `pytesseract` + Pillow to extract word rectangles
3. Normalizes tokens to match mapping keys even when the PDF has mixed casing/punctuation
4. Inserts replacement text with invisible render mode so the accessible layer updates while the visual raster remains intact
5. Returns the untouched PDF when no replacements are matched or when OCR dependencies are missing

**Key Functions**:
- `extract_text_preview()` - Text extraction with 4000 char limit
- `generate_word_occurrences()` - Word frequency analysis
- `apply_word_mapping()` - Main processing entry point
- `apply_image_ocr_mapping()` - OCR-first fallback for raster-heavy PDFs
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
Complete font-level glyph manipulation system using fontTools.

**Core Functions**:

1. **Font Selection**:
   - `get_available_fonts()` - Discovers available fonts (project + system)
   - `extract_font_info_from_pdf()` - Analyzes PDF font usage
   - `select_best_font_for_pdf()` - Intelligently selects best font match
   - Priority: DejaVuSans > Arial > Times New Roman > Helvetica > Geneva

2. **Character Mapping**:
   - `create_character_mapping_from_words()` - Converts word → char mappings
   - Handles same-length words (direct char-by-char mapping)
   - Handles different-length words (intelligent heuristics for unique chars)
   - Detects and warns about mapping conflicts

3. **Font Modification**:
   - `create_remapped_font()` - Swaps glyphs in cmap table
   - Modifies Unicode BMP character map (Platform 3, Encoding 1)
   - Preserves all other font tables and metrics

4. **Font Embedding**:
   - `create_font_descriptor()` - Creates PDF font descriptor with full metrics
   - `embed_font_in_pdf()` - Properly embeds TTF font into PDF
   - Creates font stream object with complete font file
   - Adds font descriptor with bounding box, ascent, descent, metrics
   - Replaces existing fonts while preserving images/annotations

**Features**:
- Full font descriptor support (bounding box, italic angle, stem width)
- Proper font stream embedding with Length/Length1
- WinAnsiEncoding for broad compatibility
- Preserves ALL non-font PDF resources (images, annotations, metadata)
- Comprehensive logging at each step
- Automatic fallback to overlay mode on errors

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

### Font Mode Processing (Complete Algorithm)
1. **Font Analysis**:
   - Extract font information from PDF (names, types, embedding status)
   - Match PDF fonts with available system fonts
   - Select best font using priority order

2. **Character Mapping Creation**:
   - Analyze word mappings to infer character mappings
   - Same-length words: direct character-by-character mapping
   - Different-length words: map unique characters using set difference
   - Validate all required characters exist in selected font

3. **Font Glyph Remapping**:
   - Load selected font using fontTools
   - Access Unicode BMP cmap table (Platform 3, Encoding 1)
   - For each character mapping (old_char → new_char):
     - Get glyph names for both characters
     - Remap old_char's code point to new_char's glyph
   - Save modified font to bytes

4. **Content Stream Rewriting**:
   - Parse PDF content streams
   - Apply cross-array processor for pattern matching
   - Replace text strings (e.g., "dog" → "cat")
   - Preserve all non-text operations

5. **Font Embedding**:
   - Create font descriptor with metrics from modified font
   - Create font stream object with complete TTF bytes
   - Create font dictionary with Type, Subtype, BaseFont, Descriptor
   - Replace existing font resources on each page
   - Preserve ALL other page resources (images, annotations, etc.)

6. **Result**:
   - Text visually displays replacement words
   - Actual glyphs rendered match character mappings
   - File size smaller than overlay mode (no embedded images)
   - PDF structure fully preserved

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

### Font Mode (Fully Implemented)
- **Pros**:
  - Smaller file size (no image overlays)
  - True text replacement at glyph level
  - Preserves PDF structure, images, and annotations
  - Handles different-length word mappings intelligently
  - Uses high-quality fonts (DejaVuSans, Arial, Times New Roman)
- **Implementation**:
  - Analyzes PDF fonts and selects best matching font
  - Creates character-level mappings from word mappings
  - Swaps glyphs in font character map (cmap table)
  - Properly embeds font with descriptors and streams
  - Replaces PDF fonts while preserving all other content
- **Use Case**: Preferred for text-heavy PDFs, cleaner output

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
