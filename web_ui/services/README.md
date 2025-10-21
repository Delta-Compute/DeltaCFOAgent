# Web UI Services

This directory contains processing services for the DeltaCFOAgent web interface.

## Receipt Processor

The Receipt Processor service handles document processing for supporting financial documents like:
- Payment receipts (restaurant, retail, services)
- Mining pool payout sheets
- Cryptocurrency exchange confirmations
- Bank receipts and transfer confirmations
- Any supporting documentation for transactions

### Features

✅ **Multiple Format Support**
- PDF documents
- Images: PNG, JPG, JPEG, WebP, TIFF
- HEIC/HEIF (iPhone photos)

✅ **Claude Vision Integration**
- Intelligent data extraction
- Transaction matching hints
- Automatic categorization suggestions
- Confidence scoring

✅ **Comprehensive Validation**
- File size limits (25MB max)
- Format validation
- Data quality checks
- Error handling with detailed logging

✅ **Special Document Types**
- Mining pool payouts (extracts pool name, coin, hashrate, address)
- Crypto exchange documents (extracts exchange, addresses, network)
- Multi-item receipts (line item extraction)

### Usage

#### Basic Usage

```python
from web_ui.services import ReceiptProcessor

# Initialize processor
processor = ReceiptProcessor()

# Process a single receipt
result = processor.process_receipt('path/to/receipt.pdf')

# Check result
if result['status'] == 'success':
    print(f"Vendor: {result['vendor']}")
    print(f"Amount: {result['amount']} {result['currency']}")
    print(f"Date: {result['date']}")
    print(f"Confidence: {result['confidence']:.1%}")
```

#### Batch Processing

```python
# Process multiple receipts
file_paths = ['receipt1.pdf', 'receipt2.jpg', 'receipt3.png']
results = processor.batch_process_receipts(file_paths)

# Process results
for result in results:
    if result['status'] == 'success':
        print(f"Processed: {result['vendor']} - ${result['amount']}")
```

#### With Custom API Key

```python
processor = ReceiptProcessor(api_key='your-anthropic-api-key')
```

### Response Structure

The processor returns a structured dictionary with the following fields:

```python
{
    # Document metadata
    'document_type': 'payment_receipt',  # or 'mining_payout', 'crypto_exchange', etc.
    'source_file': 'receipt.pdf',
    'processed_at': '2025-10-21T12:00:00',

    # Core transaction data
    'date': '2025-10-21',
    'vendor': 'Example Store',
    'amount': 123.45,
    'currency': 'USD',
    'payment_method': 'credit_card',

    # Matching hints (for transaction linking)
    'description': 'Purchase at Example Store',
    'location': 'New York, NY',
    'reference_number': 'RCP-12345',
    'card_last_4': '1234',
    'amount_range': None,  # or [min, max] if amount unclear

    # Line items (if available)
    'line_items': [
        {'item': 'Product A', 'quantity': 2, 'price': 50.00, 'total': 100.00},
        {'item': 'Product B', 'quantity': 1, 'price': 23.45, 'total': 23.45}
    ],

    # Categorization suggestions
    'suggested_category': 'Technology Expenses',
    'suggested_business_unit': 'Delta LLC',
    'tags': ['hardware', 'equipment'],

    # Special data (for mining/crypto receipts)
    'mining_data': None,  # or {'pool': 'F2Pool', 'coin': 'BTC', ...}
    'crypto_data': None,  # or {'exchange': 'Binance', 'type': 'withdrawal', ...}

    # Quality metrics
    'confidence': 0.95,  # 0.0 to 1.0
    'quality': 'clear',  # 'clear', 'partial', 'unclear', 'error'
    'processing_notes': 'Successfully extracted all fields',

    # Processing metadata
    'extraction_method': 'claude_vision',
    'model': 'claude-3-haiku-20240307',
    'status': 'success'  # or 'error'
}
```

### Configuration

The processor uses the `ReceiptProcessingConfig` class for configuration:

```python
from web_ui.services import ReceiptProcessingConfig

config = ReceiptProcessingConfig()

# Adjust settings
config.MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
config.PDF_DPI = 400  # Higher DPI for better quality
```

### Environment Variables

Required:
- `ANTHROPIC_API_KEY` - Your Anthropic API key for Claude Vision

### Testing

Run the test suite:

```bash
# Run all tests
python web_ui/test_receipt_processor.py

# Test with a specific file
python web_ui/test_receipt_processor.py --test-file path/to/receipt.pdf

# Verbose output
python web_ui/test_receipt_processor.py --verbose
```

### Dependencies

The receipt processor requires:
- `anthropic>=0.8.0` - Claude AI API
- `Pillow>=10.0.0` - Image processing
- `pdf2image>=1.16.0` - PDF to image conversion
- `pillow-heif>=0.13.0` - HEIC format support

Install with:
```bash
pip install anthropic Pillow pdf2image pillow-heif
```

### Error Handling

The processor handles errors gracefully and returns error responses:

```python
result = processor.process_receipt('invalid_file.pdf')

if result['status'] == 'error':
    print(f"Error: {result['error_message']}")
    print(f"Notes: {result['processing_notes']}")
```

Common errors:
- `FileNotFoundError` - Receipt file not found
- `ValueError` - Invalid file format, size, or processing error
- API errors are caught and returned in the error response

### Logging

The processor uses Python's standard logging:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or configure specific logger
logger = logging.getLogger('web_ui.services.receipt_processor')
logger.setLevel(logging.INFO)
```

### Next Steps

For integration into the web application:
1. Create upload endpoint: `POST /api/receipts/upload`
2. Implement transaction matching logic
3. Build frontend UI for receipt upload and review
4. Set up Cloud Storage for receipt files
5. Create database tables for receipt metadata

See the main project documentation for the complete Receipt Upload feature implementation plan.
