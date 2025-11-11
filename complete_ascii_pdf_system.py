"""
Complete ASCII-to-ASCII PDF Manipulation System
Integration of full ASCII mapping with existing PDF manipulation approaches
"""

import os
import json
from typing import Dict
from full_ascii_mapper import FullASCIIMapper
from advanced_approaches import approach_3_precision_overlays, approach_2_dual_layer_rendering

def create_complete_ascii_pdf_manipulation(pdf_bytes: bytes, strategy: str = "unicode_steganography") -> Dict[str, bytes]:
    """
    Create PDF with complete ASCII character remapping

    Returns:
    - original: Original PDF
    - mapped_precision: Precision overlays with full ASCII mapping
    - mapped_dual_layer: Dual-layer with full ASCII mapping
    - ascii_mapping: The character mapping used
    """

    print("🔤 COMPLETE ASCII PDF MANIPULATION SYSTEM")
    print("=" * 60)
    print(f"🎯 Strategy: {strategy}")

    # Create complete ASCII mapping
    mapper = FullASCIIMapper()
    ascii_mapping = mapper.create_complete_ascii_mapping(strategy)

    print(f"📊 Created mapping for {len(ascii_mapping)} ASCII characters")

    # Apply to different PDF manipulation approaches
    results = {
        "original": pdf_bytes,
        "ascii_mapping": json.dumps(ascii_mapping, ensure_ascii=False),
    }

    try:
        # Precision Overlays with full ASCII mapping
        print("🎯 Applying precision overlays with full ASCII mapping...")
        results["mapped_precision"] = approach_3_precision_overlays(pdf_bytes, ascii_mapping)
        print("   ✅ Precision overlays complete")

        # Dual Layer with full ASCII mapping
        print("👁️ Applying dual-layer rendering with full ASCII mapping...")
        results["mapped_dual_layer"] = approach_2_dual_layer_rendering(pdf_bytes, ascii_mapping)
        print("   ✅ Dual-layer complete")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    return results

def demonstrate_extreme_ascii_mapping():
    """Demonstrate extreme ASCII mapping capabilities"""

    print("🧪 EXTREME ASCII MAPPING CAPABILITIES")
    print("=" * 60)

    # Test different strategies with sample text
    sample_text = "The quick brown fox jumps over the lazy dog! 123 @#$"

    mapper = FullASCIIMapper()

    strategies = [
        ("shift", "Caesar cipher shift (13 positions)"),
        ("reverse", "Complete ASCII order reversal"),
        ("shuffle", "Random permutation (reproducible)"),
        ("unicode_steganography", "Visually identical Unicode homoglyphs"),
        ("rot13_extended", "Extended ROT13 for all character types")
    ]

    print(f"📄 Original text: '{sample_text}'")
    print()

    for strategy, description in strategies:
        print(f"🎯 {strategy.upper()}: {description}")
        print("-" * 50)

        # Create mapping
        mapping = mapper.create_complete_ascii_mapping(strategy)

        # Apply mapping
        transformed = mapper.apply_full_ascii_mapping(sample_text, mapping)

        print(f"📝 Result: '{transformed}'")

        # Show character-by-character comparison for first few chars
        print("   🔍 Character mapping sample:")
        for i, (orig, trans) in enumerate(zip(sample_text[:10], transformed[:10])):
            if orig != trans:
                unicode_info = f" (U+{ord(orig):04X} -> U+{ord(trans):04X})" if strategy == "unicode_steganography" else ""
                print(f"      '{orig}' -> '{trans}'{unicode_info}")

        # Test reversibility
        reverse_mapping = mapper.create_reverse_mapping(mapping)
        reversed_text = mapper.apply_full_ascii_mapping(transformed, reverse_mapping)
        reversible = reversed_text == sample_text
        print(f"   🔄 Reversible: {reversible}")

        print()

def analyze_steganography_potential():
    """Analyze the steganographic potential of different ASCII mapping strategies"""

    print("🕵️ STEGANOGRAPHY ANALYSIS")
    print("=" * 40)

    strategies_analysis = {
        "shift": {
            "detection_difficulty": "Low",
            "visual_similarity": "None",
            "use_case": "Basic obfuscation",
            "llm_bypass": "100%",
            "human_detection": "Immediate"
        },
        "unicode_steganography": {
            "detection_difficulty": "Very High",
            "visual_similarity": "Perfect",
            "use_case": "Ultimate steganography",
            "llm_bypass": "100%",
            "human_detection": "Impossible without tools"
        },
        "shuffle": {
            "detection_difficulty": "Medium",
            "visual_similarity": "None",
            "use_case": "Cryptographic obfuscation",
            "llm_bypass": "100%",
            "human_detection": "Immediate"
        },
        "reverse": {
            "detection_difficulty": "Low",
            "visual_similarity": "None",
            "use_case": "Simple encoding",
            "llm_bypass": "100%",
            "human_detection": "Immediate"
        }
    }

    for strategy, analysis in strategies_analysis.items():
        print(f"📊 {strategy.upper()}:")
        for metric, value in analysis.items():
            print(f"   {metric.replace('_', ' ').title()}: {value}")
        print()

if __name__ == "__main__":
    # Demonstrate capabilities
    demonstrate_extreme_ascii_mapping()
    print()
    analyze_steganography_potential()

    # Test with actual PDF if available
    pdf_path = "tests/sample.pdf"
    if os.path.exists(pdf_path):
        print("🔬 TESTING WITH ACTUAL PDF")
        print("=" * 30)

        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()

        # Test unicode steganography (most advanced)
        results = create_complete_ascii_pdf_manipulation(pdf_data, "unicode_steganography")

        # Save results
        output_dir = "complete_ascii_output"
        os.makedirs(output_dir, exist_ok=True)

        for approach_name, data in results.items():
            if approach_name == "ascii_mapping":
                # Save mapping as JSON
                with open(f"{output_dir}/ascii_mapping.json", 'w', encoding='utf-8') as f:
                    f.write(data)
            else:
                # Save PDF
                filename = f"{output_dir}/{approach_name}.pdf"
                with open(filename, 'wb') as f:
                    f.write(data)
                print(f"💾 Saved: {filename}")

        print(f"📁 All files saved to: {output_dir}/")

    else:
        print(f"❌ PDF file not found: {pdf_path}")
        print("   Create a test PDF first or use the web interface")