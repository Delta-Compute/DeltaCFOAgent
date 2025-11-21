#!/usr/bin/env python3
"""Check if specific ANDE amounts from third-party payments are already registered"""

from web_ui.database import db_manager

# ANDE portions that were paid via Milennia/third parties
ande_amounts = [
    ("2023-07-20", 20000, "via Milennia"),
    ("2023-08-24", 65989, "Ref: 480898956"),
    ("2023-08-30", 91469, "Ref: 666591529"),
    ("2023-09-28", 81667, "Ref: 595158552"),
    ("2023-11-13", 88675, "via Milennia"),
]

print("=" * 80)
print("CHECKING IF ANDE AMOUNTS ARE ALREADY IN DATABASE")
print("=" * 80)

found = []
not_found = []

for date_str, amount, note in ande_amounts:
    query = """
        SELECT transaction_id, date, amount, description, accounting_category, classified_entity
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
            'note': note,
            'description': result['description'],
        })
        print(f"✅ FOUND: {date_str} ${amount:>10,} {note}")
    else:
        not_found.append({
            'date': date_str,
            'amount': amount,
            'note': note
        })
        print(f"❌ NOT FOUND: {date_str} ${amount:>10,} {note}")

print("\n" + "=" * 80)
print(f"Result: {len(found)} already in DB, {len(not_found)} missing")
print("=" * 80)
