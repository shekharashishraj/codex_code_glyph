"""
Integrated Auto-Processing System
Combines automatic mapping generation with all 3 manipulation approaches
"""

from __future__ import annotations

import os
from typing import Dict, List, Tuple
from pathlib import Path

from auto_mapping_generator import AutoMappingGenerator
from advanced_approaches import (
    approach_1_custom_font_remapping,
    approach_2_dual_layer_rendering,
    approach_3_precision_overlays
)
from llm_pdf_tester import LLMPDFTester
from glyph_mapper.pdf_processor import extract_text_preview


class IntegratedAutoProcessor:
    """Integrated system for automatic PDF manipulation and testing"""

    def __init__(self):
        self.mapping_generator = AutoMappingGenerator()
        self.llm_tester = LLMPDFTester()

    def process_pdf_comprehensive(self, pdf_bytes: bytes, strategy: str = 'moderate') -> Dict:
        """Complete PDF processing pipeline with automatic mappings"""
        print("🚀 INTEGRATED AUTO-PROCESSING PIPELINE")
        print("=" * 60)

        # Step 1: Generate automatic mappings
        print("🔍 Step 1: Analyzing PDF and generating mappings...")
        test_sets = self.mapping_generator.generate_comprehensive_test_set(pdf_bytes)

        if strategy not in test_sets:
            strategy = 'moderate'
            print(f"⚠️  Strategy not found, defaulting to: {strategy}")

        selected_mappings = test_sets[strategy]
        print(f"✅ Selected {len(selected_mappings)} mappings from '{strategy}' strategy")

        # Step 2: Apply all 3 approaches
        print("\n🛠️  Step 2: Applying all 3 manipulation approaches...")

        manipulated_pdfs = {
            'original': pdf_bytes,
            'approach_1_custom_fonts': approach_1_custom_font_remapping(pdf_bytes, selected_mappings),
            'approach_2_dual_layer': approach_2_dual_layer_rendering(pdf_bytes, selected_mappings),
            'approach_3_precision_overlays': approach_3_precision_overlays(pdf_bytes, selected_mappings)
        }

        # Step 3: Validate text extraction for each approach
        print("\n📝 Step 3: Validating text extraction...")
        validation_results = {}

        for approach_name, pdf_data in manipulated_pdfs.items():
            extracted_text = extract_text_preview(pdf_data)

            # Check what was extracted
            contains_original = any(original.lower() in extracted_text.lower()
                                  for original in selected_mappings.keys())
            contains_replacement = any(replacement.lower() in extracted_text.lower()
                                     for replacement in selected_mappings.values())

            validation_results[approach_name] = {
                'extracted_text': extracted_text,
                'contains_original': contains_original,
                'contains_replacement': contains_replacement,
                'text_length': len(extracted_text),
                'success_score': self._calculate_success_score(
                    contains_original, contains_replacement, approach_name
                )
            }

            status_emoji = "✅" if validation_results[approach_name]['success_score'] > 0.5 else "❌"
            print(f"   {status_emoji} {approach_name}: Score {validation_results[approach_name]['success_score']:.2f}")

        # Step 4: Save all versions
        print("\n💾 Step 4: Saving all PDF versions...")
        saved_files = {}

        for approach_name, pdf_data in manipulated_pdfs.items():
            filename = f"tests/auto_{approach_name}.pdf"
            with open(filename, 'wb') as f:
                f.write(pdf_data)
            saved_files[approach_name] = filename
            print(f"   📄 {filename}")

        # Step 5: Create comprehensive report
        print("\n📊 Step 5: Generating comprehensive report...")
        report = self._create_comprehensive_report(
            test_sets, selected_mappings, strategy, validation_results, saved_files
        )

        return {
            'mappings': selected_mappings,
            'strategy': strategy,
            'all_strategies': test_sets,
            'manipulated_pdfs': manipulated_pdfs,
            'validation_results': validation_results,
            'saved_files': saved_files,
            'report': report
        }

    def _calculate_success_score(self, contains_original: bool, contains_replacement: bool, approach_name: str) -> float:
        """Calculate success score for each approach"""
        if approach_name == 'original':
            # Original should contain original words, not replacements
            return 1.0 if contains_original and not contains_replacement else 0.0
        else:
            # Modified approaches should contain replacements, not original
            if contains_replacement and not contains_original:
                return 1.0  # Perfect success
            elif contains_replacement and contains_original:
                return 0.7  # Partial success
            elif contains_replacement:
                return 0.8  # Good success
            else:
                return 0.0  # Failed

    def _create_comprehensive_report(self, all_strategies, selected_mappings, strategy, validation_results, saved_files) -> str:
        """Create comprehensive processing report"""
        report = []
        report.append("📋 INTEGRATED AUTO-PROCESSING REPORT")
        report.append("=" * 60)

        # Strategy summary
        report.append(f"\n🎯 SELECTED STRATEGY: {strategy.upper()}")
        report.append(f"   • Mappings generated: {len(selected_mappings)}")

        # Mapping details
        report.append(f"\n🔄 WORD MAPPINGS:")
        for i, (original, replacement) in enumerate(selected_mappings.items(), 1):
            report.append(f"   {i:2d}. {original:<15} → {replacement}")

        # All strategies summary
        report.append(f"\n📊 ALL STRATEGY OPTIONS:")
        for strat_name, mappings in all_strategies.items():
            report.append(f"   • {strat_name.capitalize():<12}: {len(mappings):2d} mappings")

        # Validation results
        report.append(f"\n✅ VALIDATION RESULTS:")
        for approach_name, results in validation_results.items():
            score = results['success_score']
            status = "🟢 EXCELLENT" if score >= 0.9 else "🟡 GOOD" if score >= 0.7 else "🔴 NEEDS WORK"
            report.append(f"   • {approach_name:<25}: {status} (Score: {score:.2f})")

            # Show what was detected
            orig_status = "🔴 YES" if results['contains_original'] else "⚪ NO"
            repl_status = "🟢 YES" if results['contains_replacement'] else "⚪ NO"
            report.append(f"     Original words detected: {orig_status}")
            report.append(f"     Replacement words detected: {repl_status}")
            report.append("")

        # File outputs
        report.append(f"💾 GENERATED FILES:")
        for approach_name, filename in saved_files.items():
            report.append(f"   • {filename}")

        # Recommendations
        report.append(f"\n💡 RECOMMENDATIONS:")

        best_approach = max(validation_results.items(), key=lambda x: x[1]['success_score'])
        report.append(f"   • Best performing approach: {best_approach[0]}")
        report.append(f"   • Best score achieved: {best_approach[1]['success_score']:.2f}")

        working_approaches = [name for name, results in validation_results.items()
                            if results['success_score'] > 0.5 and name != 'original']
        report.append(f"   • Working approaches: {len(working_approaches)}/3")

        if len(working_approaches) >= 2:
            report.append("   • ✅ Multiple approaches working - excellent success rate!")
        elif len(working_approaches) == 1:
            report.append("   • ⚠️  Single approach working - consider refinement")
        else:
            report.append("   • ❌ No approaches fully working - needs investigation")

        # LLM Testing suggestion
        report.append(f"\n🧪 NEXT STEPS:")
        report.append("   • Run LLM tests to validate against real models")
        report.append("   • Use web interface: http://127.0.0.1:5001/llm-tester")
        report.append("   • Upload the generated PDF files for testing")

        return "\n".join(report)

    def run_comprehensive_llm_tests(self, results: Dict) -> Dict:
        """Run comprehensive LLM tests on all generated approaches"""
        print("🧪 RUNNING COMPREHENSIVE LLM TESTS")
        print("=" * 50)

        manipulated_pdfs = results['manipulated_pdfs']
        selected_mappings = results['mappings']

        # Run LLM tests
        llm_results = self.llm_tester.test_all_models_all_approaches(manipulated_pdfs)

        # Calculate effectiveness scores
        effectiveness_scores = {}
        for approach_name, approach_results in llm_results.items():
            if approach_name == 'original':
                continue

            successful_results = [r for r in approach_results if r.success]
            if successful_results:
                replacement_detected = sum(1 for r in successful_results if r.contains_replacement)
                original_detected = sum(1 for r in successful_results if r.contains_original)

                # Calculate effectiveness (high replacement detection, low original detection)
                effectiveness = (replacement_detected - original_detected * 0.5) / len(successful_results)
                effectiveness_scores[approach_name] = max(0, effectiveness)
            else:
                effectiveness_scores[approach_name] = 0

        # Create LLM test report
        llm_report = self._create_llm_test_report(llm_results, effectiveness_scores, selected_mappings)

        return {
            'llm_results': llm_results,
            'effectiveness_scores': effectiveness_scores,
            'llm_report': llm_report
        }

    def _create_llm_test_report(self, llm_results: Dict, effectiveness_scores: Dict, mappings: Dict) -> str:
        """Create comprehensive LLM test report"""
        report = []
        report.append("🤖 LLM TESTING COMPREHENSIVE REPORT")
        report.append("=" * 60)

        # Mappings tested
        report.append(f"\n🔄 MAPPINGS TESTED:")
        for original, replacement in mappings.items():
            report.append(f"   • {original} → {replacement}")

        # Overall effectiveness
        report.append(f"\n📈 OVERALL EFFECTIVENESS:")
        for approach_name, score in effectiveness_scores.items():
            status = "🟢 EXCELLENT" if score >= 0.8 else "🟡 GOOD" if score >= 0.6 else "🔴 NEEDS WORK"
            report.append(f"   • {approach_name:<25}: {status} ({score:.2f})")

        # Model-by-model results
        report.append(f"\n🔍 DETAILED MODEL RESULTS:")
        for approach_name, results in llm_results.items():
            if approach_name == 'original':
                continue

            report.append(f"\n   📋 {approach_name.upper()}:")
            for result in results:
                if result.success:
                    orig_icon = "🔴" if result.contains_original else "⚪"
                    repl_icon = "🟢" if result.contains_replacement else "⚪"
                    report.append(f"      {result.model_name}: {orig_icon} Original | {repl_icon} Replacement")
                else:
                    report.append(f"      {result.model_name}: ❌ Error - {result.error}")

        return "\n".join(report)


def run_full_automated_pipeline(pdf_path: str, strategy: str = 'moderate'):
    """Run the complete automated pipeline on a PDF file"""
    print("🎯 FULL AUTOMATED PDF MANIPULATION PIPELINE")
    print("=" * 60)

    # Load PDF
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    print(f"📄 Processing: {pdf_path}")
    print(f"🎯 Strategy: {strategy}")

    # Initialize processor
    processor = IntegratedAutoProcessor()

    # Run comprehensive processing
    results = processor.process_pdf_comprehensive(pdf_bytes, strategy)

    # Display report
    print("\n" + results['report'])

    # Save report
    report_file = f"tests/integrated_report_{strategy}.txt"
    with open(report_file, 'w') as f:
        f.write(results['report'])
    print(f"\n💾 Full report saved: {report_file}")

    return results


def test_all_strategies():
    """Test all mapping strategies on the sample PDF"""
    print("🧪 TESTING ALL MAPPING STRATEGIES")
    print("=" * 50)

    strategies = ['conservative', 'moderate', 'aggressive', 'strategic']
    pdf_path = "tests/sample.pdf"

    all_results = {}

    for strategy in strategies:
        print(f"\n{'='*20} TESTING {strategy.upper()} {'='*20}")
        try:
            results = run_full_automated_pipeline(pdf_path, strategy)
            all_results[strategy] = results
        except Exception as e:
            print(f"❌ Error testing {strategy}: {e}")
            all_results[strategy] = None

    # Create comparison report
    print("\n📊 STRATEGY COMPARISON SUMMARY")
    print("=" * 50)

    for strategy, results in all_results.items():
        if results:
            mappings_count = len(results['mappings'])
            working_approaches = sum(1 for r in results['validation_results'].values()
                                   if r['success_score'] > 0.5 and r != results['validation_results'].get('original', {}))

            print(f"🎯 {strategy.upper():<12}: {mappings_count:2d} mappings, {working_approaches}/3 approaches working")
        else:
            print(f"❌ {strategy.upper():<12}: Failed")

    return all_results


if __name__ == "__main__":
    # Test with sample PDF using moderate strategy
    print("Starting automated pipeline test...")
    results = run_full_automated_pipeline("tests/sample.pdf", "moderate")

    # Optionally test all strategies
    print("\n" + "="*60)
    print("Would you like to test all strategies? (This will take longer)")
    # all_results = test_all_strategies()