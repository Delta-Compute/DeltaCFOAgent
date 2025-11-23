#!/usr/bin/env python3
"""
Add i18n translations to JavaScript-generated content in revenue.html
"""

import re

# Read the file
with open('web_ui/templates/revenue.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Define replacements for JavaScript-generated HTML
replacements = [
    # Stats cards - label replacements
    (r'<div class="stat-label">Total Invoices</div>',
     r'<div class="stat-label" data-i18n="revenue.stats.totalInvoices.label">Total Invoices</div>',
     'Total Invoices label'),

    (r'<div class="stat-sublabel">In the system</div>',
     r'<div class="stat-sublabel" data-i18n="revenue.stats.totalInvoices.sublabel">In the system</div>',
     'In the system sublabel'),

    (r'<div class="stat-label">Matched Invoices</div>',
     r'<div class="stat-label" data-i18n="revenue.stats.matchedInvoices.label">Matched Invoices</div>',
     'Matched Invoices label'),

    (r'<div class="stat-label">Unmatched Invoices</div>',
     r'<div class="stat-label" data-i18n="revenue.stats.unmatchedInvoices.label">Unmatched Invoices</div>',
     'Unmatched Invoices label'),

    (r'<div class="stat-label">Match Rate</div>',
     r'<div class="stat-label" data-i18n="revenue.stats.matchRate.label">Match Rate</div>',
     'Match Rate label'),

    (r'<div class="stat-sublabel">Automation success</div>',
     r'<div class="stat-sublabel" data-i18n="revenue.stats.matchRate.sublabel">Automation success</div>',
     'Automation success sublabel'),

    (r'<div class="stat-label">Pending Review</div>',
     r'<div class="stat-label" data-i18n="revenue.stats.pendingReview.label">Pending Review</div>',
     'Pending Review label'),

    (r'<div class="stat-sublabel">Awaiting approval</div>',
     r'<div class="stat-sublabel" data-i18n="revenue.stats.pendingReview.sublabel">Awaiting approval</div>',
     'Awaiting approval sublabel'),

    (r'<div class="stat-label">Recent Activity</div>',
     r'<div class="stat-label" data-i18n="revenue.stats.recentActivity.label">Recent Activity</div>',
     'Recent Activity label'),

    (r'<div class="stat-sublabel">Last 30 days</div>',
     r'<div class="stat-sublabel" data-i18n="revenue.stats.recentActivity.sublabel">Last 30 days</div>',
     'Last 30 days sublabel'),

    (r'<div class="stat-label">Unlinked Transactions</div>',
     r'<div class="stat-label" data-i18n="revenue.stats.unlinkedTransactions.label">Unlinked Transactions</div>',
     'Unlinked Transactions label'),

    (r'<div class="stat-sublabel">Total transactions without invoice</div>',
     r'<div class="stat-sublabel" data-i18n="revenue.stats.unlinkedTransactions.sublabel">Total transactions without invoice</div>',
     'Total transactions without invoice sublabel'),

    (r'<div class="stat-label">Unlinked Revenue Transactions</div>',
     r'<div class="stat-label" data-i18n="revenue.stats.unlinkedRevenue.label">Unlinked Revenue Transactions</div>',
     'Unlinked Revenue Transactions label'),

    (r'<div class="stat-sublabel">Positive amounts needing match</div>',
     r'<div class="stat-sublabel" data-i18n="revenue.stats.unlinkedRevenue.sublabel">Positive amounts needing match</div>',
     'Positive amounts needing match sublabel'),

    # Empty state messages
    (r'<h3>Great! All invoices are matched!</h3>',
     r'<h3 data-i18n="revenue.sections.unlinkedInvoices.empty">Great! All invoices are matched!</h3>',
     'All matched message'),

    (r'<p>No unlinked invoices found\. All invoices have been successfully matched to transactions\.</p>',
     r'<p data-i18n="revenue.sections.unlinkedInvoices.emptyDescription">No unlinked invoices found. All invoices have been successfully matched to transactions.</p>',
     'No unlinked found message'),

    (r'🔄 Refresh to Check for New Invoices',
     r'<span data-i18n="revenue.sections.unlinkedInvoices.refreshButton">🔄 Refresh to Check for New Invoices</span>',
     'Refresh button in empty state'),
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
with open('web_ui/templates/revenue.html', 'w', encoding='utf-8') as f:
    f.write(modified_content)

print("JavaScript translation attributes added to revenue.html:")
print("\n".join(changes_made))
print(f"\n✓ File updated successfully!")
