#!/usr/bin/env python3
"""
Fix currency conversion by manually setting USD equivalents
Uses reasonable historical exchange rates
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'web_ui'))

from database import db_manager

def fix_currency_conversion():
    print("=== FIXING CURRENCY CONVERSION ===")

    # Historical exchange rates (approximate)
    exchange_rates = {
        'PYG': 7400,  # PYG per USD (Paraguayan Guarani)
        'GUA': 7400,  # Same as PYG (Guarani alternate code)
        'BTC': 45000  # USD per BTC (approximate historical average)
    }

    # Update PYG invoices
    print("\nUpdating PYG invoices...")
    pyg_update = """
    UPDATE invoices
    SET
        usd_equivalent_amount = ROUND(total_amount / %s, 2),
        historical_exchange_rate = %s,
        rate_date = CURRENT_DATE,
        rate_source = 'manual_fix',
        conversion_notes = 'Manual USD conversion using historical rate'
    WHERE currency = 'PYG'
    AND (usd_equivalent_amount IS NULL OR usd_equivalent_amount = 0)
    """

    db_manager.execute_query(pyg_update, (exchange_rates['PYG'], 1.0/exchange_rates['PYG']))

    # Update GUA invoices
    print("Updating GUA invoices...")
    gua_update = """
    UPDATE invoices
    SET
        usd_equivalent_amount = ROUND(total_amount / %s, 2),
        historical_exchange_rate = %s,
        rate_date = CURRENT_DATE,
        rate_source = 'manual_fix',
        conversion_notes = 'Manual USD conversion using historical rate'
    WHERE currency = 'GUA'
    AND (usd_equivalent_amount IS NULL OR usd_equivalent_amount = 0)
    """

    db_manager.execute_query(gua_update, (exchange_rates['GUA'], 1.0/exchange_rates['GUA']))

    # Update BTC invoices
    print("Updating BTC invoices...")
    btc_update = """
    UPDATE invoices
    SET
        usd_equivalent_amount = ROUND(total_amount * %s, 2),
        historical_exchange_rate = %s,
        rate_date = CURRENT_DATE,
        rate_source = 'manual_fix',
        conversion_notes = 'Manual USD conversion using historical rate'
    WHERE currency = 'BTC'
    """

    db_manager.execute_query(btc_update, (exchange_rates['BTC'], exchange_rates['BTC']))

    # Get updated statistics
    print("\n=== UPDATED CURRENCY STATISTICS ===")

    stats_query = """
    SELECT
        currency,
        COUNT(*) as count,
        SUM(total_amount) as total_original,
        SUM(COALESCE(usd_equivalent_amount, total_amount)) as total_usd,
        AVG(COALESCE(usd_equivalent_amount, total_amount)) as avg_usd
    FROM invoices
    GROUP BY currency
    ORDER BY total_usd DESC
    """

    results = db_manager.execute_query(stats_query, fetch_all=True)

    print(f"{'Currency':<8} {'Count':<6} {'Total USD':<20} {'Avg USD':<15}")
    print("-" * 60)

    total_all_usd = 0
    for row in results:
        total_usd = float(row['total_usd'])
        total_all_usd += total_usd
        print(f"{row['currency']:<8} {row['count']:<6} ${total_usd:>17,.2f} ${float(row['avg_usd']):>12,.2f}")

    print(f"\nTOTAL (USD EQUIVALENT): ${total_all_usd:,.2f}")

    # Show some conversion examples
    print("\n=== CONVERSION EXAMPLES ===")
    examples_query = """
    SELECT invoice_number, currency, total_amount, usd_equivalent_amount, customer_name
    FROM invoices
    WHERE currency != 'USD'
    ORDER BY total_amount DESC
    LIMIT 5
    """

    examples = db_manager.execute_query(examples_query, fetch_all=True)

    for example in examples:
        original = float(example['total_amount'])
        usd_equiv = float(example.get('usd_equivalent_amount') or 0)
        print(f"Invoice {example['invoice_number']}: {example['currency']} {original:,.2f} -> USD {usd_equiv:,.2f}")

if __name__ == "__main__":
    fix_currency_conversion()