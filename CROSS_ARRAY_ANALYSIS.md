# Cross-Array Pattern Matching Analysis

## Problem Statement

Numbers and other patterns can be split across multiple TJ array operations in PDFs, making single-array processing insufficient for complete pattern recognition.

## Discovered Case: Decimal Numbers

### Input Pattern: `0.9:` and `1.2:`

**Actual PDF Structure:**
```
TJ Array 1: ['=', '0']
TJ Array 2: ['9:', 'Will', 'gradient', ...]

TJ Array 3: ['=', '1'] 
TJ Array 4: ['2:', 'Will', 'gradient', ...]
```

**Expected Reconstruction:**
- `= 0` + `9:` → `= 0.9:` → target pattern `0.9:`
- `= 1` + `2:` → `= 1.2:` → target pattern `1.2:`

## Solution Strategy

### Phase 1: Cross-Array Text Reconstruction
Build a **sliding window** approach that combines text from consecutive TJ operations to identify patterns that span multiple arrays.

### Phase 2: Pattern Recognition Scope
- **Single Array**: Current V2 processor (✅ working)
- **Cross Array**: New cross-array processor for patterns spanning multiple TJ operations
- **Cross Page**: Future enhancement for patterns spanning pages

### Phase 3: Implementation Approach

#### Option A: Content Stream Level Processing
Process the entire content stream to build a complete text representation, then apply replacements and map back to individual operations.

#### Option B: Sliding Window Approach  
Use a sliding window that looks at N consecutive TJ operations to identify cross-array patterns.

#### Option C: Hybrid Approach (Recommended)
- Use V2 processor for intra-array patterns
- Add cross-array processor for patterns spanning multiple arrays
- Fallback chain: Single Array → Cross Array → Content Stream

## Technical Implementation

### 1. Cross-Array Text Builder
```python
def build_cross_array_text(operations, start_index, window_size=5):
    """Build text from multiple consecutive TJ operations."""
    text_parts = []
    for i in range(start_index, min(start_index + window_size, len(operations))):
        if operations[i][1] == b"TJ":
            # Extract text from this TJ operation
            array_text = extract_tj_array_text(operations[i][0][0])
            text_parts.append(array_text)
    return ' '.join(text_parts)
```

### 2. Pattern Matching Strategy
```python
def find_cross_array_patterns(operations, patterns):
    """Find patterns that span multiple TJ operations."""
    matches = []
    for i in range(len(operations)):
        if operations[i][1] == b"TJ":
            # Build sliding window text
            window_text = build_cross_array_text(operations, i, window_size=5)
            # Check for pattern matches
            for pattern in patterns:
                if pattern.search(window_text):
                    matches.append((i, pattern, window_text))
    return matches
```

### 3. Replacement Application
```python
def apply_cross_array_replacements(operations, matches, mapping):
    """Apply replacements across multiple TJ operations."""
    # Sort matches by operation index (reverse order for safe replacement)
    # Apply replacements while maintaining TJ array structure
    # Update multiple operations as needed
```

## Test Cases Required

### 1. Simple Cross-Array Numbers
- Input: `['=', '0']` + `['9:', ...]` 
- Expected: `['=', '9']` + `['.0:', ...]`

### 2. Mathematical Expressions
- Input: `['∥Wh∥=', '0']` + `['.9:', ...]`
- Expected: `['∥Wh∥=', '9']` + `['.0:', ...]`

### 3. Multi-Digit Numbers
- Input: `['1']` + `['2']` + `['.5:', ...]`
- Expected: Complex redistribution

### 4. Mixed Content
- Input: `['value', '0']` + `['.9', 'percent']`
- Expected: Proper boundary detection

## Implementation Priority

1. **High Priority**: Simple decimal numbers (0.9, 1.2)
2. **Medium Priority**: Complex mathematical notation
3. **Low Priority**: Multi-digit spanning cases

## Performance Considerations

- **Window Size**: Balance between pattern detection and performance
- **Cache Results**: Avoid reprocessing the same operation sequences
- **Early Termination**: Stop window expansion when no patterns possible

## Integration Strategy

### Current V2 Processor Enhancement
```python
class TJArrayProcessorV3:
    def process_content_stream(self, operations):
        # Phase 1: Apply V2 processor to each TJ array
        # Phase 2: Apply cross-array processor for remaining patterns
        # Phase 3: Rebuild content stream with all changes
```

### Fallback Chain
1. **V2 Processor**: Handle intra-array patterns
2. **Cross-Array Processor**: Handle cross-array patterns  
3. **Content Stream Processor**: Handle complex multi-operation patterns
4. **No Change**: Return original if no patterns found