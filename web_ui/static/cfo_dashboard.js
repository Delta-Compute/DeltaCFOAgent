/**
 * CFO Dashboard JavaScript - Simplified Version
 * Aligned with existing system design
 */

// Global variables
let currentFilters = {
    period: 'all_time',
    entity: '',
    startDate: null,
    endDate: null,
    isInternal: 'false'  // Default to External Only for accurate financial reporting
};

let dashboardData = {};
let charts = {};

// Chart.js configuration
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.responsive = true;
Chart.defaults.maintainAspectRatio = false;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    setupQuickFilters();
});

/**
 * Initialize the CFO dashboard
 */
async function initializeDashboard() {
    showLoading(true);

    try {
        // Load initial data
        await loadDashboardData();

        // Populate entity dropdown
        await populateEntityDropdown();

        // Update KPIs
        updateKPICards();

        // Initialize charts
        initializeCharts();

    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showError('Failed to load dashboard data. Please refresh the page.');
    } finally {
        showLoading(false);
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Period selector
    document.getElementById('periodSelector').addEventListener('change', function() {
        currentFilters.period = this.value;

        // Show/hide custom date range
        if (this.value === 'custom') {
            showCustomDateRange();
        } else {
            hideCustomDateRange();
            currentFilters.startDate = null;
            currentFilters.endDate = null;
        }

        refreshDashboard();
    });

    // Entity filter
    document.getElementById('entityFilter').addEventListener('change', function() {
        currentFilters.entity = this.value;
        refreshDashboard();
    });

    // Internal transaction filter
    document.getElementById('internalFilter').addEventListener('change', function() {
        currentFilters.isInternal = this.value;

        // Show/hide warning when "All Transactions" is selected
        const warning = document.getElementById('allTransactionsWarning');
        if (this.value === '') {
            warning.style.display = 'block';
        } else {
            warning.style.display = 'none';
        }

        refreshDashboard();
    });

    // Refresh button
    document.getElementById('refreshDashboard').addEventListener('click', refreshDashboard);

    // Reset button
    document.getElementById('resetFilters').addEventListener('click', resetFilters);

    // Custom date inputs
    document.addEventListener('change', function(e) {
        if (e.target.id === 'startDateInput') {
            currentFilters.startDate = e.target.value;
            refreshDashboard();
        } else if (e.target.id === 'endDateInput') {
            currentFilters.endDate = e.target.value;
            refreshDashboard();
        }
    });

    // Error modal close
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('close')) {
            hideError();
        }
    });
}

/**
 * Setup quick filters
 */
function setupQuickFilters() {
    // YTD Filter
    document.getElementById('filterYTD').addEventListener('click', function() {
        const now = new Date();
        currentFilters.startDate = now.getFullYear() + '-01-01';
        currentFilters.endDate = now.toISOString().split('T')[0];
        currentFilters.period = 'custom';
        updateFilterDisplay();
        refreshDashboard();
    });

    // 2024 Filter
    document.getElementById('filter2024').addEventListener('click', function() {
        currentFilters.startDate = '2024-01-01';
        currentFilters.endDate = '2024-12-31';
        currentFilters.period = 'custom';
        updateFilterDisplay();
        refreshDashboard();
    });

    // Q4 Filter
    document.getElementById('filterQ4').addEventListener('click', function() {
        currentFilters.startDate = '2024-10-01';
        currentFilters.endDate = '2024-12-31';
        currentFilters.period = 'custom';
        updateFilterDisplay();
        refreshDashboard();
    });

    // Last Month Filter
    document.getElementById('filterLastMonth').addEventListener('click', function() {
        const now = new Date();
        const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);

        currentFilters.startDate = lastMonth.toISOString().split('T')[0];
        currentFilters.endDate = lastMonthEnd.toISOString().split('T')[0];
        currentFilters.period = 'custom';
        updateFilterDisplay();
        refreshDashboard();
    });
}

/**
 * Load dashboard data from APIs
 */
async function loadDashboardData() {
    const promises = [];

    // Load cash dashboard data
    promises.push(
        fetch('/api/reports/cash-dashboard?' + new URLSearchParams(getAPIParams()))
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    dashboardData.cashDashboard = data.data;
                }
            })
            .catch(error => console.warn('Cash dashboard API error:', error))
    );

    // Load monthly P&L data
    promises.push(
        fetch('/api/reports/monthly-pl?' + new URLSearchParams({
            ...getAPIParams(),
            months_back: currentFilters.period === 'all_time' ? 'all' : 12
        }))
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    dashboardData.monthlyPL = data.data;
                }
            })
            .catch(error => console.warn('Monthly P&L API error:', error))
    );

    // Load entity summary
    promises.push(
        fetch('/api/reports/entity-summary?' + new URLSearchParams(getAPIParams()))
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    dashboardData.entitySummary = data.data;
                }
            })
            .catch(error => console.warn('Entity summary API error:', error))
    );

    // Load charts data
    promises.push(
        fetch('/api/reports/charts-data')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    dashboardData.chartsData = data.data;
                }
            })
            .catch(error => console.warn('Charts data API error:', error))
    );

    await Promise.allSettled(promises);
}

/**
 * Populate entity dropdown
 */
async function populateEntityDropdown() {
    try {
        const response = await fetch('/api/reports/entities');
        const data = await response.json();

        if (data.success) {
            const entitySelect = document.getElementById('entityFilter');
            entitySelect.innerHTML = '<option value="">All Entities</option>';

            data.data.entities.forEach(entity => {
                const option = document.createElement('option');
                option.value = entity.name;
                option.textContent = entity.display_name || entity.name;
                entitySelect.appendChild(option);
            });
        }
    } catch (error) {
        console.warn('Error populating entity dropdown:', error);
    }
}

/**
 * Get API parameters based on current filters
 */
function getAPIParams() {
    const params = {};

    if (currentFilters.period !== 'all_time') {
        params.period = currentFilters.period;
    }

    if (currentFilters.entity) {
        params.entity = currentFilters.entity;
    }

    if (currentFilters.startDate) {
        params.start_date = currentFilters.startDate;
    }

    if (currentFilters.endDate) {
        params.end_date = currentFilters.endDate;
    }

    if (currentFilters.isInternal) {
        params.is_internal = currentFilters.isInternal;
    }

    return params;
}

/**
 * Update KPI cards with current data
 */
function updateKPICards() {
    const cashData = dashboardData.cashDashboard?.cash_position;
    const plData = dashboardData.monthlyPL?.summary?.period_totals;

    // Safe update function
    function safeUpdate(elementId, value) {
        console.log(`safeUpdate called: ${elementId} = ${value}`);
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = formatCurrency(value || 0);
            console.log(`Element ${elementId} updated with: ${element.textContent}`);
        } else {
            console.error(`Element with ID '${elementId}' not found!`);
        }
    }

    // Update cash position
    console.log('Cash Data:', cashData);
    if (cashData) {
        console.log('Updating cashPosition with:', cashData.total_cash_usd);
        safeUpdate('cashPosition', cashData.total_cash_usd);
    } else {
        console.warn('Cash data not available');
    }

    // Update P&L data
    if (plData) {
        safeUpdate('totalRevenue', plData.total_revenue);
        safeUpdate('totalExpenses', plData.total_expenses);
        safeUpdate('netProfit', plData.total_profit);

        // Update profit color
        const profitElement = document.getElementById('netProfit');
        if (profitElement) {
            profitElement.className = `stat-number ${(plData.total_profit || 0) >= 0 ? 'positive' : 'negative'}`;
        }
    }
}

/**
 * Initialize all charts
 */
function initializeCharts() {
    // Revenue vs Expenses Chart
    createRevenueExpensesChart();

    // Monthly P&L Chart
    createMonthlyPLChart();

    // Entity Performance Chart
    createEntityChart();

    // Cash Flow Chart
    createCashFlowChart();

    // Sankey Financial Flow Diagram
    createSankeyDiagram();
}

/**
 * Create Revenue vs Expenses Chart
 */
function createRevenueExpensesChart() {
    const ctx = document.getElementById('revenueExpensesChart');
    if (!ctx) return;

    const plData = dashboardData.monthlyPL?.summary?.period_totals;
    if (!plData) return;

    charts.revenueExpenses = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Revenue', 'Expenses'],
            datasets: [{
                label: 'Amount',
                data: [plData.total_revenue || 0, plData.total_expenses || 0],
                backgroundColor: ['#667eea', '#f56565'],
                borderColor: ['#5a67d8', '#e53e3e'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create Monthly P&L Chart
 */
function createMonthlyPLChart() {
    const ctx = document.getElementById('monthlyPLChart');
    if (!ctx) return;

    const monthlyData = dashboardData.monthlyPL?.monthly_pl;
    if (!monthlyData || monthlyData.length === 0) return;

    const labels = monthlyData.map(m => m.month);
    const revenue = monthlyData.map(m => m.revenue || 0);
    const expenses = monthlyData.map(m => m.expenses || 0);
    const profit = monthlyData.map(m => m.profit || 0);

    charts.monthlyPL = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Revenue',
                    data: revenue,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Expenses',
                    data: expenses,
                    borderColor: '#f56565',
                    backgroundColor: 'rgba(245, 101, 101, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Profit',
                    data: profit,
                    borderColor: '#48bb78',
                    backgroundColor: 'rgba(72, 187, 120, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create Entity Performance Chart
 */
function createEntityChart() {
    const ctx = document.getElementById('entityChart');
    if (!ctx) return;

    const entityData = dashboardData.entitySummary?.entities;
    if (!entityData || entityData.length === 0) return;

    // Get top 5 entities by revenue
    const topEntities = entityData
        .sort((a, b) => (b.financial_metrics?.total_revenue || 0) - (a.financial_metrics?.total_revenue || 0))
        .slice(0, 5);

    const labels = topEntities.map(e => e.entity);
    const data = topEntities.map(e => e.financial_metrics?.total_revenue || 0);

    charts.entity = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Revenue',
                data: data,
                backgroundColor: '#667eea',
                borderColor: '#5a67d8',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45
                    }
                }
            }
        }
    });
}

/**
 * Create Cash Flow Chart
 */
function createCashFlowChart() {
    const ctx = document.getElementById('cashFlowChart');
    if (!ctx) return;

    const cashData = dashboardData.cashDashboard?.trends?.['30_days'];
    if (!cashData || !cashData.daily_positions) return;

    const labels = cashData.daily_positions.map(point => point.date);
    const netFlowData = cashData.daily_positions.map(point => point.daily_change || 0);

    charts.cashFlow = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Daily Cash Change',
                data: netFlowData,
                borderColor: '#48bb78',
                backgroundColor: 'rgba(72, 187, 120, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 10
                    }
                }
            }
        }
    });
}

/**
 * Show/hide custom date range
 */
function showCustomDateRange() {
    const startDateGroup = document.getElementById('customDateRange');
    const endDateGroup = document.getElementById('customDateRangeEnd');

    if (startDateGroup) startDateGroup.style.display = 'block';
    if (endDateGroup) endDateGroup.style.display = 'block';
}

function hideCustomDateRange() {
    const startDateGroup = document.getElementById('customDateRange');
    const endDateGroup = document.getElementById('customDateRangeEnd');

    if (startDateGroup) startDateGroup.style.display = 'none';
    if (endDateGroup) endDateGroup.style.display = 'none';
}

/**
 * Update filter display
 */
function updateFilterDisplay() {
    // Update period selector
    document.getElementById('periodSelector').value = currentFilters.period;

    // Update entity selector
    document.getElementById('entityFilter').value = currentFilters.entity;

    // Update internal transaction filter
    document.getElementById('internalFilter').value = currentFilters.isInternal;

    // Set date inputs
    if (currentFilters.startDate) {
        const startInput = document.getElementById('startDateInput');
        if (startInput) startInput.value = currentFilters.startDate;
    }

    if (currentFilters.endDate) {
        const endInput = document.getElementById('endDateInput');
        if (endInput) endInput.value = currentFilters.endDate;
    }

    // Show/hide custom date range
    if (currentFilters.period === 'custom') {
        showCustomDateRange();
    } else {
        hideCustomDateRange();
    }
}

/**
 * Reset all filters
 */
function resetFilters() {
    currentFilters = {
        period: 'all_time',
        entity: '',
        startDate: null,
        endDate: null,
        isInternal: ''
    };

    updateFilterDisplay();
    refreshDashboard();
}

/**
 * Refresh dashboard data
 */
async function refreshDashboard() {
    showLoading(true);

    try {
        await loadDashboardData();
        updateKPICards();

        // Destroy existing charts
        Object.values(charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        charts = {};

        // Recreate charts
        initializeCharts();

    } catch (error) {
        console.error('Error refreshing dashboard:', error);
        showError('Failed to refresh dashboard data.');
    } finally {
        showLoading(false);
    }
}

/**
 * Utility Functions
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount || 0);
}

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

function showError(message) {
    const modal = document.getElementById('errorModal');
    const messageEl = document.getElementById('errorMessage');

    if (modal && messageEl) {
        messageEl.textContent = message;
        modal.style.display = 'flex';
    }
}

function hideError() {
    const modal = document.getElementById('errorModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Financial Reports Functions
 */
function generateDREReport() {
    try {
        // Show loading
        showLoading(true);

        // Load DRE data and show preview modal
        loadDREPreviewData();

    } catch (error) {
        console.error('Error loading DRE preview:', error);
        showError('Failed to load DRE preview. Please try again.');
        showLoading(false);
    }
}

/**
 * Load DRE data and show preview modal
 */
async function loadDREPreviewData() {
    try {
        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Fetch DRE data from simple JSON endpoint (same as PDF)
        const response = await fetch(`/api/reports/income-statement/simple?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load DRE data');
        }

        // Show modal first to ensure it exists
        openDREModal();

        // Then populate modal with data with small delay to ensure DOM is ready
        setTimeout(() => {
            populateDREModal(data.statement, companyName);
        }, 100);

    } catch (error) {
        console.error('Error loading DRE data:', error);
        showError('Erro ao carregar dados da DRE: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Populate DRE modal with data
 */
function populateDREModal(dreData, companyName) {
    console.log('populateDREModal called with:', dreData, companyName);

    // Check if modal exists first
    const modal = document.getElementById('drePreviewModal');
    if (!modal) {
        console.error('drePreviewModal not found in DOM');
        return;
    }

    // Update summary metrics - handle both simple and full API response formats
    let totalRevenue, grossProfit, netIncome;

    if (dreData.summary_metrics) {
        // Full API format
        const summaryMetrics = dreData.summary_metrics;
        totalRevenue = summaryMetrics.total_revenue || 0;
        grossProfit = summaryMetrics.gross_profit || 0;
        netIncome = summaryMetrics.net_income || 0;
    } else {
        // Simple API format - extract from main structure
        grossProfit = dreData.gross_profit?.amount || 0;
        netIncome = dreData.net_income?.amount || 0;
        // Calculate revenue as Gross Profit + Cost of Goods Sold
        totalRevenue = grossProfit + (dreData.cost_of_goods_sold?.total || 0);
    }

    console.log('Summary metrics:', {totalRevenue, grossProfit, netIncome});

    // Safe element updates with null checks
    const safeUpdateElement = (id, value, styleUpdates = null) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            if (styleUpdates) {
                Object.assign(element.style, styleUpdates);
            }
            console.log(`Successfully updated element '${id}' with value: ${value}`);
        } else {
            console.warn(`Element with ID '${id}' not found in DOM`);

            // Additional debugging
            const allElements = document.querySelectorAll('[id]');
            console.log('All elements with IDs found:', Array.from(allElements).map(el => el.id));
        }
    };

    safeUpdateElement('drePreviewRevenue', formatCurrency(totalRevenue));
    safeUpdateElement('drePreviewGrossProfit', formatCurrency(grossProfit));
    safeUpdateElement('drePreviewNetIncome', formatCurrency(netIncome), {
        color: netIncome >= 0 ? '#48bb78' : '#f56565'
    });

    // Update period information
    const periodInfo = dreData.period || {};
    const periodName = periodInfo.period_name || 'Período completo';
    safeUpdateElement('drePeriodInfo', periodName);

    // Update company information
    safeUpdateElement('dreCompanyInfo', companyName);
    safeUpdateElement('dreGeneratedAt', new Date().toLocaleDateString('pt-BR'));

    // Populate detailed table with DRE structure
    populateDRETable(dreData);
}

/**
 * Populate DRE detailed table
 */
function populateDRETable(dreData) {
    const tableBody = document.getElementById('dreDetailsList');
    if (!tableBody) {
        console.error('dreDetailsList element not found');
        return;
    }
    tableBody.innerHTML = '';

    // Extract values for DRE calculation
    const grossProfitAmount = dreData.gross_profit?.amount || 0;
    const costOfGoodsSold = dreData.cost_of_goods_sold?.total || 0;
    const operatingExpenses = dreData.operating_expenses?.total || 0;
    const operatingIncome = dreData.operating_income?.amount || 0;
    const otherIncomeExpenses = dreData.other_income_expenses?.total || 0;
    const netIncomeAmount = dreData.net_income?.amount || 0;

    // Calculate revenue as Gross Profit + Cost of Goods Sold
    const revenueAmount = grossProfitAmount + costOfGoodsSold;

    // Build DRE structure following Brazilian standards
    const dreStructure = [
        {
            name: 'Receita Operacional Bruta',
            amount: revenueAmount,
            isMain: true,
            type: 'revenue'
        },
        {
            name: '(-) Custo dos Produtos Vendidos',
            amount: -costOfGoodsSold,
            isMain: false,
            type: 'expense'
        },
        {
            name: '= Lucro Bruto',
            amount: grossProfitAmount,
            isMain: true,
            type: 'calculated'
        },
        {
            name: '(-) Despesas Operacionais',
            amount: -operatingExpenses,
            isMain: false,
            type: 'expense'
        },
        {
            name: '= Lucro Operacional',
            amount: operatingIncome,
            isMain: true,
            type: 'calculated'
        },
        {
            name: '(+/-) Outras Receitas/Despesas',
            amount: otherIncomeExpenses,
            isMain: false,
            type: 'other'
        },
        {
            name: '= Lucro Líquido do Exercício',
            amount: netIncomeAmount,
            isMain: true,
            type: 'final'
        }
    ];

    dreStructure.forEach(item => {
        const row = document.createElement('tr');

        // Calculate percentage of revenue - use the calculated revenueAmount
        const percentage = revenueAmount > 0 ? ((item.amount / revenueAmount) * 100).toFixed(1) : '0.0';

        row.innerHTML = `
            <td style="padding: 0.5rem 0; padding-left: ${item.isMain ? '0px' : '20px'}; font-weight: ${item.isMain ? 'bold' : 'normal'}; border-bottom: 1px solid #f1f5f9;">
                ${item.name}
            </td>
            <td style="text-align: right; padding: 0.5rem 0; font-weight: ${item.isMain ? 'bold' : 'normal'}; color: ${getDREAmountColor(item.amount, item.type)}; border-bottom: 1px solid #f1f5f9;">
                ${formatCurrency(item.amount)}
            </td>
            <td style="text-align: right; padding: 0.5rem 0; font-weight: ${item.isMain ? 'bold' : 'normal'}; color: #666; border-bottom: 1px solid #f1f5f9;">
                ${percentage}%
            </td>
        `;

        // Add special styling for main categories
        if (item.isMain) {
            row.style.backgroundColor = '#f8f9fa';
        }

        // Special styling for final result
        if (item.type === 'final') {
            row.style.backgroundColor = '#e8f5e8';
            row.style.fontWeight = 'bold';
        }

        tableBody.appendChild(row);
    });
}

/**
 * Get color for amount based on value and context
 */
function getAmountColor(amount) {
    if (amount === 0) return '#6c757d';
    return amount > 0 ? '#28a745' : '#dc3545';
}

/**
 * Get color for DRE amounts based on type and value
 */
function getDREAmountColor(amount, type) {
    if (amount === 0) return '#6c757d';

    switch (type) {
        case 'revenue':
            return amount > 0 ? '#28a745' : '#dc3545';
        case 'expense':
            return '#dc3545'; // Always red for expenses (shown as negative)
        case 'calculated':
        case 'final':
            return amount >= 0 ? '#28a745' : '#dc3545';
        case 'other':
            return amount >= 0 ? '#28a745' : '#dc3545';
        default:
            return amount > 0 ? '#28a745' : '#dc3545';
    }
}

/**
 * Open DRE preview modal
 */
function openDREModal() {
    let modal = document.getElementById('drePreviewModal');

    // If modal doesn't exist, create it dynamically
    if (!modal) {
        console.log('Modal not found, creating dynamically...');
        modal = createDREModal();
    }

    if (modal) {
        modal.style.display = 'flex';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        modal.style.zIndex = '1000';
        modal.style.justifyContent = 'center';
        modal.style.alignItems = 'center';

        // Focus trap for accessibility
        modal.focus();

        console.log('DRE modal opened successfully');
    } else {
        console.error('Failed to create or find DRE modal');
    }
}

/**
 * Create DRE modal dynamically
 */
function createDREModal() {
    const modalHTML = `
        <div id="drePreviewModal" class="modal" style="display: none;">
            <div class="modal-content" style="max-width: 800px; width: 90%; background: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); max-height: 90vh; overflow-y: auto;">
                <div class="modal-header" style="padding: 1.5rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #2d3748;">📊 Demonstração do Resultado do Exercício (DRE)</h3>
                    <span class="close" onclick="closeDREModal()" style="font-size: 1.5rem; cursor: pointer; color: #718096; border: none; background: none;">&times;</span>
                </div>
                <div class="modal-body" style="padding: 1.5rem;">
                    <div id="drePreviewContent">
                        <div class="dre-summary" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📋 Resumo do Período</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Receita Total</div>
                                    <div id="drePreviewRevenue" style="font-size: 1.2rem; font-weight: bold; color: #48bb78;">R$ 0,00</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Lucro Bruto</div>
                                    <div id="drePreviewGrossProfit" style="font-size: 1.2rem; font-weight: bold; color: #4299e1;">R$ 0,00</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Resultado Líquido</div>
                                    <div id="drePreviewNetIncome" style="font-size: 1.2rem; font-weight: bold;">R$ 0,00</div>
                                </div>
                            </div>
                        </div>

                        <div class="dre-details" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📈 Detalhes Financeiros</h4>
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;">
                                <table style="width: 100%; border-collapse: collapse;">
                                    <thead>
                                        <tr style="border-bottom: 2px solid #e2e8f0;">
                                            <th style="text-align: left; padding: 0.75rem 0; color: #4a5568;">Item</th>
                                            <th style="text-align: right; padding: 0.75rem 0; color: #4a5568;">Valor</th>
                                            <th style="text-align: right; padding: 0.75rem 0; color: #4a5568;">% da Receita</th>
                                        </tr>
                                    </thead>
                                    <tbody id="dreDetailsList">
                                        <!-- Items will be populated by JavaScript -->
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div class="dre-period-info" style="background: #edf2f7; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                                <div><strong>Período:</strong> <span id="drePeriodInfo">-</span></div>
                                <div><strong>Empresa:</strong> <span id="dreCompanyInfo">-</span></div>
                                <div><strong>Gerado em:</strong> <span id="dreGeneratedAt">-</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer" style="display: flex; gap: 1rem; justify-content: flex-end; padding: 1.5rem; border-top: 1px solid #e2e8f0;">
                    <button onclick="closeDREModal()" style="background-color: #e2e8f0; color: #4a5568; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">❌ Fechar</button>
                    <button onclick="downloadDREPDF()" style="background-color: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">📄 Baixar PDF</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = document.getElementById('drePreviewModal');
    console.log('Modal created dynamically:', modal);
    return modal;
}

/**
 * Close DRE preview modal
 */
function closeDREModal() {
    const modal = document.getElementById('drePreviewModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Download DRE PDF (called from modal)
 */
function downloadDREPDF() {
    try {
        // Show loading
        showLoading(true);

        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Build URL
        const url = `/api/reports/dre-pdf?${params.toString()}`;

        // Create a temporary link to download the PDF
        const link = document.createElement('a');
        link.href = url;
        link.download = ''; // Let the server set the filename
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Close modal
        closeDREModal();

        // Show success notification
        showReportGenerationStatus('📄 DRE PDF gerado com sucesso!', true);

        // Hide loading after a short delay
        setTimeout(() => {
            showLoading(false);
        }, 1000);

    } catch (error) {
        console.error('Error downloading DRE PDF:', error);
        showError('Failed to download DRE PDF. Please try again.');
        showLoading(false);
    }
}

function showReportGenerationStatus(message, isSuccess = true) {
    // Create a simple notification
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${isSuccess ? '#48bb78' : '#f56565'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 1001;
        font-size: 0.9rem;
        max-width: 300px;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        if (document.body.contains(notification)) {
            document.body.removeChild(notification);
        }
    }, 3000);
}

/**
 * Generate Balance Sheet Report (show modal first)
 */
function generateBalanceSheetReport() {
    try {
        // Show loading
        showLoading(true);

        // Load Balance Sheet data and show preview modal
        loadBalanceSheetPreviewData();

    } catch (error) {
        console.error('Error loading Balance Sheet preview:', error);
        showError('Failed to load Balance Sheet preview. Please try again.');
        showLoading(false);
    }
}

/**
 * Load Balance Sheet data and show preview modal
 */
async function loadBalanceSheetPreviewData() {
    try {
        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Fetch Balance Sheet data from simple JSON endpoint
        const response = await fetch(`/api/reports/balance-sheet/simple?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load Balance Sheet data');
        }

        // Show modal first to ensure it exists
        openBalanceSheetModal();

        // Then populate modal with data with small delay to ensure DOM is ready
        setTimeout(() => {
            populateBalanceSheetModal(data.statement, companyName);
        }, 100);

    } catch (error) {
        console.error('Error loading Balance Sheet data:', error);
        showError('Erro ao carregar dados do Balanço Patrimonial: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Generate Cash Flow Report (show modal first)
 */
function generateCashFlowReport() {
    try {
        // Show loading
        showLoading(true);

        // Load Cash Flow data and show preview modal
        loadCashFlowPreviewData();

    } catch (error) {
        console.error('Error loading Cash Flow preview:', error);
        showError('Failed to load Cash Flow preview. Please try again.');
        showLoading(false);
    }
}

/**
 * Load Cash Flow data and show preview modal
 */
async function loadCashFlowPreviewData() {
    try {
        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Fetch Cash Flow data from simple JSON endpoint
        const response = await fetch(`/api/reports/cash-flow/simple?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load Cash Flow data');
        }

        // Show modal first to ensure it exists
        openCashFlowModal();

        // Then populate modal with data with small delay to ensure DOM is ready
        setTimeout(() => {
            populateCashFlowModal(data.statement, companyName);
        }, 100);

    } catch (error) {
        console.error('Error loading Cash Flow data:', error);
        showError('Erro ao carregar dados do Fluxo de Caixa: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Generate DMPL Report (show modal first)
 */
function generateDMPLReport() {
    try {
        // Show loading
        showLoading(true);

        // Load DMPL data and show preview modal
        loadDMPLPreviewData();

    } catch (error) {
        console.error('Error loading DMPL preview:', error);
        showError('Failed to load DMPL preview. Please try again.');
        showLoading(false);
    }
}

/**
 * Load DMPL data and show preview modal
 */
async function loadDMPLPreviewData() {
    try {
        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Fetch DMPL data from simple JSON endpoint
        const response = await fetch(`/api/reports/dmpl/simple?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load DMPL data');
        }

        // Show modal first to ensure it exists
        openDMPLModal();

        // Then populate modal with data with small delay to ensure DOM is ready
        setTimeout(() => {
            populateDMPLModal(data.statement, companyName);
        }, 100);

    } catch (error) {
        console.error('Error loading DMPL data:', error);
        showError('Erro ao carregar dados do DMPL: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Balance Sheet Modal Functions
 */

/**
 * Populate Balance Sheet modal with data
 */
function populateBalanceSheetModal(balanceSheetData, companyName) {
    console.log('populateBalanceSheetModal called with:', balanceSheetData, companyName);

    // Check if modal exists first
    const modal = document.getElementById('balanceSheetPreviewModal');
    if (!modal) {
        console.error('balanceSheetPreviewModal not found in DOM');
        return;
    }

    // Extract metrics from API response
    let totalAssets, totalLiabilities, totalEquity;

    if (balanceSheetData.summary_metrics) {
        const summaryMetrics = balanceSheetData.summary_metrics;
        totalAssets = summaryMetrics.total_assets || 0;
        totalLiabilities = summaryMetrics.total_liabilities || 0;
        totalEquity = summaryMetrics.total_equity || 0;
    } else {
        // Fallback to assets structure if available
        totalAssets = balanceSheetData.assets?.total || 0;
        totalLiabilities = balanceSheetData.liabilities?.total || 0;
        totalEquity = balanceSheetData.equity?.total || 0;
    }

    console.log('Balance Sheet metrics:', {totalAssets, totalLiabilities, totalEquity});

    // Safe element updates with null checks
    const safeUpdateElement = (id, value, styleUpdates = null) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            if (styleUpdates) {
                Object.assign(element.style, styleUpdates);
            }
            console.log(`Successfully updated element '${id}' with value: ${value}`);
        } else {
            console.warn(`Element with ID '${id}' not found in DOM`);
        }
    };

    safeUpdateElement('balanceSheetPreviewAssets', formatCurrency(totalAssets));
    safeUpdateElement('balanceSheetPreviewLiabilities', formatCurrency(totalLiabilities));
    safeUpdateElement('balanceSheetPreviewEquity', formatCurrency(totalEquity), {
        color: totalEquity >= 0 ? '#48bb78' : '#f56565'
    });

    // Update period information
    const periodInfo = balanceSheetData.period || {};
    const periodName = periodInfo.period_name || 'Período completo';
    safeUpdateElement('balanceSheetPeriodInfo', periodName);

    // Update company information
    safeUpdateElement('balanceSheetCompanyInfo', companyName);
    safeUpdateElement('balanceSheetGeneratedAt', new Date().toLocaleDateString('pt-BR'));

    // Populate detailed table with Balance Sheet structure
    populateBalanceSheetTable(balanceSheetData);
}

/**
 * Populate Balance Sheet detailed table
 */
function populateBalanceSheetTable(balanceSheetData) {
    const tableBody = document.getElementById('balanceSheetDetailsList');
    if (!tableBody) {
        console.error('balanceSheetDetailsList element not found');
        return;
    }
    tableBody.innerHTML = '';

    // Extract values for Balance Sheet calculation
    const totalAssets = balanceSheetData.assets?.total || balanceSheetData.summary_metrics?.total_assets || 0;
    const totalLiabilities = balanceSheetData.liabilities?.total || balanceSheetData.summary_metrics?.total_liabilities || 0;
    const totalEquity = balanceSheetData.equity?.total || balanceSheetData.summary_metrics?.total_equity || 0;

    // Build Balance Sheet structure dynamically from API data
    const balanceSheetStructure = [];

    // ASSETS SECTION
    balanceSheetStructure.push({
        name: 'ATIVO',
        amount: null,
        isHeader: true,
        type: 'header'
    });

    // Current Assets
    if (balanceSheetData.assets?.current_assets) {
        const currentAssets = balanceSheetData.assets.current_assets;
        if (currentAssets.total > 0 || currentAssets.categories?.length > 0) {
            balanceSheetStructure.push({
                name: 'Ativo Circulante',
                amount: currentAssets.total,
                isMain: true,
                type: 'asset'
            });

            // Add categories
            if (currentAssets.categories && currentAssets.categories.length > 0) {
                currentAssets.categories.forEach(cat => {
                    balanceSheetStructure.push({
                        name: '    ' + cat.category,
                        amount: cat.amount,
                        isMain: false,
                        type: 'asset',
                        count: cat.count
                    });
                });
            }
        }
    }

    // Non-Current Assets
    if (balanceSheetData.assets?.non_current_assets) {
        const nonCurrentAssets = balanceSheetData.assets.non_current_assets;
        if (nonCurrentAssets.total > 0 || nonCurrentAssets.categories?.length > 0) {
            balanceSheetStructure.push({
                name: 'Ativo Não Circulante',
                amount: nonCurrentAssets.total,
                isMain: true,
                type: 'asset'
            });

            // Add categories
            if (nonCurrentAssets.categories && nonCurrentAssets.categories.length > 0) {
                nonCurrentAssets.categories.forEach(cat => {
                    balanceSheetStructure.push({
                        name: '    ' + cat.category,
                        amount: cat.amount,
                        isMain: false,
                        type: 'asset',
                        count: cat.count
                    });
                });
            }
        }
    }

    // Total Assets
    balanceSheetStructure.push({
        name: 'TOTAL DO ATIVO',
        amount: totalAssets,
        isMain: true,
        type: 'asset_total'
    });

    // Spacer
    balanceSheetStructure.push({
        name: '',
        amount: null,
        isHeader: false,
        type: 'spacer'
    });

    // LIABILITIES SECTION
    balanceSheetStructure.push({
        name: 'PASSIVO E PATRIMÔNIO LÍQUIDO',
        amount: null,
        isHeader: true,
        type: 'header'
    });

    // Current Liabilities
    if (balanceSheetData.liabilities?.current_liabilities) {
        const currentLiabilities = balanceSheetData.liabilities.current_liabilities;
        if (currentLiabilities.total > 0 || currentLiabilities.categories?.length > 0) {
            balanceSheetStructure.push({
                name: 'Passivo Circulante',
                amount: currentLiabilities.total,
                isMain: true,
                type: 'liability'
            });

            // Add categories
            if (currentLiabilities.categories && currentLiabilities.categories.length > 0) {
                currentLiabilities.categories.forEach(cat => {
                    balanceSheetStructure.push({
                        name: '    ' + cat.category,
                        amount: cat.amount,
                        isMain: false,
                        type: 'liability',
                        count: cat.count
                    });
                });
            }
        }
    }

    // Non-Current Liabilities
    if (balanceSheetData.liabilities?.non_current_liabilities) {
        const nonCurrentLiabilities = balanceSheetData.liabilities.non_current_liabilities;
        if (nonCurrentLiabilities.total > 0 || nonCurrentLiabilities.categories?.length > 0) {
            balanceSheetStructure.push({
                name: 'Passivo Não Circulante',
                amount: nonCurrentLiabilities.total,
                isMain: true,
                type: 'liability'
            });

            // Add categories
            if (nonCurrentLiabilities.categories && nonCurrentLiabilities.categories.length > 0) {
                nonCurrentLiabilities.categories.forEach(cat => {
                    balanceSheetStructure.push({
                        name: '    ' + cat.category,
                        amount: cat.amount,
                        isMain: false,
                        type: 'liability',
                        count: cat.count
                    });
                });
            }
        }
    }

    // Total Liabilities
    balanceSheetStructure.push({
        name: 'TOTAL DO PASSIVO',
        amount: totalLiabilities,
        isMain: true,
        type: 'liability_total'
    });

    // EQUITY SECTION
    if (balanceSheetData.equity) {
        balanceSheetStructure.push({
            name: 'Patrimônio Líquido',
            amount: totalEquity,
            isMain: true,
            type: 'equity'
        });

        // Add equity categories
        if (balanceSheetData.equity.categories && balanceSheetData.equity.categories.length > 0) {
            balanceSheetData.equity.categories.forEach(cat => {
                balanceSheetStructure.push({
                    name: '    ' + cat.category,
                    amount: cat.amount,
                    isMain: false,
                    type: 'equity',
                    count: cat.count
                });
            });
        }
    }

    // Spacer
    balanceSheetStructure.push({
        name: '',
        amount: null,
        isHeader: false,
        type: 'spacer'
    });

    // Total Liabilities + Equity
    balanceSheetStructure.push({
        name: 'TOTAL DO PASSIVO + PATRIMÔNIO LÍQUIDO',
        amount: totalLiabilities + totalEquity,
        isMain: true,
        type: 'total'
    });

    balanceSheetStructure.forEach(item => {
        if (item.type === 'spacer' && !item.name) {
            // Add empty row for spacing
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="2" style="padding: 0.25rem;"></td>`;
            tableBody.appendChild(row);
            return;
        }

        const row = document.createElement('tr');

        if (item.isHeader) {
            row.innerHTML = `
                <td colspan="2" style="padding: 0.75rem 0; font-weight: bold; font-size: 1.1rem; color: #2d3748; background: #f7fafc; border-bottom: 2px solid #e2e8f0;">
                    ${item.name}
                </td>
            `;
        } else {
            row.innerHTML = `
                <td style="padding: 0.5rem 0; padding-left: ${item.isMain ? '20px' : '40px'}; font-weight: ${item.isMain ? 'bold' : 'normal'}; border-bottom: 1px solid #f1f5f9;">
                    ${item.name}
                </td>
                <td style="text-align: right; padding: 0.5rem 0; font-weight: ${item.isMain ? 'bold' : 'normal'}; color: ${getBalanceSheetAmountColor(item.amount, item.type)}; border-bottom: 1px solid #f1f5f9;">
                    ${formatCurrency(item.amount)}
                </td>
            `;
        }

        // Add special styling for main categories
        if (item.isMain) {
            row.style.backgroundColor = '#f8f9fa';
        }

        // Special styling for total
        if (item.type === 'total') {
            row.style.backgroundColor = '#e8f5e8';
            row.style.fontWeight = 'bold';
        }

        tableBody.appendChild(row);
    });
}

/**
 * Get color for Balance Sheet amounts based on type and value
 */
function getBalanceSheetAmountColor(amount, type) {
    if (amount === null || amount === 0) return '#6c757d';

    switch (type) {
        case 'asset':
            return amount > 0 ? '#4299e1' : '#f56565';
        case 'liability':
            return amount > 0 ? '#f56565' : '#4299e1';
        case 'equity':
        case 'total':
            return amount >= 0 ? '#48bb78' : '#f56565';
        default:
            return amount > 0 ? '#4299e1' : '#f56565';
    }
}

/**
 * Open Balance Sheet preview modal
 */
function openBalanceSheetModal() {
    let modal = document.getElementById('balanceSheetPreviewModal');

    // If modal doesn't exist, create it dynamically
    if (!modal) {
        console.log('Modal not found, creating dynamically...');
        modal = createBalanceSheetModal();
    }

    if (modal) {
        modal.style.display = 'flex';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        modal.style.zIndex = '1000';
        modal.style.justifyContent = 'center';
        modal.style.alignItems = 'center';

        // Focus trap for accessibility
        modal.focus();

        console.log('Balance Sheet modal opened successfully');
    } else {
        console.error('Failed to create or find Balance Sheet modal');
    }
}

/**
 * Create Balance Sheet modal dynamically
 */
function createBalanceSheetModal() {
    const modalHTML = `
        <div id="balanceSheetPreviewModal" class="modal" style="display: none;">
            <div class="modal-content" style="max-width: 800px; width: 90%; background: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); max-height: 90vh; overflow-y: auto;">
                <div class="modal-header" style="padding: 1.5rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #2d3748;">⚖️ Balanço Patrimonial (BP)</h3>
                    <span class="close" onclick="closeBalanceSheetModal()" style="font-size: 1.5rem; cursor: pointer; color: #718096; border: none; background: none;">&times;</span>
                </div>
                <div class="modal-body" style="padding: 1.5rem;">
                    <div id="balanceSheetPreviewContent">
                        <div class="balance-sheet-summary" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📋 Resumo do Período</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Total do Ativo</div>
                                    <div id="balanceSheetPreviewAssets" style="font-size: 1.2rem; font-weight: bold; color: #4299e1;">$0</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Total do Passivo</div>
                                    <div id="balanceSheetPreviewLiabilities" style="font-size: 1.2rem; font-weight: bold; color: #f56565;">$0</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Patrimônio Líquido</div>
                                    <div id="balanceSheetPreviewEquity" style="font-size: 1.2rem; font-weight: bold;">$0</div>
                                </div>
                            </div>
                        </div>

                        <div class="balance-sheet-details" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📊 Estrutura Patrimonial</h4>
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;">
                                <table style="width: 100%; border-collapse: collapse;">
                                    <thead>
                                        <tr style="border-bottom: 2px solid #e2e8f0;">
                                            <th style="text-align: left; padding: 0.75rem 0; color: #4a5568;">Item</th>
                                            <th style="text-align: right; padding: 0.75rem 0; color: #4a5568;">Valor</th>
                                        </tr>
                                    </thead>
                                    <tbody id="balanceSheetDetailsList">
                                        <!-- Items will be populated by JavaScript -->
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div class="balance-sheet-period-info" style="background: #edf2f7; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                                <div><strong>Período:</strong> <span id="balanceSheetPeriodInfo">-</span></div>
                                <div><strong>Empresa:</strong> <span id="balanceSheetCompanyInfo">-</span></div>
                                <div><strong>Gerado em:</strong> <span id="balanceSheetGeneratedAt">-</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer" style="display: flex; gap: 1rem; justify-content: flex-end; padding: 1.5rem; border-top: 1px solid #e2e8f0;">
                    <button onclick="closeBalanceSheetModal()" style="background-color: #e2e8f0; color: #4a5568; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">❌ Fechar</button>
                    <button onclick="downloadBalanceSheetPDF()" style="background-color: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">📄 Baixar PDF</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = document.getElementById('balanceSheetPreviewModal');
    console.log('Balance Sheet modal created dynamically:', modal);
    return modal;
}

/**
 * Close Balance Sheet preview modal
 */
function closeBalanceSheetModal() {
    const modal = document.getElementById('balanceSheetPreviewModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Download Balance Sheet PDF (called from modal)
 */
function downloadBalanceSheetPDF() {
    try {
        // Show loading
        showLoading(true);

        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Build URL
        const url = `/api/reports/balance-sheet-pdf?${params.toString()}`;

        // Create a temporary link to download the PDF
        const link = document.createElement('a');
        link.href = url;
        link.download = ''; // Let the server set the filename
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Close modal
        closeBalanceSheetModal();

        // Show success notification
        showReportGenerationStatus('⚖️ Balanço Patrimonial PDF gerado com sucesso!', true);

        // Hide loading after a short delay
        setTimeout(() => {
            showLoading(false);
        }, 1000);

    } catch (error) {
        console.error('Error downloading Balance Sheet PDF:', error);
        showError('Failed to download Balance Sheet PDF. Please try again.');
        showLoading(false);
    }
}

/**
 * Cash Flow Modal Functions
 */

/**
 * Populate Cash Flow modal with data
 */
function populateCashFlowModal(cashFlowData, companyName) {
    console.log('populateCashFlowModal called with:', cashFlowData, companyName);

    // Check if modal exists first
    const modal = document.getElementById('cashFlowPreviewModal');
    if (!modal) {
        console.error('cashFlowPreviewModal not found in DOM');
        return;
    }

    // Extract metrics from API response
    let netCashFlow, cashReceipts, cashPayments, endingCash;

    if (cashFlowData.summary_metrics) {
        const summaryMetrics = cashFlowData.summary_metrics;
        netCashFlow = summaryMetrics.net_cash_flow || 0;
        cashReceipts = summaryMetrics.cash_receipts || 0;
        cashPayments = summaryMetrics.cash_payments || 0;
        endingCash = summaryMetrics.ending_cash || 0;
    } else if (cashFlowData.operating_activities) {
        // Fallback to operating activities structure
        const operating = cashFlowData.operating_activities;
        cashReceipts = operating.cash_receipts || 0;
        cashPayments = operating.cash_payments || 0;
        netCashFlow = operating.net_operating || 0;
        endingCash = netCashFlow; // Simplified
    } else {
        // Default values
        cashReceipts = 0;
        cashPayments = 0;
        netCashFlow = 0;
        endingCash = 0;
    }

    console.log('Cash Flow metrics:', {netCashFlow, cashReceipts, cashPayments, endingCash});

    // Safe element updates with null checks
    const safeUpdateElement = (id, value, styleUpdates = null) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            if (styleUpdates) {
                Object.assign(element.style, styleUpdates);
            }
            console.log(`Successfully updated element '${id}' with value: ${value}`);
        } else {
            console.warn(`Element with ID '${id}' not found in DOM`);
        }
    };

    safeUpdateElement('cashFlowPreviewReceipts', formatCurrency(cashReceipts));
    safeUpdateElement('cashFlowPreviewPayments', formatCurrency(cashPayments));
    safeUpdateElement('cashFlowPreviewNetFlow', formatCurrency(netCashFlow), {
        color: netCashFlow >= 0 ? '#48bb78' : '#f56565'
    });

    // Update period information
    const periodInfo = cashFlowData.period || {};
    const periodName = periodInfo.period_name || 'Período completo';
    safeUpdateElement('cashFlowPeriodInfo', periodName);

    // Update company information
    safeUpdateElement('cashFlowCompanyInfo', companyName);
    safeUpdateElement('cashFlowGeneratedAt', new Date().toLocaleDateString('pt-BR'));

    // Populate detailed table with Cash Flow structure
    populateCashFlowTable(cashFlowData);
}

/**
 * Populate Cash Flow detailed table
 */
function populateCashFlowTable(cashFlowData) {
    const tableBody = document.getElementById('cashFlowDetailsList');
    if (!tableBody) {
        console.error('cashFlowDetailsList element not found');
        return;
    }
    tableBody.innerHTML = '';

    // Extract values for Cash Flow calculation
    const cashReceipts = cashFlowData.summary_metrics?.cash_receipts || cashFlowData.operating_activities?.cash_receipts || 0;
    const cashPayments = cashFlowData.summary_metrics?.cash_payments || cashFlowData.operating_activities?.cash_payments || 0;
    const netOperating = cashFlowData.summary_metrics?.net_cash_flow || cashFlowData.operating_activities?.net_operating || (cashReceipts - cashPayments);

    // Build Cash Flow structure dynamically from API data
    const cashFlowStructure = [];

    // OPERATING ACTIVITIES SECTION
    cashFlowStructure.push({
        name: 'FLUXOS DE CAIXA DAS ATIVIDADES OPERACIONAIS',
        amount: null,
        isHeader: true,
        type: 'header'
    });

    // Add operating categories from API data
    if (cashFlowData.operating_activities?.categories && cashFlowData.operating_activities.categories.length > 0) {
        cashFlowData.operating_activities.categories.forEach(cat => {
            cashFlowStructure.push({
                name: '    ' + cat.category,
                amount: cat.amount,
                isMain: false,
                type: cat.amount > 0 ? 'operating_inflow' : 'operating_outflow',
                count: cat.count
            });
        });
    } else {
        // Fallback to simple structure
        if (cashReceipts > 0) {
            cashFlowStructure.push({
                name: '    Recebimentos de Clientes',
                amount: cashReceipts,
                isMain: false,
                type: 'operating_inflow'
            });
        }
        if (cashPayments > 0) {
            cashFlowStructure.push({
                name: '    Pagamentos a Fornecedores e Funcionários',
                amount: -cashPayments,
                isMain: false,
                type: 'operating_outflow'
            });
        }
    }

    cashFlowStructure.push({
        name: 'Caixa Líquido das Atividades Operacionais',
        amount: netOperating,
        isMain: true,
        type: 'operating_total'
    });

    // Spacer
    cashFlowStructure.push({
        name: '',
        amount: null,
        isHeader: false,
        type: 'spacer'
    });

    // INVESTING ACTIVITIES SECTION
    const netInvesting = cashFlowData.investing_activities?.net_investing || 0;

    cashFlowStructure.push({
        name: 'FLUXOS DE CAIXA DAS ATIVIDADES DE INVESTIMENTO',
        amount: null,
        isHeader: true,
        type: 'header'
    });

    // Add investing categories from API data
    if (cashFlowData.investing_activities?.categories && cashFlowData.investing_activities.categories.length > 0) {
        cashFlowData.investing_activities.categories.forEach(cat => {
            cashFlowStructure.push({
                name: '    ' + cat.category,
                amount: cat.amount,
                isMain: false,
                type: cat.amount > 0 ? 'investing_inflow' : 'investing_outflow',
                count: cat.count
            });
        });
    }

    cashFlowStructure.push({
        name: 'Caixa Líquido das Atividades de Investimento',
        amount: netInvesting,
        isMain: true,
        type: 'investing_total'
    });

    // Spacer
    cashFlowStructure.push({
        name: '',
        amount: null,
        isHeader: false,
        type: 'spacer'
    });

    // FINANCING ACTIVITIES SECTION
    const netFinancing = cashFlowData.financing_activities?.net_financing || 0;

    cashFlowStructure.push({
        name: 'FLUXOS DE CAIXA DAS ATIVIDADES DE FINANCIAMENTO',
        amount: null,
        isHeader: true,
        type: 'header'
    });

    // Add financing categories from API data
    if (cashFlowData.financing_activities?.categories && cashFlowData.financing_activities.categories.length > 0) {
        cashFlowData.financing_activities.categories.forEach(cat => {
            cashFlowStructure.push({
                name: '    ' + cat.category,
                amount: cat.amount,
                isMain: false,
                type: cat.amount > 0 ? 'financing_inflow' : 'financing_outflow',
                count: cat.count
            });
        });
    }

    cashFlowStructure.push({
        name: 'Caixa Líquido das Atividades de Financiamento',
        amount: netFinancing,
        isMain: true,
        type: 'financing_total'
    });

    // Spacer
    cashFlowStructure.push({
        name: '',
        amount: null,
        isHeader: false,
        type: 'spacer'
    });

    // Net change in cash
    const totalNetChange = netOperating + netInvesting + netFinancing;
    cashFlowStructure.push({
        name: 'AUMENTO (DIMINUIÇÃO) LÍQUIDA DE CAIXA',
        amount: totalNetChange,
        isMain: true,
        type: 'net_change'
    });

    cashFlowStructure.forEach(item => {
        if (item.type === 'spacer' && !item.name) {
            // Add empty row for spacing
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="2" style="padding: 0.25rem;"></td>`;
            tableBody.appendChild(row);
            return;
        }

        const row = document.createElement('tr');

        if (item.isHeader) {
            row.innerHTML = `
                <td colspan="2" style="padding: 0.75rem 0; font-weight: bold; font-size: 1.1rem; color: #2d3748; background: #f7fafc; border-bottom: 2px solid #e2e8f0;">
                    ${item.name}
                </td>
            `;
        } else {
            row.innerHTML = `
                <td style="padding: 0.5rem 0; padding-left: ${item.isMain ? '20px' : '40px'}; font-weight: ${item.isMain ? 'bold' : 'normal'}; border-bottom: 1px solid #f1f5f9;">
                    ${item.name}
                </td>
                <td style="text-align: right; padding: 0.5rem 0; font-weight: ${item.isMain ? 'bold' : 'normal'}; color: ${getCashFlowAmountColor(item.amount, item.type)}; border-bottom: 1px solid #f1f5f9;">
                    ${formatCurrency(item.amount)}
                </td>
            `;
        }

        // Add special styling for main categories
        if (item.isMain) {
            row.style.backgroundColor = '#f8f9fa';
        }

        // Special styling for net change
        if (item.type === 'net_change') {
            row.style.backgroundColor = '#e8f5e8';
            row.style.fontWeight = 'bold';
        }

        tableBody.appendChild(row);
    });
}

/**
 * Get color for Cash Flow amounts based on type and value
 */
function getCashFlowAmountColor(amount, type) {
    if (amount === null || amount === 0) return '#6c757d';

    switch (type) {
        case 'operating_inflow':
            return amount > 0 ? '#48bb78' : '#f56565';
        case 'operating_outflow':
            return '#f56565'; // Always red for outflows (shown as negative)
        case 'operating_total':
        case 'investing_total':
        case 'financing_total':
        case 'net_change':
            return amount >= 0 ? '#48bb78' : '#f56565';
        default:
            return amount > 0 ? '#48bb78' : '#f56565';
    }
}

/**
 * Open Cash Flow preview modal
 */
function openCashFlowModal() {
    let modal = document.getElementById('cashFlowPreviewModal');

    // If modal doesn't exist, create it dynamically
    if (!modal) {
        console.log('Modal not found, creating dynamically...');
        modal = createCashFlowModal();
    }

    if (modal) {
        modal.style.display = 'flex';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        modal.style.zIndex = '1000';
        modal.style.justifyContent = 'center';
        modal.style.alignItems = 'center';

        // Focus trap for accessibility
        modal.focus();

        console.log('Cash Flow modal opened successfully');
    } else {
        console.error('Failed to create or find Cash Flow modal');
    }
}

/**
 * Create Cash Flow modal dynamically
 */
function createCashFlowModal() {
    const modalHTML = `
        <div id="cashFlowPreviewModal" class="modal" style="display: none;">
            <div class="modal-content" style="max-width: 800px; width: 90%; background: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); max-height: 90vh; overflow-y: auto;">
                <div class="modal-header" style="padding: 1.5rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #2d3748;">💰 Demonstração de Fluxo de Caixa (DFC)</h3>
                    <span class="close" onclick="closeCashFlowModal()" style="font-size: 1.5rem; cursor: pointer; color: #718096; border: none; background: none;">&times;</span>
                </div>
                <div class="modal-body" style="padding: 1.5rem;">
                    <div id="cashFlowPreviewContent">
                        <div class="cash-flow-summary" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📋 Resumo do Período</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Recebimentos</div>
                                    <div id="cashFlowPreviewReceipts" style="font-size: 1.2rem; font-weight: bold; color: #48bb78;">$0</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Pagamentos</div>
                                    <div id="cashFlowPreviewPayments" style="font-size: 1.2rem; font-weight: bold; color: #f56565;">$0</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Fluxo Líquido</div>
                                    <div id="cashFlowPreviewNetFlow" style="font-size: 1.2rem; font-weight: bold;">$0</div>
                                </div>
                            </div>
                        </div>

                        <div class="cash-flow-details" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">💸 Fluxos de Caixa por Atividade</h4>
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;">
                                <table style="width: 100%; border-collapse: collapse;">
                                    <thead>
                                        <tr style="border-bottom: 2px solid #e2e8f0;">
                                            <th style="text-align: left; padding: 0.75rem 0; color: #4a5568;">Item</th>
                                            <th style="text-align: right; padding: 0.75rem 0; color: #4a5568;">Valor</th>
                                        </tr>
                                    </thead>
                                    <tbody id="cashFlowDetailsList">
                                        <!-- Items will be populated by JavaScript -->
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div class="cash-flow-period-info" style="background: #edf2f7; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                                <div><strong>Período:</strong> <span id="cashFlowPeriodInfo">-</span></div>
                                <div><strong>Empresa:</strong> <span id="cashFlowCompanyInfo">-</span></div>
                                <div><strong>Gerado em:</strong> <span id="cashFlowGeneratedAt">-</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer" style="display: flex; gap: 1rem; justify-content: flex-end; padding: 1.5rem; border-top: 1px solid #e2e8f0;">
                    <button onclick="closeCashFlowModal()" style="background-color: #e2e8f0; color: #4a5568; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">❌ Fechar</button>
                    <button onclick="downloadCashFlowPDF()" style="background-color: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">📄 Baixar PDF</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = document.getElementById('cashFlowPreviewModal');
    console.log('Cash Flow modal created dynamically:', modal);
    return modal;
}

/**
 * Close Cash Flow preview modal
 */
function closeCashFlowModal() {
    const modal = document.getElementById('cashFlowPreviewModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Download Cash Flow PDF (called from modal)
 */
function downloadCashFlowPDF() {
    try {
        // Show loading
        showLoading(true);

        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Build URL
        const url = `/api/reports/cash-flow-pdf?${params.toString()}`;

        // Create a temporary link to download the PDF
        const link = document.createElement('a');
        link.href = url;
        link.download = ''; // Let the server set the filename
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Close modal
        closeCashFlowModal();

        // Show success notification
        showReportGenerationStatus('💰 Demonstração de Fluxo de Caixa PDF gerado com sucesso!', true);

        // Hide loading after a short delay
        setTimeout(() => {
            showLoading(false);
        }, 1000);

    } catch (error) {
        console.error('Error downloading Cash Flow PDF:', error);
        showError('Failed to download Cash Flow PDF. Please try again.');
        showLoading(false);
    }
}

/**
 * DMPL Modal Functions
 */

/**
 * Populate DMPL modal with data
 */
function populateDMPLModal(dmplData, companyName) {
    console.log('populateDMPLModal called with:', dmplData, dmplData);

    // Check if modal exists first
    const modal = document.getElementById('dmplPreviewModal');
    if (!modal) {
        console.error('dmplPreviewModal not found in DOM');
        return;
    }

    // Extract metrics from API response
    let beginningEquity, netIncome, endingEquity;

    if (dmplData.summary_metrics) {
        const summaryMetrics = dmplData.summary_metrics;
        beginningEquity = summaryMetrics.beginning_equity || 0;
        netIncome = summaryMetrics.net_income || 0;
        endingEquity = summaryMetrics.ending_equity || 0;
    } else if (dmplData.equity_movements) {
        // Fallback to equity movements structure
        const equity = dmplData.equity_movements;
        beginningEquity = equity.beginning_equity || 0;
        netIncome = equity.net_income || 0;
        endingEquity = equity.ending_equity || 0;
    } else {
        // Default values
        beginningEquity = 0;
        netIncome = 0;
        endingEquity = 0;
    }

    console.log('DMPL metrics:', {beginningEquity, netIncome, endingEquity});

    // Safe element updates with null checks
    const safeUpdateElement = (id, value, styleUpdates = null) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            if (styleUpdates) {
                Object.assign(element.style, styleUpdates);
            }
            console.log(`Successfully updated element '${id}' with value: ${value}`);
        } else {
            console.warn(`Element with ID '${id}' not found in DOM`);
        }
    };

    safeUpdateElement('dmplPreviewBeginningEquity', formatCurrency(beginningEquity));
    safeUpdateElement('dmplPreviewNetIncome', formatCurrency(netIncome), {
        color: netIncome >= 0 ? '#48bb78' : '#f56565'
    });
    safeUpdateElement('dmplPreviewEndingEquity', formatCurrency(endingEquity), {
        color: endingEquity >= 0 ? '#48bb78' : '#f56565'
    });

    // Update period information
    const periodInfo = dmplData.period || {};
    const periodName = periodInfo.period_name || 'Período completo';
    safeUpdateElement('dmplPeriodInfo', periodName);

    // Update company information
    safeUpdateElement('dmplCompanyInfo', companyName);
    safeUpdateElement('dmplGeneratedAt', new Date().toLocaleDateString('pt-BR'));

    // Populate detailed table with DMPL structure
    populateDMPLTable(dmplData);
}

/**
 * Populate DMPL detailed table
 */
function populateDMPLTable(dmplData) {
    const tableBody = document.getElementById('dmplDetailsList');
    if (!tableBody) {
        console.error('dmplDetailsList element not found');
        return;
    }
    tableBody.innerHTML = '';

    // Extract values for DMPL calculation
    const beginningEquity = dmplData.summary_metrics?.beginning_equity || dmplData.equity_movements?.beginning_equity || 0;
    const netIncome = dmplData.summary_metrics?.net_income || dmplData.equity_movements?.net_income || 0;
    const endingEquity = dmplData.summary_metrics?.ending_equity || dmplData.equity_movements?.ending_equity || 0;

    // Build DMPL structure dynamically from API data
    const dmplStructure = [];

    // Beginning equity
    dmplStructure.push({
        name: 'PATRIMÔNIO LÍQUIDO - INÍCIO DO PERÍODO',
        amount: beginningEquity,
        isMain: true,
        type: 'beginning'
    });

    // Spacer
    dmplStructure.push({
        name: '',
        amount: null,
        isHeader: false,
        type: 'spacer'
    });

    // Equity movements
    dmplStructure.push({
        name: 'MUTAÇÕES DO PERÍODO:',
        amount: null,
        isHeader: true,
        type: 'header'
    });

    // Add equity movement categories from API data
    if (dmplData.equity_movements?.categories && dmplData.equity_movements.categories.length > 0) {
        dmplData.equity_movements.categories.forEach(cat => {
            dmplStructure.push({
                name: '    ' + cat.category,
                amount: cat.amount,
                isMain: false,
                type: cat.amount > 0 ? 'income' : 'distribution',
                count: cat.count
            });
        });
    } else {
        // Fallback to simple structure
        if (netIncome !== 0) {
            dmplStructure.push({
                name: '    Lucro/Prejuízo do Exercício',
                amount: netIncome,
                isMain: false,
                type: 'income'
            });
        }

        const capitalContributions = dmplData.equity_movements?.capital_contributions || 0;
        if (capitalContributions !== 0) {
            dmplStructure.push({
                name: '    Aportes de Capital',
                amount: capitalContributions,
                isMain: false,
                type: 'capital'
            });
        }

        const distributions = dmplData.equity_movements?.capital_distributions || dmplData.equity_movements?.dividends_paid || 0;
        if (distributions !== 0) {
            dmplStructure.push({
                name: '    Distribuições de Resultado',
                amount: distributions,
                isMain: false,
                type: 'distribution'
            });
        }
    }

    // Calculate total changes
    const totalChanges = endingEquity - beginningEquity;

    // Spacer
    dmplStructure.push({
        name: '',
        amount: null,
        isHeader: false,
        type: 'spacer'
    });

    dmplStructure.push({
        name: 'TOTAL DAS MUTAÇÕES',
        amount: totalChanges,
        isMain: true,
        type: 'total_changes'
    });

    // Spacer
    dmplStructure.push({
        name: '',
        amount: null,
        isHeader: false,
        type: 'spacer'
    });

    // Ending equity
    dmplStructure.push({
        name: 'PATRIMÔNIO LÍQUIDO - FINAL DO PERÍODO',
        amount: endingEquity,
        isMain: true,
        type: 'ending'
    });

    dmplStructure.forEach(item => {
        if (item.type === 'spacer' && !item.name) {
            // Add empty row for spacing
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="2" style="padding: 0.25rem;"></td>`;
            tableBody.appendChild(row);
            return;
        }

        const row = document.createElement('tr');

        if (item.isHeader) {
            row.innerHTML = `
                <td colspan="2" style="padding: 0.75rem 0; font-weight: bold; font-size: 1.1rem; color: #2d3748; background: #f7fafc; border-bottom: 2px solid #e2e8f0;">
                    ${item.name}
                </td>
            `;
        } else {
            row.innerHTML = `
                <td style="padding: 0.5rem 0; padding-left: ${item.isMain ? '0px' : '20px'}; font-weight: ${item.isMain ? 'bold' : 'normal'}; border-bottom: 1px solid #f1f5f9;">
                    ${item.name}
                </td>
                <td style="text-align: right; padding: 0.5rem 0; font-weight: ${item.isMain ? 'bold' : 'normal'}; color: ${getDMPLAmountColor(item.amount, item.type)}; border-bottom: 1px solid #f1f5f9;">
                    ${formatCurrency(item.amount)}
                </td>
            `;
        }

        // Add special styling for main categories
        if (item.isMain) {
            row.style.backgroundColor = '#f8f9fa';
        }

        // Special styling for ending equity
        if (item.type === 'ending') {
            row.style.backgroundColor = '#e8f5e8';
            row.style.fontWeight = 'bold';
        }

        tableBody.appendChild(row);
    });
}

/**
 * Get color for DMPL amounts based on type and value
 */
function getDMPLAmountColor(amount, type) {
    if (amount === null || amount === 0) return '#6c757d';

    switch (type) {
        case 'beginning':
        case 'ending':
            return amount >= 0 ? '#48bb78' : '#f56565';
        case 'income':
            return amount >= 0 ? '#48bb78' : '#f56565';
        case 'capital':
            return amount > 0 ? '#4299e1' : '#6c757d';
        case 'distribution':
            return amount > 0 ? '#f56565' : '#6c757d';
        case 'total_changes':
            return amount >= 0 ? '#48bb78' : '#f56565';
        default:
            return amount >= 0 ? '#48bb78' : '#f56565';
    }
}

/**
 * Open DMPL preview modal
 */
function openDMPLModal() {
    let modal = document.getElementById('dmplPreviewModal');

    // If modal doesn't exist, create it dynamically
    if (!modal) {
        console.log('Modal not found, creating dynamically...');
        modal = createDMPLModal();
    }

    if (modal) {
        modal.style.display = 'flex';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        modal.style.zIndex = '1000';
        modal.style.justifyContent = 'center';
        modal.style.alignItems = 'center';

        // Focus trap for accessibility
        modal.focus();

        console.log('DMPL modal opened successfully');
    } else {
        console.error('Failed to create or find DMPL modal');
    }
}

/**
 * Create DMPL modal dynamically
 */
function createDMPLModal() {
    const modalHTML = `
        <div id="dmplPreviewModal" class="modal" style="display: none;">
            <div class="modal-content" style="max-width: 800px; width: 90%; background: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); max-height: 90vh; overflow-y: auto;">
                <div class="modal-header" style="padding: 1.5rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #2d3748;">📈 Demonstração das Mutações do Patrimônio Líquido (DMPL)</h3>
                    <span class="close" onclick="closeDMPLModal()" style="font-size: 1.5rem; cursor: pointer; color: #718096; border: none; background: none;">&times;</span>
                </div>
                <div class="modal-body" style="padding: 1.5rem;">
                    <div id="dmplPreviewContent">
                        <div class="dmpl-summary" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📋 Resumo do Período</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">PL Inicial</div>
                                    <div id="dmplPreviewBeginningEquity" style="font-size: 1.2rem; font-weight: bold; color: #4299e1;">$0</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Resultado do Período</div>
                                    <div id="dmplPreviewNetIncome" style="font-size: 1.2rem; font-weight: bold;">$0</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">PL Final</div>
                                    <div id="dmplPreviewEndingEquity" style="font-size: 1.2rem; font-weight: bold;">$0</div>
                                </div>
                            </div>
                        </div>

                        <div class="dmpl-details" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📊 Movimentação do Patrimônio Líquido</h4>
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;">
                                <table style="width: 100%; border-collapse: collapse;">
                                    <thead>
                                        <tr style="border-bottom: 2px solid #e2e8f0;">
                                            <th style="text-align: left; padding: 0.75rem 0; color: #4a5568;">Item</th>
                                            <th style="text-align: right; padding: 0.75rem 0; color: #4a5568;">Valor</th>
                                        </tr>
                                    </thead>
                                    <tbody id="dmplDetailsList">
                                        <!-- Items will be populated by JavaScript -->
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div class="dmpl-period-info" style="background: #edf2f7; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                                <div><strong>Período:</strong> <span id="dmplPeriodInfo">-</span></div>
                                <div><strong>Empresa:</strong> <span id="dmplCompanyInfo">-</span></div>
                                <div><strong>Gerado em:</strong> <span id="dmplGeneratedAt">-</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer" style="display: flex; gap: 1rem; justify-content: flex-end; padding: 1.5rem; border-top: 1px solid #e2e8f0;">
                    <button onclick="closeDMPLModal()" style="background-color: #e2e8f0; color: #4a5568; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">❌ Fechar</button>
                    <button onclick="downloadDMPLPDF()" style="background-color: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">📄 Baixar PDF</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = document.getElementById('dmplPreviewModal');
    console.log('DMPL modal created dynamically:', modal);
    return modal;
}

/**
 * Close DMPL preview modal
 */
function closeDMPLModal() {
    const modal = document.getElementById('dmplPreviewModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Download DMPL PDF (called from modal)
 */
function downloadDMPLPDF() {
    try {
        // Show loading
        showLoading(true);

        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Build URL
        const url = `/api/reports/dmpl-pdf?${params.toString()}`;

        // Create a temporary link to download the PDF
        const link = document.createElement('a');
        link.href = url;
        link.download = ''; // Let the server set the filename
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Close modal
        closeDMPLModal();

        // Show success notification
        showReportGenerationStatus('📈 DMPL PDF gerado com sucesso!', true);

        // Hide loading after a short delay
        setTimeout(() => {
            showLoading(false);
        }, 1000);

    } catch (error) {
        console.error('Error downloading DMPL PDF:', error);
        showError('Failed to download DMPL PDF. Please try again.');
        showLoading(false);
    }
}

/**
 * Create Sankey Financial Flow Diagram
 */
function createSankeyDiagram() {
    const container = document.getElementById('sankeyDiagram');
    if (!container) {
        console.warn('Sankey diagram container not found');
        return;
    }

    // Clear any existing content
    container.innerHTML = '';

    // Check if Plotly is available, if not wait and retry
    if (typeof Plotly === 'undefined') {
        console.warn('Plotly library not loaded yet, waiting...');
        container.innerHTML = '<div style="text-align: center; color: #666; padding: 2rem;">Loading Sankey diagram...</div>';

        // Retry after a short delay to allow Plotly to load
        setTimeout(() => {
            if (typeof Plotly === 'undefined') {
                console.error('Plotly library failed to load');
                container.innerHTML = '<div style="text-align: center; color: #666; padding: 2rem;">Sankey diagram requires Plotly.js library. Please refresh the page.</div>';
            } else {
                createSankeyDiagram(); // Retry now that Plotly is loaded
            }
        }, 500);
        return;
    }

    // Get financial data for the diagram
    const plData = dashboardData.monthlyPL?.summary?.period_totals;
    if (!plData) {
        container.innerHTML = '<div style="text-align: center; color: #666; padding: 2rem;">No financial data available for Sankey diagram</div>';
        return;
    }

    // Prepare data for Sankey diagram
    const totalRevenue = Math.max(plData.total_revenue || 0, 0);
    const totalExpenses = Math.max(plData.total_expenses || 0, 0);
    const netProfit = (plData.total_profit || 0);

    // Get category data from API
    const revenueCategories = dashboardData.monthlyPL?.summary?.revenue_categories || [];
    const expenseCategories = dashboardData.monthlyPL?.summary?.expense_categories || [];

    // If no significant data, show placeholder
    if (totalRevenue < 1) {
        container.innerHTML = '<div style="text-align: center; color: #666; padding: 2rem;">Insufficient revenue data to generate meaningful flow visualization</div>';
        return;
    }

    // Build Plotly Sankey structure
    const nodeLabels = [];
    const nodeValues = []; // Store actual values for each node
    const nodeColors = [];
    const nodeMap = {};
    let nodeIndex = 0;

    // Level 0: Revenue categories (only show categories > 2% of revenue)
    const significantRevenueCategories = revenueCategories.filter(cat => {
        return cat.amount > totalRevenue * 0.02 &&
               cat.category &&
               cat.category.trim().length > 0;
    });

    // Add significant revenue category nodes (green)
    significantRevenueCategories.forEach(cat => {
        nodeLabels.push(`${cat.category}<br>${formatCurrency(cat.amount)}`);
        nodeValues.push(cat.amount);
        nodeColors.push('#86efac'); // Light green
        nodeMap[`revenue_${cat.category}`] = nodeIndex++;
    });

    // Add "Other Revenue" node if needed (green)
    const otherRevenueAmount = totalRevenue - significantRevenueCategories.reduce((sum, cat) => sum + cat.amount, 0);
    if (otherRevenueAmount > totalRevenue * 0.01) {
        nodeLabels.push(`Other Revenue<br>${formatCurrency(otherRevenueAmount)}`);
        nodeValues.push(otherRevenueAmount);
        nodeColors.push('#86efac'); // Light green
        nodeMap['other_revenue'] = nodeIndex++;
    }

    // Level 1: Total Revenue aggregation node (gray)
    nodeLabels.push(`Total Revenue<br>${formatCurrency(totalRevenue)}`);
    nodeValues.push(totalRevenue);
    nodeColors.push('#d1d5db'); // Gray
    nodeMap['total_revenue'] = nodeIndex++;

    // Level 2: Top expense subcategories (only show > 1% of expenses, pink/red)
    const expenseNodesList = [];
    expenseCategories.slice(0, 3).forEach(cat => {
        const topSubcategories = cat.subcategories
            .filter(subcat => {
                return subcat.amount > totalExpenses * 0.01 &&
                       subcat.name &&
                       subcat.name.length < 100;
            })
            .slice(0, 5);

        topSubcategories.forEach(subcat => {
            const nodeName = `${cat.category}: ${subcat.name}<br>${formatCurrency(subcat.amount)}`;
            nodeLabels.push(nodeName);
            nodeValues.push(subcat.amount);
            nodeColors.push('#fca5a5'); // Light pink/red
            expenseNodesList.push({
                index: nodeIndex,
                category: cat.category,
                subcategory: subcat.name,
                amount: subcat.amount
            });
            nodeMap[`expense_${cat.category}_${subcat.name}`] = nodeIndex++;
        });

        // Add "Other" node for remaining subcategories
        const otherSubcatsAmount = cat.total - topSubcategories.reduce((sum, sub) => sum + sub.amount, 0);
        if (otherSubcatsAmount > totalExpenses * 0.01) {
            const nodeName = `${cat.category}: Other<br>${formatCurrency(otherSubcatsAmount)}`;
            nodeLabels.push(nodeName);
            nodeValues.push(otherSubcatsAmount);
            nodeColors.push('#fca5a5'); // Light pink/red
            expenseNodesList.push({
                index: nodeIndex,
                category: cat.category,
                subcategory: 'Other',
                amount: otherSubcatsAmount
            });
            nodeMap[`expense_${cat.category}_Other`] = nodeIndex++;
        }
    });

    // Level 3: Net Profit node (only if positive, dark green)
    if (netProfit > 0) {
        nodeLabels.push(`Net Profit<br>${formatCurrency(netProfit)}`);
        nodeValues.push(netProfit);
        nodeColors.push('#22c55e'); // Dark green
        nodeMap['net_profit'] = nodeIndex++;
    }

    // Build links array
    const linkSources = [];
    const linkTargets = [];
    const linkValues = [];
    const linkColors = [];

    // Links from revenue categories to Total Revenue
    significantRevenueCategories.forEach(cat => {
        linkSources.push(nodeMap[`revenue_${cat.category}`]);
        linkTargets.push(nodeMap['total_revenue']);
        linkValues.push(cat.amount);
        linkColors.push('rgba(134, 239, 172, 0.4)'); // Light green with transparency
    });

    // Link from Other Revenue to Total Revenue
    if (otherRevenueAmount > totalRevenue * 0.01) {
        linkSources.push(nodeMap['other_revenue']);
        linkTargets.push(nodeMap['total_revenue']);
        linkValues.push(otherRevenueAmount);
        linkColors.push('rgba(134, 239, 172, 0.4)'); // Light green with transparency
    }

    // Links from Total Revenue to expense categories
    expenseNodesList.forEach(expense => {
        linkSources.push(nodeMap['total_revenue']);
        linkTargets.push(expense.index);
        linkValues.push(expense.amount);
        linkColors.push('rgba(252, 165, 165, 0.4)'); // Light pink with transparency
    });

    // Link from Total Revenue to Net Profit (if positive)
    if (netProfit > 0) {
        linkSources.push(nodeMap['total_revenue']);
        linkTargets.push(nodeMap['net_profit']);
        linkValues.push(netProfit);
        linkColors.push('rgba(34, 197, 94, 0.4)'); // Dark green with transparency
    }

    // Create Plotly Sankey trace
    const data = [{
        type: "sankey",
        orientation: "h",
        node: {
            pad: 15,
            thickness: 20,
            line: {
                color: "white",
                width: 2
            },
            label: nodeLabels,
            color: nodeColors,
            customdata: nodeValues.map(val => formatCurrency(val)),
            hovertemplate: '<b>%{label}</b><extra></extra>'
        },
        link: {
            source: linkSources,
            target: linkTargets,
            value: linkValues,
            color: linkColors,
            customdata: linkSources.map((src, i) => {
                return {
                    from: nodeLabels[src],
                    to: nodeLabels[linkTargets[i]],
                    value: formatCurrency(linkValues[i])
                };
            }),
            hovertemplate: '<b>%{customdata.from}</b> → <b>%{customdata.to}</b><br>Flow: %{customdata.value}<extra></extra>'
        }
    }];

    // Layout configuration
    const layout = {
        title: {
            text: 'Financial Flow',
            font: {
                family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                size: 18,
                color: '#1f2937'
            }
        },
        font: {
            family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            size: 12,
            color: '#4a5568'
        },
        plot_bgcolor: 'rgba(0,0,0,0)',
        paper_bgcolor: 'rgba(0,0,0,0)',
        margin: {
            l: 10,
            r: 10,
            t: 50,
            b: 10
        },
        height: 500
    };

    // Configuration
    const config = {
        displayModeBar: false,
        responsive: true
    };

    // Render the Sankey diagram
    Plotly.newPlot(container, data, layout, config);

    console.log('Plotly Sankey diagram created successfully with data:', {
        totalRevenue,
        totalExpenses,
        netProfit,
        revenueCategories: revenueCategories.length,
        expenseCategories: expenseCategories.length,
        significantRevenueCategories: significantRevenueCategories.length,
        nodes: nodeLabels.length,
        links: linkSources.length,
        nodeLabels,
        linkFlows: linkSources.map((src, i) => ({
            from: nodeLabels[src],
            to: nodeLabels[linkTargets[i]],
            value: linkValues[i]
        }))
    });
}