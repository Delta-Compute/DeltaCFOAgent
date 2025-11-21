#!/usr/bin/env python3
"""
Check if LLM-validated patterns were auto-created
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))
from database import db_manager

with db_manager.get_connection() as conn:
    cursor = conn.cursor()

    print('=' * 70)
    print('LLM-VALIDATED PATTERNS IN CLASSIFICATION_PATTERNS TABLE')
    print('=' * 70)

    cursor.execute("""
        SELECT pattern_id, description_pattern, entity, accounting_category,
               confidence_score, created_by, created_at
        FROM classification_patterns
        WHERE tenant_id = 'delta'
          AND created_by = 'llm_validated'
        ORDER BY created_at DESC
    """)

    patterns = cursor.fetchall()

    if patterns:
        print(f'\nFound {len(patterns)} LLM-validated pattern(s):\n')
        for pattern in patterns:
            print(f'Pattern ID {pattern[0]}:')
            print(f'  Description: {pattern[1][:80]}...')
            print(f'  Entity: {pattern[2]}')
            print(f'  Category: {pattern[3]}')
            print(f'  Confidence: {pattern[4]:.2f}')
            print(f'  Created: {pattern[6]}')
            print()
    else:
        print('\n❌ NO LLM-validated patterns found in classification_patterns table')
        print('This means pattern creation failed after LLM validation.\n')

    print('=' * 70)
    print('PATTERN NOTIFICATIONS')
    print('=' * 70)

    cursor.execute("""
        SELECT id, title, message, priority, created_at, is_read
        FROM pattern_notifications
        WHERE tenant_id = 'delta'
        ORDER BY created_at DESC
        LIMIT 10
    """)

    notifications = cursor.fetchall()

    if notifications:
        print(f'\nFound {len(notifications)} notification(s):\n')
        for notif in notifications:
            print(f'Notification ID {notif[0]}:')
            print(f'  Title: {notif[1]}')
            print(f'  Priority: {notif[3]}')
            print(f'  Read: {notif[5]}')
            print(f'  Created: {notif[4]}')
            print()
    else:
        print('\n❌ NO notifications found')

    cursor.close()

    print('=' * 70)
