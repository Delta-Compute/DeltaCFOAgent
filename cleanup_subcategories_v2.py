#!/usr/bin/env python3
"""
Script to clean up corrupted subcategories in the database
"""
import sys
import os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))

from database import db_manager

def find_corrupted_subcategories():
    """Find subcategories that look corrupted (too long, concatenated, etc.)"""

    print("=" * 80)
    print("ANALYZING SUBCATEGORIES FOR CORRUPTION")
    print("=" * 80)

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        # Get all distinct subcategories
        cursor.execute("""
            SELECT subcategory, COUNT(*) as count
            FROM transactions
            WHERE tenant_id = 'delta'
            AND subcategory IS NOT NULL
            AND subcategory != ''
            GROUP BY subcategory
            ORDER BY LENGTH(subcategory) DESC, subcategory
        """)

        rows = cursor.fetchall()

        corrupted = []
        clean = []

        for row in rows:
            subcat = row[0] if isinstance(row, tuple) else row['subcategory']
            count = row[1] if isinstance(row, tuple) else row['count']

            # Detect corruption patterns:
            # 1. Very long strings (> 100 chars)
            # 2. Contains multiple capital letter starts (camelCase concatenation)
            # 3. Contains "🤖" or "+ Add"
            # 4. Contains "..."

            is_corrupted = False
            reason = []

            if len(subcat) > 100:
                is_corrupted = True
                reason.append("too long")

            if "🤖" in subcat or "+ Add" in subcat or "..." in subcat:
                is_corrupted = True
                reason.append("contains UI elements")

            # Count capital letters that start words (simple heuristic)
            caps_pattern = re.findall(r'[A-Z][a-z]+', subcat)
            if len(caps_pattern) > 5:
                is_corrupted = True
                reason.append("multiple concatenated values")

            if is_corrupted:
                corrupted.append({
                    'value': subcat,
                    'count': count,
                    'reasons': reason
                })
            else:
                clean.append({
                    'value': subcat,
                    'count': count
                })

        cursor.close()

        print(f"\nFound {len(clean)} clean subcategories")
        print(f"Found {len(corrupted)} corrupted subcategories\n")

        if corrupted:
            print("CORRUPTED SUBCATEGORIES:")
            print("-" * 80)
            for item in corrupted[:10]:  # Show first 10
                preview = item['value'][:80] + "..." if len(item['value']) > 80 else item['value']
                print(f"  [{item['count']:>4} txns] {preview}")
                print(f"             Reasons: {', '.join(item['reasons'])}")
                print()

        if len(corrupted) > 10:
            print(f"  ... and {len(corrupted) - 10} more corrupted entries\n")

        return corrupted, clean

def cleanup_corrupted(corrupted_list, dry_run=True):
    """Set corrupted subcategories to NULL"""

    print("=" * 80)
    if dry_run:
        print("DRY RUN - PROPOSED CLEANUP")
    else:
        print("EXECUTING CLEANUP")
    print("=" * 80)

    if not corrupted_list:
        print("\nNo corrupted subcategories to clean up!")
        return

    total_transactions = sum(item['count'] for item in corrupted_list)

    print(f"\nWill set {len(corrupted_list)} corrupted subcategories to NULL")
    print(f"This affects {total_transactions} transactions total\n")

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        for item in corrupted_list:
            subcat = item['value']
            count = item['count']

            if not dry_run:
                cursor.execute("""
                    UPDATE transactions
                    SET subcategory = NULL
                    WHERE tenant_id = 'delta'
                    AND subcategory = %s
                """, (subcat,))
                print(f"  ✅ Cleared {count} transactions with corrupted subcategory")
            else:
                preview = subcat[:60] + "..." if len(subcat) > 60 else subcat
                print(f"  [DRY RUN] Would clear {count} transactions: '{preview}'")

        if not dry_run:
            conn.commit()
            print(f"\n✅ Cleanup completed! Cleared {total_transactions} transactions.")

        cursor.close()

def standardize_subcategories(dry_run=True):
    """Standardize subcategory naming conventions"""

    print("\n" + "=" * 80)
    print("STANDARDIZING SUBCATEGORY NAMING")
    print("=" * 80)

    # Define standardization mappings
    mappings = {
        # Personal variations
        'personal expance': 'Personal',
        'Personal expance': 'Personal',
        'Personal Expances': 'Personal',
        'personal expanses': 'Personal',
        'Personal expanses': 'Personal',
        'Pesonal expance': 'Personal',
        'Personal Expense': 'Personal',
        'Personal Expenses': 'Personal',
        'personal expense': 'Personal',
        'personal expenses': 'Personal',

        # Gas fee variations
        'Gas fee': 'Gas Fees',
        'gas fee': 'Gas Fees',
        'gas fees': 'Gas Fees',
        'Gash fees': 'Gas Fees',
        'Gas Fee': 'Gas Fees',

        # Technology variations
        'Technology expense': 'Technology Expenses',
        'Technology Expense': 'Technology Expenses',
        'Technology Espenses': 'Technology Expenses',
        'technology expense': 'Technology Expenses',

        # Investor equity
        'Investor equity': 'Investor Equity',
        'investor equity': 'Investor Equity',

        # Infrastructure
        'infra investment': 'Infrastructure Investment',
        'Infra Investment': 'Infrastructure Investment',

        # Transaction fees
        'transaction fee': 'Transaction Fees',
        'Transaction fee': 'Transaction Fees',

        # Food
        'food': 'Food & Drink',
        'Food': 'Food & Drink',

        # Health/Healthcare
        'Healthcare & Wellness': 'Health & Wellness',
        'healthcare & wellness': 'Health & Wellness',

        # Fuel
        'Fuel': 'Fuel & Gas',
        'Fuel Expense': 'Fuel & Gas',
        'fuel expense': 'Fuel & Gas',

        # Meals
        'Meals': 'Employee Meals',
        'meals': 'Employee Meals',

        # Materials/Supplies
        'Materials': 'Supplies & Materials',
        'materials': 'Supplies & Materials',
    }

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        updates_made = 0

        for old_value, new_value in mappings.items():
            # Check if this subcategory exists
            cursor.execute("""
                SELECT COUNT(*)
                FROM transactions
                WHERE tenant_id = 'delta'
                AND subcategory = %s
            """, (old_value,))

            result = cursor.fetchone()
            count = result[0] if isinstance(result, tuple) else result

            if count > 0:
                if not dry_run:
                    cursor.execute("""
                        UPDATE transactions
                        SET subcategory = %s
                        WHERE tenant_id = 'delta'
                        AND subcategory = %s
                    """, (new_value, old_value))
                    print(f"  ✅ Standardized {count} transactions: '{old_value}' -> '{new_value}'")
                    updates_made += 1
                else:
                    print(f"  [DRY RUN] Would standardize {count} transactions: '{old_value}' -> '{new_value}'")
                    updates_made += 1

        if not dry_run and updates_made > 0:
            conn.commit()
            print(f"\n✅ Standardization completed! Updated {updates_made} subcategory variants.")
        elif updates_made > 0:
            print(f"\n[DRY RUN] Would update {updates_made} subcategory variants.")
        else:
            print("\nNo standardization needed!")

        cursor.close()

def show_final_summary():
    """Show the final clean list of subcategories"""

    print("\n" + "=" * 80)
    print("FINAL SUBCATEGORY LIST")
    print("=" * 80)

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT subcategory, COUNT(*) as count
            FROM transactions
            WHERE tenant_id = 'delta'
            AND subcategory IS NOT NULL
            AND subcategory != ''
            AND LENGTH(subcategory) < 100
            GROUP BY subcategory
            ORDER BY subcategory
        """)

        rows = cursor.fetchall()

        print(f"\nFound {len(rows)} clean, distinct subcategories:\n")

        for row in rows:
            subcat = row[0] if isinstance(row, tuple) else row['subcategory']
            count = row[1] if isinstance(row, tuple) else row['count']
            print(f"  {subcat:<50} ({count:>6} transactions)")

        cursor.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Clean up corrupted subcategories')
    parser.add_argument('--execute', action='store_true', help='Execute the cleanup (default is dry-run)')
    args = parser.parse_args()

    # Step 1: Find corrupted subcategories
    corrupted, clean = find_corrupted_subcategories()

    # Step 2: Clean up corrupted entries
    cleanup_corrupted(corrupted, dry_run=not args.execute)

    # Step 3: Standardize naming conventions
    standardize_subcategories(dry_run=not args.execute)

    # Step 4: Show final summary
    if args.execute:
        show_final_summary()

    if not args.execute:
        print("\n" + "=" * 80)
        print("To execute the cleanup, run:")
        print("  python cleanup_subcategories_v2.py --execute")
        print("=" * 80)
