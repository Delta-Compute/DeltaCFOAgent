#!/usr/bin/env python3
"""
AI-Powered Homepage Content Generator
Uses Claude AI to generate engaging, data-driven homepage content
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import anthropic

from .data_queries import DataQueryService

logger = logging.getLogger(__name__)


class HomepageContentGenerator:
    """Generates homepage content using Claude AI based on company data"""

    def __init__(self, db_manager, tenant_id: str = 'delta'):
        """
        Initialize the homepage content generator

        Args:
            db_manager: DatabaseManager instance
            tenant_id: Tenant identifier
        """
        self.db_manager = db_manager
        self.tenant_id = tenant_id
        self.data_service = DataQueryService(db_manager, tenant_id)

        # Initialize Claude API client
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.claude_client = anthropic.Anthropic(api_key=api_key)
        else:
            self.claude_client = None
            logger.warning("ANTHROPIC_API_KEY not set - AI generation will be disabled")

    def _build_generation_prompt(self, data: Dict[str, Any]) -> str:
        """
        Build the prompt for Claude to generate homepage content

        Args:
            data: Dictionary with company, KPIs, entities, and portfolio data

        Returns:
            Formatted prompt string
        """
        company = data.get('company', {})
        kpis = data.get('kpis', {})
        entities = data.get('entities', [])
        portfolio = data.get('portfolio', {})

        prompt = f"""You are a professional content writer for a financial technology company. Your task is to generate engaging, professional homepage content based on real company data.

**Company Information:**
- Name: {company.get('company_name', 'Company')}
- Industry: {company.get('industry', 'Technology')}
- Current Description: {company.get('company_description', 'N/A')}

**Financial Metrics (KPIs):**
- Total Transactions Processed: {kpis.get('total_transactions', 0):,}
- Total Revenue: ${kpis.get('total_revenue', 0):,.2f}
- Total Expenses: ${kpis.get('total_expenses', 0):,.2f}
- Net Profit: ${kpis.get('net_profit', 0):,.2f}
- Years of Historical Data: {kpis.get('years_of_data', 0)}
- Transactions Needing Review: {kpis.get('needs_review', 0)}

**Invoice Statistics:**
- Total Invoices: {kpis.get('total_invoices', 0)}
- Total Invoice Value: ${kpis.get('total_invoice_value', 0):,.2f}
- Paid Invoices: {kpis.get('paid_invoices', 0)}
- Overdue Invoices: {kpis.get('overdue_invoices', 0)}

**Business Entities/Portfolio Companies:**
{self._format_entities(entities)}

**Portfolio Overview:**
- Total Business Entities: {portfolio.get('total_entities', 0)}
- Active Crypto Wallets: {portfolio.get('wallet_count', 0)}
- Connected Bank Accounts: {portfolio.get('bank_account_count', 0)}

**Top Performing Entities:**
{self._format_top_entities(kpis.get('top_entities', []))}

**Recent Trends:**
{self._format_monthly_trends(kpis.get('monthly_trends', []))}

---

Please generate the following in JSON format:

1. **company_tagline**: A compelling 1-sentence tagline (max 100 characters) that captures the essence of the business
2. **company_description**: A professional 2-3 sentence description (150-250 words) that highlights the company's mission, capabilities, and value proposition based on the actual data above
3. **ai_insights**: 3-5 bullet points of key insights, trends, or highlights from the financial data that would be interesting to display on the homepage
4. **kpi_highlights**: Suggest 4-6 key metrics to prominently display with friendly labels (e.g., "Transactions Processed", "Revenue Generated", "Years of Data", "Active Portfolios")

Return ONLY valid JSON in this exact format:
{{
  "company_tagline": "...",
  "company_description": "...",
  "ai_insights": ["insight 1", "insight 2", "insight 3"],
  "kpi_highlights": [
    {{"label": "...", "value": "...", "icon": "📊"}},
    {{"label": "...", "value": "...", "icon": "💰"}}
  ]
}}

Important guidelines:
- Be professional and factual
- Use the actual numbers provided
- Make it engaging but not overly promotional
- Focus on achievements and capabilities
- Keep language clear and concise
- Use appropriate emojis for visual appeal in kpi_highlights
"""
        return prompt

    def _format_entities(self, entities: list) -> str:
        """Format business entities for the prompt"""
        if not entities:
            return "No entities configured"

        formatted = []
        for entity in entities[:10]:  # Limit to top 10
            formatted.append(f"  - {entity.get('name', 'Unknown')}: {entity.get('description', 'No description')}")

        return "\n".join(formatted)

    def _format_top_entities(self, top_entities: list) -> str:
        """Format top performing entities for the prompt"""
        if not top_entities:
            return "No transaction data available"

        formatted = []
        for entity in top_entities[:5]:  # Top 5
            name = entity.get('name', 'Unknown')
            count = entity.get('transaction_count', 0)
            revenue = entity.get('revenue', 0)
            expenses = entity.get('expenses', 0)
            formatted.append(f"  - {name}: {count:,} transactions, ${revenue:,.2f} revenue, ${expenses:,.2f} expenses")

        return "\n".join(formatted)

    def _format_monthly_trends(self, trends: list) -> str:
        """Format monthly trends for the prompt"""
        if not trends:
            return "No trend data available"

        formatted = []
        for trend in trends[:6]:  # Last 6 months
            month = trend.get('month', 'Unknown')[:7] if trend.get('month') else 'Unknown'  # YYYY-MM
            revenue = trend.get('revenue', 0)
            expenses = trend.get('expenses', 0)
            count = trend.get('transaction_count', 0)
            formatted.append(f"  - {month}: {count} transactions, ${revenue:,.2f} revenue, ${expenses:,.2f} expenses")

        return "\n".join(formatted)

    def generate_content(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Generate homepage content using Claude AI

        Args:
            use_cache: Whether to check for cached content first

        Returns:
            Dictionary with generated content
        """
        try:
            # Check for cached content if requested
            if use_cache:
                cached = self._get_cached_content()
                if cached:
                    logger.info(f"Using cached homepage content for tenant {self.tenant_id}")
                    return cached

            # Gather all data
            logger.info(f"Gathering data for homepage generation (tenant: {self.tenant_id})")
            data = self.data_service.get_all_homepage_data()

            # Generate content with Claude
            if not self.claude_client:
                logger.warning("Claude API not available, using fallback content")
                return self._generate_fallback_content(data)

            logger.info("Calling Claude API to generate homepage content")
            prompt = self._build_generation_prompt(data)

            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20250219",
                max_tokens=2000,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response
            content_text = response.content[0].text
            logger.debug(f"Claude response: {content_text}")

            # Extract JSON from response
            generated_content = json.loads(content_text)

            # Combine with original data
            result = {
                'company_name': data['company'].get('company_name'),
                'tagline': generated_content.get('company_tagline'),
                'description': generated_content.get('company_description'),
                'ai_insights': generated_content.get('ai_insights', []),
                'kpi_highlights': generated_content.get('kpi_highlights', []),
                'kpis': data['kpis'],
                'entities': data['entities'],
                'portfolio': data['portfolio'],
                'generated_at': datetime.now().isoformat(),
                'generation_prompt': prompt
            }

            # Cache the generated content
            self._cache_content(result)

            logger.info("Homepage content generated successfully")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.error(f"Response was: {content_text if 'content_text' in locals() else 'No response'}")
            return self._generate_fallback_content(data)

        except Exception as e:
            logger.error(f"Error generating homepage content: {e}")
            # Return fallback content on error
            data = self.data_service.get_all_homepage_data()
            return self._generate_fallback_content(data)

    def _generate_fallback_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate basic content without AI when Claude is unavailable

        Args:
            data: Company data dictionary

        Returns:
            Basic homepage content
        """
        company = data.get('company', {})
        kpis = data.get('kpis', {})

        return {
            'company_name': company.get('company_name', 'Company'),
            'tagline': company.get('company_tagline', 'Financial Intelligence Platform'),
            'description': company.get('company_description', 'AI-powered financial management and analytics.'),
            'ai_insights': [
                f"Processing {kpis.get('total_transactions', 0):,} transactions",
                f"Managing ${kpis.get('total_revenue', 0):,.2f} in revenue",
                f"{kpis.get('years_of_data', 0)} years of historical data"
            ],
            'kpi_highlights': [
                {'label': 'Transactions', 'value': f"{kpis.get('total_transactions', 0):,}", 'icon': '📊'},
                {'label': 'Revenue', 'value': f"${kpis.get('total_revenue', 0):,.0f}", 'icon': '💰'},
                {'label': 'Years of Data', 'value': str(kpis.get('years_of_data', 0)), 'icon': '📅'},
                {'label': 'Business Units', 'value': str(data.get('portfolio', {}).get('total_entities', 0)), 'icon': '🏢'}
            ],
            'kpis': kpis,
            'entities': data.get('entities', []),
            'portfolio': data.get('portfolio', {}),
            'generated_at': datetime.now().isoformat(),
            'generation_method': 'fallback'
        }

    def _get_cached_content(self) -> Optional[Dict[str, Any]]:
        """
        Get cached homepage content from database

        Returns:
            Cached content or None if not found/expired
        """
        try:
            query = """
                SELECT
                    content_json,
                    generated_at
                FROM homepage_content
                WHERE tenant_id = %s
                AND (expires_at IS NULL OR expires_at > NOW())
                AND generated_at > NOW() - INTERVAL '24 hours'
            """

            result = self.db_manager.execute_query(query, (self.tenant_id,), fetch_one=True)

            if result and result['content_json']:
                content = result['content_json']
                # Add metadata
                content['cached'] = True
                if result.get('generated_at'):
                    content['generated_at'] = result['generated_at'].isoformat()
                logger.info(f"Retrieved cached homepage content for tenant {self.tenant_id}")
                return content

            return None

        except Exception as e:
            logger.error(f"Error fetching cached content: {e}")
            return None

    def _cache_content(self, content: Dict[str, Any]) -> bool:
        """
        Cache generated content in the database

        Args:
            content: Generated content to cache

        Returns:
            True if successful, False otherwise
        """
        try:
            # Store full content as JSON in content_json field
            query = """
                INSERT INTO homepage_content (
                    tenant_id,
                    content_json,
                    generation_prompt,
                    model_version,
                    expires_at
                ) VALUES (%s, %s, %s, %s, NOW() + INTERVAL '24 hours')
                ON CONFLICT (tenant_id) DO UPDATE SET
                    content_json = EXCLUDED.content_json,
                    generation_prompt = EXCLUDED.generation_prompt,
                    model_version = EXCLUDED.model_version,
                    generated_at = CURRENT_TIMESTAMP,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = CURRENT_TIMESTAMP
            """

            self.db_manager.execute_query(query, (
                self.tenant_id,
                json.dumps(content),
                content.get('generation_prompt'),
                'claude-3-5-sonnet-20250219'
            ))

            logger.info(f"Cached homepage content for tenant {self.tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Error caching content: {e}")
            return False

    def invalidate_cache(self) -> bool:
        """
        Invalidate cached homepage content by setting expires_at to the past

        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
                UPDATE homepage_content
                SET expires_at = NOW() - INTERVAL '1 hour'
                WHERE tenant_id = %s
            """

            self.db_manager.execute_query(query, (self.tenant_id,))

            logger.info(f"Invalidated cache for tenant {self.tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return False
