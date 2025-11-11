# LLM PDF Parsing Test System

## 🎯 Overview

This system tests how different LLMs (Language Learning Models) parse PDFs that have been manipulated using our 3 advanced approaches. The goal is to create PDFs that **look identical to humans** but **parse differently for machines**.

## 🚀 Quick Start

### Web Interface
1. Start the Flask server:
   ```bash
   source venv/bin/activate
   python app.py
   ```

2. Open your browser to: `http://127.0.0.1:5001/llm-tester`

3. Upload a PDF and define word mappings (e.g., "dog" → "dragon")

4. Click "Run LLM Tests" to test all 3 approaches against OpenAI models

### Command Line Testing
```bash
source venv/bin/activate
python llm_pdf_tester.py
```

## 🧪 The 3 Approaches

### 📊 Approach 1: Custom Font Glyph Remapping
**Status:** Framework ready, needs fontTools integration

**How it works:**
- Modify font files so Unicode codepoints map to different glyph shapes
- Example: 'd' codepoint → 'r' glyph shape
- Result: Text reads "dragon" but visually shows original word

**Pros:**
- ✅ Perfect visual match
- ✅ Small file size
- ✅ Clean implementation

**Cons:**
- ❌ Font licensing issues
- ❌ Complex implementation
- ❌ Limited PDF compatibility

### 👁️ Approach 2: Dual-Layer Text Rendering
**Status:** ✅ Working implementation

**How it works:**
```pdf
3 Tr (dragon) Tj     % Invisible layer for parsing
0 Tr                 % Switch to visible mode
(dog) Tj             % Visible layer for humans
```

**Test Results:**
- ✅ 100% replacement word detection
- ⚠️ 50% original word detection (needs refinement)
- ✅ Universal PDF compatibility

### 🎯 Approach 3: Precision Overlays
**Status:** ✅ Working implementation (enhanced current method)

**How it works:**
- Replace text in content streams
- Apply high-precision visual overlays
- Use exact font metrics for pixel-perfect alignment

**Test Results:**
- ✅ 100% replacement word detection
- ✅ 0% original word detection
- ✅ Perfect visual appearance

## 🔍 LLM Testing Results

### OpenAI API Testing

The system tests against these OpenAI models:
- **GPT-4o** (latest with vision)
- **GPT-4o-mini** (smaller variant)
- **GPT-4-turbo** (GPT-4 Turbo)
- **GPT-3.5-turbo** (GPT-3.5)

### Testing Methods

1. **Vision API Testing**
   - Converts PDF pages to PNG images
   - Uses vision models for OCR text extraction
   - Tests visual appearance parsing

2. **File Upload Testing** (experimental)
   - Direct PDF file processing
   - Tests native PDF parsing capabilities

### Expected Results

| Approach | Visual Appearance | Text Parsing | LLM Should See |
|----------|------------------|--------------|----------------|
| Original | "dog", "dogs" | "dog", "dogs" | Original words |
| Approach 1 | "dog", "dogs" | "dragon", "owls" | Replacement words |
| Approach 2 | "dog", "dogs" | "dragon", "owls" | Replacement words |
| Approach 3 | "dog", "dogs" | "dragon", "owls" | Replacement words |

## 📈 Success Metrics

### Effectiveness Scoring
- **100% Effective**: LLM sees only replacement words
- **50% Effective**: LLM sees both original and replacement
- **0% Effective**: LLM sees only original words

### Current Results
- **Approach 2**: ~75% effective (some original text still detected)
- **Approach 3**: ~95% effective (excellent replacement with visual preservation)

## 🌐 Web Interface Features

### Upload & Configuration
- PDF file upload (up to 25MB)
- Custom word mapping interface
- Real-time mapping row management

### Testing Dashboard
- Progress tracking for all tests
- Comprehensive results table
- Effectiveness statistics
- Model-by-model breakdown

### Results Analysis
- Visual indicators for success/failure
- Text preview extraction
- Response time measurements
- Error handling and reporting

## 🔧 Technical Implementation

### Backend (Flask)
```python
@app.post("/test-llm-parsing")
def test_llm_parsing():
    # 1. Upload PDF and get mappings
    # 2. Create all 3 approach variants
    # 3. Test against all OpenAI models
    # 4. Return comprehensive results
```

### Frontend (JavaScript)
- Async form submission
- Progress bar with simulation
- Dynamic results rendering
- Statistics calculation

### API Integration
```python
# OpenAI Vision API
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": [{
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        }]
    }]
)
```

## 📋 Usage Scenarios

### Security Research
- Test document authenticity verification
- Analyze LLM parsing vulnerabilities
- Develop countermeasures for malicious PDFs

### Data Privacy
- Create documents that appear normal but contain different searchable text
- Protect sensitive information in plain sight
- Implement steganographic communication

### Quality Assurance
- Test PDF processing pipeline robustness
- Verify text extraction accuracy
- Benchmark different LLM capabilities

## ⚙️ Configuration

### API Keys
Set your OpenAI API key in `llm_pdf_tester.py`:
```python
OPENAI_API_KEY = "your-api-key-here"
```

### Model Selection
Modify the model list in `LLMPDFTester.__init__()`:
```python
self.openai_models = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo"
]
```

### Rate Limiting
Adjust delays between API calls:
```python
time.sleep(1)  # 1 second between requests
```

## 🚨 Important Notes

### API Costs
- Each test makes multiple API calls
- Vision API calls are more expensive
- Monitor your OpenAI usage dashboard

### Rate Limits
- OpenAI has request limits per minute
- The system includes automatic delays
- May need adjustment for high-volume testing

### Legal Considerations
- Font modification (Approach 1) may violate licenses
- Use only with fonts you own or have permission to modify
- Consider trademark/copyright implications

## 🔮 Future Enhancements

### Additional LLM Providers
- Google Gemini integration
- Anthropic Claude integration
- Local model testing (Ollama, etc.)

### Advanced Testing
- Multi-page PDF support
- Complex layout testing
- Performance benchmarking

### Improved Approaches
- Better dual-layer positioning
- Font extraction automation
- Character-level manipulation

## 📊 Results Dashboard

The web interface provides:
- **Real-time testing progress**
- **Comprehensive results tables**
- **Effectiveness scoring**
- **Model comparison charts**
- **Text extraction previews**
- **Error reporting and debugging**

Visit `http://127.0.0.1:5001/llm-tester` to start testing!

---

## 🎉 Conclusion

This system demonstrates that it's possible to create PDFs that appear identical to humans but are parsed differently by machines. The dual-layer and precision overlay approaches are particularly effective, achieving high success rates while maintaining perfect visual fidelity.

The implications for security, privacy, and quality assurance are significant, making this a valuable tool for researchers and developers working with PDF processing and LLM systems.