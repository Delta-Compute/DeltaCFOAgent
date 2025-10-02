#!/usr/bin/env python3
"""
Delta CFO Agent - Database-Backed Web Dashboard
Advanced web interface for financial transaction management with Claude AI integration
"""

import os
import sys
import json
import sqlite3
import pandas as pd
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file
import random
import anthropic
from typing import List, Dict, Any, Optional
from werkzeug.utils import secure_filename
import subprocess
import shutil
import hashlib
import uuid
import base64

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import invoice processing modules
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'invoice_processing'))

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size for batch uploads

# Database connection
DB_PATH = os.path.join(os.path.dirname(__file__), 'delta_transactions.db')

# Claude API client
claude_client = None

def init_claude_client():
    """Initialize Claude API client"""
    global claude_client
    try:
        # Try to load API key from various sources
        api_key = None

        # Check environment variable
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            api_key = api_key.strip()  # Remove whitespace and newlines

        # Check for .anthropic_api_key file in parent directory
        if not api_key:
            key_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.anthropic_api_key')
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    api_key = f.read().strip()

        if api_key:
            # Additional validation and cleaning
            api_key = api_key.strip()  # Extra safety
            if not api_key.startswith('sk-ant-'):
                print(f"WARNING: API key format looks invalid. Expected 'sk-ant-', got: '{api_key[:10]}...'")
                return False

            claude_client = anthropic.Anthropic(api_key=api_key)
            print(f"✅ Claude API client initialized successfully (key: {api_key[:10]}...{api_key[-4:]})")
            return True
        else:
            print("WARNING: Claude API key not found - AI features disabled")
            return False
    except Exception as e:
        print(f"ERROR: Error initializing Claude API: {e}")
        return False

def init_invoice_tables():
    """Initialize invoice tables in the database"""
    try:
        conn = get_db_connection()

        # Main invoices table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                invoice_number TEXT UNIQUE NOT NULL,
                date TEXT NOT NULL,
                due_date TEXT,
                vendor_name TEXT NOT NULL,
                vendor_address TEXT,
                vendor_tax_id TEXT,
                customer_name TEXT,
                customer_address TEXT,
                customer_tax_id TEXT,
                total_amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                tax_amount REAL,
                subtotal REAL,
                line_items TEXT,
                payment_terms TEXT,
                status TEXT DEFAULT 'pending',
                invoice_type TEXT DEFAULT 'other',
                confidence_score REAL DEFAULT 0.0,
                processing_notes TEXT,
                source_file TEXT,
                email_id TEXT,
                processed_at TEXT,
                created_at TEXT NOT NULL,
                business_unit TEXT,
                category TEXT,
                currency_type TEXT,
                vendor_type TEXT,
                extraction_method TEXT,
                linked_transaction_id TEXT,
                FOREIGN KEY (linked_transaction_id) REFERENCES transactions(transaction_id)
            )
        ''')

        # Email processing log
        conn.execute('''
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

        # Add customer columns to existing tables (migration)
        try:
            conn.execute('ALTER TABLE invoices ADD COLUMN customer_name TEXT')
            print("Added customer_name column to invoices table")
        except:
            pass  # Column already exists

        try:
            conn.execute('ALTER TABLE invoices ADD COLUMN customer_address TEXT')
            print("Added customer_address column to invoices table")
        except:
            pass  # Column already exists

        try:
            conn.execute('ALTER TABLE invoices ADD COLUMN customer_tax_id TEXT')
            print("Added customer_tax_id column to invoices table")
        except:
            pass  # Column already exists

        conn.commit()
        conn.close()
        print("Invoice tables initialized successfully")
        return True
    except Exception as e:
        print(f"ERROR: Failed to initialize invoice tables: {e}")
        return False

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_transactions_from_db(filters=None, page=1, per_page=50):
    """Load transactions from database with filtering and pagination"""
    import re  # For crypto amount extraction
    try:
        print("Loading transactions from database...")
        conn = get_db_connection()

        # Base query
        query = """
            SELECT * FROM transactions
            WHERE 1=1
        """
        params = []

        # Apply filters
        if filters:
            if filters.get('entity'):
                query += " AND classified_entity = ?"
                params.append(filters['entity'])

            if filters.get('transaction_type') == 'Revenue':
                query += " AND amount > 0"
            elif filters.get('transaction_type') == 'Expense':
                query += " AND amount < 0"

            if filters.get('source_file'):
                query += " AND source_file = ?"
                params.append(filters['source_file'])

            if filters.get('needs_review') == 'true':
                query += " AND (confidence < 0.8 OR confidence IS NULL)"

            if filters.get('min_amount'):
                query += " AND ABS(amount) >= ?"
                params.append(float(filters['min_amount']))

            if filters.get('max_amount'):
                query += " AND ABS(amount) <= ?"
                params.append(float(filters['max_amount']))

            if filters.get('start_date'):
                query += " AND date >= ?"
                params.append(filters['start_date'])

            if filters.get('end_date'):
                query += " AND date <= ?"
                params.append(filters['end_date'])

            if filters.get('keyword'):
                keyword = f"%{filters['keyword']}%"
                query += """ AND (
                    description LIKE ? OR
                    classified_entity LIKE ? OR
                    keywords_action_type LIKE ? OR
                    keywords_platform LIKE ?
                )"""
                params.extend([keyword, keyword, keyword, keyword])

        # Add ordering and pagination
        query += " ORDER BY date DESC"

        # Get total count for pagination
        count_query = query.replace("SELECT * FROM transactions", "SELECT COUNT(*) FROM transactions")
        total_count = conn.execute(count_query, params).fetchone()[0]

        # Add pagination
        if page and per_page:
            offset = (page - 1) * per_page
            query += f" LIMIT {per_page} OFFSET {offset}"

        cursor = conn.execute(query, params)
        transactions = []

        for row in cursor.fetchall():
            transaction = dict(row)

            # Map database columns to frontend expected field names for crypto display
            # Frontend expects: transaction.amount, transaction.crypto_amount, transaction.currency

            # Handle crypto transactions with correct database structure
            # For BTC/TAO transactions: amount=USD_value, crypto_amount=token_quantity, currency=token_symbol

            # Check for BTC transactions
            if (transaction.get('classification_reason', '').lower().find('btc') != -1 or
                transaction.get('justification', '').lower().find('btc') != -1):
                # This is a BTC transaction
                token_quantity = float(transaction.get('crypto_amount', 0))
                usd_value = float(transaction.get('amount', 0))

                # The crypto_amount field contains the correct BTC token amount
                crypto_amount = f"{token_quantity:.8f}"  # BTC with 8 decimal precision

                # Calculate actual price from existing data
                token_price = usd_value / token_quantity if token_quantity > 0 else 0

                # Create simplified description format
                enhanced_description = f"Bitcoin @ ${token_price:,.2f}"
                transaction['description'] = enhanced_description

                # Set appropriate origin and destination for crypto transactions
                transaction['origin'] = 'MEXC Exchange'
                transaction['destination'] = 'Crypto Wallet'

                transaction['currency'] = 'BTC'  # Keep currency as BTC
                transaction['amount'] = usd_value
                transaction['usd_equivalent'] = usd_value

            # Check for TAO transactions
            elif (transaction.get('classification_reason', '').lower().find('tao') != -1 or
                  transaction.get('justification', '').lower().find('tao') != -1):
                # This is a TAO transaction
                token_quantity = float(transaction.get('crypto_amount', 0))
                usd_value = float(transaction.get('amount', 0))

                # The crypto_amount field contains the correct TAO token amount
                crypto_amount = f"{token_quantity:.4f}"  # TAO with 4 decimal precision

                # Calculate actual price from existing data
                token_price = usd_value / token_quantity if token_quantity > 0 else 0

                # Create simplified description format
                enhanced_description = f"TAO @ ${token_price:,.2f}"
                transaction['description'] = enhanced_description

                # Set appropriate origin and destination for crypto transactions
                transaction['origin'] = 'Unknown'
                transaction['destination'] = 'Unknown'

                transaction['currency'] = 'TAO'  # Keep currency as TAO
                transaction['amount'] = usd_value
                transaction['usd_equivalent'] = usd_value
            else:
                # For non-crypto transactions, use amount as is
                crypto_amount = str(transaction.get('crypto_amount', '') or '')

            # Add frontend-expected fields
            transaction['crypto_amount'] = crypto_amount

            transactions.append(transaction)

        conn.close()
        print(f"Loaded {len(transactions)} transactions using database backend")

        return transactions, total_count

    except Exception as e:
        print(f"ERROR: Error loading transactions from database: {e}")
        return [], 0

def get_dashboard_stats():
    """Calculate dashboard statistics from database"""
    try:
        conn = get_db_connection()

        # Total transactions
        total_transactions = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

        # Revenue and expenses
        revenue = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE amount > 0").fetchone()[0]
        expenses = conn.execute("SELECT COALESCE(SUM(ABS(amount)), 0) FROM transactions WHERE amount < 0").fetchone()[0]

        # Needs review
        needs_review = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE confidence < 0.8 OR confidence IS NULL"
        ).fetchone()[0]

        # Date range
        date_range_result = conn.execute("SELECT MIN(date), MAX(date) FROM transactions").fetchone()
        date_range = {
            'min': date_range_result[0] or 'N/A',
            'max': date_range_result[1] or 'N/A'
        }

        # Top entities
        entities = conn.execute("""
            SELECT classified_entity, COUNT(*) as count
            FROM transactions
            WHERE classified_entity IS NOT NULL
            GROUP BY classified_entity
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()

        # Top source files
        source_files = conn.execute("""
            SELECT source_file, COUNT(*) as count
            FROM transactions
            WHERE source_file IS NOT NULL
            GROUP BY source_file
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()

        conn.close()

        return {
            'total_transactions': total_transactions,
            'total_revenue': float(revenue),
            'total_expenses': float(expenses),
            'needs_review': needs_review,
            'date_range': date_range,
            'entities': [(row[0], row[1]) for row in entities],
            'source_files': [(row[0], row[1]) for row in source_files]
        }

    except Exception as e:
        print(f"ERROR: Error calculating dashboard stats: {e}")
        return {
            'total_transactions': 0,
            'total_revenue': 0,
            'total_expenses': 0,
            'needs_review': 0,
            'date_range': {'min': 'N/A', 'max': 'N/A'},
            'entities': [],
            'source_files': []
        }

def update_transaction_field(transaction_id: str, field: str, value: str, user: str = 'web_user') -> bool:
    """Update a single field in a transaction with history tracking"""
    try:
        conn = get_db_connection()

        # Get current value for history
        current_row = conn.execute(
            "SELECT * FROM transactions WHERE transaction_id = ?",
            (transaction_id,)
        ).fetchone()

        if not current_row:
            return False

        current_value = current_row[field] if field in current_row.keys() else None

        # Update the field
        update_query = f"UPDATE transactions SET {field} = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ? WHERE transaction_id = ?"
        conn.execute(update_query, (value, user, transaction_id))

        # Record change in history
        conn.execute("""
            INSERT INTO transaction_history (transaction_id, field_name, old_value, new_value, changed_by, change_reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (transaction_id, field, str(current_value) if current_value else None, str(value), user, f"Updated via web interface"))

        conn.commit()
        conn.close()

        print(f"UPDATING: Updating transaction {transaction_id}: field={field}")
        return True

    except Exception as e:
        print(f"ERROR: Error updating transaction field: {e}")
        return False

def get_claude_analyzed_similar_descriptions(context: Dict, claude_client) -> List[str]:
    """Use Claude to intelligently analyze which transactions should have similar descriptions"""
    try:
        if not claude_client or not context:
            return []

        transaction_id = context.get('transaction_id')
        new_description = context.get('value', '')

        if not transaction_id or not new_description:
            return []

        conn = get_db_connection()

        # Get the current transaction
        current_tx = conn.execute(
            "SELECT description, classified_entity FROM transactions WHERE transaction_id = ?",
            (transaction_id,)
        ).fetchone()

        if not current_tx:
            conn.close()
            return []

        original_description = current_tx[0]
        entity = current_tx[1]

        # Get potential candidate transactions using basic keyword matching
        candidate_txs = conn.execute("""
            SELECT transaction_id, date, description, confidence
            FROM transactions
            WHERE transaction_id != ?
            AND (
                (classified_entity = ? AND description LIKE ?) OR
                (description LIKE '%WIRE%' AND ? LIKE '%WIRE%') OR
                (description LIKE '%CIBC%' AND ? LIKE '%CIBC%') OR
                (description LIKE '%TORONTO%' AND ? LIKE '%TORONTO%') OR
                (description LIKE '%FEDWIRE%' AND ? LIKE '%FEDWIRE%') OR
                (description LIKE '%BANCO%' AND ? LIKE '%BANCO%') OR
                (description LIKE '%PARAGUAY%' AND ? LIKE '%PARAGUAY%')
            )
            LIMIT 20
        """, (
            transaction_id, entity, f"%{original_description[:20]}%",
            original_description, original_description, original_description,
            original_description, original_description, original_description
        )).fetchall()

        conn.close()

        if not candidate_txs:
            return []

        # Use Claude to analyze which transactions are truly similar
        candidate_descriptions = [f"Transaction {i+1}: {tx[2][:100]}..." if len(tx[2]) > 100 else f"Transaction {i+1}: {tx[2]}"
                                for i, tx in enumerate(candidate_txs)]

        prompt = f"""
        Analyze these transaction descriptions and determine which ones are similar enough to the original transaction that they should have the same cleaned description.

        Original transaction: {original_description}
        New clean description: "{new_description}"

        Candidate transactions:
        {chr(10).join(candidate_descriptions)}

        Respond with ONLY the transaction numbers (1, 2, 3, etc.) that are similar enough to warrant the same clean description "{new_description}".
        Focus on transactions that are clearly from the same merchant/entity but have messy technical details.

        Response format: Just the numbers separated by commas (e.g., "1, 3, 7") or "none" if no transactions are similar enough.
        """

        import time
        start_time = time.time()
        print(f"AI: Calling Claude API for similar descriptions analysis...")

        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        elapsed_time = time.time() - start_time
        print(f"LOADING: Claude API response time: {elapsed_time:.2f} seconds")

        response_text = response.content[0].text.strip().lower()

        if response_text == "none" or not response_text:
            return []

        # Parse Claude's response to get selected transaction indices
        try:
            selected_indices = [int(x.strip()) - 1 for x in response_text.split(',') if x.strip().isdigit()]
            selected_txs = [candidate_txs[i] for i in selected_indices if 0 <= i < len(candidate_txs)]

            # Return formatted transaction data
            return [{
                'transaction_id': tx[0],
                'date': tx[1],
                'description': tx[2][:80] + "..." if len(tx[2]) > 80 else tx[2],
                'confidence': tx[3] or 'N/A'
            } for tx in selected_txs]

        except (ValueError, IndexError) as e:
            print(f"ERROR: Error parsing Claude response for similar descriptions: {e}")
            return []

    except Exception as e:
        print(f"ERROR: Error in Claude analysis of similar descriptions: {e}")
        return []

def get_similar_descriptions_from_db(context: Dict) -> List[str]:
    """Find transactions with similar descriptions for bulk updates"""
    try:
        if not context:
            return []

        transaction_id = context.get('transaction_id')
        new_description = context.get('value', '')

        if not transaction_id or not new_description:
            return []

        conn = get_db_connection()

        # Find the current transaction to get its original description
        current_tx = conn.execute(
            "SELECT description, classified_entity FROM transactions WHERE transaction_id = ?",
            (transaction_id,)
        ).fetchone()

        if not current_tx:
            conn.close()
            return []

        original_description = current_tx[0]
        entity = current_tx[1]

        # Find transactions with similar patterns - return full transaction data
        similar_txs = conn.execute("""
            SELECT transaction_id, date, description, confidence
            FROM transactions
            WHERE transaction_id != ?
            AND (
                -- Same entity with similar description pattern
                (classified_entity = ? AND description LIKE ?) OR
                -- Contains similar keywords for CIBC/Toronto wire transfers
                (description LIKE '%CIBC%' AND ? LIKE '%CIBC%') OR
                (description LIKE '%TORONTO%' AND ? LIKE '%TORONTO%') OR
                (description LIKE '%WIRE%' AND ? LIKE '%WIRE%') OR
                (description LIKE '%FEDWIRE%' AND ? LIKE '%FEDWIRE%')
            )
            AND description != ?
            LIMIT 10
        """, (
            transaction_id,
            entity,
            f"%{original_description[:20]}%",
            original_description,
            original_description,
            original_description,
            original_description,
            new_description
        )).fetchall()

        conn.close()

        # Return full transaction data for the improved UI
        return [{
            'transaction_id': row[0],
            'date': row[1],
            'description': row[2][:80] + "..." if len(row[2]) > 80 else row[2],
            'confidence': row[3] or 'N/A'
        } for row in similar_txs]

    except Exception as e:
        print(f"ERROR: Error finding similar descriptions: {e}")
        return []

def get_ai_powered_suggestions(field_type: str, current_value: str = "", context: Dict = None) -> List[str]:
    """Get AI-powered suggestions for field values"""
    global claude_client

    if not claude_client:
        return []

    try:
        print(f"DEBUG - get_ai_powered_suggestions called with field_type={field_type}")

        # Define prompts for different field types
        prompts = {
            'accounting_category': f"""
            Based on this transaction context:
            - Current value: {current_value}
            - Description: {context.get('description', '')}
            - Amount: {context.get('amount', '')}
            - Entity: {context.get('classified_entity', '')}

            Suggest 3-5 appropriate accounting categories (like 'Office Supplies', 'Software Licenses', 'Professional Services', etc.).
            Return only the category names, one per line.
            """,

            'classified_entity': f"""
            You are a financial analyst specializing in entity classification for crypto/trading businesses.

            TRANSACTION DETAILS:
            - Description: {context.get('description', '')}
            - Amount: ${context.get('amount', '')}
            - Source File: {context.get('source_file', '')}
            - Date: {context.get('date', '')}

            ENTITY CLASSIFICATION RULES:
            • Delta LLC: US-based trading operations, exchanges, brokers, US banking
            • Delta Prop Shop LLC: Proprietary trading, DeFi protocols, yield farming, liquid staking
            • Infinity Validator: Blockchain validation, staking rewards, node operations
            • Delta Mining Paraguay S.A.: Mining operations, equipment, Paraguay-based transactions
            • Delta Brazil Operations: Brazil-based activities, regulatory compliance, local operations
            • Personal: Individual expenses, personal transfers, non-business transactions
            • Internal Transfer: Movements between company entities/wallets

            CONTEXT CLUES:
            - Bank descriptions often contain merchant/institution names
            - ACH/WIRE patterns indicate specific business relationships
            - Amount patterns may suggest recurring services vs one-time purchases
            - Geographic indicators (Paraguay, Brazil references)

            Based on the transaction description and amount, suggest 3-5 most likely entities.
            Prioritize based on:
            1. Specific merchant/institution mentioned
            2. Transaction type (ACH, WIRE, etc.)
            3. Geographic/regulatory context
            4. Amount patterns

            Return only the entity names, one per line, ranked by confidence.
            """,

            'justification': f"""
            Based on this transaction:
            - Description: {context.get('description', '')}
            - Amount: {context.get('amount', '')}
            - Entity: {context.get('classified_entity', '')}

            Suggest 2-3 brief business justifications for this expense (like 'Business operations', 'Infrastructure cost', etc.).
            Return only the justifications, one per line.
            """,

            'description': f"""
            Based on this transaction with technical details:
            - Current description: {context.get('description', '')}
            - Amount: {context.get('amount', '')}
            - Entity: {context.get('classified_entity', '')}

            Extract and suggest 3-5 clean merchant/provider/entity names from this transaction.
            Focus ONLY on WHO we are transacting with, not what type of transaction it is. Examples:
            - "Delta Prop Shop" (from technical payment codes mentioning Delta Prop Shop)
            - "Chase Bank" (from Chase-related transactions)
            - "M Merchant" (from merchant processing fees)
            - "Gateway Services" (from gateway payment processing)
            - "CIBC Toronto" (from international wire transfer details)

            Return only the merchant/provider names, one per line, maximum 30 characters each.
            """
        }

        # Special handling for similar_descriptions - use Claude to analyze similar transactions
        if field_type == 'similar_descriptions':
            return get_claude_analyzed_similar_descriptions(context, claude_client)

        prompt = prompts.get(field_type, "")
        if not prompt:
            print(f"ERROR: No prompt found for field_type: {field_type}")
            return []

        print(f"SUCCESS: Found prompt for {field_type}, enhancing with learning...")
        # Enhance prompt with learned patterns
        enhanced_prompt = enhance_ai_prompt_with_learning(field_type, prompt, context)
        print(f"SUCCESS: Enhanced prompt created, calling Claude API...")

        print(f"AI: Calling Claude API for {field_type} suggestions...")
        start_time = time.time()

        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            messages=[{"role": "user", "content": enhanced_prompt}]
        )

        elapsed_time = time.time() - start_time
        print(f"LOADING: Claude API response time: {elapsed_time:.2f} seconds")

        ai_suggestions = [line.strip() for line in response.content[0].text.strip().split('\n') if line.strip()]
        print(f"AI: Claude suggestions: {ai_suggestions}")

        # Get learned suggestions
        learned_suggestions = get_learned_suggestions(field_type, context)
        learned_values = [s['value'] for s in learned_suggestions]
        print(f"DATABASE: Learned suggestions: {learned_values}")

        # Combine suggestions, prioritizing Claude AI suggestions FIRST
        combined_suggestions = []
        for ai_suggestion in ai_suggestions:
            if ai_suggestion not in combined_suggestions:
                combined_suggestions.append(ai_suggestion)

        for learned in learned_values:
            if learned not in combined_suggestions:
                combined_suggestions.append(learned)

        print(f"SUCCESS: Final combined suggestions: {combined_suggestions[:5]}")
        return combined_suggestions[:5]  # Limit to 5 suggestions

    except Exception as e:
        print(f"ERROR: Error getting AI suggestions: {e}")
        return []

def sync_csv_to_database(csv_filename=None):
    """Sync classified CSV files to SQLite database"""
    try:
        parent_dir = os.path.dirname(os.path.dirname(__file__))

        if csv_filename:
            # Sync specific classified file
            csv_path = os.path.join(parent_dir, 'classified_transactions', f'classified_{csv_filename}')
        else:
            # Try to sync MASTER_TRANSACTIONS.csv if it exists
            csv_path = os.path.join(parent_dir, 'MASTER_TRANSACTIONS.csv')

        if not os.path.exists(csv_path):
            print(f"WARNING: CSV file not found for sync: {csv_path}")
            return False

        # Read the CSV file
        df = pd.read_csv(csv_path)
        print(f"UPDATING: Syncing {len(df)} transactions to database...")

        # Connect to database
        conn = get_db_connection()

        # For specific file uploads, only clear data from that source file
        if csv_filename:
            source_file = csv_filename.replace('classified_', '')
            conn.execute("DELETE FROM transactions WHERE source_file = ?", (source_file,))
            print(f"DATABASE: Cleared existing data for source file: {source_file}")
        else:
            # Only clear all data if syncing MASTER_TRANSACTIONS.csv (full sync)
            conn.execute("DELETE FROM transactions")
            print("DATABASE: Cleared all existing data for full sync")

        # Insert all transactions
        for _, row in df.iterrows():
            # Create transaction_id if not exists
            transaction_id = row.get('transaction_id', '')
            if not transaction_id:
                # Generate transaction_id from date + description + amount
                identifier = f"{row.get('date', '')}{row.get('description', '')}{row.get('amount', '')}"
                transaction_id = hashlib.md5(identifier.encode()).hexdigest()[:12]

            # Convert pandas types to Python types for SQLite
            # Handle both MASTER_TRANSACTIONS.csv and classified CSV column names
            data = {
                'transaction_id': transaction_id,
                'date': str(row.get('Date', row.get('date', ''))),
                'description': str(row.get('Description', row.get('description', ''))),
                'amount': float(row.get('Amount', row.get('amount', 0))),
                'currency': str(row.get('Currency', row.get('currency', 'USD'))),
                'usd_equivalent': float(row.get('Amount_USD', row.get('USD_Equivalent', row.get('usd_equivalent', row.get('Amount', row.get('amount', 0)))))),
                'classified_entity': str(row.get('classified_entity', '')),
                'justification': str(row.get('Justification', row.get('justification', ''))),
                'confidence': float(row.get('confidence', 0)),
                'classification_reason': str(row.get('classification_reason', '')),
                'origin': str(row.get('Origin', row.get('origin', ''))),
                'destination': str(row.get('Destination', row.get('destination', ''))),
                'identifier': str(row.get('Identifier', row.get('identifier', ''))),
                'source_file': str(row.get('source_file', '')),
                'crypto_amount': float(row.get('Crypto_Amount', 0)) if pd.notna(row.get('Crypto_Amount')) else None,
                'conversion_note': str(row.get('Conversion_Note', '')) if pd.notna(row.get('Conversion_Note')) else None
            }

            # Insert transaction (use REPLACE to handle duplicates)
            conn.execute("""
                INSERT OR REPLACE INTO transactions (
                    transaction_id, date, description, amount, currency, usd_equivalent,
                    classified_entity, justification, confidence, classification_reason,
                    origin, destination, identifier, source_file, crypto_amount, conversion_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['transaction_id'], data['date'], data['description'],
                data['amount'], data['currency'], data['usd_equivalent'],
                data['classified_entity'], data['justification'], data['confidence'],
                data['classification_reason'], data['origin'], data['destination'],
                data['identifier'], data['source_file'], data['crypto_amount'], data['conversion_note']
            ))

        conn.commit()
        conn.close()
        print(f"SUCCESS: Successfully synced {len(df)} transactions to database")
        return True

    except Exception as e:
        print(f"ERROR: Error syncing CSV to database: {e}")
        return False

@app.route('/')
def homepage():
    """Business overview homepage"""
    try:
        cache_buster = str(random.randint(1000, 9999))
        return render_template('business_overview.html', cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading homepage: {str(e)}", 500

@app.route('/old-homepage')
def old_homepage():
    """Old homepage with platform overview"""
    try:
        stats = get_dashboard_stats()
        cache_buster = str(random.randint(1000, 9999))
        return render_template('homepage.html', stats=stats, cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading homepage: {str(e)}", 500

@app.route('/dashboard')
def dashboard():
    """Main dashboard page"""
    try:
        stats = get_dashboard_stats()
        cache_buster = str(random.randint(1000, 9999))
        return render_template('dashboard_advanced.html', stats=stats, cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

@app.route('/revenue')
def revenue():
    """Revenue Recognition dashboard page"""
    try:
        stats = get_dashboard_stats()
        cache_buster = str(random.randint(1000, 9999))
        return render_template('revenue.html', stats=stats, cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading revenue dashboard: {str(e)}", 500

@app.route('/api/transactions')
def api_transactions():
    """API endpoint to get filtered transactions with pagination"""
    try:
        # Get filter parameters
        filters = {
            'entity': request.args.get('entity'),
            'transaction_type': request.args.get('transaction_type'),
            'source_file': request.args.get('source_file'),
            'needs_review': request.args.get('needs_review'),
            'min_amount': request.args.get('min_amount'),
            'max_amount': request.args.get('max_amount'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'keyword': request.args.get('keyword')
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v}

        # Pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        transactions, total_count = load_transactions_from_db(filters, page, per_page)

        return jsonify({
            'transactions': transactions,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """API endpoint to get dashboard statistics"""
    try:
        stats = get_dashboard_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_transaction', methods=['POST'])
def api_update_transaction():
    """API endpoint to update transaction fields"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        field = data.get('field')
        value = data.get('value')

        if not all([transaction_id, field]):
            return jsonify({'error': 'Missing required parameters'}), 400

        success = update_transaction_field(transaction_id, field, value)

        if success:
            return jsonify({'success': True, 'message': 'Transaction updated successfully'})
        else:
            return jsonify({'error': 'Failed to update transaction'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_entity_bulk', methods=['POST'])
def api_update_entity_bulk():
    """API endpoint to update entity for multiple transactions"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])
        new_entity = data.get('new_entity')

        if not transaction_ids or not new_entity:
            return jsonify({'error': 'Missing required parameters'}), 400

        # Update each transaction
        conn = get_db_connection()
        updated_count = 0

        for transaction_id in transaction_ids:
            result = conn.execute(
                "UPDATE transactions SET classified_entity = ? WHERE transaction_id = ?",
                (new_entity, transaction_id)
            )
            if result.rowcount > 0:
                updated_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} transactions',
            'updated_count': updated_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_category_bulk', methods=['POST'])
def api_update_category_bulk():
    """API endpoint to update accounting category for multiple transactions"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])
        new_category = data.get('new_category')

        if not transaction_ids or not new_category:
            return jsonify({'error': 'Missing required parameters'}), 400

        # Update each transaction
        conn = get_db_connection()
        updated_count = 0

        for transaction_id in transaction_ids:
            result = conn.execute(
                "UPDATE transactions SET accounting_category = ? WHERE transaction_id = ?",
                (new_category, transaction_id)
            )
            if result.rowcount > 0:
                updated_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} transactions',
            'updated_count': updated_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/suggestions')
def api_suggestions():
    """API endpoint to get AI-powered field suggestions"""
    try:
        field_type = request.args.get('field_type')
        current_value = request.args.get('current_value', '')
        transaction_id = request.args.get('transaction_id')

        if not field_type:
            return jsonify({'error': 'field_type parameter required'}), 400

        # Get transaction context if transaction_id provided
        context = {}
        if transaction_id:
            conn = get_db_connection()
            row = conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,)).fetchone()
            if row:
                context = dict(row)
            conn.close()

        # Add special parameters for similar_descriptions
        if field_type == 'similar_descriptions':
            context['transaction_id'] = transaction_id
            context['value'] = request.args.get('value', current_value)

        suggestions = get_ai_powered_suggestions(field_type, current_value, context)

        # Check if no suggestions were returned due to API issues
        if not suggestions and claude_client:
            return jsonify({
                'error': 'Claude API failed to generate suggestions',
                'suggestions': [],
                'fallback_available': False
            }), 500
        elif not suggestions and not claude_client:
            return jsonify({
                'error': 'Claude API not available - check ANTHROPIC_API_KEY environment variable',
                'suggestions': [],
                'fallback_available': False
            }), 500

        return jsonify({'suggestions': suggestions})

    except Exception as e:
        print(f"ERROR: API suggestions error: {e}")
        return jsonify({
            'error': f'Failed to get AI suggestions: {str(e)}',
            'suggestions': [],
            'fallback_available': False
        }), 500

@app.route('/api/update_similar_categories', methods=['POST'])
def api_update_similar_categories():
    """API endpoint to update accounting category for similar transactions"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        accounting_category = data.get('accounting_category')

        if not all([transaction_id, accounting_category]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Get the original transaction to find similar ones
        conn = get_db_connection()
        original_row = conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,)).fetchone()

        if not original_row:
            conn.close()
            return jsonify({'error': 'Transaction not found'}), 404

        original = dict(original_row)

        # Find similar transactions based on entity, description similarity, or same amount
        similar_transactions = []

        # Same entity
        if original.get('entity'):
            entity_rows = conn.execute(
                "SELECT transaction_id FROM transactions WHERE entity = ? AND transaction_id != ?",
                (original['entity'], transaction_id)
            ).fetchall()
            similar_transactions.extend([row[0] for row in entity_rows])

        # Similar descriptions (containing same keywords)
        if original.get('description'):
            desc_words = [word.lower() for word in original['description'].split() if len(word) > 3]
            for word in desc_words[:2]:  # Check first 2 meaningful words
                desc_rows = conn.execute(
                    "SELECT transaction_id FROM transactions WHERE LOWER(description) LIKE ? AND transaction_id != ? AND transaction_id NOT IN ({})".format(','.join('?' * len(similar_transactions)) if similar_transactions else ''),
                    [f'%{word}%', transaction_id] + similar_transactions
                ).fetchall()
                similar_transactions.extend([row[0] for row in desc_rows])

        # Same amount (exact match)
        if original.get('amount'):
            amount_rows = conn.execute(
                "SELECT transaction_id FROM transactions WHERE amount = ? AND transaction_id != ? AND transaction_id NOT IN ({})".format(','.join('?' * len(similar_transactions)) if similar_transactions else ''),
                [original['amount'], transaction_id] + similar_transactions
            ).fetchall()
            similar_transactions.extend([row[0] for row in amount_rows])

        # Remove duplicates
        similar_transactions = list(set(similar_transactions))

        # Update all similar transactions
        updated_count = 0
        for similar_id in similar_transactions:
            success = update_transaction_field(similar_id, 'accounting_category', accounting_category)
            if success:
                updated_count += 1

        conn.close()

        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'Updated {updated_count} similar transactions'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_similar_descriptions', methods=['POST'])
def api_update_similar_descriptions():
    """API endpoint to update description for similar transactions"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        description = data.get('description')

        if not all([transaction_id, description]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Get the original transaction to find similar ones
        conn = get_db_connection()
        original_row = conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,)).fetchone()

        if not original_row:
            conn.close()
            return jsonify({'error': 'Transaction not found'}), 404

        original = dict(original_row)

        # Find similar transactions based on entity, description similarity, or same amount
        similar_transactions = []

        # Same entity
        if original.get('entity'):
            entity_rows = conn.execute(
                "SELECT transaction_id FROM transactions WHERE entity = ? AND transaction_id != ?",
                (original['entity'], transaction_id)
            ).fetchall()
            similar_transactions.extend([row[0] for row in entity_rows])

        # Similar descriptions (containing same keywords)
        if original.get('description'):
            desc_words = [word.lower() for word in original['description'].split() if len(word) > 3]
            for word in desc_words[:2]:  # Check first 2 meaningful words
                desc_rows = conn.execute(
                    "SELECT transaction_id FROM transactions WHERE LOWER(description) LIKE ? AND transaction_id != ? AND transaction_id NOT IN ({})".format(','.join('?' * len(similar_transactions)) if similar_transactions else ''),
                    [f'%{word}%', transaction_id] + similar_transactions
                ).fetchall()
                similar_transactions.extend([row[0] for row in desc_rows])

        # Same amount (exact match)
        if original.get('amount'):
            amount_rows = conn.execute(
                "SELECT transaction_id FROM transactions WHERE amount = ? AND transaction_id != ? AND transaction_id NOT IN ({})".format(','.join('?' * len(similar_transactions)) if similar_transactions else ''),
                [original['amount'], transaction_id] + similar_transactions
            ).fetchall()
            similar_transactions.extend([row[0] for row in amount_rows])

        # Remove duplicates
        similar_transactions = list(set(similar_transactions))

        # Update all similar transactions
        updated_count = 0
        for similar_id in similar_transactions:
            success = update_transaction_field(similar_id, 'description', description)
            if success:
                updated_count += 1

        conn.close()

        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'Updated {updated_count} similar transactions'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/files')
def files_page():
    """Files management page"""
    try:
        # Get list of CSV files in the parent directory
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        csv_files = []

        for file in os.listdir(parent_dir):
            if file.endswith('.csv'):
                file_path = os.path.join(parent_dir, file)
                stat = os.stat(file_path)
                csv_files.append({
                    'name': file,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })

        # Sort by modification time (newest first)
        csv_files.sort(key=lambda x: x['modified'], reverse=True)

        return render_template('files.html', files=csv_files)
    except Exception as e:
        return f"Error loading files: {str(e)}", 500

def check_file_duplicates(filepath):
    """Check if uploaded file contains transactions that already exist in database"""
    try:
        import pandas as pd
        import hashlib

        # Read the uploaded CSV file
        df = pd.read_csv(filepath)
        print(f"📊 Checking duplicates in {len(df)} transactions from file")

        conn = get_db_connection()
        duplicates = []

        for index, row in df.iterrows():
            # Create transaction identifier similar to main.py logic
            date_str = str(row.get('Date', ''))
            if 'T' in date_str:
                date_str = date_str.split('T')[0]
            elif ' ' in date_str:
                date_str = date_str.split(' ')[0]

            description = str(row.get('Description', ''))[:50]
            amount = str(row.get('Amount', ''))

            # Create check key
            check_key = f"{date_str}|{amount}|{description}"

            # Check if this transaction exists in database
            existing = conn.execute("""
                SELECT transaction_id, date, description, amount
                FROM transactions
                WHERE (strftime('%Y-%m-%d', date) || '|' || CAST(amount AS TEXT) || '|' || substr(description, 1, 50)) = ?
                LIMIT 1
            """, (check_key,)).fetchone()

            if existing:
                duplicates.append({
                    'file_row': index + 1,
                    'date': date_str,
                    'description': description,
                    'amount': amount,
                    'existing_id': existing[0]
                })

        conn.close()

        result = {
            'has_duplicates': len(duplicates) > 0,
            'duplicate_count': len(duplicates),
            'total_transactions': len(df),
            'duplicates': duplicates[:5]  # Return first 5 for preview
        }

        print(f"🔍 Duplicate check result: {len(duplicates)} duplicates found out of {len(df)} total transactions")
        return result

    except Exception as e:
        print(f"ERROR: Error checking duplicates: {e}")
        return {
            'has_duplicates': False,
            'duplicate_count': 0,
            'total_transactions': 0,
            'duplicates': []
        }

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'Only CSV files are allowed'}), 400

        # Secure the filename
        filename = secure_filename(file.filename)

        # Save to parent directory (same location as other CSV files)
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        filepath = os.path.join(parent_dir, filename)

        # Save the uploaded file
        file.save(filepath)

        # Create backup first
        backup_path = f"{filepath}.backup"
        shutil.copy2(filepath, backup_path)

        # Always check for duplicates first
        duplicate_info = check_file_duplicates(filepath)
        if duplicate_info['has_duplicates']:
            print(f"🔍 Found {duplicate_info['duplicate_count']} duplicates, showing confirmation dialog")
            return jsonify({
                'success': False,
                'duplicate_confirmation_needed': True,
                'duplicate_info': duplicate_info,
                'message': f'Found {duplicate_info["duplicate_count"]} duplicate transactions. Please choose how to handle them.'
            })

        # Process the file in a simpler way to avoid subprocess issues
        try:
            # Use a subprocess to run the processing in a separate Python instance
            import subprocess

            processing_script = f"""
import sys
import os
sys.path.append('{parent_dir}')
os.chdir('{parent_dir}')

from main import DeltaCFOAgent

agent = DeltaCFOAgent()
result = agent.process_file('{filename}', enhance=True, use_smart_ingestion=True)

if result is not None:
    print(f'PROCESSED_COUNT:{{len(result)}}')
else:
    print('PROCESSED_COUNT:0')
"""

            # Run the processing script with environment variables
            env = os.environ.copy()
            env['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', '')

            print(f"🔧 DEBUG: Running subprocess for {filename}")
            print(f"🔧 DEBUG: API key set: {'Yes' if env.get('ANTHROPIC_API_KEY') else 'No'}")

            process_result = subprocess.run(
                [sys.executable, '-c', processing_script],
                capture_output=True,
                text=True,
                cwd=parent_dir,
                timeout=60,
                env=env
            )

            print(f"🔧 DEBUG: Subprocess return code: {process_result.returncode}")
            print(f"🔧 DEBUG: Subprocess stdout: {process_result.stdout}")
            print(f"🔧 DEBUG: Subprocess stderr: {process_result.stderr}")

            # Extract transaction count from output
            transactions_processed = 0
            if 'PROCESSED_COUNT:' in process_result.stdout:
                count_str = process_result.stdout.split('PROCESSED_COUNT:')[1].split('\n')[0]
                transactions_processed = int(count_str)

            # Now sync to database
            sync_result = sync_csv_to_database(filename)

            if sync_result:
                return jsonify({
                    'success': True,
                    'message': f'Successfully processed {filename}',
                    'transactions_processed': transactions_processed,
                    'sync_result': sync_result
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Processing succeeded but database sync failed',
                    'transactions_processed': transactions_processed
                }), 500

        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'error': 'Processing timeout - file too large or complex'
            }), 500
        except Exception as processing_error:
            import traceback
            error_details = traceback.format_exc()
            return jsonify({
                'success': False,
                'error': f'Processing failed: {str(processing_error)}',
                'details': error_details
            }), 500

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    """Download a CSV file"""
    try:
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        filepath = os.path.join(parent_dir, secure_filename(filename))

        if not os.path.exists(filepath):
            return "File not found", 404

        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return f"Error downloading file: {str(e)}", 500

@app.route('/api/process-duplicates', methods=['POST'])
def process_duplicates():
    """Process a file that was already uploaded with specific duplicate handling"""
    try:
        duplicate_handling = request.form.get('duplicateHandling', 'overwrite')
        filename = request.form.get('filename', '')

        if not filename:
            return jsonify({'error': 'No filename provided'}), 400

        print(f"🔄 Processing duplicates for {filename} with mode: {duplicate_handling}")

        # File should already exist from initial upload
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        filepath = os.path.join(parent_dir, filename)

        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 400

        # Use same processing logic as upload_file but force the duplicate handling
        import subprocess

        processing_script = f"""
import sys
import os
sys.path.append('{parent_dir}')
os.chdir('{parent_dir}')

from main import DeltaCFOAgent

agent = DeltaCFOAgent()
result = agent.process_file('{filename}', enhance=True, use_smart_ingestion=True)

if result is not None:
    print(f'PROCESSED_COUNT:{{len(result)}}')
else:
    print('PROCESSED_COUNT:0')
"""

        env = os.environ.copy()
        env['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', '')
        env['PYTHONPATH'] = parent_dir

        process_result = subprocess.run(
            ['python', '-c', processing_script],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=parent_dir,
            env=env
        )

        # Extract transaction count
        transactions_processed = 0
        if 'PROCESSED_COUNT:' in process_result.stdout:
            count_str = process_result.stdout.split('PROCESSED_COUNT:')[1].split('\n')[0]
            transactions_processed = int(count_str)

        # Sync to database
        sync_result = sync_csv_to_database(filename)

        if sync_result:
            action_msg = "updated" if duplicate_handling == 'overwrite' else "processed"
            return jsonify({
                'success': True,
                'message': f'Successfully {action_msg} {transactions_processed} transactions from {filename}',
                'transactions_processed': transactions_processed
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Processing succeeded but database sync failed'
            }), 500

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/log_interaction', methods=['POST'])
def api_log_interaction():
    """API endpoint to log user interactions for learning system"""
    try:
        data = request.get_json()

        required_fields = ['transaction_id', 'field_type', 'original_value', 'user_choice', 'action_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Extract data with defaults for optional fields
        transaction_id = data['transaction_id']
        field_type = data['field_type']
        original_value = data['original_value']
        ai_suggestions = data.get('ai_suggestions', [])
        user_choice = data['user_choice']
        action_type = data['action_type']
        transaction_context = data.get('transaction_context', {})
        session_id = data.get('session_id')

        # Log the interaction
        log_user_interaction(
            transaction_id=transaction_id,
            field_type=field_type,
            original_value=original_value,
            ai_suggestions=ai_suggestions,
            user_choice=user_choice,
            action_type=action_type,
            transaction_context=transaction_context,
            session_id=session_id
        )

        return jsonify({'success': True, 'message': 'Interaction logged successfully'})

    except Exception as e:
        print(f"ERROR: Error in api_log_interaction: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# INVOICE PROCESSING ROUTES
# ============================================================================

@app.route('/invoices')
def invoices_page():
    """Invoice management page"""
    try:
        cache_buster = str(random.randint(1000, 9999))
        return render_template('invoices.html', cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading invoices page: {str(e)}", 500

@app.route('/api/invoices')
def api_get_invoices():
    """API endpoint to get invoices with pagination and filtering"""
    try:
        # Get filter parameters
        filters = {
            'business_unit': request.args.get('business_unit'),
            'category': request.args.get('category'),
            'vendor_name': request.args.get('vendor_name'),
            'customer_name': request.args.get('customer_name')
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v}

        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        offset = (page - 1) * per_page

        conn = get_db_connection()

        # Build query
        query = "SELECT * FROM invoices WHERE 1=1"
        params = []

        if filters.get('business_unit'):
            query += " AND business_unit = ?"
            params.append(filters['business_unit'])

        if filters.get('category'):
            query += " AND category = ?"
            params.append(filters['category'])

        if filters.get('vendor_name'):
            query += " AND vendor_name LIKE ?"
            params.append(f"%{filters['vendor_name']}%")

        if filters.get('customer_name'):
            query += " AND customer_name LIKE ?"
            params.append(f"%{filters['customer_name']}%")

        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        total_count = conn.execute(count_query, params).fetchone()[0]

        # Add ordering and pagination
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        cursor = conn.execute(query, params)
        invoices = []

        for row in cursor.fetchall():
            invoice = dict(row)
            # Parse JSON fields
            if invoice.get('line_items'):
                try:
                    invoice['line_items'] = json.loads(invoice['line_items'])
                except:
                    invoice['line_items'] = []
            invoices.append(invoice)

        conn.close()

        return jsonify({
            'invoices': invoices,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/<invoice_id>')
def api_get_invoice(invoice_id):
    """Get single invoice by ID"""
    try:
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        conn.close()

        if not row:
            return jsonify({'error': 'Invoice not found'}), 404

        invoice = dict(row)
        # Parse JSON fields
        if invoice.get('line_items'):
            try:
                invoice['line_items'] = json.loads(invoice['line_items'])
            except:
                invoice['line_items'] = []

        return jsonify(invoice)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_compressed_file(file_path: str, extract_dir: str) -> List[str]:
    """
    Extract files from compressed archives (ZIP, RAR, 7z) with support for nested directories.
    Recursively walks through all subdirectories to find supported invoice files.

    Args:
        file_path: Path to the compressed archive file
        extract_dir: Directory to extract files to

    Returns:
        List of file paths for all supported invoice files found in the archive,
        or dict with 'error' key if extraction fails
    """
    try:
        import zipfile
        import py7zr

        file_ext = os.path.splitext(file_path)[1].lower()

        os.makedirs(extract_dir, exist_ok=True)

        # Extract archive based on file type
        if file_ext == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

        elif file_ext == '.7z':
            with py7zr.SevenZipFile(file_path, mode='r') as archive:
                archive.extractall(path=extract_dir)

        elif file_ext == '.rar':
            return {'error': 'RAR format requires additional setup. Please use ZIP or 7Z format.'}

        else:
            return {'error': f'Unsupported archive format: {file_ext}'}

        # Recursively walk through all directories to find supported files
        # This handles nested folder structures of any depth
        allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
        filtered_files = []

        for root, dirs, files in os.walk(extract_dir):
            for filename in files:
                file_path_in_archive = os.path.join(root, filename)
                file_extension = os.path.splitext(filename)[1].lower()

                # Only include files with supported extensions
                if file_extension in allowed_extensions and os.path.isfile(file_path_in_archive):
                    filtered_files.append(file_path_in_archive)

        return filtered_files

    except zipfile.BadZipFile:
        return {'error': 'Invalid or corrupted ZIP file'}
    except Exception as e:
        return {'error': f'Failed to extract archive: {str(e)}'}

@app.route('/api/invoices/upload', methods=['POST'])
def api_upload_invoice():
    """Upload and process invoice file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Check file type
        allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'}), 400

        # Save file
        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'invoices')
        os.makedirs(upload_dir, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)

        # Process invoice with Claude Vision
        invoice_data = process_invoice_with_claude(file_path, file.filename)

        if 'error' in invoice_data:
            return jsonify(invoice_data), 500

        return jsonify({
            'success': True,
            'invoice_id': invoice_data['id'],
            'invoice': invoice_data
        })

    except Exception as e:
        import traceback
        error_details = {
            'error': str(e),
            'error_type': type(e).__name__,
            'claude_client_status': 'initialized' if claude_client else 'not_initialized',
            'api_key_present': bool(os.getenv('ANTHROPIC_API_KEY')),
            'traceback': traceback.format_exc()
        }
        print(f"❌ Invoice upload error: {error_details}")
        return jsonify(error_details), 500

@app.route('/api/invoices/upload-batch', methods=['POST'])
def api_upload_batch_invoices():
    """Upload and process multiple invoice files or compressed archive"""
    try:
        if 'files' not in request.files and 'file' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'invoices')
        temp_extract_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'temp_extract')
        os.makedirs(upload_dir, exist_ok=True)

        results = {
            'success': True,
            'total_files': 0,
            'total_files_in_archive': 0,  # Total files found in ZIP (all types)
            'files_found': 0,  # Supported invoice files found
            'files_skipped': 0,  # Unsupported files skipped
            'processed': 0,
            'failed': 0,
            'invoices': [],
            'errors': [],
            'skipped_files': [],  # List of skipped filenames with reasons
            'archive_info': None  # Info about the archive structure
        }

        files_to_process = []
        cleanup_paths = []

        # Check if it's a compressed file
        if 'file' in request.files:
            file = request.files['file']
            file_ext = os.path.splitext(file.filename)[1].lower()

            if file_ext in ['.zip', '.7z', '.rar']:
                # Save compressed file
                compressed_path = os.path.join(upload_dir, f"{uuid.uuid4()}{file_ext}")
                file.save(compressed_path)
                cleanup_paths.append(compressed_path)

                # Count total files in archive before extraction
                total_in_archive = 0
                all_files_in_archive = []
                try:
                    if file_ext == '.zip':
                        import zipfile
                        with zipfile.ZipFile(compressed_path, 'r') as zip_ref:
                            all_files_in_archive = [name for name in zip_ref.namelist() if not name.endswith('/')]
                            total_in_archive = len(all_files_in_archive)
                    elif file_ext == '.7z':
                        import py7zr
                        with py7zr.SevenZipFile(compressed_path, mode='r') as archive:
                            all_files_in_archive = archive.getnames()
                            total_in_archive = len([f for f in all_files_in_archive if not f.endswith('/')])
                except:
                    pass

                results['total_files_in_archive'] = total_in_archive

                # Extract files
                extract_result = extract_compressed_file(compressed_path, temp_extract_dir)

                if isinstance(extract_result, dict) and 'error' in extract_result:
                    return jsonify(extract_result), 400

                files_to_process = [(f, os.path.basename(f)) for f in extract_result]
                results['files_found'] = len(files_to_process)

                # Calculate skipped files
                allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
                for file_in_archive in all_files_in_archive:
                    file_extension = os.path.splitext(file_in_archive)[1].lower()
                    if file_extension not in allowed_extensions and file_extension:
                        results['skipped_files'].append({
                            'filename': os.path.basename(file_in_archive),
                            'path': file_in_archive,
                            'reason': f'Unsupported file type: {file_extension}'
                        })

                results['files_skipped'] = len(results['skipped_files'])
                results['archive_info'] = {
                    'filename': file.filename,
                    'type': file_ext,
                    'nested_structure': any('/' in f or '\\' in f for f in all_files_in_archive)
                }

                cleanup_paths.append(temp_extract_dir)
            else:
                # Single file upload
                unique_filename = f"{uuid.uuid4()}{file_ext}"
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)
                files_to_process = [(file_path, file.filename)]

        # Check for multiple files
        elif 'files' in request.files:
            files = request.files.getlist('files')
            for file in files:
                if file.filename:
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    unique_filename = f"{uuid.uuid4()}{file_ext}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    file.save(file_path)
                    files_to_process.append((file_path, file.filename))

        results['total_files'] = len(files_to_process)

        # Process each file
        for file_path, original_filename in files_to_process:
            try:
                # Validate file type
                allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
                file_ext = os.path.splitext(file_path)[1].lower()

                if file_ext not in allowed_extensions:
                    results['failed'] += 1
                    results['errors'].append({
                        'file': original_filename,
                        'error': f'Unsupported file type: {file_ext}'
                    })
                    continue

                # Process invoice
                invoice_data = process_invoice_with_claude(file_path, original_filename)

                if 'error' in invoice_data:
                    results['failed'] += 1
                    results['errors'].append({
                        'file': original_filename,
                        'error': invoice_data['error']
                    })
                else:
                    results['processed'] += 1
                    results['invoices'].append({
                        'id': invoice_data['id'],
                        'invoice_number': invoice_data.get('invoice_number'),
                        'vendor_name': invoice_data.get('vendor_name'),
                        'total_amount': invoice_data.get('total_amount'),
                        'currency': invoice_data.get('currency'),
                        'original_filename': original_filename
                    })

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'file': original_filename,
                    'error': str(e)
                })

        # Cleanup temporary files
        for path in cleanup_paths:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    os.remove(path)
            except:
                pass

        # Set overall success status
        results['success'] = results['processed'] > 0

        return jsonify(results)

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/invoices/<invoice_id>', methods=['PUT'])
def api_update_invoice(invoice_id):
    """Update invoice fields - supports single field or multiple fields"""
    try:
        data = request.get_json()

        conn = get_db_connection()

        # Check if invoice exists
        existing = conn.execute("SELECT id FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not existing:
            conn.close()
            return jsonify({'error': 'Invoice not found'}), 404

        # Handle both single field update and multiple field update
        if 'field' in data and 'value' in data:
            # Single field update (for inline editing)
            field = data['field']
            value = data['value']

            # Validate field name to prevent SQL injection
            allowed_fields = ['invoice_number', 'date', 'due_date', 'vendor_name', 'vendor_address',
                            'vendor_tax_id', 'customer_name', 'customer_address', 'customer_tax_id',
                            'total_amount', 'currency', 'tax_amount', 'subtotal',
                            'business_unit', 'category', 'payment_terms']

            if field not in allowed_fields:
                conn.close()
                return jsonify({'error': 'Invalid field name'}), 400

            update_query = f"UPDATE invoices SET {field} = ? WHERE id = ?"
            conn.execute(update_query, (value, invoice_id))
        else:
            # Multiple field update (for modal editing)
            allowed_fields = ['invoice_number', 'date', 'due_date', 'vendor_name', 'vendor_address',
                            'vendor_tax_id', 'customer_name', 'customer_address', 'customer_tax_id',
                            'total_amount', 'currency', 'tax_amount', 'subtotal',
                            'business_unit', 'category', 'payment_terms']

            updates = []
            values = []

            for field, value in data.items():
                if field in allowed_fields and value is not None:
                    updates.append(f"{field} = ?")
                    values.append(value)

            if not updates:
                conn.close()
                return jsonify({'error': 'No valid fields to update'}), 400

            update_query = f"UPDATE invoices SET {', '.join(updates)} WHERE id = ?"
            values.append(invoice_id)
            conn.execute(update_query, values)

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Invoice updated'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/<invoice_id>', methods=['DELETE'])
def api_delete_invoice(invoice_id):
    """Delete invoice"""
    try:
        conn = get_db_connection()
        result = conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        conn.commit()
        conn.close()

        if result.rowcount == 0:
            return jsonify({'error': 'Invoice not found'}), 404

        return jsonify({'success': True, 'message': 'Invoice deleted'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/bulk-update', methods=['POST'])
def api_bulk_update_invoices():
    """Bulk update multiple invoices"""
    try:
        data = request.get_json()
        invoice_ids = data.get('invoice_ids', [])
        updates = data.get('updates', {})

        if not invoice_ids or not updates:
            return jsonify({'error': 'Missing invoice_ids or updates'}), 400

        # Validate field names
        allowed_fields = ['business_unit', 'category', 'currency', 'due_date', 'payment_terms',
                         'customer_name', 'customer_address', 'customer_tax_id']

        # Build update query
        update_parts = []
        values = []

        for field, value in updates.items():
            if field in allowed_fields and value:
                update_parts.append(f"{field} = ?")
                values.append(value)

        if not update_parts:
            return jsonify({'error': 'No valid fields to update'}), 400

        conn = get_db_connection()
        updated_count = 0

        # Update each invoice
        for invoice_id in invoice_ids:
            update_query = f"UPDATE invoices SET {', '.join(update_parts)} WHERE id = ?"
            result = conn.execute(update_query, values + [invoice_id])
            if result.rowcount > 0:
                updated_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'Successfully updated {updated_count} invoices'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/bulk-delete', methods=['POST'])
def api_bulk_delete_invoices():
    """Bulk delete multiple invoices"""
    try:
        data = request.get_json()
        invoice_ids = data.get('invoice_ids', [])

        if not invoice_ids:
            return jsonify({'error': 'No invoice IDs provided'}), 400

        conn = get_db_connection()
        deleted_count = 0

        # Delete each invoice
        for invoice_id in invoice_ids:
            result = conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
            if result.rowcount > 0:
                deleted_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} invoices'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/stats')
def api_invoice_stats():
    """Get invoice statistics"""
    try:
        conn = get_db_connection()

        # Total invoices
        total = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]

        # Total amount
        total_amount = conn.execute("SELECT COALESCE(SUM(total_amount), 0) FROM invoices").fetchone()[0]

        # Unique vendors
        unique_vendors = conn.execute("SELECT COUNT(DISTINCT vendor_name) FROM invoices WHERE vendor_name IS NOT NULL AND vendor_name != ''").fetchone()[0]

        # Unique customers
        unique_customers = conn.execute("SELECT COUNT(DISTINCT customer_name) FROM invoices WHERE customer_name IS NOT NULL AND customer_name != ''").fetchone()[0]

        # By business unit
        bu_counts = {}
        bu_rows = conn.execute("SELECT business_unit, COUNT(*), SUM(total_amount) FROM invoices WHERE business_unit IS NOT NULL GROUP BY business_unit").fetchall()
        for row in bu_rows:
            bu_counts[row[0]] = {'count': row[1], 'total': row[2]}

        # By category
        category_counts = {}
        category_rows = conn.execute("SELECT category, COUNT(*), SUM(total_amount) FROM invoices WHERE category IS NOT NULL GROUP BY category").fetchall()
        for row in category_rows:
            category_counts[row[0]] = {'count': row[1], 'total': row[2]}

        # By customer
        customer_counts = {}
        customer_rows = conn.execute("SELECT customer_name, COUNT(*), SUM(total_amount) FROM invoices WHERE customer_name IS NOT NULL AND customer_name != '' GROUP BY customer_name ORDER BY COUNT(*) DESC LIMIT 10").fetchall()
        for row in customer_rows:
            customer_counts[row[0]] = {'count': row[1], 'total': row[2]}

        # Recent invoices
        recent_rows = conn.execute("SELECT * FROM invoices ORDER BY created_at DESC LIMIT 5").fetchall()
        recent_invoices = [dict(row) for row in recent_rows]

        conn.close()

        return jsonify({
            'total_invoices': total,
            'total_amount': float(total_amount),
            'unique_vendors': unique_vendors,
            'unique_customers': unique_customers,
            'business_unit_breakdown': bu_counts,
            'category_breakdown': category_counts,
            'customer_breakdown': customer_counts,
            'recent_invoices': recent_invoices
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_invoice_with_claude(file_path: str, original_filename: str) -> Dict[str, Any]:
    """Process invoice file with Claude Vision API"""
    try:
        global claude_client

        # Initialize Claude client if not already done (lazy initialization)
        if not claude_client:
            init_success = init_claude_client()
            if not init_success or not claude_client:
                return {'error': 'Claude API client not initialized - check ANTHROPIC_API_KEY environment variable'}

        # Read and encode image
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.pdf':
            # Convert PDF to image using PyMuPDF
            try:
                import fitz  # PyMuPDF

                # Open PDF and get first page
                doc = fitz.open(file_path)
                if doc.page_count == 0:
                    return {'error': 'PDF has no pages'}

                # Get first page as image with 2x zoom for better quality
                page = doc.load_page(0)
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)

                # Convert to PNG bytes
                image_bytes = pix.pil_tobytes(format="PNG")
                doc.close()

                # Encode to base64
                image_data = base64.b64encode(image_bytes).decode('utf-8')
                media_type = 'image/png'

            except ImportError:
                return {'error': 'PyMuPDF not installed. Run: pip install PyMuPDF'}
            except Exception as e:
                return {'error': f'PDF conversion failed: {str(e)}'}
        else:
            # Read image file
            with open(file_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Determine media type
            media_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.tiff': 'image/tiff'
            }
            media_type = media_types.get(file_ext, 'image/png')

        # Build extraction prompt
        prompt = """Analyze this invoice image and extract BOTH vendor (who is sending/issuing the invoice) AND customer (who is receiving/paying the invoice) information in JSON format.

IMPORTANT: Distinguish between the two parties on the invoice:
- VENDOR/SUPPLIER (From/De/Remetente): The company ISSUING/SENDING the invoice
- CUSTOMER/CLIENT (To/Para/Destinatário): The company RECEIVING/PAYING the invoice

Common invoice keywords to help identify:
- Vendor indicators: "From", "Bill From", "Vendor", "Supplier", "De", "Remetente", "Fornecedor", "Issued by"
- Customer indicators: "To", "Bill To", "Sold To", "Client", "Customer", "Para", "Destinatário", "Cliente"

REQUIRED FIELDS:
- invoice_number: The invoice/bill number
- date: Invoice date (YYYY-MM-DD format)
- vendor_name: Company name ISSUING the invoice (FROM)
- customer_name: Company name RECEIVING the invoice (TO)
- total_amount: Total amount (numeric value only)
- currency: Currency (USD, BRL, PYG, etc.)

OPTIONAL VENDOR FIELDS:
- vendor_address: Vendor's address
- vendor_tax_id: Vendor's Tax ID/CNPJ/EIN/RUC if present

OPTIONAL CUSTOMER FIELDS:
- customer_address: Customer's address
- customer_tax_id: Customer's Tax ID/CNPJ/EIN/RUC if present

OTHER OPTIONAL FIELDS:
- due_date: Due date if present (YYYY-MM-DD format)
- tax_amount: Tax amount if itemized
- subtotal: Subtotal before tax
- line_items: Array of line items with description, quantity, unit_price, total

CLASSIFICATION HINTS:
Based on the customer (who is paying), suggest:
- business_unit: One of ["Delta LLC", "Delta Prop Shop LLC", "Delta Mining Paraguay S.A.", "Delta Brazil", "Personal"]
- category: One of ["Technology Expenses", "Utilities", "Insurance", "Professional Services", "Office Expenses", "Other"]

Return ONLY a JSON object with this structure:
{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "vendor_name": "string (FROM - who is sending the invoice)",
    "vendor_address": "string",
    "vendor_tax_id": "string",
    "customer_name": "string (TO - who is receiving/paying the invoice)",
    "customer_address": "string",
    "customer_tax_id": "string",
    "total_amount": 1234.56,
    "currency": "USD",
    "tax_amount": 123.45,
    "subtotal": 1111.11,
    "due_date": "YYYY-MM-DD",
    "line_items": [
        {"description": "Item 1", "quantity": 1, "unit_price": 100.00, "total": 100.00}
    ],
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Any issues or observations"
}

Be precise with numbers and dates. If a field is not clearly visible, use null.
CRITICAL: Make sure vendor_name is who SENT the invoice and customer_name is who RECEIVES/PAYS the invoice."""

        # Call Claude Vision API
        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4000,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        # Parse response
        response_text = response.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()

        extracted_data = json.loads(response_text)

        # Generate invoice ID
        invoice_id = str(uuid.uuid4())

        # Prepare invoice data for database
        invoice_data = {
            'id': invoice_id,
            'invoice_number': extracted_data.get('invoice_number', ''),
            'date': extracted_data.get('date'),
            'due_date': extracted_data.get('due_date'),
            'vendor_name': extracted_data.get('vendor_name', ''),
            'vendor_address': extracted_data.get('vendor_address'),
            'vendor_tax_id': extracted_data.get('vendor_tax_id'),
            'customer_name': extracted_data.get('customer_name', ''),
            'customer_address': extracted_data.get('customer_address'),
            'customer_tax_id': extracted_data.get('customer_tax_id'),
            'total_amount': float(extracted_data.get('total_amount', 0)),
            'currency': extracted_data.get('currency', 'USD'),
            'tax_amount': float(extracted_data.get('tax_amount', 0)) if extracted_data.get('tax_amount') else None,
            'subtotal': float(extracted_data.get('subtotal', 0)) if extracted_data.get('subtotal') else None,
            'line_items': json.dumps(extracted_data.get('line_items', [])),
            'status': 'pending',
            'invoice_type': 'other',
            'confidence_score': float(extracted_data.get('confidence', 0.8)),
            'processing_notes': extracted_data.get('processing_notes', ''),
            'source_file': original_filename,
            'extraction_method': 'claude_vision',
            'processed_at': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'business_unit': extracted_data.get('business_unit'),
            'category': extracted_data.get('category'),
            'currency_type': 'fiat'  # Can be enhanced later
        }

        # Save to database
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO invoices (
                id, invoice_number, date, due_date, vendor_name, vendor_address,
                vendor_tax_id, customer_name, customer_address, customer_tax_id,
                total_amount, currency, tax_amount, subtotal,
                line_items, status, invoice_type, confidence_score, processing_notes,
                source_file, extraction_method, processed_at, created_at,
                business_unit, category, currency_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_data['id'], invoice_data['invoice_number'], invoice_data['date'],
            invoice_data['due_date'], invoice_data['vendor_name'], invoice_data['vendor_address'],
            invoice_data['vendor_tax_id'], invoice_data['customer_name'], invoice_data['customer_address'],
            invoice_data['customer_tax_id'], invoice_data['total_amount'], invoice_data['currency'],
            invoice_data['tax_amount'], invoice_data['subtotal'], invoice_data['line_items'],
            invoice_data['status'], invoice_data['invoice_type'], invoice_data['confidence_score'],
            invoice_data['processing_notes'], invoice_data['source_file'], invoice_data['extraction_method'],
            invoice_data['processed_at'], invoice_data['created_at'], invoice_data['business_unit'],
            invoice_data['category'], invoice_data['currency_type']
        ))
        conn.commit()
        conn.close()

        print(f"Invoice processed successfully: {invoice_data['invoice_number']}")
        return invoice_data

    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON response from Claude: {e}")
        return {'error': f'Invalid JSON response from Claude Vision: {str(e)}'}
    except Exception as e:
        print(f"ERROR: Invoice processing failed: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

# ============================================================================
# REINFORCEMENT LEARNING SYSTEM
# ============================================================================

def log_user_interaction(transaction_id: str, field_type: str, original_value: str,
                        ai_suggestions: list, user_choice: str, action_type: str,
                        transaction_context: dict, session_id: str = None):
    """Log user interactions for learning system"""
    try:
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO user_interactions (
                transaction_id, field_type, original_value, ai_suggestions,
                user_choice, action_type, transaction_context, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_id, field_type, original_value,
            json.dumps(ai_suggestions), user_choice, action_type,
            json.dumps(transaction_context), session_id
        ))
        conn.commit()
        conn.close()
        print(f"SUCCESS: Logged user interaction: {action_type} for {field_type}")

        # Update performance metrics
        update_ai_performance_metrics(field_type, action_type == 'accepted_ai_suggestion')

        # Learn from this interaction
        learn_from_interaction(transaction_id, field_type, user_choice, transaction_context)

    except Exception as e:
        print(f"ERROR: Error logging user interaction: {e}")

def update_ai_performance_metrics(field_type: str, was_accepted: bool):
    """Update daily AI performance metrics"""
    try:
        conn = get_db_connection()
        today = datetime.now().date()

        # Get existing metrics for today
        existing = conn.execute("""
            SELECT total_suggestions, accepted_suggestions
            FROM ai_performance_metrics
            WHERE date = ? AND field_type = ?
        """, (today, field_type)).fetchone()

        if existing:
            total = existing[0] + 1
            accepted = existing[1] + (1 if was_accepted else 0)
            accuracy = accepted / total if total > 0 else 0

            conn.execute("""
                UPDATE ai_performance_metrics
                SET total_suggestions = ?, accepted_suggestions = ?, accuracy_rate = ?
                WHERE date = ? AND field_type = ?
            """, (total, accepted, accuracy, today, field_type))
        else:
            conn.execute("""
                INSERT INTO ai_performance_metrics
                (date, field_type, total_suggestions, accepted_suggestions, accuracy_rate)
                VALUES (?, ?, 1, ?, ?)
            """, (today, field_type, 1 if was_accepted else 0, 1.0 if was_accepted else 0.0))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"ERROR: Error updating performance metrics: {e}")

def learn_from_interaction(transaction_id: str, field_type: str, user_choice: str, context: dict):
    """Learn patterns from user interactions"""
    try:
        conn = get_db_connection()

        # Create pattern condition based on transaction context
        pattern_condition = {}

        if field_type == 'description':
            # For descriptions, learn based on original description patterns
            original_desc = context.get('original_value', '')
            if 'M MERCHANT' in original_desc.upper():
                pattern_condition = {'contains': 'M MERCHANT'}
            elif 'DELTA PROP SHOP' in original_desc.upper():
                pattern_condition = {'contains': 'DELTA PROP SHOP'}
            elif 'CHASE' in original_desc.upper():
                pattern_condition = {'contains': 'CHASE'}

        elif field_type == 'accounting_category':
            # Learn based on entity and amount patterns
            pattern_condition = {
                'entity': context.get('classified_entity'),
                'amount_range': 'positive' if float(context.get('amount', 0)) > 0 else 'negative'
            }

        if pattern_condition:
            pattern_type = f"{field_type}_pattern"
            condition_json = json.dumps(pattern_condition)

            # Check if pattern exists
            existing = conn.execute("""
                SELECT id, usage_count, success_count, confidence_score
                FROM learned_patterns
                WHERE pattern_type = ? AND pattern_condition = ? AND suggested_value = ?
            """, (pattern_type, condition_json, user_choice)).fetchone()

            if existing:
                # Update existing pattern
                new_usage = existing[1] + 1
                new_success = existing[2] + 1
                new_confidence = min(0.95, existing[3] + 0.05)  # Increase confidence

                conn.execute("""
                    UPDATE learned_patterns
                    SET usage_count = ?, success_count = ?, confidence_score = ?, last_used = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_usage, new_success, new_confidence, existing[0]))
            else:
                # Create new pattern
                conn.execute("""
                    INSERT INTO learned_patterns
                    (pattern_type, pattern_condition, suggested_value, confidence_score)
                    VALUES (?, ?, ?, 0.7)
                """, (pattern_type, condition_json, user_choice))

            conn.commit()
            print(f"SUCCESS: Learned pattern: {pattern_type} -> {user_choice}")

        conn.close()
    except Exception as e:
        print(f"ERROR: Error learning from interaction: {e}")

def get_learned_suggestions(field_type: str, transaction_context: dict) -> list:
    """Get suggestions based on learned patterns"""
    try:
        conn = get_db_connection()
        suggestions = []

        if field_type == 'description':
            original_desc = transaction_context.get('description', '').upper()

            # Check for learned patterns
            patterns = conn.execute("""
                SELECT suggested_value, confidence_score, pattern_condition
                FROM learned_patterns
                WHERE pattern_type = 'description_pattern' AND confidence_score > 0.6
                ORDER BY confidence_score DESC, usage_count DESC
            """).fetchall()

            for pattern in patterns:
                condition = json.loads(pattern[2])
                if 'contains' in condition:
                    if condition['contains'] in original_desc:
                        suggestions.append({
                            'value': pattern[0],
                            'confidence': pattern[1],
                            'source': 'learned_pattern'
                        })

        elif field_type == 'accounting_category':
            entity = transaction_context.get('classified_entity')
            amount = float(transaction_context.get('amount', 0))
            amount_range = 'positive' if amount > 0 else 'negative'

            patterns = conn.execute("""
                SELECT suggested_value, confidence_score, pattern_condition
                FROM learned_patterns
                WHERE pattern_type = 'accounting_category_pattern' AND confidence_score > 0.6
                ORDER BY confidence_score DESC, usage_count DESC
            """).fetchall()

            for pattern in patterns:
                condition = json.loads(pattern[2])
                if (condition.get('entity') == entity or
                    condition.get('amount_range') == amount_range):
                    suggestions.append({
                        'value': pattern[0],
                        'confidence': pattern[1],
                        'source': 'learned_pattern'
                    })

        conn.close()
        return suggestions[:3]  # Return top 3 learned suggestions

    except Exception as e:
        print(f"ERROR: Error getting learned suggestions: {e}")
        return []

def enhance_ai_prompt_with_learning(field_type: str, base_prompt: str, context: dict) -> str:
    """Enhance AI prompts with learned patterns"""
    try:
        learned_suggestions = get_learned_suggestions(field_type, context)

        if learned_suggestions:
            learning_context = "\n\nBased on previous user preferences for similar transactions:"
            for suggestion in learned_suggestions:
                confidence_pct = int(suggestion['confidence'] * 100)
                learning_context += f"\n- '{suggestion['value']}' (user chose this {confidence_pct}% of the time)"

            learning_context += "\n\nConsider these learned preferences in your suggestions."
            return base_prompt + learning_context

        return base_prompt
    except Exception as e:
        print(f"ERROR: Error enhancing prompt: {e}")
        return base_prompt

if __name__ == '__main__':
    print("Starting Delta CFO Agent Web Interface (Database Mode)")
    print("Database backend enabled")

    # Initialize Claude API
    init_claude_client()

    # Initialize invoice tables
    init_invoice_tables()

    # Get port from environment (Cloud Run sets PORT automatically)
    port = int(os.environ.get('PORT', 5002))

    print(f"Starting server on port {port}")
    print("Invoice processing module integrated")
    app.run(host='0.0.0.0', port=port, debug=False)

# Initialize Claude client and database on module import (for production deployments like Cloud Run)
try:
    if not claude_client:
        init_claude_client()
    init_invoice_tables()
    print("✅ Production initialization completed")
except Exception as e:
    print(f"⚠️  Production initialization warning: {e}")
