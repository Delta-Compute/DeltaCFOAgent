# Spanish Language & Latin American Currencies Support - Implementation Plan

## Overview
Add Spanish language (es) support and Latin American currencies (ARS, CLP, COP, MXN, PEN, UYU, BOB, VES, PYG) plus ensure Euro (EUR) is consistently supported across the entire application.

## Current State Analysis

### Existing i18n Framework
- **Location**: `web_ui/static/js/i18n.js` (vanilla JS implementation)
- **Translation Files**: `web_ui/static/locales/en.json` (53KB, ~1444 keys) and `pt.json` (58KB)
- **Languages Supported**: English (en), Portuguese (pt-BR)
- **Storage**: localStorage for client preference, database for user preference
- **API Endpoint**: `POST /api/user/language` to save preference
- **DOM Translation**: Uses `data-i18n` attributes

### Current Currency Support
- **Defined in Locales**: USD, EUR, GBP, BRL
- **Used in Code**: USD, BRL, PYG (Paraguay), EUR, GBP
- **In historical_currency_converter.py**: Any currency via external API

---

## Implementation Tasks

### Phase 1: Core i18n Infrastructure Updates

#### Task 1.1: Update i18n.js to Support Spanish
- [ ] Add 'es' to supported languages array (line 101)
- [ ] Load Spanish translations in init() (line 25-28)
- [ ] Add Spanish locale for formatNumber (es-ES or es-419)
- [ ] Add Spanish locale for formatDate
- [ ] Add Spanish currency formatting

**File**: `web_ui/static/js/i18n.js`

#### Task 1.2: Create Spanish Translation File
- [ ] Create `web_ui/static/locales/es.json`
- [ ] Copy structure from en.json
- [ ] Translate all 1444+ keys to Spanish
- [ ] Use Latin American Spanish (es-419) conventions

**New File**: `web_ui/static/locales/es.json`

#### Task 1.3: Update Database Migration
- [ ] Update `add_language_preferences.sql` to include 'es' in CHECK constraint
- [ ] Create new migration file `add_spanish_language.sql`
- [ ] Update both `users` and `tenant_configuration` tables

**Files**:
- `migrations/add_spanish_language.sql` (new)
- `migrations/apply_spanish_language_migration.py` (new)

#### Task 1.4: Update Language Switcher UI
- [ ] Add Spanish option to `_navbar.html` language dropdown
- [ ] Add Spanish flag emoji or icon
- [ ] Update click handlers

**File**: `web_ui/templates/_navbar.html`

---

### Phase 2: Currency Support Expansion

#### Task 2.1: Add Latin American Currencies to Locales
Update all three locale files (en.json, pt.json, es.json) with:
- [ ] ARS - Argentine Peso
- [ ] CLP - Chilean Peso
- [ ] COP - Colombian Peso
- [ ] MXN - Mexican Peso
- [ ] PEN - Peruvian Nuevo Sol
- [ ] UYU - Uruguayan Peso
- [ ] BOB - Bolivian Boliviano
- [ ] VES - Venezuelan Bolivar
- [ ] PYG - Paraguayan Guarani (already exists in code)

**Files**:
- `web_ui/static/locales/en.json`
- `web_ui/static/locales/pt.json`
- `web_ui/static/locales/es.json`

#### Task 2.2: Update Currency Formatting in i18n.js
- [ ] Add currency symbol map for all currencies
- [ ] Add formatCurrencyWithCode(amount, currencyCode) method
- [ ] Handle different decimal places (e.g., CLP has 0 decimals)

**File**: `web_ui/static/js/i18n.js`

#### Task 2.3: Update Backend Currency Validation
- [ ] Update currency validation in `app_db.py` (line ~9665)
- [ ] Add all new currencies to allowed list
- [ ] Update invoice form currency dropdown

**Files**:
- `web_ui/app_db.py`
- `invoice_processing/improved_visual_system.py` (if still used)

---

### Phase 3: Template Translation Gaps

The following templates have ZERO i18n implementation and need data-i18n attributes added:

#### Task 3.1: Core Dashboard Templates
- [ ] `dashboard.html` - All filter labels, table headers, buttons
- [ ] `files.html` - Upload sections, progress text, file table

#### Task 3.2: Workforce Templates
- [ ] `workforce.html` - Tabs, table headers, form labels, modals

#### Task 3.3: Invoice Templates
- [ ] `invoice_detail.html` - All labels, buttons, sidebar
- [ ] `create_invoice.html` - All form fields, dropdowns, buttons
- [ ] `invoices.html` (if not already covered)

#### Task 3.4: Authentication Templates
- [ ] `auth/login.html` - Form labels, buttons, links
- [ ] `auth/register.html` - Form labels, user type options, buttons
- [ ] `auth/profile.html` - All labels and info sections
- [ ] `auth/accept_invitation.html` - All text and buttons
- [ ] `auth/forgot_password.html` - Form labels and buttons

#### Task 3.5: Management Templates
- [ ] `users.html` - All invitation forms and labels
- [ ] `whitelisted_accounts.html` - Tabs, forms, card labels
- [ ] `transaction_detail.html` - All labels and buttons
- [ ] `payslip_detail.html` - All labels and sections
- [ ] `shareholders.html` - All form labels

#### Task 3.6: Other Templates
- [ ] `business_overview.html` - Bot interface, loading states
- [ ] `tenant_management.html` - Forms and labels

---

### Phase 4: JavaScript Hardcoded Strings

#### Task 4.1: tenant_knowledge.js (~83 instances)
- [ ] Replace all alert() messages with i18n.t() calls
- [ ] Replace all confirm() messages with i18n.t() calls
- [ ] Replace innerHTML loading/empty states with translations
- [ ] Add translation keys to es.json

#### Task 4.2: script_advanced.js (~70 instances)
- [ ] Replace confirm dialogs
- [ ] Replace showNotification messages
- [ ] Replace innerHTML content
- [ ] Replace placeholder text

#### Task 4.3: workforce.js (~16 instances)
- [ ] Replace alert messages
- [ ] Replace confirm dialogs
- [ ] Replace modal titles

#### Task 4.4: invoice_*.js files
- [ ] invoice_matches.js (~3 instances)
- [ ] invoice_attachments.js (~12 instances)
- [ ] invoice_payments.js (~11 instances)
- [ ] invoice_detail.js (~5 instances)

#### Task 4.5: payslip_*.js files
- [ ] payslip_detail.js (~7 instances)
- [ ] payslip_matches.js (~4 instances)

#### Task 4.6: Other JS files
- [ ] transaction_detail.js (~5 instances)
- [ ] auth.js (~12 instances)
- [ ] homepage.js (~7 instances)
- [ ] payment_receipts.js (~8 instances)
- [ ] whitelisted_accounts.js (~5 instances)
- [ ] shareholders.js (~7 instances)
- [ ] tenant_management.js (~4 instances)
- [ ] cfo_dashboard.js (~15 instances - NOTE: has mixed EN/PT)
- [ ] activity_timeline.js (~1 instance)
- [ ] pattern_notifications.js (~3 instances)

---

### Phase 5: Translation Keys to Add

#### Task 5.1: New Top-Level Sections for es.json
Based on the analysis, add these translation key sections:
- [ ] `currencies` - All currency names and symbols
- [ ] `errors` - All error messages
- [ ] `confirmations` - All confirmation dialogs
- [ ] `notifications` - All toast/notification messages
- [ ] `loading` - All loading states
- [ ] `empty` - All empty state messages

#### Task 5.2: Update en.json with Missing Keys
- [ ] Add all hardcoded strings found in JS files
- [ ] Add all hardcoded strings found in templates
- [ ] Maintain consistent key naming convention

#### Task 5.3: Update pt.json with Missing Keys
- [ ] Mirror all new keys from en.json
- [ ] Translate to Portuguese

---

### Phase 6: Testing & Validation

#### Task 6.1: Unit Tests
- [ ] Test language switching works for all 3 languages
- [ ] Test currency formatting for all currencies
- [ ] Test all translation keys exist in all locales

#### Task 6.2: Manual Testing Checklist
- [ ] Switch to Spanish, verify all pages render correctly
- [ ] Switch to Portuguese, verify no regressions
- [ ] Switch to English, verify no regressions
- [ ] Test all currency dropdowns show new currencies
- [ ] Test currency formatting displays correctly
- [ ] Test date formatting for each locale
- [ ] Test number formatting for each locale

#### Task 6.3: Translation Validation Script
- [ ] Create script to compare keys between en.json, pt.json, es.json
- [ ] Report missing translations
- [ ] Report unused translation keys

---

## File Change Summary

### New Files to Create
1. `web_ui/static/locales/es.json` - Spanish translations (~1500 keys)
2. `migrations/add_spanish_language.sql` - Database migration
3. `migrations/apply_spanish_language_migration.py` - Migration script
4. `tests/test_i18n.py` - Translation tests

### Files to Modify

**Core i18n:**
- `web_ui/static/js/i18n.js` - Add Spanish support, currency formatting

**Locale Files:**
- `web_ui/static/locales/en.json` - Add missing keys, currencies
- `web_ui/static/locales/pt.json` - Add missing keys, currencies

**Templates (add data-i18n attributes):**
- `web_ui/templates/_navbar.html` - Language switcher
- `web_ui/templates/dashboard.html`
- `web_ui/templates/files.html`
- `web_ui/templates/workforce.html`
- `web_ui/templates/invoice_detail.html`
- `web_ui/templates/create_invoice.html`
- `web_ui/templates/transaction_detail.html`
- `web_ui/templates/payslip_detail.html`
- `web_ui/templates/whitelisted_accounts.html`
- `web_ui/templates/shareholders.html`
- `web_ui/templates/business_overview.html`
- `web_ui/templates/users.html`
- `web_ui/templates/tenant_management.html`
- `web_ui/templates/auth/login.html`
- `web_ui/templates/auth/register.html`
- `web_ui/templates/auth/profile.html`
- `web_ui/templates/auth/accept_invitation.html`
- `web_ui/templates/auth/forgot_password.html`

**JavaScript (replace hardcoded strings):**
- `web_ui/static/js/tenant_knowledge.js`
- `web_ui/static/js/workforce.js`
- `web_ui/static/js/invoice_matches.js`
- `web_ui/static/js/invoice_attachments.js`
- `web_ui/static/js/invoice_payments.js`
- `web_ui/static/js/invoice_detail.js`
- `web_ui/static/js/payslip_detail.js`
- `web_ui/static/js/payslip_matches.js`
- `web_ui/static/js/transaction_detail.js`
- `web_ui/static/js/auth.js`
- `web_ui/static/js/homepage.js`
- `web_ui/static/js/payment_receipts.js`
- `web_ui/static/js/whitelisted_accounts.js`
- `web_ui/static/js/shareholders.js`
- `web_ui/static/js/tenant_management.js`
- `web_ui/static/js/activity_timeline.js`
- `web_ui/static/js/pattern_notifications.js`
- `web_ui/static/script_advanced.js`
- `web_ui/static/cfo_dashboard.js`

**Backend:**
- `web_ui/app_db.py` - Currency validation

---

## Currencies Reference

| Code | Name (English) | Name (Spanish) | Name (Portuguese) | Symbol | Decimals |
|------|----------------|----------------|-------------------|--------|----------|
| USD | US Dollar | Dolar estadounidense | Dolar Americano | $ | 2 |
| EUR | Euro | Euro | Euro | E | 2 |
| GBP | British Pound | Libra esterlina | Libra Esterlina | GBP | 2 |
| BRL | Brazilian Real | Real brasileno | Real Brasileiro | R$ | 2 |
| ARS | Argentine Peso | Peso argentino | Peso Argentino | $ | 2 |
| CLP | Chilean Peso | Peso chileno | Peso Chileno | $ | 0 |
| COP | Colombian Peso | Peso colombiano | Peso Colombiano | $ | 0 |
| MXN | Mexican Peso | Peso mexicano | Peso Mexicano | $ | 2 |
| PEN | Peruvian Sol | Sol peruano | Sol Peruano | S/ | 2 |
| UYU | Uruguayan Peso | Peso uruguayo | Peso Uruguaio | $U | 2 |
| BOB | Bolivian Boliviano | Boliviano | Boliviano | Bs | 2 |
| VES | Venezuelan Bolivar | Bolivar venezolano | Bolivar Venezuelano | Bs.S | 2 |
| PYG | Paraguayan Guarani | Guarani paraguayo | Guarani Paraguaio | Gs | 0 |

---

## Estimation

### Translation Work
- ~1444 keys to translate to Spanish
- ~200+ new keys to add for hardcoded strings
- Total: ~1650 translation keys for Spanish

### Code Changes
- 1 new locale file
- 2 migration files
- ~20 template files with data-i18n additions
- ~20 JavaScript files with string replacements
- 1 backend file update

---

## Success Criteria

- [ ] Spanish language option appears in language switcher
- [ ] All UI text displays correctly in Spanish
- [ ] All Latin American currencies available in dropdowns
- [ ] Currency formatting respects locale (decimal separators)
- [ ] Date formatting respects locale
- [ ] Number formatting respects locale
- [ ] No console errors when switching languages
- [ ] All existing English/Portuguese functionality works
- [ ] Database migration runs without errors
- [ ] All translation keys exist in all 3 locale files

---

## Review Section

### Phase 1 & 2 - COMPLETED (Nov 2024)
- Created es.json with full Spanish translations (~1500 keys)
- Updated i18n.js to support Spanish language and Latin American currencies
- Added all Latin American currencies (ARS, CLP, COP, MXN, PEN, UYU, BOB, VES, PYG)
- Updated _navbar.html with Spanish language option
- Database migration files created

### Phase 3 - IN PROGRESS (Nov 2024)

#### Completed Template Updates:
- [x] `files.html` - Added data-i18n attributes to upload sections, progress text, file tables, status badges
- [x] `workforce.html` - Added data-i18n to stats, tabs, table headers, modals, form labels
- [x] `invoices.html` - Added data-i18n to stats, filters, table headers, selection toolbar

#### Remaining Template Updates:
- [ ] `auth/login.html` - Form labels, buttons, links
- [ ] `auth/register.html` - Form labels, buttons
- [ ] `auth/forgot_password.html` - Form labels, buttons
- [ ] `invoice_detail.html` - Labels, buttons
- [ ] `create_invoice.html` - Form fields
- [ ] `business_overview.html` - Loading states
- [ ] `revenue.html` - Stats, controls
- [ ] `expenses.html` - Stats, filters

### Issues Encountered
- Auth templates don't include i18n.js and have no translation keys (needs separate auth section in locales)
- Some templates are very large (invoices.html ~28k tokens)

### Notes
- All translation keys for Phase 3 templates already exist in locale files (added in Phase 1)
- The i18n system loads automatically via _navbar.html which is included in most templates
- Auth templates may need special handling since they don't include the navbar
