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

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)

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

        # Check for .anthropic_api_key file in parent directory
        if not api_key:
            key_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.anthropic_api_key')
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    api_key = f.read().strip()

        if api_key:
            claude_client = anthropic.Anthropic(api_key=api_key)
            print("✅ Claude API client initialized")
            return True
        else:
            print("⚠️  Claude API key not found - AI features disabled")
            return False
    except Exception as e:
        print(f"❌ Error initializing Claude API: {e}")
        return False

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_transactions_from_db(filters=None, page=1, per_page=50):
    """Load transactions from database with filtering and pagination"""
    try:
        print("🔍 Loading transactions from database...")
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
            transactions.append(transaction)

        conn.close()
        print(f"✅ Loaded {len(transactions)} transactions using database backend")

        return transactions, total_count

    except Exception as e:
        print(f"❌ Error loading transactions from database: {e}")
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
        print(f"❌ Error calculating dashboard stats: {e}")
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

        print(f"🔄 Updating transaction {transaction_id}: field={field}")
        return True

    except Exception as e:
        print(f"❌ Error updating transaction field: {e}")
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
        print(f"🤖 Calling Claude API for similar descriptions analysis...")

        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        elapsed_time = time.time() - start_time
        print(f"⏱️  Claude API response time: {elapsed_time:.2f} seconds")

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
            print(f"❌ Error parsing Claude response for similar descriptions: {e}")
            return []

    except Exception as e:
        print(f"❌ Error in Claude analysis of similar descriptions: {e}")
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
        print(f"❌ Error finding similar descriptions: {e}")
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
            Based on this transaction:
            - Description: {context.get('description', '')}
            - Current entity: {current_value}

            Suggest 3-5 business entities this could belong to from: Delta LLC, Delta Prop Shop LLC, Infinity Validator, Delta Mining Paraguay S.A., Delta Brazil, Personal.
            Return only the entity names, one per line.
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
            print(f"❌ No prompt found for field_type: {field_type}")
            return []

        print(f"✅ Found prompt for {field_type}, enhancing with learning...")
        # Enhance prompt with learned patterns
        enhanced_prompt = enhance_ai_prompt_with_learning(field_type, prompt, context)
        print(f"✅ Enhanced prompt created, calling Claude API...")

        print(f"🤖 Calling Claude API for {field_type} suggestions...")
        start_time = time.time()

        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            messages=[{"role": "user", "content": enhanced_prompt}]
        )

        elapsed_time = time.time() - start_time
        print(f"⏱️  Claude API response time: {elapsed_time:.2f} seconds")

        ai_suggestions = [line.strip() for line in response.content[0].text.strip().split('\n') if line.strip()]
        print(f"💡 Claude suggestions: {ai_suggestions}")

        # Get learned suggestions
        learned_suggestions = get_learned_suggestions(field_type, context)
        learned_values = [s['value'] for s in learned_suggestions]
        print(f"📚 Learned suggestions: {learned_values}")

        # Combine suggestions, prioritizing Claude AI suggestions FIRST
        combined_suggestions = []
        for ai_suggestion in ai_suggestions:
            if ai_suggestion not in combined_suggestions:
                combined_suggestions.append(ai_suggestion)

        for learned in learned_values:
            if learned not in combined_suggestions:
                combined_suggestions.append(learned)

        print(f"🔗 Final combined suggestions: {combined_suggestions[:5]}")
        return combined_suggestions[:5]  # Limit to 5 suggestions

    except Exception as e:
        print(f"❌ Error getting AI suggestions: {e}")
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
            print(f"⚠️  CSV file not found for sync: {csv_path}")
            return False

        # Read the CSV file
        df = pd.read_csv(csv_path)
        print(f"🔄 Syncing {len(df)} transactions to database...")

        # Connect to database
        conn = get_db_connection()

        # For specific file uploads, only clear data from that source file
        if csv_filename:
            source_file = csv_filename.replace('classified_', '')
            conn.execute("DELETE FROM transactions WHERE source_file = ?", (source_file,))
            print(f"🗑️  Cleared existing data for source file: {source_file}")
        else:
            # Only clear all data if syncing MASTER_TRANSACTIONS.csv (full sync)
            conn.execute("DELETE FROM transactions")
            print("🗑️  Cleared all existing data for full sync")

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
        print(f"✅ Successfully synced {len(df)} transactions to database")
        return True

    except Exception as e:
        print(f"❌ Error syncing CSV to database: {e}")
        return False

@app.route('/')
def dashboard():
    """Main dashboard page"""
    try:
        stats = get_dashboard_stats()
        cache_buster = str(random.randint(1000, 9999))
        return render_template('dashboard_advanced.html', stats=stats, cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

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
        print(f"❌ API suggestions error: {e}")
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

        # Process the file using DeltaCFOAgent
        try:
            print(f"🔄 Starting processing for {filename}")

            # Import and run the main processor
            sys.path.append(parent_dir)
            from main import DeltaCFOAgent

            # Create backup first
            backup_path = f"{filepath}.backup"
            shutil.copy2(filepath, backup_path)
            print(f"✅ Created backup: {backup_path}")

            # Process the file
            print(f"🚀 Initializing DeltaCFOAgent...")
            agent = DeltaCFOAgent()
            print(f"📄 Processing file: {filepath}")
            result = agent.process_file(filepath, enhance=True, use_smart_ingestion=True)
            print(f"✅ Processing completed, result type: {type(result)}")

            # After processing, we need to sync the CSV data to the database
            print(f"🔄 Syncing to database...")
            sync_result = sync_csv_to_database(filename)
            print(f"✅ Sync result: {sync_result}")

            # Extract transaction count from DataFrame
            transactions_processed = len(result) if result is not None and hasattr(result, '__len__') else 0
            print(f"📊 Transactions processed: {transactions_processed}")

            return jsonify({
                'success': True,
                'message': f'Successfully processed {filename}',
                'transactions_processed': transactions_processed
            })

        except Exception as processing_error:
            # If processing fails, at least keep the uploaded file
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Processing error: {processing_error}")
            print(f"❌ Error details: {error_details}")
            return jsonify({
                'success': False,
                'error': f'Processing failed: {str(processing_error)}',
                'details': error_details
            }), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        print(f"❌ Error in api_log_interaction: {e}")
        return jsonify({'error': str(e)}), 500

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
        print(f"✅ Logged user interaction: {action_type} for {field_type}")

        # Update performance metrics
        update_ai_performance_metrics(field_type, action_type == 'accepted_ai_suggestion')

        # Learn from this interaction
        learn_from_interaction(transaction_id, field_type, user_choice, transaction_context)

    except Exception as e:
        print(f"❌ Error logging user interaction: {e}")

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
        print(f"❌ Error updating performance metrics: {e}")

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
            print(f"✅ Learned pattern: {pattern_type} -> {user_choice}")

        conn.close()
    except Exception as e:
        print(f"❌ Error learning from interaction: {e}")

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
        print(f"❌ Error getting learned suggestions: {e}")
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
        print(f"❌ Error enhancing prompt: {e}")
        return base_prompt

if __name__ == '__main__':
    print("🚀 Starting Delta CFO Agent Web Interface (Database Mode)")
    print("📊 Database backend enabled")

    # Initialize Claude API
    init_claude_client()

    print("🌐 Access at: http://localhost:5002")
    app.run(host='0.0.0.0', port=5002, debug=True)