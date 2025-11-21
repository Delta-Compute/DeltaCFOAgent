#!/usr/bin/env python3
"""
Reset pattern suggestions to pending status for re-validation
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))
from database import db_manager

with db_manager.get_connection() as conn:
    cursor = conn.cursor()

    print('=' * 70)
    print('RESETTING PATTERN SUGGESTIONS TO PENDING STATUS')
    print('=' * 70)

    # Reset all rejected patterns (all 4 failed patterns)
    cursor.execute("""
        UPDATE pattern_suggestions
        SET status = 'pending',
            llm_validation_result = NULL,
            llm_validated_at = NULL,
            validation_model = NULL
        WHERE tenant_id = 'delta'
          AND status = 'rejected'
        RETURNING id, description_pattern
    """)

    reset_patterns = cursor.fetchall()
    conn.commit()

    print(f'\nReset {len(reset_patterns)} pattern(s) to pending status:\n')
    for pattern in reset_patterns:
        desc = pattern[1][:60] + '...' if len(pattern[1]) > 60 else pattern[1]
        print(f'  Pattern ID {pattern[0]}: {desc}')

    cursor.close()

    print('\n' + '=' * 70)
    print('Patterns are now ready for LLM validation!')
    print('Run: python3 run_llm_pattern_validation.py')
    print('=' * 70 + '\n')
