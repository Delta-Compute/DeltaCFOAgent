#!/usr/bin/env python3
"""
Advanced Multi-Upload System - Fixed Version with Enhanced UI
Sistema aprimorado com correções de template, animações e filtros
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
app.secret_key = 'advanced_upload_fixed_secret'

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
            raw_claude_response TEXT,
            archive_source TEXT
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

            # Open PDF and extract text and images
            doc = fitz.open(file_path)
            text_content = ""

            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                text_content += page.get_text()

            doc.close()

            if text_content.strip():
                # Use text analysis if we have text
                return self._call_claude_text_analysis(text_content, file_path)
            else:
                # Convert first page to image for vision API
                doc = fitz.open(file_path)
                page = doc.load_page(0)
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)
                image_bytes = pix.pil_tobytes(format="PNG")
                doc.close()

                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                return self._call_claude_vision(image_base64, file_path)

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
        """Call Claude Vision API for image analysis"""
        try:
            # Enhanced prompt for better extraction
            prompt = """Analyze this invoice/document image and extract ALL information with maximum accuracy.

Extract these fields with precision:

REQUIRED FIELDS:
- invoice_number: Invoice/bill number (if present)
- date: Invoice date in YYYY-MM-DD format
- vendor_name: Company/vendor name
- total_amount: Total amount as number (no currency symbols)
- currency: Currency code (USD, EUR, BRL, etc.)

BUSINESS CLASSIFICATION:
Classify the business unit based on vendor:
- If vendor contains AWS/Amazon/Google/Microsoft → "Delta LLC"
- If vendor contains Coinbase/Binance/Crypto → "Delta Prop Shop LLC"
- If document mentions Paraguay → "Delta Mining Paraguay S.A."
- If document mentions Brazil → "Delta Brazil"
- Otherwise → "Delta LLC"

CATEGORY CLASSIFICATION:
- Technology/Cloud services → "Technology Expenses"
- Trading/Crypto → "Trading Expenses"
- Utilities → "Utilities"
- Professional services → "Professional Services"
- Other → "Other"

Return ONLY a JSON object:
{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "vendor_name": "string",
    "total_amount": numeric_value_only,
    "currency": "USD",
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Detailed analysis notes"
}

Be precise with numbers and dates."""

            content_parts = [
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

            if text_content:
                content_parts.append({
                    "type": "text",
                    "text": f"Additional text content: {text_content[:1000]}"
                })

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": content_parts
                }]
            )

            response_text = response.content[0].text.strip()

            # Clean JSON response
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)
            return self._format_response(extracted_data, file_path)

        except Exception as e:
            return {'status': 'error', 'error': f'Vision API error: {str(e)}'}

    def _call_claude_text_analysis(self, content, file_path):
        """Call Claude for text analysis"""
        prompt = f"""Analyze this text content and extract invoice information in JSON format:

Content:
{content}

Extract invoice fields if this appears to be financial/invoice data. If not clearly an invoice, classify as best as possible.

BUSINESS UNIT CLASSIFICATION:
- Technology vendors (AWS, Google, Microsoft, etc.) → "Delta LLC"
- Trading/Crypto (Coinbase, Binance, etc.) → "Delta Prop Shop LLC"
- Paraguay operations → "Delta Mining Paraguay S.A."
- Brazil operations → "Delta Brazil"
- Default → "Delta LLC"

Return ONLY valid JSON:
{{
    "invoice_number": "string or null",
    "date": "YYYY-MM-DD or null",
    "vendor_name": "string",
    "total_amount": numeric_value,
    "currency": "USD",
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Analysis details"
}}"""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response_text = response.content[0].text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)
            return self._format_response(extracted_data, file_path)

        except Exception as e:
            return {'status': 'error', 'error': f'Text analysis failed: {str(e)}'}

    def _format_response(self, extracted_data, file_path):
        """Format and validate the response"""
        try:
            formatted = {
                'status': 'success',
                'invoice_number': extracted_data.get('invoice_number', 'N/A'),
                'date': extracted_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'vendor_name': extracted_data.get('vendor_name', 'Unknown Vendor'),
                'total_amount': float(extracted_data.get('total_amount', 0)),
                'currency': extracted_data.get('currency', 'USD'),
                'business_unit': extracted_data.get('business_unit', 'Delta LLC'),
                'category': extracted_data.get('category', 'Other'),
                'confidence_score': float(extracted_data.get('confidence', 0.8)),
                'processing_notes': extracted_data.get('processing_notes', 'Processed successfully'),
                'source_file': os.path.basename(file_path),
                'processed_at': datetime.now().isoformat(),
                'extraction_method': 'claude_vision' if any(x in str(file_path).lower() for x in ['.png', '.jpg', '.pdf']) else 'claude_text'
            }
            return formatted
        except Exception as e:
            return {'status': 'error', 'error': f'Response formatting failed: {str(e)}'}

# Initialize processor
processor = AdvancedFileProcessor(CLAUDE_API_KEY)

# Enhanced template with loading animations and filters
ENHANCED_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Delta CFO Agent - Advanced Upload System</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1400px;
            margin: 20px auto;
            padding: 20px;
            background: #f8f9fa;
            line-height: 1.6;
        }

        .header {
            background: linear-gradient(135deg, #007bff, #0056b3);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            text-align: center;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }

        .upload-section, .results-section {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .multi-upload-area {
            border: 3px dashed #007bff;
            padding: 40px;
            text-align: center;
            border-radius: 12px;
            margin: 20px 0;
            transition: all 0.3s;
            position: relative;
        }

        .multi-upload-area:hover {
            border-color: #0056b3;
            background: #f8f9ff;
        }

        .multi-upload-area.drag-over {
            border-color: #28a745;
            background: #f8fff8;
        }

        .btn {
            background: linear-gradient(135deg, #007bff, #0056b3);
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
            position: relative;
            overflow: hidden;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,123,255,0.3);
        }

        .btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
        }

        /* Loading Animation */
        .loading {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }

        .loading.show {
            display: flex;
        }

        .loading-content {
            background: white;
            padding: 40px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }

        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid #e3e3e3;
            border-top: 4px solid #007bff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            margin: 10px 0;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #007bff, #28a745);
            transition: width 0.3s;
            animation: progress-pulse 2s ease-in-out infinite;
        }

        @keyframes progress-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }

        /* Batch Results */
        .batch-summary {
            background: linear-gradient(135deg, #e7f3ff, #cce7ff);
            padding: 20px;
            margin: 15px 0;
            border-radius: 12px;
            border: 1px solid #b3d9ff;
        }

        .file-result {
            margin: 10px 0;
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
            background: #f8f9fa;
            transition: all 0.3s;
        }

        .file-result:hover {
            transform: translateX(5px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .file-success {
            background: #d4edda;
            border-left-color: #28a745;
        }

        .file-error {
            background: #f8d7da;
            border-left-color: #dc3545;
        }

        /* Search and Filters */
        .search-filters {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #dee2e6;
        }

        .filter-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr auto;
            gap: 15px;
            align-items: end;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
        }

        .filter-group label {
            font-weight: 600;
            margin-bottom: 5px;
            color: #495057;
        }

        .filter-group input,
        .filter-group select {
            padding: 8px 12px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 14px;
        }

        .filter-group input:focus,
        .filter-group select:focus {
            outline: none;
            border-color: #007bff;
            box-shadow: 0 0 0 2px rgba(0,123,255,0.25);
        }

        .clear-filters {
            background: #6c757d;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            height: fit-content;
        }

        /* Invoice Cards */
        .invoice-card {
            background: white;
            padding: 20px;
            margin: 10px 0;
            border-radius: 12px;
            border-left: 4px solid #28a745;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: all 0.3s;
        }

        .invoice-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .invoice-header {
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 10px;
        }

        .invoice-amount {
            font-size: 18px;
            font-weight: bold;
            color: #28a745;
        }

        .invoice-meta {
            font-size: 12px;
            color: #6c757d;
            margin-top: 10px;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }

        .stat {
            background: white;
            padding: 15px;
            text-align: center;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }

        .stat-label {
            font-size: 12px;
            color: #6c757d;
            margin-top: 5px;
        }

        .supported-types {
            background: #e7f3ff;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }

        .file-list {
            margin: 20px 0;
        }

        .file-item {
            background: #f8f9fa;
            padding: 12px;
            margin: 8px 0;
            border-radius: 8px;
            border-left: 4px solid #007bff;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .remove-file {
            background: #dc3545;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .container {
                grid-template-columns: 1fr;
            }

            .filter-row {
                grid-template-columns: 1fr;
                gap: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Delta CFO Agent - Sistema Avançado de Upload</h1>
        <p>Multi-arquivo • ZIP/RAR • Claude Vision • Classificação Inteligente</p>
    </div>

    <div class="container">
        <div class="upload-section">
            <h2>📁 Multi-File Upload & Processing</h2>

            {% if batch_status %}
            <div class="batch-summary">
                <h3>✅ Resultados do Processamento</h3>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">{{ batch_status.get('total_files', 0) }}</div>
                        <div class="stat-label">Arquivos Processados</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{{ batch_status.get('successful', 0) }}</div>
                        <div class="stat-label">Sucessos</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{{ batch_status.get('errors', 0) }}</div>
                        <div class="stat-label">Erros</div>
                    </div>
                    {% if batch_status.get('archive_files') %}
                    <div class="stat">
                        <div class="stat-value">{{ batch_status.get('archive_files') }}</div>
                        <div class="stat-label">Do Arquivo ZIP</div>
                    </div>
                    {% endif %}
                </div>

                {% if batch_status.get('file_results') %}
                <h4>📄 Detalhes dos Arquivos:</h4>
                {% for result in batch_status.get('file_results', []) %}
                <div class="file-result {{ 'file-success' if result.get('status') == 'success' else 'file-error' }}">
                    <strong>{{ result.get('filename', 'Unknown') }}</strong>
                    {% if result.get('status') == 'success' %}
                        - {{ result.get('vendor_name', 'N/A') }} - ${{ result.get('total_amount', 0) }}
                        ({{ (result.get('confidence_score', 0) * 100) | round }}% confiança)
                    {% else %}
                        - ❌ Erro: {{ result.get('error', 'Unknown error') }}
                    {% endif %}
                </div>
                {% endfor %}
                {% endif %}
            </div>
            {% endif %}

            <form method="POST" enctype="multipart/form-data" id="uploadForm">
                <div class="multi-upload-area" id="dropArea">
                    <h3>📦 Arraste arquivos aqui ou clique para selecionar</h3>
                    <input type="file" name="files" id="fileInput" multiple
                           accept=".pdf,.txt,.png,.jpg,.jpeg,.csv,.xls,.xlsx,.gif,.bmp,.tiff,.docx,.rtf,.zip,.rar" style="display: none;">
                    <p>Suporte a múltiplos arquivos simultâneos</p>
                    <p><strong>🆕 NOVO:</strong> Suporte completo a ZIP/RAR com extração automática!</p>
                </div>

                <div class="file-list" id="fileList"></div>

                <button type="submit" class="btn" id="uploadBtn" disabled>
                    🚀 Processar Arquivos com Claude Vision
                </button>
            </form>

            <div class="supported-types">
                <h4>📋 Tipos de Arquivo Suportados:</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                    <div><strong>📄 Documentos:</strong> PDF, TXT, DOCX, RTF</div>
                    <div><strong>📊 Planilhas:</strong> CSV, XLS, XLSX</div>
                    <div><strong>🖼️ Imagens:</strong> PNG, JPG, GIF, BMP, TIFF</div>
                    <div><strong>📦 Arquivos:</strong> ZIP, RAR (extração automática)</div>
                </div>
            </div>

            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{{ total_invoices }}</div>
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
            <h2>📋 Invoices Processadas ({{ total_invoices }})</h2>

            <!-- Search and Filters -->
            <div class="search-filters">
                <h4>🔍 Filtros de Busca</h4>
                <div class="filter-row">
                    <div class="filter-group">
                        <label for="searchText">Buscar (vendor, número, etc.)</label>
                        <input type="text" id="searchText" placeholder="Digite para buscar...">
                    </div>
                    <div class="filter-group">
                        <label for="filterBU">Business Unit</label>
                        <select id="filterBU">
                            <option value="">Todas</option>
                            <option value="Delta LLC">Delta LLC</option>
                            <option value="Delta Prop Shop LLC">Delta Prop Shop LLC</option>
                            <option value="Delta Mining Paraguay S.A.">Delta Mining Paraguay S.A.</option>
                            <option value="Delta Brazil">Delta Brazil</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label for="filterCategory">Categoria</label>
                        <select id="filterCategory">
                            <option value="">Todas</option>
                            <option value="Technology Expenses">Technology</option>
                            <option value="Trading Expenses">Trading</option>
                            <option value="Utilities">Utilities</option>
                            <option value="Professional Services">Services</option>
                        </select>
                    </div>
                    <button type="button" class="clear-filters" onclick="clearFilters()">
                        🗑️ Limpar
                    </button>
                </div>
            </div>

            <div id="invoicesList">
                {% for invoice in recent_invoices %}
                <div class="invoice-card"
                     data-vendor="{{ invoice[3] | lower }}"
                     data-bu="{{ invoice[7] | lower }}"
                     data-category="{{ invoice[8] | lower }}"
                     data-number="{{ invoice[1] | lower }}"
                     data-date="{{ invoice[2] }}">
                    <div class="invoice-header">
                        <div>
                            <h4>{{ invoice[2] }} - {{ invoice[3] }}</h4>
                            <div class="invoice-amount">${{ invoice[5] }} {{ invoice[6] }}</div>
                        </div>
                        <div style="text-align: right;">
                            <div><strong>{{ invoice[7] }}</strong></div>
                            <div>{{ invoice[8] }}</div>
                        </div>
                    </div>
                    <div class="invoice-meta">
                        <strong>Invoice:</strong> {{ invoice[1] }} |
                        <strong>Confiança:</strong> {{ (invoice[9] * 100) | round }}% |
                        <strong>Arquivo:</strong> {{ invoice[11] }}
                        <br><small>Processado: {{ invoice[15] }}</small>
                    </div>
                    <div style="margin-top: 15px;">
                        <a href="/invoice/{{ invoice[0] }}" class="btn" style="display: inline-block; padding: 6px 12px; font-size: 12px; margin-right: 5px;">
                            👁️ Ver Detalhes
                        </a>
                        <a href="/file/{{ invoice[0] }}" class="btn" style="display: inline-block; padding: 6px 12px; font-size: 12px;">
                            📄 Ver Arquivo
                        </a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <!-- Loading Overlay -->
    <div class="loading" id="loadingOverlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <h3>🤖 Processando com Claude Vision...</h3>
            <p>Extraindo dados, classificando business units e salvando no banco de dados</p>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill" style="width: 0%"></div>
            </div>
            <p id="loadingStatus">Iniciando processamento...</p>
        </div>
    </div>

    <script>
        // Drag and Drop + File Management
        const dropArea = document.getElementById('dropArea');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const uploadBtn = document.getElementById('uploadBtn');
        const uploadForm = document.getElementById('uploadForm');
        const loadingOverlay = document.getElementById('loadingOverlay');
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

                const isArchive = file.name.toLowerCase().endsWith('.zip') || file.name.toLowerCase().endsWith('.rar');
                const archiveIcon = isArchive ? '📦 ' : '📄 ';

                div.innerHTML = `
                    <div>
                        <strong>${archiveIcon}${file.name}</strong>
                        <span style="color: #6c757d;">(${(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                        ${isArchive ? '<br><small style="color: #007bff;">📦 Arquivo será extraído automaticamente</small>' : ''}
                    </div>
                    <button type="button" class="remove-file" onclick="removeFile(${index})">×</button>
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

        // Form submission with loading animation
        uploadForm.addEventListener('submit', function(e) {
            if (selectedFiles.length === 0) {
                e.preventDefault();
                return;
            }

            // Show loading overlay
            loadingOverlay.classList.add('show');
            uploadBtn.disabled = true;

            // Simulate progress (since we can't get real progress from server)
            let progress = 0;
            const progressFill = document.getElementById('progressFill');
            const loadingStatus = document.getElementById('loadingStatus');

            const progressInterval = setInterval(() => {
                progress += Math.random() * 15;
                if (progress > 95) progress = 95;

                progressFill.style.width = progress + '%';

                if (progress < 30) {
                    loadingStatus.textContent = 'Fazendo upload dos arquivos...';
                } else if (progress < 60) {
                    loadingStatus.textContent = 'Extraindo dados com Claude Vision...';
                } else if (progress < 90) {
                    loadingStatus.textContent = 'Classificando business units...';
                } else {
                    loadingStatus.textContent = 'Salvando no banco de dados...';
                }
            }, 200);

            // Clear interval when form actually submits
            setTimeout(() => {
                clearInterval(progressInterval);
                progressFill.style.width = '100%';
                loadingStatus.textContent = 'Concluído! Redirecionando...';
            }, 8000);
        });

        // Search and Filter Functions
        const searchText = document.getElementById('searchText');
        const filterBU = document.getElementById('filterBU');
        const filterCategory = document.getElementById('filterCategory');
        const invoiceCards = document.querySelectorAll('.invoice-card');

        function filterInvoices() {
            const searchTerm = searchText.value.toLowerCase();
            const selectedBU = filterBU.value.toLowerCase();
            const selectedCategory = filterCategory.value.toLowerCase();

            invoiceCards.forEach(card => {
                const vendor = card.dataset.vendor || '';
                const bu = card.dataset.bu || '';
                const category = card.dataset.category || '';
                const number = card.dataset.number || '';
                const date = card.dataset.date || '';

                const matchesSearch = !searchTerm ||
                    vendor.includes(searchTerm) ||
                    number.includes(searchTerm) ||
                    date.includes(searchTerm);

                const matchesBU = !selectedBU || bu.includes(selectedBU);
                const matchesCategory = !selectedCategory || category.includes(selectedCategory);

                if (matchesSearch && matchesBU && matchesCategory) {
                    card.style.display = 'block';
                    card.style.animation = 'fadeIn 0.3s ease-in-out';
                } else {
                    card.style.display = 'none';
                }
            });
        }

        function clearFilters() {
            searchText.value = '';
            filterBU.value = '';
            filterCategory.value = '';
            filterInvoices();
        }

        // Add event listeners for real-time filtering
        searchText.addEventListener('input', filterInvoices);
        filterBU.addEventListener('change', filterInvoices);
        filterCategory.addEventListener('change', filterInvoices);

        // Add fade-in animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
        `;
        document.head.appendChild(style);
    </script>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def upload_form():
    """Enhanced upload form with fixed template"""
    batch_status = None

    if request.method == 'POST':
        files = request.files.getlist('files')
        if files and any(f.filename for f in files):
            batch_id = str(uuid.uuid4())[:8]
            batch_status = process_batch_files(files, batch_id)

    # Get invoices with pagination
    page = int(request.args.get('page', 1))
    per_page = 20
    offset = (page - 1) * per_page

    conn = sqlite3.connect(DB_PATH)
    invoices = conn.execute(
        "SELECT * FROM invoices ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()

    total_invoices = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]

    # Stats
    success_count = conn.execute("SELECT COUNT(*) FROM invoices WHERE confidence_score > 0.5").fetchone()[0]
    success_rate = int((success_count / total_invoices * 100)) if total_invoices > 0 else 0
    conn.close()

    total_pages = (total_invoices + per_page - 1) // per_page

    return render_template_string(ENHANCED_TEMPLATE,
                                 batch_status=batch_status,
                                 recent_invoices=invoices,
                                 total_invoices=total_invoices,
                                 current_page=page,
                                 total_pages=total_pages,
                                 success_rate=success_rate,
                                 supported_types_count=len(processor.supported_types))

def process_batch_files(files, batch_id):
    """Process multiple files in batch with enhanced results"""
    try:
        valid_files = [f for f in files if f.filename and processor.is_supported_file(f.filename)]
        if not valid_files:
            return {'type': 'error', 'message': 'Nenhum arquivo com formato suportado'}

        processed = 0
        failed = 0
        results = []
        file_results = []
        archive_files = 0

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
                    file_results.append({
                        'filename': file.filename,
                        'status': 'error',
                        'error': extracted_data.get('error', 'Unknown error')
                    })
                    print(f"Failed to process {file.filename}: {extracted_data['error']}")
                elif extracted_data.get('archive_processed'):
                    # Handle archive files with multiple results
                    archive_results = extracted_data.get('results', [])
                    archive_files += len(archive_results)

                    for archive_result in archive_results:
                        try:
                            invoice_id = save_advanced_invoice(archive_result, str(file_path), file)
                            processed += 1
                            results.append(invoice_id)

                            file_results.append({
                                'filename': archive_result.get('original_filename', 'Unknown'),
                                'status': 'success',
                                'vendor_name': archive_result.get('vendor_name'),
                                'total_amount': archive_result.get('total_amount'),
                                'confidence_score': archive_result.get('confidence_score')
                            })
                        except Exception as e:
                            failed += 1
                            file_results.append({
                                'filename': archive_result.get('original_filename', 'Unknown'),
                                'status': 'error',
                                'error': str(e)
                            })
                            print(f"Failed to save archive file result: {e}")
                else:
                    # Save to database (single file)
                    invoice_id = save_advanced_invoice(extracted_data, str(file_path), file)
                    processed += 1
                    results.append(invoice_id)

                    file_results.append({
                        'filename': file.filename,
                        'status': 'success',
                        'vendor_name': extracted_data.get('vendor_name'),
                        'total_amount': extracted_data.get('total_amount'),
                        'confidence_score': extracted_data.get('confidence_score')
                    })

            except Exception as e:
                failed += 1
                file_results.append({
                    'filename': file.filename,
                    'status': 'error',
                    'error': str(e)
                })
                print(f"Error processing {file.filename}: {e}")

        return {
            'type': 'success' if processed > 0 else 'error',
            'total_files': processed + failed,
            'successful': processed,
            'errors': failed,
            'archive_files': archive_files,
            'file_results': file_results
        }

    except Exception as e:
        return {'type': 'error', 'message': f'Batch processing failed: {str(e)}'}

def save_advanced_invoice(extracted_data, file_path, original_file):
    """Save invoice to database with enhanced metadata"""
    conn = sqlite3.connect(DB_PATH)

    invoice_id = str(uuid.uuid4())[:8]
    file_stats = os.stat(file_path)

    conn.execute('''
        INSERT INTO invoices (
            id, invoice_number, date, vendor_name, vendor_data, total_amount, currency,
            business_unit, category, confidence_score, processing_notes,
            source_file, file_path, file_type, file_size, processed_at, created_at,
            extraction_method, raw_claude_response, archive_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        invoice_id,
        extracted_data.get('invoice_number'),
        extracted_data.get('date'),
        extracted_data.get('vendor_name'),
        json.dumps(extracted_data),  # Store full data as JSON
        extracted_data.get('total_amount'),
        extracted_data.get('currency'),
        extracted_data.get('business_unit'),
        extracted_data.get('category'),
        extracted_data.get('confidence_score'),
        extracted_data.get('processing_notes'),
        original_file.filename,
        str(file_path),
        original_file.content_type,
        file_stats.st_size,
        extracted_data.get('processed_at'),
        datetime.now().isoformat(),
        extracted_data.get('extraction_method'),
        json.dumps(extracted_data),  # Raw response
        extracted_data.get('archive_source')  # Source archive if from ZIP/RAR
    ))

    conn.commit()
    conn.close()

    return invoice_id

@app.route('/invoice/<invoice_id>')
def invoice_details(invoice_id):
    """Show detailed invoice information"""
    conn = sqlite3.connect(DB_PATH)
    invoice = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()

    if not invoice:
        return "Invoice not found", 404

    # Enhanced invoice detail template
    detail_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Invoice Details - {{ invoice[1] }}</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px; background: #f8f9fa; }
            .detail-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .field { display: grid; grid-template-columns: 1fr 2fr; gap: 15px; margin: 10px 0; padding: 10px 0; border-bottom: 1px solid #eee; }
            .label { font-weight: 600; color: #495057; }
            .value { color: #212529; }
            .header { text-align: center; margin-bottom: 30px; }
            .btn { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px; display: inline-block; }
            .btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="detail-card">
            <div class="header">
                <h1>📄 Detalhes da Invoice</h1>
                <h2>{{ invoice[1] or 'N/A' }}</h2>
            </div>

            <div class="field"><div class="label">📋 Invoice ID:</div><div class="value">{{ invoice[0] }}</div></div>
            <div class="field"><div class="label">🔢 Número:</div><div class="value">{{ invoice[1] or 'N/A' }}</div></div>
            <div class="field"><div class="label">📅 Data:</div><div class="value">{{ invoice[2] or 'N/A' }}</div></div>
            <div class="field"><div class="label">🏢 Vendor:</div><div class="value">{{ invoice[3] or 'N/A' }}</div></div>
            <div class="field"><div class="label">💰 Valor:</div><div class="value">${{ invoice[5] }} {{ invoice[6] }}</div></div>
            <div class="field"><div class="label">🏛️ Business Unit:</div><div class="value">{{ invoice[7] or 'N/A' }}</div></div>
            <div class="field"><div class="label">📂 Categoria:</div><div class="value">{{ invoice[8] or 'N/A' }}</div></div>
            <div class="field"><div class="label">🎯 Confiança:</div><div class="value">{{ (invoice[9] * 100) | round }}%</div></div>
            <div class="field"><div class="label">📝 Notas:</div><div class="value">{{ invoice[10] or 'N/A' }}</div></div>
            <div class="field"><div class="label">📄 Arquivo:</div><div class="value">{{ invoice[11] }}</div></div>
            <div class="field"><div class="label">💾 Tamanho:</div><div class="value">{{ (invoice[14] / 1024 / 1024) | round(2) }} MB</div></div>
            <div class="field"><div class="label">⚙️ Método:</div><div class="value">{{ invoice[16] or 'N/A' }}</div></div>
            <div class="field"><div class="label">🕒 Processado:</div><div class="value">{{ invoice[15] }}</div></div>
            {% if invoice[19] %}
            <div class="field"><div class="label">📦 Arquivo de Origem:</div><div class="value">{{ invoice[19] }}</div></div>
            {% endif %}

            <div style="text-align: center; margin-top: 30px;">
                <a href="/file/{{ invoice[0] }}" class="btn">📄 Ver Arquivo Original</a>
                <a href="/" class="btn">🔙 Voltar</a>
            </div>
        </div>
    </body>
    </html>
    '''

    return render_template_string(detail_template, invoice=invoice)

@app.route('/file/<invoice_id>')
def serve_file(invoice_id):
    """Serve the original uploaded file"""
    conn = sqlite3.connect(DB_PATH)
    invoice = conn.execute("SELECT file_path, source_file FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()

    if not invoice or not invoice[0]:
        return "File not found", 404

    file_path = Path(invoice[0])
    if not file_path.exists():
        return "File no longer exists", 404

    return send_from_directory(file_path.parent, file_path.name, as_attachment=True)

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    conn = sqlite3.connect(DB_PATH)

    stats = {
        'total_invoices': conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0],
        'avg_confidence': conn.execute("SELECT AVG(confidence_score) FROM invoices").fetchone()[0] or 0,
        'business_units': {}
    }

    # Business unit breakdown
    bu_data = conn.execute("SELECT business_unit, COUNT(*), SUM(total_amount) FROM invoices GROUP BY business_unit").fetchall()
    for bu, count, total in bu_data:
        stats['business_units'][bu] = {'count': count, 'total_amount': total or 0}

    conn.close()
    return jsonify(stats)

if __name__ == '__main__':
    init_db()
    print("Advanced Upload System - Enhanced Version")
    print("   Features: Fixed UI, Loading animations, Search filters")
    print("   Archive Support: ZIP, RAR with auto-extraction")
    print("   Search: Real-time filtering by vendor, BU, category")
    print("   UI: Enhanced design with animations")
    print("   Access: http://localhost:5005")

    app.run(host='0.0.0.0', port=5005, debug=True, use_reloader=False)