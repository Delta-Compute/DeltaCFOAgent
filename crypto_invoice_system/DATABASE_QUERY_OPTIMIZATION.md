# Database Query Optimization Guide

## Index Strategy

This document explains the indexing strategy for the crypto invoice system and how to write optimized queries.

---

## Invoice Table Indexes

### Single Column Indexes

| Index Name | Column | Purpose | Query Pattern |
|------------|--------|---------|---------------|
| `idx_crypto_invoices_invoice_number` | invoice_number | Exact invoice lookup | `WHERE invoice_number = 'DPY-2025-10-0001'` |
| `idx_crypto_invoices_status` | status | Filter by status | `WHERE status = 'sent'` |
| `idx_crypto_invoices_client` | client_id | Filter by client | `WHERE client_id = 123` |
| `idx_crypto_invoices_created_at` | created_at DESC | Sort by creation date | `ORDER BY created_at DESC` |
| `idx_crypto_invoices_issue_date` | issue_date DESC | Sort by issue date | `ORDER BY issue_date DESC` |
| `idx_crypto_invoices_due_date` | due_date | Filter/sort by due date | `WHERE due_date < NOW()` |
| `idx_crypto_invoices_paid_at` | paid_at DESC | Sort by payment date | `ORDER BY paid_at DESC` |

### Composite Indexes

| Index Name | Columns | Purpose | Query Pattern |
|------------|---------|---------|---------------|
| `idx_crypto_invoices_status_created` | status, created_at DESC | Pending invoices by date | `WHERE status = 'sent' ORDER BY created_at DESC` |
| `idx_crypto_invoices_client_status` | client_id, status | Client invoices by status | `WHERE client_id = 123 AND status = 'paid'` |
| `idx_crypto_invoices_status_due` | status, due_date | Overdue invoice detection | `WHERE status = 'sent' AND due_date < NOW()` |

---

## Optimized Query Examples

### 1. Dashboard: Get Recent Invoices

**❌ Slow (No index usage):**
```sql
SELECT * FROM crypto_invoices ORDER BY id DESC LIMIT 10;
```

**✅ Fast (Uses idx_crypto_invoices_created_at):**
```sql
SELECT * FROM crypto_invoices ORDER BY created_at DESC LIMIT 10;
```

---

### 2. Payment Polling: Get Pending Invoices

**❌ Slow:**
```sql
SELECT * FROM crypto_invoices WHERE status IN ('sent', 'partially_paid');
```

**✅ Fast (Uses idx_crypto_invoices_status_created):**
```sql
SELECT *
FROM crypto_invoices
WHERE status IN ('sent', 'partially_paid')
ORDER BY created_at DESC;
```

---

### 3. Client Dashboard: Filter by Client and Status

**❌ Slow:**
```sql
SELECT * FROM crypto_invoices
WHERE client_id = 5 AND status = 'paid'
ORDER BY created_at DESC;
```

**✅ Fast (Uses idx_crypto_invoices_client_status):**
```sql
SELECT *
FROM crypto_invoices
WHERE client_id = 5 AND status = 'paid'
ORDER BY created_at DESC;
```

---

### 4. Overdue Detection: Find Overdue Invoices

**❌ Slow:**
```sql
SELECT * FROM crypto_invoices
WHERE due_date < CURRENT_DATE AND status = 'sent';
```

**✅ Fast (Uses idx_crypto_invoices_status_due):**
```sql
SELECT *
FROM crypto_invoices
WHERE status = 'sent' AND due_date < CURRENT_DATE;
```

**Note:** Put `status` first in WHERE clause to match composite index.

---

### 5. Search: Find Invoice by Number

**✅ Fast (Uses idx_crypto_invoices_invoice_number):**
```sql
SELECT * FROM crypto_invoices WHERE invoice_number = 'DPY-2025-10-0001';
```

---

### 6. Date Range Filtering

**❌ Slow (No index):**
```sql
SELECT * FROM crypto_invoices
WHERE created_at BETWEEN '2025-10-01' AND '2025-10-31';
```

**✅ Fast (Uses idx_crypto_invoices_created_at):**
```sql
SELECT *
FROM crypto_invoices
WHERE created_at >= '2025-10-01' AND created_at < '2025-11-01'
ORDER BY created_at DESC;
```

---

### 7. Statistics: Count by Status

**✅ Fast (Uses idx_crypto_invoices_status):**
```sql
SELECT status, COUNT(*) as count, SUM(amount_usd) as total
FROM crypto_invoices
GROUP BY status;
```

---

## Payment Transaction Indexes

| Index Name | Purpose |
|------------|---------|
| `idx_crypto_payments_invoice` | Link payments to invoices |
| `idx_crypto_payments_txhash` | Search by transaction hash |
| `idx_crypto_payments_status` | Filter by payment status |
| `idx_crypto_payments_detected_at` | Recent payments chronologically |

### Optimized Payment Queries

**Get Payments for Invoice:**
```sql
SELECT * FROM crypto_payment_transactions
WHERE invoice_id = 123
ORDER BY detected_at DESC;
```

**Find Payment by Transaction Hash:**
```sql
SELECT * FROM crypto_payment_transactions
WHERE transaction_hash = '0xabc123...';
```

---

## Client Table Indexes

| Index Name | Purpose |
|------------|---------|
| `idx_crypto_clients_name` | Search clients by name |

**Search Clients:**
```sql
SELECT * FROM crypto_clients
WHERE name ILIKE '%Alps%';
```

---

## Index Maintenance

### Check Index Usage

```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public' AND tablename LIKE 'crypto_%'
ORDER BY idx_scan DESC;
```

### Find Unused Indexes

```sql
SELECT
    schemaname,
    tablename,
    indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND schemaname = 'public'
    AND tablename LIKE 'crypto_%'
    AND indexname NOT LIKE '%_pkey';
```

### Analyze Query Performance

```sql
EXPLAIN ANALYZE
SELECT * FROM crypto_invoices
WHERE status = 'sent'
ORDER BY created_at DESC
LIMIT 10;
```

Look for:
- ✅ "Index Scan" or "Index Only Scan"
- ❌ "Seq Scan" (sequential scan - slow!)

---

## Best Practices

### 1. Always Use Indexed Columns in WHERE

```sql
-- ✅ Good
WHERE status = 'sent'

-- ❌ Bad
WHERE UPPER(status) = 'SENT'  -- Function on column disables index
```

### 2. Match Composite Index Order

```sql
-- ✅ Good (matches idx_crypto_invoices_status_created)
WHERE status = 'sent' AND created_at > '2025-10-01'

-- ❌ Bad (wrong order)
WHERE created_at > '2025-10-01' AND status = 'sent'
```

### 3. Avoid SELECT * When Possible

```sql
-- ✅ Good
SELECT invoice_number, status, amount_usd FROM crypto_invoices WHERE status = 'sent';

-- ❌ Bad (retrieves unnecessary data)
SELECT * FROM crypto_invoices WHERE status = 'sent';
```

### 4. Use LIMIT for Large Result Sets

```sql
-- ✅ Good
SELECT * FROM crypto_invoices ORDER BY created_at DESC LIMIT 50;

-- ❌ Bad (retrieves all rows)
SELECT * FROM crypto_invoices ORDER BY created_at DESC;
```

### 5. Filter Before Join

```sql
-- ✅ Good
SELECT i.*, c.name
FROM crypto_invoices i
JOIN crypto_clients c ON i.client_id = c.id
WHERE i.status = 'sent';

-- ❌ Bad (join first, filter later)
SELECT i.*, c.name
FROM crypto_invoices i
JOIN crypto_clients c ON i.client_id = c.id
WHERE i.status = 'sent';
```

---

## Performance Benchmarks

Target performance (PostgreSQL with proper indexes):

| Query Type | Row Count | Target Time |
|------------|-----------|-------------|
| Invoice by number | 1 | < 1ms |
| Recent invoices (LIMIT 10) | 10 | < 5ms |
| Status filter (SENT) | 1000 | < 20ms |
| Date range (1 month) | 5000 | < 50ms |
| Complex filter + join | 100 | < 30ms |
| Full table stats | ALL | < 100ms |

If queries exceed these times:
1. Run `EXPLAIN ANALYZE` to check index usage
2. Verify indexes exist: `\di crypto_*` in psql
3. Update table statistics: `ANALYZE crypto_invoices;`
4. Consider adding covering indexes for frequently used queries

---

## Migration Commands

```bash
# Add all indexes
psql -f crypto_invoice_system/migrations/002_add_performance_indexes.sql

# Or use Python runner
python crypto_invoice_system/migrations/run_migration_002.py

# Verify indexes exist
psql -c "\di crypto_*"

# Check index sizes
psql -c "SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) FROM pg_indexes WHERE schemaname = 'public' AND tablename LIKE 'crypto_%'"
```

---

**Last Updated:** 2025-10-22
**Version:** 1.0
