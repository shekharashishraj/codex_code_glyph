"""Comprehensive TJ array processing for handling split words and complex layouts."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Pattern, Tuple, Union

from PyPDF2.generic import ArrayObject, NumberObject, TextStringObject

from .logger import get_logger


class TJArrayProcessor:
    """
    Advanced TJ array processor that handles split words, special characters,
    and preserves formatting while enabling cross-element word replacement.
    """
    
    def __init__(self, pattern: Pattern[str], mapping: Dict[str, str], mapping_cf: Dict[str, str]):
        self.pattern = pattern
        self.mapping = mapping
        self.mapping_cf = mapping_cf
        self.logger = get_logger()
    
    def process_tj_array(self, array_obj: ArrayObject) -> Tuple[ArrayObject, bool]:
        """
        Process a TJ array with comprehensive word replacement support.
        
        Args:
            array_obj: Original TJ array from PDF
            
        Returns:
            Tuple of (modified_array, was_modified)
        """
        if not array_obj:
            return array_obj, False
        
        # Step 1: Reconstruct full text and create element mapping
        full_text, element_map = self._reconstruct_tj_text(array_obj)
        
        if not full_text.strip():
            return array_obj, False
        
        self.logger.logger.debug(f"TJ Array - Full text: {repr(full_text)}")
        
        # Step 2: Apply word replacements to full text
        replacement_result = self._apply_replacements_to_full_text(full_text)
        
        if replacement_result is None:
            self.logger.logger.debug("TJ Array - No replacements needed")
            return array_obj, False
        
        replaced_text, replacements_made = replacement_result
        
        self.logger.logger.info(f"TJ Array - Applied {len(replacements_made)} replacements")
        for original, replacement, start, end in replacements_made:
            self.logger.logger.info(f"  '{original}' → '{replacement}' at positions {start}-{end}")
        
        # Step 3: Map replacements back to array elements
        new_array = self._rebuild_tj_array(array_obj, full_text, replaced_text, element_map)
        
        return new_array, True
    
    def _reconstruct_tj_text(self, array_obj: ArrayObject) -> Tuple[str, List[Dict]]:
        """
        Reconstruct complete text from TJ array elements with position mapping.
        
        Returns:
            Tuple of (full_text, element_mapping)
            element_mapping: List of {element_index, text_start, text_end, original_text}
        """
        full_text_parts = []
        element_map = []
        current_pos = 0
        
        for i, item in enumerate(array_obj):
            if isinstance(item, TextStringObject):
                text = str(item)
                cleaned_text = self._clean_special_chars(text)
                
                element_map.append({
                    'element_index': i,
                    'text_start': current_pos,
                    'text_end': current_pos + len(cleaned_text),
                    'original_text': text,
                    'cleaned_text': cleaned_text
                })
                
                full_text_parts.append(cleaned_text)
                current_pos += len(cleaned_text)
                
            elif isinstance(item, NumberObject):
                # Handle spacing/kerning - add space for significant negative adjustments
                adjustment = float(item)
                if adjustment <= -120:  # Threshold for space
                    space_char = ' '
                    full_text_parts.append(space_char)
                    current_pos += len(space_char)
                    
                    # Record space insertion for proper mapping
                    element_map.append({
                        'element_index': i,
                        'text_start': current_pos - 1,
                        'text_end': current_pos,
                        'original_text': '',
                        'cleaned_text': space_char,
                        'is_spacing': True
                    })
        
        full_text = ''.join(full_text_parts)
        return full_text, element_map
    
    def _clean_special_chars(self, text: str) -> str:
        """
        Clean special characters while preserving text structure.
        
        The key insight is that form feeds and similar characters often represent
        ligatures or special character encodings in PDFs. For example:
        - \x0c often represents 'fi' ligature
        - \x0b might represent 'fl' ligature
        """
        # Map common PDF control characters to their likely text equivalents
        char_replacements = {
            '\x0c': 'fi',  # Form feed often represents 'fi' ligature
            '\x0b': 'fl',  # Vertical tab often represents 'fl' ligature
            '\x0e': 'ff',  # Shift out might represent 'ff' ligature
            '\x0f': 'ffi', # Shift in might represent 'ffi' ligature
            '\r': '',      # Carriage return - remove
            '\x1f': '',    # Unit separator - remove
        }
        
        cleaned = text
        for char, replacement in char_replacements.items():
            cleaned = cleaned.replace(char, replacement)
        
        # Remove any remaining non-printable characters except newlines
        import string
        printable_chars = string.printable
        cleaned = ''.join(c for c in cleaned if c in printable_chars or c == '\n')
        
        return cleaned
    
    def _apply_replacements_to_full_text(self, full_text: str) -> Optional[Tuple[str, List[Tuple[str, str, int, int]]]]:
        """
        Apply word replacements to the full reconstructed text.
        
        Returns:
            Tuple of (replaced_text, replacements_made) or None if no changes
            replacements_made: List of (original, replacement, start_pos, end_pos)
        """
        if not self.pattern:
            return None
        
        matches = list(self.pattern.finditer(full_text))
        if not matches:
            return None
        
        # Apply replacements in reverse order to maintain position accuracy
        replaced_text = full_text
        replacements_made = []
        
        for match in reversed(matches):
            start, end = match.span()
            original = match.group(0)
            replacement = self._resolve_replacement(original)
            
            if replacement and replacement != original:
                replaced_text = replaced_text[:start] + replacement + replaced_text[end:]
                # Store in original order for logging
                replacements_made.insert(0, (original, replacement, start, end))
        
        if not replacements_made:
            return None
        
        return replaced_text, replacements_made
    
    def _resolve_replacement(self, token: str) -> Optional[str]:
        """Resolve replacement for a token using exact or case-insensitive matching."""
        replacement = self.mapping.get(token)
        if replacement is not None:
            return replacement
        return self.mapping_cf.get(token.casefold())
    
    def _rebuild_tj_array(self, original_array: ArrayObject, original_text: str, 
                         replaced_text: str, element_map: List[Dict]) -> ArrayObject:
        """
        Rebuild TJ array with replacements mapped back to original structure.
        """
        new_array = ArrayObject()
        
        # Create a character-by-character mapping from original to replaced text
        char_mapping = self._create_character_mapping(original_text, replaced_text)
        
        for i, item in enumerate(original_array):
            if isinstance(item, NumberObject):
                # Keep all number elements (kerning) as-is
                new_array.append(item)
                
            elif isinstance(item, TextStringObject):
                # Find corresponding element in mapping
                element_info = None
                for elem in element_map:
                    if elem['element_index'] == i and not elem.get('is_spacing'):
                        element_info = elem
                        break
                
                if element_info:
                    # Map this element's text using character mapping
                    new_text = self._map_element_text_via_chars(
                        element_info, char_mapping, replaced_text
                    )
                    
                    if new_text != element_info['cleaned_text']:
                        # Text was modified, restore special chars and use new text
                        final_text = self._restore_special_chars(new_text, element_info['original_text'])
                        new_array.append(TextStringObject(final_text))
                        self.logger.logger.debug(f"Element {i}: '{element_info['original_text']}' → '{final_text}'")
                    else:
                        # No change, keep original
                        new_array.append(item)
                else:
                    # Fallback: keep original if mapping fails
                    new_array.append(item)
            else:
                # Keep any other elements as-is
                new_array.append(item)
        
        return new_array
    
    def _create_character_mapping(self, original_text: str, replaced_text: str) -> List[int]:
        """
        Create a character-by-character mapping from original to replaced text positions.
        
        Returns a list where index i contains the position in replaced_text 
        that corresponds to position i in original_text.
        """
        if len(original_text) == len(replaced_text):
            # Simple case: same length, direct mapping
            return list(range(len(original_text)))
        
        # Complex case: different lengths due to replacements
        # Use a more sophisticated approach that handles word boundaries better
        char_mapping = []
        
        # Calculate the scale factor
        if len(original_text) > 0:
            scale_factor = len(replaced_text) / len(original_text)
        else:
            scale_factor = 1.0
        
        for i in range(len(original_text)):
            # Scale the position and round to nearest integer
            mapped_pos = int(i * scale_factor)
            # Ensure we don't exceed the replaced text bounds
            mapped_pos = min(mapped_pos, len(replaced_text) - 1)
            char_mapping.append(mapped_pos)
        
        return char_mapping
    
    def _map_element_text_via_chars(self, element_info: Dict, char_mapping: List[int], replaced_text: str) -> str:
        """
        Map an element's text using the character mapping.
        """
        start_pos = element_info['text_start']
        end_pos = element_info['text_end']
        original_text = element_info['cleaned_text']
        
        # If the element is within our mapping range
        if start_pos < len(char_mapping) and replaced_text:
            # Get the mapped start position
            mapped_start = char_mapping[start_pos] if start_pos < len(char_mapping) else 0
            
            # For end position, we need to be more careful
            if end_pos <= len(char_mapping):
                # Use the mapping for the end position
                mapped_end = char_mapping[end_pos - 1] + 1 if end_pos > 0 else mapped_start + 1
            else:
                # Extrapolate the end position using the scale factor
                original_length = len(original_text)
                if len(char_mapping) > 0:
                    scale_factor = len(replaced_text) / len(char_mapping)
                    mapped_end = mapped_start + int(original_length * scale_factor)
                else:
                    mapped_end = mapped_start + original_length
            
            # Ensure we don't go beyond the replaced text
            mapped_end = min(mapped_end, len(replaced_text))
            
            # Also ensure we get at least something reasonable
            if mapped_end <= mapped_start:
                mapped_end = min(mapped_start + len(original_text), len(replaced_text))
            
            # Extract from the replaced text
            if mapped_start < len(replaced_text):
                result = replaced_text[mapped_start:mapped_end]
                return result if result else original_text
        
        return original_text
    
    def _extract_element_text(self, original_text: str, replaced_text: str, 
                            start_pos: int, end_pos: int, element_info: Dict) -> str:
        """
        Extract the text for a specific element from the replaced text.
        
        This handles cases where replacements change text length and affect
        subsequent element positions.
        """
        original_element_text = element_info['cleaned_text']
        
        # Calculate the length difference at this position
        length_diff = len(replaced_text) - len(original_text)
        
        # Adjust end position if text length changed
        adjusted_end = end_pos
        if length_diff != 0:
            # For simplicity, assume proportional distribution of length change
            # This is a heuristic that works for many cases
            pos_ratio = start_pos / len(original_text) if original_text else 0
            length_adjustment = int(length_diff * pos_ratio)
            adjusted_end = end_pos + length_adjustment
        
        # Extract text from replaced string
        if start_pos < len(replaced_text):
            # Ensure we don't go beyond the replaced text length
            safe_end = min(adjusted_end, len(replaced_text))
            candidate_text = replaced_text[start_pos:safe_end]
            
            # If we got a reasonable result, use it
            if candidate_text and not candidate_text.isspace():
                return candidate_text
            
            # If the adjusted extraction failed, try the original range
            if end_pos <= len(replaced_text):
                fallback_text = replaced_text[start_pos:end_pos]
                if fallback_text:
                    return fallback_text
        
        # Final fallback: try to extract what we can from the position
        if start_pos < len(replaced_text):
            # Take at least the length of the original element, or what's available
            remaining_length = len(replaced_text) - start_pos
            take_length = min(len(original_element_text), remaining_length)
            if take_length > 0:
                return replaced_text[start_pos:start_pos + take_length]
        
        # If all else fails, return the original text
        return original_element_text
    
    def _restore_special_chars(self, new_text: str, original_text: str) -> str:
        """
        Restore special characters from original text to new text where appropriate.
        """
        # If original had special chars at the end, try to preserve them
        special_chars = ''
        for char in reversed(original_text):
            if char in '\x0c\r\n\t':
                special_chars = char + special_chars
            else:
                break
        
        if special_chars:
            return new_text + special_chars
        
        return new_text


def process_tj_array_with_word_replacement(
    array_obj: ArrayObject,
    pattern: Pattern[str],
    mapping: Dict[str, str],
    mapping_cf: Dict[str, str]
) -> Tuple[ArrayObject, bool]:
    """
    Convenience function for processing TJ arrays with word replacement.
    
    Args:
        array_obj: TJ array to process
        pattern: Compiled regex pattern for matching words
        mapping: Exact case mapping dictionary
        mapping_cf: Case-insensitive mapping dictionary
        
    Returns:
        Tuple of (processed_array, was_modified)
    """
    processor = TJArrayProcessor(pattern, mapping, mapping_cf)
    return processor.process_tj_array(array_obj)


# Test utilities for debugging

def debug_tj_array_structure(array_obj: ArrayObject) -> str:
    """Debug utility to visualize TJ array structure."""
    parts = []
    for i, item in enumerate(array_obj):
        if isinstance(item, TextStringObject):
            parts.append(f"[{i}]Text: {repr(str(item))}")
        elif isinstance(item, NumberObject):
            parts.append(f"[{i}]Num: {float(item)}")
        else:
            parts.append(f"[{i}]Other: {type(item)} {repr(item)}")
    
    return " | ".join(parts)


def test_tj_reconstruction(array_obj: ArrayObject) -> str:
    """Test utility to show how TJ array gets reconstructed."""
    processor = TJArrayProcessor(None, {}, {})
    full_text, element_map = processor._reconstruct_tj_text(array_obj)
    
    result = [f"Full text: {repr(full_text)}"]
    result.append("Element mapping:")
    for elem in element_map:
        result.append(f"  [{elem['element_index']}] {elem['text_start']}-{elem['text_end']}: {repr(elem['cleaned_text'])}")
    
    return "\n".join(result)