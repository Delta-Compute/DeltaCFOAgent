"""
Payment Proof Processor - Extract payment data from receipts using Claude Vision
Processes receipts in PDF, image, Excel, and CSV formats
"""

import base64
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import anthropic
from dateutil import parser as date_parser


class PaymentProofProcessor:
    """Process payment receipts and extract structured payment data"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Claude API key"""
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Claude API key not configured. Set ANTHROPIC_API_KEY environment variable.")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-haiku-20240307"  # Fast, cost-effective model for receipt extraction
        self.max_file_size = 50 * 1024 * 1024  # 50MB

    @staticmethod
    def normalize_decimal_number(value: Any) -> float:
        """
        Normalize decimal numbers that may use comma or dot as decimal separator
        Handles formats like:
        - US/UK: 1,000.50 (comma thousands, dot decimal)
        - BR/EU: 1.000,50 (dot thousands, comma decimal)
        - No separator: 1000.50 or 1000,50

        Args:
            value: String, int, or float number

        Returns:
            float: Normalized number with dot as decimal separator
        """
        if isinstance(value, (int, float)):
            return float(value)

        if not isinstance(value, str):
            return 0.0

        # Remove spaces and currency symbols
        value = value.strip().replace(' ', '').replace('$', '').replace('€', '').replace('R$', '').replace('£', '')

        if not value:
            return 0.0

        # Count dots and commas to determine format
        dot_count = value.count('.')
        comma_count = value.count(',')

        try:
            # No separators - simple number
            if dot_count == 0 and comma_count == 0:
                return float(value)

            # Only dots - could be thousands OR decimal
            if comma_count == 0:
                # If multiple dots, they're thousands separators (EU format without decimals)
                if dot_count > 1:
                    value = value.replace('.', '')
                    return float(value)
                # Single dot - could be thousands or decimal
                # If exactly 3 digits after dot, likely thousands separator
                parts = value.split('.')
                if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
                    # Likely thousands: 1.000 -> 1000
                    value = value.replace('.', '')
                    return float(value)
                # Otherwise it's a decimal separator
                return float(value)

            # Only commas - could be thousands OR decimal
            if dot_count == 0:
                # If multiple commas, they're thousands separators (US format without decimals)
                if comma_count > 1:
                    value = value.replace(',', '')
                    return float(value)
                # Single comma - could be thousands or decimal (BR/EU format)
                # If exactly 3 digits after comma, likely thousands separator
                parts = value.split(',')
                if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
                    # Likely thousands: 1,000 -> 1000
                    value = value.replace(',', '')
                    return float(value)
                # Otherwise it's a decimal separator (BR/EU format)
                value = value.replace(',', '.')
                return float(value)

            # Both dots and commas present
            # Determine which is the decimal separator (appears last)
            last_dot_pos = value.rfind('.')
            last_comma_pos = value.rfind(',')

            if last_comma_pos > last_dot_pos:
                # Comma is decimal separator (BR/EU format): 1.000,50
                value = value.replace('.', '').replace(',', '.')
            else:
                # Dot is decimal separator (US/UK format): 1,000.50
                value = value.replace(',', '')

            return float(value)

        except (ValueError, AttributeError):
            print(f"WARNING: Could not parse number: {value}")
            return 0.0

    def process_payment_proof(self, file_path: str, invoice_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extract payment data from receipt file

        Args:
            file_path: Path to receipt file (PDF, image, Excel, CSV)
            invoice_data: Optional invoice data for validation

        Returns:
            Dict with extracted payment data:
            {
                'success': bool,
                'payment_date': str (ISO format),
                'payment_amount': float,
                'payment_currency': str,
                'payment_method': str,
                'confirmation_number': str,
                'payer_name': str,
                'receiver_name': str,
                'confidence': float (0-1),
                'discrepancies': list of str,
                'raw_text': str
            }
        """
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                return self._error_response(f"File not found: {file_path}")

            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return self._error_response(f"File too large: {file_size} bytes (max: {self.max_file_size})")

            file_ext = Path(file_path).suffix.lower()
            print(f"[Payment Proof] Processing: {os.path.basename(file_path)} ({file_size} bytes, {file_ext})")

            # Route to appropriate processor
            if file_ext in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff']:
                extracted_data = self._process_visual_receipt(file_path, file_ext)
            elif file_ext in ['.csv', '.xls', '.xlsx']:
                extracted_data = self._process_tabular_receipt(file_path, file_ext)
            else:
                return self._error_response(f"Unsupported file type: {file_ext}")

            # Validate against invoice if provided
            if invoice_data and extracted_data.get('success'):
                extracted_data['discrepancies'] = self._validate_against_invoice(
                    extracted_data, invoice_data
                )

            print(f"[Payment Proof] Extraction complete - Confidence: {extracted_data.get('confidence', 0):.2f}")
            return extracted_data

        except Exception as e:
            print(f"[Payment Proof] ERROR: {e}")
            import traceback
            traceback.print_exc()
            return self._error_response(str(e))

    def _process_visual_receipt(self, file_path: str, file_ext: str) -> Dict[str, Any]:
        """Process PDF or image receipt with Claude Vision"""
        try:
            # Convert to base64
            if file_ext == '.pdf':
                image_data = self._pdf_to_image_base64(file_path)
                media_type = "image/png"
            elif file_ext in ['.png']:
                image_data = self._encode_image_to_base64(file_path)
                media_type = "image/png"
            elif file_ext in ['.jpg', '.jpeg']:
                image_data = self._encode_image_to_base64(file_path)
                media_type = "image/jpeg"
            else:  # .tiff
                image_data = self._encode_image_to_base64(file_path)
                media_type = "image/tiff"

            # Call Claude Vision
            return self._call_claude_vision(image_data, media_type)

        except Exception as e:
            return self._error_response(f"Visual processing failed: {e}")

    def _process_tabular_receipt(self, file_path: str, file_ext: str) -> Dict[str, Any]:
        """Process Excel or CSV receipt by extracting text and using Claude"""
        try:
            import pandas as pd

            # Read file
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            else:  # .xls or .xlsx
                df = pd.read_excel(file_path)

            # Convert to text representation
            text_content = f"File: {os.path.basename(file_path)}\n\n"
            text_content += df.to_string(index=False)

            # Use Claude to extract payment data from text
            return self._call_claude_text_analysis(text_content)

        except Exception as e:
            return self._error_response(f"Tabular processing failed: {e}")

    def _pdf_to_image_base64(self, pdf_path: str) -> str:
        """Convert PDF first page to base64 PNG"""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            page = doc[0]

            # Render at high DPI
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))

            # Convert to PNG bytes
            png_bytes = pix.tobytes("png")

            doc.close()

            return base64.b64encode(png_bytes).decode('utf-8')

        except ImportError:
            raise ValueError("PDF processing requires: pip install PyMuPDF")
        except Exception as e:
            raise ValueError(f"PDF conversion failed: {e}")

    def _encode_image_to_base64(self, image_path: str) -> str:
        """Encode image file to base64"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _call_claude_vision(self, image_base64: str, media_type: str) -> Dict[str, Any]:
        """Call Claude Vision API to extract payment data from image"""
        try:
            prompt = """You are a payment receipt analyzer. Extract the following information from this payment receipt/proof:

1. **Payment Date**: When was the payment made (ISO format YYYY-MM-DD)
2. **Payment Amount**: The total amount paid (numeric value)
3. **Currency**: Currency code (USD, BRL, PYG, EUR, etc.)
4. **Payment Method**: How was it paid (PIX, Bank Transfer, Credit Card, Crypto, Cash, etc.)
5. **Confirmation Number**: Transaction ID, confirmation code, or reference number
6. **Payer Name**: Who made the payment (person/company)
7. **Receiver Name**: Who received the payment (person/company)
8. **Bank/Platform**: Name of bank or payment platform

Return a JSON object with this structure:
{
    "payment_date": "YYYY-MM-DD",
    "payment_amount": 0.0,
    "payment_currency": "USD",
    "payment_method": "PIX",
    "confirmation_number": "ABC123",
    "payer_name": "Company Name",
    "receiver_name": "Receiver Name",
    "bank_platform": "Bank Name",
    "confidence": 0.95,
    "raw_text": "All visible text from the receipt"
}

If you cannot find a field, use null. Estimate confidence 0-1 based on image quality and data completeness."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }],
            )

            # Parse response
            response_text = response.content[0].text

            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                extracted_data = json.loads(json_str)

                # Normalize payment_amount to handle comma/dot decimal separators
                if 'payment_amount' in extracted_data:
                    extracted_data['payment_amount'] = self.normalize_decimal_number(extracted_data['payment_amount'])

                extracted_data['success'] = True
                extracted_data['discrepancies'] = []
                return extracted_data
            else:
                return self._error_response("Could not extract JSON from Claude response")

        except Exception as e:
            return self._error_response(f"Claude Vision call failed: {e}")

    def _call_claude_text_analysis(self, text_content: str) -> Dict[str, Any]:
        """Call Claude to extract payment data from text (CSV/Excel)"""
        try:
            prompt = f"""You are a payment receipt analyzer. Extract payment information from this tabular data:

{text_content}

Return a JSON object with this structure:
{{
    "payment_date": "YYYY-MM-DD",
    "payment_amount": 0.0,
    "payment_currency": "USD",
    "payment_method": "Bank Transfer",
    "confirmation_number": "ABC123",
    "payer_name": "Company Name",
    "receiver_name": "Receiver Name",
    "bank_platform": "Bank Name",
    "confidence": 0.95,
    "raw_text": "Key text from the data"
}}

If you cannot find a field, use null. Estimate confidence 0-1 based on data completeness."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
            )

            response_text = response.content[0].text

            # Extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                extracted_data = json.loads(json_str)

                # Normalize payment_amount to handle comma/dot decimal separators
                if 'payment_amount' in extracted_data:
                    extracted_data['payment_amount'] = self.normalize_decimal_number(extracted_data['payment_amount'])

                extracted_data['success'] = True
                extracted_data['discrepancies'] = []
                return extracted_data
            else:
                return self._error_response("Could not extract JSON from Claude response")

        except Exception as e:
            return self._error_response(f"Claude text analysis failed: {e}")

    def _validate_against_invoice(self, payment_data: Dict, invoice_data: Dict) -> list:
        """
        Validate extracted payment data against invoice

        Returns list of discrepancy messages
        """
        discrepancies = []

        # Check amount
        invoice_amount = invoice_data.get('total_amount', 0)
        payment_amount = payment_data.get('payment_amount', 0)

        if invoice_amount and payment_amount:
            # Convert to float to handle Decimal from database
            invoice_amount = float(invoice_amount)
            payment_amount = float(payment_amount)
            diff_pct = abs(invoice_amount - payment_amount) / invoice_amount * 100
            if diff_pct > 2.0:  # More than 2% difference
                discrepancies.append(
                    f"Amount mismatch: Invoice ${invoice_amount:.2f} vs Payment ${payment_amount:.2f} ({diff_pct:.1f}% difference)"
                )

        # Check currency
        invoice_currency = invoice_data.get('currency', 'USD')
        payment_currency = payment_data.get('payment_currency', 'USD')

        if invoice_currency and payment_currency and invoice_currency != payment_currency:
            discrepancies.append(
                f"Currency mismatch: Invoice {invoice_currency} vs Payment {payment_currency}"
            )

        # Check date
        invoice_date_str = invoice_data.get('date')
        payment_date_str = payment_data.get('payment_date')

        if invoice_date_str and payment_date_str:
            try:
                invoice_date = date_parser.parse(invoice_date_str)
                payment_date = date_parser.parse(payment_date_str)

                if payment_date < invoice_date:
                    discrepancies.append(
                        f"Payment date ({payment_date_str}) is before invoice date ({invoice_date_str})"
                    )
            except Exception as e:
                discrepancies.append(f"Date validation error: {e}")

        return discrepancies

    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            'success': False,
            'error': error_message,
            'payment_date': None,
            'payment_amount': None,
            'payment_currency': None,
            'payment_method': None,
            'confirmation_number': None,
            'payer_name': None,
            'receiver_name': None,
            'bank_platform': None,
            'confidence': 0.0,
            'discrepancies': [error_message],
            'raw_text': ''
        }


def store_payment_proof(file_path: str, invoice_id: str, tenant_id: str) -> str:
    """
    Store payment proof file in organized structure

    Args:
        file_path: Path to uploaded file
        invoice_id: Invoice ID
        tenant_id: Tenant ID

    Returns:
        Stored file path relative to web_ui/
    """
    try:
        # Create directory structure: uploads/payment_proofs/{tenant_id}/{invoice_id}/
        base_dir = Path(__file__).parent.parent / 'uploads' / 'payment_proofs' / tenant_id / invoice_id
        base_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename with timestamp
        original_filename = Path(file_path).name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_ext = Path(file_path).suffix
        new_filename = f"receipt_{timestamp}{file_ext}"

        # Copy file
        dest_path = base_dir / new_filename

        import shutil
        shutil.copy2(file_path, dest_path)

        # Return relative path from web_ui/
        relative_path = f"uploads/payment_proofs/{tenant_id}/{invoice_id}/{new_filename}"

        print(f"[Payment Proof] Stored: {relative_path}")
        return relative_path

    except Exception as e:
        print(f"[Payment Proof] Storage error: {e}")
        raise
