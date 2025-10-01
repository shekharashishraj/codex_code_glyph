"""Simplified but robust TJ array processor that preserves element boundaries."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Pattern, Tuple, Union

from PyPDF2.generic import ArrayObject, NumberObject, TextStringObject

from .logger import get_logger


_SPACE_THRESHOLD = -120  # Matches threshold used for treating kerning as spaces.


class TJArrayProcessorV2:
    """TJ array processor that keeps word ownership aligned to original segments."""
    
    def __init__(self, pattern: Pattern[str], mapping: Dict[str, str], mapping_cf: Dict[str, str]):
        self.pattern = pattern
        self.mapping = mapping
        self.mapping_cf = mapping_cf
        self.logger = get_logger()
    
    def process_tj_array(self, array_obj: ArrayObject) -> Tuple[ArrayObject, bool]:
        """Process a TJ array with word replacement support."""
        if not array_obj:
            return array_obj, False

        # Step 1: Extract text segments together with ownership mapping
        text_segments: List[Dict] = []
        array_index_to_segment: Dict[int, int] = {}
        char_owner_indices: List[Optional[int]] = []
        combined_parts: List[str] = []
        current_pos = 0

        for array_index, item in enumerate(array_obj):
            if isinstance(item, TextStringObject):
                raw_text = str(item)
                cleaned_text = self._clean_special_chars(raw_text)

                segment_index = len(text_segments)
                text_segments.append(
                    {
                        "array_index": array_index,
                        "raw": raw_text,
                        "clean": cleaned_text,
                        "start": current_pos,
                        "end": current_pos + len(cleaned_text),
                    }
                )
                array_index_to_segment[array_index] = segment_index

                combined_parts.append(cleaned_text)
                for _ in cleaned_text:
                    char_owner_indices.append(segment_index)
                current_pos += len(cleaned_text)

            elif isinstance(item, NumberObject):
                # Negative kerning adjustments (large magnitude) usually encode spaces
                if float(item) <= _SPACE_THRESHOLD:
                    combined_parts.append(" ")
                    char_owner_indices.append(None)
                    current_pos += 1

        combined_text = "".join(combined_parts)
        if not combined_text:
            return array_obj, False

        self.logger.logger.debug(f"TJ Array - Combined text: {repr(combined_text)}")

        replacement_result = self._apply_replacements(combined_text)
        if replacement_result is None:
            return array_obj, False

        replaced_text, replacements = replacement_result
        self.logger.logger.info(f"TJ Array - Applied {len(replacements)} replacements")
        for repl in replacements:
            self.logger.logger.info(
                "  '%s' → '%s' at positions %d-%d",
                repl["original"],
                repl["replacement"],
                repl["start"],
                repl["end"],
            )

        # Step 2: Rebuild characters with updated ownership mapping
        rebuilt_chars: List[str] = []
        rebuilt_owner_indices: List[Optional[int]] = []
        cursor = 0

        for repl in replacements:
            start = repl["start"]
            end = repl["end"]
            replacement_text = repl["replacement"]

            while cursor < start:
                rebuilt_chars.append(combined_text[cursor])
                rebuilt_owner_indices.append(
                    char_owner_indices[cursor] if cursor < len(char_owner_indices) else None
                )
                cursor += 1

            owner_index = self._resolve_owner_for_replacement(
                char_owner_indices, start, end
            )

            for ch in replacement_text:
                rebuilt_chars.append(ch)
                rebuilt_owner_indices.append(owner_index)

            cursor = end

        while cursor < len(combined_text):
            rebuilt_chars.append(combined_text[cursor])
            rebuilt_owner_indices.append(char_owner_indices[cursor])
            cursor += 1

        rebuilt_text = "".join(rebuilt_chars)

        # Step 3: Aggregate characters back into their original segments
        new_segment_texts = [""] * len(text_segments)
        for ch, owner in zip(rebuilt_chars, rebuilt_owner_indices):
            if owner is None:
                continue
            new_segment_texts[owner] += ch

        # Step 4: Write updated segments back into a new array
        new_array = ArrayObject()
        modified = False

        for array_index, item in enumerate(array_obj):
            if isinstance(item, TextStringObject):
                segment_index = array_index_to_segment.get(array_index)
                if segment_index is None:
                    new_array.append(item)
                    continue

                original_clean = text_segments[segment_index]["clean"]
                new_clean = new_segment_texts[segment_index]

                if new_clean == original_clean:
                    new_array.append(item)
                else:
                    final_text = self._restore_special_chars(
                        new_clean, text_segments[segment_index]["raw"]
                    )
                    new_array.append(TextStringObject(final_text))
                    modified = True
            else:
                new_array.append(item)

        return new_array, modified
    
    def _clean_special_chars(self, text: str) -> str:
        """Clean special characters, converting ligature codes to text."""
        char_replacements = {
            '\x0c': 'fi',  # Form feed → 'fi' ligature
            '\x0b': 'fl',  # Vertical tab → 'fl' ligature
            '\x0e': 'ff',  # Shift out → 'ff' ligature
            '\x0f': 'ffi', # Shift in → 'ffi' ligature
            '\r': '',      # Carriage return → remove
            '\x1f': '',    # Unit separator → remove
        }
        
        cleaned = text
        for char, replacement in char_replacements.items():
            cleaned = cleaned.replace(char, replacement)
        
        # Remove remaining non-printable characters
        import string
        cleaned = ''.join(c for c in cleaned if c in string.printable or c == '\n')
        
        return cleaned
    
    def _apply_replacements(
        self, text: str
    ) -> Optional[Tuple[str, List[Dict[str, Union[int, str]]]]]:
        """Apply word replacements to text, returning replacement metadata."""
        if not self.pattern:
            return None

        matches = list(self.pattern.finditer(text))
        if not matches:
            return None

        pieces: List[str] = []
        replacements: List[Dict[str, Union[int, str]]] = []
        cursor = 0

        for match in matches:
            start, end = match.span()
            original = match.group(0)
            replacement = self._resolve_replacement(original)

            if not replacement or replacement == original:
                continue

            pieces.append(text[cursor:start])
            pieces.append(replacement)
            replacements.append(
                {
                    "start": start,
                    "end": end,
                    "original": original,
                    "replacement": replacement,
                }
            )
            cursor = end

        if not replacements:
            return None

        pieces.append(text[cursor:])
        replaced_text = "".join(pieces)
        return replaced_text, replacements
    
    def _resolve_replacement(self, token: str) -> Optional[str]:
        """Resolve replacement for a token."""
        replacement = self.mapping.get(token)
        if replacement is not None:
            return replacement
        return self.mapping_cf.get(token.casefold())
    
    def _resolve_owner_for_replacement(
        self, owners: List[Optional[int]], start: int, end: int
    ) -> Optional[int]:
        """Determine which segment should own replacement characters."""
        if start < len(owners) and owners[start] is not None:
            return owners[start]

        # Look backwards for the nearest owning segment
        for idx in range(min(start, len(owners)) - 1, -1, -1):
            owner = owners[idx]
            if owner is not None:
                return owner

        # Fallback: search forward past the replaced range
        for idx in range(min(end, len(owners)), len(owners)):
            owner = owners[idx]
            if owner is not None:
                return owner

        return None
    
    def _restore_special_chars(self, new_text: str, original_text: str) -> str:
        """Restore special characters from original text where appropriate."""
        # If original had special chars at the end, try to preserve them
        special_suffix = ''
        for char in reversed(original_text):
            if char in '\x0c\r\n\t\x0b\x0e\x0f':
                special_suffix = char + special_suffix
            else:
                break
        
        return new_text + special_suffix


def process_tj_array_with_word_replacement_v2(
    array_obj: ArrayObject,
    pattern: Pattern[str],
    mapping: Dict[str, str],
    mapping_cf: Dict[str, str]
) -> Tuple[ArrayObject, bool]:
    """
    Process TJ arrays using the simplified proportional distribution approach.
    """
    processor = TJArrayProcessorV2(pattern, mapping, mapping_cf)
    return processor.process_tj_array(array_obj)
