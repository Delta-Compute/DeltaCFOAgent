#!/usr/bin/env python3
"""Check pattern learning status after trigger fix"""

import sys
sys.path.insert(0, '/Users/whitdhamer/DeltaCFOAgentv2/web_ui')

from database import DatabaseManager

db_manager = DatabaseManager()

print("=" * 80)
print("PATTERN LEARNING STATUS CHECK")
print("=" * 80)

# Check user classification tracking
print("\n1. USER CLASSIFICATION TRACKING:")
query = """
    SELECT
        COUNT(*) as total,
        COUNT(DISTINCT description_pattern) as unique_patterns,
        COUNT(DISTINCT new_value) as unique_values
    FROM user_classification_tracking
    WHERE tenant_id = 'delta'
"""
result = db_manager.execute_query(query, fetch_one=True)
if result:
    print(f"   Total classifications: {result['total']}")
    print(f"   Unique description patterns: {result['unique_patterns']}")
    print(f"   Unique values: {result['unique_values']}")

# Check for patterns with 3+ occurrences
print("\n2. PATTERNS WITH 3+ OCCURRENCES (Should trigger suggestions):")
query = """
    SELECT
        new_value,
        description_pattern,
        origin,
        destination,
        COUNT(*) as occurrences
    FROM user_classification_tracking
    WHERE tenant_id = 'delta'
    GROUP BY new_value, description_pattern, origin, destination
    HAVING COUNT(*) >= 3
    ORDER BY occurrences DESC
    LIMIT 10
"""
result = db_manager.execute_query(query, fetch_all=True)
if result and len(result) > 0:
    for row in result:
        print(f"   Value: {row['new_value']}")
        print(f"   Pattern: {row['description_pattern']}")
        print(f"   Origin: {row['origin']}")
        print(f"   Destination: {row['destination']}")
        print(f"   Count: {row['occurrences']}")
        print()
else:
    print("   No patterns with 3+ occurrences found")

# Check pattern suggestions
print("\n3. PATTERN SUGGESTIONS (Created by trigger):")
query = """
    SELECT
        id,
        pattern_type,
        pattern_data,
        supporting_classifications_count,
        status,
        created_at
    FROM pattern_suggestions
    WHERE tenant_id = 'delta'
    ORDER BY created_at DESC
    LIMIT 10
"""
result = db_manager.execute_query(query, fetch_all=True)
if result and len(result) > 0:
    print(f"   Total pattern suggestions: {len(result)}")
    for row in result:
        print(f"   ID: {row['id']} | Type: {row['pattern_type']} | Count: {row['supporting_classifications_count']} | Status: {row['status']}")
else:
    print("   No pattern suggestions found")

# Check pattern notifications
print("\n4. PATTERN NOTIFICATIONS:")
query = """
    SELECT
        COUNT(*) as total,
        COUNT(CASE WHEN is_read = false THEN 1 END) as unread
    FROM pattern_notifications
    WHERE tenant_id = 'delta'
"""
result = db_manager.execute_query(query, fetch_one=True)
if result:
    print(f"   Total notifications: {result['total']}")
    print(f"   Unread notifications: {result['unread']}")

# Check trigger function
print("\n5. TRIGGER FUNCTION STATUS:")
query = """
    SELECT
        t.tgname as trigger_name,
        c.relname as table_name,
        p.proname as function_name
    FROM pg_trigger t
    JOIN pg_class c ON t.tgrelid = c.oid
    JOIN pg_proc p ON t.tgfoid = p.oid
    WHERE c.relname = 'user_classification_tracking'
    AND p.proname LIKE '%pattern%'
"""
result = db_manager.execute_query(query, fetch_all=True)
if result and len(result) > 0:
    for row in result:
        print(f"   Trigger: {row['trigger_name']} on table {row['table_name']} calls function {row['function_name']}")
else:
    print("   No pattern-related triggers found")

print("\n" + "=" * 80)
print("ANALYSIS:")
print("=" * 80)

# Get the counts for analysis
query = "SELECT COUNT(*) as count FROM user_classification_tracking WHERE tenant_id = 'delta'"
result = db_manager.execute_query(query, fetch_one=True)
tracking_count = result['count'] if result else 0

query = "SELECT COUNT(*) as count FROM pattern_suggestions WHERE tenant_id = 'delta'"
result = db_manager.execute_query(query, fetch_one=True)
suggestions_count = result['count'] if result else 0

query = """
    SELECT COUNT(*) as count
    FROM (
        SELECT new_value, description_pattern
        FROM user_classification_tracking
        WHERE tenant_id = 'delta'
        GROUP BY new_value, description_pattern
        HAVING COUNT(*) >= 3
    ) t
"""
result = db_manager.execute_query(query, fetch_one=True)
eligible_patterns = result['count'] if result else 0

if tracking_count > 0:
    print(f"\n✓ Found {tracking_count} user classifications in tracking table")

    if eligible_patterns > 0:
        print(f"✓ Found {eligible_patterns} pattern(s) with 3+ occurrences that should trigger suggestions")

        if suggestions_count == 0:
            print("✗ BUT no pattern suggestions were created!")
            print("\nPOSSIBLE CAUSES:")
            print("  1. Trigger function not firing (check trigger exists)")
            print("  2. Trigger logic still has issues with NULL values")
            print("  3. Description similarity not matching")
            print("\nRECOMMENDATION:")
            print("  Manually insert a test record into user_classification_tracking")
            print("  and see if trigger creates a pattern_suggestion")
        else:
            print(f"✓ Created {suggestions_count} pattern suggestion(s)")
            print("\nNEXT STEP:")
            print("  Run LLM validation: POST /api/pattern-learning/process")
    else:
        print("○ No patterns with 3+ occurrences yet")
        print("  User needs to categorize 3 similar transactions to trigger pattern learning")
else:
    print("✗ No user classifications found in tracking table")
    print("  The trigger won't fire because no classifications have been recorded")

db_manager.close()
