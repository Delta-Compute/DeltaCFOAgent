"""
Database Modifier for AI Chatbot
Safe database modification layer with validation and audit logging
"""

import json
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import sys
import os
import re

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db_manager


class DatabaseModifier:
    """Handles safe database modifications with validation and audit logging"""

    def __init__(self, tenant_id: str = 'delta', user_id: str = 'chatbot', session_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.session_id = session_id

    def _log_audit(self, conn, transaction_id: int, action: str, changes: Dict, reason: str = None):
        """Log changes to audit history"""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transaction_audit_history
            (transaction_id, tenant_id, action, changes, user_id, session_id, change_reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (transaction_id, self.tenant_id, action, json.dumps(changes), self.user_id, self.session_id, reason))

    # ========================================
    # BUSINESS ENTITY OPERATIONS
    # ========================================

    def add_business_entity(self, name: str, entity_type: str, description: str = None) -> Tuple[bool, str, Optional[int]]:
        """
        Add a new business entity

        Returns: (success, message, entity_id)
        """
        # Validate inputs
        if not name or not name.strip():
            return False, "Entity name is required", None

        valid_types = ['subsidiary', 'vendor', 'customer', 'internal']
        if entity_type not in valid_types:
            return False, f"Invalid entity type. Must be one of: {', '.join(valid_types)}", None

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Check if entity already exists
            cursor.execute("""
                SELECT id FROM business_entities
                WHERE tenant_id = %s AND name = %s
            """, (self.tenant_id, name))

            if cursor.fetchone():
                conn.close()
                return False, f"Entity '{name}' already exists", None

            # Insert new entity
            cursor.execute("""
                INSERT INTO business_entities (tenant_id, name, description, entity_type)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (self.tenant_id, name, description, entity_type))

            entity_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()

            return True, f"Successfully added entity '{name}'", entity_id

        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Error adding entity: {str(e)}", None

    def update_business_entity(self, entity_id: int, **kwargs) -> Tuple[bool, str]:
        """
        Update an existing business entity

        Allowed fields: name, description, entity_type, active
        """
        allowed_fields = {'name', 'description', 'entity_type', 'active'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False, "No valid fields to update"

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Verify entity exists and belongs to tenant
            cursor.execute("""
                SELECT id FROM business_entities
                WHERE id = %s AND tenant_id = %s
            """, (entity_id, self.tenant_id))

            if not cursor.fetchone():
                conn.close()
                return False, "Entity not found"

            # Build UPDATE query
            set_clause = ", ".join([f"{field} = %s" for field in updates.keys()])
            values = list(updates.values()) + [entity_id, self.tenant_id]

            cursor.execute(f"""
                UPDATE business_entities
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND tenant_id = %s
            """, values)

            conn.commit()
            conn.close()

            return True, f"Successfully updated entity (fields: {', '.join(updates.keys())})"

        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Error updating entity: {str(e)}"

    # ========================================
    # CLASSIFICATION PATTERN OPERATIONS
    # ========================================

    def add_classification_pattern(self, pattern_type: str, description_pattern: str,
                                   accounting_category: str, entity: str = None,
                                   confidence_score: float = 0.75) -> Tuple[bool, str, Optional[int]]:
        """
        Add a new classification pattern

        Returns: (success, message, pattern_id)
        """
        # Validate pattern type
        valid_types = ['revenue', 'expense', 'crypto', 'transfer']
        if pattern_type not in valid_types:
            return False, f"Invalid pattern type. Must be one of: {', '.join(valid_types)}", None

        # Validate confidence score
        if not 0 <= confidence_score <= 1:
            return False, "Confidence score must be between 0 and 1", None

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Check if pattern already exists
            cursor.execute("""
                SELECT id FROM classification_patterns
                WHERE tenant_id = %s AND pattern_type = %s AND description_pattern = %s
            """, (self.tenant_id, pattern_type, description_pattern))

            if cursor.fetchone():
                conn.close()
                return False, f"Pattern '{description_pattern}' already exists for type '{pattern_type}'", None

            # Insert new pattern
            cursor.execute("""
                INSERT INTO classification_patterns
                (tenant_id, pattern_type, description_pattern, entity, accounting_category,
                 confidence_score, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (self.tenant_id, pattern_type, description_pattern, entity, accounting_category,
                  confidence_score, self.user_id))

            pattern_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()

            return True, f"Successfully added classification pattern", pattern_id

        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Error adding pattern: {str(e)}", None

    # ========================================
    # BUSINESS RULE OPERATIONS
    # ========================================

    def create_business_rule(self, rule_name: str, rule_type: str, description: str,
                            conditions: List[Dict], actions: List[Dict],
                            priority: int = 100) -> Tuple[bool, str, Optional[int]]:
        """
        Create a complete business rule with conditions and actions

        conditions format: [{'field': 'description', 'operator': 'contains', 'value': 'AWS'}]
        actions format: [{'action_type': 'classify', 'target_category': 'Technology Expenses'}]

        Returns: (success, message, rule_id)
        """
        # Validate rule type
        valid_types = ['classification', 'alert', 'validation']
        if rule_type not in valid_types:
            return False, f"Invalid rule type. Must be one of: {', '.join(valid_types)}", None

        # Validate conditions
        if not conditions:
            return False, "At least one condition is required", None

        valid_operators = ['contains', 'equals', 'greater_than', 'less_than', 'regex_match']
        for cond in conditions:
            if 'field' not in cond or 'operator' not in cond or 'value' not in cond:
                return False, "Each condition must have 'field', 'operator', and 'value'", None
            if cond['operator'] not in valid_operators:
                return False, f"Invalid operator '{cond['operator']}'. Must be one of: {', '.join(valid_operators)}", None

        # Validate actions
        if not actions:
            return False, "At least one action is required", None

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Check if rule name already exists
            cursor.execute("""
                SELECT id FROM business_rules
                WHERE tenant_id = %s AND rule_name = %s
            """, (self.tenant_id, rule_name))

            if cursor.fetchone():
                conn.close()
                return False, f"Rule '{rule_name}' already exists", None

            # Insert rule
            cursor.execute("""
                INSERT INTO business_rules
                (tenant_id, rule_name, rule_type, description, priority, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (self.tenant_id, rule_name, rule_type, description, priority, self.user_id))

            rule_id = cursor.fetchone()[0]

            # Insert conditions
            for order_num, condition in enumerate(conditions):
                cursor.execute("""
                    INSERT INTO rule_conditions
                    (rule_id, field_name, operator, condition_value, order_num)
                    VALUES (%s, %s, %s, %s, %s)
                """, (rule_id, condition['field'], condition['operator'], condition['value'], order_num))

            # Insert actions
            for action in actions:
                cursor.execute("""
                    INSERT INTO rule_actions
                    (rule_id, action_type, target_category, target_subcategory,
                     target_entity, confidence_score)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (rule_id, action.get('action_type', 'classify'),
                      action.get('target_category'),
                      action.get('target_subcategory'),
                      action.get('target_entity'),
                      action.get('confidence_score', 0.85)))

            conn.commit()
            conn.close()

            return True, f"Successfully created rule '{rule_name}' with {len(conditions)} condition(s) and {len(actions)} action(s)", rule_id

        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Error creating rule: {str(e)}", None

    # ========================================
    # INVESTOR OPERATIONS
    # ========================================

    def add_investor(self, investor_name: str, investor_type: str,
                    contact_email: str = None, country: str = None,
                    investment_focus: str = None) -> Tuple[bool, str, Optional[int]]:
        """
        Add a new investor

        Returns: (success, message, investor_id)
        """
        valid_types = ['VC', 'angel', 'institutional', 'individual']
        if investor_type not in valid_types:
            return False, f"Invalid investor type. Must be one of: {', '.join(valid_types)}", None

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO investor_relationships
                (tenant_id, investor_name, investor_type, country, contact_email, investment_focus, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'prospect')
                RETURNING id
            """, (self.tenant_id, investor_name, investor_type, country, contact_email, investment_focus))

            investor_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()

            return True, f"Successfully added investor '{investor_name}'", investor_id

        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Error adding investor: {str(e)}", None

    def record_investment(self, investor_id: int, entity_id: int, amount: float,
                         currency: str = 'USD', investment_date: date = None,
                         terms: str = None, transaction_id: int = None) -> Tuple[bool, str, Optional[int]]:
        """
        Record a new investment

        Returns: (success, message, investment_id)
        """
        if investment_date is None:
            investment_date = date.today()

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Verify investor exists
            cursor.execute("""
                SELECT id FROM investor_relationships
                WHERE id = %s AND tenant_id = %s
            """, (investor_id, self.tenant_id))

            if not cursor.fetchone():
                conn.close()
                return False, "Investor not found", None

            # Verify entity exists
            cursor.execute("""
                SELECT id FROM business_entities
                WHERE id = %s AND tenant_id = %s
            """, (entity_id, self.tenant_id))

            if not cursor.fetchone():
                conn.close()
                return False, "Entity not found", None

            # Insert investment
            cursor.execute("""
                INSERT INTO investments
                (tenant_id, investor_id, entity_id, amount, currency, investment_date,
                 terms, status, transaction_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', %s)
                RETURNING id
            """, (self.tenant_id, investor_id, entity_id, amount, currency,
                  investment_date, terms, transaction_id))

            investment_id = cursor.fetchone()[0]

            # Update investor totals
            cursor.execute("""
                UPDATE investor_relationships
                SET total_invested = COALESCE(total_invested, 0) + %s,
                    last_investment_date = %s,
                    first_investment_date = COALESCE(first_investment_date, %s),
                    status = 'active'
                WHERE id = %s
            """, (amount, investment_date, investment_date, investor_id))

            conn.commit()
            conn.close()

            return True, f"Successfully recorded investment of {currency} {amount:,.2f}", investment_id

        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Error recording investment: {str(e)}", None

    # ========================================
    # VENDOR OPERATIONS
    # ========================================

    def add_vendor(self, vendor_name: str, vendor_type: str,
                  contact_email: str = None, payment_terms: str = None,
                  is_preferred: bool = False) -> Tuple[bool, str, Optional[int]]:
        """
        Add a new vendor

        Returns: (success, message, vendor_id)
        """
        valid_types = ['service_provider', 'supplier', 'contractor']
        if vendor_type not in valid_types:
            return False, f"Invalid vendor type. Must be one of: {', '.join(valid_types)}", None

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO vendor_profiles
                (tenant_id, vendor_name, vendor_type, contact_email, payment_terms, is_preferred)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (self.tenant_id, vendor_name, vendor_type, contact_email, payment_terms, is_preferred))

            vendor_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()

            return True, f"Successfully added vendor '{vendor_name}'", vendor_id

        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Error adding vendor: {str(e)}", None

    # ========================================
    # TRANSACTION RECLASSIFICATION
    # ========================================

    def reclassify_transactions(self, filters: Dict, new_classification: Dict,
                               preview: bool = False) -> Tuple[bool, str, List[int]]:
        """
        Reclassify transactions based on filters

        filters: {'description_contains': 'AWS', 'entity': 'Delta LLC', 'date_from': '2024-01-01'}
        new_classification: {'category': 'Technology Expenses', 'entity': 'Delta LLC', 'confidence': 0.9}
        preview: If True, return affected transaction IDs without making changes

        Returns: (success, message, affected_transaction_ids)
        """
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Build WHERE clause based on filters
            where_conditions = ["tenant_id = %s"]
            params = [self.tenant_id]

            if filters.get('description_contains'):
                where_conditions.append("description ILIKE %s")
                params.append(f"%{filters['description_contains']}%")

            if filters.get('entity'):
                where_conditions.append("entity = %s")
                params.append(filters['entity'])

            if filters.get('category'):
                where_conditions.append("category = %s")
                params.append(filters['category'])

            if filters.get('date_from'):
                where_conditions.append("date >= %s")
                params.append(filters['date_from'])

            if filters.get('date_to'):
                where_conditions.append("date <= %s")
                params.append(filters['date_to'])

            if filters.get('amount_min'):
                where_conditions.append("amount >= %s")
                params.append(filters['amount_min'])

            if filters.get('amount_max'):
                where_conditions.append("amount <= %s")
                params.append(filters['amount_max'])

            where_clause = " AND ".join(where_conditions)

            # Get affected transaction IDs
            cursor.execute(f"""
                SELECT id FROM transactions
                WHERE {where_clause}
            """, params)

            affected_ids = [row[0] for row in cursor.fetchall()]

            if not affected_ids:
                conn.close()
                return True, "No transactions match the specified filters", []

            # If preview mode, return IDs without making changes
            if preview:
                conn.close()
                return True, f"Preview: {len(affected_ids)} transaction(s) would be affected", affected_ids

            # Build UPDATE clause based on new_classification
            update_fields = []
            update_params = []

            if new_classification.get('category'):
                update_fields.append("category = %s")
                update_params.append(new_classification['category'])

            if new_classification.get('subcategory'):
                update_fields.append("subcategory = %s")
                update_params.append(new_classification['subcategory'])

            if new_classification.get('entity'):
                update_fields.append("entity = %s")
                update_params.append(new_classification['entity'])

            if new_classification.get('confidence_score'):
                update_fields.append("confidence_score = %s")
                update_params.append(new_classification['confidence_score'])

            if not update_fields:
                conn.close()
                return False, "No classification fields to update", []

            update_clause = ", ".join(update_fields)
            update_params.extend(params)

            # Perform update
            cursor.execute(f"""
                UPDATE transactions
                SET {update_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE {where_clause}
            """, update_params)

            # Log audit entries for each affected transaction
            for trans_id in affected_ids:
                self._log_audit(conn, trans_id, 'UPDATE', new_classification,
                              f"Bulk reclassification: {filters}")

            conn.commit()
            conn.close()

            return True, f"Successfully reclassified {len(affected_ids)} transaction(s)", affected_ids

        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Error reclassifying transactions: {str(e)}", []


# Convenience functions
def quick_add_entity(name: str, entity_type: str, description: str = None, tenant_id: str = 'delta'):
    """Quick function to add an entity"""
    modifier = DatabaseModifier(tenant_id)
    return modifier.add_business_entity(name, entity_type, description)


def quick_add_pattern(pattern_type: str, description_pattern: str, accounting_category: str, tenant_id: str = 'delta'):
    """Quick function to add a classification pattern"""
    modifier = DatabaseModifier(tenant_id)
    return modifier.add_classification_pattern(pattern_type, description_pattern, accounting_category)


if __name__ == '__main__':
    # Test the modifier
    modifier = DatabaseModifier('delta', 'test_user')

    # Test adding an entity
    success, msg, entity_id = modifier.add_business_entity(
        "Test Company LLC",
        "vendor",
        "A test vendor for development"
    )
    print(f"Add entity: {success} - {msg} (ID: {entity_id})")
