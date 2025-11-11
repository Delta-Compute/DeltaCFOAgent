/**
 * Transaction Detail Page JavaScript
 * Handles data loading, display, and interactions for transaction detail pages
 */

(function() {
    'use strict';

    // Global state
    let transactionData = null;

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        initializePage();
    });

    /**
     * Initialize the page
     */
    function initializePage() {
        setupTabNavigation();
        setupEventListeners();
        loadTransactionDetails();
    }

    /**
     * Setup tab navigation
     */
    function setupTabNavigation() {
        const tabButtons = document.querySelectorAll('.tab-button');

        tabButtons.forEach(button => {
            button.addEventListener('click', function() {
                const tabName = this.getAttribute('data-tab');
                switchTab(tabName);
            });
        });
    }

    /**
     * Switch between tabs
     */
    function switchTab(tabName) {
        // Update button states
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update content visibility
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`tab-${tabName}`).classList.add('active');
    }

    /**
     * Setup event listeners for actions
     */
    function setupEventListeners() {
        // Header actions
        document.getElementById('btn-edit-transaction')?.addEventListener('click', handleEditTransaction);
        document.getElementById('btn-export-transaction')?.addEventListener('click', handleExport);
    }

    /**
     * Load transaction details from API
     */
    async function loadTransactionDetails() {
        showLoading(true);

        try {
            const response = await fetch(API_ENDPOINT);
            const data = await response.json();

            if (data.success) {
                transactionData = data;
                renderTransactionDetails(data);
            } else {
                showToast('Failed to load transaction details: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error loading transaction details:', error);
            showToast('Error loading transaction details', 'error');
        } finally {
            showLoading(false);
        }
    }

    /**
     * Render all transaction details on the page
     */
    function renderTransactionDetails(data) {
        const transaction = data.transaction;
        const stats = data.statistics;

        // Update page title and subtitle
        document.getElementById('transaction-title').textContent = `Transaction ${transaction.transaction_id}`;
        document.getElementById('transaction-subtitle').textContent = `${transaction.description} - ${formatCurrency(transaction.amount, transaction.currency)}`;
        document.getElementById('transaction-id-breadcrumb').textContent = transaction.transaction_id.substring(0, 8);

        // Update status badges
        renderStatusBadges(transaction, stats);

        // Update quick info card
        renderQuickInfo(transaction);

        // Update sidebar stats
        renderSidebarStats(stats, transaction);

        // Render tab contents
        renderOverviewTab(transaction);
        renderDetailsTab(transaction);
        renderMatchesTab(data);

        // Render activity timeline
        if (window.ActivityTimeline && data.activity_history) {
            window.ActivityTimeline.render(data.activity_history, 'activity-timeline-container');
        }
    }

    /**
     * Render status badges
     */
    function renderStatusBadges(transaction, stats) {
        const statusBadge = document.getElementById('transaction-status-badge');
        const matchBadge = document.getElementById('transaction-match-badge');

        // Status badge based on amount
        if (transaction.amount > 0) {
            statusBadge.textContent = 'Income';
            statusBadge.className = 'status-badge approved';
        } else {
            statusBadge.textContent = 'Expense';
            statusBadge.className = 'status-badge pending';
        }

        // Match badge
        if (stats.is_matched) {
            matchBadge.textContent = 'Matched';
            matchBadge.className = 'match-badge matched';
        } else {
            matchBadge.textContent = 'Unmatched';
            matchBadge.className = 'match-badge unmatched';
        }
    }

    /**
     * Render quick info section
     */
    function renderQuickInfo(transaction) {
        document.getElementById('info-transaction-date').textContent = formatDate(transaction.date);
        document.getElementById('info-amount').textContent = formatCurrency(transaction.amount, transaction.currency || 'USD');

        // Category: Show accounting_category and subcategory
        const category = transaction.subcategory || transaction.accounting_category || 'Uncategorized';
        document.getElementById('info-category').textContent = category;

        // Origin and destination with display names if available
        document.getElementById('info-origin').textContent = transaction.origin_display || transaction.origin || 'N/A';
        document.getElementById('info-destination').textContent = transaction.destination_display || transaction.destination || 'N/A';

        // Business Unit is classified_entity
        document.getElementById('info-business-unit').textContent = transaction.classified_entity || 'N/A';
    }

    /**
     * Render sidebar statistics
     */
    function renderSidebarStats(stats, transaction) {
        const statsContainer = document.getElementById('sidebar-stats');
        if (!statsContainer) return;

        statsContainer.innerHTML = `
            <div class="stat-item">
                <span class="stat-label">View Count</span>
                <span class="stat-value">${stats.view_count || 0}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Last Viewed</span>
                <span class="stat-value">${stats.last_viewed_at ? formatDate(stats.last_viewed_at) : 'Never'}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Activities</span>
                <span class="stat-value">${stats.total_activities || 0}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Matched</span>
                <span class="stat-value">${stats.is_matched ? 'Yes' : 'No'}</span>
            </div>
        `;
    }

    /**
     * Render overview tab
     */
    function renderOverviewTab(transaction) {
        const detailsSection = document.getElementById('transaction-details');
        if (!detailsSection) return;

        detailsSection.innerHTML = `
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="detail-label">Transaction ID</span>
                    <span class="detail-value">${transaction.transaction_id}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Date</span>
                    <span class="detail-value">${formatDate(transaction.date)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Description</span>
                    <span class="detail-value">${transaction.description || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Amount</span>
                    <span class="detail-value">${formatCurrency(transaction.amount, transaction.currency)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Origin</span>
                    <span class="detail-value">${transaction.origin || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Destination</span>
                    <span class="detail-value">${transaction.destination || 'N/A'}</span>
                </div>
            </div>
        `;

        const classificationSection = document.getElementById('classification-details');
        if (!classificationSection) return;

        classificationSection.innerHTML = `
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="detail-label">Category</span>
                    <span class="detail-value">${transaction.category || 'Uncategorized'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Subcategory</span>
                    <span class="detail-value">${transaction.subcategory || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Business Unit</span>
                    <span class="detail-value">${transaction.business_unit || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Confidence</span>
                    <span class="detail-value">${transaction.confidence_score || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Justification</span>
                    <span class="detail-value">${transaction.justification || 'N/A'}</span>
                </div>
            </div>
        `;
    }

    /**
     * Render details tab
     */
    function renderDetailsTab(transaction) {
        const additionalInfo = document.getElementById('additional-info');
        if (!additionalInfo) return;

        additionalInfo.innerHTML = `
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="detail-label">Currency</span>
                    <span class="detail-value">${transaction.currency || 'USD'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">USD Equivalent</span>
                    <span class="detail-value">${transaction.usd_equivalent ? formatCurrency(transaction.usd_equivalent, 'USD') : 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Exchange Rate</span>
                    <span class="detail-value">${transaction.exchange_rate || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Created At</span>
                    <span class="detail-value">${formatDate(transaction.created_at)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Updated At</span>
                    <span class="detail-value">${transaction.updated_at ? formatDate(transaction.updated_at) : 'N/A'}</span>
                </div>
            </div>
        `;
    }

    /**
     * Render matches tab
     */
    function renderMatchesTab(data) {
        // Linked invoice
        const linkedInvoiceSection = document.getElementById('linked-invoice-section');
        if (linkedInvoiceSection) {
            if (data.linked_invoice) {
                const invoice = data.linked_invoice;
                linkedInvoiceSection.innerHTML = `
                    <div class="linked-record-card">
                        <h4>Invoice #${invoice.invoice_number}</h4>
                        <p>${invoice.vendor_name} - ${formatCurrency(invoice.total_amount, invoice.currency)}</p>
                        <a href="/invoices/${invoice.id}" class="btn btn-sm btn-secondary">View Invoice</a>
                    </div>
                `;
            } else {
                linkedInvoiceSection.innerHTML = '<p class="empty-state-text">No linked invoice</p>';
            }
        }

        // Linked payslip
        const linkedPayslipSection = document.getElementById('linked-payslip-section');
        if (linkedPayslipSection) {
            if (data.linked_payslip) {
                const payslip = data.linked_payslip;
                linkedPayslipSection.innerHTML = `
                    <div class="linked-record-card">
                        <h4>Payslip #${payslip.payslip_number}</h4>
                        <p>${payslip.employee_name} - ${formatCurrency(payslip.net_amount, payslip.currency)}</p>
                        <a href="/payslips/${payslip.id}" class="btn btn-sm btn-secondary">View Payslip</a>
                    </div>
                `;
            } else {
                linkedPayslipSection.innerHTML = '<p class="empty-state-text">No linked payslip</p>';
            }
        }

        // Potential matches
        const potentialMatchesSection = document.getElementById('potential-matches-section');
        if (potentialMatchesSection) {
            if (data.potential_matches && data.potential_matches.length > 0) {
                potentialMatchesSection.innerHTML = `<p>Found ${data.potential_matches.length} potential matches</p>`;
            } else {
                potentialMatchesSection.innerHTML = '<p class="empty-state-text">No potential matches found</p>';
            }
        }
    }

    /**
     * Event Handlers
     */
    function handleEditTransaction() {
        alert('Edit transaction functionality coming soon');
    }

    function handleExport() {
        alert('Export functionality coming soon');
    }

    /**
     * Utility Functions
     */
    function formatCurrency(amount, currency) {
        const value = parseFloat(amount);
        if (isNaN(value)) return 'N/A';

        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency || 'USD'
        }).format(value);
    }

    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    function showLoading(show) {
        const loader = document.getElementById('loading-indicator');
        if (loader) {
            loader.style.display = show ? 'block' : 'none';
        }
    }

    function showToast(message, type) {
        console.log(`[${type.toUpperCase()}] ${message}`);
        // Toast implementation would go here
    }

})();
