#!/usr/bin/env python3
"""
Fix date format from YYYY-DD-MM to YYYY-MM-DD in transactions table
"""
import sys
sys.path.append('web_ui')

from database import db_manager

try:
    # Find all transactions with month > 12 (these are in YYYY-DD-MM format)
    print("\n=== Finding transactions with incorrect date format ===")
    query = """
    SELECT transaction_id, date, description, amount
    FROM transactions
    WHERE tenant_id = 'delta'
    AND date LIKE '%-%-%'
    AND LENGTH(SPLIT_PART(date, '-', 2)) = 2
    AND CAST(SPLIT_PART(date, '-', 2) AS INTEGER) > 12;
    """

    bad_dates = db_manager.execute_query(query, fetch_all=True)
    print(f"Found {len(bad_dates)} transactions with dates in YYYY-DD-MM format")

    if bad_dates:
        # Fix each date by swapping month and day
        print("\n=== Fixing dates ===")
        update_query = """
        UPDATE transactions
        SET date = CONCAT(
            SPLIT_PART(date, '-', 1), '-',
            SPLIT_PART(date, '-', 3), '-',
            SPLIT_PART(date, '-', 2)
        )
        WHERE tenant_id = 'delta'
        AND date LIKE '%-%-%'
        AND LENGTH(SPLIT_PART(date, '-', 2)) = 2
        AND CAST(SPLIT_PART(date, '-', 2) AS INTEGER) > 12;
        """

        result = db_manager.execute_query(update_query)
        print(f"Updated {len(bad_dates)} transactions successfully")

        # Verify the fix
        print("\n=== Verifying fix ===")
        verify_query = """
        SELECT COUNT(*) as count
        FROM transactions
        WHERE tenant_id = 'delta'
        AND date LIKE '%-%-%'
        AND LENGTH(SPLIT_PART(date, '-', 2)) = 2
        AND CAST(SPLIT_PART(date, '-', 2) AS INTEGER) > 12;
        """

        verify_result = db_manager.execute_query(verify_query, fetch_one=True)
        if verify_result['count'] == 0:
            print("SUCCESS: All dates have been corrected!")
        else:
            print(f"WARNING: Still {verify_result['count']} dates with invalid format")

        # Show sample of corrected dates
        print("\n=== Sample of corrected dates ===")
        sample_query = """
        SELECT transaction_id, date, description
        FROM transactions
        WHERE tenant_id = 'delta'
        AND transaction_id = ANY(%s)
        LIMIT 10;
        """

        sample_ids = [row['transaction_id'] for row in bad_dates[:10]]
        samples = db_manager.execute_query(sample_query, (sample_ids,), fetch_all=True)
        for row in samples:
            print(f"  {row['date']} - {row['description'][:50]}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
