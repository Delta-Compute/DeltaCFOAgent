#!/usr/bin/env python3
"""
Chatbot Context Loader
Builds tenant-specific context for AI CFO Assistant chatbot
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ChatbotContextBuilder:
    """
    Builds rich context for chatbot based on tenant data
    """

    def __init__(self, db_manager, tenant_id: str):
        """
        Initialize context builder

        Args:
            db_manager: Database manager instance
            tenant_id: Current tenant identifier
        """
        self.db_manager = db_manager
        self.tenant_id = tenant_id
        self.business_knowledge = self._load_business_knowledge()

    def _load_business_knowledge(self) -> Dict[str, Any]:
        """
        Load business knowledge from business_knowledge.md

        Returns:
            dict: Parsed business knowledge
        """
        try:
            knowledge_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'business_knowledge.md'
            )

            if not os.path.exists(knowledge_file):
                logger.warning("business_knowledge.md not found")
                return {}

            with open(knowledge_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse business entities
            entities = []
            revenue_patterns = []
            expense_patterns = []
            accounting_categories = []

            lines = content.split('\n')
            current_section = None

            for line in lines:
                line = line.strip()

                if line.startswith('## Business Entities'):
                    current_section = 'entities'
                elif line.startswith('## Revenue Classification'):
                    current_section = 'revenue'
                elif line.startswith('## Expense Classification'):
                    current_section = 'expenses'
                elif line.startswith('## Accounting Categories'):
                    current_section = 'categories'
                elif line.startswith('##'):
                    current_section = None

                # Parse entities
                if current_section == 'entities' and line.startswith('- **'):
                    entity = line.replace('- **', '').split('**:')[0].strip()
                    description = line.split('**:')[1].strip() if '**:' in line else ''
                    entities.append({'name': entity, 'description': description})

                # Parse revenue patterns
                elif current_section == 'revenue' and line.startswith('- **'):
                    pattern = line.replace('- **', '').split('**:')[0].strip()
                    revenue_patterns.append(pattern)

                # Parse expense patterns
                elif current_section == 'expenses' and line.startswith('- **'):
                    pattern = line.replace('- **', '').split('**:')[0].strip()
                    expense_patterns.append(pattern)

                # Parse accounting categories
                elif current_section == 'categories' and line.startswith('- **'):
                    category = line.replace('- **', '').split('**:')[0].strip()
                    description = line.split('**:')[1].strip() if '**:' in line else ''
                    accounting_categories.append({'category': category, 'description': description})

            return {
                'entities': entities,
                'revenue_patterns': revenue_patterns,
                'expense_patterns': expense_patterns,
                'accounting_categories': accounting_categories
            }

        except Exception as e:
            logger.error(f"Error loading business knowledge: {e}")
            return {}

    def get_tenant_profile(self) -> Dict[str, Any]:
        """
        Get tenant business profile

        Returns:
            dict: Tenant profile information
        """
        # For now, use default Delta profile
        # In the future, this would query a tenants table
        profile = {
            'tenant_id': self.tenant_id,
            'tenant_name': 'Delta LLC',
            'business_type': 'Financial Services & Trading',
            'jurisdiction': 'United States',
            'accounting_standard': 'US GAAP',
            'fiscal_year_end': 'December 31',
            'base_currency': 'USD',
            'entities': self.business_knowledge.get('entities', [])
        }

        return profile

    def get_recent_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get recent financial statistics for context

        Returns:
            dict: Recent stats or None if unavailable
        """
        try:
            # Get last 30 days stats
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

            query = """
                SELECT
                    COUNT(*) as transaction_count,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_revenue,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expenses,
                    COUNT(DISTINCT business_entity) as entity_count,
                    COUNT(CASE WHEN needs_review = true THEN 1 END) as needs_review_count
                FROM transactions
                WHERE tenant_id = %s AND date >= %s
            """

            result = self.db_manager.execute_query(
                query,
                (self.tenant_id, thirty_days_ago)
            )

            if result and len(result) > 0:
                row = result[0]
                return {
                    'period': 'Last 30 days',
                    'transaction_count': row[0] or 0,
                    'total_revenue': float(row[1] or 0),
                    'total_expenses': float(row[2] or 0),
                    'entity_count': row[3] or 0,
                    'needs_review_count': row[4] or 0
                }

            return None

        except Exception as e:
            logger.error(f"Error getting recent stats: {e}")
            return None

    def build_system_prompt(self) -> str:
        """
        Build comprehensive system prompt for Claude API

        Returns:
            str: System prompt with full tenant context
        """
        profile = self.get_tenant_profile()
        stats = self.get_recent_stats()

        # Build entities description
        entities_desc = "\n".join([
            f"  - {entity['name']}: {entity['description']}"
            for entity in profile.get('entities', [])
        ])

        # Build accounting categories
        categories = self.business_knowledge.get('accounting_categories', [])
        categories_desc = "\n".join([
            f"  - {cat['category']}: {cat['description']}"
            for cat in categories
        ])

        # Build stats summary
        stats_desc = ""
        if stats:
            stats_desc = f"""
Recent Financial Activity ({stats['period']}):
- Total Transactions: {stats['transaction_count']}
- Total Revenue: ${stats['total_revenue']:,.2f}
- Total Expenses: ${stats['total_expenses']:,.2f}
- Active Entities: {stats['entity_count']}
- Transactions Needing Review: {stats['needs_review_count']}
"""

        prompt = f"""You are an AI CFO Assistant for {profile['tenant_name']}, an expert in financial management, accounting, and business operations.

TENANT PROFILE:
- Business Type: {profile['business_type']}
- Jurisdiction: {profile['jurisdiction']}
- Accounting Standard: {profile['accounting_standard']}
- Fiscal Year End: {profile['fiscal_year_end']}
- Base Currency: {profile['base_currency']}

BUSINESS ENTITIES:
{entities_desc}

ACCOUNTING CATEGORIES & CLASSIFICATIONS:
{categories_desc}

{stats_desc}

YOUR ROLE:
You are a helpful, professional CFO assistant with deep knowledge of:
1. US GAAP accounting standards and financial reporting
2. The specific business entities and their operations
3. Revenue recognition, expense classification, and financial analysis
4. Tax planning and regulatory compliance
5. Financial metrics, KPIs, and business intelligence

GUIDELINES:
- Provide accurate, professional financial advice
- Reference specific business entities when relevant
- Explain accounting concepts clearly
- Suggest best practices for financial management
- Be concise but thorough
- When discussing transactions or classifications, reference the accounting categories above
- If asked about data not in your context, acknowledge limitations

IMPORTANT:
- You have access to the business structure and accounting rules above
- For specific transaction data or detailed reports, users should use the dashboard
- Focus on explaining concepts, providing guidance, and answering financial questions
- Always maintain professional, CFO-level expertise

How can you assist with financial or accounting questions today?"""

        return prompt

    def format_conversation_history(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Format conversation history for Claude API

        Args:
            history: List of conversation messages

        Returns:
            list: Formatted messages for Claude API
        """
        formatted = []

        for msg in history:
            role = msg.get('role')
            content = msg.get('content')

            if role and content:
                # Claude API uses 'user' and 'assistant' roles
                formatted.append({
                    'role': role,
                    'content': content
                })

        return formatted


def get_chatbot_context(db_manager, tenant_id: str) -> ChatbotContextBuilder:
    """
    Factory function to create chatbot context builder

    Args:
        db_manager: Database manager instance
        tenant_id: Current tenant identifier

    Returns:
        ChatbotContextBuilder: Initialized context builder
    """
    return ChatbotContextBuilder(db_manager, tenant_id)
