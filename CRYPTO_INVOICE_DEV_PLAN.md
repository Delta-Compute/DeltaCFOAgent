# CRYPTO INVOICE SYSTEM - DEVELOPMENT PLAN

**Project:** Complete Crypto Invoice System Implementation (PRD to Production)
**Date:** 2025-10-22
**Status:** AWAITING APPROVAL

---

## EXECUTIVE SUMMARY

This plan implements the complete Crypto Invoice System PRD on top of the existing foundation. The system is **~60% complete** with core infrastructure in place. This plan focuses on:

1. **Client-Facing Features** - Payment pages, real-time updates, better UX
2. **Enhanced Automation** - Rate locking, expiration, edge cases
3. **AI CFO Integration** - Automatic transaction classification
4. **Production Readiness** - Security, monitoring, error handling

**Estimated Complexity:** 40-50 tasks across 8 phases
**Approach:** Incremental, test-driven, minimal code changes per task

---

## CURRENT STATE ANALYSIS

### What Already Exists (60% Complete)

✅ **Database Schema** - PostgreSQL with all required tables
✅ **Invoice Creation API** - `/api/invoice/create` with PDF generation
✅ **Payment Polling** - Background service checking MEXC every 30s
✅ **MEXC Integration** - Deposit addresses, payment detection
✅ **Basic Dashboard** - Invoice list, statistics, status display
✅ **PDF Generation** - Professional invoices with QR codes
✅ **Manual Verification** - Admin can verify payments manually
✅ **Notification Service** - Email templates (not fully integrated)

### What's Missing (40% Remaining)

❌ **Client Payment Page** - No public-facing payment interface
❌ **Rate Lock Mechanism** - Exchange rates not locked for 15 minutes
❌ **Invoice Expiration** - No automatic expiration logic
❌ **Enhanced Fee/Tax** - No transaction fee % or tax % fields
❌ **Email Integration** - Notifications not triggered on events
❌ **AI CFO Sync** - Payments not auto-classified in main system
❌ **Wallet Integration** - Invoice addresses not registered in main DB
❌ **Edge Case Handling** - PARTIAL/OVERPAID statuses not implemented
❌ **Advanced Dashboard** - No search, filtering, CSV export
❌ **Security** - No authentication, rate limiting, or input validation

---

## DEVELOPMENT PHASES

### **PHASE 1: Database Enhancements** (5 tasks)
Extend schema for new PRD requirements

**1.1** Add invoice fields: `transaction_fee_percent`, `tax_percent`, `expiration_hours`, `allow_client_choice`, `rate_locked_until`, `client_wallet_address`

**1.2** Add invoice statuses: `EXPIRED`, `PARTIAL`, `OVERPAID`, `COMPLETE`

**1.3** Create indexes for performance: invoice search, client filtering, date range queries

**1.4** Add configuration for multi-chain support: chain list, token list per chain, confirmations per chain, explorer URLs

**1.5** Create invoice-to-cfo-transaction mapping table for tracking synced records

**Validation:** Run migration script, verify all fields exist, test queries

---

### **PHASE 2: Enhanced Invoice Creation** (6 tasks)
Implement missing FR-1 requirements

**2.1** Update invoice creation form UI: Add fee %, tax %, expiration hours, client wallet address, allow client choice checkbox

**2.2** Implement fee/tax calculation logic in backend: `total = base + (base × fee%) + (base × tax%)`

**2.3** Implement 15-minute rate lock: Lock exchange rate on creation, store `rate_locked_until` timestamp, warn if expired

**2.4** Add invoice expiration logic: Calculate expiration time from creation + expiration_hours, auto-expire in polling service

**2.5** Enhance line items UI: Better formatting, validation, subtotal calculation

**2.6** Add invoice validation: Required fields, amount > 0, valid date ranges, valid percentages (0-30%)

**Validation:** Create test invoice with fees/taxes, verify calculations, check expiration

---

### **PHASE 3: Client Payment Page** (8 tasks)
Build FR-2 public-facing payment interface

**3.1** Create `/invoice/<invoice_number>` public payment page route (no auth required)

**3.2** Design payment page UI: Invoice header, client info, amount breakdown, payment instructions, QR code, status display

**3.3** Implement payment configuration selector: Chain/token dropdowns (if allow_client_choice enabled), recalculate amount on change

**3.4** Add real-time status updates: Auto-refresh every 30s via AJAX, update status badge, show confirmation progress

**3.5** Implement copy-to-clipboard buttons: Copy address, copy amount, show confirmation toast

**3.6** Add manual TxID entry form: Client can submit transaction hash, verify and update status

**3.7** Make page mobile-responsive: QR code prominent on mobile, touch-friendly buttons, proper scaling

**3.8** Add PDF download button: Link to invoice PDF from payment page

**Validation:** Open payment page on mobile/desktop, test all interactions, verify real-time updates

---

### **PHASE 4: Advanced Payment Detection** (7 tasks)
Enhance FR-3 automation and edge cases

**4.1** Implement rate lock expiration handling: Check if rate expired, notify user, option to refresh rate

**4.2** Add PARTIAL payment status: Detect underpayment (< 99.5% of expected), mark as PARTIAL, notify issuer

**4.3** Add OVERPAID status: Detect overpayment (> 100.5% of expected), mark as OVERPAID, notify issuer

**4.4** Implement invoice expiration: Check `created_at + expiration_hours`, mark as EXPIRED, stop polling

**4.5** Add wrong token detection: Check if currency/network matches, flag as INVALID if wrong

**4.6** Enhance confirmation tracking: Update confirmation count on each poll, smooth status transitions (PAID → CONFIRMED → COMPLETE)

**4.7** Improve tolerance configuration: Make payment tolerance configurable per currency (BTC: 0.5%, stablecoins: 0.1%)

**Validation:** Test edge cases - underpay, overpay, wrong token, expired invoice

---

### **PHASE 5: Email Notification Integration** (6 tasks)
Connect FR-4 email system to workflows

**5.1** Create HTML email templates: Invoice sent, payment detected, payment confirmed, invoice overdue (with inline CSS)

**5.2** Integrate notifications with invoice creation: Send invoice email to client on creation, attach PDF

**5.3** Integrate notifications with payment detection: Send "payment detected" email to issuer when payment found

**5.4** Integrate notifications with payment confirmation: Send "payment confirmed" to client + issuer when fully confirmed

**5.5** Add QR code embedding in emails: Embed QR code image inline in invoice email

**5.6** Configure SMTP settings: Load from environment variables, test email sending, handle failures gracefully

**Validation:** Create invoice, verify client receives email with PDF, trigger payment, verify confirmation emails

---

### **PHASE 6: AI CFO Integration** (5 tasks)
Implement INT-1, INT-2, INT-3, INT-4 from PRD

**6.1** Register invoice addresses in main wallet database: On invoice creation, add address to `wallet_addresses` table with entity/purpose

**6.2** Auto-create transaction in AI CFO on payment confirmation: Insert into `transactions` table with 100% confidence, link to invoice

**6.3** Map invoice clients to existing CFO clients: Link Alps, Exos, GM to existing client records

**6.4** Add revenue recognition workflow: Map invoice to contract records, trigger revenue recognition on payment

**6.5** Test end-to-end integration: Create invoice → receive payment → verify appears in CFO dashboard with correct classification

**Validation:** Check main dashboard shows invoice payment as classified transaction, verify wallet registration

---

### **PHASE 7: Enhanced Dashboard & UX** (6 tasks)
Complete FR-5 and improve overall UX

**7.1** Add search functionality: Search by invoice number, client name, amount

**7.2** Add date range filtering: Filter invoices by creation date, due date, paid date

**7.3** Implement CSV export: Export filtered invoice list to CSV

**7.4** Add sorting: Sort by date, amount, status, client name

**7.5** Enhance statistics panel: Add charts, trend analysis, average payment time, conversion rate

**7.6** Add invoice detail modal: Click invoice to see full details, payment history, timeline

**Validation:** Test all filters, search, export, verify statistics accuracy

---

### **PHASE 8: Production Readiness** (7 tasks)
Security, monitoring, error handling (NFRs)

**8.1** Add input validation: Sanitize all user inputs, validate amounts/dates/emails, prevent SQL injection

**8.2** Implement rate limiting: Limit API calls per IP, prevent abuse

**8.3** Add comprehensive logging: Log all API calls, payment events, errors with structured format

**8.4** Implement error tracking: Capture exceptions, send alerts on critical errors

**8.5** Add monitoring dashboard: Track polling uptime, payment detection latency, error rates

**8.6** Create health check endpoint: `/health` returns system status, database connection, MEXC API status

**8.7** Write deployment documentation: Environment setup, configuration, monitoring, troubleshooting

**Validation:** Load test API, verify rate limiting works, check logs, trigger errors and verify alerts

---

## DEVELOPMENT PRINCIPLES

Following CLAUDE.md requirements:

1. **Simplicity First** - Each task impacts minimal code, single responsibility
2. **No Laziness** - Find root causes, no temporary fixes
3. **Test Everything** - Manual testing after each task, verify integrations
4. **Incremental Delivery** - Each phase is independently deployable
5. **Git Discipline** - Commit after each task, clear messages, push to designated branch

---

## TASK DEPENDENCIES

```
Phase 1 (Database) → Must complete before all others
Phase 2 (Invoice Creation) → Enables Phase 3, 5
Phase 3 (Payment Page) → Independent after Phase 1
Phase 4 (Payment Detection) → Can run parallel to Phase 3
Phase 5 (Emails) → Requires Phase 2, 3 complete
Phase 6 (CFO Integration) → Requires Phase 2, 4 complete
Phase 7 (Dashboard) → Can run parallel to Phase 5, 6
Phase 8 (Production) → Final phase, integrates all
```

**Suggested Execution Order:**
1. Phase 1 → Phase 2 → Phase 3 → Phase 5
2. Phase 1 → Phase 4 → Phase 6
3. Phase 7 (parallel with Phase 5/6)
4. Phase 8 (final integration)

---

## SUCCESS METRICS (from PRD)

The implementation will be validated against these metrics:

✅ **100% automation** - All invoice payments auto-classified without manual intervention
✅ **< 2 minutes** - Detection speed from blockchain confirmation to system
✅ **0% false positives** - No incorrect payment matching
✅ **< 5 minutes** - Average payment completion time
✅ **< 5 minutes** - All payments appear in AI CFO after confirmation
✅ **99.9% uptime** - Payment monitoring reliability
✅ **100% adoption** - Finance team uses for all crypto invoicing

---

## QUESTIONS FOR APPROVAL

Before starting implementation, please confirm:

1. **Scope Approval** - Are all 8 phases required for MVP, or should we prioritize certain phases?
2. **Timeline** - Is there a target completion date? Should we parallelize phases?
3. **Testing Strategy** - Should we use MEXC testnet or production API for testing?
4. **Email Service** - Which SMTP provider should we use? (SendGrid, AWS SES, Gmail?)
5. **Authentication** - Phase 8 mentions rate limiting but not authentication. Do we need user login for the dashboard?
6. **Client Records** - Should we import existing client data (Alps, Exos, GM) or create new?
7. **Deployment** - Should we deploy incrementally after each phase or wait for complete implementation?

---

## OUT OF SCOPE (Per PRD)

The following are explicitly NOT included in this plan:

❌ Recurring/subscription invoices
❌ Milestone payments with escrow
❌ Multi-signature authorization
❌ Dispute resolution
❌ Payment plans/installments
❌ Credit card payments
❌ Auto-invoice generation from contracts
❌ Client portal with login
❌ Advanced analytics/forecasting
❌ Multi-currency fiat conversions
❌ QuickBooks/Xero integration

---

## NEXT STEPS

**If this plan is approved:**

1. Create feature branch: `claude/crypto-invoice-prd-implementation`
2. Start with Phase 1 (Database Enhancements)
3. Create detailed task list in TodoWrite for Phase 1
4. Implement tasks one at a time
5. Commit and push after each completed task
6. Move to Phase 2 after Phase 1 validation

**If modifications needed:**

Please specify:
- Which phases to prioritize
- Which features to cut/add
- Any technical constraints or preferences
- Timeline requirements

---

**Ready to proceed? Please approve this plan or request modifications.**
