# Phase 4: Onboarding Bot Update for Entity/Business Line Architecture

## Overview
Update the onboarding bot to work with the new Entity/Business Line architecture completed in Phases 1-3. The bot currently uses the deprecated `business_entities` table and needs to be updated to use the new `entities` and `business_lines` tables.

## Context

### What's Been Completed (Phases 1-3)
✅ Phase 1: Database schema (`entities` and `business_lines` tables)
✅ Phase 2: REST APIs (`/api/entities` and `/api/business-lines`)
✅ Phase 3: Frontend management page (`/entities`)

### What's Needed (Phase 4)
❌ Onboarding bot integration with new architecture
❌ Conversation flow updates to distinguish entities vs business lines
❌ API route updates for onboarding
❌ Progressive disclosure for simple vs complex businesses

## Architecture Comparison

### OLD System (Current Onboarding Bot)
```
business_entities table:
- id
- name
- description
- entity_type (subsidiary/vendor/customer/internal)
- active
```

### NEW System (Target)
```
entities table (Legal Entities - Tier 2):
- id (UUID)
- tenant_id
- code (e.g., "DLLC", "DPY")
- name
- legal_name
- tax_id
- tax_jurisdiction
- entity_type (LLC, S-Corp, etc.)
- base_currency
- fiscal_year_end
- address
- country_code
- is_active

business_lines table (Profit Centers - Tier 3):
- id (UUID)
- entity_id (FK to entities)
- code (e.g., "HOST", "VAL")
- name
- description
- color_hex
- is_default
- is_active
```

## Implementation Plan

### Task 4.1: Update OnboardingBot Service ⚠️ CRITICAL
**File:** `web_ui/services/onboarding_bot.py`
**Lines to modify:** ~178-281

#### Changes Required:

**1. Update `get_business_entities()` → `get_entities_with_business_lines()`**
```python
def get_entities_with_business_lines(self) -> Dict[str, Any]:
    """Get all entities and their business lines for the current tenant"""
    # Query entities table
    entities_query = """
        SELECT id, tenant_id, code, name, legal_name, tax_id,
               entity_type, base_currency, is_active
        FROM entities
        WHERE tenant_id = %s AND is_active = TRUE
        ORDER BY name
    """

    # Query business_lines table
    business_lines_query = """
        SELECT bl.id, bl.entity_id, bl.code, bl.name, bl.description,
               bl.color_hex, bl.is_default
        FROM business_lines bl
        JOIN entities e ON bl.entity_id = e.id
        WHERE e.tenant_id = %s AND bl.is_active = TRUE
        ORDER BY e.name, bl.name
    """

    entities = self.db_manager.execute_query(entities_query, (self.tenant_id,), fetch_all=True)
    business_lines = self.db_manager.execute_query(business_lines_query, (self.tenant_id,), fetch_all=True)

    # Group business lines by entity
    result = {
        'entities': [dict(e) for e in entities],
        'business_lines': [dict(bl) for bl in business_lines],
        'entity_count': len(entities),
        'business_line_count': len(business_lines)
    }

    return result
```

**2. Replace `create_or_update_business_entity()` with two methods:**

```python
def create_entity(self, entity_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a legal entity for the tenant

    Args:
        entity_data: {
            'code': 'DLLC',
            'name': 'Delta Mining LLC',
            'legal_name': 'Delta Mining LLC', (optional)
            'tax_id': 'XX-XXXXXXX', (optional)
            'entity_type': 'LLC', (optional)
            'base_currency': 'USD',
            'fiscal_year_end': '12-31'
        }

    Returns:
        entity_id (UUID) if successful, None otherwise
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
                tenant_id, code, name, legal_name, tax_id, entity_type,
                base_currency, fiscal_year_end, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            RETURNING id
        """

        result = self.db_manager.execute_query(query, (
            self.tenant_id,
            code,
            name,
            entity_data.get('legal_name', name),
            entity_data.get('tax_id'),
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
        return None


def create_business_line(self, bl_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a business line under an entity

    Args:
        bl_data: {
            'entity_id': 'uuid-string',
            'code': 'HOST',
            'name': 'Hosting Services',
            'description': 'Web hosting operations', (optional)
            'color_hex': '#3B82F6', (optional)
            'is_default': False
        }

    Returns:
        business_line_id (UUID) if successful, None otherwise
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
                entity_id, code, name, description, color_hex, is_default, is_active
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
        return None
```

**3. Update `_build_conversation_prompt()` to distinguish entities vs business lines**

Key changes to the prompt (lines 282-473):

```python
# Update entities_text to show both entities and business lines
structure = self.get_entities_with_business_lines()
entities_text = ""

if structure['entity_count'] > 0:
    entities_text = "\n**Current Entity Structure:**\n"
    for entity in structure['entities']:
        entities_text += f"\n**Entity:** {entity['name']} ({entity['code']})\n"

        # Show business lines for this entity
        entity_bls = [bl for bl in structure['business_lines']
                      if bl['entity_id'] == entity['id']]
        if entity_bls:
            entities_text += "  Business Lines:\n"
            for bl in entity_bls:
                default_tag = " (default)" if bl.get('is_default') else ""
                entities_text += f"  - {bl['name']} ({bl['code']}){default_tag}\n"
        else:
            entities_text += "  Business Lines: None\n"
```

**4. Update Claude prompt to extract entity and business line data separately:**

Add to prompt response format:
```python
**Response Format** (JSON):
{
  "response": "Your natural, conversational response",
  "extracted_data": {
    "company_name": "value or null",
    "industry": "value or null",
    ...
  },
  "entities": [
    {
      "code": "DLLC",
      "name": "Delta Mining LLC",
      "legal_name": "Delta Mining LLC",
      "tax_id": "XX-XXXXXXX",
      "entity_type": "LLC",
      "base_currency": "USD"
    }
  ],
  "business_lines": [
    {
      "entity_code": "DLLC",  // Which entity this belongs to
      "code": "HOST",
      "name": "Hosting Services",
      "description": "Web hosting operations",
      "color_hex": "#3B82F6"
    }
  ],
  "next_question": "what to ask next or null",
  "completion_percentage": 75
}
```

**5. Update `chat()` method to process both entities and business lines:**

```python
# Extract and save entities (lines 582-592)
entities = result.get('entities', [])
business_lines = result.get('business_lines', [])
entities_created = []
business_lines_created = []

# Create entities first
entity_id_map = {}  # Map entity code to UUID
if entities:
    for entity_data in entities:
        if entity_data.get('code') and entity_data.get('name'):
            entity_id = self.create_entity(entity_data)
            if entity_id:
                entities_created.append(entity_data['name'])
                entity_id_map[entity_data['code']] = entity_id
                logger.info(f"Created entity: {entity_data['name']}")

# Create business lines for created entities
if business_lines:
    for bl_data in business_lines:
        entity_code = bl_data.get('entity_code')
        if entity_code and entity_code in entity_id_map:
            bl_data['entity_id'] = entity_id_map[entity_code]
            bl_id = self.create_business_line(bl_data)
            if bl_id:
                business_lines_created.append(bl_data['name'])
                logger.info(f"Created business line: {bl_data['name']}")

# Update extracted summary
extracted_summary = {}
if updates:
    extracted_summary.update(updates)
if entities_created:
    extracted_summary['entities_created'] = entities_created
if business_lines_created:
    extracted_summary['business_lines_created'] = business_lines_created
```

### Task 4.2: Update Onboarding API Routes
**File:** `api/onboarding_routes.py`
**Lines to modify:** ~194-206, ~303-338

#### Changes Required:

**1. Update `/api/onboarding/complete-setup` endpoint (lines 111-301):**

Replace the entities creation section (currently lines 194-206):

```python
# OLD (lines 194-206):
# 2.5. Create business entities if provided
for entity in entities:
    db_manager.execute_query("""
        INSERT INTO business_entities
        (tenant_id, name, description, entity_type, active)
        VALUES (%s, %s, %s, %s, true)
    """, (
        tenant_id,
        entity.get('name'),
        entity.get('description', ''),
        entity.get('entity_type', 'subsidiary')
    ))

# NEW:
# 2.5. Create entities and business lines if provided
entity_id_map = {}  # Map entity codes to UUIDs
for entity in entities:
    entity_code = entity.get('code', entity.get('name')[:4].upper())
    entity_name = entity.get('name')

    # Create entity
    result = db_manager.execute_query("""
        INSERT INTO entities
        (tenant_id, code, name, legal_name, entity_type, base_currency, fiscal_year_end, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, true)
        RETURNING id
    """, (
        tenant_id,
        entity_code,
        entity_name,
        entity.get('legal_name', entity_name),
        entity.get('entity_type', 'LLC'),
        entity.get('base_currency', 'USD'),
        entity.get('fiscal_year_end', '12-31')
    ), fetch_one=True)

    entity_id = str(result['id'])
    entity_id_map[entity_code] = entity_id

    # Create default business line for this entity
    db_manager.execute_query("""
        INSERT INTO business_lines
        (entity_id, code, name, description, is_default, is_active)
        VALUES (%s, 'DEFAULT', %s, 'General operations', true, true)
    """, (entity_id, f"{entity_name} - General"))

# Create additional business lines if provided
business_lines = data.get('business_lines', [])
for bl in business_lines:
    entity_code = bl.get('entity_code')
    if entity_code and entity_code in entity_id_map:
        db_manager.execute_query("""
            INSERT INTO business_lines
            (entity_id, code, name, description, color_hex, is_default, is_active)
            VALUES (%s, %s, %s, %s, %s, false, true)
        """, (
            entity_id_map[entity_code],
            bl.get('code'),
            bl.get('name'),
            bl.get('description', ''),
            bl.get('color_hex', '#3B82F6')
        ))
```

**2. Update `/api/onboarding/entities` GET endpoint (lines 303-338):**

```python
@onboarding_bp.route('/entities', methods=['GET'])
@require_auth
def get_entities():
    """
    Get all entities with their business lines for current tenant.

    Returns:
        {
            "success": true,
            "entities": [
                {
                    "id": "uuid",
                    "code": "DLLC",
                    "name": "Delta Mining LLC",
                    "entity_type": "LLC",
                    "active": true,
                    "business_lines": [
                        {
                            "id": "uuid",
                            "code": "HOST",
                            "name": "Hosting Services",
                            "is_default": false
                        }
                    ]
                }
            ]
        }
    """
    try:
        tenant_id = get_current_tenant_id()

        # Get entities
        entities = db_manager.execute_query("""
            SELECT id, tenant_id, code, name, legal_name, entity_type,
                   base_currency, is_active, created_at
            FROM entities
            WHERE tenant_id = %s AND is_active = true
            ORDER BY name
        """, (tenant_id,), fetch_all=True)

        # Get business lines
        business_lines = db_manager.execute_query("""
            SELECT bl.id, bl.entity_id, bl.code, bl.name, bl.description,
                   bl.color_hex, bl.is_default
            FROM business_lines bl
            JOIN entities e ON bl.entity_id = e.id
            WHERE e.tenant_id = %s AND bl.is_active = true
            ORDER BY e.name, bl.name
        """, (tenant_id,), fetch_all=True)

        # Build result with business lines nested under entities
        result_entities = []
        for entity in entities:
            entity_dict = dict(entity)
            entity_dict['id'] = str(entity_dict['id'])
            entity_dict['business_lines'] = [
                {
                    'id': str(bl['id']),
                    'code': bl['code'],
                    'name': bl['name'],
                    'description': bl['description'],
                    'color_hex': bl['color_hex'],
                    'is_default': bl['is_default']
                }
                for bl in business_lines
                if bl['entity_id'] == entity['id']
            ]
            result_entities.append(entity_dict)

        return jsonify({
            'success': True,
            'entities': result_entities
        }), 200

    except Exception as e:
        logger.error(f"Get entities error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred'
        }), 500
```

**3. Update `/api/onboarding/entities` POST endpoint:**

```python
@onboarding_bp.route('/entities', methods=['POST'])
@require_auth
def create_entity():
    """
    Create a new entity with default business line for current tenant.

    Request Body:
        {
            "code": "DLLC",
            "name": "Delta Mining LLC",
            "legal_name": "Delta Mining LLC",  // optional
            "entity_type": "LLC",  // optional
            "base_currency": "USD"  // optional
        }

    Returns:
        {
            "success": true,
            "entity": {...},
            "default_business_line": {...}
        }
    """
    try:
        tenant_id = get_current_tenant_id()
        data = request.get_json()

        if not data.get('code') or not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'code and name are required'
            }), 400

        # Insert entity
        entity_result = db_manager.execute_query("""
            INSERT INTO entities
            (tenant_id, code, name, legal_name, entity_type, base_currency,
             fiscal_year_end, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, true)
            RETURNING id, tenant_id, code, name, legal_name, entity_type,
                      base_currency, is_active, created_at
        """, (
            tenant_id,
            data['code'],
            data['name'],
            data.get('legal_name', data['name']),
            data.get('entity_type', 'LLC'),
            data.get('base_currency', 'USD'),
            data.get('fiscal_year_end', '12-31')
        ), fetch_one=True)

        entity_id = str(entity_result['id'])

        # Create default business line
        bl_result = db_manager.execute_query("""
            INSERT INTO business_lines
            (entity_id, code, name, description, is_default, is_active)
            VALUES (%s, 'DEFAULT', %s, 'General operations', true, true)
            RETURNING id, entity_id, code, name, description, is_default, created_at
        """, (entity_id, f"{data['name']} - General"), fetch_one=True)

        logger.info(f"Created entity: {data['name']} with default business line for tenant: {tenant_id}")

        return jsonify({
            'success': True,
            'entity': dict(entity_result),
            'default_business_line': dict(bl_result)
        }), 201

    except Exception as e:
        logger.error(f"Create entity error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': f'An error occurred: {str(e)}'
        }), 500
```

**4. Add new endpoint `/api/onboarding/business-lines`:**

```python
@onboarding_bp.route('/business-lines', methods=['POST'])
@require_auth
def create_business_line():
    """
    Create a new business line under an entity.

    Request Body:
        {
            "entity_id": "uuid",
            "code": "HOST",
            "name": "Hosting Services",
            "description": "Web hosting operations",  // optional
            "color_hex": "#3B82F6"  // optional
        }

    Returns:
        {
            "success": true,
            "business_line": {...}
        }
    """
    try:
        tenant_id = get_current_tenant_id()
        data = request.get_json()

        if not data.get('entity_id') or not data.get('code') or not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'entity_id, code, and name are required'
            }), 400

        # Verify entity belongs to tenant
        entity_check = db_manager.execute_query("""
            SELECT id FROM entities
            WHERE id = %s AND tenant_id = %s
        """, (data['entity_id'], tenant_id), fetch_one=True)

        if not entity_check:
            return jsonify({
                'success': False,
                'error': 'invalid_entity',
                'message': 'Entity not found or access denied'
            }), 404

        # Insert business line
        result = db_manager.execute_query("""
            INSERT INTO business_lines
            (entity_id, code, name, description, color_hex, is_default, is_active)
            VALUES (%s, %s, %s, %s, %s, false, true)
            RETURNING id, entity_id, code, name, description, color_hex,
                      is_default, is_active, created_at
        """, (
            data['entity_id'],
            data['code'],
            data['name'],
            data.get('description', ''),
            data.get('color_hex', '#3B82F6')
        ), fetch_one=True)

        logger.info(f"Created business line: {data['name']} for tenant: {tenant_id}")

        return jsonify({
            'success': True,
            'business_line': dict(result)
        }), 201

    except Exception as e:
        logger.error(f"Create business line error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': f'An error occurred: {str(e)}'
        }), 500
```

### Task 4.3: Update Conversation Prompts
**File:** `web_ui/services/onboarding_bot.py`

Add intelligent questioning to distinguish entity types:

```python
**Entity vs Business Line Guidance:**

When user mentions organizational structure:
- "subsidiary", "separate company", "different tax ID" → Create ENTITY
- "division", "department", "profit center", "business unit" → Create BUSINESS LINE
- "branch", "office", "location" → Ask: "Is this a separate legal entity or a division?"

Examples:
- User: "We have Delta Mining in Delaware and Delta Paraguay"
  → Extract: 2 entities (different legal entities)

- User: "We have 3 divisions: Hosting, Validator, Property"
  → Extract: 1 entity with 3 business lines (profit centers)

- User: "We have an LLC in Delaware with 2 business units"
  → Extract: 1 entity (Delaware LLC) + 2 business lines

**Smart Defaults:**
- Single business: 1 entity + 1 default business line (hidden)
- Multiple divisions same company: 1 entity + N business lines
- Multiple companies: N entities + 1 default business line each
```

### Task 4.4: Update Frontend Bot UI (Optional Enhancement)
**File:** `web_ui/static/onboarding_bot.js`

Add visual indicators for entity vs business line:

```javascript
// In renderMessage() function, add badges for extracted data
if (entities_created && entities_created.length > 0) {
    html += '<div class="mt-2">';
    html += '<span class="badge bg-primary">🏢 Entities Created:</span> ';
    html += entities_created.join(', ');
    html += '</div>';
}

if (business_lines_created && business_lines_created.length > 0) {
    html += '<div class="mt-2">';
    html += '<span class="badge bg-info">📊 Business Lines Created:</span> ';
    html += business_lines_created.join(', ');
    html += '</div>';
}
```

## Testing Plan

### Test Case 1: Simple Business (1 Entity, 1 Business Line)
**Scenario:** Small business owner, no complex structure

**User Input:**
```
Bot: "What's your company name?"
User: "Acme Corporation"

Bot: "Do you operate as a single company or have subsidiaries?"
User: "Just one company"

Bot: "Great! What's your entity code (e.g., ACME)?"
User: "ACME"
```

**Expected Result:**
- 1 entity created: "ACME" / "Acme Corporation"
- 1 default business line created: "DEFAULT" / "General Operations"
- Default business line hidden in UI (progressive disclosure)

### Test Case 2: Multi-Division Business (1 Entity, Multiple Business Lines)
**Scenario:** Medium business with profit centers

**User Input:**
```
Bot: "What's your company name?"
User: "Delta Services LLC"

Bot: "Do you have any divisions or profit centers?"
User: "Yes, we have Hosting Services, Validator Operations, and Property Management"

Bot: "Got it! What entity code would you like (e.g., DSL)?"
User: "DSL"
```

**Expected Result:**
- 1 entity created: "DSL" / "Delta Services LLC"
- 4 business lines created:
  - "DEFAULT" / "General Operations" (hidden, is_default=true)
  - "HOST" / "Hosting Services"
  - "VAL" / "Validator Operations"
  - "PROP" / "Property Management"

### Test Case 3: Multi-Entity Business (Multiple Entities, Multiple Business Lines)
**Scenario:** Complex holding company structure

**User Input:**
```
Bot: "What's your company name?"
User: "Delta Capital Holdings"

Bot: "Do you have subsidiaries or operate multiple legal entities?"
User: "Yes, we have Delta Mining LLC in Delaware and Delta Paraguay SA in Paraguay"

Bot: "Great! Do any of these entities have divisions or business lines?"
User: "Yes, Delta Mining has Hosting and Validator divisions"
```

**Expected Result:**
- 2 entities created:
  - "DLLC" / "Delta Mining LLC" (entity_type: LLC, tax_jurisdiction: US-Delaware)
  - "DPY" / "Delta Paraguay SA" (entity_type: SA, tax_jurisdiction: Paraguay)
- 4 business lines created:
  - "DLLC" → "DEFAULT" / "General Operations" (hidden)
  - "DLLC" → "HOST" / "Hosting Services"
  - "DLLC" → "VAL" / "Validator Operations"
  - "DPY" → "DEFAULT" / "General Operations" (hidden)

### Test Case 4: Existing Tenant Update
**Scenario:** Tenant already has company info, adding entities

**User Input:**
```
User: "I need to add a new subsidiary"

Bot: "Sure! What's the name of the new subsidiary?"
User: "Delta Brazil Ltda"

Bot: "What entity code (e.g., DBR)?"
User: "DBR"

Bot: "What type of entity (LLC, S-Corp, SA, Ltda, etc.)?"
User: "Ltda"
```

**Expected Result:**
- 1 entity created: "DBR" / "Delta Brazil Ltda" (entity_type: Ltda)
- 1 default business line created: "DEFAULT" / "General Operations"
- No change to existing tenant data

## Success Criteria

### Functional
- [ ] Bot creates entities in `entities` table (not `business_entities`)
- [ ] Bot creates business lines in `business_lines` table
- [ ] Each entity has at least one business line (default)
- [ ] Bot distinguishes between legal entities and profit centers
- [ ] Bot extracts entity-specific data (code, tax_id, entity_type)
- [ ] Bot extracts business line data (code, color_hex)
- [ ] Default business lines marked with is_default=true
- [ ] All entities visible in /entities page
- [ ] All business lines visible in /entities page

### Conversation Quality
- [ ] Bot asks clear questions about entity structure
- [ ] Bot explains difference between entity and business line
- [ ] Bot handles simple cases without overwhelming user
- [ ] Bot handles complex cases with full detail capture
- [ ] Bot provides helpful examples and guidance

### Data Quality
- [ ] Entity codes are unique per tenant
- [ ] Business line codes are unique per entity
- [ ] All foreign keys are valid UUIDs
- [ ] Multi-tenant isolation maintained
- [ ] No orphaned business lines (all have valid entity_id)

### User Experience
- [ ] Simple businesses don't see complexity
- [ ] Progressive disclosure works correctly
- [ ] Complex businesses can express full structure
- [ ] Clear confirmation of what was created
- [ ] Easy to correct mistakes

## Rollback Plan

If issues arise:

1. **Keep old `business_entities` table temporarily**
   - Don't drop during migration
   - Bot can fall back if new tables fail

2. **Feature flag for new flow**
   ```python
   USE_NEW_ENTITY_STRUCTURE = os.getenv('USE_NEW_ENTITY_STRUCTURE', 'false') == 'true'
   ```

3. **Gradual rollout**
   - Enable for Delta tenant only initially
   - Monitor for errors and user feedback
   - Enable for new tenants once stable
   - Enable for all tenants after 2 weeks

4. **Migration script for existing data**
   ```bash
   python migrations/migrate_business_entities_to_entities.py
   ```

## Timeline

- **Day 1:** Task 4.1 - Update OnboardingBot service (4-6 hours)
- **Day 2:** Task 4.2 - Update API routes (3-4 hours)
- **Day 3:** Task 4.3 - Update conversation prompts (2-3 hours)
- **Day 3:** Task 4.4 - Update frontend UI (1-2 hours, optional)
- **Day 4:** Testing and refinement (full day)
- **Day 5:** Documentation and deployment (2-3 hours)

**Total:** 3-5 days

## Next Steps After Phase 4

Once onboarding bot is complete:

- **Phase 5:** Entity-specific reporting and dashboards
- **Phase 6:** AI classification with entity/business line inference
- **Phase 7:** Intercompany transaction tracking
- **Phase 8:** Multi-entity consolidation and reporting

## References

- Phase 1-3 implementation: `tasks/todo.md`
- Entity API: `web_ui/entity_api.py`
- Database schema: `migrations/add_entities_and_business_lines.sql`
- Frontend: `web_ui/templates/entities.html`, `web_ui/static/js/entities.js`
