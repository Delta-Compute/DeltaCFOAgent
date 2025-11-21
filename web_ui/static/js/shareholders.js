// Shareholder Equity Management
let shareholders = [];
let contributions = [];
let currentTab = 'shareholders';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    loadStats();
    loadShareholders();
    loadContributions();
    setupSearchHandlers();
    setupFormHandlers();
    setupShareClassListener();
});

// Tab Management
function initializeTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    currentTab = tabName;

    // Update tab buttons
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// Load Statistics
async function loadStats() {
    try {
        const response = await fetch('/api/shareholders/stats');
        const data = await response.json();

        if (data.success) {
            const stats = data.stats;
            document.getElementById('stat-total-shareholders').textContent = stats.total_shareholders || '0';
            document.getElementById('stat-total-equity').textContent = formatCurrency(stats.total_equity_raised || 0);
            document.getElementById('stat-total-shares').textContent = (stats.total_shares_outstanding || 0).toLocaleString();

            // Get contributions count
            const contribResponse = await fetch('/api/equity-contributions');
            const contribData = await contribResponse.json();
            if (contribData.success) {
                document.getElementById('stat-total-contributions').textContent = contribData.count || '0';
            }
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load Shareholders
async function loadShareholders() {
    try {
        const response = await fetch('/api/shareholders?status=all');
        const data = await response.json();

        if (data.success) {
            shareholders = data.shareholders;
            renderShareholders();
        }
    } catch (error) {
        console.error('Error loading shareholders:', error);
        showError('Failed to load shareholders');
    }
}

function renderShareholders() {
    const tbody = document.getElementById('shareholders-tbody');

    if (shareholders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-state"><div class="empty-icon">📊</div><div>No shareholders found. Click "Add Shareholder" to get started.</div></td></tr>';
        return;
    }

    tbody.innerHTML = shareholders.map(s => `
        <tr>
            <td>${s.shareholder_name}</td>
            <td>${s.entity || '-'}</td>
            <td><span class="type-badge type-${s.shareholder_type}">${formatType(s.shareholder_type)}</span></td>
            <td>${s.share_class || '-'}${s.share_class === 'SAFE' && s.safe_terms ? ' *' : ''}</td>
            <td>${(s.total_shares || 0).toLocaleString()}</td>
            <td>${parseFloat(s.ownership_percentage || 0).toFixed(2)}%</td>
            <td>${formatCurrency(s.total_contributed || 0)}</td>
            <td><span class="status-badge status-${s.status}">${s.status}</span></td>
            <td>
                <span class="action-icon" onclick="editShareholder('${s.id}')" title="Edit">✏️</span>
                <span class="action-icon" onclick="deleteShareholder('${s.id}')" title="Delete">🗑️</span>
            </td>
        </tr>
    `).join('');
}

// Load entities for dropdown
async function loadEntities() {
    try {
        const response = await fetch('/api/entities');
        const data = await response.json();

        if (data.entities && data.entities.length > 0) {
            const select = document.getElementById('shareholder-entity');
            select.innerHTML = '<option value="">Select entity</option>' +
                data.entities.map(e => `<option value="${e}">${e}</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading entities:', error);
    }
}

// Setup share class listener for SAFE terms
function setupShareClassListener() {
    const shareClassSelect = document.getElementById('shareholder-share-class');
    const safeTermsSection = document.getElementById('safe-terms-section');

    if (shareClassSelect && safeTermsSection) {
        shareClassSelect.addEventListener('change', function() {
            if (this.value === 'SAFE') {
                safeTermsSection.style.display = 'block';
            } else {
                safeTermsSection.style.display = 'none';
                document.getElementById('shareholder-safe-discount').value = '';
                document.getElementById('shareholder-safe-cap').value = '';
                document.getElementById('shareholder-safe-amount').value = '';
            }
        });
    }
}

// Load Contributions
async function loadContributions() {
    try {
        const response = await fetch('/api/equity-contributions');
        const data = await response.json();

        if (data.success) {
            contributions = data.contributions;
            renderContributions();
        }
    } catch (error) {
        console.error('Error loading contributions:', error);
        showError('Failed to load contributions');
    }
}

function renderContributions() {
    const tbody = document.getElementById('contributions-tbody');

    if (contributions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state"><div class="empty-icon">💰</div><div>No contributions recorded yet.</div></td></tr>';
        return;
    }

    tbody.innerHTML = contributions.map(c => `
        <tr>
            <td>${formatDate(c.contribution_date)}</td>
            <td>${c.shareholder_name}</td>
            <td>${formatType(c.contribution_type)}</td>
            <td>${formatCurrency(c.cash_amount || 0)}</td>
            <td>${formatCurrency(c.non_cash_value || 0)}</td>
            <td>${(c.shares_issued || 0).toLocaleString()}</td>
            <td>${c.price_per_share ? formatCurrency(c.price_per_share) : '-'}</td>
            <td>
                <span class="action-icon" onclick="deleteContribution('${c.id}')" title="Delete">🗑️</span>
            </td>
        </tr>
    `).join('');
}

// Modal Management
function openAddShareholderModal() {
    document.getElementById('shareholder-modal-title').textContent = 'Add Shareholder';
    document.getElementById('shareholder-form').reset();
    document.getElementById('shareholder-id').value = '';
    document.getElementById('safe-terms-section').style.display = 'none';
    loadEntities();
    document.getElementById('shareholder-modal').classList.add('show');
}

function closeShareholderModal() {
    document.getElementById('shareholder-modal').classList.remove('show');
}

async function editShareholder(id) {
    try {
        const response = await fetch(`/api/shareholders/${id}`);
        const data = await response.json();

        if (data.success) {
            const s = data.shareholder;

            // Load entities first
            await loadEntities();

            document.getElementById('shareholder-modal-title').textContent = 'Edit Shareholder';
            document.getElementById('shareholder-id').value = s.id;
            document.getElementById('shareholder-name').value = s.shareholder_name;
            document.getElementById('shareholder-type').value = s.shareholder_type;
            document.getElementById('shareholder-entity').value = s.entity || '';
            document.getElementById('shareholder-share-class').value = s.share_class;
            document.getElementById('shareholder-shares').value = s.total_shares || '';
            document.getElementById('shareholder-ownership').value = s.ownership_percentage || '';
            document.getElementById('shareholder-joining-date').value = s.joining_date || '';
            document.getElementById('shareholder-email').value = s.contact_email || '';
            document.getElementById('shareholder-phone').value = s.contact_phone || '';
            document.getElementById('shareholder-tax-id').value = s.tax_id || '';
            document.getElementById('shareholder-address').value = s.address || '';
            document.getElementById('shareholder-board').value = s.board_member ? 'true' : 'false';
            document.getElementById('shareholder-voting').value = s.voting_rights ? 'true' : 'false';
            document.getElementById('shareholder-status').value = s.status;
            document.getElementById('shareholder-notes').value = s.notes || '';

            // Handle SAFE terms
            if (s.share_class === 'SAFE' && s.safe_terms) {
                document.getElementById('safe-terms-section').style.display = 'block';
                const safeTerms = typeof s.safe_terms === 'string' ? JSON.parse(s.safe_terms) : s.safe_terms;
                document.getElementById('shareholder-safe-discount').value = safeTerms.discount_rate || '';
                document.getElementById('shareholder-safe-cap').value = safeTerms.cap || '';
            } else {
                document.getElementById('safe-terms-section').style.display = 'none';
                document.getElementById('shareholder-safe-discount').value = '';
                document.getElementById('shareholder-safe-cap').value = '';
            }

            document.getElementById('shareholder-modal').classList.add('show');
        }
    } catch (error) {
        console.error('Error loading shareholder:', error);
        showError('Failed to load shareholder details');
    }
}

async function deleteShareholder(id) {
    if (!confirm('Are you sure you want to delete this shareholder? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/api/shareholders/${id}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
            showSuccess('Shareholder deleted successfully');
            loadShareholders();
            loadStats();
        } else {
            showError(data.error || 'Failed to delete shareholder');
        }
    } catch (error) {
        console.error('Error deleting shareholder:', error);
        showError('Failed to delete shareholder');
    }
}

function openAddContributionModal() {
    document.getElementById('contribution-form').reset();
    loadShareholderOptions();
    document.getElementById('contribution-modal').classList.add('show');
}

function closeContributionModal() {
    document.getElementById('contribution-modal').classList.remove('show');
}

async function loadShareholderOptions() {
    try {
        const response = await fetch('/api/shareholders?status=active');
        const data = await response.json();

        if (data.success) {
            const select = document.getElementById('contribution-shareholder');
            select.innerHTML = '<option value="">Select shareholder</option>' +
                data.shareholders.map(s => `<option value="${s.id}">${s.shareholder_name}</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading shareholders:', error);
    }
}

async function deleteContribution(id) {
    if (!confirm('Are you sure you want to delete this contribution?')) {
        return;
    }

    try {
        const response = await fetch(`/api/equity-contributions/${id}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
            showSuccess('Contribution deleted successfully');
            loadContributions();
            loadStats();
        } else {
            showError(data.error || 'Failed to delete contribution');
        }
    } catch (error) {
        console.error('Error deleting contribution:', error);
        showError('Failed to delete contribution');
    }
}

// Form Handlers
function setupFormHandlers() {
    // Shareholder form
    document.getElementById('shareholder-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const id = document.getElementById('shareholder-id').value;
        const shareClass = document.getElementById('shareholder-share-class').value;

        const payload = {
            shareholder_name: document.getElementById('shareholder-name').value,
            shareholder_type: document.getElementById('shareholder-type').value,
            entity: document.getElementById('shareholder-entity').value || null,
            share_class: shareClass,
            total_shares: document.getElementById('shareholder-shares').value || null,
            ownership_percentage: document.getElementById('shareholder-ownership').value || null,
            joining_date: document.getElementById('shareholder-joining-date').value || null,
            contact_email: document.getElementById('shareholder-email').value || null,
            contact_phone: document.getElementById('shareholder-phone').value || null,
            tax_id: document.getElementById('shareholder-tax-id').value || null,
            address: document.getElementById('shareholder-address').value || null,
            board_member: document.getElementById('shareholder-board').value === 'true',
            voting_rights: document.getElementById('shareholder-voting').value === 'true',
            status: document.getElementById('shareholder-status').value,
            notes: document.getElementById('shareholder-notes').value || null
        };

        // Add SAFE terms if share class is SAFE
        let safeInvestmentAmount = null;
        if (shareClass === 'SAFE') {
            payload.safe_discount_rate = parseFloat(document.getElementById('shareholder-safe-discount').value) || null;
            payload.safe_cap = parseFloat(document.getElementById('shareholder-safe-cap').value) || null;
            safeInvestmentAmount = parseFloat(document.getElementById('shareholder-safe-amount').value) || null;
        }

        try {
            const url = id ? `/api/shareholders/${id}` : '/api/shareholders';
            const method = id ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const data = await response.json();

            if (data.success) {
                // If SAFE investment amount was provided and we're creating (not editing), create contribution
                if (safeInvestmentAmount && safeInvestmentAmount > 0 && !id && data.shareholder_id) {
                    try {
                        const discountText = payload.safe_discount_rate ? payload.safe_discount_rate + '%' : 'N/A';
                        const capText = payload.safe_cap ? '$' + payload.safe_cap.toLocaleString() : 'N/A';

                        const contributionPayload = {
                            shareholder_id: data.shareholder_id,
                            contribution_date: payload.joining_date || new Date().toISOString().split('T')[0],
                            contribution_type: 'cash',
                            cash_amount: safeInvestmentAmount,
                            non_cash_value: 0,
                            shares_issued: 0,
                            share_class: 'SAFE',
                            description: 'SAFE investment - Discount Rate: ' + discountText + ', Valuation CAP: ' + capText,
                            notes: 'Auto-created from SAFE shareholder form'
                        };

                        const contribResponse = await fetch('/api/equity-contributions', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(contributionPayload)
                        });

                        const contribData = await contribResponse.json();
                        if (contribData.success) {
                            showSuccess('Shareholder and SAFE contribution created successfully');
                        } else {
                            showSuccess('Shareholder created, but contribution failed: ' + (contribData.error || 'Unknown error'));
                        }
                    } catch (contribError) {
                        console.error('Error creating contribution:', contribError);
                        showSuccess('Shareholder created, but contribution failed');
                    }
                } else {
                    showSuccess(id ? 'Shareholder updated successfully' : 'Shareholder created successfully');
                }

                closeShareholderModal();
                loadShareholders();
                loadStats();
                loadContributions();
            } else {
                showError(data.error || 'Failed to save shareholder');
            }
        } catch (error) {
            console.error('Error saving shareholder:', error);
            showError('Failed to save shareholder');
        }
    });

    // Contribution form
    document.getElementById('contribution-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = {
            shareholder_id: document.getElementById('contribution-shareholder').value,
            contribution_date: document.getElementById('contribution-date').value,
            contribution_type: document.getElementById('contribution-type').value,
            cash_amount: parseFloat(document.getElementById('contribution-cash').value) || 0,
            non_cash_value: parseFloat(document.getElementById('contribution-non-cash').value) || 0,
            shares_issued: parseInt(document.getElementById('contribution-shares').value),
            price_per_share: parseFloat(document.getElementById('contribution-price').value) || null,
            share_class: document.getElementById('contribution-share-class').value,
            valuation_at_contribution: parseFloat(document.getElementById('contribution-valuation').value) || null,
            dilution_percentage: parseFloat(document.getElementById('contribution-dilution').value) || null,
            description: document.getElementById('contribution-description').value || null,
            notes: document.getElementById('contribution-notes').value || null
        };

        try {
            const response = await fetch('/api/equity-contributions', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const data = await response.json();

            if (data.success) {
                showSuccess('Contribution created successfully');
                closeContributionModal();
                loadContributions();
                loadStats();
            } else {
                showError(data.error || 'Failed to save contribution');
            }
        } catch (error) {
            console.error('Error saving contribution:', error);
            showError('Failed to save contribution');
        }
    });
}

// Search
function setupSearchHandlers() {
    document.getElementById('shareholders-search').addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const filtered = shareholders.filter(s =>
            s.shareholder_name.toLowerCase().includes(query) ||
            s.shareholder_type.toLowerCase().includes(query) ||
            (s.share_class && s.share_class.toLowerCase().includes(query))
        );
        renderFilteredShareholders(filtered);
    });

    document.getElementById('contributions-search').addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const filtered = contributions.filter(c =>
            c.shareholder_name.toLowerCase().includes(query) ||
            c.contribution_type.toLowerCase().includes(query)
        );
        renderFilteredContributions(filtered);
    });
}

function renderFilteredShareholders(filtered) {
    const tbody = document.getElementById('shareholders-tbody');
    tbody.innerHTML = filtered.map(s => `
        <tr>
            <td>${s.shareholder_name}</td>
            <td>${s.entity || '-'}</td>
            <td><span class="type-badge type-${s.shareholder_type}">${formatType(s.shareholder_type)}</span></td>
            <td>${s.share_class || '-'}${s.share_class === 'SAFE' && s.safe_terms ? ' *' : ''}</td>
            <td>${(s.total_shares || 0).toLocaleString()}</td>
            <td>${parseFloat(s.ownership_percentage || 0).toFixed(2)}%</td>
            <td>${formatCurrency(s.total_contributed || 0)}</td>
            <td><span class="status-badge status-${s.status}">${s.status}</span></td>
            <td>
                <span class="action-icon" onclick="editShareholder('${s.id}')" title="Edit">✏️</span>
                <span class="action-icon" onclick="deleteShareholder('${s.id}')" title="Delete">🗑️</span>
            </td>
        </tr>
    `).join('');
}

function renderFilteredContributions(filtered) {
    const tbody = document.getElementById('contributions-tbody');
    tbody.innerHTML = filtered.map(c => `
        <tr>
            <td>${formatDate(c.contribution_date)}</td>
            <td>${c.shareholder_name}</td>
            <td>${formatType(c.contribution_type)}</td>
            <td>${formatCurrency(c.cash_amount || 0)}</td>
            <td>${formatCurrency(c.non_cash_value || 0)}</td>
            <td>${(c.shares_issued || 0).toLocaleString()}</td>
            <td>${c.price_per_share ? formatCurrency(c.price_per_share) : '-'}</td>
            <td>
                <span class="action-icon" onclick="deleteContribution('${c.id}')" title="Delete">🗑️</span>
            </td>
        </tr>
    `).join('');
}

// Refresh Functions
function refreshShareholders() {
    loadShareholders();
    loadStats();
}

function refreshContributions() {
    loadContributions();
    loadStats();
}

// Utility Functions
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {year: 'numeric', month: 'short', day: 'numeric'});
}

function formatType(type) {
    return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function showSuccess(message) {
    alert(message);
}

function showError(message) {
    alert('Error: ' + message);
}
