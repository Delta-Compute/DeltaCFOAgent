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

    def get_entities_with_business_lines(self) -> Dict[str, Any]:
        """
        Get all entities and their business lines for the current tenant

        Returns:
            Dictionary with entities, business_lines, and counts
        """
        # Query entities table
        entities_query = """
            SELECT
                id, tenant_id, code, name, legal_name, tax_id,
                tax_jurisdiction, entity_type, base_currency,
                fiscal_year_end, is_active, created_at, updated_at
            FROM entities
            WHERE tenant_id = %s AND is_active = TRUE
            ORDER BY name
        """

        # Query business_lines table
        business_lines_query = """
            SELECT
                bl.id, bl.entity_id, bl.code, bl.name, bl.description,
                bl.color_hex, bl.is_default, bl.is_active, bl.created_at
            FROM business_lines bl
            JOIN entities e ON bl.entity_id = e.id
            WHERE e.tenant_id = %s AND bl.is_active = TRUE
            ORDER BY e.name, bl.name
        """

        entities_results = self.db_manager.execute_query(
            entities_query, (self.tenant_id,), fetch_all=True
        )

        business_lines_results = self.db_manager.execute_query(
            business_lines_query, (self.tenant_id,), fetch_all=True
        )

        # Convert to dictionaries with proper formatting
        entities = []
        if entities_results:
            for row in entities_results:
                entity = dict(row)
                # Convert UUID to string
                if entity.get('id'):
                    entity['id'] = str(entity['id'])
                # Convert dates to ISO format
                if entity.get('created_at'):
                    entity['created_at'] = entity['created_at'].isoformat()
                if entity.get('updated_at'):
                    entity['updated_at'] = entity['updated_at'].isoformat()
                entities.append(entity)

        business_lines = []
        if business_lines_results:
            for row in business_lines_results:
                bl = dict(row)
                # Convert UUIDs to strings
                if bl.get('id'):
                    bl['id'] = str(bl['id'])
                if bl.get('entity_id'):
                    bl['entity_id'] = str(bl['entity_id'])
                # Convert dates to ISO format
                if bl.get('created_at'):
                    bl['created_at'] = bl['created_at'].isoformat()
                business_lines.append(bl)

        return {
            'entities': entities,
            'business_lines': business_lines,
            'entity_count': len(entities),
            'business_line_count': len(business_lines)
        }

    def create_entity(self, entity_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a legal entity for the tenant

        Args:
            entity_data: {
                'code': 'DLLC',  # Required: Short entity code
                'name': 'Delta Mining LLC',  # Required: Entity name
                'legal_name': 'Delta Mining LLC',  # Optional: Official name
                'tax_id': 'XX-XXXXXXX',  # Optional: Tax ID/EIN
                'tax_jurisdiction': 'US-Delaware',  # Optional
                'entity_type': 'LLC',  # Optional: LLC, S-Corp, etc.
                'base_currency': 'USD',  # Optional: Default USD
                'fiscal_year_end': '12-31'  # Optional: Default 12-31
            }

        Returns:
            entity_id (UUID string) if successful, None otherwise
        """
        code = entity_data.get('code')
        name = entity_data.get('name')

        if not code or not name:
            logger.error("Entity code and name are required")
            return None

        try:
            # Check if entity already exists
            existing = self.db_manager.execute_query("""
                SELECT id FROM entities
                WHERE tenant_id = %s AND (code = %s OR name = %s)
            """, (self.tenant_id, code, name), fetch_one=True)

            if existing:
                logger.warning(f"Entity already exists: {code}")
                return str(existing['id'])

            # Create entity
            query = """
                INSERT INTO entities (
                    tenant_id, code, name, legal_name, tax_id,
                    tax_jurisdiction, entity_type, base_currency,
                    fiscal_year_end, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                RETURNING id
            """

            result = self.db_manager.execute_query(query, (
                self.tenant_id,
                code,
                name,
                entity_data.get('legal_name', name),
                entity_data.get('tax_id'),
                entity_data.get('tax_jurisdiction'),
                entity_data.get('entity_type', 'LLC'),
                entity_data.get('base_currency', 'USD'),
                entity_data.get('fiscal_year_end', '12-31')
            ), fetch_one=True)

            entity_id = str(result['id'])
            logger.info(f"Created entity: {code} ({entity_id})")

            # Auto-create default business line
            self.create_business_line({
                'entity_id': entity_id,
                'code': 'DEFAULT',
                'name': 'General Operations',
                'description': 'Default business line',
                'is_default': True
            })

            return entity_id

        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def create_business_line(self, bl_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a business line under an entity

        Args:
            bl_data: {
                'entity_id': 'uuid-string',  # Required: Parent entity UUID
                'code': 'HOST',  # Required: Short code
                'name': 'Hosting Services',  # Required: Business line name
                'description': 'Web hosting operations',  # Optional
                'color_hex': '#3B82F6',  # Optional: UI color
                'is_default': False  # Optional: Is this the default BL?
            }

        Returns:
            business_line_id (UUID string) if successful, None otherwise
        """
        entity_id = bl_data.get('entity_id')
        code = bl_data.get('code')
        name = bl_data.get('name')

        if not entity_id or not code or not name:
            logger.error("Business line entity_id, code, and name are required")
            return None

        try:
            # Check if business line exists
            existing = self.db_manager.execute_query("""
                SELECT id FROM business_lines
                WHERE entity_id = %s AND (code = %s OR name = %s)
            """, (entity_id, code, name), fetch_one=True)

            if existing:
                logger.warning(f"Business line already exists: {code}")
                return str(existing['id'])

            # Create business line
            query = """
                INSERT INTO business_lines (
                    entity_id, code, name, description,
                    color_hex, is_default, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                RETURNING id
            """

            result = self.db_manager.execute_query(query, (
                entity_id,
                code,
                name,
                bl_data.get('description', ''),
                bl_data.get('color_hex', '#3B82F6'),
                bl_data.get('is_default', False)
            ), fetch_one=True)

            bl_id = str(result['id'])
            logger.info(f"Created business line: {code} ({bl_id})")

            return bl_id

        except Exception as e:
            logger.error(f"Error creating business line: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

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

        # Get current entity structure (entities + business lines)
        structure = self.get_entities_with_business_lines()
        entities = structure['entities']
        business_lines = structure['business_lines']

        entities_text = ""
        if structure['entity_count'] > 0:
            entities_text = "\n**Current Entity Structure:**\n"
            for entity in entities:
                # Show entity info
                entity_type = entity.get('entity_type', 'Entity')
                currency = entity.get('base_currency', 'USD')
                entities_text += f"\n**Entity:** {entity['name']} ({entity['code']})\n"
                entities_text += f"  Type: {entity_type}, Currency: {currency}\n"

                # Show business lines for this entity
                entity_bls = [bl for bl in business_lines if bl['entity_id'] == entity['id']]
                if entity_bls:
                    # Don't show default-only business lines (progressive disclosure)
                    non_default_bls = [bl for bl in entity_bls if not bl.get('is_default')]
                    if non_default_bls:
                        entities_text += "  Business Lines:\n"
                        for bl in non_default_bls:
                            desc = f" - {bl['description']}" if bl.get('description') else ""
                            entities_text += f"    • {bl['name']} ({bl['code']}){desc}\n"
                    # Note if there are no non-default business lines
                    elif len(entity_bls) == 1:
                        entities_text += "  Business Lines: None (using default)\n"
                else:
                    entities_text += "  Business Lines: None\n"

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
        entities_asked = structure['entity_count'] > 0 or any('entit' in msg.get('content', '').lower() or 'subsidiar' in msg.get('content', '').lower() for msg in conversation_history[-5:])

        # Check if this is a fully configured tenant (has entities and core data)
        is_fully_configured = core_complete and structure['entity_count'] > 0

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
- Adding new legal entities (subsidiaries with separate tax IDs)
- Adding new business lines/divisions (profit centers within entities)
- Updating company information (location, industry, revenue)
- Learning about business patterns (vendors, expense categories, revenue sources)
- Analyzing documents they upload
- Answering questions about their data

**CRITICAL - Entity vs Business Line Distinction:**
When user mentions organizational structure:
- "subsidiary", "separate company", "different tax ID", "incorporated in" → Create LEGAL ENTITY
- "division", "department", "profit center", "business unit", "business line" → Create BUSINESS LINE
- "branch", "office", "location" → AMBIGUOUS - Ask: "Is [name] a separate legal entity with its own tax ID, or a division/branch within your main company?"

Examples:
- "We have Delta Mining in Delaware and Delta Paraguay" → 2 legal entities
- "We have 3 divisions: Hosting, Validator, Property" → 1 entity with 3 business lines
- "Our LLC has a hosting division and validator operations" → 1 entity + 2 business lines
- "We have a branch in Miami" → Ask clarifying question before creating

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
      "code": "DLLC",
      "name": "Delta Mining LLC",
      "legal_name": "Delta Mining LLC",
      "tax_id": "XX-XXXXXXX",
      "tax_jurisdiction": "US-Delaware",
      "entity_type": "LLC",
      "base_currency": "USD"
    }}
  ],
  "business_lines": [
    {{
      "entity_code": "DLLC",
      "code": "HOST",
      "name": "Hosting Services",
      "description": "Web hosting operations",
      "color_hex": "#3B82F6"
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
- **Entity vs Business Line**: CRITICAL distinction!
  * "subsidiary", "separate company", "different tax ID", "incorporated in" → LEGAL ENTITY (entities array)
  * "division", "department", "profit center", "business line", "business unit" → BUSINESS LINE (business_lines array)
  * "branch", "office", "location" → AMBIGUOUS - Ask: "Is [name] a separate legal entity with its own tax ID, or a division/branch within your main company?"
  * If unclear, ask clarifying question BEFORE creating anything
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
- **Entity Code Generation**: Create short 2-4 letter codes automatically:
  * "Delta Mining LLC" → "DLLC" or "DM"
  * "Acme Corporation" → "ACME" or "AC"
  * "Tech Solutions Inc" → "TSI" or "TECH"
  * Use company name abbreviation or acronym

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
      "code": "DLLC",
      "name": "Delta Mining LLC",
      "legal_name": "Delta Mining LLC",
      "tax_id": "XX-XXXXXXX",
      "tax_jurisdiction": "US-Delaware",
      "entity_type": "LLC",
      "base_currency": "USD",
      "fiscal_year_end": "12-31"
    }}
  ],
  "business_lines": [
    {{
      "entity_code": "DLLC",
      "code": "HOST",
      "name": "Hosting Services",
      "description": "Web hosting and infrastructure",
      "color_hex": "#3B82F6"
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

            # Extract and save entities and business lines
            entities = result.get('entities', [])
            business_lines = result.get('business_lines', [])
            entities_created = []
            business_lines_created = []

            # Map entity codes to UUIDs for business line creation
            entity_id_map = {}

            # Create entities first
            if entities:
                for entity_data in entities:
                    if entity_data.get('code') and entity_data.get('name'):
                        entity_id = self.create_entity(entity_data)
                        if entity_id:
                            entities_created.append(entity_data['name'])
                            entity_id_map[entity_data['code']] = entity_id
                            logger.info(f"Created entity: {entity_data['name']} ({entity_id})")

            # Create business lines for created entities
            if business_lines:
                for bl_data in business_lines:
                    entity_code = bl_data.get('entity_code')
                    if entity_code and entity_code in entity_id_map:
                        # Add entity_id to business line data
                        bl_data['entity_id'] = entity_id_map[entity_code]
                        bl_id = self.create_business_line(bl_data)
                        if bl_id:
                            business_lines_created.append(bl_data['name'])
                            logger.info(f"Created business line: {bl_data['name']} ({bl_id})")
                    elif bl_data.get('code') and bl_data.get('name'):
                        # Business line without entity_code - try to find first entity
                        if entity_id_map:
                            first_entity_id = list(entity_id_map.values())[0]
                            bl_data['entity_id'] = first_entity_id
                            bl_id = self.create_business_line(bl_data)
                            if bl_id:
                                business_lines_created.append(bl_data['name'])
                                logger.info(f"Created business line: {bl_data['name']} under first entity")

            # Build extracted summary
            extracted_summary = {}
            if updates:
                extracted_summary.update(updates)
            if entities_created:
                extracted_summary['entities_created'] = entities_created
            if business_lines_created:
                extracted_summary['business_lines_created'] = business_lines_created


            # Save assistant response
            self.save_message(session_id, 'assistant', result['response'], extracted_summary)

            return {
                'response': result['response'],
                'extracted_data': extracted,
                'entities_created': entities_created,
                'business_lines_created': business_lines_created,
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

    def get_completion_milestones(self) -> Dict[str, Any]:
        """
        Get completion status with meaningful milestones that reflect actual usage.

        Milestones:
        - Profile (20%): company_name + description + industry
        - Entities (20%): At least 1 entity created
        - Accounts (20%): At least 1 bank account or crypto wallet
        - Transactions (25%): At least 10 transactions uploaded
        - Patterns (15%): At least 3 classification patterns

        Returns:
            Dictionary with milestones, completion percentage, capabilities, and next steps
        """
        # Get tenant profile data
        current_data = self.get_current_tenant_data()

        # Get entity count
        structure = self.get_entities_with_business_lines()
        entity_count = structure.get('entity_count', 0)
        entity_names = [e.get('name', '') for e in structure.get('entities', [])[:5]]

        # Get account counts
        bank_accounts_result = self.db_manager.execute_query("""
            SELECT COUNT(*) as count FROM bank_accounts
            WHERE tenant_id = %s AND is_active = TRUE
        """, (self.tenant_id,), fetch_one=True)
        bank_account_count = bank_accounts_result['count'] if bank_accounts_result else 0

        crypto_wallets_result = self.db_manager.execute_query("""
            SELECT COUNT(*) as count FROM wallet_addresses
            WHERE tenant_id = %s AND is_active = TRUE
        """, (self.tenant_id,), fetch_one=True)
        crypto_wallet_count = crypto_wallets_result['count'] if crypto_wallets_result else 0

        # Get transaction count and date range
        transactions_result = self.db_manager.execute_query("""
            SELECT COUNT(*) as count,
                   MIN(date) as min_date,
                   MAX(date) as max_date
            FROM transactions
            WHERE tenant_id = %s
        """, (self.tenant_id,), fetch_one=True)
        transaction_count = transactions_result['count'] if transactions_result else 0
        min_date = transactions_result['min_date'] if transactions_result else None
        max_date = transactions_result['max_date'] if transactions_result else None

        # Get classification pattern count
        patterns_result = self.db_manager.execute_query("""
            SELECT COUNT(*) as count FROM classification_patterns
            WHERE tenant_id = %s AND is_active = TRUE
        """, (self.tenant_id,), fetch_one=True)
        pattern_count = patterns_result['count'] if patterns_result else 0

        # Define milestones
        milestones = {}

        # Profile milestone (20%)
        profile_fields = ['company_name', 'company_description', 'industry']
        profile_complete = all(current_data.get(f) for f in profile_fields)
        milestones['profile'] = {
            'id': 'profile',
            'name': 'Business Profile',
            'complete': profile_complete,
            'weight': 20,
            'icon': 'building',
            'details': {
                'company_name': current_data.get('company_name'),
                'industry': current_data.get('industry'),
                'has_description': bool(current_data.get('company_description'))
            }
        }

        # Entities milestone (20%)
        entities_complete = entity_count >= 1
        milestones['entities'] = {
            'id': 'entities',
            'name': 'Legal Entities',
            'complete': entities_complete,
            'weight': 20,
            'icon': 'sitemap',
            'details': {
                'count': entity_count,
                'names': entity_names,
                'required': 1
            }
        }

        # Accounts milestone (20%)
        total_accounts = bank_account_count + crypto_wallet_count
        accounts_complete = total_accounts >= 1
        milestones['accounts'] = {
            'id': 'accounts',
            'name': 'Financial Accounts',
            'complete': accounts_complete,
            'weight': 20,
            'icon': 'bank',
            'details': {
                'bank_accounts': bank_account_count,
                'crypto_wallets': crypto_wallet_count,
                'total': total_accounts,
                'required': 1
            }
        }

        # Transactions milestone (25%)
        transactions_complete = transaction_count >= 10
        milestones['transactions'] = {
            'id': 'transactions',
            'name': 'Transaction Data',
            'complete': transactions_complete,
            'weight': 25,
            'icon': 'exchange',
            'details': {
                'count': transaction_count,
                'required': 10,
                'date_range': f"{min_date} to {max_date}" if min_date and max_date else None
            }
        }

        # Patterns milestone (15%)
        patterns_complete = pattern_count >= 3
        milestones['patterns'] = {
            'id': 'patterns',
            'name': 'Classification Patterns',
            'complete': patterns_complete,
            'weight': 15,
            'icon': 'brain',
            'details': {
                'count': pattern_count,
                'required': 3
            }
        }

        # Calculate total completion percentage
        completion_percentage = sum(
            m['weight'] for m in milestones.values() if m['complete']
        )

        # Determine capabilities based on milestones
        capabilities = {
            'dashboard': True,  # Always enabled
            'entities': profile_complete,  # Requires profile
            'accounts': profile_complete,  # Requires profile
            'transactions': entities_complete,  # Requires entities
            'analytics': transactions_complete,  # Requires 10+ transactions
            'reports': transactions_complete,  # Requires transactions
            'workforce': transactions_complete,  # Requires transactions
            'invoices': transactions_complete,  # Requires transactions
            'patterns': entities_complete  # Requires entities
        }

        # Build next steps for incomplete milestones
        next_steps = []
        if not profile_complete:
            missing = [f.replace('_', ' ').title() for f in profile_fields if not current_data.get(f)]
            next_steps.append({
                'milestone': 'profile',
                'message': f"Complete your business profile: {', '.join(missing)}",
                'action_url': '/?openBot=true',
                'action_label': 'Complete Profile'
            })
        if not entities_complete:
            next_steps.append({
                'milestone': 'entities',
                'message': 'Add at least one legal entity to organize your finances',
                'action_url': '/entities',
                'action_label': 'Add Entity'
            })
        if not accounts_complete:
            next_steps.append({
                'milestone': 'accounts',
                'message': 'Add a bank account or crypto wallet to enable reconciliation',
                'action_url': '/whitelisted-accounts',
                'action_label': 'Add Account'
            })
        if not transactions_complete:
            next_steps.append({
                'milestone': 'transactions',
                'message': f'Upload transactions ({transaction_count}/10 minimum)',
                'action_url': '/files',
                'action_label': 'Upload Transactions'
            })
        if not patterns_complete:
            next_steps.append({
                'milestone': 'patterns',
                'message': f'Create classification patterns ({pattern_count}/3 minimum)',
                'action_url': '/tenant-knowledge',
                'action_label': 'Add Patterns'
            })

        return {
            'completion_percentage': completion_percentage,
            'milestones': milestones,
            'capabilities': capabilities,
            'next_steps': next_steps,
            'is_fully_setup': completion_percentage >= 80
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
        structure = self.get_entities_with_business_lines()
        entities = structure.get('entities', [])
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
