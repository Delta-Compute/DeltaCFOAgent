#!/usr/bin/env python3
"""
Backfill missing expense transactions for triangular payments
Creates the expense side for invoices that were marked as paid with a recipient
"""

import sys
sys.path.append('/Users/whitdhamer/DeltaCFOAgentv2/web_ui')

from database import db_manager
import uuid

def backfill_triangular_expenses():
    """Create missing expense transactions for triangular payments"""

    tenant_id = 'delta'

    print("\n" + "="*100)
    print("BACKFILLING EXPENSE TRANSACTIONS FOR TRIANGULAR PAYMENTS")
    print("="*100 + "\n")

    # Find all paid invoices with ANDE as recipient (triangular payments)
    query = """
        SELECT i.id, i.invoice_number, i.vendor_name, i.customer_name,
               i.total_amount, i.currency, i.payment_date, i.payment_notes,
               i.linked_transaction_id,
               t.destination as recipient
        FROM invoices i
        JOIN transactions t ON i.linked_transaction_id = t.transaction_id
        WHERE i.tenant_id = %s
        AND i.payment_status = 'paid'
        AND t.destination = 'ANDE'
        AND t.amount > 0
        AND t.accounting_category = 'Revenue'
        AND DATE(i.payment_date::date) = CURRENT_DATE
    """

    invoices = db_manager.execute_query(query, (tenant_id,), fetch_all=True)

    print(f"Found {len(invoices)} invoices with triangular payments to ANDE\n")

    created_count = 0

    for inv in invoices:
        print(f"Processing Invoice: {inv['invoice_number']}")
        print(f"  Customer: {inv['customer_name']}")
        print(f"  Vendor: {inv['vendor_name']}")
        print(f"  Recipient: {inv['recipient']}")
        print(f"  Amount: {inv['currency']} {inv['total_amount']:,.2f}")

        # Check if expense transaction already exists
        check_query = """
            SELECT COUNT(*) as count
            FROM transactions
            WHERE tenant_id = %s
            AND invoice_id = %s
            AND amount < 0
            AND accounting_category = 'Expense'
        """

        existing = db_manager.execute_query(check_query, (tenant_id, inv['id']), fetch_one=True)

        if existing['count'] > 0:
            print(f"  ✓ Expense transaction already exists - skipping")
            print()
            continue

        # Create expense transaction
        expense_txn_id = str(uuid.uuid4())
        expense_amount = -abs(float(inv['total_amount']))
        expense_description = f"Expense paid by {inv['customer_name']} to {inv['recipient']} for Invoice #{inv['invoice_number']}"
        expense_justification = f"Expense to {inv['recipient']} - paid on our behalf by {inv['customer_name']} for Invoice #{inv['invoice_number']}"
        if inv['payment_notes']:
            expense_justification += f" - {inv['payment_notes']}"

        insert_query = """
            INSERT INTO transactions (
                transaction_id, tenant_id, date, description, amount, currency,
                accounting_category, subcategory, classified_entity, origin, destination,
                justification, invoice_id, source_file, confidence, classification_reason,
                created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                CURRENT_TIMESTAMP
            )
        """

        db_manager.execute_query(insert_query, (
            expense_txn_id,
            tenant_id,
            inv['payment_date'],
            expense_description,
            expense_amount,
            inv['currency'],
            'Expense',
            'Supplier Payment',
            tenant_id,
            inv['vendor_name'],  # Origin: our company
            inv['recipient'],  # Destination: ANDE
            expense_justification,
            inv['id'],
            f"invoice_{inv['invoice_number']}_triangular_expense_backfill",
            1.0,
            'Backfilled expense transaction for triangular payment'
        ))

        print(f"  ✓ Created expense transaction: {expense_txn_id}")
        print(f"    Amount: {inv['currency']} {expense_amount:,.2f}")
        print()
        created_count += 1

    print("="*100)
    print(f"SUMMARY:")
    print(f"  - Invoices processed: {len(invoices)}")
    print(f"  - Expense transactions created: {created_count}")
    print("="*100 + "\n")

    return created_count

if __name__ == '__main__':
    try:
        count = backfill_triangular_expenses()
        print(f"✅ Backfill completed successfully. Created {count} expense transactions.\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
