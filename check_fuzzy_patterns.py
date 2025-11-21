#!/usr/bin/env python3
"""
Check if fuzzy pattern matching is working and if patterns were created
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from web_ui.database import db_manager

with db_manager.get_connection() as conn:
    cursor = conn.cursor()

    print("=" * 70)
    print("FUZZY PATTERN MATCHING STATUS")
    print("=" * 70)

    # Check Bitcoin tracking records
    print("\n1. Bitcoin Transaction Records:")
    print("-" * 70)
    cursor.execute("""
        SELECT
            id,
            LEFT(description_pattern, 50) as description,
            normalized_pattern,
            field_changed,
            new_value
        FROM user_classification_tracking
        WHERE tenant_id = 'delta'
        AND normalized_pattern ILIKE '%bitcoin%'
        ORDER BY created_at DESC
    """)

    bitcoin_records = cursor.fetchall()
    print(f"Found {len(bitcoin_records)} Bitcoin transaction records\n")

    if bitcoin_records:
        # Group by normalized pattern
        normalized = bitcoin_records[0][2]
        print(f"All have normalized pattern: '{normalized}'")
        print(f"Field changed: {bitcoin_records[0][3]}")
        print(f"New value: {bitcoin_records[0][4]}")
        print(f"\nThis means {len(bitcoin_records)} matching transactions were found!")

    # Check pattern suggestions
    print("\n2. Pattern Suggestions Created:")
    print("-" * 70)
    cursor.execute("""
        SELECT
            id,
            description_pattern,
            entity,
            occurrence_count,
            confidence_score,
            status,
            created_at
        FROM pattern_suggestions
        WHERE tenant_id = 'delta'
        ORDER BY created_at DESC
    """)

    suggestions = cursor.fetchall()
    if suggestions:
        print(f"Found {len(suggestions)} pattern suggestion(s)\n")
        for sugg in suggestions:
            print(f"Pattern ID {sugg[0]}:")
            print(f"  Description: {sugg[1]}")
            print(f"  Entity: {sugg[2]}")
            print(f"  Occurrences: {sugg[3]}")
            print(f"  Confidence: {sugg[4]}")
            print(f"  Status: {sugg[5]}")
            print(f"  Created: {sugg[6]}")
            print()
    else:
        print("No pattern suggestions found.")
        print("\nDEBUG: Checking why no pattern was created...")
        print("\nThis could mean:")
        print("  1. Fuzzy matching trigger hasn't detected 3+ matches yet")
        print("  2. The trigger only fires on NEW inserts (not backfilled data)")
        print("\nSOLUTION: Manually categorize ONE more similar Bitcoin transaction")
        print("          and the trigger will create the pattern suggestion.")

    cursor.close()

    print("=" * 70)
