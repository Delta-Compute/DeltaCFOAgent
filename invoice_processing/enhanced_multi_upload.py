#!/usr/bin/env python3
"""
Enhanced Multi-Upload System with Archive Support
Sistema aprimorado com suporte a arquivos comprimidos e melhor navegação
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
import rarfile
import tempfile
import shutil

# Configuração
CLAUDE_API_KEY = os.getenv('ANTHROPIC_API_KEY') or input("Cole sua API key da Anthropic: ")

app = Flask(__name__)
app.secret_key = 'enhanced_multi_upload_secret'

# Database setup
DB_PATH = Path(__file__).parent / "enhanced_invoices.db"
UPLOAD_DIR = Path(__file__).parent / "uploaded_files"
UPLOAD_DIR.mkdir(exist_ok=True)

def init_db():
    """Initialize enhanced database"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            batch_id TEXT,
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
            archive_source TEXT
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS batch_uploads (
            id TEXT PRIMARY KEY,
            total_files INTEGER,
            processed_files INTEGER,
            failed_files INTEGER,
            status TEXT,
            created_at TEXT,
            completed_at TEXT,
            archive_processed BOOLEAN DEFAULT FALSE
        )
    ''')

    conn.commit()
    conn.close()

class EnhancedFileProcessor:
    """Enhanced file processor with archive support"""

    def __init__(self, api_key):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.supported_types = {
            # Documents
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.rtf': 'application/rtf',
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
            # Archives
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed',
            '.7z': 'application/x-7z-compressed'
        }

    def is_supported_file(self, filename):
        """Check if file type is supported"""
        ext = Path(filename).suffix.lower()
        return ext in self.supported_types

    def is_archive_file(self, filename):
        """Check if file is an archive"""
        ext = Path(filename).suffix.lower()
        return ext in ['.zip', '.rar', '.7z']

    def extract_archive(self, archive_path, extract_dir):
        """Extract archive and return list of extracted files"""
        extracted_files = []
        ext = Path(archive_path).suffix.lower()

        try:
            if ext == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                    for file_info in zip_ref.filelist:
                        if not file_info.is_dir():
                            extracted_path = Path(extract_dir) / file_info.filename
                            if self.is_supported_file(file_info.filename):
                                extracted_files.append({
                                    'path': str(extracted_path),
                                    'original_name': file_info.filename,
                                    'size': file_info.file_size
                                })

            elif ext == '.rar':
                try:
                    with rarfile.RarFile(archive_path, 'r') as rar_ref:
                        rar_ref.extractall(extract_dir)
                        for file_info in rar_ref.infolist():
                            if not file_info.is_dir():
                                extracted_path = Path(extract_dir) / file_info.filename
                                if self.is_supported_file(file_info.filename):
                                    extracted_files.append({
                                        'path': str(extracted_path),
                                        'original_name': file_info.filename,
                                        'size': file_info.file_size
                                    })
                except Exception as e:
                    print(f"RAR extraction failed (may need unrar tool): {e}")

            return extracted_files

        except Exception as e:
            print(f"Archive extraction failed: {e}")
            return []

    def extract_invoice_data(self, file_path):
        """Extract data from various file formats"""
        try:
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

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _process_pdf(self, file_path):
        """Process PDF files with hybrid text+vision approach"""
        try:
            import fitz
            doc = fitz.open(file_path)
            if doc.page_count == 0:
                raise ValueError("PDF has no pages")

            # Extract text content
            text_content = ""
            for page in doc:
                text_content += page.get_text()

            # Convert first page to image
            page = doc.load_page(0)
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            image_bytes = pix.pil_tobytes(format="PNG")
            doc.close()

            # Use hybrid approach: text + vision
            if len(text_content.strip()) > 50:
                # Text is substantial, use text analysis
                return self._call_claude_text_analysis(text_content, file_path, use_vision=False)
            else:
                # Text is minimal, use vision
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                return self._call_claude_vision(image_base64, file_path)

        except Exception as e:
            return {'status': 'error', 'error': f'PDF processing failed: {e}'}

    def _process_csv(self, file_path):
        """Process CSV files"""
        try:
            df = pd.read_csv(file_path)
            csv_content = f"CSV Data from {os.path.basename(file_path)}:\n\n"
            csv_content += f"Columns: {', '.join(df.columns.tolist())}\n\n"
            csv_content += df.to_string(max_rows=50)
            return self._call_claude_text_analysis(csv_content, file_path)
        except Exception as e:
            return {'status': 'error', 'error': f'CSV processing failed: {e}'}

    def _process_excel(self, file_path):
        """Process Excel files"""
        try:
            df = pd.read_excel(file_path, sheet_name=0)
            excel_content = f"Excel Data from {os.path.basename(file_path)}:\n\n"
            excel_content += f"Columns: {', '.join(df.columns.tolist())}\n\n"
            excel_content += df.to_string(max_rows=50)
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

    def _call_claude_vision(self, image_base64, file_path):
        """Call Claude Vision API"""
        try:
            prompt = f"""
Analyze this financial document and extract invoice information in JSON format.

File: {os.path.basename(file_path)}

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
    "invoice_number": "string or null",
    "date": "YYYY-MM-DD or null",
    "vendor_name": "string",
    "total_amount": 1234.56,
    "currency": "USD",
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Detailed analysis"
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
                    ]
                }]
            )

            return self._process_claude_response(response, file_path, 'claude_vision')

        except Exception as e:
            return {'status': 'error', 'error': f'Claude Vision API error: {e}'}

    def _call_claude_text_analysis(self, content, file_path, use_vision=True):
        """Call Claude for text analysis"""
        try:
            prompt = f"""
Analyze this financial data and extract invoice information in JSON format:

{content[:3000]}...

Extract invoice fields if this appears to be financial/invoice data.

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
    "processing_notes": "Detailed analysis"
}}
"""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            return self._process_claude_response(response, file_path, 'claude_text_analysis')

        except Exception as e:
            return {'status': 'error', 'error': f'Claude text analysis error: {e}'}

    def _process_claude_response(self, response, file_path, method):
        """Process Claude response and format data"""
        try:
            response_text = response.content[0].text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)

            # Format and validate
            extracted_data.update({
                'source_file': os.path.basename(file_path),
                'extraction_method': method,
                'processed_at': datetime.now().isoformat(),
                'status': 'success'
            })

            return extracted_data

        except json.JSONDecodeError as e:
            return {'status': 'error', 'error': f'Invalid JSON response: {e}'}
        except Exception as e:
            return {'status': 'error', 'error': f'Response processing error: {e}'}

# Initialize processor
processor = EnhancedFileProcessor(CLAUDE_API_KEY)

# Enhanced HTML Template with better navigation
ENHANCED_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Delta CFO Agent - Enhanced Multi-Upload System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1600px; margin: 0 auto; padding: 20px; background: #f8f9fa; }
        .container { display: grid; grid-template-columns: 2fr 1fr; gap: 30px; }
        .upload-section, .results-section { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .multi-upload-area { border: 3px dashed #007bff; padding: 40px; text-align: center; border-radius: 12px; margin: 20px 0; transition: all 0.3s; }
        .multi-upload-area:hover { border-color: #0056b3; background: #f8f9ff; }
        .multi-upload-area.drag-over { border-color: #28a745; background: #f8fff8; }
        .btn { background: linear-gradient(135deg, #007bff, #0056b3); color: white; padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.3s; text-decoration: none; display: inline-block; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,123,255,0.3); }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        .file-list { margin: 20px 0; }
        .file-item { background: #f8f9fa; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 4px solid #007bff; display: flex; justify-content: space-between; align-items: center; }
        .success { background: #d4edda; border-left-color: #28a745; }
        .error { background: #f8d7da; border-left-color: #dc3545; }
        .supported-types { background: #e7f3ff; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .invoice-card { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #28a745; }
        .invoice-card h4 { margin: 0 0 10px 0; color: #495057; }
        .invoice-meta { font-size: 14px; color: #6c757d; margin: 5px 0; }
        .invoice-actions { margin-top: 10px; }
        .progress-bar { width: 100%; height: 8px; background: #e9ecef; border-radius: 4px; margin: 10px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #007bff, #28a745); transition: width 0.3s; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat { background: white; padding: 15px; text-align: center; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 24px; font-weight: bold; color: #007bff; }
        .stat-label { font-size: 12px; color: #6c757d; margin-top: 5px; }
        .pagination { display: flex; justify-content: center; align-items: center; margin: 20px 0; gap: 10px; }
        .search-bar { width: 100%; padding: 12px; border: 2px solid #e9ecef; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }
        .search-bar:focus { border-color: #007bff; outline: none; }
        .filters { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .filter-select { padding: 8px 12px; border: 1px solid #e9ecef; border-radius: 6px; background: white; }
        .archive-info { background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 6px; margin: 10px 0; }

        @media (max-width: 1200px) {
            .container { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <h1>🚀 Delta CFO Agent - Enhanced Multi-Upload System</h1>
    <p>Sistema avançado com suporte a arquivos comprimidos (ZIP, RAR) e navegação melhorada</p>

    <div class="container">
        <div class="upload-section">
            <h2>📁 Multi-File Upload</h2>

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
                    <h3>📦 Arraste arquivos ou comprimidos aqui</h3>
                    <input type="file" name="files" id="fileInput" multiple
                           accept=".pdf,.txt,.png,.jpg,.jpeg,.csv,.xls,.xlsx,.gif,.bmp,.tiff,.docx,.rtf,.zip,.rar,.7z" style="display: none;">
                    <p>Suporte a múltiplos arquivos + ZIP/RAR</p>
                </div>

                <div class="file-list" id="fileList"></div>

                <button type="submit" class="btn" id="uploadBtn" disabled>
                    🚀 Processar Arquivos Selecionados
                </button>
            </form>

            <div class="supported-types">
                <h4>📋 Tipos Suportados:</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                    <div><strong>Documentos:</strong> PDF, TXT, DOCX, RTF</div>
                    <div><strong>Planilhas:</strong> CSV, XLS, XLSX</div>
                    <div><strong>Imagens:</strong> PNG, JPG, GIF, BMP, TIFF</div>
                    <div><strong>Comprimidos:</strong> ZIP, RAR, 7Z</div>
                </div>
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
            <h2>📋 Resultados ({{ total_invoices }})</h2>

            <!-- Search and Filters -->
            <input type="text" class="search-bar" id="searchBar" placeholder="🔍 Buscar por vendor, valor, etc...">

            <div class="filters">
                <select class="filter-select" id="businessUnitFilter">
                    <option value="">Todas Business Units</option>
                    {% for bu in business_units %}
                        <option value="{{ bu }}">{{ bu }}</option>
                    {% endfor %}
                </select>

                <select class="filter-select" id="categoryFilter">
                    <option value="">Todas Categorias</option>
                    {% for cat in categories %}
                        <option value="{{ cat }}">{{ cat }}</option>
                    {% endfor %}
                </select>
            </div>

            <!-- Invoice List -->
            <div id="invoiceList">
                {% for invoice in invoices %}
                    <div class="invoice-card" data-vendor="{{ invoice[3]|lower }}" data-bu="{{ invoice[7] }}" data-category="{{ invoice[8] }}">
                        <h4>{{ invoice[3] or 'Vendor Desconhecido' }}</h4>
                        <div class="invoice-meta">
                            <strong>Valor:</strong> ${{ "{:.2f}".format(invoice[5] if invoice[5] is not None else 0) }} {{ invoice[6] or 'USD' }}
                        </div>
                        <div class="invoice-meta">
                            <strong>Business Unit:</strong> {{ invoice[7] or 'N/A' }}
                        </div>
                        <div class="invoice-meta">
                            <strong>Data:</strong> {{ invoice[2] or 'N/A' }} |
                            <strong>Confiança:</strong> {{ "{:.0f}".format((invoice[9] if invoice[9] is not None else 0) * 100) }}%
                        </div>
                        <div class="invoice-meta">
                            <strong>Arquivo:</strong> {{ invoice[11] }}
                            {% if invoice[18] %}
                                <span style="color: #28a745;">📦 (de arquivo comprimido)</span>
                            {% endif %}
                        </div>
                        <div class="invoice-actions">
                            <a href="/invoice/{{ invoice[0] }}" class="btn btn-sm">Ver Detalhes</a>
                            <a href="/file/{{ invoice[0] }}" class="btn btn-sm">Ver Arquivo</a>
                        </div>
                    </div>
                {% endfor %}
            </div>

            <!-- Pagination -->
            {% if total_pages > 1 %}
            <div class="pagination">
                {% if current_page > 1 %}
                    <a href="?page={{ current_page - 1 }}" class="btn btn-sm">◀ Anterior</a>
                {% endif %}

                <span>Página {{ current_page }} de {{ total_pages }}</span>

                {% if current_page < total_pages %}
                    <a href="?page={{ current_page + 1 }}" class="btn btn-sm">Próxima ▶</a>
                {% endif %}
            </div>
            {% endif %}
        </div>
    </div>

    <script>
        // File handling
        const dropArea = document.getElementById('dropArea');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const uploadBtn = document.getElementById('uploadBtn');
        let selectedFiles = [];

        // Drag and drop
        dropArea.addEventListener('click', () => fileInput.click());
        dropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropArea.classList.add('drag-over');
        });
        dropArea.addEventListener('dragleave', () => dropArea.classList.remove('drag-over'));
        dropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            dropArea.classList.remove('drag-over');
            handleFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

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
                const isArchive = ['.zip', '.rar', '.7z'].some(ext => file.name.toLowerCase().endsWith(ext));
                div.innerHTML = `
                    <div>
                        <strong>${file.name}</strong> ${isArchive ? '📦' : '📄'}
                        <span style="color: #6c757d;">(${(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                    </div>
                    <button type="button" onclick="removeFile(${index})" style="background: #dc3545; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">✕</button>
                `;
                fileList.appendChild(div);
            });
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            displayFileList();
            uploadBtn.disabled = selectedFiles.length === 0;

            const dt = new DataTransfer();
            selectedFiles.forEach(file => dt.items.add(file));
            fileInput.files = dt.files;
        }

        // Search and filtering
        const searchBar = document.getElementById('searchBar');
        const businessUnitFilter = document.getElementById('businessUnitFilter');
        const categoryFilter = document.getElementById('categoryFilter');

        function filterInvoices() {
            const searchTerm = searchBar.value.toLowerCase();
            const selectedBU = businessUnitFilter.value;
            const selectedCategory = categoryFilter.value;

            document.querySelectorAll('.invoice-card').forEach(card => {
                const vendor = card.getAttribute('data-vendor') || '';
                const bu = card.getAttribute('data-bu') || '';
                const category = card.getAttribute('data-category') || '';
                const cardText = card.textContent.toLowerCase();

                const matchesSearch = searchTerm === '' || cardText.includes(searchTerm);
                const matchesBU = selectedBU === '' || bu === selectedBU;
                const matchesCategory = selectedCategory === '' || category === selectedCategory;

                card.style.display = (matchesSearch && matchesBU && matchesCategory) ? 'block' : 'none';
            });
        }

        searchBar.addEventListener('input', filterInvoices);
        businessUnitFilter.addEventListener('change', filterInvoices);
        categoryFilter.addEventListener('change', filterInvoices);
    </script>
</body>
</html>
'''

@app.route('/')
def enhanced_upload_form():
    """Enhanced upload form with pagination and search"""
    batch_status = None

    if request.method == 'POST':
        files = request.files.getlist('files')
        if not files or all(not f.filename for f in files):
            batch_status = {'type': 'error', 'message': 'Nenhum arquivo selecionado'}
        else:
            batch_id = str(uuid.uuid4())[:8]
            batch_status = process_enhanced_batch_files(files, batch_id)

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    # Get invoices with pagination
    conn = sqlite3.connect(DB_PATH)
    total_invoices = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    total_pages = (total_invoices + per_page - 1) // per_page

    invoices = conn.execute(
        "SELECT * FROM invoices ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()

    # Get filter options
    business_units = [row[0] for row in conn.execute("SELECT DISTINCT business_unit FROM invoices WHERE business_unit IS NOT NULL").fetchall()]
    categories = [row[0] for row in conn.execute("SELECT DISTINCT category FROM invoices WHERE category IS NOT NULL").fetchall()]

    # Stats
    success_count = conn.execute("SELECT COUNT(*) FROM invoices WHERE confidence_score > 0.5").fetchone()[0]
    success_rate = int((success_count / total_invoices * 100)) if total_invoices > 0 else 0
    conn.close()

    return render_template_string(ENHANCED_TEMPLATE,
                                 batch_status=batch_status,
                                 invoices=invoices,
                                 total_invoices=total_invoices,
                                 current_page=page,
                                 total_pages=total_pages,
                                 business_units=business_units,
                                 categories=categories,
                                 total_processed=total_invoices,
                                 success_rate=success_rate,
                                 supported_types_count=len(processor.supported_types))

# Make the route accept both GET and POST
@app.route('/', methods=['GET', 'POST'])
def enhanced_upload_form_with_post():
    return enhanced_upload_form()

def process_enhanced_batch_files(files, batch_id):
    """Process multiple files including archives"""
    try:
        valid_files = [f for f in files if f.filename and processor.is_supported_file(f.filename)]
        if not valid_files:
            return {'type': 'error', 'message': 'Nenhum arquivo com formato suportado'}

        processed = 0
        failed = 0
        archive_files_extracted = 0

        for file in valid_files:
            try:
                # Save file
                file_id = str(uuid.uuid4())[:8]
                filename = f"{file_id}_{file.filename}"
                file_path = UPLOAD_DIR / filename
                file.save(str(file_path))

                # Check if it's an archive
                if processor.is_archive_file(file.filename):
                    # Extract archive and process contents
                    temp_extract_dir = tempfile.mkdtemp()
                    try:
                        extracted_files = processor.extract_archive(str(file_path), temp_extract_dir)
                        print(f"Extracted {len(extracted_files)} files from {file.filename}")

                        for extracted_file in extracted_files:
                            try:
                                # Process extracted file
                                extracted_data = processor.extract_invoice_data(extracted_file['path'])

                                if extracted_data.get('status') != 'error':
                                    # Save extracted file to permanent location
                                    perm_filename = f"{str(uuid.uuid4())[:8]}_{extracted_file['original_name']}"
                                    perm_path = UPLOAD_DIR / perm_filename
                                    shutil.copy2(extracted_file['path'], str(perm_path))

                                    # Save to database with archive reference
                                    save_enhanced_invoice(extracted_data, str(perm_path),
                                                        extracted_file['original_name'],
                                                        archive_source=file.filename)
                                    processed += 1
                                    archive_files_extracted += 1
                                else:
                                    failed += 1
                                    print(f"Failed to process extracted file {extracted_file['original_name']}: {extracted_data['error']}")

                            except Exception as e:
                                failed += 1
                                print(f"Error processing extracted file: {e}")

                        # Clean up temp directory
                        shutil.rmtree(temp_extract_dir)

                    except Exception as e:
                        print(f"Archive extraction failed: {e}")
                        failed += 1

                else:
                    # Regular file processing
                    extracted_data = processor.extract_invoice_data(str(file_path))

                    if extracted_data.get('status') != 'error':
                        save_enhanced_invoice(extracted_data, str(file_path), file.filename)
                        processed += 1
                    else:
                        failed += 1
                        print(f"Failed to process {file.filename}: {extracted_data['error']}")

            except Exception as e:
                failed += 1
                print(f"Error processing {file.filename}: {e}")

        # Create message
        message = f"✅ Processados {processed} arquivos com sucesso"
        if archive_files_extracted > 0:
            message += f" (incluindo {archive_files_extracted} de arquivos comprimidos)"
        if failed > 0:
            message += f", ❌ {failed} falharam"

        return {
            'type': 'success' if processed > 0 else 'error',
            'message': message,
            'progress': int((processed / (processed + failed)) * 100) if (processed + failed) > 0 else 0,
            'processed': processed,
            'failed': failed,
            'archive_extracted': archive_files_extracted
        }

    except Exception as e:
        return {'type': 'error', 'message': f'Erro no processamento: {str(e)}'}

def save_enhanced_invoice(extracted_data, file_path, original_filename, archive_source=None):
    """Save invoice with enhanced metadata"""
    conn = sqlite3.connect(DB_PATH)

    invoice_id = str(uuid.uuid4())[:8]
    file_stats = Path(file_path).stat()

    conn.execute('''
        INSERT INTO invoices (
            id, invoice_number, date, vendor_name, total_amount, currency,
            business_unit, category, confidence_score, processing_notes,
            source_file, file_path, file_type, file_size, processed_at,
            created_at, extraction_method, archive_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        original_filename,
        str(file_path),
        'archive_extracted' if archive_source else 'direct_upload',
        file_stats.st_size,
        extracted_data.get('processed_at'),
        datetime.now().isoformat(),
        extracted_data.get('extraction_method'),
        archive_source
    ))

    conn.commit()
    conn.close()
    return invoice_id

@app.route('/invoice/<invoice_id>')
def enhanced_invoice_details(invoice_id):
    """Enhanced invoice details view"""
    conn = sqlite3.connect(DB_PATH)
    invoice = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()

    if not invoice:
        return "Invoice not found", 404

    detail_template = '''
    <!DOCTYPE html>
    <html><head><title>Invoice Details - {{ invoice_id }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 900px; margin: 20px auto; padding: 20px; background: #f8f9fa; }
        .detail-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .field-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .field { padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #007bff; }
        .label { font-weight: bold; color: #495057; margin-bottom: 8px; }
        .value { color: #212529; line-height: 1.5; }
        .btn { background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block; margin: 5px; font-weight: 600; }
        .btn:hover { background: #0056b3; }
        .confidence-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .confidence-high { background: #d4edda; color: #155724; }
        .confidence-medium { background: #fff3cd; color: #856404; }
        .confidence-low { background: #f8d7da; color: #721c24; }
        .archive-info { background: #e7f3ff; border: 1px solid #bee5eb; padding: 15px; border-radius: 8px; margin: 20px 0; }
    </style></head>
    <body>
        <div class="detail-card">
            <div class="header">
                <h1>📄 Invoice Details</h1>
                <div>
                    {% set confidence = (invoice[9] * 100) | round %}
                    <span class="confidence-badge {{ 'confidence-high' if confidence >= 90 else 'confidence-medium' if confidence >= 70 else 'confidence-low' }}">
                        {{ confidence }}% Confidence
                    </span>
                </div>
            </div>

            {% if invoice[18] %}
            <div class="archive-info">
                <strong>📦 Arquivo Extraído:</strong> Este arquivo foi extraído do arquivo comprimido "{{ invoice[18] }}"
            </div>
            {% endif %}

            <div class="field-grid">
                <div class="field">
                    <div class="label">🆔 Invoice ID</div>
                    <div class="value">{{ invoice[0] }}</div>
                </div>
                <div class="field">
                    <div class="label">📝 Invoice Number</div>
                    <div class="value">{{ invoice[1] or 'N/A' }}</div>
                </div>
                <div class="field">
                    <div class="label">📅 Date</div>
                    <div class="value">{{ invoice[2] or 'N/A' }}</div>
                </div>
                <div class="field">
                    <div class="label">🏢 Vendor</div>
                    <div class="value">{{ invoice[3] or 'N/A' }}</div>
                </div>
                <div class="field">
                    <div class="label">💰 Amount</div>
                    <div class="value">${{ "{:.2f}".format(invoice[5] if invoice[5] is not None else 0) }} {{ invoice[6] or 'USD' }}</div>
                </div>
                <div class="field">
                    <div class="label">🏛️ Business Unit</div>
                    <div class="value">{{ invoice[7] or 'N/A' }}</div>
                </div>
                <div class="field">
                    <div class="label">📂 Category</div>
                    <div class="value">{{ invoice[8] or 'N/A' }}</div>
                </div>
                <div class="field">
                    <div class="label">📄 Source File</div>
                    <div class="value">{{ invoice[11] }}</div>
                </div>
                <div class="field">
                    <div class="label">💾 File Size</div>
                    <div class="value">{{ "{:.2f}".format(((invoice[14] | default(0, true)) | int) / 1024 / 1024) }} MB</div>
                </div>
                <div class="field">
                    <div class="label">⚡ Processing Method</div>
                    <div class="value">{{ invoice[16] or 'N/A' }}</div>
                </div>
                <div class="field">
                    <div class="label">🕐 Processed At</div>
                    <div class="value">{{ invoice[15] or 'N/A' }}</div>
                </div>
            </div>

            {% if invoice[10] %}
            <div class="field" style="margin-top: 20px;">
                <div class="label">📋 Processing Notes</div>
                <div class="value">{{ invoice[10] }}</div>
            </div>
            {% endif %}

            <div style="margin-top: 30px; text-align: center;">
                <a href="/file/{{ invoice[0] }}" class="btn">📥 Download Original File</a>
                <a href="/" class="btn">⬅️ Back to List</a>
            </div>
        </div>
    </body></html>
    '''
    return render_template_string(detail_template, invoice=invoice, invoice_id=invoice_id)

@app.route('/file/<invoice_id>')
def enhanced_serve_file(invoice_id):
    """Enhanced file serving"""
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
def enhanced_api_stats():
    """Enhanced API stats"""
    conn = sqlite3.connect(DB_PATH)

    stats = {
        'total_invoices': conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0],
        'avg_confidence': conn.execute("SELECT AVG(confidence_score) FROM invoices").fetchone()[0] or 0,
        'archive_extracted': conn.execute("SELECT COUNT(*) FROM invoices WHERE archive_source IS NOT NULL").fetchone()[0],
        'business_units': {},
        'categories': {},
        'file_types': {}
    }

    # Detailed breakdowns
    for table, field in [('business_unit', 'business_units'), ('category', 'categories'), ('file_type', 'file_types')]:
        data = conn.execute(f"SELECT {table}, COUNT(*), SUM(total_amount) FROM invoices WHERE {table} IS NOT NULL GROUP BY {table}").fetchall()
        for value, count, total_amount in data:
            stats[field][value] = {'count': count, 'total_amount': total_amount or 0}

    conn.close()
    return jsonify(stats)

if __name__ == '__main__':
    init_db()
    print("Enhanced Multi-Upload System starting...")
    print("   Features: Multi-file, Archives (ZIP/RAR), Search, Pagination")
    print("   Access: http://localhost:5006")
    print("   Archive Support: ZIP, RAR, 7Z automatic extraction")
    print("   Navigation: Search, filters, pagination")

    app.run(host='0.0.0.0', port=5006, debug=True, use_reloader=False)