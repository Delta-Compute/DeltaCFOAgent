#!/usr/bin/env python3
"""
Add i18n translations to tenant_management.html
"""

import re

# Read the file
with open('web_ui/templates/tenant_management.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Define replacements
replacements = [
    # Title
    (r'(<title>)Delta CFO Agent - Tenant Management(</title>)',
     r'\1Delta CFO Agent - <span data-i18n="tenantManagement.pageTitle">Tenant Management</span>\2',
     'Page title'),

    # Main header
    (r'(<h1>)🏢 Tenant Management(</h1>)',
     r'\1<span data-i18n="tenantManagement.title">🏢 Tenant Management</span>\2',
     'Main heading'),

    (r'(<div class="date-range">)\s*Manage your client tenants\s*(</div>)',
     r'\1<span data-i18n="tenantManagement.subtitle">Manage your client tenants</span>\2',
     'Subtitle'),

    # Current Tenant section
    (r'(<h2>)🔄 Current Tenant(</h2>)',
     r'\1<span data-i18n="tenantManagement.currentTenant.sectionTitle">🔄 Current Tenant</span>\2',
     'Current Tenant section title'),

    (r'(<span>)Switch between your client tenants(</span>)',
     r'\1<span data-i18n="tenantManagement.currentTenant.description">Switch between your client tenants</span>\2',
     'Switch description'),

    (r'(<label[^>]*>)\s*Active Tenant:\s*(</label>)',
     r'\1<span data-i18n="tenantManagement.currentTenant.label">Active Tenant:</span>\2',
     'Active Tenant label'),

    (r'<option value="">Loading tenants\.\.\.</option>',
     r'<option value=""><span data-i18n="tenantManagement.currentTenant.loading">Loading tenants...</span></option>',
     'Loading tenants option'),

    (r'All data and operations will be scoped to the selected tenant',
     r'<span data-i18n="tenantManagement.currentTenant.scopeNote">All data and operations will be scoped to the selected tenant</span>',
     'Scope note'),

    # Create New Tenant section
    (r'(<h2>)➕ Create New Tenant(</h2>)',
     r'\1<span data-i18n="tenantManagement.createTenant.sectionTitle">➕ Create New Tenant</span>\2',
     'Create Tenant section title'),

    (r'(<span>)Add a new client to manage with the AI CFO Agent(</span>)',
     r'\1<span data-i18n="tenantManagement.createTenant.description">Add a new client to manage with the AI CFO Agent</span>\2',
     'Create description'),

    # Form labels
    (r'Company Name <span style="color: #e53e3e;">\*</span>',
     r'<span data-i18n="tenantManagement.createTenant.form.companyName">Company Name</span> <span style="color: #e53e3e;" data-i18n="tenantManagement.createTenant.form.required">*</span>',
     'Company Name label'),

    (r'placeholder="Client Company Inc\."',
     r'data-i18n-attr="placeholder" data-i18n="tenantManagement.createTenant.form.companyNamePlaceholder" placeholder="Client Company Inc."',
     'Company Name placeholder'),

    (r'Description <span style="font-size: 0\.85rem; font-weight: normal; color: #718096;">\(optional\)</span>',
     r'<span data-i18n="tenantManagement.createTenant.form.description">Description</span> <span style="font-size: 0.85rem; font-weight: normal; color: #718096;" data-i18n="tenantManagement.createTenant.form.descriptionOptional">(optional)</span>',
     'Description label'),

    (r'placeholder="Brief description of the client\'s business\.\.\."',
     r'data-i18n-attr="placeholder" data-i18n="tenantManagement.createTenant.form.descriptionPlaceholder" placeholder="Brief description of the client\'s business..."',
     'Description placeholder'),

    (r'Admin Email <span style="font-size: 0\.85rem; font-weight: normal; color: #718096;">\(optional\)</span>',
     r'<span data-i18n="tenantManagement.createTenant.form.adminEmail">Admin Email</span> <span style="font-size: 0.85rem; font-weight: normal; color: #718096;" data-i18n="tenantManagement.createTenant.form.descriptionOptional">(optional)</span>',
     'Admin Email label'),

    (r'placeholder="admin@clientcompany\.com"',
     r'data-i18n-attr="placeholder" data-i18n="tenantManagement.createTenant.form.adminEmailPlaceholder" placeholder="admin@clientcompany.com"',
     'Admin Email placeholder'),

    (r'If provided, an invitation will be sent to this email to join as tenant admin',
     r'<span data-i18n="tenantManagement.createTenant.form.adminEmailNote">If provided, an invitation will be sent to this email to join as tenant admin</span>',
     'Admin email note'),

    # Buttons
    (r'(id="createTenantBtn"[^>]*>)\s*Create Tenant\s*(<)',
     r'\1<span data-i18n="tenantManagement.createTenant.form.createButton">Create Tenant</span>\2',
     'Create Tenant button'),

    (r'(type="button"[^>]*onclick="clearTenantForm\(\)"[^>]*>)\s*Clear\s*(<)',
     r'\1<span data-i18n="tenantManagement.createTenant.form.clearButton">Clear</span>\2',
     'Clear button'),

    # Tenant List section
    (r'(<h2>)📋 Your Tenants(</h2>)',
     r'\1<span data-i18n="tenantManagement.tenantList.sectionTitle">📋 Your Tenants</span>\2',
     'Your Tenants section title'),

    (r'(<span>)All client tenants you have access to(</span>)',
     r'\1<span data-i18n="tenantManagement.tenantList.description">All client tenants you have access to</span>\2',
     'Tenant list description'),

    (r'Loading tenants\.\.\.',
     r'<span data-i18n="tenantManagement.tenantList.loading">Loading tenants...</span>',
     'Loading tenants message'),

    (r'No tenants found',
     r'<span data-i18n="tenantManagement.tenantList.empty">No tenants found</span>',
     'No tenants message'),
]

# Apply replacements
modified_content = content
changes_made = []

for pattern, replacement, description in replacements:
    count = len(re.findall(pattern, modified_content))
    if count > 0:
        modified_content = re.sub(pattern, replacement, modified_content)
        changes_made.append(f"  ✓ {description}: {count} occurrence(s)")
    else:
        changes_made.append(f"  ✗ {description}: NOT FOUND")

# Write modified content
with open('web_ui/templates/tenant_management.html', 'w', encoding='utf-8') as f:
    f.write(modified_content)

print("Translation attributes added to tenant_management.html:")
print("\n".join(changes_made))
print(f"\n✓ File updated successfully!")
