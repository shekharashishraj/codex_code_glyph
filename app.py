"""Flask app exposing PDF glyph remapping workflow."""

from __future__ import annotations

import base64
import io
from typing import Dict

from flask import Flask, Response, flash, redirect, render_template, request, send_file, url_for

from glyph_mapper import (
    apply_word_mapping,
    extract_text_preview,
    generate_word_occurrences,
    summarise_vocabulary,
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "dev-secret-key"  # Replace with an environment variable in production.
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB uploads

    @app.get("/")
    def index() -> str:
        return render_template("upload.html")

    @app.post("/analyze")
    def analyze_pdf() -> str:
        uploaded = request.files.get("pdf")
        if uploaded is None or uploaded.filename == "":
            flash("Please choose a PDF before continuing.")
            return redirect(url_for("index"))

        pdf_bytes = uploaded.read()
        if not pdf_bytes.startswith(b"%PDF"):
            flash("This doesn't look like a valid PDF file.")
            return redirect(url_for("index"))

        preview_text = extract_text_preview(pdf_bytes)
        word_index = generate_word_occurrences(pdf_bytes)
        top_words = summarise_vocabulary(word_index, top_n=60)
        if not preview_text:
            flash("No extractable text found. The document may be scanned or image-only.")

        encoded_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

        return render_template(
            "mapping.html",
            preview=preview_text,
            top_words=top_words,
            pdf_data=encoded_pdf,
        )

    @app.post("/remap")
    def remap_pdf() -> Response:
        encoded_pdf = request.form.get("pdf_data")
        if not encoded_pdf:
            flash("Upload session expired. Please submit the PDF again.")
            return redirect(url_for("index"))

        try:
            pdf_bytes = base64.b64decode(encoded_pdf)
        except (ValueError, TypeError):
            flash("Could not decode the uploaded PDF payload.")
            return redirect(url_for("index"))

        originals = request.form.getlist("original")
        replacements = request.form.getlist("replacement")
        mapping: Dict[str, str] = {
            original: replacement
            for original, replacement in zip(originals, replacements)
            if original.strip() and replacement.strip()
        }

        remapped_pdf = apply_word_mapping(pdf_bytes, mapping)
        output = io.BytesIO(remapped_pdf)
        output.seek(0)
        return send_file(
            output,
            mimetype="application/pdf",
            download_name="glyph-remapped.pdf",
            as_attachment=True,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
