#!/usr/bin/env python3
"""
AI Transaction Tools
Provides tool definitions and execution handlers for Claude AI chatbot.
Enables the AI to query actual transaction data instead of returning generic responses.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Definitions for Claude API
# =============================================================================

TRANSACTION_TOOLS = [
    {
        "name": "get_financial_summary",
        "description": "Get financial summary for a time period including total revenue, expenses, net income, and transaction counts. Use this when users ask for financial overviews, summaries, or want to know their financial position.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["today", "yesterday", "this_week", "last_week", "this_month", "last_month", "this_quarter", "last_quarter", "this_year", "last_year", "last_7_days", "last_30_days", "last_90_days", "all_time"],
                    "description": "Time period for the summary"
                },
                "entity": {
                    "type": "string",
                    "description": "Optional: Filter by specific business entity name"
                }
            },
            "required": ["period"]
        }
    },
    {
        "name": "search_transactions",
        "description": "Search and filter transactions by various criteria. Use this when users ask to find specific transactions, look up payments, or search for particular expenses or revenue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
                "transaction_type": {
                    "type": "string",
                    "enum": ["Revenue", "Expense", "All"],
                    "description": "Filter by transaction type"
                },
                "category": {
                    "type": "string",
                    "description": "Filter by accounting category"
                },
                "subcategory": {
                    "type": "string",
                    "description": "Filter by subcategory"
                },
                "entity": {
                    "type": "string",
                    "description": "Filter by business entity"
                },
                "min_amount": {
                    "type": "number",
                    "description": "Minimum transaction amount (absolute value)"
                },
                "max_amount": {
                    "type": "number",
                    "description": "Maximum transaction amount (absolute value)"
                },
                "keyword": {
                    "type": "string",
                    "description": "Search keyword in transaction description"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 10, max 50)"
                }
            }
        }
    },
    {
        "name": "get_category_breakdown",
        "description": "Get spending or revenue breakdown by category with totals and percentages. Use this when users want to see where their money is going or coming from.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["this_week", "last_week", "this_month", "last_month", "this_quarter", "last_quarter", "this_year", "last_30_days", "last_90_days"],
                    "description": "Time period for the breakdown"
                },
                "type": {
                    "type": "string",
                    "enum": ["expenses", "revenue", "both"],
                    "description": "Type of breakdown to show"
                }
            },
            "required": ["period"]
        }
    },
    {
        "name": "get_entity_summary",
        "description": "Get financial summary broken down by business entity. Use this when users want to compare performance across their different business units or entities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["this_month", "last_month", "this_quarter", "this_year", "last_30_days", "last_90_days"],
                    "description": "Time period for the summary"
                }
            },
            "required": ["period"]
        }
    },
    {
        "name": "get_recent_transactions",
        "description": "Get the most recent transactions. Use this when users ask about recent activity, latest transactions, or what happened recently.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent transactions to return (default 10, max 25)"
                },
                "transaction_type": {
                    "type": "string",
                    "enum": ["Revenue", "Expense", "All"],
                    "description": "Filter by transaction type"
                }
            }
        }
    },
    {
        "name": "get_top_expenses",
        "description": "Get the largest expenses for a period. Use this when users ask about biggest expenses, major costs, or where most money was spent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["this_week", "this_month", "last_month", "this_quarter", "this_year", "last_30_days"],
                    "description": "Time period to analyze"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of top expenses to return (default 10)"
                }
            },
            "required": ["period"]
        }
    },
    {
        "name": "get_top_revenue",
        "description": "Get the largest revenue transactions for a period. Use this when users ask about biggest income sources, top revenue, or major payments received.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["this_week", "this_month", "last_month", "this_quarter", "this_year", "last_30_days"],
                    "description": "Time period to analyze"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of top revenue items to return (default 10)"
                }
            },
            "required": ["period"]
        }
    }
]


# =============================================================================
# Date Period Helpers
# =============================================================================

def get_date_range(period: str) -> tuple:
    """
    Convert a period string to start and end dates.

    Args:
        period: Period string like 'this_month', 'last_30_days', etc.

    Returns:
        tuple: (start_date, end_date) as YYYY-MM-DD strings
    """
    today = datetime.now().date()

    if period == "today":
        return str(today), str(today)

    elif period == "yesterday":
        yesterday = today - timedelta(days=1)
        return str(yesterday), str(yesterday)

    elif period == "this_week":
        start = today - timedelta(days=today.weekday())
        return str(start), str(today)

    elif period == "last_week":
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
        return str(start), str(end)

    elif period == "this_month":
        start = today.replace(day=1)
        return str(start), str(today)

    elif period == "last_month":
        first_of_this_month = today.replace(day=1)
        end = first_of_this_month - timedelta(days=1)
        start = end.replace(day=1)
        return str(start), str(end)

    elif period == "this_quarter":
        quarter = (today.month - 1) // 3
        start = today.replace(month=quarter * 3 + 1, day=1)
        return str(start), str(today)

    elif period == "last_quarter":
        quarter = (today.month - 1) // 3
        if quarter == 0:
            start = today.replace(year=today.year - 1, month=10, day=1)
            end = today.replace(year=today.year - 1, month=12, day=31)
        else:
            start = today.replace(month=(quarter - 1) * 3 + 1, day=1)
            end_month = quarter * 3
            if end_month == 3:
                end = today.replace(month=3, day=31)
            elif end_month == 6:
                end = today.replace(month=6, day=30)
            elif end_month == 9:
                end = today.replace(month=9, day=30)
            else:
                end = today.replace(month=12, day=31)
        return str(start), str(end)

    elif period == "this_year":
        start = today.replace(month=1, day=1)
        return str(start), str(today)

    elif period == "last_year":
        start = today.replace(year=today.year - 1, month=1, day=1)
        end = today.replace(year=today.year - 1, month=12, day=31)
        return str(start), str(end)

    elif period == "last_7_days":
        start = today - timedelta(days=7)
        return str(start), str(today)

    elif period == "last_30_days":
        start = today - timedelta(days=30)
        return str(start), str(today)

    elif period == "last_90_days":
        start = today - timedelta(days=90)
        return str(start), str(today)

    elif period == "all_time":
        return None, None

    else:
        # Default to last 30 days
        start = today - timedelta(days=30)
        return str(start), str(today)


def format_period_name(period: str) -> str:
    """Convert period code to human-readable name."""
    period_names = {
        "today": "Today",
        "yesterday": "Yesterday",
        "this_week": "This Week",
        "last_week": "Last Week",
        "this_month": "This Month",
        "last_month": "Last Month",
        "this_quarter": "This Quarter",
        "last_quarter": "Last Quarter",
        "this_year": "This Year",
        "last_year": "Last Year",
        "last_7_days": "Last 7 Days",
        "last_30_days": "Last 30 Days",
        "last_90_days": "Last 90 Days",
        "all_time": "All Time"
    }
    return period_names.get(period, period.replace("_", " ").title())


# =============================================================================
# Tool Execution Handlers
# =============================================================================

class AIToolExecutor:
    """
    Executes AI tool calls and returns formatted results.
    All queries are filtered by tenant_id for security.
    """

    def __init__(self, db_manager, tenant_id: str):
        """
        Initialize the tool executor.

        Args:
            db_manager: Database manager instance
            tenant_id: Current tenant identifier (REQUIRED - no fallbacks)
        """
        if not tenant_id:
            raise ValueError("tenant_id is required for AIToolExecutor")

        self.db_manager = db_manager
        self.tenant_id = tenant_id

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Execute a tool and return the result as a string.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            str: Tool result formatted for Claude
        """
        logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

        try:
            if tool_name == "get_financial_summary":
                return self._get_financial_summary(tool_input)
            elif tool_name == "search_transactions":
                return self._search_transactions(tool_input)
            elif tool_name == "get_category_breakdown":
                return self._get_category_breakdown(tool_input)
            elif tool_name == "get_entity_summary":
                return self._get_entity_summary(tool_input)
            elif tool_name == "get_recent_transactions":
                return self._get_recent_transactions(tool_input)
            elif tool_name == "get_top_expenses":
                return self._get_top_expenses(tool_input)
            elif tool_name == "get_top_revenue":
                return self._get_top_revenue(tool_input)
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return f"Error executing {tool_name}: {str(e)}"

    def _format_currency(self, amount: float, currency: str = "USD") -> str:
        """Format amount as currency string."""
        if amount is None:
            return "$0.00"
        if currency == "USD":
            return f"${amount:,.2f}"
        return f"{amount:,.2f} {currency}"

    def _get_financial_summary(self, params: Dict[str, Any]) -> str:
        """Execute get_financial_summary tool."""
        period = params.get("period", "this_month")
        entity_filter = params.get("entity")

        start_date, end_date = get_date_range(period)
        period_name = format_period_name(period)

        # Build query
        query = """
            SELECT
                COUNT(*) as transaction_count,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_revenue,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expenses,
                COUNT(CASE WHEN amount > 0 THEN 1 END) as revenue_count,
                COUNT(CASE WHEN amount < 0 THEN 1 END) as expense_count,
                COUNT(DISTINCT classified_entity) as entity_count
            FROM transactions
            WHERE tenant_id = %s
              AND (archived = FALSE OR archived IS NULL)
        """
        params_list = [self.tenant_id]

        if start_date:
            query += " AND date::date >= %s::date"
            params_list.append(start_date)
        if end_date:
            query += " AND date::date <= %s::date"
            params_list.append(end_date)
        if entity_filter:
            query += " AND classified_entity = %s"
            params_list.append(entity_filter)

        with self.db_manager.get_connection() as conn:
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, tuple(params_list))
            result = cursor.fetchone()

        if not result or result['transaction_count'] == 0:
            return f"No transactions found for {period_name}."

        total_revenue = float(result['total_revenue'] or 0)
        total_expenses = float(result['total_expenses'] or 0)
        net_income = total_revenue - total_expenses

        # Format response
        entity_text = f" for {entity_filter}" if entity_filter else ""
        response = f"""Financial Summary{entity_text} - {period_name}:

TOTALS:
- Total Revenue: {self._format_currency(total_revenue)} ({result['revenue_count']} transactions)
- Total Expenses: {self._format_currency(total_expenses)} ({result['expense_count']} transactions)
- Net Income: {self._format_currency(net_income)}
- Total Transactions: {result['transaction_count']}
- Active Entities: {result['entity_count']}"""

        # Add profit margin if there's revenue
        if total_revenue > 0:
            margin = (net_income / total_revenue) * 100
            response += f"\n- Profit Margin: {margin:.1f}%"

        return response

    def _search_transactions(self, params: Dict[str, Any]) -> str:
        """Execute search_transactions tool."""
        limit = min(params.get("limit", 10), 50)  # Cap at 50

        # Build WHERE clause
        conditions = [
            "tenant_id = %s",
            "(archived = FALSE OR archived IS NULL)"
        ]
        params_list = [self.tenant_id]

        if params.get("start_date"):
            conditions.append("date::date >= %s::date")
            params_list.append(params["start_date"])

        if params.get("end_date"):
            conditions.append("date::date <= %s::date")
            params_list.append(params["end_date"])

        if params.get("transaction_type") == "Revenue":
            conditions.append("amount > 0")
        elif params.get("transaction_type") == "Expense":
            conditions.append("amount < 0")

        if params.get("category"):
            conditions.append("accounting_category = %s")
            params_list.append(params["category"])

        if params.get("subcategory"):
            conditions.append("subcategory = %s")
            params_list.append(params["subcategory"])

        if params.get("entity"):
            conditions.append("classified_entity = %s")
            params_list.append(params["entity"])

        if params.get("min_amount"):
            conditions.append("ABS(amount) >= %s")
            params_list.append(params["min_amount"])

        if params.get("max_amount"):
            conditions.append("ABS(amount) <= %s")
            params_list.append(params["max_amount"])

        if params.get("keyword"):
            conditions.append("(description ILIKE %s OR justification ILIKE %s)")
            keyword_pattern = f"%{params['keyword']}%"
            params_list.extend([keyword_pattern, keyword_pattern])

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT id, date, description, amount, classified_entity,
                   accounting_category, subcategory, currency
            FROM transactions
            WHERE {where_clause}
            ORDER BY date DESC, id DESC
            LIMIT %s
        """
        params_list.append(limit)

        with self.db_manager.get_connection() as conn:
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, tuple(params_list))
            transactions = cursor.fetchall()

        if not transactions:
            return "No transactions found matching your criteria."

        # Format response
        total_amount = sum(float(t['amount'] or 0) for t in transactions)

        response = f"Found {len(transactions)} transaction(s):\n\n"

        for t in transactions:
            amount = float(t['amount'] or 0)
            currency = t.get('currency', 'USD') or 'USD'
            amount_str = self._format_currency(abs(amount), currency)
            tx_type = "+" if amount > 0 else "-"

            response += f"- {t['date']}: {t['description'][:50]}"
            if len(t['description']) > 50:
                response += "..."
            response += f" | {tx_type}{amount_str}"
            if t.get('classified_entity'):
                response += f" | {t['classified_entity']}"
            response += "\n"

        response += f"\nTotal: {self._format_currency(total_amount)}"

        return response

    def _get_category_breakdown(self, params: Dict[str, Any]) -> str:
        """Execute get_category_breakdown tool."""
        period = params.get("period", "this_month")
        breakdown_type = params.get("type", "both")

        start_date, end_date = get_date_range(period)
        period_name = format_period_name(period)

        response_parts = []

        if breakdown_type in ["expenses", "both"]:
            expense_breakdown = self._get_breakdown_by_type(
                start_date, end_date, is_expense=True
            )
            if expense_breakdown:
                response_parts.append(f"EXPENSE BREAKDOWN ({period_name}):\n{expense_breakdown}")

        if breakdown_type in ["revenue", "both"]:
            revenue_breakdown = self._get_breakdown_by_type(
                start_date, end_date, is_expense=False
            )
            if revenue_breakdown:
                response_parts.append(f"REVENUE BREAKDOWN ({period_name}):\n{revenue_breakdown}")

        if not response_parts:
            return f"No transactions found for {period_name}."

        return "\n\n".join(response_parts)

    def _get_breakdown_by_type(self, start_date: str, end_date: str, is_expense: bool) -> str:
        """Get category breakdown for expenses or revenue."""
        amount_condition = "amount < 0" if is_expense else "amount > 0"
        amount_select = "ABS(amount)" if is_expense else "amount"

        query = f"""
            SELECT
                COALESCE(accounting_category, 'Uncategorized') as category,
                COUNT(*) as count,
                SUM({amount_select}) as total
            FROM transactions
            WHERE tenant_id = %s
              AND (archived = FALSE OR archived IS NULL)
              AND {amount_condition}
        """
        params_list = [self.tenant_id]

        if start_date:
            query += " AND date::date >= %s::date"
            params_list.append(start_date)
        if end_date:
            query += " AND date::date <= %s::date"
            params_list.append(end_date)

        query += " GROUP BY accounting_category ORDER BY total DESC LIMIT 15"

        with self.db_manager.get_connection() as conn:
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, tuple(params_list))
            categories = cursor.fetchall()

        if not categories:
            return None

        grand_total = sum(float(c['total'] or 0) for c in categories)

        lines = []
        for cat in categories:
            total = float(cat['total'] or 0)
            percentage = (total / grand_total * 100) if grand_total > 0 else 0
            lines.append(
                f"- {cat['category']}: {self._format_currency(total)} ({percentage:.1f}%) - {cat['count']} transactions"
            )

        lines.append(f"\nTotal: {self._format_currency(grand_total)}")

        return "\n".join(lines)

    def _get_entity_summary(self, params: Dict[str, Any]) -> str:
        """Execute get_entity_summary tool."""
        period = params.get("period", "this_month")
        start_date, end_date = get_date_range(period)
        period_name = format_period_name(period)

        query = """
            SELECT
                COALESCE(classified_entity, 'Unassigned') as entity,
                COUNT(*) as count,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
            FROM transactions
            WHERE tenant_id = %s
              AND (archived = FALSE OR archived IS NULL)
        """
        params_list = [self.tenant_id]

        if start_date:
            query += " AND date::date >= %s::date"
            params_list.append(start_date)
        if end_date:
            query += " AND date::date <= %s::date"
            params_list.append(end_date)

        query += " GROUP BY classified_entity ORDER BY revenue DESC, expenses DESC"

        with self.db_manager.get_connection() as conn:
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, tuple(params_list))
            entities = cursor.fetchall()

        if not entities:
            return f"No transactions found for {period_name}."

        response = f"Entity Summary - {period_name}:\n\n"

        total_revenue = 0
        total_expenses = 0

        for entity in entities:
            revenue = float(entity['revenue'] or 0)
            expenses = float(entity['expenses'] or 0)
            net = revenue - expenses

            total_revenue += revenue
            total_expenses += expenses

            response += f"**{entity['entity']}** ({entity['count']} transactions)\n"
            response += f"  Revenue: {self._format_currency(revenue)}\n"
            response += f"  Expenses: {self._format_currency(expenses)}\n"
            response += f"  Net: {self._format_currency(net)}\n\n"

        total_net = total_revenue - total_expenses
        response += f"---\nGRAND TOTAL:\n"
        response += f"  Revenue: {self._format_currency(total_revenue)}\n"
        response += f"  Expenses: {self._format_currency(total_expenses)}\n"
        response += f"  Net: {self._format_currency(total_net)}"

        return response

    def _get_recent_transactions(self, params: Dict[str, Any]) -> str:
        """Execute get_recent_transactions tool."""
        limit = min(params.get("limit", 10), 25)
        transaction_type = params.get("transaction_type", "All")

        query = """
            SELECT id, date, description, amount, classified_entity,
                   accounting_category, currency
            FROM transactions
            WHERE tenant_id = %s
              AND (archived = FALSE OR archived IS NULL)
        """
        params_list = [self.tenant_id]

        if transaction_type == "Revenue":
            query += " AND amount > 0"
        elif transaction_type == "Expense":
            query += " AND amount < 0"

        query += " ORDER BY date DESC, id DESC LIMIT %s"
        params_list.append(limit)

        with self.db_manager.get_connection() as conn:
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, tuple(params_list))
            transactions = cursor.fetchall()

        if not transactions:
            return "No recent transactions found."

        type_text = f" {transaction_type.lower()}" if transaction_type != "All" else ""
        response = f"Recent{type_text} transactions ({len(transactions)} shown):\n\n"

        for t in transactions:
            amount = float(t['amount'] or 0)
            currency = t.get('currency', 'USD') or 'USD'
            amount_str = self._format_currency(abs(amount), currency)
            tx_type = "+" if amount > 0 else "-"

            response += f"- {t['date']}: {t['description'][:45]}"
            if len(t['description']) > 45:
                response += "..."
            response += f" | {tx_type}{amount_str}"
            if t.get('classified_entity'):
                response += f" | {t['classified_entity']}"
            response += "\n"

        return response

    def _get_top_expenses(self, params: Dict[str, Any]) -> str:
        """Execute get_top_expenses tool."""
        period = params.get("period", "this_month")
        limit = min(params.get("limit", 10), 20)

        start_date, end_date = get_date_range(period)
        period_name = format_period_name(period)

        query = """
            SELECT id, date, description, amount, classified_entity,
                   accounting_category, currency
            FROM transactions
            WHERE tenant_id = %s
              AND (archived = FALSE OR archived IS NULL)
              AND amount < 0
        """
        params_list = [self.tenant_id]

        if start_date:
            query += " AND date::date >= %s::date"
            params_list.append(start_date)
        if end_date:
            query += " AND date::date <= %s::date"
            params_list.append(end_date)

        query += " ORDER BY amount ASC LIMIT %s"  # ASC because expenses are negative
        params_list.append(limit)

        with self.db_manager.get_connection() as conn:
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, tuple(params_list))
            transactions = cursor.fetchall()

        if not transactions:
            return f"No expenses found for {period_name}."

        total_shown = sum(abs(float(t['amount'] or 0)) for t in transactions)

        response = f"Top {len(transactions)} Expenses - {period_name}:\n\n"

        for i, t in enumerate(transactions, 1):
            amount = abs(float(t['amount'] or 0))
            currency = t.get('currency', 'USD') or 'USD'

            response += f"{i}. {t['date']}: {t['description'][:40]}"
            if len(t['description']) > 40:
                response += "..."
            response += f"\n   Amount: {self._format_currency(amount, currency)}"
            if t.get('accounting_category'):
                response += f" | Category: {t['accounting_category']}"
            if t.get('classified_entity'):
                response += f" | Entity: {t['classified_entity']}"
            response += "\n\n"

        response += f"Total of top {len(transactions)} expenses: {self._format_currency(total_shown)}"

        return response

    def _get_top_revenue(self, params: Dict[str, Any]) -> str:
        """Execute get_top_revenue tool."""
        period = params.get("period", "this_month")
        limit = min(params.get("limit", 10), 20)

        start_date, end_date = get_date_range(period)
        period_name = format_period_name(period)

        query = """
            SELECT id, date, description, amount, classified_entity,
                   accounting_category, currency
            FROM transactions
            WHERE tenant_id = %s
              AND (archived = FALSE OR archived IS NULL)
              AND amount > 0
        """
        params_list = [self.tenant_id]

        if start_date:
            query += " AND date::date >= %s::date"
            params_list.append(start_date)
        if end_date:
            query += " AND date::date <= %s::date"
            params_list.append(end_date)

        query += " ORDER BY amount DESC LIMIT %s"
        params_list.append(limit)

        with self.db_manager.get_connection() as conn:
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, tuple(params_list))
            transactions = cursor.fetchall()

        if not transactions:
            return f"No revenue found for {period_name}."

        total_shown = sum(float(t['amount'] or 0) for t in transactions)

        response = f"Top {len(transactions)} Revenue - {period_name}:\n\n"

        for i, t in enumerate(transactions, 1):
            amount = float(t['amount'] or 0)
            currency = t.get('currency', 'USD') or 'USD'

            response += f"{i}. {t['date']}: {t['description'][:40]}"
            if len(t['description']) > 40:
                response += "..."
            response += f"\n   Amount: {self._format_currency(amount, currency)}"
            if t.get('accounting_category'):
                response += f" | Category: {t['accounting_category']}"
            if t.get('classified_entity'):
                response += f" | Entity: {t['classified_entity']}"
            response += "\n\n"

        response += f"Total of top {len(transactions)} revenue: {self._format_currency(total_shown)}"

        return response


def get_tool_executor(db_manager, tenant_id: str) -> AIToolExecutor:
    """
    Factory function to create an AI tool executor.

    Args:
        db_manager: Database manager instance
        tenant_id: Current tenant identifier

    Returns:
        AIToolExecutor: Initialized tool executor
    """
    return AIToolExecutor(db_manager, tenant_id)
