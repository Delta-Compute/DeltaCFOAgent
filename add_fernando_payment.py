#!/usr/bin/env python3
"""Add Fernando contractor payroll payment"""

from web_ui.database import db_manager
from datetime import datetime
import uuid

# Configuration
TENANT_ID = 'delta'
ENTITY = 'Delta Mining Paraguay S.A.'
CURRENCY = 'USD'
CONFIDENCE = 1.0

# Fernando contractor payment
payment = {
    'date': '2023-11-30',
    'amount': 57252,
    'description': 'Contractor/Partner Payroll - Fernando'
}

print("=" * 80)
print("ADDING FERNANDO CONTRACTOR PAYMENT")
print("=" * 80)
print(f"Tenant: {TENANT_ID}")
print(f"Entity: {ENTITY}")
print(f"Category: Operating Expenses / Contractor Payments")
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

try:
    transaction_id = str(uuid.uuid4())
    expense_amount = -abs(payment['amount'])

    result = db_manager.execute_query(
        insert_query,
        (
            transaction_id,
            TENANT_ID,
            payment['date'],
            payment['description'],
            expense_amount,
            CURRENCY,
            expense_amount,
            ENTITY,
            'Operating Expenses',
            'Contractor Payments',
            'Contractor/Partner Payroll - Fernando',
            CONFIDENCE,
            'Manual entry - Contractor payroll payment',
            'Delta Mining Paraguay S.A.',
            'Fernando (Contractor)',
            'manual_entry_fernando.py',
        ),
        fetch_one=True
    )

    print(f"\n✅ Successfully added:")
    print(f"   Date: {payment['date']}")
    print(f"   Amount: ${payment['amount']:,.2f}")
    print(f"   Description: {payment['description']}")
    print(f"   Transaction ID: {result['transaction_id']}")

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")

print("\n" + "=" * 80)
