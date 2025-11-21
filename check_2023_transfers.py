#!/usr/bin/env python3
"""Check which 2023 transfers are registered in the database"""

from web_ui.database import db_manager
from datetime import datetime

# Parse the transfer list for 2023
transfers = [
    ("2023-04-14", 70000, "coinbase"),
    ("2023-04-27", 68665, "coinbase"),
    ("2023-06-22", 56024, "Delta to Millen 7478"),
    ("2023-07-17", 84285, "Delta to Millen 7479"),
    ("2023-08-22", 5624, "Delta to Millen 7480"),
    ("2023-08-23", 67732, "Delta to Millen 7481"),
    ("2023-11-10", 14000, "Delta to Millen 7482"),
    ("2023-11-13", 19675, "Delta to Millen 7483"),
    ("2023-11-17", 1651, "Delta to Millen 7484"),
    ("2023-11-29", 36000, "Delta to Millen 7485"),
    ("2023-11-30", 57252, "Delt to Fernando"),
]

print("=" * 80)
print("CHECKING 2023 TRANSFERS IN DATABASE (tenant: delta)")
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
        entity_display = item['entity'][:35] if item['entity'] else 'N/A'
        desc_display = item['description'][:45] if item['description'] else 'N/A'
        print(f"  {item['date']:<15} ${item['amount']:>12,}  {note_display:<25}")
        print(f"      Entity: {entity_display}")
        print(f"      Description: {desc_display}")
        print()

print("=" * 80)
print(f"SUMMARY: {len(found)}/{len(transfers)} transfers found in database")
print("=" * 80)
