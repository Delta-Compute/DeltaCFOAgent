#!/usr/bin/env python3
"""
Migration: Backfill Transactions for Existing Paid Payslips

This script creates transaction records for all existing paid payslips
that don't have a linked transaction_id.

Purpose:
- Fix historical data where payslips were marked "paid" but no transactions created
- Ensures all payslips appear in financial reports and Sankey diagrams
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'web_ui'))

from database import db_manager
import uuid
from datetime import datetime

def backfill_payslip_transactions(tenant_id='delta', dry_run=True):
    """
    Create transactions for all paid payslips without transaction_id

    Args:
        tenant_id: Tenant to process (default: 'delta')
        dry_run: If True, show what would be done without making changes
    """

    print(f"\n{'='*80}")
    print(f"PAYSLIP TRANSACTION BACKFILL - {'DRY RUN' if dry_run else 'LIVE RUN'}")
    print(f"Tenant: {tenant_id}")
    print(f"{'='*80}\n")

    # Find paid payslips without transactions
    query = """
        SELECT
            p.id, p.payslip_number, p.payment_date, p.gross_amount,
            p.net_amount, p.currency, p.transaction_id,
            w.full_name as employee_name, w.employment_type
        FROM payslips p
        JOIN workforce_members w ON p.workforce_member_id = w.id
        WHERE p.tenant_id = %s
          AND p.status = 'paid'
          AND p.transaction_id IS NULL
        ORDER BY p.payment_date DESC
    """

    payslips = db_manager.execute_query(query, (tenant_id,), fetch_all=True)

    print(f"Found {len(payslips)} paid payslips without transactions\n")

    if not payslips:
        print("No payslips to process. Exiting.")
        return

    # Show summary
    total_amount = sum(float(p['net_amount']) for p in payslips)
    print(f"Summary:")
    print(f"  - Total payslips: {len(payslips)}")
    print(f"  - Total net amount: ${total_amount:,.2f}")
    print(f"  - Date range: {payslips[-1]['payment_date']} to {payslips[0]['payment_date']}")
    print()

    if dry_run:
        print("DRY RUN - Showing what would be created:\n")
        for i, payslip in enumerate(payslips[:10], 1):  # Show first 10
            print(f"{i}. {payslip['payslip_number']}: {payslip['employee_name']}")
            print(f"   Date: {payslip['payment_date']}, Amount: ${payslip['net_amount']}")
            print(f"   Would create transaction: Payroll - {payslip['employee_name']} - {payslip['employment_type']}\n")

        if len(payslips) > 10:
            print(f"... and {len(payslips) - 10} more payslips\n")

        print("\nTo execute this migration, run:")
        print(f"  python {__file__} --execute")
        return

    # LIVE RUN - Create transactions
    print("LIVE RUN - Creating transactions...\n")

    created_count = 0
    failed_count = 0

    insert_txn_query = """
        INSERT INTO transactions (
            transaction_id, tenant_id, date, description, amount, currency,
            accounting_category, subcategory, classified_entity, origin, destination,
            justification, source_file, confidence, classification_reason,
            created_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            CURRENT_TIMESTAMP
        )
    """

    update_payslip_query = """
        UPDATE payslips
        SET transaction_id = %s
        WHERE id = %s AND tenant_id = %s
    """

    for payslip in payslips:
        try:
            # Generate transaction ID
            transaction_id = str(uuid.uuid4())

            # Prepare transaction data
            description = f"Payroll - {payslip['employee_name']} - {payslip['employment_type']}"
            amount = -abs(float(payslip['net_amount']))  # Negative for expense
            justification = f"Payroll payment to {payslip['employee_name']} - Payslip #{payslip['payslip_number']} (Backfilled)"

            # Insert transaction
            db_manager.execute_query(insert_txn_query, (
                transaction_id,
                tenant_id,
                payslip['payment_date'],
                description,
                amount,
                payslip.get('currency', 'USD'),
                'Payroll Expense',
                'Salary Payment',
                tenant_id,  # Default entity to tenant
                'Company',
                payslip['employee_name'],
                justification,
                f"payslip_{payslip['payslip_number']}",
                1.0,  # High confidence - direct from payslip
                'Automated payslip transaction creation (backfill migration)'
            ))

            # Update payslip with transaction link
            db_manager.execute_query(update_payslip_query, (
                transaction_id,
                payslip['id'],
                tenant_id
            ))

            created_count += 1
            print(f"✓ Created transaction for {payslip['payslip_number']}: {payslip['employee_name']} (${amount})")

        except Exception as e:
            failed_count += 1
            print(f"✗ Failed to create transaction for {payslip['payslip_number']}: {e}")

    print(f"\n{'='*80}")
    print(f"BACKFILL COMPLETE")
    print(f"{'='*80}")
    print(f"  Created: {created_count}")
    print(f"  Failed:  {failed_count}")
    print(f"  Total:   {len(payslips)}")
    print()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Backfill transactions for paid payslips')
    parser.add_argument('--execute', action='store_true', help='Execute the migration (default is dry-run)')
    parser.add_argument('--tenant', default='delta', help='Tenant ID to process (default: delta)')

    args = parser.parse_args()

    backfill_payslip_transactions(
        tenant_id=args.tenant,
        dry_run=not args.execute
    )
