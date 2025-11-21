# Example Business Knowledge Files

This directory contains **historical example files** for reference and documentation purposes only.

## ⚠️ IMPORTANT: These files are NOT used in production

### delta_business_knowledge_EXAMPLE.md

This file contains Delta's original business classification patterns from when the system was single-tenant.

**Status:** DEPRECATED - For reference only

**Why deprecated:**
- The multi-tenant SaaS architecture stores all classification patterns in the PostgreSQL database (`classification_patterns` table)
- Each tenant has their own patterns filtered by `tenant_id`
- Using a shared file would leak Delta's business patterns to all tenants (security risk)
- File-based fallback was removed in favor of fail-fast database-only approach

**Production Pattern Storage:**
- All patterns stored in: `classification_patterns` table with `tenant_id` column
- Loaded via: `main.py:106-111` (database query)
- Managed via: Web UI Knowledge page (`/tenant-knowledge`)

**For New Tenants:**
- Industry-specific pattern templates will be created in the database
- Onboarding flow copies appropriate templates based on tenant's industry
- Tenants build custom patterns through the web UI

**Historical Context:**
This file represents Delta's business structure with:
- Multiple business entities (Delta LLC, Delta Prop Shop, Infinity Validator, etc.)
- Crypto mining and trading operations
- Paraguay/Brazil regional operations

These are specific to Delta's business and should NOT be used as a generic template.
