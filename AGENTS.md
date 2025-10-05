# Repository Guidelines

## Project Structure & Module Organization
The Flask entry point lives in `app.py`, orchestrating uploads and rendering Jinja templates. Core PDF logic resides under `glyph_mapper/`, with `pdf_processor.py` coordinating PyMuPDF extraction and PyPDF2 rewriting, supported by helpers such as `tj_array_processor_v2.py` for kerning-aware edits and `font_manipulator.py` for glyph overlays. UI assets sit in `templates/` and `static/` (styles, JS, and images), while custom fonts for glyph swaps are stored in `fonts/`. Sample inputs and quick verification artefacts live in `tests/` and `PDFS/`; `logs/` is created at runtime for troubleshooting traces.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` — create an isolated Python 3.10+ environment.
- `pip install -r requirements.txt` — install Flask, PyMuPDF, PyPDF2, and fonttools.
- `python app.py` or `FLASK_ENV=development python app.py` — run the dev server at `http://127.0.0.1:5001/` with live reload.
- `python - <<'PY' ... PY` (see `README.md`) — regenerate a remapped PDF using the automation snippet in `tests/`.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation, descriptive snake_case for functions, and CapWords for classes. Keep module-level docstrings and type hints consistent with existing files (`glyph_mapper/pdf_processor.py`). Prefer f-strings for logging and ensure logger calls use the structured helpers in `glyph_mapper/logger.py`. Template variables mirror Flask route names; keep new routes small and descriptive (e.g., `preview_mapping`).

## Testing Guidelines
No formal test harness ships today; lean on the sample program in `README.md` and the PDFs under `tests/` to validate remapping changes. When adding features, supply a focused script under `tests/` demonstrating the scenario and mention expected textual output. Document any manual verification steps in the PR description, and capture before/after text extraction to prove glyph fidelity.

## Commit & Pull Request Guidelines
Commits follow short, imperative subjects (`Add glyph remapping mode`) with additional context in the body when needed. Group logically related changes and avoid mixing UI and processor refactors. PRs should link tracking issues, outline functional impacts, and attach screenshots or extracted-text diffs whenever the UI or PDF stream handling changes. Flag any new dependencies and note required environment variables or configuration updates.
