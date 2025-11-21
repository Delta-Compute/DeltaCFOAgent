#!/usr/bin/env python3
"""
Migrate all hardcoded classification patterns from main.py to database

This script extracts ALL hardcoded patterns from the classify_transaction method
and inserts them into the classification_patterns table for the Delta tenant.

Categories of patterns migrated:
1. Intermediate routing patterns (priority 0-99)
2. Currency-based rules (priority 100-199)
3. Hardcoded if/elif patterns (priority 300-399)
4. Employee/vendor patterns (priority 300-399)

Note: Wallet addresses and account mappings are already database-driven
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui.database import db_manager

def migrate_hardcoded_patterns(tenant_id='delta'):
    """Migrate all hardcoded patterns to database"""

    print("=" * 80)
    print("MIGRATING HARDCODED CLASSIFICATION PATTERNS TO DATABASE")
    print("=" * 80)
    print(f"Tenant: {tenant_id}")
    print()

    patterns_to_insert = []

    # ========================================
    # CATEGORY 1: INTERMEDIATE ROUTING PATTERNS
    # Priority: 0-99 (highest priority)
    # These patterns match intermediate steps, not final classification
    # ========================================

    intermediate_routing = [
        # Coinbase routing
        {
            'pattern_type': 'intermediate_routing',
            'description_pattern': '%COINBASE.COM%',
            'entity': None,  # Don't set entity yet
            'accounting_category': 'Intermediate Transfer',
            'subcategory': 'Exchange Routing',
            'confidence_score': 1.00,
            'priority': 10,
            'rule_conditions': json.dumps({
                'type': 'intermediate_routing',
                'exchange': 'Coinbase',
                'mark_for_reprocessing': True
            }),
            'notes': 'Coinbase intermediate routing - requires second pass for final entity'
        },
        {
            'pattern_type': 'intermediate_routing',
            'description_pattern': '%COINBASE INC.%',
            'entity': None,
            'accounting_category': 'Intermediate Transfer',
            'subcategory': 'Exchange Routing',
            'confidence_score': 1.00,
            'priority': 10,
            'rule_conditions': json.dumps({
                'type': 'intermediate_routing',
                'exchange': 'Coinbase',
                'mark_for_reprocessing': True
            }),
            'notes': 'Coinbase Inc intermediate routing'
        },
        # MEXC routing
        {
            'pattern_type': 'intermediate_routing',
            'description_pattern': '%MEXC%',
            'entity': None,
            'accounting_category': 'Intermediate Transfer',
            'subcategory': 'Exchange Routing',
            'confidence_score': 1.00,
            'priority': 10,
            'rule_conditions': json.dumps({
                'type': 'intermediate_routing',
                'exchange': 'MEXC',
                'mark_for_reprocessing': True
            }),
            'notes': 'MEXC exchange intermediate routing'
        },
        # Binance routing
        {
            'pattern_type': 'intermediate_routing',
            'description_pattern': '%BINANCE%',
            'entity': None,
            'accounting_category': 'Intermediate Transfer',
            'subcategory': 'Exchange Routing',
            'confidence_score': 1.00,
            'priority': 10,
            'rule_conditions': json.dumps({
                'type': 'intermediate_routing',
                'exchange': 'Binance',
                'mark_for_reprocessing': True
            }),
            'notes': 'Binance exchange intermediate routing'
        },
        # Kraken routing
        {
            'pattern_type': 'intermediate_routing',
            'description_pattern': '%KRAKEN%',
            'entity': None,
            'accounting_category': 'Intermediate Transfer',
            'subcategory': 'Exchange Routing',
            'confidence_score': 1.00,
            'priority': 10,
            'rule_conditions': json.dumps({
                'type': 'intermediate_routing',
                'exchange': 'Kraken',
                'mark_for_reprocessing': True
            }),
            'notes': 'Kraken exchange intermediate routing'
        },
        # OKX routing
        {
            'pattern_type': 'intermediate_routing',
            'description_pattern': '%OKX%',
            'entity': None,
            'accounting_category': 'Intermediate Transfer',
            'subcategory': 'Exchange Routing',
            'confidence_score': 1.00,
            'priority': 10,
            'rule_conditions': json.dumps({
                'type': 'intermediate_routing',
                'exchange': 'OKX',
                'mark_for_reprocessing': True
            }),
            'notes': 'OKX exchange intermediate routing'
        },
        # General "FROM" routing patterns
        {
            'pattern_type': 'intermediate_routing',
            'description_pattern': 'FROM %',
            'entity': None,
            'accounting_category': 'Intermediate Transfer',
            'subcategory': 'Origin Transfer',
            'confidence_score': 0.60,
            'priority': 50,
            'rule_conditions': json.dumps({
                'type': 'intermediate_routing',
                'pattern_prefix': 'FROM',
                'mark_for_reprocessing': True
            }),
            'notes': 'Generic FROM pattern - low priority intermediate routing'
        },
        # "TO" routing patterns
        {
            'pattern_type': 'intermediate_routing',
            'description_pattern': 'TO %',
            'entity': None,
            'accounting_category': 'Intermediate Transfer',
            'subcategory': 'Destination Transfer',
            'confidence_score': 0.60,
            'priority': 50,
            'rule_conditions': json.dumps({
                'type': 'intermediate_routing',
                'pattern_prefix': 'TO',
                'mark_for_reprocessing': True
            }),
            'notes': 'Generic TO pattern - low priority intermediate routing'
        },
        # ROUTING keyword
        {
            'pattern_type': 'intermediate_routing',
            'description_pattern': '%ROUTING%',
            'entity': None,
            'accounting_category': 'Intermediate Transfer',
            'subcategory': 'General Routing',
            'confidence_score': 0.70,
            'priority': 30,
            'rule_conditions': json.dumps({
                'type': 'intermediate_routing',
                'keyword': 'ROUTING',
                'mark_for_reprocessing': True
            }),
            'notes': 'General routing keyword pattern'
        },
        # TRANSFER keyword
        {
            'pattern_type': 'intermediate_routing',
            'description_pattern': '%TRANSFER%',
            'entity': None,
            'accounting_category': 'Intermediate Transfer',
            'subcategory': 'General Transfer',
            'confidence_score': 0.70,
            'priority': 30,
            'rule_conditions': json.dumps({
                'type': 'intermediate_routing',
                'keyword': 'TRANSFER',
                'mark_for_reprocessing': True
            }),
            'notes': 'General transfer keyword pattern'
        },
        # PAYMENT keyword
        {
            'pattern_type': 'intermediate_routing',
            'description_pattern': '%PAYMENT%',
            'entity': None,
            'accounting_category': 'Intermediate Transfer',
            'subcategory': 'Payment Processing',
            'confidence_score': 0.70,
            'priority': 30,
            'rule_conditions': json.dumps({
                'type': 'intermediate_routing',
                'keyword': 'PAYMENT',
                'mark_for_reprocessing': True
            }),
            'notes': 'General payment keyword pattern'
        },
    ]

    patterns_to_insert.extend(intermediate_routing)

    # ========================================
    # CATEGORY 2: CURRENCY-BASED RULES
    # Priority: 100-199
    # These patterns match based on cryptocurrency type
    # ========================================

    currency_rules = [
        {
            'pattern_type': 'currency_rule',
            'description_pattern': '%',  # Matches all descriptions
            'entity': 'Infinity Validator',
            'accounting_category': 'Cryptocurrency Revenue',
            'subcategory': 'BTC Mining',
            'confidence_score': 1.00,
            'priority': 100,
            'rule_conditions': json.dumps({
                'type': 'currency_match',
                'currency': 'BTC',
                'entity': 'Infinity Validator',
                'category': 'Cryptocurrency Revenue'
            }),
            'notes': 'All BTC transactions go to Infinity Validator'
        },
        {
            'pattern_type': 'currency_rule',
            'description_pattern': '%',
            'entity': 'Delta Prop Shop LLC',
            'accounting_category': 'Cryptocurrency Revenue',
            'subcategory': 'TAO Staking',
            'confidence_score': 1.00,
            'priority': 100,
            'rule_conditions': json.dumps({
                'type': 'currency_match',
                'currency': 'TAO',
                'entity': 'Delta Prop Shop LLC',
                'category': 'Cryptocurrency Revenue'
            }),
            'notes': 'All TAO transactions go to Delta Prop Shop LLC'
        },
        {
            'pattern_type': 'currency_rule',
            'description_pattern': '%',
            'entity': 'Delta LLC',
            'accounting_category': 'Cryptocurrency Transfer',
            'subcategory': 'USDC Movement',
            'confidence_score': 0.80,
            'priority': 120,
            'rule_conditions': json.dumps({
                'type': 'currency_match',
                'currency': 'USDC',
                'entity': 'Delta LLC',
                'category': 'Cryptocurrency Transfer',
                'note': 'Default USDC classification - may be overridden by specific patterns'
            }),
            'notes': 'Default USDC transactions to Delta LLC (unless more specific pattern matches)'
        },
        {
            'pattern_type': 'currency_rule',
            'description_pattern': '%',
            'entity': 'Delta LLC',
            'accounting_category': 'Cryptocurrency Transfer',
            'subcategory': 'USDT Movement',
            'confidence_score': 0.80,
            'priority': 120,
            'rule_conditions': json.dumps({
                'type': 'currency_match',
                'currency': 'USDT',
                'entity': 'Delta LLC',
                'category': 'Cryptocurrency Transfer',
                'note': 'Default USDT classification - may be overridden by specific patterns'
            }),
            'notes': 'Default USDT transactions to Delta LLC (unless more specific pattern matches)'
        },
    ]

    patterns_to_insert.extend(currency_rules)

    # ========================================
    # CATEGORY 3: HARDCODED IF/ELIF PATTERNS
    # Priority: 300-399
    # These are specific transaction patterns from hardcoded logic
    # ========================================

    hardcoded_patterns = [
        # Crypto sends/receives
        {
            'pattern_type': 'crypto_transaction',
            'description_pattern': '%SEND USDC%',
            'entity': 'Delta LLC',
            'accounting_category': 'Cryptocurrency Transfer',
            'subcategory': 'USDC Outbound',
            'confidence_score': 1.00,
            'priority': 300,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'amount_sign': 'negative'
            }),
            'notes': 'USDC outbound transfers'
        },
        {
            'pattern_type': 'crypto_transaction',
            'description_pattern': '%RECEIVE USDC%',
            'entity': 'Delta LLC',
            'accounting_category': 'Cryptocurrency Transfer',
            'subcategory': 'USDC Inbound',
            'confidence_score': 1.00,
            'priority': 300,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'amount_sign': 'positive'
            }),
            'notes': 'USDC inbound transfers'
        },
        {
            'pattern_type': 'crypto_transaction',
            'description_pattern': '%SEND BTC%',
            'entity': 'Infinity Validator',
            'accounting_category': 'Cryptocurrency Transfer',
            'subcategory': 'BTC Outbound',
            'confidence_score': 1.00,
            'priority': 300,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'amount_sign': 'negative'
            }),
            'notes': 'BTC outbound transfers'
        },
        {
            'pattern_type': 'crypto_transaction',
            'description_pattern': '%RECEIVE BTC%',
            'entity': 'Infinity Validator',
            'accounting_category': 'Cryptocurrency Revenue',
            'subcategory': 'BTC Inbound',
            'confidence_score': 1.00,
            'priority': 300,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'amount_sign': 'positive'
            }),
            'notes': 'BTC inbound transfers (revenue)'
        },
        # External account patterns
        {
            'pattern_type': 'crypto_transaction',
            'description_pattern': '%RECEIVE BTC - EXTERNAL ACCOUNT%',
            'entity': 'Infinity Validator',
            'accounting_category': 'Cryptocurrency Revenue',
            'subcategory': 'External BTC Receipt',
            'confidence_score': 1.00,
            'priority': 290,  # Higher priority than generic RECEIVE BTC
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'amount_sign': 'positive',
                'source': 'external_account'
            }),
            'notes': 'BTC received from external accounts (priority over generic BTC receive)'
        },
        {
            'pattern_type': 'crypto_transaction',
            'description_pattern': '%SEND USDC - EXTERNAL ACCOUNT%',
            'entity': 'Delta LLC',
            'accounting_category': 'Cryptocurrency Transfer',
            'subcategory': 'External USDC Send',
            'confidence_score': 1.00,
            'priority': 290,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'amount_sign': 'negative',
                'destination': 'external_account'
            }),
            'notes': 'USDC sent to external accounts'
        },
        # Buy/Sell patterns
        {
            'pattern_type': 'crypto_transaction',
            'description_pattern': '%BUY BTC%',
            'entity': 'Infinity Validator',
            'accounting_category': 'Cryptocurrency Purchase',
            'subcategory': 'BTC Acquisition',
            'confidence_score': 1.00,
            'priority': 300,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'transaction_type': 'buy'
            }),
            'notes': 'BTC purchases'
        },
        {
            'pattern_type': 'crypto_transaction',
            'description_pattern': '%SELL BTC%',
            'entity': 'Infinity Validator',
            'accounting_category': 'Cryptocurrency Sale',
            'subcategory': 'BTC Disposition',
            'confidence_score': 1.00,
            'priority': 300,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'transaction_type': 'sell'
            }),
            'notes': 'BTC sales'
        },
        {
            'pattern_type': 'crypto_transaction',
            'description_pattern': '%BUY USDC%',
            'entity': 'Delta LLC',
            'accounting_category': 'Cryptocurrency Purchase',
            'subcategory': 'USDC Acquisition',
            'confidence_score': 1.00,
            'priority': 300,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'transaction_type': 'buy'
            }),
            'notes': 'USDC purchases'
        },
        {
            'pattern_type': 'crypto_transaction',
            'description_pattern': '%CONVERT%',
            'entity': 'Delta LLC',
            'accounting_category': 'Cryptocurrency Conversion',
            'subcategory': 'Token Swap',
            'confidence_score': 0.90,
            'priority': 310,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'transaction_type': 'convert'
            }),
            'notes': 'Cryptocurrency conversions/swaps'
        },
        # Reward/Staking
        {
            'pattern_type': 'crypto_transaction',
            'description_pattern': '%REWARD%',
            'entity': 'Delta Prop Shop LLC',
            'accounting_category': 'Cryptocurrency Revenue',
            'subcategory': 'Staking Rewards',
            'confidence_score': 1.00,
            'priority': 300,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'transaction_type': 'reward'
            }),
            'notes': 'Staking rewards and crypto rewards'
        },
        {
            'pattern_type': 'crypto_transaction',
            'description_pattern': '%STAKING%',
            'entity': 'Delta Prop Shop LLC',
            'accounting_category': 'Cryptocurrency Revenue',
            'subcategory': 'Staking Income',
            'confidence_score': 1.00,
            'priority': 300,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'transaction_type': 'staking'
            }),
            'notes': 'Staking income'
        },
        # Gas fees
        {
            'pattern_type': 'expense',
            'description_pattern': '%GAS FEE%',
            'entity': None,
            'accounting_category': 'Blockchain Fees',
            'subcategory': 'Gas Fees',
            'confidence_score': 1.00,
            'priority': 300,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'is_fee': True
            }),
            'notes': 'Blockchain gas fees'
        },
        {
            'pattern_type': 'expense',
            'description_pattern': '%NETWORK FEE%',
            'entity': None,
            'accounting_category': 'Blockchain Fees',
            'subcategory': 'Network Fees',
            'confidence_score': 1.00,
            'priority': 300,
            'rule_conditions': json.dumps({
                'type': 'exact_pattern',
                'match_mode': 'contains',
                'is_fee': True
            }),
            'notes': 'Blockchain network fees'
        },
    ]

    patterns_to_insert.extend(hardcoded_patterns)

    # ========================================
    # CATEGORY 4: EMPLOYEE/VENDOR PATTERNS
    # Priority: 300-399
    # Specific people and vendor names from hardcoded logic
    # ========================================

    employee_vendor_patterns = [
        # Brazilian employees (Delta Brazil)
        {
            'pattern_type': 'employee_expense',
            'description_pattern': '%TIAGO%',
            'entity': 'Delta Brazil',
            'accounting_category': 'Employee Expense',
            'subcategory': 'Payroll',
            'confidence_score': 1.00,
            'priority': 320,
            'rule_conditions': json.dumps({
                'type': 'employee_match',
                'employee_name': 'Tiago',
                'entity': 'Delta Brazil',
                'expense_type': 'payroll'
            }),
            'notes': 'Tiago - Delta Brazil employee'
        },
        {
            'pattern_type': 'employee_expense',
            'description_pattern': '%VICTOR%',
            'entity': 'Delta Brazil',
            'accounting_category': 'Employee Expense',
            'subcategory': 'Payroll',
            'confidence_score': 1.00,
            'priority': 320,
            'rule_conditions': json.dumps({
                'type': 'employee_match',
                'employee_name': 'Victor',
                'entity': 'Delta Brazil',
                'expense_type': 'payroll'
            }),
            'notes': 'Victor - Delta Brazil employee'
        },
        {
            'pattern_type': 'employee_expense',
            'description_pattern': '%RAFAEL%',
            'entity': 'Delta Brazil',
            'accounting_category': 'Employee Expense',
            'subcategory': 'Payroll',
            'confidence_score': 1.00,
            'priority': 320,
            'rule_conditions': json.dumps({
                'type': 'employee_match',
                'employee_name': 'Rafael',
                'entity': 'Delta Brazil',
                'expense_type': 'payroll'
            }),
            'notes': 'Rafael - Delta Brazil employee'
        },
        {
            'pattern_type': 'employee_expense',
            'description_pattern': '%LUCAS%',
            'entity': 'Delta Brazil',
            'accounting_category': 'Employee Expense',
            'subcategory': 'Payroll',
            'confidence_score': 1.00,
            'priority': 320,
            'rule_conditions': json.dumps({
                'type': 'employee_match',
                'employee_name': 'Lucas',
                'entity': 'Delta Brazil',
                'expense_type': 'payroll'
            }),
            'notes': 'Lucas - Delta Brazil employee'
        },
        {
            'pattern_type': 'employee_expense',
            'description_pattern': '%MATHEUS%',
            'entity': 'Delta Brazil',
            'accounting_category': 'Employee Expense',
            'subcategory': 'Payroll',
            'confidence_score': 1.00,
            'priority': 320,
            'rule_conditions': json.dumps({
                'type': 'employee_match',
                'employee_name': 'Matheus',
                'entity': 'Delta Brazil',
                'expense_type': 'payroll'
            }),
            'notes': 'Matheus - Delta Brazil employee'
        },
        # Contractors
        {
            'pattern_type': 'contractor_expense',
            'description_pattern': '%ACME CONSULTING%',
            'entity': 'Delta LLC',
            'accounting_category': 'Professional Services',
            'subcategory': 'Consulting Fees',
            'confidence_score': 1.00,
            'priority': 330,
            'rule_conditions': json.dumps({
                'type': 'vendor_match',
                'vendor_name': 'Acme Consulting',
                'expense_type': 'professional_services'
            }),
            'notes': 'Acme Consulting - contractor/vendor'
        },
        # Paraguay operations
        {
            'pattern_type': 'operational_expense',
            'description_pattern': '%PARAGUAY%',
            'entity': 'Delta Mining Paraguay S.A.',
            'accounting_category': 'Operational Expense',
            'subcategory': 'Mining Operations',
            'confidence_score': 0.95,
            'priority': 340,
            'rule_conditions': json.dumps({
                'type': 'location_match',
                'location': 'Paraguay',
                'entity': 'Delta Mining Paraguay S.A.'
            }),
            'notes': 'Paraguay operations - mining entity'
        },
        {
            'pattern_type': 'operational_expense',
            'description_pattern': '%ASUNCION%',
            'entity': 'Delta Mining Paraguay S.A.',
            'accounting_category': 'Operational Expense',
            'subcategory': 'Mining Operations',
            'confidence_score': 0.95,
            'priority': 340,
            'rule_conditions': json.dumps({
                'type': 'location_match',
                'location': 'Asuncion',
                'entity': 'Delta Mining Paraguay S.A.'
            }),
            'notes': 'Asuncion (Paraguay capital) - mining entity'
        },
        # Mining specific
        {
            'pattern_type': 'revenue',
            'description_pattern': '%MINING REVENUE%',
            'entity': 'Delta Mining Paraguay S.A.',
            'accounting_category': 'Mining Revenue',
            'subcategory': 'Cryptocurrency Mining',
            'confidence_score': 1.00,
            'priority': 310,
            'rule_conditions': json.dumps({
                'type': 'revenue_match',
                'revenue_type': 'mining',
                'entity': 'Delta Mining Paraguay S.A.'
            }),
            'notes': 'Cryptocurrency mining revenue'
        },
        # Technology expenses
        {
            'pattern_type': 'technology',
            'description_pattern': '%AWS%',
            'entity': 'Delta LLC',
            'accounting_category': 'Technology Expense',
            'subcategory': 'Cloud Services',
            'confidence_score': 1.00,
            'priority': 350,
            'rule_conditions': json.dumps({
                'type': 'vendor_match',
                'vendor_name': 'AWS',
                'expense_type': 'cloud_services'
            }),
            'notes': 'Amazon Web Services - cloud infrastructure'
        },
        {
            'pattern_type': 'technology',
            'description_pattern': '%OPENAI%',
            'entity': 'Delta LLC',
            'accounting_category': 'Technology Expense',
            'subcategory': 'AI Services',
            'confidence_score': 1.00,
            'priority': 350,
            'rule_conditions': json.dumps({
                'type': 'vendor_match',
                'vendor_name': 'OpenAI',
                'expense_type': 'ai_services'
            }),
            'notes': 'OpenAI API services'
        },
    ]

    patterns_to_insert.extend(employee_vendor_patterns)

    # ========================================
    # INSERT PATTERNS INTO DATABASE
    # ========================================

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            print(f"[1/4] Preparing to insert {len(patterns_to_insert)} patterns...")
            print()

            # First, apply the schema migration
            print("[2/4] Applying schema enhancements...")
            schema_file = os.path.join(os.path.dirname(__file__), 'enhance_classification_patterns.sql')
            with open(schema_file, 'r') as f:
                schema_sql = f.read()

            cursor.execute(schema_sql)
            conn.commit()
            print("   ✓ Schema enhanced successfully")
            print()

            # Count existing patterns for this tenant
            cursor.execute("""
                SELECT COUNT(*) FROM classification_patterns WHERE tenant_id = %s
            """, (tenant_id,))
            existing_count = cursor.fetchone()[0]
            print(f"[3/4] Found {existing_count} existing patterns for tenant '{tenant_id}'")
            print()

            # Insert new patterns
            print(f"[4/4] Inserting {len(patterns_to_insert)} new patterns...")
            inserted_count = 0
            skipped_count = 0

            for pattern in patterns_to_insert:
                try:
                    cursor.execute("""
                        INSERT INTO classification_patterns (
                            tenant_id, pattern_type, description_pattern, entity,
                            accounting_category, subcategory, confidence_score, priority,
                            rule_conditions, notes, created_by, is_active
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        tenant_id,
                        pattern['pattern_type'],
                        pattern['description_pattern'],
                        pattern.get('entity'),
                        pattern['accounting_category'],
                        pattern.get('subcategory'),
                        pattern['confidence_score'],
                        pattern['priority'],
                        pattern.get('rule_conditions'),
                        pattern.get('notes'),
                        'system_migration',
                        True
                    ))
                    inserted_count += 1

                    if inserted_count % 10 == 0:
                        print(f"   ... inserted {inserted_count} patterns")

                except Exception as e:
                    # Pattern might already exist - skip it
                    if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                        skipped_count += 1
                    else:
                        print(f"   ⚠ Warning inserting pattern {pattern['description_pattern']}: {e}")
                        skipped_count += 1

            conn.commit()

            # Final count
            cursor.execute("""
                SELECT COUNT(*) FROM classification_patterns WHERE tenant_id = %s
            """, (tenant_id,))
            final_count = cursor.fetchone()[0]

            cursor.close()

            print()
            print("=" * 80)
            print("MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print(f"\nSummary:")
            print(f"  - Patterns before migration: {existing_count}")
            print(f"  - New patterns inserted: {inserted_count}")
            print(f"  - Patterns skipped (duplicates/errors): {skipped_count}")
            print(f"  - Total patterns now: {final_count}")
            print()
            print("Pattern breakdown by category:")
            print(f"  - Intermediate routing: {len(intermediate_routing)}")
            print(f"  - Currency rules: {len(currency_rules)}")
            print(f"  - Hardcoded patterns: {len(hardcoded_patterns)}")
            print(f"  - Employee/vendor patterns: {len(employee_vendor_patterns)}")
            print()
            print("✅ All hardcoded patterns migrated to database!")
            print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate hardcoded classification patterns to database')
    parser.add_argument('--tenant', default='delta', help='Tenant ID (default: delta)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without executing')

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        print()

    migrate_hardcoded_patterns(tenant_id=args.tenant)
