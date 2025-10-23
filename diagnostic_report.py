#!/usr/bin/env python3
"""
Diagnostic Report for DeltaCFOAgent Homepage & Accounts Implementation
Checks database, APIs, and identifies missing data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web_ui'))

from web_ui.database import db_manager
from web_ui.services.data_queries import DataQueryService
import json

def check_database_tables():
    """Check if all required tables exist"""
    print("=" * 80)
    print("1. DATABASE TABLES CHECK")
    print("=" * 80)

    required_tables = [
        'tenant_configuration',
        'wallet_addresses',
        'bank_accounts',
        'homepage_content',
        'transactions',
        'business_entities'
    ]

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            for table in required_tables:
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = '{table}'
                    )
                """)
                exists = cursor.fetchone()[0]
                status = "✅ EXISTS" if exists else "❌ MISSING"
                print(f"{status}: {table}")

                if exists:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"   → {count} records")

            cursor.close()

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print()


def check_tenant_configuration():
    """Check tenant configuration data"""
    print("=" * 80)
    print("2. TENANT CONFIGURATION CHECK")
    print("=" * 80)

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT tenant_id, company_name, company_tagline, company_description,
                       industry, default_currency
                FROM tenant_configuration
                WHERE tenant_id = 'delta'
            """)

            result = cursor.fetchone()

            if result:
                print("✅ Delta tenant configuration found:")
                print(f"   Tenant ID: {result[0]}")
                print(f"   Company Name: {result[1]}")
                print(f"   Tagline: {result[2]}")
                print(f"   Description: {result[3][:100]}..." if result[3] else "   Description: None")
                print(f"   Industry: {result[4]}")
                print(f"   Currency: {result[5]}")
            else:
                print("❌ No tenant configuration found for 'delta'")
                print("   This is why AI description might be generic!")

            cursor.close()

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print()


def check_business_entities():
    """Check business entities"""
    print("=" * 80)
    print("3. BUSINESS ENTITIES CHECK")
    print("=" * 80)

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name, description, entity_type, active
                FROM business_entities
                WHERE active = TRUE
                ORDER BY name
            """)

            results = cursor.fetchall()

            if results:
                print(f"✅ Found {len(results)} active business entities:")
                for row in results:
                    print(f"   • {row[0]} ({row[2]})")
                    print(f"     {row[1][:80]}..." if row[1] else "     No description")
            else:
                print("❌ No business entities found")
                print("   AI cannot describe portfolio companies!")

            cursor.close()

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print()


def check_transactions_data():
    """Check transactions data"""
    print("=" * 80)
    print("4. TRANSACTIONS DATA CHECK")
    print("=" * 80)

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Total transactions
            cursor.execute("""
                SELECT COUNT(*) FROM transactions
                WHERE tenant_id = 'delta' AND (archived = FALSE OR archived IS NULL)
            """)
            total = cursor.fetchone()[0]
            print(f"Total Transactions: {total}")

            if total == 0:
                print("❌ NO TRANSACTIONS FOUND - AI has no financial data to analyze!")
                cursor.close()
                return

            # Revenue
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE tenant_id = 'delta' AND amount > 0
                AND (archived = FALSE OR archived IS NULL)
            """)
            revenue = cursor.fetchone()[0]
            print(f"Total Revenue: ${float(revenue):,.2f}")

            # Expenses
            cursor.execute("""
                SELECT COALESCE(SUM(ABS(amount)), 0)
                FROM transactions
                WHERE tenant_id = 'delta' AND amount < 0
                AND (archived = FALSE OR archived IS NULL)
            """)
            expenses = cursor.fetchone()[0]
            print(f"Total Expenses: ${float(expenses):,.2f}")

            # Date range
            cursor.execute("""
                SELECT MIN(date), MAX(date)
                FROM transactions
                WHERE tenant_id = 'delta' AND (archived = FALSE OR archived IS NULL)
            """)
            dates = cursor.fetchone()
            if dates[0]:
                print(f"Date Range: {dates[0]} to {dates[1]}")

            # Top entities
            cursor.execute("""
                SELECT classified_entity, COUNT(*)
                FROM transactions
                WHERE tenant_id = 'delta' AND classified_entity IS NOT NULL
                AND (archived = FALSE OR archived IS NULL)
                GROUP BY classified_entity
                ORDER BY COUNT(*) DESC
                LIMIT 5
            """)
            entities = cursor.fetchall()

            if entities:
                print("\nTop 5 Entities by Transaction Count:")
                for entity, count in entities:
                    print(f"   • {entity}: {count} transactions")

            cursor.close()

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print()


def check_accounts():
    """Check bank accounts and wallets"""
    print("=" * 80)
    print("5. BANK ACCOUNTS & WALLETS CHECK")
    print("=" * 80)

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Bank accounts
            cursor.execute("""
                SELECT COUNT(*) FROM bank_accounts
                WHERE tenant_id = 'delta' AND status != 'closed'
            """)
            bank_count = cursor.fetchone()[0]
            print(f"Bank Accounts: {bank_count}")

            if bank_count > 0:
                cursor.execute("""
                    SELECT account_name, institution_name, account_type, status
                    FROM bank_accounts
                    WHERE tenant_id = 'delta' AND status != 'closed'
                    ORDER BY is_primary DESC, created_at DESC
                """)
                accounts = cursor.fetchall()
                for acc in accounts:
                    print(f"   • {acc[0]} - {acc[1]} ({acc[2]}) - {acc[3]}")

            # Wallets
            cursor.execute("""
                SELECT COUNT(*) FROM wallet_addresses
                WHERE tenant_id = 'delta' AND is_active = TRUE
            """)
            wallet_count = cursor.fetchone()[0]
            print(f"\nCrypto Wallets: {wallet_count}")

            if wallet_count > 0:
                cursor.execute("""
                    SELECT entity_name, wallet_type, blockchain
                    FROM wallet_addresses
                    WHERE tenant_id = 'delta' AND is_active = TRUE
                    ORDER BY created_at DESC
                """)
                wallets = cursor.fetchall()
                for wallet in wallets:
                    blockchain = wallet[2] if wallet[2] else 'unknown'
                    print(f"   • {wallet[0]} ({wallet[1]}) - {blockchain}")

            cursor.close()

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print()


def check_homepage_content():
    """Check cached homepage content"""
    print("=" * 80)
    print("6. HOMEPAGE CONTENT CACHE CHECK")
    print("=" * 80)

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT company_name, tagline, description,
                       ai_insights, generated_at, generated_by
                FROM homepage_content
                WHERE tenant_id = 'delta' AND is_active = TRUE
            """)

            result = cursor.fetchone()

            if result:
                print("✅ Cached content found:")
                print(f"   Company: {result[0]}")
                print(f"   Tagline: {result[1]}")
                print(f"   Description: {result[2][:100]}..." if result[2] else "   Description: None")
                print(f"   Generated: {result[4]}")
                print(f"   Generated by: {result[5]}")

                # Check if stale (>24 hours)
                from datetime import datetime, timedelta
                if result[4]:
                    age = datetime.now() - result[4]
                    if age > timedelta(hours=24):
                        print(f"   ⚠️  Cache is {age.days} days old - should regenerate")
                    else:
                        print(f"   ✅ Cache is fresh ({age.seconds // 3600} hours old)")
            else:
                print("❌ No cached content found")
                print("   Content will be generated on first request")

            cursor.close()

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print()


def test_data_queries():
    """Test the data query service"""
    print("=" * 80)
    print("7. DATA QUERY SERVICE TEST")
    print("=" * 80)

    try:
        service = DataQueryService(db_manager, 'delta')

        # Test company overview
        print("Testing get_company_overview()...")
        company = service.get_company_overview()
        print(f"   Company Name: {company.get('company_name')}")
        print(f"   Has Description: {'Yes' if company.get('company_description') else 'No'}")

        # Test KPIs
        print("\nTesting get_company_kpis()...")
        kpis = service.get_company_kpis()
        print(f"   Total Transactions: {kpis.get('total_transactions')}")
        print(f"   Total Revenue: ${kpis.get('total_revenue', 0):,.2f}")
        print(f"   Total Expenses: ${kpis.get('total_expenses', 0):,.2f}")
        print(f"   Years of Data: {kpis.get('years_of_data')}")

        # Test entities
        print("\nTesting get_business_entities()...")
        entities = service.get_business_entities()
        print(f"   Found {len(entities)} entities")

        if len(entities) == 0:
            print("   ❌ NO ENTITIES - This is why AI description is generic!")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()


def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "DELTACFOAGENT DIAGNOSTIC REPORT" + " " * 32 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    check_database_tables()
    check_tenant_configuration()
    check_business_entities()
    check_transactions_data()
    check_accounts()
    check_homepage_content()
    test_data_queries()

    print("=" * 80)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("Common Issues & Fixes:")
    print()
    print("1. If 'No business entities found':")
    print("   → Run: psql ... < postgres_unified_schema.sql")
    print("   → This loads default entities (Delta LLC, Delta Prop Shop, etc.)")
    print()
    print("2. If 'No tenant configuration found':")
    print("   → The seed data wasn't loaded")
    print("   → Run the schema file to insert Delta tenant config")
    print()
    print("3. If 'No transactions found':")
    print("   → Upload transaction files through /files page")
    print("   → AI needs real financial data to generate accurate descriptions")
    print()
    print("4. If AI description is generic:")
    print("   → Check that business_entities table has data")
    print("   → Check that tenant_configuration has description")
    print("   → Ensure transactions exist for KPI calculations")
    print()
    print("5. If White Listed Accounts page shows 404:")
    print("   → Check that app_db.py has the route registered")
    print("   → Restart the Flask application")
    print()
    print("=" * 80)
    print()


if __name__ == '__main__':
    main()
