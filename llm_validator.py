"""
Real LLM Parsing Validation System
Tests what LLMs actually extract from manipulated PDFs
"""

import base64
import time
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass
import openai
import fitz  # PyMuPDF
from difflib import SequenceMatcher

@dataclass
class ValidationResult:
    """Results of LLM parsing validation"""
    model: str
    pdf_approach: str
    raw_extracted_text: str
    cleaned_extracted_text: str
    expected_words: List[str]
    found_words: List[str]
    missing_words: List[str]
    unexpected_words: List[str]
    effectiveness_score: float
    parsing_success: bool
    validation_details: Dict

class LLMParsingValidator:
    """Validate what LLMs actually read from our manipulated PDFs"""

    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]

    def validate_pdf_set(self, pdf_files: Dict[str, bytes], expected_mapping: Dict[str, str]) -> List[ValidationResult]:
        """Validate a complete set of PDF manipulations"""
        results = []

        print("🔬 REAL LLM PARSING VALIDATION")
        print("=" * 50)

        for approach_name, pdf_bytes in pdf_files.items():
            print(f"\n📄 Testing {approach_name}:")

            for model in self.models:
                try:
                    result = self._validate_single_pdf(
                        pdf_bytes, model, approach_name, expected_mapping
                    )
                    results.append(result)

                    print(f"   • {model}: {result.effectiveness_score:.1%} effective")
                    print(f"     Expected: {len(result.expected_words)} words")
                    print(f"     Found: {len(result.found_words)} words")
                    print(f"     Missing: {len(result.missing_words)} words")

                except Exception as e:
                    print(f"   ❌ {model}: Error - {e}")

        return results

    def _validate_single_pdf(self, pdf_bytes: bytes, model: str, approach: str, mapping: Dict[str, str]) -> ValidationResult:
        """Validate what a single LLM model extracts from one PDF"""

        # Step 1: Extract text using LLM Vision API
        raw_text = self._extract_text_via_llm(pdf_bytes, model)
        cleaned_text = self._clean_extracted_text(raw_text)

        # Step 2: Determine what we expected based on approach
        expected_words, unexpected_words = self._determine_expected_content(approach, mapping)

        # Step 3: Analyze what was actually found
        found_words = self._find_words_in_text(expected_words, cleaned_text)
        missing_words = [word for word in expected_words if word not in found_words]
        actually_unexpected = self._find_words_in_text(unexpected_words, cleaned_text)

        # Step 4: Calculate effectiveness score
        effectiveness_score = self._calculate_effectiveness(
            approach, expected_words, found_words, actually_unexpected
        )

        # Step 5: Detailed analysis
        validation_details = {
            "word_matches": self._detailed_word_analysis(cleaned_text, mapping),
            "text_similarity": self._calculate_text_similarity(cleaned_text, mapping),
            "parsing_confidence": len(found_words) / max(len(expected_words), 1)
        }

        return ValidationResult(
            model=model,
            pdf_approach=approach,
            raw_extracted_text=raw_text,
            cleaned_extracted_text=cleaned_text,
            expected_words=expected_words,
            found_words=found_words,
            missing_words=missing_words,
            unexpected_words=actually_unexpected,
            effectiveness_score=effectiveness_score,
            parsing_success=len(found_words) > 0,
            validation_details=validation_details
        )

    def _extract_text_via_llm(self, pdf_bytes: bytes, model: str) -> str:
        """Extract text using LLM Vision API"""
        # Convert PDF to image for vision API
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap(dpi=200)  # Higher DPI for better OCR
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
                            "text": "Extract ALL text from this image. Return ONLY the text content, word for word, with no explanations, formatting, or additional comments. If you see any text, transcribe it exactly."
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
            max_tokens=1500,
            temperature=0  # Deterministic extraction
        )

        return response.choices[0].message.content.strip()

    def _clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        import re
        # Remove extra whitespace, normalize punctuation
        cleaned = re.sub(r'\s+', ' ', text)
        cleaned = cleaned.strip()
        return cleaned.lower()

    def _determine_expected_content(self, approach: str, mapping: Dict[str, str]) -> Tuple[List[str], List[str]]:
        """Determine what words we expect to find vs not find"""
        if approach == "original":
            # Original PDF should contain original words, not replacements
            expected = list(mapping.keys())  # Original words
            unexpected = list(mapping.values())  # Replacement words
        else:
            # Manipulated PDFs should contain replacements, not originals
            expected = list(mapping.values())  # Replacement words
            unexpected = list(mapping.keys())  # Original words

        return [word.lower() for word in expected], [word.lower() for word in unexpected]

    def _find_words_in_text(self, word_list: List[str], text: str) -> List[str]:
        """Find which words from the list appear in the text"""
        found = []
        for word in word_list:
            if word.lower() in text.lower():
                found.append(word)
        return found

    def _calculate_effectiveness(self, approach: str, expected: List[str], found: List[str], unexpected: List[str]) -> float:
        """Calculate how effective the manipulation was"""
        if approach == "original":
            # Original should be 0% effective (control group)
            return 0.0

        # For manipulated PDFs:
        # Perfect score = all expected words found, no unexpected words found
        expected_score = len(found) / max(len(expected), 1)  # Found expected words
        unexpected_penalty = len(unexpected) / max(len(expected), 1)  # Found unexpected words

        effectiveness = max(0.0, expected_score - (unexpected_penalty * 0.5))
        return min(1.0, effectiveness)

    def _detailed_word_analysis(self, text: str, mapping: Dict[str, str]) -> Dict:
        """Detailed analysis of word matches"""
        analysis = {}

        for original, replacement in mapping.items():
            analysis[f"{original}→{replacement}"] = {
                "original_found": original.lower() in text.lower(),
                "replacement_found": replacement.lower() in text.lower(),
                "success": replacement.lower() in text.lower() and original.lower() not in text.lower()
            }

        return analysis

    def _calculate_text_similarity(self, extracted_text: str, mapping: Dict[str, str]) -> Dict:
        """Calculate similarity metrics"""
        # Create expected text variations
        original_text_pattern = " ".join(mapping.keys()).lower()
        replacement_text_pattern = " ".join(mapping.values()).lower()

        original_similarity = SequenceMatcher(None, extracted_text, original_text_pattern).ratio()
        replacement_similarity = SequenceMatcher(None, extracted_text, replacement_text_pattern).ratio()

        return {
            "original_similarity": original_similarity,
            "replacement_similarity": replacement_similarity,
            "manipulation_detected": replacement_similarity > original_similarity
        }

def validate_manipulation_effectiveness(pdf_files: Dict[str, bytes], mapping: Dict[str, str], api_key: str) -> None:
    """Main validation function - tests real LLM parsing"""

    validator = LLMParsingValidator(api_key)
    results = validator.validate_pdf_set(pdf_files, mapping)

    # Generate comprehensive report
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE VALIDATION REPORT")
    print("=" * 60)

    # Group results by approach
    by_approach = {}
    for result in results:
        if result.pdf_approach not in by_approach:
            by_approach[result.pdf_approach] = []
        by_approach[result.pdf_approach].append(result)

    # Report by approach
    for approach, approach_results in by_approach.items():
        print(f"\n🔍 {approach.upper()}:")

        avg_effectiveness = sum(r.effectiveness_score for r in approach_results) / len(approach_results)
        print(f"   📈 Average Effectiveness: {avg_effectiveness:.1%}")

        successful_models = [r.model for r in approach_results if r.parsing_success]
        print(f"   ✅ Successful Models: {len(successful_models)}/{len(approach_results)}")

        # Show word detection details
        if approach_results:
            sample_result = approach_results[0]
            print(f"   📝 Expected Words: {sample_result.expected_words}")
            print(f"   🎯 Word Detection Success Rate: {len(sample_result.found_words)}/{len(sample_result.expected_words)}")

            # Show actual extracted text sample
            sample_text = sample_result.cleaned_extracted_text[:100] + "..." if len(sample_result.cleaned_extracted_text) > 100 else sample_result.cleaned_extracted_text
            print(f"   📄 Sample Extracted: '{sample_text}'")

    # Overall summary
    all_manipulated_results = [r for r in results if r.pdf_approach != "original"]
    if all_manipulated_results:
        overall_effectiveness = sum(r.effectiveness_score for r in all_manipulated_results) / len(all_manipulated_results)
        print(f"\n🎯 OVERALL MANIPULATION EFFECTIVENESS: {overall_effectiveness:.1%}")

        best_approach = max(by_approach.items(), key=lambda x: sum(r.effectiveness_score for r in x[1]) / len(x[1]))
        print(f"🏆 BEST APPROACH: {best_approach[0]} ({sum(r.effectiveness_score for r in best_approach[1]) / len(best_approach[1]):.1%})")

    # Save detailed results
    results_data = []
    for result in results:
        results_data.append({
            "model": result.model,
            "approach": result.pdf_approach,
            "effectiveness": result.effectiveness_score,
            "extracted_text": result.cleaned_extracted_text,
            "word_analysis": result.validation_details["word_matches"],
            "similarity_metrics": result.validation_details["text_similarity"]
        })

    with open("validation_results.json", "w") as f:
        json.dump(results_data, f, indent=2)

    print(f"\n💾 Detailed results saved to: validation_results.json")

if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python llm_validator.py <openai_api_key>")
        sys.exit(1)

    api_key = sys.argv[1]

    # Test with existing generated PDFs
    import os
    pdf_files = {}

    test_files = [
        "tests/generated_original.pdf",
        "tests/generated_approach_2_dual_layer.pdf",
        "tests/generated_approach_3_precision_overlays.pdf"
    ]

    for file_path in test_files:
        if os.path.exists(file_path):
            approach_name = file_path.split("_", 2)[-1].replace(".pdf", "")
            with open(file_path, "rb") as f:
                pdf_files[approach_name] = f.read()

    # Example mapping
    test_mapping = {
        "brown": "bronze",
        "dog": "cat",
        "quick": "fishes"
    }

    if pdf_files:
        validate_manipulation_effectiveness(pdf_files, test_mapping, api_key)
    else:
        print("❌ No test PDF files found. Generate PDFs first using the web interface.")