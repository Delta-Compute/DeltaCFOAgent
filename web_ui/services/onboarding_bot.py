#!/usr/bin/env python3
"""
AI Onboarding Bot Service
==========================
Conversational AI bot that gathers business context from users and updates
the tenant configuration database. Fully SaaS-ready, no hardcoding.

The bot:
- Asks natural questions about the business
- Extracts structured data from conversation
- Updates tenant_configuration table progressively
- Provides context for homepage AI generation
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import anthropic

logger = logging.getLogger(__name__)


class OnboardingBot:
    """Conversational AI bot for gathering business context"""

    def __init__(self, db_manager, tenant_id: str):
        """
        Initialize the onboarding bot

        Args:
            db_manager: DatabaseManager instance
            tenant_id: Tenant identifier
        """
        self.db_manager = db_manager
        self.tenant_id = tenant_id

        # Initialize Claude API - check environment variable and fallback to file
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            # Check for API key file (same as main app)
            key_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.anthropic_api_key')
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    api_key = f.read().strip()
                logger.info(f"Loaded API key from file: {key_file}")

        if api_key:
            api_key = api_key.strip()
            self.claude_client = anthropic.Anthropic(api_key=api_key)
            logger.info("OnboardingBot: Claude API client initialized successfully")
        else:
            self.claude_client = None
            logger.warning("ANTHROPIC_API_KEY not set - bot will be disabled")

    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a session

        Args:
            session_id: Unique session identifier

        Returns:
            List of messages with role and content
        """
        query = """
            SELECT role, content, created_at
            FROM bot_conversations
            WHERE tenant_id = %s AND session_id = %s
            ORDER BY created_at ASC
        """

        results = self.db_manager.execute_query(query, (self.tenant_id, session_id), fetch_all=True)

        if results:
            return [
                {
                    'role': row['role'],
                    'content': row['content'],
                    'timestamp': row['created_at'].isoformat() if row['created_at'] else None
                }
                for row in results
            ]
        return []

    def save_message(self, session_id: str, role: str, content: str, extracted_data: Optional[Dict] = None):
        """
        Save a message to conversation history

        Args:
            session_id: Unique session identifier
            role: 'user' or 'assistant'
            content: Message content
            extracted_data: Any structured data extracted from this message
        """
        query = """
            INSERT INTO bot_conversations (
                tenant_id, session_id, role, content, extracted_data, created_at
            ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """

        self.db_manager.execute_query(
            query,
            (self.tenant_id, session_id, role, content, json.dumps(extracted_data) if extracted_data else None)
        )

    def get_current_tenant_data(self) -> Dict[str, Any]:
        """
        Get current tenant configuration data

        Returns:
            Dictionary with current tenant data
        """
        query = """
            SELECT
                company_name, company_tagline, company_description,
                industry, founded_date, headquarters_location,
                website_url, contact_email, default_currency,
                settings
            FROM tenant_configuration
            WHERE tenant_id = %s
        """

        result = self.db_manager.execute_query(query, (self.tenant_id,), fetch_one=True)

        if result:
            data = dict(result)
            # Convert date to string if present
            if data.get('founded_date'):
                data['founded_date'] = data['founded_date'].isoformat()
            return data

        return {}

    def update_tenant_data(self, updates: Dict[str, Any]):
        """
        Update tenant configuration with extracted data

        Args:
            updates: Dictionary of fields to update
        """
        # Build dynamic UPDATE query
        set_clauses = []
        params = []

        # Define allowed fields
        allowed_fields = {
            'company_name', 'company_tagline', 'company_description',
            'industry', 'founded_date', 'headquarters_location',
            'website_url', 'contact_email', 'contact_phone',
            'default_currency', 'timezone'
        }

        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                set_clauses.append(f"{field} = %s")
                params.append(value)

        if not set_clauses:
            return  # Nothing to update

        # Add updated_at
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")

        # Add tenant_id for WHERE clause
        params.append(self.tenant_id)

        query = f"""
            UPDATE tenant_configuration
            SET {', '.join(set_clauses)}
            WHERE tenant_id = %s
        """

        self.db_manager.execute_query(query, tuple(params))
        logger.info(f"Updated tenant {self.tenant_id} with fields: {list(updates.keys())}")

    def get_business_entities(self) -> List[Dict[str, Any]]:
        """
        Get all business entities for the current tenant

        Returns:
            List of business entities
        """
        query = """
            SELECT
                id, name, description, entity_type,
                annual_revenue, transaction_volume,
                active, created_at, updated_at
            FROM business_entities
            WHERE tenant_id = %s AND active = TRUE
            ORDER BY name
        """

        results = self.db_manager.execute_query(query, (self.tenant_id,), fetch_all=True)

        if results:
            entities = []
            for row in results:
                entity = dict(row)
                if entity.get('created_at'):
                    entity['created_at'] = entity['created_at'].isoformat()
                if entity.get('updated_at'):
                    entity['updated_at'] = entity['updated_at'].isoformat()
                if entity.get('annual_revenue'):
                    entity['annual_revenue'] = float(entity['annual_revenue'])
                entities.append(entity)
            return entities
        return []

    def create_or_update_business_entity(self, entity_data: Dict[str, Any]) -> bool:
        """
        Create or update a business entity for the tenant

        Args:
            entity_data: Dictionary with entity fields (name, description, entity_type, etc.)

        Returns:
            True if successful
        """
        name = entity_data.get('name')
        if not name:
            logger.error("Entity name is required")
            return False

        try:
            # Check if entity exists
            existing = self.db_manager.execute_query("""
                SELECT id FROM business_entities
                WHERE tenant_id = %s AND name = %s
            """, (self.tenant_id, name), fetch_one=True)

            if existing:
                # Update existing entity
                set_clauses = []
                params = []

                allowed_fields = {
                    'description', 'entity_type', 'annual_revenue', 'transaction_volume'
                }

                for field, value in entity_data.items():
                    if field in allowed_fields and value is not None:
                        set_clauses.append(f"{field} = %s")
                        params.append(value)

                if set_clauses:
                    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                    params.extend([self.tenant_id, name])

                    query = f"""
                        UPDATE business_entities
                        SET {', '.join(set_clauses)}
                        WHERE tenant_id = %s AND name = %s
                    """
                    self.db_manager.execute_query(query, tuple(params))
                    logger.info(f"Updated entity: {name}")
            else:
                # Create new entity
                query = """
                    INSERT INTO business_entities (
                        tenant_id, name, description, entity_type,
                        annual_revenue, transaction_volume, active
                    ) VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                """
                self.db_manager.execute_query(query, (
                    self.tenant_id,
                    name,
                    entity_data.get('description'),
                    entity_data.get('entity_type', 'business_unit'),
                    entity_data.get('annual_revenue'),
                    entity_data.get('transaction_volume')
                ))
                logger.info(f"Created entity: {name}")

            return True

        except Exception as e:
            logger.error(f"Error creating/updating entity: {e}")
            return False

    def _build_conversation_prompt(self, user_message: str, conversation_history: List[Dict], current_data: Dict) -> str:
        """
        Build prompt for Claude including conversation context AND entity collection

        Enhanced version that adds business entity questions after basic company info is collected
        """
        # Format conversation history
        history_text = ""
        for msg in conversation_history[-10:]:
            role_label = "User" if msg['role'] == 'user' else "Assistant"
            history_text += f"{role_label}: {msg['content']}\n"

        # Get current entities
        entities = self.get_business_entities()
        entities_text = ""
        if entities:
            entities_text = "\n**Current Business Entities:**\n"
            for entity in entities:
                rev_text = f" (${entity.get('annual_revenue', 0):,.0f}/year)" if entity.get('annual_revenue') else ""
                entities_text += f"- {entity['name']}: {entity.get('description', 'N/A')}{rev_text}\n"

        # Format current data status
        data_status = []
        fields_needed = []

        # Core fields
        field_descriptions = {
            'company_name': 'Company name',
            'company_tagline': 'Company tagline',
            'company_description': 'Company description',
            'industry': 'Industry',
            'founded_date': 'Founded date',
            'headquarters_location': 'Headquarters location',
            'website_url': 'Website URL',
            'contact_email': 'Contact email',
            'contact_phone': 'Contact phone (optional)',
            'default_currency': 'Default currency',
            'fiscal_year_end': 'Fiscal year end (optional)',
            'timezone': 'Timezone',
            'tax_id': 'Tax ID (optional)',
        }

        for field, description in field_descriptions.items():
            value = current_data.get(field)
            if value and str(value).strip():
                data_status.append(f"✓ {description}: {value}")
            elif '(optional)' not in description:
                fields_needed.append(description)

        # Determine conversation phase
        core_complete = all(current_data.get(f) for f in ['company_name', 'company_description', 'industry', 'default_currency'])
        entities_asked = len(entities) > 0 or any('entit' in msg.get('content', '').lower() or 'subsidiar' in msg.get('content', '').lower() for msg in conversation_history[-5:])

        # Check if this is a fully configured tenant (has entities and core data)
        is_fully_configured = core_complete and len(entities) > 0

        # Different prompts for configured vs onboarding tenants
        if is_fully_configured:
            prompt = f"""You are a helpful AI assistant for an established business using a financial management platform. The business is already set up and you're here to help with updates, learning, and assistance.

**Current Business Profile:**
{chr(10).join(data_status) if data_status else 'No data collected yet'}
{entities_text if entities else ''}

**Conversation History:**
{history_text if history_text else 'This is the start of the conversation'}

**Latest User Message:**
{user_message}

**Your Role:**
1. **Helpful Assistant**: You're not onboarding - you're assisting an existing business
2. **Update Detector**: If they mention changes (new products, locations, revenue changes, etc.), extract and save them
3. **Knowledge Gatherer**: Learn about their business to improve transaction classification
4. **DO NOT**: Ask basic onboarding questions like "what's your company name" unless they want to change it
5. **DO**: Help with specific tasks like adding entities, updating info, or learning about business patterns

**What You Can Help With:**
- Adding new business entities, subsidiaries, or divisions
- Updating company information (location, industry, revenue)
- Learning about business patterns (vendors, expense categories, revenue sources)
- Analyzing documents they upload
- Answering questions about their data

**Response Format** (JSON):
{{
  "response": "Your natural, helpful response (under 100 words)",
  "extracted_data": {{
    "company_description": "value or null (only if they mention changes)",
    "industry": "value or null (only if they mention changes)",
    "headquarters_location": "value or null (only if they mention changes)"
  }},
  "entities": [
    {{
      "name": "Entity Name (if they mention a new entity/subsidiary/division)",
      "description": "what this entity does",
      "entity_type": "subsidiary/division/business_unit",
      "annual_revenue": 1500000.00
    }}
  ],
  "next_question": "follow-up question or null",
  "completion_percentage": {100 if is_fully_configured else 75}
}}

**Guidelines:**
- Be conversational and helpful, not rigid or scripted
- Focus on what they're asking for
- Extract information naturally mentioned
- Don't interrogate - they're already set up!
"""
        else:
            prompt = f"""You are an inquisitive onboarding assistant for a financial management platform. Your goal is to naturally gather business context through conversation.

**Current Data Status:**
{chr(10).join(data_status) if data_status else 'No data collected yet'}
{entities_text if entities else ''}

**Still Needed:**
{chr(10).join(f'- {field}' for field in fields_needed) if fields_needed else 'Basic info complete!'}

**Conversation History:**
{history_text if history_text else 'This is the start of the conversation'}

**Latest User Message:**
{user_message}

**Your Conversation Strategy:**

1. **Be Naturally Curious**: Ask follow-up questions based on what the user tells you
2. **Extract Intelligently**: If user mentions something (e.g., "we're a fintech startup in NYC"), extract ALL relevant data
3. **Progress Logically**:
   - Start: Company name, what they do, industry
   - Then: Location, contact info, basic details
   - After basics: "Do you operate as a single company or have subsidiaries/divisions/business units?"
   - For each entity: Get name, description, and optionally revenue

4. **Current Phase**:
   - Core complete: {"YES" if core_complete else "NO"}
   - Entities asked: {"YES" if entities_asked else "NO"}

**CRITICAL EXTRACTION RULES:**
- **Always extract ALL mentioned info**, even if not directly asked
- **Business entities**: When user mentions divisions, subsidiaries, business units - extract them!
- **Don't repeat questions**: Check current data first
- **Smart Industry Inference**: AUTOMATICALLY infer industry from business description. Examples:
  * "sell hair extensions", "megahair", "beauty products" → "Retail - Beauty & Personal Care"
  * "fintech", "payment processing", "banking app" → "Technology - Financial Services"
  * "restaurant", "food delivery", "catering" → "Food & Beverage"
  * "consulting", "advisory services" → "Professional Services - Consulting"
  * "real estate", "property management" → "Real Estate"
  * "software", "SaaS", "app development" → "Technology - Software"
  * "manufacturing", "production", "factory" → "Manufacturing"
  * NEVER ask "What industry are you in?" if you can infer it from context!

**Response Format** (JSON):
{{
  "response": "Your natural, conversational response (under 100 words)",
  "extracted_data": {{
    "company_name": "value or null",
    "company_tagline": "value or null",
    "company_description": "value or null",
    "industry": "value or null",
    "founded_date": "YYYY-MM-DD or null",
    "headquarters_location": "value or null",
    "website_url": "value or null",
    "contact_email": "value or null",
    "contact_phone": "value or null",
    "default_currency": "USD/EUR/GBP/etc or null",
    "fiscal_year_end": "MM-DD or null",
    "timezone": "America/New_York or null",
    "tax_id": "value or null"
  }},
  "entities": [
    {{
      "name": "Entity Name",
      "description": "what this entity does",
      "entity_type": "subsidiary/division/business_unit",
      "annual_revenue": 1500000.00
    }}
  ],
  "next_question": "what to ask next or null",
  "completion_percentage": 75
}}

**Guidelines:**
- Keep responses friendly, under 100 words
- ONE question at a time
- **CRITICAL**: After timezone is collected, you MUST ask: "Do you operate as a single company or do you have any subsidiaries, divisions, or business units?"
- DO NOT congratulate or say "we're done" until AFTER asking about entities
- Revenue questions for entities are OPTIONAL
- Only when basics AND entities question has been asked, then congratulate and explain they can update anytime
"""

        return prompt

    def chat(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and generate response

        Args:
            session_id: Unique session identifier
            user_message: User's message

        Returns:
            Dictionary with response, extracted_data, and completion status
        """
        if not self.claude_client:
            return {
                'response': "Sorry, the AI assistant is not configured. Please set ANTHROPIC_API_KEY.",
                'error': 'API key not configured'
            }

        try:
            # Get conversation history
            history = self.get_conversation_history(session_id)

            # Get current tenant data
            current_data = self.get_current_tenant_data()

            # Save user message
            self.save_message(session_id, 'user', user_message)

            # Build prompt
            prompt = self._build_conversation_prompt(user_message, history, current_data)

            # Call Claude - using Haiku for compatibility with all API keys
            response = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,  # Increased for entity arrays
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response
            response_text = response.content[0].text
            logger.debug(f"Claude response: {response_text}")

            # Extract JSON - handle both pure JSON and markdown-wrapped JSON
            json_text = response_text.strip()

            # Try to find JSON within the response (Claude sometimes adds text before/after JSON)
            # Look for the first '{' and last '}' to extract just the JSON portion
            first_brace = json_text.find('{')
            last_brace = json_text.rfind('}')

            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                json_text = json_text[first_brace:last_brace+1]

            # Remove markdown code blocks if present
            if json_text.startswith('```'):
                # Find the actual JSON content between code blocks
                lines = json_text.split('\n')
                json_lines = []
                in_code_block = False
                for line in lines:
                    if line.strip().startswith('```'):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block or (line.strip().startswith('{') or json_lines):
                        json_lines.append(line)
                        if line.strip().endswith('}') and line.strip().count('{') <= line.strip().count('}'):
                            break
                json_text = '\n'.join(json_lines).strip()

            # Try to parse JSON
            try:
                result = json.loads(json_text)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try one more time to extract just the response text before JSON
                logger.warning(f"Claude returned non-JSON or mixed response: {e}")

                # Extract any text BEFORE the JSON as the response
                first_brace = response_text.find('{')
                if first_brace > 0:
                    # There's text before the JSON - use it as the response
                    plain_response = response_text[:first_brace].strip()
                else:
                    # No JSON found - use entire response as plain text
                    plain_response = response_text.strip()

                result = {
                    'response': plain_response if plain_response else "I'm here to help! What would you like to know?",
                    'extracted_data': {},
                    'entities': [],
                    'next_question': None,
                    'completion_percentage': 0
                }

            # Extract and update data
            extracted = result.get('extracted_data', {})
            updates = {}
            if extracted and any(v for v in extracted.values() if v):
                updates = {k: v for k, v in extracted.items() if v is not None}
                if updates:
                    self.update_tenant_data(updates)
                    logger.info(f"Extracted and saved: {list(updates.keys())}")

            # Extract and save business entities
            entities = result.get('entities', [])
            entities_saved = []
            if entities:
                for entity_data in entities:
                    if entity_data.get('name'):
                        success = self.create_or_update_business_entity(entity_data)
                        if success:
                            entities_saved.append(entity_data['name'])
                            logger.info(f"Saved entity: {entity_data['name']}")

            # Build extracted summary
            extracted_summary = {}
            if updates:
                extracted_summary.update(updates)
            if entities_saved:
                extracted_summary['entities_saved'] = entities_saved


            # Save assistant response
            self.save_message(session_id, 'assistant', result['response'], extracted_summary)

            return {
                'response': result['response'],
                'extracted_data': extracted,
                'entities_saved': entities_saved,
                'next_question': result.get('next_question'),
                'completion_percentage': result.get('completion_percentage', 0),
                'success': True
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return {
                'response': "I'm having trouble processing that. Could you rephrase?",
                'error': 'Parse error'
            }
        except Exception as e:
            logger.error(f"Bot error: {e}")
            return {
                'response': "Sorry, I encountered an error. Please try again.",
                'error': str(e)
            }

    def get_onboarding_status(self) -> Dict[str, Any]:
        """
        Get current onboarding completion status

        Returns:
            Dictionary with completion percentage and missing fields
        """
        current_data = self.get_current_tenant_data()

        required_fields = [
            'company_name', 'company_tagline', 'company_description', 'industry'
        ]

        optional_fields = [
            'founded_date', 'headquarters_location', 'website_url', 'contact_email'
        ]

        filled_required = sum(1 for field in required_fields if current_data.get(field))
        filled_optional = sum(1 for field in optional_fields if current_data.get(field))

        total_fields = len(required_fields) + len(optional_fields)
        filled_fields = filled_required + filled_optional

        completion = int((filled_fields / total_fields) * 100)

        missing_required = [field for field in required_fields if not current_data.get(field)]
        missing_optional = [field for field in optional_fields if not current_data.get(field)]

        return {
            'completion_percentage': completion,
            'required_complete': filled_required == len(required_fields),
            'filled_fields': filled_fields,
            'total_fields': total_fields,
            'missing_required': missing_required,
            'missing_optional': missing_optional,
            'current_data': current_data
        }

    def start_new_session(self) -> str:
        """
        Start a new onboarding session

        Returns:
            Session ID
        """
        import uuid
        session_id = str(uuid.uuid4())

        # Get current status to create contextual greeting
        status = self.get_onboarding_status()
        current_data = status.get('current_data', {})

        # Check if tenant has business entities (sign of actual usage)
        entities = self.get_business_entities()
        has_entities = len(entities) > 0

        # Build greeting based on what we already know
        if status['completion_percentage'] == 0:
            greeting = "Hi! I'm here to help set up your financial dashboard. I'll ask you a few questions about your business to personalize your experience. Let's start with the basics - what's your company name?"
        elif status['completion_percentage'] >= 90 and has_entities:
            # Fully configured tenant - provide helpful assistant greeting
            company_name = current_data.get('company_name', 'your company')
            greeting = f"Welcome back! I'm your AI assistant for {company_name}.\n\n"
            greeting += "Here's what I can help you with:\n"
            greeting += "• Upload and analyze business documents\n"
            greeting += "• Manage business entities and accounts\n"
            greeting += "• Learn about your business to improve transaction classification\n"
            greeting += "• Update company information and settings\n\n"
            greeting += "Has anything material changed in your business that I should know about? Or would you like help with something specific?"
        elif status['completion_percentage'] >= 90:
            # Almost complete - acknowledge what we have and ask about missing pieces
            company_name = current_data.get('company_name', 'your company')
            greeting = f"Great to see you again! I see {company_name} is almost fully set up ({status['completion_percentage']}% complete). "

            if status['missing_required']:
                missing = ', '.join([f.replace('_', ' ').title() for f in status['missing_required']])
                greeting += f"We're just missing a few details: {missing}. Would you like to fill those in, or is there anything else you'd like to update?"
            else:
                greeting += "Is there anything you'd like to add or update about your business?"
        elif status['completion_percentage'] < 100:
            company_name = current_data.get('company_name', 'your company')
            greeting = f"Welcome back! I see {company_name} is {status['completion_percentage']}% set up. Would you like to continue filling in the missing details, or update any existing information?"
        else:
            greeting = "Your profile is complete! Would you like to update any information or add more details about your business?"

        # Save initial greeting
        self.save_message(session_id, 'assistant', greeting)

        return session_id
