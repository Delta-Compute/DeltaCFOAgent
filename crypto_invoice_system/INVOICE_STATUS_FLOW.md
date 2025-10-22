# Invoice Status Flow

## Status Definitions

### Primary Statuses

**DRAFT** (`draft`)
- Invoice created but not yet sent to client
- Editable
- Not monitored for payments

**SENT** (`sent`)
- Invoice sent to client
- Payment monitoring active
- QR code and payment page accessible
- Rate lock active (15 minutes from creation)

**PARTIALLY_PAID** (`partially_paid`)
- Payment detected on blockchain
- Awaiting confirmations
- Amount matches expected value (within tolerance)
- Intermediate state during confirmation process

**PAID** (`paid`)
- Payment fully confirmed on blockchain
- Required confirmations reached
- Invoice marked as paid but not yet synced to AI CFO

**COMPLETE** (`complete`)
- Payment confirmed on blockchain
- Transaction synced to AI CFO system
- Revenue recognized
- Final successful state

### Edge Case Statuses

**EXPIRED** (`expired`)
- Invoice past expiration time without payment
- Payment monitoring stopped
- Client can no longer pay this invoice
- Occurs when: `current_time > (created_at + expiration_hours)`

**PARTIAL** (`partial`)
- Underpayment detected
- Client sent less than expected amount
- Amount received: < 99.5% of invoice amount
- Requires manual review or client follow-up

**OVERPAID** (`overpaid`)
- Overpayment detected
- Client sent more than expected amount
- Amount received: > 100.5% of invoice amount
- Requires refund or credit processing

**OVERDUE** (`overdue`)
- Past due date without payment
- Invoice still valid but overdue
- Occurs when: `current_date > due_date AND status IN (SENT, PARTIALLY_PAID)`
- Payment monitoring continues

**CANCELLED** (`cancelled`)
- Manually cancelled by issuer
- Payment monitoring stopped
- Invoice void

---

## Status Flow Diagram

```
┌─────────┐
│  DRAFT  │ (Initial state - editable)
└────┬────┘
     │ send_invoice()
     ▼
┌─────────┐
│  SENT   │ ◄─── Payment monitoring starts
└────┬────┘      Rate lock: 15 minutes
     │            Expiration timer: 24h (default)
     │
     ├──── [Payment detected] ───► PARTIALLY_PAID
     │                                  │
     │                                  │ [Confirmations reached]
     │                                  ▼
     ├──── [Direct confirm] ────────► PAID
     │                                  │
     │                                  │ [Synced to AI CFO]
     │                                  ▼
     │                              COMPLETE
     │
     ├──── [Time > expiration] ─────► EXPIRED
     │
     ├──── [Date > due_date] ───────► OVERDUE
     │                                  │
     │                                  └──► Can still → PAID
     │
     ├──── [Underpayment] ──────────► PARTIAL
     │                                  │
     │                                  └──► Manual review needed
     │
     ├──── [Overpayment] ───────────► OVERPAID
     │                                  │
     │                                  └──► Manual refund/credit
     │
     └──── [Manual cancel] ─────────► CANCELLED
```

---

## Status Transition Rules

### Valid Transitions

| From | To | Trigger | Automated |
|------|----|---------| ---------|
| DRAFT | SENT | Invoice sent to client | Manual |
| SENT | PARTIALLY_PAID | Payment detected (0+ confirmations) | Auto |
| SENT | PAID | Payment confirmed directly | Auto |
| SENT | EXPIRED | Expiration time reached | Auto |
| SENT | OVERDUE | Due date passed | Auto |
| SENT | PARTIAL | Underpayment detected | Auto |
| SENT | OVERPAID | Overpayment detected | Auto |
| SENT | CANCELLED | Manual cancellation | Manual |
| PARTIALLY_PAID | PAID | Required confirmations reached | Auto |
| PARTIALLY_PAID | OVERDUE | Due date passed during confirmation | Auto |
| PAID | COMPLETE | Synced to AI CFO system | Auto |
| OVERDUE | PAID | Late payment confirmed | Auto |
| OVERDUE | EXPIRED | Expiration time reached | Auto |

### Invalid Transitions

These transitions should never occur:
- Any status → DRAFT (once sent, cannot go back to draft)
- COMPLETE → any other status (final state)
- EXPIRED → PAID (expired invoices cannot be paid)
- CANCELLED → any active status (cancelled is terminal)

---

## Edge Case Handling

### Underpayment (PARTIAL)

**Condition:** `amount_received < invoice_amount * 0.995`

**Actions:**
1. Mark invoice as PARTIAL
2. Send notification to issuer
3. Record actual amount received
4. Wait for issuer decision:
   - Accept partial payment
   - Request additional payment
   - Cancel invoice

### Overpayment (OVERPAID)

**Condition:** `amount_received > invoice_amount * 1.005`

**Actions:**
1. Mark invoice as OVERPAID
2. Send notification to issuer
3. Record actual amount received
4. Process refund or issue credit:
   - Refund excess to client wallet
   - Apply as credit to next invoice
   - Accept as tip/donation

### Rate Lock Expiration

**Condition:** `current_time > rate_locked_until`

**Actions:**
1. Display warning on payment page
2. Show "Rate expired - actual amount may vary"
3. Option to refresh rate (extends lock another 15 min)
4. Payment still accepted but amount might differ

### Invoice Expiration

**Condition:** `current_time > (created_at + expiration_hours * 3600)`

**Actions:**
1. Mark invoice as EXPIRED
2. Stop payment monitoring
3. Payment page shows "Invoice expired"
4. Option for client to request new invoice

---

## Monitoring & Automation

### Payment Poller Checks

Every 30 seconds, the payment poller:

1. **Get pending invoices** (`status IN (SENT, PARTIALLY_PAID, OVERDUE)`)
2. **Check for payments** via MEXC API
3. **Detect amount matching** (with 0.1% tolerance for shared addresses)
4. **Update status based on findings:**
   - Payment found → PARTIALLY_PAID
   - Confirmations reached → PAID
   - Underpayment → PARTIAL
   - Overpayment → OVERPAID
5. **Check expiration** (`current_time > created_at + expiration_hours`)
   - Expired → EXPIRED
6. **Check overdue** (`current_date > due_date`)
   - Overdue → OVERDUE

### AI CFO Sync

When invoice reaches `PAID` status:

1. Create transaction record in main CFO database
2. Set entity based on invoice issuer
3. Set category = "Revenue"
4. Set confidence = 100% (from our system)
5. Link transaction hash and invoice number
6. Mark invoice as `COMPLETE`

---

## Status Priority

When multiple conditions are true, status priority:

1. **CANCELLED** (manual override, highest priority)
2. **EXPIRED** (hard deadline)
3. **COMPLETE** (final successful state)
4. **PAID** (payment confirmed)
5. **OVERPAID** (edge case - needs attention)
6. **PARTIAL** (edge case - needs attention)
7. **PARTIALLY_PAID** (in progress)
8. **OVERDUE** (past due but still valid)
9. **SENT** (normal waiting state)
10. **DRAFT** (initial state)

---

## API Response Codes

| Status | HTTP Color | Dashboard Color | Icon |
|--------|-----------|----------------|------|
| DRAFT | Grey | #757575 | 📝 |
| SENT | Blue | #1976d2 | 📤 |
| PARTIALLY_PAID | Orange | #f57c00 | ⏳ |
| PAID | Green | #388e3c | ✅ |
| COMPLETE | Dark Green | #2e7d32 | 🎉 |
| EXPIRED | Purple | #7b1fa2 | ⏰ |
| PARTIAL | Dark Orange | #e65100 | ⚠️ |
| OVERPAID | Yellow | #f57f17 | 💰 |
| OVERDUE | Red | #c62828 | ❌ |
| CANCELLED | Grey Strike | #455a64 | 🚫 |

---

## Implementation Checklist

- [x] Define InvoiceStatus enum with all statuses
- [x] Add dashboard CSS for all status badges
- [ ] Update payment poller to detect edge cases
- [ ] Implement expiration checking logic
- [ ] Implement AI CFO sync on PAID → COMPLETE
- [ ] Add status transition validation
- [ ] Create status history log table (future enhancement)
- [ ] Add webhook notifications for status changes

---

**Last Updated:** 2025-10-22
**Version:** 1.0
