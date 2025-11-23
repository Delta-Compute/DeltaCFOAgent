#!/usr/bin/env python3
"""
Add i18n translations to users.html, tenant_management.html, and whitelisted_accounts.html
"""

import re

def translate_users_html():
    """Translate users.html"""
    with open('web_ui/templates/users.html', 'r', encoding='utf-8') as f:
        content = f.read()

    replacements = [
        # Title and headers
        (r'(<title>)User Management - Delta CFO Agent(</title>)',
         r'\1<span data-i18n="users.pageTitle">User Management</span> - Delta CFO Agent\2',
         'Page title'),

        (r'(<h1>)User Management(</h1>)',
         r'\1<span data-i18n="users.title">User Management</span>\2',
         'Main heading'),

        (r'Invite team members and manage access to your tenant',
         r'<span data-i18n="users.subtitle">Invite team members and manage access to your tenant</span>',
         'Subtitle'),

        (r'>Back to Dashboard<',
         r'><span data-i18n="users.backToDashboard">Back to Dashboard</span><',
         'Back button'),

        # CFO Section
        (r'(<h2>)Invite Fractional CFO(</h2>)',
         r'\1<span data-i18n="users.inviteCFO.sectionTitle">Invite Fractional CFO</span>\2',
         'Invite CFO section'),

        (r'(<label for="cfoEmail">)Email Address \*(</label>)',
         r'\1<span data-i18n="users.inviteCFO.form.email">Email Address</span> <span data-i18n="users.inviteCFO.form.required">*</span>\2',
         'CFO Email label'),

        (r'placeholder="cfo@example\.com"',
         r'data-i18n-attr="placeholder" data-i18n="users.inviteCFO.form.emailPlaceholder" placeholder="cfo@example.com"',
         'CFO Email placeholder'),

        (r'(<label for="cfoName">)Display Name \*(</label>)',
         r'\1<span data-i18n="users.inviteCFO.form.name">Display Name</span> <span data-i18n="users.inviteCFO.form.required">*</span>\2',
         'CFO Name label'),

        (r'Fractional CFO will have full access to manage financials, reports, and can invite their own assistants to help manage your tenant\.',
         r'<span data-i18n="users.inviteCFO.form.infoText">Fractional CFO will have full access to manage financials, reports, and can invite their own assistants to help manage your tenant.</span>',
         'CFO info text'),

        (r'(id="inviteCFOBtn">)\s*Send Invitation to CFO\s*(<)',
         r'\1<span data-i18n="users.inviteCFO.form.submitButton">Send Invitation to CFO</span>\2',
         'CFO Submit button'),

        # CFO Assistant Section
        (r'(<h2>)Invite CFO Assistant(</h2>)',
         r'\1<span data-i18n="users.inviteCFOAssistant.sectionTitle">Invite CFO Assistant</span>\2',
         'Invite Assistant section'),

        (r'(<label for="assistantEmail">)Email Address \*(</label>)',
         r'\1<span data-i18n="users.inviteCFOAssistant.form.email">Email Address</span> <span data-i18n="users.inviteCFOAssistant.form.required">*</span>\2',
         'Assistant Email label'),

        (r'placeholder="assistant@example\.com"',
         r'data-i18n-attr="placeholder" data-i18n="users.inviteCFOAssistant.form.emailPlaceholder" placeholder="assistant@example.com"',
         'Assistant Email placeholder'),

        (r'(<label for="assistantName">)Display Name \*(</label>)',
         r'\1<span data-i18n="users.inviteCFOAssistant.form.name">Display Name</span> <span data-i18n="users.inviteCFOAssistant.form.required">*</span>\2',
         'Assistant Name label'),

        (r'CFO assistants support the Fractional CFO with access based on their privilege level\.',
         r'<span data-i18n="users.inviteCFOAssistant.form.infoText">CFO assistants support the Fractional CFO with access based on their privilege level.</span>',
         'Assistant info text'),

        (r'(id="inviteCFOAssistantBtn">)\s*Send Invitation to CFO Assistant\s*(<)',
         r'\1<span data-i18n="users.inviteCFOAssistant.form.submitButton">Send Invitation to CFO Assistant</span>\2',
         'Assistant Submit button'),

        # Employee Section
        (r'(<h2>)Invite Team Member \(Employee\)(</h2>)',
         r'\1<span data-i18n="users.inviteEmployee.sectionTitle">Invite Team Member (Employee)</span>\2',
         'Invite Employee section'),

        (r'(<label for="employeeEmail">)Email Address \*(</label>)',
         r'\1<span data-i18n="users.inviteEmployee.form.email">Email Address</span> <span data-i18n="users.inviteEmployee.form.required">*</span>\2',
         'Employee Email label'),

        (r'placeholder="employee@example\.com"',
         r'data-i18n-attr="placeholder" data-i18n="users.inviteEmployee.form.emailPlaceholder" placeholder="employee@example.com"',
         'Employee Email placeholder'),

        (r'(<label for="employeeName">)Display Name \*(</label>)',
         r'\1<span data-i18n="users.inviteEmployee.form.name">Display Name</span> <span data-i18n="users.inviteEmployee.form.required">*</span>\2',
         'Employee Name label'),
    ]

    modified_content = content
    changes_made = []

    for pattern, replacement, description in replacements:
        count = len(re.findall(pattern, modified_content))
        if count > 0:
            modified_content = re.sub(pattern, replacement, modified_content)
            changes_made.append(f"  ✓ {description}: {count} occurrence(s)")
        else:
            changes_made.append(f"  ✗ {description}: NOT FOUND")

    with open('web_ui/templates/users.html', 'w', encoding='utf-8') as f:
        f.write(modified_content)

    print("users.html translations:")
    print("\n".join(changes_made))
    return len([c for c in changes_made if "✓" in c])

# Run translation
print("="*60)
print("TRANSLATING users.html")
print("="*60)
users_count = translate_users_html()
print(f"\n✓ users.html updated - {users_count} translations applied!\n")
