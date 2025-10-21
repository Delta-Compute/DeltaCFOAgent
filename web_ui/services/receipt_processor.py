#!/usr/bin/env python3
"""
Receipt Processing Service - Claude Vision for Supporting Documents
Processes payment receipts, mining pool payout sheets, and other supporting documentation
"""

import base64
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import anthropic

# Configure logging
logger = logging.getLogger(__name__)


class ReceiptProcessingConfig:
    """Configuration for receipt processing"""

    # File size limits (larger than invoices to support high-res photos)
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

    # Supported file formats
    ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.heic', '.webp', '.tiff', '.tif'}

    # Image formats that need conversion to PNG for Claude
    IMAGE_FORMATS = {'.png', '.jpg', '.jpeg', '.webp', '.tiff', '.tif'}

    # Formats that need special handling
    HEIC_FORMAT = {'.heic'}
    PDF_FORMAT = {'.pdf'}

    # Claude API settings
    CLAUDE_MODEL = 'claude-3-haiku-20240307'  # Fast, cost-effective for receipt processing
    CLAUDE_MAX_TOKENS = 4000
    CLAUDE_TEMPERATURE = 0.1  # Low temperature for accurate data extraction

    # Validation limits
    MAX_AMOUNT = 10000000  # $10M max (for large mining payouts)
    MIN_AMOUNT = 0.001  # Support small crypto amounts
    DATE_RANGE_DAYS = 730  # 2 years back

    # PDF processing
    PDF_DPI = 300  # High DPI for clear text extraction
    PDF_MAX_PAGES = 5  # Process up to 5 pages


class ReceiptProcessor:
    """Service for processing receipt documents with Claude Vision"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the receipt processor

        Args:
            api_key: Anthropic API key (defaults to environment variable)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set for receipt processing")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.config = ReceiptProcessingConfig()

        logger.info("ReceiptProcessor initialized successfully")

    def process_receipt(self, file_path: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Process a receipt file and extract structured data

        Args:
            file_path: Path to the receipt file
            filename: Optional original filename (for logging/display)

        Returns:
            Dict containing extracted receipt data and transaction matching hints
        """
        try:
            logger.info(f"Processing receipt: {filename or file_path}")

            # Validate file
            self._validate_file(file_path)

            # Convert to base64 image
            image_data, media_type = self._prepare_image(file_path)

            # Extract data with Claude Vision
            extracted_data = self._extract_receipt_data(image_data, media_type, filename or os.path.basename(file_path))

            # Validate and structure response
            structured_data = self._validate_and_structure(extracted_data, file_path)

            logger.info(f"✅ Receipt processed successfully: {structured_data.get('vendor', 'Unknown')}")
            return structured_data

        except Exception as e:
            logger.error(f"❌ Receipt processing failed: {e}", exc_info=True)
            return self._create_error_response(str(e), file_path)

    def _validate_file(self, file_path: str) -> None:
        """Validate file exists, size, and format

        Args:
            file_path: Path to file to validate

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is invalid (size, format)
        """
        # Check existence
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Receipt file not found: {file_path}")

        # Check size
        file_size = os.path.getsize(file_path)
        if file_size > self.config.MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            raise ValueError(f"File too large: {size_mb:.1f}MB (max: {self.config.MAX_FILE_SIZE / (1024 * 1024)}MB)")

        if file_size == 0:
            raise ValueError("File is empty")

        # Check format
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in self.config.ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {file_ext}. Allowed: {', '.join(self.config.ALLOWED_EXTENSIONS)}")

        logger.info(f"File validation passed: {os.path.basename(file_path)} ({file_size} bytes)")

    def _prepare_image(self, file_path: str) -> Tuple[str, str]:
        """Convert file to base64 image for Claude Vision

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (base64_data, media_type)
        """
        file_ext = Path(file_path).suffix.lower()

        try:
            if file_ext in self.config.PDF_FORMAT:
                return self._pdf_to_base64(file_path)
            elif file_ext in self.config.HEIC_FORMAT:
                return self._heic_to_base64(file_path)
            elif file_ext in self.config.IMAGE_FORMATS:
                return self._image_to_base64(file_path)
            else:
                raise ValueError(f"Unsupported format: {file_ext}")

        except Exception as e:
            logger.error(f"Image preparation failed: {e}")
            raise ValueError(f"Failed to prepare image: {e}")

    def _pdf_to_base64(self, pdf_path: str) -> Tuple[str, str]:
        """Convert PDF to base64 PNG image (first page)

        Args:
            pdf_path: Path to PDF file

        Returns:
            Tuple of (base64_data, media_type)
        """
        try:
            from pdf2image import convert_from_path
            from io import BytesIO
            from PIL import Image

            logger.info(f"Converting PDF to image: {os.path.basename(pdf_path)}")

            # Convert first page to image at high DPI
            pages = convert_from_path(
                pdf_path,
                dpi=self.config.PDF_DPI,
                first_page=1,
                last_page=1
            )

            if not pages:
                raise ValueError("PDF conversion produced no images")

            # Convert to PNG bytes
            img = pages[0]
            buffer = BytesIO()
            img.save(buffer, format='PNG', optimize=True)
            image_bytes = buffer.getvalue()

            # Encode to base64
            base64_data = base64.b64encode(image_bytes).decode('utf-8')

            logger.info(f"PDF converted successfully: {len(base64_data)} bytes")
            return base64_data, 'image/png'

        except ImportError:
            raise ValueError("PDF processing requires: pip install pdf2image Pillow poppler-utils")
        except Exception as e:
            raise ValueError(f"PDF conversion failed: {e}")

    def _heic_to_base64(self, heic_path: str) -> Tuple[str, str]:
        """Convert HEIC (iPhone photo format) to base64 PNG

        Args:
            heic_path: Path to HEIC file

        Returns:
            Tuple of (base64_data, media_type)
        """
        try:
            from PIL import Image
            from io import BytesIO
            import pillow_heif

            logger.info(f"Converting HEIC to PNG: {os.path.basename(heic_path)}")

            # Register HEIF opener
            pillow_heif.register_heif_opener()

            # Open and convert
            img = Image.open(heic_path)

            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Save as PNG
            buffer = BytesIO()
            img.save(buffer, format='PNG', optimize=True)
            image_bytes = buffer.getvalue()

            # Encode to base64
            base64_data = base64.b64encode(image_bytes).decode('utf-8')

            logger.info(f"HEIC converted successfully: {len(base64_data)} bytes")
            return base64_data, 'image/png'

        except ImportError:
            raise ValueError("HEIC processing requires: pip install pillow-heif")
        except Exception as e:
            raise ValueError(f"HEIC conversion failed: {e}")

    def _image_to_base64(self, image_path: str) -> Tuple[str, str]:
        """Encode image file to base64

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (base64_data, media_type)
        """
        try:
            file_ext = Path(image_path).suffix.lower()

            # Determine media type
            media_type_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.webp': 'image/webp',
                '.tiff': 'image/tiff',
                '.tif': 'image/tiff'
            }
            media_type = media_type_map.get(file_ext, 'image/png')

            # Read and encode
            with open(image_path, 'rb') as f:
                image_bytes = f.read()

            base64_data = base64.b64encode(image_bytes).decode('utf-8')

            logger.info(f"Image encoded successfully: {len(base64_data)} bytes, type: {media_type}")
            return base64_data, media_type

        except Exception as e:
            raise ValueError(f"Image encoding failed: {e}")

    def _extract_receipt_data(self, image_base64: str, media_type: str, filename: str) -> Dict[str, Any]:
        """Call Claude Vision API to extract receipt data

        Args:
            image_base64: Base64 encoded image
            media_type: MIME type of the image
            filename: Original filename for context

        Returns:
            Extracted receipt data as dictionary
        """
        try:
            prompt = self._build_receipt_prompt(filename)

            logger.info(f"Calling Claude Vision API for receipt analysis...")

            response = self.client.messages.create(
                model=self.config.CLAUDE_MODEL,
                max_tokens=self.config.CLAUDE_MAX_TOKENS,
                temperature=self.config.CLAUDE_TEMPERATURE,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            # Parse JSON response
            response_text = response.content[0].text.strip()

            # Extract JSON from response
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)

            logger.info(f"Claude Vision extraction successful")
            return extracted_data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Claude: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            raise ValueError(f"Claude returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Claude Vision API call failed: {e}")
            raise ValueError(f"Receipt extraction failed: {e}")

    def _build_receipt_prompt(self, filename: str) -> str:
        """Build Claude prompt for receipt analysis

        Args:
            filename: Original filename for context

        Returns:
            Formatted prompt string
        """
        return f"""
You are analyzing a RECEIPT or SUPPORTING DOCUMENT (not an invoice) for a financial transaction categorization system.

File: {filename}

This could be:
- Payment receipt (restaurant, retail, service)
- ATM receipt or deposit slip
- Cryptocurrency mining pool payout sheet
- Exchange withdrawal/deposit confirmation
- Bank transfer receipt
- Any document that supports a financial transaction

EXTRACT THE FOLLOWING DATA:

**DOCUMENT TYPE:**
Identify the type: "payment_receipt", "mining_payout", "crypto_exchange", "bank_receipt", "transfer_receipt", "other"

**CORE TRANSACTION DATA:**
- date: Transaction date (YYYY-MM-DD format) - CRITICAL for matching
- vendor: Merchant/vendor/sender name
- amount: Transaction amount (numeric only)
- currency: Currency code (USD, BTC, TAO, BRL, etc.)
- payment_method: How paid (cash, card, crypto, wire, etc.)

**TRANSACTION MATCHING HINTS:**
Help match this receipt to existing transactions by extracting:
- description: Natural description of what this is for
- location: Store location, city, or address if present
- reference_number: Receipt #, transaction ID, hash, confirmation code
- card_last_4: Last 4 digits of card if visible
- amount_range: If amount unclear, provide [min, max] range

**DETAILED LINE ITEMS (if present):**
- line_items: Array of items purchased/services with quantities and prices

**CATEGORIZATION HINTS:**
Based on the content, suggest:
- category: One of ["Technology Expenses", "Utilities", "Mining Operations", "Professional Services", "Office Expenses", "Travel & Entertainment", "Other"]
- business_unit: One of ["Delta LLC", "Delta Prop Shop LLC", "Delta Mining Paraguay S.A.", "MMIW LLC", "DM Mining LLC", "Personal", "Unknown"]
- tags: Relevant tags (e.g., ["crypto", "hardware", "recurring", "travel"])

**SPECIAL HANDLING:**
For mining pool payouts:
- Extract: pool name, coin type, hashrate if shown, payout address
- mining_data: {{"pool": "...", "coin": "...", "hashrate": "...", "address": "..."}}

For crypto exchanges:
- Extract: exchange name, transaction type (deposit/withdrawal), wallet addresses, network
- crypto_data: {{"exchange": "...", "type": "...", "from_address": "...", "to_address": "...", "network": "..."}}

**CONFIDENCE & QUALITY:**
- confidence: Float 0.0-1.0 (how confident are you in the extraction?)
- quality: "clear", "partial", "unclear" (receipt readability)
- processing_notes: Any issues, ambiguities, or important observations

Return ONLY valid JSON with this structure:
{{
    "document_type": "payment_receipt",
    "date": "YYYY-MM-DD",
    "vendor": "Merchant Name",
    "amount": 123.45,
    "currency": "USD",
    "payment_method": "credit_card",

    "description": "Natural description of transaction",
    "location": "Store location or city",
    "reference_number": "Receipt/confirmation number",
    "card_last_4": "1234",
    "amount_range": null,

    "line_items": [
        {{"item": "Product/service", "quantity": 1, "price": 10.00, "total": 10.00}}
    ],

    "category": "Technology Expenses",
    "business_unit": "Delta LLC",
    "tags": ["tag1", "tag2"],

    "mining_data": null,
    "crypto_data": null,

    "confidence": 0.95,
    "quality": "clear",
    "processing_notes": "Any observations or issues"
}}

CRITICAL RULES:
1. Be precise with dates and amounts - these are used for transaction matching
2. If data is unclear or missing, use null (not empty string or 0)
3. Extract ALL visible text that could help match to a transaction
4. For mining payouts or crypto docs, extract addresses and transaction hashes
5. Confidence should reflect actual clarity of the document

Return ONLY the JSON object, no other text.
"""

    def _validate_and_structure(self, raw_data: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Validate and structure extracted receipt data

        Args:
            raw_data: Raw data from Claude
            file_path: Original file path

        Returns:
            Validated and structured receipt data
        """
        try:
            # Validate critical fields
            if not raw_data.get('date'):
                logger.warning("Missing date in receipt")

            if not raw_data.get('amount'):
                logger.warning("Missing amount in receipt")

            # Structure the response
            structured = {
                # Document metadata
                'document_type': raw_data.get('document_type', 'payment_receipt'),
                'source_file': os.path.basename(file_path),
                'processed_at': datetime.now().isoformat(),

                # Core transaction data
                'date': raw_data.get('date'),
                'vendor': raw_data.get('vendor', ''),
                'amount': float(raw_data.get('amount', 0)) if raw_data.get('amount') else None,
                'currency': raw_data.get('currency', 'USD'),
                'payment_method': raw_data.get('payment_method'),

                # Matching hints
                'description': raw_data.get('description', ''),
                'location': raw_data.get('location'),
                'reference_number': raw_data.get('reference_number'),
                'card_last_4': raw_data.get('card_last_4'),
                'amount_range': raw_data.get('amount_range'),

                # Line items
                'line_items': raw_data.get('line_items', []),

                # Categorization suggestions
                'suggested_category': raw_data.get('category'),
                'suggested_business_unit': raw_data.get('business_unit'),
                'tags': raw_data.get('tags', []),

                # Special data
                'mining_data': raw_data.get('mining_data'),
                'crypto_data': raw_data.get('crypto_data'),

                # Quality metrics
                'confidence': float(raw_data.get('confidence', 0.5)),
                'quality': raw_data.get('quality', 'unknown'),
                'processing_notes': raw_data.get('processing_notes', ''),

                # Processing metadata
                'extraction_method': 'claude_vision',
                'model': self.config.CLAUDE_MODEL,
                'status': 'success'
            }

            # Validate amount if present
            if structured['amount'] is not None:
                if structured['amount'] > self.config.MAX_AMOUNT:
                    logger.warning(f"Amount exceeds maximum: {structured['amount']}")
                elif structured['amount'] < self.config.MIN_AMOUNT:
                    logger.warning(f"Amount below minimum: {structured['amount']}")

            return structured

        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return self._create_error_response(f"Validation error: {e}", file_path)

    def _create_error_response(self, error_message: str, file_path: str) -> Dict[str, Any]:
        """Create standardized error response

        Args:
            error_message: Error description
            file_path: Original file path

        Returns:
            Error response dictionary
        """
        return {
            'document_type': 'error',
            'source_file': os.path.basename(file_path),
            'processed_at': datetime.now().isoformat(),
            'date': None,
            'vendor': 'ERROR',
            'amount': None,
            'currency': 'USD',
            'description': f'Processing failed: {error_message}',
            'confidence': 0.0,
            'quality': 'error',
            'processing_notes': error_message,
            'status': 'error',
            'error_message': error_message
        }

    def batch_process_receipts(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Process multiple receipts in batch

        Args:
            file_paths: List of file paths to process

        Returns:
            List of processing results
        """
        results = []

        logger.info(f"Starting batch processing of {len(file_paths)} receipts")

        for i, file_path in enumerate(file_paths, 1):
            logger.info(f"Processing receipt {i}/{len(file_paths)}")

            try:
                result = self.process_receipt(file_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                results.append(self._create_error_response(str(e), file_path))

        success_count = sum(1 for r in results if r.get('status') == 'success')
        logger.info(f"Batch processing complete: {success_count}/{len(file_paths)} successful")

        return results


def test_receipt_processor():
    """Test the receipt processor with sample files"""
    try:
        processor = ReceiptProcessor()
        logger.info("✅ ReceiptProcessor initialized")

        # Test files to look for
        test_files = [
            "test_receipt.pdf",
            "sample_receipt.png",
            "test_data/receipt_sample.jpg"
        ]

        for test_file in test_files:
            if os.path.exists(test_file):
                logger.info(f"Testing with: {test_file}")
                result = processor.process_receipt(test_file)

                logger.info(f"📊 EXTRACTION RESULTS:")
                logger.info(f"  Type: {result.get('document_type')}")
                logger.info(f"  Vendor: {result.get('vendor')}")
                logger.info(f"  Amount: {result.get('amount')} {result.get('currency')}")
                logger.info(f"  Date: {result.get('date')}")
                logger.info(f"  Confidence: {result.get('confidence', 0):.1%}")

                return result

        logger.info("ℹ️  No test files found. Add a test receipt to test extraction.")
        return {'status': 'no_test_files'}

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return {'error': str(e)}


if __name__ == "__main__":
    # Configure logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    test_receipt_processor()
