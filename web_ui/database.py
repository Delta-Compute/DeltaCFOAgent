#!/usr/bin/env python3
"""
Database Connection Manager for Delta CFO Agent
Supports both SQLite (development) and PostgreSQL (production)
"""

import os
import sqlite3
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import Generator, Optional, Any
import time

class DatabaseManager:
    def __init__(self):
        self.db_type = os.getenv('DB_TYPE', 'sqlite')  # 'sqlite' or 'postgresql'
        self.connection_config = self._get_connection_config()

    def _get_connection_config(self) -> dict:
        """Get database connection configuration based on environment"""
        if self.db_type == 'postgresql':
            return {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'delta_cfo'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', ''),
                'sslmode': os.getenv('DB_SSL_MODE', 'require'),
                # Cloud SQL specific
                'unix_sock': os.getenv('DB_SOCKET_PATH'),  # For Cloud SQL socket connection
            }
        else:
            # SQLite configuration
            db_path = os.getenv('SQLITE_DB_PATH', 'web_ui/delta_transactions.db')
            return {
                'database': db_path,
                'timeout': 60.0,
                'check_same_thread': False
            }

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """Get database connection with proper error handling and retries"""
        connection = None
        max_retries = 3

        for attempt in range(max_retries):
            try:
                if self.db_type == 'postgresql':
                    connection = self._get_postgresql_connection()
                else:
                    connection = self._get_sqlite_connection()

                yield connection
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"Database connection attempt {attempt + 1} failed: {e}")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"All database connection attempts failed: {e}")
                    raise
            finally:
                if connection:
                    connection.close()

    def _get_postgresql_connection(self):
        """Create PostgreSQL connection"""
        config = self.connection_config.copy()

        # Handle Cloud SQL socket connection
        if config.get('unix_sock'):
            config['host'] = config['unix_sock']
            config.pop('unix_sock', None)
            # For Unix socket connections, SSL is not applicable
            config['sslmode'] = 'disable'

        # Remove None values
        config = {k: v for k, v in config.items() if v is not None}

        conn = psycopg2.connect(**config)
        conn.autocommit = False  # Use transactions
        return conn

    def _get_sqlite_connection(self):
        """Create SQLite connection with optimizations"""
        config = self.connection_config
        conn = sqlite3.connect(**config)

        # Configure SQLite for better performance
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=60000")
        conn.execute("PRAGMA foreign_keys=ON")

        # Row factory for dict-like access
        conn.row_factory = sqlite3.Row

        return conn

    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
        """Execute a query and return results"""
        with self.get_connection() as conn:
            if self.db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cursor = conn.cursor()

            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetch_one:
                    result = cursor.fetchone()
                elif fetch_all:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount

                conn.commit()
                return result

            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()

    def execute_many(self, query: str, params_list: list):
        """Execute a query multiple times with different parameters"""
        with self.get_connection() as conn:
            if self.db_type == 'postgresql':
                cursor = conn.cursor()
            else:
                cursor = conn.cursor()

            try:
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount

            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()

    def init_database(self):
        """Initialize database with schema"""
        if self.db_type == 'postgresql':
            self._init_postgresql_schema()
        else:
            self._init_sqlite_schema()

    def _init_postgresql_schema(self):
        """Initialize PostgreSQL schema"""
        schema_file = os.path.join(os.path.dirname(__file__), '..', 'migration', 'postgresql_schema.sql')

        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema_sql = f.read()

            with self.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    # Execute schema in chunks (split by semicolon)
                    statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                    for statement in statements:
                        if statement:
                            cursor.execute(statement)
                    conn.commit()
                    print("PostgreSQL schema initialized successfully")
                except Exception as e:
                    conn.rollback()
                    print(f"Error initializing PostgreSQL schema: {e}")
                    raise
                finally:
                    cursor.close()
        else:
            print("PostgreSQL schema file not found")

    def _init_sqlite_schema(self):
        """Initialize SQLite schema (existing logic)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    date TEXT,
                    description TEXT,
                    amount REAL,
                    currency TEXT,
                    usd_equivalent REAL,
                    classified_entity TEXT,
                    justification TEXT,
                    confidence REAL,
                    classification_reason TEXT,
                    origin TEXT,
                    destination TEXT,
                    identifier TEXT,
                    source_file TEXT,
                    crypto_amount TEXT,
                    conversion_note TEXT,
                    accounting_category TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT
                )
            """)

            # Create invoices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    invoice_number TEXT UNIQUE NOT NULL,
                    date TEXT NOT NULL,
                    vendor_name TEXT,
                    total_amount REAL,
                    currency TEXT DEFAULT 'USD',
                    payment_due_date TEXT,
                    payment_status TEXT DEFAULT 'pending',
                    items TEXT,
                    raw_text TEXT,
                    confidence REAL,
                    processing_notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    vendor_address TEXT,
                    vendor_tax_id TEXT,
                    vendor_contact TEXT,
                    vendor_type TEXT,
                    extraction_method TEXT,
                    customer_name TEXT,
                    customer_address TEXT,
                    customer_tax_id TEXT,
                    linked_transaction_id TEXT,
                    FOREIGN KEY (linked_transaction_id) REFERENCES transactions(transaction_id)
                )
            ''')

            # Create invoice email log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoice_email_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT UNIQUE NOT NULL,
                    subject TEXT,
                    sender TEXT,
                    received_at TEXT,
                    processed_at TEXT,
                    status TEXT DEFAULT 'pending',
                    attachments_count INTEGER DEFAULT 0,
                    invoices_extracted INTEGER DEFAULT 0,
                    error_message TEXT
                )
            ''')

            conn.commit()
            print("SQLite schema initialized successfully")

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for backward compatibility
def get_db_connection():
    """Get database connection (backward compatibility)"""
    return db_manager.get_connection()

def init_database():
    """Initialize database"""
    return db_manager.init_database()