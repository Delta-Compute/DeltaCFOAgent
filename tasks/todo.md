# Frontend Refactoring: Flask/Jinja to Next.js + React

## Overview

Migrate the DeltaCFOAgent frontend from Flask/Jinja templates to a modern Next.js + React stack while keeping the Flask backend as the API layer.

### Current State
- **Templates**: 27 HTML files (30,321 lines)
- **JavaScript**: 26 files (11,154 lines)
- **CSS**: 7 files (5,306 lines)
- **API Routes**: 150+ Flask REST endpoints (working and stable)

### Target Stack
| Aspect     | Technology                         |
|------------|------------------------------------|
| Framework  | Next.js 16 (App Router) + React 19 |
| UI Library | shadcn/ui (New York style)         |
| Styling    | Tailwind CSS v4                    |
| Icons      | Lucide React                       |
| Fonts      | Sora (headings) + DM Sans (body)   |
| Forms      | react-hook-form + Zod              |
| Auth       | NextAuth v4 (with Firebase)        |
| Toasts     | Sonner                             |
| i18n       | next-intl                          |

### Architecture Decision
**Keep Flask as API backend** - The 150+ API endpoints are stable and well-tested. The Next.js app will:
1. Run as a separate frontend application
2. Call the Flask API via HTTP
3. Handle client-side state, routing, and rendering

---

## Phase 1: Project Setup & Configuration - COMPLETED

### Task 1.1: Initialize Next.js Project
- [x] Create `frontend/` directory at project root
- [x] Initialize Next.js 15 with App Router
- [x] Configure TypeScript strict mode
- [x] Set up path aliases (@/components, @/lib, etc.)

### Task 1.2: Install Core Dependencies
- [x] Install shadcn/ui (New York style)
- [x] Install 14 shadcn components (button, input, card, dialog, etc.)
- [x] Install lucide-react for icons
- [x] Install sonner for toasts
- [x] Install react-hook-form + @hookform/resolvers + zod
- [x] Install next-auth for authentication (configured)
- [x] Install next-intl for i18n (configured)

### Task 1.3: Configure Design System
- [x] Create globals.css with design tokens:
  - Background: #FAFAF9 (warm off-white)
  - Foreground: #18181B (dark zinc)
  - Primary: #4F46E5 (deep indigo)
  - Secondary: #F4F4F5 (cool gray)
  - Accent: #FEF3C7 (warm amber)
  - Destructive: #DC2626 (red)
- [x] Configure fonts: Sora (headings) + DM Sans (body) + JetBrains Mono (code)
- [x] Set up Tailwind CSS 3.4 with custom theme

### Task 1.4: Configure API Integration
- [x] Create lib/api.ts for Flask API client
- [x] Configure environment variables for API URL
- [x] Set up API proxy rewrites in next.config.ts
- [x] Create typed API response interfaces (60+ types)

---

## Phase 2: Core Layout & Navigation - COMPLETED

### Task 2.1: Create Root Layout
- [x] app/layout.tsx with:
  - Providers wrapper (Auth, Tenant, Tooltip)
  - Toaster (Sonner - top-right)
  - Google Fonts via link tags
  - Metadata configuration

### Task 2.2: Create Dashboard Layout
- [x] app/(dashboard)/layout.tsx with:
  - Auth check (redirect to /login if not authenticated)
  - Tenant check (redirect to /onboarding if no tenant)
  - Top navigation bar (DashboardNav)
  - Main content container (max-w-7xl)
  - Loading state with spinner

### Task 2.3: Create Navigation Components
- [x] components/dashboard/dashboard-nav.tsx:
  - Logo with company icon
  - Tenant Switcher dropdown
  - Navigation links (Overview, Transactions, Revenue, Invoices, etc.)
  - Collapsible search input
  - Notifications with badge
  - Settings dropdown
  - User menu (avatar, profile, logout)
  - Mobile hamburger menu
- [x] Active state styling: bg-indigo-50 text-indigo-700
- [x] Sticky top, white background, z-50

### Task 2.4: Create Utility Components
- [x] components/ui/loading.tsx - LoadingSpinner, LoadingPage, Skeleton variants
- [x] components/ui/error-boundary.tsx - ErrorBoundary, ErrorDisplay, ErrorMessage
- [x] components/ui/empty-state.tsx - EmptyState, NoDataFound, NoSearchResults
- [x] context/auth-context.tsx - AuthProvider, useAuth hook
- [x] context/tenant-context.tsx - TenantProvider, useTenant hook
- [x] components/providers.tsx - Combined providers wrapper

---

## Phase 3: Authentication System

### Task 3.1: Configure NextAuth
- [ ] Create app/api/auth/[...nextauth]/route.ts
- [ ] Configure Firebase as authentication provider
- [ ] Set up JWT session strategy
- [ ] Handle token refresh

### Task 3.2: Create Auth Pages
- [ ] app/(auth)/login/page.tsx - Centered card, gradient background
- [ ] app/(auth)/register/page.tsx - User registration
- [ ] app/(auth)/forgot-password/page.tsx - Password reset
- [ ] app/(auth)/accept-invitation/page.tsx - Email invitation flow

### Task 3.3: Create Auth Hooks & Context
- [ ] hooks/use-auth.ts - Authentication state hook
- [ ] hooks/use-tenant.ts - Tenant context hook
- [ ] context/auth-context.tsx - Auth provider
- [ ] context/tenant-context.tsx - Tenant provider

---

## Phase 4: Page Migration (Priority Order)

### Task 4.1: Business Overview (Homepage)
- [ ] app/(dashboard)/page.tsx
- [ ] Components:
  - HeroSection with company branding
  - KPICards with animated counters
  - HoldingsGrid for business entities
  - QuickActions panel
- [ ] API integration: /api/homepage/content

### Task 4.2: Dashboard (Transactions)
- [ ] app/(dashboard)/dashboard/page.tsx
- [ ] Components:
  - TransactionFilters (date, category, entity, status)
  - TransactionStats cards
  - TransactionsTable with sorting/pagination
  - BulkActionsToolbar
- [ ] API integration: /api/transactions

### Task 4.3: Revenue Recognition
- [ ] app/(dashboard)/revenue/page.tsx
- [ ] Components:
  - MatchingStats cards
  - PendingMatchesTable
  - ConfirmedMatchesTable
  - MatchingModal with confidence scoring
  - BulkMatchActions
- [ ] API integration: /api/revenue/*

### Task 4.4: Invoices
- [ ] app/(dashboard)/invoices/page.tsx
- [ ] app/(dashboard)/invoices/[id]/page.tsx (detail)
- [ ] app/(dashboard)/invoices/create/page.tsx
- [ ] Components:
  - InvoiceFilters
  - InvoicesTable
  - InvoiceDetailCard
  - AttachmentsUploader
  - PaymentTracker
- [ ] API integration: /api/invoices/*

### Task 4.5: File Manager
- [ ] app/(dashboard)/files/page.tsx
- [ ] Components:
  - TransactionUploadSection
  - InvoiceUploadSection
  - ProcessingProgress
  - FileHistoryTable
- [ ] API integration: /api/upload/*

### Task 4.6: Workforce/Payroll
- [ ] app/(dashboard)/workforce/page.tsx
- [ ] Components:
  - WorkforceTabs (Members / Payslips)
  - WorkforceTable
  - PayslipsTable
  - PayslipMatchingModal
- [ ] API integration: /api/workforce/*, /api/payslips/*

### Task 4.7: Shareholders
- [ ] app/(dashboard)/shareholders/page.tsx
- [ ] Components:
  - ShareholdersList
  - EquityContributionsTable
  - OwnershipChart
- [ ] API integration: /api/shareholders/*

### Task 4.8: Whitelisted Accounts
- [ ] app/(dashboard)/accounts/page.tsx
- [ ] Components:
  - AccountsTabs (Bank / Crypto)
  - BankAccountsTable
  - CryptoWalletsTable
  - AccountFormModal
- [ ] API integration: /api/bank-accounts, /api/wallets

### Task 4.9: Settings & Management
- [ ] app/(dashboard)/settings/page.tsx (tabbed form sections)
- [ ] app/(dashboard)/tenant-knowledge/page.tsx
- [ ] app/(dashboard)/users/page.tsx
- [ ] Components:
  - SettingsTabs
  - KnowledgePatternEditor
  - UserManagementTable
  - InvitationForm

### Task 4.10: Reports
- [ ] app/(dashboard)/reports/page.tsx
- [ ] app/(dashboard)/reports/pl-trend/page.tsx
- [ ] Components:
  - ReportSelector
  - PLTrendChart
  - DateRangePicker
  - ExportButtons

---

## Phase 5: Internationalization (i18n)

### Task 5.1: Configure next-intl
- [ ] Set up next-intl with middleware
- [ ] Configure supported locales: en, pt, es
- [ ] Create messages directory structure

### Task 5.2: Migrate Translation Files
- [ ] Convert web_ui/static/locales/en.json to Next.js format
- [ ] Convert web_ui/static/locales/pt.json
- [ ] Convert web_ui/static/locales/es.json
- [ ] Create useTranslations hook usage patterns

### Task 5.3: Language Switcher
- [ ] Add language switcher to navigation
- [ ] Persist preference to localStorage and API
- [ ] Handle locale routing

---

## Phase 6: Shared Components Library

### Task 6.1: Status & Priority Badges
- [ ] components/ui/status-badge.tsx
- [ ] components/ui/priority-badge.tsx
- [ ] Color-coded variants matching design system

### Task 6.2: Data Display Components
- [ ] components/dashboard/stats-card.tsx
- [ ] components/dashboard/data-table.tsx (sortable, paginated)
- [ ] components/dashboard/empty-state.tsx
- [ ] components/dashboard/loading-skeleton.tsx

### Task 6.3: Form Components
- [ ] components/forms/currency-input.tsx
- [ ] components/forms/date-picker.tsx
- [ ] components/forms/file-uploader.tsx
- [ ] components/forms/entity-selector.tsx

### Task 6.4: Modal Dialogs
- [ ] components/modals/confirm-dialog.tsx
- [ ] components/modals/form-dialog.tsx
- [ ] components/modals/matching-dialog.tsx

---

## Phase 7: Testing & QA

### Task 7.1: Unit Tests
- [ ] Set up Jest + React Testing Library
- [ ] Write tests for utility functions
- [ ] Write tests for hooks
- [ ] Write tests for critical components

### Task 7.2: Integration Tests
- [ ] Test API integration layer
- [ ] Test authentication flow
- [ ] Test form submissions

### Task 7.3: E2E Tests (Optional)
- [ ] Set up Playwright
- [ ] Test critical user journeys

---

## Phase 8: Deployment Configuration

### Task 8.1: Docker Configuration
- [ ] Create frontend/Dockerfile
- [ ] Configure multi-stage build
- [ ] Set up environment variables

### Task 8.2: Cloud Run Deployment
- [ ] Create cloudbuild-frontend.yaml
- [ ] Configure Cloud Run service
- [ ] Set up routing (frontend vs API)

### Task 8.3: Production Checklist
- [ ] Configure production API URL
- [ ] Set up error monitoring (Sentry)
- [ ] Configure performance monitoring
- [ ] Set up CDN for static assets

---

## File Structure

```
frontend/
  src/
    app/
      (auth)/
        login/page.tsx
        register/page.tsx
        forgot-password/page.tsx
      (dashboard)/
        layout.tsx
        page.tsx                    # Business Overview
        dashboard/page.tsx          # Transactions
        revenue/page.tsx
        invoices/
          page.tsx
          [id]/page.tsx
          create/page.tsx
        files/page.tsx
        workforce/page.tsx
        shareholders/page.tsx
        accounts/page.tsx           # Whitelisted Accounts
        settings/page.tsx
        tenant-knowledge/page.tsx
        users/page.tsx
        reports/
          page.tsx
          pl-trend/page.tsx
      api/
        auth/[...nextauth]/route.ts
      layout.tsx
      globals.css
    components/
      ui/                           # shadcn/ui components
      dashboard/
        dashboard-nav.tsx
        stats-card.tsx
        data-table.tsx
        ...
      forms/
      modals/
    lib/
      api.ts                        # Flask API client
      utils.ts                      # cn() helper
      auth.ts                       # NextAuth config
    hooks/
      use-auth.ts
      use-tenant.ts
      use-api.ts
    context/
      auth-context.tsx
      tenant-context.tsx
    types/
      api.ts                        # API response types
      models.ts                     # Data models
    messages/
      en.json
      pt.json
      es.json
  public/
    fonts/
    images/
  next.config.js
  tailwind.config.ts
  components.json                   # shadcn config
  package.json
```

---

## Migration Strategy

1. **Parallel Operation**: Run both Flask templates and Next.js during migration
2. **Feature Flags**: Use feature flags to toggle between old/new UI
3. **Incremental Migration**: Migrate one page at a time
4. **API Compatibility**: No changes to Flask API required
5. **Testing**: Test each page thoroughly before moving to next

---

## Success Criteria

- [ ] All 27 pages migrated to React components
- [ ] All API integrations working
- [ ] Authentication working with Firebase
- [ ] i18n working for all 3 languages
- [ ] Responsive design on all screen sizes
- [ ] No regressions in functionality
- [ ] Performance equal or better than current
- [ ] All tests passing

---

## Notes

- **Keep Flask Backend**: All 150+ API endpoints remain unchanged
- **No Database Changes**: Frontend-only refactoring
- **Gradual Rollout**: Can deploy incrementally
- **Fallback Available**: Flask templates remain as fallback

---

## Review Section

### Phase 1: Project Setup & Configuration - COMPLETED (Dec 2024)

**Commit:** `1a91937` - feat(frontend): Initialize Next.js frontend with shadcn/ui (Phase 1)

**What was created:**

1. **Project Structure** (`frontend/`)
   - Next.js 15.1 with App Router and TypeScript
   - Tailwind CSS 3.4 with custom design system
   - ESLint + TypeScript strict mode
   - Path aliases (@/components, @/lib, etc.)

2. **Design System** (`src/app/globals.css`)
   - Color palette: Indigo primary (#4F46E5), warm off-white background (#FAFAF9)
   - Typography: Sora (headings) + DM Sans (body) + JetBrains Mono (code)
   - Component classes: stats-card, badge variants, nav-link, table styles
   - Status badges: new, pending, confirmed, paid, rejected, overdue
   - Confidence indicators: high/medium/low with color coding

3. **UI Components** (`src/components/ui/`) - 14 shadcn/ui components:
   - Form: button, input, label, checkbox, switch, select
   - Layout: card, separator, tabs, table
   - Overlay: dialog, dropdown-menu, tooltip
   - Display: badge, avatar, progress

4. **API Client** (`src/lib/api.ts`)
   - Typed fetch wrapper with error handling
   - All Flask API endpoints organized by feature:
     - Homepage, Transactions, Invoices, Revenue matching
     - Workforce, Payslips, Payroll matching
     - Bank accounts, Wallets, Shareholders
     - Tenant config, Knowledge patterns, Auth
   - Full TypeScript interfaces for all API responses

5. **Configuration Files**
   - `next.config.ts` - API proxy rewrites to Flask backend
   - `tailwind.config.ts` - Design tokens and animations
   - `components.json` - shadcn/ui New York style config
   - `.env.local.example` - Environment variables template

**Build Status:** Passing (type-check and production build successful)

**Next Steps:** Phase 2 - Core Layout & Navigation

---

### Phase 2: Core Layout & Navigation - COMPLETED (Dec 2024)

**Commit:** `7aab92f` - feat(frontend): Add dashboard layout and navigation (Phase 2)

**What was created:**

1. **Context Providers** (`src/context/`)
   - `auth-context.tsx`: AuthProvider with login/logout, user state
   - `tenant-context.tsx`: TenantProvider with tenant switching
   - `providers.tsx`: Combined wrapper component

2. **Dashboard Layout** (`src/app/(dashboard)/layout.tsx`)
   - Auth check with redirect to /login
   - Tenant check for onboarding flow
   - Loading state with spinner
   - Container max-w-7xl layout

3. **Navigation Component** (`src/components/dashboard/dashboard-nav.tsx`)
   - Sticky top navigation (z-50)
   - Logo with Building2 icon
   - Tenant switcher dropdown
   - 8 navigation links with icons
   - Collapsible search input
   - Notifications bell with badge
   - Settings dropdown
   - User menu with avatar
   - Mobile hamburger menu

4. **Utility Components** (`src/components/ui/`)
   - `loading.tsx`: LoadingSpinner, LoadingPage, Skeleton, CardSkeleton, TableSkeleton
   - `error-boundary.tsx`: ErrorBoundary class, ErrorDisplay, ErrorMessage
   - `empty-state.tsx`: EmptyState, NoDataFound, NoSearchResults, ErrorState

5. **Dashboard Homepage** (`src/app/(dashboard)/page.tsx`)
   - KPI cards with trend indicators
   - AI insights section
   - Quick action cards

**Build Status:** Passing

**Next Steps:** Phase 3 - Authentication System (or Phase 4 - Page Migration)

