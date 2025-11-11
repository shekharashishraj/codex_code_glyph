"""Flask app exposing PDF glyph remapping workflow."""

from __future__ import annotations

import base64
import io
import os
import logging
import json
import traceback
from datetime import datetime
from typing import Dict

from flask import Flask, Response, flash, redirect, render_template, request, send_file, url_for, jsonify

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

    # Setup logging
    if not os.path.exists('logs'):
        os.makedirs('logs')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )

    app.logger = logging.getLogger(__name__)

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

    @app.get("/llm-tester")
    def llm_tester() -> str:
        """LLM PDF parsing test interface"""
        return render_template("llm_tester.html")

    @app.post("/auto-generate-mappings")
    def auto_generate_mappings():
        """Auto-generate word mappings from uploaded PDF"""
        app.logger.info("Starting auto-mapping generation")

        uploaded = request.files.get("pdf")
        if uploaded is None or uploaded.filename == "":
            app.logger.error("No PDF file uploaded")
            return jsonify({"error": "Please choose a PDF file"}), 400

        pdf_bytes = uploaded.read()
        if not pdf_bytes.startswith(b"%PDF"):
            app.logger.error("Invalid PDF file format")
            return jsonify({"error": "Invalid PDF file"}), 400

        strategy = request.form.get("strategy", "moderate")
        app.logger.info(f"Using strategy: {strategy}")

        try:
            from auto_mapping_generator import AutoMappingGenerator

            generator = AutoMappingGenerator()
            test_sets = generator.generate_comprehensive_test_set(pdf_bytes)
            analysis = generator.analyze_pdf_content(pdf_bytes)

            if strategy not in test_sets:
                strategy = "moderate"

            selected_mappings = test_sets[strategy]
            app.logger.info(f"Generated {len(selected_mappings)} mappings")

            return jsonify({
                "success": True,
                "mappings": selected_mappings,
                "strategy": strategy,
                "all_strategies": test_sets,
                "analysis": {
                    "domain": analysis["domain"],
                    "unique_words": analysis["unique_words"],
                    "total_words": analysis["total_words"],
                    "top_words": analysis["top_words"][:10]  # First 10 for display
                }
            })

        except Exception as e:
            app.logger.error(f"Error in auto-generation: {e}")
            app.logger.error(traceback.format_exc())
            return jsonify({"error": f"Auto-generation failed: {str(e)}"}), 500

    @app.post("/test-llm-parsing")
    def test_llm_parsing():
        """Run LLM parsing tests on uploaded PDF with all 3 approaches"""
        uploaded = request.files.get("pdf")
        if uploaded is None or uploaded.filename == "":
            return jsonify({"error": "Please choose a PDF file"}), 400

        pdf_bytes = uploaded.read()
        if not pdf_bytes.startswith(b"%PDF"):
            return jsonify({"error": "Invalid PDF file"}), 400

        # Check for test mode (skips actual LLM API calls)
        test_mode = request.form.get("test_mode") == "true"

        # Check if we should use auto-generated mappings
        use_auto = request.form.get("use_auto_mappings") == "true"

        if use_auto:
            # Auto-generate mappings
            try:
                from auto_mapping_generator import AutoMappingGenerator

                strategy = request.form.get("auto_strategy", "moderate")
                generator = AutoMappingGenerator()
                test_sets = generator.generate_comprehensive_test_set(pdf_bytes)

                if strategy not in test_sets:
                    strategy = "moderate"

                mapping = test_sets[strategy]

                if not mapping:
                    return jsonify({"error": "Auto-generation produced no mappings"}), 400

            except Exception as e:
                return jsonify({"error": f"Auto-generation failed: {str(e)}"}), 500
        else:
            # Get mappings from form
            originals = request.form.getlist("original[]")
            replacements = request.form.getlist("replacement[]")
            mapping: Dict[str, str] = {
                original.strip(): replacement.strip()
                for original, replacement in zip(originals, replacements)
                if original.strip() and replacement.strip()
            }

            if not mapping:
                return jsonify({"error": "Please provide at least one word mapping"}), 400

        try:
            # Import and run the PDF processing
            from advanced_approaches import (
                approach_1_custom_font_remapping,
                approach_2_dual_layer_rendering,
                approach_3_precision_overlays
            )

            # Create test PDFs with all 3 approaches
            test_pdfs = {
                "original": pdf_bytes,
                "approach_1_custom_fonts": approach_1_custom_font_remapping(pdf_bytes, mapping),
                "approach_2_dual_layer": approach_2_dual_layer_rendering(pdf_bytes, mapping),
                "approach_3_precision_overlays": approach_3_precision_overlays(pdf_bytes, mapping)
            }

            if test_mode:
                # Test mode: Skip LLM API calls, return mock results
                mock_results = create_mock_llm_results(mapping)
                stats = calculate_test_statistics(mock_results, mapping)

                return jsonify({
                    "success": True,
                    "results": {k: [result.__dict__ for result in v] for k, v in mock_results.items()},
                    "total_tests": stats["total_tests"],
                    "successful_tests": stats["successful_tests"],
                    "approach_2_effectiveness": stats["approach_2_effectiveness"],
                    "approach_3_effectiveness": stats["approach_3_effectiveness"],
                    "mapping": mapping,
                    "auto_generated": use_auto,
                    "test_mode": True
                })
            else:
                # Real mode: Run actual LLM tests
                from llm_pdf_tester import LLMPDFTester

                tester = LLMPDFTester()
                results = tester.test_all_models_all_approaches(test_pdfs)

                # Calculate statistics
                stats = calculate_test_statistics(results, mapping)

                return jsonify({
                    "success": True,
                    "results": {k: [result.__dict__ for result in v] for k, v in results.items()},
                    "total_tests": stats["total_tests"],
                    "successful_tests": stats["successful_tests"],
                    "approach_2_effectiveness": stats["approach_2_effectiveness"],
                    "approach_3_effectiveness": stats["approach_3_effectiveness"],
                    "mapping": mapping,
                    "auto_generated": use_auto,
                    "test_mode": False
                })

        except Exception as e:
            import traceback
            print(f"Error in LLM testing: {e}")
            print(traceback.format_exc())
            return jsonify({"error": f"Testing failed: {str(e)}"}), 500

    @app.get("/view-pdf/<filename>")
    def view_pdf(filename: str):
        """Serve generated test PDFs for viewing"""
        import os
        pdf_path = os.path.join("tests", filename)
        if os.path.exists(pdf_path):
            return send_file(pdf_path, mimetype="application/pdf", as_attachment=False)
        else:
            return "PDF not found", 404

    return app


def create_mock_llm_results(mapping):
    """Create mock LLM results for UI testing"""
    from llm_pdf_tester import LLMTestResult
    import time

    models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    approaches = ["original", "approach_1_custom_fonts", "approach_2_dual_layer", "approach_3_precision_overlays"]

    mock_results = {}

    for approach in approaches:
        approach_results = []
        for model in models:
            # Mock different success scenarios
            if approach == "original":
                # Original should show original words
                result = LLMTestResult(
                    model_name=model,
                    approach="test",
                    extracted_text="Mock extracted text with original words",
                    contains_original=True,
                    contains_replacement=False,
                    parsing_method="Mock Vision",
                    response_time=1.5,
                    success=True
                )
            elif approach == "approach_2_dual_layer":
                # Dual layer should show some success
                result = LLMTestResult(
                    model_name=model,
                    approach="test",
                    extracted_text="Mock extracted text with replacement words",
                    contains_original=model == "gpt-3.5-turbo",  # One model still sees original
                    contains_replacement=True,
                    parsing_method="Mock Vision",
                    response_time=2.1,
                    success=True
                )
            elif approach == "approach_3_precision_overlays":
                # Precision overlays should show high success
                result = LLMTestResult(
                    model_name=model,
                    approach="test",
                    extracted_text="Mock extracted text with replacement words",
                    contains_original=False,  # No original detected
                    contains_replacement=True,
                    parsing_method="Mock Vision",
                    response_time=1.8,
                    success=True
                )
            else:
                # Approach 1 framework
                result = LLMTestResult(
                    model_name=model,
                    approach="test",
                    extracted_text="Mock extracted text",
                    contains_original=True,
                    contains_replacement=True,
                    parsing_method="Mock Vision",
                    response_time=1.2,
                    success=True
                )

            approach_results.append(result)

        mock_results[approach] = approach_results

    return mock_results


def calculate_test_statistics(results, mapping):
    """Calculate effectiveness statistics for the test results"""
    total_tests = sum(len(approach_results) for approach_results in results.values())
    successful_tests = sum(
        len([r for r in approach_results if r.success])
        for approach_results in results.values()
    )

    # Calculate approach effectiveness
    def calc_approach_effectiveness(approach_name):
        if approach_name not in results:
            return 0

        approach_results = [r for r in results[approach_name] if r.success]
        if not approach_results:
            return 0

        # Count how many detected replacement text (success) vs original text (failure)
        detected_replacement = sum(1 for r in approach_results if r.contains_replacement)
        return (detected_replacement / len(approach_results)) * 100

    approach_2_effectiveness = calc_approach_effectiveness("approach_2_dual_layer")
    approach_3_effectiveness = calc_approach_effectiveness("approach_3_precision_overlays")

    return {
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "approach_2_effectiveness": approach_2_effectiveness,
        "approach_3_effectiveness": approach_3_effectiveness
    }


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
