# Glyph Mapper Demo

An implementation inspired by the *Invisible Prompts, Visible Threats* paper. The web tool lets you upload any PDF, review its textual content, and remap specific words so downstream parsers (copy/paste, PDF-to-text, LLM ingestion) receive alternative text while the document still renders the original glyphs.

## Features
- ✅ Upload PDF files entirely in-memory (no persistence).
- ✅ Preview extracted text and get word-frequency hints to speed up selection.
- ✅ Define one or more word-to-word mappings after the upload step.
- ✅ Generate a new PDF that rewrites text content streams yet overlays the original glyph imagery up front, hiding the manipulation from human readers while altering machine-parsed output.

## Getting Started
1. Create and activate a Python 3.10+ virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch the Flask server:
   ```bash
   python app.py
   ```
4. Open `http://127.0.0.1:5001/` in your browser.

## Usage
1. Upload a PDF. The app shows a text preview and the 60 most frequent tokens.
2. Use the buttons or manual entry to add mapping rows. Each row consists of the original word (matching the PDF exactly, punctuation included) and the replacement word.
3. Submit the form to download a remapped PDF.
4. Copying text from the generated PDF—or feeding it to an LLM—emits the replacement words, while the visual document remains unchanged thanks to the glyph overlay performed before text rewriting.

## Implementation Notes
- PDF parsing for the UI preview and vocabulary analysis uses PyMuPDF for speed and positional accuracy.
- Remapping first overlays captured glyph imagery using PyMuPDF, then rewrites page content streams via `PyPDF2`. Text rewriting handles both `Tj` and `TJ` operators so PDFs that rely on kerning arrays are supported.
- Mappings are resolved case-insensitively: if you type `multiple` we still target `Multiple` in the document and reuse the original glyph bitmap so the page appearance stays intact.
- The current encoder operates on whole-token matches. Documents that encode terms across ligatures or stylistic substitutions may require additional logic. The UI exposes the detected tokens so you can match exactly what the parser sees.
- Complex hyphenation boundaries may require extra handling. Because overlaying happens before rewriting, the captured glyphs reflect the untouched page, avoiding spacing regressions.

## Testing
A sample document is provided in `tests/sample.pdf`. You can run:
```bash
python - <<'PY'
from pathlib import Path
from glyph_mapper.pdf_processor import apply_word_mapping
original = Path('tests/sample.pdf').read_bytes()
remapped = apply_word_mapping(original, {'dog.': 'dragon!', 'dogs': 'owls'})
Path('tests/sample_remapped.pdf').write_bytes(remapped)
print('Remapped PDF written to tests/sample_remapped.pdf')
PY
```
This mirrors the automated verification used during development where the resulting PDF extracts the altered words while rendering remains unchanged through the glyph overlays.

## Next Steps
- Support more granular selection (bounding boxes / highlights) directly in the UI.
- Persist uploads beyond a single postback (e.g., temporary storage or database) for multi-user deployments.
- Harden against adversarial uploads and add automated tests around the content stream transformations.
