"""
Smart Document Ingestion System
Uses Claude API to analyze document structure and determine optimal processing approach
"""

import os
import pandas as pd
import json
from typing import Dict, Any, Optional, Tuple
import anthropic
from pathlib import Path

class SmartDocumentIngestion:
    def __init__(self):
        self.claude_client = self._init_claude_client()

    def _init_claude_client(self):
        """Initialize Claude API client"""
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                print("⚠️  No ANTHROPIC_API_KEY found - smart ingestion disabled")
                return None
            return anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            print(f"❌ Error initializing Claude API: {e}")
            return None

    def analyze_document_structure(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze document structure using Claude API
        Returns mapping instructions for processing
        """
        if not self.claude_client:
            return self._fallback_analysis(file_path)

        try:
            # Read sample of the document
            sample_content = self._get_document_sample(file_path)
            if not sample_content:
                return self._fallback_analysis(file_path)

            # Ask Claude to analyze the structure
            prompt = self._build_analysis_prompt(sample_content, file_path)
            response = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",  # Fast, cheap model for structure analysis
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse Claude's response
            analysis = self._parse_claude_response(response.content[0].text)
            analysis['claude_analysis'] = True
            analysis['cost_estimate'] = 0.02  # Approximate cost

            print(f"🤖 Claude analyzed document structure: {analysis.get('format', 'unknown')}")
            return analysis

        except Exception as e:
            print(f"❌ Claude analysis failed: {e}")
            return self._fallback_analysis(file_path)

    def _get_document_sample(self, file_path: str) -> Optional[str]:
        """Get sample content from document for analysis"""
        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext == '.csv':
                # Read first 10 lines of CSV
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = [f.readline().strip() for _ in range(10)]
                return '\n'.join(lines)

            elif file_ext in ['.xlsx', '.xls']:
                # Read first 10 rows of Excel
                df = pd.read_excel(file_path, nrows=10)
                return df.to_string()

            elif file_ext == '.pdf':
                # For PDFs, we'll need full Claude processing
                return f"PDF_FILE:{file_path}"

            else:
                # Try to read as text
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read(2000)  # First 2000 chars

        except Exception as e:
            print(f"❌ Error reading document sample: {e}")
            return None

    def _build_analysis_prompt(self, sample_content: str, file_path: str) -> str:
        """Build prompt for Claude to analyze document structure"""
        file_name = os.path.basename(file_path)

        return f"""
Analyze this financial document and determine how to process it for transaction extraction.

File: {file_name}
Content sample:
{sample_content}

Please respond with a JSON object containing:
{{
    "format": "chase_checking|chase_credit|bank_statement|pdf|excel|other",
    "date_column": "column_name_containing_dates",
    "description_column": "column_name_containing_descriptions",
    "amount_column": "column_name_containing_amounts",
    "special_handling": "misaligned_headers|standard|pdf_extraction|none",
    "confidence": 0.95,
    "processing_method": "python_pandas|claude_extraction",
    "notes": "Any special considerations"
}}

Focus on:
1. Identifying the correct column mapping for dates, descriptions, and amounts
2. Detecting if headers are misaligned with data
3. Determining if this needs special processing
4. Being very precise about column names

Only respond with the JSON object, no other text.
"""

    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's JSON response"""
        try:
            # Extract JSON from response
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            return json.loads(response_text)
        except Exception as e:
            print(f"❌ Error parsing Claude response: {e}")
            return self._default_structure()

    def _fallback_analysis(self, file_path: str) -> Dict[str, Any]:
        """Fallback analysis when Claude API is not available"""
        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext == '.csv':
                # Quick pandas analysis
                df = pd.read_csv(file_path, nrows=5)
                columns = list(df.columns)

                # Detect Chase formats
                if 'Details' in columns and 'Posting Date' in columns and 'Description' in columns:
                    return {
                        'format': 'chase_checking_misaligned',
                        'date_column': 'Details',
                        'description_column': 'Posting Date',
                        'amount_column': 'Description',
                        'special_handling': 'misaligned_headers',
                        'confidence': 0.9,
                        'processing_method': 'python_pandas',
                        'claude_analysis': False
                    }
                elif 'Transaction Date' in columns and 'Description' in columns and 'Amount' in columns:
                    return {
                        'format': 'chase_credit',
                        'date_column': 'Transaction Date',
                        'description_column': 'Description',
                        'amount_column': 'Amount',
                        'special_handling': 'standard',
                        'confidence': 0.9,
                        'processing_method': 'python_pandas',
                        'claude_analysis': False
                    }
                else:
                    # Standard detection
                    date_col = self._find_column(columns, ['date', 'time'])
                    desc_col = self._find_column(columns, ['description', 'desc', 'memo'])
                    amount_col = self._find_column(columns, ['amount', 'value', 'total'])

                    return {
                        'format': 'standard_csv',
                        'date_column': date_col or columns[0],
                        'description_column': desc_col or (columns[1] if len(columns) > 1 else columns[0]),
                        'amount_column': amount_col or (columns[2] if len(columns) > 2 else columns[0]),
                        'special_handling': 'standard',
                        'confidence': 0.7,
                        'processing_method': 'python_pandas',
                        'claude_analysis': False
                    }
            else:
                return self._default_structure()

        except Exception as e:
            print(f"❌ Fallback analysis failed: {e}")
            return self._default_structure()

    def _find_column(self, columns, keywords):
        """Find column matching keywords"""
        for col in columns:
            for keyword in keywords:
                if keyword.lower() in col.lower():
                    return col
        return None

    def _default_structure(self) -> Dict[str, Any]:
        """Default structure when analysis fails"""
        return {
            'format': 'unknown',
            'date_column': 'Date',
            'description_column': 'Description',
            'amount_column': 'Amount',
            'special_handling': 'none',
            'confidence': 0.1,
            'processing_method': 'python_pandas',
            'claude_analysis': False,
            'notes': 'Analysis failed - using defaults'
        }

    def process_with_structure_info(self, file_path: str, structure_info: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Process document using structure information"""
        try:
            if structure_info['processing_method'] == 'claude_extraction':
                return self._claude_extract_data(file_path)
            else:
                return self._python_process_with_mapping(file_path, structure_info)
        except Exception as e:
            print(f"❌ Processing failed: {e}")
            return None

    def _python_process_with_mapping(self, file_path: str, structure_info: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Process using Python with Claude's column mapping"""
        try:
            file_ext = Path(file_path).suffix.lower()

            # Read the file
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                print(f"❌ Unsupported file type for Python processing: {file_ext}")
                return None

            print(f"📊 Found {len(df)} transactions")
            print(f"🤖 Using Claude's mapping: Date={structure_info['date_column']}, "
                  f"Desc={structure_info['description_column']}, Amount={structure_info['amount_column']}")

            # Apply special handling
            if structure_info['special_handling'] == 'misaligned_headers':
                # Create standardized DataFrame for misaligned headers
                standardized_df = pd.DataFrame()
                standardized_df['Date'] = df[structure_info['date_column']]
                standardized_df['Description'] = df[structure_info['description_column']]
                standardized_df['Amount'] = df[structure_info['amount_column']]

                # Copy other columns
                for col in df.columns:
                    if col not in [structure_info['date_column'], structure_info['description_column'],
                                 structure_info['amount_column']] and col not in ['Date', 'Description', 'Amount']:
                        standardized_df[col] = df[col]

                df = standardized_df
                print("✅ Applied misaligned header correction")

            return df

        except Exception as e:
            print(f"❌ Python processing failed: {e}")
            return None

    def _claude_extract_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """Use Claude to extract data from complex documents (PDFs, etc.)"""
        if not self.claude_client:
            print("❌ Claude API not available for data extraction")
            return None

        try:
            # This would be for PDFs and complex documents
            # Implementation would involve sending document to Claude for full extraction
            print("🤖 Using Claude for full document extraction (not implemented yet)")
            return None

        except Exception as e:
            print(f"❌ Claude extraction failed: {e}")
            return None

# Integration function to replace existing column detection logic
def smart_process_file(file_path: str, enhance: bool = True) -> Optional[pd.DataFrame]:
    """
    Smart file processing using Claude API for structure analysis
    This replaces the manual column detection logic
    """
    ingestion = SmartDocumentIngestion()

    # Step 1: Analyze document structure
    print(f"🔍 Analyzing document structure: {os.path.basename(file_path)}")
    structure_info = ingestion.analyze_document_structure(file_path)

    # Step 2: Process using structure information
    df = ingestion.process_with_structure_info(file_path, structure_info)

    if df is not None:
        print(f"✅ Smart ingestion successful - {len(df)} transactions")
        print(f"📋 Confidence: {structure_info.get('confidence', 0):.1%}")

        # Return standardized column names
        return df
    else:
        print("❌ Smart ingestion failed")
        return None