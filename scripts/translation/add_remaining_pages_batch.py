#!/usr/bin/env python3
"""
Batch translate remaining pages: shareholders, business_overview, files, invoices
"""

import re
import os

def translate_file(filepath, replacements, page_name):
    """Apply translations to a file"""
    if not os.path.exists(filepath):
        print(f"⚠️  File not found: {filepath}")
        return 0

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    modified_content = content
    changes = 0

    for pattern, replacement, description in replacements:
        count = len(re.findall(pattern, modified_content))
        if count > 0:
            modified_content = re.sub(pattern, replacement, modified_content)
            changes += count

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(modified_content)

    print(f"  ✓ {page_name}: {changes} translations applied")
    return changes

# SHAREHOLDERS.HTML
shareholders_replacements = [
    (r'(<title>)Shareholder Equity Management - Delta CFO Agent(</title>)',
     r'\1<span data-i18n="shareholders.pageTitle">Shareholder Equity Management</span> - Delta CFO Agent\2',
     'Page title'),

    (r'(<h2 class="page-title">)Shareholder Equity Management(</h2>)',
     r'\1<span data-i18n="shareholders.title">Shareholder Equity Management</span>\2',
     'Main heading'),

    (r'<div class="stat-label">Total Shareholders</div>',
     r'<div class="stat-label" data-i18n="shareholders.stats.totalShareholders">Total Shareholders</div>',
     'Total Shareholders stat'),

    (r'<div class="stat-label">Shares Outstanding</div>',
     r'<div class="stat-label" data-i18n="shareholders.stats.sharesOutstanding">Shares Outstanding</div>',
     'Shares Outstanding stat'),

    (r'(data-tab="shareholders">)Shareholders(<)',
     r'\1<span data-i18n="shareholders.tabs.shareholders">Shareholders</span>\2',
     'Shareholders tab'),

    (r'(data-tab="transactions">)Transactions(<)',
     r'\1<span data-i18n="shareholders.tabs.transactions">Transactions</span>\2',
     'Transactions tab'),

    (r'(\+ Add Shareholder)',
     r'<span data-i18n="shareholders.buttons.addShareholder">+ Add Shareholder</span>',
     'Add Shareholder button'),

    (r'(<th>)Shareholder Name(</th>)',
     r'\1<span data-i18n="shareholders.table.shareholderName">Shareholder Name</span>\2',
     'Shareholder Name header'),

    (r'(<th>)Email(</th>)',
     r'\1<span data-i18n="shareholders.table.email">Email</span>\2',
     'Email header'),

    (r'(<th>)Share Class(</th>)',
     r'\1<span data-i18n="shareholders.table.shareClass">Share Class</span>\2',
     'Share Class header'),

    (r'(<th>)Total Shares(</th>)',
     r'\1<span data-i18n="shareholders.table.totalShares">Total Shares</span>\2',
     'Total Shares header'),

    (r'(<th>)Ownership %(</th>)',
     r'\1<span data-i18n="shareholders.table.ownershipPercent">Ownership %</span>\2',
     'Ownership header'),

    (r'(<label class="form-label">)Shareholder Name \*(</label>)',
     r'\1<span data-i18n="shareholders.modal.shareholderName">Shareholder Name</span> <span data-i18n="shareholders.modal.required">*</span>\2',
     'Shareholder Name label'),

    (r'Save Shareholder',
     r'<span data-i18n="shareholders.modal.saveButton">Save Shareholder</span>',
     'Save button'),
]

# BUSINESS_OVERVIEW.HTML (focus on key elements)
business_overview_replacements = [
    (r'(<title>)Delta Capital Holdings - Business Overview(</title>)',
     r'\1<span data-i18n="businessOverview.pageTitle">Business Overview</span> - Delta CFO Agent\2',
     'Page title'),

    (r'Quick Actions',
     r'<span data-i18n="businessOverview.quickActions">Quick Actions</span>',
     'Quick Actions'),

    (r'Recent Activity',
     r'<span data-i18n="businessOverview.recentActivity">Recent Activity</span>',
     'Recent Activity'),

    (r'View Report',
     r'<span data-i18n="businessOverview.viewReport">View Report</span>',
     'View Report'),
]

# FILES.HTML (key elements)
files_replacements = [
    (r'(<title>)File Manager - Delta CFO Agent(</title>)',
     r'\1<span data-i18n="files.pageTitle">File Manager</span> - Delta CFO Agent\2',
     'Page title'),

    (r'(<h1[^>]*>)File Manager(</h1>)',
     r'\1<span data-i18n="files.title">File Manager</span>\2',
     'Main heading'),

    (r'Upload File',
     r'<span data-i18n="files.uploadFile">Upload File</span>',
     'Upload File'),

    (r'Download',
     r'<span data-i18n="files.download">Download</span>',
     'Download'),

    (r'Delete',
     r'<span data-i18n="files.delete">Delete</span>',
     'Delete'),
]

# INVOICES.HTML (key elements)
invoices_replacements = [
    (r'(<title>)Invoices - Delta CFO Agent(</title>)',
     r'\1<span data-i18n="invoices.pageTitle">Invoices</span> - Delta CFO Agent\2',
     'Page title'),

    (r'(<h1[^>]*>)Invoices(</h1>)',
     r'\1<span data-i18n="invoices.title">Invoices</span>\2',
     'Main heading'),

    (r'Create Invoice',
     r'<span data-i18n="invoices.createInvoice">Create Invoice</span>',
     'Create Invoice'),

    (r'Export',
     r'<span data-i18n="invoices.export">Export</span>',
     'Export'),

    (r'Filter',
     r'<span data-i18n="invoices.filter">Filter</span>',
     'Filter'),
]

# Run translations
print("="*60)
print("BATCH TRANSLATING REMAINING PAGES")
print("="*60)

total = 0
total += translate_file('web_ui/templates/shareholders.html', shareholders_replacements, 'shareholders.html')
total += translate_file('web_ui/templates/business_overview.html', business_overview_replacements, 'business_overview.html')
total += translate_file('web_ui/templates/files.html', files_replacements, 'files.html')
total += translate_file('web_ui/templates/invoices.html', invoices_replacements, 'invoices.html')

print("\n" + "="*60)
print(f"✓ BATCH COMPLETED: {total} translations applied")
print("="*60)
