-- Migration: Add blockchain configuration tables
-- Date: 2025-10-22
-- Description: Creates tables to store blockchain chain and token configurations

-- =============================================================================
-- BLOCKCHAIN CHAINS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS crypto_blockchain_chains (
    id SERIAL PRIMARY KEY,
    chain_id VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    native_token VARCHAR(10) NOT NULL,
    required_confirmations INTEGER NOT NULL DEFAULT 6,
    block_explorer_url VARCHAR(255) NOT NULL,
    block_explorer_tx_path VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE crypto_blockchain_chains IS 'Supported blockchain networks configuration';
COMMENT ON COLUMN crypto_blockchain_chains.chain_id IS 'Unique chain identifier (e.g., BTC, ETH, BSC)';
COMMENT ON COLUMN crypto_blockchain_chains.required_confirmations IS 'Number of confirmations needed for payment verification';
COMMENT ON COLUMN crypto_blockchain_chains.block_explorer_url IS 'Base URL for blockchain explorer';
COMMENT ON COLUMN crypto_blockchain_chains.block_explorer_tx_path IS 'Path segment for transaction URLs';

-- =============================================================================
-- BLOCKCHAIN TOKENS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS crypto_blockchain_tokens (
    id SERIAL PRIMARY KEY,
    chain_id VARCHAR(20) NOT NULL REFERENCES crypto_blockchain_chains(chain_id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    decimals INTEGER NOT NULL DEFAULT 18,
    is_stablecoin BOOLEAN DEFAULT FALSE,
    payment_tolerance DECIMAL(6,5) DEFAULT 0.005,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chain_id, symbol)
);

COMMENT ON TABLE crypto_blockchain_tokens IS 'Supported tokens per blockchain';
COMMENT ON COLUMN crypto_blockchain_tokens.decimals IS 'Number of decimal places for token';
COMMENT ON COLUMN crypto_blockchain_tokens.is_stablecoin IS 'Whether token is a stablecoin (tighter tolerance)';
COMMENT ON COLUMN crypto_blockchain_tokens.payment_tolerance IS 'Acceptable payment variance (e.g., 0.005 = 0.5%)';

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_crypto_chains_enabled ON crypto_blockchain_chains(enabled);
CREATE INDEX IF NOT EXISTS idx_crypto_tokens_chain ON crypto_blockchain_tokens(chain_id);
CREATE INDEX IF NOT EXISTS idx_crypto_tokens_enabled ON crypto_blockchain_tokens(chain_id, enabled);

-- =============================================================================
-- SEED DATA
-- =============================================================================

-- Insert supported blockchain chains
INSERT INTO crypto_blockchain_chains (chain_id, name, display_name, native_token, required_confirmations, block_explorer_url, block_explorer_tx_path, enabled) VALUES
    ('BTC', 'Bitcoin', 'Bitcoin (BTC)', 'BTC', 3, 'https://blockchair.com/bitcoin', '/transaction/', TRUE),
    ('ETH', 'Ethereum', 'Ethereum (ERC20)', 'ETH', 12, 'https://etherscan.io', '/tx/', TRUE),
    ('BSC', 'Binance Smart Chain', 'Binance Smart Chain (BEP20)', 'BNB', 15, 'https://bscscan.com', '/tx/', TRUE),
    ('POLYGON', 'Polygon', 'Polygon (MATIC)', 'MATIC', 128, 'https://polygonscan.com', '/tx/', TRUE),
    ('ARBITRUM', 'Arbitrum', 'Arbitrum One', 'ETH', 1, 'https://arbiscan.io', '/tx/', TRUE),
    ('BASE', 'Base', 'Base (Coinbase L2)', 'ETH', 1, 'https://basescan.org', '/tx/', TRUE),
    ('TRC20', 'Tron', 'Tron (TRC20)', 'TRX', 20, 'https://tronscan.org', '/#/transaction/', TRUE),
    ('TAO', 'Bittensor', 'Bittensor (TAO)', 'TAO', 12, 'https://taostats.io', '/extrinsic/', TRUE)
ON CONFLICT (chain_id) DO NOTHING;

-- Insert supported tokens per chain
INSERT INTO crypto_blockchain_tokens (chain_id, symbol, name, decimals, is_stablecoin, payment_tolerance, enabled) VALUES
    -- Bitcoin
    ('BTC', 'BTC', 'Bitcoin', 8, FALSE, 0.005, TRUE),

    -- Ethereum
    ('ETH', 'ETH', 'Ethereum', 18, FALSE, 0.005, TRUE),
    ('ETH', 'USDT', 'Tether USD', 6, TRUE, 0.001, TRUE),
    ('ETH', 'USDC', 'USD Coin', 6, TRUE, 0.001, TRUE),
    ('ETH', 'DAI', 'Dai Stablecoin', 18, TRUE, 0.001, TRUE),

    -- BSC
    ('BSC', 'BNB', 'BNB', 18, FALSE, 0.005, TRUE),
    ('BSC', 'USDT', 'Tether USD', 18, TRUE, 0.001, TRUE),
    ('BSC', 'USDC', 'USD Coin', 18, TRUE, 0.001, TRUE),
    ('BSC', 'BUSD', 'Binance USD', 18, TRUE, 0.001, TRUE),

    -- Polygon
    ('POLYGON', 'MATIC', 'Polygon', 18, FALSE, 0.005, TRUE),
    ('POLYGON', 'USDT', 'Tether USD', 6, TRUE, 0.001, TRUE),
    ('POLYGON', 'USDC', 'USD Coin', 6, TRUE, 0.001, TRUE),
    ('POLYGON', 'DAI', 'Dai Stablecoin', 18, TRUE, 0.001, TRUE),

    -- Arbitrum
    ('ARBITRUM', 'ETH', 'Ethereum', 18, FALSE, 0.005, TRUE),
    ('ARBITRUM', 'USDT', 'Tether USD', 6, TRUE, 0.001, TRUE),
    ('ARBITRUM', 'USDC', 'USD Coin', 6, TRUE, 0.001, TRUE),
    ('ARBITRUM', 'DAI', 'Dai Stablecoin', 18, TRUE, 0.001, TRUE),

    -- Base
    ('BASE', 'ETH', 'Ethereum', 18, FALSE, 0.005, TRUE),
    ('BASE', 'USDC', 'USD Coin', 6, TRUE, 0.001, TRUE),
    ('BASE', 'DAI', 'Dai Stablecoin', 18, TRUE, 0.001, TRUE),

    -- Tron
    ('TRC20', 'TRX', 'Tron', 6, FALSE, 0.005, TRUE),
    ('TRC20', 'USDT', 'Tether USD', 6, TRUE, 0.001, TRUE),

    -- Bittensor
    ('TAO', 'TAO', 'Bittensor', 9, FALSE, 0.005, TRUE)
ON CONFLICT (chain_id, symbol) DO NOTHING;
