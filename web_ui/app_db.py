#!/usr/bin/env python3
"""
Delta CFO Agent - Database-Backed Web Dashboard
Advanced web interface for financial transaction management with Claude AI integration
"""

import os
import sys
import json
import sqlite3  # Kept for backward compatibility - main DB uses database.py manager
import pandas as pd
import time
import threading
import traceback
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import anthropic
from typing import List, Dict, Any, Optional
from werkzeug.utils import secure_filename
import subprocess
import shutil
import hashlib
import uuid
import base64
import zipfile
import re
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Archive handling imports - optional
try:
    import py7zr
    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False
    print("WARNING: py7zr not available - 7z archive support disabled")

# Database imports - support both SQLite and PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    print("WARNING: psycopg2 not available - PostgreSQL support disabled")

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import invoice processing modules
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'invoice_processing'))

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size for batch uploads

# Database connection - DEPRECATED: Now using database manager (database.py)
# DB_PATH = os.path.join(os.path.dirname(__file__), 'delta_transactions.db')

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
            print(f"[OK] Claude API client initialized successfully (key: {api_key[:10]}...{api_key[-4:]})")
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
        with get_db_connection() as conn:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')

            # Main invoices table
            cursor.execute('''
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
            if is_postgresql:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS invoice_email_log (
                        id SERIAL PRIMARY KEY,
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
            else:
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

            # Background jobs table for async processing
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS background_jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    total_items INTEGER NOT NULL DEFAULT 0,
                    processed_items INTEGER NOT NULL DEFAULT 0,
                    successful_items INTEGER NOT NULL DEFAULT 0,
                    failed_items INTEGER NOT NULL DEFAULT 0,
                    progress_percentage REAL NOT NULL DEFAULT 0.0,
                    started_at TEXT,
                    completed_at TEXT,
                    created_at TEXT NOT NULL,
                    created_by TEXT DEFAULT 'system',
                    source_file TEXT,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')

            # Job items table for tracking individual files in a job
            if is_postgresql:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS job_items (
                        id SERIAL PRIMARY KEY,
                        job_id TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        item_path TEXT,
                        status TEXT NOT NULL DEFAULT 'pending',
                        processed_at TEXT,
                        error_message TEXT,
                        result_data TEXT,
                        processing_time_seconds REAL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (job_id) REFERENCES background_jobs(id)
                    )
                ''')
            else:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS job_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        item_path TEXT,
                        status TEXT NOT NULL DEFAULT 'pending',
                        processed_at TEXT,
                        error_message TEXT,
                        result_data TEXT,
                        processing_time_seconds REAL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (job_id) REFERENCES background_jobs(id)
                    )
                ''')

            # Add customer columns to existing tables (migration)
            try:
                cursor.execute('ALTER TABLE invoices ADD COLUMN customer_name TEXT')
                print("Added customer_name column to invoices table")
            except:
                pass  # Column already exists

            try:
                cursor.execute('ALTER TABLE invoices ADD COLUMN customer_address TEXT')
                print("Added customer_address column to invoices table")
            except:
                pass  # Column already exists

            try:
                cursor.execute('ALTER TABLE invoices ADD COLUMN customer_tax_id TEXT')
                print("Added customer_tax_id column to invoices table")
            except:
                pass  # Column already exists

            conn.commit()
            print("Invoice tables initialized successfully")
            return True
    except Exception as e:
        print(f"ERROR: Failed to initialize invoice tables: {e}")
        return False

def init_database():
    """Initialize database and create tables if they don't exist - now uses database manager"""
    try:
        from database import db_manager
        db_manager.init_database()
        print("[OK] Database initialized successfully")
    except Exception as e:
        print(f"[ERROR] Failed to initialize database: {e}")
        raise

# ============================================================================
# BACKGROUND JOBS MANAGEMENT
# ============================================================================

def ensure_background_jobs_tables():
    """Ensure background jobs tables exist with correct schema"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')

            # MIGRATION: Expand VARCHAR(10) fields to avoid overflow errors
            if is_postgresql:
                try:
                    # Expand currency field in transactions table
                    cursor.execute("ALTER TABLE transactions ALTER COLUMN currency TYPE VARCHAR(50)")
                    print("[OK] Migrated transactions.currency VARCHAR(10) → VARCHAR(50)")
                except Exception as e:
                    if "does not exist" not in str(e) and "already exists" not in str(e):
                        print(f"Currency migration info: {e}")

                try:
                    # Expand currency field in invoices table
                    cursor.execute("ALTER TABLE invoices ALTER COLUMN currency TYPE VARCHAR(50)")
                    print("[OK] Migrated invoices.currency VARCHAR(10) → VARCHAR(50)")
                except Exception as e:
                    if "does not exist" not in str(e) and "already exists" not in str(e):
                        print(f"Currency migration info: {e}")

            # Background jobs table for async processing
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS background_jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    total_items INTEGER NOT NULL DEFAULT 0,
                    processed_items INTEGER NOT NULL DEFAULT 0,
                    successful_items INTEGER NOT NULL DEFAULT 0,
                    failed_items INTEGER NOT NULL DEFAULT 0,
                    progress_percentage REAL NOT NULL DEFAULT 0.0,
                    started_at TEXT,
                    completed_at TEXT,
                    created_at TEXT NOT NULL,
                    created_by TEXT DEFAULT 'system',
                    source_file TEXT,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')

            # Job items table for tracking individual files in a job
            if is_postgresql:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS job_items (
                        id SERIAL PRIMARY KEY,
                        job_id TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        item_path TEXT,
                        status TEXT NOT NULL DEFAULT 'pending',
                        processed_at TEXT,
                        error_message TEXT,
                        result_data TEXT,
                        processing_time_seconds REAL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (job_id) REFERENCES background_jobs(id)
                    )
                ''')
            else:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS job_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        item_path TEXT,
                        status TEXT NOT NULL DEFAULT 'pending',
                        processed_at TEXT,
                        error_message TEXT,
                        result_data TEXT,
                        processing_time_seconds REAL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (job_id) REFERENCES background_jobs(id)
                    )
                ''')

            conn.commit()
            print("[OK] Background jobs tables ensured")
            return True

    except Exception as e:
        print(f"ERROR: Failed to ensure background jobs tables: {e}")
        return False

def create_background_job(job_type: str, total_items: int, created_by: str = 'system',
                         source_file: str = None, metadata: str = None) -> str:
    """Create a new background job and return job ID"""
    # First ensure tables exist
    if not ensure_background_jobs_tables():
        print("ERROR: Cannot create background job - tables not available")
        return None

    job_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            cursor.execute(f"""
                INSERT INTO background_jobs (
                    id, job_type, status, total_items, created_at, created_by,
                    source_file, metadata
                ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder},
                         {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """, (job_id, job_type, 'pending', total_items, created_at, created_by,
                  source_file, metadata))

            conn.commit()
            print(f"[OK] Created background job {job_id} with {total_items} items")
            return job_id

    except Exception as e:
        print(f"ERROR: Failed to create background job: {e}")
        traceback.print_exc()
        return None

def add_job_item(job_id: str, item_name: str, item_path: str = None) -> int:
    """Add an item to a job and return item ID"""
    created_at = datetime.utcnow().isoformat()

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            cursor.execute(f"""
                INSERT INTO job_items (job_id, item_name, item_path, status, created_at)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """, (job_id, item_name, item_path, 'pending', created_at))

            if is_postgresql:
                cursor.execute("SELECT lastval()")
                item_id = cursor.fetchone()['lastval']
            else:
                item_id = cursor.lastrowid

            conn.commit()
            return item_id

    except Exception as e:
        print(f"ERROR: Failed to add job item: {e}")
        return None

def update_job_progress(job_id: str, processed_items: int = None, successful_items: int = None,
                       failed_items: int = None, status: str = None, error_message: str = None):
    """Update job progress and status"""

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            # Build dynamic update query
            updates = []
            values = []

            if processed_items is not None:
                updates.append(f"processed_items = {placeholder}")
                values.append(processed_items)
            if successful_items is not None:
                updates.append(f"successful_items = {placeholder}")
                values.append(successful_items)
            if failed_items is not None:
                updates.append(f"failed_items = {placeholder}")
                values.append(failed_items)
            if status is not None:
                updates.append(f"status = {placeholder}")
                values.append(status)
                if status in ['completed', 'failed', 'completed_with_errors']:
                    updates.append(f"completed_at = {placeholder}")
                    values.append(datetime.utcnow().isoformat())
                elif status == 'processing':
                    updates.append(f"started_at = {placeholder}")
                    values.append(datetime.utcnow().isoformat())
            if error_message is not None:
                updates.append(f"error_message = {placeholder}")
                values.append(error_message)

            # Calculate progress percentage if we have processed_items
            if processed_items is not None:
                cursor.execute(f"SELECT total_items FROM background_jobs WHERE id = {placeholder}", (job_id,))
                result = cursor.fetchone()
                if result:
                    total = result['total_items'] if is_postgresql else result[0]
                    if total > 0:
                        progress = (processed_items / total) * 100
                        updates.append(f"progress_percentage = {placeholder}")
                        values.append(progress)

            if updates:
                values.append(job_id)
                update_query = f"UPDATE background_jobs SET {', '.join(updates)} WHERE id = {placeholder}"
                cursor.execute(update_query, values)

            conn.commit()

    except Exception as e:
        print(f"ERROR: Failed to update job progress: {e}")

def update_job_item_status(job_id: str, item_name: str, status: str,
                          error_message: str = None, result_data: str = None, processing_time: float = None):
    """Update individual job item status"""

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            processed_at = datetime.utcnow().isoformat() if status in ['completed', 'failed'] else None

            cursor.execute(f"""
                UPDATE job_items
                SET status = {placeholder}, processed_at = {placeholder},
                    error_message = {placeholder}, result_data = {placeholder}, processing_time_seconds = {placeholder}
                WHERE job_id = {placeholder} AND item_name = {placeholder}
            """, (status, processed_at, error_message, result_data, processing_time, job_id, item_name))

            conn.commit()

    except Exception as e:
        print(f"ERROR: Failed to update job item status: {e}")

def get_job_status(job_id: str) -> dict:
    """Get complete job status with items"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            # Get job info
            cursor.execute(f"SELECT * FROM background_jobs WHERE id = {placeholder}", (job_id,))
            job_row = cursor.fetchone()

            if not job_row:
                return {'error': 'Job not found'}

            job_info = dict(job_row)

            # Get job items
            cursor.execute(f"SELECT * FROM job_items WHERE job_id = {placeholder} ORDER BY created_at", (job_id,))
            items_rows = cursor.fetchall()
            job_info['items'] = [dict(row) for row in items_rows]

            return job_info

    except Exception as e:
        print(f"ERROR: Failed to get job status: {e}")
        return {'error': str(e)}

def process_single_invoice_item(job_id: str, item: dict):
    """Process a single invoice item (for parallel execution)"""

    item_name = item['item_name']
    item_path = item.get('item_path')

    if not item_path or not os.path.exists(item_path):
        # File not found - mark as failed
        update_job_item_status(job_id, item_name, 'failed',
                             error_message='File not found or path invalid')
        return {'status': 'failed', 'item_name': item_name, 'error': 'File not found'}

    print(f"[PROCESS] Processing item: {item_name}")
    start_time = time.time()

    try:
        # Process the invoice using existing function
        invoice_data = process_invoice_with_claude(item_path, item_name)
        processing_time = time.time() - start_time

        if 'error' in invoice_data:
            # Processing failed
            update_job_item_status(job_id, item_name, 'failed',
                                 error_message=invoice_data['error'],
                                 processing_time=processing_time)
            print(f"[ERROR] Failed item: {item_name} - {invoice_data['error']}")
            return {'status': 'failed', 'item_name': item_name, 'error': invoice_data['error']}
        else:
            # Processing successful
            result_summary = {
                'id': invoice_data.get('id'),
                'invoice_number': invoice_data.get('invoice_number'),
                'vendor_name': invoice_data.get('vendor_name'),
                'total_amount': invoice_data.get('total_amount')
            }
            update_job_item_status(job_id, item_name, 'completed',
                                 result_data=str(result_summary),
                                 processing_time=processing_time)
            print(f"[OK] Completed item: {item_name} in {processing_time:.2f}s")

            # Clean up processed file to save storage
            try:
                os.remove(item_path)
                print(f"🗑️ Cleaned up file: {item_path}")
            except:
                pass  # File cleanup failed, but processing succeeded

            return {'status': 'completed', 'item_name': item_name, 'result': result_summary}

    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Processing error: {str(e)}"
        print(f"[ERROR] Failed item: {item_name} - {error_msg}")

        update_job_item_status(job_id, item_name, 'failed',
                             error_message=error_msg,
                             processing_time=processing_time)
        return {'status': 'failed', 'item_name': item_name, 'error': error_msg}

def process_invoice_batch_job(job_id: str):
    """Background worker to process invoice batch job with parallel processing"""
    print(f"🚀 Starting background job {job_id}")

    try:
        # Update job status to processing
        update_job_progress(job_id, status='processing')

        # Get job details
        job_info = get_job_status(job_id)
        if 'error' in job_info:
            update_job_progress(job_id, status='failed', error_message='Job not found')
            return

        items = job_info.get('items', [])
        processed_count = 0
        successful_count = 0
        failed_count = 0

        print(f"📋 Processing {len(items)} items in job {job_id} with parallel workers")

        # Process items in parallel with ThreadPoolExecutor
        max_workers = min(5, len(items))  # Limit to 5 concurrent workers
        print(f"🔥 Using {max_workers} parallel workers")

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=f"InvoiceWorker-{job_id[:8]}") as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(process_single_invoice_item, job_id, item): item
                for item in items
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_item):
                result = future.result()

                if result['status'] == 'completed':
                    successful_count += 1
                else:
                    failed_count += 1

                processed_count += 1

                # Update job progress after each completed item
                update_job_progress(job_id,
                                  processed_items=processed_count,
                                  successful_items=successful_count,
                                  failed_items=failed_count)

                progress = (processed_count / len(items)) * 100
                print(f"[STATS] Progress: {processed_count}/{len(items)} ({progress:.1f}%) - [OK]{successful_count} [ERROR]{failed_count}")

        # Mark job as completed
        final_status = 'completed' if failed_count == 0 else 'completed_with_errors'
        update_job_progress(job_id, status=final_status,
                          processed_items=processed_count,
                          successful_items=successful_count,
                          failed_items=failed_count)

        print(f"[COMPLETE] Job {job_id} finished: {successful_count} successful, {failed_count} failed")

    except Exception as e:
        error_msg = f"Job processing error: {str(e)}"
        print(f"[ERROR] Job {job_id} failed: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")

        update_job_progress(job_id, status='failed', error_message=error_msg)

def start_background_job(job_id: str, job_type: str = 'invoice_batch'):
    """Start a background job in a separate thread"""
    if job_type == 'invoice_batch':
        worker_thread = threading.Thread(
            target=process_invoice_batch_job,
            args=(job_id,),
            name=f"JobWorker-{job_id[:8]}",
            daemon=True  # Thread will not prevent program exit
        )
        worker_thread.start()
        print(f"🔥 Started background worker thread for job {job_id}")
        return True
    else:
        print(f"[ERROR] Unknown job type: {job_type}")
        return False

def get_db_connection():
    """Get database connection using the centralized database manager"""
    try:
        from database import db_manager
        # Return a connection context - this will be used in a 'with' statement
        return db_manager.get_connection()
    except Exception as e:
        print(f"[ERROR] Failed to get database connection: {e}")
        raise

def load_transactions_from_db(filters=None, page=1, per_page=50):
    """Load transactions from database with filtering and pagination"""
    # Temporarily removed try/except to see actual error
    from database import db_manager

    # Use the exact same pattern as get_dashboard_stats function
    with db_manager.get_connection() as conn:
        if db_manager.db_type == 'postgresql':
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cursor = conn.cursor()

        is_postgresql = db_manager.db_type == 'postgresql'

        # Simple test - get total count without archived filter first
        cursor.execute("SELECT COUNT(*) as total FROM transactions")
        count_result = cursor.fetchone()
        total_without_filter = count_result['total'] if is_postgresql else count_result[0]

        # Now get count with archived filter (same as stats API)
        cursor.execute("SELECT COUNT(*) as total FROM transactions WHERE (archived = FALSE OR archived IS NULL)")
        count_result = cursor.fetchone()
        total_count = count_result['total'] if is_postgresql else count_result[0]

        # For debugging: return both counts in a way we can see
        if total_without_filter == 0:
            return [], 0  # No transactions at all

        if total_count == 0:
            # All transactions are archived, but let's return some for testing
            cursor.execute("SELECT * FROM transactions LIMIT 3")
            results = cursor.fetchall()
            test_transactions = []
            for row in results:
                if is_postgresql:
                    transaction = dict(row)
                else:
                    transaction = dict(row)
                test_transactions.append(transaction)
            return test_transactions, total_without_filter

        # Normal path - get transactions with archived filter
        offset = (page - 1) * per_page if page > 0 else 0
        query = f"SELECT * FROM transactions WHERE (archived = FALSE OR archived IS NULL) ORDER BY date DESC LIMIT {per_page} OFFSET {offset}"
        cursor.execute(query)

        results = cursor.fetchall()
        transactions = []

        for row in results:
            if is_postgresql:
                transaction = dict(row)
            else:
                transaction = dict(row)
            transactions.append(transaction)

        return transactions, total_count

def get_dashboard_stats():
    """Calculate dashboard statistics from database"""
    try:
        from database import db_manager

        # Use the robust database manager instead of old get_db_connection
        with db_manager.get_connection() as conn:
            if db_manager.db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cursor = conn.cursor()

            # Detect database type for compatible syntax
            is_postgresql = db_manager.db_type == 'postgresql'

            # Total transactions (exclude archived to match /api/transactions behavior)
            cursor.execute("SELECT COUNT(*) as total FROM transactions WHERE (archived = FALSE OR archived IS NULL)")
            result = cursor.fetchone()
            total_transactions = result['total'] if is_postgresql else result[0]

            # Revenue and expenses (exclude archived)
            cursor.execute("SELECT COALESCE(SUM(amount), 0) as revenue FROM transactions WHERE amount > 0 AND (archived = FALSE OR archived IS NULL)")
            result = cursor.fetchone()
            revenue = result['revenue'] if is_postgresql else result[0]

            cursor.execute("SELECT COALESCE(SUM(ABS(amount)), 0) as expenses FROM transactions WHERE amount < 0 AND (archived = FALSE OR archived IS NULL)")
            result = cursor.fetchone()
            expenses = result['expenses'] if is_postgresql else result[0]

            # Needs review (exclude archived)
            cursor.execute("SELECT COUNT(*) as needs_review FROM transactions WHERE (confidence < 0.8 OR confidence IS NULL) AND (archived = FALSE OR archived IS NULL)")
            result = cursor.fetchone()
            needs_review = result['needs_review'] if is_postgresql else result[0]

            # Date range (exclude archived)
            cursor.execute("SELECT MIN(date) as min_date, MAX(date) as max_date FROM transactions WHERE (archived = FALSE OR archived IS NULL)")
            date_range_result = cursor.fetchone()
            if is_postgresql:
                date_range = {
                    'min': date_range_result['min_date'] or 'N/A',
                    'max': date_range_result['max_date'] or 'N/A'
                }
            else:
                date_range = {
                    'min': date_range_result[0] or 'N/A',
                    'max': date_range_result[1] or 'N/A'
                }

            # Top entities (exclude archived)
            cursor.execute("""
                SELECT classified_entity, COUNT(*) as count
                FROM transactions
                WHERE classified_entity IS NOT NULL
                AND (archived = FALSE OR archived IS NULL)
                GROUP BY classified_entity
                ORDER BY count DESC
                LIMIT 10
            """)
            entities = cursor.fetchall()

            # Top source files (exclude archived)
            cursor.execute("""
                SELECT source_file, COUNT(*) as count
                FROM transactions
                WHERE source_file IS NOT NULL
                AND (archived = FALSE OR archived IS NULL)
                GROUP BY source_file
                ORDER BY count DESC
                LIMIT 10
            """)
            source_files = cursor.fetchall()

            cursor.close()

        return {
            'total_transactions': total_transactions,
            'total_revenue': float(revenue),
            'total_expenses': float(expenses),
            'needs_review': needs_review,
            'date_range': date_range,
            'entities': [(row['classified_entity'], row['count']) if is_postgresql else (row[0], row[1]) for row in entities],
            'source_files': [(row['source_file'], row['count']) if is_postgresql else (row[0], row[1]) for row in source_files]
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
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Detect database type for compatible syntax
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            # Get current value for history
            cursor.execute(
                f"SELECT * FROM transactions WHERE transaction_id = {placeholder}",
                (transaction_id,)
            )
            current_row = cursor.fetchone()

            if not current_row:
                return False

            # Handle both RealDictCursor (PostgreSQL) and Row (SQLite)
            current_dict = dict(current_row) if current_row else {}
            current_value = current_dict.get(field) if field in current_dict else None

            # Update the field
            update_query = f"UPDATE transactions SET {field} = {placeholder} WHERE transaction_id = {placeholder}"
            cursor.execute(update_query, (value, transaction_id))

            # CRITICAL: Commit the UPDATE immediately to ensure it persists
            # In PostgreSQL, if a later query fails, it can rollback the entire transaction
            conn.commit()

            print(f"UPDATING: Updated transaction {transaction_id}: field={field}, value={value}")

            # Record change in history (only if table exists)
            # This is done in a separate transaction so failures don't affect the main update
            try:
                # The transaction_history table uses old_values/new_values as JSONB
                old_values_json = {field: current_value} if current_value is not None else {}
                new_values_json = {field: value}

                cursor.execute(f"""
                    INSERT INTO transaction_history (transaction_id, old_values, new_values, changed_by)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                """, (transaction_id, json.dumps(old_values_json), json.dumps(new_values_json), user))
                conn.commit()
            except Exception as history_error:
                print(f"INFO: Could not record history: {history_error}")
                # Rollback only affects the history insert, main update already committed
                try:
                    conn.rollback()
                except:
                    pass

            return True

    except Exception as e:
        print(f"ERROR: Error updating transaction field: {e}")
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        return False

def extract_entity_patterns_with_llm(transaction_id: str, entity_name: str, description: str, claude_client) -> Dict:
    """
    Use Claude to extract identifying patterns from a transaction description when user classifies it to an entity.
    This implements the pure LLM pattern learning approach.
    """
    try:
        if not claude_client or not description or not entity_name:
            return {}

        prompt = f"""
Analyze this transaction description and extract the key identifying patterns that uniquely identify the entity "{entity_name}".

TRANSACTION DESCRIPTION:
"{description}"

ENTITY CLASSIFIED TO: "{entity_name}"

Extract and return the following identifying patterns in JSON format:

1. **company_names**: List of company/organization names mentioned (full names, abbreviations, variations)
2. **originator_patterns**: Payment processor identifiers like "ORIG CO NAME:", "B/O:", "IND NAME:", etc.
3. **bank_identifiers**: Bank names, routing info, or financial institution identifiers
4. **transaction_keywords**: Specific keywords that repeatedly appear in transactions from this entity
5. **reference_patterns**: Invoice numbers, account numbers, or reference ID patterns
6. **payment_method_type**: Type of transaction (WIRE, ACH, FEDWIRE, CHIPS, etc.)

IMPORTANT: Extract patterns that are SPECIFIC to this entity and would help identify future transactions from the same entity, not generic patterns.

Example output format:
{{
  "company_names": ["EVERMINER LLC", "EVERMINER"],
  "originator_patterns": ["B/O: EVERMINER LLC"],
  "bank_identifiers": ["CHOICE FINANCIAL GROUP/091311229"],
  "transaction_keywords": ["hosting", "invoice"],
  "reference_patterns": ["INVOICE \\\\d{{3}}-\\\\d{{3}}-\\\\d{{6}}"],
  "payment_method_type": "FEDWIRE"
}}

Return only the JSON object, no additional text.
"""

        print(f"DEBUG: Extracting entity patterns for {entity_name} from transaction {transaction_id}")

        response = claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()
        print(f"DEBUG: Claude pattern extraction response: {response_text[:200]}...")

        # Parse JSON response
        pattern_data = json.loads(response_text)

        # Store patterns in database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            cursor.execute(f"""
                INSERT INTO entity_patterns (entity_name, pattern_data, transaction_id, confidence_score)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
            """, (entity_name, json.dumps(pattern_data), transaction_id, 1.0))

            conn.commit()

        print(f"SUCCESS: Stored entity patterns for {entity_name}: {pattern_data}")
        return pattern_data

    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse Claude response as JSON: {e}")
        print(f"ERROR: Response was: {response_text}")
        return {}
    except Exception as e:
        print(f"ERROR: Failed to extract entity patterns: {e}")
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        return {}

def get_claude_analyzed_similar_descriptions(context: Dict, claude_client) -> List[str]:
    """Use Claude to intelligently analyze which transactions should have similar descriptions/entities"""
    try:
        if not claude_client or not context:
            return []

        transaction_id = context.get('transaction_id')
        new_value = context.get('value', '')
        field_type = context.get('field_type', '')  # 'similar_descriptions' or 'similar_entities'

        if not transaction_id or not new_value:
            return []

        with get_db_connection() as conn:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            # Get the current transaction
            cursor.execute(
                f"SELECT description, classified_entity FROM transactions WHERE transaction_id = {placeholder}",
                (transaction_id,)
            )
            current_tx = cursor.fetchone()

            if not current_tx:
                return []

            # Safe extraction of description and entity from current_tx
            try:
                if is_postgresql:
                    current_description = current_tx.get('description', '') if isinstance(current_tx, dict) else (current_tx[0] if len(current_tx) > 0 else '')
                    current_entity = current_tx.get('classified_entity', '') if isinstance(current_tx, dict) else (current_tx[1] if len(current_tx) > 1 else '')
                else:
                    current_description = current_tx[0] if len(current_tx) > 0 else ''
                    current_entity = current_tx[1] if len(current_tx) > 1 else ''
            except Exception as e:
                print(f"ERROR: Failed to extract description/entity from current_tx: {e}, type={type(current_tx)}, len={len(current_tx) if hasattr(current_tx, '__len__') else 'N/A'}")
                return []

            # Different logic for entity classification vs description cleanup vs accounting category
            if field_type == 'similar_entities':
                # For entity classification: Use learned patterns to pre-filter candidates
                print(f"DEBUG: Searching for similar entities - current entity: {current_entity}, new entity: {new_value}")

                # First, fetch learned patterns for this entity to build SQL filters
                pattern_conditions = []
                params = []  # Initialize params list for SQL query
                try:
                    pattern_conn = get_db_connection()
                    pattern_cursor = pattern_conn.cursor()
                    pattern_placeholder_temp = '%s' if hasattr(pattern_cursor, 'mogrify') else '?'

                    pattern_cursor.execute(f"""
                        SELECT pattern_data
                        FROM entity_patterns
                        WHERE entity_name = {pattern_placeholder_temp}
                        ORDER BY created_at DESC
                        LIMIT 5
                    """, (new_value,))

                    learned_patterns_rows = pattern_cursor.fetchall()
                    pattern_conn.close()

                    if learned_patterns_rows and len(learned_patterns_rows) > 0:
                        print(f"DEBUG: Found {len(learned_patterns_rows)} learned patterns for {new_value}, building SQL filters...")
                        # Extract all company names, keywords, and bank identifiers from patterns
                        all_company_names = set()
                        all_keywords = set()
                        all_bank_ids = set()

                        for pattern_row in learned_patterns_rows:
                            pattern_data = pattern_row.get('pattern_data', '{}') if isinstance(pattern_row, dict) else pattern_row[0]
                            if isinstance(pattern_data, str):
                                pattern_data = json.loads(pattern_data)

                            all_company_names.update(pattern_data.get('company_names', []))
                            all_keywords.update(pattern_data.get('transaction_keywords', []))
                            all_bank_ids.update(pattern_data.get('bank_identifiers', []))

                        # Build ILIKE conditions for each pattern element
                        for company in all_company_names:
                            if company:  # Skip empty strings
                                pattern_conditions.append(f"description ILIKE {placeholder}")
                                params.append(f"%{company}%")

                        for keyword in all_keywords:
                            if keyword and len(keyword) > 3:  # Skip short/generic keywords
                                pattern_conditions.append(f"description ILIKE {placeholder}")
                                params.append(f"%{keyword}%")

                        for bank_id in all_bank_ids:
                            if bank_id:
                                pattern_conditions.append(f"description ILIKE {placeholder}")
                                params.append(f"%{bank_id}%")

                        print(f"DEBUG: Built {len(pattern_conditions)} SQL pattern filters")
                except Exception as pattern_error:
                    print(f"WARNING: Failed to build pattern filters: {pattern_error}")

                # Build the query with pattern-based filtering if we have patterns
                if pattern_conditions:
                    # Use learned patterns to pre-filter candidates
                    pattern_filter = " OR ".join(pattern_conditions)
                    base_query = f"""
                        SELECT transaction_id, date, description, confidence, classified_entity, amount
                        FROM transactions
                        WHERE transaction_id != {placeholder}
                        AND (classified_entity = 'NEEDS REVIEW' OR classified_entity = 'Unclassified Expense' OR classified_entity = 'Unclassified Revenue' OR classified_entity IS NULL)
                        AND ({pattern_filter})
                        LIMIT 30
                    """
                    params = [transaction_id] + params
                    print(f"DEBUG: Using pattern-based pre-filtering with {len(pattern_conditions)} conditions")
                else:
                    # No patterns learned yet - use basic similarity based on current transaction description
                    print(f"DEBUG: No patterns found, using description-based filtering as fallback")
                    # Extract key terms from current description for basic filtering
                    desc_words = [w.strip() for w in current_description.upper().split() if len(w.strip()) > 4]
                    desc_conditions = []
                    for word in desc_words[:5]:  # Use top 5 longest words
                        if word and not word.isdigit():
                            desc_conditions.append(f"UPPER(description) LIKE {placeholder}")
                            params.append(f"%{word}%")

                    if desc_conditions:
                        desc_filter = " OR ".join(desc_conditions)
                        base_query = f"""
                            SELECT transaction_id, date, description, confidence, classified_entity, amount
                            FROM transactions
                            WHERE transaction_id != {placeholder}
                            AND (classified_entity = 'NEEDS REVIEW' OR classified_entity = 'Unclassified Expense' OR classified_entity = 'Unclassified Revenue' OR classified_entity IS NULL)
                            AND ({desc_filter})
                            LIMIT 30
                        """
                        params = [transaction_id] + params
                    else:
                        # Ultimate fallback - just grab unclassified transactions
                        base_query = f"""
                            SELECT transaction_id, date, description, confidence, classified_entity, amount
                            FROM transactions
                            WHERE transaction_id != {placeholder}
                            AND (classified_entity = 'NEEDS REVIEW' OR classified_entity = 'Unclassified Expense' OR classified_entity = 'Unclassified Revenue' OR classified_entity IS NULL)
                            LIMIT 50
                        """
                        params = [transaction_id]
            elif field_type == 'similar_accounting':
                # For accounting category: find transactions from same entity that need review
                # Include: uncategorized, low confidence, OR different category (to suggest recategorization)
                print(f"DEBUG: Searching for similar accounting categories - entity: {current_entity}, new category: {new_value}")

                base_query = f"""
                    SELECT transaction_id, date, description, amount, accounting_category
                    FROM transactions
                    WHERE transaction_id != {placeholder}
                    AND classified_entity = {placeholder}
                    AND (
                        accounting_category IS NULL
                        OR accounting_category = 'N/A'
                        OR confidence < 0.7
                        OR (accounting_category != {placeholder} AND accounting_category IS NOT NULL)
                    )
                    LIMIT 30
                """
                params = [transaction_id, current_entity, new_value]
            else:
                # For description cleanup: find transactions with same entity but different descriptions
                # Since the description has already been updated, we search by entity
                print(f"DEBUG: Searching for similar descriptions - entity: {current_entity}, new description: {new_value}")

                base_query = f"""
                    SELECT transaction_id, date, description, confidence
                    FROM transactions
                    WHERE transaction_id != {placeholder}
                    AND classified_entity = {placeholder}
                    AND description != {placeholder}
                    LIMIT 20
                """
                params = [transaction_id, current_entity, new_value]

            cursor.execute(base_query, tuple(params))
        candidate_txs = cursor.fetchall()

        conn.close()

        if not candidate_txs:
            print(f"DEBUG: No candidate transactions found")
            return []

        print(f"DEBUG: Found {len(candidate_txs)} candidate transactions")

        # Use Claude to analyze which transactions are truly similar
        candidate_descriptions = []
        for i, tx in enumerate(candidate_txs):
            try:
                if is_postgresql:
                    desc = tx.get('description', '') if isinstance(tx, dict) else str(tx[2] if len(tx) > 2 else '')
                    if field_type == 'similar_accounting':
                        amount = tx.get('amount', '') if isinstance(tx, dict) else str(tx[3] if len(tx) > 3 else '')
                        current_cat = tx.get('accounting_category', 'N/A') if isinstance(tx, dict) else str(tx[4] if len(tx) > 4 else 'N/A')
                else:
                    desc = tx[2] if len(tx) > 2 else ''
                    if field_type == 'similar_accounting':
                        amount = tx[3] if len(tx) > 3 else ''
                        tx_type = tx[5] if len(tx) > 5 else ''
                        current_cat = tx[4] if len(tx) > 4 else 'N/A'

                desc_text = f"{desc[:100]}..." if len(desc) > 100 else desc

                if field_type == 'similar_accounting':
                    # Determine direction from amount
                    direction = "DEBIT/Expense" if float(amount) < 0 else "CREDIT/Revenue" if float(amount) > 0 else "Zero"
                    candidate_descriptions.append(
                        f"Transaction {i+1}: {desc_text} | Direction: {direction} | Amount: ${amount} | Current Category: {current_cat}"
                    )
                else:
                    candidate_descriptions.append(f"Transaction {i+1}: {desc_text}")
            except Exception as e:
                print(f"ERROR: Failed to process candidate tx {i}: {e}")
                candidate_descriptions.append(f"Transaction {i+1}: [Error loading description]")

        # Different prompts for entity classification vs description cleanup vs accounting category
        if field_type == 'similar_entities':
            current_tx_type = context.get('type', '')
            current_source = context.get('source_file', '')

            # Fetch learned patterns for this entity from database
            learned_patterns_text = "No patterns learned yet for this entity."
            try:
                pattern_conn = get_db_connection()
                pattern_cursor = pattern_conn.cursor()
                pattern_placeholder = '%s' if hasattr(pattern_cursor, 'mogrify') else '?'

                pattern_cursor.execute(f"""
                    SELECT pattern_data, confidence_score
                    FROM entity_patterns
                    WHERE entity_name = {pattern_placeholder}
                    ORDER BY created_at DESC
                    LIMIT 10
                """, (new_value,))

                learned_patterns = pattern_cursor.fetchall()
                pattern_conn.close()

                if learned_patterns and len(learned_patterns) > 0:
                    learned_patterns_text = "LEARNED PATTERNS FOR THIS ENTITY:\n"
                    for i, pattern_row in enumerate(learned_patterns):
                        pattern_data = pattern_row.get('pattern_data', '{}') if isinstance(pattern_row, dict) else pattern_row[0]
                        if isinstance(pattern_data, str):
                            pattern_data = json.loads(pattern_data)

                        learned_patterns_text += f"\nPattern {i+1}:\n"
                        learned_patterns_text += f"  - Company names: {', '.join(pattern_data.get('company_names', []))}\n"
                        learned_patterns_text += f"  - Originator patterns: {', '.join(pattern_data.get('originator_patterns', []))}\n"
                        learned_patterns_text += f"  - Bank identifiers: {', '.join(pattern_data.get('bank_identifiers', []))}\n"
                        learned_patterns_text += f"  - Keywords: {', '.join(pattern_data.get('transaction_keywords', []))}\n"
                        learned_patterns_text += f"  - Payment method: {pattern_data.get('payment_method_type', 'N/A')}\n"

                    # Store in context for API response
                    context['has_learned_patterns'] = True
            except Exception as pattern_error:
                print(f"WARNING: Failed to fetch learned patterns: {pattern_error}")

            prompt = f"""
            Analyze these unclassified transactions and determine which ones belong to the same business entity as the current transaction.

            CURRENT TRANSACTION:
            - Description: "{current_description}"
            - Type: {current_tx_type}
            - NEW Entity Classification: "{new_value}"
            - Source File: {current_source}

            {learned_patterns_text}

            UNCLASSIFIED CANDIDATE TRANSACTIONS:
            {chr(10).join(candidate_descriptions)}

            MATCHING INSTRUCTIONS:
            1. Use the learned patterns above as your PRIMARY matching criteria
            2. Look for transactions that match the company names, originator patterns, bank identifiers, or payment methods from the learned patterns
            3. If no patterns are learned yet, use intelligent matching based on:
               - Same company/business name (including abbreviations and variations)
               - Same payment processor/originator ("ORIG CO NAME", "B/O", "IND NAME")
               - Same bank/financial institution
               - Consistent business activity patterns
            4. Be SPECIFIC with payment processors - "PAYPAL ABC COMPANY" is different from "PAYPAL XYZ COMPANY"
            5. Be conservative: When in doubt, don't match - false negatives are better than false positives

            Response format: Just the numbers separated by commas (e.g., "1, 3, 7") or "none" if no transactions match.
            """
        elif field_type == 'similar_accounting':
            # Get current transaction type and direction for context
            current_tx_type = context.get('type', '')
            current_amount = float(context.get('amount', 0))
            current_direction = "DEBIT/Expense" if current_amount < 0 else "CREDIT/Revenue" if current_amount > 0 else "Zero"
            current_source = context.get('source_file', '')

            prompt = f"""
            Analyze these transactions and determine which ones should have the same accounting category as the current transaction.

            CURRENT TRANSACTION:
            - Description: "{current_description}"
            - Type: {current_tx_type}
            - Direction: {current_direction}
            - Amount: ${current_amount}
            - NEW Accounting Category: "{new_value}"
            - Entity: {current_entity}
            - Source File: {current_source}

            CANDIDATE TRANSACTIONS FROM SAME ENTITY:
            {chr(10).join(candidate_descriptions)}

            MATCHING CRITERIA - Consider these factors:
            1. **Transaction Purpose**: What is the transaction for? (hosting, trading income, bank fees, power bills, etc.)
            2. **Transaction Flow**: DEBIT (expense/outgoing) vs CREDIT (revenue/incoming) - must match current transaction
            3. **Transaction Type**: Wire transfer, ACH, credit card merchant, etc.
            4. **Business Function**: Same business activity or cost center
            5. **Recategorization**: If a transaction has a DIFFERENT category but appears to be the SAME type as current, include it (it may be miscategorized)

            IMPORTANT RULES:
            - Expenses and revenues are NEVER the same category
            - A $15 bank fee and a $3000 wire transfer are DIFFERENT (fee vs transfer)
            - Two hosting payments from same provider ARE the same (even if different amounts)
            - Ignore amount - focus on transaction nature and purpose
            - Include transactions with wrong categories if they match the current transaction's purpose

            Response format: Just the numbers separated by commas (e.g., "1, 3, 7") or "none" if no transactions match.
            """
        else:
            prompt = f"""
            Analyze these transaction descriptions from the same entity/business unit and determine which ones should have the same cleaned description.

            Current transaction has been updated to: "{new_value}"
            Entity: {current_entity}

            Other transactions from the same entity:
            {chr(10).join(candidate_descriptions)}

            Respond with ONLY the transaction numbers (1, 2, 3, etc.) that appear to be the same type of transaction and should use the clean description "{new_value}".
            Look for transactions that seem to be from the same source/purpose, even if the descriptions are messy.

            Response format: Just the numbers separated by commas (e.g., "1, 3, 7") or "none" if no transactions are similar enough.
            """

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
        print(f"DEBUG: Claude response for similar entities: {response_text}")

        if response_text == "none" or not response_text:
            return []

        # Parse Claude's response to get selected transaction indices
        # Claude may respond in different formats:
        # 1. "1, 2, 3" (comma separated)
        # 2. "transaction 1\ntransaction 2" (line separated with "transaction" prefix)
        # 3. "1\n2\n3" (line separated numbers)
        # 4. "based on... 1, 3, 7... explanation" (mixed with explanatory text)
        try:
            selected_indices = []

            # First try: Extract all numbers from the response (handles all formats)
            import re
            numbers = re.findall(r'\b\d+\b', response_text)
            for num_str in numbers:
                try:
                    num = int(num_str)
                    # Only include numbers that are valid transaction indices (1-based)
                    if 1 <= num <= len(candidate_txs):
                        selected_indices.append(num - 1)  # Convert to 0-based
                except ValueError:
                    continue

            selected_txs = [candidate_txs[i] for i in selected_indices if 0 <= i < len(candidate_txs)]

            # Return formatted transaction data
            result = []
            for tx in selected_txs:
                try:
                    if is_postgresql and isinstance(tx, dict):
                        tx_id = tx.get('transaction_id', '')
                        date = tx.get('date', '')
                        desc = tx.get('description', '')
                        conf = tx.get('confidence', 'N/A')
                        amount = tx.get('amount', 0)
                        entity = tx.get('classified_entity', '')
                        acct_cat = tx.get('accounting_category', 'N/A')
                    else:
                        tx_id = tx[0] if len(tx) > 0 else ''
                        date = tx[1] if len(tx) > 1 else ''
                        desc = tx[2] if len(tx) > 2 else ''
                        conf = tx[3] if len(tx) > 3 else 'N/A'
                        # For entity suggestions: amount is at index 5
                        # For accounting suggestions: amount is at index 3
                        # For description suggestions: no amount field
                        if field_type == 'similar_entities':
                            entity = tx[4] if len(tx) > 4 else ''
                            amount = tx[5] if len(tx) > 5 else 0
                            acct_cat = 'N/A'
                        elif field_type == 'similar_accounting':
                            entity = current_entity
                            amount = tx[3] if len(tx) > 3 else 0
                            acct_cat = tx[4] if len(tx) > 4 else 'N/A'
                        else:
                            entity = current_entity
                            amount = 0
                            acct_cat = 'N/A'

                    result.append({
                        'transaction_id': tx_id,
                        'date': date,
                        'description': desc[:80] + "..." if len(desc) > 80 else desc,
                        'confidence': conf or 'N/A',
                        'amount': amount,
                        'classified_entity': entity,
                        'accounting_category': acct_cat
                    })
                except Exception as e:
                    print(f"ERROR: Failed to format transaction: {e}")

            print(f"DEBUG: Returning {len(result)} similar transactions")
            return result

        except (ValueError, IndexError) as e:
            print(f"ERROR: Error parsing Claude response for similar descriptions: {e}")
            return []

    except Exception as e:
        import traceback
        print(f"ERROR: Error in Claude analysis of similar descriptions: {e}")
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
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
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        # Find the current transaction to get its original description
        cursor.execute(
            f"SELECT description, classified_entity FROM transactions WHERE transaction_id = {placeholder}",
            (transaction_id,)
        )
        current_tx = cursor.fetchone()

        if not current_tx:
            conn.close()
            return []

        if is_postgresql:
            original_description = current_tx['description']
            entity = current_tx['classified_entity']
        else:
            original_description = current_tx[0]
            entity = current_tx[1]

        # Find transactions with similar patterns - return full transaction data
        cursor.execute(f"""
            SELECT transaction_id, date, description, confidence
            FROM transactions
            WHERE transaction_id != {placeholder}
            AND (
                -- Same entity with similar description pattern
                (classified_entity = {placeholder} AND description LIKE {placeholder}) OR
                -- Contains similar keywords for CIBC/Toronto wire transfers
                (description LIKE '%CIBC%' AND {placeholder} LIKE '%CIBC%') OR
                (description LIKE '%TORONTO%' AND {placeholder} LIKE '%TORONTO%') OR
                (description LIKE '%WIRE%' AND {placeholder} LIKE '%WIRE%') OR
                (description LIKE '%FEDWIRE%' AND {placeholder} LIKE '%FEDWIRE%')
            )
            AND description != {placeholder}
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
        ))
        similar_txs = cursor.fetchall()

        conn.close()

        # Return full transaction data for the improved UI
        if is_postgresql:
            return [{
                'transaction_id': row['transaction_id'],
                'date': row['date'],
                'description': row['description'][:80] + "..." if len(row['description']) > 80 else row['description'],
                'confidence': row['confidence'] or 'N/A'
            } for row in similar_txs]
        else:
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

        # Special handling for similar_descriptions, similar_entities, and similar_accounting - use Claude to analyze similar transactions
        if field_type in ['similar_descriptions', 'similar_entities', 'similar_accounting']:
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

        # Parse Claude response and filter out introduction/instruction text
        raw_lines = [line.strip() for line in response.content[0].text.strip().split('\n') if line.strip()]

        # Filter out lines that are clearly instructions or headers (containing "based on", "here are", etc.)
        ai_suggestions = []
        for line in raw_lines:
            lower_line = line.lower()
            # Skip lines that are instructions/headers
            if any(phrase in lower_line for phrase in ['here are', 'based on', 'provided transaction', 'clean merchant', 'provider', 'entity names']):
                continue
            # Skip lines that end with colon (likely headers)
            if line.endswith(':'):
                continue
            ai_suggestions.append(line)

        print(f"AI: Claude suggestions (filtered): {ai_suggestions}")

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
    print(f"🔧 DEBUG: Starting sync_csv_to_database for {csv_filename}")
    try:
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        print(f"🔧 DEBUG: Parent directory: {parent_dir}")

        if csv_filename:
            # Sync specific classified file
            csv_path = os.path.join(parent_dir, 'classified_transactions', f'classified_{csv_filename}')
            print(f"🔧 DEBUG: Looking for classified file: {csv_path}")
        else:
            # Try to sync MASTER_TRANSACTIONS.csv if it exists
            csv_path = os.path.join(parent_dir, 'MASTER_TRANSACTIONS.csv')
            print(f"🔧 DEBUG: Looking for MASTER_TRANSACTIONS.csv: {csv_path}")

        # Check if classified_transactions directory exists
        classified_dir = os.path.join(parent_dir, 'classified_transactions')
        print(f"🔧 DEBUG: Classified directory exists: {os.path.exists(classified_dir)}")
        if os.path.exists(classified_dir):
            files_in_dir = os.listdir(classified_dir)
            print(f"🔧 DEBUG: Files in classified_transactions: {files_in_dir}")

        if not os.path.exists(csv_path):
            print(f"WARNING: CSV file not found for sync: {csv_path}")

            # Try alternative paths and files
            alternative_paths = [
                os.path.join(parent_dir, f'classified_{csv_filename}'),  # Root directory
                os.path.join(parent_dir, 'web_ui', 'classified_transactions', f'classified_{csv_filename}'),  # web_ui subfolder
                os.path.join(parent_dir, csv_filename),  # Original filename without classified_ prefix
            ] if csv_filename else []

            for alt_path in alternative_paths:
                print(f"🔧 DEBUG: Trying alternative path: {alt_path}")
                if os.path.exists(alt_path):
                    csv_path = alt_path
                    print(f"[OK] DEBUG: Found file at alternative path: {alt_path}")
                    break
            else:
                print(f"[ERROR] DEBUG: No alternative paths found")
                return False

        # Read the CSV file
        df = pd.read_csv(csv_path)
        print(f"UPDATING: Syncing {len(df)} transactions to database...")

        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Detect database type for compatible syntax
        is_postgresql = hasattr(cursor, 'mogrify')  # PostgreSQL-specific method
        placeholder = '%s' if is_postgresql else '?'

        # For specific file uploads, only clear data from that source file
        if csv_filename:
            source_file = csv_filename.replace('classified_', '')
            if is_postgresql:
                cursor.execute("DELETE FROM transactions WHERE source_file = %s", (source_file,))
            else:
                cursor.execute("DELETE FROM transactions WHERE source_file = ?", (source_file,))
            print(f"DATABASE: Cleared existing data for source file: {source_file}")
        else:
            # Only clear all data if syncing MASTER_TRANSACTIONS.csv (full sync)
            cursor.execute("DELETE FROM transactions")
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

            # Insert transaction (database-specific syntax for handling duplicates)
            if is_postgresql:
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_id, date, description, amount, currency, usd_equivalent,
                        classified_entity, justification, confidence, classification_reason,
                        origin, destination, identifier, source_file, crypto_amount, conversion_note
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (transaction_id) DO UPDATE SET
                        date = EXCLUDED.date,
                        description = EXCLUDED.description,
                        amount = EXCLUDED.amount,
                        currency = EXCLUDED.currency,
                        usd_equivalent = EXCLUDED.usd_equivalent,
                        classified_entity = EXCLUDED.classified_entity,
                        justification = EXCLUDED.justification,
                        confidence = EXCLUDED.confidence,
                        classification_reason = EXCLUDED.classification_reason,
                        origin = EXCLUDED.origin,
                        destination = EXCLUDED.destination,
                        identifier = EXCLUDED.identifier,
                        source_file = EXCLUDED.source_file,
                        crypto_amount = EXCLUDED.crypto_amount,
                        conversion_note = EXCLUDED.conversion_note
                """, (
                    data['transaction_id'], data['date'], data['description'],
                    data['amount'], data['currency'], data['usd_equivalent'],
                    data['classified_entity'], data['justification'], data['confidence'],
                    data['classification_reason'], data['origin'], data['destination'],
                    data['identifier'], data['source_file'], data['crypto_amount'], data['conversion_note']
                ))
            else:
                cursor.execute("""
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
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        return False

@app.route('/')
def homepage():
    """Business overview homepage"""
    try:
        cache_buster = str(random.randint(1000, 9999))
        return render_template('business_overview.html', cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading homepage: {str(e)}", 500

@app.route('/health')
def health_check():
    """Health check endpoint that returns database type and status"""
    try:
        db_type = os.getenv('DB_TYPE', 'sqlite').lower()

        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Detect which database we're actually using
        try:
            if hasattr(cursor, 'mogrify'):  # PostgreSQL cursor has mogrify
                cursor.execute("SELECT version()")
                db_info = "PostgreSQL"
            else:
                cursor.execute("SELECT sqlite_version()")
                db_info = "SQLite"
        except:
            # Fallback detection
            try:
                cursor.execute("SELECT sqlite_version()")
                db_info = "SQLite"
            except:
                cursor.execute("SELECT version()")
                db_info = "PostgreSQL"

        conn.close()

        return jsonify({
            "status": "healthy",
            "database": db_info,
            "db_type_env": db_type,
            "postgresql_available": POSTGRESQL_AVAILABLE,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0"
        }), 200

    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/debug')
def debug_db():
    """Debug endpoint to show database connection details"""
    try:
        debug_info = {
            "environment_vars": {
                "DB_TYPE": os.getenv('DB_TYPE', 'not_set'),
                "DB_HOST": os.getenv('DB_HOST', 'not_set'),
                "DB_PORT": os.getenv('DB_PORT', 'not_set'),
                "DB_NAME": os.getenv('DB_NAME', 'not_set'),
                "DB_USER": os.getenv('DB_USER', 'not_set'),
                "DB_PASSWORD": "***" if os.getenv('DB_PASSWORD') else "not_set",
                "DB_SOCKET_PATH": os.getenv('DB_SOCKET_PATH', 'not_set'),
                "FLASK_ENV": os.getenv('FLASK_ENV', 'not_set'),
            },
            "postgresql_available": POSTGRESQL_AVAILABLE,
            "connection_attempt": None
        }

        # Try PostgreSQL connection manually
        if POSTGRESQL_AVAILABLE and os.getenv('DB_TYPE', '').lower() == 'postgresql':
            try:
                socket_path = os.getenv('DB_SOCKET_PATH')
                if socket_path:
                    conn = psycopg2.connect(
                        host=socket_path,
                        database=os.getenv('DB_NAME', 'delta_cfo'),
                        user=os.getenv('DB_USER', 'delta_user'),
                        password=os.getenv('DB_PASSWORD')
                    )
                    debug_info["connection_attempt"] = "success_socket"
                else:
                    conn = psycopg2.connect(
                        host=os.getenv('DB_HOST', '34.39.143.82'),
                        port=os.getenv('DB_PORT', '5432'),
                        database=os.getenv('DB_NAME', 'delta_cfo'),
                        user=os.getenv('DB_USER', 'delta_user'),
                        password=os.getenv('DB_PASSWORD')
                    )
                    debug_info["connection_attempt"] = "success_tcp"
                conn.close()
            except Exception as e:
                debug_info["connection_attempt"] = f"failed: {str(e)}"

        return jsonify(debug_info), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
            'keyword': request.args.get('keyword'),
            'show_archived': request.args.get('show_archived')
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v}

        # Pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        print(f"API: About to call load_transactions_from_db with filters={filters}")
        transactions, total_count = load_transactions_from_db(filters, page, per_page)
        print(f"API: Got result - transactions count={len(transactions)}, total_count={total_count}")

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

@app.route('/api/test_transactions')
def api_test_transactions():
    """Simple test endpoint to debug transaction retrieval"""
    try:
        from database import db_manager

        # Direct database query like get_dashboard_stats
        with db_manager.get_connection() as conn:
            if db_manager.db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cursor = conn.cursor()

            is_postgresql = db_manager.db_type == 'postgresql'

            # Test 1: Total count
            cursor.execute("SELECT COUNT(*) as total FROM transactions")
            result = cursor.fetchone()
            total_all = result['total'] if is_postgresql else result[0]

            # Test 2: Non-archived count
            cursor.execute("SELECT COUNT(*) as total FROM transactions WHERE (archived = FALSE OR archived IS NULL)")
            result = cursor.fetchone()
            total_unarchived = result['total'] if is_postgresql else result[0]

            # Test 3: Get first 3 transactions
            cursor.execute("SELECT transaction_id, date, description, amount, archived FROM transactions LIMIT 3")
            sample_transactions = cursor.fetchall()

            # Convert to list of dicts
            sample_list = []
            for row in sample_transactions:
                if is_postgresql:
                    sample_list.append(dict(row))
                else:
                    sample_list.append(dict(row))

            return jsonify({
                'total_all_transactions': total_all,
                'total_unarchived_transactions': total_unarchived,
                'sample_transactions': sample_list,
                'db_type': db_manager.db_type
            })

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/debug/positive-transactions')
def api_debug_positive_transactions():
    """Debug endpoint to find positive (revenue) transactions"""
    try:
        from database import db_manager

        with db_manager.get_connection() as conn:
            if db_manager.db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cursor = conn.cursor()

            is_postgresql = db_manager.db_type == 'postgresql'

            # Find positive transactions
            cursor.execute("""
                SELECT transaction_id, date, description, amount, classified_entity, currency
                FROM transactions
                WHERE amount > 0
                ORDER BY amount DESC
                LIMIT 10
            """)
            positive_transactions = cursor.fetchall()

            # Find transactions with highest absolute values (both positive and negative)
            cursor.execute("""
                SELECT transaction_id, date, description, amount, classified_entity, currency
                FROM transactions
                ORDER BY ABS(amount) DESC
                LIMIT 10
            """)
            highest_transactions = cursor.fetchall()

            # Count positive vs negative
            cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE amount > 0")
            result = cursor.fetchone()
            positive_count = result['count'] if is_postgresql else result[0]

            cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE amount < 0")
            result = cursor.fetchone()
            negative_count = result['count'] if is_postgresql else result[0]

            # Convert to list of dicts
            positive_list = []
            for row in positive_transactions:
                if is_postgresql:
                    positive_list.append(dict(row))
                else:
                    positive_list.append(dict(row))

            highest_list = []
            for row in highest_transactions:
                if is_postgresql:
                    highest_list.append(dict(row))
                else:
                    highest_list.append(dict(row))

            return jsonify({
                'positive_transactions': positive_list,
                'highest_value_transactions': highest_list,
                'stats': {
                    'positive_count': positive_count,
                    'negative_count': negative_count,
                    'total_count': positive_count + negative_count
                }
            })

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/revenue/reset-all-matches', methods=['POST'])
def api_reset_all_matches():
    """Reset all invoice-transaction matches - remove all links"""
    try:
        from database import db_manager

        with db_manager.get_connection() as conn:
            if db_manager.db_type == 'postgresql':
                cursor = conn.cursor()
            else:
                cursor = conn.cursor()

            # Count current matches
            cursor.execute("SELECT COUNT(*) FROM invoices WHERE linked_transaction_id IS NOT NULL")
            current_matches = cursor.fetchone()[0]

            # Remove all matches from invoices table
            cursor.execute("""
                UPDATE invoices
                SET linked_transaction_id = NULL,
                    match_confidence = NULL,
                    match_method = NULL
                WHERE linked_transaction_id IS NOT NULL
            """)

            # Clear invoice match log table if it exists
            try:
                cursor.execute("DELETE FROM invoice_match_log")
            except:
                pass  # Table might not exist

            conn.commit()

            return jsonify({
                'success': True,
                'message': f'Successfully reset {current_matches} matches',
                'matches_removed': current_matches
            })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

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

        # If classified_entity field is updated, extract and store entity patterns using LLM
        if success and field == 'classified_entity' and value and value != 'N/A':
            try:
                # Get transaction description for pattern extraction
                conn = get_db_connection()
                cursor = conn.cursor()
                is_postgresql = hasattr(cursor, 'mogrify')
                placeholder = '%s' if is_postgresql else '?'

                cursor.execute(
                    f"SELECT description FROM transactions WHERE transaction_id = {placeholder}",
                    (transaction_id,)
                )
                tx_row = cursor.fetchone()
                conn.close()

                if tx_row:
                    description = tx_row.get('description', '') if isinstance(tx_row, dict) else tx_row[0]

                    # Extract patterns asynchronously in background
                    # For now, we'll do it synchronously but this could be moved to a background job
                    extract_entity_patterns_with_llm(transaction_id, value, description, claude_client)
                    print(f"INFO: Entity pattern extraction triggered for transaction {transaction_id}, entity: {value}")
            except Exception as pattern_error:
                # Don't fail the update if pattern extraction fails
                print(f"WARNING: Pattern extraction failed but transaction update succeeded: {pattern_error}")

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
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'
        updated_count = 0

        for transaction_id in transaction_ids:
            cursor.execute(
                f"UPDATE transactions SET classified_entity = {placeholder} WHERE transaction_id = {placeholder}",
                (new_entity, transaction_id)
            )
            if cursor.rowcount > 0:
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
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'
        updated_count = 0

        for transaction_id in transaction_ids:
            cursor.execute(
                f"UPDATE transactions SET accounting_category = {placeholder} WHERE transaction_id = {placeholder}",
                (new_category, transaction_id)
            )
            if cursor.rowcount > 0:
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

@app.route('/api/archive_transactions', methods=['POST'])
def api_archive_transactions():
    """API endpoint to archive multiple transactions"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])

        if not transaction_ids:
            return jsonify({'error': 'No transaction IDs provided'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'
        archived_count = 0

        for transaction_id in transaction_ids:
            cursor.execute(
                f"UPDATE transactions SET archived = TRUE WHERE transaction_id = {placeholder}",
                (transaction_id,)
            )
            if cursor.rowcount > 0:
                archived_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Archived {archived_count} transactions',
            'archived_count': archived_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/unarchive_transactions', methods=['POST'])
def api_unarchive_transactions():
    """API endpoint to unarchive multiple transactions"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])

        if not transaction_ids:
            return jsonify({'error': 'No transaction IDs provided'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'
        unarchived_count = 0

        for transaction_id in transaction_ids:
            cursor.execute(
                f"UPDATE transactions SET archived = FALSE WHERE transaction_id = {placeholder}",
                (transaction_id,)
            )
            if cursor.rowcount > 0:
                unarchived_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Unarchived {unarchived_count} transactions',
            'unarchived_count': unarchived_count
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
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            cursor.execute(f"SELECT * FROM transactions WHERE transaction_id = {placeholder}", (transaction_id,))
            row = cursor.fetchone()
            if row:
                context = dict(row)
            conn.close()

        # Add special parameters for similar_descriptions, similar_entities, and similar_accounting
        if field_type in ['similar_descriptions', 'similar_entities', 'similar_accounting']:
            context['transaction_id'] = transaction_id
            context['value'] = request.args.get('value', current_value)
            context['field_type'] = field_type

        suggestions = get_ai_powered_suggestions(field_type, current_value, context)

        # Check if None was returned due to API issues (empty list [] is valid - means no matches)
        if suggestions is None and claude_client:
            return jsonify({
                'error': 'Claude API failed to generate suggestions',
                'suggestions': [],
                'fallback_available': False,
                'has_learned_patterns': False
            }), 500
        elif suggestions is None and not claude_client:
            return jsonify({
                'error': 'Claude API not available - check ANTHROPIC_API_KEY environment variable',
                'suggestions': [],
                'fallback_available': False,
                'has_learned_patterns': False
            }), 500

        # Return suggestions with pattern learning status for entity suggestions
        has_patterns = context.get('has_learned_patterns', False) if field_type == 'similar_entities' else None
        result = {'suggestions': suggestions}
        if has_patterns is not None:
            result['has_learned_patterns'] = has_patterns

        return jsonify(result)

    except Exception as e:
        print(f"ERROR: API suggestions error: {e}", flush=True)
        print(f"ERROR TRACEBACK: {traceback.format_exc()}", flush=True)
        return jsonify({
            'error': f'Failed to get AI suggestions: {str(e)}',
            'suggestions': [],
            'fallback_available': False
        }), 500

@app.route('/api/accounting_categories', methods=['GET'])
def api_get_accounting_categories():
    """API endpoint to fetch distinct accounting categories from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')

        # Get distinct accounting categories that are not NULL or 'N/A'
        query = """
            SELECT DISTINCT accounting_category
            FROM transactions
            WHERE accounting_category IS NOT NULL
            AND accounting_category != 'N/A'
            AND accounting_category != ''
            ORDER BY accounting_category
        """

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        # Extract categories from rows
        if is_postgresql:
            categories = [row['accounting_category'] if isinstance(row, dict) else row[0] for row in rows]
        else:
            categories = [row[0] for row in rows]

        return jsonify({'categories': categories})

    except Exception as e:
        print(f"ERROR: Failed to fetch accounting categories: {e}", flush=True)
        return jsonify({'error': str(e), 'categories': []}), 500

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
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        cursor.execute(f"SELECT * FROM transactions WHERE transaction_id = {placeholder}", (transaction_id,))
        original_row = cursor.fetchone()

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
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        cursor.execute(f"SELECT * FROM transactions WHERE transaction_id = {placeholder}", (transaction_id,))
        original_row = cursor.fetchone()

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
        # Read the uploaded CSV file
        df = pd.read_csv(filepath)
        print(f"[STATS] Checking duplicates in {len(df)} transactions from file")

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

        print(f"[CHECK] Duplicate check result: {len(duplicates)} duplicates found out of {len(df)} total transactions")
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
            print(f"[FOUND] Found {duplicate_info['duplicate_count']} duplicates, showing confirmation dialog")
            return jsonify({
                'success': False,
                'duplicate_confirmation_needed': True,
                'duplicate_info': duplicate_info,
                'message': f'Found {duplicate_info["duplicate_count"]} duplicate transactions. Please choose how to handle them.'
            })

        # Process the file in a simpler way to avoid subprocess issues
        try:
            # Use a subprocess to run the processing in a separate Python instance
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
            # Ensure database environment variables are passed through
            if os.getenv('DB_TYPE'):
                env['DB_TYPE'] = os.getenv('DB_TYPE')
            if os.getenv('DB_HOST'):
                env['DB_HOST'] = os.getenv('DB_HOST')
            if os.getenv('DB_PORT'):
                env['DB_PORT'] = os.getenv('DB_PORT')
            if os.getenv('DB_NAME'):
                env['DB_NAME'] = os.getenv('DB_NAME')
            if os.getenv('DB_USER'):
                env['DB_USER'] = os.getenv('DB_USER')
            if os.getenv('DB_PASSWORD'):
                env['DB_PASSWORD'] = os.getenv('DB_PASSWORD')

            print(f"🔧 DEBUG: Running subprocess for {filename}")
            print(f"🔧 DEBUG: API key set: {'Yes' if env.get('ANTHROPIC_API_KEY') else 'No'}")
            print(f"🔧 DEBUG: Working directory: {parent_dir}")
            print(f"🔧 DEBUG: Processing script length: {len(processing_script)}")

            process_result = subprocess.run(
                [sys.executable, '-c', processing_script],
                capture_output=True,
                text=True,
                cwd=parent_dir,
                timeout=120,  # Increase timeout to 2 minutes
                env=env
            )

            print(f"🔧 DEBUG: Subprocess return code: {process_result.returncode}")
            print(f"🔧 DEBUG: Subprocess stdout length: {len(process_result.stdout)}")
            print(f"🔧 DEBUG: Subprocess stderr length: {len(process_result.stderr)}")

            if process_result.stdout:
                print(f"🔧 DEBUG: Subprocess stdout: {process_result.stdout}")
            if process_result.stderr:
                print(f"🔧 DEBUG: Subprocess stderr: {process_result.stderr}")

            # Check for specific error patterns
            if process_result.returncode != 0:
                print(f"[ERROR] DEBUG: Subprocess failed with return code {process_result.returncode}")
                if "claude" in process_result.stderr.lower() or "anthropic" in process_result.stderr.lower():
                    print("🔧 DEBUG: Detected Claude/Anthropic related error")
                if "import" in process_result.stderr.lower():
                    print("🔧 DEBUG: Detected import error")
                if "timeout" in process_result.stderr.lower():
                    print("🔧 DEBUG: Detected timeout error")

            # Extract transaction count from output
            transactions_processed = 0
            if 'PROCESSED_COUNT:' in process_result.stdout:
                count_str = process_result.stdout.split('PROCESSED_COUNT:')[1].split('\n')[0]
                try:
                    transactions_processed = int(count_str)
                    print(f"🔧 DEBUG: Extracted transaction count: {transactions_processed}")
                except ValueError as e:
                    print(f"🔧 DEBUG: Failed to parse transaction count '{count_str}': {e}")

            # If subprocess failed, return the error immediately
            if process_result.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': f'Classification failed: {process_result.stderr or "Unknown subprocess error"}',
                    'subprocess_stdout': process_result.stdout,
                    'subprocess_stderr': process_result.stderr,
                    'return_code': process_result.returncode
                }), 500

            # Now sync to database
            print(f"🔧 DEBUG: Starting database sync for {filename}...")
            sync_result = sync_csv_to_database(filename)
            print(f"🔧 DEBUG: Database sync result: {sync_result}")

            if sync_result:
                # Auto-trigger revenue matching after successful transaction upload
                try:
                    print(f"🔧 AUTO-TRIGGER: Starting automatic revenue matching...")
                    from robust_revenue_matcher import RobustRevenueInvoiceMatcher

                    matcher = RobustRevenueInvoiceMatcher()
                    matches_result = matcher.process_revenue_matching(auto_apply=False, match_all=True)

                    if matches_result and matches_result.get('matches_found', 0) > 0:
                        print(f"✅ AUTO-TRIGGER: Found {matches_result['matches_found']} new matches automatically!")
                    else:
                        print("ℹ️ AUTO-TRIGGER: No new matches found after transaction upload")

                except Exception as e:
                    print(f"⚠️ AUTO-TRIGGER: Error during automatic matching: {e}")
                    # Don't fail the upload if matching fails

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
                    'transactions_processed': transactions_processed,
                    'subprocess_stdout': process_result.stdout,
                    'subprocess_stderr': process_result.stderr
                }), 500

        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'error': 'Processing timeout - file too large or complex'
            }), 500
        except Exception as processing_error:
            error_details = traceback.format_exc()
            return jsonify({
                'success': False,
                'error': f'Processing failed: {str(processing_error)}',
                'details': error_details
            }), 500

    except Exception as e:
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

        print(f"[PROCESS] Processing duplicates for {filename} with mode: {duplicate_handling}")

        # File should already exist from initial upload
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        filepath = os.path.join(parent_dir, filename)

        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 400

        # Use same processing logic as upload_file but force the duplicate handling
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
        # Ensure database environment variables are passed through
        if os.getenv('DB_TYPE'):
            env['DB_TYPE'] = os.getenv('DB_TYPE')
        if os.getenv('DB_HOST'):
            env['DB_HOST'] = os.getenv('DB_HOST')
        if os.getenv('DB_PORT'):
            env['DB_PORT'] = os.getenv('DB_PORT')
        if os.getenv('DB_NAME'):
            env['DB_NAME'] = os.getenv('DB_NAME')
        if os.getenv('DB_USER'):
            env['DB_USER'] = os.getenv('DB_USER')
        if os.getenv('DB_PASSWORD'):
            env['DB_PASSWORD'] = os.getenv('DB_PASSWORD')

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
        print(f"[DEBUG] api_get_invoices called with args: {request.args}")
        # Get filter parameters
        filters = {
            'business_unit': request.args.get('business_unit'),
            'category': request.args.get('category'),
            'vendor_name': request.args.get('vendor_name'),
            'customer_name': request.args.get('customer_name'),
            'linked_transaction_id': request.args.get('linked_transaction_id')
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v}

        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        offset = (page - 1) * per_page

        from database import db_manager

        # Use PostgreSQL placeholders since we're using db_manager
        placeholder = '%s'

        # Build query
        query = "SELECT * FROM invoices WHERE 1=1"
        params = []

        if filters.get('business_unit'):
            query += f" AND business_unit = {placeholder}"
            params.append(filters['business_unit'])

        if filters.get('category'):
            query += f" AND category = {placeholder}"
            params.append(filters['category'])

        if filters.get('vendor_name'):
            query += f" AND vendor_name LIKE {placeholder}"
            params.append(f"%{filters['vendor_name']}%")

        if filters.get('customer_name'):
            query += f" AND customer_name LIKE {placeholder}"
            params.append(f"%{filters['customer_name']}%")

        # Filter by linked_transaction_id (special handling before filters cleanup)
        linked_filter = request.args.get('linked_transaction_id')
        if linked_filter:
            if linked_filter.lower() in ['null', 'none', 'unlinked']:
                # Show only unlinked invoices
                query += " AND (linked_transaction_id IS NULL OR linked_transaction_id = '')"
                print(f"[DEBUG] Applied unlinked filter: {query}")
            elif linked_filter.lower() in ['not_null', 'linked']:
                # Show only linked invoices
                query += " AND linked_transaction_id IS NOT NULL AND linked_transaction_id != ''"
                print(f"[DEBUG] Applied linked filter: {query}")
            else:
                # Show invoices with specific transaction ID
                query += f" AND linked_transaction_id = {placeholder}"
                params.append(linked_filter)
                print(f"[DEBUG] Applied specific ID filter: {query}")

        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*) as total")
        count_result = db_manager.execute_query(count_query, tuple(params), fetch_one=True)
        total_count = count_result['total'] if count_result else 0

        # Add ordering and pagination
        query += f" ORDER BY created_at DESC LIMIT {placeholder} OFFSET {placeholder}"
        params.extend([per_page, offset])

        results = db_manager.execute_query(query, tuple(params), fetch_all=True)
        invoices = []

        if results:
            for row in results:
                invoice = dict(row)
                # Parse JSON fields
                if invoice.get('line_items'):
                    try:
                        invoice['line_items'] = json.loads(invoice['line_items'])
                    except:
                        invoice['line_items'] = []
                invoices.append(invoice)

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
        from database import db_manager

        # Execute query using db_manager
        row = db_manager.execute_query("SELECT * FROM invoices WHERE id = %s", (invoice_id,), fetch_one=True)

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

        file_ext = os.path.splitext(file_path)[1].lower()

        os.makedirs(extract_dir, exist_ok=True)

        # Extract archive based on file type
        if file_ext == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

        elif file_ext == '.7z':
            if not PY7ZR_AVAILABLE:
                return {'error': '7z support not available - py7zr package required'}
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

        # Auto-trigger revenue matching after successful invoice upload
        try:
            print(f"🔧 AUTO-TRIGGER: Starting automatic revenue matching after invoice upload...")
            from robust_revenue_matcher import RobustRevenueInvoiceMatcher

            matcher = RobustRevenueInvoiceMatcher()
            # Focus on the newly uploaded invoice
            matches_result = matcher.process_revenue_matching(auto_apply=False, match_all=True)

            if matches_result and matches_result.get('matches_found', 0) > 0:
                print(f"✅ AUTO-TRIGGER: Found {matches_result['matches_found']} new matches automatically!")
            else:
                print("ℹ️ AUTO-TRIGGER: No new matches found after invoice upload")

        except Exception as e:
            print(f"⚠️ AUTO-TRIGGER: Error during automatic matching: {e}")
            # Don't fail the upload if matching fails

        return jsonify({
            'success': True,
            'invoice_id': invoice_data['id'],
            'invoice': invoice_data
        })

    except Exception as e:
        error_details = {
            'error': str(e),
            'error_type': type(e).__name__,
            'claude_client_status': 'initialized' if claude_client else 'not_initialized',
            'api_key_present': bool(os.getenv('ANTHROPIC_API_KEY')),
            'traceback': traceback.format_exc()
        }
        print(f"[ERROR] Invoice upload error: {error_details}")
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
                        with zipfile.ZipFile(compressed_path, 'r') as zip_ref:
                            all_files_in_archive = [name for name in zip_ref.namelist() if not name.endswith('/')]
                            total_in_archive = len(all_files_in_archive)
                    elif file_ext == '.7z':
                        if PY7ZR_AVAILABLE:
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

        # Auto-trigger revenue matching after successful batch invoice upload
        if results['processed'] > 0:
            try:
                print(f"🔧 AUTO-TRIGGER: Starting automatic revenue matching after batch upload ({results['processed']} invoices)...")
                from robust_revenue_matcher import RobustRevenueInvoiceMatcher

                matcher = RobustRevenueInvoiceMatcher()
                matches_result = matcher.process_revenue_matching(auto_apply=False, match_all=True)

                if matches_result and matches_result.get('matches_found', 0) > 0:
                    print(f"✅ AUTO-TRIGGER: Found {matches_result['matches_found']} new matches automatically!")
                    results['auto_matches_found'] = matches_result['matches_found']
                else:
                    print("ℹ️ AUTO-TRIGGER: No new matches found after batch upload")
                    results['auto_matches_found'] = 0

            except Exception as e:
                print(f"⚠️ AUTO-TRIGGER: Error during automatic matching: {e}")
                results['auto_trigger_error'] = str(e)

        return jsonify(results)

    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/invoices/upload-batch-async', methods=['POST'])
def api_upload_batch_invoices_async():
    """Upload and process multiple invoice files asynchronously using background jobs"""
    try:
        if 'files' not in request.files and 'file' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'invoices')
        temp_extract_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'temp_extract')
        os.makedirs(upload_dir, exist_ok=True)

        files_to_process = []
        cleanup_paths = []
        source_file_name = None

        # Handle file upload (same logic as sync version)
        if 'file' in request.files:
            file = request.files['file']
            file_ext = os.path.splitext(file.filename)[1].lower()
            source_file_name = file.filename

            if file_ext in ['.zip', '.7z', '.rar']:
                # Save compressed file
                compressed_path = os.path.join(upload_dir, f"{uuid.uuid4()}{file_ext}")
                file.save(compressed_path)
                cleanup_paths.append(compressed_path)

                # Extract files
                extract_result = extract_compressed_file(compressed_path, temp_extract_dir)

                if isinstance(extract_result, dict) and 'error' in extract_result:
                    return jsonify(extract_result), 400

                files_to_process = [(f, os.path.basename(f)) for f in extract_result]
                cleanup_paths.append(temp_extract_dir)
            else:
                # Single file upload
                unique_filename = f"{uuid.uuid4()}{file_ext}"
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)
                files_to_process = [(file_path, file.filename)]

        # Handle multiple files
        elif 'files' in request.files:
            files = request.files.getlist('files')
            for file in files:
                if file.filename:
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    unique_filename = f"{uuid.uuid4()}{file_ext}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    file.save(file_path)
                    files_to_process.append((file_path, file.filename))
            source_file_name = f"{len(files)} files uploaded"

        if not files_to_process:
            return jsonify({'error': 'No valid files to process'}), 400

        # Filter supported file types
        allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
        valid_files = []

        for file_path, original_name in files_to_process:
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in allowed_extensions:
                valid_files.append((file_path, original_name))
            else:
                # Clean up unsupported files
                try:
                    os.remove(file_path)
                except:
                    pass

        if not valid_files:
            return jsonify({'error': 'No supported file types found'}), 400

        # Create background job
        metadata = f"Source: {source_file_name}, Files: {len(valid_files)}"
        job_id = create_background_job(
            job_type='invoice_batch',
            total_items=len(valid_files),
            created_by='web_user',
            source_file=source_file_name,
            metadata=metadata
        )

        if not job_id:
            return jsonify({'error': 'Failed to create background job'}), 500

        # Add all files as job items
        for file_path, original_name in valid_files:
            add_job_item(job_id, original_name, file_path)

        # Start background processing
        success = start_background_job(job_id, 'invoice_batch')

        if not success:
            return jsonify({'error': 'Failed to start background processing'}), 500

        # Return immediately with job ID
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': f'Background job created successfully. Processing {len(valid_files)} files.',
            'total_files': len(valid_files),
            'status_url': f'/api/jobs/{job_id}'
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/invoices/<invoice_id>', methods=['PUT'])
def api_update_invoice(invoice_id):
    """Update invoice fields - supports single field or multiple fields"""
    try:
        from database import db_manager
        data = request.get_json()

        # Check if invoice exists
        existing = db_manager.execute_query("SELECT id FROM invoices WHERE id = %s", (invoice_id,), fetch_one=True)
        if not existing:
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
                return jsonify({'error': 'Invalid field name'}), 400

            update_query = f"UPDATE invoices SET {field} = %s WHERE id = %s"
            db_manager.execute_query(update_query, (value, invoice_id))
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
                    updates.append(f"{field} = %s")
                    values.append(value)

            if not updates:
                return jsonify({'error': 'No valid fields to update'}), 400

            update_query = f"UPDATE invoices SET {', '.join(updates)} WHERE id = %s"
            values.append(invoice_id)
            db_manager.execute_query(update_query, tuple(values))

        return jsonify({'success': True, 'message': 'Invoice updated'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/<invoice_id>', methods=['DELETE'])
def api_delete_invoice(invoice_id):
    """Delete invoice"""
    try:
        from database import db_manager

        # Execute delete query
        rows_affected = db_manager.execute_query("DELETE FROM invoices WHERE id = %s", (invoice_id,))

        if rows_affected == 0:
            return jsonify({'error': 'Invoice not found'}), 404

        return jsonify({'success': True, 'message': 'Invoice deleted'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/bulk-update', methods=['POST'])
def api_bulk_update_invoices():
    """Bulk update multiple invoices"""
    try:
        from database import db_manager
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
                update_parts.append(f"{field} = %s")
                values.append(value)

        if not update_parts:
            return jsonify({'error': 'No valid fields to update'}), 400

        updated_count = 0

        # Use transaction for consistency
        with db_manager.get_transaction() as conn:
            cursor = conn.cursor()

            # Update each invoice
            for invoice_id in invoice_ids:
                update_query = f"UPDATE invoices SET {', '.join(update_parts)} WHERE id = %s"
                cursor.execute(update_query, values + [invoice_id])
                if cursor.rowcount > 0:
                    updated_count += 1

            cursor.close()

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
        from database import db_manager
        data = request.get_json()
        invoice_ids = data.get('invoice_ids', [])

        if not invoice_ids:
            return jsonify({'error': 'No invoice IDs provided'}), 400

        deleted_count = 0

        # Use transaction for consistency
        with db_manager.get_transaction() as conn:
            cursor = conn.cursor()

            # Delete each invoice
            for invoice_id in invoice_ids:
                cursor.execute("DELETE FROM invoices WHERE id = %s", (invoice_id,))
                if cursor.rowcount > 0:
                    deleted_count += 1

            cursor.close()

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
        from database import db_manager

        # Total invoices
        total_result = db_manager.execute_query("SELECT COUNT(*) as count FROM invoices", fetch_one=True)
        total = total_result['count'] if total_result else 0

        # Total amount
        amount_result = db_manager.execute_query("SELECT COALESCE(SUM(total_amount), 0) as total FROM invoices", fetch_one=True)
        total_amount = amount_result['total'] if amount_result else 0

        # Unique vendors
        vendors_result = db_manager.execute_query("SELECT COUNT(DISTINCT vendor_name) as count FROM invoices WHERE vendor_name IS NOT NULL AND vendor_name != ''", fetch_one=True)
        unique_vendors = vendors_result['count'] if vendors_result else 0

        # Unique customers
        customers_result = db_manager.execute_query("SELECT COUNT(DISTINCT customer_name) as count FROM invoices WHERE customer_name IS NOT NULL AND customer_name != ''", fetch_one=True)
        unique_customers = customers_result['count'] if customers_result else 0

        # By business unit
        bu_counts = {}
        try:
            bu_rows = db_manager.execute_query("SELECT business_unit, COUNT(*) as count, SUM(total_amount) as total FROM invoices WHERE business_unit IS NOT NULL GROUP BY business_unit", fetch_all=True)
            if bu_rows:
                for row in bu_rows:
                    bu_counts[row['business_unit']] = {'count': row['count'], 'total': row['total']}
        except:
            pass  # Column might not exist

        # By category
        category_counts = {}
        try:
            category_rows = db_manager.execute_query("SELECT category, COUNT(*) as count, SUM(total_amount) as total FROM invoices WHERE category IS NOT NULL GROUP BY category", fetch_all=True)
            if category_rows:
                for row in category_rows:
                    category_counts[row['category']] = {'count': row['count'], 'total': row['total']}
        except:
            pass  # Column might not exist

        # By customer
        customer_counts = {}
        customer_rows = db_manager.execute_query("SELECT customer_name, COUNT(*) as count, SUM(total_amount) as total FROM invoices WHERE customer_name IS NOT NULL AND customer_name != '' GROUP BY customer_name ORDER BY COUNT(*) DESC LIMIT 10", fetch_all=True)
        if customer_rows:
            for row in customer_rows:
                customer_counts[row['customer_name']] = {'count': row['count'], 'total': row['total']}

        # Recent invoices
        recent_rows = db_manager.execute_query("SELECT * FROM invoices ORDER BY created_at DESC LIMIT 5", fetch_all=True)
        recent_invoices = [dict(row) for row in recent_rows] if recent_rows else []

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
        logger.error(f"Error getting invoice stats: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# BACKGROUND JOBS API ENDPOINTS
# ============================================================================

@app.route('/api/jobs/<job_id>')
def api_get_job_status(job_id):
    """Get status and progress of a background job"""
    try:
        job_status = get_job_status(job_id)

        if 'error' in job_status:
            return jsonify(job_status), 404

        return jsonify({
            'success': True,
            'data': job_status
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs')
def api_list_jobs():
    """List recent background jobs with pagination"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 50)  # Max 50 per page
        offset = (page - 1) * per_page

        # Get job filter
        status_filter = request.args.get('status')  # pending, processing, completed, failed
        job_type_filter = request.args.get('job_type')  # invoice_batch, etc.

        conn = get_db_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        # Build query with filters
        where_clauses = []
        params = []

        if status_filter:
            where_clauses.append(f"status = {placeholder}")
            params.append(status_filter)

        if job_type_filter:
            where_clauses.append(f"job_type = {placeholder}")
            params.append(job_type_filter)

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Get total count
        count_query = f"SELECT COUNT(*) FROM background_jobs {where_clause}"
        cursor.execute(count_query, params)
        total_result = cursor.fetchone()
        total = total_result['count'] if is_postgresql else total_result[0]

        # Get jobs with pagination
        params.extend([per_page, offset])
        jobs_query = f"""
            SELECT id, job_type, status, total_items, processed_items, successful_items,
                   failed_items, progress_percentage, started_at, completed_at, created_at,
                   created_by, source_file, error_message
            FROM background_jobs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT {placeholder} OFFSET {placeholder}
        """

        cursor.execute(jobs_query, params)
        jobs = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return jsonify({
            'jobs': jobs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/cancel', methods=['POST'])
def api_cancel_job(job_id):
    """Cancel a running background job"""
    try:
        # Get current job status
        job_status = get_job_status(job_id)

        if 'error' in job_status:
            return jsonify({'error': 'Job not found'}), 404

        current_status = job_status.get('status')

        if current_status in ['completed', 'failed']:
            return jsonify({'error': f'Cannot cancel job that is already {current_status}'}), 400

        # Update job status to cancelled
        update_job_progress(job_id, status='cancelled',
                          error_message='Job cancelled by user')

        return jsonify({
            'success': True,
            'message': 'Job cancelled successfully',
            'job_id': job_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def safe_insert_invoice(conn, invoice_data):
    """
    Safely insert or update invoice to avoid UNIQUE constraint errors
    """
    cursor = conn.cursor()

    # Detect database type for compatible syntax
    is_postgresql = hasattr(cursor, 'mogrify')  # PostgreSQL-specific method

    # Check if invoice exists
    if is_postgresql:
        cursor.execute('SELECT id FROM invoices WHERE invoice_number = %s', (invoice_data['invoice_number'],))
    else:
        cursor.execute('SELECT id FROM invoices WHERE invoice_number = ?', (invoice_data['invoice_number'],))
    existing = cursor.fetchone()

    if existing:
        # Update existing invoice
        if is_postgresql:
            cursor.execute("""
                UPDATE invoices SET
                    date=%s, due_date=%s, vendor_name=%s, vendor_address=%s,
                    vendor_tax_id=%s, customer_name=%s, customer_address=%s, customer_tax_id=%s,
                    total_amount=%s, currency=%s, tax_amount=%s, subtotal=%s,
                    line_items=%s, status=%s, invoice_type=%s, confidence_score=%s, processing_notes=%s,
                    source_file=%s, extraction_method=%s, processed_at=%s, created_at=%s,
                    business_unit=%s, category=%s, currency_type=%s
                WHERE invoice_number=%s
            """, (
                invoice_data['date'], invoice_data['due_date'], invoice_data['vendor_name'],
                invoice_data['vendor_address'], invoice_data['vendor_tax_id'], invoice_data['customer_name'],
                invoice_data['customer_address'], invoice_data['customer_tax_id'], invoice_data['total_amount'],
                invoice_data['currency'], invoice_data['tax_amount'], invoice_data['subtotal'],
                invoice_data['line_items'], invoice_data['status'], invoice_data['invoice_type'],
                invoice_data['confidence_score'], invoice_data['processing_notes'], invoice_data['source_file'],
                invoice_data['extraction_method'], invoice_data['processed_at'], invoice_data['created_at'],
                invoice_data['business_unit'], invoice_data['category'], invoice_data['currency_type'],
                invoice_data['invoice_number']
            ))
        else:
            cursor.execute("""
                UPDATE invoices SET
                    date=?, due_date=?, vendor_name=?, vendor_address=?,
                    vendor_tax_id=?, customer_name=?, customer_address=?, customer_tax_id=?,
                    total_amount=?, currency=?, tax_amount=?, subtotal=?,
                    line_items=?, status=?, invoice_type=?, confidence_score=?, processing_notes=?,
                    source_file=?, extraction_method=?, processed_at=?, created_at=?,
                    business_unit=?, category=?, currency_type=?
                WHERE invoice_number=?
            """, (
                invoice_data['date'], invoice_data['due_date'], invoice_data['vendor_name'],
                invoice_data['vendor_address'], invoice_data['vendor_tax_id'], invoice_data['customer_name'],
                invoice_data['customer_address'], invoice_data['customer_tax_id'], invoice_data['total_amount'],
                invoice_data['currency'], invoice_data['tax_amount'], invoice_data['subtotal'],
                invoice_data['line_items'], invoice_data['status'], invoice_data['invoice_type'],
                invoice_data['confidence_score'], invoice_data['processing_notes'], invoice_data['source_file'],
                invoice_data['extraction_method'], invoice_data['processed_at'], invoice_data['created_at'],
                invoice_data['business_unit'], invoice_data['category'], invoice_data['currency_type'],
                invoice_data['invoice_number']
            ))
        print(f"Updated existing invoice: {invoice_data['invoice_number']}")
        return "updated"
    else:
        # Insert new invoice
        if is_postgresql:
            cursor.execute("""
                INSERT INTO invoices (
                    id, invoice_number, date, due_date, vendor_name, vendor_address,
                    vendor_tax_id, customer_name, customer_address, customer_tax_id,
                    total_amount, currency, tax_amount, subtotal,
                    line_items, status, invoice_type, confidence_score, processing_notes,
                    source_file, extraction_method, processed_at, created_at,
                    business_unit, category, currency_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
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
        else:
            cursor.execute("""
                INSERT INTO invoices (
                    id, invoice_number, date, due_date, vendor_name, vendor_address,
                    vendor_tax_id, customer_name, customer_address, customer_tax_id,
                    total_amount, currency, tax_amount, subtotal,
                    line_items, status, invoice_type, confidence_score, processing_notes,
                    source_file, extraction_method, processed_at, created_at,
                    business_unit, category, currency_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
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
        print(f"Inserted new invoice: {invoice_data['invoice_number']}")
        return "inserted"

def preprocess_invoice_data(invoice_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ultra-robust preprocessing to handle all common failure cases"""
    import re
    from datetime import datetime, timedelta

    if 'error' in invoice_data:
        return invoice_data

    # Layer 2A: Date field cleaning
    problematic_dates = ['DUE ON RECEIPT', 'Due on Receipt', 'Due on receipt', 'PAID', 'NET 30', 'NET 15', 'UPON RECEIPT']

    if 'due_date' in invoice_data:
        due_date = str(invoice_data['due_date']).strip()
        if due_date.upper() in [d.upper() for d in problematic_dates]:
            # Convert to NULL for database
            invoice_data['due_date'] = None
            print(f"🔧 Cleaned problematic due_date: '{due_date}' → NULL")
        elif due_date.upper() == 'NET 30':
            # Smart conversion: NET 30 = invoice_date + 30 days
            try:
                if invoice_data.get('date'):
                    invoice_date = datetime.strptime(invoice_data['date'], '%Y-%m-%d')
                    invoice_data['due_date'] = (invoice_date + timedelta(days=30)).strftime('%Y-%m-%d')
                    print(f"🧠 Smart conversion: NET 30 → {invoice_data['due_date']}")
                else:
                    invoice_data['due_date'] = None
            except:
                invoice_data['due_date'] = None

    # Layer 2B: Field length limits and cleaning
    field_limits = {
        'currency': 45,  # Allow up to 45 chars (we expanded to 50, keeping 5 char buffer)
        'invoice_number': 100,
        'vendor_name': 200,
        'customer_name': 200
    }

    for field, limit in field_limits.items():
        if field in invoice_data and invoice_data[field]:
            original_value = str(invoice_data[field])
            if len(original_value) > limit:
                invoice_data[field] = original_value[:limit].strip()
                print(f"🔧 Truncated {field}: '{original_value[:20]}...' ({len(original_value)} chars → {limit})")

    # Layer 2C: Currency normalization
    if 'currency' in invoice_data and invoice_data['currency']:
        currency = str(invoice_data['currency']).strip()
        # Extract common currency codes from mixed strings
        currency_patterns = {
            r'USD|US\$|\$': 'USD',
            r'EUR|€': 'EUR',
            r'BTC|₿': 'BTC',
            r'PYG|₲': 'PYG'
        }

        for pattern, code in currency_patterns.items():
            if re.search(pattern, currency, re.IGNORECASE):
                if currency != code:
                    print(f"🔧 Normalized currency: '{currency}' → '{code}'")
                    invoice_data['currency'] = code
                break
        else:
            # If no pattern matches, keep first 3 chars as currency code
            if len(currency) > 3:
                invoice_data['currency'] = currency[:3].upper()
                print(f"🔧 Currency code extracted: '{currency}' → '{invoice_data['currency']}'")

    return invoice_data

def repair_json_string(json_str: str) -> str:
    """Repair common JSON formatting issues"""
    import re

    # Fix missing commas between objects
    json_str = re.sub(r'"\s*\n\s*"', '",\n  "', json_str)

    # Fix missing commas after values
    json_str = re.sub(r'(\d+|"[^"]*"|\]|\})\s*\n\s*"', r'\1,\n  "', json_str)

    # Fix trailing commas
    json_str = re.sub(r',(\s*[\}\]])', r'\1', json_str)

    # Ensure proper quotes around keys
    json_str = re.sub(r'(\w+):', r'"\1":', json_str)

    return json_str

def fallback_extract_invoice_data(text: str) -> dict:
    """Fallback extraction using regex when JSON parsing fails"""
    import re

    data = {}

    # Common field patterns
    patterns = {
        'invoice_number': r'"invoice_number":\s*"([^"]*)"',
        'vendor_name': r'"vendor_name":\s*"([^"]*)"',
        'total_amount': r'"total_amount":\s*([0-9.]+)',
        'currency': r'"currency":\s*"([^"]*)"',
        'date': r'"date":\s*"([^"]*)"'
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1)
            if field == 'total_amount':
                try:
                    data[field] = float(value)
                except:
                    data[field] = 0.0
            else:
                data[field] = value

    # Return None if no essential fields found
    if not data.get('vendor_name') and not data.get('total_amount'):
        return None

    # Fill in defaults for missing fields
    data.setdefault('invoice_number', f'AUTO_{int(time.time())}')
    data.setdefault('currency', 'USD')
    data.setdefault('date', datetime.now().strftime('%Y-%m-%d'))

    return data

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
- due_date: Due date ONLY if a SPECIFIC DATE is present (YYYY-MM-DD format). For text like "DUE ON RECEIPT", "NET 30", "PAID", use null
- tax_amount: Tax amount if itemized
- subtotal: Subtotal before tax
- line_items: Array of line items with description, quantity, unit_price, total

CRITICAL FORMATTING RULES:
1. DATES: Only use YYYY-MM-DD format or null. NEVER use text like "DUE ON RECEIPT", "NET 30", "PAID"
2. CURRENCY: Use standard 3-letter codes (USD, EUR, BTC, PYG). If unclear, extract first 3 characters
3. JSON: MUST be valid JSON with all commas and quotes correct. Double-check syntax
4. NUMBERS: Use numeric values only (e.g., 150.50, not "$150.50")

⚡ EXAMPLES:
[ERROR] "due_date": "DUE ON RECEIPT"
[OK] "due_date": null

[ERROR] "currency": "US Dollars"
[OK] "currency": "USD"

[ERROR] "total_amount": "$1,500.00"
[OK] "total_amount": 1500.00

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

        # LAYER 3: JSON repair and retry logic
        extracted_data = None
        json_parse_attempts = 0
        max_json_attempts = 3

        while extracted_data is None and json_parse_attempts < max_json_attempts:
            json_parse_attempts += 1
            try:
                extracted_data = json.loads(response_text)
                if json_parse_attempts > 1:
                    print(f"[OK] JSON parsed successfully on attempt {json_parse_attempts}")
                break
            except json.JSONDecodeError as e:
                print(f"WARNING: JSON parse attempt {json_parse_attempts} failed: {str(e)[:100]}")

                if json_parse_attempts < max_json_attempts:
                    # LAYER 3A: Auto-repair common JSON issues
                    response_text = repair_json_string(response_text)
                    print(f"🔧 Applied JSON auto-repair, retrying...")
                else:
                    # LAYER 3B: If all repairs fail, try regex fallback
                    print(f"[ERROR] JSON parsing failed after {max_json_attempts} attempts, trying fallback extraction...")
                    extracted_data = fallback_extract_invoice_data(response_text)
                    if extracted_data:
                        print("[OK] Fallback extraction succeeded")
                    else:
                        raise json.JSONDecodeError(f"Failed to parse or repair JSON after {max_json_attempts} attempts", response_text, 0)

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

        # LAYER 2: Ultra-robust preprocessing to handle all failure cases
        invoice_data = preprocess_invoice_data(invoice_data)

        # If preprocessing detected an error, return it
        if 'error' in invoice_data:
            return invoice_data

        # Save to database with robust connection handling
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = get_db_connection()

                # Check if invoice_number already exists
                cursor = conn.cursor()

                # Detect database type for compatible syntax
                is_postgresql = hasattr(cursor, 'mogrify')  # PostgreSQL-specific method

                if is_postgresql:
                    cursor.execute('SELECT id FROM invoices WHERE invoice_number = %s', (invoice_data['invoice_number'],))
                else:
                    cursor.execute('SELECT id FROM invoices WHERE invoice_number = ?', (invoice_data['invoice_number'],))
                existing = cursor.fetchone()

                if existing:
                    # Generate unique invoice number by appending timestamp
                    timestamp = int(time.time())
                    original_number = invoice_data['invoice_number']
                    invoice_data['invoice_number'] = f"{original_number}_{timestamp}"
                    print(f"Duplicate invoice number detected. Changed {original_number} to {invoice_data['invoice_number']}")

                # Use database-specific syntax for insert
                if is_postgresql:
                    cursor.execute('''
                        INSERT INTO invoices (
                            id, invoice_number, date, due_date, vendor_name, vendor_address,
                            vendor_tax_id, customer_name, customer_address, customer_tax_id,
                            total_amount, currency, tax_amount, subtotal,
                            line_items, status, invoice_type, confidence_score, processing_notes,
                            source_file, extraction_method, processed_at, created_at,
                            business_unit, category, currency_type
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                else:
                    cursor.execute('''
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
            except sqlite3.OperationalError as e:
                if conn:
                    conn.close()
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"Database locked during invoice insert, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Database error after {attempt + 1} attempts: {e}")
                    return {'error': f'Database locked after {attempt + 1} attempts: {str(e)}'}
            except Exception as e:
                # Handle both SQLite and PostgreSQL integrity errors
                is_integrity_error = (
                    isinstance(e, sqlite3.IntegrityError) or
                    (POSTGRESQL_AVAILABLE and hasattr(psycopg2, 'IntegrityError') and isinstance(e, psycopg2.IntegrityError))
                )
                if conn:
                    conn.close()
                # Handle duplicate invoice number constraint violations
                if is_integrity_error and ("duplicate key value violates unique constraint" in str(e) or "UNIQUE constraint failed" in str(e)):
                    if attempt < max_retries - 1:
                        # Generate new unique invoice number with timestamp
                        timestamp = int(time.time() * 1000) + attempt  # More unique with attempt number
                        original_number = invoice_data.get('invoice_number', 'UNKNOWN')
                        invoice_data['invoice_number'] = f"{original_number}_{timestamp}"
                        print(f"Duplicate constraint violation. Retrying with unique number: {invoice_data['invoice_number']}")
                        time.sleep(0.1)  # Small delay to avoid further collisions
                        continue
                    else:
                        print(f"Failed to resolve duplicate after {max_retries} attempts: {e}")
                        return {'error': f'Duplicate invoice number could not be resolved: {str(e)}'}
                else:
                    print(f"Unexpected error during invoice insert: {e}")
                    return {'error': str(e)}

    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON response from Claude: {e}")
        return {'error': f'Invalid JSON response from Claude Vision: {str(e)}'}
    except Exception as e:
        print(f"ERROR: Invoice processing failed: {e}")
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
        cursor = conn.cursor()
        suggestions = []

        if field_type == 'description':
            original_desc = transaction_context.get('description', '').upper()

            # Check for learned patterns - use cursor for both SQLite and PostgreSQL
            cursor.execute("""
                SELECT suggested_value, confidence_score, pattern_condition
                FROM learned_patterns
                WHERE pattern_type = 'description_pattern' AND confidence_score > 0.6
                ORDER BY confidence_score DESC, usage_count DESC
            """)
            patterns = cursor.fetchall()

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

            cursor.execute("""
                SELECT suggested_value, confidence_score, pattern_condition
                FROM learned_patterns
                WHERE pattern_type = 'accounting_category_pattern' AND confidence_score > 0.6
                ORDER BY confidence_score DESC, usage_count DESC
            """)
            patterns = cursor.fetchall()

            for pattern in patterns:
                condition = json.loads(pattern[2])
                if (condition.get('entity') == entity or
                    condition.get('amount_range') == amount_range):
                    suggestions.append({
                        'value': pattern[0],
                        'confidence': pattern[1],
                        'source': 'learned_pattern'
                    })

        cursor.close()
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

@app.route('/api/test-sync/<filename>')
def test_sync(filename):
    """Test endpoint to manually trigger sync for debugging"""
    print(f"🔧 TEST: Manual sync test for {filename}")

    # Check if original file exists where upload saves it (parent directory)
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    actual_file_path = os.path.join(parent_dir, filename)  # This is where upload saves files
    uploads_path = os.path.join(parent_dir, 'web_ui', 'uploads', filename)  # This was wrong assumption

    print(f"🔧 TEST: Checking actual upload path: {actual_file_path}")
    print(f"🔧 TEST: File exists at actual path: {os.path.exists(actual_file_path)}")
    print(f"🔧 TEST: Also checking uploads path: {uploads_path}")
    print(f"🔧 TEST: File exists at uploads path: {os.path.exists(uploads_path)}")

    # List files in parent directory
    try:
        files_in_parent = [f for f in os.listdir(parent_dir) if f.endswith('.csv')]
        print(f"🔧 TEST: CSV files in parent dir: {files_in_parent}")
    except Exception as e:
        print(f"🔧 TEST: Error listing parent dir: {e}")
        files_in_parent = []

    if os.path.exists(actual_file_path):
        # Try sync
        result = sync_csv_to_database(filename)
        return jsonify({
            'test_result': 'success' if result else 'failed',
            'file_found': True,
            'actual_path': actual_file_path,
            'sync_result': result,
            'classified_dir_check': os.path.exists(os.path.join(parent_dir, 'classified_transactions')),
            'files_in_classified': os.listdir(os.path.join(parent_dir, 'classified_transactions')) if os.path.exists(os.path.join(parent_dir, 'classified_transactions')) else [],
            'csv_files_in_parent': files_in_parent
        })
    else:
        return jsonify({
            'test_result': 'file_not_found_anywhere',
            'file_found': False,
            'checked_actual_path': actual_file_path,
            'checked_uploads_path': uploads_path,
            'csv_files_in_parent': files_in_parent
        })

@app.route('/api/debug-sync/<filename>')
def debug_sync(filename):
    """Debug endpoint to show detailed sync logs"""
    import io
    from contextlib import redirect_stdout, redirect_stderr

    # Capture all prints during sync
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            result = sync_csv_to_database(filename)

        return jsonify({
            'sync_result': result,
            'stdout_logs': stdout_capture.getvalue(),
            'stderr_logs': stderr_capture.getvalue(),
            'success': result is not False
        })
    except Exception as e:
        return jsonify({
            'sync_result': False,
            'stdout_logs': stdout_capture.getvalue(),
            'stderr_logs': stderr_capture.getvalue(),
            'exception': str(e),
            'success': False
        })

# ===============================================
# REVENUE MATCHING API ENDPOINTS
# ===============================================

@app.route('/api/revenue/run-matching', methods=['POST'])
def api_run_revenue_matching():
    """
    Executa matching automático de invoices com transações (versão básica)
    Body: {
        "invoice_ids": ["id1", "id2", ...] (opcional - se não fornecido, processa todos),
        "auto_apply": true/false (se deve aplicar matches automáticos)
    }
    """
    try:
        from revenue_matcher import run_invoice_matching

        data = request.get_json() or {}
        invoice_ids = data.get('invoice_ids')
        auto_apply = data.get('auto_apply', False)

        logger.info(f"Starting revenue matching - Invoice IDs: {invoice_ids}, Auto-apply: {auto_apply}")

        # Run the matching process
        result = run_invoice_matching(invoice_ids=invoice_ids, auto_apply=auto_apply)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in revenue matching: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/revenue/pending-matches')
def api_get_pending_matches():
    """Retorna matches pendentes de revisão"""
    try:
        from database import db_manager
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        offset = (page - 1) * per_page

        # Query including explanation and confidence_level fields
        query = """
            SELECT
                pm.id,
                pm.invoice_id,
                pm.transaction_id,
                pm.score,
                pm.match_type,
                pm.confidence_level,
                pm.explanation,
                pm.created_at,
                i.invoice_number,
                i.vendor_name,
                i.total_amount as invoice_amount,
                i.currency as invoice_currency,
                i.date as invoice_date,
                i.due_date,
                t.description,
                t.amount as transaction_amount,
                t.date as transaction_date,
                t.classified_entity
            FROM pending_invoice_matches pm
            JOIN invoices i ON pm.invoice_id = i.id
            JOIN transactions t ON pm.transaction_id = t.transaction_id
            WHERE pm.status = 'pending'
            ORDER BY pm.score DESC, pm.created_at DESC
            LIMIT %s OFFSET %s
        """

        matches = db_manager.execute_query(query, (per_page, offset), fetch_all=True)

        # Get total count
        count_query = """
            SELECT COUNT(*) as total
            FROM pending_invoice_matches
            WHERE status = 'pending'
        """
        total_result = db_manager.execute_query(count_query, fetch_one=True)
        total = total_result['total'] if total_result else 0

        # Format matches for frontend
        formatted_matches = []
        for match in matches:
            formatted_matches.append({
                'id': match['id'],
                'invoice_id': match['invoice_id'],
                'transaction_id': match['transaction_id'],
                'score': float(match['score']) if match['score'] else 0.0,
                'match_type': match['match_type'] or 'AUTO',
                'confidence_level': match['confidence_level'] or 'MEDIUM',
                'explanation': match['explanation'] or 'Match found based on automated criteria',
                'created_at': match['created_at'],
                'invoice': {
                    'number': match['invoice_number'],
                    'vendor_name': match['vendor_name'],
                    'amount': float(match['invoice_amount']) if match['invoice_amount'] else 0.0,
                    'currency': match['invoice_currency'],
                    'date': match['invoice_date'],
                    'due_date': match['due_date']
                },
                'transaction': {
                    'description': match['description'],
                    'amount': float(match['transaction_amount']) if match['transaction_amount'] else 0.0,
                    'date': match['transaction_date'],
                    'classified_entity': match['classified_entity']
                }
            })

        return jsonify({
            'success': True,
            'matches': formatted_matches,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        logger.error(f"Error getting pending matches: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/confirm-match', methods=['POST'])
def api_confirm_match():
    """
    Confirma um match pendente
    Body: {
        "match_id": int,
        "user_id": "string" (opcional)
    }
    """
    try:
        from database import db_manager
        data = request.get_json()
        match_id = data.get('match_id')
        user_id = data.get('user_id', 'Unknown')

        if not match_id:
            return jsonify({'success': False, 'error': 'match_id is required'}), 400

        # Get match details
        query = """
            SELECT invoice_id, transaction_id, score, match_type
            FROM pending_invoice_matches
            WHERE id = %s AND status = 'pending'
        """
        match = db_manager.execute_query(query, (match_id,), fetch_one=True)

        if not match:
            return jsonify({'success': False, 'error': 'Match not found or already processed'}), 404

        # Apply the match
        update_invoice_query = """
            UPDATE invoices
            SET linked_transaction_id = %s,
                status = 'paid'
            WHERE id = %s
        """
        db_manager.execute_query(update_invoice_query, (match['transaction_id'], match['invoice_id']))

        # Mark match as confirmed
        confirm_query = """
            UPDATE pending_invoice_matches
            SET status = 'confirmed',
                reviewed_by = %s,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        db_manager.execute_query(confirm_query, (user_id, match_id))

        # Log the action
        log_query = """
            INSERT INTO invoice_match_log
            (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
            VALUES (%s, %s, 'MANUAL_CONFIRMED', %s, %s, %s, CURRENT_TIMESTAMP)
        """
        db_manager.execute_query(log_query, (
            match['invoice_id'],
            match['transaction_id'],
            match['score'],
            match['match_type'],
            user_id
        ))

        return jsonify({
            'success': True,
            'message': 'Match confirmed successfully'
        })

    except Exception as e:
        logger.error(f"Error confirming match: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/reject-match', methods=['POST'])
def api_reject_match():
    """
    Rejeita um match pendente
    Body: {
        "match_id": int,
        "user_id": "string" (opcional),
        "reason": "string" (opcional)
    }
    """
    try:
        from database import db_manager
        data = request.get_json()
        match_id = data.get('match_id')
        user_id = data.get('user_id', 'Unknown')
        reason = data.get('reason', '')

        if not match_id:
            return jsonify({'success': False, 'error': 'match_id is required'}), 400

        # Get match details for logging
        query = """
            SELECT invoice_id, transaction_id, score, match_type
            FROM pending_invoice_matches
            WHERE id = %s AND status = 'pending'
        """
        match = db_manager.execute_query(query, (match_id,), fetch_one=True)

        if not match:
            return jsonify({'success': False, 'error': 'Match not found or already processed'}), 404

        # Mark match as rejected
        reject_query = """
            UPDATE pending_invoice_matches
            SET status = 'rejected',
                reviewed_by = %s,
                reviewed_at = CURRENT_TIMESTAMP,
                explanation = CONCAT(explanation, ' | REJECTED: ', %s)
            WHERE id = %s
        """
        db_manager.execute_query(reject_query, (user_id, reason, match_id))

        # Log the action
        log_query = """
            INSERT INTO invoice_match_log
            (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
            VALUES (%s, %s, 'MANUAL_REJECTED', %s, %s, %s, CURRENT_TIMESTAMP)
        """
        db_manager.execute_query(log_query, (
            match['invoice_id'],
            match['transaction_id'],
            match['score'],
            f"{match['match_type']}_REJECTED",
            user_id
        ))

        return jsonify({
            'success': True,
            'message': 'Match rejected successfully'
        })

    except Exception as e:
        logger.error(f"Error rejecting match: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/manual-match', methods=['POST'])
def api_manual_match():
    """
    Cria um match manual entre invoice e transação
    Body: {
        "invoice_id": "string",
        "transaction_id": "string",
        "user_id": "string" (opcional),
        "reason": "string" (opcional)
    }
    """
    try:
        data = request.get_json()
        invoice_id = data.get('invoice_id')
        transaction_id = data.get('transaction_id')
        user_id = data.get('user_id', 'Unknown')
        reason = data.get('reason', 'Manual match by user')

        if not invoice_id or not transaction_id:
            return jsonify({'success': False, 'error': 'invoice_id and transaction_id are required'}), 400

        # Verify invoice and transaction exist
        invoice_query = "SELECT id FROM invoices WHERE id = %s"
        invoice = db_manager.execute_query(invoice_query, (invoice_id,), fetch_one=True)

        transaction_query = "SELECT transaction_id FROM transactions WHERE transaction_id = %s"
        transaction = db_manager.execute_query(transaction_query, (transaction_id,), fetch_one=True)

        if not invoice:
            return jsonify({'success': False, 'error': 'Invoice not found'}), 404
        if not transaction:
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404

        # Apply the manual match
        update_query = """
            UPDATE invoices
            SET linked_transaction_id = %s,
                status = 'paid'
            WHERE id = %s
        """
        db_manager.execute_query(update_query, (transaction_id, invoice_id))

        # Log the manual match
        log_query = """
            INSERT INTO invoice_match_log
            (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
            VALUES (%s, %s, 'MANUAL_MATCH', 1.0, 'MANUAL', %s, CURRENT_TIMESTAMP)
        """
        db_manager.execute_query(log_query, (invoice_id, transaction_id, user_id))

        return jsonify({
            'success': True,
            'message': 'Manual match created successfully'
        })

    except Exception as e:
        logger.error(f"Error creating manual match: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/matched-pairs')
def api_get_matched_pairs():
    """Retorna invoices que já foram matchados com transações"""
    try:
        from database import db_manager
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        offset = (page - 1) * per_page

        query = """
            SELECT
                i.id as invoice_id,
                i.invoice_number,
                i.vendor_name,
                i.total_amount as invoice_amount,
                i.currency,
                i.date as invoice_date,
                i.due_date,
                i.status,
                t.transaction_id,
                t.description,
                t.amount as transaction_amount,
                t.date as transaction_date,
                t.classified_entity,
                log.action,
                log.score,
                log.match_type,
                log.user_id,
                log.created_at as matched_at
            FROM invoices i
            JOIN transactions t ON i.linked_transaction_id = t.transaction_id
            LEFT JOIN invoice_match_log log ON i.id = log.invoice_id AND t.transaction_id = log.transaction_id
            WHERE i.linked_transaction_id IS NOT NULL AND i.linked_transaction_id != ''
            ORDER BY COALESCE(log.created_at, i.created_at) DESC
            LIMIT %s OFFSET %s
        """

        pairs = db_manager.execute_query(query, (per_page, offset), fetch_all=True)

        # Get total count
        count_query = """
            SELECT COUNT(*) as total
            FROM invoices
            WHERE linked_transaction_id IS NOT NULL AND linked_transaction_id != ''
        """
        total_result = db_manager.execute_query(count_query, fetch_one=True)
        total = total_result['total'] if total_result else 0

        # Format pairs for frontend
        formatted_pairs = []
        for pair in pairs:
            formatted_pairs.append({
                'invoice_id': pair['invoice_id'],
                'transaction_id': pair['transaction_id'],
                'matched_at': pair['matched_at'],
                'match_type': pair['match_type'],
                'match_action': pair['action'],
                'match_score': float(pair['score']) if pair['score'] else None,
                'matched_by': pair['user_id'],
                'invoice': {
                    'number': pair['invoice_number'],
                    'vendor_name': pair['vendor_name'],
                    'amount': float(pair['invoice_amount']),
                    'currency': pair['currency'],
                    'date': pair['invoice_date'],
                    'due_date': pair['due_date'],
                    'status': pair['status']
                },
                'transaction': {
                    'description': pair['description'],
                    'amount': float(pair['transaction_amount']),
                    'date': pair['transaction_date'],
                    'classified_entity': pair['classified_entity']
                }
            })

        return jsonify({
            'success': True,
            'pairs': formatted_pairs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        logger.error(f"Error getting matched pairs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/stats')
def api_get_revenue_stats():
    """Retorna estatísticas do sistema de revenue matching"""
    try:
        from database import db_manager
        stats = {}

        # Total invoices
        query = "SELECT COUNT(*) as total FROM invoices"
        result = db_manager.execute_query(query, fetch_one=True)
        stats['total_invoices'] = result['total'] if result else 0

        # Matched invoices
        query = """
            SELECT COUNT(*) as matched
            FROM invoices
            WHERE linked_transaction_id IS NOT NULL AND linked_transaction_id != ''
        """
        result = db_manager.execute_query(query, fetch_one=True)
        stats['matched_invoices'] = result['matched'] if result else 0

        # Unmatched invoices
        stats['unmatched_invoices'] = stats['total_invoices'] - stats['matched_invoices']

        # Pending matches for review
        query = """
            SELECT COUNT(*) as pending
            FROM pending_invoice_matches
            WHERE status = 'pending'
        """
        result = db_manager.execute_query(query, fetch_one=True)
        stats['pending_matches'] = result['pending'] if result else 0

        # Total revenue amounts
        query = """
            SELECT
                COALESCE(SUM(CASE WHEN linked_transaction_id IS NOT NULL THEN total_amount ELSE 0 END), 0) as matched_revenue,
                COALESCE(SUM(CASE WHEN linked_transaction_id IS NULL THEN total_amount ELSE 0 END), 0) as unmatched_revenue,
                COALESCE(SUM(total_amount), 0) as total_revenue
            FROM invoices
        """
        result = db_manager.execute_query(query, fetch_one=True)
        if result:
            stats['matched_revenue'] = float(result['matched_revenue'])
            stats['unmatched_revenue'] = float(result['unmatched_revenue'])
            stats['total_revenue'] = float(result['total_revenue'])
        else:
            stats['matched_revenue'] = 0
            stats['unmatched_revenue'] = 0
            stats['total_revenue'] = 0

        # Match rate percentage
        if stats['total_invoices'] > 0:
            stats['match_rate'] = (stats['matched_invoices'] / stats['total_invoices']) * 100
        else:
            stats['match_rate'] = 0

        # Recent matching activity (last 30 days)
        query = """
            SELECT COUNT(*) as recent_matches
            FROM invoice_match_log
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
        """
        result = db_manager.execute_query(query, fetch_one=True)
        stats['recent_matches'] = result['recent_matches'] if result else 0

        # Match types breakdown
        query = """
            SELECT
                match_type,
                COUNT(*) as count
            FROM invoice_match_log
            WHERE action IN ('AUTO_APPLIED', 'MANUAL_CONFIRMED', 'MANUAL_MATCH')
            GROUP BY match_type
            ORDER BY count DESC
        """
        result = db_manager.execute_query(query, fetch_all=True)
        stats['match_types'] = {row['match_type']: row['count'] for row in result} if result else {}

        # Transaction statistics (opposite side of matching)
        # Total transactions
        query = "SELECT COUNT(*) as total FROM transactions"
        result = db_manager.execute_query(query, fetch_one=True)
        stats['total_transactions'] = result['total'] if result else 0

        # Linked transactions (transactions that are already linked to invoices)
        query = """
            SELECT COUNT(DISTINCT t.transaction_id) as linked
            FROM transactions t
            JOIN invoices i ON i.linked_transaction_id = t.transaction_id
            WHERE i.linked_transaction_id IS NOT NULL AND i.linked_transaction_id != ''
        """
        result = db_manager.execute_query(query, fetch_one=True)
        stats['linked_transactions'] = result['linked'] if result else 0

        # Unlinked transactions (transactions not linked to any invoice)
        stats['unlinked_transactions'] = stats['total_transactions'] - stats['linked_transactions']

        # Revenue transactions specifically (positive amounts that could match invoices)
        query = """
            SELECT COUNT(*) as revenue_transactions
            FROM transactions
            WHERE amount > 0
        """
        result = db_manager.execute_query(query, fetch_one=True)
        stats['revenue_transactions'] = result['revenue_transactions'] if result else 0

        # Unlinked revenue transactions (positive transactions not linked to invoices)
        query = """
            SELECT COUNT(*) as unlinked_revenue_transactions
            FROM transactions t
            WHERE t.amount > 0
            AND t.transaction_id NOT IN (
                SELECT DISTINCT i.linked_transaction_id
                FROM invoices i
                WHERE i.linked_transaction_id IS NOT NULL AND i.linked_transaction_id != ''
            )
        """
        result = db_manager.execute_query(query, fetch_one=True)
        stats['unlinked_revenue_transactions'] = result['unlinked_revenue_transactions'] if result else 0

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Error getting revenue stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/unmatch', methods=['POST'])
def api_unmatch_invoice():
    """
    Remove o match de um invoice
    Body: {
        "invoice_id": "string",
        "user_id": "string" (opcional),
        "reason": "string" (opcional)
    }
    """
    try:
        from database import db_manager
        data = request.get_json()
        invoice_id = data.get('invoice_id')
        user_id = data.get('user_id', 'Unknown')
        reason = data.get('reason', 'Manual unmatch by user')

        if not invoice_id:
            return jsonify({'success': False, 'error': 'invoice_id is required'}), 400

        # Get current match info for logging
        query = """
            SELECT linked_transaction_id
            FROM invoices
            WHERE id = %s AND linked_transaction_id IS NOT NULL
        """
        result = db_manager.execute_query(query, (invoice_id,), fetch_one=True)

        if not result:
            return jsonify({'success': False, 'error': 'Invoice not found or not matched'}), 404

        transaction_id = result['linked_transaction_id']

        # Remove the match
        update_query = """
            UPDATE invoices
            SET linked_transaction_id = NULL,
                status = 'pending'
            WHERE id = %s
        """
        db_manager.execute_query(update_query, (invoice_id,))

        # Log the unmatch action
        log_query = """
            INSERT INTO invoice_match_log
            (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
            VALUES (%s, %s, 'MANUAL_UNMATCHED', 0.0, 'UNMATCH', %s, CURRENT_TIMESTAMP)
        """
        db_manager.execute_query(log_query, (invoice_id, transaction_id, user_id))

        return jsonify({
            'success': True,
            'message': 'Invoice unmatched successfully'
        })

    except Exception as e:
        logger.error(f"Error unmatching invoice: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===============================================
# ROBUST REVENUE MATCHING API ENDPOINTS
# ===============================================

@app.route('/api/revenue/run-robust-matching', methods=['POST'])
def api_run_robust_revenue_matching():
    """
    Executa matching robusto de invoices com transações para produção
    Body: {
        "invoice_ids": ["id1", "id2", ...] (opcional),
        "auto_apply": true/false,
        "enable_learning": true/false (padrão: true)
    }
    """
    try:
        from robust_revenue_matcher import run_robust_invoice_matching

        data = request.get_json() or {}
        invoice_ids = data.get('invoice_ids')
        auto_apply = data.get('auto_apply', False)
        enable_learning = data.get('enable_learning', True)

        # Execute robust matching
        result = run_robust_invoice_matching(
            invoice_ids=invoice_ids,
            auto_apply=auto_apply,
            enable_learning=enable_learning
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in robust revenue matching: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {
                'total_invoices_processed': 0,
                'total_matches_found': 0,
                'errors_count': 1
            }
        }), 500

@app.route('/api/revenue/health')
def api_revenue_health_check():
    """
    Health check para o sistema de revenue matching
    Retorna status de conectividade e performance do banco
    """
    try:
        from database import db_manager

        # Perform database health check
        health_status = db_manager.health_check()

        # Additional checks specific to revenue matching
        revenue_health = {
            'database': health_status,
            'revenue_tables': {},
            'claude_api': {
                'available': bool(os.getenv('ANTHROPIC_API_KEY')),
                'status': 'configured' if os.getenv('ANTHROPIC_API_KEY') else 'not_configured'
            }
        }

        # Check revenue-specific tables
        revenue_tables = ['invoices', 'transactions', 'pending_invoice_matches', 'invoice_match_log']

        for table in revenue_tables:
            try:
                if db_manager.db_type == 'postgresql':
                    query = """
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = %s
                        )
                    """
                else:
                    query = """
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name = ?
                    """

                result = db_manager.execute_query(query, (table,), fetch_one=True)

                if db_manager.db_type == 'postgresql':
                    exists = result['exists'] if result else False
                else:
                    exists = bool(result)

                revenue_health['revenue_tables'][table] = 'exists' if exists else 'missing'

            except Exception as e:
                revenue_health['revenue_tables'][table] = f'error: {str(e)}'

        # Overall health status
        overall_status = 'healthy'
        if health_status['status'] != 'healthy':
            overall_status = 'unhealthy'
        elif any(status != 'exists' for status in revenue_health['revenue_tables'].values()):
            overall_status = 'degraded'

        revenue_health['overall_status'] = overall_status

        return jsonify({
            'success': True,
            'health': revenue_health
        })

    except Exception as e:
        logger.error(f"Error in revenue health check: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'health': {
                'overall_status': 'unhealthy',
                'error': str(e)
            }
        }), 500

@app.route('/api/revenue/batch-operations', methods=['POST'])
def api_revenue_batch_operations():
    """
    Executa operações em lote no sistema de revenue
    Body: {
        "operations": [
            {
                "type": "confirm_match",
                "invoice_id": "string",
                "transaction_id": "string",
                "user_id": "string"
            },
            {
                "type": "reject_match",
                "invoice_id": "string",
                "transaction_id": "string",
                "user_id": "string",
                "reason": "string"
            }
        ]
    }
    """
    try:
        from database import db_manager

        data = request.get_json() or {}
        operations = data.get('operations', [])

        if not operations:
            return jsonify({
                'success': False,
                'error': 'No operations provided'
            }), 400

        # Prepare batch operations for database
        db_operations = []
        results = {
            'total_operations': len(operations),
            'successful_operations': 0,
            'failed_operations': 0,
            'errors': []
        }

        for i, operation in enumerate(operations):
            op_type = operation.get('type')
            invoice_id = operation.get('invoice_id')
            transaction_id = operation.get('transaction_id')
            user_id = operation.get('user_id', 'system')

            try:
                if op_type == 'confirm_match':
                    # Add operation to update invoice
                    update_query = """
                        UPDATE invoices
                        SET linked_transaction_id = ?,
                            payment_status = 'paid'
                        WHERE id = ?
                    """
                    if db_manager.db_type == 'postgresql':
                        update_query = update_query.replace('?', '%s')

                    db_operations.append({
                        'query': update_query,
                        'params': (transaction_id, invoice_id)
                    })

                    # Add log operation
                    log_query = """
                        INSERT INTO invoice_match_log
                        (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
                        VALUES (?, ?, 'BATCH_CONFIRMED', 1.0, 'BATCH_OPERATION', ?, CURRENT_TIMESTAMP)
                    """
                    if db_manager.db_type == 'postgresql':
                        log_query = log_query.replace('?', '%s')

                    db_operations.append({
                        'query': log_query,
                        'params': (invoice_id, transaction_id, user_id)
                    })

                elif op_type == 'reject_match':
                    # Remove from pending matches
                    delete_query = """
                        DELETE FROM pending_invoice_matches
                        WHERE invoice_id = ? AND transaction_id = ?
                    """
                    if db_manager.db_type == 'postgresql':
                        delete_query = delete_query.replace('?', '%s')

                    db_operations.append({
                        'query': delete_query,
                        'params': (invoice_id, transaction_id)
                    })

                    # Add log operation
                    log_query = """
                        INSERT INTO invoice_match_log
                        (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
                        VALUES (?, ?, 'BATCH_REJECTED', 0.0, 'BATCH_OPERATION', ?, CURRENT_TIMESTAMP)
                    """
                    if db_manager.db_type == 'postgresql':
                        log_query = log_query.replace('?', '%s')

                    db_operations.append({
                        'query': log_query,
                        'params': (invoice_id, transaction_id, user_id)
                    })

                else:
                    results['failed_operations'] += 1
                    results['errors'].append(f"Operation {i}: Unknown operation type '{op_type}'")

            except Exception as e:
                results['failed_operations'] += 1
                results['errors'].append(f"Operation {i}: {str(e)}")

        # Execute batch operations
        if db_operations:
            batch_results = db_manager.execute_batch_operation(db_operations, batch_size=50)
            results['successful_operations'] = batch_results['successful_batches'] * 2  # Each operation has 2 queries
            results['database_stats'] = batch_results

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        logger.error(f"Error in batch operations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/performance-stats')
def api_revenue_performance_stats():
    """
    Retorna estatísticas de performance do sistema de matching
    """
    try:
        from database import db_manager

        # Get database health
        health_status = db_manager.health_check()

        # Performance metrics
        performance_stats = {
            'database_response_time_ms': health_status.get('response_time_ms', 0),
            'connection_pool_status': health_status.get('connection_pool_status'),
            'recent_activity': {}
        }

        # Recent matching activity (last 24 hours)
        query = """
            SELECT
                action,
                COUNT(*) as count,
                AVG(score) as avg_score
            FROM invoice_match_log
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
            GROUP BY action
            ORDER BY count DESC
        """

        if db_manager.db_type == 'sqlite':
            query = """
                SELECT
                    action,
                    COUNT(*) as count,
                    AVG(score) as avg_score
                FROM invoice_match_log
                WHERE created_at >= datetime('now', '-24 hours')
                GROUP BY action
                ORDER BY count DESC
            """

        try:
            result = db_manager.execute_query(query, fetch_all=True)
            for row in result:
                performance_stats['recent_activity'][row['action']] = {
                    'count': row['count'],
                    'avg_score': round(row['avg_score'], 2) if row['avg_score'] else 0
                }
        except Exception as e:
            logger.warning(f"Could not get recent activity stats: {e}")
            performance_stats['recent_activity'] = {}

        # Batch processing stats (if available)
        try:
            batch_query = """
                SELECT COUNT(*) as total_batches
                FROM invoice_match_log
                WHERE match_type LIKE '%BATCH%'
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
            """

            if db_manager.db_type == 'sqlite':
                batch_query = """
                    SELECT COUNT(*) as total_batches
                    FROM invoice_match_log
                    WHERE match_type LIKE '%BATCH%'
                    AND created_at >= datetime('now', '-7 days')
                """

            result = db_manager.execute_query(batch_query, fetch_one=True)
            performance_stats['batch_operations_last_week'] = result['total_batches'] if result else 0

        except Exception as e:
            logger.warning(f"Could not get batch stats: {e}")
            performance_stats['batch_operations_last_week'] = 0

        return jsonify({
            'success': True,
            'performance': performance_stats
        })

    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# TRANSACTION CHAIN API ENDPOINTS
# ============================================

# Import Transaction Chain Analyzer
try:
    from transaction_chain_analyzer import TransactionChainAnalyzer
    CHAIN_ANALYZER_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Transaction Chain Analyzer not available: {e}")
    CHAIN_ANALYZER_AVAILABLE = False

@app.route('/api/transactions/<transaction_id>/chains', methods=['GET'])
def api_get_transaction_chains(transaction_id):
    """Get intelligent transaction chains for a specific transaction"""
    if not CHAIN_ANALYZER_AVAILABLE:
        return jsonify({
            "error": "Transaction Chain Analyzer not available",
            "fallback_message": "Opening dashboard with transaction search instead"
        }), 503

    try:
        analyzer = TransactionChainAnalyzer()
        chains = analyzer.find_transaction_chains(transaction_id)

        # Add metadata for UI
        chains['api_version'] = '1.0'
        chains['timestamp'] = datetime.now().isoformat()

        return jsonify(chains)

    except Exception as e:
        logger.error(f"Error analyzing transaction chains for {transaction_id}: {e}")
        return jsonify({
            "error": str(e),
            "transaction_id": transaction_id,
            "fallback_action": "dashboard_search"
        }), 500

@app.route('/api/system/transaction-chains', methods=['GET'])
def api_get_system_transaction_chains():
    """Get system-wide transaction chain analysis"""
    if not CHAIN_ANALYZER_AVAILABLE:
        return jsonify({
            "error": "Transaction Chain Analyzer not available"
        }), 503

    try:
        limit = request.args.get('limit', 50, type=int)
        analyzer = TransactionChainAnalyzer()
        chains = analyzer.find_transaction_chains(limit=limit)

        # Add metadata
        chains['api_version'] = '1.0'
        chains['timestamp'] = datetime.now().isoformat()

        return jsonify(chains)

    except Exception as e:
        logger.error(f"Error analyzing system transaction chains: {e}")
        return jsonify({
            "error": str(e),
            "system_analysis": True
        }), 500

@app.route('/api/transactions/chains/stats', methods=['GET'])
def api_get_chain_stats():
    """Get transaction chain statistics and insights"""
    if not CHAIN_ANALYZER_AVAILABLE:
        return jsonify({
            "error": "Transaction Chain Analyzer not available"
        }), 503

    try:
        analyzer = TransactionChainAnalyzer()

        # Get system-wide analysis for statistics
        system_analysis = analyzer.find_transaction_chains(limit=100)

        if 'chains_detected' in system_analysis:
            chains = system_analysis.get('top_chains', [])
            pattern_distribution = system_analysis.get('pattern_distribution', {})

            stats = {
                'total_chains_detected': system_analysis['chains_detected'],
                'total_transactions_analyzed': system_analysis.get('total_transactions_analyzed', 0),
                'pattern_distribution': pattern_distribution,
                'top_patterns': sorted(pattern_distribution.items(), key=lambda x: x[1], reverse=True)[:5],
                'high_confidence_chains': len([c for c in chains if c.get('confidence', 0) > 0.8]),
                'medium_confidence_chains': len([c for c in chains if 0.6 <= c.get('confidence', 0) <= 0.8]),
                'low_confidence_chains': len([c for c in chains if c.get('confidence', 0) < 0.6]),
                'recommendations': system_analysis.get('recommendations', []),
                'last_analysis': datetime.now().isoformat()
            }
        else:
            stats = {
                'error': 'No chain analysis data available',
                'total_chains_detected': 0
            }

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting chain stats: {e}")
        return jsonify({
            "error": str(e)
        }), 500


if __name__ == '__main__':
    print("Starting Delta CFO Agent Web Interface (Database Mode)")
    print("Database backend enabled")

    # Initialize Claude API
    init_claude_client()

    # Initialize invoice tables
    init_invoice_tables()

    # Ensure background jobs tables exist
    ensure_background_jobs_tables()

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
    ensure_background_jobs_tables()
    print("[OK] Production initialization completed")
except Exception as e:
    print(f"WARNING: Production initialization warning: {e}")

