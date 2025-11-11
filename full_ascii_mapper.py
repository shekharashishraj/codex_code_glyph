"""
Complete ASCII Input/Output Mapping System
Maps entire ASCII character set (32-126) for ultimate text manipulation
"""

import string
import random
from typing import Dict, List, Tuple
import json

class FullASCIIMapper:
    """Create complete ASCII character remapping for ultimate steganography"""

    def __init__(self):
        # ASCII printable characters (32-126 = 95 characters)
        self.ascii_printable = string.printable[:95]  # Space to ~ (excluding \t\n\r\x0b\x0c)
        self.ascii_range = list(range(32, 127))  # 32=' ', 126='~'

    def create_complete_ascii_mapping(self, strategy: str = "shift") -> Dict[str, str]:
        """
        Create complete ASCII character mapping using various strategies

        Strategies:
        - shift: Caesar cipher-style shift
        - reverse: Reverse ASCII order
        - shuffle: Random permutation
        - rot13_extended: ROT13 for letters, shift for others
        - custom: User-defined mapping
        """

        print(f"🔤 CREATING COMPLETE ASCII MAPPING: {strategy}")
        print(f"📊 Mapping {len(self.ascii_printable)} ASCII characters (32-126)")

        if strategy == "shift":
            return self._create_shift_mapping()
        elif strategy == "reverse":
            return self._create_reverse_mapping()
        elif strategy == "shuffle":
            return self._create_shuffle_mapping()
        elif strategy == "rot13_extended":
            return self._create_rot13_extended_mapping()
        elif strategy == "phonetic":
            return self._create_phonetic_mapping()
        elif strategy == "unicode_steganography":
            return self._create_unicode_steganography_mapping()
        else:
            return self._create_shift_mapping()  # Default

    def _create_shift_mapping(self, shift: int = 13) -> Dict[str, str]:
        """Caesar cipher-style shift for entire ASCII range"""
        mapping = {}

        for i, char in enumerate(self.ascii_printable):
            # Shift within printable ASCII range
            new_index = (i + shift) % len(self.ascii_printable)
            new_char = self.ascii_printable[new_index]
            mapping[char] = new_char

        print(f"   📈 Shift mapping with offset {shift}")
        self._show_mapping_sample(mapping)
        return mapping

    def _create_reverse_mapping(self) -> Dict[str, str]:
        """Reverse ASCII order mapping"""
        mapping = {}
        reversed_chars = self.ascii_printable[::-1]

        for original, reversed_char in zip(self.ascii_printable, reversed_chars):
            mapping[original] = reversed_char

        print("   🔄 Reverse order mapping")
        self._show_mapping_sample(mapping)
        return mapping

    def _create_shuffle_mapping(self, seed: int = 42) -> Dict[str, str]:
        """Random permutation mapping (reproducible with seed)"""
        random.seed(seed)  # For reproducible results

        shuffled_chars = list(self.ascii_printable)
        random.shuffle(shuffled_chars)

        mapping = {}
        for original, shuffled in zip(self.ascii_printable, shuffled_chars):
            mapping[original] = shuffled

        print(f"   🎲 Random shuffle mapping (seed: {seed})")
        self._show_mapping_sample(mapping)
        return mapping

    def _create_rot13_extended_mapping(self) -> Dict[str, str]:
        """Extended ROT13: letters rotate, others shift by different amounts"""
        mapping = {}

        for char in self.ascii_printable:
            if char.isalpha():
                # ROT13 for letters
                if char.islower():
                    mapping[char] = chr((ord(char) - ord('a') + 13) % 26 + ord('a'))
                else:
                    mapping[char] = chr((ord(char) - ord('A') + 13) % 26 + ord('A'))
            elif char.isdigit():
                # ROT5 for digits
                mapping[char] = str((int(char) + 5) % 10)
            else:
                # Different shifts for punctuation
                ascii_val = ord(char)
                if 32 <= ascii_val <= 47:  # Space to /
                    new_val = 32 + ((ascii_val - 32 + 7) % 16)
                elif 58 <= ascii_val <= 64:  # : to @
                    new_val = 58 + ((ascii_val - 58 + 3) % 7)
                elif 91 <= ascii_val <= 96:  # [ to `
                    new_val = 91 + ((ascii_val - 91 + 2) % 6)
                elif 123 <= ascii_val <= 126:  # { to ~
                    new_val = 123 + ((ascii_val - 123 + 1) % 4)
                else:
                    new_val = ascii_val
                mapping[char] = chr(new_val)

        print("   🔀 Extended ROT13 mapping")
        self._show_mapping_sample(mapping)
        return mapping

    def _create_phonetic_mapping(self) -> Dict[str, str]:
        """Map to phonetic/similar-looking characters"""
        # Create visually similar or phonetically similar mappings
        similar_mappings = {
            # Numbers to letters
            '0': 'O', '1': 'l', '2': 'Z', '3': 'E', '4': 'A', '5': 'S',
            '6': 'G', '7': 'T', '8': 'B', '9': 'g',

            # Visually similar letters
            'a': 'α', 'e': 'ε', 'o': 'ο', 'p': 'ρ', 'x': 'χ',
            'A': 'Α', 'B': 'Β', 'E': 'Ε', 'H': 'Η', 'I': 'Ι',
            'K': 'Κ', 'M': 'Μ', 'N': 'Ν', 'O': 'Ο', 'P': 'Ρ',
            'T': 'Τ', 'X': 'Χ', 'Y': 'Υ', 'Z': 'Ζ',

            # Special characters
            '-': '−',  # Minus sign vs hyphen
            "'": '\u2019',  # Curly apostrophe
            '"': '\u201C',  # Curly quotes
            '...': '…', # Ellipsis
        }

        mapping = {}
        for char in self.ascii_printable:
            if char in similar_mappings:
                mapping[char] = similar_mappings[char]
            else:
                # Use shift for unmapped characters
                ascii_val = ord(char)
                new_val = 32 + ((ascii_val - 32 + 7) % (127 - 32))
                mapping[char] = chr(new_val)

        print("   👁️ Phonetic/visual similarity mapping")
        self._show_mapping_sample(mapping)
        return mapping

    def _create_unicode_steganography_mapping(self) -> Dict[str, str]:
        """Map to visually identical Unicode characters for ultimate steganography"""

        # Unicode characters that look identical to ASCII but have different codepoints
        unicode_steganography = {
            # Cyrillic letters that look like Latin
            'a': 'а',  # U+0061 -> U+0430 (Cyrillic small a)
            'e': 'е',  # U+0065 -> U+0435 (Cyrillic small e)
            'o': 'о',  # U+006F -> U+043E (Cyrillic small o)
            'p': 'р',  # U+0070 -> U+0440 (Cyrillic small p)
            'c': 'с',  # U+0063 -> U+0441 (Cyrillic small c)
            'x': 'х',  # U+0078 -> U+0445 (Cyrillic small x)
            'y': 'у',  # U+0079 -> U+0443 (Cyrillic small u that looks like y)

            'A': 'А',  # U+0041 -> U+0410 (Cyrillic capital A)
            'B': 'В',  # U+0042 -> U+0412 (Cyrillic capital B)
            'E': 'Е',  # U+0045 -> U+0415 (Cyrillic capital E)
            'H': 'Н',  # U+0048 -> U+041D (Cyrillic capital H)
            'K': 'К',  # U+004B -> U+041A (Cyrillic capital K)
            'M': 'М',  # U+004D -> U+041C (Cyrillic capital M)
            'O': 'О',  # U+004F -> U+041E (Cyrillic capital O)
            'P': 'Р',  # U+0050 -> U+0420 (Cyrillic capital P)
            'T': 'Т',  # U+0054 -> U+0422 (Cyrillic capital T)
            'X': 'Х',  # U+0058 -> U+0425 (Cyrillic capital X)

            # Greek letters
            'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e',

            # Mathematical symbols that look like regular chars
            '−': '-',  # U+2212 (minus) vs U+002D (hyphen-minus)
            '‐': '-',  # U+2010 (hyphen)
            '–': '-',  # U+2013 (en dash)
            '—': '-',  # U+2014 (em dash)

            # Quotation marks
            '\u2019': "'",  # U+2019 vs U+0027
            '\u201C': '"',  # U+201C vs U+0022
            '\u201D': '"',  # U+201D vs U+0022
        }

        mapping = {}
        for char in self.ascii_printable:
            if char in unicode_steganography:
                mapping[char] = unicode_steganography[char]
            else:
                # For unmapped chars, use homoglyphs or keep same
                mapping[char] = self._find_unicode_homoglyph(char)

        print("   🕵️ Unicode steganography mapping (visually identical)")
        self._show_mapping_sample(mapping, show_unicode=True)
        return mapping

    def _find_unicode_homoglyph(self, char: str) -> str:
        """Find Unicode character that looks identical to ASCII char"""
        # This would be expanded with a comprehensive homoglyph database
        homoglyphs = {
            '0': '０',  # Fullwidth digit zero
            '1': '１',  # Fullwidth digit one
            '2': '２',  # Fullwidth digit two
            # ... (would include comprehensive mappings)
        }

        return homoglyphs.get(char, char)  # Return same if no homoglyph

    def _show_mapping_sample(self, mapping: Dict[str, str], show_unicode: bool = False, sample_size: int = 10):
        """Show sample of the mapping"""
        print("   📋 Sample mappings:")

        # Show a sample of mappings
        sample_chars = list(mapping.keys())[:sample_size]
        for char in sample_chars:
            mapped = mapping[char]
            if show_unicode:
                print(f"      '{char}' (U+{ord(char):04X}) -> '{mapped}' (U+{ord(mapped):04X})")
            else:
                print(f"      '{char}' -> '{mapped}'")

        if len(mapping) > sample_size:
            print(f"      ... and {len(mapping) - sample_size} more")

    def apply_full_ascii_mapping(self, text: str, mapping: Dict[str, str]) -> str:
        """Apply complete ASCII mapping to text"""
        result = ""
        for char in text:
            result += mapping.get(char, char)  # Use mapping or keep original
        return result

    def create_reverse_mapping(self, mapping: Dict[str, str]) -> Dict[str, str]:
        """Create reverse mapping for decoding"""
        return {v: k for k, v in mapping.items()}

    def save_mapping(self, mapping: Dict[str, str], filename: str):
        """Save mapping to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        print(f"   💾 Mapping saved to {filename}")

    def load_mapping(self, filename: str) -> Dict[str, str]:
        """Load mapping from JSON file"""
        with open(filename, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        print(f"   📁 Mapping loaded from {filename}")
        return mapping

def demonstrate_full_ascii_mapping():
    """Demonstrate complete ASCII mapping capabilities"""

    print("🔤 FULL ASCII MAPPING DEMONSTRATION")
    print("=" * 60)

    mapper = FullASCIIMapper()
    test_text = "Hello, World! 123 @#$ %^&*()"

    print(f"📄 Original text: '{test_text}'")
    print()

    # Test all mapping strategies
    strategies = ["shift", "reverse", "shuffle", "rot13_extended", "phonetic", "unicode_steganography"]

    for strategy in strategies:
        print(f"\n🎯 STRATEGY: {strategy.upper()}")
        print("-" * 40)

        # Create mapping
        mapping = mapper.create_complete_ascii_mapping(strategy)

        # Apply mapping
        encoded_text = mapper.apply_full_ascii_mapping(test_text, mapping)
        print(f"📝 Encoded text: '{encoded_text}'")

        # Test reverse mapping
        reverse_mapping = mapper.create_reverse_mapping(mapping)
        decoded_text = mapper.apply_full_ascii_mapping(encoded_text, reverse_mapping)
        print(f"🔄 Decoded text: '{decoded_text}'")

        # Verify round-trip
        success = decoded_text == test_text
        print(f"✅ Round-trip success: {success}")

        # Save mapping
        mapper.save_mapping(mapping, f"mapping_{strategy}.json")
        print()

def create_pdf_with_full_ascii_mapping(pdf_bytes: bytes, strategy: str = "unicode_steganography") -> bytes:
    """
    Create PDF with complete ASCII character mapping
    Every single character gets remapped according to strategy
    """

    print(f"🔤 APPLYING FULL ASCII MAPPING TO PDF: {strategy}")

    mapper = FullASCIIMapper()
    ascii_mapping = mapper.create_complete_ascii_mapping(strategy)

    # Use existing precision overlay approach but with complete ASCII mapping
    from advanced_approaches import approach_3_precision_overlays

    return approach_3_precision_overlays(pdf_bytes, ascii_mapping)

if __name__ == "__main__":
    demonstrate_full_ascii_mapping()

    # Test extreme cases
    print("\n🧪 EXTREME CASE TESTING:")
    print("=" * 40)

    mapper = FullASCIIMapper()

    # Test with complete ASCII range
    all_ascii = ''.join(chr(i) for i in range(32, 127))
    print(f"📊 Testing all {len(all_ascii)} ASCII characters:")
    print(f"Original: '{all_ascii[:20]}...'")

    mapping = mapper.create_complete_ascii_mapping("unicode_steganography")
    encoded = mapper.apply_full_ascii_mapping(all_ascii, mapping)
    print(f"Encoded:  '{encoded[:20]}...'")

    # Verify every character got mapped
    changes = sum(1 for orig, enc in zip(all_ascii, encoded) if orig != enc)
    print(f"📈 Characters changed: {changes}/{len(all_ascii)} ({changes/len(all_ascii)*100:.1f}%)")