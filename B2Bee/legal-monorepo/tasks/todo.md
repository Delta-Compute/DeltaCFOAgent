# LEGAL AI - Legal Practice Management System - Development Plan

## Project Overview
Build a comprehensive legal practice management SaaS platform for Brazilian lawyers and law firms. The system automates case management, court monitoring, client communication, financial tracking, and document generation using AI.

**Target Market:** Brazilian lawyers and law firms (solo practitioners to large firms)
**Language:** Brazilian Portuguese (pt-BR)
**Pricing Model:** Tiered subscription (LIGHT, UP, SMART, COMPANY, VIP)

---

## Previous Setup (Completed)
- [x] Monorepo scaffolding with Turbo
- [x] Next.js 14 app setup
- [x] Firebase authentication (client + admin)
- [x] Prisma with base User/Tenant models
- [x] TailwindCSS configuration
- [x] Basic auth pages (login, register, forgot-password)
- [x] Dashboard placeholder page

---

## Phase 1: Database Schema & Core Models (COMPLETED)
**Goal:** Extend Prisma schema with all legal-specific models

### Tasks:
- [x] 1.1 Add Firm model (law firm/office entity)
- [x] 1.2 Add OABRegistration model (lawyer bar registration)
- [x] 1.3 Add Case (Processo) model with CNJ number format
- [x] 1.4 Add CaseMovement (Andamento) model
- [x] 1.5 Add Publication (Publicacao) model for court notices
- [x] 1.6 Add Contact model (clients, parties, witnesses)
- [x] 1.7 Add ClientService (Atendimento) model
- [x] 1.8 Add Task (Tarefa) model
- [x] 1.9 Add CalendarEvent (Agenda) model
- [x] 1.10 Add FinancialEntry (Lancamento) model
- [x] 1.11 Add Invoice (Fatura) model
- [x] 1.12 Add Document (Documento) model
- [x] 1.13 Add LegalDocument (Peca) model for AI-generated documents
- [x] 1.14 Add Alert (Alerta) model
- [x] 1.15 Add PricingPlan and Subscription models
- [ ] 1.16 Run Prisma migration (requires npm install first)

---

## Phase 2: Onboarding Flow (5-Step Wizard) (COMPLETED)
**Goal:** Implement the signup and OAB-based case import flow

### Tasks:
- [x] 2.1 Create onboarding layout with progress stepper
- [x] 2.2 Step 1: Profile page (/onboarding)
  - Name and phone form
  - Brazilian phone formatting
- [x] 2.3 Step 2: Firm size qualification page (/onboarding/escritorio)
  - Process volume selection cards
  - Segment storage for personalization
- [x] 2.4 Step 3: OAB integration page (/onboarding/oab)
  - OAB number + state dropdown form
  - Real court API integration (Digesto and JusBrasil)
  - Case import with preview
- [x] 2.5 Step 4: Confirm information page (/onboarding/confirmacao)
  - Display imported cases count
  - Confirm automatic monitoring
- [x] 2.6 Step 5: Team invitation page (/onboarding/equipe)
  - Email input with add more functionality
  - Send invitation emails
  - Skip option
- [x] 2.7 Step 6: Onboarding complete page (/onboarding/completo)
  - Success message with checkmarks
  - CTA to view dashboard
- [ ] 2.8 Create floating chat widget component

---

## Phase 3: Main Application Layout (COMPLETED)
**Goal:** Build the dashboard shell with navigation sidebar

### Tasks:
- [x] 3.1 Create main layout component with sidebar
- [x] 3.2 Build sidebar navigation component
  - Logo
  - Search bar
  - Navigation items with icons
  - AI feature badge styling
  - Upgrade CTA button
- [x] 3.3 Build header bar component
  - Global search
  - Quick actions (+, sync, notifications, messages, settings)
  - User profile dropdown
  - Upgrade button
- [x] 3.4 Create sidebar configuration file (pt-BR labels)
- [x] 3.5 Implement route protection middleware
- [x] 3.6 Create Portuguese language constants file

---

## Phase 4: Dashboard (Area de Trabalho) (COMPLETED - UI)
**Goal:** Central hub with today's priorities

### Tasks:
- [x] 4.1 Create dashboard page (/main/workspace)
- [x] 4.2 Build today's tasks widget
- [x] 4.3 Build recent case movements widget
- [x] 4.4 Build upcoming hearings widget
- [x] 4.5 Build quick action cards
- [x] 4.6 Build performance summary widgets
- [ ] 4.7 Create welcome modal for first-time users

---

## Phase 5: Calendar Module (Agenda) (PARTIAL)
**Goal:** Centralized calendar for hearings, deadlines, meetings

### Tasks:
- [x] 5.1 Create agenda page (/main/agenda)
- [ ] 5.2 Implement day/week/month view switcher
- [ ] 5.3 Build calendar grid component
- [ ] 5.4 Build event creation/edit modal
- [ ] 5.5 Implement color-coded event types
- [ ] 5.6 Create calendar event API routes (CRUD)
- [ ] 5.7 Add hearing reminders functionality

---

## Phase 6: Contacts Module (Contatos) (COMPLETED)
**Goal:** CRM for clients and related parties

### Tasks:
- [x] 6.1 Create contacts list page (/main/contacts)
- [x] 6.2 Build contact detail view (modal)
- [x] 6.3 Build contact creation/edit modal
- [x] 6.4 Implement contact categorization (client, opposing party, witness)
- [x] 6.5 Build associated cases section (in modal)
- [x] 6.6 Create contacts API routes (CRUD)
- [x] 6.7 Add search and filtering

---

## Phase 7: Client Services Module (Atendimentos) (PARTIAL)
**Goal:** Track client consultations and service delivery

### Tasks:
- [x] 7.1 Create services list page (/main/services)
- [ ] 7.2 Build service record detail view
- [ ] 7.3 Build service creation/edit modal
- [ ] 7.4 Implement time tracking per client
- [ ] 7.5 Create services API routes (CRUD)

---

## Phase 8: Cases Module (Processos e Casos) - CORE (MOSTLY COMPLETE)
**Goal:** Core case management with court integration

### Tasks:
- [x] 8.1 Create cases list page (/main/cases)
- [x] 8.2 Build case filters (court, status, client, area of law)
- [x] 8.3 Build case detail page (/main/cases/[id])
  - CNJ number display
  - Parties involved section
  - Court and judge info
  - Case timeline/movements
  - Associated tasks
  - Documents section
  - Financial records
  - Notes
- [ ] 8.4 Build case creation modal
- [x] 8.5 Create cases API routes (CRUD)
- [x] 8.6 Implement CNJ number validation (in lib/utils.ts)
- [x] 8.7 Build case status tracking
- [x] 8.8 Court integration service (Digesto + JusBrasil APIs)

---

## Phase 9: Publications Module (Publicacoes) (MOSTLY COMPLETE)
**Goal:** Monitor and manage court publications

### Tasks:
- [x] 9.1 Create publications list page (/main/clippings)
- [x] 9.2 Build publication inbox with status (new, viewed, handled)
- [x] 9.3 Build publication detail modal
- [x] 9.4 Implement link publications to cases (in API)
- [x] 9.5 Create tasks from publications functionality (modal button)
- [x] 9.6 Build deadline extraction display (in modal)
- [x] 9.7 Create publications API routes (CRUD)
- [ ] 9.8 Create welcome modal component

---

## Phase 10: Financial Module (Financeiro) (PARTIAL)
**Goal:** Complete financial management for law firms

### Tasks:
- [x] 10.1 Create financial page with tabs (/main/financial/entries)
- [x] 10.2 Build entries tab (income/expense records)
- [x] 10.3 Build invoices tab (client billing)
- [x] 10.4 Build cash flow tab (financial overview)
- [ ] 10.5 Build settings tab (categories, cost centers)
- [ ] 10.6 Create entry creation/edit modal
- [ ] 10.7 Create invoice generation feature
- [ ] 10.8 Create financial API routes (CRUD)
- [x] 10.9 Build empty state with illustration

---

## Phase 11: Document Management Module (Documentos) (PARTIAL)
**Goal:** File upload and organization

### Tasks:
- [x] 11.1 Create documents page (/main/documents)
- [ ] 11.2 Build file upload component
- [x] 11.3 Build folder structure navigation
- [ ] 11.4 Implement case association
- [x] 11.5 Build document search
- [ ] 11.6 Create documents API routes (CRUD)

---

## Phase 12: AI Document Creation Module (Criacao de Pecas)
**Goal:** AI-powered legal document generation

### Tasks:
- [ ] 12.1 Create document creator page (/main/document-creator)
- [ ] 12.2 Build template category selector (civil, labor, etc.)
- [ ] 12.3 Build template selection interface (45+ templates)
- [ ] 12.4 Create document generation form
- [ ] 12.5 Integrate Claude API for document generation
- [ ] 12.6 Build jurisprudence search integration (mock)
- [ ] 12.7 Build editable AI output component
- [ ] 12.8 Create document generation API routes
- [ ] 12.9 Implement plan-gating for AI features

---

## Phase 13: Analytics Module (Indicadores) (PARTIAL)
**Goal:** Business intelligence and performance metrics

### Tasks:
- [x] 13.1 Create indicators page (/main/indicators)
- [ ] 13.2 Build case volume trends chart
- [ ] 13.3 Build revenue analytics chart
- [x] 13.4 Build deadline compliance rate widget
- [x] 13.5 Build productivity metrics widget
- [ ] 13.6 Create analytics API routes

---

## Phase 14: Alerts Module (Alertas) (PARTIAL)
**Goal:** Notification management

### Tasks:
- [x] 14.1 Create alerts page (/main/alerts)
- [x] 14.2 Build alerts list component
- [ ] 14.3 Build alert configuration modal
- [ ] 14.4 Implement customizable alert rules
- [ ] 14.5 Create alerts API routes (CRUD)

---

## Phase 15: AI Features Hub (PARTIAL)
**Goal:** Centralized showcase of AI capabilities with plan-gating

### Tasks:
- [x] 15.1 Create AI hub page (/main/hub-ia)
- [x] 15.2 Build overview section with tabs
- [x] 15.3 Build Publication Processing AI card (COMPANY, VIP)
- [x] 15.4 Build Client Updates AI card (SMART, COMPANY, VIP)
- [x] 15.5 Build Document Creation AI card (UP, SMART, COMPANY, VIP)
- [x] 15.6 Build Progress Prioritization AI card (all plans)
- [x] 15.7 Implement plan-gating UI with upgrade prompts
- [ ] 15.8 Add tutorial video sections

---

## Phase 16: Pricing & Subscription
**Goal:** Implement subscription management

### Tasks:
- [ ] 16.1 Create pricing plans page
- [ ] 16.2 Build plan comparison table
- [ ] 16.3 Implement Stripe integration for subscriptions
- [ ] 16.4 Create subscription management API routes
- [ ] 16.5 Implement plan-gating middleware

---

## Phase 17: Tasks System (PARTIAL)
**Goal:** Task management throughout the app

### Tasks:
- [ ] 17.1 Create tasks list component (reusable)
- [ ] 17.2 Build task creation/edit modal
- [ ] 17.3 Implement task due dates with calendar integration
- [x] 17.4 Create tasks API routes (CRUD)
- [x] 17.5 Build task assignment functionality (in API)

---

## Phase 18: UI Components Library (COMPLETED)
**Goal:** Build all reusable UI components

### Tasks:
- [x] 18.1 Create Button component variants
- [x] 18.2 Create Card component variants
- [x] 18.3 Create Modal/Dialog component
- [x] 18.4 Create Form components (Input, Select, Textarea)
- [x] 18.5 Create Table component with pagination
- [x] 18.6 Create Badge/Tag component
- [x] 18.7 Create Toast notification component
- [x] 18.8 Create Loading spinner/skeleton components
- [x] 18.9 Create Empty state component
- [x] 18.10 Create Avatar component
- [x] 18.11 Create Dropdown menu component
- [x] 18.12 Create Tabs component
- [x] 18.13 Create Progress stepper component
- [ ] 18.14 Create Chat widget component

---

## Phase 19: Localization (pt-BR) (COMPLETED)
**Goal:** Full Brazilian Portuguese support

### Tasks:
- [x] 19.1 Create language constants file (lib/i18n.ts)
- [x] 19.2 Translate all UI labels
- [x] 19.3 Implement date formatting (DD/MM/YYYY) - formatDateBR()
- [x] 19.4 Implement currency formatting (R$) - formatCurrencyBR()
- [x] 19.5 Implement number formatting (1.234,56) - formatNumberBR()

---

## Phase 20: Testing & Quality
**Goal:** Ensure code quality and test coverage

### Tasks:
- [ ] 20.1 Set up Jest testing framework
- [ ] 20.2 Write unit tests for API routes
- [ ] 20.3 Write component tests
- [ ] 20.4 Write integration tests for core flows
- [ ] 20.5 Add ESLint rules
- [ ] 20.6 Add Prettier configuration

---

## Phase 21: Deployment & Documentation
**Goal:** Production deployment

### Tasks:
- [ ] 21.1 Update Vercel configuration
- [ ] 21.2 Configure production environment variables
- [ ] 21.3 Set up production database
- [ ] 21.4 Create API documentation
- [ ] 21.5 Update CLAUDE.md with new patterns

---

## Implementation Priority Order

### Sprint 1 (Foundation):
1. Phase 18: UI Components Library (core components)
2. Phase 1: Database Schema
3. Phase 3: Main Application Layout
4. Phase 19: Localization (pt-BR)

### Sprint 2 (Onboarding & Core):
5. Phase 2: Onboarding Flow
6. Phase 8: Cases Module (core feature)
7. Phase 4: Dashboard

### Sprint 3 (Essential Modules):
8. Phase 6: Contacts Module
9. Phase 9: Publications Module
10. Phase 17: Tasks System

### Sprint 4 (Calendar & Services):
11. Phase 5: Calendar Module
12. Phase 7: Client Services Module

### Sprint 5 (Financial & Documents):
13. Phase 10: Financial Module
14. Phase 11: Document Management

### Sprint 6 (AI & Analytics):
15. Phase 12: AI Document Creation
16. Phase 13: Analytics Module
17. Phase 15: AI Features Hub

### Sprint 7 (Alerts & Subscription):
18. Phase 14: Alerts Module
19. Phase 16: Pricing & Subscription

### Sprint 8 (Polish):
20. Phase 20: Testing
21. Phase 21: Deployment

---

## Notes

- All development follows B2Bee platform patterns (Firebase auth, Prisma, TailwindCSS)
- Multi-tenant architecture with tenantId on all models
- Brazilian Portuguese is primary language
- Court integration will be mocked initially (future: real Brazilian court APIs)
- AI features use Claude API
- Plan-gating controls access to premium features

---

## Review Section

### Sprint 1 Completed (Foundation)

**Date:** January 15, 2026

### Changes Made:

1. **UI Components Library (Phase 18)** - Created 14 reusable components:
   - Button, Card, Input, Select, Textarea (form components)
   - Modal, Tabs, Badge, Avatar, Dropdown (interaction components)
   - Table, Stepper, EmptyState, Loading, Toast (data display)
   - All components follow B2Bee design patterns with TailwindCSS

2. **Database Schema (Phase 1)** - Extended Prisma schema with 18 legal models:
   - Core: Firm, OABRegistration
   - Cases: Case (CNJ format), CaseMovement, CaseParty
   - Publications: Publication
   - CRM: Contact, ClientService
   - Productivity: Task, CalendarEvent, Alert
   - Documents: Document, LegalDocument
   - Financial: FinancialEntry, Invoice
   - Billing: PricingPlan, Subscription

3. **Main Application Layout (Phase 3)** - Created protected layout:
   - Collapsible sidebar with mobile support
   - Header with quick actions and user menu
   - Route protection with auth check
   - Navigation configuration in sidebar-config.ts

4. **Localization (Phase 19)** - Full pt-BR support:
   - lib/i18n.ts with all UI labels (~400 lines)
   - Brazilian date/currency/number formatters
   - CNJ and OAB validation functions
   - All 27 Brazilian states constant

5. **Module Pages (Phases 4-15)** - Created UI for all modules:
   - Dashboard (workspace) with stats and widgets
   - Cases list with filters
   - Contacts grid with categorization
   - Publications inbox
   - Financial with tabs
   - AI Hub with plan-gating
   - Agenda, Services, Documents, Indicators, Alerts

### Technical Decisions:

1. **Mock Data First** - All pages use mock data to enable UI development before API routes
2. **Plan-Gating UI** - AI features show lock icons and upgrade prompts based on plan
3. **Route Structure** - (main) group for protected routes with shared layout
4. **Component Reuse** - Dropdown, Table, Badge used across all modules

### Known Issues:

1. **Prisma Migration Pending** - Need to run `npm install` then `npm run db:push`
2. **Calendar Grid** - Full calendar component not yet built
3. **File Upload** - Document upload functionality not implemented
4. **Chat Widget** - Floating support chat not yet created
5. **Case Creation Modal** - Modal for creating new cases not implemented

---

### Sprint 2 Completed (Onboarding & Core)

**Date:** January 15, 2026

### Changes Made:

1. **Product Renamed** - Changed from "Astrea" to "LEGAL AI" across all files
   - Updated CLAUDE.md, sidebar, UI components, todo.md

2. **Onboarding Flow (Phase 2)** - Complete 5-step wizard:
   - `/onboarding` - Profile (name, phone)
   - `/onboarding/escritorio` - Firm size selection
   - `/onboarding/oab` - OAB integration with mock import
   - `/onboarding/confirmacao` - Data confirmation
   - `/onboarding/equipe` - Team invitation
   - `/onboarding/completo` - Success page
   - Created `lib/onboarding-context.tsx` for state management

3. **Case Detail Page (Phase 8.3)** - Full case view:
   - `/main/cases/[id]` with tabs:
     - Overview (client info, parties, notes)
     - Movements (timeline)
     - Tasks (with status and assignees)
     - Documents (file list)
     - Financial (income/expense summary)
   - Quick info cards (tribunal, judge, value, date)

4. **Cases API Routes (Phase 8.5)**:
   - `GET /api/cases` - List with pagination and filters
   - `POST /api/cases` - Create new case
   - `GET /api/cases/[id]` - Get case with all related data
   - `PUT /api/cases/[id]` - Update case
   - `DELETE /api/cases/[id]` - Archive case
   - `GET /api/cases/[id]/movements` - List movements
   - `POST /api/cases/[id]/movements` - Add movement

---

### Sprint 3 Completed (Essential Modules)

**Date:** January 15, 2026

### Changes Made:

1. **Contacts API Routes**:
   - `GET /api/contacts` - List with filters and search
   - `POST /api/contacts` - Create contact
   - `GET /api/contacts/[id]` - Get with cases and services
   - `PUT /api/contacts/[id]` - Update contact
   - `DELETE /api/contacts/[id]` - Delete (with case link check)

2. **Contact Modal Component**:
   - View mode with tabs (Info, Cases, Services)
   - Edit/Create mode with form
   - Brazilian CPF/CNPJ formatting
   - Phone number formatting

3. **Publications API Routes**:
   - `GET /api/publications` - List with status counts
   - `POST /api/publications` - Create publication
   - `GET /api/publications/[id]` - Get and mark as viewed
   - `PUT /api/publications/[id]` - Update status
   - `DELETE /api/publications/[id]` - Delete publication

4. **Publication Modal Component**:
   - View publication content
   - Change status (new, viewed, handled)
   - Link to case
   - Deadline warnings
   - Create task from publication

5. **Tasks API Routes**:
   - `GET /api/tasks` - List with filters (status, case, assignee, due soon)
   - `POST /api/tasks` - Create task
   - `GET /api/tasks/[id]` - Get task details
   - `PUT /api/tasks/[id]` - Update (auto-set completedAt)
   - `DELETE /api/tasks/[id]` - Delete task

### Files Created:
- `app/api/contacts/route.ts`
- `app/api/contacts/[id]/route.ts`
- `app/api/publications/route.ts`
- `app/api/publications/[id]/route.ts`
- `app/api/tasks/route.ts`
- `app/api/tasks/[id]/route.ts`
- `components/contacts/contact-modal.tsx`
- `components/contacts/index.ts`
- `components/publications/publication-modal.tsx`
- `components/publications/index.ts`

### Next Steps (Sprint 5):

1. Run `npm install` and `npm run db:push` to test
2. Build full calendar component
3. Create financial API routes
4. Add document upload functionality
5. Implement AI document creation with Claude API

---

### Sprint 4 Completed (Court Integration)

**Date:** January 15, 2026

### Changes Made:

1. **Court Integration Service** (`lib/services/court-integration.ts`):
   - `DigestoClient` class for Digesto API integration
     - OAB monitoring endpoint: `POST /api/monitoramento/oab/acompanhamento/`
     - Transforms response to unified case format
   - `JusBrasilClient` class for JusBrasil API integration
     - OAB search endpoint for case lookup
     - Case details endpoint by CNJ number
   - `CourtIntegrationService` unified service
     - Tries Digesto first, falls back to JusBrasil
     - Returns unified `ImportedCase` format
     - Configuration check for API keys

2. **Court API Routes**:
   - `POST /api/court/oab/search` - Search cases by OAB number
     - Accepts: lawyerName, oabNumber, oabState
     - Returns: lawyer info, cases list, total count
   - `GET /api/court/oab/search` - Check API configuration status
   - `GET /api/court/cases/[cnj]` - Get case details by CNJ number

3. **Onboarding Context Updates** (`lib/onboarding-context.tsx`):
   - Added `ImportedCaseData` interface for case storage
   - Added `LawyerData` interface for lawyer info
   - Extended `OnboardingData` with:
     - `importedCasesList: ImportedCaseData[]`
     - `lawyerData: LawyerData | null`

4. **OAB Onboarding Page Updates** (`app/onboarding/oab/page.tsx`):
   - Real API integration replacing mock
   - Firebase token authentication for API calls
   - Error handling with retry capability
   - Demo mode fallback when APIs not configured
   - Preview of first 5 imported cases
   - Error state UI with retry button

### Environment Variables Required:
```
DIGESTO_API_TOKEN=<your_digesto_api_token>
JUSBRASIL_API_KEY=<your_jusbrasil_api_key>
```

### Files Created:
- `lib/services/court-integration.ts`
- `app/api/court/oab/search/route.ts`
- `app/api/court/cases/[cnj]/route.ts`

### Files Modified:
- `lib/onboarding-context.tsx`
- `app/onboarding/oab/page.tsx`
- `tasks/todo.md`

### Technical Notes:
- Court APIs require authentication tokens (env vars)
- Demo mode available when APIs not configured (503 status triggers fallback)
- Unified case format allows mixing Digesto and JusBrasil data
- All API routes require Firebase authentication
