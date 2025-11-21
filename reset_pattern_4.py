#!/usr/bin/env python3
"""
Reset pattern #4 (the approved one with 7 occurrences) to test successful pattern creation
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))
from database import db_manager

with db_manager.get_connection() as conn:
    cursor = conn.cursor()

    print('=' * 70)
    print('RESETTING PATTERN #4 TO PENDING FOR TESTING')
    print('=' * 70)

    # Reset pattern ID 4 (the one with 7 occurrences that should be approved)
    cursor.execute("""
        UPDATE pattern_suggestions
        SET status = 'pending',
            llm_validation_result = NULL,
            llm_validated_at = NULL,
            validation_model = NULL
        WHERE tenant_id = 'delta'
          AND id = 4
        RETURNING id, description_pattern, occurrence_count, status
    """)

    result = cursor.fetchone()
    conn.commit()

    if result:
        print(f'\nReset pattern ID {result[0]} to pending status:')
        desc = result[1][:80] + '...' if len(result[1]) > 80 else result[1]
        print(f'  Description: {desc}')
        print(f'  Occurrences: {result[2]}')
        print(f'  New Status: {result[3]}')
    else:
        print('\nNo pattern found with ID 4')

    cursor.close()

    print('\n' + '=' * 70)
    print('Pattern is ready for LLM validation!')
    print('Run: python3 run_llm_pattern_validation.py')
    print('=' * 70 + '\n')
