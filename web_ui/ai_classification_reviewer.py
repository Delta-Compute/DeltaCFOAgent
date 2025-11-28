"""
AI Classification Reviewer - Pass 2 for transaction classification

This module provides AI-powered review of transaction classifications,
using the tenant's business knowledge context to improve accuracy.
"""

import os
import json
import anthropic
from datetime import datetime


class AIClassificationReviewer:
    """
    Reviews transaction classifications using Claude AI with business context.

    Pass 2 in the classification pipeline:
    1. Pass 1: Pattern matching (fast, rule-based)
    2. Pass 2: AI review (for low-confidence results)
    """

    def __init__(self, tenant_id, business_context_markdown):
        """
        Initialize reviewer with tenant context.

        Args:
            tenant_id: The tenant identifier
            business_context_markdown: Pre-generated business knowledge summary
        """
        self.tenant_id = tenant_id
        self.business_context = business_context_markdown
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')

        if self.api_key:
            self.claude = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.claude = None
            print("[AI Reviewer] Warning: ANTHROPIC_API_KEY not set")

    def review_batch(self, transactions, confidence_threshold=0.85, batch_size=30):
        """
        Review a batch of transactions and return corrections.

        Args:
            transactions: List of transaction dicts with classification results
            confidence_threshold: Only review transactions below this confidence
            batch_size: Max transactions per API call

        Returns:
            dict with 'corrections', 'pattern_suggestions', 'summary'
        """
        if not self.claude:
            return {'corrections': [], 'pattern_suggestions': [], 'summary': 'AI not available'}

        # Filter to low-confidence transactions
        needs_review = [
            t for t in transactions
            if t.get('confidence', 0) < confidence_threshold
            or t.get('classified_entity') in ['Unclassified', None, '']
            or 'error' in str(t.get('justification', '')).lower()
        ]

        if not needs_review:
            return {
                'corrections': [],
                'pattern_suggestions': [],
                'summary': 'All transactions classified with high confidence'
            }

        # Process in batches
        all_corrections = []
        all_suggestions = []

        for i in range(0, len(needs_review), batch_size):
            batch = needs_review[i:i + batch_size]
            result = self._review_single_batch(batch)

            if result:
                all_corrections.extend(result.get('corrections', []))
                all_suggestions.extend(result.get('pattern_suggestions', []))

        return {
            'corrections': all_corrections,
            'pattern_suggestions': all_suggestions,
            'summary': f'Reviewed {len(needs_review)} transactions, suggested {len(all_corrections)} corrections',
            'reviewed_count': len(needs_review),
            'total_count': len(transactions)
        }

    def _review_single_batch(self, transactions):
        """Review a single batch of transactions"""

        # Format transactions for the prompt
        txn_text = self._format_transactions_for_prompt(transactions)

        prompt = f"""You are a financial classification expert reviewing transaction categorizations.

## Business Context
{self.business_context}

## Transactions to Review
Each transaction shows: Date | Description | Amount | Current Classification

{txn_text}

## Your Task
Review each transaction and determine if the current classification is correct.

For INCORRECT classifications, provide corrections. Consider:
1. Match against known employees/contractors in the Business Context
2. Match against known vendors and patterns
3. Use entity context (which entity does this transaction belong to?)
4. Infer from description keywords (PIX, Pix enviado, Pix recebido, etc.)

For each correction, also indicate if we should CREATE A NEW PATTERN to handle similar transactions in the future.

## Response Format (JSON only)
{{
    "corrections": [
        {{
            "index": 0,
            "description": "original description",
            "current_entity": "what it was",
            "correct_entity": "what it should be",
            "correct_category": "OPERATING_EXPENSE|REVENUE|TRANSFER|etc",
            "correct_subcategory": "Payroll & Benefits|Contractor Payment|etc",
            "confidence": 0.90,
            "justification": "Why this classification is correct",
            "create_pattern": true,
            "pattern_keyword": "KEYWORD TO MATCH"
        }}
    ],
    "pattern_suggestions": [
        {{
            "keyword": "PATTERN KEYWORD",
            "entity": "Target Entity",
            "category": "CATEGORY",
            "subcategory": "Subcategory",
            "justification": "Why this pattern should be created"
        }}
    ],
    "summary": "Brief summary of findings"
}}

If a transaction is correctly classified, do NOT include it in corrections.
Only respond with valid JSON, no other text."""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response
            text = response.content[0].text.strip()

            # Try to extract JSON
            start = text.find('{')
            end = text.rfind('}') + 1

            if start >= 0 and end > start:
                json_text = text[start:end]
                result = json.loads(json_text)
                return result
            else:
                print(f"[AI Reviewer] No JSON found in response")
                return None

        except json.JSONDecodeError as e:
            print(f"[AI Reviewer] JSON parse error: {e}")
            return None
        except Exception as e:
            print(f"[AI Reviewer] API error: {e}")
            return None

    def _format_transactions_for_prompt(self, transactions):
        """Format transactions for the AI prompt"""
        lines = []
        for i, t in enumerate(transactions):
            date = t.get('date', 'N/A')
            desc = t.get('description', '')[:80]
            amount = t.get('amount', 0)
            entity = t.get('classified_entity', 'Unclassified')
            category = t.get('accounting_category', 'N/A')
            subcategory = t.get('subcategory', '')
            confidence = t.get('confidence', 0)

            cat_str = f"{category}/{subcategory}" if subcategory else category
            lines.append(f"[{i}] {date} | {desc} | ${amount:,.2f} | {entity} ({cat_str}) conf={confidence:.2f}")

        return '\n'.join(lines)

    def apply_corrections(self, transactions, corrections):
        """
        Apply AI corrections to transaction list.

        Args:
            transactions: Original transaction list
            corrections: List of correction dicts from review_batch

        Returns:
            Updated transactions list with corrections applied
        """
        # Build index map for quick lookup
        correction_map = {c['index']: c for c in corrections if 'index' in c}

        for i, txn in enumerate(transactions):
            if i in correction_map:
                c = correction_map[i]
                txn['classified_entity'] = c.get('correct_entity', txn.get('classified_entity'))
                txn['accounting_category'] = c.get('correct_category', txn.get('accounting_category'))
                txn['subcategory'] = c.get('correct_subcategory', txn.get('subcategory'))
                txn['confidence'] = c.get('confidence', 0.90)
                txn['justification'] = f"[AI Review] {c.get('justification', '')}"

        return transactions


def queue_pattern_suggestions(tenant_id, suggestions):
    """
    Queue pattern suggestions for user approval.

    Args:
        tenant_id: Tenant identifier
        suggestions: List of pattern suggestion dicts
    """
    if not suggestions:
        return

    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from database import db_manager

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        for s in suggestions:
            cursor.execute("""
                INSERT INTO pattern_suggestions (
                    tenant_id, suggested_pattern, suggested_entity,
                    suggested_category, suggested_subcategory,
                    justification, source, confidence_score, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                tenant_id,
                f"%{s.get('keyword', '')}%",
                s.get('entity'),
                s.get('category'),
                s.get('subcategory'),
                s.get('justification', 'AI-suggested pattern'),
                'ai_pass2_review',
                0.85,
                'pending'
            ))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"[AI Reviewer] Queued {len(suggestions)} pattern suggestions")

    except Exception as e:
        print(f"[AI Reviewer] Error queuing suggestions: {e}")
