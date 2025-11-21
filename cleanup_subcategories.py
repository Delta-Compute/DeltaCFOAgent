#!/usr/bin/env python3
"""
Script to analyze and clean up duplicate/corrupted subcategories
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))

from database import db_manager

def analyze_subcategories():
    """Analyze current subcategories and identify issues"""

    print("=" * 80)
    print("SUBCATEGORY ANALYSIS")
    print("=" * 80)

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        # Get all distinct subcategories with counts
        cursor.execute("""
            SELECT subcategory, COUNT(*) as count
            FROM transactions
            WHERE tenant_id = 'delta'
            AND subcategory IS NOT NULL
            AND subcategory != ''
            GROUP BY subcategory
            ORDER BY subcategory
        """)

        rows = cursor.fetchall()

        print(f"\nFound {len(rows)} distinct subcategories:\n")

        subcategories = {}
        for row in rows:
            subcat = row[0] if isinstance(row, tuple) else row['subcategory']
            count = row[1] if isinstance(row, tuple) else row['count']
            subcategories[subcat] = count
            print(f"  {subcat:<50} ({count:>6} transactions)")

        cursor.close()

    return subcategories

def identify_duplicates(subcategories):
    """Identify duplicate subcategories with different formats"""

    print("\n" + "=" * 80)
    print("IDENTIFYING DUPLICATES")
    print("=" * 80)

    # Normalize subcategories to find duplicates
    normalized_map = {}
    duplicates = []

    for subcat in subcategories.keys():
        # Normalize: lowercase, remove underscores, remove spaces
        normalized = subcat.lower().replace('_', '').replace(' ', '')

        if normalized in normalized_map:
            duplicates.append({
                'canonical': normalized_map[normalized],
                'duplicate': subcat,
                'canonical_count': subcategories[normalized_map[normalized]],
                'duplicate_count': subcategories[subcat]
            })
        else:
            normalized_map[normalized] = subcat

    if duplicates:
        print(f"\nFound {len(duplicates)} duplicate groups:\n")
        for dup in duplicates:
            print(f"  CANONICAL: {dup['canonical']:<40} ({dup['canonical_count']:>6} transactions)")
            print(f"  DUPLICATE: {dup['duplicate']:<40} ({dup['duplicate_count']:>6} transactions)")
            print()
    else:
        print("\nNo duplicates found!")

    return duplicates

def propose_cleanup(duplicates):
    """Propose cleanup operations"""

    if not duplicates:
        print("\nNo cleanup needed!")
        return []

    print("=" * 80)
    print("PROPOSED CLEANUP OPERATIONS")
    print("=" * 80)

    # Define canonical formats (preferred naming convention)
    canonical_formats = {
        'personalexpense': 'Personal',
        'personal': 'Personal',
        'operatingexpense': 'Operating Expense',
        'operating_expense': 'Operating Expense',
        'internaltransfer': 'Internal Transfer',
        'internal_transfer': 'Internal Transfer',
        'interestexpense': 'Interest Expense',
        'interest_expense': 'Interest Expense',
        'payrollexpense': 'Payroll Expense',
        'payroll_expense': 'Payroll Expense',
        'otherincome': 'Other Income',
        'other_income': 'Other Income',
        'otherexpense': 'Other Expense',
        'other_expense': 'Other Expense',
        'revenue': 'Revenue',
        'refund': 'Refund',
        'trading': 'Trading',
        'technologyexpenses': 'Technology Expenses',
        'technology_expenses': 'Technology Expenses',
        'investorequity': 'Investor Equity',
        'investor_equity': 'Investor Equity',
        'invoicepayment': 'Invoice Payment',
        'invoice_payment': 'Invoice Payment',
        'uncategorized': 'Uncategorized',
        'workforce': 'Work Force',
        'workforcecapex': 'Work Force CAPEX',
    }

    operations = []

    # Collect all subcategories that need updating
    all_subcats = set()
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT subcategory
            FROM transactions
            WHERE tenant_id = 'delta'
            AND subcategory IS NOT NULL
            AND subcategory != ''
        """)
        rows = cursor.fetchall()
        for row in rows:
            all_subcats.add(row[0] if isinstance(row, tuple) else row['subcategory'])
        cursor.close()

    # Map each subcategory to its canonical form
    for subcat in all_subcats:
        normalized = subcat.lower().replace('_', '').replace(' ', '')
        if normalized in canonical_formats:
            canonical = canonical_formats[normalized]
            if subcat != canonical:
                operations.append({
                    'from': subcat,
                    'to': canonical
                })

    if operations:
        print(f"\nWill update {len(operations)} subcategory variants:\n")
        for op in operations:
            print(f"  {op['from']:<50} -> {op['to']}")

    return operations

def execute_cleanup(operations, dry_run=True):
    """Execute the cleanup operations"""

    if not operations:
        print("\nNo operations to execute!")
        return

    print("\n" + "=" * 80)
    if dry_run:
        print("DRY RUN - NO CHANGES WILL BE MADE")
    else:
        print("EXECUTING CLEANUP")
    print("=" * 80)

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        for op in operations:
            from_subcat = op['from']
            to_subcat = op['to']

            # Count how many will be updated
            cursor.execute("""
                SELECT COUNT(*)
                FROM transactions
                WHERE tenant_id = 'delta'
                AND subcategory = %s
            """, (from_subcat,))
            count = cursor.fetchone()[0] if isinstance(cursor.fetchone(), tuple) else cursor.fetchone()

            # Reset cursor after fetchone
            cursor.execute("""
                SELECT COUNT(*)
                FROM transactions
                WHERE tenant_id = 'delta'
                AND subcategory = %s
            """, (from_subcat,))
            count_row = cursor.fetchone()
            count = count_row[0] if isinstance(count_row, tuple) else count_row

            if not dry_run:
                cursor.execute("""
                    UPDATE transactions
                    SET subcategory = %s
                    WHERE tenant_id = 'delta'
                    AND subcategory = %s
                """, (to_subcat, from_subcat))
                print(f"  ✅ Updated {count} transactions: '{from_subcat}' -> '{to_subcat}'")
            else:
                print(f"  [DRY RUN] Would update {count} transactions: '{from_subcat}' -> '{to_subcat}'")

        if not dry_run:
            conn.commit()
            print(f"\n✅ Cleanup completed! Updated {len(operations)} subcategory variants.")
        else:
            print(f"\n[DRY RUN] Would update {len(operations)} subcategory variants.")

        cursor.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Clean up duplicate subcategories')
    parser.add_argument('--execute', action='store_true', help='Execute the cleanup (default is dry-run)')
    args = parser.parse_args()

    # Step 1: Analyze current state
    subcategories = analyze_subcategories()

    # Step 2: Identify duplicates
    duplicates = identify_duplicates(subcategories)

    # Step 3: Propose cleanup
    operations = propose_cleanup(duplicates)

    # Step 4: Execute cleanup
    execute_cleanup(operations, dry_run=not args.execute)

    if not args.execute and operations:
        print("\n" + "=" * 80)
        print("To execute the cleanup, run:")
        print("  python cleanup_subcategories.py --execute")
        print("=" * 80)
