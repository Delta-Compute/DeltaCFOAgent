# Phase 5: Completion % & Progressive Disclosure

## Overview
Enhance the onboarding completion tracking to include meaningful milestones beyond just tenant_configuration fields, and implement progressive disclosure to hide advanced features until prerequisites are met.

## Current State Analysis

### Current `get_onboarding_status()` only tracks:
- Required: company_name, company_tagline, company_description, industry
- Optional: founded_date, headquarters_location, website_url, contact_email

### Problems:
1. Doesn't track entities, bank accounts, transactions, patterns
2. A tenant with 100% completion could have zero financial data
3. No way to know which features are "ready to use"

## New Milestone System

### Milestone Categories

| Milestone | Weight | Criteria | Unlocks |
|-----------|--------|----------|---------|
| **Profile** | 20% | company_name + description + industry | Basic dashboard |
| **Entities** | 20% | At least 1 entity created | Entity filters, entity reports |
| **Accounts** | 20% | At least 1 bank account OR crypto wallet | Account reconciliation |
| **Transactions** | 25% | At least 10 transactions uploaded | Transaction dashboard, analytics |
| **Patterns** | 15% | At least 3 classification patterns | Auto-classification |

### Completion Calculation
```
completion_percentage = sum(milestone_weight if milestone_complete else 0)
```

## Implementation Tasks

### Task 5.1: Enhanced Completion Milestones

**File:** `web_ui/services/onboarding_bot.py`

Replace `get_onboarding_status()` with `get_completion_milestones()`:

```python
def get_completion_milestones(self) -> Dict[str, Any]:
    """
    Get completion status with meaningful milestones

    Returns:
        {
            'completion_percentage': 65,
            'milestones': {
                'profile': {'complete': True, 'weight': 20, 'details': {...}},
                'entities': {'complete': True, 'weight': 20, 'details': {...}},
                'accounts': {'complete': False, 'weight': 20, 'details': {...}},
                'transactions': {'complete': True, 'weight': 25, 'details': {...}},
                'patterns': {'complete': False, 'weight': 15, 'details': {...}}
            },
            'next_steps': ['Add a bank account or crypto wallet', 'Create classification patterns'],
            'capabilities': ['dashboard', 'entities', 'transactions']
        }
    """
```

### Task 5.2: Tenant Capabilities Endpoint

**File:** `api/onboarding_routes.py`

New endpoint: `GET /api/onboarding/capabilities`

```python
@onboarding_bp.route('/capabilities', methods=['GET'])
@require_auth
def get_capabilities():
    """
    Get tenant capabilities based on setup completion

    Returns:
        {
            'success': True,
            'capabilities': {
                'dashboard': True,      # Always enabled
                'entities': True,       # Enabled if profile complete
                'transactions': True,   # Enabled if entities exist
                'analytics': False,     # Requires 10+ transactions
                'reports': False,       # Requires analytics
                'workforce': False,     # Requires transactions
                'invoices': False       # Requires transactions
            },
            'completion': {...}  # Full milestone data
        }
    """
```

### Task 5.3: Update Completion Progress UI

**File:** `web_ui/static/onboarding_bot.js`

Update progress bar to show milestones:
- Show milestone icons/checkmarks
- Tooltip with milestone details
- Visual indication of next milestone to complete

### Task 5.4: Progressive Disclosure

**File:** `web_ui/templates/dashboard_advanced.html` and `web_ui/static/script_advanced.js`

1. Add capability check on page load
2. Hide/disable features based on capabilities
3. Show "setup required" messages with links to complete setup

## API Response Format

### GET /api/onboarding/capabilities

```json
{
  "success": true,
  "completion_percentage": 65,
  "milestones": {
    "profile": {
      "id": "profile",
      "name": "Business Profile",
      "complete": true,
      "weight": 20,
      "icon": "building",
      "details": {
        "company_name": "Delta Mining",
        "industry": "Technology"
      }
    },
    "entities": {
      "id": "entities",
      "name": "Legal Entities",
      "complete": true,
      "weight": 20,
      "icon": "sitemap",
      "details": {
        "count": 3,
        "names": ["Delta Mining LLC", "Delta Paraguay", "Delta Brasil"]
      }
    },
    "accounts": {
      "id": "accounts",
      "name": "Financial Accounts",
      "complete": false,
      "weight": 20,
      "icon": "bank",
      "details": {
        "bank_accounts": 0,
        "crypto_wallets": 0
      }
    },
    "transactions": {
      "id": "transactions",
      "name": "Transaction Data",
      "complete": true,
      "weight": 25,
      "icon": "exchange",
      "details": {
        "count": 1547,
        "date_range": "2024-01-01 to 2024-12-01"
      }
    },
    "patterns": {
      "id": "patterns",
      "name": "Classification Patterns",
      "complete": false,
      "weight": 15,
      "icon": "brain",
      "details": {
        "count": 2,
        "required": 3
      }
    }
  },
  "capabilities": {
    "dashboard": true,
    "entities": true,
    "transactions": true,
    "analytics": true,
    "reports": true,
    "workforce": true,
    "invoices": true,
    "accounts": false
  },
  "next_steps": [
    {
      "milestone": "accounts",
      "message": "Add a bank account or crypto wallet to enable account reconciliation",
      "action_url": "/whitelisted-accounts",
      "action_label": "Add Account"
    },
    {
      "milestone": "patterns",
      "message": "Create 1 more classification pattern to enable auto-classification",
      "action_url": "/tenant-knowledge",
      "action_label": "Add Pattern"
    }
  ]
}
```

## Implementation Order

1. **Task 5.1**: Create `get_completion_milestones()` method
2. **Task 5.2**: Create `/api/onboarding/capabilities` endpoint
3. **Task 5.3**: Update frontend progress UI
4. **Task 5.4**: Apply progressive disclosure to dashboard

## Testing Checklist

- [ ] New tenant shows 0% completion
- [ ] Profile milestone completes with company name + description + industry
- [ ] Entities milestone completes with 1+ entity
- [ ] Accounts milestone completes with 1+ account
- [ ] Transactions milestone completes with 10+ transactions
- [ ] Patterns milestone completes with 3+ patterns
- [ ] Capabilities correctly reflect milestone status
- [ ] Dashboard hides features when capabilities are false
- [ ] Next steps are actionable and correct
