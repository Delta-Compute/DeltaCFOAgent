/**
 * CFO Home Dashboard JavaScript
 *
 * Handles all CFO dashboard interactions including managing clients,
 * assistants, and viewing statistics.
 */

// State
let currentClients = [];
let currentAssistants = [];
let currentStats = {};
let currentUser = null;
let selectedAssistantId = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadCurrentUser();
    loadStats();
    loadClients();
    loadAssistants();
    setupEventListeners();
});

// Load current user from localStorage
function loadCurrentUser() {
    const userStr = localStorage.getItem('user');

    if (!userStr) {
        window.location.href = '/auth/login';
        return;
    }

    currentUser = JSON.parse(userStr);

    // Verify user is a fractional CFO
    if (currentUser.user_type !== 'fractional_cfo') {
        window.location.href = '/';
        return;
    }

    // Update UI
    document.getElementById('userName').textContent = currentUser.display_name || currentUser.email;

    // Set avatar initial
    const initials = (currentUser.display_name || currentUser.email).charAt(0).toUpperCase();
    document.getElementById('userAvatar').textContent = initials;
}

// API Helper
async function apiCall(url, method = 'GET', data = null) {
    const token = await getFirebaseToken();

    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    const response = await fetch(url, options);
    const result = await response.json();

    if (!result.success) {
        throw new Error(result.message || 'An error occurred');
    }

    return result;
}

// Get Firebase token
async function getFirebaseToken() {
    // Import from firebase_client.js
    const { getCurrentUserToken } = await import('./firebase_client.js');
    return await getCurrentUserToken();
}

// Setup Event Listeners
function setupEventListeners() {
    // Add client
    document.getElementById('addClientBtn').addEventListener('click', () => openModal('addClientModal'));
    document.getElementById('addClientForm').addEventListener('submit', handleAddClient);

    // Invite assistant
    document.getElementById('inviteAssistantBtn').addEventListener('click', () => openInviteAssistantModal());
    document.getElementById('inviteAssistantForm').addEventListener('submit', handleInviteAssistant);

    // Manage assistant
    document.getElementById('manageAssistantForm').addEventListener('submit', handleManageAssistant);

    // Search clients
    document.getElementById('searchClients').addEventListener('input', filterClients);

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
}

// Load Stats
async function loadStats() {
    try {
        const result = await apiCall('/api/cfo/stats');
        currentStats = result.stats;
        renderStats();
    } catch (error) {
        console.error('Failed to load stats:', error);
        showStatsError();
    }
}

// Render Stats
function renderStats() {
    document.getElementById('totalClients').textContent = currentStats.total_clients || 0;
    document.getElementById('activeClients').textContent = currentStats.active_clients || 0;
    document.getElementById('totalAssistants').textContent = currentStats.total_assistants || 0;
    document.getElementById('totalUsers').textContent = currentStats.total_users || 0;
}

// Show stats error
function showStatsError() {
    document.getElementById('totalClients').innerHTML = '<span style="color: #e53e3e;">-</span>';
    document.getElementById('activeClients').innerHTML = '<span style="color: #e53e3e;">-</span>';
    document.getElementById('totalAssistants').innerHTML = '<span style="color: #e53e3e;">-</span>';
    document.getElementById('totalUsers').innerHTML = '<span style="color: #e53e3e;">-</span>';
}

// Load Clients
async function loadClients() {
    try {
        const result = await apiCall('/api/cfo/clients');
        currentClients = result.clients;
        renderClients();
    } catch (error) {
        showError('Failed to load clients: ' + error.message, 'clientsGrid');
    }
}

// Render Clients
function renderClients() {
    const grid = document.getElementById('clientsGrid');

    if (currentClients.length === 0) {
        grid.innerHTML = '<div class="empty-state">No clients yet. Add your first client to get started!</div>';
        return;
    }

    grid.innerHTML = currentClients.map(client => `
        <div class="client-card">
            <div class="client-header">
                <div class="client-avatar">${client.company_name.charAt(0).toUpperCase()}</div>
                <div class="client-info">
                    <h3>${client.company_name}</h3>
                    <p>${client.description || 'No description'}</p>
                </div>
            </div>
            <div class="client-stats">
                <div class="client-stat">
                    <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/>
                    </svg>
                    <span>${client.user_count || 0} users</span>
                </div>
                <div class="client-stat">
                    <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <span>${client.last_activity ? formatDate(client.last_activity) : 'Never'}</span>
                </div>
            </div>
            <div class="client-meta">
                <span class="badge badge-${getPaymentBadge(client.payment_owner)}">${client.payment_owner === 'cfo' ? 'CFO Paid' : 'Client Paid'}</span>
                <span class="badge badge-${getSubscriptionBadge(client.subscription_status)}">${formatSubscriptionStatus(client.subscription_status)}</span>
            </div>
            <div class="client-actions">
                <button class="btn-secondary btn-small" onclick="switchToClient('${client.id}')">
                    View Dashboard
                </button>
                <button class="btn-icon" onclick="viewClientDetails('${client.id}')" title="Details">
                    <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                </button>
            </div>
        </div>
    `).join('');
}

// Load Assistants
async function loadAssistants() {
    try {
        const result = await apiCall('/api/cfo/assistants');
        currentAssistants = result.assistants;
        renderAssistants();
    } catch (error) {
        showError('Failed to load assistants: ' + error.message, 'assistantsTableBody');
    }
}

// Render Assistants
function renderAssistants() {
    const tbody = document.getElementById('assistantsTableBody');

    if (currentAssistants.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No assistants yet. Invite an assistant to help manage your clients.</td></tr>';
        return;
    }

    tbody.innerHTML = currentAssistants.map(assistant => `
        <tr>
            <td>
                <div class="user-cell">
                    <div class="user-avatar-small">${assistant.display_name?.charAt(0).toUpperCase() || 'A'}</div>
                    <div class="user-name-cell">${assistant.display_name || 'N/A'}</div>
                </div>
            </td>
            <td>${assistant.email}</td>
            <td>
                <div class="client-badges">
                    ${assistant.client_count > 0 ? `<span class="badge badge-info">${assistant.client_count} client${assistant.client_count > 1 ? 's' : ''}</span>` : '<span class="text-muted">No clients</span>'}
                </div>
            </td>
            <td><span class="status-badge status-${assistant.is_active ? 'active' : 'inactive'}">${assistant.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>${assistant.last_login_at ? formatDate(assistant.last_login_at) : 'Never'}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn-icon" onclick="manageAssistantClients('${assistant.id}', '${assistant.display_name}')" title="Manage Clients">
                        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                            <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Filter Clients
function filterClients() {
    const searchTerm = document.getElementById('searchClients').value.toLowerCase();

    const filtered = currentClients.filter(client => {
        return client.company_name.toLowerCase().includes(searchTerm) ||
               (client.description && client.description.toLowerCase().includes(searchTerm));
    });

    // Update grid with filtered clients
    const temp = currentClients;
    currentClients = filtered;
    renderClients();
    currentClients = temp;
}

// Handle Add Client
async function handleAddClient(e) {
    e.preventDefault();
    setLoading('createClientBtn', true);
    hideAlerts('addClientModal');

    const companyName = document.getElementById('clientCompanyName').value;
    const description = document.getElementById('clientDescription').value;
    const adminEmail = document.getElementById('clientAdminEmail').value;

    try {
        await apiCall('/api/tenants', 'POST', {
            company_name: companyName,
            description,
            admin_email: adminEmail || undefined
        });

        showSuccess('Client created successfully!', 'addClientSuccess');
        setTimeout(() => {
            closeModal('addClientModal');
            loadClients();
            loadStats();
            document.getElementById('addClientForm').reset();
        }, 1500);
    } catch (error) {
        showAlert(error.message, 'addClientError', 'error');
        setLoading('createClientBtn', false);
    }
}

// Open Invite Assistant Modal
async function openInviteAssistantModal() {
    openModal('inviteAssistantModal');

    // Load clients for checkbox selection
    const container = document.getElementById('assistantClients');
    container.innerHTML = '<div class="loader-small"></div><p>Loading clients...</p>';

    try {
        const result = await apiCall('/api/cfo/clients');
        const clients = result.clients;

        if (clients.length === 0) {
            container.innerHTML = '<p class="text-muted">No clients available. Create a client first.</p>';
            return;
        }

        container.innerHTML = clients.map(client => `
            <label class="checkbox-label">
                <input type="checkbox" name="client_id" value="${client.id}">
                <span>${client.company_name}</span>
            </label>
        `).join('');
    } catch (error) {
        container.innerHTML = '<p class="text-error">Failed to load clients</p>';
    }
}

// Handle Invite Assistant
async function handleInviteAssistant(e) {
    e.preventDefault();
    setLoading('sendAssistantInviteBtn', true);
    hideAlerts('inviteAssistantModal');

    const email = document.getElementById('assistantEmail').value;

    // Get selected clients
    const clientIds = [];
    document.querySelectorAll('#assistantClients input[name="client_id"]:checked').forEach(cb => {
        clientIds.push(cb.value);
    });

    if (clientIds.length === 0) {
        showAlert('Please select at least one client', 'inviteAssistantError', 'error');
        setLoading('sendAssistantInviteBtn', false);
        return;
    }

    try {
        await apiCall('/api/cfo/assistants/invite', 'POST', {
            email,
            client_ids: clientIds
        });

        showSuccess('Assistant invited successfully!', 'inviteAssistantSuccess');
        setTimeout(() => {
            closeModal('inviteAssistantModal');
            loadAssistants();
            loadStats();
            document.getElementById('inviteAssistantForm').reset();
        }, 1500);
    } catch (error) {
        showAlert(error.message, 'inviteAssistantError', 'error');
        setLoading('sendAssistantInviteBtn', false);
    }
}

// Manage Assistant Clients
window.manageAssistantClients = async function(assistantId, assistantName) {
    selectedAssistantId = assistantId;
    document.getElementById('manageAssistantId').value = assistantId;
    document.getElementById('manageAssistantName').textContent = assistantName;

    const container = document.getElementById('manageAssistantClients');
    container.innerHTML = '<div class="loader-small"></div><p>Loading...</p>';

    openModal('manageAssistantModal');

    try {
        // Load all clients
        const clientsResult = await apiCall('/api/cfo/clients');
        const clients = clientsResult.clients;

        // Get current assistant details
        const assistant = currentAssistants.find(a => a.id === assistantId);
        const assistantClientIds = assistant ? assistant.client_ids : [];

        container.innerHTML = clients.map(client => `
            <label class="checkbox-label">
                <input type="checkbox" name="manage_client_id" value="${client.id}" ${assistantClientIds.includes(client.id) ? 'checked' : ''}>
                <span>${client.company_name}</span>
            </label>
        `).join('');
    } catch (error) {
        container.innerHTML = '<p class="text-error">Failed to load clients</p>';
    }
};

// Handle Manage Assistant
async function handleManageAssistant(e) {
    e.preventDefault();
    setLoading('updateAssistantBtn', true);
    hideAlerts('manageAssistantModal');

    const assistantId = document.getElementById('manageAssistantId').value;

    // Get selected clients
    const clientIds = [];
    document.querySelectorAll('#manageAssistantClients input[name="manage_client_id"]:checked').forEach(cb => {
        clientIds.push(cb.value);
    });

    try {
        await apiCall(`/api/cfo/assistants/${assistantId}/clients`, 'PUT', {
            client_ids: clientIds
        });

        showSuccess('Assistant access updated successfully!', 'manageAssistantSuccess');
        setTimeout(() => {
            closeModal('manageAssistantModal');
            loadAssistants();
        }, 1500);
    } catch (error) {
        showAlert(error.message, 'manageAssistantError', 'error');
        setLoading('updateAssistantBtn', false);
    }
}

// Switch to Client
window.switchToClient = function(clientId) {
    // Store selected tenant in localStorage
    const client = currentClients.find(c => c.id === clientId);
    if (client) {
        localStorage.setItem('current_tenant', JSON.stringify({
            id: client.id,
            company_name: client.company_name,
            role: client.role
        }));
        window.location.href = '/';
    }
};

// View Client Details
window.viewClientDetails = function(clientId) {
    // Navigate to tenant details page
    window.location.href = `/tenants/${clientId}`;
};

// Modal Functions
window.openModal = function(modalId) {
    document.getElementById(modalId).classList.add('active');
};

window.closeModal = function(modalId) {
    document.getElementById(modalId).classList.remove('active');
    hideAlerts(modalId);
};

// Utility Functions
function setLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    if (!btn) return;

    const textEl = btn.querySelector('.btn-text');
    const loaderEl = btn.querySelector('.btn-loader');

    if (loading) {
        btn.disabled = true;
        if (textEl) textEl.style.display = 'none';
        if (loaderEl) loaderEl.style.display = 'inline-block';
    } else {
        btn.disabled = false;
        if (textEl) textEl.style.display = 'inline';
        if (loaderEl) loaderEl.style.display = 'none';
    }
}

function showAlert(message, elementId, type) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.style.display = 'block';
    }
}

function showSuccess(message, elementId) {
    showAlert(message, elementId, 'success');
}

function hideAlerts(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.querySelectorAll('.alert').forEach(alert => {
            alert.style.display = 'none';
        });
    }
}

function showError(message, containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="error-cell">
                <div class="alert alert-error">${message}</div>
            </div>
        `;
    }
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getPaymentBadge(owner) {
    return owner === 'cfo' ? 'warning' : 'success';
}

function getSubscriptionBadge(status) {
    const map = {
        'active': 'success',
        'trial': 'info',
        'inactive': 'secondary',
        'cancelled': 'danger'
    };
    return map[status] || 'secondary';
}

function formatSubscriptionStatus(status) {
    if (!status) return 'N/A';
    return status.charAt(0).toUpperCase() + status.slice(1);
}

// Logout
async function handleLogout() {
    try {
        const { signOutUser } = await import('./firebase_client.js');
        await signOutUser();
        localStorage.clear();
        window.location.href = '/auth/login';
    } catch (error) {
        console.error('Logout error:', error);
        localStorage.clear();
        window.location.href = '/auth/login';
    }
}
