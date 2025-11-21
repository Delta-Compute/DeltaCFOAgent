#!/usr/bin/env python3
"""Add missing ANDE transfers to the database"""

from web_ui.database import db_manager
from datetime import datetime
import uuid

# Missing transfers to add
transfers = [
    ("2025-01-17", 500, "ANDE - Energy Payment Jan 17"),
    ("2025-01-22", 4109, "ANDE - Energy Payment Jan 22 (1)"),
    ("2025-01-22", 67346, "ANDE - Energy Payment Jan 22 (2)"),
    ("2025-01-24", 1000, "ANDE - Energy Payment Jan 24"),
    ("2025-02-06", 14000, "ANDE - Energy Payment Feb 6"),
    ("2025-02-12", 24000, "ANDE - Energy Payment Feb 12"),
    ("2025-10-02", 43000, "ANDE - Energy Payment Oct 2"),
]

# Configuration
TENANT_ID = 'delta'
ENTITY = 'Delta Mining Paraguay S.A.'
CATEGORY = 'COGS'
SUBCATEGORY = 'Utilities'
JUSTIFICATION = 'ANDE Energy'
CURRENCY = 'USD'
CONFIDENCE = 1.0

print("=" * 80)
print("ADDING MISSING ANDE TRANSFERS TO DATABASE")
print("=" * 80)
print(f"Tenant: {TENANT_ID}")
print(f"Entity: {ENTITY}")
print(f"Category: {CATEGORY}")
print(f"Subcategory: {SUBCATEGORY}")
print(f"Justification: {JUSTIFICATION}")
print("=" * 80)

# Insert query
insert_query = """
    INSERT INTO transactions (
        transaction_id, tenant_id, date, description, amount, currency, usd_equivalent,
        classified_entity, accounting_category, subcategory, justification,
        confidence, classification_reason, origin, destination,
        source_file, created_at, updated_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    )
    RETURNING transaction_id, date, amount, description
"""

added = []
errors = []

for date_str, amount, description in transfers:
    try:
        # Generate unique transaction ID
        transaction_id = str(uuid.uuid4())

        # Make amount negative (expense)
        expense_amount = -abs(amount)

        result = db_manager.execute_query(
            insert_query,
            (
                transaction_id,
                TENANT_ID,
                date_str,
                description,
                expense_amount,
                CURRENCY,
                expense_amount,  # USD equivalent
                ENTITY,
                CATEGORY,
                SUBCATEGORY,
                JUSTIFICATION,
                CONFIDENCE,
                'Manual entry - ANDE Energy payment',
                'Delta Mining Paraguay S.A.',
                'ANDE (Administración Nacional de Electricidad)',
                'manual_entry_ande_transfers.py',
            ),
            fetch_one=True
        )

        added.append({
            'transaction_id': result['transaction_id'],
            'date': result['date'],
            'amount': result['amount'],
            'description': result['description']
        })

        print(f"✅ Added: {date_str} | ${amount:>10,} | {description}")

    except Exception as e:
        errors.append({
            'date': date_str,
            'amount': amount,
            'error': str(e)
        })
        print(f"❌ ERROR: {date_str} | ${amount:>10,} | {str(e)[:60]}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"✅ Successfully added: {len(added)} transactions")
print(f"❌ Errors: {len(errors)} transactions")

if added:
    total_added = sum(abs(t['amount']) for t in added)
    print(f"\nTotal amount added: ${total_added:,.2f}")

if errors:
    print("\nERRORS:")
    for err in errors:
        print(f"  {err['date']}: ${err['amount']:,} - {err['error']}")

print("=" * 80)
