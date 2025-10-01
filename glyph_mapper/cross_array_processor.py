"""Cross-array pattern matching for handling patterns split across multiple TJ operations."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Pattern, Tuple

from PyPDF2.generic import ArrayObject, NumberObject, TextStringObject

from .logger import get_logger
from .tj_array_processor_v2 import TJArrayProcessorV2


class CrossArrayProcessor:
    """
    Processor for handling patterns that span multiple TJ array operations.
    
    This handles cases where patterns like "0.9:" are split across multiple
    TJ operations: ['=', '0'] in one array and ['9:', ...] in another.
    """
    
    def __init__(self, pattern: Pattern[str], mapping: Dict[str, str], mapping_cf: Dict[str, str]):
        self.pattern = pattern
        self.mapping = mapping
        self.mapping_cf = mapping_cf
        self.logger = get_logger()
        self.v2_processor = TJArrayProcessorV2(pattern, mapping, mapping_cf)
    
    def process_content_operations(self, operations: List[Tuple]) -> Tuple[List[Tuple], bool]:
        """
        Process a list of content stream operations to handle cross-array patterns.
        
        Args:
            operations: List of (operands, operator) tuples from content stream
            
        Returns:
            Tuple of (modified_operations, was_modified)
        """
        if not operations:
            return operations, False

        # Phase 1: Apply V2 processor to individual TJ arrays
        operations_after_v2, v2_modified = self._apply_v2_processor(operations)

        # Phase 2: Apply cross-array processing for patterns spanning multiple operations
        operations_after_cross, cross_modified = self._apply_cross_array_processing(operations_after_v2)

        return operations_after_cross, v2_modified or cross_modified
    
    def _apply_v2_processor(self, operations: List[Tuple]) -> Tuple[List[Tuple], bool]:
        """Apply V2 processor to individual TJ arrays and Tj operations."""
        modified_operations = []
        any_modified = False
        
        for operands, operator in operations:
            if operator == b"TJ" and operands:
                array_obj = operands[0]
                if isinstance(array_obj, ArrayObject):
                    processed_array, array_modified = self.v2_processor.process_tj_array(array_obj)
                    if array_modified:
                        modified_operations.append(([processed_array], operator))
                        any_modified = True
                    else:
                        modified_operations.append((operands, operator))
                else:
                    modified_operations.append((operands, operator))
            elif operator == b"Tj" and operands:
                # Handle single text string operations carefully
                # Only process if we detect patterns that need replacement
                text_obj = operands[0]
                text = str(text_obj)
                
                # Check if this text contains any of our target patterns
                if self.pattern and self.pattern.search(text):
                    # Apply replacement directly to the text
                    modified_text = self._apply_pattern_replacement(text)
                    if modified_text != text:
                        from PyPDF2.generic import TextStringObject
                        modified_operations.append(([TextStringObject(modified_text)], operator))
                        any_modified = True
                        self.logger.logger.info(f"Tj replacement: '{text}' → '{modified_text}'")
                    else:
                        modified_operations.append((operands, operator))
                else:
                    modified_operations.append((operands, operator))
            else:
                modified_operations.append((operands, operator))
        
        return modified_operations, any_modified
    
    def _apply_cross_array_processing(self, operations: List[Tuple]) -> Tuple[List[Tuple], bool]:
        """Apply cross-array pattern matching and replacement."""
        if not self.pattern:
            return operations, False
        
        # Find TJ operations and build sliding windows
        tj_operations = []
        for i, (operands, operator) in enumerate(operations):
            if operator == b"TJ" and operands:
                array_obj = operands[0]
                if isinstance(array_obj, ArrayObject):
                    tj_operations.append((i, array_obj))
        
        if len(tj_operations) < 2:
            # Need at least 2 TJ operations for cross-array patterns
            return operations, False
        
        # Find cross-array matches
        cross_matches = self._find_cross_array_matches(tj_operations)
        
        if not cross_matches:
            return operations, False

        # Apply replacements to the matched operations
        modified_operations = list(operations)
        any_modified = False

        # Process matches in reverse order to maintain indices
        for match in reversed(cross_matches):
            success = self._apply_cross_array_replacement(modified_operations, match)
            if success:
                any_modified = True
        
        return modified_operations, any_modified
    
    def _find_cross_array_matches(self, tj_operations: List[Tuple[int, ArrayObject]]) -> List[Dict]:
        """Find patterns that span across multiple TJ operations."""
        matches = []
        
        # Use sliding window approach
        window_size = 3  # Look at up to 3 consecutive TJ operations
        
        for i in range(len(tj_operations) - 1):
            window_operations = tj_operations[i:i + window_size]
            window_text = self._build_window_text(window_operations)
            
            self.logger.logger.debug(f"Cross-array window {i}: {repr(window_text)}")
            
            # Check for pattern matches in the window
            pattern_matches = list(self.pattern.finditer(window_text))
            
            # Also check for decimal number patterns that might be split
            decimal_matches = self._find_split_decimal_patterns(window_text, window_operations)
            
            # Combine both types of matches
            all_matches = pattern_matches + decimal_matches
            
            for match in all_matches:
                if hasattr(match, 'span'):
                    # Regular regex match
                    start, end = match.span()
                    matched_text = match.group(0)
                else:
                    # Custom decimal match
                    start, end = match['span']
                    matched_text = match['text']
                
                replacement = self._resolve_replacement(matched_text)
                
                if replacement and replacement != matched_text:
                    self.logger.logger.info(f"Cross-array match: '{matched_text}' → '{replacement}' in window {i}")
                    
                    matches.append({
                        'window_start': i,
                        'window_operations': window_operations,
                        'match_start': start,
                        'match_end': end,
                        'original': matched_text,
                        'replacement': replacement,
                        'window_text': window_text
                    })
        
        return matches
    
    def _find_split_decimal_patterns(self, window_text: str, window_operations: List) -> List[Dict]:
        """Find decimal patterns that are split across arrays (missing decimal point)."""
        decimal_matches = []
        
        # Look for patterns where decimal point is missing entirely
        # Real case: "= 0 : 9:" should be "0.9:"
        split_decimal_patterns = [
            r'(?:=\s*)?(\d)\s*:\s*(\d+):',  # Matches "= 0 : 9:" (decimal point missing)
            r'(?:=\s*)?(\d)\s+(\d+):',      # Matches "= 0 9:" (space instead of decimal)
            r'(?:=\s*)?(\d)\s*(\d+):',      # Matches "= 09:" (no space)
        ]
        
        for pattern_str in split_decimal_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            for match in pattern.finditer(window_text):
                # Reconstruct the decimal number
                digit1 = match.group(1)
                digit2 = match.group(2)
                reconstructed = f"{digit1}.{digit2}:"
                
                self.logger.logger.debug(f"Found split decimal: '{match.group(0)}' → '{reconstructed}'")
                
                # Check if this reconstructed pattern is in our mappings
                if reconstructed in self.mapping or reconstructed.lower() in self.mapping_cf:
                    decimal_matches.append({
                        'span': match.span(),
                        'text': reconstructed,
                        'original_match': match.group(0)
                    })
        
        return decimal_matches
    
    def _build_window_text(self, window_operations: List[Tuple[int, ArrayObject]]) -> str:
        """Build combined text from a window of TJ operations."""
        text_parts = []
        
        for _, array_obj in window_operations:
            array_text = self._extract_array_text(array_obj)
            if array_text:
                text_parts.append(array_text)
        
        # Join with spaces to approximate the actual spacing
        return ' '.join(text_parts)
    
    def _extract_array_text(self, array_obj: ArrayObject) -> str:
        """Extract text from a TJ array, cleaning special characters."""
        text_elements = []
        
        for item in array_obj:
            if isinstance(item, TextStringObject):
                text = str(item)
                # Apply the same cleaning as V2 processor
                cleaned_text = self.v2_processor._clean_special_chars(text)
                text_elements.append(cleaned_text)
            elif isinstance(item, NumberObject):
                # Add space for significant negative adjustments
                if float(item) <= -120:
                    text_elements.append(' ')
                # For positive NumberObjects, they might represent missing characters
                # In some PDFs, decimal points are represented as positioning numbers
                elif 0 < float(item) < 10 and len(str(item)) == 1:
                    # This might be a missing decimal point in decimal number contexts
                    pass  # For now, ignore small positive numbers
        
        return ''.join(text_elements)
    
    def _resolve_replacement(self, token: str) -> Optional[str]:
        """Resolve replacement for a token."""
        replacement = self.mapping.get(token)
        if replacement is not None:
            return replacement
        return self.mapping_cf.get(token.casefold())
    
    def _apply_cross_array_replacement(self, operations: List[Tuple], match: Dict) -> bool:
        """Apply a cross-array replacement to the operations list."""
        try:
            window_ops = match['window_operations']
            original = match['original']
            replacement = match['replacement']
            
            # For decimal patterns like "0.9:" → "9.0:", we need to:
            # 1. Modify the first array: "0" → "9"  
            # 2. Modify the second array: "9:" → "0:" (add decimal point)
            
            if '.' in original and ':' in original and len(window_ops) >= 2:
                return self._apply_decimal_cross_array_replacement(operations, match)
            else:
                # Fallback to simple replacement in first array
                return self._apply_simple_cross_array_replacement(operations, match)

        except Exception as e:
            self.logger.log_error(e, f"cross_array_replacement")
            return False
    
    def _apply_decimal_cross_array_replacement(self, operations: List[Tuple], match: Dict) -> bool:
        """Apply decimal number replacement across two arrays."""
        window_ops = match['window_operations']
        original = match['original']  # e.g., "0.9:"
        replacement = match['replacement']  # e.g., "9.0:"
        
        if len(window_ops) < 2:
            return False
        
        # Parse the decimal patterns
        orig_parts = original.split('.')
        repl_parts = replacement.split('.')
        
        if len(orig_parts) != 2 or len(repl_parts) != 2:
            return False
        
        # Extract digits from the actual replacement string
        # For "0.9:" → "9.0:", we want first digit 0→9, second digit 9→0
        # For "1.2:" → "0.2:", we want first digit 1→0, second digit 2→2 (no change)
        import re
        orig_digits = re.findall(r'\d', original)
        repl_digits = re.findall(r'\d', replacement)
        
        if len(orig_digits) != 2 or len(repl_digits) != 2:
            return False
        
        orig_digit1, orig_digit2 = orig_digits[0], orig_digits[1]
        repl_digit1, repl_digit2 = repl_digits[0], repl_digits[1]
        
        success = False

        # Modify the first array: replace "0" with "9"
        first_op_index = window_ops[0][0]
        operands, operator = operations[first_op_index]
        if operator == b"TJ" and operands:
            array_obj = operands[0]
            if isinstance(array_obj, ArrayObject):
                new_array = self._replace_digit_in_array(array_obj, orig_digit1, repl_digit1)
                if new_array:
                    operations[first_op_index] = ([new_array], operator)
                    success = True

        # Modify the second array: replace "9:" with ".0:"
        second_op_index = window_ops[1][0]
        operands, operator = operations[second_op_index]
        if operator == b"TJ" and operands:
            array_obj = operands[0]
            if isinstance(array_obj, ArrayObject):
                new_array = self._replace_digit_with_decimal_in_array(
                    array_obj, orig_digit2, repl_digit2
                )
                if new_array:
                    operations[second_op_index] = ([new_array], operator)
                    success = True

        if success:
            self.logger.logger.debug(f"Applied decimal cross-array replacement: {original} → {replacement}")
        
        return success
    
    def _apply_simple_cross_array_replacement(self, operations: List[Tuple], match: Dict) -> bool:
        """Apply simple replacement in the first array."""
        window_ops = match['window_operations']
        original = match['original']
        replacement = match['replacement']
        
        target_op_index = window_ops[0][0]
        operands, operator = operations[target_op_index]
        if operator == b"TJ" and operands:
            array_obj = operands[0]
            if isinstance(array_obj, ArrayObject):
                modified_array = self._create_modified_array_for_cross_replacement(
                    array_obj, original, replacement, match
                )

                if modified_array:
                    operations[target_op_index] = ([modified_array], operator)
                    self.logger.logger.debug(f"Applied simple cross-array replacement to operation {target_op_index}")
                    return True
        
        return False
    
    def _create_modified_array_for_cross_replacement(self, array_obj: ArrayObject, 
                                                   original: str, replacement: str, 
                                                   match: Dict) -> Optional[ArrayObject]:
        """
        Create a modified array for cross-array replacement.
        
        For decimal number cases like "0.9:" split across arrays,
        we need to properly distribute the replacement text.
        """
        new_array = ArrayObject()
        
        # For split decimal patterns like "0.9:" → "9.0:", we need to:
        # 1. Replace the digit in the first array with the replacement digit
        # 2. Handle the decimal point and remaining parts appropriately
        
        for item in array_obj:
            if isinstance(item, TextStringObject):
                text = str(item)
                
                # Handle decimal number replacements specifically
                if '.' in original and ':' in original:
                    # This is a decimal pattern like "0.9:" → "9.0:"
                    orig_parts = original.split('.')
                    repl_parts = replacement.split('.')
                    
                    if len(orig_parts) == 2 and len(repl_parts) == 2:
                        orig_digit = orig_parts[0]  # "0"
                        repl_digit = repl_parts[0]  # "9"
                        
                        # If this text contains the first digit, replace it
                        if orig_digit in text:
                            modified_text = text.replace(orig_digit, repl_digit)
                            new_array.append(TextStringObject(modified_text))
                            continue
                
                # Fallback: general digit replacement
                if any(char.isdigit() for char in text) and any(char.isdigit() for char in original):
                    # Extract digits from original and replacement
                    orig_digits = ''.join(c for c in original if c.isdigit())
                    repl_digits = ''.join(c for c in replacement if c.isdigit())
                    
                    if orig_digits and repl_digits:
                        # Replace first digit with first replacement digit
                        first_orig_digit = orig_digits[0]
                        first_repl_digit = repl_digits[0]
                        
                        if first_orig_digit in text:
                            modified_text = text.replace(first_orig_digit, first_repl_digit)
                            new_array.append(TextStringObject(modified_text))
                            continue
                
                new_array.append(item)
            else:
                new_array.append(item)
        
        return new_array
    
    def _replace_digit_in_array(self, array_obj: ArrayObject, old_digit: str, new_digit: str) -> Optional[ArrayObject]:
        """Replace a digit in an array object."""
        new_array = ArrayObject()
        modified = False
        
        for item in array_obj:
            if isinstance(item, TextStringObject):
                text = str(item)
                if old_digit in text:
                    modified_text = text.replace(old_digit, new_digit)
                    new_array.append(TextStringObject(modified_text))
                    modified = True
                else:
                    new_array.append(item)
            else:
                new_array.append(item)
        
        return new_array if modified else None
    
    def _replace_digit_with_decimal_in_array(self, array_obj: ArrayObject, old_digit: str, new_digit: str) -> Optional[ArrayObject]:
        """Replace a digit with a decimal format (e.g., '9:' → '.0:')."""
        new_array = ArrayObject()
        modified = False
        
        for item in array_obj:
            if isinstance(item, TextStringObject):
                text = str(item)
                # Look for the pattern like "9:" and replace with ".0:"
                if old_digit + ':' in text:
                    modified_text = text.replace(old_digit + ':', '.' + new_digit + ':')
                    new_array.append(TextStringObject(modified_text))
                    modified = True
                elif old_digit in text and not '.' in text:
                    # Only add decimal if there isn't one already
                    modified_text = text.replace(old_digit, '.' + new_digit)
                    new_array.append(TextStringObject(modified_text))
                    modified = True
                else:
                    new_array.append(item)
            else:
                new_array.append(item)
        
        return new_array if modified else None
    
    def _apply_pattern_replacement(self, text: str) -> str:
        """Apply simple pattern replacement to text."""
        if not self.pattern:
            return text
        
        # Apply replacements using the pattern
        result = text
        for match in reversed(list(self.pattern.finditer(text))):
            original = match.group(0)
            replacement = self._resolve_replacement(original)
            if replacement and replacement != original:
                start, end = match.span()
                result = result[:start] + replacement + result[end:]
        
        return result


def process_content_stream_with_cross_array_support(
    operations: List[Tuple],
    pattern: Pattern[str],
    mapping: Dict[str, str],
    mapping_cf: Dict[str, str]
) -> Tuple[List[Tuple], bool]:
    """
    Process content stream operations with cross-array pattern support.
    
    Args:
        operations: List of (operands, operator) tuples
        pattern: Compiled regex pattern
        mapping: Exact case mapping dictionary
        mapping_cf: Case-insensitive mapping dictionary
        
    Returns:
        Tuple of (modified_operations, was_modified)
    """
    processor = CrossArrayProcessor(pattern, mapping, mapping_cf)
    return processor.process_content_operations(operations)
