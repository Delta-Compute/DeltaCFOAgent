#!/usr/bin/env python3
"""
Add i18n translations to whitelisted_accounts.html
"""

import re

# Read the file
with open('web_ui/templates/whitelisted_accounts.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Define replacements
replacements = [
    # Title and header
    (r'(<title>)White Listed Accounts - Delta CFO Agent(</title>)',
     r'\1<span data-i18n="whitelistedAccounts.pageTitle">White Listed Accounts</span> - Delta CFO Agent\2',
     'Page title'),

    (r'(<h1 class="page-title">)White Listed Accounts(</h1>)',
     r'\1<span data-i18n="whitelistedAccounts.title">White Listed Accounts</span>\2',
     'Main heading'),

    (r'(<p class="page-subtitle">)Manage your bank accounts and cryptocurrency wallets(</p>)',
     r'\1<span data-i18n="whitelistedAccounts.subtitle">Manage your bank accounts and cryptocurrency wallets</span>\2',
     'Subtitle'),

    # Tabs
    (r'(class="tab-button[^"]*"[^>]*>)\s*🏦 Bank Accounts\s*(<)',
     r'\1<span data-i18n="whitelistedAccounts.tabs.bankAccounts">🏦 Bank Accounts</span>\2',
     'Bank Accounts tab'),

    (r'(class="tab-button[^"]*"[^>]*>)\s*₿ Crypto Wallets\s*(<)',
     r'\1<span data-i18n="whitelistedAccounts.tabs.cryptoWallets">₿ Crypto Wallets</span>\2',
     'Crypto Wallets tab'),

    # Buttons
    (r'(class="add-button"[^>]*>)\s*➕ Add Bank Account\s*(<)',
     r'\1<span data-i18n="whitelistedAccounts.bankAccounts.addButton">➕ Add Bank Account</span>\2',
     'Add Bank Account button'),

    (r'(class="add-button"[^>]*>)\s*➕ Add Crypto Wallet\s*(<)',
     r'\1<span data-i18n="whitelistedAccounts.cryptoWallets.addButton">➕ Add Crypto Wallet</span>\2',
     'Add Crypto Wallet button'),

    # Modal titles
    (r'(<h2 class="modal-title" id="bankModalTitle">)Add Bank Account(</h2>)',
     r'\1<span data-i18n="whitelistedAccounts.bankAccounts.modal.titleAdd">Add Bank Account</span>\2',
     'Add Bank Account modal title'),

    (r'(<h2 class="modal-title" id="walletModalTitle">)Add Crypto Wallet(</h2>)',
     r'\1<span data-i18n="whitelistedAccounts.cryptoWallets.modal.titleAdd">Add Crypto Wallet</span>\2',
     'Add Crypto Wallet modal title'),

    # Bank Account form labels
    (r'(<label class="form-label">)Account Name \*(</label>)',
     r'\1<span data-i18n="whitelistedAccounts.bankAccounts.modal.accountName">Account Name</span> <span data-i18n="whitelistedAccounts.bankAccounts.modal.required">*</span>\2',
     'Account Name label'),

    (r'(<label class="form-label">)Bank Name \*(</label>)',
     r'\1<span data-i18n="whitelistedAccounts.bankAccounts.modal.bankName">Bank Name</span> <span data-i18n="whitelistedAccounts.bankAccounts.modal.required">*</span>\2',
     'Bank Name label'),

    (r'(<label class="form-label">)Account Number(</label>)',
     r'\1<span data-i18n="whitelistedAccounts.bankAccounts.modal.accountNumber">Account Number</span>\2',
     'Account Number label'),

    (r'(<label class="form-label">)Account Type \*(</label>)',
     r'\1<span data-i18n="whitelistedAccounts.bankAccounts.modal.accountType">Account Type</span> <span data-i18n="whitelistedAccounts.bankAccounts.modal.required">*</span>\2',
     'Account Type label'),

    (r'(<label class="form-label">)Currency \*(</label>)',
     r'\1<span data-i18n="whitelistedAccounts.bankAccounts.modal.currency">Currency</span> <span data-i18n="whitelistedAccounts.bankAccounts.modal.required">*</span>\2',
     'Currency label'),

    (r'(<label class="form-label">)Status(</label>)',
     r'\1<span data-i18n="whitelistedAccounts.bankAccounts.modal.status">Status</span>\2',
     'Status label'),

    (r'(<label class="form-label">)Notes(</label>)',
     r'\1<span data-i18n="whitelistedAccounts.bankAccounts.modal.notes">Notes</span>\2',
     'Notes label'),

    # Bank Account Type options
    (r'<option value="">Select account type</option>',
     r'<option value=""><span data-i18n="whitelistedAccounts.bankAccounts.modal.selectAccountType">Select account type</span></option>',
     'Select account type'),

    (r'<option value="checking">Checking</option>',
     r'<option value="checking"><span data-i18n="whitelistedAccounts.accountTypes.checking">Checking</span></option>',
     'Checking option'),

    (r'<option value="savings">Savings</option>',
     r'<option value="savings"><span data-i18n="whitelistedAccounts.accountTypes.savings">Savings</span></option>',
     'Savings option'),

    (r'<option value="credit">Credit</option>',
     r'<option value="credit"><span data-i18n="whitelistedAccounts.accountTypes.credit">Credit</span></option>',
     'Credit option'),

    (r'<option value="investment">Investment</option>',
     r'<option value="investment"><span data-i18n="whitelistedAccounts.accountTypes.investment">Investment</span></option>',
     'Investment option'),

    (r'<option value="loan">Loan</option>',
     r'<option value="loan"><span data-i18n="whitelistedAccounts.accountTypes.loan">Loan</span></option>',
     'Loan option'),

    # Status options
    (r'<option value="active">Active</option>',
     r'<option value="active"><span data-i18n="whitelistedAccounts.status.active">Active</span></option>',
     'Active status'),

    (r'<option value="inactive">Inactive</option>',
     r'<option value="inactive"><span data-i18n="whitelistedAccounts.status.inactive">Inactive</span></option>',
     'Inactive status'),

    (r'<option value="closed">Closed</option>',
     r'<option value="closed"><span data-i18n="whitelistedAccounts.status.closed">Closed</span></option>',
     'Closed status'),

    # Crypto Wallet form labels
    (r'(<label class="form-label">)Wallet Name \*(</label>)',
     r'\1<span data-i18n="whitelistedAccounts.cryptoWallets.modal.walletName">Wallet Name</span> <span data-i18n="whitelistedAccounts.cryptoWallets.modal.required">*</span>\2',
     'Wallet Name label'),

    (r'(<label class="form-label">)Wallet Address \*(</label>)',
     r'\1<span data-i18n="whitelistedAccounts.cryptoWallets.modal.walletAddress">Wallet Address</span> <span data-i18n="whitelistedAccounts.cryptoWallets.modal.required">*</span>\2',
     'Wallet Address label'),

    (r'(<label class="form-label">)Wallet Type \*(</label>)',
     r'\1<span data-i18n="whitelistedAccounts.cryptoWallets.modal.walletType">Wallet Type</span> <span data-i18n="whitelistedAccounts.cryptoWallets.modal.required">*</span>\2',
     'Wallet Type label'),

    (r'(<label class="form-label">)Blockchain \*(</label>)',
     r'\1<span data-i18n="whitelistedAccounts.cryptoWallets.modal.blockchain">Blockchain</span> <span data-i18n="whitelistedAccounts.cryptoWallets.modal.required">*</span>\2',
     'Blockchain label'),

    # Wallet Type options
    (r'<option value="">Select wallet type</option>',
     r'<option value=""><span data-i18n="whitelistedAccounts.cryptoWallets.modal.selectWalletType">Select wallet type</span></option>',
     'Select wallet type'),

    (r'<option value="hot">Hot Wallet</option>',
     r'<option value="hot"><span data-i18n="whitelistedAccounts.walletTypes.hot">Hot Wallet</span></option>',
     'Hot Wallet option'),

    (r'<option value="cold">Cold Wallet</option>',
     r'<option value="cold"><span data-i18n="whitelistedAccounts.walletTypes.cold">Cold Wallet</span></option>',
     'Cold Wallet option'),

    (r'<option value="exchange">Exchange</option>',
     r'<option value="exchange"><span data-i18n="whitelistedAccounts.walletTypes.exchange">Exchange</span></option>',
     'Exchange option'),

    (r'<option value="hardware">Hardware Wallet</option>',
     r'<option value="hardware"><span data-i18n="whitelistedAccounts.walletTypes.hardware">Hardware Wallet</span></option>',
     'Hardware Wallet option'),

    # Modal buttons
    (r'(class="btn btn-secondary"[^>]*onclick="closeBankModal\(\)">)\s*Cancel\s*(<)',
     r'\1<span data-i18n="whitelistedAccounts.bankAccounts.modal.cancelButton">Cancel</span>\2',
     'Bank modal cancel button'),

    (r'(class="btn btn-primary"[^>]*type="submit">)\s*Save Bank Account\s*(<)',
     r'\1<span data-i18n="whitelistedAccounts.bankAccounts.modal.saveButton">Save Bank Account</span>\2',
     'Bank modal save button'),

    (r'(class="btn btn-secondary"[^>]*onclick="closeWalletModal\(\)">)\s*Cancel\s*(<)',
     r'\1<span data-i18n="whitelistedAccounts.cryptoWallets.modal.cancelButton">Cancel</span>\2',
     'Wallet modal cancel button'),

    (r'(class="btn btn-primary"[^>]*type="submit">)\s*Save Wallet\s*(<)',
     r'\1<span data-i18n="whitelistedAccounts.cryptoWallets.modal.saveButton">Save Wallet</span>\2',
     'Wallet modal save button'),
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
with open('web_ui/templates/whitelisted_accounts.html', 'w', encoding='utf-8') as f:
    f.write(modified_content)

print("Translation attributes added to whitelisted_accounts.html:")
print("\n".join(changes_made))
successful = len([c for c in changes_made if "✓" in c])
print(f"\n✓ File updated successfully! {successful} translations applied.")
