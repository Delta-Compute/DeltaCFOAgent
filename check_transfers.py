#!/usr/bin/env python3
"""Check which transfers are registered in the database"""

from web_ui.database import db_manager
from datetime import datetime
from decimal import Decimal

# Parse the transfer list
transfers = [
    ("2025-01-21", 65200),
    ("2025-01-22", 67346),
    ("2025-01-17", 500),
    ("2025-01-24", 1000),
    ("2025-01-22", 4109),
    ("2025-02-05", 39000),
    ("2025-02-06", 14000),
    ("2025-02-12", 24000),
    ("2025-02-25", 44000),
    ("2025-02-27", 60000),
    ("2025-03-07", 32000),
    ("2025-03-14", 35500),
    ("2025-03-18", 42000),
    ("2025-03-28", 5000),
    ("2025-04-02", 42856),
    ("2025-05-20", 139500),
    ("2025-06-09", 80000),
    ("2025-06-20", 49000),
    ("2025-07-08", 37000),
    ("2025-07-18", 37960),
    ("2025-07-22", 24500),
    ("2025-07-25", 48550),
    ("2025-07-29", 32950),
    ("2025-07-30", 9975),
    ("2025-08-08", 40000),
    ("2025-08-19", 48400),
    ("2025-08-28", 76000),
    ("2025-09-04", 65500),
    ("2025-09-19", 53000),
    ("2025-09-23", 44280),
    ("2025-10-02", 43000),
]

print("=" * 80)
print("CHECKING TRANSFERS IN DATABASE (tenant: delta)")
print("=" * 80)

not_found = []
found = []

for date_str, amount in transfers:
    # Check if transaction exists in database with this date and amount
    # Try matching by date and amount (allowing small tolerance for amount)
    query = """
        SELECT transaction_id, date, amount, description, accounting_category
        FROM transactions
        WHERE tenant_id = %s
          AND DATE(date) = %s
          AND ABS(ABS(amount) - %s) < 1
        LIMIT 1
    """

    result = db_manager.execute_query(
        query,
        ('delta', date_str, amount),
        fetch_one=True
    )

    if result:
        found.append({
            'date': date_str,
            'amount': amount,
            'db_amount': float(result['amount']),
            'description': result['description'],
            'category': result['accounting_category']
        })
    else:
        not_found.append({
            'date': date_str,
            'amount': amount
        })

print(f"\n✅ FOUND: {len(found)} transfers")
print(f"❌ NOT FOUND: {len(not_found)} transfers\n")

if not_found:
    print("=" * 80)
    print("TRANSFERS NOT FOUND IN DATABASE:")
    print("=" * 80)
    total_missing = 0
    for item in not_found:
        print(f"  {item['date']:<15} ${item['amount']:>12,}")
        total_missing += item['amount']
    print("-" * 80)
    print(f"  {'TOTAL MISSING:':<15} ${total_missing:>12,}")
    print("=" * 80)

if found:
    print("\n" + "=" * 80)
    print("TRANSFERS FOUND IN DATABASE:")
    print("=" * 80)
    for item in found:
        print(f"  {item['date']:<15} ${item['amount']:>12,} | {item['description'][:40]}")

print("\n" + "=" * 80)
print(f"SUMMARY: {len(found)}/{len(transfers)} transfers found in database")
print("=" * 80)
