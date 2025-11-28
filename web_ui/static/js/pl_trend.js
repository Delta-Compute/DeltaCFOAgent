/**
 * P&L Trend Chart - JavaScript
 * Bar chart with Revenue, COGS, SG&A, Net Income and hover features
 */

// Global state
let plTrendChart = null;
let plTrendData = null;
let aiSummaryCache = new Map();
let hoverTimeout = null;

// Format currency
function formatCurrency(value) {
    if (value === null || value === undefined || isNaN(value)) return '$0';
    const absValue = Math.abs(value);
    if (absValue >= 1000000) {
        return '$' + (value / 1000000).toFixed(1) + 'M';
    } else if (absValue >= 1000) {
        return '$' + (value / 1000).toFixed(1) + 'K';
    }
    return '$' + value.toFixed(0);
}

// Format currency full
function formatCurrencyFull(value) {
    if (value === null || value === undefined || isNaN(value)) return '$0.00';
    return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('P&L Trend page loaded');
    loadPLTrendData();

    // Event listeners
    document.getElementById('refreshChart').addEventListener('click', loadPLTrendData);
    document.getElementById('monthsBackSelector').addEventListener('change', loadPLTrendData);
    document.getElementById('internalFilter').addEventListener('change', loadPLTrendData);
});

/**
 * Load P&L Trend data from API
 */
async function loadPLTrendData() {
    const monthsBack = document.getElementById('monthsBackSelector').value;
    const isInternal = document.getElementById('internalFilter').value;

    // Build query string
    let queryParams = new URLSearchParams();
    queryParams.set('months_back', monthsBack);
    if (isInternal) {
        queryParams.set('is_internal', isInternal);
    }

    // Show loading state
    document.getElementById('chartLoading').style.display = 'block';

    try {
        const response = await fetch(`/api/reports/pl-trend?${queryParams.toString()}`);
        const result = await response.json();

        if (result.success) {
            plTrendData = result.data;
            updateSummaryStats(plTrendData);
            createPLTrendChart(plTrendData);
            updateBreakdowns(plTrendData);
        } else {
            console.error('Failed to load P&L trend data:', result.error);
            showError('Failed to load data: ' + result.error);
        }
    } catch (error) {
        console.error('Error loading P&L trend data:', error);
        showError('Error loading data. Please try again.');
    } finally {
        document.getElementById('chartLoading').style.display = 'none';
    }
}

/**
 * Update summary statistics
 */
function updateSummaryStats(data) {
    const totals = data.totals;

    document.getElementById('totalRevenue').textContent = formatCurrency(totals.revenue);
    document.getElementById('totalCogs').textContent = formatCurrency(totals.cogs);
    document.getElementById('totalSga').textContent = formatCurrency(totals.sga);

    const netIncomeEl = document.getElementById('totalNetIncome');
    netIncomeEl.textContent = formatCurrency(totals.net_income);
    netIncomeEl.className = 'stat-number ' + (totals.net_income >= 0 ? 'positive' : 'negative');

    document.getElementById('grossMargin').textContent = totals.gross_margin_percent.toFixed(1) + '%';
}

/**
 * Create the P&L Trend bar chart with gross margin line
 */
function createPLTrendChart(data) {
    const ctx = document.getElementById('plTrendChart').getContext('2d');

    // Destroy existing chart
    if (plTrendChart) {
        plTrendChart.destroy();
    }

    const monthlyData = data.monthly_pl;
    const labels = monthlyData.map(m => m.month);
    const revenue = monthlyData.map(m => m.revenue);
    const cogs = monthlyData.map(m => m.cogs);
    const sga = monthlyData.map(m => m.sga);
    const netIncome = monthlyData.map(m => m.net_income);
    const grossMarginPct = monthlyData.map(m => m.gross_margin_percent);

    plTrendChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Revenue',
                    data: revenue,
                    backgroundColor: 'rgba(30, 41, 59, 0.85)',
                    borderColor: 'rgb(30, 41, 59)',
                    borderWidth: 1,
                    order: 2,
                    categoryPercentage: 0.8,
                    barPercentage: 0.9
                },
                {
                    label: 'COGS',
                    data: cogs,
                    backgroundColor: 'rgba(249, 115, 22, 0.85)',
                    borderColor: 'rgb(249, 115, 22)',
                    borderWidth: 1,
                    order: 2,
                    categoryPercentage: 0.8,
                    barPercentage: 0.9
                },
                {
                    label: 'SG&A',
                    data: sga,
                    backgroundColor: 'rgba(59, 130, 246, 0.85)',
                    borderColor: 'rgb(59, 130, 246)',
                    borderWidth: 1,
                    order: 2,
                    categoryPercentage: 0.8,
                    barPercentage: 0.9
                },
                {
                    label: 'Net Income',
                    data: netIncome,
                    backgroundColor: netIncome.map(v => v >= 0 ? 'rgba(34, 197, 94, 0.85)' : 'rgba(239, 68, 68, 0.85)'),
                    borderColor: netIncome.map(v => v >= 0 ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)'),
                    borderWidth: 1,
                    order: 2,
                    categoryPercentage: 0.8,
                    barPercentage: 0.9
                },
                {
                    label: 'Gross Margin %',
                    data: grossMarginPct,
                    type: 'line',
                    borderColor: 'rgb(168, 85, 247)',
                    backgroundColor: 'rgba(168, 85, 247, 0.1)',
                    borderWidth: 3,
                    pointRadius: 5,
                    pointBackgroundColor: 'rgb(168, 85, 247)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    fill: false,
                    yAxisID: 'y1',
                    order: 1,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        label: function(context) {
                            const datasetLabel = context.dataset.label;
                            const value = context.parsed.y;

                            if (datasetLabel === 'Gross Margin %') {
                                return datasetLabel + ': ' + value.toFixed(1) + '%';
                            }
                            return datasetLabel + ': ' + formatCurrencyFull(value);
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Amount ($)'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Gross Margin (%)'
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            },
            onHover: function(event, elements) {
                handleChartHover(event, elements);
            }
        }
    });

    // Add click handler for drill-down
    document.getElementById('plTrendChart').onclick = function(evt) {
        handleChartClick(evt);
    };
}

/**
 * Handle hover on chart elements
 */
function handleChartHover(event, elements) {
    clearTimeout(hoverTimeout);

    if (!elements || elements.length === 0) {
        hideTooltip();
        return;
    }

    const element = elements[0];
    const datasetIndex = element.datasetIndex;
    const dataIndex = element.index;
    const datasetLabel = plTrendChart.data.datasets[datasetIndex].label;

    // Debounce hover events
    hoverTimeout = setTimeout(() => {
        if (datasetLabel === 'COGS') {
            showBreakdownTooltip('COGS', dataIndex, event);
        } else if (datasetLabel === 'SG&A') {
            showBreakdownTooltip('SG&A', dataIndex, event);
        } else if (datasetLabel === 'Net Income') {
            showNetIncomeAISummary(dataIndex, event);
        }
    }, 300);
}

/**
 * Handle click on chart elements
 */
function handleChartClick(evt) {
    const elements = plTrendChart.getElementsAtEventForMode(evt, 'nearest', { intersect: true }, false);

    if (elements.length === 0) return;

    const element = elements[0];
    const datasetIndex = element.datasetIndex;
    const datasetLabel = plTrendChart.data.datasets[datasetIndex].label;

    // Could add drill-down navigation here in the future
    console.log('Clicked on:', datasetLabel);
}

/**
 * Show breakdown tooltip for COGS or SG&A
 */
function showBreakdownTooltip(type, monthIndex, event) {
    const monthData = plTrendData.monthly_pl[monthIndex];
    const breakdowns = plTrendData.breakdowns;
    const breakdown = type === 'COGS' ? breakdowns.cogs : breakdowns.sga;
    const totalAmount = type === 'COGS' ? monthData.cogs : monthData.sga;

    let html = `
        <div style="min-width: 280px;">
            <div style="font-weight: 600; font-size: 1.1rem; margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0;">
                ${type} Breakdown - ${monthData.month}
            </div>
            <div style="font-size: 0.9rem; color: #64748b; margin-bottom: 0.75rem;">
                Total: ${formatCurrencyFull(totalAmount)}
            </div>
    `;

    if (breakdown && breakdown.length > 0) {
        html += '<div style="max-height: 300px; overflow-y: auto;">';
        breakdown.forEach((item, idx) => {
            const pct = totalAmount > 0 ? (item.amount / totalAmount * 100).toFixed(1) : 0;
            const bgColor = idx % 2 === 0 ? '#f8fafc' : 'white';
            html += `
                <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: ${bgColor}; border-radius: 4px; margin-bottom: 0.25rem;">
                    <span style="color: #334155;">${item.category}</span>
                    <span style="font-weight: 500; color: #1e293b;">${formatCurrencyFull(item.amount)} <span style="color: #94a3b8;">(${pct}%)</span></span>
                </div>
            `;
        });
        html += '</div>';
    } else {
        html += '<div style="color: #94a3b8; font-style: italic;">No breakdown data available</div>';
    }

    html += '</div>';

    showTooltipAtPosition(html, event);
}

/**
 * Show AI-generated Net Income summary
 */
async function showNetIncomeAISummary(monthIndex, event) {
    const monthData = plTrendData.monthly_pl[monthIndex];
    const cacheKey = `${monthData.month}_${monthData.net_income}`;

    // Check cache first
    if (aiSummaryCache.has(cacheKey)) {
        const cached = aiSummaryCache.get(cacheKey);
        showAISummaryTooltip(monthData, cached.summary, event);
        return;
    }

    // Show loading state
    showTooltipAtPosition(`
        <div style="min-width: 300px;">
            <div style="font-weight: 600; font-size: 1.1rem; margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0;">
                Net Income Analysis - ${monthData.month}
            </div>
            <div style="text-align: center; padding: 1.5rem; color: #64748b;">
                <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">Generating AI Summary...</div>
                <div style="font-size: 0.85rem;">Analyzing financial performance</div>
            </div>
        </div>
    `, event);

    try {
        const response = await fetch('/api/reports/pl-trend/ai-summary', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                month: monthData.month,
                revenue: monthData.revenue,
                cogs: monthData.cogs,
                sga: monthData.sga,
                net_income: monthData.net_income,
                gross_margin_percent: monthData.gross_margin_percent,
                trend_data: plTrendData.monthly_pl
            })
        });

        const result = await response.json();

        if (result.success) {
            // Cache the result
            aiSummaryCache.set(cacheKey, { summary: result.summary, timestamp: Date.now() });
            showAISummaryTooltip(monthData, result.summary, event);
        } else {
            showAISummaryTooltip(monthData, 'Unable to generate summary: ' + result.error, event);
        }
    } catch (error) {
        console.error('Error fetching AI summary:', error);
        showAISummaryTooltip(monthData, 'Error generating summary. Please try again.', event);
    }
}

/**
 * Show AI summary in tooltip
 */
function showAISummaryTooltip(monthData, summary, event) {
    const netIncomeColor = monthData.net_income >= 0 ? '#22c55e' : '#ef4444';
    const netIncomeLabel = monthData.net_income >= 0 ? 'Profit' : 'Loss';

    const html = `
        <div style="min-width: 350px; max-width: 450px;">
            <div style="font-weight: 600; font-size: 1.1rem; margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                <span>Net Income Analysis - ${monthData.month}</span>
                <span style="color: ${netIncomeColor}; font-size: 1rem;">${formatCurrencyFull(monthData.net_income)}</span>
            </div>

            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; margin-bottom: 1rem; padding: 0.75rem; background: #f8fafc; border-radius: 8px;">
                <div>
                    <div style="font-size: 0.75rem; color: #64748b;">Revenue</div>
                    <div style="font-weight: 600; color: #1e293b;">${formatCurrencyFull(monthData.revenue)}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #64748b;">Gross Margin</div>
                    <div style="font-weight: 600; color: #1e293b;">${monthData.gross_margin_percent.toFixed(1)}%</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #64748b;">COGS</div>
                    <div style="font-weight: 600; color: #f97316;">${formatCurrencyFull(monthData.cogs)}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #64748b;">SG&A</div>
                    <div style="font-weight: 600; color: #3b82f6;">${formatCurrencyFull(monthData.sga)}</div>
                </div>
            </div>

            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem; border-radius: 8px;">
                <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; opacity: 0.9;">AI Analysis</div>
                <div style="font-size: 0.95rem; line-height: 1.6;">${summary}</div>
            </div>
        </div>
    `;

    showTooltipAtPosition(html, event);
}

/**
 * Show tooltip at mouse position
 */
function showTooltipAtPosition(html, event) {
    const tooltip = document.getElementById('plTrendTooltip');
    tooltip.innerHTML = html;
    tooltip.style.display = 'block';

    // Position near mouse but ensure it stays in viewport
    const mouseX = event.native ? event.native.clientX : event.clientX || window.innerWidth / 2;
    const mouseY = event.native ? event.native.clientY : event.clientY || window.innerHeight / 2;

    const tooltipRect = tooltip.getBoundingClientRect();
    const padding = 20;

    let left = mouseX + padding;
    let top = mouseY - padding;

    // Adjust if would go off right edge
    if (left + tooltipRect.width > window.innerWidth - padding) {
        left = mouseX - tooltipRect.width - padding;
    }

    // Adjust if would go off bottom edge
    if (top + tooltipRect.height > window.innerHeight - padding) {
        top = window.innerHeight - tooltipRect.height - padding;
    }

    // Ensure not off top edge
    if (top < padding) {
        top = padding;
    }

    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';

    // Add close on mouse leave (with delay)
    let leaveTimeout = null;
    tooltip.onmouseenter = () => clearTimeout(leaveTimeout);
    tooltip.onmouseleave = () => {
        leaveTimeout = setTimeout(hideTooltip, 300);
    };
}

/**
 * Hide the tooltip
 */
function hideTooltip() {
    const tooltip = document.getElementById('plTrendTooltip');
    if (tooltip) {
        tooltip.style.display = 'none';
    }
}

/**
 * Update breakdown sections
 */
function updateBreakdowns(data) {
    const breakdowns = data.breakdowns;

    // COGS Breakdown
    const cogsContainer = document.getElementById('cogsBreakdown');
    if (breakdowns.cogs && breakdowns.cogs.length > 0) {
        let cogsHtml = '<table style="width: 100%; border-collapse: collapse;">';
        cogsHtml += '<thead><tr style="border-bottom: 2px solid #e2e8f0;"><th style="text-align: left; padding: 0.5rem;">Category</th><th style="text-align: right; padding: 0.5rem;">Amount</th><th style="text-align: right; padding: 0.5rem;">Count</th></tr></thead><tbody>';

        breakdowns.cogs.forEach((item, idx) => {
            const bgColor = idx % 2 === 0 ? '#f8fafc' : 'white';
            cogsHtml += `<tr style="background: ${bgColor};"><td style="padding: 0.5rem; color: #334155;">${item.category}</td><td style="padding: 0.5rem; text-align: right; font-weight: 500;">${formatCurrencyFull(item.amount)}</td><td style="padding: 0.5rem; text-align: right; color: #64748b;">${item.count}</td></tr>`;
        });

        cogsHtml += '</tbody></table>';
        cogsContainer.innerHTML = cogsHtml;
    } else {
        cogsContainer.innerHTML = '<p style="color: #94a3b8; font-style: italic;">No COGS data available</p>';
    }

    // SG&A Breakdown
    const sgaContainer = document.getElementById('sgaBreakdown');
    if (breakdowns.sga && breakdowns.sga.length > 0) {
        let sgaHtml = '<table style="width: 100%; border-collapse: collapse;">';
        sgaHtml += '<thead><tr style="border-bottom: 2px solid #e2e8f0;"><th style="text-align: left; padding: 0.5rem;">Category</th><th style="text-align: right; padding: 0.5rem;">Amount</th><th style="text-align: right; padding: 0.5rem;">Count</th></tr></thead><tbody>';

        breakdowns.sga.forEach((item, idx) => {
            const bgColor = idx % 2 === 0 ? '#f8fafc' : 'white';
            sgaHtml += `<tr style="background: ${bgColor};"><td style="padding: 0.5rem; color: #334155;">${item.category}</td><td style="padding: 0.5rem; text-align: right; font-weight: 500;">${formatCurrencyFull(item.amount)}</td><td style="padding: 0.5rem; text-align: right; color: #64748b;">${item.count}</td></tr>`;
        });

        sgaHtml += '</tbody></table>';
        sgaContainer.innerHTML = sgaHtml;
    } else {
        sgaContainer.innerHTML = '<p style="color: #94a3b8; font-style: italic;">No SG&A data available</p>';
    }
}

/**
 * Show error message
 */
function showError(message) {
    const chartContainer = document.getElementById('plTrendChart').parentElement;
    chartContainer.innerHTML = `<div style="text-align: center; color: #ef4444; padding: 2rem;"><p style="font-size: 1.2rem;">${message}</p><button onclick="loadPLTrendData()" class="btn-primary" style="margin-top: 1rem;">Retry</button></div>`;
}
