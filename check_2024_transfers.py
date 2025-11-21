#!/usr/bin/env python3
"""Check which 2024 transfers are registered in the database"""

from web_ui.database import db_manager
from datetime import datetime

# Parse the transfer list for 2024
transfers = [
    ("2024-06-14", 44490, "Mil to ANDE"),
    ("2024-06-21", 97000, "chase"),
    ("2024-07-25", 195000, "chase"),
    ("2024-08-12", 27112, "Mil to ANDE"),
    ("2024-08-13", 160000, "chase"),
    ("2024-08-26", 225000, "chase"),
    ("2024-09-12", 29835, "Mil to ANDE"),
    ("2024-09-27", 166700, "chase"),
    ("2024-10-08", 170700, ""),
    ("2024-10-09", 20341, "Mil to ANDE"),
    ("2024-10-23", 186000, "chase"),
    ("2024-11-01", 18604, "Mil to ANDE"),  # Nov 2024 - assuming Nov 1
    ("2024-11-27", 22900, "chase"),
    ("2024-11-27", 137000, "chase"),
    ("2024-12-16", 13912, "Mill to ANDE"),
    ("2024-12-20", 125000, "chase"),
    ("2024-12-26", 72000, "chase"),
]

print("=" * 80)
print("CHECKING 2024 TRANSFERS IN DATABASE (tenant: delta)")
print("=" * 80)

not_found = []
found = []

for date_str, amount, note in transfers:
    # Check if transaction exists in database with this date and amount
    # Try matching by date and amount (allowing small tolerance for amount)
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
            'db_amount': float(result['amount']),
            'description': result['description'],
            'category': result['accounting_category'],
            'entity': result['classified_entity']
        })
    else:
        not_found.append({
            'date': date_str,
            'amount': amount,
            'note': note
        })

print(f"\n✅ FOUND: {len(found)} transfers")
print(f"❌ NOT FOUND: {len(not_found)} transfers\n")

if not_found:
    print("=" * 80)
    print("TRANSFERS NOT FOUND IN DATABASE:")
    print("=" * 80)
    total_missing = 0
    for item in not_found:
        note_display = f"({item['note']})" if item['note'] else ""
        print(f"  {item['date']:<15} ${item['amount']:>12,}  {note_display}")
        total_missing += item['amount']
    print("-" * 80)
    print(f"  {'TOTAL MISSING:':<15} ${total_missing:>12,}")
    print("=" * 80)

if found:
    print("\n" + "=" * 80)
    print("TRANSFERS FOUND IN DATABASE:")
    print("=" * 80)
    for item in found:
        note_display = f"({item['note']})" if item['note'] else ""
        entity_display = item['entity'][:30] if item['entity'] else 'N/A'
        print(f"  {item['date']:<15} ${item['amount']:>12,}  {note_display:<20} | {entity_display}")

print("\n" + "=" * 80)
print(f"SUMMARY: {len(found)}/{len(transfers)} transfers found in database")
print("=" * 80)
