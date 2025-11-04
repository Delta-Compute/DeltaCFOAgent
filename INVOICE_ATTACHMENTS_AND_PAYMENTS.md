# Invoice Attachments and Partial Payments System

## Overview

This system enables tracking of multiple attachments and partial payments per invoice, specifically designed to handle crypto payment splits where clients divide large payments into multiple transactions due to exchange limits.

## Key Features

### 1. Multiple Attachments Per Invoice
- Upload any file type (PDF, images, spreadsheets, documents, archives, emails)
- AI-powered analysis using Claude Vision to extract payment data
- Track analysis status (pending, analyzed, failed)
- Link attachments as payment proofs
- Secure file storage with organized directory structure

### 2. Partial Payments Tracking
- Record unlimited payment splits per invoice
- Automatic status calculation (pending → partially_paid → paid)
- Visual progress tracking with percentage completion
- Multi-currency support (USD, BRL, EUR, USDT, BTC, etc.)
- Payment method tracking (crypto, wire, check, cash, credit card)
- Transaction reference/hash storage

### 3. AI Integration
- Automatic extraction of payment data from uploaded files
- Extracts: amount, date, method, transaction ID
- Uses existing Claude Vision integration (PaymentProofProcessor)
- Optional manual trigger for re-analysis

## Architecture

### Database Schema

**invoice_attachments table:**
```sql
- id (UUID) - Primary key
- invoice_id (TEXT) - References invoices(id)
- tenant_id (VARCHAR) - Multi-tenant support
- attachment_type (VARCHAR) - payment_proof, invoice_pdf, supporting_doc, contract, other
- file_name (VARCHAR) - Original filename
- file_path (TEXT) - Relative path to file
- file_size (INTEGER) - File size in bytes
- mime_type (VARCHAR) - File MIME type
- description (TEXT) - Optional description
- ai_extracted_data (JSONB) - AI analysis results
- ai_analysis_status (VARCHAR) - pending, analyzed, failed
- uploaded_by (VARCHAR) - User who uploaded
- uploaded_at (TIMESTAMP) - Upload timestamp
- analyzed_at (TIMESTAMP) - Analysis timestamp
```

**invoice_payments table:**
```sql
- id (UUID) - Primary key
- invoice_id (TEXT) - References invoices(id)
- tenant_id (VARCHAR) - Multi-tenant support
- payment_date (DATE) - Payment date
- payment_amount (DECIMAL) - Payment amount
- payment_currency (VARCHAR) - Currency code (USD, BRL, etc.)
- payment_method (VARCHAR) - Payment method
- payment_reference (VARCHAR) - Transaction reference/hash
- payment_notes (TEXT) - Additional notes
- attachment_id (UUID) - Optional link to proof
- recorded_by (VARCHAR) - User who recorded
- created_at (TIMESTAMP) - Record creation time
- updated_at (TIMESTAMP) - Last update time
```

### Backend Services

**AttachmentManager** (`web_ui/services/attachment_manager.py`):
- `upload_attachment()` - Upload file with optional AI analysis
- `analyze_attachment()` - Trigger AI analysis
- `list_attachments()` - List attachments with filtering
- `get_attachment()` - Get single attachment details
- `delete_attachment()` - Delete attachment and file
- `get_attachment_stats()` - Get statistics

**PaymentManager** (`web_ui/services/payment_manager.py`):
- `add_payment()` - Add new payment record
- `get_payments()` - List all payments for invoice
- `get_payment()` - Get single payment details
- `calculate_payment_summary()` - Calculate totals, remaining, percentage
- `update_invoice_payment_status()` - Auto-update invoice status
- `update_payment()` - Update payment details
- `delete_payment()` - Delete payment record
- `link_payment_to_attachment()` - Link payment to proof

### API Endpoints

**Attachments (7 endpoints):**
- `POST /api/invoices/<id>/attachments` - Upload attachment
- `GET /api/invoices/<id>/attachments` - List attachments
- `GET /api/attachments/<id>` - Get attachment details
- `DELETE /api/attachments/<id>` - Delete attachment
- `POST /api/attachments/<id>/analyze` - Trigger AI analysis
- `GET /api/attachments/<id>/download` - Download file
- `GET /api/invoices/<id>/attachment-stats` - Get statistics

**Payments (8 endpoints):**
- `POST /api/invoices/<id>/payments` - Add payment
- `GET /api/invoices/<id>/payments` - List payments
- `GET /api/invoices/<id>/payment-summary` - Get payment summary
- `GET /api/payments/<id>` - Get payment details
- `PUT /api/payments/<id>` - Update payment
- `DELETE /api/payments/<id>` - Delete payment
- `POST /api/payments/<id>/link-attachment` - Link to attachment

### Frontend Components

**Tabbed Interface** (`web_ui/templates/invoices.html`):
- Three tabs: Overview, Payments, Attachments
- Badge counts showing number of items
- Lazy loading for performance
- Modern CSS styling with gradients

**JavaScript Modules:**
- `invoice_attachments.js` - Attachment management UI
- `invoice_payments.js` - Payment tracking UI
- Modal forms for add/edit operations
- Real-time updates and badge refresh

## Installation & Setup

### 1. Database Tables

Tables are automatically created on app startup via `app_db.py`. No manual SQL execution needed.

To verify tables exist:
```sql
SELECT * FROM invoice_attachments LIMIT 1;
SELECT * FROM invoice_payments LIMIT 1;
```

### 2. Migrate Existing Data (Optional)

If you have existing invoices with payment data in the old single-payment columns:

```bash
# Preview migration
python migrations/migrate_existing_payment_data.py --dry-run

# Execute migration
python migrations/migrate_existing_payment_data.py --execute

# Verify migration
python migrations/migrate_existing_payment_data.py --verify
```

### 3. File Storage

Ensure the uploads directory is writable:
```bash
mkdir -p uploads/attachments
chmod 755 uploads/attachments
```

Directory structure:
```
uploads/
  attachments/
    {tenant_id}/
      {invoice_id}/
        {timestamp}_{uuid}_{filename}
```

## Usage Guide

### For End Users

#### Uploading Attachments:

1. Open any invoice in the Invoices page
2. Click the "Attachments" tab
3. Click "Upload Attachment" button
4. Select file (any type supported)
5. Choose attachment type (payment_proof, invoice_pdf, etc.)
6. Add optional description
7. Check "Analyze with AI immediately" for automatic extraction
8. Click "Upload"

#### Recording Partial Payments:

1. Open invoice and click "Payments" tab
2. View payment summary showing total, paid, remaining, progress
3. Click "Add Payment" button
4. Enter payment amount and date
5. Select currency (USD, BRL, EUR, crypto, etc.)
6. Select payment method (crypto, wire, check, etc.)
7. Add transaction reference/hash (for crypto payments)
8. Add optional notes
9. Click "Add Payment"
10. Status automatically updates (pending → partially_paid → paid)

#### Example: Crypto Split Payment Scenario

**Scenario:** Client needs to pay $3,000 invoice but exchange limits to $1,000 per transaction.

**Steps:**
1. Client sends 3 separate crypto transactions:
   - TX1: $1,000 on 2025-01-15
   - TX2: $1,000 on 2025-01-16
   - TX3: $1,000 on 2025-01-17

2. User records each payment:
   - Open invoice, go to Payments tab
   - Add Payment #1: Amount=$1,000, Date=2025-01-15, Method=crypto, Ref=0x123abc...
   - Status updates to "PARTIALLY PAID" (33.3%)
   - Add Payment #2: Amount=$1,000, Date=2025-01-16, Method=crypto, Ref=0x456def...
   - Status updates to "PARTIALLY PAID" (66.7%)
   - Add Payment #3: Amount=$1,000, Date=2025-01-17, Method=crypto, Ref=0x789ghi...
   - Status updates to "PAID" (100%)

3. Invoice automatically marked as fully paid in main list

### For Developers

#### Using AttachmentManager:

```python
from web_ui.services.attachment_manager import AttachmentManager
from web_ui.database import db_manager

manager = AttachmentManager(db_manager)

# Upload attachment
success, message, attachment = manager.upload_attachment(
    file_obj=request.files['file'],
    invoice_id='invoice-123',
    tenant_id='delta',
    attachment_type='payment_proof',
    description='Payment receipt from client',
    uploaded_by='user@example.com',
    analyze_with_ai=True
)

# List attachments
attachments = manager.list_attachments('invoice-123', 'delta')

# Get AI analysis
attachment = manager.get_attachment('attachment-id', 'delta')
if attachment['ai_analysis_status'] == 'analyzed':
    data = attachment['ai_extracted_data']
    print(f"Amount: {data['payment_amount']}")
    print(f"Date: {data['payment_date']}")
```

#### Using PaymentManager:

```python
from web_ui.services.payment_manager import PaymentManager
from web_ui.database import db_manager

manager = PaymentManager(db_manager)

# Add payment
success, message, payment = manager.add_payment(
    invoice_id='invoice-123',
    tenant_id='delta',
    payment_amount=1000.00,
    payment_date='2025-01-15',
    payment_currency='USD',
    payment_method='crypto',
    payment_reference='0x123abc...',
    payment_notes='First of three payments',
    recorded_by='user@example.com'
)

# Get summary
summary = manager.calculate_payment_summary('invoice-123', 'delta')
print(f"Total: ${summary['total_amount']}")
print(f"Paid: ${summary['total_paid']}")
print(f"Remaining: ${summary['remaining']}")
print(f"Progress: {summary['percentage_paid']}%")
print(f"Status: {summary['status']}")
```

## Configuration

### File Upload Limits

Configure in Flask app settings:
```python
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
```

### Allowed File Types

Configured in `AttachmentManager.ALLOWED_EXTENSIONS`:
```python
ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif', 'bmp', 'gif', 'webp',  # Images & PDFs
    'csv', 'xls', 'xlsx', 'xlsm',  # Spreadsheets
    'doc', 'docx', 'txt', 'rtf',  # Documents
    'zip', 'rar', '7z',  # Archives
    'eml', 'msg'  # Emails
}
```

### AI Analysis

AI analysis uses the existing `PaymentProofProcessor` which leverages Claude Vision API. Supports:
- PDF files
- Images (PNG, JPG, TIFF, etc.)
- CSV files
- Excel spreadsheets

## Security Considerations

1. **File Upload Security:**
   - Filename sanitization using `werkzeug.secure_filename`
   - File type validation
   - Size limits enforced
   - Files stored outside web root

2. **Multi-Tenant Isolation:**
   - All queries filtered by `tenant_id`
   - Directory structure includes tenant separation
   - API endpoints validate tenant access

3. **Database Security:**
   - Foreign key constraints with CASCADE delete
   - Prepared statements prevent SQL injection
   - UUID primary keys prevent enumeration

4. **Access Control:**
   - Authentication required for all endpoints
   - User tracking (uploaded_by, recorded_by fields)
   - Audit trail with timestamps

## Troubleshooting

### Common Issues

**Issue:** Attachments not appearing after upload
- Check file permissions on `uploads/attachments/` directory
- Verify database connection and table existence
- Check browser console for JavaScript errors

**Issue:** AI analysis fails
- Verify ANTHROPIC_API_KEY is set in environment
- Check Claude API rate limits and quotas
- Ensure file type is supported (PDF, images, CSV, Excel)

**Issue:** Payment status not updating
- Verify `payment_manager.update_invoice_payment_status()` is being called
- Check database foreign key relationships
- Ensure `payment_amount` and `total_amount` are numeric types

**Issue:** Tab counts show 0 despite having data
- Check `loadTabCounts()` function is being called
- Verify API endpoints return correct data structure
- Check browser network tab for failed API calls

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check database queries:
```sql
-- Verify attachments
SELECT COUNT(*) FROM invoice_attachments WHERE invoice_id = 'your-invoice-id';

-- Verify payments
SELECT COUNT(*) FROM invoice_payments WHERE invoice_id = 'your-invoice-id';

-- Check payment summary
SELECT
    i.invoice_number,
    i.total_amount,
    i.payment_status,
    COUNT(p.id) as payment_count,
    SUM(p.payment_amount) as total_paid
FROM invoices i
LEFT JOIN invoice_payments p ON i.id = p.invoice_id
WHERE i.id = 'your-invoice-id'
GROUP BY i.id, i.invoice_number, i.total_amount, i.payment_status;
```

## Future Enhancements

Potential improvements:
1. Bulk attachment upload with drag-and-drop
2. Attachment previews (thumbnails for images, PDF viewer)
3. Payment reminders for partially paid invoices
4. Export payment history to CSV/PDF
5. Payment matching algorithm for auto-linking to invoices
6. OCR for handwritten receipts
7. Integration with blockchain explorers for crypto tx verification
8. Email notifications when partial payment received
9. Payment plan scheduler for installment payments
10. Multi-currency conversion at time of payment

## Support

For issues or questions:
1. Check this documentation
2. Review code comments in source files
3. Check database schema and constraints
4. Test with dry-run migrations first
5. Enable debug logging for detailed error messages

## License

Part of Delta CFO Agent system. Internal use only.
