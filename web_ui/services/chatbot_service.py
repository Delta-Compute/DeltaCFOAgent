"""
Chatbot Service for AI-powered CFO Assistant
Integrates Claude AI with database operations and business context
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db_manager
from services.context_manager import ContextManager
from services.db_modifier import DatabaseModifier

# Import Anthropic
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: anthropic package not available")


class ChatbotService:
    """Main chatbot service integrating Claude AI with database operations"""

    def __init__(self, tenant_id: str = 'delta', user_id: str = 'user'):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.context_manager = ContextManager(tenant_id)
        self.db_modifier = DatabaseModifier(tenant_id, user_id)

        # Initialize Claude client
        self.claude_client = None
        if ANTHROPIC_AVAILABLE:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if not api_key and os.path.exists('.anthropic_api_key'):
                with open('.anthropic_api_key', 'r') as f:
                    api_key = f.read().strip()

            if api_key:
                self.claude_client = Anthropic(api_key=api_key)

    # ========================================
    # SESSION MANAGEMENT
    # ========================================

    def create_session(self, user_agent: str = None, ip_address: str = None) -> str:
        """Create a new chat session"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO user_sessions (tenant_id, user_id, user_agent, ip_address)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (self.tenant_id, self.user_id, user_agent, ip_address))

            session_id = str(cursor.fetchone()[0])
            conn.commit()
            conn.close()

            return session_id

        except Exception as e:
            conn.rollback()
            conn.close()
            raise Exception(f"Error creating session: {str(e)}")

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session information"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, user_id, started_at, last_activity, context_data
                FROM user_sessions
                WHERE id = %s AND tenant_id = %s
            """, (session_id, self.tenant_id))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return {
                'session_id': str(row[0]),
                'user_id': row[1],
                'started_at': str(row[2]),
                'last_activity': str(row[3]),
                'context_data': row[4]
            }

        except Exception as e:
            conn.close()
            return None

    def update_session_activity(self, session_id: str):
        """Update last activity timestamp for session"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE user_sessions
                SET last_activity = CURRENT_TIMESTAMP
                WHERE id = %s AND tenant_id = %s
            """, (session_id, self.tenant_id))

            conn.commit()
            conn.close()

        except Exception as e:
            conn.rollback()
            conn.close()

    def end_session(self, session_id: str):
        """End a chat session"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE user_sessions
                SET ended_at = CURRENT_TIMESTAMP
                WHERE id = %s AND tenant_id = %s
            """, (session_id, self.tenant_id))

            conn.commit()
            conn.close()

        except Exception as e:
            conn.rollback()
            conn.close()

    def set_session_context(self, session_id: str, context_key: str, context_value: str):
        """Set a context value for the session"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO chatbot_context (session_id, context_key, context_value)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_id, context_key)
                DO UPDATE SET context_value = EXCLUDED.context_value,
                             updated_at = CURRENT_TIMESTAMP
            """, (session_id, context_key, context_value))

            conn.commit()
            conn.close()

        except Exception as e:
            conn.rollback()
            conn.close()
            raise Exception(f"Error setting context: {str(e)}")

    def get_session_context(self, session_id: str) -> Dict[str, str]:
        """Get all context for a session"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT context_key, context_value
                FROM chatbot_context
                WHERE session_id = %s
            """, (session_id,))

            context = {}
            for row in cursor.fetchall():
                context[row[0]] = row[1]

            conn.close()
            return context

        except Exception as e:
            conn.close()
            return {}

    # ========================================
    # CONVERSATION HISTORY
    # ========================================

    def save_interaction(self, session_id: str, user_message: str, chatbot_response: str,
                        intent: str = None, entities_mentioned: Dict = None,
                        confidence_score: float = None) -> str:
        """Save a chatbot interaction"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO chatbot_interactions
                (tenant_id, session_id, user_id, user_message, chatbot_response,
                 intent, entities_mentioned, confidence_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (self.tenant_id, session_id, self.user_id, user_message, chatbot_response,
                  intent, json.dumps(entities_mentioned) if entities_mentioned else None,
                  confidence_score))

            interaction_id = str(cursor.fetchone()[0])
            conn.commit()
            conn.close()

            return interaction_id

        except Exception as e:
            conn.rollback()
            conn.close()
            raise Exception(f"Error saving interaction: {str(e)}")

    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history for a session"""
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT user_message, chatbot_response, intent, timestamp
                FROM chatbot_interactions
                WHERE session_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (session_id, limit))

            history = []
            for row in cursor.fetchall():
                history.append({
                    'user_message': row[0],
                    'chatbot_response': row[1],
                    'intent': row[2],
                    'timestamp': str(row[3])
                })

            conn.close()
            # Reverse to get chronological order
            return list(reversed(history))

        except Exception as e:
            conn.close()
            return []

    # ========================================
    # CLAUDE AI INTEGRATION
    # ========================================

    def _get_system_prompt(self) -> str:
        """Build system prompt with business context"""
        business_context = self.context_manager.format_for_claude_prompt()

        system_prompt = f"""You are Delta CFO Agent, an AI-powered financial assistant for Delta's business operations.

You help users manage their financial data, classify transactions, track business relationships, and provide insights.

CURRENT BUSINESS CONTEXT:
{business_context}

YOUR CAPABILITIES:
1. Transaction Analysis & Classification
   - Help classify transactions by analyzing descriptions and amounts
   - Suggest appropriate accounting categories and business entities
   - Explain classification decisions

2. Business Entity Management
   - Add new business entities (subsidiaries, vendors, customers)
   - Update entity information
   - View entity details and relationships

3. Investor & Vendor Tracking
   - Add and track investors (VC, angel, institutional, individual)
   - Record investments and funding sources
   - Add and manage vendor relationships
   - Track vendor performance

4. Business Rules & Patterns
   - Create categorization rules for automatic transaction classification
   - Define patterns based on transaction descriptions
   - Apply rules retroactively to existing transactions

5. Financial Insights
   - Answer questions about business performance
   - Provide transaction summaries and statistics
   - Identify trends and patterns

INTERACTION GUIDELINES:
- Be helpful, precise, and professional
- Always confirm before making bulk changes to transactions
- Provide clear explanations for your suggestions
- Ask for clarification when needed
- Use the available functions to perform database operations
- For retroactive changes, show preview before applying

When users ask you to perform database operations (add entities, create rules, modify transactions), use the available functions to execute these operations safely.
"""
        return system_prompt

    def _get_function_definitions(self) -> List[Dict]:
        """Define available functions for Claude to call"""
        return [
            {
                "name": "add_business_entity",
                "description": "Add a new business entity (subsidiary, vendor, customer, or internal account)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the entity (e.g., 'Acme Corp', 'Delta Mining LLC')"
                        },
                        "entity_type": {
                            "type": "string",
                            "enum": ["subsidiary", "vendor", "customer", "internal"],
                            "description": "Type of entity"
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional description of the entity and its purpose"
                        }
                    },
                    "required": ["name", "entity_type"]
                }
            },
            {
                "name": "add_classification_pattern",
                "description": "Add a new classification pattern for automatic transaction categorization",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern_type": {
                            "type": "string",
                            "enum": ["revenue", "expense", "crypto", "transfer"],
                            "description": "Type of pattern"
                        },
                        "description_pattern": {
                            "type": "string",
                            "description": "Text pattern to match in transaction descriptions (e.g., 'AWS', 'Stripe')"
                        },
                        "accounting_category": {
                            "type": "string",
                            "description": "Accounting category to assign (e.g., 'Technology Expenses', 'Revenue - Trading')"
                        },
                        "entity": {
                            "type": "string",
                            "description": "Optional: Specific entity to assign to matching transactions"
                        },
                        "confidence_score": {
                            "type": "number",
                            "description": "Confidence score between 0 and 1 (default 0.75)"
                        }
                    },
                    "required": ["pattern_type", "description_pattern", "accounting_category"]
                }
            },
            {
                "name": "create_business_rule",
                "description": "Create a comprehensive business rule with multiple conditions and actions",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "rule_name": {
                            "type": "string",
                            "description": "Unique name for the rule"
                        },
                        "rule_type": {
                            "type": "string",
                            "enum": ["classification", "alert", "validation"],
                            "description": "Type of rule"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of what the rule does"
                        },
                        "conditions": {
                            "type": "array",
                            "description": "Array of conditions that must be met",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "field": {"type": "string"},
                                    "operator": {"type": "string", "enum": ["contains", "equals", "greater_than", "less_than", "regex_match"]},
                                    "value": {"type": "string"}
                                }
                            }
                        },
                        "actions": {
                            "type": "array",
                            "description": "Array of actions to execute when conditions are met",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "action_type": {"type": "string"},
                                    "target_category": {"type": "string"},
                                    "target_entity": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["rule_name", "rule_type", "description", "conditions", "actions"]
                }
            },
            {
                "name": "add_investor",
                "description": "Add a new investor to track funding sources",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "investor_name": {"type": "string"},
                        "investor_type": {
                            "type": "string",
                            "enum": ["VC", "angel", "institutional", "individual"]
                        },
                        "contact_email": {"type": "string"},
                        "country": {"type": "string"},
                        "investment_focus": {"type": "string", "description": "Areas of investment interest"}
                    },
                    "required": ["investor_name", "investor_type"]
                }
            },
            {
                "name": "add_vendor",
                "description": "Add a new vendor for expense tracking",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "vendor_name": {"type": "string"},
                        "vendor_type": {
                            "type": "string",
                            "enum": ["service_provider", "supplier", "contractor"]
                        },
                        "contact_email": {"type": "string"},
                        "payment_terms": {"type": "string", "description": "e.g., 'net30', 'net60'"},
                        "is_preferred": {"type": "boolean", "description": "Mark as preferred vendor"}
                    },
                    "required": ["vendor_name", "vendor_type"]
                }
            },
            {
                "name": "reclassify_transactions_preview",
                "description": "Preview which transactions would be affected by reclassification (doesn't make changes)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filters": {
                            "type": "object",
                            "description": "Filters to match transactions",
                            "properties": {
                                "description_contains": {"type": "string"},
                                "entity": {"type": "string"},
                                "category": {"type": "string"},
                                "date_from": {"type": "string"},
                                "date_to": {"type": "string"}
                            }
                        },
                        "new_classification": {
                            "type": "object",
                            "description": "New classification to apply",
                            "properties": {
                                "category": {"type": "string"},
                                "entity": {"type": "string"},
                                "confidence_score": {"type": "number"}
                            }
                        }
                    },
                    "required": ["filters", "new_classification"]
                }
            },
            {
                "name": "reclassify_transactions_apply",
                "description": "Apply reclassification to matching transactions (makes actual changes)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filters": {
                            "type": "object",
                            "description": "Filters to match transactions"
                        },
                        "new_classification": {
                            "type": "object",
                            "description": "New classification to apply"
                        }
                    },
                    "required": ["filters", "new_classification"]
                }
            },
            {
                "name": "get_business_overview",
                "description": "Get comprehensive overview of business entities, investors, vendors, and rules",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def _execute_function(self, function_name: str, arguments: Dict) -> Dict[str, Any]:
        """Execute a function call from Claude"""
        try:
            if function_name == "add_business_entity":
                success, message, entity_id = self.db_modifier.add_business_entity(
                    arguments['name'],
                    arguments['entity_type'],
                    arguments.get('description')
                )
                return {
                    "success": success,
                    "message": message,
                    "entity_id": entity_id
                }

            elif function_name == "add_classification_pattern":
                success, message, pattern_id = self.db_modifier.add_classification_pattern(
                    arguments['pattern_type'],
                    arguments['description_pattern'],
                    arguments['accounting_category'],
                    arguments.get('entity'),
                    arguments.get('confidence_score', 0.75)
                )
                return {
                    "success": success,
                    "message": message,
                    "pattern_id": pattern_id
                }

            elif function_name == "create_business_rule":
                success, message, rule_id = self.db_modifier.create_business_rule(
                    arguments['rule_name'],
                    arguments['rule_type'],
                    arguments['description'],
                    arguments['conditions'],
                    arguments['actions'],
                    arguments.get('priority', 100)
                )
                return {
                    "success": success,
                    "message": message,
                    "rule_id": rule_id
                }

            elif function_name == "add_investor":
                success, message, investor_id = self.db_modifier.add_investor(
                    arguments['investor_name'],
                    arguments['investor_type'],
                    arguments.get('contact_email'),
                    arguments.get('country'),
                    arguments.get('investment_focus')
                )
                return {
                    "success": success,
                    "message": message,
                    "investor_id": investor_id
                }

            elif function_name == "add_vendor":
                success, message, vendor_id = self.db_modifier.add_vendor(
                    arguments['vendor_name'],
                    arguments['vendor_type'],
                    arguments.get('contact_email'),
                    arguments.get('payment_terms'),
                    arguments.get('is_preferred', False)
                )
                return {
                    "success": success,
                    "message": message,
                    "vendor_id": vendor_id
                }

            elif function_name == "reclassify_transactions_preview":
                success, message, affected_ids = self.db_modifier.reclassify_transactions(
                    arguments['filters'],
                    arguments['new_classification'],
                    preview=True
                )
                return {
                    "success": success,
                    "message": message,
                    "affected_count": len(affected_ids),
                    "affected_ids": affected_ids[:10]  # Return first 10 IDs
                }

            elif function_name == "reclassify_transactions_apply":
                success, message, affected_ids = self.db_modifier.reclassify_transactions(
                    arguments['filters'],
                    arguments['new_classification'],
                    preview=False
                )
                return {
                    "success": success,
                    "message": message,
                    "affected_count": len(affected_ids)
                }

            elif function_name == "get_business_overview":
                overview = self.context_manager.get_business_overview()
                return {
                    "success": True,
                    "overview": overview
                }

            else:
                return {
                    "success": False,
                    "message": f"Unknown function: {function_name}"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error executing {function_name}: {str(e)}"
            }

    def chat(self, session_id: str, user_message: str, use_sonnet: bool = True) -> Dict[str, Any]:
        """
        Send a message to the chatbot and get a response

        Args:
            session_id: UUID of the chat session
            user_message: User's message
            use_sonnet: If True, use Claude 3.5 Sonnet; if False, use Claude 3 Haiku

        Returns:
            Dict with response, intent, entities, etc.
        """
        if not self.claude_client:
            return {
                "success": False,
                "response": "Claude AI is not available. Please configure ANTHROPIC_API_KEY.",
                "intent": None
            }

        try:
            # Update session activity
            self.update_session_activity(session_id)

            # Get conversation history
            history = self.get_conversation_history(session_id, limit=5)

            # Build messages array for Claude
            messages = []

            # Add conversation history
            for entry in history:
                messages.append({
                    "role": "user",
                    "content": entry['user_message']
                })
                messages.append({
                    "role": "assistant",
                    "content": entry['chatbot_response']
                })

            # Add current message
            messages.append({
                "role": "user",
                "content": user_message
            })

            # Choose model
            model = "claude-3-5-sonnet-20241022" if use_sonnet else "claude-3-haiku-20240307"

            # Call Claude API with function calling
            response = self.claude_client.messages.create(
                model=model,
                max_tokens=2000,
                temperature=0.3,
                system=self._get_system_prompt(),
                tools=self._get_function_definitions(),
                messages=messages
            )

            # Process response
            assistant_message = ""
            function_results = []

            for block in response.content:
                if block.type == "text":
                    assistant_message += block.text
                elif block.type == "tool_use":
                    # Execute the function
                    function_name = block.name
                    function_args = block.input

                    result = self._execute_function(function_name, function_args)
                    function_results.append({
                        "function": function_name,
                        "arguments": function_args,
                        "result": result
                    })

                    # If there were function calls, continue the conversation
                    if function_results:
                        messages.append({
                            "role": "assistant",
                            "content": response.content
                        })

                        # Add function results
                        tool_results = []
                        for func_result in function_results:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(func_result['result'])
                            })

                        messages.append({
                            "role": "user",
                            "content": tool_results
                        })

                        # Get Claude's final response
                        final_response = self.claude_client.messages.create(
                            model=model,
                            max_tokens=1000,
                            temperature=0.3,
                            system=self._get_system_prompt(),
                            messages=messages
                        )

                        for final_block in final_response.content:
                            if final_block.type == "text":
                                assistant_message += "\n\n" + final_block.text

            # Save interaction
            self.save_interaction(
                session_id,
                user_message,
                assistant_message,
                intent=None,
                entities_mentioned={"functions_called": [f['function'] for f in function_results]} if function_results else None
            )

            return {
                "success": True,
                "response": assistant_message,
                "function_calls": function_results,
                "model": model
            }

        except Exception as e:
            return {
                "success": False,
                "response": f"Error processing message: {str(e)}",
                "error": str(e)
            }


# Convenience function
def quick_chat(message: str, tenant_id: str = 'delta', user_id: str = 'user') -> str:
    """Quick chat without session management"""
    service = ChatbotService(tenant_id, user_id)
    session_id = service.create_session()
    result = service.chat(session_id, message)
    return result.get('response', 'Error')


if __name__ == '__main__':
    # Test the chatbot
    service = ChatbotService('delta', 'test_user')
    session_id = service.create_session()

    # Test message
    result = service.chat(session_id, "What business entities do we have?")
    print(f"Response: {result.get('response')}")

    if result.get('function_calls'):
        print(f"\nFunction calls: {json.dumps(result['function_calls'], indent=2)}")
