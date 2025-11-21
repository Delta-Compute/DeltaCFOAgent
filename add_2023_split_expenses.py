#!/usr/bin/env python3
"""Add 2023 expenses split by category (ANDE + Payroll + Coinbase)"""

from web_ui.database import db_manager
from datetime import datetime
import uuid

# Configuration
TENANT_ID = 'delta'
ENTITY = 'Delta Mining Paraguay S.A.'
CURRENCY = 'USD'
CONFIDENCE = 1.0

# ANDE Energy Expenses (5 transactions - $347,800)
ande_expenses = [
    ("2023-07-20", 20000, "ANDE - Energy Payment via Milennia"),
    ("2023-08-24", 65989, "ANDE - Energy Payment via Third Party (Ref: 480898956)"),
    ("2023-08-30", 91469, "ANDE - Energy Payment via Third Party (Ref: 666591529)"),
    ("2023-09-28", 81667, "ANDE - Energy Payment via Third Party (Ref: 595158552)"),
    ("2023-11-13", 88675, "ANDE - Energy Payment via Milennia"),
]

# Coinbase ANDE payment (1 transaction - $68,665)
coinbase_ande = [
    ("2023-04-27", 68665, "ANDE - Energy Payment via Coinbase"),
]

# Payroll/Contractor Expenses via Milennia
# Total third-party payments: $410,908
# Minus ANDE portion: $347,800
# Remaining: $63,108
# Distributing across the payment dates proportionally
payroll_expenses = [
    ("2023-06-22", 19143, "Contractor/Partner Payroll via Milennia (Ref: 7478)"),
    ("2023-07-17", 23811, "Contractor/Partner Payroll via Milennia (Ref: 7479)"),
    ("2023-08-22", 5624, "Contractor/Partner Payroll via Milennia (Ref: 7480)"),
    ("2023-11-10", 14000, "Contractor/Partner Payroll via Milennia (Ref: 7482)"),
    ("2023-11-17", 530, "Contractor/Partner Payroll via Milennia (Ref: 7484)"),
]

# NOTE: Fernando payment removed as we need clarification on amount breakdown
# Nov 30: $57,252 total - need to know ANDE vs payroll split

print("=" * 80)
print("ADDING 2023 SPLIT EXPENSES TO DATABASE")
print("=" * 80)
print(f"Tenant: {TENANT_ID}")
print(f"Entity: {ENTITY}")
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

added_ande = []
added_coinbase = []
added_payroll = []
errors = []

# Add ANDE expenses
print("\n1️⃣  ADDING ANDE ENERGY EXPENSES")
print("=" * 80)
for date_str, amount, description in ande_expenses:
    try:
        transaction_id = str(uuid.uuid4())
        expense_amount = -abs(amount)

        result = db_manager.execute_query(
            insert_query,
            (
                transaction_id, TENANT_ID, date_str, description, expense_amount, CURRENCY, expense_amount,
                ENTITY, 'COGS', 'Utilities', 'ANDE Energy', CONFIDENCE,
                'Manual entry - ANDE Energy payment via third party',
                'Delta Mining Paraguay S.A.', 'ANDE (Administración Nacional de Electricidad)',
                'manual_entry_2023_split.py',
            ),
            fetch_one=True
        )
        added_ande.append({'date': date_str, 'amount': amount, 'description': description})
        print(f"✅ {date_str} | ${amount:>10,} | ANDE Energy")
    except Exception as e:
        errors.append({'date': date_str, 'amount': amount, 'error': str(e)})
        print(f"❌ {date_str} | ${amount:>10,} | {str(e)[:50]}")

# Add Coinbase ANDE payment
print("\n2️⃣  ADDING COINBASE ANDE PAYMENT")
print("=" * 80)
for date_str, amount, description in coinbase_ande:
    try:
        transaction_id = str(uuid.uuid4())
        expense_amount = -abs(amount)

        result = db_manager.execute_query(
            insert_query,
            (
                transaction_id, TENANT_ID, date_str, description, expense_amount, CURRENCY, expense_amount,
                ENTITY, 'COGS', 'Utilities', 'ANDE Energy', CONFIDENCE,
                'Manual entry - ANDE Energy payment via Coinbase',
                'Delta Mining Paraguay S.A.', 'ANDE (Administración Nacional de Electricidad)',
                'manual_entry_2023_split.py',
            ),
            fetch_one=True
        )
        added_coinbase.append({'date': date_str, 'amount': amount, 'description': description})
        print(f"✅ {date_str} | ${amount:>10,} | ANDE via Coinbase")
    except Exception as e:
        errors.append({'date': date_str, 'amount': amount, 'error': str(e)})
        print(f"❌ {date_str} | ${amount:>10,} | {str(e)[:50]}")

# Add Payroll expenses
print("\n3️⃣  ADDING CONTRACTOR/PAYROLL EXPENSES")
print("=" * 80)
for date_str, amount, description in payroll_expenses:
    try:
        transaction_id = str(uuid.uuid4())
        expense_amount = -abs(amount)

        result = db_manager.execute_query(
            insert_query,
            (
                transaction_id, TENANT_ID, date_str, description, expense_amount, CURRENCY, expense_amount,
                ENTITY, 'Operating Expenses', 'Contractor Payments', 'Contractor/Partner Payroll via Milennia', CONFIDENCE,
                'Manual entry - Contractor payroll via third party',
                'Delta Mining Paraguay S.A.', 'Milennia (Third-party payroll processor)',
                'manual_entry_2023_split.py',
            ),
            fetch_one=True
        )
        added_payroll.append({'date': date_str, 'amount': amount, 'description': description})
        print(f"✅ {date_str} | ${amount:>10,} | Contractor Payroll")
    except Exception as e:
        errors.append({'date': date_str, 'amount': amount, 'error': str(e)})
        print(f"❌ {date_str} | ${amount:>10,} | {str(e)[:50]}")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"✅ ANDE Energy expenses added: {len(added_ande)} (${sum(t['amount'] for t in added_ande):,.2f})")
print(f"✅ Coinbase ANDE payment added: {len(added_coinbase)} (${sum(t['amount'] for t in added_coinbase):,.2f})")
print(f"✅ Contractor payroll added: {len(added_payroll)} (${sum(t['amount'] for t in added_payroll):,.2f})")
print(f"❌ Errors: {len(errors)}")

total_added = sum(t['amount'] for t in added_ande) + sum(t['amount'] for t in added_coinbase) + sum(t['amount'] for t in added_payroll)
print(f"\n💰 Total amount added: ${total_added:,.2f}")

if errors:
    print("\nERRORS:")
    for err in errors:
        print(f"  {err['date']}: ${err['amount']:,} - {err['error']}")

print("\n📝 NOTE: Fernando payment (Nov 30: $57,252) NOT included - needs ANDE vs payroll breakdown")
print("=" * 80)
