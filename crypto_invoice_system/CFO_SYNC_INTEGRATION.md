# CFO Sync Integration Guide

## Overview

This document explains how the crypto invoice system integrates with the main AI CFO transaction classification system.

**Goal:** 100% automated revenue recognition - invoice payments automatically appear in the main CFO dashboard with correct classification, entity mapping, and confidence scoring.

---

## Architecture

```
┌──────────────────────┐
│ Crypto Invoice System│
│                      │
│  1. Invoice Created  │
│  2. Payment Detected │
│  3. Payment Confirmed│ ─────┐
└──────────────────────┘      │
                              │
                              ▼
                    ┌─────────────────────┐
                    │ CFO Sync Service    │
                    │                     │
                    │ • Maps invoice data │
                    │ • Creates CFO txn   │
                    │ • Links records     │
                    │ • Handles errors    │
                    └─────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────┐
│  Main AI CFO System                  │
│                                      │
│  transactions table:                 │
│  • Date, Description, Amount         │
│  • classified_entity                 │
│  • transaction_type: "Revenue"       │
│  • confidence: 1.0 (100%)            │
│  • source_file: "crypto_invoice_..." │
│  • Identifier: invoice_number        │
└──────────────────────────────────────┘
```

---

## Database Tables

### crypto_invoice_cfo_sync

Main mapping table linking invoices to CFO transactions.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| invoice_id | INTEGER | Reference to crypto_invoices |
| cfo_transaction_id | INTEGER | ID in main CFO transactions table |
| sync_status | VARCHAR(20) | pending, synced, failed, retry |
| sync_timestamp | TIMESTAMP | When sync completed |
| entity_mapped | VARCHAR(255) | Entity assigned in CFO |
| category_mapped | VARCHAR(100) | Category (Revenue) |
| confidence_score | DECIMAL | Always 1.0 for invoices |
| sync_error | TEXT | Error message if failed |
| retry_count | INTEGER | Number of retry attempts |

### crypto_cfo_sync_log

Audit trail of all sync attempts.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| invoice_id | INTEGER | Reference to invoice |
| sync_attempt_timestamp | TIMESTAMP | When attempt made |
| sync_status | VARCHAR(20) | Result of attempt |
| error_message | TEXT | Error if failed |
| request_payload | JSONB | Data sent to CFO |
| response_data | JSONB | Response from CFO |

---

## Sync Process Flow

### Trigger: Invoice Payment Confirmed

When invoice reaches `PAID` status:

1. **Check if already synced**
   ```sql
   SELECT * FROM crypto_invoice_cfo_sync WHERE invoice_id = ?
   ```

2. **If not synced, gather data**
   - Invoice details (number, amount, client)
   - Payment details (transaction hash, currency, amount)
   - Client mapping (match to existing CFO client)
   - Entity assignment (based on issuer)

3. **Create CFO transaction record**
   ```sql
   INSERT INTO transactions (
       Date,
       Description,
       Amount,
       classified_entity,
       Business_Unit,
       source_file,
       transaction_type,
       confidence,
       classification_reason,
       Origin,
       Destination,
       Identifier,
       Currency
   ) VALUES (
       paid_at,
       'Invoice {invoice_number} - {client_name} - {billing_period}',
       amount_usd,
       'Delta Mining Paraguay S.A.',  -- Entity from invoice issuer
       'Delta Mining Paraguay S.A.',
       'crypto_invoice_{invoice_number}',
       'Revenue',
       1.0,  -- 100% confidence
       'Crypto invoice payment from {client}',
       'External Account',
       'Delta Paraguay Operations',
       invoice_number,
       crypto_currency
   )
   ```

4. **Record sync mapping**
   ```sql
   INSERT INTO crypto_invoice_cfo_sync (
       invoice_id,
       cfo_transaction_id,
       sync_status,
       sync_timestamp,
       entity_mapped,
       category_mapped,
       confidence_score
   ) VALUES (
       invoice_id,
       cfo_txn_id,
       'synced',
       NOW(),
       'Delta Mining Paraguay S.A.',
       'Revenue',
       1.0
   )
   ```

5. **Log sync attempt**
   ```sql
   INSERT INTO crypto_cfo_sync_log (
       invoice_id,
       sync_status,
       cfo_transaction_id,
       request_payload,
       response_data
   )
   ```

6. **Update invoice status to COMPLETE**
   ```sql
   UPDATE crypto_invoices
   SET status = 'complete'
   WHERE id = invoice_id
   ```

---

## Entity Mapping

### Client to Entity Mapping

| Invoice Client | CFO Entity | Business Unit |
|----------------|------------|---------------|
| Alps Blockchain | Delta Mining Paraguay S.A. | Paraguay Mining |
| Exos Capital | Delta Mining Paraguay S.A. | Paraguay Hosting |
| GM Data Centers | Delta Mining Paraguay S.A. | Paraguay Colocation |
| Other | Delta Mining Paraguay S.A. | Paraguay Operations |

### Revenue Subcategories

Based on invoice `billing_period` or `description`:

| Keyword | Subcategory |
|---------|-------------|
| "hosting" | Client Hosting Revenue |
| "mining" | Mining Revenue |
| "colocation" | Colocation Revenue |
| "validator" | Validator Revenue |
| "platform" | Platform Fees |
| default | Client Services Revenue |

---

## Error Handling

### Retry Logic

**Automatic Retries:**
- Max retries: 3
- Retry interval: Exponential backoff (1 min, 5 min, 15 min)
- Retry conditions:
  - Network errors
  - Temporary database errors
  - Timeout errors

**No Retry:**
- Validation errors
- Duplicate transaction errors
- Schema mismatch errors

### Failed Sync Recovery

Query failed syncs:
```sql
SELECT *
FROM v_crypto_invoices_pending_sync
WHERE sync_status = 'failed'
AND retry_count < 3;
```

Manual retry:
```python
from crypto_invoice_system.services.cfo_sync import CFOSyncService

sync_service = CFOSyncService()
result = sync_service.sync_invoice_to_cfo(invoice_id, force_retry=True)
```

---

## Monitoring & Alerts

### Key Metrics

1. **Sync Lag** - Time from payment confirmed to CFO sync
   ```sql
   SELECT AVG(EXTRACT(EPOCH FROM (sync_timestamp - paid_at)))
   FROM crypto_invoice_cfo_sync s
   JOIN crypto_invoices i ON s.invoice_id = i.id
   WHERE sync_timestamp > NOW() - INTERVAL '24 hours';
   ```

2. **Sync Success Rate**
   ```sql
   SELECT
       COUNT(*) FILTER (WHERE sync_status = 'synced') * 100.0 / COUNT(*) as success_rate
   FROM crypto_invoice_cfo_sync
   WHERE created_at > NOW() - INTERVAL '7 days';
   ```

3. **Pending Syncs**
   ```sql
   SELECT COUNT(*) FROM v_crypto_invoices_pending_sync;
   ```

### Alerts

Set up alerts for:
- ⚠️ Sync lag > 10 minutes
- ⚠️ Failed syncs with retry_count >= 3
- ⚠️ Pending syncs > 5 invoices
- ⚠️ Success rate < 95%

---

## API Endpoints

### Trigger Manual Sync

```
POST /api/invoice/{invoice_id}/sync-to-cfo
```

**Response:**
```json
{
    "success": true,
    "invoice_id": 123,
    "cfo_transaction_id": 45678,
    "sync_status": "synced",
    "sync_timestamp": "2025-10-22T14:30:00Z"
}
```

### Check Sync Status

```
GET /api/invoice/{invoice_id}/sync-status
```

**Response:**
```json
{
    "invoice_id": 123,
    "invoice_number": "DPY-2025-10-0001",
    "invoice_status": "complete",
    "sync_status": "synced",
    "cfo_transaction_id": 45678,
    "sync_timestamp": "2025-10-22T14:30:00Z",
    "entity_mapped": "Delta Mining Paraguay S.A.",
    "category_mapped": "Revenue"
}
```

### Get Pending Syncs

```
GET /api/cfo-sync/pending
```

**Response:**
```json
{
    "count": 2,
    "invoices": [
        {
            "invoice_id": 124,
            "invoice_number": "DPY-2025-10-0002",
            "client_name": "Alps Blockchain",
            "amount_usd": 5000.00,
            "paid_at": "2025-10-22T14:00:00Z",
            "sync_status": "pending",
            "retry_count": 0
        }
    ]
}
```

---

## Database Views

### v_crypto_invoices_pending_sync

Shows invoices that need to be synced to CFO.

```sql
SELECT * FROM v_crypto_invoices_pending_sync;
```

### v_crypto_invoices_synced

Shows successfully synced invoices with CFO details.

```sql
SELECT * FROM v_crypto_invoices_synced;
```

---

## Helper Functions

### get_invoices_ready_for_sync()

PostgreSQL function that returns invoices ready to sync.

```sql
SELECT * FROM get_invoices_ready_for_sync();
```

Returns invoices that are:
- Status = 'paid'
- Sync status = NULL or 'failed'
- Retry count < 3
- Ordered by paid_at ASC (oldest first)

---

## Testing

### Test Sync Process

1. **Create test invoice**
   ```python
   invoice_id = create_test_invoice(
       client="Alps Blockchain",
       amount=100.00,
       currency="USDT",
       network="TRC20"
   )
   ```

2. **Simulate payment**
   ```python
   mark_invoice_as_paid(invoice_id, tx_hash="0xtest123")
   ```

3. **Trigger sync**
   ```python
   result = sync_invoice_to_cfo(invoice_id)
   assert result['success'] == True
   ```

4. **Verify in CFO database**
   ```sql
   SELECT * FROM transactions
   WHERE source_file LIKE 'crypto_invoice_%'
   ORDER BY created_at DESC LIMIT 1;
   ```

5. **Check sync status**
   ```sql
   SELECT * FROM crypto_invoice_cfo_sync
   WHERE invoice_id = {invoice_id};
   ```

---

## Troubleshooting

### Issue: Sync not triggering automatically

**Check:**
1. Invoice status is 'paid'
2. No existing sync record
3. Payment poller is running
4. No errors in logs

**Solution:**
```python
# Manual trigger
POST /api/invoice/{invoice_id}/sync-to-cfo
```

### Issue: Sync fails with duplicate error

**Cause:** Transaction already exists in CFO system

**Solution:**
1. Check if transaction already in CFO:
   ```sql
   SELECT * FROM transactions
   WHERE Identifier = 'DPY-2025-10-0001';
   ```
2. If exists, update sync mapping to point to existing transaction
3. Mark as synced without creating duplicate

### Issue: Wrong entity mapped

**Cause:** Client mapping configuration incorrect

**Solution:**
1. Update client-to-entity mapping in configuration
2. Update existing sync record:
   ```sql
   UPDATE crypto_invoice_cfo_sync
   SET entity_mapped = 'Correct Entity'
   WHERE invoice_id = {invoice_id};
   ```
3. Update CFO transaction:
   ```sql
   UPDATE transactions
   SET classified_entity = 'Correct Entity'
   WHERE id = {cfo_transaction_id};
   ```

---

**Last Updated:** 2025-10-22
**Version:** 1.0
