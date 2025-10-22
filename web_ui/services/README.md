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

---

## Receipt Matcher

The Receipt Matcher service provides intelligent transaction matching algorithms to link receipts to existing transactions in the database.

### Features

✅ **Multiple Matching Strategies**
- Exact amount + exact date matching (95%+ confidence)
- Fuzzy amount matching (±5% tolerance)
- Date range matching (±3 days)
- Vendor name similarity (fuzzy string matching)
- Description similarity matching
- Reference number exact matching
- Card last 4 digits matching

✅ **Intelligent Confidence Scoring**
- Weighted confidence algorithm
- Multiple strategy combination
- Recommendation levels (auto_apply, suggested, possible, uncertain)
- Configurable confidence thresholds

✅ **Database Integration**
- PostgreSQL connection pooling
- Optimized candidate transaction queries
- Date and amount range filtering
- Error handling with retry logic

✅ **Flexible Configuration**
- Date range: ±3 days (configurable)
- Amount fuzzy match: ±5% (configurable)
- Vendor similarity threshold: 60%
- Minimum confidence: 40%
- Max results returned: 10

### Usage

#### Basic Matching

```python
from web_ui.services import ReceiptMatcher

# Initialize matcher
matcher = ReceiptMatcher()

# Receipt data from ReceiptProcessor
receipt_data = {
    'date': '2025-10-21',
    'vendor': 'Amazon',
    'amount': 99.99,
    'currency': 'USD',
    'description': 'Purchase at Amazon.com',
    'reference_number': 'AMZ-123456'
}

# Find matching transactions
matches = matcher.find_matches(receipt_data)

# Process results
for match in matches:
    match_info = match.to_dict()
    print(f"Transaction #{match_info['transaction_id']}")
    print(f"Confidence: {match_info['confidence']:.1%}")
    print(f"Recommendation: {match_info['recommendation']}")
    print(f"Strategies: {match_info['matching_strategies']}")
```

#### With Custom Configuration

```python
matcher = ReceiptMatcher()

# Customize matching parameters
matcher.config['date_range_days'] = 5  # ±5 days instead of ±3
matcher.config['amount_fuzzy_percent'] = 10  # ±10% instead of ±5%
matcher.config['min_confidence_threshold'] = 0.6  # Higher threshold

matches = matcher.find_matches(receipt_data, limit=5)
```

#### Handling Match Results

```python
matches = matcher.find_matches(receipt_data)

if matches:
    top_match = matches[0].to_dict()

    if top_match['recommendation'] == 'auto_apply':
        # Very high confidence (95%+) - can auto-link
        link_receipt_to_transaction(
            receipt_id,
            top_match['transaction_id']
        )
    elif top_match['recommendation'] == 'suggested':
        # High confidence (80-95%) - show to user for approval
        show_suggested_match_modal(top_match)
    elif top_match['recommendation'] == 'possible':
        # Medium confidence (60-80%) - show as option
        show_possible_matches(matches)
    else:
        # Low confidence (<60%) - show but mark uncertain
        show_uncertain_matches(matches)
else:
    # No matches found - suggest creating new transaction
    suggestion = matcher.suggest_new_transaction(receipt_data)
    show_create_transaction_modal(suggestion)
```

### Matching Strategies

The matcher uses multiple strategies and combines them for overall confidence:

#### 1. Reference Number Match
- **Confidence:** 99%
- **Logic:** Exact match after normalization (removes spaces, dashes, special chars)
- **Example:** `INV-123` matches `inv123`

#### 2. Card Last 4 Match
- **Confidence:** 85%
- **Logic:** Card last 4 digits found in transaction identifier
- **Example:** `1234` matches transaction with identifier containing `1234`

#### 3. Exact Amount + Same Date
- **Confidence:** 95%
- **Logic:** Amount within $0.01, same calendar date
- **Example:** $99.99 on 2025-10-21 matches $99.99 on 2025-10-21

#### 4. Exact Amount + 1 Day Difference
- **Confidence:** 90%
- **Logic:** Amount within $0.01, dates differ by 1 day
- **Example:** Receipt dated 10/21, transaction dated 10/22

#### 5. Exact Amount + Date Range
- **Confidence:** 80% - (days_diff * 5%)
- **Logic:** Amount within $0.01, dates within ±3 days
- **Example:** Receipt 10/21, transaction 10/24 → 80% - (3 * 5%) = 65%

#### 6. Fuzzy Amount + Close Date
- **Confidence:** 75% - (amount_diff% * 1%)
- **Logic:** Amount within ±5%, dates within ±1 day
- **Example:** $100 vs $102 (2% diff), 1 day apart → 75% - 2% = 73%

#### 7. Vendor Name Similarity
- **Confidence:** similarity * 70%
- **Logic:** Fuzzy string matching (60%+ similarity threshold)
- **Example:** "Amazon" vs "Amazon.com" → 75% similarity → 52.5% confidence

#### 8. Description Similarity
- **Confidence:** similarity * 50%
- **Logic:** Fuzzy string matching (50%+ similarity threshold)
- **Example:** Contributes to overall confidence when combined with other strategies

### Response Structure

`TransactionMatch` objects contain:

```python
{
    'transaction_id': 12345,
    'transaction_data': {
        'id': 12345,
        'date': '2025-10-21',
        'description': 'AMAZON.COM',
        'amount': -99.99,
        'entity': 'Delta LLC',
        # ... other transaction fields
    },
    'confidence': 0.95,  # 0.0 to 1.0
    'matching_strategies': [
        'exact_amount_and_date',
        'vendor_similarity'
    ],
    'match_details': {
        'amount_match': 'exact',
        'date_diff_days': 0,
        'vendor_similarity': 0.75
    },
    'recommendation': 'auto_apply'  # auto_apply | suggested | possible | uncertain
}
```

### Configuration Options

```python
matcher.config = {
    'date_range_days': 3,  # ±3 days from receipt date
    'amount_fuzzy_percent': 5,  # ±5% for fuzzy amount matching
    'vendor_similarity_threshold': 0.6,  # 60% similarity for vendors
    'description_similarity_threshold': 0.5,  # 50% for descriptions
    'min_confidence_threshold': 0.4,  # Minimum confidence to return
    'max_matches_returned': 10  # Maximum results
}
```

### Testing

Run the test suite:

```bash
# Run all tests
python web_ui/test_receipt_matcher.py

# With verbose logging
python web_ui/test_receipt_matcher.py --verbose

# Test database integration (requires PostgreSQL)
python web_ui/test_receipt_matcher.py --test-db
```

Test coverage includes:
- ✅ Date parsing (multiple formats)
- ✅ String similarity calculations
- ✅ Reference number normalization
- ✅ Confidence scoring logic
- ✅ New transaction suggestions
- ✅ Database query handling

### Integration with Receipt Processor

Complete workflow:

```python
from web_ui.services import ReceiptProcessor, ReceiptMatcher

# Step 1: Process the receipt
processor = ReceiptProcessor()
receipt_data = processor.process_receipt('receipt.pdf')

if receipt_data['status'] != 'success':
    handle_error(receipt_data['error_message'])
    return

# Step 2: Find matching transactions
matcher = ReceiptMatcher()
matches = matcher.find_matches(receipt_data)

# Step 3: Present to user
if matches:
    # Show matches in UI modal
    show_matching_modal(receipt_data, matches)
else:
    # Suggest creating new transaction
    suggestion = matcher.suggest_new_transaction(receipt_data)
    show_create_transaction_modal(suggestion)
```

### Performance

- **Database Query Time:** ~50-200ms (depends on transaction volume)
- **Matching Algorithm:** ~5-10ms per candidate transaction
- **Typical Match Time:** <500ms for 100 candidate transactions

### Next Steps

For complete Receipt Upload feature:
1. ✅ Receipt Processing Service (Task 4) - COMPLETE
2. ✅ Transaction Matching Logic (Task 6) - COMPLETE
3. 🔲 Receipt Upload API Endpoints (Task 7)
4. 🔲 Receipt Upload UI (Task 8)
5. 🔲 Cloud Storage Integration
6. 🔲 Database Schema Updates

See `RECEIPT_PROCESSOR_IMPLEMENTATION.md` for full implementation details.
