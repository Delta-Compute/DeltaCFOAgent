#!/usr/bin/env python3
"""
Blockchain Configuration
Defines supported chains, tokens, confirmations, and explorer URLs
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class TokenConfig:
    """Configuration for a cryptocurrency token"""
    symbol: str
    name: str
    decimals: int
    stablecoin: bool = False
    enabled: bool = True


@dataclass
class ChainConfig:
    """Configuration for a blockchain network"""
    chain_id: str
    name: str
    display_name: str
    native_token: str
    supported_tokens: List[TokenConfig]
    required_confirmations: int
    block_explorer_url: str
    block_explorer_tx_path: str
    enabled: bool = True


# =============================================================================
# BLOCKCHAIN CONFIGURATIONS
# =============================================================================

# Bitcoin
BITCOIN_CONFIG = ChainConfig(
    chain_id="BTC",
    name="Bitcoin",
    display_name="Bitcoin (BTC)",
    native_token="BTC",
    supported_tokens=[
        TokenConfig(symbol="BTC", name="Bitcoin", decimals=8, stablecoin=False)
    ],
    required_confirmations=3,
    block_explorer_url="https://blockchair.com/bitcoin",
    block_explorer_tx_path="/transaction/"
)

# Ethereum (ERC20)
ETHEREUM_CONFIG = ChainConfig(
    chain_id="ETH",
    name="Ethereum",
    display_name="Ethereum (ERC20)",
    native_token="ETH",
    supported_tokens=[
        TokenConfig(symbol="ETH", name="Ethereum", decimals=18, stablecoin=False),
        TokenConfig(symbol="USDT", name="Tether USD", decimals=6, stablecoin=True),
        TokenConfig(symbol="USDC", name="USD Coin", decimals=6, stablecoin=True),
        TokenConfig(symbol="DAI", name="Dai Stablecoin", decimals=18, stablecoin=True),
    ],
    required_confirmations=12,
    block_explorer_url="https://etherscan.io",
    block_explorer_tx_path="/tx/"
)

# Binance Smart Chain (BEP20)
BSC_CONFIG = ChainConfig(
    chain_id="BSC",
    name="Binance Smart Chain",
    display_name="Binance Smart Chain (BEP20)",
    native_token="BNB",
    supported_tokens=[
        TokenConfig(symbol="BNB", name="BNB", decimals=18, stablecoin=False),
        TokenConfig(symbol="USDT", name="Tether USD", decimals=18, stablecoin=True),
        TokenConfig(symbol="USDC", name="USD Coin", decimals=18, stablecoin=True),
        TokenConfig(symbol="BUSD", name="Binance USD", decimals=18, stablecoin=True),
    ],
    required_confirmations=15,
    block_explorer_url="https://bscscan.com",
    block_explorer_tx_path="/tx/"
)

# Polygon (MATIC)
POLYGON_CONFIG = ChainConfig(
    chain_id="POLYGON",
    name="Polygon",
    display_name="Polygon (MATIC)",
    native_token="MATIC",
    supported_tokens=[
        TokenConfig(symbol="MATIC", name="Polygon", decimals=18, stablecoin=False),
        TokenConfig(symbol="USDT", name="Tether USD", decimals=6, stablecoin=True),
        TokenConfig(symbol="USDC", name="USD Coin", decimals=6, stablecoin=True),
        TokenConfig(symbol="DAI", name="Dai Stablecoin", decimals=18, stablecoin=True),
    ],
    required_confirmations=128,
    block_explorer_url="https://polygonscan.com",
    block_explorer_tx_path="/tx/"
)

# Arbitrum
ARBITRUM_CONFIG = ChainConfig(
    chain_id="ARBITRUM",
    name="Arbitrum",
    display_name="Arbitrum One",
    native_token="ETH",
    supported_tokens=[
        TokenConfig(symbol="ETH", name="Ethereum", decimals=18, stablecoin=False),
        TokenConfig(symbol="USDT", name="Tether USD", decimals=6, stablecoin=True),
        TokenConfig(symbol="USDC", name="USD Coin", decimals=6, stablecoin=True),
        TokenConfig(symbol="DAI", name="Dai Stablecoin", decimals=18, stablecoin=True),
    ],
    required_confirmations=1,  # Arbitrum finality is fast
    block_explorer_url="https://arbiscan.io",
    block_explorer_tx_path="/tx/"
)

# Base (Coinbase L2)
BASE_CONFIG = ChainConfig(
    chain_id="BASE",
    name="Base",
    display_name="Base (Coinbase L2)",
    native_token="ETH",
    supported_tokens=[
        TokenConfig(symbol="ETH", name="Ethereum", decimals=18, stablecoin=False),
        TokenConfig(symbol="USDC", name="USD Coin", decimals=6, stablecoin=True),
        TokenConfig(symbol="DAI", name="Dai Stablecoin", decimals=18, stablecoin=True),
    ],
    required_confirmations=1,
    block_explorer_url="https://basescan.org",
    block_explorer_tx_path="/tx/"
)

# Tron (TRC20)
TRON_CONFIG = ChainConfig(
    chain_id="TRC20",
    name="Tron",
    display_name="Tron (TRC20)",
    native_token="TRX",
    supported_tokens=[
        TokenConfig(symbol="TRX", name="Tron", decimals=6, stablecoin=False),
        TokenConfig(symbol="USDT", name="Tether USD", decimals=6, stablecoin=True),
    ],
    required_confirmations=20,
    block_explorer_url="https://tronscan.org",
    block_explorer_tx_path="/#/transaction/"
)

# Bittensor (TAO)
BITTENSOR_CONFIG = ChainConfig(
    chain_id="TAO",
    name="Bittensor",
    display_name="Bittensor (TAO)",
    native_token="TAO",
    supported_tokens=[
        TokenConfig(symbol="TAO", name="Bittensor", decimals=9, stablecoin=False),
    ],
    required_confirmations=12,
    block_explorer_url="https://taostats.io",
    block_explorer_tx_path="/extrinsic/"
)


# =============================================================================
# BLOCKCHAIN REGISTRY
# =============================================================================

class BlockchainRegistry:
    """Registry of all supported blockchain configurations"""

    def __init__(self):
        self._chains: Dict[str, ChainConfig] = {
            "BTC": BITCOIN_CONFIG,
            "ETH": ETHEREUM_CONFIG,
            "BSC": BSC_CONFIG,
            "POLYGON": POLYGON_CONFIG,
            "ARBITRUM": ARBITRUM_CONFIG,
            "BASE": BASE_CONFIG,
            "TRC20": TRON_CONFIG,
            "TAO": BITTENSOR_CONFIG,
        }

    def get_chain(self, chain_id: str) -> Optional[ChainConfig]:
        """Get chain configuration by ID"""
        return self._chains.get(chain_id.upper())

    def get_all_chains(self, enabled_only: bool = True) -> List[ChainConfig]:
        """Get all chain configurations"""
        chains = list(self._chains.values())
        if enabled_only:
            chains = [c for c in chains if c.enabled]
        return chains

    def get_chain_tokens(self, chain_id: str, enabled_only: bool = True) -> List[TokenConfig]:
        """Get all tokens supported on a chain"""
        chain = self.get_chain(chain_id)
        if not chain:
            return []

        tokens = chain.supported_tokens
        if enabled_only:
            tokens = [t for t in tokens if t.enabled]
        return tokens

    def get_token_on_chain(self, chain_id: str, token_symbol: str) -> Optional[TokenConfig]:
        """Get specific token configuration on a chain"""
        tokens = self.get_chain_tokens(chain_id, enabled_only=False)
        for token in tokens:
            if token.symbol.upper() == token_symbol.upper():
                return token
        return None

    def get_confirmations_required(self, chain_id: str) -> int:
        """Get required confirmations for a chain"""
        chain = self.get_chain(chain_id)
        return chain.required_confirmations if chain else 6  # Default to 6

    def get_explorer_tx_url(self, chain_id: str, tx_hash: str) -> str:
        """Get block explorer URL for a transaction"""
        chain = self.get_chain(chain_id)
        if not chain:
            return ""

        return f"{chain.block_explorer_url}{chain.block_explorer_tx_path}{tx_hash}"

    def is_stablecoin(self, chain_id: str, token_symbol: str) -> bool:
        """Check if a token is a stablecoin"""
        token = self.get_token_on_chain(chain_id, token_symbol)
        return token.stablecoin if token else False

    def get_payment_tolerance(self, chain_id: str, token_symbol: str) -> float:
        """Get payment tolerance percentage for a token"""
        # Stablecoins have tighter tolerance (0.1%)
        # Native tokens have looser tolerance (0.5%)
        if self.is_stablecoin(chain_id, token_symbol):
            return 0.001  # 0.1%
        else:
            return 0.005  # 0.5%


# Global registry instance
blockchain_registry = BlockchainRegistry()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_supported_chains() -> List[Dict[str, str]]:
    """Get list of supported chains for UI dropdowns"""
    return [
        {
            "id": chain.chain_id,
            "name": chain.display_name,
            "native_token": chain.native_token
        }
        for chain in blockchain_registry.get_all_chains()
    ]


def get_supported_tokens(chain_id: str) -> List[Dict[str, str]]:
    """Get list of supported tokens for a chain (UI dropdowns)"""
    tokens = blockchain_registry.get_chain_tokens(chain_id)
    return [
        {
            "symbol": token.symbol,
            "name": token.name,
            "decimals": token.decimals,
            "stablecoin": token.stablecoin
        }
        for token in tokens
    ]


def get_explorer_link(chain_id: str, tx_hash: str) -> str:
    """Get block explorer link for a transaction"""
    return blockchain_registry.get_explorer_tx_url(chain_id, tx_hash)


def get_confirmations_for_chain(chain_id: str) -> int:
    """Get required confirmations for a chain"""
    return blockchain_registry.get_confirmations_required(chain_id)


def validate_chain_token_combo(chain_id: str, token_symbol: str) -> bool:
    """Validate that a token is supported on a chain"""
    token = blockchain_registry.get_token_on_chain(chain_id, token_symbol)
    return token is not None and token.enabled


# =============================================================================
# ALCHEMY INTEGRATION (PRD Requirement)
# =============================================================================

ALCHEMY_SUPPORTED_CHAINS = {
    "ETH": "eth-mainnet",
    "POLYGON": "polygon-mainnet",
    "ARBITRUM": "arb-mainnet",
    "BASE": "base-mainnet",
}


def get_alchemy_network(chain_id: str) -> Optional[str]:
    """Get Alchemy network identifier for a chain"""
    return ALCHEMY_SUPPORTED_CHAINS.get(chain_id.upper())


def is_alchemy_supported(chain_id: str) -> bool:
    """Check if chain is supported by Alchemy"""
    return chain_id.upper() in ALCHEMY_SUPPORTED_CHAINS
