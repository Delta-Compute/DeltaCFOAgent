#!/usr/bin/env python3
"""
Multi-File Upload System - Enhanced test_full_pipeline.py with multi-file support
"""

import os
import sys
import sqlite3
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
import uuid
import json
import anthropic
import base64
import zipfile
import tempfile

# Configuration
CLAUDE_API_KEY = os.getenv('ANTHROPIC_API_KEY') or input("Cole sua API key da Anthropic: ")

app = Flask(__name__)
app.secret_key = 'multi_file_secret_key'

# Database setup
DB_PATH = Path(__file__).parent / "full_pipeline_test.db"

def init_db():
    """Initialize complete test database"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            invoice_number TEXT,
            date TEXT,
            vendor_name TEXT,
            vendor_data TEXT,
            total_amount REAL,
            currency TEXT,
            business_unit TEXT,
            category TEXT,
            confidence_score REAL,
            processing_notes TEXT,
            source_file TEXT,
            processed_at TEXT,
            created_at TEXT,
            extraction_method TEXT,
            raw_claude_response TEXT
        )
    ''')
    conn.commit()
    conn.close()

class SimplifiedClaudeVision:
    """Simplified Claude Vision for testing"""

    def __init__(self, api_key):
        self.client = anthropic.Anthropic(api_key=api_key)

    def extract_invoice_data(self, file_path):
        """Extract data from text file or PDF"""
        try:
            content = ""
            file_path_str = str(file_path)

            # Handle different file types
            if file_path_str.endswith('.txt') or file_path_str.endswith('.csv'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                extraction_type = "text_analysis"

            elif file_path_str.endswith('.pdf'):
                # Convert PDF to image and use vision
                image_base64 = self._pdf_to_image_base64(file_path_str)
                return self._call_claude_vision_with_image(image_base64, file_path_str)

            else:
                return {
                    'status': 'error',
                    'error': f'Unsupported file type: {os.path.splitext(file_path_str)[1]}'
                }

            # For text files, use text analysis
            prompt = f"""
Analyze this invoice text and extract information in JSON format:

{content}

Return ONLY a JSON object with this structure:
{{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "vendor_name": "string",
    "total_amount": 1234.56,
    "currency": "USD",
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Analysis notes"
}}
"""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response_text = response.content[0].text.strip()

            # Clean JSON response
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)

            # Add metadata
            extracted_data.update({
                'source_file': os.path.basename(file_path_str),
                'extraction_method': extraction_type,
                'processed_at': datetime.now().isoformat(),
                'status': 'success'
            })

            return extracted_data

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'source_file': os.path.basename(str(file_path)) if file_path else 'unknown'
            }

    def _pdf_to_image_base64(self, pdf_path):
        """Convert PDF first page to base64 image using PyMuPDF"""
        try:
            import fitz  # PyMuPDF

            # Open PDF and get first page
            doc = fitz.open(pdf_path)
            if doc.page_count == 0:
                raise ValueError("PDF has no pages")

            # Get first page as image
            page = doc.load_page(0)  # First page
            mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)

            # Convert to PNG bytes
            image_bytes = pix.pil_tobytes(format="PNG")
            doc.close()

            return base64.b64encode(image_bytes).decode('utf-8')

        except ImportError:
            raise ValueError("PyMuPDF not installed. Run: pip install PyMuPDF")
        except Exception as e:
            raise ValueError(f"PDF conversion failed: {e}")

    def _call_claude_vision_with_image(self, image_base64, file_path):
        """Call Claude Vision API with image"""
        try:
            prompt = """
Analyze this invoice image and extract the following information in JSON format.

Extract these fields with high accuracy:

REQUIRED FIELDS:
- invoice_number: The invoice/bill number
- date: Invoice date (YYYY-MM-DD format)
- vendor_name: Company/vendor name
- total_amount: Total amount (numeric value only)
- currency: Currency (USD, BRL, etc.)

CLASSIFICATION HINTS:
Based on the vendor, suggest:
- business_unit: One of ["Delta LLC", "Delta Prop Shop LLC", "Delta Mining Paraguay S.A.", "Delta Brazil", "Personal"]
- category: One of ["Technology Expenses", "Utilities", "Insurance", "Professional Services", "Trading Expenses", "Other"]

Return ONLY a JSON object with this structure:
{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "vendor_name": "string",
    "total_amount": 1234.56,
    "currency": "USD",
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Analysis notes"
}

Be precise with numbers and dates. If a field is not clearly visible, use reasonable defaults.
"""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
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

            response_text = response.content[0].text.strip()

            # Clean JSON response
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)

            # Add metadata
            extracted_data.update({
                'source_file': os.path.basename(file_path),
                'extraction_method': 'claude_vision',
                'processed_at': datetime.now().isoformat(),
                'status': 'success'
            })

            return extracted_data

        except Exception as e:
            return {
                'status': 'error',
                'error': f"Vision API error: {str(e)}"
            }

# Initialize Claude service
claude_service = SimplifiedClaudeVision(CLAUDE_API_KEY)

# Enhanced HTML template with multi-file support
MULTIFILE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Delta CFO Agent - Multi-File Upload</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 20px auto; padding: 20px; }
        .container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .upload-section { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        .results-section { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        .upload-area { border: 2px dashed #ccc; padding: 30px; text-align: center; margin: 20px 0; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        .status { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .warning { background: #fff3cd; color: #856404; }
        .invoice-details { background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .metric { display: inline-block; margin: 5px 10px; padding: 5px 10px; background: #f0f0f0; border-radius: 3px; }
        .batch-summary { background: #e6f3ff; padding: 15px; margin: 15px 0; border-radius: 8px; border: 1px solid #cce7ff; }
        .file-result { margin: 8px 0; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .file-success { background: #d4edda; }
        .file-error { background: #f8d7da; }
    </style>
</head>
<body>
    <h1>Delta CFO Agent - Multi-File Upload</h1>
    <p>Teste multi-arquivo: Upload → Claude Vision → Business Classification → Database</p>

    <div class="container">
        <div class="upload-section">
            <h2>Multi-File Upload & Processing</h2>

            {% if batch_results %}
                <div class="batch-summary">
                    <h3>Batch Processing Results</h3>
                    <div class="metric">Files Processed: {{ batch_results.total_files }}</div>
                    <div class="metric">Successful: {{ batch_results.successful_count }}</div>
                    <div class="metric">Errors: {{ batch_results.error_count }}</div>
                    {% if batch_results.archive_extracted %}
                        <div class="metric">Archive Files: {{ batch_results.archive_files }}</div>
                    {% endif %}
                </div>

                {% for result in batch_results.file_results %}
                <div class="file-result {{ 'file-success' if result.status == 'success' else 'file-error' }}">
                    <strong>{{ result.filename }}</strong>
                    {% if result.status == 'success' %}
                        - {{ result.vendor_name }} - ${{ result.total_amount }} ({{ result.confidence_score * 100 }}%)
                    {% else %}
                        - Error: {{ result.error }}
                    {% endif %}
                </div>
                {% endfor %}
            {% endif %}

            <form method="POST" enctype="multipart/form-data">
                <div class="upload-area">
                    <h3>Selecione múltiplos arquivos ou ZIP para processar</h3>
                    <input type="file" name="files" multiple accept=".txt,.pdf,.png,.jpg,.jpeg,.csv,.zip" required>
                    <br><br>
                    <small>Formatos: TXT, PDF, PNG, JPG, CSV, ZIP (com arquivos compatíveis)</small>
                </div>
                <button type="submit" class="btn">Processar Arquivos com Claude Vision</button>
            </form>

            <h3>Sistema Status</h3>
            <div class="metric">Database: ✅ Conectado</div>
            <div class="metric">Claude API: ✅ Configurado</div>
            <div class="metric">Total Processed: {{ total_invoices }}</div>
        </div>

        <div class="results-section">
            <h2>Invoices Processadas ({{ total_invoices }})</h2>

            {% for invoice in recent_invoices %}
                <div style="border: 1px solid #ddd; padding: 8px; margin: 5px 0; font-size: 14px;">
                    <strong>{{ invoice[2] }}</strong> - ${{ invoice[5] }} - {{ invoice[7] }}
                    <br><small>{{ invoice[1] }} | Confidence: {{ (invoice[9] * 100) | round }}% | {{ invoice[11] }}</small>
                </div>
            {% endfor %}
        </div>
    </div>

</body>
</html>
'''

def extract_archive_files(archive_file, temp_dir):
    """Extract files from ZIP archive"""
    extracted_files = []

    try:
        archive_path = temp_dir / archive_file.filename
        archive_file.save(str(archive_path))

        if archive_file.filename.lower().endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                for file_info in zip_ref.filelist:
                    if not file_info.is_dir():
                        extracted_path = temp_dir / file_info.filename
                        if extracted_path.suffix.lower() in ['.txt', '.csv', '.pdf', '.png', '.jpg', '.jpeg']:
                            extracted_files.append(extracted_path)

        # Clean up archive file
        archive_path.unlink(missing_ok=True)

    except Exception as e:
        print(f"Archive extraction error: {e}")

    return extracted_files

def process_batch_files(files_list):
    """Process multiple files and return results"""
    batch_results = {
        'total_files': 0,
        'successful_count': 0,
        'error_count': 0,
        'archive_extracted': False,
        'archive_files': 0,
        'file_results': []
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        all_files_to_process = []

        # Process uploaded files
        for file in files_list:
            if not file.filename:
                continue

            if file.filename.lower().endswith('.zip'):
                # Extract archive
                extracted_files = extract_archive_files(file, temp_path)
                all_files_to_process.extend(extracted_files)
                batch_results['archive_extracted'] = True
                batch_results['archive_files'] += len(extracted_files)
            else:
                # Save regular file
                file_path = temp_path / file.filename
                file.save(str(file_path))
                all_files_to_process.append(file_path)

        batch_results['total_files'] = len(all_files_to_process)

        # Process each file
        for file_path in all_files_to_process:
            try:
                print(f"Processing: {file_path.name}")

                # Extract with Claude Vision
                extracted_data = claude_service.extract_invoice_data(file_path)

                if extracted_data.get('status') == 'error':
                    batch_results['file_results'].append({
                        'filename': file_path.name,
                        'status': 'error',
                        'error': extracted_data.get('error', 'Unknown error')
                    })
                    batch_results['error_count'] += 1
                else:
                    # Enhance with business intelligence
                    enhanced_data = enhance_with_business_intelligence(extracted_data)

                    # Save to database
                    invoice_id = save_invoice_to_db(enhanced_data)

                    batch_results['file_results'].append({
                        'filename': file_path.name,
                        'status': 'success',
                        'invoice_id': invoice_id,
                        'vendor_name': enhanced_data.get('vendor_name', 'N/A'),
                        'total_amount': enhanced_data.get('total_amount', 0),
                        'confidence_score': enhanced_data.get('confidence_score', 0)
                    })
                    batch_results['successful_count'] += 1

            except Exception as e:
                batch_results['file_results'].append({
                    'filename': file_path.name,
                    'status': 'error',
                    'error': str(e)
                })
                batch_results['error_count'] += 1

    return batch_results

@app.route('/', methods=['GET', 'POST'])
def multi_file_upload_form():
    """Multi-file upload form"""
    batch_results = None

    if request.method == 'POST':
        files_list = request.files.getlist('files')
        valid_files = [f for f in files_list if f.filename]

        if valid_files:
            try:
                batch_results = process_batch_files(valid_files)
            except Exception as e:
                print(f"Batch processing error: {e}")
                batch_results = {
                    'total_files': len(valid_files),
                    'successful_count': 0,
                    'error_count': len(valid_files),
                    'archive_extracted': False,
                    'archive_files': 0,
                    'file_results': [{'filename': f.filename, 'status': 'error', 'error': str(e)} for f in valid_files]
                }

    # Get recent invoices and stats
    conn = sqlite3.connect(DB_PATH)
    recent_invoices = conn.execute("SELECT * FROM invoices ORDER BY created_at DESC LIMIT 10").fetchall()
    total_count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    conn.close()

    return render_template_string(MULTIFILE_TEMPLATE,
                                 batch_results=batch_results,
                                 recent_invoices=recent_invoices,
                                 total_invoices=total_count)

def enhance_with_business_intelligence(extracted_data):
    """Enhance extracted data with Delta business intelligence"""
    # Simple business unit classification
    vendor_name = extracted_data.get('vendor_name', '').lower()

    # Override business unit based on vendor analysis
    if any(tech in vendor_name for tech in ['aws', 'amazon', 'google', 'microsoft']):
        extracted_data['business_unit'] = 'Delta LLC'
        extracted_data['category'] = 'Technology Expenses'
    elif 'coinbase' in vendor_name or 'crypto' in vendor_name:
        extracted_data['business_unit'] = 'Delta Prop Shop LLC'
        extracted_data['category'] = 'Trading Expenses'

    # Add currency type detection
    extracted_data['currency_type'] = 'cryptocurrency' if 'crypto' in vendor_name else 'fiat'

    # Add enhanced confidence
    base_confidence = extracted_data.get('confidence', 0.8)
    bu_bonus = 0.1 if extracted_data['business_unit'] != 'Delta LLC' else 0
    extracted_data['confidence_score'] = min(base_confidence + bu_bonus, 1.0)

    # Add timestamps
    extracted_data['created_at'] = datetime.now().isoformat()
    extracted_data['id'] = str(uuid.uuid4())[:8]

    return extracted_data

def save_invoice_to_db(invoice_data):
    """Save invoice to database"""
    conn = sqlite3.connect(DB_PATH)

    conn.execute('''
        INSERT INTO invoices (
            id, invoice_number, date, vendor_name, total_amount, currency,
            business_unit, category, confidence_score, processing_notes,
            source_file, processed_at, created_at, extraction_method
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        invoice_data['id'],
        invoice_data.get('invoice_number'),
        invoice_data.get('date'),
        invoice_data.get('vendor_name'),
        invoice_data.get('total_amount'),
        invoice_data.get('currency'),
        invoice_data.get('business_unit'),
        invoice_data.get('category'),
        invoice_data.get('confidence_score'),
        invoice_data.get('processing_notes'),
        invoice_data.get('source_file'),
        invoice_data.get('processed_at'),
        invoice_data.get('created_at'),
        invoice_data.get('extraction_method')
    ))

    conn.commit()
    conn.close()

    return invoice_data['id']

@app.route('/api/stats')
def api_stats():
    """API endpoint for processing statistics"""
    conn = sqlite3.connect(DB_PATH)

    stats = {
        'total_invoices': conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0],
        'avg_confidence': conn.execute("SELECT AVG(confidence_score) FROM invoices").fetchone()[0] or 0,
        'business_units': {}
    }

    # Business unit breakdown
    bu_data = conn.execute("SELECT business_unit, COUNT(*), SUM(total_amount) FROM invoices GROUP BY business_unit").fetchall()
    for bu, count, total in bu_data:
        stats['business_units'][bu] = {'count': count, 'total_amount': total}

    conn.close()
    return jsonify(stats)

if __name__ == '__main__':
    init_db()
    print("Multi-File Upload System starting...")
    print("   Features: Multi-file + ZIP extraction + Claude Vision + Business Intelligence")
    print("   Access: http://localhost:5005")
    print("   API Stats: http://localhost:5005/api/stats")

    app.run(host='0.0.0.0', port=5005, debug=True, use_reloader=False)