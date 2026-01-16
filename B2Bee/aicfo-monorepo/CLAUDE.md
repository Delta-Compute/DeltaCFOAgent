# CLAUDE.md

## Session Scope

### This Session Owns
- Flask web app (web_ui/)
- Next.js frontend (frontend/)
- Crypto invoice system
- Transaction processing
- AI classification/ingestion
- Workforce management
- Sidebar component (frontend/src/components/sidebar/) - NOT shared, this is AICFO's copy

### Redirect To
- B2Bee Global → Stripe billing, aicfo.b2bee.tech landing page, shared nav
- Scout → If lead/CRM related

### Cross-Session Protocol
If a request spans multiple domains:
1. Identify which parts belong to this session
2. Complete work within this session's scope
3. Tell the user: "The [X] portion should be done in the B2Bee Global terminal" or "The [X] portion should be done in the Scout terminal"

---

## Links
- GitHub: https://github.com/Delta-Compute/aicfo-monorepo
- App: https://deltacfo-app.vercel.app
- Landing: https://aicfo.b2bee.tech
- Vercel Project: deltacfo-app

---

## B2Bee Ecosystem Standards

### Authentication (CRITICAL)
- ALL B2Bee products use Firebase Auth (project: aicfo-473816)
- NEVER create separate auth systems
- Google Sign-In required for all products

### Multi-Tenancy
- Every data model requires tenantId
- All queries MUST filter by tenant

### Payments
- Stripe integration owned by B2Bee Global
- Individual products call shared Stripe utilities
- Do NOT implement product-specific payment logic

### 🚨 CRITICAL: Database Safety

**ALL B2Bee products learned from the SignupCode data loss incident (Jan 15, 2026).**

**Before ANY database schema change:**
1. ✅ Backup database: `pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql`
2. ✅ **ALWAYS use migrations**: `npx prisma migrate dev --name change_description`
3. ✅ **NEVER use `prisma db push`** without backup and explicit approval
4. ✅ Test on staging database first
5. ✅ Verify if this database is shared with other apps

**What happened:** `prisma db push` wiped ALL signup codes in marketing-monorepo's shared database, affecting Scout, EmailAgent, SocialAgent, and Sales-Ops. Zero codes remain.

**Safe practices:**
- Use migrations for all schema changes
- Backup before ANY database operation
- Test on local/staging first
- Never use `--accept-data-loss` flag

---

## Commit Standards

### Commit Message Format
[PRODUCT] type: description

Product tags:
- [BUMBLEBEE-DESKTOP]
- [BUMBLEBEE-MOBILE]
- [AICFO]
- [SCOUT]
- [EMAILAGENT]
- [SOCIALAGENT]
- [B2BEE-GLOBAL]
- [B2BEE-GLOBAL-XREPO] (for cross-product fixes from B2Bee Global)

Types: feat, fix, refactor, docs, style, test, chore

### Before Committing
1. `git pull origin main` - always pull latest
2. `git status` - confirm only expected files changed
3. Check for changes in shared files (see below)

### Shared File Protocol
If modifying any of these files, STOP and notify user:
- prisma/schema.prisma
- package.json (dependency changes)
- .env.example
- Any file in packages/ (marketing-monorepo)
- Firebase config
- Stripe config

Tell user: "This change touches [file] which affects [other products]. Confirm before committing."

### Migration Protocol
1. Never auto-run migrations
2. Notify user before committing migration files
3. For marketing-monorepo: migrations affect Scout, EmailAgent, SocialAgent simultaneously

---

## Project Overview

AICFO is an AI-powered financial transaction processing and management system that integrates Claude AI for:
- Intelligent transaction classification
- Smart document ingestion
- Business intelligence
- Invoice management with transaction matching
- Cryptocurrency pricing integration
- Workforce/payroll management

## Development Commands

### Running the Application
```bash
# Main web dashboard (PostgreSQL)
cd web_ui && python app_db.py
# Access: http://localhost:5001

# Crypto invoice system
cd crypto_invoice_system && python api/invoice_api.py
# Access: http://localhost:5003

# Analytics service
cd services/analytics_service && python app.py
# Access: http://localhost:8080
```

### Database Operations
```bash
# Apply unified schema
psql -h <host> -U <user> -d <database> -f postgres_unified_schema.sql

# Validate database setup
python validate_simple.py
```

## Architecture

### Core Components
- **web_ui/app_db.py** - Main Flask dashboard with PostgreSQL backend
- **frontend/** - Next.js frontend application
- **crypto_invoice_system/** - Invoice processing with MEXC integration
- **invoice_processing/** - PDF/OCR processing with Claude Vision
- **services/analytics_service/** - Financial analytics microservice

### Key Design Patterns
- PostgreSQL-only database strategy
- Multi-tenant architecture with tenant_id isolation
- AI-powered transaction classification with reinforcement learning
- Smart document ingestion with Claude API

## Tech Stack
- **Backend:** Python/Flask, FastAPI
- **Frontend:** Next.js, React
- **Database:** PostgreSQL (Cloud SQL in production)
- **AI:** Claude API (Anthropic)
- **Auth:** Firebase Authentication
- **Deployment:** GCP Cloud Run

## Environment Variables

```bash
DATABASE_URL="postgresql://..."
ANTHROPIC_API_KEY="sk-ant-..."
FIREBASE_PROJECT_ID="aicfo-473816"
```
