#!/usr/bin/env python3
"""Check which misc transfers are registered in the database"""

from web_ui.database import db_manager
from datetime import datetime

# Parse the transfer list
transfers = [
    ("2023-04-12", 85857.63, "625730400"),
    ("2023-12-28", 78000, "Delta to Milen 1299"),
    ("2024-02-02", 52577, "383158365"),
    ("2024-02-07", 35310, "256276668"),
    ("2024-03-15", 105422, "765138595"),
    ("2024-03-21", 11427, "82932965"),
    ("2024-04-24", 72450, "Alps"),
    ("2024-04-29", 28511, "Alps"),
]

print("=" * 80)
print("CHECKING MISC TRANSFERS IN DATABASE (tenant: delta)")
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
        print(f"  {item['date']:<15} ${item['amount']:>12,.2f}  {note_display}")
        total_missing += item['amount']
    print("-" * 80)
    print(f"  {'TOTAL MISSING:':<15} ${total_missing:>12,.2f}")
    print("=" * 80)

if found:
    print("\n" + "=" * 80)
    print("TRANSFERS FOUND IN DATABASE:")
    print("=" * 80)
    for item in found:
        note_display = f"({item['note']})" if item['note'] else ""
        entity_display = item['entity'][:35] if item['entity'] else 'N/A'
        desc_display = item['description'][:40] if item['description'] else 'N/A'
        print(f"  {item['date']:<15} ${item['amount']:>12,.2f}  {note_display:<20}")
        print(f"      Entity: {entity_display}")
        print(f"      Description: {desc_display}")
        print()

print("=" * 80)
print(f"SUMMARY: {len(found)}/{len(transfers)} transfers found in database")
print("=" * 80)
