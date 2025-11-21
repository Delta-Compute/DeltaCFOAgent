#!/usr/bin/env python3
"""
Investigation: Why whitelisted wallet transactions aren't being classified
"""

import sys
sys.path.append('web_ui')

from database import db_manager

# Check if the wallet address 0x88cAa22 exists in the database
wallet_query = """
SELECT wallet_address, entity_name, wallet_type, purpose, confidence_score
FROM wallet_addresses
WHERE tenant_id = 'delta'
AND (wallet_address ILIKE '%88caa22%' OR wallet_address ILIKE '%88c%')
ORDER BY created_at DESC
"""

print("=" * 80)
print("STEP 1: Checking wallet_addresses table")
print("=" * 80)

wallets = db_manager.execute_query(wallet_query, fetch_all=True)

if wallets:
    print(f"\nFound {len(wallets)} matching wallets:")
    for wallet in wallets:
        print(f"\n  Address: {wallet.get('wallet_address')}")
        print(f"  Entity: {wallet.get('entity_name')}")
        print(f"  Type: {wallet.get('wallet_type')}")
        print(f"  Purpose: {wallet.get('purpose')}")
        print(f"  Confidence: {wallet.get('confidence_score')}")
else:
    print("\n❌ NO WALLETS FOUND - This is the problem!")
    print("\nThe wallet address 0x88cAa22... needs to be added to wallet_addresses table")
    print("User should add it via /whitelisted-accounts page")

# Check the transaction
print("\n" + "=" * 80)
print("STEP 2: Checking transaction with wallet address")
print("=" * 80)

txn_query = """
SELECT transaction_id, date, description, destination, destination_display,
       classified_entity, accounting_category, subcategory, justification,
       confidence
FROM transactions
WHERE tenant_id = 'delta'
AND (description ILIKE '%88caa22%' OR destination ILIKE '%88caa22%')
ORDER BY date DESC
LIMIT 5
"""

transactions = db_manager.execute_query(txn_query, fetch_all=True)

if transactions:
    print(f"\nFound {len(transactions)} transactions with this wallet:")
    for txn in transactions:
        print(f"\n  Transaction ID: {txn.get('transaction_id')}")
        print(f"  Date: {txn.get('date')}")
        print(f"  Description: {txn.get('description')[:80]}...")
        print(f"  Destination (raw): {txn.get('destination')}")
        print(f"  Destination (display): {txn.get('destination_display')}")
        print(f"  Entity: {txn.get('classified_entity')}")
        print(f"  Category: {txn.get('accounting_category')}")
        print(f"  Subcategory: {txn.get('subcategory')}")
        print(f"  Justification: {txn.get('justification')}")
        print(f"  Confidence: {txn.get('confidence')}")
else:
    print("\n  No transactions found with this wallet address")

print("\n" + "=" * 80)
print("DIAGNOSIS:")
print("=" * 80)

if not wallets:
    print("""
❌ ROOT CAUSE: Wallet address 0x88cAa22... is NOT in the wallet_addresses table

SOLUTION:
1. User needs to add this wallet to the whitelisted accounts page
2. Go to /whitelisted-accounts
3. Add the wallet with:
   - Address: 0x88cAa22...
   - Entity Name: (e.g., "MEXC Exchange", "Coinbase Wallet", etc.)
   - Wallet Type: (e.g., "exchange", "vendor", "customer")
   - Purpose: (e.g., "Exchange account for crypto trading")
    """)
elif wallets and transactions:
    print("""
⚠️  PARTIAL ISSUE: Wallet exists in database but classification not applied

Current Status:
- ✅ Wallet is whitelisted
- ❌ Transaction classification missing

The system should automatically classify transactions based on wallet data:
- Entity should be set to wallet's entity_name
- Category should be based on wallet_type
- Description should include destination_display (friendly name)
- Justification should reference the wallet purpose

NEXT STEP: Fix the classification logic to use wallet data
    """)
else:
    print("""
✅ Wallet is in database, but no matching transactions found

This might be a different issue - check if:
1. Transaction was imported correctly
2. Wallet address in transaction matches exactly
3. Tenant ID is correct
    """)

print("=" * 80)
