"""
AI-Powered Business Knowledge Generator

This service analyzes transaction history to automatically generate:
1. Business insights (evidence layer)
2. Classification patterns (action layer)

The generated patterns immediately work for future transaction classification.
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import json
import anthropic

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_ui'))
from database import db_manager


class KnowledgeGenerator:
    """Generates actionable business knowledge from transaction history"""

    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        if self.api_key:
            self.claude = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.claude = None
            print("⚠️  Warning: ANTHROPIC_API_KEY not set - AI summaries will be basic")

    def analyze_all(self, min_frequency=75.0, min_transactions=5):
        """
        Analyze all aspects of the business and generate knowledge

        Args:
            min_frequency: Minimum pattern frequency (%) to create a pattern
            min_transactions: Minimum number of transactions to consider a pattern
        """
        print("\n" + "="*80)
        print(f"AI KNOWLEDGE GENERATION - Tenant: {self.tenant_id}")
        print("="*80)
        print(f"Min frequency: {min_frequency}%")
        print(f"Min transactions: {min_transactions}")

        results = {
            'accounts_analyzed': 0,
            'vendors_analyzed': 0,
            'patterns_created': 0,
            'insights_generated': 0
        }

        # 1. Analyze bank account usage
        print("\n" + "-"*80)
        print("1. ANALYZING BANK ACCOUNT USAGE PATTERNS")
        print("-"*80)
        account_results = self.analyze_all_accounts(min_frequency, min_transactions)
        results['accounts_analyzed'] = account_results['analyzed']
        results['patterns_created'] += account_results['patterns_created']
        results['insights_generated'] += account_results['insights_generated']

        # 2. Analyze recurring vendors
        print("\n" + "-"*80)
        print("2. ANALYZING RECURRING VENDOR PATTERNS")
        print("-"*80)
        vendor_results = self.analyze_recurring_vendors(min_frequency, min_transactions)
        results['vendors_analyzed'] = vendor_results['analyzed']
        results['patterns_created'] += vendor_results['patterns_created']
        results['insights_generated'] += vendor_results['insights_generated']

        # 3. Analyze entity behaviors
        print("\n" + "-"*80)
        print("3. ANALYZING BUSINESS ENTITY BEHAVIORS")
        print("-"*80)
        entity_results = self.analyze_entity_patterns(min_frequency, min_transactions)
        results['patterns_created'] += entity_results['patterns_created']
        results['insights_generated'] += entity_results['insights_generated']

        print("\n" + "="*80)
        print("KNOWLEDGE GENERATION COMPLETE")
        print("="*80)
        print(f"  Accounts analyzed:     {results['accounts_analyzed']}")
        print(f"  Vendors analyzed:      {results['vendors_analyzed']}")
        print(f"  Patterns created:      {results['patterns_created']}")
        print(f"  Insights generated:    {results['insights_generated']}")
        print("="*80)

        return results

    def analyze_all_accounts(self, min_frequency=75.0, min_transactions=5):
        """Analyze all bank accounts and generate patterns"""

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        # Get all accounts for this tenant
        cursor.execute("""
            SELECT DISTINCT account_number, account_name, institution_name
            FROM bank_accounts
            WHERE tenant_id = %s AND account_number IS NOT NULL
        """, (self.tenant_id,))

        accounts = cursor.fetchall()
        cursor.close()
        conn.close()

        results = {'analyzed': 0, 'patterns_created': 0, 'insights_generated': 0}

        for account_number, account_name, institution in accounts:
            print(f"\n  Analyzing account: {institution} {account_number} ({account_name})")

            analysis = self.analyze_account_usage(account_number)
            results['analyzed'] += 1

            if not analysis:
                print(f"    ⊘ Skipped - no transactions found")
                continue

            if analysis['transaction_count'] < min_transactions:
                print(f"    ⊘ Skipped - only {analysis['transaction_count']} transactions")
                continue

            if analysis['frequency'] < min_frequency:
                print(f"    ⊘ Skipped - frequency {analysis['frequency']:.1f}% < {min_frequency}%")
                continue

            # Generate AI summary
            ai_summary = self.generate_account_insight(analysis)

            # Create pattern and insight
            pattern_id = self.create_pattern_from_account_analysis(analysis, ai_summary)

            if pattern_id:
                results['patterns_created'] += 1
                results['insights_generated'] += 1
                print(f"    ✓ Pattern created (ID: {pattern_id})")

        return results

    def analyze_account_usage(self, account_number):
        """Analyze how a specific account is used"""

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        # Get all transactions for this account
        cursor.execute("""
            SELECT
                classified_entity,
                accounting_category,
                subcategory,
                COUNT(*) as count,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount,
                MIN(date) as first_date,
                MAX(date) as last_date
            FROM transactions
            WHERE tenant_id = %s
              AND (account_name LIKE %s OR account_name = %s)
              AND classified_entity IS NOT NULL
              AND classified_entity != ''
            GROUP BY classified_entity, accounting_category, subcategory
            ORDER BY count DESC
        """, (self.tenant_id, f'%{account_number}%', account_number))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            return None

        # Calculate totals
        total_transactions = sum(row[3] for row in rows)
        most_common = rows[0]

        frequency = (most_common[3] / total_transactions) * 100 if total_transactions > 0 else 0

        return {
            'account_number': account_number,
            'transaction_count': total_transactions,
            'most_common_entity': most_common[0],
            'most_common_category': most_common[1],
            'most_common_subcategory': most_common[2],
            'frequency': frequency,
            'pattern_count': most_common[3],
            'total_amount': float(most_common[4]) if most_common[4] else 0,
            'avg_amount': float(most_common[5]) if most_common[5] else 0,
            'date_range_start': most_common[6],
            'date_range_end': most_common[7],
            'all_patterns': [
                {
                    'entity': row[0],
                    'category': row[1],
                    'subcategory': row[2],
                    'count': row[3],
                    'percentage': (row[3] / total_transactions) * 100
                }
                for row in rows
            ]
        }

    def generate_account_insight(self, analysis):
        """Generate AI summary for account usage pattern"""

        if not self.claude:
            # Fallback without AI
            return {
                'description': f"Account used primarily for {analysis['most_common_subcategory'] or analysis['most_common_category']}",
                'justification': f"Based on {analysis['pattern_count']} of {analysis['transaction_count']} transactions ({analysis['frequency']:.1f}%)",
                'confidence': min(analysis['frequency'] / 100, 0.95)
            }

        # Build prompt for Claude
        prompt = f"""Analyze this bank account usage pattern and provide business insights:

Account Number: {analysis['account_number']}
Total Transactions: {analysis['transaction_count']}
Date Range: {analysis['date_range_start']} to {analysis['date_range_end']}

Most Common Pattern ({analysis['frequency']:.1f}% of transactions):
- Entity: {analysis['most_common_entity']}
- Category: {analysis['most_common_category']}
- Subcategory: {analysis['most_common_subcategory']}
- Occurrences: {analysis['pattern_count']} transactions
- Average Amount: ${analysis['avg_amount']:,.2f}

All Patterns:
{self._format_patterns_for_ai(analysis['all_patterns'][:5])}

Provide:
1. A concise description of what this account is used for (1-2 sentences)
2. A justification for creating an auto-classification pattern (why this pattern is reliable)
3. Confidence level (0.0-1.0) for auto-classifying future transactions

Respond in JSON format:
{{
    "description": "...",
    "justification": "...",
    "confidence": 0.85
}}"""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract JSON from response
            text = response.content[0].text
            # Try to find JSON in the response
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_text = text[start:end]
                result = json.loads(json_text)
                return result
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            print(f"      ⚠️  AI analysis failed: {e}")
            # Fallback
            return {
                'description': f"Account used for {analysis['most_common_subcategory'] or analysis['most_common_category']}",
                'justification': f"Pattern detected in {analysis['frequency']:.1f}% of transactions",
                'confidence': min(analysis['frequency'] / 100, 0.85)
            }

    def create_pattern_from_account_analysis(self, analysis, ai_summary):
        """Create actionable classification pattern from account analysis"""

        # Only create if confidence is high enough
        if ai_summary['confidence'] < 0.70:
            print(f"      ⊘ Confidence too low ({ai_summary['confidence']:.2f})")
            return None

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Check if pattern already exists
            cursor.execute("""
                SELECT pattern_id FROM classification_patterns
                WHERE tenant_id = %s
                  AND pattern_type = 'account_number'
                  AND description_pattern = %s
            """, (self.tenant_id, analysis['account_number']))

            existing = cursor.fetchone()
            if existing:
                print(f"      ⊘ Pattern already exists (ID: {existing[0]})")
                cursor.close()
                conn.close()
                return existing[0]

            # Create the classification pattern
            cursor.execute("""
                INSERT INTO classification_patterns (
                    tenant_id, pattern_type, description_pattern,
                    entity, accounting_category, accounting_subcategory,
                    confidence_score, justification, notes, created_by, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING pattern_id
            """, (
                self.tenant_id,
                'account_number',
                analysis['account_number'],
                analysis['most_common_entity'],
                analysis['most_common_category'],
                analysis['most_common_subcategory'],
                ai_summary['confidence'],
                ai_summary['justification'],
                f"AI-generated from {analysis['transaction_count']} historical transactions",
                'ai',
                'active'
            ))

            pattern_id = cursor.fetchone()[0]

            # Create the business insight (evidence)
            cursor.execute("""
                INSERT INTO business_insights (
                    tenant_id, insight_type, subject_id, subject_type,
                    transaction_count, date_range_start, date_range_end,
                    pattern_frequency, total_amount, avg_amount,
                    detected_entity, detected_category, detected_subcategory,
                    ai_summary, ai_justification, confidence_score,
                    generated_pattern_id, supporting_data,
                    status, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                self.tenant_id,
                'account_usage',
                analysis['account_number'],
                'bank_account',
                analysis['transaction_count'],
                analysis['date_range_start'],
                analysis['date_range_end'],
                analysis['frequency'],
                analysis['total_amount'],
                analysis['avg_amount'],
                analysis['most_common_entity'],
                analysis['most_common_category'],
                analysis['most_common_subcategory'],
                ai_summary['description'],
                ai_summary['justification'],
                ai_summary['confidence'],
                pattern_id,
                json.dumps({'all_patterns': analysis['all_patterns']}),
                'active',
                'ai'
            ))

            conn.commit()

            print(f"      ✓ Insight: {ai_summary['description']}")

            return pattern_id

        except Exception as e:
            conn.rollback()
            print(f"      ✗ Error creating pattern: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    def analyze_recurring_vendors(self, min_frequency=75.0, min_transactions=5):
        """Analyze recurring vendors and create patterns"""

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        # Find recurring vendors (detected from description patterns)
        cursor.execute("""
            SELECT
                description,
                classified_entity,
                accounting_category,
                subcategory,
                COUNT(*) as count,
                AVG(amount) as avg_amount
            FROM transactions
            WHERE tenant_id = %s
              AND description IS NOT NULL
              AND classified_entity IS NOT NULL
              AND classified_entity != ''
            GROUP BY description, classified_entity, accounting_category, subcategory
            HAVING COUNT(*) >= %s
            ORDER BY count DESC
            LIMIT 50
        """, (self.tenant_id, min_transactions))

        vendors = cursor.fetchall()
        cursor.close()
        conn.close()

        results = {'analyzed': len(vendors), 'patterns_created': 0, 'insights_generated': 0}

        print(f"\n  Found {len(vendors)} recurring vendor patterns")

        for description, entity, category, subcategory, count, avg_amount in vendors[:10]:  # Process top 10
            # Extract vendor name (simplified - could use AI for better extraction)
            vendor_keywords = self._extract_vendor_keywords(description)
            if not vendor_keywords:
                continue

            print(f"\n  Vendor pattern: {vendor_keywords} ({count} transactions)")

            # Check if pattern exists
            pattern_exists = self._check_pattern_exists(vendor_keywords, 'expense')
            if pattern_exists:
                print(f"    ⊘ Pattern already exists")
                continue

            # Create pattern
            pattern_id = self._create_vendor_pattern(
                vendor_keywords, entity, category, subcategory,
                count, avg_amount
            )

            if pattern_id:
                results['patterns_created'] += 1
                results['insights_generated'] += 1
                print(f"    ✓ Pattern created (ID: {pattern_id})")

        return results

    def analyze_entity_patterns(self, min_frequency=75.0, min_transactions=10):
        """Analyze how different entities are used"""
        # TODO: Implement entity behavior analysis
        return {'patterns_created': 0, 'insights_generated': 0}

    def _format_patterns_for_ai(self, patterns):
        """Format patterns list for AI prompt"""
        lines = []
        for p in patterns:
            lines.append(f"  - {p['entity']}: {p['category']} / {p['subcategory']} ({p['percentage']:.1f}%, {p['count']} transactions)")
        return '\n'.join(lines)

    def _extract_vendor_keywords(self, description):
        """Extract vendor name/keywords from description"""
        # Simple extraction - take first few words
        # In production, could use AI for better extraction
        words = description.upper().split()[:3]
        return ' '.join(words) if words else None

    def _check_pattern_exists(self, pattern_text, pattern_type):
        """Check if a pattern already exists"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT pattern_id FROM classification_patterns
            WHERE tenant_id = %s
              AND pattern_type = %s
              AND description_pattern LIKE %s
        """, (self.tenant_id, pattern_type, f'%{pattern_text}%'))

        exists = cursor.fetchone() is not None
        cursor.close()
        conn.close()

        return exists

    def _create_vendor_pattern(self, vendor_keywords, entity, category, subcategory, count, avg_amount):
        """Create a vendor pattern"""

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            pattern_text = f'%{vendor_keywords}%'

            cursor.execute("""
                INSERT INTO classification_patterns (
                    tenant_id, pattern_type, description_pattern,
                    entity, accounting_category, accounting_subcategory,
                    confidence_score, justification, notes, created_by, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING pattern_id
            """, (
                self.tenant_id,
                'expense',
                pattern_text,
                entity,
                category,
                subcategory,
                0.80,
                f"Recurring vendor detected in {count} transactions",
                f"AI-generated vendor pattern (avg: ${avg_amount:.2f})",
                'ai',
                'active'
            ))

            pattern_id = cursor.fetchone()[0]
            conn.commit()
            return pattern_id

        except Exception as e:
            conn.rollback()
            print(f"      ✗ Error: {e}")
            return None
        finally:
            cursor.close()
            conn.close()


    def generate_tenant_knowledge_summary(self, triggered_by='manual', source_file=None):
        """
        Generate a structured markdown summary of all tenant business knowledge.
        This summary is used as context for AI classification review (Pass 2).

        Format is optimized for:
        - AI comprehension (keyword-rich, structured)
        - Human readability (concise, scannable)
        - Token efficiency (no verbose descriptions)

        Returns:
            dict with 'markdown', 'stats', and storage result
        """
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        stats = {
            'entity_count': 0,
            'pattern_count': 0,
            'workforce_count': 0,
            'transaction_count': 0
        }

        sections = []

        # 1. BUSINESS ENTITIES
        cursor.execute("""
            SELECT name, entity_type, description
            FROM business_entities
            WHERE tenant_id = %s AND active = TRUE
            ORDER BY name
        """, (self.tenant_id,))
        entities = cursor.fetchall()
        stats['entity_count'] = len(entities)

        if entities:
            entity_lines = ["## Business Entities"]
            for name, etype, desc in entities:
                desc_short = desc[:80] if desc else ''
                entity_lines.append(f"- **{name}** ({etype or 'company'}): {desc_short}")
            sections.append('\n'.join(entity_lines))

        # 2. WORKFORCE MEMBERS (employees/contractors)
        cursor.execute("""
            SELECT full_name, employment_type, job_title, status
            FROM workforce_members
            WHERE tenant_id = %s
            ORDER BY full_name
        """, (self.tenant_id,))
        workforce = cursor.fetchall()
        stats['workforce_count'] = len(workforce)

        if workforce:
            wf_lines = ["## Employees & Contractors"]
            for name, emp_type, title, status in workforce:
                status_tag = '' if status == 'active' else f' [{status}]'
                wf_lines.append(f"- {name} ({emp_type}, {title or 'N/A'}){status_tag}")
            sections.append('\n'.join(wf_lines))

        # 3. CLASSIFICATION PATTERNS (grouped by type)
        cursor.execute("""
            SELECT pattern_type, description_pattern, entity,
                   accounting_category, accounting_subcategory, justification
            FROM classification_patterns
            WHERE tenant_id = %s AND status = 'active'
            ORDER BY pattern_type, entity
        """, (self.tenant_id,))
        patterns = cursor.fetchall()
        stats['pattern_count'] = len(patterns)

        if patterns:
            pattern_lines = ["## Classification Patterns"]
            current_type = None
            for ptype, pattern, entity, cat, subcat, just in patterns:
                if ptype != current_type:
                    pattern_lines.append(f"\n### {ptype.upper()}")
                    current_type = ptype
                cat_str = f"{cat}/{subcat}" if subcat else cat
                pattern_lines.append(f"- `{pattern}` -> {entity} | {cat_str}")
            sections.append('\n'.join(pattern_lines))

        # 4. BANK ACCOUNTS
        cursor.execute("""
            SELECT account_name, account_number,
                   COALESCE(institution_name, bank_name) as bank, account_type
            FROM bank_accounts
            WHERE tenant_id = %s AND is_active = TRUE
            ORDER BY bank_name
        """, (self.tenant_id,))
        accounts = cursor.fetchall()

        if accounts:
            acct_lines = ["## Bank Accounts"]
            for name, number, bank, atype in accounts:
                num_masked = f"...{number[-4:]}" if number and len(number) > 4 else number
                acct_lines.append(f"- {bank or 'Unknown'} {num_masked} ({atype or 'account'}): {name or 'Unnamed'}")
            sections.append('\n'.join(acct_lines))

        # 5. CRYPTO WALLETS
        cursor.execute("""
            SELECT entity_name, wallet_type, wallet_address, purpose
            FROM wallet_addresses
            WHERE tenant_id = %s AND is_active = TRUE
            ORDER BY entity_name
        """, (self.tenant_id,))
        wallets = cursor.fetchall()

        if wallets:
            wallet_lines = ["## Crypto Wallets"]
            for entity, wtype, addr, purpose in wallets:
                addr_short = addr[:12] + '...' if addr and len(addr) > 15 else addr
                wallet_lines.append(f"- {entity} ({wtype}): {addr_short} - {purpose or ''}")
            sections.append('\n'.join(wallet_lines))

        # 6. RECENT TRANSACTION STATS
        cursor.execute("""
            SELECT COUNT(*), MIN(date), MAX(date)
            FROM transactions
            WHERE tenant_id = %s
        """, (self.tenant_id,))
        txn_stats = cursor.fetchone()
        stats['transaction_count'] = txn_stats[0] or 0

        # Build final markdown
        header = f"# Business Knowledge Summary\n**Tenant:** {self.tenant_id}\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"

        summary_md = header + '\n\n' + '\n\n'.join(sections)

        # Store in database
        cursor.execute("""
            INSERT INTO tenant_business_summary
                (tenant_id, summary_markdown, triggered_by, source_file,
                 transaction_count, pattern_count, entity_count, workforce_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id) DO UPDATE SET
                summary_markdown = EXCLUDED.summary_markdown,
                generated_at = CURRENT_TIMESTAMP,
                triggered_by = EXCLUDED.triggered_by,
                source_file = EXCLUDED.source_file,
                transaction_count = EXCLUDED.transaction_count,
                pattern_count = EXCLUDED.pattern_count,
                entity_count = EXCLUDED.entity_count,
                workforce_count = EXCLUDED.workforce_count
        """, (
            self.tenant_id, summary_md, triggered_by, source_file,
            stats['transaction_count'], stats['pattern_count'],
            stats['entity_count'], stats['workforce_count']
        ))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"  Business summary generated: {len(summary_md)} chars, {stats['pattern_count']} patterns")

        return {
            'markdown': summary_md,
            'stats': stats
        }

    def get_cached_summary(self):
        """Get the cached business summary from database"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT summary_markdown, generated_at, triggered_by, source_file,
                   transaction_count, pattern_count, entity_count, workforce_count
            FROM tenant_business_summary
            WHERE tenant_id = %s
        """, (self.tenant_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            return {
                'markdown': row[0],
                'generated_at': row[1].isoformat() if row[1] else None,
                'triggered_by': row[2],
                'source_file': row[3],
                'stats': {
                    'transaction_count': row[4],
                    'pattern_count': row[5],
                    'entity_count': row[6],
                    'workforce_count': row[7]
                }
            }
        return None


if __name__ == '__main__':
    # Example usage
    import sys

    tenant_id = sys.argv[1] if len(sys.argv) > 1 else 'delta'

    generator = KnowledgeGenerator(tenant_id)
    results = generator.analyze_all(min_frequency=75.0, min_transactions=5)

    print(f"\n✓ Knowledge generation complete!")
    print(f"  Generated {results['patterns_created']} actionable patterns")
    print(f"  Created {results['insights_generated']} business insights")
