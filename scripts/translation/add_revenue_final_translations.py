#!/usr/bin/env python3
"""
Add final batch of i18n translations to revenue.html
"""

import re

# Read the file
with open('web_ui/templates/revenue.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Define final batch of replacements
replacements = [
    # Button texts in cards
    (r'⚡ Quick Match\s*</',
     r'<span data-i18n="revenue.controls.buttons.quickMatch">⚡ Quick Match</span></',
     'Quick Match button text'),

    (r'👁️ View Details\s*</',
     r'<span data-i18n="revenue.controls.buttons.viewDetails">👁️ View Details</span></',
     'View Details button text'),

    (r'✅ Confirm Match\s*</',
     r'<span data-i18n="revenue.controls.buttons.confirmMatch">✅ Confirm Match</span></',
     'Confirm Match button text'),

    (r'❌ Reject Match\s*</',
     r'<span data-i18n="revenue.controls.buttons.rejectMatch">❌ Reject Match</span></',
     'Reject Match button text'),

    # Table headers
    (r'📄 Invoice Details</th>',
     r'<span data-i18n="revenue.matchCard.invoiceDetails">📄 Invoice Details</span></th>',
     'Invoice Details header'),

    (r'💰 Transaction Details</th>',
     r'<span data-i18n="revenue.matchCard.transactionDetails">💰 Transaction Details</span></th>',
     'Transaction Details header'),

    # Pagination
    (r'← Previous\s*</',
     r'<span data-i18n="revenue.pagination.previous">← Previous</span></',
     'Previous button'),

    (r'Next →\s*</',
     r'<span data-i18n="revenue.pagination.next">Next →</span></',
     'Next button'),

    (r'<label for="per-page-select">Per page:</label>',
     r'<label for="per-page-select" data-i18n="revenue.pagination.perPage">Per page:</label>',
     'Per page label'),

    # Status texts
    (r'Awaiting matching',
     r'<span data-i18n="revenue.invoiceCard.status">Awaiting matching</span>',
     'Awaiting matching status'),

    (r'No transaction match',
     r'<span data-i18n="revenue.matchCard.noMatch">No transaction match</span>',
     'No match text'),

    (r'Run matching to find candidates',
     r'<span data-i18n="revenue.matchCard.runMatching">Run matching to find candidates</span>',
     'Run matching suggestion'),

    # Help text
    (r'Use Quick Match to automatically find potential transaction matches\.',
     r'<span data-i18n="revenue.sections.unlinkedInvoices.quickMatchHelp">Use Quick Match to automatically find potential transaction matches.</span>',
     'Quick match help text'),
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
        changes_made.append(f"  ✗ {description}: NOT FOUND (may already be translated)")

# Write modified content
with open('web_ui/templates/revenue.html', 'w', encoding='utf-8') as f:
    f.write(modified_content)

print("Final translation attributes added to revenue.html:")
print("\n".join(changes_made))
print(f"\n✓ File updated successfully!")
print("\nNote: Some elements may not be found if they're dynamically generated or already translated.")
