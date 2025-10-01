"""Comprehensive logging system for PDF glyph remapping operations."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Create logs directory
LOGS_DIR = Path("/Users/ashishrajshekhar/codex_code_glyph/logs")
RUNS_DIR = Path("/Users/ashishrajshekhar/codex_code_glyph/runs")

LOGS_DIR.mkdir(exist_ok=True)
RUNS_DIR.mkdir(exist_ok=True)

class PDFProcessingLogger:
    """Logger for tracking PDF processing operations with detailed steps."""
    
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        self.run_dir = RUNS_DIR / self.run_id
        self.run_dir.mkdir(exist_ok=True)
        
        # Set up file logging
        log_file = LOGS_DIR / f"pdf_processing_{self.run_id}.log"
        self.logger = logging.getLogger(f"pdf_processor_{self.run_id}")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler with detailed formatting
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)8s | %(funcName)20s:%(lineno)4d | %(message)s'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler for important messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Initialize run metadata
        self.run_metadata = {
            "run_id": self.run_id,
            "start_time": datetime.now().isoformat(),
            "mode": None,
            "mappings": {},
            "steps": [],
            "errors": [],
            "results": {}
        }
        
        self.logger.info(f"=== Starting PDF Processing Run: {self.run_id} ===")
    
    def log_input_pdf(self, pdf_bytes: bytes, filename: str = "input.pdf"):
        """Save and log the input PDF."""
        input_path = self.run_dir / filename
        input_path.write_bytes(pdf_bytes)
        
        self.logger.info(f"Input PDF saved: {input_path} ({len(pdf_bytes)} bytes)")
        self.run_metadata["input_pdf"] = {
            "filename": filename,
            "size_bytes": len(pdf_bytes),
            "path": str(input_path)
        }
    
    def log_mode_selection(self, mode: str):
        """Log the processing mode selection."""
        self.logger.info(f"Processing mode selected: {mode}")
        self.run_metadata["mode"] = mode
    
    def log_mappings(self, mappings: Dict[str, str]):
        """Log the word mappings to be applied."""
        self.logger.info(f"Word mappings to apply: {len(mappings)} total")
        for original, replacement in mappings.items():
            self.logger.info(f"  '{original}' → '{replacement}'")
        
        self.run_metadata["mappings"] = mappings
    
    def log_text_extraction(self, text: str, max_preview: int = 500):
        """Log extracted text preview."""
        preview = text[:max_preview] + "..." if len(text) > max_preview else text
        self.logger.info(f"Extracted text ({len(text)} chars): {repr(preview)}")
        
        # Save full text to file
        text_file = self.run_dir / "extracted_text.txt"
        text_file.write_text(text, encoding='utf-8')
        self.logger.debug(f"Full extracted text saved to: {text_file}")
    
    def log_pattern_building(self, words: List[str], pattern_str: str, ignore_case: bool):
        """Log regex pattern construction."""
        self.logger.info(f"Building regex pattern for {len(words)} words (ignore_case={ignore_case})")
        self.logger.debug(f"Words to match: {words}")
        self.logger.debug(f"Compiled pattern: {pattern_str}")
    
    def log_word_occurrences(self, word: str, count: int):
        """Log word occurrence counts."""
        self.logger.debug(f"Word '{word}': {count} occurrences found")
    
    def log_text_segment_analysis(self, text: str, segments: Optional[List], original: str, replacement: str):
        """Log detailed text segmentation analysis."""
        if segments is None:
            self.logger.debug(f"No matches found for '{original}' in text: {repr(text[:100])}")
            return
        
        self.logger.debug(f"Text segmentation for '{original}' → '{replacement}':")
        self.logger.debug(f"  Original text: {repr(text)}")
        self.logger.debug(f"  Segments: {segments}")
        
        # Show what will change
        rebuilt = []
        changes = []
        for segment_text, repl in segments:
            if repl is not None:
                rebuilt.append(repl)
                changes.append(f"'{segment_text}' → '{repl}'")
            else:
                rebuilt.append(segment_text)
        
        if changes:
            final_text = "".join(rebuilt)
            self.logger.info(f"Text replacement in segment: {changes}")
            self.logger.debug(f"  Result: {repr(final_text)}")
        else:
            self.logger.debug(f"  No changes made to this segment")
    
    def log_content_stream_operation(self, operator: bytes, operands: List, page_num: int, op_index: int):
        """Log PDF content stream operations."""
        self.logger.debug(f"Page {page_num}, Op {op_index}: {operator} with {len(operands)} operands")
        
        if operator in [b"Tj", b"TJ"]:
            # Log text operations specifically
            if operator == b"Tj" and operands:
                text = str(operands[0])
                self.logger.debug(f"  Tj text: {repr(text)}")
            elif operator == b"TJ" and operands:
                from PyPDF2.generic import ArrayObject, TextStringObject
                array_obj = operands[0]
                if isinstance(array_obj, ArrayObject):
                    text_elements = [str(item) for item in array_obj if isinstance(item, TextStringObject)]
                    self.logger.debug(f"  TJ array texts: {text_elements}")
    
    def log_replacement_attempt(self, original_text: str, pattern_str: str, mapping: Dict[str, str], result: Optional[str]):
        """Log individual text replacement attempts."""
        if result is not None:
            self.logger.info(f"✅ Replacement successful: {repr(original_text)} → {repr(result)}")
            self.run_metadata["steps"].append({
                "type": "replacement_success",
                "original": original_text,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
        else:
            self.logger.debug(f"❌ No replacement needed for: {repr(original_text)}")
    
    def log_fallback(self, from_mode: str, to_mode: str, reason: str):
        """Log mode fallback events."""
        self.logger.warning(f"Falling back from {from_mode} to {to_mode}: {reason}")
        self.run_metadata["steps"].append({
            "type": "fallback",
            "from_mode": from_mode,
            "to_mode": to_mode,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_error(self, error: Exception, context: str):
        """Log errors with context."""
        error_msg = f"Error in {context}: {type(error).__name__}: {error}"
        self.logger.error(error_msg)
        self.run_metadata["errors"].append({
            "context": context,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat()
        })
    
    def log_output_pdf(self, pdf_bytes: bytes, filename: str = "output.pdf"):
        """Save and log the output PDF."""
        output_path = self.run_dir / filename
        output_path.write_bytes(pdf_bytes)
        
        self.logger.info(f"Output PDF saved: {output_path} ({len(pdf_bytes)} bytes)")
        self.run_metadata["results"]["output_pdf"] = {
            "filename": filename,
            "size_bytes": len(pdf_bytes),
            "path": str(output_path)
        }
    
    def log_font_analysis(self, font_path: str, char_availability: Dict[str, bool]):
        """Log font character availability analysis."""
        available = sum(1 for v in char_availability.values() if v)
        total = len(char_availability)
        
        self.logger.info(f"Font analysis for {font_path}: {available}/{total} characters available")
        for char, available in char_availability.items():
            status = "✅" if available else "❌"
            self.logger.debug(f"  Character '{char}': {status}")
    
    def finalize_run(self):
        """Finalize the run and save metadata."""
        self.run_metadata["end_time"] = datetime.now().isoformat()
        
        # Calculate duration
        start = datetime.fromisoformat(self.run_metadata["start_time"])
        end = datetime.fromisoformat(self.run_metadata["end_time"])
        duration = (end - start).total_seconds()
        self.run_metadata["duration_seconds"] = duration
        
        # Save metadata
        metadata_file = self.run_dir / "run_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.run_metadata, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"=== Run Complete: {self.run_id} (Duration: {duration:.2f}s) ===")
        self.logger.info(f"Run directory: {self.run_dir}")
        self.logger.info(f"Metadata saved: {metadata_file}")
        
        # Summary
        mappings_count = len(self.run_metadata.get("mappings", {}))
        errors_count = len(self.run_metadata.get("errors", []))
        
        if errors_count > 0:
            self.logger.warning(f"Run completed with {errors_count} errors")
        else:
            self.logger.info(f"Run completed successfully with {mappings_count} mappings applied")


# Global logger instance
_current_logger: Optional[PDFProcessingLogger] = None

def get_logger() -> PDFProcessingLogger:
    """Get the current logger instance."""
    global _current_logger
    if _current_logger is None:
        _current_logger = PDFProcessingLogger()
    return _current_logger

def start_new_run(run_id: Optional[str] = None) -> PDFProcessingLogger:
    """Start a new logging run."""
    global _current_logger
    _current_logger = PDFProcessingLogger(run_id)
    return _current_logger

def finish_current_run():
    """Finalize the current run."""
    global _current_logger
    if _current_logger:
        _current_logger.finalize_run()
        _current_logger = None