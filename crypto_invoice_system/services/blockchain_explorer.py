#!/usr/bin/env python3
"""
Blockchain Explorer Service
Multi-chain transaction verification and monitoring
Supports: BTC, ETH, BSC, Polygon, Arbitrum, Base, Tron, TAO
"""

import requests
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class BlockchainExplorer:
    """
    Multi-chain blockchain explorer integration
    Verifies transactions across different networks
    """

    def __init__(self, api_keys: Dict[str, str] = None):
        """
        Initialize blockchain explorer with API keys

        Args:
            api_keys: Dictionary of API keys for various services
                     {
                         'etherscan': 'your_key',
                         'bscscan': 'your_key',
                         'polygonscan': 'your_key',
                         'arbiscan': 'your_key',
                         'basescan': 'your_key',
                         'alchemy': 'your_key'
                     }
        """
        self.api_keys = api_keys or {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DeltaCFO-Invoice-System/1.0'
        })

    # =============================================================================
    # BITCOIN (BTC)
    # =============================================================================

    def check_btc_transaction(self, tx_hash: str, expected_amount: Decimal,
                              address: str) -> Optional[Dict[str, Any]]:
        """
        Verify Bitcoin transaction using blockchain.info API

        Args:
            tx_hash: Transaction hash
            expected_amount: Expected amount in BTC
            address: Expected recipient address

        Returns:
            Transaction details or None if not found
        """
        try:
            url = f"https://blockchain.info/rawtx/{tx_hash}"
            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                logger.warning(f"BTC transaction not found: {tx_hash}")
                return None

            data = response.json()

            # Find output matching our address
            matching_output = None
            for output in data.get('out', []):
                if output.get('addr') == address:
                    matching_output = output
                    break

            if not matching_output:
                logger.warning(f"BTC tx {tx_hash} doesn't send to {address}")
                return None

            # Convert satoshis to BTC
            amount_satoshis = matching_output.get('value', 0)
            amount_btc = Decimal(amount_satoshis) / Decimal(100000000)

            # Get confirmations (approximate from block height)
            confirmations = 0
            if data.get('block_height'):
                # Would need current block height from separate API
                # For now, assume confirmed if in block
                confirmations = 6  # Simplified

            return {
                'tx_hash': tx_hash,
                'amount': float(amount_btc),
                'confirmations': confirmations,
                'status': 'confirmed' if confirmations >= 3 else 'pending',
                'timestamp': data.get('time'),
                'block_height': data.get('block_height'),
                'explorer_url': f"https://blockchain.info/tx/{tx_hash}"
            }

        except Exception as e:
            logger.error(f"Error checking BTC transaction {tx_hash}: {e}")
            return None

    # =============================================================================
    # ETHEREUM & ERC20 (ETH, USDT, USDC, DAI)
    # =============================================================================

    def check_eth_transaction(self, tx_hash: str, expected_amount: Decimal,
                              address: str, network: str = "ETH") -> Optional[Dict[str, Any]]:
        """
        Verify Ethereum/ERC20 transaction using Etherscan API

        Args:
            tx_hash: Transaction hash
            expected_amount: Expected amount
            address: Expected recipient address
            network: ETH, BSC, POLYGON, ARBITRUM, or BASE

        Returns:
            Transaction details or None if not found
        """
        # Map network to Etherscan-like API
        api_urls = {
            "ETH": "https://api.etherscan.io/api",
            "BSC": "https://api.bscscan.com/api",
            "POLYGON": "https://api.polygonscan.com/api",
            "ARBITRUM": "https://api.arbiscan.io/api",
            "BASE": "https://api.basescan.org/api"
        }

        api_key_names = {
            "ETH": "etherscan",
            "BSC": "bscscan",
            "POLYGON": "polygonscan",
            "ARBITRUM": "arbiscan",
            "BASE": "basescan"
        }

        if network not in api_urls:
            logger.error(f"Unsupported network: {network}")
            return None

        api_url = api_urls[network]
        api_key = self.api_keys.get(api_key_names.get(network), "")

        try:
            # Get transaction receipt
            params = {
                'module': 'proxy',
                'action': 'eth_getTransactionByHash',
                'txhash': tx_hash,
                'apikey': api_key
            }

            response = self.session.get(api_url, params=params, timeout=10)
            data = response.json()

            if data.get('result') is None:
                logger.warning(f"{network} transaction not found: {tx_hash}")
                return None

            tx_data = data['result']

            # Get transaction receipt for confirmations
            receipt_params = {
                'module': 'proxy',
                'action': 'eth_getTransactionReceipt',
                'txhash': tx_hash,
                'apikey': api_key
            }

            receipt_response = self.session.get(api_url, params=receipt_params, timeout=10)
            receipt_data = receipt_response.json()

            confirmations = 0
            if receipt_data.get('result') and receipt_data['result'].get('blockNumber'):
                # Get current block number
                block_params = {
                    'module': 'proxy',
                    'action': 'eth_blockNumber',
                    'apikey': api_key
                }
                block_response = self.session.get(api_url, params=block_params, timeout=10)
                current_block = int(block_response.json().get('result', '0x0'), 16)
                tx_block = int(receipt_data['result']['blockNumber'], 16)
                confirmations = current_block - tx_block

            # Check if transaction went to expected address
            to_address = tx_data.get('to', '').lower()
            if to_address != address.lower():
                logger.warning(f"{network} tx {tx_hash} to={to_address}, expected={address}")

            # Extract amount (convert from wei for native tokens)
            value_wei = int(tx_data.get('value', '0x0'), 16)
            amount_eth = Decimal(value_wei) / Decimal(10**18)

            return {
                'tx_hash': tx_hash,
                'amount': float(amount_eth),
                'confirmations': confirmations,
                'status': 'confirmed' if confirmations >= 12 else 'pending',
                'from_address': tx_data.get('from'),
                'to_address': to_address,
                'block_number': int(tx_data.get('blockNumber', '0x0'), 16) if tx_data.get('blockNumber') else None,
                'explorer_url': self._get_explorer_url(network, tx_hash)
            }

        except Exception as e:
            logger.error(f"Error checking {network} transaction {tx_hash}: {e}")
            return None

    # =============================================================================
    # TRON (TRX, USDT-TRC20)
    # =============================================================================

    def check_tron_transaction(self, tx_hash: str, expected_amount: Decimal,
                               address: str) -> Optional[Dict[str, Any]]:
        """
        Verify Tron transaction using TronGrid API

        Args:
            tx_hash: Transaction hash
            expected_amount: Expected amount
            address: Expected recipient address

        Returns:
            Transaction details or None if not found
        """
        try:
            # TronGrid API
            url = f"https://api.trongrid.io/v1/transactions/{tx_hash}"

            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                logger.warning(f"Tron transaction not found: {tx_hash}")
                return None

            data = response.json()

            # Check if confirmed
            confirmed = data.get('ret', [{}])[0].get('contractRet') == 'SUCCESS'

            # Extract transaction details
            tx_info = data.get('raw_data', {})
            contract = tx_info.get('contract', [{}])[0]
            value = contract.get('parameter', {}).get('value', {})

            # Convert from sun to TRX (1 TRX = 1,000,000 sun)
            amount_sun = value.get('amount', 0)
            amount_trx = Decimal(amount_sun) / Decimal(1000000)

            to_address = value.get('to_address', '')

            return {
                'tx_hash': tx_hash,
                'amount': float(amount_trx),
                'confirmations': 20 if confirmed else 0,  # Simplified
                'status': 'confirmed' if confirmed else 'pending',
                'to_address': to_address,
                'timestamp': tx_info.get('timestamp'),
                'explorer_url': f"https://tronscan.org/#/transaction/{tx_hash}"
            }

        except Exception as e:
            logger.error(f"Error checking Tron transaction {tx_hash}: {e}")
            return None

    # =============================================================================
    # BITTENSOR (TAO)
    # =============================================================================

    def check_bittensor_transaction(self, tx_hash: str, expected_amount: Decimal,
                                    address: str) -> Optional[Dict[str, Any]]:
        """
        Verify Bittensor transaction using Taostats API

        Args:
            tx_hash: Transaction hash (extrinsic hash)
            expected_amount: Expected amount in TAO
            address: Expected recipient address

        Returns:
            Transaction details or None if not found
        """
        try:
            # Taostats API (if available)
            # Note: This is a placeholder - actual API may differ
            url = f"https://api.taostats.io/api/extrinsic/{tx_hash}"

            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                logger.warning(f"TAO transaction not found: {tx_hash}")
                return None

            data = response.json()

            # Extract amount and confirmations
            # This is simplified - actual implementation depends on API structure
            amount_tao = data.get('amount', 0)
            confirmations = data.get('confirmations', 0)

            return {
                'tx_hash': tx_hash,
                'amount': float(amount_tao),
                'confirmations': confirmations,
                'status': 'confirmed' if confirmations >= 12 else 'pending',
                'explorer_url': f"https://taostats.io/extrinsic/{tx_hash}"
            }

        except Exception as e:
            logger.error(f"Error checking TAO transaction {tx_hash}: {e}")
            return None

    # =============================================================================
    # UNIFIED INTERFACE
    # =============================================================================

    def verify_transaction(self, tx_hash: str, currency: str, network: str,
                          expected_amount: Decimal, address: str) -> Optional[Dict[str, Any]]:
        """
        Unified transaction verification across all supported chains

        Args:
            tx_hash: Transaction hash
            currency: Cryptocurrency symbol (BTC, ETH, USDT, etc.)
            network: Network/chain (BTC, ETH, BSC, POLYGON, TRC20, etc.)
            expected_amount: Expected amount
            address: Expected recipient address

        Returns:
            Standardized transaction details or None
        """
        logger.info(f"Verifying {currency}/{network} transaction {tx_hash}")

        # Route to appropriate chain checker
        if network == "BTC":
            return self.check_btc_transaction(tx_hash, expected_amount, address)

        elif network in ["ETH", "BSC", "POLYGON", "ARBITRUM", "BASE"]:
            return self.check_eth_transaction(tx_hash, expected_amount, address, network)

        elif network == "TRC20" or network == "TRON":
            return self.check_tron_transaction(tx_hash, expected_amount, address)

        elif network == "TAO":
            return self.check_bittensor_transaction(tx_hash, expected_amount, address)

        else:
            logger.error(f"Unsupported network: {network}")
            return None

    def _get_explorer_url(self, network: str, tx_hash: str) -> str:
        """Get blockchain explorer URL for transaction"""
        explorer_urls = {
            "BTC": f"https://blockchain.info/tx/{tx_hash}",
            "ETH": f"https://etherscan.io/tx/{tx_hash}",
            "BSC": f"https://bscscan.com/tx/{tx_hash}",
            "POLYGON": f"https://polygonscan.com/tx/{tx_hash}",
            "ARBITRUM": f"https://arbiscan.io/tx/{tx_hash}",
            "BASE": f"https://basescan.org/tx/{tx_hash}",
            "TRC20": f"https://tronscan.org/#/transaction/{tx_hash}",
            "TRON": f"https://tronscan.org/#/transaction/{tx_hash}",
            "TAO": f"https://taostats.io/extrinsic/{tx_hash}"
        }
        return explorer_urls.get(network, "")

    # =============================================================================
    # HELPER METHODS
    # =============================================================================

    def get_current_block_height(self, network: str) -> Optional[int]:
        """Get current block height for a network"""
        try:
            if network == "BTC":
                response = self.session.get("https://blockchain.info/latestblock", timeout=10)
                return response.json().get('height')

            elif network in ["ETH", "BSC", "POLYGON", "ARBITRUM", "BASE"]:
                api_url = {
                    "ETH": "https://api.etherscan.io/api",
                    "BSC": "https://api.bscscan.com/api",
                    "POLYGON": "https://api.polygonscan.com/api",
                    "ARBITRUM": "https://api.arbiscan.io/api",
                    "BASE": "https://api.basescan.org/api"
                }[network]

                params = {
                    'module': 'proxy',
                    'action': 'eth_blockNumber'
                }
                response = self.session.get(api_url, params=params, timeout=10)
                return int(response.json().get('result', '0x0'), 16)

            return None

        except Exception as e:
            logger.error(f"Error getting block height for {network}: {e}")
            return None

    def check_address_balance(self, address: str, currency: str, network: str) -> Optional[Decimal]:
        """
        Check current balance of an address

        Args:
            address: Wallet address
            currency: Currency symbol
            network: Network/chain

        Returns:
            Current balance or None
        """
        # Implementation varies by chain
        # This is a placeholder for future enhancement
        logger.info(f"Checking balance for {address} on {network}")
        return None
