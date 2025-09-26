#!/usr/bin/env python3
"""
Advanced Multi-Upload System
Sistema avançado de upload múltiplo com suporte a diversos tipos de arquivo
"""

import os
import sys
import sqlite3
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, send_from_directory
from datetime import datetime
import uuid
import json
import anthropic
import base64
import pandas as pd
import zipfile
import tempfile
import shutil

# Configuração
CLAUDE_API_KEY = os.getenv('ANTHROPIC_API_KEY') or input("Cole sua API key da Anthropic: ")

app = Flask(__name__)
app.secret_key = 'advanced_upload_secret'

# Database setup
DB_PATH = Path(__file__).parent / "advanced_invoices.db"
UPLOAD_DIR = Path(__file__).parent / "uploaded_files"
UPLOAD_DIR.mkdir(exist_ok=True)

def init_db():
    """Initialize advanced database with file storage"""
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
            file_path TEXT,
            file_type TEXT,
            file_size INTEGER,
            processed_at TEXT,
            created_at TEXT,
            extraction_method TEXT,
            raw_claude_response TEXT
        )
    ''')

    # Batch processing table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS batch_uploads (
            id TEXT PRIMARY KEY,
            total_files INTEGER,
            processed_files INTEGER,
            failed_files INTEGER,
            status TEXT,
            created_at TEXT,
            completed_at TEXT
        )
    ''')

    conn.commit()
    conn.close()

class AdvancedFileProcessor:
    """Advanced file processor supporting multiple formats"""

    def __init__(self, api_key):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.supported_types = {
            # Documents
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            # Images
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            # Spreadsheets
            '.csv': 'text/csv',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            # Other formats
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.rtf': 'application/rtf',
            # Archives
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed'
        }

        # File types that can be processed directly
        self.processable_types = {'.pdf', '.txt', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.csv', '.xls', '.xlsx', '.docx', '.rtf'}
        # Archive types that need extraction
        self.archive_types = {'.zip', '.rar'}

    def is_supported_file(self, filename):
        """Check if file type is supported"""
        ext = Path(filename).suffix.lower()
        return ext in self.supported_types

    def extract_invoice_data(self, file_path):
        """Extract data from various file formats"""
        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext in self.archive_types:
                return self._process_archive(file_path)
            elif file_ext == '.pdf':
                return self._process_pdf(file_path)
            elif file_ext == '.csv':
                return self._process_csv(file_path)
            elif file_ext in ['.xls', '.xlsx']:
                return self._process_excel(file_path)
            elif file_ext == '.txt':
                return self._process_text(file_path)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
                return self._process_image(file_path)
            else:
                return {'status': 'error', 'error': f'Unsupported file type: {file_ext}'}

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _process_archive(self, archive_path):
        """Process archive files (ZIP/RAR) and extract contents"""
        try:
            results = []
            extracted_files = []

            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract archive
                if archive_path.lower().endswith('.zip'):
                    extracted_files = self._extract_zip(archive_path, temp_path)
                elif archive_path.lower().endswith('.rar'):
                    extracted_files = self._extract_rar(archive_path, temp_path)

                if not extracted_files:
                    return {'status': 'error', 'error': 'No supported files found in archive'}

                # Process each extracted file
                for file_path in extracted_files:
                    try:
                        file_result = self._process_single_file(file_path)
                        if file_result.get('status') == 'success':
                            file_result['archive_source'] = os.path.basename(archive_path)
                            file_result['original_filename'] = file_path.name
                            results.append(file_result)
                    except Exception as e:
                        print(f"Error processing {file_path.name}: {e}")
                        continue

            if not results:
                return {'status': 'error', 'error': 'No files could be processed from archive'}

            # Return combined results
            return {
                'status': 'success',
                'archive_processed': True,
                'total_files': len(results),
                'results': results,
                'source_file': os.path.basename(archive_path)
            }

        except Exception as e:
            return {'status': 'error', 'error': f'Archive processing failed: {str(e)}'}

    def _extract_zip(self, zip_path, extract_dir):
        """Extract ZIP file and return list of processable files"""
        extracted_files = []
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

                for file_info in zip_ref.filelist:
                    if not file_info.is_dir():
                        file_path = extract_dir / file_info.filename
                        if file_path.exists() and file_path.suffix.lower() in self.processable_types:
                            extracted_files.append(file_path)

        except Exception as e:
            print(f"ZIP extraction error: {e}")

        return extracted_files

    def _extract_rar(self, rar_path, extract_dir):
        """Extract RAR file and return list of processable files"""
        extracted_files = []
        try:
            # Try to use rarfile if available
            import rarfile
            with rarfile.RarFile(rar_path, 'r') as rar_ref:
                rar_ref.extractall(extract_dir)

                for file_info in rar_ref.infolist():
                    if not file_info.is_dir():
                        file_path = extract_dir / file_info.filename
                        if file_path.exists() and file_path.suffix.lower() in self.processable_types:
                            extracted_files.append(file_path)

        except ImportError:
            return []  # RAR support not available
        except Exception as e:
            print(f"RAR extraction error: {e}")

        return extracted_files

    def _process_single_file(self, file_path):
        """Process a single file (used internally for archive contents)"""
        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.pdf':
            return self._process_pdf(file_path)
        elif file_ext == '.csv':
            return self._process_csv(file_path)
        elif file_ext in ['.xls', '.xlsx']:
            return self._process_excel(file_path)
        elif file_ext == '.txt':
            return self._process_text(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
            return self._process_image(file_path)
        else:
            return {'status': 'error', 'error': f'Unsupported file type: {file_ext}'}

    def _process_pdf(self, file_path):
        """Process PDF files"""
        try:
            import fitz
            doc = fitz.open(file_path)
            if doc.page_count == 0:
                raise ValueError("PDF has no pages")

            # Convert first page to image
            page = doc.load_page(0)
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            image_bytes = pix.pil_tobytes(format="PNG")
            doc.close()

            # Also extract text for hybrid processing
            doc = fitz.open(file_path)
            text_content = ""
            for page in doc:
                text_content += page.get_text()
            doc.close()

            # Use Claude Vision with both image and text
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            return self._call_claude_vision(image_base64, file_path, text_content)

        except Exception as e:
            return {'status': 'error', 'error': f'PDF processing failed: {e}'}

    def _process_csv(self, file_path):
        """Process CSV files"""
        try:
            df = pd.read_csv(file_path)

            # Convert DataFrame to readable text for Claude
            csv_content = f"CSV Data from {os.path.basename(file_path)}:\n\n"
            csv_content += f"Columns: {', '.join(df.columns.tolist())}\n\n"
            csv_content += df.to_string(max_rows=20)  # Limit to first 20 rows

            return self._call_claude_text_analysis(csv_content, file_path)

        except Exception as e:
            return {'status': 'error', 'error': f'CSV processing failed: {e}'}

    def _process_excel(self, file_path):
        """Process Excel files"""
        try:
            # Try to read Excel file
            df = pd.read_excel(file_path, sheet_name=0)  # Read first sheet

            excel_content = f"Excel Data from {os.path.basename(file_path)}:\n\n"
            excel_content += f"Columns: {', '.join(df.columns.tolist())}\n\n"
            excel_content += df.to_string(max_rows=20)

            return self._call_claude_text_analysis(excel_content, file_path)

        except Exception as e:
            return {'status': 'error', 'error': f'Excel processing failed: {e}'}

    def _process_text(self, file_path):
        """Process text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self._call_claude_text_analysis(content, file_path)
        except Exception as e:
            return {'status': 'error', 'error': f'Text processing failed: {e}'}

    def _process_image(self, file_path):
        """Process image files"""
        try:
            with open(file_path, 'rb') as f:
                image_bytes = f.read()

            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            return self._call_claude_vision(image_base64, file_path)

        except Exception as e:
            return {'status': 'error', 'error': f'Image processing failed: {e}'}

    def _call_claude_vision(self, image_base64, file_path, text_content=None):
        """Call Claude Vision API"""
        try:
            prompt = f"""
Analyze this financial document and extract invoice information in JSON format.

File: {os.path.basename(file_path)}
{f"Text content available: {text_content[:500]}..." if text_content else ""}

Extract these fields with high accuracy:

REQUIRED FIELDS:
- invoice_number: The invoice/bill number
- date: Invoice date (YYYY-MM-DD format)
- vendor_name: Company/vendor name
- total_amount: Total amount (numeric only)
- currency: Currency (USD, BRL, etc.)

CLASSIFICATION:
- business_unit: ["Delta LLC", "Delta Prop Shop LLC", "Delta Mining Paraguay S.A.", "Delta Brazil", "Personal"]
- category: ["Technology Expenses", "Trading Expenses", "Utilities", "Professional Services", "Other"]

Return ONLY JSON:
{{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "vendor_name": "string",
    "total_amount": 1234.56,
    "currency": "USD",
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Analysis details"
}}
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
                    ] if image_base64 else [{"type": "text", "text": prompt}]
                }]
            )

            response_text = response.content[0].text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)
            return self._format_response(extracted_data, file_path)

        except Exception as e:
            return {'status': 'error', 'error': f'Claude Vision API error: {e}'}

    def _call_claude_text_analysis(self, content, file_path):
        """Call Claude for text analysis"""
        try:
            prompt = f"""
Analyze this financial data and extract invoice information in JSON format:

{content[:2000]}...

Extract invoice fields if this appears to be financial/invoice data. If not clearly an invoice, classify as best as possible.

Return ONLY JSON:
{{
    "invoice_number": "string or null",
    "date": "YYYY-MM-DD or null",
    "vendor_name": "string",
    "total_amount": 1234.56,
    "currency": "USD",
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Analysis details"
}}
"""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)
            return self._format_response(extracted_data, file_path)

        except Exception as e:
            return {'status': 'error', 'error': f'Claude text analysis error: {e}'}

    def _format_response(self, extracted_data, file_path):
        """Format and validate response"""
        extracted_data.update({
            'source_file': os.path.basename(file_path),
            'extraction_method': 'claude_advanced',
            'processed_at': datetime.now().isoformat(),
            'status': 'success'
        })
        return extracted_data

# Initialize processor
processor = AdvancedFileProcessor(CLAUDE_API_KEY)

# Enhanced HTML Template
ADVANCED_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Delta CFO Agent - Advanced Upload System</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1400px; margin: 20px auto; padding: 20px; background: #f8f9fa; }
        .container { display: grid; grid-template-columns: 2fr 1fr; gap: 30px; }
        .upload-section, .results-section { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .multi-upload-area { border: 3px dashed #007bff; padding: 40px; text-align: center; border-radius: 12px; margin: 20px 0; transition: all 0.3s; }
        .multi-upload-area:hover { border-color: #0056b3; background: #f8f9ff; }
        .multi-upload-area.drag-over { border-color: #28a745; background: #f8fff8; }
        .btn { background: linear-gradient(135deg, #007bff, #0056b3); color: white; padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.3s; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,123,255,0.3); }
        .file-list { margin: 20px 0; }
        .file-item { background: #f8f9fa; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 4px solid #007bff; }
        .processing { background: #fff3cd; border-left-color: #ffc107; }
        .success { background: #d4edda; border-left-color: #28a745; }
        .error { background: #f8d7da; border-left-color: #dc3545; }
        .supported-types { background: #e7f3ff; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .invoice-card { background: #f8f9fa; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #28a745; }
        .progress-bar { width: 100%; height: 8px; background: #e9ecef; border-radius: 4px; margin: 10px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #007bff, #28a745); transition: width 0.3s; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat { background: white; padding: 15px; text-align: center; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 24px; font-weight: bold; color: #007bff; }
        .stat-label { font-size: 12px; color: #6c757d; margin-top: 5px; }
    </style>
</head>
<body>
    <h1>Delta CFO Agent - Advanced Upload System</h1>
    <p>Sistema avançado de upload múltiplo com suporte a diversos tipos de arquivo</p>

    <div class="container">
        <div class="upload-section">
            <h2>Multi-File Upload</h2>

            {% if batch_status %}
                <div class="file-item {{ batch_status.type }}">
                    {{ batch_status.message }}
                    {% if batch_status.progress %}
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {{ batch_status.progress }}%"></div>
                        </div>
                        <small>{{ batch_status.progress }}% completo</small>
                    {% endif %}
                </div>
            {% endif %}

            <form method="POST" enctype="multipart/form-data" id="uploadForm">
                <div class="multi-upload-area" id="dropArea">
                    <h3>📁 Arraste arquivos aqui ou clique para selecionar</h3>
                    <input type="file" name="files" id="fileInput" multiple
                           accept=".pdf,.txt,.png,.jpg,.jpeg,.csv,.xls,.xlsx,.gif,.bmp,.tiff,.docx,.rtf,.zip,.rar" style="display: none;">
                    <p>Suporte a múltiplos arquivos simultâneos</p>
                </div>

                <div class="file-list" id="fileList"></div>

                <button type="submit" class="btn" id="uploadBtn" disabled>
                    🚀 Processar Arquivos Selecionados
                </button>
            </form>

            <div class="supported-types">
                <h4>📋 Tipos de Arquivo Suportados:</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                    <div><strong>Documentos:</strong> PDF, TXT, DOCX, RTF</div>
                    <div><strong>Planilhas:</strong> CSV, XLS, XLSX</div>
                    <div><strong>Imagens:</strong> PNG, JPG, GIF, BMP, TIFF</div>
                    <div><strong>📦 Arquivos Comprimidos:</strong> ZIP, RAR</div>
                </div>
                <p style="font-size: 12px; color: #666; margin-top: 10px;">
                    💡 <strong>Novo:</strong> Arquivos ZIP/RAR são automaticamente extraídos e todos os arquivos compatíveis dentro deles são processados!
                </p>
            </div>

            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{{ total_processed }}</div>
                    <div class="stat-label">Total Processado</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ success_rate }}%</div>
                    <div class="stat-label">Taxa de Sucesso</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ supported_types_count }}</div>
                    <div class="stat-label">Tipos Suportados</div>
                </div>
            </div>
        </div>

        <div class="results-section">
            <h2>Resultados Recentes</h2>

            {% for invoice in recent_invoices %}
                <div class="invoice-card">
                    <h4>{{ invoice[2] }}</h4>
                    <p><strong>Valor:</strong> ${{ invoice[5] }} {{ invoice[6] }}</p>
                    <p><strong>Business Unit:</strong> {{ invoice[7] }}</p>
                    <p><strong>Arquivo:</strong> {{ invoice[10] }}</p>
                    <p><strong>Confiança:</strong> {{ (invoice[9] * 100) | round }}%</p>
                    <small>Processado em {{ invoice[15] }}</small>
                    <div style="margin-top: 10px;">
                        <a href="/invoice/{{ invoice[0] }}" class="btn" style="display: inline-block; padding: 6px 12px; font-size: 12px;">
                            Ver Detalhes
                        </a>
                        <a href="/file/{{ invoice[0] }}" class="btn" style="display: inline-block; padding: 6px 12px; font-size: 12px; margin-left: 5px;">
                            Ver Arquivo
                        </a>
                    </div>
                </div>
            {% endfor %}
        </div>
    </div>

    <script>
        const dropArea = document.getElementById('dropArea');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const uploadBtn = document.getElementById('uploadBtn');
        let selectedFiles = [];

        // Drag and drop functionality
        dropArea.addEventListener('click', () => fileInput.click());

        dropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropArea.classList.add('drag-over');
        });

        dropArea.addEventListener('dragleave', () => {
            dropArea.classList.remove('drag-over');
        });

        dropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            dropArea.classList.remove('drag-over');
            handleFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });

        function handleFiles(files) {
            selectedFiles = Array.from(files);
            displayFileList();
            uploadBtn.disabled = selectedFiles.length === 0;
        }

        function displayFileList() {
            fileList.innerHTML = '';
            selectedFiles.forEach((file, index) => {
                const div = document.createElement('div');
                div.className = 'file-item';
                div.innerHTML = `
                    <strong>${file.name}</strong>
                    <span style="color: #6c757d;">(${(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                    <button type="button" onclick="removeFile(${index})" style="float: right; background: #dc3545; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">×</button>
                `;
                fileList.appendChild(div);
            });
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            displayFileList();
            uploadBtn.disabled = selectedFiles.length === 0;

            // Update file input
            const dt = new DataTransfer();
            selectedFiles.forEach(file => dt.items.add(file));
            fileInput.files = dt.files;
        }
    </script>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def upload_form():
    """Advanced multi-file upload form"""
    batch_status = None

    if request.method == 'POST':
        files = request.files.getlist('files')
        if not files or not files[0].filename:
            batch_status = {'type': 'error', 'message': 'Nenhum arquivo selecionado'}
        else:
            # Process multiple files
            batch_id = str(uuid.uuid4())[:8]
            batch_status = process_batch_files(files, batch_id)

    # Get stats and recent invoices
    conn = sqlite3.connect(DB_PATH)
    recent_invoices = conn.execute("SELECT * FROM invoices ORDER BY created_at DESC LIMIT 5").fetchall()
    total_count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    success_count = conn.execute("SELECT COUNT(*) FROM invoices WHERE confidence_score > 0.5").fetchone()[0]
    success_rate = int((success_count / total_count * 100)) if total_count > 0 else 0
    conn.close()

    return render_template_string(ADVANCED_TEMPLATE,
                                 batch_status=batch_status,
                                 recent_invoices=recent_invoices,
                                 total_processed=total_count,
                                 success_rate=success_rate,
                                 supported_types_count=len(processor.supported_types))

def process_batch_files(files, batch_id):
    """Process multiple files in batch"""
    try:
        valid_files = [f for f in files if f.filename and processor.is_supported_file(f.filename)]
        if not valid_files:
            return {'type': 'error', 'message': 'Nenhum arquivo com formato suportado'}

        processed = 0
        failed = 0
        results = []

        for file in valid_files:
            try:
                # Save file
                file_id = str(uuid.uuid4())[:8]
                filename = f"{file_id}_{file.filename}"
                file_path = UPLOAD_DIR / filename
                file.save(str(file_path))

                # Process file
                extracted_data = processor.extract_invoice_data(str(file_path))

                if extracted_data.get('status') == 'error':
                    failed += 1
                    print(f"Failed to process {file.filename}: {extracted_data['error']}")
                elif extracted_data.get('archive_processed'):
                    # Handle archive files with multiple results
                    archive_results = extracted_data.get('results', [])
                    for archive_result in archive_results:
                        try:
                            invoice_id = save_advanced_invoice(archive_result, str(file_path), file)
                            processed += 1
                            results.append(invoice_id)
                        except Exception as e:
                            failed += 1
                            print(f"Failed to save archive file result: {e}")
                else:
                    # Save to database (single file)
                    invoice_id = save_advanced_invoice(extracted_data, str(file_path), file)
                    processed += 1
                    results.append(invoice_id)

            except Exception as e:
                failed += 1
                print(f"Error processing {file.filename}: {e}")

        # Create success message
        message = f"Processados {processed} arquivos com sucesso"
        if failed > 0:
            message += f", {failed} falharam"

        return {
            'type': 'success' if processed > 0 else 'error',
            'message': message,
            'progress': int((processed / len(valid_files)) * 100),
            'processed': processed,
            'failed': failed
        }

    except Exception as e:
        return {'type': 'error', 'message': f'Erro no processamento em lote: {str(e)}'}

def save_advanced_invoice(extracted_data, file_path, original_file):
    """Save invoice with file information"""
    conn = sqlite3.connect(DB_PATH)

    invoice_id = str(uuid.uuid4())[:8]
    file_stats = Path(file_path).stat()

    conn.execute('''
        INSERT INTO invoices (
            id, invoice_number, date, vendor_name, total_amount, currency,
            business_unit, category, confidence_score, processing_notes,
            source_file, file_path, file_type, file_size, processed_at,
            created_at, extraction_method
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        invoice_id,
        extracted_data.get('invoice_number'),
        extracted_data.get('date'),
        extracted_data.get('vendor_name'),
        extracted_data.get('total_amount'),
        extracted_data.get('currency'),
        extracted_data.get('business_unit'),
        extracted_data.get('category'),
        extracted_data.get('confidence'),
        extracted_data.get('processing_notes'),
        original_file.filename,
        str(file_path),
        original_file.content_type,
        file_stats.st_size,
        extracted_data.get('processed_at'),
        datetime.now().isoformat(),
        extracted_data.get('extraction_method')
    ))

    conn.commit()
    conn.close()
    return invoice_id

@app.route('/invoice/<invoice_id>')
def invoice_details(invoice_id):
    """Detailed view of specific invoice"""
    conn = sqlite3.connect(DB_PATH)
    invoice = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()

    if not invoice:
        return "Invoice not found", 404

    # Convert to dict for easier template usage
    invoice_dict = {
        'id': invoice[0], 'invoice_number': invoice[1], 'date': invoice[2],
        'vendor_name': invoice[3], 'total_amount': invoice[5], 'currency': invoice[6],
        'business_unit': invoice[7], 'category': invoice[8], 'confidence_score': invoice[9],
        'processing_notes': invoice[10], 'source_file': invoice[11], 'file_path': invoice[12],
        'file_type': invoice[13], 'file_size': invoice[14], 'processed_at': invoice[15]
    }

    detail_template = '''
    <!DOCTYPE html>
    <html><head><title>Invoice Details - {{ invoice.id }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px; }
        .detail-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .field { margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 6px; }
        .label { font-weight: bold; color: #495057; }
        .value { margin-top: 5px; }
        .btn { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 5px; }
    </style></head>
    <body>
        <div class="detail-card">
            <h1>Invoice Details</h1>
            <div class="field"><div class="label">Invoice ID:</div><div class="value">{{ invoice.id }}</div></div>
            <div class="field"><div class="label">Invoice Number:</div><div class="value">{{ invoice.invoice_number or 'N/A' }}</div></div>
            <div class="field"><div class="label">Date:</div><div class="value">{{ invoice.date or 'N/A' }}</div></div>
            <div class="field"><div class="label">Vendor:</div><div class="value">{{ invoice.vendor_name or 'N/A' }}</div></div>
            <div class="field"><div class="label">Amount:</div><div class="value">${{ invoice.total_amount }} {{ invoice.currency }}</div></div>
            <div class="field"><div class="label">Business Unit:</div><div class="value">{{ invoice.business_unit or 'N/A' }}</div></div>
            <div class="field"><div class="label">Category:</div><div class="value">{{ invoice.category or 'N/A' }}</div></div>
            <div class="field"><div class="label">Confidence Score:</div><div class="value">{{ (invoice.confidence_score * 100) | round }}%</div></div>
            <div class="field"><div class="label">Processing Notes:</div><div class="value">{{ invoice.processing_notes or 'N/A' }}</div></div>
            <div class="field"><div class="label">Source File:</div><div class="value">{{ invoice.source_file }}</div></div>
            <div class="field"><div class="label">File Size:</div><div class="value">{{ (invoice.file_size / 1024 / 1024) | round(2) }} MB</div></div>
            <div class="field"><div class="label">Processed At:</div><div class="value">{{ invoice.processed_at }}</div></div>

            <div style="margin-top: 30px;">
                <a href="/file/{{ invoice.id }}" class="btn">Ver Arquivo Original</a>
                <a href="/" class="btn">Voltar</a>
            </div>
        </div>
    </body></html>
    '''
    return render_template_string(detail_template, invoice=invoice_dict)

@app.route('/file/<invoice_id>')
def serve_file(invoice_id):
    """Serve original uploaded file"""
    conn = sqlite3.connect(DB_PATH)
    invoice = conn.execute("SELECT file_path, source_file FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()

    if not invoice or not os.path.exists(invoice[0]):
        return "File not found", 404

    return send_from_directory(
        os.path.dirname(invoice[0]),
        os.path.basename(invoice[0]),
        as_attachment=True,
        download_name=invoice[1]
    )

@app.route('/api/stats')
def api_stats():
    """API for statistics"""
    conn = sqlite3.connect(DB_PATH)

    stats = {
        'total_invoices': conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0],
        'avg_confidence': conn.execute("SELECT AVG(confidence_score) FROM invoices").fetchone()[0] or 0,
        'file_types': {}
    }

    # File type breakdown
    file_types = conn.execute("SELECT file_type, COUNT(*) FROM invoices GROUP BY file_type").fetchall()
    for file_type, count in file_types:
        stats['file_types'][file_type or 'unknown'] = count

    conn.close()
    return jsonify(stats)

if __name__ == '__main__':
    init_db()
    print("Advanced Upload System starting...")
    print("   Features: Multi-file upload, Multiple formats, File viewing")
    print("   Access: http://localhost:5005")
    print("   Supported: PDF, CSV, XLS, XLSX, Images, Text files")

    app.run(host='0.0.0.0', port=5005, debug=True, use_reloader=False)