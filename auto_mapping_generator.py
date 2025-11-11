"""
Automatic Word Mapping Generator
Analyzes PDF content and generates strategic word mappings for maximum effectiveness
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple, Set
from collections import Counter
from glyph_mapper.pdf_processor import extract_text_preview, generate_word_occurrences, summarise_vocabulary


class AutoMappingGenerator:
    """Generate strategic word mappings from PDF analysis"""

    def __init__(self):
        # Common word categories for smart replacements
        self.word_categories = {
            'animals': {
                'dog': 'cat', 'dogs': 'cats', 'cat': 'dog', 'cats': 'dogs',
                'bird': 'fish', 'birds': 'fishes', 'fish': 'bird', 'fishes': 'birds',
                'mouse': 'rat', 'mice': 'rats', 'rat': 'mouse', 'rats': 'mice',
                'horse': 'pony', 'horses': 'ponies', 'cow': 'bull', 'cows': 'bulls'
            },
            'actions': {
                'run': 'walk', 'running': 'walking', 'walk': 'run', 'walking': 'running',
                'jump': 'leap', 'jumping': 'leaping', 'leap': 'jump', 'leaping': 'jumping',
                'eat': 'drink', 'eating': 'drinking', 'drink': 'eat', 'drinking': 'eating',
                'sleep': 'wake', 'sleeping': 'waking', 'wake': 'sleep', 'waking': 'sleeping'
            },
            'objects': {
                'car': 'truck', 'cars': 'trucks', 'truck': 'car', 'trucks': 'cars',
                'house': 'home', 'houses': 'homes', 'home': 'house', 'homes': 'houses',
                'book': 'paper', 'books': 'papers', 'paper': 'book', 'papers': 'books',
                'phone': 'device', 'phones': 'devices', 'computer': 'machine', 'computers': 'machines'
            },
            'people': {
                'man': 'person', 'men': 'people', 'woman': 'person', 'women': 'people',
                'child': 'kid', 'children': 'kids', 'boy': 'lad', 'boys': 'lads',
                'girl': 'lady', 'girls': 'ladies', 'person': 'individual', 'people': 'individuals'
            },
            'places': {
                'city': 'town', 'cities': 'towns', 'town': 'city', 'towns': 'cities',
                'school': 'academy', 'schools': 'academies', 'office': 'workplace', 'offices': 'workplaces',
                'park': 'garden', 'parks': 'gardens', 'store': 'shop', 'stores': 'shops'
            },
            'emotions': {
                'happy': 'joyful', 'sad': 'sorrowful', 'angry': 'furious', 'excited': 'thrilled',
                'calm': 'peaceful', 'worried': 'anxious', 'surprised': 'amazed', 'confused': 'puzzled'
            },
            'colors': {
                'red': 'crimson', 'blue': 'azure', 'green': 'emerald', 'yellow': 'golden',
                'black': 'dark', 'white': 'bright', 'gray': 'silver', 'brown': 'bronze'
            },
            'numbers': {
                'one': 'single', 'two': 'pair', 'three': 'triple', 'four': 'quad',
                'first': 'primary', 'second': 'secondary', 'third': 'tertiary', 'last': 'final'
            }
        }

        # Strategic replacement patterns
        self.strategic_patterns = {
            'opposite_sentiment': {
                'good': 'bad', 'bad': 'good', 'right': 'wrong', 'wrong': 'right',
                'true': 'false', 'false': 'true', 'yes': 'no', 'no': 'yes',
                'success': 'failure', 'failure': 'success', 'win': 'lose', 'lose': 'win'
            },
            'business_terms': {
                'profit': 'revenue', 'revenue': 'profit', 'cost': 'expense', 'expense': 'cost',
                'buy': 'purchase', 'purchase': 'buy', 'sell': 'trade', 'trade': 'sell',
                'company': 'corporation', 'corporation': 'company', 'business': 'enterprise'
            },
            'technical_terms': {
                'data': 'information', 'information': 'data', 'system': 'platform', 'platform': 'system',
                'network': 'connection', 'connection': 'network', 'software': 'program', 'program': 'software',
                'hardware': 'equipment', 'equipment': 'hardware', 'digital': 'electronic'
            }
        }

    def analyze_pdf_content(self, pdf_bytes: bytes) -> Dict[str, any]:
        """Comprehensive analysis of PDF content for mapping generation"""
        print("🔍 Analyzing PDF content...")

        # Extract text and word occurrences
        text_content = extract_text_preview(pdf_bytes, max_chars=10000)
        word_index = generate_word_occurrences(pdf_bytes)
        top_words = summarise_vocabulary(word_index, top_n=100)

        # Analyze text patterns
        sentences = re.split(r'[.!?]+', text_content)
        word_frequency = Counter(re.findall(r'\b\w+\b', text_content.lower()))

        # Identify document type/domain
        domain = self._identify_domain(text_content)

        # Get contextual information
        context_words = self._extract_context_words(text_content)

        analysis = {
            'text_content': text_content,
            'word_index': word_index,
            'top_words': top_words,
            'word_frequency': word_frequency,
            'sentences': sentences,
            'domain': domain,
            'context_words': context_words,
            'total_words': len(word_frequency),
            'unique_words': len(word_index),
            'sentence_count': len([s for s in sentences if s.strip()])
        }

        print(f"   📊 Found {analysis['unique_words']} unique words, {analysis['total_words']} total words")
        print(f"   📄 Document domain: {domain}")
        print(f"   📝 Sentences: {analysis['sentence_count']}")

        return analysis

    def _identify_domain(self, text: str) -> str:
        """Identify the domain/type of document"""
        text_lower = text.lower()

        domain_keywords = {
            'business': ['company', 'business', 'profit', 'revenue', 'market', 'customer', 'sales'],
            'technical': ['system', 'software', 'data', 'network', 'technology', 'digital', 'computer'],
            'academic': ['research', 'study', 'analysis', 'method', 'result', 'conclusion', 'paper'],
            'legal': ['law', 'legal', 'contract', 'agreement', 'clause', 'terms', 'liability'],
            'medical': ['patient', 'treatment', 'medical', 'health', 'diagnosis', 'therapy', 'clinical'],
            'news': ['report', 'news', 'today', 'yesterday', 'announced', 'sources', 'according'],
            'story': ['once', 'story', 'character', 'adventure', 'journey', 'tale', 'narrative'],
            'general': ['the', 'and', 'or', 'but', 'with', 'from', 'they']
        }

        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            domain_scores[domain] = score

        return max(domain_scores.items(), key=lambda x: x[1])[0]

    def _extract_context_words(self, text: str) -> Dict[str, List[str]]:
        """Extract context words around potential targets"""
        words = re.findall(r'\b\w+\b', text.lower())
        context_map = {}

        for i, word in enumerate(words):
            if len(word) > 3:  # Focus on longer words
                context_before = words[max(0, i-2):i]
                context_after = words[i+1:min(len(words), i+3)]
                context_map[word] = {
                    'before': context_before,
                    'after': context_after,
                    'frequency': words.count(word)
                }

        return context_map

    def generate_strategic_mappings(self, analysis: Dict[str, any], max_mappings: int = 15) -> Dict[str, str]:
        """Generate strategic word mappings based on analysis"""
        print("🎯 Generating strategic word mappings...")

        mappings = {}
        word_frequency = analysis['word_frequency']
        domain = analysis['domain']
        top_words = analysis['top_words']

        # Strategy 1: High-frequency words with category replacements
        print("   📈 Strategy 1: High-frequency word replacements")
        for word, count in top_words[:20]:  # Top 20 most frequent
            if len(word) > 3 and word.isalpha():  # Skip short words and non-alphabetic
                replacement = self._find_category_replacement(word, domain)
                if replacement and replacement != word:
                    mappings[word] = replacement
                    print(f"      {word} → {replacement} (frequency: {count})")

        # Strategy 2: Domain-specific replacements
        print("   🎯 Strategy 2: Domain-specific replacements")
        domain_mappings = self._get_domain_specific_mappings(domain)
        for original, replacement in domain_mappings.items():
            if original in word_frequency and len(mappings) < max_mappings:
                mappings[original] = replacement
                print(f"      {original} → {replacement} (domain: {domain})")

        # Strategy 3: Contextual opposites for high impact
        print("   🔄 Strategy 3: High-impact contextual opposites")
        for word in word_frequency:
            if word in self.strategic_patterns['opposite_sentiment'] and len(mappings) < max_mappings:
                replacement = self.strategic_patterns['opposite_sentiment'][word]
                mappings[word] = replacement
                print(f"      {word} → {replacement} (opposite sentiment)")

        # Strategy 4: Punctuated words (like "dog." in the example)
        print("   📍 Strategy 4: Punctuated word variants")
        text_content = analysis['text_content']
        punctuated_words = re.findall(r'\b\w+[.!?,:;]\b', text_content)
        for punct_word in punctuated_words[:5]:  # Top 5 punctuated words
            base_word = re.sub(r'[.!?,:;]', '', punct_word.lower())
            if base_word in mappings:
                # Create punctuated version of replacement
                punctuation = punct_word[-1]
                replacement = mappings[base_word] + punctuation
                mappings[punct_word] = replacement
                print(f"      {punct_word} → {replacement} (punctuated variant)")

        # Strategy 5: Similar length replacements to maintain visual layout
        print("   📏 Strategy 5: Length-preserving replacements")
        remaining_words = [w for w, c in top_words if w not in mappings and len(w) > 4][:10]
        for word in remaining_words:
            if len(mappings) < max_mappings:
                replacement = self._find_similar_length_replacement(word)
                if replacement:
                    mappings[word] = replacement
                    print(f"      {word} → {replacement} (similar length)")

        print(f"   ✅ Generated {len(mappings)} strategic mappings")
        return mappings

    def _find_category_replacement(self, word: str, domain: str) -> str:
        """Find a category-appropriate replacement for a word"""
        word_lower = word.lower()

        # Check all categories
        for category, word_map in self.word_categories.items():
            if word_lower in word_map:
                return word_map[word_lower]

        # Check strategic patterns
        for pattern_type, word_map in self.strategic_patterns.items():
            if word_lower in word_map:
                return word_map[word_lower]

        return None

    def _get_domain_specific_mappings(self, domain: str) -> Dict[str, str]:
        """Get mappings specific to the identified domain"""
        domain_maps = {
            'business': self.strategic_patterns['business_terms'],
            'technical': self.strategic_patterns['technical_terms'],
            'general': self.word_categories['animals']
        }

        return domain_maps.get(domain, self.word_categories['animals'])

    def _find_similar_length_replacement(self, word: str) -> str:
        """Find replacement word with similar length"""
        target_length = len(word)

        # Look through all categories for similar length words
        for category, word_map in self.word_categories.items():
            for original, replacement in word_map.items():
                if (len(original) == target_length and
                    original != word.lower() and
                    abs(len(replacement) - target_length) <= 1):  # Allow ±1 character difference
                    return replacement

        return None

    def generate_comprehensive_test_set(self, pdf_bytes: bytes) -> Dict[str, Dict[str, str]]:
        """Generate multiple mapping strategies for comprehensive testing"""
        print("🧪 Generating comprehensive test mapping sets...")

        analysis = self.analyze_pdf_content(pdf_bytes)

        test_sets = {
            'conservative': {},
            'moderate': {},
            'aggressive': {},
            'strategic': {}
        }

        # Conservative: Only high-frequency, safe replacements
        print("\n📊 Conservative mappings (high-frequency, safe replacements):")
        conservative_words = [word for word, count in analysis['top_words'][:10]
                             if len(word) > 3 and word.isalpha()]
        for word in conservative_words[:5]:
            replacement = self._find_category_replacement(word, analysis['domain'])
            if replacement:
                test_sets['conservative'][word] = replacement
                print(f"   {word} → {replacement}")

        # Moderate: Mix of frequency and domain-specific
        print("\n⚖️  Moderate mappings (mixed strategy):")
        moderate_mappings = self.generate_strategic_mappings(analysis, max_mappings=8)
        test_sets['moderate'] = dict(list(moderate_mappings.items())[:8])
        for word, replacement in test_sets['moderate'].items():
            print(f"   {word} → {replacement}")

        # Aggressive: Maximum replacements including opposites
        print("\n🔥 Aggressive mappings (maximum replacements):")
        aggressive_mappings = self.generate_strategic_mappings(analysis, max_mappings=15)
        # Add opposite sentiments
        for word in analysis['word_frequency']:
            if word in self.strategic_patterns['opposite_sentiment']:
                aggressive_mappings[word] = self.strategic_patterns['opposite_sentiment'][word]
        test_sets['aggressive'] = aggressive_mappings
        print(f"   {len(test_sets['aggressive'])} total mappings")

        # Strategic: Carefully selected high-impact words
        print("\n🎯 Strategic mappings (high-impact selections):")
        # Focus on words that appear in important contexts
        strategic_candidates = []
        for word, context in analysis['context_words'].items():
            if (context['frequency'] >= 2 and
                len(word) > 3 and
                any(keyword in ' '.join(context['before'] + context['after'])
                    for keyword in ['important', 'key', 'main', 'primary', 'significant', 'critical'])):
                strategic_candidates.append(word)

        for word in strategic_candidates[:6]:
            replacement = self._find_category_replacement(word, analysis['domain'])
            if replacement:
                test_sets['strategic'][word] = replacement
                print(f"   {word} → {replacement} (high-impact)")

        return test_sets

    def create_visual_mapping_report(self, analysis: Dict[str, any], test_sets: Dict[str, Dict[str, str]]) -> str:
        """Create a visual report of the generated mappings"""
        report = []
        report.append("📋 AUTOMATIC MAPPING GENERATION REPORT")
        report.append("=" * 50)

        # Document analysis summary
        report.append(f"\n📄 DOCUMENT ANALYSIS:")
        report.append(f"   • Domain: {analysis['domain']}")
        report.append(f"   • Total words: {analysis['total_words']:,}")
        report.append(f"   • Unique words: {analysis['unique_words']:,}")
        report.append(f"   • Sentences: {analysis['sentence_count']}")

        # Top words analysis
        report.append(f"\n📊 TOP WORDS ANALYSIS:")
        for i, (word, count) in enumerate(analysis['top_words'][:10], 1):
            report.append(f"   {i:2d}. {word:<12} ({count:3d} occurrences)")

        # Mapping strategies summary
        report.append(f"\n🎯 MAPPING STRATEGIES SUMMARY:")
        for strategy_name, mappings in test_sets.items():
            effectiveness_score = len(mappings) * 10  # Simple scoring
            report.append(f"   • {strategy_name.capitalize():<12}: {len(mappings):2d} mappings (Score: {effectiveness_score})")

        # Detailed mappings
        for strategy_name, mappings in test_sets.items():
            if mappings:
                report.append(f"\n🔄 {strategy_name.upper()} MAPPINGS:")
                for original, replacement in mappings.items():
                    freq = analysis['word_frequency'].get(original.lower(), 0)
                    report.append(f"   • {original:<15} → {replacement:<15} (freq: {freq})")

        # Recommendations
        report.append(f"\n💡 RECOMMENDATIONS:")
        best_strategy = max(test_sets.items(), key=lambda x: len(x[1]))
        report.append(f"   • Best strategy: {best_strategy[0]} ({len(best_strategy[1])} mappings)")

        high_freq_words = [w for w, c in analysis['top_words'][:5]]
        covered_words = sum(1 for strategy_mappings in test_sets.values()
                           for word in strategy_mappings.keys()
                           if word in high_freq_words)
        report.append(f"   • High-frequency coverage: {covered_words}/5 top words")

        return "\n".join(report)


def test_auto_mapping_generator():
    """Test the automatic mapping generator with sample PDF"""
    print("🧪 TESTING AUTOMATIC MAPPING GENERATOR")
    print("=" * 50)

    # Load sample PDF
    with open("tests/sample.pdf", "rb") as f:
        pdf_bytes = f.read()

    # Initialize generator
    generator = AutoMappingGenerator()

    # Generate comprehensive test sets
    test_sets = generator.generate_comprehensive_test_set(pdf_bytes)

    # Create visual report
    analysis = generator.analyze_pdf_content(pdf_bytes)
    report = generator.create_visual_mapping_report(analysis, test_sets)

    print("\n" + report)

    # Save report
    with open("tests/auto_mapping_report.txt", "w") as f:
        f.write(report)
    print(f"\n💾 Report saved to: tests/auto_mapping_report.txt")

    return test_sets, analysis


if __name__ == "__main__":
    test_sets, analysis = test_auto_mapping_generator()