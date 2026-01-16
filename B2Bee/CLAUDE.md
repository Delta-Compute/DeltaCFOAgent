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
