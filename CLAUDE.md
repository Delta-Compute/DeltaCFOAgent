# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeltaCFOAgent is an AI-powered financial transaction processing and management system that integrates Claude AI for intelligent transaction classification, smart document ingestion, and business intelligence. Delta is the entity that is designing the system for its own use, BUT Delta will market this CFO AI Agent to other companies - so all Claude Code changes and code should be written to work for any user. The project is built for a company with multiple business entities with automated invoice processing, cryptocurrency pricing, and comprehensive financial dashboards and all other CFO corporate responsibilities. Reinforcement learning systems should be put in palce wherever and everywhere users input and provide data on the user's business.

## Development Commands

### Environment Setup
```bash
# Install dependencies (includes all modules)
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Add ANTHROPIC_API_KEY and database credentials
```

### Running the Application
```bash
# Main web dashboard (PostgreSQL)
cd web_ui && python app_db.py
# Access: http://localhost:5001

# Legacy dashboard (CSV-based)
cd web_ui && python app.py
# Access: http://localhost:5002

# Crypto invoice system
cd crypto_invoice_system && python api/invoice_api.py
# Access: http://localhost:5003

# Analytics service
cd services/analytics_service && python app.py
# Access: http://localhost:8080
```

### Testing
```bash
# Manual integration tests (no automated framework exists)
python test_final.py  # Production health checks
python invoice_processing/test_database.py  # Database operations
python invoice_processing/test_full_pipeline.py  # Full pipeline with Flask UI

# Note: No pytest framework currently implemented
```

### Database Operations
```bash
# Create database tables
python create_tables.py

# Apply schema (multiple regional options)
python apply_schema_sa.py  # South America region

# Validate database setup
python validate_simple.py
```

## Architecture Overview

### Core System Architecture
The system follows a modular microservices architecture with three main layers:

1. **Processing Layer**: Smart document ingestion with Claude AI classification
2. **Data Layer**: PostgreSQL-only architecture (production-ready)
3. **Presentation Layer**: Multiple web interfaces for different use cases

### Key Components

**Main Transaction Processing (`main.py`)**
- `DeltaCFOAgent` class: Core transaction classification and processing
- Business knowledge integration from `business_knowledge.md`
- Support for multiple file formats (CSV, bank statements)
- Reinforcement learning from user feedback

**Smart Ingestion System (`smart_ingestion.py`)**
- Claude API integration for document structure analysis
- Automatic format detection and column mapping
- Handles Chase bank formats, standard CSV, and custom formats

**Web Interfaces**
- `web_ui/app_db.py`: Advanced dashboard with database backend
- `web_ui/app.py`: Simple dashboard with CSV backend
- Templates in `web_ui/templates/` with advanced JavaScript interactions

**Specialized Modules**
- `crypto_invoice_system/`: Complete invoice processing with MEXC exchange integration
- `invoice_processing/`: PDF/OCR processing with Claude Vision
- `services/analytics_service/`: Microservice for financial analytics

### Database Architecture

**PostgreSQL-Only Strategy**:
- **All Environments**: PostgreSQL (development and production)
- **Production**: PostgreSQL on Google Cloud SQL
- **Development**: Direct connection to production PostgreSQL instance

**Key Tables**:
- `transactions`: Main transaction records with AI classifications
- `invoices`: Invoice data with vendor information and line items
- `learned_patterns`: Machine learning feedback storage
- `user_interactions`: Reinforcement learning data
- `tenant_configuration`: Company settings, branding, and metadata per tenant
- `wallet_addresses`: Cryptocurrency wallet addresses for transaction classification
- `bank_accounts`: Bank account information for traditional banking integration
- `homepage_content`: Cached AI-generated homepage content with KPIs and insights

**Connection Management**: `DatabaseManager` class in `web_ui/database.py` provides centralized PostgreSQL connectivity for all components.

### AI Integration Patterns

**Claude API Integration**:
- Transaction classification with confidence scoring
- Document structure analysis for smart ingestion
- Business rule application from `business_knowledge.md`
- Vision API for PDF/image processing in invoice module

**Business Classification Rules**:
The system uses a hierarchical classification approach:
1. Exact pattern matching (high confidence)
2. Claude AI classification (medium confidence)
3. Fallback categorization (low confidence)

Business entities and rules are defined in `business_knowledge.md`.

### Deployment Configuration

**Google Cloud Run** (Primary):
- Multi-stage Docker builds (`Dockerfile`)
- Cloud Build integration (`cloudbuild.yaml`)
- Secret Manager for API keys and credentials
- Cloud SQL for production database

**Alternative Deployment**:
- Vercel support via `api/index.py` and `vercel.json`
- Development server with direct PostgreSQL access

### Security Considerations

**Critical Security Notes**:
- API keys must be stored in environment variables or Secret Manager
- Database credentials should never be hardcoded
- All endpoints currently lack authentication (development state)
- File uploads need validation and sanitization

### Module Dependencies

**Core Dependencies**:
- `anthropic`: Claude AI API integration
- `flask`: Web framework for all interfaces
- `pandas`: Data processing and CSV handling
- `psycopg2-binary`: PostgreSQL adapter
- `requests`: External API calls (CoinGecko, MEXC)

**Specialized Dependencies**:
- `PyMuPDF`, `pdfplumber`: PDF processing
- `pytesseract`: OCR functionality
- `exchangelib`: Email automation (invoice processing)
- `qrcode`: QR code generation (crypto invoices)

### AI-Powered Homepage System

**Dynamic Content Generation:**
- `web_ui/services/data_queries.py`: Queries company data, KPIs, entities, and portfolio stats
- `web_ui/services/homepage_generator.py`: Claude AI integration for generating personalized homepage content
- 24-hour smart caching system to minimize API calls
- Fallback content when AI is unavailable

**API Endpoints:**
- `GET /api/homepage/content` - Get cached or fresh AI-generated content
- `POST /api/homepage/regenerate` - Force regeneration with Claude AI
- `GET /api/homepage/data` - Raw data without AI processing
- `GET /api/homepage/kpis` - Just KPI calculations

**Frontend:**
- `/` (business_overview.html) - Dynamic homepage with AI content
- `static/js/homepage.js` - Handles content loading, regeneration, KPI animations
- Animated KPI counters with smart number formatting
- Real-time cache status indicators

### White Listed Accounts Management

**Account Types Supported:**
- Bank Accounts: Checking, savings, credit, investment, loan accounts
- Crypto Wallets: Multi-blockchain support (Ethereum, Bitcoin, Polygon, etc.)

**API Endpoints:**
- Bank Accounts: `GET/POST/PUT/DELETE /api/bank-accounts`
- Crypto Wallets: `GET/POST/PUT/DELETE /api/wallets`

**Frontend:**
- `/whitelisted-accounts` - Two-tab interface for managing accounts
- `static/js/whitelisted_accounts.js` - Full CRUD operations
- Modal forms for add/edit operations
- Color-coded account types and status indicators

### Workforce Management System

**Overview:**
Complete payroll management system for employees and contractors with automated transaction matching. Reuses 80-90% of invoice-transaction matching code for efficient implementation.

**Database Tables:**
- `workforce_members`: Employee and contractor records with compensation details
  - Full name, employment type (employee/contractor), document info
  - Date of hire, termination date, status (active/inactive)
  - Pay rate, pay frequency, currency
  - Contact information (email, phone, address)
  - Job title, department, notes
- `payslips`: Payslip records with payment tracking
  - Payslip number, pay period dates, payment date
  - Gross amount, deductions, net amount
  - Line items (JSONB) for detailed breakdown
  - Payment status (draft/approved/paid)
  - Transaction linking for matching
- `pending_payslip_matches`: Potential transaction matches
  - Payslip-transaction pairs with scoring
  - Match type, confidence level, explanation
  - Status tracking (pending/confirmed/rejected)
- `payslip_match_log`: Audit trail for matching actions
  - All match/unmatch operations logged
  - User ID and timestamp tracking

**Matching Engine (`web_ui/payslip_matcher.py`):**
- `PayslipMatcher` class adapted from `RevenueInvoiceMatcher`
- Filters for NEGATIVE transactions (outgoing payments)
- Matching criteria:
  - Amount matching with 3% tolerance
  - Date proximity scoring (payment date ± days)
  - Employee name detection in transaction descriptions
  - Payroll keyword recognition (salary, wage, payroll, etc.)
  - Claude AI semantic matching support
- Confidence scoring: HIGH (80%+), MEDIUM (55-80%), LOW (<55%)
- Automatic and manual matching workflows

**API Endpoints:**
- Workforce Members: `GET/POST/PUT/DELETE /api/workforce`
- Workforce Member Details: `GET/PUT/DELETE /api/workforce/<id>`
- Payslips: `GET/POST/PUT/DELETE /api/payslips`
- Payslip Details: `GET/PUT/DELETE /api/payslips/<id>`
- Mark Paid: `POST /api/payslips/<id>/mark-paid`
- Transaction Matching:
  - `GET /api/payslips/<id>/find-matching-transactions` - Find matches
  - `POST /api/payslips/<id>/link-transaction` - Manual link
  - `POST /api/payroll/run-matching` - Run automatic matching
  - `GET /api/payroll/matched-pairs` - Get confirmed matches
  - `GET /api/payroll/stats` - Matching statistics

**Frontend:**
- `/workforce` - Two-tab interface (Workforce Members / Payslips)
- `web_ui/templates/workforce.html` - Main page template
- `web_ui/static/js/workforce.js` - Frontend logic and API integration
- `web_ui/static/js/payslip_matches.js` - Transaction matching UI
- Features:
  - Real-time statistics dashboard
  - Search and pagination
  - Create/edit/delete operations
  - Transaction matching modal
  - Status badges and type indicators
  - Auto-calculations (gross - deductions = net)

**Transaction Enrichment:**
When payslip is matched to transaction:
- Category set to "Payroll Expense"
- Subcategory set to "Salary Payment"
- Justification includes: "Payroll payment to [Employee Name] - Payslip #[Number]"
- Match confidence and method tracked

**Migration:**
- SQL: `migrations/add_workforce_tables.sql`
- Python helper: `migrations/apply_workforce_migration.py`
- Run: `python migrations/apply_workforce_migration.py`

**Key Features:**
- Full CRUD for employees and contractors
- Payslip generation with line items and deductions
- Automated transaction matching (reuses invoice matching logic)
- Match confirmation/rejection workflows
- Audit trail for all operations
- Multi-tenant support with tenant_id filtering
- PostgreSQL-only implementation

### Multi-Tenant Architecture

**Tenant Configuration:**
- `tenant_configuration` table stores company settings, branding, and metadata
- Dynamic tenant_id support (currently defaults to 'delta' for development)
- Centralized company name and description management
- Support for custom branding colors and logos

**Tenant Isolation:**
- All queries filtered by tenant_id
- Wallet addresses and bank accounts isolated per tenant
- Homepage content cached per tenant
- Future-ready for multi-client deployment

### Firebase Authentication & User Management

**Authentication Architecture:**
- Firebase Admin SDK for server-side authentication (`auth/firebase_config.py`)
- Firebase Client SDK for frontend authentication (`web_ui/static/js/firebase_client.js`)
- Session-based authentication with Firebase ID tokens
- Multi-tenant user access control

**User Types:**
1. **Fractional CFO** - Creates tenants, manages multiple clients, can create assistants
2. **CFO Assistant** - Supports CFO for specific tenants, invited via email
3. **Tenant Admin** - Business owner with full access, can invite employees and CFOs
4. **Employee** - Internal user with role-based permissions

**Database Tables:**
- `users`: User accounts with Firebase UID integration
- `tenant_users`: User-tenant relationships with roles and permissions (JSONB)
- `user_permissions`: Reference table for available permissions
- `user_invitations`: Email invitation system with token-based acceptance
- `audit_log`: Comprehensive audit trail for all user actions

**Authentication Middleware** (`middleware/auth_middleware.py`):
- `@require_auth`: Requires valid Firebase token
- `@require_role(['admin', 'owner'])`: Requires specific role(s)
- `@require_permission('users.manage')`: Requires specific permission
- `@require_user_type(['fractional_cfo'])`: Requires user type
- `@require_tenant_access`: Validates tenant access
- `@optional_auth`: Works with or without authentication

**Permission System:**
Permissions are stored as JSONB in tenant_users table:
- Transactions: view, create, edit, delete, export
- Invoices: view, create, edit, delete, approve
- Users: view, invite, manage
- Reports: view, generate, export
- Settings: view, edit, billing
- Accounts: view, manage

**Email Service** (`services/email_service.py`):
- SendGrid integration (primary) and SMTP fallback
- User invitation emails with expiry
- Welcome emails for new users
- Admin transfer notifications
- HTML and plain text templates

**Key Business Rules:**
- CFO can create tenants → CFO is initial admin → CFO transfers admin to Tenant Admin
- Tenant ownership tracked by payment: CFO-paid or Tenant-paid
- Tenant Admin can remove CFO only if Tenant owns payment
- If CFO owns payment, Tenant must add payment method before removing CFO
- All user invitations sent via email with 7-day expiry (configurable)

**Migration:**
- Database schema: `migrations/add_auth_tables.sql`
- Migration script: `migrations/apply_auth_migration.py`
- Run: `python migrations/apply_auth_migration.py` (includes --dry-run and --rollback options)

## Key Development Patterns

### Error Handling
The codebase uses a mix of patterns:
- Try-catch with logging for external API calls
- Graceful degradation when AI services are unavailable
- Database transaction rollback for data integrity
- Smart caching with fallback content for critical features

### Configuration Management
- Environment variables for API keys and database credentials
- `business_knowledge.md` for business logic configuration
- Regional deployment configurations for different Cloud SQL instances
- `tenant_configuration` table for per-tenant customization

### File Processing Pipeline
1. File upload and validation
2. Smart format detection (Claude analysis)
3. Data extraction and normalization
4. AI-powered classification
5. Database storage with confidence scoring
6. User feedback integration for learning

### AI Integration Best Practices
- **Caching Strategy**: 24-hour cache for homepage content to reduce API costs
- **Fallback Content**: Always provide basic content when AI is unavailable
- **Prompt Engineering**: Structured prompts with real data for consistent output
- **Error Recovery**: Graceful handling of API failures with user notifications

## Database Guidelines - PostgreSQL Only

### 🚨 CRITICAL: PostgreSQL-Only Policy

**This project has been fully migrated to PostgreSQL. NO NEW SQLite code should be added.**

### Database Development Rules:

1. **Always Use DatabaseManager**: All database access must go through the centralized `DatabaseManager` in `web_ui/database.py`
2. **No Direct SQLite**: Never import `sqlite3` or create new SQLite connections
3. **PostgreSQL Queries**: Write SQL compatible with PostgreSQL syntax
4. **Connection Pooling**: Use the existing connection management - never create direct connections
5. **Schema Updates**: All schema changes must be applied to `postgres_unified_schema.sql`

### Available Database Components:

- **Main System**: Uses `db_manager` from `web_ui/database.py`
- **Crypto Pricing**: Uses `CryptoPricingDB` → `db_manager`
- **Crypto Invoices**: Uses `CryptoInvoiceDatabaseManager` → `db_manager`
- **Analytics**: Uses `AnalyticsEngine` → `db_manager`

### Database Testing:

```bash
# Test PostgreSQL migration
python test_postgresql_migration.py --verbose

# Test specific component
python test_postgresql_migration.py --component=main
```

### Migration Resources:

- **Schema**: `postgres_unified_schema.sql` (unified schema for all components)
- **Data Migration**: `migrate_data_to_postgresql.py` (SQLite → PostgreSQL)
- **Testing**: `test_postgresql_migration.py` (comprehensive validation)
- **Guide**: `POSTGRESQL_MIGRATION_GUIDE.md` (step-by-step instructions)

## Important Notes

- The system is currently in active development with production deployment
- Database schema evolution is managed manually (no formal migration system)
- Business knowledge and classification rules are externalized in markdown files
- Multiple deployment guides exist - prefer `DEPLOYMENT_GUIDE.md` for comprehensive instructions
- Some test files are mixed with production code and should be cleaned up

Claude's Code Rules:
1. First, think about the problem, read the code base for the relevant files, and write a plan in tasks/todo.md.
2. The plan should have a list of tasks that you can mark as complete as you finish them.
3. Before you start working, contact me and I will check the plan.
4. Then start working on the tasks, marking them as complete as you go.
5. Please, every step of the way, just give me a detailed explanation of the changes you've made.
6. Make each task and code change as simple as possible. We want to avoid large or complex changes. Each change should impact as little code as possible. It all comes down to simplicity.
7. Finally, add a review section to the all.md file with a summary of the changes made and any other relevant information.
8. DON'T BE LAZY. NEVER BE LAZY. IF THERE IS A BUG, FIND THE ROOT CAUSE AND FIX IT. NO TEMPORARY FIXES. YOU ARE A SENIOR DEVELOPER. NEVER BE LAZY.
9. MAKE ALL CORRECTIONS AND CODE CHANGES AS SIMPLE AS POSSIBLE. THEY SHOULD ONLY IMPACT THE CODE THAT IS NECESSARY AND RELEVANT TO THE TASK AND NOTHING ELSE. IT SHOULD IMPACT AS LITTLE CODE AS POSSIBLE. YOUR GOAL IS TO NOT INTRODUCE ANY BUGS. IT'S ALL ABOUT SIMPLICITY.
10. Before making a commit, check that there are proper unit tests for your new code, if not write them, add to the Test Suite and include in your commit
11. Do not use emojis in the code