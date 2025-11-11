#!/usr/bin/env python3
"""
Command Line Interface for PDF Manipulation and LLM Testing
Usage: python cli_test.py <pdf_file> [--api-key <key>] [--strategy <strategy>]
"""

import argparse
import json
import sys
import os
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Test PDF manipulation and LLM parsing')
    parser.add_argument('pdf_file', help='Path to PDF file')
    parser.add_argument('--api-key', help='OpenAI API key for real testing')
    parser.add_argument('--strategy', default='moderate',
                        choices=['conservative', 'moderate', 'aggressive', 'strategic'],
                        help='Mapping generation strategy')
    parser.add_argument('--test-mode', action='store_true',
                        help='Use mock testing (no API calls)')

    args = parser.parse_args()

    # Check if PDF file exists
    if not os.path.exists(args.pdf_file):
        print(f"❌ Error: PDF file '{args.pdf_file}' not found")
        sys.exit(1)

    print("🎯 PDF Manipulation & LLM Testing CLI")
    print("=" * 50)
    print(f"📄 PDF File: {args.pdf_file}")
    print(f"🎲 Strategy: {args.strategy}")
    print(f"🧪 Test Mode: {'Mock' if args.test_mode else 'Real API'}")
    print()

    try:
        # Step 1: Generate mappings
        print("🔍 Step 1: Generating word mappings...")
        from auto_mapping_generator import AutoMappingGenerator

        with open(args.pdf_file, 'rb') as f:
            pdf_bytes = f.read()

        generator = AutoMappingGenerator()
        test_sets = generator.generate_comprehensive_test_set(pdf_bytes)
        analysis = generator.analyze_pdf_content(pdf_bytes)

        mapping = test_sets.get(args.strategy, test_sets.get('moderate', {}))

        print(f"✅ Generated {len(mapping)} word mappings:")
        for orig, repl in list(mapping.items())[:5]:  # Show first 5
            print(f"   • {orig} → {repl}")
        if len(mapping) > 5:
            print(f"   ... and {len(mapping) - 5} more")
        print()

        # Step 2: Generate PDF variants
        print("🛠️ Step 2: Generating PDF variants...")
        from advanced_approaches import (
            approach_1_custom_font_remapping,
            approach_2_dual_layer_rendering,
            approach_3_precision_overlays
        )

        # Create output directory
        output_dir = Path('cli_output')
        output_dir.mkdir(exist_ok=True)

        # Generate all PDFs
        results = {
            "original": pdf_bytes,
            "approach_1_custom_fonts": approach_1_custom_font_remapping(pdf_bytes, mapping),
            "approach_2_dual_layer": approach_2_dual_layer_rendering(pdf_bytes, mapping),
            "approach_3_precision_overlays": approach_3_precision_overlays(pdf_bytes, mapping)
        }

        generated_files = []
        for approach_name, pdf_data in results.items():
            filename = f"cli_{approach_name}.pdf"
            filepath = output_dir / filename

            with open(filepath, "wb") as f:
                f.write(pdf_data)
            generated_files.append(str(filepath))
            print(f"   ✅ Generated: {filepath}")

        print()

        # Step 3: LLM Testing
        print("🧪 Step 3: Testing with LLM models...")

        if args.test_mode or not args.api_key:
            print("📝 Using mock testing mode (no API calls)")
            # Mock testing
            from app import create_mock_single_pdf_results

            for filepath in generated_files:
                filename = os.path.basename(filepath)
                print(f"\n🔬 Testing {filename}:")

                mock_results = create_mock_single_pdf_results(filename, mapping)

                for result in mock_results[:2]:  # Show first 2 models
                    original_status = "❌" if result.contains_original else "✅"
                    replacement_status = "✅" if result.contains_replacement else "❌"

                    print(f"   • {result.model_name}:")
                    print(f"     Original detected: {original_status}")
                    print(f"     Replacement detected: {replacement_status}")
        else:
            print("🔗 Using real OpenAI API testing")
            from llm_pdf_tester import LLMPDFTester

            tester = LLMPDFTester(api_key=args.api_key)

            for filepath in generated_files:
                with open(filepath, 'rb') as f:
                    pdf_data = f.read()

                filename = os.path.basename(filepath)
                print(f"\n🔬 Testing {filename}:")

                # Test with first 2 models to save API calls
                for model in tester.openai_models[:2]:
                    try:
                        result = tester.test_openai_vision_api(pdf_data, model)
                        original_status = "❌" if result.contains_original else "✅"
                        replacement_status = "✅" if result.contains_replacement else "❌"

                        print(f"   • {model}:")
                        print(f"     Original detected: {original_status}")
                        print(f"     Replacement detected: {replacement_status}")
                        print(f"     Response time: {result.response_time:.2f}s")
                    except Exception as e:
                        print(f"   ❌ Error testing {model}: {e}")

        print()
        print("🎯 Testing Complete!")
        print(f"📁 Generated files saved in: {output_dir}")
        print()
        print("💡 Next Steps:")
        print("   • View PDFs to verify they look identical")
        print("   • Upload to different LLM interfaces to test parsing")
        print("   • Use the web interface for more detailed analysis")
        print(f"   🌐 Web Interface: http://127.0.0.1:5001/llm-tester")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()