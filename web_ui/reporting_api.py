#!/usr/bin/env python3
"""
CFO Reporting API Endpoints
Flask routes for financial statements and reporting functionality
"""

import os
import sys
import json
import logging
from datetime import datetime, date, timedelta
from flask import request, jsonify, send_file
from decimal import Decimal
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.colors import HexColor

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reporting.financial_statements import FinancialStatementsGenerator
from database import db_manager

logger = logging.getLogger(__name__)


def register_reporting_routes(app):
    """Register all CFO reporting routes with the Flask app"""

    @app.route('/api/reports/income-statement', methods=['GET', 'POST'])
    def api_income_statement():
        """
        Generate Income Statement (P&L)

        GET Parameters:
            - start_date: Start date (YYYY-MM-DD or MM/DD/YYYY)
            - end_date: End date (YYYY-MM-DD or MM/DD/YYYY)
            - period_id: Accounting period ID (optional)
            - include_details: Include transaction details (true/false)
            - comparison_period_id: Period to compare against (optional)

        Returns:
            JSON with complete Income Statement data
        """
        try:
            # Parse parameters
            start_date_str = request.args.get('start_date') or request.json.get('start_date') if request.method == 'POST' else None
            end_date_str = request.args.get('end_date') or request.json.get('end_date') if request.method == 'POST' else None
            period_id = request.args.get('period_id') or request.json.get('period_id') if request.method == 'POST' else None
            include_details = request.args.get('include_details', 'false').lower() == 'true' or \
                            (request.json.get('include_details', False) if request.method == 'POST' else False)
            comparison_period_id = request.args.get('comparison_period_id') or \
                                 (request.json.get('comparison_period_id') if request.method == 'POST' else None)

            # Parse dates
            start_date = None
            end_date = None

            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        start_date = datetime.strptime(start_date_str, '%m/%d/%Y').date()
                    except ValueError:
                        return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD or MM/DD/YYYY'}), 400

            if end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        end_date = datetime.strptime(end_date_str, '%m/%d/%Y').date()
                    except ValueError:
                        return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD or MM/DD/YYYY'}), 400

            # Generate statement
            generator = FinancialStatementsGenerator()

            statement = generator.generate_income_statement(
                period_id=int(period_id) if period_id else None,
                start_date=start_date,
                end_date=end_date,
                comparison_period_id=int(comparison_period_id) if comparison_period_id else None,
                include_details=include_details
            )

            return jsonify({
                'success': True,
                'statement': statement
            })

        except Exception as e:
            logger.error(f"Error generating income statement: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/income-statement/simple', methods=['GET'])
    def api_income_statement_simple():
        """
        Generate simplified Income Statement using direct SQL (fast)
        This endpoint uses the optimized query approach from test_pl_simple.py

        Returns:
            JSON with simplified P&L data
        """
        try:
            start_time = datetime.now()

            # Revenue: All positive amounts
            revenue_query = """
                SELECT
                    COALESCE(accounting_category, classified_entity, 'Uncategorized Revenue') as category,
                    SUM(COALESCE(usd_equivalent, amount, 0)) as total,
                    COUNT(*) as count
                FROM transactions
                WHERE amount > 0
                GROUP BY COALESCE(accounting_category, classified_entity, 'Uncategorized Revenue')
                ORDER BY total DESC
            """
            revenue_data = db_manager.execute_query(revenue_query, fetch_all=True)

            total_revenue = Decimal('0')
            revenue_categories = []

            for row in revenue_data:
                amount = Decimal(str(row['total'] or 0))
                revenue_categories.append({
                    'category': row['category'],
                    'amount': float(amount),
                    'count': row['count']
                })
                total_revenue += amount

            # Operating Expenses: All negative amounts
            opex_query = """
                SELECT
                    COALESCE(accounting_category, classified_entity, 'General & Administrative') as category,
                    SUM(ABS(COALESCE(usd_equivalent, amount, 0))) as total,
                    COUNT(*) as count
                FROM transactions
                WHERE amount < 0
                AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%material%'
                AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%inventory%'
                AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%manufacturing%'
                AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%production%'
                AND LOWER(COALESCE(accounting_category, '')) NOT LIKE '%supplier%'
                GROUP BY COALESCE(accounting_category, classified_entity, 'General & Administrative')
                ORDER BY total DESC
            """
            opex_data = db_manager.execute_query(opex_query, fetch_all=True)

            total_opex = Decimal('0')
            opex_categories = []

            for row in opex_data:
                amount = Decimal(str(row['total'] or 0))
                opex_categories.append({
                    'category': row['category'],
                    'amount': float(amount),
                    'count': row['count']
                })
                total_opex += amount

            # Calculate metrics
            gross_profit = total_revenue
            operating_income = gross_profit - total_opex
            net_income = operating_income

            gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
            operating_margin = (operating_income / total_revenue * 100) if total_revenue > 0 else 0
            net_margin = (net_income / total_revenue * 100) if total_revenue > 0 else 0

            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'statement': {
                    'statement_type': 'IncomeStatement',
                    'statement_name': 'Income Statement - All Periods',
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms,

                    'revenue': {
                        'total': float(total_revenue),
                        'categories': revenue_categories
                    },

                    'cost_of_goods_sold': {
                        'total': 0,
                        'categories': []
                    },

                    'gross_profit': {
                        'amount': float(gross_profit),
                        'margin_percent': round(float(gross_margin), 2)
                    },

                    'operating_expenses': {
                        'total': float(total_opex),
                        'categories': opex_categories
                    },

                    'operating_income': {
                        'amount': float(operating_income),
                        'margin_percent': round(float(operating_margin), 2)
                    },

                    'other_income_expenses': {
                        'total': 0,
                        'categories': []
                    },

                    'net_income': {
                        'amount': float(net_income),
                        'margin_percent': round(float(net_margin), 2)
                    },

                    'summary_metrics': {
                        'total_revenue': float(total_revenue),
                        'gross_profit': float(gross_profit),
                        'gross_margin_percent': round(float(gross_margin), 2),
                        'operating_income': float(operating_income),
                        'operating_margin_percent': round(float(operating_margin), 2),
                        'net_income': float(net_income),
                        'net_margin_percent': round(float(net_margin), 2),
                        'transaction_count': sum(c['count'] for c in revenue_categories) + sum(c['count'] for c in opex_categories)
                    }
                }
            })

        except Exception as e:
            logger.error(f"Error generating simplified income statement: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/balance-sheet/simple', methods=['GET'])
    def api_balance_sheet_simple():
        """
        Generate simplified Balance Sheet using direct SQL (fast)

        Returns:
            JSON with simplified Balance Sheet data
        """
        try:
            start_time = datetime.now()

            # Assets: All positive balances in balance sheet accounts or cash-related transactions
            assets_query = """
                SELECT
                    CASE
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%cash%' THEN 'Caixa e Equivalentes'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%receivable%' THEN 'Contas a Receber'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%inventory%' THEN 'Estoque'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%equipment%' THEN 'Equipamentos'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%asset%' THEN 'Outros Ativos'
                        ELSE 'Ativos Circulantes'
                    END as category,
                    SUM(COALESCE(usd_equivalent, amount, 0)) as total,
                    COUNT(*) as count
                FROM transactions
                WHERE (
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%cash%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%asset%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%receivable%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%inventory%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%equipment%' OR
                    (amount > 0 AND LOWER(COALESCE(description, '')) LIKE '%deposit%')
                )
                GROUP BY CASE
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%cash%' THEN 'Caixa e Equivalentes'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%receivable%' THEN 'Contas a Receber'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%inventory%' THEN 'Estoque'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%equipment%' THEN 'Equipamentos'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%asset%' THEN 'Outros Ativos'
                    ELSE 'Ativos Circulantes'
                END
                ORDER BY total DESC
            """
            assets_data = db_manager.execute_query(assets_query, fetch_all=True)

            total_assets = Decimal('0')
            assets_categories = []

            for row in assets_data:
                amount = Decimal(str(row['total'] or 0))
                if amount > 0:  # Only positive asset values
                    assets_categories.append({
                        'category': row['category'],
                        'amount': float(amount),
                        'count': row['count']
                    })
                    total_assets += amount

            # If no specific asset transactions, estimate current assets from revenue
            if total_assets == 0:
                revenue_query = """
                    SELECT SUM(COALESCE(usd_equivalent, amount, 0)) as total_revenue
                    FROM transactions
                    WHERE amount > 0
                """
                revenue_result = db_manager.execute_query(revenue_query, fetch_one=True)
                estimated_assets = Decimal(str(revenue_result['total_revenue'] or 0)) * Decimal('0.3')  # Estimate 30% of revenue as assets

                if estimated_assets > 0:
                    assets_categories.append({
                        'category': 'Ativos Estimados (30% da Receita)',
                        'amount': float(estimated_assets),
                        'count': 1
                    })
                    total_assets = estimated_assets

            # Liabilities: All negative balances that represent actual debts/obligations
            liabilities_query = """
                SELECT
                    CASE
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%payable%' THEN 'Contas a Pagar'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%loan%' THEN 'Empréstimos'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%debt%' THEN 'Dívidas'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%liability%' THEN 'Outros Passivos'
                        WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%tax%' THEN 'Impostos a Pagar'
                        ELSE 'Passivos Circulantes'
                    END as category,
                    SUM(ABS(COALESCE(usd_equivalent, amount, 0))) as total,
                    COUNT(*) as count
                FROM transactions
                WHERE (
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%payable%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%loan%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%debt%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%liability%' OR
                    LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%tax%' OR
                    (amount < 0 AND LOWER(COALESCE(description, '')) LIKE '%payment%')
                ) AND amount < 0
                GROUP BY CASE
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%payable%' THEN 'Contas a Pagar'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%loan%' THEN 'Empréstimos'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%debt%' THEN 'Dívidas'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%liability%' THEN 'Outros Passivos'
                    WHEN LOWER(COALESCE(accounting_category, classified_entity, '')) LIKE '%tax%' THEN 'Impostos a Pagar'
                    ELSE 'Passivos Circulantes'
                END
                ORDER BY total DESC
            """
            liabilities_data = db_manager.execute_query(liabilities_query, fetch_all=True)

            total_liabilities = Decimal('0')
            liabilities_categories = []

            for row in liabilities_data:
                amount = Decimal(str(row['total'] or 0))
                if amount > 0:  # Only positive liability values (absolute)
                    liabilities_categories.append({
                        'category': row['category'],
                        'amount': float(amount),
                        'count': row['count']
                    })
                    total_liabilities += amount

            # Calculate Equity (Assets - Liabilities)
            total_equity = total_assets - total_liabilities

            # Ensure balance
            if abs(total_assets - (total_liabilities + total_equity)) > Decimal('0.01'):
                # Adjust equity to balance
                total_equity = total_assets - total_liabilities

            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'statement': {
                    'statement_type': 'BalanceSheet',
                    'statement_name': 'Balanço Patrimonial - Todos os Períodos',
                    'generated_at': datetime.now().isoformat(),
                    'generation_time_ms': generation_time_ms,

                    'assets': {
                        'current_assets': {
                            'total': float(total_assets),
                            'categories': assets_categories
                        },
                        'non_current_assets': {
                            'total': 0,
                            'categories': []
                        },
                        'total': float(total_assets)
                    },

                    'liabilities': {
                        'current_liabilities': {
                            'total': float(total_liabilities),
                            'categories': liabilities_categories
                        },
                        'non_current_liabilities': {
                            'total': 0,
                            'categories': []
                        },
                        'total': float(total_liabilities)
                    },

                    'equity': {
                        'total': float(total_equity),
                        'categories': [
                            {
                                'category': 'Patrimônio Líquido Acumulado',
                                'amount': float(total_equity),
                                'count': 1
                            }
                        ]
                    },

                    'summary_metrics': {
                        'total_assets': float(total_assets),
                        'total_liabilities': float(total_liabilities),
                        'total_equity': float(total_equity),
                        'debt_to_equity_ratio': float(total_liabilities / total_equity) if total_equity != 0 else 0,
                        'asset_turnover': 0,  # Would need revenue data for calculation
                        'balance_check': abs(float(total_assets - (total_liabilities + total_equity))) < 0.01
                    }
                }
            })

        except Exception as e:
            logger.error(f"Error generating simplified balance sheet: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/periods', methods=['GET'])
    def api_accounting_periods():
        """
        Get list of accounting periods

        GET Parameters:
            - year: Filter by fiscal year (optional)
            - period_type: Filter by type (Monthly, Quarterly, Yearly) (optional)
            - status: Filter by status (Open, Closed, Locked) (optional)

        Returns:
            JSON with list of accounting periods
        """
        try:
            year = request.args.get('year')
            period_type = request.args.get('period_type')
            status = request.args.get('status')

            # Build query
            query = "SELECT * FROM cfo_accounting_periods WHERE 1=1"
            params = []

            if year:
                query += " AND fiscal_year = %s" if db_manager.db_type == 'postgresql' else " AND fiscal_year = ?"
                params.append(int(year))

            if period_type:
                query += " AND period_type = %s" if db_manager.db_type == 'postgresql' else " AND period_type = ?"
                params.append(period_type)

            if status:
                query += " AND status = %s" if db_manager.db_type == 'postgresql' else " AND status = ?"
                params.append(status)

            query += " ORDER BY start_date DESC"

            periods = db_manager.execute_query(query, tuple(params) if params else None, fetch_all=True)

            return jsonify({
                'success': True,
                'periods': [dict(p) for p in periods]
            })

        except Exception as e:
            logger.error(f"Error fetching accounting periods: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/chart-of-accounts', methods=['GET'])
    def api_chart_of_accounts():
        """
        Get chart of accounts

        GET Parameters:
            - account_type: Filter by type (Asset, Liability, Equity, Revenue, Expense) (optional)
            - is_active: Filter by active status (true/false) (optional)

        Returns:
            JSON with chart of accounts
        """
        try:
            account_type = request.args.get('account_type')
            is_active = request.args.get('is_active')

            # Build query
            query = "SELECT * FROM cfo_chart_of_accounts WHERE 1=1"
            params = []

            if account_type:
                query += " AND account_type = %s" if db_manager.db_type == 'postgresql' else " AND account_type = ?"
                params.append(account_type)

            if is_active is not None:
                if db_manager.db_type == 'postgresql':
                    query += " AND is_active = %s"
                    params.append(is_active.lower() == 'true')
                else:
                    query += " AND is_active = ?"
                    params.append(1 if is_active.lower() == 'true' else 0)

            query += " ORDER BY account_code"

            accounts = db_manager.execute_query(query, tuple(params) if params else None, fetch_all=True)

            return jsonify({
                'success': True,
                'accounts': [dict(a) for a in accounts]
            })

        except Exception as e:
            logger.error(f"Error fetching chart of accounts: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reports/health', methods=['GET'])
    def api_reports_health():
        """Health check for reporting system"""
        try:
            # Check database
            db_health = db_manager.health_check()

            # Check CFO tables
            table_check_query = """
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE 'cfo_%'
            """ if db_manager.db_type == 'postgresql' else """
                SELECT COUNT(*) as count
                FROM sqlite_master
                WHERE type='table'
                AND name LIKE 'cfo_%'
            """

            result = db_manager.execute_query(table_check_query, fetch_one=True)
            cfo_tables_count = result['count']

            # Check data
            periods_query = "SELECT COUNT(*) as count FROM cfo_accounting_periods"
            periods_result = db_manager.execute_query(periods_query, fetch_one=True)

            accounts_query = "SELECT COUNT(*) as count FROM cfo_chart_of_accounts"
            accounts_result = db_manager.execute_query(accounts_query, fetch_one=True)

            statements_query = "SELECT COUNT(*) as count FROM cfo_financial_statements"
            statements_result = db_manager.execute_query(statements_query, fetch_one=True)

            return jsonify({
                'success': True,
                'health': {
                    'database': db_health,
                    'cfo_tables_count': cfo_tables_count,
                    'data': {
                        'accounting_periods': periods_result['count'],
                        'chart_of_accounts': accounts_result['count'],
                        'financial_statements': statements_result['count']
                    },
                    'status': 'healthy' if cfo_tables_count == 8 else 'degraded'
                }
            })

        except Exception as e:
            logger.error(f"Error in reports health check: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'status': 'unhealthy'
            }), 500

    @app.route('/api/reports/charts-data', methods=['GET'])
    def api_charts_data():
        """
        Endpoint otimizado para dados de gráficos - versão robusta

        Returns:
            JSON com dados prontos para Chart.js
        """
        try:
            start_time = datetime.now()

            # Initialize default fallback data
            default_charts_data = {
                'revenue_expenses': {
                    'labels': ['Receitas', 'Despesas'],
                    'data': [0, 0],
                    'net_income': 0
                },
                'categories': {
                    'labels': ['Uncategorized'],
                    'data': [0],
                    'counts': [0]
                },
                'monthly_trend': {
                    'labels': ['Current'],
                    'revenue_data': [0],
                    'expenses_data': [0],
                    'margin_data': [0]
                },
                'summary': {
                    'total_revenue': 0,
                    'total_expenses': 0,
                    'current_margin': 0,
                    'transactions_count': 0
                }
            }

            # Safe query execution function
            def safe_query(query, fetch_all=False):
                try:
                    if fetch_all:
                        result = db_manager.execute_query(query, fetch_all=True)
                        return result if result else []
                    else:
                        result = db_manager.execute_query(query, fetch_one=True)
                        return result if result else {}
                except Exception as query_error:
                    logger.warning(f"Query failed safely: {query_error}")
                    return [] if fetch_all else {}

            # Revenue vs Expenses data
            revenue_expenses_query = """
                SELECT
                    'Revenue' as type,
                    COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as amount
                FROM transactions
                UNION ALL
                SELECT
                    'Expenses' as type,
                    COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) as amount
                FROM transactions
            """
            revenue_expenses_data = safe_query(revenue_expenses_query, fetch_all=True)

            # Top revenue categories
            categories_query = """
                SELECT
                    COALESCE(accounting_category, classified_entity, 'Uncategorized') as category,
                    COALESCE(SUM(amount), 0) as amount,
                    COUNT(*) as count
                FROM transactions
                WHERE amount > 0
                GROUP BY COALESCE(accounting_category, classified_entity, 'Uncategorized')
                ORDER BY amount DESC
                LIMIT 8
            """
            categories_data = safe_query(categories_query, fetch_all=True)

            # Monthly trend data (last 6 months) - simplified query for SQLite compatibility
            monthly_trend_query = """
                SELECT
                    strftime('%Y-%m', date) as month,
                    COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as revenue,
                    COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) as expenses
                FROM transactions
                WHERE date >= date('now', '-6 months')
                GROUP BY strftime('%Y-%m', date)
                ORDER BY month
            """ if db_manager.db_type == 'sqlite' else """
                SELECT
                    DATE_TRUNC('month', date) as month,
                    COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as revenue,
                    COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) as expenses
                FROM transactions
                WHERE date >= CURRENT_DATE - INTERVAL '6 months'
                GROUP BY DATE_TRUNC('month', date)
                ORDER BY month
            """
            monthly_data = safe_query(monthly_trend_query, fetch_all=True)

            # Calculate margins for monthly data
            monthly_margins = []
            for row in monthly_data:
                try:
                    revenue = float(row.get('revenue', 0) or 0)
                    expenses = float(row.get('expenses', 0) or 0)
                    net_income = revenue - expenses
                    margin = (net_income / revenue * 100) if revenue > 0 else 0

                    # Handle different month formats
                    month_display = 'Unknown'
                    if row.get('month'):
                        if isinstance(row['month'], str):
                            # For SQLite: '2025-10' format
                            try:
                                month_obj = datetime.strptime(row['month'], '%Y-%m')
                                month_display = month_obj.strftime('%b %Y')
                            except:
                                month_display = row['month']
                        else:
                            # For PostgreSQL: datetime object
                            month_display = row['month'].strftime('%b %Y')

                    monthly_margins.append({
                        'month': month_display,
                        'revenue': revenue,
                        'expenses': expenses,
                        'net_income': net_income,
                        'margin_percent': round(margin, 2)
                    })
                except Exception as row_error:
                    logger.warning(f"Error processing monthly row: {row_error}")
                    continue

            # Format data for charts with safe access
            try:
                revenue_amount = float(revenue_expenses_data[0].get('amount', 0) or 0) if len(revenue_expenses_data) > 0 else 0
                expenses_amount = float(revenue_expenses_data[1].get('amount', 0) or 0) if len(revenue_expenses_data) > 1 else 0
            except (IndexError, TypeError, ValueError):
                revenue_amount = 0
                expenses_amount = 0

            charts_data = {
                'revenue_expenses': {
                    'labels': ['Receitas', 'Despesas'],
                    'data': [revenue_amount, expenses_amount],
                    'net_income': revenue_amount - expenses_amount
                },

                'categories': {
                    'labels': [row.get('category', 'Unknown') for row in categories_data] if categories_data else ['No Data'],
                    'data': [float(row.get('amount', 0) or 0) for row in categories_data] if categories_data else [0],
                    'counts': [int(row.get('count', 0) or 0) for row in categories_data] if categories_data else [0]
                },

                'monthly_trend': {
                    'labels': [item['month'] for item in monthly_margins] if monthly_margins else ['Current'],
                    'revenue_data': [item['revenue'] for item in monthly_margins] if monthly_margins else [0],
                    'expenses_data': [item['expenses'] for item in monthly_margins] if monthly_margins else [0],
                    'margin_data': [item['margin_percent'] for item in monthly_margins] if monthly_margins else [0]
                },

                'summary': {
                    'total_revenue': sum([item['revenue'] for item in monthly_margins]) if monthly_margins else 0,
                    'total_expenses': sum([item['expenses'] for item in monthly_margins]) if monthly_margins else 0,
                    'current_margin': monthly_margins[-1]['margin_percent'] if monthly_margins else 0,
                    'transactions_count': sum([row.get('count', 0) for row in categories_data]) if categories_data else 0
                }
            }

            # Ensure all data is valid
            if not charts_data['categories']['data'] or all(x == 0 for x in charts_data['categories']['data']):
                charts_data = default_charts_data

            end_time = datetime.now()
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return jsonify({
                'success': True,
                'data': charts_data,
                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': generation_time_ms
            })

        except Exception as e:
            logger.error(f"Error generating charts data: {e}")
            import traceback
            traceback.print_exc()

            # Return fallback data instead of 500 error
            return jsonify({
                'success': True,
                'data': {
                    'revenue_expenses': {
                        'labels': ['Receitas', 'Despesas'],
                        'data': [0, 0],
                        'net_income': 0
                    },
                    'categories': {
                        'labels': ['No Data Available'],
                        'data': [1],
                        'counts': [0]
                    },
                    'monthly_trend': {
                        'labels': ['Current'],
                        'revenue_data': [0],
                        'expenses_data': [0],
                        'margin_data': [0]
                    },
                    'summary': {
                        'total_revenue': 0,
                        'total_expenses': 0,
                        'current_margin': 0,
                        'transactions_count': 0
                    }
                },
                'generated_at': datetime.now().isoformat(),
                'generation_time_ms': 0,
                'fallback': True,
                'original_error': str(e)
            })

    @app.route('/api/reports/export-pdf', methods=['POST'])
    def api_export_pdf():
        """
        Export financial reports to PDF format

        POST Parameters (JSON):
            - report_type: Type of report ('income-statement', 'balance-sheet', etc.)
            - start_date: Start date for the report (optional)
            - end_date: End date for the report (optional)
            - include_charts: Include chart images (boolean, default: false)

        Returns:
            PDF file download
        """
        try:
            data = request.get_json()
            report_type = data.get('report_type', 'income-statement')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            include_charts = data.get('include_charts', False)

            # Parse dates if provided
            start_date_obj = None
            end_date_obj = None

            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                except ValueError:
                    start_date_obj = datetime.strptime(start_date, '%m/%d/%Y').date()

            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                except ValueError:
                    end_date_obj = datetime.strptime(end_date, '%m/%d/%Y').date()

            # Generate the requested report type
            if report_type == 'income-statement':
                # Use the simplified income statement endpoint for income statement data
                response = api_income_statement_simple()
                if response.status_code != 200:
                    return response

                income_statement_data = response.get_json()['statement']

                # Generate PDF
                pdf_buffer = generate_income_statement_pdf(income_statement_data)

                # Create filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"DeltaCFO_IncomeStatement_{timestamp}.pdf"

                return send_file(
                    pdf_buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/pdf'
                )

            elif report_type == 'balance-sheet':
                # Use the simplified balance sheet endpoint for balance sheet data
                response = api_balance_sheet_simple()
                if response.status_code != 200:
                    return response

                balance_sheet_data = response.get_json()['statement']

                # Generate PDF
                pdf_buffer = generate_balance_sheet_pdf(balance_sheet_data)

                # Create filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"DeltaCFO_BalanceSheet_{timestamp}.pdf"

                return send_file(
                    pdf_buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/pdf'
                )
            else:
                return jsonify({
                    'success': False,
                    'error': f'Report type "{report_type}" not yet supported'
                }), 400

        except Exception as e:
            logger.error(f"Error exporting PDF: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def generate_income_statement_pdf(statement_data):
        """Generate a professional PDF for income statement"""

        # Create a buffer to hold the PDF data
        buffer = io.BytesIO()

        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=HexColor('#2563eb'),
            spaceAfter=30,
            alignment=1  # Center alignment
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#374151'),
            spaceAfter=20,
            alignment=1
        )

        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=HexColor('#1f2937'),
            spaceAfter=10,
            spaceBefore=15
        )

        # Build the content
        content = []

        # Header
        content.append(Paragraph("Delta CFO Agent", title_style))
        content.append(Paragraph(
            statement_data.get('statement_name', 'Demonstração de Resultado'),
            subtitle_style
        ))

        # Generation info
        generated_at = datetime.now().strftime('%d/%m/%Y às %H:%M')
        content.append(Paragraph(f"Gerado em: {generated_at}", styles['Normal']))
        content.append(Spacer(1, 20))

        # Summary metrics (if available)
        if statement_data.get('summary_metrics'):
            metrics = statement_data['summary_metrics']
            content.append(Paragraph("📊 Resumo Executivo", section_style))

            metrics_data = [
                ['Métrica', 'Valor'],
                ['Receita Total', f"${metrics.get('total_revenue', 0):,.2f}"],
                ['Lucro Operacional', f"${metrics.get('operating_income', 0):,.2f}"],
                ['Lucro Líquido', f"${metrics.get('net_income', 0):,.2f}"],
                ['Margem Líquida', f"{metrics.get('net_margin_percent', 0):.1f}%"],
                ['Total de Transações', f"{metrics.get('transaction_count', 0):,}"]
            ]

            metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#1f2937')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#e5e7eb'))
            ]))

            content.append(metrics_table)
            content.append(Spacer(1, 20))

        # Revenue section
        if statement_data.get('revenue'):
            content.append(Paragraph("💰 RECEITAS", section_style))

            revenue_data = [['Categoria', 'Valor']]
            for category in statement_data['revenue'].get('categories', []):
                revenue_data.append([
                    category.get('category', 'N/A'),
                    f"${category.get('amount', 0):,.2f}"
                ])

            # Add total
            revenue_data.append([
                'TOTAL DE RECEITAS',
                f"${statement_data['revenue'].get('total', 0):,.2f}"
            ])

            revenue_table = Table(revenue_data, colWidths=[3.5*inch, 1.5*inch])
            revenue_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#dcfce7')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#166534')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, -1), (-1, -1), HexColor('#f0fdf4')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, HexColor('#16a34a')),
                ('GRID', (0, 0), (-1, -2), 0.5, HexColor('#bbf7d0'))
            ]))

            content.append(revenue_table)
            content.append(Spacer(1, 15))

        # Operating expenses section
        if statement_data.get('operating_expenses'):
            content.append(Paragraph("💸 DESPESAS OPERACIONAIS", section_style))

            expenses_data = [['Categoria', 'Valor']]
            for category in statement_data['operating_expenses'].get('categories', []):
                expenses_data.append([
                    category.get('category', 'N/A'),
                    f"${category.get('amount', 0):,.2f}"
                ])

            # Add total
            expenses_data.append([
                'TOTAL DE DESPESAS OPERACIONAIS',
                f"${statement_data['operating_expenses'].get('total', 0):,.2f}"
            ])

            expenses_table = Table(expenses_data, colWidths=[3.5*inch, 1.5*inch])
            expenses_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#fee2e2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#991b1b')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, -1), (-1, -1), HexColor('#fef2f2')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, HexColor('#dc2626')),
                ('GRID', (0, 0), (-1, -2), 0.5, HexColor('#fecaca'))
            ]))

            content.append(expenses_table)
            content.append(Spacer(1, 15))

        # Net income section
        if statement_data.get('net_income'):
            content.append(Paragraph("📈 RESULTADO LÍQUIDO", section_style))

            net_income = statement_data['net_income']
            result_data = [
                ['Lucro Operacional', f"${statement_data.get('operating_income', {}).get('amount', 0):,.2f}"],
                ['Outras Receitas/Despesas', f"${statement_data.get('other_income_expenses', {}).get('total', 0):,.2f}"],
                ['LUCRO LÍQUIDO', f"${net_income.get('amount', 0):,.2f}"],
                ['Margem Líquida', f"{net_income.get('margin_percent', 0):.1f}%"]
            ]

            result_table = Table(result_data, colWidths=[3.5*inch, 1.5*inch])
            result_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, -2), (-1, -1), HexColor('#eff6ff')),
                ('TEXTCOLOR', (0, -2), (-1, -1), HexColor('#1e40af')),
                ('LINEABOVE', (0, -2), (-1, -2), 2, HexColor('#3b82f6')),
                ('GRID', (0, 0), (-1, -3), 0.5, HexColor('#e5e7eb'))
            ]))

            content.append(result_table)
            content.append(Spacer(1, 20))

        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=HexColor('#6b7280'),
            alignment=1
        )

        generation_time = statement_data.get('generation_time_ms', 0)
        content.append(Paragraph(
            f"Relatório gerado automaticamente pela Delta CFO Agent em {generation_time}ms | "
            f"Delta's proprietary self improving AI CFO Agent",
            footer_style
        ))

        # Build PDF
        doc.build(content)
        buffer.seek(0)
        return buffer

    def generate_balance_sheet_pdf(statement_data):
        """Generate a professional PDF for balance sheet"""

        # Create a buffer to hold the PDF data
        buffer = io.BytesIO()

        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=HexColor('#2563eb'),
            spaceAfter=30,
            alignment=1  # Center alignment
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#374151'),
            spaceAfter=20,
            alignment=1
        )

        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=HexColor('#1f2937'),
            spaceAfter=10,
            spaceBefore=15
        )

        # Build the content
        content = []

        # Header
        content.append(Paragraph("Delta CFO Agent", title_style))
        content.append(Paragraph(
            statement_data.get('statement_name', 'Balanço Patrimonial'),
            subtitle_style
        ))

        # Generation info
        generated_at = datetime.now().strftime('%d/%m/%Y às %H:%M')
        content.append(Paragraph(f"Gerado em: {generated_at}", styles['Normal']))
        content.append(Spacer(1, 20))

        # Summary metrics (if available)
        if statement_data.get('summary_metrics'):
            metrics = statement_data['summary_metrics']
            content.append(Paragraph("📊 Resumo Executivo", section_style))

            metrics_data = [
                ['Métrica', 'Valor'],
                ['Total de Ativos', f"${metrics.get('total_assets', 0):,.2f}"],
                ['Total de Passivos', f"${metrics.get('total_liabilities', 0):,.2f}"],
                ['Patrimônio Líquido', f"${metrics.get('total_equity', 0):,.2f}"],
                ['Índice de Endividamento', f"{metrics.get('debt_to_equity_ratio', 0):.2f}"],
                ['Balanceamento', '✓' if metrics.get('balance_check', False) else '✗']
            ]

            metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#1f2937')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#e5e7eb'))
            ]))

            content.append(metrics_table)
            content.append(Spacer(1, 20))

        # Assets section
        if statement_data.get('assets'):
            content.append(Paragraph("🏛️ ATIVOS", section_style))

            assets_data = [['Categoria', 'Valor']]

            # Current assets
            current_assets = statement_data['assets'].get('current_assets', {})
            for category in current_assets.get('categories', []):
                assets_data.append([
                    category.get('category', 'N/A'),
                    f"${category.get('amount', 0):,.2f}"
                ])

            # Add total
            assets_data.append([
                'TOTAL DE ATIVOS',
                f"${statement_data['assets'].get('total', 0):,.2f}"
            ])

            assets_table = Table(assets_data, colWidths=[3.5*inch, 1.5*inch])
            assets_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#dbeafe')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#1e40af')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, -1), (-1, -1), HexColor('#f0f9ff')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, HexColor('#3b82f6')),
                ('GRID', (0, 0), (-1, -2), 0.5, HexColor('#bfdbfe'))
            ]))

            content.append(assets_table)
            content.append(Spacer(1, 15))

        # Liabilities section
        if statement_data.get('liabilities'):
            content.append(Paragraph("📋 PASSIVOS", section_style))

            liabilities_data = [['Categoria', 'Valor']]

            # Current liabilities
            current_liabilities = statement_data['liabilities'].get('current_liabilities', {})
            for category in current_liabilities.get('categories', []):
                liabilities_data.append([
                    category.get('category', 'N/A'),
                    f"${category.get('amount', 0):,.2f}"
                ])

            # Add total
            liabilities_data.append([
                'TOTAL DE PASSIVOS',
                f"${statement_data['liabilities'].get('total', 0):,.2f}"
            ])

            liabilities_table = Table(liabilities_data, colWidths=[3.5*inch, 1.5*inch])
            liabilities_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#fef3c7')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#92400e')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, -1), (-1, -1), HexColor('#fffbeb')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, HexColor('#d97706')),
                ('GRID', (0, 0), (-1, -2), 0.5, HexColor('#fde68a'))
            ]))

            content.append(liabilities_table)
            content.append(Spacer(1, 15))

        # Equity section
        if statement_data.get('equity'):
            content.append(Paragraph("💎 PATRIMÔNIO LÍQUIDO", section_style))

            equity_data = [['Categoria', 'Valor']]

            for category in statement_data['equity'].get('categories', []):
                equity_data.append([
                    category.get('category', 'N/A'),
                    f"${category.get('amount', 0):,.2f}"
                ])

            # Add total
            equity_data.append([
                'TOTAL DO PATRIMÔNIO LÍQUIDO',
                f"${statement_data['equity'].get('total', 0):,.2f}"
            ])

            equity_table = Table(equity_data, colWidths=[3.5*inch, 1.5*inch])
            equity_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#d1fae5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#065f46')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, -1), (-1, -1), HexColor('#ecfdf5')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, HexColor('#10b981')),
                ('GRID', (0, 0), (-1, -2), 0.5, HexColor('#a7f3d0'))
            ]))

            content.append(equity_table)
            content.append(Spacer(1, 20))

        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=HexColor('#6b7280'),
            alignment=1
        )

        generation_time = statement_data.get('generation_time_ms', 0)
        content.append(Paragraph(
            f"Relatório gerado automaticamente pela Delta CFO Agent em {generation_time}ms | "
            f"Delta's proprietary self improving AI CFO Agent",
            footer_style
        ))

        # Build PDF
        doc.build(content)
        buffer.seek(0)
        return buffer

    @app.route('/api/reports/period-comparison', methods=['GET', 'POST'])
    def api_period_comparison():
        """
        Compare financial metrics between two periods

        Parameters:
            - current_start_date: Start date for current period
            - current_end_date: End date for current period
            - previous_start_date: Start date for previous period
            - previous_end_date: End date for previous period
            - comparison_type: 'month_over_month', 'quarter_over_quarter', 'year_over_year', 'custom'

        Returns:
            JSON with comparison data including variance analysis
        """
        try:
            # Parse parameters
            if request.method == 'POST':
                data = request.get_json()
            else:
                data = request.args

            current_start = data.get('current_start_date')
            current_end = data.get('current_end_date')
            previous_start = data.get('previous_start_date')
            previous_end = data.get('previous_end_date')
            comparison_type = data.get('comparison_type', 'custom')

            # Auto-calculate previous period if comparison_type is specified
            if comparison_type != 'custom' and current_start and current_end:
                current_start_date = datetime.strptime(current_start, '%Y-%m-%d').date()
                current_end_date = datetime.strptime(current_end, '%Y-%m-%d').date()

                if comparison_type == 'month_over_month':
                    # Safe month calculation that handles different month lengths
                    if current_start_date.month > 1:
                        # Go to previous month
                        previous_month = current_start_date.month - 1
                        previous_year = current_start_date.year
                    else:
                        # Go to December of previous year
                        previous_month = 12
                        previous_year = current_start_date.year - 1

                    # Handle day overflow (e.g., Jan 31 -> Feb 28)
                    try:
                        previous_start_date = current_start_date.replace(year=previous_year, month=previous_month)
                    except ValueError:
                        # Day doesn't exist in target month, use last day of target month
                        from calendar import monthrange
                        last_day = monthrange(previous_year, previous_month)[1]
                        previous_start_date = current_start_date.replace(year=previous_year, month=previous_month, day=min(current_start_date.day, last_day))

                    # Same logic for end date
                    if current_end_date.month > 1:
                        previous_month = current_end_date.month - 1
                        previous_year = current_end_date.year
                    else:
                        previous_month = 12
                        previous_year = current_end_date.year - 1

                    try:
                        previous_end_date = current_end_date.replace(year=previous_year, month=previous_month)
                    except ValueError:
                        from calendar import monthrange
                        last_day = monthrange(previous_year, previous_month)[1]
                        previous_end_date = current_end_date.replace(year=previous_year, month=previous_month, day=min(current_end_date.day, last_day))
                elif comparison_type == 'quarter_over_quarter':
                    # Calculate previous quarter
                    months_back = 3
                    previous_start_date = (current_start_date.replace(day=1) - timedelta(days=1)).replace(day=1) if current_start_date.month > 3 else current_start_date.replace(year=current_start_date.year-1, month=current_start_date.month+9)
                    previous_end_date = (current_end_date.replace(day=1) - timedelta(days=1)).replace(day=1) if current_end_date.month > 3 else current_end_date.replace(year=current_end_date.year-1, month=current_end_date.month+9)
                elif comparison_type == 'year_over_year':
                    previous_start_date = current_start_date.replace(year=current_start_date.year-1)
                    previous_end_date = current_end_date.replace(year=current_end_date.year-1)
            else:
                # Parse custom dates
                previous_start_date = datetime.strptime(previous_start, '%Y-%m-%d').date() if previous_start else None
                previous_end_date = datetime.strptime(previous_end, '%Y-%m-%d').date() if previous_end else None
                current_start_date = datetime.strptime(current_start, '%Y-%m-%d').date() if current_start else None
                current_end_date = datetime.strptime(current_end, '%Y-%m-%d').date() if current_end else None

            if not all([current_start_date, current_end_date, previous_start_date, previous_end_date]):
                return jsonify({
                    'success': False,
                    'error': 'All date parameters are required'
                }), 400

            # Generate financial data for both periods
            current_period_data = generate_period_financial_data(current_start_date, current_end_date)
            previous_period_data = generate_period_financial_data(previous_start_date, previous_end_date)

            # Calculate variance analysis
            variance_analysis = calculate_variance_analysis(current_period_data, previous_period_data)

            return jsonify({
                'success': True,
                'comparison': {
                    'current_period': {
                        'start_date': current_start_date.isoformat(),
                        'end_date': current_end_date.isoformat(),
                        'data': current_period_data
                    },
                    'previous_period': {
                        'start_date': previous_start_date.isoformat(),
                        'end_date': previous_end_date.isoformat(),
                        'data': previous_period_data
                    },
                    'variance_analysis': variance_analysis,
                    'comparison_type': comparison_type
                },
                'generated_at': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error in period comparison: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def generate_period_financial_data(start_date, end_date):
        """Generate financial data for a specific period"""

        # Safe query execution
        def safe_query(query, params=None):
            try:
                result = db_manager.execute_query(query, params, fetch_all=True)
                return result if result else []
            except Exception as e:
                logger.warning(f"Query failed safely: {e}")
                return []

        # Revenue query for the period
        revenue_query = """
            SELECT
                COALESCE(accounting_category, classified_entity, 'Uncategorized') as category,
                COALESCE(SUM(amount), 0) as amount,
                COUNT(*) as count
            FROM transactions
            WHERE amount > 0
            AND TO_DATE(date, 'MM/DD/YYYY'::text) >= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
            AND TO_DATE(date, 'MM/DD/YYYY'::text) <= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
            GROUP BY COALESCE(accounting_category, classified_entity, 'Uncategorized')
            ORDER BY amount DESC
        """ if db_manager.db_type == 'postgresql' else """
            SELECT
                COALESCE(accounting_category, classified_entity, 'Uncategorized') as category,
                COALESCE(SUM(amount), 0) as amount,
                COUNT(*) as count
            FROM transactions
            WHERE amount > 0
            AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) >= date(?)
            AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) <= date(?)
            GROUP BY COALESCE(accounting_category, classified_entity, 'Uncategorized')
            ORDER BY amount DESC
        """

        revenue_data = safe_query(revenue_query, (start_date, end_date))

        # Expenses query for the period
        expenses_query = """
            SELECT
                COALESCE(accounting_category, classified_entity, 'General & Administrative') as category,
                COALESCE(SUM(ABS(amount)), 0) as amount,
                COUNT(*) as count
            FROM transactions
            WHERE amount < 0
            AND TO_DATE(date, 'MM/DD/YYYY'::text) >= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
            AND TO_DATE(date, 'MM/DD/YYYY'::text) <= TO_DATE(%s::text, 'YYYY-MM-DD'::text)
            GROUP BY COALESCE(accounting_category, classified_entity, 'General & Administrative')
            ORDER BY amount DESC
        """ if db_manager.db_type == 'postgresql' else """
            SELECT
                COALESCE(accounting_category, classified_entity, 'General & Administrative') as category,
                COALESCE(SUM(ABS(amount)), 0) as amount,
                COUNT(*) as count
            FROM transactions
            WHERE amount < 0
            AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) >= date(?)
            AND date(substr(date, 7, 4) || '-' || substr(date, 1, 2) || '-' || substr(date, 4, 2)) <= date(?)
            GROUP BY COALESCE(accounting_category, classified_entity, 'General & Administrative')
            ORDER BY amount DESC
        """

        expenses_data = safe_query(expenses_query, (start_date, end_date))

        # Calculate totals
        total_revenue = sum(float(row.get('amount', 0)) for row in revenue_data)
        total_expenses = sum(float(row.get('amount', 0)) for row in expenses_data)
        net_income = total_revenue - total_expenses
        margin_percent = (net_income / total_revenue * 100) if total_revenue > 0 else 0

        return {
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_income': net_income,
            'margin_percent': round(margin_percent, 2),
            'revenue_categories': [{'category': r.get('category', ''), 'amount': float(r.get('amount', 0))} for r in revenue_data],
            'expense_categories': [{'category': e.get('category', ''), 'amount': float(e.get('amount', 0))} for e in expenses_data],
            'transaction_count': sum(r.get('count', 0) for r in revenue_data) + sum(e.get('count', 0) for e in expenses_data)
        }

    def calculate_variance_analysis(current, previous):
        """Calculate variance analysis between two periods"""

        def safe_divide(numerator, denominator):
            return (numerator / denominator) if denominator != 0 else 0

        def calculate_change(current_val, previous_val):
            if previous_val == 0:
                return {'absolute': current_val, 'percentage': 100.0 if current_val > 0 else 0.0}

            absolute_change = current_val - previous_val
            percentage_change = (absolute_change / abs(previous_val)) * 100

            return {
                'absolute': round(absolute_change, 2),
                'percentage': round(percentage_change, 2)
            }

        revenue_change = calculate_change(current['total_revenue'], previous['total_revenue'])
        expenses_change = calculate_change(current['total_expenses'], previous['total_expenses'])
        net_income_change = calculate_change(current['net_income'], previous['net_income'])
        margin_change = {
            'absolute': round(current['margin_percent'] - previous['margin_percent'], 2),
            'percentage': round(((current['margin_percent'] - previous['margin_percent']) / abs(previous['margin_percent']) * 100) if previous['margin_percent'] != 0 else 0, 2)
        }

        # Growth rates
        revenue_growth_rate = safe_divide(revenue_change['absolute'], abs(previous['total_revenue'])) * 100
        expense_growth_rate = safe_divide(expenses_change['absolute'], abs(previous['total_expenses'])) * 100

        return {
            'revenue_change': revenue_change,
            'expenses_change': expenses_change,
            'net_income_change': net_income_change,
            'margin_change': margin_change,
            'revenue_growth_rate': round(revenue_growth_rate, 2),
            'expense_growth_rate': round(expense_growth_rate, 2),
            'efficiency_metrics': {
                'revenue_per_transaction': {
                    'current': round(safe_divide(current['total_revenue'], current['transaction_count']), 2),
                    'previous': round(safe_divide(previous['total_revenue'], previous['transaction_count']), 2)
                },
                'expense_ratio': {
                    'current': round(safe_divide(current['total_expenses'], current['total_revenue']) * 100, 2),
                    'previous': round(safe_divide(previous['total_expenses'], previous['total_revenue']) * 100, 2)
                }
            }
        }

    @app.route('/api/reports/templates', methods=['GET', 'POST', 'DELETE'])
    def api_report_templates():
        """
        Manage custom report templates

        GET: List all templates
        POST: Create or update a template
        DELETE: Delete a template
        """
        try:
            if request.method == 'GET':
                # Get all templates
                templates_query = """
                    SELECT id, name, description, template_config, created_at, updated_at
                    FROM report_templates
                    ORDER BY updated_at DESC
                """
                templates = db_manager.execute_query(templates_query, fetch_all=True)

                # Parse JSON configs
                template_list = []
                for template in templates:
                    template_dict = dict(template)
                    try:
                        template_dict['template_config'] = json.loads(template['template_config'])
                    except (json.JSONDecodeError, TypeError):
                        template_dict['template_config'] = {}
                    template_list.append(template_dict)

                return jsonify({
                    'success': True,
                    'templates': template_list
                })

            elif request.method == 'POST':
                # Create or update template
                data = request.get_json()
                template_name = data.get('name')
                description = data.get('description', '')
                config = data.get('config', {})
                template_id = data.get('id')

                if not template_name:
                    return jsonify({
                        'success': False,
                        'error': 'Template name is required'
                    }), 400

                config_json = json.dumps(config)

                if template_id:
                    # Update existing template
                    update_query = """
                        UPDATE report_templates
                        SET name = %s, description = %s, template_config = %s, updated_at = %s
                        WHERE id = %s
                    """ if db_manager.db_type == 'postgresql' else """
                        UPDATE report_templates
                        SET name = ?, description = ?, template_config = ?, updated_at = ?
                        WHERE id = ?
                    """
                    db_manager.execute_query(update_query, (template_name, description, config_json, datetime.now(), template_id))
                else:
                    # Create new template
                    insert_query = """
                        INSERT INTO report_templates (name, description, template_config, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """ if db_manager.db_type == 'postgresql' else """
                        INSERT INTO report_templates (name, description, template_config, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """
                    db_manager.execute_query(insert_query, (template_name, description, config_json, datetime.now(), datetime.now()))

                return jsonify({
                    'success': True,
                    'message': 'Template saved successfully'
                })

            elif request.method == 'DELETE':
                # Delete template
                template_id = request.args.get('id')
                if not template_id:
                    return jsonify({
                        'success': False,
                        'error': 'Template ID is required'
                    }), 400

                delete_query = """
                    DELETE FROM report_templates WHERE id = %s
                """ if db_manager.db_type == 'postgresql' else """
                    DELETE FROM report_templates WHERE id = ?
                """
                db_manager.execute_query(delete_query, (template_id,))

                return jsonify({
                    'success': True,
                    'message': 'Template deleted successfully'
                })

        except Exception as e:
            logger.error(f"Error managing report templates: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def ensure_report_templates_table():
        """Ensure the report templates table exists"""
        try:
            if db_manager.db_type == 'postgresql':
                create_table_query = """
                    CREATE TABLE IF NOT EXISTS report_templates (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        template_config JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_report_templates_name ON report_templates(name);
                """
            else:
                create_table_query = """
                    CREATE TABLE IF NOT EXISTS report_templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        template_config TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_report_templates_name ON report_templates(name);
                """

            db_manager.execute_query(create_table_query)
            logger.info("Report templates table ensured")

            # Create default templates if none exist
            count_query = "SELECT COUNT(*) as count FROM report_templates"
            result = db_manager.execute_query(count_query, fetch_one=True)

            if result['count'] == 0:
                create_default_templates()

        except Exception as e:
            logger.warning(f"Could not ensure report templates table: {e}")

    def create_default_templates():
        """Create default report templates"""
        default_templates = [
            {
                'name': 'Relatório Mensal Padrão',
                'description': 'Demonstração de resultado mensal com gráficos',
                'config': {
                    'report_type': 'income-statement',
                    'period_type': 'monthly',
                    'include_charts': True,
                    'include_comparison': False,
                    'default_date_range': 'current_month'
                }
            },
            {
                'name': 'Análise Trimestral Completa',
                'description': 'Relatório trimestral com comparações e gráficos',
                'config': {
                    'report_type': 'income-statement',
                    'period_type': 'quarterly',
                    'include_charts': True,
                    'include_comparison': True,
                    'comparison_type': 'quarter_over_quarter',
                    'default_date_range': 'current_quarter'
                }
            },
            {
                'name': 'Dashboard Executivo',
                'description': 'Visão executiva com métricas principais e tendências',
                'config': {
                    'report_type': 'dashboard',
                    'period_type': 'monthly',
                    'include_charts': True,
                    'include_comparison': True,
                    'comparison_type': 'month_over_month',
                    'metrics': ['revenue', 'expenses', 'net_income', 'margin'],
                    'default_date_range': 'last_3_months'
                }
            }
        ]

        for template in default_templates:
            config_json = json.dumps(template['config'])
            insert_query = """
                INSERT INTO report_templates (name, description, template_config, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
            """ if db_manager.db_type == 'postgresql' else """
                INSERT INTO report_templates (name, description, template_config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """
            db_manager.execute_query(insert_query, (
                template['name'],
                template['description'],
                config_json,
                datetime.now(),
                datetime.now()
            ))

        logger.info("Default report templates created")

    # Ensure templates table exists
    ensure_report_templates_table()

    logger.info("CFO Reporting API routes registered successfully")
    return app
