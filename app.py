"""Flask app exposing PDF glyph remapping workflow with comprehensive LLM testing."""

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
from glyph_mapper.logger import start_new_run


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
        # Start a new logging run
        logger = start_new_run()
        
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
        processing_mode = request.form.get("processing_mode", "overlay")
        if processing_mode not in {"overlay", "font", "ocr"}:
            processing_mode = "overlay"
        
        mapping: Dict[str, str] = {
            original: replacement
            for original, replacement in zip(originals, replacements)
            if original.strip() and replacement.strip()
        }

        logger.logger.info(f"Starting PDF remapping with {len(mapping)} mappings in {processing_mode} mode")
        
        try:
            remapped_pdf = apply_word_mapping(pdf_bytes, mapping, mode=processing_mode)
            output = io.BytesIO(remapped_pdf)
            output.seek(0)
            
            # Create a more descriptive filename with run ID and mode
            filename = f"glyph-remapped-{logger.run_id}-{processing_mode}.pdf"
            
            return send_file(
                output,
                mimetype="application/pdf",
                download_name=filename,
                as_attachment=True,
            )
        except Exception as e:
            logger.log_error(e, "Flask remap_pdf route")
            logger.finalize_run()
            flash(f"Error processing PDF: {str(e)}")
            return redirect(url_for("index"))

    @app.get("/llm-tester")
    def llm_tester() -> str:
        """LLM PDF parsing test interface"""
        return render_template("llm_tester_new.html")

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

    @app.post("/generate-all-pdfs")
    def generate_all_pdfs():
        """Generate all 3 PDF manipulation approaches"""
        app.logger.info("Starting PDF generation for all approaches")

        try:
            uploaded = request.files.get("pdf")
            if uploaded is None or uploaded.filename == "":
                return jsonify({"error": "Please choose a PDF file"}), 400

            pdf_bytes = uploaded.read()
            if not pdf_bytes.startswith(b"%PDF"):
                return jsonify({"error": "Invalid PDF file"}), 400

            # Get mappings from form
            mappings_json = request.form.get("mappings")
            if not mappings_json:
                return jsonify({"error": "No mappings provided"}), 400

            mapping = json.loads(mappings_json)
            app.logger.info(f"Applying {len(mapping)} word mappings")

            # Import and generate all approaches
            from advanced_approaches import (
                approach_1_custom_font_remapping,
                approach_2_dual_layer_rendering,
                approach_3_precision_overlays
            )

            # Generate all PDFs
            results = {
                "original": pdf_bytes,
                "approach_1_custom_fonts": approach_1_custom_font_remapping(pdf_bytes, mapping),
                "approach_2_dual_layer": approach_2_dual_layer_rendering(pdf_bytes, mapping),
                "approach_3_precision_overlays": approach_3_precision_overlays(pdf_bytes, mapping)
            }

            # Save all PDFs to tests directory
            if not os.path.exists("tests"):
                os.makedirs("tests")

            generated_files = []
            for approach_name, pdf_data in results.items():
                filename = f"generated_{approach_name}.pdf"
                filepath = os.path.join("tests", filename)

                with open(filepath, "wb") as f:
                    f.write(pdf_data)
                generated_files.append(filename)
                app.logger.info(f"Saved {filename}")

            return jsonify({
                "success": True,
                "generated_files": generated_files,
                "mapping": mapping,
                "message": f"Generated {len(generated_files)} PDF variants"
            })

        except Exception as e:
            app.logger.error(f"Error generating PDFs: {e}")
            app.logger.error(traceback.format_exc())
            return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500

    @app.get("/view-pdf/<filename>")
    def view_pdf(filename: str):
        """Serve generated test PDFs for viewing"""
        pdf_path = os.path.join("tests", filename)
        if os.path.exists(pdf_path):
            return send_file(pdf_path, mimetype="application/pdf", as_attachment=False)
        else:
            return "PDF not found", 404

    @app.get("/download-pdf/<filename>")
    def download_pdf(filename: str):
        """Download generated test PDFs"""
        pdf_path = os.path.join("tests", filename)
        if os.path.exists(pdf_path):
            return send_file(pdf_path, mimetype="application/pdf", as_attachment=True)
        else:
            return "PDF not found", 404

    @app.get("/list-generated-pdfs")
    def list_generated_pdfs():
        """List all generated PDF files"""
        try:
            files = []
            tests_dir = "tests"
            if os.path.exists(tests_dir):
                for filename in os.listdir(tests_dir):
                    if filename.startswith("generated_") and filename.endswith(".pdf"):
                        filepath = os.path.join(tests_dir, filename)
                        file_info = {
                            "filename": filename,
                            "display_name": filename.replace("generated_", "").replace(".pdf", "").replace("_", " ").title(),
                            "size": os.path.getsize(filepath),
                            "modified": os.path.getmtime(filepath)
                        }
                        files.append(file_info)

            return jsonify({"files": files})
        except Exception as e:
            app.logger.error(f"Error listing PDFs: {e}")
            return jsonify({"error": str(e)}), 500

    @app.post("/test-single-pdf")
    def test_single_pdf():
        """Test a single PDF with all LLM models"""
        app.logger.info("Starting single PDF LLM test")

        try:
            filename = request.form.get("filename")
            openai_api_key = request.form.get("openai_api_key")
            test_mode = request.form.get("test_mode") == "true"

            if not filename:
                return jsonify({"error": "No filename provided"}), 400

            if not test_mode and not openai_api_key:
                return jsonify({"error": "OpenAI API key required for real testing"}), 400

            # Load PDF
            pdf_path = os.path.join("tests", filename)
            if not os.path.exists(pdf_path):
                return jsonify({"error": f"PDF {filename} not found"}), 404

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            # Get expected mappings for validation
            mappings_json = request.form.get("mappings", "{}")
            mapping = json.loads(mappings_json)

            if test_mode:
                # Mock testing
                app.logger.info(f"Running mock test on {filename}")
                results = create_mock_single_pdf_results(filename, mapping)
            else:
                # Real API testing
                app.logger.info(f"Running real API test on {filename}")
                from llm_pdf_tester import LLMPDFTester

                tester = LLMPDFTester(api_key=openai_api_key)
                results = []

                for model in tester.openai_models:
                    try:
                        app.logger.info(f"Testing with {model}")
                        result = tester.test_openai_vision_api(pdf_bytes, model)
                        # Validate results against expected mappings
                        validated_result = validate_llm_result(result, mapping)
                        results.append(validated_result.__dict__)
                    except Exception as e:
                        app.logger.error(f"Error testing {model}: {e}")
                        results.append({
                            "model_name": model,
                            "success": False,
                            "error": str(e)
                        })

            return jsonify({
                "success": True,
                "filename": filename,
                "results": results,
                "test_mode": test_mode
            })

        except Exception as e:
            app.logger.error(f"Error in single PDF test: {e}")
            app.logger.error(traceback.format_exc())
            return jsonify({"error": f"Testing failed: {str(e)}"}), 500

    @app.get("/logs")
    def view_logs():
        """View application logs"""
        try:
            log_path = "logs/app.log"
            if os.path.exists(log_path):
                with open(log_path, "r") as f:
                    logs = f.readlines()
                # Return last 100 log lines
                return jsonify({"logs": logs[-100:]})
            else:
                return jsonify({"logs": ["No logs available"]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


def create_mock_single_pdf_results(filename: str, mapping: Dict[str, str]):
    """Create mock LLM results for a single PDF"""
    from llm_pdf_tester import LLMTestResult

    models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    results = []

    for model in models:
        if "original" in filename:
            # Original should detect original words
            result = LLMTestResult(
                model_name=model,
                approach="original",
                extracted_text="Mock extracted original text",
                contains_original=True,
                contains_replacement=False,
                parsing_method="Mock Vision",
                response_time=1.5,
                success=True
            )
        elif "dual_layer" in filename:
            # Dual layer should show mixed results
            result = LLMTestResult(
                model_name=model,
                approach="dual_layer",
                extracted_text="Mock extracted text with some replacement words",
                contains_original=model == "gpt-3.5-turbo",  # One model still sees original
                contains_replacement=True,
                parsing_method="Mock Vision",
                response_time=2.1,
                success=True
            )
        elif "precision_overlays" in filename:
            # Precision overlays should show excellent results
            result = LLMTestResult(
                model_name=model,
                approach="precision_overlays",
                extracted_text="Mock extracted replacement text only",
                contains_original=False,
                contains_replacement=True,
                parsing_method="Mock Vision",
                response_time=1.8,
                success=True
            )
        else:
            # Custom fonts approach
            result = LLMTestResult(
                model_name=model,
                approach="custom_fonts",
                extracted_text="Mock extracted mixed text",
                contains_original=True,
                contains_replacement=True,
                parsing_method="Mock Vision",
                response_time=1.2,
                success=True
            )

        results.append(result)

    return results


def validate_llm_result(result, mapping: Dict[str, str]):
    """Validate LLM result against expected word mappings"""
    # Check if extracted text contains original or replacement words
    extracted_text = result.extracted_text.lower()

    contains_original = any(original.lower() in extracted_text for original in mapping.keys())
    contains_replacement = any(replacement.lower() in extracted_text for replacement in mapping.values())

    # Update result with validation
    result.contains_original = contains_original
    result.contains_replacement = contains_replacement

    return result


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5002)
