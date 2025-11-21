# Delta Tenant Invoice Summary

**Generated:** 2025-01-18
**Tenant:** delta

## Overall Statistics

- **Total Invoices:** 271
- **Pending (Need Transactions):** 263 invoices
- **Paid (Already Have Transactions):** 4 invoices
- **Other Status:** 4 invoices

## Key Findings

### Pending Invoices Breakdown

The 263 pending invoices need transactions created via the "Mark as Paid" feature:

**By Currency:**
- Majority in USD
- Several large invoices in PYG (Paraguayan Guaraní)

**By Vendor:**
- Primary vendor: Delta Mining Paraguay S.A.
- Secondary: Delta Brazil, Delta Energy

**By Customer/Client:**
- ACUARIO, LLC - Multiple high-value invoices
- EXOS DIGITAL ASSETS I LLC - Multiple invoices
- Dolomiti Paraguay S.A. - Several large invoices
- BURJ AL CB S.A. - Several PYG invoices
- GM Data Centers AG - Multiple invoices
- Individual clients: Pablo Chuck, Sergio Von Tiesenhausen, Pablo Jonson Zalazar, etc.

**Amount Ranges:**
- Small: $10 - $1,000
- Medium: $1,000 - $10,000
- Large: $10,000 - $50,000+
- Very Large (PYG): 15M - 306M PYG

**Date Range:**
- Oldest: 2022-02-01
- Newest: 2029-09-02 (likely data entry error)
- Most invoices: 2024-2025

### Sample Pending Invoices (First 20):

1. **c4430ddb-b682-4491-bbfc-6c17c5c25a4c** - Invoice #N 001-002-020925_1762450377
   - Date: 2029-09-02
   - Customer: Silvia Cordero
   - Amount: USD 710.80
   - Business Unit: Delta Mining Paraguay S.A.

2. **854ca93f-1585-4770-a7e7-5ddd6d4f506f** - Invoice #N 001-003-120325
   - Date: 2025-12-03
   - Customer: EXOS DIGITAL ASSETS I LLC
   - Amount: USD 1,350.00
   - Business Unit: Delta Mining Paraguay S.A.

3. **aeff5933-44bd-4ea8-91be-6e002b848212** - Invoice #20251103202826
   - Date: 2025-11-03
   - Customer: Krause
   - Amount: USD 363.81

4. **320df48e-d13a-46a0-aff5-8a7b118aba14** - Invoice #20251028152842
   - Date: 2025-10-28
   - Customer: ACUARIO, LLC
   - Amount: USD 34,818.05

5. **a2e5ae63-efb1-46c9-9e94-bb2c809d4898** - Invoice #20251024180743
   - Date: 2025-10-24
   - Customer: ACUARIO, LLC
   - Amount: USD 34,276.55

6. **48372be1-1d1b-4f73-a2cc-b91816a604b7** - Invoice #20251024190145
   - Date: 2025-10-24
   - Customer: DELTA ENERGY / t
   - Amount: USD 11.00

7. **51dc6b44-ed84-4ead-baa3-9162413334bc** - Invoice #RUC 80127432-0
   - Date: 2025-10-09
   - Customer: Everminer, LLC
   - Amount: USD 8,639.68
   - **Note:** Has linked_transaction_id (66ee3a952b62) but still pending status

8. **975ba075-e8c4-4f1d-919a-19e4affcaf76** - Invoice #RUC 80127432-0_1759785307
   - Date: 2025-10-09
   - Customer: Everminer, LLC
   - Amount: USD 3,625.58

9. **1bdcb7f9-10d1-4cc9-97ae-a5eb6af29c99** - Invoice #N 001-002-02102025
   - Date: 2025-10-02
   - Customer: ACUARIO, LLC
   - Amount: USD 6,660.35
   - **Note:** Has linked_transaction_id (949d5fbbbefc) but still pending

10. **14c46afd-2144-426b-b175-9c14bb409add** - Invoice #N 001-002-030925
    - Date: 2025-09-03
    - Customer: Nadon LLC
    - Amount: USD 309.77
    - **Note:** Has linked_transaction_id (4aa90c0985e9) but still pending

### Invoices Already Paid (Have Transactions):

1. **Paid Invoice 1** - Already has transaction and payment_status = 'paid'
2. **Paid Invoice 2** - Already has transaction and payment_status = 'paid'
3. **Paid Invoice 3** - Already has transaction and payment_status = 'paid'
4. **Paid Invoice 4** - Already has transaction and payment_status = 'paid'

## Important Notes

1. **Some pending invoices have linked_transaction_id but status is still 'pending'**
   - These were matched to transactions but never updated to 'paid' status
   - Example: Invoice #RUC 80127432-0 (ID: 51dc6b44-ed84-4ead-baa3-9162413334bc)
   - These should be updated to 'paid' status

2. **Date Validation Needed**
   - Invoice #N 001-002-020925_1762450377 has date 2029-09-02 (future date, likely error)
   - Some invoices may have incorrect dates

3. **Missing Business Unit/Category**
   - Several recent invoices (2025-10, 2025-11) have NULL business_unit and category
   - These should be categorized properly

## Recommendations

### Option 1: Manual Mark as Paid via UI
- Use the new "Mark as Paid" button in the Invoices page
- Process invoices one by one, providing payment details
- Best for: Complex cases requiring specific payment information

### Option 2: Bulk Script (Auto-Create Transactions)
- Create a Python script to automatically process all pending invoices
- Auto-match existing transactions or create virtual transactions
- Best for: High volume of straightforward cases

### Option 3: Hybrid Approach
1. First, update invoices that already have linked_transaction_id to 'paid' status (simple UPDATE query)
2. Then process remaining truly pending invoices via script or UI

## Next Steps

Please review this summary and let me know:

1. **Which approach do you prefer?**
   - Manual via UI (best for small batches)
   - Automated script (best for bulk processing)
   - Hybrid (update existing links first, then process rest)

2. **Payment date strategy:**
   - Use invoice date as payment date?
   - Use due_date as payment date?
   - Use current date for all?
   - Use a specific historical date?

3. **Payer/Recipient information:**
   - For most invoices, should we use:
     - Payer: Customer name from invoice
     - Recipient: Vendor name (Delta Mining Paraguay S.A.)
   - Or leave blank for automatic transaction creation?

4. **Notes/Justification:**
   - Should we add a standard note like "Historical invoice - bulk transaction creation"?
   - Or leave blank?

I can then create the appropriate script to process these 263 pending invoices efficiently.
