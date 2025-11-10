/**
 * Workforce Management JavaScript
 * Handles employees, contractors, and payslips
 */

// State management
let currentTab = 'members';
let workforceMembers = [];
let payslips = [];
let currentMemberPage = 1;
let currentPayslipPage = 1;
const itemsPerPage = 20;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    loadStats();
    loadWorkforceMembers();
    loadPayslips();
    setupSearch();
    setupAutoCalculations();
});

// Tab management
function initializeTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    currentTab = tabName;

    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Load data for the active tab
    if (tabName === 'members') {
        loadWorkforceMembers();
    } else if (tabName === 'payslips') {
        loadPayslips();
    }
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch('/api/payroll/stats');
        const data = await response.json();

        if (data.success) {
            const stats = data.stats;
            document.getElementById('stat-active-members').textContent = stats.total_active_members || 0;
            document.getElementById('stat-total-payslips').textContent = stats.total_payslips || 0;
            document.getElementById('stat-matched-payslips').textContent = stats.matched_payslips || 0;
            document.getElementById('stat-match-rate').textContent = stats.match_rate + '%';
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Workforce Members Management
async function loadWorkforceMembers(page = 1) {
    currentMemberPage = page;
    const searchTerm = document.getElementById('members-search').value;
    const tbody = document.getElementById('members-tbody');

    tbody.innerHTML = '<tr><td colspan="7" class="loading">Loading...</td></tr>';

    try {
        const params = new URLSearchParams({
            page: page,
            per_page: itemsPerPage,
            ...(searchTerm && { keyword: searchTerm })
        });

        const response = await fetch(`/api/workforce?${params}`);
        const data = await response.json();

        if (data.success) {
            workforceMembers = data.workforce_members;
            renderWorkforceMembers(data.workforce_members);
            renderPagination(data.pagination, 'members');
        } else {
            showError(tbody, data.error || 'Failed to load workforce members', 7);
        }
    } catch (error) {
        console.error('Error loading workforce members:', error);
        showError(tbody, 'Network error. Please try again.', 7);
    }
}

function renderWorkforceMembers(members) {
    const tbody = document.getElementById('members-tbody');

    if (members.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    <div class="empty-icon">👥</div>
                    <p>No workforce members found</p>
                    <button class="btn btn-primary" onclick="openAddMemberModal()" style="margin-top: 1rem;">Add First Member</button>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = members.map(member => `
        <tr>
            <td><strong>${escapeHtml(member.full_name)}</strong></td>
            <td>
                <span class="type-badge type-${member.employment_type}">
                    ${member.employment_type === 'employee' ? 'Employee' : 'Contractor'}
                </span>
            </td>
            <td style="word-wrap: break-word;">${escapeHtml(member.job_title || '-')}</td>
            <td>${formatDate(member.date_of_hire)}</td>
            <td>${member.currency || 'USD'} ${formatNumber(member.pay_rate)} / ${member.pay_frequency}</td>
            <td>
                <span class="status-badge status-${member.status}">
                    ${member.status.charAt(0).toUpperCase() + member.status.slice(1)}
                </span>
            </td>
            <td>
                <span class="action-icon" onclick="editMember('${member.id}')" title="Edit">✏️</span>
                <span class="action-icon" onclick="viewMemberPayslips('${member.id}')" title="View Payslips">📄</span>
                <span class="action-icon" onclick="deleteMember('${member.id}')" title="Deactivate">🗑️</span>
            </td>
        </tr>
    `).join('');
}

// Payslips Management
async function loadPayslips(page = 1) {
    currentPayslipPage = page;
    const searchTerm = document.getElementById('payslips-search').value;
    const tbody = document.getElementById('payslips-tbody');

    tbody.innerHTML = '<tr><td colspan="8" class="loading">Loading...</td></tr>';

    try {
        const params = new URLSearchParams({
            page: page,
            per_page: itemsPerPage,
            ...(searchTerm && { keyword: searchTerm })
        });

        const response = await fetch(`/api/payslips?${params}`);
        const data = await response.json();

        if (data.success) {
            payslips = data.payslips;
            renderPayslips(data.payslips);
            renderPagination(data.pagination, 'payslips');
        } else {
            showError(tbody, data.error || 'Failed to load payslips', 8);
        }
    } catch (error) {
        console.error('Error loading payslips:', error);
        showError(tbody, 'Network error. Please try again.', 8);
    }
}

function renderPayslips(payslips) {
    const tbody = document.getElementById('payslips-tbody');

    if (payslips.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state">
                    <div class="empty-icon">📊</div>
                    <p>No payslips found</p>
                    <button class="btn btn-primary" onclick="openAddPayslipModal()" style="margin-top: 1rem;">Create First Payslip</button>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = payslips.map(payslip => `
        <tr>
            <td><strong>${escapeHtml(payslip.payslip_number)}</strong></td>
            <td>${escapeHtml(payslip.employee_name)}</td>
            <td>${formatDate(payslip.pay_period_start)} - ${formatDate(payslip.pay_period_end)}</td>
            <td>${formatDate(payslip.payment_date)}</td>
            <td>$${formatNumber(payslip.gross_amount)}</td>
            <td>$${formatNumber(payslip.net_amount)}</td>
            <td>
                <span class="status-badge status-${payslip.status}">
                    ${payslip.status.charAt(0).toUpperCase() + payslip.status.slice(1)}
                </span>
            </td>
            <td>
                <span class="action-icon" onclick="editPayslip('${payslip.id}')" title="Edit">✏️</span>
                <span class="action-icon" onclick="viewPayslipMatches('${payslip.id}')" title="Match Transactions">🔗</span>
                ${payslip.status !== 'paid' ? `<span class="action-icon" onclick="markPayslipPaid('${payslip.id}')" title="Mark as Paid">✓</span>` : ''}
                ${payslip.status === 'draft' ? `<span class="action-icon" onclick="deletePayslip('${payslip.id}')" title="Delete">🗑️</span>` : ''}
            </td>
        </tr>
    `).join('');
}

// Pagination
function renderPagination(pagination, type) {
    const container = document.getElementById(`${type}-pagination`);

    if (!pagination || pagination.total === 0) {
        container.innerHTML = '';
        return;
    }

    const { page, pages, total } = pagination;
    const start = (page - 1) * itemsPerPage + 1;
    const end = Math.min(page * itemsPerPage, total);

    container.innerHTML = `
        <button onclick="load${type === 'members' ? 'WorkforceMembers' : 'Payslips'}(${page - 1})" ${page === 1 ? 'disabled' : ''}>
            Previous
        </button>
        <span class="pagination-info">
            Showing ${start}-${end} of ${total}
        </span>
        <button onclick="load${type === 'members' ? 'WorkforceMembers' : 'Payslips'}(${page + 1})" ${page === pages ? 'disabled' : ''}>
            Next
        </button>
    `;
}

// Search functionality
function setupSearch() {
    const membersSearch = document.getElementById('members-search');
    const payslipsSearch = document.getElementById('payslips-search');

    let memberSearchTimeout;
    membersSearch.addEventListener('input', function() {
        clearTimeout(memberSearchTimeout);
        memberSearchTimeout = setTimeout(() => loadWorkforceMembers(1), 500);
    });

    let payslipSearchTimeout;
    payslipsSearch.addEventListener('input', function() {
        clearTimeout(payslipSearchTimeout);
        payslipSearchTimeout = setTimeout(() => loadPayslips(1), 500);
    });
}

// Modal Management - Workforce Members
function openAddMemberModal() {
    document.getElementById('member-modal-title').textContent = 'Add Workforce Member';
    document.getElementById('member-form').reset();
    document.getElementById('member-id').value = '';
    document.getElementById('member-modal').classList.add('show');
}

function closeMemberModal() {
    document.getElementById('member-modal').classList.remove('show');
}

async function editMember(memberId) {
    try {
        const response = await fetch(`/api/workforce/${memberId}`);
        const data = await response.json();

        if (data.success) {
            const member = data.member;
            document.getElementById('member-modal-title').textContent = 'Edit Workforce Member';
            document.getElementById('member-id').value = member.id;
            document.getElementById('member-name').value = member.full_name;
            document.getElementById('member-type').value = member.employment_type;
            document.getElementById('member-status').value = member.status;
            document.getElementById('member-doc-type').value = member.document_type || '';
            document.getElementById('member-doc-number').value = member.document_number || '';
            document.getElementById('member-hire-date').value = member.date_of_hire;
            document.getElementById('member-pay-rate').value = member.pay_rate;
            document.getElementById('member-currency').value = member.currency || 'USD';
            document.getElementById('member-pay-frequency').value = member.pay_frequency;
            document.getElementById('member-job-title').value = member.job_title || '';
            document.getElementById('member-department').value = member.department || '';
            document.getElementById('member-email').value = member.email || '';
            document.getElementById('member-phone').value = member.phone || '';
            document.getElementById('member-notes').value = member.notes || '';

            document.getElementById('member-modal').classList.add('show');
        }
    } catch (error) {
        console.error('Error loading member:', error);
        alert('Failed to load member details');
    }
}

async function deleteMember(memberId) {
    if (!confirm('Are you sure you want to deactivate this workforce member?')) {
        return;
    }

    try {
        const response = await fetch(`/api/workforce/${memberId}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
            alert('Member deactivated successfully');
            loadWorkforceMembers(currentMemberPage);
            loadStats();
        } else {
            alert('Error: ' + (data.error || 'Failed to deactivate member'));
        }
    } catch (error) {
        console.error('Error deleting member:', error);
        alert('Network error. Please try again.');
    }
}

// Member form submission
document.getElementById('member-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const memberId = document.getElementById('member-id').value;
    const memberData = {
        full_name: document.getElementById('member-name').value,
        employment_type: document.getElementById('member-type').value,
        status: document.getElementById('member-status').value,
        document_type: document.getElementById('member-doc-type').value || null,
        document_number: document.getElementById('member-doc-number').value || null,
        date_of_hire: document.getElementById('member-hire-date').value,
        pay_rate: parseFloat(document.getElementById('member-pay-rate').value),
        currency: document.getElementById('member-currency').value,
        pay_frequency: document.getElementById('member-pay-frequency').value,
        job_title: document.getElementById('member-job-title').value || null,
        department: document.getElementById('member-department').value || null,
        email: document.getElementById('member-email').value || null,
        phone: document.getElementById('member-phone').value || null,
        notes: document.getElementById('member-notes').value || null
    };

    try {
        const url = memberId ? `/api/workforce/${memberId}` : '/api/workforce';
        const method = memberId ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(memberData)
        });

        const data = await response.json();

        if (data.success) {
            alert(memberId ? 'Member updated successfully' : 'Member created successfully');
            closeMemberModal();
            loadWorkforceMembers(currentMemberPage);
            loadStats();
        } else {
            alert('Error: ' + (data.error || 'Failed to save member'));
        }
    } catch (error) {
        console.error('Error saving member:', error);
        alert('Network error. Please try again.');
    }
});

// Modal Management - Payslips
async function openAddPayslipModal() {
    document.getElementById('payslip-modal-title').textContent = 'Create Payslip';
    document.getElementById('payslip-form').reset();
    document.getElementById('payslip-id').value = '';

    // Load active employees for dropdown
    await loadEmployeeDropdown();

    // Generate payslip number
    const payslipNumber = 'PAY-' + Date.now().toString().slice(-8);
    document.getElementById('payslip-number').value = payslipNumber;

    // Set default dates
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);

    document.getElementById('payslip-period-start').value = formatDateInput(firstDay);
    document.getElementById('payslip-period-end').value = formatDateInput(lastDay);
    document.getElementById('payslip-payment-date').value = formatDateInput(today);

    document.getElementById('payslip-modal').classList.add('show');
}

function closePayslipModal() {
    document.getElementById('payslip-modal').classList.remove('show');
}

async function loadEmployeeDropdown() {
    try {
        const response = await fetch('/api/workforce?status=active&per_page=100');
        const data = await response.json();

        if (data.success) {
            const select = document.getElementById('payslip-employee');
            select.innerHTML = '<option value="">Select employee</option>' +
                data.workforce_members.map(member =>
                    `<option value="${member.id}">${escapeHtml(member.full_name)} (${member.employment_type})</option>`
                ).join('');
        }
    } catch (error) {
        console.error('Error loading employees:', error);
    }
}

async function editPayslip(payslipId) {
    try {
        const response = await fetch(`/api/payslips/${payslipId}`);
        const data = await response.json();

        if (data.success) {
            const payslip = data.payslip;
            document.getElementById('payslip-modal-title').textContent = 'Edit Payslip';
            await loadEmployeeDropdown();

            document.getElementById('payslip-id').value = payslip.id;
            document.getElementById('payslip-employee').value = payslip.workforce_member_id;
            document.getElementById('payslip-number').value = payslip.payslip_number;
            document.getElementById('payslip-period-start').value = payslip.pay_period_start;
            document.getElementById('payslip-period-end').value = payslip.pay_period_end;
            document.getElementById('payslip-payment-date').value = payslip.payment_date;
            document.getElementById('payslip-gross').value = payslip.gross_amount;
            document.getElementById('payslip-deductions').value = payslip.deductions || 0;
            document.getElementById('payslip-net').value = payslip.net_amount;
            document.getElementById('payslip-payment-method').value = payslip.payment_method || '';
            document.getElementById('payslip-status').value = payslip.status;
            document.getElementById('payslip-notes').value = payslip.notes || '';

            document.getElementById('payslip-modal').classList.add('show');
        }
    } catch (error) {
        console.error('Error loading payslip:', error);
        alert('Failed to load payslip details');
    }
}

async function markPayslipPaid(payslipId) {
    if (!confirm('Mark this payslip as paid?')) {
        return;
    }

    try {
        const response = await fetch(`/api/payslips/${payslipId}/mark-paid`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (data.success) {
            alert('Payslip marked as paid');
            loadPayslips(currentPayslipPage);
            loadStats();
        } else {
            alert('Error: ' + (data.error || 'Failed to mark payslip as paid'));
        }
    } catch (error) {
        console.error('Error marking payslip as paid:', error);
        alert('Network error. Please try again.');
    }
}

async function deletePayslip(payslipId) {
    if (!confirm('Are you sure you want to delete this payslip?')) {
        return;
    }

    try {
        const response = await fetch(`/api/payslips/${payslipId}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
            alert('Payslip deleted successfully');
            loadPayslips(currentPayslipPage);
            loadStats();
        } else {
            alert('Error: ' + (data.error || 'Failed to delete payslip'));
        }
    } catch (error) {
        console.error('Error deleting payslip:', error);
        alert('Network error. Please try again.');
    }
}

// Payslip form submission
document.getElementById('payslip-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const payslipId = document.getElementById('payslip-id').value;
    const payslipData = {
        workforce_member_id: document.getElementById('payslip-employee').value,
        payslip_number: document.getElementById('payslip-number').value,
        pay_period_start: document.getElementById('payslip-period-start').value,
        pay_period_end: document.getElementById('payslip-period-end').value,
        payment_date: document.getElementById('payslip-payment-date').value,
        gross_amount: parseFloat(document.getElementById('payslip-gross').value),
        deductions: parseFloat(document.getElementById('payslip-deductions').value) || 0,
        net_amount: parseFloat(document.getElementById('payslip-net').value),
        payment_method: document.getElementById('payslip-payment-method').value || null,
        status: document.getElementById('payslip-status').value,
        notes: document.getElementById('payslip-notes').value || null
    };

    try {
        const url = payslipId ? `/api/payslips/${payslipId}` : '/api/payslips';
        const method = payslipId ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payslipData)
        });

        const data = await response.json();

        if (data.success) {
            alert(payslipId ? 'Payslip updated successfully' : 'Payslip created successfully');
            closePayslipModal();
            loadPayslips(currentPayslipPage);
            loadStats();
        } else {
            alert('Error: ' + (data.error || 'Failed to save payslip'));
        }
    } catch (error) {
        console.error('Error saving payslip:', error);
        alert('Network error. Please try again.');
    }
});

// Auto calculations
function setupAutoCalculations() {
    const grossInput = document.getElementById('payslip-gross');
    const deductionsInput = document.getElementById('payslip-deductions');
    const netInput = document.getElementById('payslip-net');

    function calculateNet() {
        const gross = parseFloat(grossInput.value) || 0;
        const deductions = parseFloat(deductionsInput.value) || 0;
        netInput.value = (gross - deductions).toFixed(2);
    }

    grossInput.addEventListener('input', calculateNet);
    deductionsInput.addEventListener('input', calculateNet);
}

// Transaction matching (stub for integration with payslip_matches.js)
function viewPayslipMatches(payslipId) {
    alert(`Transaction matching for payslip ${payslipId} - Implementation in progress`);
    // This will be implemented in payslip_matches.js
}

function viewMemberPayslips(memberId) {
    // Switch to payslips tab and filter by member
    switchTab('payslips');
    // TODO: Implement member filtering
}

// Refresh functions
function refreshMembers() {
    loadWorkforceMembers(currentMemberPage);
    loadStats();
}

function refreshPayslips() {
    loadPayslips(currentPayslipPage);
    loadStats();
}

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatDateInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function formatNumber(num) {
    if (num === null || num === undefined) return '0.00';
    return parseFloat(num).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function showError(container, message, colspan) {
    container.innerHTML = `
        <tr>
            <td colspan="${colspan}" class="empty-state">
                <div style="color: #ef4444;">
                    <div class="empty-icon">⚠️</div>
                    <p>${escapeHtml(message)}</p>
                </div>
            </td>
        </tr>
    `;
}

// Close modals when clicking outside
window.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('show');
    }
});
