/**
 * User Management Dashboard JavaScript
 *
 * Handles all user management interactions including listing users,
 * inviting new users, editing users, and managing permissions.
 */

// State
let currentUsers = [];
let currentInvitations = [];
let currentUser = null;
let currentTenant = null;
let selectedUserId = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadCurrentUser();
    loadUsers();
    loadInvitations();
    setupEventListeners();
});

// Load current user from localStorage
function loadCurrentUser() {
    const userStr = localStorage.getItem('user');
    const tenantStr = localStorage.getItem('current_tenant');

    if (!userStr) {
        window.location.href = '/auth/login';
        return;
    }

    currentUser = JSON.parse(userStr);
    currentTenant = tenantStr ? JSON.parse(tenantStr) : null;

    // Update UI
    document.getElementById('userName').textContent = currentUser.display_name || currentUser.email;
    document.getElementById('userRole').textContent = (currentTenant?.role || currentUser.user_type).replace('_', ' ').toUpperCase();
    document.getElementById('tenantName').textContent = currentTenant?.company_name || 'Delta CFO';

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
    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Search
    document.getElementById('searchUsers').addEventListener('input', filterUsers);

    // Filters
    document.getElementById('roleFilter').addEventListener('change', filterUsers);
    document.getElementById('showInactive').addEventListener('change', filterUsers);

    // Invite user
    document.getElementById('inviteUserBtn').addEventListener('click', () => openModal('inviteModal'));
    document.getElementById('inviteForm').addEventListener('submit', handleInviteUser);

    // Edit user
    document.getElementById('editForm').addEventListener('submit', handleEditUser);

    // Deactivate user
    document.getElementById('confirmDeactivateBtn').addEventListener('click', handleDeactivateUser);

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
}

// Load Users
async function loadUsers() {
    try {
        const result = await apiCall('/api/users?include_inactive=false');
        currentUsers = result.users;
        renderUsers();
    } catch (error) {
        showError('Failed to load users: ' + error.message, 'usersTableBody');
    }
}

// Load Invitations
async function loadInvitations() {
    try {
        const result = await apiCall('/api/users/invitations');
        currentInvitations = result.invitations;
        renderInvitations();
    } catch (error) {
        showError('Failed to load invitations: ' + error.message, 'invitationsTableBody');
    }
}

// Render Users
function renderUsers() {
    const tbody = document.getElementById('usersTableBody');

    if (currentUsers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No users found</td></tr>';
        return;
    }

    tbody.innerHTML = currentUsers.map(user => `
        <tr>
            <td>
                <div class="user-cell">
                    <div class="user-avatar-small">${user.display_name?.charAt(0).toUpperCase() || 'U'}</div>
                    <div>
                        <div class="user-name-cell">${user.display_name || 'N/A'}</div>
                        <div class="user-email-cell">${user.email}</div>
                    </div>
                </div>
            </td>
            <td><span class="badge badge-${getRoleBadgeClass(user.role)}">${formatRole(user.role)}</span></td>
            <td><span class="status-badge status-${user.is_active ? 'active' : 'inactive'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>${user.last_login_at ? formatDate(user.last_login_at) : 'Never'}</td>
            <td>${formatDate(user.added_at)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn-icon" onclick="editUser('${user.id}')" title="Edit">
                        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                        </svg>
                    </button>
                    <button class="btn-icon btn-danger" onclick="confirmDeactivate('${user.id}', '${user.display_name}')" title="Deactivate">
                        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Render Invitations
function renderInvitations() {
    const tbody = document.getElementById('invitationsTableBody');

    if (currentInvitations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No pending invitations</td></tr>';
        return;
    }

    tbody.innerHTML = currentInvitations.map(inv => `
        <tr>
            <td>${inv.email}</td>
            <td><span class="badge badge-${getRoleBadgeClass(inv.role)}">${formatRole(inv.role)}</span></td>
            <td>${inv.invited_by_name}</td>
            <td>${formatDate(inv.sent_at)}</td>
            <td>${formatDate(inv.expires_at)}</td>
            <td><span class="status-badge status-${inv.status}">${inv.status.toUpperCase()}</span></td>
            <td>
                <div class="action-buttons">
                    ${inv.status === 'pending' ? `
                        <button class="btn-icon" onclick="resendInvitation('${inv.id}')" title="Resend">
                            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                            </svg>
                        </button>
                        <button class="btn-icon btn-danger" onclick="revokeInvitation('${inv.id}')" title="Revoke">
                            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                <path d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `).join('');
}

// Filter Users
function filterUsers() {
    const searchTerm = document.getElementById('searchUsers').value.toLowerCase();
    const roleFilter = document.getElementById('roleFilter').value;
    const showInactive = document.getElementById('showInactive').checked;

    const filtered = currentUsers.filter(user => {
        const matchesSearch = user.display_name?.toLowerCase().includes(searchTerm) ||
                            user.email.toLowerCase().includes(searchTerm);
        const matchesRole = !roleFilter || user.role === roleFilter;
        const matchesActive = showInactive || user.is_active;

        return matchesSearch && matchesRole && matchesActive;
    });

    // Update table
    const tbody = document.getElementById('usersTableBody');
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No users match your filters</td></tr>';
        return;
    }

    // Re-render with filtered users (reuse render logic)
    const temp = currentUsers;
    currentUsers = filtered;
    renderUsers();
    currentUsers = temp;
}

// Handle Invite User
async function handleInviteUser(e) {
    e.preventDefault();
    setLoading('sendInviteBtn', true);
    hideAlerts('inviteModal');

    const email = document.getElementById('inviteEmail').value;
    const userType = document.getElementById('inviteUserType').value;
    const role = document.getElementById('inviteRole').value;

    // Get selected permissions
    const permissions = {};
    document.querySelectorAll('#inviteModal input[name="permission"]:checked').forEach(cb => {
        permissions[cb.value] = true;
    });

    try {
        await apiCall('/api/users/invite', 'POST', {
            email,
            user_type: userType,
            role,
            permissions
        });

        showSuccess('Invitation sent successfully!', 'inviteSuccess');
        setTimeout(() => {
            closeModal('inviteModal');
            loadInvitations();
            document.getElementById('inviteForm').reset();
        }, 1500);
    } catch (error) {
        showAlert(error.message, 'inviteError', 'error');
        setLoading('sendInviteBtn', false);
    }
}

// Edit User
window.editUser = async function(userId) {
    selectedUserId = userId;
    const user = currentUsers.find(u => u.id === userId);

    if (!user) return;

    // Populate form
    document.getElementById('editUserId').value = userId;
    document.getElementById('editDisplayName').value = user.display_name || '';
    document.getElementById('editRole').value = user.role;

    // Populate permissions
    const permissionsGrid = document.getElementById('editPermissions');
    const allPermissions = [
        'transactions.view', 'transactions.edit', 'transactions.delete',
        'invoices.view', 'invoices.edit', 'invoices.approve',
        'users.view', 'users.manage',
        'reports.view', 'reports.generate',
        'settings.view', 'settings.edit'
    ];

    permissionsGrid.innerHTML = allPermissions.map(perm => `
        <label class="checkbox-label">
            <input type="checkbox" name="edit_permission" value="${perm}" ${user.permissions?.[perm] ? 'checked' : ''}>
            <span>${formatPermission(perm)}</span>
        </label>
    `).join('');

    openModal('editModal');
};

// Handle Edit User
async function handleEditUser(e) {
    e.preventDefault();
    setLoading('updateUserBtn', true);
    hideAlerts('editModal');

    const displayName = document.getElementById('editDisplayName').value;
    const role = document.getElementById('editRole').value;

    // Get selected permissions
    const permissions = {};
    document.querySelectorAll('#editModal input[name="edit_permission"]:checked').forEach(cb => {
        permissions[cb.value] = true;
    });

    try {
        await apiCall(`/api/users/${selectedUserId}`, 'PUT', {
            display_name: displayName,
            role,
            permissions
        });

        showSuccess('User updated successfully!', 'editSuccess');
        setTimeout(() => {
            closeModal('editModal');
            loadUsers();
        }, 1500);
    } catch (error) {
        showAlert(error.message, 'editError', 'error');
        setLoading('updateUserBtn', false);
    }
}

// Confirm Deactivate
window.confirmDeactivate = function(userId, userName) {
    selectedUserId = userId;
    document.getElementById('deactivateUserName').textContent = userName;
    openModal('deactivateModal');
};

// Handle Deactivate User
async function handleDeactivateUser() {
    setLoading('confirmDeactivateBtn', true);
    hideAlerts('deactivateModal');

    try {
        await apiCall(`/api/users/${selectedUserId}`, 'DELETE');
        closeModal('deactivateModal');
        loadUsers();
    } catch (error) {
        showAlert(error.message, 'deactivateError', 'error');
        setLoading('confirmDeactivateBtn', false);
    }
}

// Resend Invitation
window.resendInvitation = async function(invitationId) {
    try {
        await apiCall(`/api/users/invitations/${invitationId}/resend`, 'POST');
        alert('Invitation resent successfully!');
    } catch (error) {
        alert('Failed to resend invitation: ' + error.message);
    }
};

// Revoke Invitation
window.revokeInvitation = async function(invitationId) {
    if (!confirm('Are you sure you want to revoke this invitation?')) return;

    try {
        await apiCall(`/api/users/invitations/${invitationId}`, 'DELETE');
        loadInvitations();
    } catch (error) {
        alert('Failed to revoke invitation: ' + error.message);
    }
};

// Switch Tab
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    if (tabName === 'team') {
        document.getElementById('teamTab').classList.add('active');
    } else {
        document.getElementById('invitationsTab').classList.add('active');
    }
}

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
            <tr>
                <td colspan="6" class="error-cell">
                    <div class="alert alert-error">${message}</div>
                </td>
            </tr>
        `;
    }
}

function formatRole(role) {
    if (!role) return 'N/A';
    return role.replace('_', ' ').split(' ').map(word =>
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

function formatPermission(perm) {
    return perm.split('.').map(word =>
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

function getRoleBadgeClass(role) {
    const map = {
        'owner': 'primary',
        'admin': 'success',
        'cfo': 'info',
        'cfo_assistant': 'warning',
        'employee': 'secondary'
    };
    return map[role] || 'secondary';
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
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
