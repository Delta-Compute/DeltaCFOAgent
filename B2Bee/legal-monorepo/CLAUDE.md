# LEGAL AI - Legal Practice Management System

Comprehensive legal practice management SaaS platform for Brazilian lawyers and law firms. Part of the B2Bee ecosystem.

## Project Overview

**Product Name:** LEGAL AI
**Target Market:** Brazilian lawyers and law firms
**Language:** Brazilian Portuguese (pt-BR)
**Pricing Model:** Tiered subscription (LIGHT, UP, SMART, COMPANY, VIP)

## Project Structure

```
legal-monorepo/
├── apps/
│   └── web/                    # Next.js web application
│       ├── app/
│       │   ├── (auth)/         # Public auth pages (login, register)
│       │   ├── (main)/         # Protected app routes
│       │   │   └── main/
│       │   │       ├── workspace/    # Dashboard
│       │   │       ├── agenda/       # Calendar
│       │   │       ├── contacts/     # CRM
│       │   │       ├── services/     # Client services
│       │   │       ├── cases/        # Case management
│       │   │       ├── clippings/    # Publications
│       │   │       ├── financial/    # Financial module
│       │   │       ├── documents/    # Document management
│       │   │       ├── hub-ia/       # AI features hub
│       │   │       ├── indicators/   # Analytics
│       │   │       └── alerts/       # Notifications
│       │   └── api/            # API routes
│       ├── components/
│       │   ├── ui/             # Reusable UI components
│       │   └── layout/         # Layout components (sidebar, header)
│       ├── lib/
│       │   ├── utils.ts        # Utility functions (cn, formatters)
│       │   ├── i18n.ts         # Portuguese localization
│       │   ├── sidebar-config.ts # Navigation config
│       │   ├── firebase.ts     # Firebase client
│       │   ├── firebase-admin.ts
│       │   ├── auth-context.tsx
│       │   └── prisma.ts
│       ├── hooks/
│       └── prisma/
│           └── schema.prisma   # Database schema
├── packages/                   # Shared packages (future)
├── tasks/
│   └── todo.md                 # Development task tracking
├── turbo.json
└── package.json
```

## Development Commands

```bash
# Install dependencies
npm install

# Run development server (port 3006)
npm run dev

# Build for production
npm run build

# Database commands
npm run db:generate   # Generate Prisma client
npm run db:push       # Push schema to database
npm run db:studio     # Open Prisma Studio
npm run db:migrate    # Create and apply migrations
```

## Core Features

### 1. Case Management (Processos)
- CNJ number format validation (NNNNNNN-NN.NNNN.N.NN.NNNN)
- Court integration (mocked, future: real Brazilian court APIs)
- Case movements tracking (Andamentos)
- Parties management

### 2. Publications (Publicacoes)
- Diario Oficial monitoring
- Publication status workflow (new -> viewed -> handled)
- AI-powered workflow suggestions (plan-gated)
- Deadline extraction

### 3. Financial Module (Financeiro)
- Income/expense tracking
- Invoice generation
- Cost centers
- BRL currency formatting

### 4. AI Features (Plan-Gated)
- **Progress Prioritization:** All plans
- **Document Creation:** UP+
- **Client Updates:** SMART+
- **Publication Processing:** COMPANY+

### 5. OAB Integration
- Lawyer bar registration validation
- Auto-import cases via OAB number
- State (UF) seccional support

## Database Models

Key models in `prisma/schema.prisma`:

- **Core:** User, Tenant, TenantUser
- **Law Firm:** Firm, OABRegistration
- **Cases:** Case, CaseMovement, CaseParty
- **Publications:** Publication
- **CRM:** Contact, ClientService
- **Productivity:** Task, CalendarEvent, Alert
- **Documents:** Document, LegalDocument
- **Financial:** FinancialEntry, Invoice
- **Billing:** PricingPlan, Subscription

## UI Components

All components in `components/ui/`:
- Button, Card, Input, Select, Textarea
- Modal, Tabs, Badge, Avatar
- Table, Dropdown, Stepper
- Toast, Loading, EmptyState

## Localization

All UI text is in Brazilian Portuguese. Constants in `lib/i18n.ts`.

Formatting utilities in `lib/utils.ts`:
- `formatDateBR(date)` - DD/MM/YYYY
- `formatCurrencyBR(value)` - R$ 1.234,56
- `formatNumberBR(value)` - 1.234,56
- `isValidCNJ(cnj)` - CNJ validation
- `isValidOAB(oab)` - OAB validation

## B2Bee Ecosystem Standards

### Authentication
- Firebase project: `aicfo-473816`
- Firebase-only authentication (no NextAuth)
- Google Sign-In enabled
- Client SDK for frontend auth state
- Admin SDK for server-side token verification

### Database
- PostgreSQL (shared with other B2Bee apps)
- Prisma ORM
- All models include `tenantId` for multi-tenancy

### Styling
- TailwindCSS with custom primary color palette
- Lucide React icons
- Custom animation utilities in globals.css

### Commit Standards
```
[LEGAL] type: description

Types: feat, fix, refactor, docs, test, chore
```

## Shared File Protocol

STOP and notify user before modifying:
- `prisma/schema.prisma` (shared database schema)
- Firebase configuration
- Environment variables structure

## Cross-Product Integration

- Uses same Firebase project as Scout, EmailAgent, SocialAgent
- Shares PostgreSQL database
- Follows B2Bee multi-tenant architecture

## Routes Structure

| Route | Module |
|-------|--------|
| `/main/workspace` | Dashboard |
| `/main/agenda` | Calendar |
| `/main/contacts` | CRM |
| `/main/services` | Client Services |
| `/main/cases` | Case Management |
| `/main/clippings` | Publications |
| `/main/financial/entries` | Financial |
| `/main/document-creator` | AI Document Creation |
| `/main/documents` | Document Management |
| `/main/indicators` | Analytics |
| `/main/alerts` | Notifications |
| `/main/hub-ia` | AI Features Hub |

## Plan Features Matrix

| Feature | LIGHT | UP | SMART | COMPANY | VIP |
|---------|-------|-----|-------|---------|-----|
| Case Management | Yes | Yes | Yes | Yes | Yes |
| Publications | Yes | Yes | Yes | Yes | Yes |
| Progress Prioritization AI | Yes | Yes | Yes | Yes | Yes |
| Document Creation AI | - | Yes | Yes | Yes | Yes |
| Client Updates AI | - | - | Yes | Yes | Yes |
| Publication Processing AI | - | - | - | Yes | Yes |

## Future Development

1. **OAB Court Integration:** Real Brazilian court APIs
2. **Calendar:** Full calendar implementation with external sync
3. **Mobile App:** React Native/Expo companion app
4. **AI Features:** Claude API integration for document generation
5. **Stripe:** Subscription billing integration
