#!/usr/bin/env python3
"""
Check LLM validation results for pattern suggestions
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))
from database import db_manager

with db_manager.get_connection() as conn:
    cursor = conn.cursor()

    print('=' * 70)
    print('LLM VALIDATION RESULTS FOR BITCOIN PATTERNS')
    print('=' * 70)

    cursor.execute("""
        SELECT
            id,
            description_pattern,
            status,
            occurrence_count,
            confidence_score,
            llm_validation_result,
            llm_validated_at
        FROM pattern_suggestions
        WHERE tenant_id = 'delta'
        ORDER BY id
    """)

    results = cursor.fetchall()

    for row in results:
        print(f'\nPattern ID {row[0]}:')
        print(f'  Description: {row[1][:80]}...')
        print(f'  Status: {row[2]}')
        print(f'  Occurrences: {row[3]}')
        print(f'  Confidence: {row[4]}')
        print(f'  LLM Validated: {row[6]}')

        if row[5]:
            validation = json.loads(row[5]) if isinstance(row[5], str) else row[5]
            print(f'  LLM Valid: {validation.get("is_valid")}')
            print(f'  Reasoning: {validation.get("reasoning", "N/A")}')
            print(f'  Risk: {validation.get("risk_assessment", "N/A")}')
        else:
            print('  LLM Result: Not validated yet')

    cursor.close()
    print('\n' + '=' * 70)
