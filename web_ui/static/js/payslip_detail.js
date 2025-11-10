/**
 * Payslip Detail Page JavaScript
 * Handles data loading, display, and interactions for payslip detail pages
 */

(function() {
    'use strict';

    // Global state
    let payslipData = null;

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
        loadPayslipDetails();
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
        document.getElementById('btn-edit-payslip')?.addEventListener('click', handleEditPayslip);
        document.getElementById('btn-mark-paid')?.addEventListener('click', handleMarkPaid);
        document.getElementById('btn-download-pdf')?.addEventListener('click', handleDownloadPDF);
    }

    /**
     * Load payslip details from API
     */
    async function loadPayslipDetails() {
        showLoading(true);

        try {
            const response = await fetch(API_ENDPOINT);
            const data = await response.json();

            if (data.success) {
                payslipData = data;
                renderPayslipDetails(data);
            } else {
                showToast('Failed to load payslip details: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error loading payslip details:', error);
            showToast('Error loading payslip details', 'error');
        } finally {
            showLoading(false);
        }
    }

    /**
     * Render all payslip details on the page
     */
    function renderPayslipDetails(data) {
        const payslip = data.payslip;
        const stats = data.statistics;

        // Update page title and subtitle
        document.getElementById('payslip-title').textContent = `Payslip ${payslip.payslip_number}`;
        document.getElementById('payslip-subtitle').textContent = `${payslip.employee_name} - ${formatCurrency(payslip.net_amount, payslip.currency)}`;
        document.getElementById('payslip-number-breadcrumb').textContent = payslip.payslip_number;

        // Update status badges
        renderStatusBadges(payslip, stats);

        // Update quick info card
        renderQuickInfo(payslip);

        // Update sidebar stats
        renderSidebarStats(stats, payslip);

        // Render tab contents
        renderOverviewTab(payslip);
        renderDetailsTab(payslip, data.employee);
        renderMatchesTab(data);

        // Render activity timeline
        if (window.ActivityTimeline && data.activity_history) {
            window.ActivityTimeline.render(data.activity_history, 'activity-timeline-container');
        }
    }

    /**
     * Render status badges
     */
    function renderStatusBadges(payslip, stats) {
        const statusBadge = document.getElementById('payslip-status-badge');
        const matchBadge = document.getElementById('payslip-match-badge');

        // Status badge
        statusBadge.textContent = payslip.payment_status || 'Pending';
        statusBadge.className = `status-badge ${(payslip.payment_status || 'pending').toLowerCase()}`;

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
    function renderQuickInfo(payslip) {
        document.getElementById('info-payslip-number').textContent = payslip.payslip_number || 'N/A';
        document.getElementById('info-employee-name').textContent = payslip.employee_name || 'N/A';
        document.getElementById('info-net-amount').textContent = formatCurrency(payslip.net_amount, payslip.currency || 'USD');
        document.getElementById('info-pay-period').textContent = `${formatDate(payslip.pay_period_start)} - ${formatDate(payslip.pay_period_end)}`;
        document.getElementById('info-payment-date').textContent = formatDate(payslip.payment_date);
        document.getElementById('info-status').textContent = payslip.payment_status || 'Pending';
    }

    /**
     * Render sidebar statistics
     */
    function renderSidebarStats(stats, payslip) {
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
    function renderOverviewTab(payslip) {
        const summarySection = document.getElementById('payslip-summary');
        if (!summarySection) return;

        summarySection.innerHTML = `
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="detail-label">Payslip Number</span>
                    <span class="detail-value">${payslip.payslip_number}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Employee</span>
                    <span class="detail-value">${payslip.employee_name}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Pay Period</span>
                    <span class="detail-value">${formatDate(payslip.pay_period_start)} - ${formatDate(payslip.pay_period_end)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Payment Date</span>
                    <span class="detail-value">${formatDate(payslip.payment_date)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Gross Amount</span>
                    <span class="detail-value">${formatCurrency(payslip.gross_amount, payslip.currency)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Total Deductions</span>
                    <span class="detail-value">${formatCurrency(payslip.total_deductions, payslip.currency)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Net Amount</span>
                    <span class="detail-value">${formatCurrency(payslip.net_amount, payslip.currency)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Status</span>
                    <span class="detail-value">${payslip.payment_status || 'Pending'}</span>
                </div>
            </div>
        `;

        // Render line items
        const lineItemsTable = document.getElementById('line-items-table');
        if (!lineItemsTable) return;

        const lineItems = payslip.line_items || [];
        if (lineItems.length > 0) {
            lineItemsTable.innerHTML = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Description</th>
                            <th>Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${lineItems.map(item => `
                            <tr>
                                <td>${item.description}</td>
                                <td>${formatCurrency(item.amount, payslip.currency)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } else {
            lineItemsTable.innerHTML = '<p class="empty-state-text">No line items available</p>';
        }
    }

    /**
     * Render details tab
     */
    function renderDetailsTab(payslip, employee) {
        const employeeInfo = document.getElementById('employee-info');
        if (!employeeInfo) return;

        if (employee) {
            employeeInfo.innerHTML = `
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Full Name</span>
                        <span class="detail-value">${employee.full_name}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Employment Type</span>
                        <span class="detail-value">${employee.employment_type}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Job Title</span>
                        <span class="detail-value">${employee.job_title || 'N/A'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Department</span>
                        <span class="detail-value">${employee.department || 'N/A'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Email</span>
                        <span class="detail-value">${employee.email || 'N/A'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Status</span>
                        <span class="detail-value">${employee.status}</span>
                    </div>
                </div>
            `;
        } else {
            employeeInfo.innerHTML = '<p class="empty-state-text">Employee information not available</p>';
        }
    }

    /**
     * Render matches tab
     */
    function renderMatchesTab(data) {
        // Linked transaction
        const linkedTransactionSection = document.getElementById('linked-transaction-section');
        if (linkedTransactionSection) {
            if (data.linked_transaction) {
                const transaction = data.linked_transaction;
                linkedTransactionSection.innerHTML = `
                    <div class="linked-record-card">
                        <h4>Transaction ${transaction.transaction_id.substring(0, 8)}</h4>
                        <p>${transaction.description} - ${formatCurrency(transaction.amount, transaction.currency)}</p>
                        <a href="/transactions/${transaction.transaction_id}" class="btn btn-sm btn-secondary">View Transaction</a>
                    </div>
                `;
            } else {
                linkedTransactionSection.innerHTML = '<p class="empty-state-text">No linked transaction</p>';
            }
        }

        // Potential matches
        const potentialMatchesSection = document.getElementById('potential-matches-section');
        if (potentialMatchesSection) {
            if (data.pending_matches && data.pending_matches.length > 0) {
                potentialMatchesSection.innerHTML = `
                    <p>Found ${data.pending_matches.length} potential transaction matches</p>
                    <div class="matches-list">
                        ${data.pending_matches.map(match => `
                            <div class="match-card">
                                <div class="match-header">
                                    <span class="match-confidence ${match.confidence_level.toLowerCase()}">${match.confidence_level}</span>
                                    <span class="match-score">${(parseFloat(match.score) * 100).toFixed(0)}%</span>
                                </div>
                                <div class="match-details">
                                    <p><strong>${match.description}</strong></p>
                                    <p>${formatCurrency(match.amount, 'USD')} on ${formatDate(match.date)}</p>
                                    <p class="match-explanation">${match.explanation}</p>
                                </div>
                                <div class="match-actions">
                                    <button class="btn btn-sm btn-primary" onclick="confirmMatch('${match.id}')">Link</button>
                                    <button class="btn btn-sm btn-secondary" onclick="rejectMatch('${match.id}')">Reject</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            } else {
                potentialMatchesSection.innerHTML = '<p class="empty-state-text">No potential matches found</p>';
            }
        }
    }

    /**
     * Event Handlers
     */
    function handleEditPayslip() {
        alert('Edit payslip functionality coming soon');
    }

    function handleMarkPaid() {
        alert('Mark as paid functionality coming soon');
    }

    function handleDownloadPDF() {
        alert('Download PDF functionality coming soon');
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

    // Global functions for match actions
    window.confirmMatch = function(matchId) {
        alert(`Confirm match ${matchId} - functionality coming soon`);
    };

    window.rejectMatch = function(matchId) {
        alert(`Reject match ${matchId} - functionality coming soon`);
    };

})();
