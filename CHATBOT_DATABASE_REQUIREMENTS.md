# Chatbot Database Requirements - Quick Reference

**Created:** 2025-10-22  
**Purpose:** Define database tables and schema needed for AI chatbot enhancements

---

## TOP 5 CRITICAL FINDINGS

### 1. **PRODUCTION BUG: Missing classification_patterns Table**
**Severity:** CRITICAL  
**Location:** `main.py` line 93-96

The code references a `classification_patterns` table that doesn't exist:
```python
cursor.execute("""
    SELECT pattern_type, description_pattern, entity, accounting_category, confidence_score
    FROM classification_patterns
    WHERE tenant_id = %s
""", (tenant_id,))
```

**Impact:** This fails silently if classification_patterns doesn't exist in the unified schema.
**Fix:** Add table to postgres_unified_schema.sql (see schema below)

---

### 2. **Schema Conflict: Two Different PostgreSQL Schemas**
**Severity:** HIGH

Two schema files exist with different table structures:
- `/postgres_unified_schema.sql` (15 tables, modern crypto invoice design)
- `/migration/postgresql_schema.sql` (4-5 tables, legacy transaction focus)

**Impact:** Uncertainty about which is the source of truth
**Fix:** 
1. Determine which schema is currently in production
2. Consolidate into single authoritative schema
3. Add missing tables to unified schema
4. Update DatabaseManager.init_database() to reference correct file

---

### 3. **No Pattern Learning Feedback Loop**
**Severity:** HIGH

Current flow:
```
User corrects classification
    ↓
Stored in user_interactions table
    ↓
❌ Pattern learning doesn't improve
    ↓
Next transaction: Same incorrect classification
```

**Fix:** Create pattern_feedback table and implement update logic

---

### 4. **Missing Multi-Tenant Support in Core Tables**
**Severity:** MEDIUM-HIGH

- `tenant_id` migration exists but not integrated
- Only wallet_addresses has tenant_id
- transactions, learned_patterns, user_interactions missing tenant_id

**Impact:** Cannot safely deploy for multiple customers
**Fix:** Add tenant_id to all core tables

---

### 5. **Business Rules Hardcoded in Markdown**
**Severity:** MEDIUM

Business rules stored in `business_knowledge.md` markdown file, not queryable:
```markdown
## Revenue Classification Patterns
- **Challenge Revenue**: Patterns like "Challenge", "Contest", "Prize"
- **Trading Revenue**: Patterns like "Trading", "Exchange", "Market"
```

**Impact:** Cannot dynamically update rules without code deployment
**Fix:** Move rules to database tables (business_rules, rule_conditions)

---

## REQUIRED TABLES FOR CHATBOT (with SQL)

### Priority 1: CRITICAL (Must have before deployment)

#### **1. classification_patterns** (FIXES main.py bug)
```sql
CREATE TABLE classification_patterns (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    pattern_type VARCHAR(50) NOT NULL,  -- 'revenue', 'expense', 'crypto', 'transfer'
    description_pattern TEXT NOT NULL,
    entity VARCHAR(100),
    accounting_category VARCHAR(100),
    confidence_score DECIMAL(5,2) DEFAULT 0.75,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    UNIQUE(tenant_id, pattern_type, description_pattern),
    INDEX idx_tenant_pattern (tenant_id, pattern_type),
    INDEX idx_active (is_active)
);
```

#### **2. transaction_audit_history** (Full transaction audit trail)
```sql
CREATE TABLE transaction_audit_history (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    action VARCHAR(20) NOT NULL,  -- 'CREATE', 'UPDATE', 'DELETE'
    changes JSONB,  -- {field: value, old: value}
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT,
    INDEX idx_transaction_id (transaction_id),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_timestamp (timestamp)
);
```

#### **3. user_sessions** (Track user context for chatbot)
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    user_id VARCHAR(100) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address VARCHAR(45),
    context_data JSONB,  -- Store conversation context
    INDEX idx_user_id (user_id),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_started_at (started_at)
);
```

#### **4. Update existing tables - Add tenant_id**
```sql
-- Add to transactions table
ALTER TABLE transactions ADD COLUMN tenant_id VARCHAR(100) DEFAULT 'delta' NOT NULL;
CREATE INDEX idx_transactions_tenant_id ON transactions(tenant_id);
CREATE INDEX idx_transactions_tenant_date ON transactions(tenant_id, date);

-- Add to learned_patterns table
ALTER TABLE learned_patterns ADD COLUMN tenant_id VARCHAR(100) DEFAULT 'delta' NOT NULL;
CREATE INDEX idx_patterns_tenant_id ON learned_patterns(tenant_id);

-- Add to user_interactions table
ALTER TABLE user_interactions 
    ADD COLUMN tenant_id VARCHAR(100) DEFAULT 'delta' NOT NULL,
    ADD COLUMN user_id VARCHAR(100),
    ADD COLUMN session_id VARCHAR(100),
    ADD COLUMN interaction_type VARCHAR(50),  -- 'correction', 'confirmation', 'question'
    ADD COLUMN outcome VARCHAR(20),  -- 'accepted', 'rejected', 'modified'
    ADD COLUMN confidence_adjustment DECIMAL(3,2);
CREATE INDEX idx_interactions_user_id ON user_interactions(user_id);
CREATE INDEX idx_interactions_session_id ON user_interactions(session_id);

-- Add to business_entities table
ALTER TABLE business_entities ADD COLUMN tenant_id VARCHAR(100) DEFAULT 'delta' NOT NULL;
CREATE INDEX idx_entities_tenant_id ON business_entities(tenant_id);
```

---

### Priority 2: HIGH (Needed for full chatbot intelligence)

#### **5. investor_relationships**
```sql
CREATE TABLE investor_relationships (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    investor_name VARCHAR(255) NOT NULL,
    investor_type VARCHAR(50),  -- 'VC', 'angel', 'institutional', 'individual'
    country VARCHAR(100),
    contact_email VARCHAR(255),
    investment_focus TEXT,  -- Business areas investor is interested in
    total_invested DECIMAL(15,2),
    first_investment_date DATE,
    last_investment_date DATE,
    status VARCHAR(20),  -- 'active', 'inactive', 'prospect'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_investor_type (investor_type)
);

CREATE TABLE investments (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    investor_id INTEGER NOT NULL REFERENCES investor_relationships(id) ON DELETE CASCADE,
    entity_id INTEGER NOT NULL REFERENCES business_entities(id) ON DELETE CASCADE,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    investment_date DATE NOT NULL,
    terms TEXT,  -- Equity %, debt terms, etc.
    status VARCHAR(20),  -- 'proposed', 'active', 'completed', 'exited'
    transaction_id INTEGER REFERENCES transactions(id),  -- Link to transaction
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_investor_id (investor_id),
    INDEX idx_entity_id (entity_id),
    INDEX idx_tenant_id (tenant_id)
);
```

#### **6. vendor_profiles**
```sql
CREATE TABLE vendor_profiles (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    vendor_name VARCHAR(255) NOT NULL,
    vendor_type VARCHAR(50),  -- 'service_provider', 'supplier', 'contractor'
    country VARCHAR(100),
    tax_id VARCHAR(50),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(20),
    payment_terms VARCHAR(50),  -- 'net30', 'net60', 'immediate'
    quality_score DECIMAL(3,2),  -- 0.0 to 1.0
    reliability_score DECIMAL(3,2),  -- Based on payment history
    total_spent DECIMAL(15,2),
    transaction_count INTEGER DEFAULT 0,
    last_transaction_date DATE,
    notes TEXT,
    is_preferred BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_vendor_type (vendor_type)
);

CREATE TABLE vendor_interactions (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    vendor_id INTEGER NOT NULL REFERENCES vendor_profiles(id) ON DELETE CASCADE,
    transaction_id INTEGER REFERENCES transactions(id),
    interaction_type VARCHAR(50),  -- 'payment', 'inquiry', 'complaint', 'praise'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_vendor_id (vendor_id),
    INDEX idx_tenant_id (tenant_id)
);
```

#### **7. business_rules** (Move from hardcoded markdown)
```sql
CREATE TABLE business_rules (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50),  -- 'classification', 'alert', 'validation'
    description TEXT,
    priority INTEGER DEFAULT 100,  -- Higher = execute first
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    UNIQUE(tenant_id, rule_name),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_active (is_active)
);

CREATE TABLE rule_conditions (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL REFERENCES business_rules(id) ON DELETE CASCADE,
    field_name VARCHAR(100),  -- 'description', 'amount', 'date', etc.
    operator VARCHAR(20),  -- 'contains', 'equals', 'greater_than', 'regex_match'
    condition_value TEXT,
    order_num INTEGER DEFAULT 0,  -- For AND/OR evaluation
    INDEX idx_rule_id (rule_id)
);

CREATE TABLE rule_actions (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL REFERENCES business_rules(id) ON DELETE CASCADE,
    action_type VARCHAR(50),  -- 'classify', 'alert', 'escalate'
    target_category VARCHAR(100),
    target_subcategory VARCHAR(100),
    target_entity VARCHAR(100),
    confidence_score DECIMAL(5,2),
    INDEX idx_rule_id (rule_id)
);
```

#### **8. pattern_feedback** (Improve pattern learning)
```sql
CREATE TABLE pattern_feedback (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    pattern_id INTEGER REFERENCES learned_patterns(id) ON DELETE CASCADE,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    user_id VARCHAR(100),
    feedback_type VARCHAR(50),  -- 'correct', 'incorrect', 'partial', 'helpful'
    accuracy_score DECIMAL(3,2),  -- User's confidence in pattern (0.0-1.0)
    provided_answer TEXT,  -- What user said was correct
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    useful BOOLEAN,  -- Was this feedback useful?
    INDEX idx_pattern_id (pattern_id),
    INDEX idx_transaction_id (transaction_id),
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp)
);
```

---

### Priority 3: MEDIUM (Nice to have, enables advanced features)

#### **9. category_hierarchy** (Flexible category management)
```sql
CREATE TABLE category_hierarchy (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    parent_id INTEGER REFERENCES category_hierarchy(id),
    category_name VARCHAR(100) NOT NULL,
    accounting_code VARCHAR(20),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    level INTEGER,  -- For reporting hierarchy
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, category_name),
    INDEX idx_parent_id (parent_id)
);
```

#### **10. chatbot_interactions** (Store all chatbot conversations)
```sql
CREATE TABLE chatbot_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    session_id UUID NOT NULL REFERENCES user_sessions(id),
    user_id VARCHAR(100) NOT NULL,
    user_message TEXT NOT NULL,
    chatbot_response TEXT,
    intent VARCHAR(50),  -- 'classify_transaction', 'analyze_vendor', 'report'
    entities_mentioned JSONB,  -- {entity_type: [values]}
    confidence_score DECIMAL(3,2),
    feedback_type VARCHAR(20),  -- 'helpful', 'not_helpful', 'partially_correct'
    is_resolved BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_intent (intent)
);

CREATE TABLE chatbot_context (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES user_sessions(id),
    context_key VARCHAR(100),  -- 'current_entity', 'current_period', 'filter'
    context_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, context_key)
);
```

#### **11. api_audit_log** (Track API usage)
```sql
CREATE TABLE api_audit_log (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    api_endpoint VARCHAR(255),
    method VARCHAR(10),
    request_data JSONB,
    response_status INTEGER,
    error_message TEXT,
    response_time_ms INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_timestamp (timestamp)
);
```

---

## IMPLEMENTATION ORDER

### Phase 1 (Week 1): Fix Critical Bugs
1. Create `classification_patterns` table
2. Add `tenant_id` to core tables
3. Create `transaction_audit_history`
4. Create `user_sessions`
5. Test main.py works with new schema

### Phase 2 (Week 2): Enable Learning
1. Create `pattern_feedback` table
2. Implement feedback loop in pattern learning logic
3. Create `user_interactions` enhancements
4. Test pattern improvement over time

### Phase 3 (Week 3): Chatbot Intelligence
1. Create `investor_relationships` & `investments` tables
2. Create `vendor_profiles` tables
3. Create `business_rules` tables
4. Create `chatbot_interactions` tables
5. Update chatbot to use new data sources

### Phase 4 (Week 4): Optimization
1. Create materialized views for analytics
2. Add indexes for performance
3. Implement Row Level Security (RLS) for tenants
4. Performance testing and tuning

---

## QUICK SUMMARY TABLE

| Table Name | Status | Priority | Purpose |
|---|---|---|---|
| classification_patterns | MISSING | CRITICAL | Main.py dependency, pattern storage |
| transaction_audit_history | MISSING | CRITICAL | Full audit trail |
| user_sessions | MISSING | CRITICAL | Session tracking for chatbot |
| transactions (+ tenant_id) | EXISTS | CRITICAL | Add missing field |
| learned_patterns (+ tenant_id) | EXISTS | CRITICAL | Add missing field |
| user_interactions (+ fields) | EXISTS | CRITICAL | Add missing fields |
| business_entities (+ tenant_id) | EXISTS | CRITICAL | Add missing field |
| investor_relationships | MISSING | HIGH | Financial stakeholder tracking |
| investments | MISSING | HIGH | Investment management |
| vendor_profiles | MISSING | HIGH | Vendor intelligence |
| vendor_interactions | MISSING | HIGH | Vendor transaction history |
| business_rules | MISSING | HIGH | Move from markdown |
| rule_conditions | MISSING | HIGH | Rule configuration |
| rule_actions | MISSING | HIGH | Rule execution |
| pattern_feedback | MISSING | HIGH | Pattern improvement |
| category_hierarchy | MISSING | MEDIUM | Flexible categorization |
| chatbot_interactions | MISSING | MEDIUM | Store conversations |
| chatbot_context | MISSING | MEDIUM | Session context |
| api_audit_log | MISSING | MEDIUM | Usage tracking |

---

## DATABASE SIZE IMPACT

### Current Size (Estimated):
- transactions: 10K-100K rows = 10-50 MB
- invoices: 100-1K rows = 1-10 MB
- Other tables: < 10 MB
- **Total: ~100-200 MB**

### After Additions (Estimated):
- New tables: ~50 MB (static data)
- chatbot_interactions: ~1-10 MB/month
- audit_history: ~5-20 MB/month
- **Monthly growth: ~10-30 MB/month**

### Cost Impact (Google Cloud SQL):
- Standard-1 tier: ~$10-15/month (OK for 1 year)
- Projected 1 year: 1-5 GB total size
- Recommendation: Use smallest Cloud SQL tier initially, scale as needed

---

## DATA ISOLATION & SECURITY

### Current Gaps:
1. No Row Level Security (RLS) policies
2. Hard-coded credentials in main.py
3. No encryption for sensitive fields

### Required Before Production:
1. Enable RLS policies (when authentication ready)
2. Remove hardcoded DB_PASSWORD from main.py
3. Add encryption to wallet addresses column
4. Add audit logging to sensitive tables
5. Implement data access controls by tenant

---

## NEXT STEPS

1. **Review this analysis** with development team
2. **Decide on schema strategy**: Keep unified or consolidate?
3. **Create database migration script** for all Priority 1 tables
4. **Update DatabaseManager** with tenant filtering
5. **Test main.py** with new classification_patterns table
6. **Implement pattern feedback loop** in classification logic
7. **Design chatbot context management** (use user_sessions + chatbot_context)

---

## CONTACTS & REFERENCES

- **Schema Files:**
  - `/postgres_unified_schema.sql` (Main schema - 15 tables)
  - `/migration/postgresql_schema.sql` (Legacy schema - 4 tables)
  - `/migrations/add_tenant_id_to_core_tables.sql` (Tenant migration)
  - `/migrations/create_wallet_addresses_table.sql` (Wallet addresses)

- **Related Files:**
  - `web_ui/database.py` - DatabaseManager implementation
  - `main.py` - Transaction classification (line 93 references missing table)
  - `business_knowledge.md` - Hardcoded business rules

---

## APPENDIX: Full SQL for Phase 1 Implementation

See the section "REQUIRED TABLES FOR CHATBOT" above for complete CREATE TABLE statements with indexes.

