"""
Migrate Existing Payment Data
Migrates payment data from invoices table (single payment) to invoice_payments table (multiple payments)
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_ui.database import db_manager
import uuid


def migrate_payment_data(dry_run=False):
    """Migrate existing payment data from invoices table to invoice_payments table"""

    print("=" * 80)
    print("MIGRATE EXISTING PAYMENT DATA")
    print("=" * 80)
    print()

    if dry_run:
        print("[DRY RUN MODE - No changes will be made]")
        print()

    # Step 1: Get all invoices with payment data
    print("Step 1: Finding invoices with payment data...")

    query = """
        SELECT
            id,
            tenant_id,
            payment_status,
            payment_date,
            payment_method,
            total_amount,
            currency,
            invoice_number
        FROM invoices
        WHERE payment_status = 'paid'
           OR payment_date IS NOT NULL
        ORDER BY payment_date DESC
    """

    try:
        invoices = db_manager.execute_query(query, fetch_all=True)

        if not invoices:
            print("  [INFO] No invoices with payment data found")
            return True

        print(f"  [OK] Found {len(invoices)} invoices with payment data")
        print()

    except Exception as e:
        print(f"  [ERROR] Failed to query invoices: {e}")
        return False

    # Step 2: Preview migration
    print("Step 2: Migration Preview")
    print("-" * 80)

    migration_plan = []

    for invoice in invoices:
        # Check if payment already exists in new table
        check_query = """
            SELECT COUNT(*) as count
            FROM invoice_payments
            WHERE invoice_id = %s AND tenant_id = %s
        """

        existing = db_manager.execute_query(
            check_query,
            (invoice['id'], invoice['tenant_id']),
            fetch_one=True
        )

        if existing and existing['count'] > 0:
            print(f"  [SKIP] Invoice {invoice['invoice_number']} - Already has {existing['count']} payment(s) in new table")
            continue

        payment_data = {
            'invoice_id': invoice['id'],
            'tenant_id': invoice['tenant_id'],
            'invoice_number': invoice['invoice_number'],
            'payment_date': invoice['payment_date'],
            'payment_amount': float(invoice['total_amount']),
            'payment_currency': invoice['currency'] or 'USD',
            'payment_method': invoice['payment_method'],
            'payment_status': invoice['payment_status']
        }

        migration_plan.append(payment_data)

        print(f"  [MIGRATE] Invoice {invoice['invoice_number']}")
        print(f"            Amount: {payment_data['payment_currency']} {payment_data['payment_amount']}")
        print(f"            Date: {payment_data['payment_date'] or 'Not set'}")
        print(f"            Method: {payment_data['payment_method'] or 'Not specified'}")
        print()

    if not migration_plan:
        print("  [INFO] All invoices already migrated or no migration needed")
        return True

    print(f"Total invoices to migrate: {len(migration_plan)}")
    print()

    if dry_run:
        print("[DRY RUN] Would migrate the above payments")
        return True

    # Step 3: Confirm migration
    print("=" * 80)
    print("WARNING: This will create payment records in the invoice_payments table.")
    print("=" * 80)
    confirm = input("Type 'yes' to proceed with migration: ")

    if confirm.lower() != 'yes':
        print("Migration cancelled.")
        return False

    # Step 4: Execute migration
    print()
    print("Step 3: Migrating payment data...")

    success_count = 0
    error_count = 0

    for payment in migration_plan:
        try:
            # Only create payment record if there's a valid date
            if not payment['payment_date']:
                print(f"  [SKIP] {payment['invoice_number']} - No payment date")
                continue

            payment_id = str(uuid.uuid4())

            insert_query = """
                INSERT INTO invoice_payments (
                    id,
                    invoice_id,
                    tenant_id,
                    payment_date,
                    payment_amount,
                    payment_currency,
                    payment_method,
                    payment_notes,
                    recorded_by,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """

            db_manager.execute_query(
                insert_query,
                (
                    payment_id,
                    payment['invoice_id'],
                    payment['tenant_id'],
                    payment['payment_date'],
                    payment['payment_amount'],
                    payment['payment_currency'],
                    payment['payment_method'],
                    'Migrated from legacy payment data',
                    'migration_script'
                )
            )

            print(f"  [OK] Migrated {payment['invoice_number']}")
            success_count += 1

        except Exception as e:
            print(f"  [ERROR] Failed to migrate {payment['invoice_number']}: {e}")
            error_count += 1

    print()
    print("=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Successfully migrated: {success_count}")
    print(f"Errors: {error_count}")
    print()

    if success_count > 0:
        print("Next steps:")
        print("1. Verify migrated payments in the UI (Invoices → Payment tab)")
        print("2. Check that invoice payment statuses are correct")
        print("3. Optionally, you can clean up the old payment columns in invoices table:")
        print("   - payment_date")
        print("   - payment_method")
        print("   Note: payment_status column is still used by the system")
        print()

    return error_count == 0


def verify_migration():
    """Verify the migration was successful"""

    print("=" * 80)
    print("VERIFY MIGRATION")
    print("=" * 80)
    print()

    # Check invoice_payments table
    print("Step 1: Checking invoice_payments table...")

    try:
        query = """
            SELECT
                COUNT(*) as total_payments,
                COUNT(DISTINCT invoice_id) as unique_invoices,
                SUM(payment_amount) as total_amount,
                MIN(payment_date) as earliest_payment,
                MAX(payment_date) as latest_payment
            FROM invoice_payments
        """

        stats = db_manager.execute_query(query, fetch_one=True)

        print(f"  Total payment records: {stats['total_payments']}")
        print(f"  Unique invoices with payments: {stats['unique_invoices']}")
        print(f"  Total amount: ${stats['total_amount'] or 0:,.2f}")
        print(f"  Date range: {stats['earliest_payment']} to {stats['latest_payment']}")
        print()

    except Exception as e:
        print(f"  [ERROR] Failed to query payment stats: {e}")
        return False

    # Check for invoices with mismatched status
    print("Step 2: Checking for status mismatches...")

    try:
        query = """
            SELECT
                i.id,
                i.invoice_number,
                i.payment_status as invoice_status,
                i.total_amount,
                COALESCE(SUM(p.payment_amount), 0) as total_paid,
                COUNT(p.id) as payment_count
            FROM invoices i
            LEFT JOIN invoice_payments p ON i.id = p.invoice_id AND i.tenant_id = p.tenant_id
            WHERE i.payment_status IN ('paid', 'partially_paid')
            GROUP BY i.id, i.invoice_number, i.payment_status, i.total_amount
            HAVING COUNT(p.id) = 0 OR (
                i.payment_status = 'paid' AND COALESCE(SUM(p.payment_amount), 0) < i.total_amount
            )
            ORDER BY i.invoice_number
        """

        mismatches = db_manager.execute_query(query, fetch_all=True)

        if mismatches:
            print(f"  [WARNING] Found {len(mismatches)} invoices with status mismatches:")
            for invoice in mismatches[:10]:  # Show first 10
                print(f"    - {invoice['invoice_number']}: Status={invoice['invoice_status']}, "
                      f"Total=${invoice['total_amount']}, Paid=${invoice['total_paid']}, "
                      f"Payments={invoice['payment_count']}")
            if len(mismatches) > 10:
                print(f"    ... and {len(mismatches) - 10} more")
        else:
            print("  [OK] No status mismatches found")

        print()

    except Exception as e:
        print(f"  [ERROR] Failed to check mismatches: {e}")
        return False

    print("[SUCCESS] Verification complete")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Migrate existing payment data to new system')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without making changes')
    parser.add_argument('--verify', action='store_true',
                        help='Verify the migration was successful')
    parser.add_argument('--execute', action='store_true',
                        help='Execute the migration (required for actual changes)')

    args = parser.parse_args()

    if args.verify:
        success = verify_migration()
    elif args.execute or args.dry_run:
        success = migrate_payment_data(dry_run=args.dry_run)
    else:
        parser.print_help()
        print()
        print("Examples:")
        print("  python migrate_existing_payment_data.py --dry-run    # Preview migration")
        print("  python migrate_existing_payment_data.py --execute    # Execute migration")
        print("  python migrate_existing_payment_data.py --verify     # Verify after migration")
        sys.exit(0)

    sys.exit(0 if success else 1)
