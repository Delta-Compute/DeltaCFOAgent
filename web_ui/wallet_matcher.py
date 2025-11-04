"""
Wallet Address Matcher
Matches wallet addresses in transactions to friendly entity names from whitelisted wallets
"""
import re
from typing import Optional, Tuple
from database import db_manager


def is_wallet_address(address: str) -> bool:
    """
    Check if a string appears to be a wallet address

    Supports:
    - Ethereum/EVM: 0x followed by 40 hex chars
    - Bitcoin: Base58, 26-35 chars starting with 1, 3, or bc1
    - Shortened display format: 0x1234...abcd

    Args:
        address: String to check

    Returns:
        True if address appears to be a wallet address
    """
    if not address or len(address) < 10:
        return False

    address = str(address).strip()

    # Ethereum/EVM style (full address)
    if re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return True

    # Shortened display format (0x...abc)
    if re.match(r'^0x[a-fA-F0-9]{6,10}\.\.\.[a-fA-F0-9]{6,12}$', address):
        return True

    # Bitcoin P2PKH (starts with 1)
    if re.match(r'^1[a-km-zA-HJ-NP-Z1-9]{25,34}$', address):
        return True

    # Bitcoin P2SH (starts with 3)
    if re.match(r'^3[a-km-zA-HJ-NP-Z1-9]{25,34}$', address):
        return True

    # Bitcoin Bech32 (starts with bc1)
    if re.match(r'^bc1[a-zA-HJ-NP-Z0-9]{39,87}$', address):
        return True

    return False


def match_wallet_to_entity(wallet_address: str, tenant_id: str) -> Optional[str]:
    """
    Match a wallet address to a whitelisted entity name

    Args:
        wallet_address: The wallet address to match
        tenant_id: Tenant ID for isolation

    Returns:
        Entity name if match found, None otherwise
    """
    if not wallet_address or not is_wallet_address(wallet_address):
        return None

    # Normalize the wallet address (lowercase for case-insensitive matching)
    normalized_address = wallet_address.strip().lower()

    # Query whitelisted wallets for this tenant
    query = """
        SELECT entity_name, wallet_address
        FROM wallet_addresses
        WHERE tenant_id = %s
        AND is_active = TRUE
        ORDER BY confidence_score DESC
    """

    wallets = db_manager.execute_query(query, (tenant_id,), fetch_all=True)

    if not wallets:
        return None

    # Try exact match first
    for wallet in wallets:
        db_address = str(wallet.get('wallet_address', '')).strip().lower()
        if db_address == normalized_address:
            return wallet.get('entity_name')

    # Try matching shortened format (0x1234...abcd)
    if '...' in normalized_address:
        prefix, suffix = normalized_address.split('...', 1)

        for wallet in wallets:
            db_address = str(wallet.get('wallet_address', '')).strip().lower()
            if db_address.startswith(prefix) and db_address.endswith(suffix):
                return wallet.get('entity_name')

    # Try matching full address against shortened format in database
    else:
        for wallet in wallets:
            db_address = str(wallet.get('wallet_address', '')).strip().lower()
            if '...' in db_address:
                prefix, suffix = db_address.split('...', 1)
                if normalized_address.startswith(prefix) and normalized_address.endswith(suffix):
                    return wallet.get('entity_name')

    return None


def enrich_transaction_with_wallet_names(
    transaction: dict,
    tenant_id: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Enrich a transaction with wallet entity names

    Args:
        transaction: Transaction dict with origin and destination fields
        tenant_id: Tenant ID for isolation

    Returns:
        Tuple of (origin_display, destination_display)
        Returns None for fields that don't match wallets
    """
    origin = transaction.get('origin')
    destination = transaction.get('destination')

    origin_display = None
    destination_display = None

    # Check origin
    if origin and is_wallet_address(origin):
        origin_display = match_wallet_to_entity(origin, tenant_id)

    # Check destination
    if destination and is_wallet_address(destination):
        destination_display = match_wallet_to_entity(destination, tenant_id)

    return origin_display, destination_display


def update_transaction_wallet_displays(transaction_id: str, tenant_id: str) -> bool:
    """
    Update a single transaction's wallet display fields

    Args:
        transaction_id: Transaction ID to update
        tenant_id: Tenant ID for isolation

    Returns:
        True if updated, False otherwise
    """
    # Get transaction
    query = """
        SELECT origin, destination
        FROM transactions
        WHERE transaction_id = %s AND tenant_id = %s
    """

    result = db_manager.execute_query(query, (transaction_id, tenant_id), fetch_one=True)

    if not result:
        return False

    # Get wallet names
    origin_display, destination_display = enrich_transaction_with_wallet_names(
        {'origin': result.get('origin'), 'destination': result.get('destination')},
        tenant_id
    )

    # Update transaction if we found any wallet matches
    if origin_display or destination_display:
        update_query = """
            UPDATE transactions
            SET origin_display = %s,
                destination_display = %s
            WHERE transaction_id = %s AND tenant_id = %s
        """

        db_manager.execute_query(
            update_query,
            (origin_display, destination_display, transaction_id, tenant_id)
        )

        return True

    return False


def bulk_update_wallet_displays(tenant_id: str, limit: Optional[int] = None) -> int:
    """
    Update all transactions with wallet display names

    Args:
        tenant_id: Tenant ID for isolation
        limit: Optional limit for number of transactions to update

    Returns:
        Number of transactions updated
    """
    # Get all transactions with wallet-like origin or destination
    query = """
        SELECT transaction_id, origin, destination
        FROM transactions
        WHERE tenant_id = %s
        AND (
            origin LIKE '0x%%'
            OR origin LIKE '1%%'
            OR origin LIKE '3%%'
            OR origin LIKE 'bc1%%'
            OR destination LIKE '0x%%'
            OR destination LIKE '1%%'
            OR destination LIKE '3%%'
            OR destination LIKE 'bc1%%'
        )
    """

    if limit:
        query += f" LIMIT {limit}"

    transactions = db_manager.execute_query(query, (tenant_id,), fetch_all=True)

    updated_count = 0

    for txn in transactions:
        # Get wallet names
        origin_display, destination_display = enrich_transaction_with_wallet_names(txn, tenant_id)

        # Update if we found any wallet matches
        if origin_display or destination_display:
            update_query = """
                UPDATE transactions
                SET origin_display = %s,
                    destination_display = %s
                WHERE transaction_id = %s AND tenant_id = %s
            """

            db_manager.execute_query(
                update_query,
                (origin_display, destination_display, txn.get('transaction_id'), tenant_id)
            )

            updated_count += 1

    return updated_count
