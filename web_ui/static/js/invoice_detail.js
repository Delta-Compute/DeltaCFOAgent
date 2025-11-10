/**
 * Invoice Detail Page JavaScript
 * Handles data loading, display, and interactions for invoice detail pages
 */

(function() {
    'use strict';

    // Global state
    let invoiceData = null;

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
        loadInvoiceDetails();
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
        document.getElementById('btn-edit-invoice')?.addEventListener('click', handleEditInvoice);
        document.getElementById('btn-mark-paid')?.addEventListener('click', handleMarkPaid);
        document.getElementById('btn-download-pdf')?.addEventListener('click', handleDownloadPDF);

        // Quick actions
        document.getElementById('action-find-matches')?.addEventListener('click', handleFindMatches);
        document.getElementById('action-send-reminder')?.addEventListener('click', handleSendReminder);
        document.getElementById('action-duplicate')?.addEventListener('click', handleDuplicate);
        document.getElementById('action-delete')?.addEventListener('click', handleDelete);
    }

    /**
     * Load invoice details from API
     */
    async function loadInvoiceDetails() {
        showLoading(true);

        try {
            const response = await fetch(API_ENDPOINT);
            const data = await response.json();

            if (data.success) {
                invoiceData = data;
                renderInvoiceDetails(data);
            } else {
                showToast('Failed to load invoice details: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error loading invoice details:', error);
            showToast('Error loading invoice details', 'error');
        } finally {
            showLoading(false);
        }
    }

    /**
     * Render all invoice details on the page
     */
    function renderInvoiceDetails(data) {
        const invoice = data.invoice;
        const stats = data.statistics;

        // Update page title and subtitle
        document.getElementById('invoice-title').textContent = `Invoice ${invoice.invoice_number}`;
        document.getElementById('invoice-subtitle').textContent = `${invoice.vendor_name} - ${formatCurrency(invoice.total_amount, invoice.currency)}`;
        document.getElementById('invoice-number-breadcrumb').textContent = invoice.invoice_number;

        // Update status badges
        renderStatusBadges(invoice, stats);

        // Update quick info card
        renderQuickInfo(invoice);

        // Update sidebar stats
        renderSidebarStats(stats, invoice);

        // Render tab contents
        renderOverviewTab(invoice);
        renderDetailsTab(invoice);
        renderMatchesTab(data);

        // Render activity timeline
        if (window.ActivityTimeline && data.activity_history) {
            window.ActivityTimeline.render(data.activity_history, 'activity-timeline-container');
        }

        // Render related records
        renderRelatedRecords(data);
    }

    /**
     * Render status badges
     */
    function renderStatusBadges(invoice, stats) {
        const statusBadge = document.getElementById('invoice-status-badge');
        const matchBadge = document.getElementById('invoice-match-badge');

        // Status badge
        statusBadge.textContent = invoice.status || 'Pending';
        statusBadge.className = `status-badge ${(invoice.status || 'pending').toLowerCase()}`;

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
     * Render quick info card
     */
    function renderQuickInfo(invoice) {
        document.getElementById('info-invoice-number').textContent = invoice.invoice_number || 'N/A';
        document.getElementById('info-vendor-name').textContent = invoice.vendor_name || 'N/A';
        document.getElementById('info-total-amount').textContent = formatCurrency(invoice.total_amount, invoice.currency);
        document.getElementById('info-invoice-date').textContent = formatDate(invoice.invoice_date);
        document.getElementById('info-due-date').textContent = formatDate(invoice.due_date);
        document.getElementById('info-status').textContent = invoice.status || 'Pending';
    }

    /**
     * Render sidebar statistics
     */
    function renderSidebarStats(stats, invoice) {
        document.getElementById('stat-view-count').textContent = stats.view_count || 0;
        document.getElementById('stat-activity-count').textContent = stats.total_activities || 0;
        document.getElementById('stat-last-viewed').textContent = stats.last_viewed_at ? formatDateTime(stats.last_viewed_at) : 'Never';
        document.getElementById('stat-match-status').textContent = stats.is_matched ? 'Matched' : 'Unmatched';
    }

    /**
     * Render overview tab
     */
    function renderOverviewTab(invoice) {
        // Invoice summary
        const summaryHTML = `
            <div class="details-grid">
                <div class="detail-item">
                    <span class="detail-item-label">Vendor</span>
                    <span class="detail-item-value">${invoice.vendor_name || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-item-label">Invoice Date</span>
                    <span class="detail-item-value">${formatDate(invoice.invoice_date)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-item-label">Due Date</span>
                    <span class="detail-item-value">${formatDate(invoice.due_date)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-item-label">Total Amount</span>
                    <span class="detail-item-value">${formatCurrency(invoice.total_amount, invoice.currency)}</span>
                </div>
            </div>
            ${invoice.notes ? `<div class="invoice-notes" style="margin-top: 1rem; padding: 1rem; background: #f8fafc; border-radius: 8px;">
                <strong>Notes:</strong> ${invoice.notes}
            </div>` : ''}
        `;
        document.getElementById('invoice-summary').innerHTML = summaryHTML;

        // Line items
        renderLineItems(invoice.line_items);
    }

    /**
     * Render line items table
     */
    function renderLineItems(lineItems) {
        if (!lineItems || lineItems.length === 0) {
            document.getElementById('line-items-table').innerHTML = '<p class="empty-state-text">No line items</p>';
            return;
        }

        let html = `
            <table>
                <thead>
                    <tr>
                        <th>Description</th>
                        <th>Quantity</th>
                        <th>Unit Price</th>
                        <th>Amount</th>
                    </tr>
                </thead>
                <tbody>
        `;

        let subtotal = 0;
        lineItems.forEach(item => {
            const amount = (item.quantity || 0) * (item.unit_price || 0);
            subtotal += amount;
            html += `
                <tr>
                    <td>${item.description || 'N/A'}</td>
                    <td>${item.quantity || 0}</td>
                    <td>${formatCurrency(item.unit_price)}</td>
                    <td>${formatCurrency(amount)}</td>
                </tr>
            `;
        });

        html += `
                </tbody>
                <tfoot>
                    <tr>
                        <td colspan="3" style="text-align: right;">Subtotal:</td>
                        <td>${formatCurrency(subtotal)}</td>
                    </tr>
                </tfoot>
            </table>
        `;

        document.getElementById('line-items-table').innerHTML = html;
    }

    /**
     * Render details tab
     */
    function renderDetailsTab(invoice) {
        const detailsHTML = `
            <div class="detail-item">
                <span class="detail-item-label">Invoice Number</span>
                <span class="detail-item-value">${invoice.invoice_number || 'N/A'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-item-label">Vendor Name</span>
                <span class="detail-item-value">${invoice.vendor_name || 'N/A'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-item-label">Vendor Email</span>
                <span class="detail-item-value">${invoice.vendor_email || 'N/A'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-item-label">Currency</span>
                <span class="detail-item-value">${invoice.currency || 'USD'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-item-label">Status</span>
                <span class="detail-item-value">${invoice.status || 'Pending'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-item-label">Created At</span>
                <span class="detail-item-value">${formatDateTime(invoice.created_at)}</span>
            </div>
        `;
        document.getElementById('invoice-details-grid').innerHTML = detailsHTML;

        // Payment info
        const paymentHTML = invoice.payment_terms ? `
            <div class="detail-item">
                <span class="detail-item-label">Payment Terms</span>
                <span class="detail-item-value">${invoice.payment_terms}</span>
            </div>
        ` : '<p class="empty-state-text">No payment information</p>';
        document.getElementById('payment-info').innerHTML = paymentHTML;
    }

    /**
     * Render matches tab
     */
    function renderMatchesTab(data) {
        // Linked transaction
        const linkedContainer = document.getElementById('linked-transaction-container');
        if (data.linked_transaction) {
            const tx = data.linked_transaction;
            linkedContainer.innerHTML = renderMatchCard(tx, true);
            document.getElementById('linked-status').textContent = 'Transaction linked';
        } else {
            linkedContainer.innerHTML = '<p class="empty-state-text">No transaction linked to this invoice</p>';
        }

        // Pending matches
        const matchesContainer = document.getElementById('pending-matches-container');
        const matchesCount = document.getElementById('matches-count');

        if (data.pending_matches && data.pending_matches.length > 0) {
            matchesCount.textContent = `${data.pending_matches.length} pending matches`;
            matchesContainer.innerHTML = data.pending_matches.map(match => renderMatchCard(match, false)).join('');

            // Setup match action listeners
            setupMatchActions();
        } else {
            matchesCount.textContent = '0 pending matches';
            matchesContainer.innerHTML = '<p class="empty-state-text">No pending matches found</p>';
        }
    }

    /**
     * Render a match card
     */
    function renderMatchCard(match, isConfirmed) {
        const scoreClass = getScoreClass(match.score);
        const scoreLabel = match.score ? `${Math.round(match.score * 100)}%` : 'N/A';

        return `
            <div class="match-card ${isConfirmed ? 'confirmed' : ''}" data-match-id="${match.id}" data-transaction-id="${match.transaction_id || match.id}">
                <div class="match-card-header">
                    <span class="match-score ${scoreClass}">${scoreLabel} Match</span>
                    ${match.match_type ? `<span style="font-size: 0.8rem; color: #64748b;">${match.match_type}</span>` : ''}
                </div>
                <div class="match-card-body">
                    <div class="match-detail"><strong>Date:</strong> ${formatDate(match.date)}</div>
                    <div class="match-detail"><strong>Amount:</strong> ${formatCurrency(match.amount, match.currency)}</div>
                    <div class="match-detail"><strong>Description:</strong> ${match.description || 'N/A'}</div>
                    <div class="match-detail"><strong>Origin:</strong> ${match.origin || 'N/A'}</div>
                    <div class="match-detail"><strong>Destination:</strong> ${match.destination || 'N/A'}</div>
                    ${match.explanation ? `<div class="match-detail" style="margin-top: 0.5rem;"><strong>Why:</strong> ${match.explanation}</div>` : ''}
                </div>
                ${!isConfirmed ? `
                    <div class="match-actions">
                        <button class="match-action-btn confirm" data-action="confirm">Confirm Match</button>
                        <button class="match-action-btn reject" data-action="reject">Reject</button>
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Get score class based on confidence level
     */
    function getScoreClass(score) {
        if (!score) return 'low';
        if (score >= 0.8) return 'high';
        if (score >= 0.55) return 'medium';
        return 'low';
    }

    /**
     * Setup match action listeners
     */
    function setupMatchActions() {
        document.querySelectorAll('.match-action-btn').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.stopPropagation();
                const action = this.getAttribute('data-action');
                const matchCard = this.closest('.match-card');
                const transactionId = matchCard.getAttribute('data-transaction-id');

                if (action === 'confirm') {
                    await confirmMatch(transactionId);
                } else if (action === 'reject') {
                    await rejectMatch(transactionId);
                }
            });
        });
    }

    /**
     * Confirm a match
     */
    async function confirmMatch(transactionId) {
        showLoading(true);
        try {
            const response = await fetch(`/api/invoices/${RECORD_ID}/link-transaction`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ transaction_id: transactionId })
            });

            const data = await response.json();
            if (data.success) {
                showToast('Transaction matched successfully', 'success');
                await loadInvoiceDetails(); // Reload page
            } else {
                showToast('Failed to match transaction: ' + data.error, 'error');
            }
        } catch (error) {
            showToast('Error matching transaction', 'error');
        } finally {
            showLoading(false);
        }
    }

    /**
     * Reject a match
     */
    async function rejectMatch(transactionId) {
        // TODO: Implement reject endpoint if needed
        showToast('Match rejected', 'info');
    }

    /**
     * Render related records
     */
    function renderRelatedRecords(data) {
        const container = document.getElementById('related-records-container');
        let html = '';

        // Add linked transaction as related
        if (data.linked_transaction) {
            html += `
                <a href="/transactions/${data.linked_transaction.id}" class="related-item">
                    <div class="related-item-icon">T</div>
                    <div class="related-item-content">
                        <div class="related-item-title">Transaction</div>
                        <div class="related-item-subtitle">${formatCurrency(data.linked_transaction.amount)}</div>
                    </div>
                </a>
            `;
        }

        // Add attachments count
        if (data.attachments && data.attachments.length > 0) {
            html += `
                <div class="related-item">
                    <div class="related-item-icon">F</div>
                    <div class="related-item-content">
                        <div class="related-item-title">${data.attachments.length} Attachments</div>
                        <div class="related-item-subtitle">Click to view</div>
                    </div>
                </div>
            `;
        }

        container.innerHTML = html || '<p class="empty-state-text">No related records</p>';
    }

    // === ACTION HANDLERS ===

    function handleEditInvoice() {
        window.location.href = `/invoices/${RECORD_ID}/edit`;
    }

    async function handleMarkPaid() {
        if (!confirm('Mark this invoice as paid?')) return;

        showLoading(true);
        try {
            const response = await fetch(`/api/invoices/${RECORD_ID}/mark-paid`, {
                method: 'POST'
            });

            const data = await response.json();
            if (data.success) {
                showToast('Invoice marked as paid', 'success');
                await loadInvoiceDetails();
            } else {
                showToast('Failed to mark as paid: ' + data.error, 'error');
            }
        } catch (error) {
            showToast('Error marking as paid', 'error');
        } finally {
            showLoading(false);
        }
    }

    function handleDownloadPDF() {
        window.location.href = `/api/invoices/${RECORD_ID}/download`;
    }

    async function handleFindMatches() {
        showLoading(true);
        try {
            const response = await fetch(`/api/invoices/${RECORD_ID}/find-matching-transactions`);
            const data = await response.json();

            if (data.success) {
                showToast(`Found ${data.matches?.length || 0} potential matches`, 'success');
                await loadInvoiceDetails();
                switchTab('matches');
            } else {
                showToast('Failed to find matches: ' + data.error, 'error');
            }
        } catch (error) {
            showToast('Error finding matches', 'error');
        } finally {
            showLoading(false);
        }
    }

    function handleSendReminder() {
        showToast('Payment reminder feature coming soon', 'info');
    }

    function handleDuplicate() {
        window.location.href = `/invoices/create?duplicate=${RECORD_ID}`;
    }

    async function handleDelete() {
        if (!confirm('Are you sure you want to delete this invoice? This action cannot be undone.')) return;

        showLoading(true);
        try {
            const response = await fetch(`/api/invoices/${RECORD_ID}`, {
                method: 'DELETE'
            });

            const data = await response.json();
            if (data.success) {
                showToast('Invoice deleted successfully', 'success');
                setTimeout(() => {
                    window.location.href = '/invoices';
                }, 1500);
            } else {
                showToast('Failed to delete invoice: ' + data.error, 'error');
            }
        } catch (error) {
            showToast('Error deleting invoice', 'error');
        } finally {
            showLoading(false);
        }
    }

    // === UTILITY FUNCTIONS ===

    function showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }
    }

    function showToast(message, type = 'info') {
        const toast = document.getElementById('toast-notification');
        if (!toast) return;

        toast.textContent = message;
        toast.className = `toast-notification ${type} show`;

        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    }

    function formatDateTime(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function formatCurrency(amount, currency = 'USD') {
        if (amount === null || amount === undefined) return 'N/A';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency || 'USD'
        }).format(amount);
    }

})();
