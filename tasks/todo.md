# DeltaCFO Onboarding System - Development Plan

**Version:** 1.0
**Created:** December 1, 2025
**Target Completion:** 4-5 weeks

---

## Current Progress

### Phase 0: Bug Fixes & Foundation (Days 1-2) - COMPLETE
- [x] **Task 0.1.1**: Create bot_conversations table (already existed)
- [x] **Task 0.1.2**: Fix get_business_entities() → get_entities_with_business_lines()
- [x] **Task 0.1.3**: Verify onboarding completes end-to-end
- [x] **Task 0.2.1**: Audit existing file upload code (saved to docs/file_ingestion_audit.md)
- [x] **Task 0.2.2**: Create unified file type detector (web_ui/services/file_detector.py)

### Phase 1: Universal File Ingestion (Days 3-6)
- [ ] Task 1.1.1: Enhance CSV column detection
- [ ] Task 1.1.2: Add column mapping UI for edge cases
- [ ] Task 1.2.1: Enhance PDF text extraction
- [ ] Task 1.2.2: Implement PDF type classification
- [ ] Task 1.2.3: Implement PDF transaction extraction
- [ ] Task 1.3.1: Implement XLS/XLSX parser
- [ ] Task 1.3.2: Add Excel column mapping UI
- [ ] Task 1.4.1: Implement receipt/invoice image parser
- [ ] Task 1.5.1: Create unified ingestion endpoint
- [ ] Task 1.5.2: Create ingestion queue for background processing

### Phase 2: Classification Preview (Days 7-9)
- [ ] Task 2.1.1: Add Step 6 to wizard flow
- [ ] Task 2.1.2: Create onboarding-specific upload handler
- [ ] Task 2.2.1: Create classification preview endpoint
- [ ] Task 2.2.2: Build preview modal component
- [ ] Task 2.2.3: Wire preview modal to upload flow
- [ ] Task 2.3.1: Implement transaction persistence
- [ ] Task 2.3.2: Update wizard completion flow

### Phase 3: Industry Templates 2.0 (Days 10-13)
- [ ] Task 3.1.1: Design enhanced template schema
- [ ] Task 3.1.2: Create template application function
- [ ] Task 3.2.1: Create Technology/SaaS template
- [ ] Task 3.2.2: Create Crypto/Blockchain template
- [ ] Task 3.2.3: Create Retail/E-commerce template
- [ ] Task 3.2.4: Create Consulting/Professional Services template
- [ ] Task 3.2.5: Create Healthcare template
- [ ] Task 3.2.6: Create Generic template
- [ ] Task 3.3.1: Add structure type to onboarding
- [ ] Task 3.3.2: Store structure type in database
- [ ] Task 3.3.3: Apply structure-specific setup

### Phase 4: Entity & Business Line Flow (Days 14-17) - COMPLETE
- [x] Task 4.1: Update OnboardingBot Service (entity/BL methods)
- [x] Task 4.2: Update Onboarding API Routes
- [x] Task 4.3: Update Conversation Prompts (ambiguous terms handling)
- [x] Task 4.4: Update Frontend Bot UI (entity/BL badges)
- [x] Task 4.5: Testing and validation

### Phase 5: Completion % & Progressive Disclosure (Days 18-19) - COMPLETE
- [x] Task 5.1: Create get_completion_milestones() method (5 milestones with weights)
- [x] Task 5.2: Create /api/onboarding/capabilities endpoint
- [x] Task 5.3: Update frontend progress UI with milestone indicators
- [x] Task 5.4: Apply progressive disclosure to navbar (data-capability attributes)

### Phase 6: Intercompany Setup (Days 20-21)
- [ ] Task 6.1.1: Add intercompany question to AI chat
- [ ] Task 6.1.2: Create intercompany relationships table
- [ ] Task 6.2.1: Add is_intercompany to transactions
- [ ] Task 6.2.2: Implement intercompany auto-detection
- [ ] Task 6.2.3: Add intercompany toggle to dashboard

### Phase 7: Testing & Polish (Days 22-24)
- [ ] Task 7.1.1: Create test tenant scenarios
- [ ] Task 7.1.2: Test file ingestion across formats
- [ ] Task 7.2.1: Fix bugs from testing
- [ ] Task 7.3.1: Update developer documentation
- [ ] Task 7.3.2: Create user-facing help content

---

## SaaS-First Architecture Rules

**NO DELTA-SPECIFIC CODE ALLOWED**

- DO NOT hardcode "Delta", "Alps", "Paraguay", or any client names
- DO NOT create Delta-specific patterns, entities, or business lines
- DO NOT assume crypto/mining is the only industry
- DO use industry templates that ANY tenant can select
- DO make all patterns, entities, BLs configurable per tenant
- DO test with non-crypto industries (retail, consulting, etc.)

---

## Task Details

See `/Users/whitdhamer/Downloads/onboarding_dev_plan.md` for full subtask breakdown.
