# B2Bee Ecosystem

## Multi-Agent Development Environment

This project runs 7 concurrent Claude Code sessions:

| Session | Directory | Scope |
|---------|-----------|-------|
| BumbleBee Desktop | bumblebee-monorepo/ | Dashboard, desktop agents, backend |
| BumbleBee Mobile | bumblebee-monorepo/apps/mobile/ | iOS/Android Expo app |
| AICFO | aicfo-monorepo/ | AI CFO product |
| Scout | marketing-monorepo/apps/scout/ | LeadScout CRM |
| EmailAgent | marketing-monorepo/apps/email/ | Email automation |
| SocialAgent | marketing-monorepo/apps/meta/ | Social media automation |
| B2Bee Global | b2bee-landing/ | Homepage, Stripe, marketing, cross-product UI |

## High-Risk Shared Files

Changes to these affect multiple products - coordinate before committing:

| File | Affects |
|------|---------|
| marketing-monorepo/packages/* | Scout, EmailAgent, SocialAgent |
| marketing-monorepo/prisma/schema.prisma | Scout, EmailAgent, SocialAgent |
| Firebase config | All products |
| Stripe webhooks | All products with billing |

## 🚨 CRITICAL: Shared Database Safety

### NEVER run `prisma db push` on shared databases

**All signup codes were wiped on Jan 15, 2026** when `prisma db push` was executed during schema changes in marketing-monorepo.

### Shared Databases Across B2Bee

- **marketing-monorepo**: Scout, EmailAgent, SocialAgent, Sales-Ops share ONE PostgreSQL database
- **Other monorepos**: Verify if apps share databases before schema changes

**Schema change in ONE app affects ALL apps sharing that database!**

### Safe Database Operations

**ALWAYS use migrations:**
```bash
npx prisma migrate dev --name descriptive_name  # Development
npx prisma migrate deploy                        # Production
```

**NEVER use `prisma db push` without:**
- [ ] Database backup: `pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql`
- [ ] Checking all affected apps
- [ ] Testing on staging first
- [ ] Team approval

### If Data Loss Occurs

1. Check git history and application logs
2. Restore from backup (if available)
3. Document incident in commit message
4. Recreate critical data manually

See individual app CLAUDE.md files for detailed database safety rules.

## Cloud Run Secrets Management

### NEVER set secrets manually in Cloud Console

**Nova Vida API keys were wiped on Feb 4, 2026** because secrets were set manually in Cloud Console instead of in cloudbuild.yaml.

### Why This Happens

Cloud Build's `gcloud run deploy` uses `--set-secrets` which is a **REPLACEMENT** operation, not a merge. Every deploy completely replaces the Cloud Run service configuration, wiping any manually-added secrets.

### Safe Secrets Operations

**ALWAYS add secrets to cloudbuild.yaml:**
```yaml
- '--set-secrets'
- 'SECRET_NAME=secret-manager-name:latest,ANOTHER_SECRET=another-name:latest'
```

**Before adding a new integration that needs secrets:**
1. Create secret in Secret Manager: `gcloud secrets create SECRET_NAME --project=PROJECT_ID`
2. Add version: `echo -n 'value' | gcloud secrets versions add SECRET_NAME --data-file=-`
3. Add to cloudbuild.yaml's `--set-secrets` line
4. Commit cloudbuild.yaml changes

**Run audit before deploy (AICFO example):**
```bash
./scripts/audit-secrets.sh  # Checks all secrets exist in Secret Manager
```

### Products Using Cloud Run

| Product | cloudbuild.yaml Location | Secrets Location |
|---------|-------------------------|------------------|
| AICFO | aicfo-monorepo/cloudbuild.yaml | Google Secret Manager |

### NEVER modify another product's secrets

**AICFO suffered a 67-minute outage on Feb 5, 2026** because the `db_password_sa` secret was changed to an incorrect value during a batch of secret updates. All database operations failed.

**Protected secrets per product (DO NOT TOUCH from other sessions):**

| Secret | Owner | DO NOT modify from |
|--------|-------|-------------------|
| `db_password_sa` | AICFO | Any non-AICFO session |
| `anthropic_api_key` | AICFO | Any non-AICFO session |
| `firebase-service-account` | Shared | Any session without explicit approval |
| `sendgrid-api-key` | AICFO | Any non-AICFO session |

**Before modifying ANY secret:**
1. Verify which products use it: `gcloud run services describe SERVICE --region=REGION --format=yaml | grep -A2 secretKeyRef`
2. If shared, coordinate with the owning product's session
3. NEVER change a secret's value unless you are certain the new value is correct
4. After changing, verify the service can still connect: check Cloud Run logs for errors

**Incident reference:** `aicfo-monorepo/docs/incidents/2026-02-05-db-password-secret-outage.md`

## Session Start Checklist

Each session should start with:
```bash
git pull origin main
git log --oneline -5  # Check recent commits from other sessions
```

## Cross-Session Protocol

If a change in one session requires changes in another:
1. Complete and commit your session's portion
2. Tell user: "This requires corresponding changes in [X] session"
3. User switches to that terminal to continue

## Ecosystem Standards

### Authentication
- ALL products use Firebase Auth (project: aicfo-473816)
- Google Sign-In required

### Multi-Tenancy
- Every data model requires tenantId
- All queries filter by tenant

### Payments
- Stripe integration owned by B2Bee Global
- Products call shared Stripe utilities

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

## Future Backlog

### Consolidate Sidebar Component
Current: Duplicated in 6 locations
Target: Single shared component in marketing-monorepo/packages/ui/
Status: Documenting current state, consolidation deferred
