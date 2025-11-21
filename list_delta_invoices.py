#!/usr/bin/env python3
"""
List all invoices for Delta tenant
Shows invoice details and payment status to determine which need transactions created
"""

import sys
sys.path.append('/Users/whitdhamer/DeltaCFOAgentv2/web_ui')

from database import db_manager

def list_delta_invoices():
    """List all invoices for Delta tenant"""

    tenant_id = 'delta'

    print(f"\n{'='*100}")
    print(f"INVOICES FOR TENANT: {tenant_id}")
    print(f"{'='*100}\n")

    # Query all invoices for Delta tenant
    query = """
        SELECT
            id,
            invoice_number,
            date,
            due_date,
            vendor_name,
            customer_name,
            total_amount,
            currency,
            payment_status,
            linked_transaction_id,
            match_method,
            payment_date,
            business_unit,
            category,
            created_at
        FROM invoices
        WHERE tenant_id = %s
        ORDER BY date DESC, invoice_number ASC
    """

    invoices = db_manager.execute_query(query, (tenant_id,), fetch_all=True)

    if not invoices:
        print("No invoices found for Delta tenant.\n")
        return []

    print(f"Total Invoices: {len(invoices)}\n")

    # Group by payment status
    pending_invoices = []
    paid_invoices = []
    other_invoices = []

    for invoice in invoices:
        inv_dict = dict(invoice)
        payment_status = inv_dict.get('payment_status', 'pending')

        if payment_status == 'paid':
            paid_invoices.append(inv_dict)
        elif payment_status == 'pending':
            pending_invoices.append(inv_dict)
        else:
            other_invoices.append(inv_dict)

    # Print summary
    print(f"SUMMARY:")
    print(f"  - Pending: {len(pending_invoices)}")
    print(f"  - Paid: {len(paid_invoices)}")
    print(f"  - Other: {len(other_invoices)}")
    print()

    # Print pending invoices (need transactions created)
    if pending_invoices:
        print(f"\n{'='*100}")
        print(f"PENDING INVOICES (Need Transactions Created)")
        print(f"{'='*100}\n")

        for idx, inv in enumerate(pending_invoices, 1):
            print(f"{idx}. Invoice #{inv['invoice_number']}")
            print(f"   ID: {inv['id']}")
            print(f"   Date: {inv['date']}")
            print(f"   Vendor: {inv['vendor_name']}")
            print(f"   Customer: {inv['customer_name']}")
            print(f"   Amount: {inv['currency']} {inv['total_amount']:,.2f}")
            print(f"   Payment Status: {inv['payment_status']}")
            print(f"   Linked Transaction: {inv['linked_transaction_id'] or 'None'}")
            print(f"   Business Unit: {inv['business_unit']}")
            print(f"   Category: {inv['category']}")
            print()

    # Print paid invoices (already have transactions)
    if paid_invoices:
        print(f"\n{'='*100}")
        print(f"PAID INVOICES (Already Have Transactions)")
        print(f"{'='*100}\n")

        for idx, inv in enumerate(paid_invoices, 1):
            print(f"{idx}. Invoice #{inv['invoice_number']}")
            print(f"   ID: {inv['id']}")
            print(f"   Date: {inv['date']}")
            print(f"   Amount: {inv['currency']} {inv['total_amount']:,.2f}")
            print(f"   Payment Status: {inv['payment_status']}")
            print(f"   Linked Transaction: {inv['linked_transaction_id']}")
            print(f"   Match Method: {inv['match_method']}")
            print(f"   Payment Date: {inv['payment_date']}")
            print()

    # Print other status invoices
    if other_invoices:
        print(f"\n{'='*100}")
        print(f"OTHER STATUS INVOICES")
        print(f"{'='*100}\n")

        for idx, inv in enumerate(other_invoices, 1):
            print(f"{idx}. Invoice #{inv['invoice_number']}")
            print(f"   ID: {inv['id']}")
            print(f"   Date: {inv['date']}")
            print(f"   Amount: {inv['currency']} {inv['total_amount']:,.2f}")
            print(f"   Payment Status: {inv['payment_status']}")
            print(f"   Linked Transaction: {inv['linked_transaction_id'] or 'None'}")
            print()

    # Return all invoices
    all_invoices = pending_invoices + paid_invoices + other_invoices

    print(f"\n{'='*100}")
    print(f"RECOMMENDATIONS:")
    print(f"{'='*100}\n")

    if pending_invoices:
        print(f"Found {len(pending_invoices)} pending invoices that need transactions created.")
        print(f"These invoices can be marked as paid using the new 'Mark as Paid' feature.")
        print(f"\nInvoice IDs to process:")
        for inv in pending_invoices:
            print(f"  - {inv['id']} (Invoice #{inv['invoice_number']}, {inv['currency']} {inv['total_amount']:,.2f})")
    else:
        print("All invoices are already marked as paid or have other statuses.")

    print()

    return all_invoices

if __name__ == '__main__':
    try:
        invoices = list_delta_invoices()
        print(f"\nScript completed successfully. Total invoices found: {len(invoices)}\n")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
