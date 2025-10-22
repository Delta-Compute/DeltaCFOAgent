# DeltaCFOAgent Database Schema Analysis

**Date:** 2025-10-22  
**Status:** Comprehensive Schema Review  
**Focus:** Understanding current structure and gaps for chatbot enhancement

---

## EXECUTIVE SUMMARY

The database architecture consists of **two distinct schema sets** that need reconciliation:

1. **Unified Schema** (`postgres_unified_schema.sql`) - Modern, production-ready design with crypto support
2. **Migration Schema** (`migration/postgresql_schema.sql`) - Legacy design focusing on transactions and invoices

### Current Issues:
- **Schema Conflict**: Two different PostgreSQL schemas exist but the codebase references different tables
- **Missing Tables**: `classification_patterns` table referenced in `main.py` (line 93) doesn't exist in schema
- **Pattern Learning**: Current `learned_patterns` table is under-designed for the chatbot requirements
- **No Investor/Funding Tracking**: Missing tables for investor relationships and funding sources
- **No Business Logic Config**: Missing dedicated tables for configurable business rules

---

## DATABASE TABLES - COMPLETE INVENTORY

### PART 1: CORE TRANSACTION & PATTERN MANAGEMENT

#### **1. transactions** (Unified Schema)
```
Columns: id, date, description, amount, type, category, subcategory, 
         entity, origin, destination, confidence_score, ai_generated, 
         created_at, updated_at
Indexes: date, entity, category, amount, created_at
Purpose: Core financial transaction records
Gaps: Missing tenant_id (multi-tenant support), no link to learned patterns
```

#### **2. learned_patterns** (Unified Schema)
```
Columns: id, description_pattern, suggested_category, suggested_subcategory, 
         suggested_entity, confidence_score, usage_count, created_at, updated_at
Indexes: None
Purpose: Store learned transaction classification patterns
Gaps: 
  - No pattern type field (revenue, expense, crypto, etc.)
  - No feedback mechanism linking back to transactions
  - No frequency analysis (last_used_at missing)
  - No pattern versioning or deprecation tracking
  - Should have context fields (industry, business_type)
```

#### **3. user_interactions** (Unified Schema)
```
Columns: id, transaction_id (FK), original_category, user_category, 
         original_entity, user_entity, feedback_type, created_at
Purpose: Track user corrections/confirmations for reinforcement learning
Gaps:
  - No session tracking (user_id missing)
  - No interaction_type details (confidence adjustment, rule creation, etc.)
  - No outcome field (was correction applied, was it helpful?)
  - No timestamp for when correction was applied
```

#### **4. business_entities** (Unified Schema)
```
Columns: id, name, description, entity_type, active, created_at
Purpose: Known business entities for classification
Current Values (pre-loaded):
  - Delta LLC (subsidiary)
  - Delta Prop Shop LLC (subsidiary)
  - Infinity Validator (subsidiary)
  - MMIW LLC (subsidiary)
  - DM Mining LLC (subsidiary)
  - Delta Mining Paraguay S.A. (subsidiary)
Gaps:
  - No parent_entity_id (for hierarchies)
  - No region/country field
  - No address or tax_id
  - No performance metrics
  - No relationships to customers/vendors
```

---

### PART 2: MULTI-TENANT INFRASTRUCTURE (From Migrations)

#### **5. wallet_addresses** (NEW - Migration)
```
Columns: id (UUID), tenant_id, wallet_address, entity_name, purpose, 
         wallet_type, confidence_score, is_active, notes, 
         created_at, updated_at, created_by
Indexes: tenant_id, wallet_address, entity_name, is_active
Purpose: Classify crypto transactions by wallet address
Status: NEWLY ADDED, requires integration with main schema
Pre-loaded:
  - 0x86cc1529bdf444200f06957ab567b56a385c5e90 (Internal Transfer)
```

#### **6. transaction_history** (Migration Schema)
```
Columns: id, transaction_id (FK), field_name, old_value, new_value, 
         changed_by, changed_at, change_reason
Purpose: Audit trail for transaction changes
Status: Only in migration schema, not in unified schema
Missing in unified: This should exist for compliance/audit
```

---

### PART 3: CRYPTO INVOICE SYSTEM

#### **7. invoices** (Unified Schema)
```
Columns: id, invoice_number, client_id (FK), status, amount_usd, 
         crypto_currency, crypto_amount, crypto_network, exchange_rate, 
         deposit_address, memo_tag, billing_period, description, 
         line_items (JSONB), due_date, issue_date, paid_at, 
         payment_tolerance, pdf_path, qr_code_path, notes, 
         created_at, updated_at
Indexes: status, client_id, due_date, created_at, crypto_currency
Purpose: Cryptocurrency invoice tracking and payment monitoring
```

#### **8. clients** (Unified Schema)
```
Columns: id, name, contact_email, billing_address, tax_id, notes, 
         created_at, updated_at
Pre-loaded:
  - Alps Blockchain (mining client)
  - Exos Capital (investment fund)
  - GM Data Centers (colocation)
  - Other (miscellaneous)
Gaps:
  - No client_type field (vendor, customer, partner)
  - No payment_terms or credit_limit
  - No contact_person or phone
```

#### **9. payment_transactions** (Unified Schema)
```
Columns: id, invoice_id (FK), transaction_hash, amount_received, currency, 
         network, deposit_address, status, confirmations, 
         required_confirmations, is_manual_verification, verified_by, 
         mexc_transaction_id, raw_api_response (JSONB), detected_at, 
         confirmed_at, created_at
Purpose: Track individual crypto payments against invoices
```

#### **10. mexc_addresses** (Unified Schema)
```
Columns: id, currency, network, address, memo_tag, is_primary, 
         last_used_at, created_at
Purpose: Cache MEXC deposit addresses for payment monitoring
```

#### **11. address_usage** (Unified Schema)
```
Columns: id, address, invoice_id (FK), used_at
Purpose: Track which address is used for which invoice
```

#### **12. polling_logs** (Unified Schema)
```
Columns: id, invoice_id (FK), status, deposits_found, error_message, 
         api_response, created_at
Purpose: Log payment polling operations
```

#### **13. notifications** (Unified Schema)
```
Columns: id, invoice_id (FK), notification_type, recipient_email, 
         subject, message, sent_at, status, error_message, created_at
Purpose: Track email notifications sent to clients
```

---

### PART 4: SYSTEM CONFIGURATION

#### **14. crypto_historic_prices** (Unified Schema)
```
Columns: date, symbol, price_usd, created_at, updated_at
Primary Key: (date, symbol)
Purpose: Store historical cryptocurrency prices for USD conversions
```

#### **15. system_config** (Unified Schema)
```
Columns: key (PK), value, description, updated_at
Pre-loaded values:
  - invoice_overdue_days: 7
  - default_payment_tolerance: 0.005
  - polling_interval_seconds: 30
  - btc_confirmations_required: 3
  - usdt_confirmations_required: 20
  - tao_confirmations_required: 12
Purpose: System-wide configuration
```

---

### PART 5: VIEWS FOR ANALYTICS

#### **16. monthly_transaction_summary** (VIEW)
```
Columns: month, entity, income, expenses, net_flow, transaction_count
Filters: Last 24 months
Purpose: Monthly aggregation by entity
```

#### **17. entity_performance** (VIEW)
```
Columns: entity, total_transactions, total_income, total_expenses, 
         net_position, avg_transaction_size, first_transaction, 
         last_transaction
Purpose: Entity-level performance metrics
```

#### **18. invoice_status_summary** (VIEW)
```
Columns: status, count, total_usd, avg_usd, oldest_invoice, newest_invoice
Purpose: Invoice status distribution and metrics
```

---

## CRITICAL GAPS FOR CHATBOT ENHANCEMENT

### 1. **MISSING: Classification Pattern Management**
```
Current Issue: main.py references 'classification_patterns' table (line 93-96)
               that doesn't exist in postgres_unified_schema.sql

Needed Table Structure:
CREATE TABLE classification_patterns (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL,
    pattern_type VARCHAR(50),  -- 'revenue', 'expense', 'crypto', etc.
    description_pattern TEXT NOT NULL,
    entity VARCHAR(100),
    accounting_category VARCHAR(100),
    confidence_score DECIMAL(5,2),
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    UNIQUE(tenant_id, description_pattern)
);
```

### 2. **MISSING: Investor & Funding Relationships**
```
For chatbot to understand investor flows and financial relationships:

Needed Tables:
- investors (id, name, type, country, investment_focus)
- investments (id, investor_id FK, entity_id FK, amount, currency, date, terms)
- funding_sources (id, source_name, type, contact_info, terms)
- capital_allocation (id, funding_source_id FK, entity_id FK, amount, purpose)
```

### 3. **INCOMPLETE: Business Rules Configuration**
```
Current Issue: Business rules hardcoded in business_knowledge.md markdown file
               Not queryable from database

Needed Tables:
- business_rules (id, tenant_id, rule_type, condition, action, priority, active)
- rule_conditions (id, rule_id FK, field, operator, value)
- rule_actions (id, rule_id FK, category, subcategory, entity)
- rule_feedback (id, rule_id FK, user_id, feedback_type, timestamp)
```

### 4. **INCOMPLETE: User/Session Tracking**
```
Current Issue: user_interactions missing user_id field
               No way to track which user provided feedback

Needed Additions:
ALTER TABLE user_interactions ADD COLUMN user_id VARCHAR(100);
ALTER TABLE user_interactions ADD COLUMN session_id VARCHAR(100);
ALTER TABLE user_interactions ADD COLUMN interaction_type VARCHAR(50);
ALTER TABLE user_interactions ADD COLUMN outcome VARCHAR(50);  -- 'accepted', 'rejected'
ALTER TABLE user_interactions ADD COLUMN confidence_adjustment DECIMAL(3,2);

New Table:
- user_sessions (id, user_id, tenant_id, started_at, ended_at, user_agent)
```

### 5. **MISSING: Vendor/Customer Intelligence**
```
Current Issue: clients table only for crypto invoicing
               No general vendor/customer management

Needed Tables:
- vendors (id, tenant_id, name, type, country, tax_id, 
          payment_terms, quality_score, created_at)
- vendor_interactions (id, vendor_id FK, transaction_id FK, 
                      interaction_type, notes, created_at)
- customer_profiles (id, tenant_id, name, industry, revenue, location)
- transaction_partners (id, tenant_id, partner_name, partner_type, 
                        transaction_count, total_value)
```

### 6. **INCOMPLETE: Pattern Feedback & Versioning**
```
Current Issue: learned_patterns doesn't track what led to the pattern
               No versioning for deprecated patterns

Needed Additions:
ALTER TABLE learned_patterns ADD COLUMN pattern_version INTEGER DEFAULT 1;
ALTER TABLE learned_patterns ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE learned_patterns ADD COLUMN deprecation_reason TEXT;
ALTER TABLE learned_patterns ADD COLUMN deprecation_date TIMESTAMP;

New Table:
- pattern_feedback (id, pattern_id FK, transaction_id FK, feedback_type, 
                   accuracy_score, timestamp)
```

### 7. **MISSING: Multi-Tenant Support in Core Tables**
```
Current Issue: tenant_id added in migration but not in postgres_unified_schema.sql
               Inconsistent tenant support across tables

Required:
- Add tenant_id to: transactions, learned_patterns, user_interactions, 
                    business_entities, crypto_historic_prices
- Update all indexes to include tenant_id as prefix
- Add tenant filtering to all views
```

### 8. **INCOMPLETE: Transaction Categorization Options**
```
Current Issue: categories hardcoded, no flexible category management

Needed Table:
- category_hierarchy (id, tenant_id, parent_category_id FK, 
                     category_name, accounting_code, description, 
                     is_active, created_at)
```

---

## CURRENT PATTERN LEARNING MECHANISMS

### What Works:
1. **learned_patterns table** - Stores patterns with confidence scores
2. **user_interactions table** - Captures user corrections
3. **Triggers** - Automatic timestamp updates via PostgreSQL triggers
4. **Business entities** - Pre-configured known entities

### What's Missing:
1. **No feedback loop** - Patterns aren't updated based on user interactions
2. **No accuracy tracking** - No measurement of pattern effectiveness
3. **No time-decay** - Old patterns never deprecate
4. **No context awareness** - Patterns don't consider transaction context
5. **No pattern relationships** - Can't express pattern combinations
6. **No user attribution** - Can't track whose feedback created patterns

---

## DATABASE MANAGER CAPABILITIES

### What's Implemented:
✓ PostgreSQL connection pooling (minconn=2, maxconn=20)  
✓ Connection retry logic (3 attempts with exponential backoff)  
✓ Transaction management with savepoints  
✓ Batch operations with rollback on error  
✓ Health check endpoint  
✓ Cloud SQL socket support  
✓ Both PostgreSQL and SQLite support (legacy)  

### What's Missing:
- No tenant filtering in base queries
- No query logging/audit trail
- No prepared statement support
- No connection statistics
- No query performance monitoring

---

## SCHEMA RECONCILIATION NEEDED

### Critical Issue:
The project has TWO different PostgreSQL schemas:

**Unified Schema** (`postgres_unified_schema.sql`):
- Modern design with crypto invoice system
- Views for analytics
- System config table
- Triggers for auto-timestamps
- ~15 tables

**Migration Schema** (`migration/postgresql_schema.sql`):
- Legacy transaction-focused design
- Missing crypto system
- Different column names
- References outdated terminology
- ~4-5 tables

### Action Required:
1. Determine which schema is authoritative
2. Migrate all data if switching
3. Update DatabaseManager.init_database() to use correct schema
4. Remove duplicate schema files
5. Add missing tables (classification_patterns, etc.)

---

## RECOMMENDED TABLE ADDITIONS FOR CHATBOT

### Priority 1 (CRITICAL):
1. `classification_patterns` - Fix main.py dependency
2. `transaction_audit_history` - Full transaction change tracking
3. `user_sessions` - Track user context
4. Add `tenant_id` to all core tables

### Priority 2 (HIGH):
1. `business_rules` - Configurable classification logic
2. `investor_relationships` - Financial stakeholder tracking
3. `vendor_profiles` - Vendor intelligence
4. `category_hierarchy` - Flexible categorization

### Priority 3 (MEDIUM):
1. `pattern_feedback` - Pattern accuracy tracking
2. `user_preferences` - User-specific learning
3. `api_audit_log` - API usage tracking
4. `chatbot_interactions` - Chatbot conversation logs

---

## INDEXES SUMMARY

### Well-Indexed Tables:
- transactions (5 indexes)
- invoices (5 indexes)
- payment_transactions (3 indexes)
- crypto_historic_prices (2 indexes)

### Under-Indexed Tables:
- learned_patterns (0 indexes)
- user_interactions (0 indexes)
- business_entities (0 indexes)
- clients (0 indexes)

### Missing Composite Indexes:
- (tenant_id, entity, date) for multi-tenant performance
- (tenant_id, category, date) for aggregations
- (pattern_type, confidence_score) for pattern discovery

---

## SECURITY CONSIDERATIONS

### Current Gaps:
1. No Row Level Security (RLS) enabled - commented out in migration
2. No audit trail on sensitive operations (learned_patterns changes)
3. No encryption for sensitive fields (wallet addresses, api_keys)
4. No data masking for PII
5. Hard-coded credentials in main.py (DB_PASSWORD visible on line 75)

### Required for Production:
1. Enable RLS policies per tenant
2. Add encryption for sensitive columns
3. Remove hardcoded credentials (use environment variables)
4. Implement audit triggers on business_entities, classification_patterns
5. Add data access logging

---

## PERFORMANCE ANALYSIS

### Current Query Patterns:
- Heavy reliance on transaction lookups by date/entity
- Analytics views do full table scans
- No materialized views for expensive aggregations

### Optimization Opportunities:
1. Partition transactions by date (monthly)
2. Partition learned_patterns by pattern_type
3. Add materialized view for pattern effectiveness
4. Consider JSONB indexing for invoice line_items
5. Add statistics for query planner hints

### Connection Pool:
- minconn=2, maxconn=20 is reasonable for Cloud SQL
- Cloud SQL default quota is 100 connections, so current safe

---

## RECOMMENDATIONS FOR CHATBOT DEVELOPMENT

### Immediate Actions:
1. Create `classification_patterns` table (fixes main.py reference)
2. Add `tenant_id` to all core tables
3. Create `transaction_audit_history` for full change tracking
4. Implement user session tracking

### Architectural Improvements:
1. Separate "Learning" tables (patterns, feedback) from "Operations" tables
2. Add soft-delete flags to track deprecated patterns
3. Implement pattern versioning for A/B testing
4. Create "Staging" tables for unconfirmed patterns

### Chatbot-Specific Tables:
1. `chatbot_interactions` - Store all chatbot messages
2. `chatbot_context` - Session context (entity being discussed, etc.)
3. `chatbot_suggestions` - Suggestions made to user
4. `chatbot_feedback` - User feedback on suggestions

---

## DATABASE SIZE ESTIMATES

### Current Production Data (est.):
- transactions: ~10K-100K records
- invoices: ~100-1K records
- learned_patterns: ~100-500 records
- user_interactions: ~1K-10K records

### Projected with Chatbot:
- chatbot_interactions: +1K-10K/month
- pattern_feedback: +10K-100K/year
- transaction_audit_history: +10K-100K/month

### Storage Requirements:
- Current: ~100-500 MB
- Projected (1 year): ~1-5 GB
- No issues with Cloud SQL instance

---

## NEXT STEPS

1. **Review this analysis** with the team
2. **Create database migration plan** for missing tables
3. **Fix schema conflict** between unified and migration schemas
4. **Implement tenant_id** across all tables
5. **Create classification_patterns** table (main.py dependency)
6. **Design chatbot interaction** tables
7. **Update DatabaseManager** with tenant filtering
8. **Add pattern learning** feedback loop

