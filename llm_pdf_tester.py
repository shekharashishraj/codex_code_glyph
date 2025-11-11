"""
LLM PDF Parsing Test System
Tests how different LLMs parse our manipulated PDFs via API
"""

import os
import base64
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
import openai
from pathlib import Path

# Configure OpenAI API (will be set dynamically)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


@dataclass
class LLMTestResult:
    model_name: str
    approach: str
    extracted_text: str
    contains_original: bool
    contains_replacement: bool
    parsing_method: str
    response_time: float
    success: bool
    error: Optional[str] = None


class LLMPDFTester:
    """Test how various LLMs parse our manipulated PDFs"""

    def __init__(self, api_key: str = None):
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            self.client = openai.OpenAI(api_key=api_key)
        elif OPENAI_API_KEY:
            self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        else:
            self.client = None

        # OpenAI models to test
        self.openai_models = [
            "gpt-4o",           # Latest GPT-4 with vision
            "gpt-4o-mini",      # Smaller GPT-4 variant
            "gpt-4-turbo",      # GPT-4 Turbo
            "gpt-3.5-turbo",    # GPT-3.5
        ]

    def encode_pdf_for_api(self, pdf_bytes: bytes) -> str:
        """Encode PDF as base64 for API transmission"""
        return base64.b64encode(pdf_bytes).decode('utf-8')

    def test_openai_vision_api(self, pdf_bytes: bytes, model: str) -> LLMTestResult:
        """Test OpenAI vision API with PDF"""
        start_time = time.time()

        try:
            # For vision models, we need to convert PDF pages to images first
            # OpenAI vision API doesn't directly accept PDFs
            import fitz  # PyMuPDF

            # Convert first page to PNG
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            doc.close()

            img_b64 = base64.b64encode(img_bytes).decode('utf-8')

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please extract and transcribe all the text you can see in this image. Return only the text content, no explanations."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_b64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )

            extracted_text = response.choices[0].message.content.strip()
            response_time = time.time() - start_time

            return LLMTestResult(
                model_name=model,
                approach="vision_api",
                extracted_text=extracted_text,
                contains_original=any(word in extracted_text.lower() for word in ["dog", "dogs"]),
                contains_replacement=any(word in extracted_text.lower() for word in ["dragon", "owls"]),
                parsing_method="OCR/Vision",
                response_time=response_time,
                success=True
            )

        except Exception as e:
            return LLMTestResult(
                model_name=model,
                approach="vision_api",
                extracted_text="",
                contains_original=False,
                contains_replacement=False,
                parsing_method="OCR/Vision",
                response_time=time.time() - start_time,
                success=False,
                error=str(e)
            )

    def test_openai_file_upload(self, pdf_bytes: bytes, model: str) -> LLMTestResult:
        """Test OpenAI API with file upload (if supported)"""
        start_time = time.time()

        try:
            # Create temporary file
            temp_path = f"/tmp/claude/test_{model.replace('-', '_')}.pdf"
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)

            with open(temp_path, "wb") as f:
                f.write(pdf_bytes)

            # Try to upload file and process
            with open(temp_path, "rb") as f:
                file_response = self.client.files.create(
                    file=f,
                    purpose="assistants"  # or "fine-tune" depending on use case
                )

            # This is experimental - OpenAI's file processing capabilities vary
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": f"Extract all text from the uploaded PDF file {file_response.id}. Return only the text content."
                    }
                ],
                max_tokens=1000
            )

            extracted_text = response.choices[0].message.content.strip()
            response_time = time.time() - start_time

            # Clean up
            os.unlink(temp_path)
            self.client.files.delete(file_response.id)

            return LLMTestResult(
                model_name=model,
                approach="file_upload",
                extracted_text=extracted_text,
                contains_original=any(word in extracted_text.lower() for word in ["dog", "dogs"]),
                contains_replacement=any(word in extracted_text.lower() for word in ["dragon", "owls"]),
                parsing_method="Direct PDF Processing",
                response_time=response_time,
                success=True
            )

        except Exception as e:
            return LLMTestResult(
                model_name=model,
                approach="file_upload",
                extracted_text="",
                contains_original=False,
                contains_replacement=False,
                parsing_method="Direct PDF Processing",
                response_time=time.time() - start_time,
                success=False,
                error=str(e)
            )

    def test_all_approaches_single_model(self, pdf_bytes: bytes, model: str) -> List[LLMTestResult]:
        """Test all available methods for a single model"""
        results = []

        print(f"🔍 Testing {model}...")

        # Test Vision API (convert PDF to image)
        print(f"   📸 Testing vision API...")
        vision_result = self.test_openai_vision_api(pdf_bytes, model)
        results.append(vision_result)

        # Test File Upload (if supported)
        print(f"   📁 Testing file upload...")
        file_result = self.test_openai_file_upload(pdf_bytes, model)
        results.append(file_result)

        return results

    def test_all_models_all_approaches(self, pdf_files: Dict[str, bytes]) -> Dict[str, List[LLMTestResult]]:
        """Test all models with all PDF approaches"""
        all_results = {}

        for approach_name, pdf_bytes in pdf_files.items():
            print(f"\n🧪 TESTING {approach_name.upper()}")
            print("=" * 50)

            approach_results = []

            for model in self.openai_models:
                model_results = self.test_all_approaches_single_model(pdf_bytes, model)
                approach_results.extend(model_results)

                # Add delay to respect rate limits
                time.sleep(1)

            all_results[approach_name] = approach_results

        return all_results


def create_test_pdfs() -> Dict[str, bytes]:
    """Create all 3 approaches for testing"""
    print("📄 Creating test PDFs...")

    # Load original PDF
    with open("tests/sample.pdf", "rb") as f:
        original_pdf = f.read()

    # Import our advanced approaches
    from advanced_approaches import (
        approach_1_custom_font_remapping,
        approach_2_dual_layer_rendering,
        approach_3_precision_overlays
    )

    mapping = {"dog.": "dragon!", "dogs": "owls"}

    pdfs = {
        "original": original_pdf,
        "approach_1_custom_fonts": approach_1_custom_font_remapping(original_pdf, mapping),
        "approach_2_dual_layer": approach_2_dual_layer_rendering(original_pdf, mapping),
        "approach_3_precision_overlays": approach_3_precision_overlays(original_pdf, mapping)
    }

    print(f"✅ Created {len(pdfs)} PDFs for testing")
    return pdfs


def format_results_table(results: Dict[str, List[LLMTestResult]]) -> str:
    """Format results as a nice table"""
    table = []
    table.append("📊 LLM PDF PARSING RESULTS")
    table.append("=" * 80)

    for approach_name, approach_results in results.items():
        table.append(f"\n🔧 {approach_name.upper()}")
        table.append("-" * 40)

        for result in approach_results:
            status = "✅" if result.success else "❌"
            original_detected = "🔴" if result.contains_original else "⚪"
            replacement_detected = "🟢" if result.contains_replacement else "⚪"

            table.append(f"{status} {result.model_name} ({result.parsing_method})")
            table.append(f"   Time: {result.response_time:.2f}s")
            table.append(f"   Original words detected: {original_detected}")
            table.append(f"   Replacement words detected: {replacement_detected}")

            if result.success:
                # Show first 100 chars of extracted text
                preview = result.extracted_text[:100] + "..." if len(result.extracted_text) > 100 else result.extracted_text
                table.append(f"   Extracted: '{preview}'")
            else:
                table.append(f"   Error: {result.error}")
            table.append("")

    return "\n".join(table)


def analyze_effectiveness(results: Dict[str, List[LLMTestResult]]) -> str:
    """Analyze which approaches work best"""
    analysis = []
    analysis.append("🎯 EFFECTIVENESS ANALYSIS")
    analysis.append("=" * 50)

    for approach_name, approach_results in results.items():
        successful_results = [r for r in approach_results if r.success]

        if not successful_results:
            analysis.append(f"\n❌ {approach_name}: No successful tests")
            continue

        # Count how many saw original vs replacement
        saw_original = sum(1 for r in successful_results if r.contains_original)
        saw_replacement = sum(1 for r in successful_results if r.contains_replacement)
        total = len(successful_results)

        analysis.append(f"\n📈 {approach_name}:")
        analysis.append(f"   Success rate: {total}/{len(approach_results)} tests")
        analysis.append(f"   Saw original text: {saw_original}/{total} ({saw_original/total*100:.1f}%)")
        analysis.append(f"   Saw replacement text: {saw_replacement}/{total} ({saw_replacement/total*100:.1f}%)")

        # Effectiveness score
        if approach_name == "original":
            # Original should show original text, not replacements
            effectiveness = saw_original / total if total > 0 else 0
        else:
            # Modified approaches should show replacements, not original
            effectiveness = saw_replacement / total if total > 0 else 0

        analysis.append(f"   Effectiveness: {effectiveness*100:.1f}%")

        if approach_name != "original" and saw_original > 0:
            analysis.append(f"   ⚠️  Still detecting original text - needs improvement")
        if approach_name != "original" and saw_replacement == 0:
            analysis.append(f"   ❌ Not detecting replacement text - approach failed")

    return "\n".join(analysis)


def main():
    """Main testing function"""
    print("🚀 LLM PDF PARSING TEST SUITE")
    print("Testing how LLMs parse our manipulated PDFs")
    print("=" * 60)

    # Create test PDFs
    test_pdfs = create_test_pdfs()

    # Initialize tester
    tester = LLMPDFTester()

    # Run all tests
    print("\n🧪 Running comprehensive LLM tests...")
    results = tester.test_all_models_all_approaches(test_pdfs)

    # Format and display results
    print("\n" + format_results_table(results))
    print("\n" + analyze_effectiveness(results))

    # Save results to file
    results_file = "tests/llm_parsing_results.txt"
    with open(results_file, "w") as f:
        f.write(format_results_table(results))
        f.write("\n\n")
        f.write(analyze_effectiveness(results))

    print(f"\n💾 Results saved to {results_file}")
    print("\n✅ Testing complete!")


if __name__ == "__main__":
    main()