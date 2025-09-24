#!/usr/bin/env python3
"""Historic crypto pricing database for accurate USD conversions"""

import sqlite3
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import os

class CryptoPricingDB:
    def __init__(self, db_path='crypto_pricing.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the pricing database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create historic_prices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historic_prices (
                date TEXT,
                symbol TEXT,
                price_usd REAL,
                PRIMARY KEY (date, symbol)
            )
        ''')

        conn.commit()
        conn.close()
        print(f"📊 Crypto pricing database initialized: {self.db_path}")

    def fetch_historic_prices_yahoo(self, symbol, start_date='2024-01-01', end_date=None):
        """Fetch historic prices from Yahoo Finance"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # Yahoo Finance symbols
        yahoo_symbols = {
            'BTC': 'BTC-USD',
            'TAO': 'TAO-USD',  # Bittensor
            'ETH': 'ETH-USD',
            'USDC': 'USDC-USD',
            'USDT': 'USDT-USD'
        }

        if symbol not in yahoo_symbols:
            print(f"⚠️ Symbol {symbol} not supported")
            return

        yahoo_symbol = yahoo_symbols[symbol]
        print(f"📈 Fetching {symbol} prices from Yahoo Finance ({yahoo_symbol})...")

        try:
            # Yahoo Finance historic data URL
            # Format: https://query1.finance.yahoo.com/v7/finance/download/BTC-USD?period1=start&period2=end&interval=1d
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())

            url = f"https://query1.finance.yahoo.com/v7/finance/download/{yahoo_symbol}"
            params = {
                'period1': start_ts,
                'period2': end_ts,
                'interval': '1d',
                'events': 'history'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            # Parse CSV data
            import io
            csv_data = io.StringIO(response.text)
            df = pd.read_csv(csv_data)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            inserted_count = 0
            for _, row in df.iterrows():
                date = row['Date']
                # Use Close price as the daily price
                price = float(row['Close'])

                # Insert or update price
                cursor.execute('''
                    INSERT OR REPLACE INTO historic_prices (date, symbol, price_usd)
                    VALUES (?, ?, ?)
                ''', (date, symbol, price))
                inserted_count += 1

            conn.commit()
            conn.close()

            print(f"✅ Inserted {inserted_count} {symbol} price records from Yahoo Finance")

        except Exception as e:
            print(f"❌ Error fetching {symbol} prices from Yahoo Finance: {e}")
            # Try alternative free API as fallback
            self.fetch_historic_prices_binance(symbol, start_date, end_date)

    def fetch_historic_prices_binance(self, symbol, start_date='2024-01-01', end_date=None):
        """Fetch historic prices from Binance public API (fallback)"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # Binance symbols
        binance_symbols = {
            'BTC': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'USDC': None,  # Not available on Binance
            'USDT': None,  # Base currency
            'TAO': 'TAOUSDT'  # If available
        }

        if symbol not in binance_symbols or binance_symbols[symbol] is None:
            print(f"⚠️ {symbol} not available on Binance, using fallback price")
            # Insert fallback prices for stablecoins
            if symbol in ['USDC', 'USDT']:
                self.insert_stable_prices(symbol, start_date, end_date, 1.0)
            return

        binance_symbol = binance_symbols[symbol]
        print(f"📈 Fetching {symbol} prices from Binance ({binance_symbol})...")

        try:
            # Binance Klines API
            url = "https://api.binance.com/api/v3/klines"

            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)

            params = {
                'symbol': binance_symbol,
                'interval': '1d',
                'startTime': start_ts,
                'endTime': end_ts,
                'limit': 1000
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            inserted_count = 0
            for kline in data:
                # kline format: [timestamp, open, high, low, close, volume, ...]
                timestamp_ms = kline[0]
                close_price = float(kline[4])

                date = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')

                cursor.execute('''
                    INSERT OR REPLACE INTO historic_prices (date, symbol, price_usd)
                    VALUES (?, ?, ?)
                ''', (date, symbol, close_price))
                inserted_count += 1

            conn.commit()
            conn.close()

            print(f"✅ Inserted {inserted_count} {symbol} price records from Binance")

        except Exception as e:
            print(f"❌ Error fetching {symbol} prices from Binance: {e}")

    def insert_stable_prices(self, symbol, start_date, end_date, price=1.0):
        """Insert stable prices for stablecoins"""
        print(f"💵 Inserting stable prices for {symbol} at ${price}")

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        current_date = start
        inserted_count = 0

        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            cursor.execute('''
                INSERT OR REPLACE INTO historic_prices (date, symbol, price_usd)
                VALUES (?, ?, ?)
            ''', (date_str, symbol, price))
            current_date += timedelta(days=1)
            inserted_count += 1

        conn.commit()
        conn.close()

        print(f"✅ Inserted {inserted_count} {symbol} stable price records")

    def get_price_on_date(self, symbol, date_str):
        """Get price for a specific date, with fallback logic"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # First try exact date
        cursor.execute('''
            SELECT price_usd FROM historic_prices
            WHERE date = ? AND symbol = ?
        ''', (date_str, symbol))

        result = cursor.fetchone()
        if result:
            conn.close()
            return result[0]

        # Try nearest date within 7 days
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        for i in range(1, 8):
            # Check previous days
            prev_date = (target_date - timedelta(days=i)).strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT price_usd FROM historic_prices
                WHERE date = ? AND symbol = ?
            ''', (prev_date, symbol))

            result = cursor.fetchone()
            if result:
                conn.close()
                return result[0]

            # Check next days
            next_date = (target_date + timedelta(days=i)).strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT price_usd FROM historic_prices
                WHERE date = ? AND symbol = ?
            ''', (next_date, symbol))

            result = cursor.fetchone()
            if result:
                conn.close()
                return result[0]

        conn.close()

        # Fallback to current approximate prices if no historic data
        fallback_prices = {
            'BTC': 45000.0,
            'TAO': 250.0,
            'ETH': 2500.0,
            'USDC': 1.0,
            'USDT': 1.0,
            'USD': 1.0
        }

        print(f"⚠️ No historic price found for {symbol} on {date_str}, using fallback: ${fallback_prices.get(symbol, 1.0)}")
        return fallback_prices.get(symbol, 1.0)

    def populate_all_prices(self, start_date='2024-01-01'):
        """Populate all supported crypto prices from real sources"""
        symbols = ['BTC', 'TAO', 'ETH', 'USDC', 'USDT']

        for symbol in symbols:
            print(f"\n🔄 Processing {symbol}...")
            # Try Yahoo Finance first, then Binance as fallback
            self.fetch_historic_prices_yahoo(symbol, start_date)
            time.sleep(1)  # Rate limiting

    def get_db_stats(self):
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT symbol, COUNT(*) as count, MIN(date) as earliest, MAX(date) as latest
            FROM historic_prices
            GROUP BY symbol
        ''')

        stats = cursor.fetchall()
        conn.close()

        print("📊 Crypto Pricing Database Stats:")
        for symbol, count, earliest, latest in stats:
            print(f"  {symbol}: {count} records ({earliest} to {latest})")

        return stats

def main():
    """Test the crypto pricing database"""
    db = CryptoPricingDB()

    # Populate with historic data
    db.populate_all_prices()

    # Show stats
    db.get_db_stats()

    # Test price lookup
    test_date = '2025-08-15'
    btc_price = db.get_price_on_date('BTC', test_date)
    tao_price = db.get_price_on_date('TAO', test_date)

    print(f"\n🧪 Test Price Lookup for {test_date}:")
    print(f"  BTC: ${btc_price:,.2f}")
    print(f"  TAO: ${tao_price:,.2f}")

if __name__ == '__main__':
    main()