#!/usr/bin/env python3
"""
Add i18n translations to all detail pages (transaction, invoice, payslip)
"""

import re

def translate_file(filepath, replacements, page_name):
    """Apply translations to a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"⚠️  File not found: {filepath}")
        return 0

    modified_content = content
    changes_made = []

    for pattern, replacement, description in replacements:
        count = len(re.findall(pattern, modified_content))
        if count > 0:
            modified_content = re.sub(pattern, replacement, modified_content)
            changes_made.append(f"  ✓ {description}: {count}")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(modified_content)

    print(f"\n{page_name}:")
    print("\n".join([c for c in changes_made if "✓" in c]))
    return len([c for c in changes_made if "✓" in c])

# Common replacements for all detail pages
common_replacements = [
    (r'<span class="info-label">Date</span>',
     r'<span class="info-label" data-i18n="detail.labels.date">Date</span>',
     'Date label'),

    (r'<span class="info-label">Amount</span>',
     r'<span class="info-label" data-i18n="detail.labels.amount">Amount</span>',
     'Amount label'),

    (r'<span class="info-label">Status</span>',
     r'<span class="info-label" data-i18n="detail.labels.status">Status</span>',
     'Status label'),

    (r'>Edit<',
     r'><span data-i18n="detail.buttons.edit">Edit</span><',
     'Edit button'),

    (r'>Export<',
     r'><span data-i18n="detail.buttons.export">Export</span><',
     'Export button'),

    (r'>Download<',
     r'><span data-i18n="detail.buttons.download">Download</span><',
     'Download button'),

    (r'<span id="[^"]*-title">Transaction Details</span>',
     r'<span id="transaction-title" data-i18n="detail.transaction.title">Transaction Details</span>',
     'Transaction title'),

    (r'<span id="[^"]*-title">Invoice Details</span>',
     r'<span id="invoice-title" data-i18n="detail.invoice.title">Invoice Details</span>',
     'Invoice title'),

    (r'<span id="[^"]*-title">Payslip Details</span>',
     r'<span id="payslip-title" data-i18n="detail.payslip.title">Payslip Details</span>',
     'Payslip title'),
]

# Transaction-specific
transaction_replacements = common_replacements + [
    (r'<a href="/transactions"[^>]*>Transactions</a>',
     r'<a href="/transactions" class="breadcrumb-link"><span data-i18n="detail.transaction.breadcrumb">Transactions</span></a>',
     'Transactions breadcrumb'),

    (r'<span class="info-label">Category</span>',
     r'<span class="info-label" data-i18n="detail.transaction.category">Category</span>',
     'Category label'),

    (r'<span class="info-label">Origin</span>',
     r'<span class="info-label" data-i18n="detail.transaction.origin">Origin</span>',
     'Origin label'),

    (r'<span class="info-label">Destination</span>',
     r'<span class="info-label" data-i18n="detail.transaction.destination">Destination</span>',
     'Destination label'),

    (r'<span class="info-label">Business Unit</span>',
     r'<span class="info-label" data-i18n="detail.transaction.businessUnit">Business Unit</span>',
     'Business Unit label'),

    (r'<h3 class="card-title">Transaction Details</h3>',
     r'<h3 class="card-title" data-i18n="detail.transaction.cardTitle">Transaction Details</h3>',
     'Transaction Details card'),

    (r'<h3 class="card-title">Classification</h3>',
     r'<h3 class="card-title" data-i18n="detail.transaction.classification">Classification</h3>',
     'Classification card'),

    (r'<h3 class="card-title">Additional Information</h3>',
     r'<h3 class="card-title" data-i18n="detail.transaction.additionalInfo">Additional Information</h3>',
     'Additional Info card'),

    (r'<h3 class="card-title">Linked Invoice</h3>',
     r'<h3 class="card-title" data-i18n="detail.transaction.linkedInvoice">Linked Invoice</h3>',
     'Linked Invoice card'),

    (r'<h3 class="card-title">Linked Payslip</h3>',
     r'<h3 class="card-title" data-i18n="detail.transaction.linkedPayslip">Linked Payslip</h3>',
     'Linked Payslip card'),

    (r'<h3 class="card-title">Potential Matches</h3>',
     r'<h3 class="card-title" data-i18n="detail.transaction.potentialMatches">Potential Matches</h3>',
     'Potential Matches card'),
]

# Invoice-specific
invoice_replacements = common_replacements + [
    (r'<a href="/invoices"[^>]*>Invoices</a>',
     r'<a href="/invoices" class="breadcrumb-link"><span data-i18n="detail.invoice.breadcrumb">Invoices</span></a>',
     'Invoices breadcrumb'),

    (r'<span class="info-label">Invoice Number</span>',
     r'<span class="info-label" data-i18n="detail.invoice.invoiceNumber">Invoice Number</span>',
     'Invoice Number label'),

    (r'<span class="info-label">Vendor</span>',
     r'<span class="info-label" data-i18n="detail.invoice.vendor">Vendor</span>',
     'Vendor label'),

    (r'<span class="info-label">Invoice Date</span>',
     r'<span class="info-label" data-i18n="detail.invoice.invoiceDate">Invoice Date</span>',
     'Invoice Date label'),

    (r'<span class="info-label">Due Date</span>',
     r'<span class="info-label" data-i18n="detail.invoice.dueDate">Due Date</span>',
     'Due Date label'),

    (r'>Mark as Paid<',
     r'><span data-i18n="detail.invoice.markAsPaid">Mark as Paid</span><',
     'Mark as Paid button'),

    (r'<h3 class="card-title">Invoice Summary</h3>',
     r'<h3 class="card-title" data-i18n="detail.invoice.summary">Invoice Summary</h3>',
     'Invoice Summary card'),

    (r'<h3 class="card-title">Line Items</h3>',
     r'<h3 class="card-title" data-i18n="detail.invoice.lineItems">Line Items</h3>',
     'Line Items card'),

    (r'<h3 class="card-title">Complete Invoice Details</h3>',
     r'<h3 class="card-title" data-i18n="detail.invoice.completeDetails">Complete Invoice Details</h3>',
     'Complete Details card'),

    (r'<h3 class="card-title">Payment Information</h3>',
     r'<h3 class="card-title" data-i18n="detail.invoice.paymentInfo">Payment Information</h3>',
     'Payment Info card'),

    (r'Linked Transaction',
     r'<span data-i18n="detail.invoice.linkedTransaction">Linked Transaction</span>',
     'Linked Transaction'),

    (r'No transaction linked',
     r'<span data-i18n="detail.invoice.noTransactionLinked">No transaction linked</span>',
     'No transaction linked'),

    (r'Potential Matches',
     r'<span data-i18n="detail.invoice.potentialMatches">Potential Matches</span>',
     'Potential Matches'),

    (r'>Find Matching Transactions<',
     r'><span data-i18n="detail.invoice.findMatches">Find Matching Transactions</span><',
     'Find Matches button'),

    (r'>Send Payment Reminder<',
     r'><span data-i18n="detail.invoice.sendReminder">Send Payment Reminder</span><',
     'Send Reminder button'),

    (r'>Duplicate Invoice<',
     r'><span data-i18n="detail.invoice.duplicate">Duplicate Invoice</span><',
     'Duplicate button'),

    (r'>Delete Invoice<',
     r'><span data-i18n="detail.invoice.delete">Delete Invoice</span><',
     'Delete button'),
]

# Payslip-specific
payslip_replacements = common_replacements + [
    (r'<a href="/workforce"[^>]*>Workforce</a>',
     r'<a href="/workforce" class="breadcrumb-link"><span data-i18n="detail.payslip.breadcrumb">Workforce</span></a>',
     'Workforce breadcrumb'),

    (r'<span class="info-label">Payslip Number</span>',
     r'<span class="info-label" data-i18n="detail.payslip.payslipNumber">Payslip Number</span>',
     'Payslip Number label'),

    (r'<span class="info-label">Employee</span>',
     r'<span class="info-label" data-i18n="detail.payslip.employee">Employee</span>',
     'Employee label'),

    (r'<span class="info-label">Net Amount</span>',
     r'<span class="info-label" data-i18n="detail.payslip.netAmount">Net Amount</span>',
     'Net Amount label'),

    (r'<span class="info-label">Pay Period</span>',
     r'<span class="info-label" data-i18n="detail.payslip.payPeriod">Pay Period</span>',
     'Pay Period label'),

    (r'<span class="info-label">Payment Date</span>',
     r'<span class="info-label" data-i18n="detail.payslip.paymentDate">Payment Date</span>',
     'Payment Date label'),

    (r'<h3 class="card-title">Payslip Summary</h3>',
     r'<h3 class="card-title" data-i18n="detail.payslip.summary">Payslip Summary</h3>',
     'Payslip Summary card'),

    (r'<h3 class="card-title">Earnings & Deductions</h3>',
     r'<h3 class="card-title" data-i18n="detail.payslip.earningsDeductions">Earnings & Deductions</h3>',
     'Earnings & Deductions card'),

    (r'<h3 class="card-title">Employee Information</h3>',
     r'<h3 class="card-title" data-i18n="detail.payslip.employeeInfo">Employee Information</h3>',
     'Employee Info card'),

    (r'<h3 class="card-title">Linked Transaction</h3>',
     r'<h3 class="card-title" data-i18n="detail.payslip.linkedTransaction">Linked Transaction</h3>',
     'Linked Transaction card'),

    (r'<h3 class="card-title">Potential Transaction Matches</h3>',
     r'<h3 class="card-title" data-i18n="detail.payslip.potentialMatches">Potential Transaction Matches</h3>',
     'Potential Matches card'),
]

# Run translations
print("="*60)
print("TRANSLATING DETAIL PAGES")
print("="*60)

total = 0
total += translate_file('web_ui/templates/transaction_detail.html', transaction_replacements, 'transaction_detail.html')
total += translate_file('web_ui/templates/invoice_detail.html', invoice_replacements, 'invoice_detail.html')
total += translate_file('web_ui/templates/payslip_detail.html', payslip_replacements, 'payslip_detail.html')

print("\n" + "="*60)
print(f"✓ COMPLETED: {total} translations applied to detail pages")
print("="*60)
