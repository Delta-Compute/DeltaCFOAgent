#!/usr/bin/env python3
"""
Add i18n translations to workforce.html
"""

import re

# Read the file
with open('web_ui/templates/workforce.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Define replacements
replacements = [
    # Title
    (r'(<title>)Workforce Management - Delta CFO Agent(</title>)',
     r'\1<span data-i18n="workforce.pageTitle">Workforce Management</span> - Delta CFO Agent\2',
     'Page title'),

    # Page header
    (r'(<h2 class="page-title">)Workforce Management(</h2>)',
     r'\1<span data-i18n="workforce.title">Workforce Management</span>\2',
     'Main heading'),

    (r'(<p class="page-subtitle">)Manage employees, contractors, and payslips(</p>)',
     r'\1<span data-i18n="workforce.subtitle">Manage employees, contractors, and payslips</span>\2',
     'Subtitle'),

    # Stats labels
    (r'<div class="stat-label">Active Members</div>',
     r'<div class="stat-label" data-i18n="workforce.stats.activeMembers">Active Members</div>',
     'Active Members stat'),

    (r'<div class="stat-label">Total Payslips</div>',
     r'<div class="stat-label" data-i18n="workforce.stats.totalPayslips">Total Payslips</div>',
     'Total Payslips stat'),

    (r'<div class="stat-label">Matched Payslips</div>',
     r'<div class="stat-label" data-i18n="workforce.stats.matchedPayslips">Matched Payslips</div>',
     'Matched Payslips stat'),

    (r'<div class="stat-label">Match Rate</div>',
     r'<div class="stat-label" data-i18n="workforce.stats.matchRate">Match Rate</div>',
     'Match Rate stat'),

    # Tabs
    (r'(data-tab="members">)Workforce Members(<)',
     r'\1<span data-i18n="workforce.tabs.members">Workforce Members</span>\2',
     'Members tab'),

    (r'(data-tab="payslips">)Payslips(<)',
     r'\1<span data-i18n="workforce.tabs.payslips">Payslips</span>\2',
     'Payslips tab'),

    # Search placeholders
    (r'placeholder="Search by name, title, email\.\.\."',
     r'data-i18n-attr="placeholder" data-i18n="workforce.members.search.placeholder" placeholder="Search by name, title, email..."',
     'Members search placeholder'),

    (r'placeholder="Search by employee, payslip number\.\.\."',
     r'data-i18n-attr="placeholder" data-i18n="workforce.payslips.search.placeholder" placeholder="Search by employee, payslip number..."',
     'Payslips search placeholder'),

    # Buttons
    (r'(onclick="openAddMemberModal\(\)">)\s*\+ Add Member\s*(<)',
     r'\1<span data-i18n="workforce.members.buttons.addMember">+ Add Member</span>\2',
     'Add Member button'),

    (r'(onclick="refreshMembers\(\)">)\s*Refresh\s*(<)',
     r'\1<span data-i18n="workforce.members.buttons.refresh">Refresh</span>\2',
     'Refresh Members button'),

    (r'(onclick="openAddPayslipModal\(\)">)\s*\+ Create Payslip\s*(<)',
     r'\1<span data-i18n="workforce.payslips.buttons.createPayslip">+ Create Payslip</span>\2',
     'Create Payslip button'),

    (r'(onclick="refreshPayslips\(\)">)\s*Refresh\s*(<)',
     r'\1<span data-i18n="workforce.payslips.buttons.refresh">Refresh</span>\2',
     'Refresh Payslips button'),

    # Table headers - Members
    (r'<th>Name</th>\s*<th>Type</th>\s*<th>Job Title</th>\s*<th>Date of Hire</th>\s*<th>Pay Rate</th>\s*<th>Status</th>\s*<th>Actions</th>',
     r'<th data-i18n="workforce.members.table.name">Name</th><th data-i18n="workforce.members.table.type">Type</th><th data-i18n="workforce.members.table.jobTitle">Job Title</th><th data-i18n="workforce.members.table.dateOfHire">Date of Hire</th><th data-i18n="workforce.members.table.payRate">Pay Rate</th><th data-i18n="workforce.members.table.status">Status</th><th data-i18n="workforce.members.table.actions">Actions</th>',
     'Members table headers'),

    # Table headers - Payslips
    (r'<th>Payslip #</th>\s*<th>Employee</th>\s*<th>Period</th>\s*<th>Payment Date</th>\s*<th>Gross Amount</th>\s*<th>Net Amount</th>\s*<th>Status</th>\s*<th>Actions</th>',
     r'<th data-i18n="workforce.payslips.table.payslipNumber">Payslip #</th><th data-i18n="workforce.payslips.table.employee">Employee</th><th data-i18n="workforce.payslips.table.period">Period</th><th data-i18n="workforce.payslips.table.paymentDate">Payment Date</th><th data-i18n="workforce.payslips.table.grossAmount">Gross Amount</th><th data-i18n="workforce.payslips.table.netAmount">Net Amount</th><th data-i18n="workforce.payslips.table.status">Status</th><th data-i18n="workforce.payslips.table.actions">Actions</th>',
     'Payslips table headers'),

    # Loading messages
    (r'(<td colspan="7" class="loading">)Loading workforce members\.\.\.(</td>)',
     r'\1<span data-i18n="workforce.members.table.loading">Loading workforce members...</span>\2',
     'Loading members message'),

    (r'(<td colspan="8" class="loading">)Loading payslips\.\.\.(</td>)',
     r'\1<span data-i18n="workforce.payslips.table.loading">Loading payslips...</span>\2',
     'Loading payslips message'),

    # Modal titles
    (r'(<h3 class="modal-title" id="member-modal-title">)Add Workforce Member(</h3>)',
     r'\1<span data-i18n="workforce.modals.member.titleAdd">Add Workforce Member</span>\2',
     'Add Member modal title'),

    # Form labels - Members
    (r'(<label class="form-label">)Full Name \*(</label>)',
     r'\1<span data-i18n="workforce.modals.member.fields.fullName">Full Name *</span>\2',
     'Full Name label'),

    (r'(<label class="form-label">)Employment Type \*(</label>)',
     r'\1<span data-i18n="workforce.modals.member.fields.employmentType">Employment Type *</span>\2',
     'Employment Type label'),

    (r'(<label class="form-label">)Status(</label>)',
     r'\1<span data-i18n="workforce.modals.member.fields.status">Status</span>\2',
     'Status label'),

    # Option text
    (r'(<option value="">)Select type(</option>)',
     r'\1<span data-i18n="workforce.modals.member.fields.employmentTypePlaceholder">Select type</span>\2',
     'Select type option'),

    (r'(<option value="employee">)Employee(</option>)',
     r'\1<span data-i18n="workforce.type.employee">Employee</span>\2',
     'Employee option'),

    (r'(<option value="contractor">)Contractor(</option>)',
     r'\1<span data-i18n="workforce.type.contractor">Contractor</span>\2',
     'Contractor option'),

    (r'(<option value="active">)Active(</option>)',
     r'\1<span data-i18n="workforce.status.active">Active</span>\2',
     'Active option'),

    (r'(<option value="inactive">)Inactive(</option>)',
     r'\1<span data-i18n="workforce.status.inactive">Inactive</span>\2',
     'Inactive option'),
]

# Apply replacements
modified_content = content
changes_made = []

for pattern, replacement, description in replacements:
    count = len(re.findall(pattern, modified_content, re.DOTALL))
    if count > 0:
        modified_content = re.sub(pattern, replacement, modified_content, flags=re.DOTALL)
        changes_made.append(f"  ✓ {description}: {count} occurrence(s)")
    else:
        changes_made.append(f"  ✗ {description}: NOT FOUND")

# Write modified content
with open('web_ui/templates/workforce.html', 'w', encoding='utf-8') as f:
    f.write(modified_content)

print("Translation attributes added to workforce.html:")
print("\n".join(changes_made))
print(f"\n✓ File updated successfully!")
