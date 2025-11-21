// Tenant Management JavaScript

let currentUser = null;
let currentToken = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await initializeAuth();
    await loadTenants();
    setupFormHandlers();
});

// Initialize Firebase Auth
async function initializeAuth() {
    return new Promise((resolve) => {
        firebase.auth().onAuthStateChanged(async (user) => {
            if (!user) {
                window.location.href = '/auth/login';
                return;
            }

            currentUser = user;
            currentToken = await user.getIdToken();
            resolve();
        });
    });
}

// Load all tenants for current user
async function loadTenants() {
    try {
        showLoading(true);

        const response = await fetch('/api/tenants', {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });

        const data = await response.json();

        if (data.success) {
            displayTenants(data.tenants);
            populateTenantSelector(data.tenants);
        } else {
            showMessage('Error loading tenants: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error loading tenants:', error);
        showMessage('Error loading tenants', 'error');
    } finally {
        showLoading(false);
    }
}

// Display tenants as cards
function displayTenants(tenants) {
    const container = document.getElementById('tenantListContainer');

    if (!tenants || tenants.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: #718096;">
                <p style="font-size: 1.2rem; margin-bottom: 0.5rem;">No tenants found</p>
                <p style="font-size: 0.9rem;">Create your first tenant to get started</p>
            </div>
        `;
        return;
    }

    container.innerHTML = tenants.map(tenant => `
        <div style="background: white; border-radius: 12px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); padding: 1.5rem; border-left: 4px solid ${getRoleColor(tenant.role)};">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                <h3 style="margin: 0; color: #2d3748; font-size: 1.2rem;">${escapeHtml(tenant.company_name)}</h3>
                <span style="background: ${getRoleColor(tenant.role)}; color: white; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">
                    ${tenant.role.toUpperCase()}
                </span>
            </div>

            ${tenant.description ? `
                <p style="color: #718096; font-size: 0.9rem; margin-bottom: 1rem; line-height: 1.5;">
                    ${escapeHtml(tenant.description)}
                </p>
            ` : ''}

            <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;">
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                    <span style="color: #94a3b8;">Status:</span>
                    <span style="color: #2d3748; font-weight: 600;">${tenant.subscription_status || 'trial'}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                    <span style="color: #94a3b8;">Payment:</span>
                    <span style="color: #2d3748; font-weight: 600;">${tenant.payment_owner || 'cfo'}</span>
                </div>
                ${tenant.admin_name ? `
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                        <span style="color: #94a3b8;">Admin:</span>
                        <span style="color: #2d3748;">${escapeHtml(tenant.admin_name)}</span>
                    </div>
                ` : ''}
            </div>

            <button
                onclick="switchToTenant('${tenant.id}')"
                style="width: 100%; padding: 0.75rem; background-color: #667eea; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: background-color 0.2s;"
                onmouseover="this.style.backgroundColor='#5a67d8'"
                onmouseout="this.style.backgroundColor='#667eea'">
                Switch to This Tenant
            </button>
        </div>
    `).join('');
}

// Populate tenant selector dropdown
function populateTenantSelector(tenants) {
    const selector = document.getElementById('tenantSelector');

    if (!tenants || tenants.length === 0) {
        selector.innerHTML = '<option value="">No tenants available</option>';
        return;
    }

    // Get current tenant from session/localStorage
    const currentTenantId = localStorage.getItem('current_tenant_id');

    selector.innerHTML = tenants.map(tenant => `
        <option value="${tenant.id}" ${tenant.id === currentTenantId ? 'selected' : ''}>
            ${escapeHtml(tenant.company_name)} (${tenant.role})
        </option>
    `).join('');

    // Add change handler
    selector.addEventListener('change', (e) => {
        if (e.target.value) {
            switchToTenant(e.target.value);
        }
    });
}

// Switch to a different tenant
async function switchToTenant(tenantId) {
    try {
        showLoading(true);

        // Store in localStorage
        localStorage.setItem('current_tenant_id', tenantId);

        // Send to backend to update session
        const response = await fetch('/api/users/switch-tenant', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ tenant_id: tenantId })
        });

        const data = await response.json();

        if (data.success) {
            showMessage('Tenant switched successfully!', 'success');
            // Reload page to refresh all tenant-scoped data
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showMessage('Error switching tenant: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error switching tenant:', error);
        showMessage('Error switching tenant', 'error');
    } finally {
        showLoading(false);
    }
}

// Setup form handlers
function setupFormHandlers() {
    const form = document.getElementById('createTenantForm');

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await createTenant();
        });
    }
}

// Create new tenant
async function createTenant() {
    const companyName = document.getElementById('companyName').value.trim();
    const companyDescription = document.getElementById('companyDescription').value.trim();
    const adminEmail = document.getElementById('adminEmail').value.trim();

    if (!companyName) {
        showMessage('Company name is required', 'error');
        return;
    }

    try {
        showLoading(true);

        const requestBody = {
            company_name: companyName
        };

        if (companyDescription) {
            requestBody.description = companyDescription;
        }

        if (adminEmail) {
            requestBody.admin_email = adminEmail;
        }

        const response = await fetch('/api/tenants', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.success) {
            showMessage('Tenant created successfully!', 'success');

            // Clear form
            document.getElementById('createTenantForm').reset();

            // Reload tenants
            await loadTenants();
        } else {
            showMessage('Error creating tenant: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error creating tenant:', error);
        showMessage('Error creating tenant', 'error');
    } finally {
        showLoading(false);
    }
}

// Utility Functions

function getRoleColor(role) {
    const colors = {
        'owner': '#667eea',
        'admin': '#48bb78',
        'cfo': '#ed8936',
        'cfo_assistant': '#4299e1',
        'employee': '#a0aec0'
    };
    return colors[role] || '#a0aec0';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
}

function showMessage(message, type = 'info') {
    const container = document.getElementById('messageContainer');

    const colors = {
        'success': { bg: '#48bb78', border: '#38a169' },
        'error': { bg: '#f56565', border: '#e53e3e' },
        'info': { bg: '#4299e1', border: '#3182ce' }
    };

    const color = colors[type] || colors.info;

    const messageEl = document.createElement('div');
    messageEl.style.cssText = `
        background: ${color.bg};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-left: 4px solid ${color.border};
        animation: slideIn 0.3s ease-out;
    `;
    messageEl.textContent = message;

    container.appendChild(messageEl);

    // Auto remove after 5 seconds
    setTimeout(() => {
        messageEl.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => messageEl.remove(), 300);
    }, 5000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
