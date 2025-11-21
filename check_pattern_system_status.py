#!/usr/bin/env python3
"""
Check if the pattern learning system is working and show recent activity
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))
from database import db_manager

with db_manager.get_connection() as conn:
    cursor = conn.cursor()

    print('=' * 70)
    print('PATTERN LEARNING SYSTEM STATUS')
    print('=' * 70)

    # Check for recent user classifications
    cursor.execute("""
        SELECT COUNT(*), MAX(created_at) as last_classification
        FROM user_classification_tracking
        WHERE tenant_id = 'delta'
        AND created_at > NOW() - INTERVAL '1 hour'
    """)

    recent = cursor.fetchone()
    print(f'\n📊 USER CLASSIFICATIONS (Last 1 hour):')
    print(f'   Count: {recent[0]}')
    print(f'   Most recent: {recent[1] if recent[1] else "None"}')

    # Check pattern suggestions status
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM pattern_suggestions
        WHERE tenant_id = 'delta'
        GROUP BY status
        ORDER BY status
    """)

    print(f'\n💡 PATTERN SUGGESTIONS BY STATUS:')
    suggestions = cursor.fetchall()
    if suggestions:
        for status, count in suggestions:
            print(f'   {status}: {count}')
    else:
        print('   No pattern suggestions found')

    # Show recent pattern suggestions
    cursor.execute("""
        SELECT id, description_pattern, status, occurrence_count,
               confidence_score, created_at, llm_validated_at
        FROM pattern_suggestions
        WHERE tenant_id = 'delta'
        ORDER BY created_at DESC
        LIMIT 5
    """)

    print(f'\n🔍 MOST RECENT PATTERN SUGGESTIONS:')
    recent_suggestions = cursor.fetchall()
    if recent_suggestions:
        for sugg in recent_suggestions:
            pattern_preview = sugg[1][:60] + '...' if len(sugg[1]) > 60 else sugg[1]
            validated = '✓ Validated' if sugg[6] else '⏳ Pending'
            print(f'\n   ID {sugg[0]}: {sugg[2].upper()}')
            print(f'   Pattern: {pattern_preview}')
            print(f'   Occurrences: {sugg[3]} | Confidence: {sugg[4]:.2f}')
            print(f'   Created: {sugg[5]}')
            print(f'   Status: {validated}')
    else:
        print('   No pattern suggestions yet')

    # Check if trigger exists
    cursor.execute("""
        SELECT trigger_name, event_manipulation, action_statement
        FROM information_schema.triggers
        WHERE trigger_name LIKE '%pattern%'
        AND event_object_table = 'user_classification_tracking'
    """)

    print(f'\n⚙️  DATABASE TRIGGERS:')
    triggers = cursor.fetchall()
    if triggers:
        for trigger in triggers:
            print(f'   ✓ {trigger[0]} (on {trigger[1]})')
    else:
        print('   ❌ No pattern learning triggers found!')
        print('   System will NOT automatically create pattern suggestions')

    # Check recent notifications
    cursor.execute("""
        SELECT COUNT(*), MAX(created_at)
        FROM pattern_notifications
        WHERE tenant_id = 'delta'
        AND created_at > NOW() - INTERVAL '24 hours'
    """)

    notif = cursor.fetchone()
    print(f'\n🔔 PATTERN NOTIFICATIONS (Last 24 hours):')
    print(f'   Count: {notif[0]}')
    if notif[0] > 0:
        print(f'   Most recent: {notif[1]}')

    cursor.close()

    print('\n' + '=' * 70)
    print('HOW THE SYSTEM WORKS:')
    print('=' * 70)
    print("""
1. You classify transactions manually (entity, category, etc.)
2. After 3 similar classifications, a trigger creates a pattern suggestion
3. Pattern suggestions have status 'pending' initially
4. Run: python3 run_llm_pattern_validation.py
5. LLM validates each pending pattern
6. If approved → creates classification_pattern + notification
7. If rejected → updates status to 'rejected' with reasoning

TO SEE NEW PATTERNS:
- Check pattern_suggestions table for new entries (status: pending)
- Run LLM validation script manually
- Check pattern_notifications table for results
- Or check classification_patterns table for auto-created patterns
    """)
    print('=' * 70)
