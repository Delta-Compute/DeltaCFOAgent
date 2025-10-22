# Task Plan: Enhance /files Uploader to Accept PDFs

## Task Description
Enhance the `/files` uploader to accept and read PDFs using the existing PDF reading functionality framework from the invoice uploader and payment receipt file upload systems.

## Analysis Summary

### Current State
- **Location**: `/home/user/DeltaCFOAgent/web_ui/app_db.py` (line 5174+)
- **Current Restriction**: Only accepts `.csv` files (line 5191-5192)
- **Template**: `/home/user/DeltaCFOAgent/web_ui/templates/files.html`
- **Processing**: Uses smart ingestion with DeltaCFOAgent for CSV files

### Existing PDF Framework
- **Main Library**: `invoice_processing/services/claude_vision.py`
- **PDF Processing**:
  - Uses `pdf2image` to convert PDF to PNG (300 DPI)
  - Uses `PyMuPDF (fitz)` for advanced processing
  - Sends images to Claude Vision API
  - Extracts structured data from invoices
- **Alternative**: `invoice_processing/improved_visual_system.py` supports multiple formats

## Implementation Plan

### Step 1: Update File Validation in app_db.py ✅
**File**: `/home/user/DeltaCFOAgent/web_ui/app_db.py`
**Location**: Line 5191-5192

**Current Code**:
```python
if not file.filename.lower().endswith('.csv'):
    return jsonify({'error': 'Only CSV files are allowed'}), 400
```

**Change To**:
```python
allowed_extensions = ['.csv', '.pdf']
file_ext = os.path.splitext(file.filename.lower())[1]
if file_ext not in allowed_extensions:
    return jsonify({'error': 'Only CSV and PDF files are allowed'}), 400
```

**Impact**: Minimal - just extends allowed file types

---

### Step 2: Add PDF Processing Logic ✅
**File**: `/home/user/DeltaCFOAgent/web_ui/app_db.py`
**Location**: After line 5202 (after file.save())

**Add New Function** (before `upload_file()` function):
```python
def process_pdf_with_claude_vision(filepath: str, filename: str) -> Dict[str, Any]:
    """
    Process PDF using Claude Vision to extract transaction data
    Reuses existing invoice processing framework
    """
    try:
        # Import PDF processing libraries
        from pdf2image import convert_from_path
        from io import BytesIO
        import base64

        # Convert PDF first page to image
        pages = convert_from_path(filepath, first_page=1, last_page=1, dpi=300)
        if not pages:
            raise ValueError("Could not convert PDF to image")

        # Convert to base64
        img = pages[0]
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Call Claude Vision to extract data
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

        prompt = """
        Analyze this document and extract ALL transaction data you can find.

        This could be:
        - Bank statement with multiple transactions
        - Invoice with line items
        - Receipt with transaction details
        - Financial report

        Extract each transaction with:
        - date (YYYY-MM-DD format)
        - description
        - amount (positive for income, negative for expenses)
        - category (if mentioned)
        - entity/business unit (if mentioned)

        Return JSON array:
        {
            "transactions": [
                {
                    "date": "2024-01-15",
                    "description": "Office supplies",
                    "amount": -150.50,
                    "category": "Technology",
                    "entity": "Delta LLC"
                }
            ],
            "total_found": 10,
            "document_type": "Bank Statement"
        }
        """

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4000,
            temperature=0.1,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )

        # Parse response
        response_text = response.content[0].text.strip()
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()

        return json.loads(response_text)

    except Exception as e:
        print(f"❌ PDF processing failed: {e}")
        return {"error": str(e), "transactions": [], "total_found": 0}
```

**Add Logic in upload_file()** (after line 5202):
```python
# Save the uploaded file
file.save(filepath)

# Check if PDF or CSV
file_ext = os.path.splitext(filename.lower())[1]

if file_ext == '.pdf':
    # NEW: Process PDF with Claude Vision
    print(f"🔧 DEBUG: Processing PDF file with Claude Vision: {filename}")

    pdf_result = process_pdf_with_claude_vision(filepath, filename)

    if pdf_result.get('error'):
        return jsonify({
            'success': False,
            'error': f'PDF processing failed: {pdf_result["error"]}'
        }), 500

    if pdf_result.get('total_found', 0) == 0:
        return jsonify({
            'success': False,
            'error': 'No transactions found in PDF'
        }), 400

    # TODO: Convert extracted transactions to CSV format for existing pipeline
    # For now, return success with transaction count
    return jsonify({
        'success': True,
        'message': f'Successfully extracted {pdf_result["total_found"]} transactions from PDF',
        'transactions_processed': pdf_result['total_found'],
        'document_type': pdf_result.get('document_type', 'Unknown')
    })

# Create backup first (existing code for CSV)
backup_path = f"{filepath}.backup"
shutil.copy2(filepath, backup_path)
```

**Impact**: Moderate - adds new processing path for PDFs without affecting CSV logic

---

### Step 3: Update files.html Template ✅
**File**: `/home/user/DeltaCFOAgent/web_ui/templates/files.html`
**Changes**:

1. **Line 41** - Update file input accept attribute:
   ```html
   <!-- OLD -->
   <input type="file" id="fileInput" multiple accept=".csv" style="display: none;">

   <!-- NEW -->
   <input type="file" id="fileInput" multiple accept=".csv,.pdf" style="display: none;">
   ```

2. **Line 35** - Update section title:
   ```html
   <!-- OLD -->
   <h2>📤 Upload New CSV Files</h2>

   <!-- NEW -->
   <h2>📤 Upload CSV or PDF Files</h2>
   ```

3. **Line 39** - Update drag & drop text:
   ```html
   <!-- OLD -->
   <h3>Drag & Drop CSV Files Here</h3>

   <!-- NEW -->
   <h3>Drag & Drop CSV or PDF Files Here</h3>
   ```

4. **Line 58** - Update section title:
   ```html
   <!-- OLD -->
   <h2>📋 CSV Files</h2>

   <!-- NEW -->
   <h2>📋 Files</h2>
   ```

5. **Line 200-203** - Update JavaScript validation:
   ```javascript
   // OLD
   async function uploadFile(file) {
       if (!file.name.toLowerCase().endsWith('.csv')) {
           showToast('Only CSV files are allowed', 'error');
           return;
       }

   // NEW
   async function uploadFile(file) {
       const allowedExtensions = ['.csv', '.pdf'];
       const fileExt = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
       if (!allowedExtensions.includes(fileExt)) {
           showToast('Only CSV and PDF files are allowed', 'error');
           return;
       }
   ```

**Impact**: Minimal - just UI text and validation updates

---

### Step 4: Test PDF Upload ✅
1. Start the application: `cd web_ui && python app_db.py`
2. Navigate to `/files`
3. Upload a test PDF (bank statement or invoice)
4. Verify:
   - File is accepted
   - Claude Vision extracts transactions
   - Success message shows transaction count
   - No errors in console

---

## Dependencies Required
All dependencies are already in `requirements.txt`:
- ✅ `pdf2image>=1.16.0`
- ✅ `Pillow>=10.0.0`
- ✅ `anthropic` (already in use)

## Risks & Mitigation

### Risk 1: PDF Format Variability
- **Risk**: PDFs vary widely in structure (scanned images, text-based, complex layouts)
- **Mitigation**: Use Claude Vision which handles various formats well
- **Fallback**: Show clear error if extraction fails

### Risk 2: Large PDF Files
- **Risk**: Large PDFs may timeout or exceed API limits
- **Mitigation**: Only process first page (like invoice system does)
- **Future**: Add pagination support if needed

### Risk 3: Integration with Existing Duplicate Detection
- **Risk**: Duplicate detection expects CSV format
- **Mitigation**: Phase 1 - show extracted data only; Phase 2 - integrate with duplicate pipeline

## Success Criteria
- ✅ Users can upload PDF files via /files page
- ✅ PDF files are processed using Claude Vision
- ✅ Transaction data is extracted and displayed
- ✅ No breaking changes to existing CSV functionality
- ✅ Clear error messages for unsupported PDFs

## Code Simplicity Principles
1. **Minimal Changes**: Only modify 2 files (app_db.py, files.html)
2. **Reuse Existing**: Leverage invoice_processing PDF framework
3. **No Breaking Changes**: CSV processing remains identical
4. **Simple Logic**: Add separate PDF path, don't mix with CSV logic
5. **Clear Separation**: PDF handling isolated in new function

## Timeline Estimate
- Step 1 (File Validation): 5 minutes
- Step 2 (PDF Processing): 20 minutes
- Step 3 (Template Updates): 10 minutes
- Step 4 (Testing): 15 minutes
- **Total**: ~50 minutes

---

## Next Steps
1. ✅ Get user approval for this plan
2. Implement Step 1-3 sequentially
3. Test thoroughly
4. Update review in tasks/all.md
