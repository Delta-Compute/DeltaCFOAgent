#!/usr/bin/env python3
"""
Add i18n translations to revenue.html
Maps English text to translation keys from en.json/pt.json
"""

import re

# Read the file
with open('web_ui/templates/revenue.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Define replacements: (pattern, replacement, description)
replacements = [
    # Header
    (r'(<h1>)💰 Revenue Recognition Dashboard(</h1>)',
     r'\1<span data-i18n="revenue.header.title">💰 Revenue Recognition Dashboard</span>\2',
     'Main title'),

    (r'(<p[^>]*>)Automated invoice-transaction matching with AI intelligence(</p>)',
     r'\1<span data-i18n="revenue.header.subtitle">Automated invoice-transaction matching with AI intelligence</span>\2',
     'Subtitle'),

    # Matching Controls Section
    (r'(<h2>)🔗 Invoice Matching(</h2>)',
     r'\1<span data-i18n="revenue.controls.matching.title">🔗 Invoice Matching</span>\2',
     'Invoice Matching title'),

    (r'Automatically find and link invoices to transactions with AI-powered matching\.',
     r'<span data-i18n="revenue.controls.matching.description">Automatically find and link invoices to transactions with AI-powered matching.</span>',
     'Matching description'),

    # Buttons - need to preserve onclick and other attributes
    (r'(onclick="runUltraFastMatching\(false\)"[^>]*>)\s*▶️ Run Match\s*(<)',
     r'\1<span data-i18n="revenue.controls.buttons.runMatch">▶️ Run Match</span>\2',
     'Run Match button'),

    (r'(onclick="runUltraFastMatching\(true\)"[^>]*>)\s*⚡ Auto-Match HIGH\s*(<)',
     r'\1<span data-i18n="revenue.controls.buttons.autoMatchHigh">⚡ Auto-Match HIGH</span>\2',
     'Auto-Match button'),

    (r'(onclick="toggleAdvancedOptions\(\)"[^>]*>)\s*⚙️ More Options\s*(<)',
     r'\1<span data-i18n="revenue.controls.buttons.moreOptions">⚙️ More Options</span>\2',
     'More Options button'),

    (r'(onclick="refreshData\(\)"[^>]*>)\s*🔄 Refresh Data\s*(<)',
     r'\1<span data-i18n="revenue.controls.buttons.refreshData">🔄 Refresh Data</span>\2',
     'Refresh Data button'),

    (r'(onclick="showMatchedPairs\(\)"[^>]*>)\s*📋 View All Matches\s*(<)',
     r'\1<span data-i18n="revenue.controls.buttons.viewAllMatches">📋 View All Matches</span>\2',
     'View All Matches button'),

    # Progress messages
    (r'(<strong>)🚀 Initializing matching process\.\.\.(</strong>)',
     r'\1<span data-i18n="revenue.controls.progress.initializing">🚀 Initializing matching process...</span>\2',
     'Initializing message'),

    (r'📊 Status: <span id="progress-status">Starting\.\.\.</span>',
     r'<span data-i18n="revenue.controls.progress.status">📊 Status:</span> <span id="progress-status" data-i18n="revenue.controls.progress.starting">Starting...</span>',
     'Status label'),

    (r'⏱️ Time: <span id="progress-time">Calculating\.\.\.</span>',
     r'<span data-i18n="revenue.controls.progress.time">⏱️ Time:</span> <span id="progress-time" data-i18n="revenue.controls.progress.calculating">Calculating...</span>',
     'Time label'),

    (r'🔧 Optimizations: <span id="progress-optimizations">Loading\.\.\.</span>',
     r'<span data-i18n="revenue.controls.progress.optimizations">🔧 Optimizations:</span> <span id="progress-optimizations" data-i18n="revenue.controls.progress.loading">Loading...</span>',
     'Optimizations label'),

    # Section titles
    (r'(<h2 class="section-title">)\s*🔍 Pending Matches for Review',
     r'\1<span data-i18n="revenue.sections.pendingMatches.title">🔍 Pending Matches for Review</span>',
     'Pending Matches title'),

    (r'(<h2 class="section-title">)\s*🔗 Unlinked Invoices Ready for Matching',
     r'\1<span data-i18n="revenue.sections.unlinkedInvoices.title">🔗 Unlinked Invoices Ready for Matching</span>',
     'Unlinked Invoices title'),

    (r'(<h2 class="section-title">)\s*✅ Recent Confirmed Matches',
     r'\1<span data-i18n="revenue.sections.recentMatches.title">✅ Recent Confirmed Matches</span>',
     'Recent Matches title'),

    # Filter tabs
    (r'(onclick="filterMatches\(\'all\'\)">)All(<)',
     r'\1<span data-i18n="revenue.filters.all">All</span>\2',
     'All filter'),

    (r'(onclick="filterMatches\(\'high\'\)">)High Confidence(<)',
     r'\1<span data-i18n="revenue.filters.highConfidence">High Confidence</span>\2',
     'High Confidence filter'),

    (r'(onclick="filterMatches\(\'medium\'\)">)Medium Confidence(<)',
     r'\1<span data-i18n="revenue.filters.mediumConfidence">Medium Confidence</span>\2',
     'Medium Confidence filter'),

    (r'(onclick="filterUnlinkedInvoices\(\'all\'\)">)All Unlinked(<)',
     r'\1<span data-i18n="revenue.filters.allUnlinked">All Unlinked</span>\2',
     'All Unlinked filter'),

    (r'(onclick="filterUnlinkedInvoices\(\'recent\'\)">)Recent \(30 days\)(<)',
     r'\1<span data-i18n="revenue.filters.recent30Days">Recent (30 days)</span>\2',
     'Recent filter'),

    (r'(onclick="filterUnlinkedInvoices\(\'high-value\'\)">)High Value \(\$1000\+\)(<)',
     r'\1<span data-i18n="revenue.filters.highValue">High Value ($1000+)</span>\2',
     'High Value filter'),

    # Bulk action buttons
    (r'(<span id="selection-count">)0 matches selected(</span>)',
     r'\1<span data-i18n="revenue.controls.selected.noSelection">0 matches selected</span>\2',
     'Selection count'),

    (r'(id="bulk-approve-btn"[^>]*>)\s*✅ Approve Selected\s*(<)',
     r'\1<span data-i18n="revenue.controls.buttons.approveSelected">✅ Approve Selected</span>\2',
     'Approve Selected button'),

    (r'(id="bulk-reject-btn"[^>]*>)\s*❌ Reject Selected\s*(<)',
     r'\1<span data-i18n="revenue.controls.buttons.rejectSelected">❌ Reject Selected</span>\2',
     'Reject Selected button'),

    (r'(id="clear-selection-btn"[^>]*>)\s*🔄 Clear Selection\s*(<)',
     r'\1<span data-i18n="revenue.controls.buttons.clearSelection">🔄 Clear Selection</span>\2',
     'Clear Selection button'),

    # More buttons
    (r'(onclick="loadUnlinkedInvoices\(\)"[^>]*>)\s*🔄 Refresh Unlinked\s*(<)',
     r'\1<span data-i18n="revenue.controls.buttons.refreshUnlinked">🔄 Refresh Unlinked</span>\2',
     'Refresh Unlinked button'),

    (r'(onclick="quickMatchAll\(\)"[^>]*>)\s*⚡ Quick Match All\s*(<)',
     r'\1<span data-i18n="revenue.controls.buttons.quickMatchAll">⚡ Quick Match All</span>\2',
     'Quick Match All button'),

    (r'(onclick="loadMatchedPairs\(\)"[^>]*>)\s*View All Confirmed\s*(<)',
     r'\1<span data-i18n="revenue.controls.buttons.viewAllConfirmed">View All Confirmed</span>\2',
     'View All Confirmed button'),
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

print("Translation attributes added to revenue.html:")
print("\n".join(changes_made))
print(f"\n✓ File updated successfully!")
