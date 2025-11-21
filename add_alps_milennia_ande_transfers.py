#!/usr/bin/env python3
"""Add Alps and Milennia ANDE transfers to the database"""

from web_ui.database import db_manager
from datetime import datetime
import uuid

# Missing transfers to add - Alps and Milennia paid ANDE on behalf of Delta
transfers = [
    ("2023-04-12", 85857.63, "ANDE - Energy Payment via Third Party (Ref: 625730400)"),
    ("2023-12-28", 78000, "ANDE - Energy Payment via Milennia (Ref: 1299)"),
    ("2024-02-02", 52577, "ANDE - Energy Payment via Third Party (Ref: 383158365)"),
    ("2024-02-07", 35310, "ANDE - Energy Payment via Third Party (Ref: 256276668)"),
    ("2024-03-15", 105422, "ANDE - Energy Payment via Third Party (Ref: 765138595)"),
    ("2024-03-21", 11427, "ANDE - Energy Payment via Third Party (Ref: 82932965)"),
    ("2024-04-24", 72450, "ANDE - Energy Payment via Alps Mining"),
    ("2024-04-29", 28511, "ANDE - Energy Payment via Alps Mining"),
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
print("ADDING ALPS & MILENNIA ANDE TRANSFERS TO DATABASE")
print("=" * 80)
print(f"Tenant: {TENANT_ID}")
print(f"Entity: {ENTITY}")
print(f"Category: {CATEGORY}")
print(f"Subcategory: {SUBCATEGORY}")
print(f"Justification: {JUSTIFICATION}")
print(f"Note: Alps and Milennia paid ANDE on behalf of Delta")
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
                'Manual entry - ANDE Energy payment via third party (Alps/Milennia)',
                'Delta Mining Paraguay S.A.',
                'ANDE (Administración Nacional de Electricidad)',
                'manual_entry_alps_milennia_ande.py',
            ),
            fetch_one=True
        )

        added.append({
            'transaction_id': result['transaction_id'],
            'date': result['date'],
            'amount': result['amount'],
            'description': result['description']
        })

        print(f"✅ Added: {date_str} | ${amount:>12,.2f} | {description[:55]}")

    except Exception as e:
        errors.append({
            'date': date_str,
            'amount': amount,
            'error': str(e)
        })
        print(f"❌ ERROR: {date_str} | ${amount:>12,.2f} | {str(e)[:60]}")

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
