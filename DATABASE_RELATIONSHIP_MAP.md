# DeltaCFOAgent Database Relationship Map

## Current Database Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TRANSACTION CORE                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐      ┌──────────────────────┐                 │
│  │  transactions    │      │  learned_patterns    │                 │
│  │  (Primary Data)  │      │  (Pattern Learning)  │                 │
│  ├──────────────────┤      ├──────────────────────┤                 │
│  │ id (PK)          │      │ id (PK)              │                 │
│  │ date             │◄─────│ description_pattern  │                 │
│  │ description      │      │ suggested_category   │                 │
│  │ amount           │      │ suggested_entity     │                 │
│  │ category         │      │ confidence_score     │                 │
│  │ entity           │      │ usage_count          │                 │
│  │ confidence       │      │ created_at/updated_at│                 │
│  │ created_at       │      └──────────────────────┘                 │
│  └────────┬─────────┘              ▲                                 │
│           │                        │                                 │
│           └────────────────────────┘                                 │
│           (Pattern matches transaction)                              │
│                                                                       │
│  ┌──────────────────┐      ┌──────────────────────┐                 │
│  │ user_interactions│      │ business_entities    │                 │
│  │ (User Feedback)  │      │ (Known Entities)     │                 │
│  ├──────────────────┤      ├──────────────────────┤                 │
│  │ id (PK)          │      │ id (PK)              │                 │
│  │ transaction_id --┼─────►│ name (UNIQUE)        │                 │
│  │ (FK)             │      │ description          │                 │
│  │ original_category│      │ entity_type          │                 │
│  │ user_category    │      │ active               │                 │
│  │ feedback_type    │      │ created_at           │                 │
│  └──────────────────┘      └──────────────────────┘                 │
│                                                                       │
│  *** CRITICAL MISSING: classification_patterns table ***             │
│      (main.py line 93 references non-existent table)                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                        CRYPTO INVOICE SYSTEM                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐      ┌──────────────────────┐                 │
│  │    invoices      │      │      clients         │                 │
│  │   (Main Invoices)│      │    (Bill Targets)    │                 │
│  ├──────────────────┤      ├──────────────────────┤                 │
│  │ id (PK)          │      │ id (PK)              │                 │
│  │ invoice_number   │      │ name                 │                 │
│  │ client_id -------┼─────►│ contact_email        │                 │
│  │ (FK)             │      │ billing_address      │                 │
│  │ status           │      │ tax_id               │                 │
│  │ amount_usd       │      │ created_at           │                 │
│  │ crypto_currency  │      └──────────────────────┘                 │
│  │ crypto_amount    │                                               │
│  │ crypto_network   │                                               │
│  │ exchange_rate    │                                               │
│  │ deposit_address  │                                               │
│  │ due_date         │                                               │
│  │ paid_at          │                                               │
│  └─────────┬────────┘                                               │
│            │                                                         │
│  ┌─────────▼─────────┐                                              │
│  │payment_transactions                                              │
│  │(Crypto Payments)  │                                              │
│  ├─────────────────────┤                                            │
│  │id (PK)              │                                            │
│  │invoice_id ──────────┼──── References invoices(id)               │
│  │(FK)                 │                                            │
│  │transaction_hash     │                                            │
│  │amount_received      │                                            │
│  │currency             │                                            │
│  │network              │                                            │
│  │status               │                                            │
│  │confirmations        │                                            │
│  │detected_at          │                                            │
│  │confirmed_at         │                                            │
│  └─────────────────────┘                                            │
│                                                                       │
│  ┌─────────────────────┐    ┌──────────────────────┐                │
│  │  mexc_addresses     │    │   address_usage      │                │
│  │  (Address Cache)    │    │  (Address Tracking)  │                │
│  ├─────────────────────┤    ├──────────────────────┤                │
│  │ id (PK)             │    │ id (PK)              │                │
│  │ currency            │    │ address              │                │
│  │ network             │    │ invoice_id ──────────┼─┐              │
│  │ address             │    │ (FK)                 │ │              │
│  │ is_primary          │    │ used_at              │ │              │
│  │ last_used_at        │    └──────────────────────┘ │              │
│  └─────────────────────┘                              │              │
│                                                        │              │
│  ┌──────────────────────────┬─────────────────────────┘              │
│  │                          │                                         │
│  │  ┌─────────────────┐     │                                        │
│  │  │polling_logs     │     │                                        │
│  │  │(Operation Logs) │     │                                        │
│  │  ├─────────────────┤     │                                        │
│  │  │id (PK)          │     │                                        │
│  │  │invoice_id ──────┼─────┘                                        │
│  │  │(FK)             │                                              │
│  │  │status           │                                              │
│  │  │deposits_found   │                                              │
│  │  │created_at       │                                              │
│  │  └─────────────────┘                                              │
│  │                                                                    │
│  │  ┌──────────────────────┐                                         │
│  │  │notifications        │                                         │
│  │  │(Email Tracking)     │                                         │
│  │  ├──────────────────────┤                                         │
│  │  │id (PK)               │                                         │
│  │  │invoice_id ───────────┼─── References invoices(id)             │
│  │  │(FK)                  │                                         │
│  │  │notification_type    │                                         │
│  │  │recipient_email      │                                         │
│  │  │subject              │                                         │
│  │  │sent_at              │                                         │
│  │  │status               │                                         │
│  │  └──────────────────────┘                                         │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                          CONFIGURATION & HISTORY                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐      ┌──────────────────────┐                 │
│  │  system_config   │      │crypto_historic_prices                  │
│  │  (Settings)      │      │  (Crypto Prices)     │                 │
│  ├──────────────────┤      ├──────────────────────┤                 │
│  │ key (PK)         │      │ date, symbol (PK)    │                 │
│  │ value            │      │ price_usd            │                 │
│  │ description      │      │ created_at           │                 │
│  │ updated_at       │      └──────────────────────┘                 │
│  └──────────────────┘                                               │
│                                                                       │
│  ┌──────────────────────────────┐ (Only in migration schema,         │
│  │  transaction_history         │  NOT in unified schema)            │
│  │  (Audit Trail - MISSING!)    │                                    │
│  ├──────────────────────────────┤                                    │
│  │id (PK)                       │                                    │
│  │transaction_id ────┐          │                                    │
│  │(FK)               │ ◄─────── References transactions(id)         │
│  │field_name         │                                              │
│  │old_value          │                                              │
│  │new_value          │                                              │
│  │changed_by         │                                              │
│  │changed_at         │                                              │
│  │change_reason      │                                              │
│  └──────────────────────────────┘                                    │
│                                                                       │
│  ┌──────────────────────────────┐ (NEW - wallet_addresses migration) │
│  │  wallet_addresses            │                                    │
│  │  (Crypto Wallet Classification)                                   │
│  ├──────────────────────────────┤                                    │
│  │id (UUID PK)                  │                                    │
│  │tenant_id                     │                                    │
│  │wallet_address                │                                    │
│  │entity_name                   │                                    │
│  │wallet_type                   │                                    │
│  │confidence_score              │                                    │
│  │created_at/updated_at         │                                    │
│  └──────────────────────────────┘                                    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Critical Gaps & Missing Relationships

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MISSING FOR CHATBOT (NOT IN DB)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────┐     ┌──────────────────────┐              │
│  │classification       │     │ investor_           │              │
│  │_patterns (MISSING!) │     │relationships (MISSING)              │
│  ├──────────────────────┤     ├──────────────────────┤              │
│  │id (PK)               │     │id (PK)               │              │
│  │pattern_type          │     │investor_id (FK)      │              │
│  │description_pattern   │     │entity_id (FK)        │              │
│  │entity                │     │amount                │              │
│  │accounting_category   │     │investment_date       │              │
│  │confidence_score      │     │terms                 │              │
│  │usage_count           │     └──────────────────────┘              │
│  └──────────────────────┘                   ▲                      │
│         * REFERENCED BY main.py             │                      │
│           but doesn't exist!                │                      │
│                                             │                      │
│  ┌──────────────────────┐     ┌─────────────┴──────────┐           │
│  │user_sessions        │     │  investors (MISSING)   │           │
│  │(MISSING SESSION   │     │  (Investor Master)   │           │
│  │TRACKING!)          │     ├────────────────────────┤           │
│  ├──────────────────────┤     │id (PK)                 │           │
│  │id (PK)               │     │name                    │           │
│  │user_id               │     │type                    │           │
│  │tenant_id             │     │country                 │           │
│  │started_at            │     │investment_focus        │           │
│  │ended_at              │     └────────────────────────┘           │
│  │user_agent            │                                          │
│  └──────────────────────┘                                          │
│                                                                     │
│  ┌──────────────────────┐     ┌──────────────────────┐             │
│  │business_rules       │     │ vendor_profiles      │             │
│  │(HARDCODED IN MD!)   │     │  (MISSING)           │             │
│  ├──────────────────────┤     ├──────────────────────┤             │
│  │id (PK)               │     │id (PK)               │             │
│  │rule_type             │     │tenant_id             │             │
│  │condition             │     │name                  │             │
│  │action                │     │type                  │             │
│  │priority              │     │country               │             │
│  │active                │     │payment_terms         │             │
│  └──────────────────────┘     │quality_score         │             │
│         * Stored in MD file,   └──────────────────────┘             │
│           not queryable                                             │
│                                                                     │
│  ┌──────────────────────┐     ┌──────────────────────┐             │
│  │chatbot_interactions │     │ pattern_feedback     │             │
│  │(CHATBOT SPECIFIC!)   │     │(MISSING FEEDBACK!)   │             │
│  ├──────────────────────┤     ├──────────────────────┤             │
│  │id (PK)               │     │id (PK)               │             │
│  │session_id (FK)       │     │pattern_id (FK)       │             │
│  │user_message          │     │transaction_id (FK)   │             │
│  │chatbot_response      │     │feedback_type         │             │
│  │intent                │     │accuracy_score        │             │
│  │sentiment             │     │timestamp             │             │
│  │timestamp             │     └──────────────────────┘             │
│  └──────────────────────┘                                          │
│                                                                     │
│  ┌──────────────────────────────┐  ┌────────────────────────┐      │
│  │ category_hierarchy           │  │ transaction_audit_     │      │
│  │ (FLEXIBLE CATEGORIES)        │  │history (FULL AUDIT)    │      │
│  ├──────────────────────────────┤  ├────────────────────────┤      │
│  │ id (PK)                      │  │ id (PK)                │      │
│  │ parent_category_id (FK)      │  │ transaction_id (FK)    │      │
│  │ category_name                │  │ user_id                │      │
│  │ accounting_code              │  │ action (INSERT/UPDATE) │      │
│  │ is_active                    │  │ timestamp              │      │
│  └──────────────────────────────┘  │ details (JSONB)        │      │
│                                     └────────────────────────┘      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Current vs. Needed Data Model

### TODAY'S FLOW:
```
Transaction CSV
    ↓
main.py loads it
    ↓
Searches in business_knowledge.md (hardcoded rules)
    ↓
Uses learned_patterns table (if matches)
    ↓
Classifies with Claude AI (if needed)
    ↓
Stores in transactions table
    ↓
User sees classification
    ↓
User corrects it → user_interactions table
    ↓
❌ No feedback loop back to learned_patterns!
    ↓
Next transaction: No improvement, same process
```

### NEEDED FLOW FOR CHATBOT:
```
User asks chatbot about transactions
    ↓
Chatbot queries transactions (with context)
    ↓
Chatbot queries learned_patterns for hints
    ↓
✓ Chatbot queries classification_patterns (missing!)
    ↓
✓ Chatbot queries business_rules from DB (not hardcoded!)
    ↓
✓ Chatbot queries investor_relationships (for context)
    ↓
✓ Chatbot queries vendor_profiles (for insights)
    ↓
Chatbot generates response with confidence
    ↓
User confirms/corrects → chatbot_interactions
    ↓
✓ Feedback stored in pattern_feedback table
    ↓
✓ Transaction audit trail created
    ↓
✓ Learned patterns updated with confidence
    ↓
Next query: System is smarter, fewer corrections needed
```

---

## Multi-Tenant Architecture Status

### Current State:
- `wallet_addresses` table HAS tenant_id ✓
- `transactions` missing tenant_id ✗
- `learned_patterns` missing tenant_id ✗
- `user_interactions` missing user_id and session tracking ✗
- `business_entities` missing tenant_id ✗
- Migration file added tenant_id infrastructure but not in unified schema

### Required for Multi-Tenant Chatbot:
```
Every table should have:
├── tenant_id (for data isolation)
├── created_by user_id (for audit)
├── created_at timestamp (for tracking)
└── updated_at timestamp (for sorting)

Specifically for chatbot:
├── chatbot_interactions.user_id
├── chatbot_interactions.tenant_id
├── chatbot_interactions.session_id
├── pattern_feedback.user_id
├── user_sessions.user_id + session_id
└── all views filtered by tenant_id
```

---

## Schema Inconsistencies Summary

| Component | Unified Schema | Migration Schema | Status |
|-----------|---|---|---|
| transactions | ✓ (11 columns) | ✓ (15 columns) | CONFLICT: Different columns |
| invoices | ✓ (20 columns) | ✓ (21 columns) | CONFLICT: Different structure |
| user_interactions | ✓ | ✗ | Unified only |
| learned_patterns | ✓ | ✗ | Unified only |
| transaction_history | ✗ | ✓ | Migration only |
| wallet_addresses | ✗ | ✓ | Migration only |
| crypto_historic_prices | ✓ | ✗ | Unified only |
| system_config | ✓ | ✗ | Unified only |
| classification_patterns | ✗ | ✗ | **MISSING** (but referenced!) |
| investors | ✗ | ✗ | **MISSING** |
| business_rules | ✗ | ✗ | **MISSING** (hardcoded in MD) |

