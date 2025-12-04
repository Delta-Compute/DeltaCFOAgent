// Delta CFO Agent - Dashboard JavaScript

let currentTransactions = [];
let entities = [];
let businessLines = [];

document.addEventListener('DOMContentLoaded', function() {
    // Load initial data
    loadEntities();
    loadBusinessLines();
    loadTransactions();

    // Set up event listeners
    setupEventListeners();
});

function setupEventListeners() {
    // Filter button
    document.getElementById('applyFilters').addEventListener('click', loadTransactions);

    // Clear filters button
    document.getElementById('clearFilters').addEventListener('click', clearFilters);

    // Refresh button
    document.getElementById('refreshData').addEventListener('click', loadTransactions);

    // Entity filter change - cascade to business line filter
    document.getElementById('entityFilter').addEventListener('change', function() {
        const entityId = this.value;
        populateBusinessLineFilter(entityId);
    });

    // Quick filter buttons
    document.getElementById('filterTodos').addEventListener('click', () => {
        document.getElementById('needsReview').value = 'true';
        loadTransactions();
    });

    document.getElementById('filter2025').addEventListener('click', () => {
        document.getElementById('startDate').value = '2025-01-01';
        document.getElementById('endDate').value = '2025-12-31';
        loadTransactions();
    });

    document.getElementById('filter2024').addEventListener('click', () => {
        document.getElementById('startDate').value = '2024-01-01';
        document.getElementById('endDate').value = '2024-12-31';
        loadTransactions();
    });

    document.getElementById('filterYTD').addEventListener('click', () => {
        const now = new Date();
        document.getElementById('startDate').value = '2025-01-01';
        document.getElementById('endDate').value = now.toISOString().split('T')[0];
        loadTransactions();
    });
}

function clearFilters() {
    // Clear all filter inputs
    document.getElementById('entityFilter').value = '';
    document.getElementById('businessLineFilter').value = '';
    document.getElementById('transactionType').value = '';
    document.getElementById('sourceFile').value = '';
    document.getElementById('needsReview').value = '';
    document.getElementById('minAmount').value = '';
    document.getElementById('maxAmount').value = '';
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    document.getElementById('keywordFilter').value = '';

    // Reset business line filter to show all
    populateBusinessLineFilter('');

    // Reload transactions
    loadTransactions();
}

function buildFilterQuery() {
    const params = new URLSearchParams();

    const entityId = document.getElementById('entityFilter').value;
    if (entityId) params.append('entity_id', entityId);

    const businessLineId = document.getElementById('businessLineFilter').value;
    if (businessLineId) params.append('business_line_id', businessLineId);

    const transactionType = document.getElementById('transactionType').value;
    if (transactionType) params.append('transaction_type', transactionType);

    const sourceFile = document.getElementById('sourceFile').value;
    if (sourceFile) params.append('source_file', sourceFile);

    const needsReview = document.getElementById('needsReview').value;
    if (needsReview) params.append('needs_review', needsReview);

    const minAmount = document.getElementById('minAmount').value;
    if (minAmount) params.append('min_amount', minAmount);

    const maxAmount = document.getElementById('maxAmount').value;
    if (maxAmount) params.append('max_amount', maxAmount);

    const startDate = document.getElementById('startDate').value;
    if (startDate) params.append('start_date', startDate);

    const endDate = document.getElementById('endDate').value;
    if (endDate) params.append('end_date', endDate);

    const keyword = document.getElementById('keywordFilter').value;
    if (keyword) params.append('keyword', keyword);

    return params.toString();
}

async function loadTransactions() {
    try {
        const query = buildFilterQuery();
        const url = `/api/transactions?${query}`;

        const response = await fetch(url);
        const transactions = await response.json();

        currentTransactions = transactions;
        renderTransactionTable(transactions);
        updateTableInfo(transactions);

    } catch (error) {
        console.error('Error loading transactions:', error);
        document.getElementById('transactionTableBody').innerHTML =
            '<tr><td colspan="8" class="loading">Error loading transactions</td></tr>';
    }
}

function renderTransactionTable(transactions) {
    const tbody = document.getElementById('transactionTableBody');

    if (transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">No transactions found</td></tr>';
        return;
    }

    tbody.innerHTML = transactions.map(transaction => {
        const amount = parseFloat(transaction.Amount || 0);
        const amountClass = amount > 0 ? 'positive' : amount < 0 ? 'negative' : '';
        const formattedAmount = Math.abs(amount).toLocaleString('en-US', {
            style: 'currency',
            currency: 'USD'
        });

        const confidence = transaction.confidence ?
            (parseFloat(transaction.confidence) * 100).toFixed(0) + '%' : 'N/A';

        const confidenceClass = transaction.confidence && parseFloat(transaction.confidence) < 0.8 ?
            'warning' : '';

        // Get entity and business line information
        const entityName = transaction.entity_name || transaction.classified_entity || 'N/A';
        const entityCode = transaction.entity_code ? `(${transaction.entity_code})` : '';
        const businessLineName = transaction.business_line_name || '-';
        const businessLineCode = transaction.business_line_code ? `(${transaction.business_line_code})` : '';

        return `
            <tr>
                <td>${transaction.Date || 'N/A'}</td>
                <td>${transaction.Description || 'N/A'}</td>
                <td class="${amountClass}">${formattedAmount}</td>
                <td>
                    ${entityName} ${entityCode}
                </td>
                <td>
                    ${businessLineName} ${businessLineCode}
                </td>
                <td class="${confidenceClass}">${confidence}</td>
                <td>${transaction.source_file || 'N/A'}</td>
                <td>
                    <button class="btn-secondary btn-sm" onclick="viewTransaction('${transaction.id || ''}')">
                        View
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function updateTableInfo(transactions) {
    const info = document.getElementById('tableInfo');
    const count = transactions.length;
    const total = currentTransactions.length;

    if (count === total) {
        info.textContent = `Showing ${count} transactions`;
    } else {
        info.textContent = `Showing ${count} of ${total} transactions`;
    }
}

function viewTransaction(id) {
    // Placeholder for transaction detail view
    alert(`View transaction: ${id}`);
}

// Format currency values
function formatCurrency(value) {
    const num = parseFloat(value || 0);
    return Math.abs(num).toLocaleString('en-US', {
        style: 'currency',
        currency: 'USD'
    });
}

// Format dates
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US');
    } catch {
        return dateString;
    }
}

// ========================================
// ENTITY & BUSINESS LINE MANAGEMENT
// ========================================

async function loadEntities() {
    try {
        const response = await fetch('/api/entities');
        const result = await response.json();

        if (result.success && result.entities) {
            entities = result.entities;
            populateEntityFilter();
        } else {
            console.error('Failed to load entities:', result.error);
        }
    } catch (error) {
        console.error('Error loading entities:', error);
    }
}

async function loadBusinessLines() {
    try {
        const response = await fetch('/api/business-lines');
        const result = await response.json();

        if (result.success && result.business_lines) {
            businessLines = result.business_lines;
            populateBusinessLineFilter(''); // Show all initially
        } else {
            console.error('Failed to load business lines:', result.error);
        }
    } catch (error) {
        console.error('Error loading business lines:', error);
    }
}

function populateEntityFilter() {
    const entityFilter = document.getElementById('entityFilter');

    entityFilter.innerHTML = '<option value="">All Entities</option>' +
        entities.filter(e => e.is_active).map(entity => `
            <option value="${entity.id}">
                ${escapeHtml(entity.name)} (${escapeHtml(entity.code)})
            </option>
        `).join('');
}

function populateBusinessLineFilter(entityId) {
    const blFilter = document.getElementById('businessLineFilter');

    let filteredBusinessLines = businessLines.filter(bl => bl.is_active);

    if (entityId) {
        filteredBusinessLines = filteredBusinessLines.filter(bl => bl.entity_id === entityId);
    }

    blFilter.innerHTML = '<option value="">All Business Lines</option>' +
        filteredBusinessLines.map(bl => {
            const entity = entities.find(e => e.id === bl.entity_id);
            const entityLabel = entity ? ` - ${entity.code}` : '';
            return `
                <option value="${bl.id}">
                    ${escapeHtml(bl.name)} (${escapeHtml(bl.code)})${entityLabel}
                </option>
            `;
        }).join('');
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}