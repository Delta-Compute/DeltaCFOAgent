"""
Context Manager for AI Chatbot
Aggregates business context from database for Claude AI prompts
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db_manager


class ContextManager:
    """Manages business context for chatbot conversations"""

    def __init__(self, tenant_id: str = 'delta'):
        self.tenant_id = tenant_id

    def get_business_overview(self) -> Dict[str, Any]:
        """
        Get comprehensive business overview including all context
        """
        return {
            'entities': self.get_business_entities(),
            'investors': self.get_investor_summary(),
            'vendors': self.get_vendor_summary(),
            'classification_rules': self.get_classification_patterns(),
            'business_rules': self.get_business_rules(),
            'recent_transactions': self.get_recent_transaction_stats(),
            'generated_at': datetime.now().isoformat()
        }

    def get_business_entities(self) -> List[Dict[str, Any]]:
        """Get all business entities for the tenant"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, name, description, entity_type, active, created_at
                FROM business_entities
                WHERE tenant_id = %s
                ORDER BY name
            """, (self.tenant_id,))

            entities = []
            for row in cursor.fetchall():
                entities.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'entity_type': row[3],
                    'active': row[4],
                    'created_at': str(row[5]) if row[5] else None
                })

            return entities

        finally:
            conn.close()

    def get_classification_patterns(self) -> List[Dict[str, Any]]:
        """Get all active classification patterns"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, pattern_type, description_pattern, entity,
                       accounting_category, confidence_score, usage_count
                FROM classification_patterns
                WHERE tenant_id = %s AND is_active = TRUE
                ORDER BY pattern_type, confidence_score DESC
            """, (self.tenant_id,))

            patterns = []
            for row in cursor.fetchall():
                patterns.append({
                    'id': row[0],
                    'pattern_type': row[1],
                    'description_pattern': row[2],
                    'entity': row[3],
                    'accounting_category': row[4],
                    'confidence_score': float(row[5]) if row[5] else 0.0,
                    'usage_count': row[6] or 0
                })

            return patterns

        finally:
            conn.close()

    def get_investor_summary(self) -> Dict[str, Any]:
        """Get investor relationships summary"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Get investor count and total invested
            cursor.execute("""
                SELECT COUNT(*), SUM(total_invested),
                       COUNT(CASE WHEN status = 'active' THEN 1 END)
                FROM investor_relationships
                WHERE tenant_id = %s
            """, (self.tenant_id,))

            row = cursor.fetchone()
            total_count = row[0] or 0
            total_invested = float(row[1]) if row[1] else 0.0
            active_count = row[2] or 0

            # Get top investors
            cursor.execute("""
                SELECT investor_name, investor_type, total_invested, status
                FROM investor_relationships
                WHERE tenant_id = %s
                ORDER BY total_invested DESC NULLS LAST
                LIMIT 5
            """, (self.tenant_id,))

            top_investors = []
            for row in cursor.fetchall():
                top_investors.append({
                    'name': row[0],
                    'type': row[1],
                    'total_invested': float(row[2]) if row[2] else 0.0,
                    'status': row[3]
                })

            return {
                'total_count': total_count,
                'active_count': active_count,
                'total_invested': total_invested,
                'top_investors': top_investors
            }

        finally:
            conn.close()

    def get_vendor_summary(self) -> Dict[str, Any]:
        """Get vendor relationships summary"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Get vendor count and total spent
            cursor.execute("""
                SELECT COUNT(*), SUM(total_spent),
                       COUNT(CASE WHEN is_preferred = TRUE THEN 1 END)
                FROM vendor_profiles
                WHERE tenant_id = %s
            """, (self.tenant_id,))

            row = cursor.fetchone()
            total_count = row[0] or 0
            total_spent = float(row[1]) if row[1] else 0.0
            preferred_count = row[2] or 0

            # Get top vendors
            cursor.execute("""
                SELECT vendor_name, vendor_type, total_spent, is_preferred
                FROM vendor_profiles
                WHERE tenant_id = %s
                ORDER BY total_spent DESC NULLS LAST
                LIMIT 5
            """, (self.tenant_id,))

            top_vendors = []
            for row in cursor.fetchall():
                top_vendors.append({
                    'name': row[0],
                    'type': row[1],
                    'total_spent': float(row[2]) if row[2] else 0.0,
                    'is_preferred': row[3]
                })

            return {
                'total_count': total_count,
                'preferred_count': preferred_count,
                'total_spent': total_spent,
                'top_vendors': top_vendors
            }

        finally:
            conn.close()

    def get_business_rules(self) -> List[Dict[str, Any]]:
        """Get active business rules with their conditions and actions"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, rule_name, rule_type, description, priority, is_active
                FROM business_rules
                WHERE tenant_id = %s AND is_active = TRUE
                ORDER BY priority DESC
            """, (self.tenant_id,))

            rules = []
            for row in cursor.fetchall():
                rule_id = row[0]

                # Get conditions for this rule
                cursor.execute("""
                    SELECT field_name, operator, condition_value
                    FROM rule_conditions
                    WHERE rule_id = %s
                    ORDER BY order_num
                """, (rule_id,))

                conditions = []
                for cond_row in cursor.fetchall():
                    conditions.append({
                        'field': cond_row[0],
                        'operator': cond_row[1],
                        'value': cond_row[2]
                    })

                # Get actions for this rule
                cursor.execute("""
                    SELECT action_type, target_category, target_subcategory,
                           target_entity, confidence_score
                    FROM rule_actions
                    WHERE rule_id = %s
                """, (rule_id,))

                actions = []
                for act_row in cursor.fetchall():
                    actions.append({
                        'action_type': act_row[0],
                        'target_category': act_row[1],
                        'target_subcategory': act_row[2],
                        'target_entity': act_row[3],
                        'confidence_score': float(act_row[4]) if act_row[4] else 0.0
                    })

                rules.append({
                    'id': rule_id,
                    'rule_name': row[1],
                    'rule_type': row[2],
                    'description': row[3],
                    'priority': row[4],
                    'conditions': conditions,
                    'actions': actions
                })

            return rules

        finally:
            conn.close()

    def get_recent_transaction_stats(self) -> Dict[str, Any]:
        """Get recent transaction statistics"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Get transaction counts by entity (last 30 days)
            cursor.execute("""
                SELECT entity, COUNT(*), SUM(amount), AVG(confidence_score)
                FROM transactions
                WHERE tenant_id = %s
                  AND date >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY entity
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """, (self.tenant_id,))

            entity_stats = []
            for row in cursor.fetchall():
                entity_stats.append({
                    'entity': row[0],
                    'count': row[1],
                    'total_amount': float(row[2]) if row[2] else 0.0,
                    'avg_confidence': float(row[3]) if row[3] else 0.0
                })

            # Get total transaction count
            cursor.execute("""
                SELECT COUNT(*),
                       COUNT(CASE WHEN confidence_score >= 0.9 THEN 1 END),
                       COUNT(CASE WHEN confidence_score < 0.7 THEN 1 END)
                FROM transactions
                WHERE tenant_id = %s
            """, (self.tenant_id,))

            row = cursor.fetchone()

            return {
                'total_transactions': row[0] or 0,
                'high_confidence_count': row[1] or 0,
                'low_confidence_count': row[2] or 0,
                'by_entity': entity_stats
            }

        finally:
            conn.close()

    def format_for_claude_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Format business context for Claude AI system prompt
        """
        if context is None:
            context = self.get_business_overview()

        # Build formatted context string
        sections = []

        # Business entities section
        if context.get('entities'):
            entities_str = "BUSINESS ENTITIES:\n"
            for entity in context['entities']:
                status = "Active" if entity.get('active') else "Inactive"
                entities_str += f"- {entity['name']} ({entity.get('entity_type', 'unknown')}): {entity.get('description', 'No description')} [{status}]\n"
            sections.append(entities_str)

        # Investors section
        if context.get('investors') and context['investors'].get('total_count', 0) > 0:
            inv = context['investors']
            investors_str = f"INVESTORS ({inv['total_count']} total, {inv['active_count']} active, ${inv['total_invested']:,.2f} invested):\n"
            for investor in inv.get('top_investors', []):
                investors_str += f"- {investor['name']} ({investor.get('type', 'N/A')}): ${investor.get('total_invested', 0):,.2f} - {investor.get('status', 'N/A')}\n"
            sections.append(investors_str)

        # Vendors section
        if context.get('vendors') and context['vendors'].get('total_count', 0) > 0:
            vnd = context['vendors']
            vendors_str = f"VENDORS ({vnd['total_count']} total, {vnd['preferred_count']} preferred, ${vnd['total_spent']:,.2f} spent):\n"
            for vendor in vnd.get('top_vendors', []):
                pref = " ⭐" if vendor.get('is_preferred') else ""
                vendors_str += f"- {vendor['name']} ({vendor.get('type', 'N/A')}): ${vendor.get('total_spent', 0):,.2f}{pref}\n"
            sections.append(vendors_str)

        # Classification patterns section (show top patterns by type)
        if context.get('classification_rules'):
            patterns_by_type = {}
            for pattern in context['classification_rules']:
                ptype = pattern.get('pattern_type', 'other')
                if ptype not in patterns_by_type:
                    patterns_by_type[ptype] = []
                patterns_by_type[ptype].append(pattern)

            patterns_str = "CLASSIFICATION PATTERNS:\n"
            for ptype, patterns in patterns_by_type.items():
                patterns_str += f"\n{ptype.upper()}:\n"
                for pattern in patterns[:5]:  # Top 5 per type
                    patterns_str += f"  - '{pattern['description_pattern']}' → {pattern.get('accounting_category', 'N/A')}"
                    if pattern.get('entity'):
                        patterns_str += f" ({pattern['entity']})"
                    patterns_str += f" [confidence: {pattern.get('confidence_score', 0):.2f}]\n"
            sections.append(patterns_str)

        # Business rules section
        if context.get('business_rules'):
            rules_str = f"ACTIVE BUSINESS RULES ({len(context['business_rules'])} rules):\n"
            for rule in context['business_rules'][:10]:  # Top 10 rules
                rules_str += f"- {rule['rule_name']} ({rule.get('rule_type', 'N/A')}): {rule.get('description', 'No description')}\n"
                if rule.get('conditions'):
                    rules_str += f"  Conditions: {len(rule['conditions'])} condition(s)\n"
            sections.append(rules_str)

        # Transaction stats section
        if context.get('recent_transactions'):
            stats = context['recent_transactions']
            stats_str = f"TRANSACTION STATISTICS:\n"
            stats_str += f"- Total transactions: {stats.get('total_transactions', 0):,}\n"
            stats_str += f"- High confidence (≥90%): {stats.get('high_confidence_count', 0):,}\n"
            stats_str += f"- Low confidence (<70%): {stats.get('low_confidence_count', 0):,}\n"
            if stats.get('by_entity'):
                stats_str += "\nRecent activity (last 30 days) by entity:\n"
                for entity_stat in stats['by_entity'][:5]:
                    stats_str += f"  - {entity_stat['entity']}: {entity_stat['count']} transactions, ${entity_stat['total_amount']:,.2f}\n"
            sections.append(stats_str)

        return "\n".join(sections)


# Convenience function
def get_business_context_prompt(tenant_id: str = 'delta') -> str:
    """Quick function to get formatted business context for Claude"""
    manager = ContextManager(tenant_id)
    return manager.format_for_claude_prompt()


if __name__ == '__main__':
    # Test the context manager
    manager = ContextManager('delta')
    context = manager.get_business_overview()
    print(json.dumps(context, indent=2))
    print("\n" + "="*80 + "\n")
    print(manager.format_for_claude_prompt(context))
