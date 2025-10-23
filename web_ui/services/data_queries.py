#!/usr/bin/env python3
"""
Data Query Functions for Homepage and AI Content Generation
Provides database queries for company overview, KPIs, entities, and portfolio statistics
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import psycopg2.extras

logger = logging.getLogger(__name__)


class DataQueryService:
    """Service for querying company and financial data from the database"""

    def __init__(self, db_manager, tenant_id: str = 'delta'):
        """
        Initialize the data query service

        Args:
            db_manager: DatabaseManager instance
            tenant_id: Tenant identifier (default 'delta')
        """
        self.db_manager = db_manager
        self.tenant_id = tenant_id

    def get_company_overview(self) -> Dict[str, Any]:
        """
        Get company configuration and overview information

        Returns:
            Dictionary with company name, tagline, description, and settings
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                query = """
                    SELECT
                        tenant_id, company_name, company_tagline, company_description,
                        logo_url, primary_color, secondary_color, industry,
                        founded_date, headquarters_location, website_url,
                        contact_email, contact_phone, default_currency, timezone,
                        settings, created_at, updated_at
                    FROM tenant_configuration
                    WHERE tenant_id = %s AND is_active = TRUE
                """

                cursor.execute(query, (self.tenant_id,))
                result = cursor.fetchone()
                cursor.close()

                if result:
                    # Convert to regular dict and handle date serialization
                    overview = dict(result)
                    if overview.get('founded_date'):
                        overview['founded_date'] = overview['founded_date'].isoformat()
                    if overview.get('created_at'):
                        overview['created_at'] = overview['created_at'].isoformat()
                    if overview.get('updated_at'):
                        overview['updated_at'] = overview['updated_at'].isoformat()
                    return overview
                else:
                    # Return default if no configuration exists
                    return {
                        'tenant_id': self.tenant_id,
                        'company_name': 'Delta Capital Holdings',
                        'company_tagline': 'Diversified Technology & Innovation Portfolio',
                        'company_description': 'A strategic holding company focused on emerging technologies.',
                        'industry': 'Technology & Investment',
                        'default_currency': 'USD',
                        'timezone': 'UTC'
                    }

        except Exception as e:
            logger.error(f"Error fetching company overview: {e}")
            return {
                'tenant_id': self.tenant_id,
                'company_name': 'Delta Capital Holdings',
                'error': str(e)
            }

    def get_business_entities(self) -> List[Dict[str, Any]]:
        """
        Get all business entities/portfolio companies

        Returns:
            List of business entities with their details
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                query = """
                    SELECT
                        id, name, description, entity_type,
                        active, created_at
                    FROM business_entities
                    WHERE active = TRUE
                    ORDER BY name
                """

                cursor.execute(query)
                results = cursor.fetchall()
                cursor.close()

                entities = []
                for row in results:
                    entity = dict(row)
                    if entity.get('created_at'):
                        entity['created_at'] = entity['created_at'].isoformat()
                    entities.append(entity)

                return entities

        except Exception as e:
            logger.error(f"Error fetching business entities: {e}")
            return []

    def get_company_kpis(self) -> Dict[str, Any]:
        """
        Calculate key performance indicators from transaction and invoice data

        Returns:
            Dictionary with KPIs: total transactions, revenue, expenses, date ranges, etc.
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                kpis = {}

                # Total transactions (exclude archived)
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM transactions
                    WHERE tenant_id = %s AND (archived = FALSE OR archived IS NULL)
                """, (self.tenant_id,))
                result = cursor.fetchone()
                kpis['total_transactions'] = result['total'] if result else 0

                # Revenue (positive amounts)
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as revenue
                    FROM transactions
                    WHERE tenant_id = %s
                    AND amount > 0
                    AND (archived = FALSE OR archived IS NULL)
                """, (self.tenant_id,))
                result = cursor.fetchone()
                kpis['total_revenue'] = float(result['revenue']) if result else 0.0

                # Expenses (negative amounts)
                cursor.execute("""
                    SELECT COALESCE(SUM(ABS(amount)), 0) as expenses
                    FROM transactions
                    WHERE tenant_id = %s
                    AND amount < 0
                    AND (archived = FALSE OR archived IS NULL)
                """, (self.tenant_id,))
                result = cursor.fetchone()
                kpis['total_expenses'] = float(result['expenses']) if result else 0.0

                # Net profit
                kpis['net_profit'] = kpis['total_revenue'] - kpis['total_expenses']

                # Date range
                cursor.execute("""
                    SELECT
                        MIN(date) as min_date,
                        MAX(date) as max_date
                    FROM transactions
                    WHERE tenant_id = %s AND (archived = FALSE OR archived IS NULL)
                """, (self.tenant_id,))
                result = cursor.fetchone()
                if result and result['min_date']:
                    kpis['date_range'] = {
                        'min': result['min_date'].isoformat(),
                        'max': result['max_date'].isoformat()
                    }
                    # Calculate years of data
                    min_date = result['min_date']
                    max_date = result['max_date']
                    years = (max_date - min_date).days / 365.25
                    kpis['years_of_data'] = round(years, 1)
                else:
                    kpis['date_range'] = {'min': 'N/A', 'max': 'N/A'}
                    kpis['years_of_data'] = 0

                # Transactions by entity
                cursor.execute("""
                    SELECT
                        classified_entity,
                        COUNT(*) as count,
                        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
                    FROM transactions
                    WHERE tenant_id = %s
                    AND classified_entity IS NOT NULL
                    AND (archived = FALSE OR archived IS NULL)
                    GROUP BY classified_entity
                    ORDER BY count DESC
                    LIMIT 10
                """, (self.tenant_id,))
                results = cursor.fetchall()
                kpis['top_entities'] = [
                    {
                        'name': row['classified_entity'],
                        'transaction_count': row['count'],
                        'revenue': float(row['revenue']) if row['revenue'] else 0.0,
                        'expenses': float(row['expenses']) if row['expenses'] else 0.0
                    }
                    for row in results
                ]

                # Needs review count
                cursor.execute("""
                    SELECT COUNT(*) as needs_review
                    FROM transactions
                    WHERE tenant_id = %s
                    AND (confidence < 0.8 OR confidence IS NULL)
                    AND (archived = FALSE OR archived IS NULL)
                """, (self.tenant_id,))
                result = cursor.fetchone()
                kpis['needs_review'] = result['needs_review'] if result else 0

                # Invoice statistics
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_invoices,
                        COALESCE(SUM(amount_usd), 0) as total_invoice_value,
                        COUNT(CASE WHEN status = 'paid' THEN 1 END) as paid_invoices,
                        COUNT(CASE WHEN status = 'overdue' THEN 1 END) as overdue_invoices
                    FROM invoices
                """, ())
                result = cursor.fetchone()
                if result:
                    kpis['total_invoices'] = result['total_invoices']
                    kpis['total_invoice_value'] = float(result['total_invoice_value']) if result['total_invoice_value'] else 0.0
                    kpis['paid_invoices'] = result['paid_invoices']
                    kpis['overdue_invoices'] = result['overdue_invoices']
                else:
                    kpis['total_invoices'] = 0
                    kpis['total_invoice_value'] = 0.0
                    kpis['paid_invoices'] = 0
                    kpis['overdue_invoices'] = 0

                # Monthly trends (last 12 months)
                cursor.execute("""
                    SELECT
                        DATE_TRUNC('month', date) as month,
                        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                        COUNT(*) as transaction_count
                    FROM transactions
                    WHERE tenant_id = %s
                    AND date >= CURRENT_DATE - INTERVAL '12 months'
                    AND (archived = FALSE OR archived IS NULL)
                    GROUP BY DATE_TRUNC('month', date)
                    ORDER BY month DESC
                    LIMIT 12
                """, (self.tenant_id,))
                results = cursor.fetchall()
                kpis['monthly_trends'] = [
                    {
                        'month': row['month'].isoformat() if row['month'] else None,
                        'revenue': float(row['revenue']) if row['revenue'] else 0.0,
                        'expenses': float(row['expenses']) if row['expenses'] else 0.0,
                        'transaction_count': row['transaction_count']
                    }
                    for row in results
                ]

                cursor.close()
                return kpis

        except Exception as e:
            logger.error(f"Error calculating KPIs: {e}")
            return {
                'total_transactions': 0,
                'total_revenue': 0.0,
                'total_expenses': 0.0,
                'error': str(e)
            }

    def get_portfolio_stats(self) -> Dict[str, Any]:
        """
        Get statistics about portfolio companies

        Returns:
            Dictionary with portfolio company counts and metrics
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                # Count entities by type
                cursor.execute("""
                    SELECT
                        entity_type,
                        COUNT(*) as count
                    FROM business_entities
                    WHERE active = TRUE
                    GROUP BY entity_type
                """)
                results = cursor.fetchall()

                entity_counts = {}
                total_entities = 0
                for row in results:
                    entity_counts[row['entity_type']] = row['count']
                    total_entities += row['count']

                # Count wallet addresses
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM wallet_addresses
                    WHERE tenant_id = %s AND is_active = TRUE
                """, (self.tenant_id,))
                result = cursor.fetchone()
                wallet_count = result['count'] if result else 0

                # Count bank accounts
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM bank_accounts
                    WHERE tenant_id = %s AND status = 'active'
                """, (self.tenant_id,))
                result = cursor.fetchone()
                bank_account_count = result['count'] if result else 0

                cursor.close()

                return {
                    'total_entities': total_entities,
                    'entity_counts': entity_counts,
                    'wallet_count': wallet_count,
                    'bank_account_count': bank_account_count
                }

        except Exception as e:
            logger.error(f"Error fetching portfolio stats: {e}")
            return {
                'total_entities': 0,
                'entity_counts': {},
                'error': str(e)
            }

    def get_all_homepage_data(self) -> Dict[str, Any]:
        """
        Get all data needed for homepage generation in one call

        Returns:
            Dictionary with company overview, KPIs, entities, and portfolio stats
        """
        return {
            'company': self.get_company_overview(),
            'kpis': self.get_company_kpis(),
            'entities': self.get_business_entities(),
            'portfolio': self.get_portfolio_stats(),
            'generated_at': datetime.now().isoformat()
        }


# Convenience function for backward compatibility
def get_company_overview(db_manager, tenant_id: str = 'delta') -> Dict[str, Any]:
    """Get company overview (standalone function)"""
    service = DataQueryService(db_manager, tenant_id)
    return service.get_company_overview()


def get_company_kpis(db_manager, tenant_id: str = 'delta') -> Dict[str, Any]:
    """Get company KPIs (standalone function)"""
    service = DataQueryService(db_manager, tenant_id)
    return service.get_company_kpis()


def get_business_entities(db_manager, tenant_id: str = 'delta') -> List[Dict[str, Any]]:
    """Get business entities (standalone function)"""
    service = DataQueryService(db_manager, tenant_id)
    return service.get_business_entities()


def get_portfolio_stats(db_manager, tenant_id: str = 'delta') -> Dict[str, Any]:
    """Get portfolio statistics (standalone function)"""
    service = DataQueryService(db_manager, tenant_id)
    return service.get_portfolio_stats()
