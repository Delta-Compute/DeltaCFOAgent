#!/usr/bin/env python3
"""
Delta CFO Agent - Analytics Microservice
=====================================

Advanced analytics service for financial data insights and reporting.
Provides REST API endpoints for business intelligence and data visualization.
"""

import os
import sys
from flask import Flask, request, jsonify, render_template
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import json
from pathlib import Path

# Add parent directories to path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent.parent))

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Configuration
DATABASE_PATH = os.environ.get('DATABASE_PATH', '../../web_ui/delta_transactions.db')
PORT = int(os.environ.get('PORT', 8080))
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

class AnalyticsEngine:
    """Core analytics engine for financial data processing"""

    def __init__(self):
        self.db_path = DATABASE_PATH

    def get_db_connection(self):
        """Get database connection"""
        try:
            # Check if database file exists
            if not os.path.exists(self.db_path):
                print(f"⚠️ Database not found at {self.db_path}")
                # Create empty database for testing
                conn = sqlite3.connect(self.db_path)
                conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    date TEXT,
                    description TEXT,
                    amount REAL,
                    entity TEXT,
                    category TEXT
                )''')
                conn.commit()
                print(f"✅ Created empty database at {self.db_path}")
            else:
                conn = sqlite3.connect(self.db_path)

            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

    def get_monthly_summary(self, months=12):
        """Get monthly transaction summary"""
        conn = self.get_db_connection()
        if not conn:
            return {"error": "Database connection failed"}

        try:
            query = """
            SELECT
                DATE(date, 'start of month') as month,
                entity,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                SUM(amount) as net_flow,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE date >= date('now', '-{} months')
            GROUP BY month, entity
            ORDER BY month DESC, entity
            """.format(months)

            df = pd.read_sql_query(query, conn)
            conn.close()

            # Convert to JSON-friendly format
            result = {
                'summary': df.to_dict('records'),
                'total_months': months,
                'generated_at': datetime.now().isoformat()
            }

            return result

        except Exception as e:
            conn.close()
            return {"error": f"Query failed: {str(e)}"}

    def get_entity_breakdown(self):
        """Get transaction breakdown by business entity"""
        conn = self.get_db_connection()
        if not conn:
            return {"error": "Database connection failed"}

        try:
            query = """
            SELECT
                entity,
                COUNT(*) as total_transactions,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expenses,
                SUM(amount) as net_position,
                AVG(amount) as avg_transaction_size,
                MIN(date) as first_transaction,
                MAX(date) as last_transaction
            FROM transactions
            GROUP BY entity
            ORDER BY total_transactions DESC
            """

            df = pd.read_sql_query(query, conn)
            conn.close()

            result = {
                'entities': df.to_dict('records'),
                'generated_at': datetime.now().isoformat()
            }

            return result

        except Exception as e:
            conn.close()
            return {"error": f"Query failed: {str(e)}"}

    def get_category_analysis(self):
        """Analyze spending by category"""
        conn = self.get_db_connection()
        if not conn:
            return {"error": "Database connection failed"}

        try:
            query = """
            SELECT
                category,
                entity,
                COUNT(*) as transaction_count,
                SUM(ABS(amount)) as total_amount,
                AVG(ABS(amount)) as avg_amount,
                SUM(CASE WHEN amount > 0 THEN 1 ELSE 0 END) as income_transactions,
                SUM(CASE WHEN amount < 0 THEN 1 ELSE 0 END) as expense_transactions
            FROM transactions
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category, entity
            ORDER BY total_amount DESC
            LIMIT 50
            """

            df = pd.read_sql_query(query, conn)
            conn.close()

            result = {
                'categories': df.to_dict('records'),
                'generated_at': datetime.now().isoformat()
            }

            return result

        except Exception as e:
            conn.close()
            return {"error": f"Query failed: {str(e)}"}

# Initialize analytics engine
analytics = AnalyticsEngine()

@app.route('/')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'service': 'Delta CFO Analytics Service',
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/analytics/monthly-summary')
def monthly_summary():
    """Get monthly transaction summary"""
    months = request.args.get('months', 12, type=int)
    months = min(max(months, 1), 24)  # Limit between 1-24 months

    result = analytics.get_monthly_summary(months)
    return jsonify(result)

@app.route('/api/analytics/entities')
def entity_breakdown():
    """Get transaction breakdown by business entity"""
    result = analytics.get_entity_breakdown()
    return jsonify(result)

@app.route('/api/analytics/categories')
def category_analysis():
    """Get spending analysis by category"""
    result = analytics.get_category_analysis()
    return jsonify(result)

@app.route('/api/analytics/dashboard')
def dashboard_data():
    """Get comprehensive dashboard data"""
    try:
        # Combine multiple analytics
        monthly = analytics.get_monthly_summary(6)  # Last 6 months
        entities = analytics.get_entity_breakdown()
        categories = analytics.get_category_analysis()

        dashboard = {
            'monthly_summary': monthly,
            'entity_breakdown': entities,
            'category_analysis': categories,
            'generated_at': datetime.now().isoformat(),
            'service_info': {
                'name': 'Delta CFO Analytics Service',
                'version': '1.0.0'
            }
        }

        return jsonify(dashboard)

    except Exception as e:
        return jsonify({'error': f'Dashboard generation failed: {str(e)}'}), 500

@app.route('/api/analytics/status')
def service_status():
    """Get service status and database connectivity"""
    try:
        conn = analytics.get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transactions")
            transaction_count = cursor.fetchone()[0]
            conn.close()

            return jsonify({
                'service': 'analytics-service',
                'status': 'operational',
                'database': 'connected',
                'transaction_count': transaction_count,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'service': 'analytics-service',
                'status': 'degraded',
                'database': 'disconnected',
                'timestamp': datetime.now().isoformat()
            }), 503

    except Exception as e:
        return jsonify({
            'service': 'analytics-service',
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': [
            '/api/analytics/monthly-summary',
            '/api/analytics/entities',
            '/api/analytics/categories',
            '/api/analytics/dashboard',
            '/api/analytics/status'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': 'Analytics service encountered an error'
    }), 500

if __name__ == '__main__':
    print(f"🚀 Starting Delta CFO Analytics Service on port {PORT}")
    print(f"📊 Database: {DATABASE_PATH}")
    print(f"🔧 Debug mode: {DEBUG}")

    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=DEBUG,
        threaded=True
    )