/**
 * CFO Dashboard JavaScript - Simplified Version
 * Aligned with existing system design
 */

// Global variables
let currentFilters = {
    period: 'all_time',
    entity: '',
    startDate: null,
    endDate: null
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
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = formatCurrency(value || 0);
        }
    }

    // Update cash position
    if (cashData) {
        safeUpdate('cashPosition', cashData.total_cash);
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
        endDate: null
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

        // Add company name
        const companyName = document.getElementById('reportCompanyName')?.value || 'Delta Mining';
        params.set('company_name', companyName);

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

        // Add company name
        const companyName = document.getElementById('reportCompanyName')?.value || 'Delta Mining';
        params.set('company_name', companyName);

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