#!/usr/bin/env python3
"""
Fix Invalid Transaction Dates
Removes transactions with invalid date values like 'Na', 'NaN', NULL, etc.
"""
import sys
sys.path.insert(0, 'web_ui')
from database import DatabaseManager

def fix_invalid_dates():
    db = DatabaseManager()

    print("=" * 80)
    print("FIXING INVALID TRANSACTION DATES")
    print("=" * 80)

    # Check for transactions with invalid dates
    check_query = """
    SELECT COUNT(*) as count
    FROM transactions
    WHERE date IS NULL
       OR date::text IN ('Na', 'NaN', 'NULL', '', 'nan')
       OR (description IS NULL OR description = 'nan')
    """

    result = db.execute_query(check_query, fetch_one=True)
    count = result.get('count', 0) if result else 0

    print(f"\nFound {count} transaction(s) with invalid dates or descriptions")

    if count == 0:
        print("\nNo invalid transactions found. Database is clean!")
        return

    # Show the invalid transactions
    show_query = """
    SELECT transaction_id, date, description, amount, classified_entity
    FROM transactions
    WHERE date IS NULL
       OR date::text IN ('Na', 'NaN', 'NULL', '', 'nan')
       OR (description IS NULL OR description = 'nan')
    LIMIT 20
    """

    invalid_txns = db.execute_query(show_query, fetch_all=True)

    print("\nInvalid transactions:")
    for txn in invalid_txns:
        print(f"  - ID: {txn.get('transaction_id', 'N/A')}")
        print(f"    Date: {txn.get('date', 'NULL')}")
        print(f"    Description: {txn.get('description', 'NULL')[:50]}")
        print(f"    Amount: {txn.get('amount', 0)}")
        print(f"    Entity: {txn.get('classified_entity', 'N/A')}")
        print()

    # Delete invalid transactions
    delete_query = """
    DELETE FROM transactions
    WHERE date IS NULL
       OR date::text IN ('Na', 'NaN', 'NULL', '', 'nan')
       OR (description IS NULL OR description = 'nan')
    RETURNING transaction_id
    """

    deleted = db.execute_query(delete_query, fetch_all=True)

    print(f"\nDeleted {len(deleted)} invalid transaction(s)")
    print("\nDatabase cleaned successfully!")
    print("=" * 80)

if __name__ == '__main__':
    try:
        fix_invalid_dates()
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
