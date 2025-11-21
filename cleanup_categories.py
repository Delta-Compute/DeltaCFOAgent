#!/usr/bin/env python3
"""
Script to clean up corrupted categories in the database
"""
import sys
import os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))

from database import db_manager

def find_corrupted_categories():
    """Find categories that look corrupted (too long, concatenated, etc.)"""

    print("=" * 80)
    print("ANALYZING CATEGORIES FOR CORRUPTION")
    print("=" * 80)

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        # Get all distinct categories
        cursor.execute("""
            SELECT accounting_category, COUNT(*) as count
            FROM transactions
            WHERE tenant_id = 'delta'
            AND accounting_category IS NOT NULL
            AND accounting_category != ''
            GROUP BY accounting_category
            ORDER BY LENGTH(accounting_category) DESC, accounting_category
        """)

        rows = cursor.fetchall()

        corrupted = []
        clean = []

        for row in rows:
            category = row[0] if isinstance(row, tuple) else row['accounting_category']
            count = row[1] if isinstance(row, tuple) else row['count']

            # Detect corruption patterns:
            # 1. Very long strings (> 100 chars)
            # 2. Contains multiple capital letter starts (camelCase concatenation)
            # 3. Contains special UI characters or patterns
            # 4. Contains "..."

            is_corrupted = False
            reason = []

            if len(category) > 100:
                is_corrupted = True
                reason.append("too long")

            if "..." in category or "Ask AI" in category or "+ Add" in category:
                is_corrupted = True
                reason.append("contains UI elements")

            # Count capital letters that start words (simple heuristic)
            caps_pattern = re.findall(r'[A-Z][a-z]+', category)
            if len(caps_pattern) > 10:
                is_corrupted = True
                reason.append("multiple concatenated values")

            if is_corrupted:
                corrupted.append({
                    'value': category,
                    'count': count,
                    'reasons': reason
                })
            else:
                clean.append({
                    'value': category,
                    'count': count
                })

        cursor.close()

        print(f"\nFound {len(clean)} clean categories")
        print(f"Found {len(corrupted)} corrupted categories\n")

        if corrupted:
            print("CORRUPTED CATEGORIES:")
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
    """Set corrupted categories to NULL"""

    print("=" * 80)
    if dry_run:
        print("DRY RUN - PROPOSED CLEANUP")
    else:
        print("EXECUTING CLEANUP")
    print("=" * 80)

    if not corrupted_list:
        print("\nNo corrupted categories to clean up!")
        return

    total_transactions = sum(item['count'] for item in corrupted_list)

    print(f"\nWill set {len(corrupted_list)} corrupted categories to NULL")
    print(f"This affects {total_transactions} transactions total\n")

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        for item in corrupted_list:
            category = item['value']
            count = item['count']

            if not dry_run:
                cursor.execute("""
                    UPDATE transactions
                    SET accounting_category = NULL
                    WHERE tenant_id = 'delta'
                    AND accounting_category = %s
                """, (category,))
                print(f"  Cleared {count} transactions with corrupted category")
            else:
                preview = category[:60] + "..." if len(category) > 60 else category
                print(f"  [DRY RUN] Would clear {count} transactions: '{preview}'")

        if not dry_run:
            conn.commit()
            print(f"\nCleanup completed! Cleared {total_transactions} transactions.")

        cursor.close()

def show_final_summary():
    """Show the final clean list of categories"""

    print("\n" + "=" * 80)
    print("FINAL CATEGORY LIST")
    print("=" * 80)

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT accounting_category, COUNT(*) as count
            FROM transactions
            WHERE tenant_id = 'delta'
            AND accounting_category IS NOT NULL
            AND accounting_category != ''
            AND LENGTH(accounting_category) < 100
            GROUP BY accounting_category
            ORDER BY accounting_category
        """)

        rows = cursor.fetchall()

        print(f"\nFound {len(rows)} clean, distinct categories:\n")

        for row in rows:
            category = row[0] if isinstance(row, tuple) else row['accounting_category']
            count = row[1] if isinstance(row, tuple) else row['count']
            print(f"  {category:<50} ({count:>6} transactions)")

        cursor.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Clean up corrupted categories')
    parser.add_argument('--execute', action='store_true', help='Execute the cleanup (default is dry-run)')
    args = parser.parse_args()

    # Step 1: Find corrupted categories
    corrupted, clean = find_corrupted_categories()

    # Step 2: Clean up corrupted entries
    cleanup_corrupted(corrupted, dry_run=not args.execute)

    # Step 3: Show final summary
    if args.execute:
        show_final_summary()

    if not args.execute:
        print("\n" + "=" * 80)
        print("To execute the cleanup, run:")
        print("  python cleanup_categories.py --execute")
        print("=" * 80)
