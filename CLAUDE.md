# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Running
```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask development server
python app.py
```
The app runs on http://127.0.0.1:5001/

### Testing
```bash
# Manual testing with sample PDF
python - <<'PY'
from pathlib import Path
from glyph_mapper.pdf_processor import apply_word_mapping
original = Path('tests/sample.pdf').read_bytes()
remapped = apply_word_mapping(original, {'dog.': 'dragon!', 'dogs': 'owls'})
Path('tests/sample_remapped.pdf').write_bytes(remapped)
print('Remapped PDF written to tests/sample_remapped.pdf')
PY
```

## Architecture

### Core Components
- **Flask App** (`app.py`): Main web application with three routes:
  - `/` - PDF upload form
  - `/analyze` - Extracts text and shows mapping interface
  - `/remap` - Applies mappings and returns modified PDF

- **PDF Processing Module** (`glyph_mapper/`): Core functionality for:
  - Text extraction and preview (`extract_text_preview`)
  - Word frequency analysis (`generate_word_occurrences`, `summarise_vocabulary`)
  - Glyph remapping (`apply_word_mapping`)

### Key Implementation Details
- Uses PyMuPDF for PDF parsing and text extraction
- Uses PyPDF2 for content stream rewriting  
- Glyph overlay technique: captures original glyphs before text replacement to maintain visual appearance
- Handles both `Tj` and `TJ` PDF text operators for kerning array support
- Case-insensitive mapping resolution
- In-memory processing (no file persistence)

### File Structure
```
├── app.py                    # Flask web application
├── glyph_mapper/            # Core PDF processing module
│   ├── __init__.py          # Public API exports
│   └── pdf_processor.py     # PDF manipulation logic
├── templates/               # Flask HTML templates
│   ├── base.html
│   ├── upload.html
│   └── mapping.html
├── static/js/               # Frontend JavaScript
├── tests/
│   └── sample.pdf           # Test document
└── requirements.txt         # Python dependencies
```

### Dependencies
- Flask 2.3+ (web framework)
- PyMuPDF 1.26+ (PDF text extraction)
- PyPDF2 3.0+ (PDF content stream manipulation)