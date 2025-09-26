#!/usr/bin/env python3
"""
Visual Enhanced Invoice System
Sistema aprimorado com interface visual moderna, filtros e pesquisa
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
app.secret_key = 'visual_enhanced_secret'

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

    def _process_archive(self, archive_path):
        """Process archive files (ZIP/RAR) and extract contents"""
        try:
            results = []
            extracted_files = []
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract archive
                if archive_path.suffix.lower() == '.zip':
                    extracted_files = self._extract_zip(archive_path, temp_path)
                elif archive_path.suffix.lower() == '.rar':
                    extracted_files = self._extract_rar(archive_path, temp_path)

                print(f"Extracted {len(extracted_files)} files from archive")

                # Process each extracted file
                for extracted_file in extracted_files:
                    if extracted_file.suffix.lower() in self.supported_types:
                        print(f"Processing extracted file: {extracted_file.name}")
                        result = self.process_single_file(extracted_file)
                        if result:
                            result['source_archive'] = archive_path.name
                            results.append(result)
                    else:
                        print(f"Skipping unsupported file: {extracted_file.name}")

            return results

        except Exception as e:
            print(f"Error processing archive {archive_path}: {e}")
            return []

    def _extract_zip(self, archive_path, extract_dir):
        """Extract ZIP archive and return list of extracted files"""
        extracted_files = []
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

                # Get all extracted files
                for item in zip_ref.namelist():
                    extracted_path = extract_dir / item
                    if extracted_path.is_file():
                        extracted_files.append(extracted_path)

        except Exception as e:
            print(f"Error extracting ZIP: {e}")

        return extracted_files

    def _extract_rar(self, archive_path, extract_dir):
        """Extract RAR archive and return list of extracted files"""
        extracted_files = []
        try:
            import rarfile
            with rarfile.RarFile(archive_path, 'r') as rar_ref:
                rar_ref.extractall(extract_dir)

                # Get all extracted files
                for item in rar_ref.namelist():
                    extracted_path = extract_dir / item
                    if extracted_path.is_file():
                        extracted_files.append(extracted_path)

        except ImportError:
            print("rarfile library not installed. Install with: pip install rarfile")
        except Exception as e:
            print(f"Error extracting RAR: {e}")

        return extracted_files

    def process_batch_files(self, file_paths):
        """Process multiple files and return results"""
        batch_id = str(uuid.uuid4())
        results = []
        total_files = len(file_paths)
        processed_files = 0
        failed_files = 0

        # Save batch info
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''
            INSERT INTO batch_uploads (id, total_files, processed_files, failed_files, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (batch_id, total_files, 0, 0, 'processing', datetime.now().isoformat()))
        conn.commit()
        conn.close()

        print(f"Starting batch processing: {total_files} files")

        for file_path in file_paths:
            try:
                print(f"Processing: {file_path.name}")

                # Check if it's an archive
                if file_path.suffix.lower() in ['.zip', '.rar']:
                    print(f"Archive detected: {file_path.name}")
                    archive_results = self._process_archive(file_path)
                    results.extend(archive_results)
                    processed_files += len(archive_results)
                else:
                    # Process regular file
                    result = self.process_single_file(file_path)
                    if result:
                        results.append(result)
                        processed_files += 1
                    else:
                        failed_files += 1

            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                failed_files += 1

        # Update batch status
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''
            UPDATE batch_uploads
            SET processed_files = ?, failed_files = ?, status = ?, completed_at = ?
            WHERE id = ?
        ''', (processed_files, failed_files, 'completed', datetime.now().isoformat(), batch_id))
        conn.commit()
        conn.close()

        print(f"Batch completed: {processed_files} processed, {failed_files} failed")

        return {
            'batch_id': batch_id,
            'results': results,
            'total_files': total_files,
            'processed_files': processed_files,
            'failed_files': failed_files,
            'success_rate': round((processed_files / total_files) * 100, 2) if total_files > 0 else 0
        }

    def process_single_file(self, file_path):
        """Process a single file and return structured data"""
        try:
            file_ext = file_path.suffix.lower()

            if file_ext not in self.supported_types:
                print(f"Unsupported file type: {file_ext}")
                return None

            # Read and process file based on type
            if file_ext in ['.csv', '.xls', '.xlsx']:
                return self._process_spreadsheet(file_path)
            elif file_ext == '.pdf':
                return self._process_pdf(file_path)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
                return self._process_image(file_path)
            elif file_ext == '.txt':
                return self._process_text(file_path)
            else:
                print(f"Processing method not implemented for: {file_ext}")
                return None

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None

    def _process_spreadsheet(self, file_path):
        """Process spreadsheet files"""
        try:
            # Read spreadsheet
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # Convert to structured data for Claude
            data_text = f"Spreadsheet data from {file_path.name}:\n"
            data_text += df.to_string(index=False)

            return self._analyze_with_claude(data_text, file_path, 'spreadsheet')

        except Exception as e:
            print(f"Error processing spreadsheet {file_path}: {e}")
            return None

    def _process_pdf(self, file_path):
        """Process PDF files"""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(file_path)
            text_content = ""

            for page_num in range(len(doc)):
                page = doc[page_num]
                text_content += page.get_text()

            doc.close()

            return self._analyze_with_claude(text_content, file_path, 'pdf_text')

        except ImportError:
            print("PyMuPDF not installed. Install with: pip install PyMuPDF")
            return None
        except Exception as e:
            print(f"Error processing PDF {file_path}: {e}")
            return None

    def _process_image(self, file_path):
        """Process image files with Claude Vision"""
        try:
            with open(file_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            media_type = self.supported_types[file_path.suffix.lower()]

            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": """Analyze this document image and extract invoice/financial information. Return a JSON with:
{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "vendor_name": "string",
    "vendor_data": "full vendor info",
    "total_amount": number,
    "currency": "USD/BRL/etc",
    "business_unit": "classify as Delta Prop, Delta Mining, Delta Land, Delta Agro, or Other",
    "category": "Trading/Mining/Agriculture/Real Estate/Other",
    "confidence_score": 0.0-1.0,
    "processing_notes": "any relevant notes"
}"""
                        }
                    ]
                }]
            )

            return self._parse_claude_response(message.content[0].text, file_path, 'image')

        except Exception as e:
            print(f"Error processing image {file_path}: {e}")
            return None

    def _process_text(self, file_path):
        """Process text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return self._analyze_with_claude(content, file_path, 'text')

        except Exception as e:
            print(f"Error processing text file {file_path}: {e}")
            return None

    def _analyze_with_claude(self, content, file_path, method):
        """Analyze content with Claude API"""
        try:
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze this document content and extract invoice/financial information. Return a JSON with:
{{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "vendor_name": "string",
    "vendor_data": "full vendor info",
    "total_amount": number,
    "currency": "USD/BRL/etc",
    "business_unit": "classify as Delta Prop, Delta Mining, Delta Land, Delta Agro, or Other",
    "category": "Trading/Mining/Agriculture/Real Estate/Other",
    "confidence_score": 0.0-1.0,
    "processing_notes": "any relevant notes"
}}

Document content:
{content[:3000]}"""
                }]
            )

            return self._parse_claude_response(message.content[0].text, file_path, method)

        except Exception as e:
            print(f"Error analyzing with Claude: {e}")
            return None

    def _parse_claude_response(self, response_text, file_path, method):
        """Parse Claude response and save to database"""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")

            # Copy file to upload directory
            new_file_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file_path.name}"
            if file_path.exists():
                shutil.copy2(file_path, new_file_path)

            # Prepare invoice data
            invoice_id = str(uuid.uuid4())
            invoice_data = {
                'id': invoice_id,
                'invoice_number': data.get('invoice_number', ''),
                'date': data.get('date', ''),
                'vendor_name': data.get('vendor_name', ''),
                'vendor_data': data.get('vendor_data', ''),
                'total_amount': float(data.get('total_amount', 0)) if data.get('total_amount') else 0,
                'currency': data.get('currency', 'USD'),
                'business_unit': data.get('business_unit', 'Other'),
                'category': data.get('category', 'Other'),
                'confidence_score': float(data.get('confidence_score', 0)) if data.get('confidence_score') else 0,
                'processing_notes': data.get('processing_notes', ''),
                'source_file': file_path.name,
                'file_path': str(new_file_path),
                'file_type': file_path.suffix.lower(),
                'file_size': file_path.stat().st_size if file_path.exists() else 0,
                'processed_at': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'extraction_method': method,
                'raw_claude_response': response_text
            }

            # Save to database
            conn = sqlite3.connect(DB_PATH)
            conn.execute('''
                INSERT INTO invoices (
                    id, invoice_number, date, vendor_name, vendor_data, total_amount, currency,
                    business_unit, category, confidence_score, processing_notes, source_file,
                    file_path, file_type, file_size, processed_at, created_at,
                    extraction_method, raw_claude_response
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_data['id'], invoice_data['invoice_number'], invoice_data['date'],
                invoice_data['vendor_name'], invoice_data['vendor_data'], invoice_data['total_amount'],
                invoice_data['currency'], invoice_data['business_unit'], invoice_data['category'],
                invoice_data['confidence_score'], invoice_data['processing_notes'], invoice_data['source_file'],
                invoice_data['file_path'], invoice_data['file_type'], invoice_data['file_size'],
                invoice_data['processed_at'], invoice_data['created_at'], invoice_data['extraction_method'],
                invoice_data['raw_claude_response']
            ))
            conn.commit()
            conn.close()

            print(f"Successfully processed: {file_path.name}")
            return invoice_data

        except Exception as e:
            print(f"Error parsing Claude response: {e}")
            return None

# Global processor instance
processor = AdvancedFileProcessor(CLAUDE_API_KEY)

# Enhanced HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Delta CFO Agent - Sistema de Upload Avançado</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            padding: 30px;
            margin-bottom: 30px;
            transition: transform 0.3s ease;
        }

        .card:hover {
            transform: translateY(-5px);
        }

        .upload-section {
            text-align: center;
        }

        .upload-section h2 {
            color: #4a5568;
            margin-bottom: 20px;
            font-size: 1.8em;
        }

        .file-input-wrapper {
            position: relative;
            display: inline-block;
            margin: 20px 0;
        }

        .file-input {
            opacity: 0;
            position: absolute;
            z-index: -1;
        }

        .file-input-button {
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1.1em;
            transition: all 0.3s ease;
            border: none;
            text-decoration: none;
        }

        .file-input-button:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }

        .process-button {
            background: linear-gradient(135deg, #ff7b7b 0%, #ff6b6b 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1.1em;
            margin: 20px 10px;
            transition: all 0.3s ease;
        }

        .process-button:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(255,107,107,0.4);
        }

        .process-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .selected-files {
            margin: 20px 0;
            text-align: left;
            max-height: 200px;
            overflow-y: auto;
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
        }

        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
        }

        .file-item:last-child {
            border-bottom: none;
        }

        .file-info {
            display: flex;
            flex-direction: column;
        }

        .file-name {
            font-weight: 600;
            color: #495057;
        }

        .file-size {
            font-size: 0.9em;
            color: #6c757d;
        }

        .loading {
            display: none;
            text-align: center;
            padding: 30px;
        }

        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .results-section {
            margin-top: 30px;
        }

        .results-section h2 {
            color: #4a5568;
            margin-bottom: 20px;
            font-size: 1.8em;
            text-align: center;
        }

        .filters {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .filter-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
        }

        .filter-group label {
            font-weight: 600;
            color: #495057;
            margin-bottom: 5px;
        }

        .filter-group input,
        .filter-group select {
            padding: 10px;
            border: 2px solid #e9ecef;
            border-radius: 5px;
            font-size: 1em;
            transition: border-color 0.3s ease;
        }

        .filter-group input:focus,
        .filter-group select:focus {
            outline: none;
            border-color: #667eea;
        }

        .clear-filters {
            background: #6c757d;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }

        .clear-filters:hover {
            background: #5a6268;
        }

        .invoice-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }

        .invoice-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            padding: 20px;
            transition: all 0.3s ease;
            border-left: 5px solid #667eea;
        }

        .invoice-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }

        .invoice-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .invoice-number {
            font-weight: 700;
            font-size: 1.2em;
            color: #2d3748;
        }

        .invoice-amount {
            font-weight: 700;
            font-size: 1.3em;
            color: #48bb78;
        }

        .invoice-vendor {
            font-size: 1.1em;
            color: #4a5568;
            margin-bottom: 10px;
            font-weight: 600;
        }

        .invoice-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 15px 0;
            font-size: 0.9em;
        }

        .detail-item {
            display: flex;
            flex-direction: column;
        }

        .detail-label {
            font-weight: 600;
            color: #718096;
            font-size: 0.8em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .detail-value {
            color: #2d3748;
            margin-top: 2px;
        }

        .business-unit-tag {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .bu-delta-prop { background: #e6fffa; color: #319795; }
        .bu-delta-mining { background: #fef5e7; color: #d69e2e; }
        .bu-delta-land { background: #f0fff4; color: #38a169; }
        .bu-delta-agro { background: #edf2f7; color: #4a5568; }
        .bu-other { background: #fed7e2; color: #b83280; }

        .invoice-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e2e8f0;
        }

        .action-button {
            flex: 1;
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 600;
            transition: all 0.3s ease;
            text-decoration: none;
            text-align: center;
            display: inline-block;
        }

        .view-details {
            background: #667eea;
            color: white;
        }

        .view-details:hover {
            background: #5a67d8;
            transform: translateY(-1px);
        }

        .download-file {
            background: #48bb78;
            color: white;
        }

        .download-file:hover {
            background: #38a169;
            transform: translateY(-1px);
        }

        .no-invoices {
            text-align: center;
            padding: 60px 20px;
            color: #718096;
        }

        .no-invoices h3 {
            font-size: 1.5em;
            margin-bottom: 10px;
        }

        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: 30px;
            gap: 10px;
        }

        .pagination button {
            padding: 8px 16px;
            border: 2px solid #e2e8f0;
            background: white;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .pagination button:hover {
            border-color: #667eea;
            background: #667eea;
            color: white;
        }

        .pagination button.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }

        .pagination button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }

        .stat-value {
            font-size: 2em;
            font-weight: 700;
            display: block;
        }

        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }

            .header h1 {
                font-size: 2em;
            }

            .card {
                padding: 20px;
            }

            .filter-row {
                grid-template-columns: 1fr;
            }

            .invoice-grid {
                grid-template-columns: 1fr;
            }

            .invoice-details {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Delta CFO Agent</h1>
            <p>Sistema Avançado de Processamento de Invoices</p>
        </div>

        <!-- Upload Section -->
        <div class="card upload-section">
            <h2>Upload de Documentos</h2>
            <p style="color: #666; margin-bottom: 20px;">
                Suporte para: PDF, CSV, XLS, XLSX, Imagens, ZIP, RAR
            </p>

            <div class="file-input-wrapper">
                <input type="file" id="fileInput" class="file-input" multiple accept=".pdf,.csv,.xls,.xlsx,.png,.jpg,.jpeg,.gif,.bmp,.tiff,.zip,.rar,.txt,.docx,.rtf">
                <label for="fileInput" class="file-input-button">
                    Selecionar Arquivos
                </label>
            </div>

            <div id="selectedFiles" class="selected-files" style="display: none;"></div>

            <button id="processButton" class="process-button" onclick="processFiles()" disabled>
                Processar Arquivos
            </button>

            <div id="loading" class="loading">
                <div class="spinner"></div>
                <p id="loadingText">Processando arquivos...</p>
            </div>
        </div>

        <!-- Results Section -->
        <div class="card results-section">
            <h2>Lista de Invoices</h2>

            <!-- Statistics -->
            <div id="stats" class="stats"></div>

            <!-- Filters -->
            <div class="filters">
                <div class="filter-row">
                    <div class="filter-group">
                        <label for="searchInput">Buscar</label>
                        <input type="text" id="searchInput" placeholder="Número, fornecedor, categoria...">
                    </div>
                    <div class="filter-group">
                        <label for="businessUnitFilter">Business Unit</label>
                        <select id="businessUnitFilter">
                            <option value="">Todas</option>
                            <option value="Delta Prop">Delta Prop</option>
                            <option value="Delta Mining">Delta Mining</option>
                            <option value="Delta Land">Delta Land</option>
                            <option value="Delta Agro">Delta Agro</option>
                            <option value="Other">Outras</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label for="categoryFilter">Categoria</label>
                        <select id="categoryFilter">
                            <option value="">Todas</option>
                            <option value="Trading">Trading</option>
                            <option value="Mining">Mining</option>
                            <option value="Agriculture">Agriculture</option>
                            <option value="Real Estate">Real Estate</option>
                            <option value="Other">Outras</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label for="dateFilter">Data</label>
                        <input type="date" id="dateFilter">
                    </div>
                </div>
                <button onclick="clearFilters()" class="clear-filters">Limpar Filtros</button>
            </div>

            <!-- Invoice Grid -->
            <div id="invoiceGrid" class="invoice-grid"></div>

            <!-- Pagination -->
            <div id="pagination" class="pagination"></div>
        </div>
    </div>

    <script>
        let selectedFiles = [];
        let allInvoices = [];
        let filteredInvoices = [];
        let currentPage = 1;
        const itemsPerPage = 6;

        // File selection handling
        document.getElementById('fileInput').addEventListener('change', function(e) {
            selectedFiles = Array.from(e.target.files);
            updateSelectedFiles();
            updateProcessButton();
        });

        function updateSelectedFiles() {
            const container = document.getElementById('selectedFiles');

            if (selectedFiles.length === 0) {
                container.style.display = 'none';
                return;
            }

            container.style.display = 'block';
            container.innerHTML = '<h4>Arquivos Selecionados:</h4>';

            selectedFiles.forEach((file, index) => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <div class="file-info">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${formatFileSize(file.size)}</div>
                    </div>
                    <button onclick="removeFile(${index})" style="background: #ff6b6b; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">
                        Remover
                    </button>
                `;
                container.appendChild(fileItem);
            });
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            updateSelectedFiles();
            updateProcessButton();
        }

        function updateProcessButton() {
            const button = document.getElementById('processButton');
            button.disabled = selectedFiles.length === 0;
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        // File processing
        async function processFiles() {
            if (selectedFiles.length === 0) return;

            const loading = document.getElementById('loading');
            const processButton = document.getElementById('processButton');
            const loadingText = document.getElementById('loadingText');

            loading.style.display = 'block';
            processButton.disabled = true;

            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('files', file);
            });

            try {
                const response = await fetch('/upload_batch', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    loadingText.textContent = `Processamento concluído! ${result.processed_files} arquivos processados.`;
                    setTimeout(() => {
                        loading.style.display = 'none';
                        selectedFiles = [];
                        document.getElementById('fileInput').value = '';
                        updateSelectedFiles();
                        updateProcessButton();
                        loadInvoices();
                    }, 2000);
                } else {
                    loadingText.textContent = 'Erro no processamento: ' + result.message;
                    setTimeout(() => {
                        loading.style.display = 'none';
                        processButton.disabled = false;
                    }, 3000);
                }
            } catch (error) {
                loadingText.textContent = 'Erro de conexão: ' + error.message;
                setTimeout(() => {
                    loading.style.display = 'none';
                    processButton.disabled = false;
                }, 3000);
            }
        }

        // Invoice loading and filtering
        async function loadInvoices() {
            try {
                const response = await fetch('/get_invoices');
                const data = await response.json();
                allInvoices = data.invoices || [];
                updateStats(data.stats);
                applyFilters();
            } catch (error) {
                console.error('Error loading invoices:', error);
            }
        }

        function updateStats(stats) {
            const statsContainer = document.getElementById('stats');
            if (!stats) return;

            statsContainer.innerHTML = `
                <div class="stat-card">
                    <span class="stat-value">${stats.total_invoices}</span>
                    <span class="stat-label">Total Invoices</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${stats.total_amount ? stats.total_amount.toFixed(2) : '0.00'}</span>
                    <span class="stat-label">Valor Total</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${stats.avg_confidence ? (stats.avg_confidence * 100).toFixed(1) + '%' : '0%'}</span>
                    <span class="stat-label">Confiança Média</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${stats.unique_vendors || 0}</span>
                    <span class="stat-label">Fornecedores</span>
                </div>
            `;
        }

        function applyFilters() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const businessUnit = document.getElementById('businessUnitFilter').value;
            const category = document.getElementById('categoryFilter').value;
            const dateFilter = document.getElementById('dateFilter').value;

            filteredInvoices = allInvoices.filter(invoice => {
                const matchesSearch = !searchTerm ||
                    invoice.invoice_number.toLowerCase().includes(searchTerm) ||
                    invoice.vendor_name.toLowerCase().includes(searchTerm) ||
                    invoice.category.toLowerCase().includes(searchTerm);

                const matchesBU = !businessUnit || invoice.business_unit === businessUnit;
                const matchesCategory = !category || invoice.category === category;
                const matchesDate = !dateFilter || invoice.date === dateFilter;

                return matchesSearch && matchesBU && matchesCategory && matchesDate;
            });

            currentPage = 1;
            displayInvoices();
            displayPagination();
        }

        function displayInvoices() {
            const grid = document.getElementById('invoiceGrid');
            const start = (currentPage - 1) * itemsPerPage;
            const end = start + itemsPerPage;
            const pageInvoices = filteredInvoices.slice(start, end);

            if (pageInvoices.length === 0) {
                grid.innerHTML = `
                    <div class="no-invoices">
                        <h3>Nenhum invoice encontrado</h3>
                        <p>Faça upload de documentos ou ajuste os filtros</p>
                    </div>
                `;
                return;
            }

            grid.innerHTML = pageInvoices.map(invoice => createInvoiceCard(invoice)).join('');
        }

        function createInvoiceCard(invoice) {
            const businessUnitClass = `bu-${invoice.business_unit.toLowerCase().replace(/\\s+/g, '-')}`;
            const amount = invoice.total_amount ? parseFloat(invoice.total_amount).toFixed(2) : '0.00';
            const confidence = invoice.confidence_score ? (invoice.confidence_score * 100).toFixed(1) : '0';

            return `
                <div class="invoice-card">
                    <div class="invoice-header">
                        <div class="invoice-number">${invoice.invoice_number || 'N/A'}</div>
                        <div class="invoice-amount">${invoice.currency} ${amount}</div>
                    </div>

                    <div class="invoice-vendor">${invoice.vendor_name || 'Fornecedor não identificado'}</div>

                    <div class="invoice-details">
                        <div class="detail-item">
                            <span class="detail-label">Data</span>
                            <span class="detail-value">${invoice.date || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Categoria</span>
                            <span class="detail-value">${invoice.category || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Business Unit</span>
                            <span class="detail-value">
                                <span class="business-unit-tag ${businessUnitClass}">
                                    ${invoice.business_unit || 'Other'}
                                </span>
                            </span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Confiança</span>
                            <span class="detail-value">${confidence}%</span>
                        </div>
                    </div>

                    <div class="invoice-actions">
                        <button class="action-button view-details" onclick="viewDetails('${invoice.id}')">
                            Ver Detalhes
                        </button>
                        <a href="/download/${invoice.id}" class="action-button download-file">
                            Download
                        </a>
                    </div>
                </div>
            `;
        }

        function displayPagination() {
            const pagination = document.getElementById('pagination');
            const totalPages = Math.ceil(filteredInvoices.length / itemsPerPage);

            if (totalPages <= 1) {
                pagination.innerHTML = '';
                return;
            }

            let paginationHTML = '';

            // Previous button
            paginationHTML += `
                <button onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
                    Anterior
                </button>
            `;

            // Page numbers
            for (let i = 1; i <= totalPages; i++) {
                if (i === currentPage) {
                    paginationHTML += `<button class="active">${i}</button>`;
                } else {
                    paginationHTML += `<button onclick="changePage(${i})">${i}</button>`;
                }
            }

            // Next button
            paginationHTML += `
                <button onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
                    Próximo
                </button>
            `;

            pagination.innerHTML = paginationHTML;
        }

        function changePage(page) {
            const totalPages = Math.ceil(filteredInvoices.length / itemsPerPage);
            if (page >= 1 && page <= totalPages) {
                currentPage = page;
                displayInvoices();
                displayPagination();
            }
        }

        function clearFilters() {
            document.getElementById('searchInput').value = '';
            document.getElementById('businessUnitFilter').value = '';
            document.getElementById('categoryFilter').value = '';
            document.getElementById('dateFilter').value = '';
            applyFilters();
        }

        function viewDetails(invoiceId) {
            window.open(`/invoice/${invoiceId}`, '_blank');
        }

        // Event listeners for filters
        document.getElementById('searchInput').addEventListener('input', applyFilters);
        document.getElementById('businessUnitFilter').addEventListener('change', applyFilters);
        document.getElementById('categoryFilter').addEventListener('change', applyFilters);
        document.getElementById('dateFilter').addEventListener('change', applyFilters);

        // Load invoices on page load
        document.addEventListener('DOMContentLoaded', loadInvoices);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Main page with enhanced interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload_batch', methods=['POST'])
def upload_batch():
    """Handle batch file uploads"""
    try:
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'})

        # Save uploaded files
        temp_files = []
        for file in files:
            if file.filename:
                temp_path = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}_{file.filename}"
                file.save(temp_path)
                temp_files.append(temp_path)

        # Process files
        result = processor.process_batch_files(temp_files)

        # Clean up temp files
        for temp_file in temp_files:
            try:
                temp_file.unlink()
            except:
                pass

        return jsonify({
            'success': True,
            'batch_id': result['batch_id'],
            'processed_files': result['processed_files'],
            'failed_files': result['failed_files'],
            'success_rate': result['success_rate']
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/get_invoices')
def get_invoices():
    """Get all invoices with statistics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        # Get invoices
        invoices = conn.execute('''
            SELECT * FROM invoices
            ORDER BY processed_at DESC
        ''').fetchall()

        # Get statistics
        stats = conn.execute('''
            SELECT
                COUNT(*) as total_invoices,
                SUM(total_amount) as total_amount,
                AVG(confidence_score) as avg_confidence,
                COUNT(DISTINCT vendor_name) as unique_vendors
            FROM invoices
        ''').fetchone()

        conn.close()

        return jsonify({
            'invoices': [dict(row) for row in invoices],
            'stats': dict(stats) if stats else {}
        })

    except Exception as e:
        return jsonify({'invoices': [], 'stats': {}, 'error': str(e)})

@app.route('/invoice/<invoice_id>')
def invoice_details(invoice_id):
    """Display detailed invoice information"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        invoice = conn.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,)).fetchone()
        conn.close()

        if not invoice:
            return "Invoice não encontrado", 404

        invoice_dict = dict(invoice)

        # Format the raw Claude response for display
        raw_response = invoice_dict.get('raw_claude_response', '')
        vendor_data = invoice_dict.get('vendor_data', '')

        details_html = f'''
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Detalhes do Invoice - {invoice_dict.get('invoice_number', 'N/A')}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; border-bottom: 2px solid #667eea; padding-bottom: 20px; }}
                .detail-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .detail-section {{ background: #f8f9fa; padding: 20px; border-radius: 8px; }}
                .detail-section h3 {{ margin-top: 0; color: #4a5568; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }}
                .detail-item {{ margin: 10px 0; }}
                .detail-label {{ font-weight: 600; color: #718096; display: inline-block; min-width: 120px; }}
                .detail-value {{ color: #2d3748; }}
                .raw-response {{ background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 5px; padding: 15px; max-height: 300px; overflow-y: auto; font-family: monospace; font-size: 0.9em; white-space: pre-wrap; }}
                .back-button {{ display: inline-block; background: #667eea; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; margin-bottom: 20px; }}
                .back-button:hover {{ background: #5a67d8; }}
                .download-button {{ background: #48bb78; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; margin-left: 10px; }}
                .download-button:hover {{ background: #38a169; }}
            </style>
        </head>
        <body>
            <div class="container">
                <a href="javascript:history.back()" class="back-button">← Voltar</a>
                <a href="/download/{invoice_id}" class="download-button">Download Arquivo</a>

                <div class="header">
                    <h1>Invoice {invoice_dict.get('invoice_number', 'N/A')}</h1>
                    <p>Processado em {invoice_dict.get('processed_at', 'N/A')}</p>
                </div>

                <div class="detail-grid">
                    <div class="detail-section">
                        <h3>Informações Básicas</h3>
                        <div class="detail-item">
                            <span class="detail-label">Número:</span>
                            <span class="detail-value">{invoice_dict.get('invoice_number', 'N/A')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Data:</span>
                            <span class="detail-value">{invoice_dict.get('date', 'N/A')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Valor:</span>
                            <span class="detail-value">{invoice_dict.get('currency', 'USD')} {invoice_dict.get('total_amount', 0):.2f}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Business Unit:</span>
                            <span class="detail-value">{invoice_dict.get('business_unit', 'N/A')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Categoria:</span>
                            <span class="detail-value">{invoice_dict.get('category', 'N/A')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Confiança:</span>
                            <span class="detail-value">{(invoice_dict.get('confidence_score', 0) * 100):.1f}%</span>
                        </div>
                    </div>

                    <div class="detail-section">
                        <h3>Arquivo</h3>
                        <div class="detail-item">
                            <span class="detail-label">Nome:</span>
                            <span class="detail-value">{invoice_dict.get('source_file', 'N/A')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Tipo:</span>
                            <span class="detail-value">{invoice_dict.get('file_type', 'N/A')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Tamanho:</span>
                            <span class="detail-value">{invoice_dict.get('file_size', 0)} bytes</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Método:</span>
                            <span class="detail-value">{invoice_dict.get('extraction_method', 'N/A')}</span>
                        </div>
                    </div>
                </div>

                <div class="detail-section">
                    <h3>Fornecedor</h3>
                    <div class="detail-item">
                        <span class="detail-label">Nome:</span>
                        <span class="detail-value">{invoice_dict.get('vendor_name', 'N/A')}</span>
                    </div>
                    {f'<div class="detail-item"><span class="detail-label">Dados Completos:</span><div class="raw-response">{vendor_data}</div></div>' if vendor_data else ''}
                </div>

                {f'<div class="detail-section"><h3>Notas de Processamento</h3><div class="raw-response">{invoice_dict.get("processing_notes", "Nenhuma nota disponível")}</div></div>' if invoice_dict.get('processing_notes') else ''}

                {f'<div class="detail-section"><h3>Resposta Completa do Claude</h3><div class="raw-response">{raw_response}</div></div>' if raw_response else ''}
            </div>
        </body>
        </html>
        '''

        return details_html

    except Exception as e:
        return f"Erro ao carregar detalhes: {e}", 500

@app.route('/download/<invoice_id>')
def download_file(invoice_id):
    """Download invoice file"""
    try:
        conn = sqlite3.connect(DB_PATH)
        invoice = conn.execute('SELECT file_path, source_file FROM invoices WHERE id = ?', (invoice_id,)).fetchone()
        conn.close()

        if not invoice:
            return "Invoice não encontrado", 404

        file_path, original_name = invoice
        if not Path(file_path).exists():
            return "Arquivo não encontrado", 404

        return send_from_directory(
            Path(file_path).parent,
            Path(file_path).name,
            as_attachment=True,
            download_name=original_name
        )

    except Exception as e:
        return f"Erro no download: {e}", 500

if __name__ == '__main__':
    init_db()
    print("Visual Enhanced Invoice System")
    print("   Features: Modern UI, Search & Filters, Archive Support")
    print("   Access: http://localhost:5005")

    app.run(host='0.0.0.0', port=5005, debug=True, use_reloader=False)